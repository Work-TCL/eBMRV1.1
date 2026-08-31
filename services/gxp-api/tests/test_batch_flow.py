"""Covers the mandatory negative/failure set from .claude/rules/01-gxp-mutation-rules.md: unauthorized
user, stale version, duplicate submission (same key / changed payload), missing signature, invalid
transition, and the SoD independent-signer rule — plus one full happy-path walkthrough that checks the
audit/outbox transactional guarantee directly against the database.
"""

import uuid
from unittest.mock import patch

import pytest
from sqlalchemy import func, select
from sqlalchemy.exc import OperationalError

from app.core.db import SessionLocal
from app.modules.audit.models import AuditEvent
from app.modules.batch.commands import StartStepCommand, start_step
from app.modules.batch.models import Batch, BatchStep
from app.modules.mutation.models import CommandReceipt, OutboxEvent
from app.modules.signature.models import Signature, SignaturePolicy
from tests.conftest import auth_headers, idem, login


async def _create_product_recipe(client, token, site_id):
    resp = await client.post(
        "/products",
        json={"idempotency_key": idem(), "site_id": str(site_id), "code": "P1", "name": "Product 1"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    product_id = resp.json()["aggregate_id"]

    resp = await client.post(
        "/recipes",
        json={
            "idempotency_key": idem(),
            "product_id": product_id,
            "version": 1,
            "steps": [
                {"step_number": 1, "name": "Dispense", "requires_signature": False},
                {
                    "step_number": 2,
                    "name": "Blend",
                    "requires_signature": True,
                    "signature_meaning": "Performed",
                },
            ],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return product_id, resp.json()["aggregate_id"]


async def _create_and_issue_batch(client, token, site_id, product_id, recipe_id, batch_number="B1"):
    resp = await client.post(
        "/batches",
        json={
            "idempotency_key": idem(),
            "site_id": str(site_id),
            "product_id": product_id,
            "recipe_id": recipe_id,
            "recipe_version": 1,
            "batch_number": batch_number,
            "target_quantity": "10.000000",
            "uom": "kg",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/batches/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return batch_id


async def _complete_step_signed(client, token, batch_id, step, expected_version):
    challenge = (
        await client.post(
            f"/batches/{batch_id}/signature-challenges",
            json={"action": "complete_step", "batch_step_id": step["batch_step_id"]},
            headers=auth_headers(token),
        )
    ).json()
    resp = await client.post(
        f"/batches/{batch_id}/steps/{step['batch_step_id']}/complete",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": expected_version,
            "batch_step_id": step["batch_step_id"],
            "data": {},
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text


async def _walk_batch_to_release_ready(client, op_token, reviewer_token, site_id, batch_number):
    """Build a batch and drive it through both steps and an approved QA review, stopping right before
    release — the shared setup for the Fix 3b dependency-outage tests below.
    """
    product_id, recipe_id = await _create_product_recipe(client, op_token, site_id)
    batch_id = await _create_and_issue_batch(client, op_token, site_id, product_id, recipe_id, batch_number)

    detail = (await client.get(f"/batches/{batch_id}")).json()
    step1, step2 = detail["steps"]

    for step, start_version, complete_version in ((step1, 2, 3), (step2, 4, 5)):
        resp = await client.post(
            f"/batches/{batch_id}/steps/{step['batch_step_id']}/start",
            json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": start_version, "batch_step_id": step["batch_step_id"]},
            headers=auth_headers(op_token),
        )
        assert resp.status_code == 200, resp.text
        await _complete_step_signed(client, op_token, batch_id, step, complete_version)

    resp = await client.post(
        f"/batches/{batch_id}/submit-for-review",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 6},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    challenge = (
        await client.post(
            f"/batches/{batch_id}/signature-challenges",
            json={"action": "review"},
            headers=auth_headers(reviewer_token),
        )
    ).json()
    resp = await client.post(
        f"/batches/{batch_id}/review",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 7,
            "decision": "approved",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(reviewer_token),
    )
    assert resp.status_code == 200, resp.text
    return batch_id  # at version 8, qa_review, ready for release


async def test_full_happy_path_and_audit_outbox_guarantee(client, seeded, db):
    site_id = seeded["site_id"]
    op_token = await login(client, "operator1")

    product_id, recipe_id = await _create_product_recipe(client, op_token, site_id)
    batch_id = await _create_and_issue_batch(client, op_token, site_id, product_id, recipe_id)

    # SG-146 (remainder, module 4 of 8): "kg" has no released rules.gxp_uom row in this environment --
    # the dual-write is a no-op (expand-phase contract, nothing breaks).
    batch_row = await db.get(Batch, uuid.UUID(batch_id))
    assert batch_row.uom == "kg"
    assert batch_row.uom_id is None

    detail = (await client.get(f"/batches/{batch_id}")).json()
    step1, step2 = detail["steps"]

    resp = await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2, "batch_step_id": step1["batch_step_id"]},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    # step1's recipe flag is requires_signature=False, but the Document 106 platform floor for
    # batch_step/complete_step is unconditional — the floor can only be raised by a recipe, never
    # lowered, so every step completion needs a signature (REMEDIATION_R1 FIX 1).
    challenge = (
        await client.post(
            f"/batches/{batch_id}/signature-challenges",
            json={"action": "complete_step", "batch_step_id": step1["batch_step_id"]},
            headers=auth_headers(op_token),
        )
    ).json()
    resp = await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/complete",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 3,
            "batch_step_id": step1["batch_step_id"],
            "data": {},
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/batches/{batch_id}/steps/{step2['batch_step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 4, "batch_step_id": step2["batch_step_id"]},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    challenge = (
        await client.post(
            f"/batches/{batch_id}/signature-challenges",
            json={"action": "complete_step", "batch_step_id": step2["batch_step_id"]},
            headers=auth_headers(op_token),
        )
    ).json()
    resp = await client.post(
        f"/batches/{batch_id}/steps/{step2['batch_step_id']}/complete",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 5,
            "batch_step_id": step2["batch_step_id"],
            "data": {},
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/batches/{batch_id}/submit-for-review",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 6},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text

    reviewer_token = await login(client, "qa.reviewer")
    challenge = (
        await client.post(
            f"/batches/{batch_id}/signature-challenges",
            json={"action": "review"},
            headers=auth_headers(reviewer_token),
        )
    ).json()
    resp = await client.post(
        f"/batches/{batch_id}/review",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 7,
            "decision": "approved",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(reviewer_token),
    )
    assert resp.status_code == 200, resp.text

    releaser_token = await login(client, "qa.releaser")
    challenge = (
        await client.post(
            f"/batches/{batch_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(releaser_token),
        )
    ).json()
    resp = await client.post(
        f"/batches/{batch_id}/release",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 8,
            "decision": "released",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 200, resp.text

    final = (await client.get(f"/batches/{batch_id}")).json()
    assert final["status"] == "released"
    assert final["version"] == 9

    # The transactional guarantee: exactly one audit row and one outbox row per version.
    audit_rows = (
        await db.execute(select(AuditEvent).where(AuditEvent.aggregate_id == batch_id))
    ).scalars().all()
    outbox_rows = (
        await db.execute(select(OutboxEvent).where(OutboxEvent.aggregate_id == batch_id))
    ).scalars().all()
    assert len(audit_rows) == 9
    assert len(outbox_rows) == 9
    assert {r.aggregate_version for r in audit_rows} == set(range(1, 10))


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/products", json={"idempotency_key": idem(), "site_id": str(1), "code": "X", "name": "X"})
    assert resp.status_code == 401


async def test_stale_version_rejected(client, seeded):
    site_id = seeded["site_id"]
    op_token = await login(client, "operator1")
    product_id, recipe_id = await _create_product_recipe(client, op_token, site_id)
    batch_id = await _create_and_issue_batch(client, op_token, site_id, product_id, recipe_id, "B-STALE")

    resp = await client.post(
        f"/batches/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_same_payload_returns_same_receipt(client, seeded):
    site_id = seeded["site_id"]
    op_token = await login(client, "operator1")
    key = idem()
    body = {"idempotency_key": key, "site_id": str(site_id), "code": "DUP1", "name": "Dup"}
    first = await client.post("/products", json=body, headers=auth_headers(op_token))
    second = await client.post("/products", json=body, headers=auth_headers(op_token))
    assert first.status_code == 200 and second.status_code == 200
    assert first.json()["command_id"] == second.json()["command_id"]
    assert first.json()["aggregate_id"] == second.json()["aggregate_id"]


async def test_idempotency_conflict_on_changed_payload(client, seeded):
    site_id = seeded["site_id"]
    op_token = await login(client, "operator1")
    key = idem()
    await client.post(
        "/products",
        json={"idempotency_key": key, "site_id": str(site_id), "code": "C1", "name": "Original"},
        headers=auth_headers(op_token),
    )
    resp = await client.post(
        "/products",
        json={"idempotency_key": key, "site_id": str(site_id), "code": "C2-DIFFERENT", "name": "Changed"},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_missing_signature_rejected(client, seeded):
    """step1's recipe flag is requires_signature=False, but the Document 106 platform floor for
    batch_step/complete_step is unconditional (REMEDIATION_R1 FIX 1) — completing it with no signature
    is rejected even though the recipe itself never asked for one.
    """
    site_id = seeded["site_id"]
    op_token = await login(client, "operator1")
    product_id, recipe_id = await _create_product_recipe(client, op_token, site_id)
    batch_id = await _create_and_issue_batch(client, op_token, site_id, product_id, recipe_id, "B-SIG")

    detail = (await client.get(f"/batches/{batch_id}")).json()
    step1, _step2 = detail["steps"]

    await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2, "batch_step_id": step1["batch_step_id"]},
        headers=auth_headers(op_token),
    )
    resp = await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/complete",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 3, "batch_step_id": step1["batch_step_id"], "data": {}},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 428
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_release_before_review_rejected(client, seeded):
    site_id = seeded["site_id"]
    op_token = await login(client, "operator1")
    product_id, recipe_id = await _create_product_recipe(client, op_token, site_id)
    batch_id = await _create_and_issue_batch(client, op_token, site_id, product_id, recipe_id, "B-ORDER")

    releaser_token = await login(client, "qa.releaser")
    challenge = (
        await client.post(
            f"/batches/{batch_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(releaser_token),
        )
    ).json()
    resp = await client.post(
        f"/batches/{batch_id}/release",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 2,
            "decision": "released",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_sod_reviewer_cannot_release_own_review(client, seeded, db):
    """Independent-signer rule: the same person cannot both review and release a batch."""
    from app.modules.iam.models import Role, UserSiteRole
    from app.core.security import hash_password
    from app.modules.iam.models import User

    # Give qa.reviewer the QA Releaser role too, so the only thing stopping them is the SoD check,
    # not a missing role.
    async with db.begin():
        releaser_role = (
            await db.execute(select(Role).where(Role.name == "QA Releaser"))
        ).scalar_one()
        reviewer_user = (
            await db.execute(select(User).where(User.username == "qa.reviewer"))
        ).scalar_one()
        db.add(UserSiteRole(user_id=reviewer_user.id, site_id=seeded["site_id"], role_id=releaser_role.id))

    op_token = await login(client, "operator1")
    product_id, recipe_id = await _create_product_recipe(client, op_token, site_id=seeded["site_id"])
    batch_id = await _create_and_issue_batch(
        client, op_token, seeded["site_id"], product_id, recipe_id, "B-SOD"
    )
    detail = (await client.get(f"/batches/{batch_id}")).json()
    step1, step2 = detail["steps"]
    for step, expected_version in ((step1, 2), (step2, 4)):
        await client.post(
            f"/batches/{batch_id}/steps/{step['batch_step_id']}/start",
            json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": expected_version, "batch_step_id": step["batch_step_id"]},
            headers=auth_headers(op_token),
        )
        body = {"idempotency_key": idem(), "batch_id": batch_id, "expected_version": expected_version + 1, "batch_step_id": step["batch_step_id"], "data": {}}
        # Every step needs a signature now (Document 106 platform floor is unconditional for
        # batch_step/complete_step, REMEDIATION_R1 FIX 1) — not just the recipe-flagged one.
        challenge = (
            await client.post(
                f"/batches/{batch_id}/signature-challenges",
                json={"action": "complete_step", "batch_step_id": step["batch_step_id"]},
                headers=auth_headers(op_token),
            )
        ).json()
        body["challenge_id"] = challenge["challenge_id"]
        body["reauth_password"] = "ChangeMe123!"
        await client.post(
            f"/batches/{batch_id}/steps/{step['batch_step_id']}/complete", json=body, headers=auth_headers(op_token)
        )
    await client.post(
        f"/batches/{batch_id}/submit-for-review",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 6},
        headers=auth_headers(op_token),
    )

    reviewer_token = await login(client, "qa.reviewer")
    challenge = (
        await client.post(
            f"/batches/{batch_id}/signature-challenges",
            json={"action": "review"},
            headers=auth_headers(reviewer_token),
        )
    ).json()
    await client.post(
        f"/batches/{batch_id}/review",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 7,
            "decision": "approved",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(reviewer_token),
    )

    challenge = (
        await client.post(
            f"/batches/{batch_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(reviewer_token),
        )
    ).json()
    resp = await client.post(
        f"/batches/{batch_id}/release",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 8,
            "decision": "released",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(reviewer_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_TRANSITION"
    assert "independent" in resp.json()["message"].lower()


# ---------------------------------------------------------------------------
# REMEDIATION_R1 FIX 1 — signature policy must fail closed (Doc 106 SIGP-FR-004)
# ---------------------------------------------------------------------------


async def test_signature_policy_missing_fails_closed(client, seeded, db):
    """Deleting the policy row must block the command, not permit an unsigned commit."""
    site_id = seeded["site_id"]
    op_token = await login(client, "operator1")
    product_id, recipe_id = await _create_product_recipe(client, op_token, site_id)
    batch_id = await _create_and_issue_batch(client, op_token, site_id, product_id, recipe_id, "B-NOPOLICY")

    detail = (await client.get(f"/batches/{batch_id}")).json()
    step1, _step2 = detail["steps"]

    await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2, "batch_step_id": step1["batch_step_id"]},
        headers=auth_headers(op_token),
    )

    # The runtime app role has no DELETE grant anywhere (migration 0002_append_only_privilege_lockdown
    # never grants DELETE at all, by design — PG-FR-005) — deleting a policy row to simulate "missing"
    # has to go through the migration role, same as a real DBA-controlled config change would.
    from sqlalchemy.ext.asyncio import create_async_engine

    from app.core.config import settings

    migration_engine = create_async_engine(settings.migration_database_url)
    try:
        async with migration_engine.begin() as conn:
            await conn.execute(
                SignaturePolicy.__table__.delete().where(
                    SignaturePolicy.record_type == "batch_step", SignaturePolicy.action == "complete_step"
                )
            )
    finally:
        await migration_engine.dispose()

    # The router's challenge-creation gate resolves the same policy (REMEDIATION_R1 FIX 1 corollary),
    # so this fails closed before a challenge can even be created — there is no way to route around it
    # by skipping straight to /complete without a challenge_id, since that path raises MISSING_SIGNATURE
    # instead and still never commits.
    resp = await client.post(
        f"/batches/{batch_id}/signature-challenges",
        json={"action": "complete_step", "batch_step_id": step1["batch_step_id"]},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"

    resp = await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/complete",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 3,
            "batch_step_id": step1["batch_step_id"],
            "data": {},
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"

    async with SessionLocal() as fresh:
        step = await fresh.get(BatchStep, uuid.UUID(step1["batch_step_id"]))
        assert step.status == "in_progress"  # never reached "completed"
        batch = await fresh.get(Batch, uuid.UUID(batch_id))
        assert batch.version == 3  # unchanged since the start_step commit
        audit_count = (
            await fresh.execute(
                select(func.count()).select_from(AuditEvent).where(
                    AuditEvent.aggregate_id == uuid.UUID(batch_id), AuditEvent.aggregate_version == 4
                )
            )
        ).scalar_one()
        assert audit_count == 0


async def test_recipe_flag_cannot_lower_policy_floor(client, seeded):
    """The recipe step is authored with requires_signature=False, but the Document 106 platform floor
    for batch_step/complete_step is signature_required=True — the recipe can raise the requirement,
    never lower it, so the step is still rejected without a signature.
    """
    site_id = seeded["site_id"]
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/products",
        json={"idempotency_key": idem(), "site_id": str(site_id), "code": "P-FLOOR", "name": "Floor Test"},
        headers=auth_headers(op_token),
    )
    product_id = resp.json()["aggregate_id"]
    resp = await client.post(
        "/recipes",
        json={
            "idempotency_key": idem(),
            "product_id": product_id,
            "version": 1,
            "steps": [{"step_number": 1, "name": "Unsigned by recipe", "requires_signature": False}],
        },
        headers=auth_headers(op_token),
    )
    recipe_id = resp.json()["aggregate_id"]
    batch_id = await _create_and_issue_batch(client, op_token, site_id, product_id, recipe_id, "B-FLOOR")

    detail = (await client.get(f"/batches/{batch_id}")).json()
    (step1,) = detail["steps"]
    assert step1["requires_signature"] is False

    await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2, "batch_step_id": step1["batch_step_id"]},
        headers=auth_headers(op_token),
    )
    resp = await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/complete",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 3, "batch_step_id": step1["batch_step_id"], "data": {}},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 428
    assert resp.json()["code"] == "MISSING_SIGNATURE"


# ---------------------------------------------------------------------------
# REMEDIATION_R1 FIX 3a — transaction rollback leaves no orphan state
# ---------------------------------------------------------------------------


async def test_transaction_rollback_leaves_no_orphan_state(client, seeded, db):
    """Failure after the domain write must leave no domain row, audit event, outbox row or receipt,
    at every injection point in the mutation gateway kernel. Read back through a fresh session — the
    rolled-back session's identity map can look consistent even when nothing actually committed.
    """
    site_id = seeded["site_id"]
    operator_id = seeded["users"]["operator1"].id
    op_token = await login(client, "operator1")
    product_id, recipe_id = await _create_product_recipe(client, op_token, site_id)
    batch_id = await _create_and_issue_batch(client, op_token, site_id, product_id, recipe_id, "B-ROLLBACK")

    detail = (await client.get(f"/batches/{batch_id}")).json()
    step1 = detail["steps"][0]

    injection_points = [
        "app.modules.batch.commands.write_audit_event",
        "app.modules.batch.commands.write_outbox_event",
        "app.modules.batch.commands.record_command_receipt",
    ]
    for target in injection_points:
        cmd = StartStepCommand(
            idempotency_key=idem(),
            batch_id=uuid.UUID(batch_id),
            expected_version=2,
            batch_step_id=uuid.UUID(step1["batch_step_id"]),
        )
        with patch(target, side_effect=RuntimeError(f"injected failure at {target}")):
            with pytest.raises(RuntimeError):
                async with db.begin():
                    await start_step(db, cmd, operator_id, site_id)

        async with SessionLocal() as fresh:
            step = await fresh.get(BatchStep, uuid.UUID(step1["batch_step_id"]))
            assert step.status == "ready"  # unchanged — never reached "in_progress"
            batch = await fresh.get(Batch, uuid.UUID(batch_id))
            assert batch.version == 2  # unchanged, not incremented
            audit_count = (
                await fresh.execute(
                    select(func.count()).select_from(AuditEvent).where(
                        AuditEvent.aggregate_id == uuid.UUID(batch_id), AuditEvent.aggregate_version == 3
                    )
                )
            ).scalar_one()
            outbox_count = (
                await fresh.execute(
                    select(func.count()).select_from(OutboxEvent).where(
                        OutboxEvent.aggregate_id == uuid.UUID(batch_id), OutboxEvent.aggregate_version == 3
                    )
                )
            ).scalar_one()
            receipt_count = (
                await fresh.execute(
                    select(func.count()).select_from(CommandReceipt).where(
                        CommandReceipt.idempotency_key == cmd.idempotency_key
                    )
                )
            ).scalar_one()
            assert audit_count == 0, f"orphan audit event after failure at {target}"
            assert outbox_count == 0, f"orphan outbox event after failure at {target}"
            assert receipt_count == 0, f"orphan command receipt after failure at {target}"


# ---------------------------------------------------------------------------
# REMEDIATION_R1 FIX 3b — dependency outage fails closed (MUT-FR-022)
# ---------------------------------------------------------------------------


async def test_signature_service_unavailable_fails_closed(client, seeded, db):
    site_id = seeded["site_id"]
    op_token = await login(client, "operator1")
    reviewer_token = await login(client, "qa.reviewer")
    batch_id = await _walk_batch_to_release_ready(client, op_token, reviewer_token, site_id, "B-SIGOUT")

    releaser_token = await login(client, "qa.releaser")
    challenge = (
        await client.post(
            f"/batches/{batch_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(releaser_token),
        )
    ).json()
    with patch(
        "app.modules.signature.service.consume_challenge",
        side_effect=OperationalError("connection lost", None, None),
    ):
        resp = await client.post(
            f"/batches/{batch_id}/release",
            json={
                "idempotency_key": idem(),
                "batch_id": batch_id,
                "expected_version": 8,
                "decision": "released",
                "challenge_id": challenge["challenge_id"],
                "reauth_password": "ChangeMe123!",
            },
            headers=auth_headers(releaser_token),
        )
    assert resp.status_code >= 400
    assert resp.json()["code"] in ("DEPENDENCY_UNAVAILABLE", "SYSTEM_FAULT")

    async with SessionLocal() as fresh:
        batch = await fresh.get(Batch, uuid.UUID(batch_id))
        assert batch.status != "released"
        # Getting the batch to qa_review already created 3 legitimate signatures (2 step completions +
        # 1 review) — the assertion that matters is that the outage produced no *additional* one for
        # this release attempt, i.e. no degraded-mode commit.
        released_sig_count = (
            await fresh.execute(
                select(func.count()).select_from(Signature).where(
                    Signature.record_id == uuid.UUID(batch_id), Signature.meaning == "Released"
                )
            )
        ).scalar_one()
        assert released_sig_count == 0


async def test_authorization_unavailable_fails_closed(client, seeded, db):
    """Same fail-closed guarantee, injected at the authorization dependency instead of signature."""
    site_id = seeded["site_id"]
    op_token = await login(client, "operator1")
    reviewer_token = await login(client, "qa.reviewer")
    batch_id = await _walk_batch_to_release_ready(client, op_token, reviewer_token, site_id, "B-AUTHZOUT")

    releaser_token = await login(client, "qa.releaser")
    challenge = (
        await client.post(
            f"/batches/{batch_id}/signature-challenges",
            json={"action": "release"},
            headers=auth_headers(releaser_token),
        )
    ).json()
    with patch(
        "app.modules.batch.commands.evaluate_policy",
        side_effect=OperationalError("connection lost", None, None),
    ):
        resp = await client.post(
            f"/batches/{batch_id}/release",
            json={
                "idempotency_key": idem(),
                "batch_id": batch_id,
                "expected_version": 8,
                "decision": "released",
                "challenge_id": challenge["challenge_id"],
                "reauth_password": "ChangeMe123!",
            },
            headers=auth_headers(releaser_token),
        )
    assert resp.status_code >= 400
    assert resp.json()["code"] in ("DEPENDENCY_UNAVAILABLE", "SYSTEM_FAULT")

    async with SessionLocal() as fresh:
        batch = await fresh.get(Batch, uuid.UUID(batch_id))
        assert batch.status != "released"
