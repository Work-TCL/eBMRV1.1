"""Covers the mandatory negative/failure set from .claude/rules/01-gxp-mutation-rules.md: unauthorized
user, stale version, duplicate submission (same key / changed payload), missing signature, invalid
transition, and the SoD independent-signer rule — plus one full happy-path walkthrough that checks the
audit/outbox transactional guarantee directly against the database.
"""

from sqlalchemy import select

from app.modules.audit.models import AuditEvent
from app.modules.mutation.models import OutboxEvent
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


async def test_full_happy_path_and_audit_outbox_guarantee(client, seeded, db):
    site_id = seeded["site_id"]
    op_token = await login(client, "operator1")

    product_id, recipe_id = await _create_product_recipe(client, op_token, site_id)
    batch_id = await _create_and_issue_batch(client, op_token, site_id, product_id, recipe_id)

    detail = (await client.get(f"/batches/{batch_id}")).json()
    step1, step2 = detail["steps"]

    resp = await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2, "batch_step_id": step1["batch_step_id"]},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/complete",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 3, "batch_step_id": step1["batch_step_id"], "data": {}},
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
    site_id = seeded["site_id"]
    op_token = await login(client, "operator1")
    product_id, recipe_id = await _create_product_recipe(client, op_token, site_id)
    batch_id = await _create_and_issue_batch(client, op_token, site_id, product_id, recipe_id, "B-SIG")

    detail = (await client.get(f"/batches/{batch_id}")).json()
    step1, step2 = detail["steps"]

    await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2, "batch_step_id": step1["batch_step_id"]},
        headers=auth_headers(op_token),
    )
    await client.post(
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/complete",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 3, "batch_step_id": step1["batch_step_id"], "data": {}},
        headers=auth_headers(op_token),
    )
    await client.post(
        f"/batches/{batch_id}/steps/{step2['batch_step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 4, "batch_step_id": step2["batch_step_id"]},
        headers=auth_headers(op_token),
    )
    resp = await client.post(
        f"/batches/{batch_id}/steps/{step2['batch_step_id']}/complete",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 5, "batch_step_id": step2["batch_step_id"], "data": {}},
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
        if step["requires_signature"]:
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
