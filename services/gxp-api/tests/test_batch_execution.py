"""Document 11 (SPEC-EBMR-002) -- the buildable slice: create/issue/start/hold/resume/abort a batch and
claim/start a batch step, against real released product_master/recipe_master versions. New, additive
module -- does not touch app/modules/batch (the legacy Batch-facing stub); the full pre-existing suite
passes unmodified, proving that. Everything gated on gxp_step_result/gxp_step_evidence_link/
gxp_batch_hold or on absent infrastructure (Temporal, Material Service, Equipment, qualification schema,
exception/rework/branch entities) is out of scope this pass -- SG-047/SG-048.
"""

import uuid
from datetime import datetime, timedelta, timezone

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.batch_execution.models import Batch
from app.modules.equipment.commands import QUALIFIED_MARKER
from app.modules.equipment.models import EquipmentAsset
from app.modules.iam.models import Permission, Qualification, Role, RolePermission, User, UserSiteRole
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username="admin.batch"):
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name="Test Admin",
        password_hash=hash_password(DEMO_PASSWORD),
        status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))
    return user


async def _make_released_product_and_recipe(
    client, admin_token, site_id, tag, step_a_role=None, step_a_parameters=None, step_a_evidence=None,
    step_a_qualification_code=None, step_a_equipment_requirements=None, step_a_qc_requirements=None,
):
    resp = await client.post(
        "/products/v1/drafts",
        json={
            "idempotency_key": idem(),
            "product_business_id": f"BATPRD-{tag}",
            "product_code": f"BATPRD-{tag}",
            "name": "Batch Test Product",
            "version_no": 1,
            "site_id": str(site_id),
            "manufacturing_profile_code": "pharma",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    product_version_id = resp.json()["aggregate_id"]

    await client.post(
        f"/products/v1/drafts/{product_version_id}/submit",
        json={"idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/products/v1/drafts/{product_version_id}/release",
        json={"idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/recipes/v2/drafts",
        json={
            "idempotency_key": idem(),
            "product_business_id": f"BATPRD-{tag}",
            "recipe_code": f"BATRCP-{tag}",
            "version_no": 1,
            "product_version_id": product_version_id,
            "site_id": str(site_id),
            "manufacturing_profile_code": "pharma",
            "sections": [{"stable_section_code": "SEC-1", "name": "Dispensing", "sequence": 1}],
            "steps": [
                {
                    "stable_step_code": "STEP-A", "section_code": "SEC-1", "step_type": "weigh", "sequence_hint": 1,
                    **({"required_role_code": step_a_role} if step_a_role else {}),
                    **({"parameters": step_a_parameters} if step_a_parameters else {}),
                    **({"evidence_requirements": step_a_evidence} if step_a_evidence else {}),
                    **({"required_qualification_code": step_a_qualification_code} if step_a_qualification_code else {}),
                    **({"equipment_requirements": step_a_equipment_requirements} if step_a_equipment_requirements else {}),
                    **({"qc_requirements": step_a_qc_requirements} if step_a_qc_requirements else {}),
                },
                {"stable_step_code": "STEP-B", "section_code": "SEC-1", "step_type": "instruction", "sequence_hint": 2},
            ],
            "dependencies": [{"predecessor_step_code": "STEP-A", "successor_step_code": "STEP-B"}],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    recipe_version_id = resp.json()["aggregate_id"]

    await client.post(
        f"/recipes/v2/drafts/{recipe_version_id}/submit",
        json={"idempotency_key": idem(), "recipe_version_id": recipe_version_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/recipes/v2/drafts/{recipe_version_id}/release",
        json={"idempotency_key": idem(), "recipe_version_id": recipe_version_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    return product_version_id, recipe_version_id


async def _released_pair(
    db, client, seeded, tag, step_a_role=None, step_a_parameters=None, step_a_evidence=None,
    step_a_qualification_code=None, step_a_equipment_requirements=None, step_a_qc_requirements=None,
):
    async with db.begin():
        await _make_admin(db, seeded, f"admin.batch{tag}")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, f"admin.batch{tag}")
    product_version_id, recipe_version_id = await _make_released_product_and_recipe(
        client, admin_token, seeded["site_id"], tag, step_a_role=step_a_role, step_a_parameters=step_a_parameters,
        step_a_evidence=step_a_evidence, step_a_qualification_code=step_a_qualification_code,
        step_a_equipment_requirements=step_a_equipment_requirements, step_a_qc_requirements=step_a_qc_requirements,
    )
    return admin_token, product_version_id, recipe_version_id


async def _make_user_with_role(db, seeded, username, role_name):
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name=username,
        password_hash=hash_password(DEMO_PASSWORD),
        status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"][role_name].id))
    return user


async def _issue_start_and_get_ready_step(client, token, batch_id):
    await client.post(
        f"/batches/v1/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(token),
    )
    await client.post(
        f"/batches/v1/{batch_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2},
        headers=auth_headers(token),
    )
    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(token))).json()
    return next(s for s in view["steps"] if s["state"] == "ready")


def _create_body(site_id, product_version_id, recipe_version_id, batch_number, **overrides):
    body = {
        "idempotency_key": idem(),
        "site_id": str(site_id),
        "batch_number": batch_number,
        "product_version_id": product_version_id,
        "recipe_version_id": recipe_version_id,
        "target_qty": "100.0",
        "target_uom": "kg",
    }
    body.update(overrides)
    return body


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/batches/v1", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_batch_requires_permission(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "1")
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-PERM"),
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_create_batch_rejects_draft_recipe(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.batch2")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, "admin.batch2")
    resp = await client.post(
        "/products/v1/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": "BATPRD-2", "product_code": "BATPRD-2",
            "name": "P", "version_no": 1, "site_id": str(seeded["site_id"]), "manufacturing_profile_code": "pharma",
        },
        headers=auth_headers(admin_token),
    )
    product_version_id = resp.json()["aggregate_id"]
    await client.post(
        f"/products/v1/drafts/{product_version_id}/submit",
        json={"idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    await client.post(
        f"/products/v1/drafts/{product_version_id}/release",
        json={"idempotency_key": idem(), "product_version_id": product_version_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        "/recipes/v2/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": "BATPRD-2", "recipe_code": "BATRCP-2", "version_no": 1,
            "product_version_id": product_version_id, "site_id": str(seeded["site_id"]), "manufacturing_profile_code": "pharma",
            "sections": [], "steps": [], "dependencies": [],
        },
        headers=auth_headers(admin_token),
    )
    recipe_version_id = resp.json()["aggregate_id"]  # stays in "draft" -- never submitted/released

    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-DRAFT"),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_duplicate_batch_number_at_site_rejected(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "3")
    body = _create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-DUP")
    resp = await client.post("/batches/v1", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text

    body2 = _create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-DUP")
    resp = await client.post("/batches/v1", json=body2, headers=auth_headers(admin_token))
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_issue_creates_snapshot_and_instantiates_steps(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "4")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-ISSUE"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]

    # Client requirements #2/#3 (2026-09-21): "kg" is now a baseline released rules.gxp_uom row (see
    # conftest.py's `seeded` fixture) and create_batch hardens uom resolution via
    # `_resolve_uom_id_strict` -- the dual-write resolves.
    batch_row = await db.get(Batch, uuid.UUID(batch_id))
    assert batch_row.target_uom == "kg"
    assert batch_row.target_uom_id is not None

    resp = await client.post(
        f"/batches/v1/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    detail = (await client.get(f"/batches/v1/{batch_id}", headers=auth_headers(admin_token))).json()
    assert detail["state"] == "issued"
    assert detail["execution_snapshot_id"] is not None

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    assert len(view["steps"]) == 2
    by_code = {s["recipe_step_code"]: s for s in view["steps"]}
    assert by_code["STEP-A"]["state"] == "ready"  # no predecessor
    assert by_code["STEP-B"]["state"] == "pending"  # predecessor STEP-A not completed (completion out of scope)
    assert len(view["blockers"]) == 1
    assert view["blockers"][0]["recipe_step_code"] == "STEP-B"


async def test_start_step_requires_batch_in_execution(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "5")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-EARLY"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    await client.post(
        f"/batches/v1/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    ready_step = next(s for s in view["steps"] if s["state"] == "ready")

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_full_lifecycle_start_hold_resume_and_claim_step(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "6")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-FULL"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    await client.post(
        f"/batches/v1/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )

    resp = await client.post(
        f"/batches/v1/{batch_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert (await client.get(f"/batches/v1/{batch_id}", headers=auth_headers(admin_token))).json()["state"] == "in_execution"

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    ready_step = next(s for s in view["steps"] if s["state"] == "ready")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    started = next(s for s in view["steps"] if s["step_id"] == ready_step["step_id"])
    assert started["state"] == "in_progress"
    assert started["assigned_subject_id"] is not None

    resp = await client.post(
        f"/batches/v1/{batch_id}/hold",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 3, "reason": "line clearance issue"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert (await client.get(f"/batches/v1/{batch_id}", headers=auth_headers(admin_token))).json()["state"] == "on_hold"

    resp = await client.post(
        f"/batches/v1/{batch_id}/resume",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 4},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert (await client.get(f"/batches/v1/{batch_id}", headers=auth_headers(admin_token))).json()["state"] == "in_execution"


async def test_abort_from_planned_retains_batch(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "7")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-ABORT"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/batches/v1/{batch_id}/abort",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1, "reason": "wrong product selected"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/batches/v1/{batch_id}", headers=auth_headers(admin_token))).json()
    assert detail["state"] == "aborted"

    # No further transition is legal from a terminal state.
    resp = await client.post(
        f"/batches/v1/{batch_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_stale_version_rejected(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "8")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-STALE"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/batches/v1/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 99},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "9")
    key = idem()
    body = _create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-IDEM", idempotency_key=key)
    resp1 = await client.post("/batches/v1", json=body, headers=auth_headers(admin_token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/batches/v1", json=body, headers=auth_headers(admin_token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]
    assert resp1.json()["command_id"] == resp2.json()["command_id"]


async def test_dashboard_lists_batches_and_hold_count(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "11")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-DASH"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    await client.post(
        f"/batches/v1/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    await client.post(
        f"/batches/v1/{batch_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    await client.post(
        f"/batches/v1/{batch_id}/hold",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 3},
        headers=auth_headers(admin_token),
    )

    resp = await client.get(f"/batches/v1?site_id={seeded['site_id']}", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert any(b["batch_id"] == batch_id for b in body["batches"])
    assert body["on_hold_count"] == 1

    resp = await client.get(f"/batches/v1?site_id={seeded['site_id']}&state=on_hold", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    assert {b["batch_id"] for b in resp.json()["batches"]} == {batch_id}


async def test_cross_site_batch_number_reuse_allowed(client, seeded, db):
    """BAT-FR-002: uniqueness is site-scoped, not global -- two different sites may reuse a batch_number."""
    from app.modules.iam.models import Site

    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "10")

    async with db.begin():
        site2 = Site(organization_id=seeded["org_id"], code="T2", name="Test Site 2")
        db.add(site2)
        await db.flush()
        admin_user = (await db.execute(select(User).where(User.username == "admin.batch10"))).scalar_one()
        db.add(UserSiteRole(user_id=admin_user.id, site_id=site2.id, role_id=seeded["roles"]["Admin"].id))
    product_version_id_2, recipe_version_id_2 = await _make_released_product_and_recipe(client, admin_token, site2.id, "10b")

    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-CROSS"),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/batches/v1",
        json=_create_body(site2.id, product_version_id_2, recipe_version_id_2, "BAT-CROSS"),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# SG-178 — recipe step required_role_code enforced at step start (regulated /batch-execution path only)
# ---------------------------------------------------------------------------


async def test_start_step_carries_required_role_code_into_snapshot(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "role1", step_a_role="Operator")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-ROLE-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    assert ready_step["recipe_step_code"] == "STEP-A"
    # frozen onto the batch step at issue time, visible on the execution view
    assert ready_step["required_role_code"] == "Operator"


async def test_start_step_hard_blocks_a_role_the_actor_does_not_hold(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "role2", step_a_role="Operator")
    async with db.begin():
        await _make_user_with_role(db, seeded, "sup.role2", "Supervisor")
    sup_token = await login(client, "sup.role2")

    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-ROLE-2"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)

    # Supervisor holds batch_execution.execute but not the recipe-declared "Operator" role, and gives
    # no override_reason -> hard fail closed.
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"],
        },
        headers=auth_headers(sup_token),
    )
    assert resp.status_code == 403
    body = resp.json()
    assert body["code"] == "STEP_ROLE_MISMATCH"
    assert body["details"]["required_role_code"] == "Operator"


async def test_start_step_allows_the_actor_who_holds_the_declared_role(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "role3", step_a_role="Operator")
    op_token = await login(client, "operator1")

    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-ROLE-3"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"],
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text


async def test_start_step_documented_override_by_a_role_override_holder(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "role4", step_a_role="Operator")
    async with db.begin():
        await _make_user_with_role(db, seeded, "sup.role4", "Supervisor")
    sup_token = await login(client, "sup.role4")

    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-ROLE-4"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)

    # Supervisor holds batch_step.role_override -> a documented reason lets the mismatched start proceed.
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"],
            "override_reason": "Cross-trained filling lead covering an absent operator, per shift log 2601",
        },
        headers=auth_headers(sup_token),
    )
    assert resp.status_code == 200, resp.text
    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    started = next(s for s in view["steps"] if s["step_id"] == ready_step["step_id"])
    assert started["state"] == "in_progress"


async def test_start_step_override_denied_without_the_role_override_permission(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "role5", step_a_role="Operator")
    # A bespoke role that can execute batch steps but is not "Operator" and lacks batch_step.role_override.
    async with db.begin():
        line_lead = Role(name="Line Lead role5")
        db.add(line_lead)
        await db.flush()
        for code in ("batch_execution.execute", "batch_execution.view"):
            perm = (await db.execute(select(Permission).where(Permission.code == code))).scalar_one()
            db.add(RolePermission(role_id=line_lead.id, permission_id=perm.id))
        user = User(
            username="lead.role5", email="lead.role5@example.com", full_name="lead.role5",
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(user)
        await db.flush()
        db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=line_lead.id))
    lead_token = await login(client, "lead.role5")

    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-ROLE-5"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"],
            "override_reason": "trying to override without the permission",
        },
        headers=auth_headers(lead_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "STEP_ROLE_MISMATCH"


async def test_start_step_unrestricted_step_is_unaffected(client, seeded, db):
    # STEP-A carries no required_role_code -> any batch_execution.execute holder starts it, as before.
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "role6")
    async with db.begin():
        await _make_user_with_role(db, seeded, "sup.role6", "Supervisor")
    sup_token = await login(client, "sup.role6")

    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-ROLE-6"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"],
        },
        headers=auth_headers(sup_token),
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# SG-047 partial resolution (2026-09-09) — gxp_step_result, results/complete, BAT-FR-006 runtime
# ---------------------------------------------------------------------------


async def _sign_step(client, token, batch_id, step_id, action):
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/signature-challenges",
        json={"action": action},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["challenge_id"]


async def test_complete_step_blocked_without_required_parameter_result(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "res1",
        step_a_parameters=[{"parameter_code": "WEIGHT", "data_type": "numeric", "uom": "kg", "source_type": "manual", "required": True}],
    )
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-RES-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    challenge_id = await _sign_step(client, admin_token, batch_id, ready_step["step_id"], "complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"] + 1,
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == "PARAMETER_REQUIRED"
    assert body["details"]["missing_parameter_codes"] == ["WEIGHT"]


async def test_complete_step_requires_signature(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "res2")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-RES-2"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"] + 1,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_record_results_and_complete_step_advances_dependency_graph(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "res3",
        step_a_parameters=[{"parameter_code": "WEIGHT", "data_type": "numeric", "uom": "kg", "source_type": "manual", "required": True}],
    )
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-RES-3"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    assert ready_step["recipe_step_code"] == "STEP-A"
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = ready_step["version"] + 1  # bumped by start

    challenge_id = await _sign_step(client, admin_token, batch_id, ready_step["step_id"], "results")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/results",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": step_version,
            "results": [{"parameter_code": "WEIGHT", "value_numeric": "12.5"}],
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = resp.json()["resulting_version"]

    challenge_id = await _sign_step(client, admin_token, batch_id, ready_step["step_id"], "complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": step_version,
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    by_code = {s["recipe_step_code"]: s for s in view["steps"]}
    assert by_code["STEP-A"]["state"] == "complete"
    assert by_code["STEP-A"]["completed_at"] is not None
    assert by_code["STEP-B"]["state"] == "ready"  # BAT-FR-006 runtime: predecessor now complete
    assert view["blockers"] == []

    step_a_id = by_code["STEP-A"]["step_id"]
    recorded = view["results_by_step_id"][step_a_id]
    assert len(recorded) == 1
    assert recorded[0]["parameter_code"] == "WEIGHT"
    assert recorded[0]["value_numeric"] == "12.50000000"
    assert recorded[0]["signature_id"] is not None

    # "Step detail" view (2026-09-09, client-requested): instruction/section/dependencies/evidence,
    # read from the live recipe graph and keyed by step_id.
    step_b_id = by_code["STEP-B"]["step_id"]
    detail_a = view["step_detail_by_step_id"][step_a_id]
    detail_b = view["step_detail_by_step_id"][step_b_id]
    assert detail_a["step_type"] == "weigh"
    assert detail_a["section_code"] == "SEC-1"
    assert detail_a["section_name"] == "Dispensing"
    assert detail_a["successor_codes"] == ["STEP-B"]
    assert detail_b["step_type"] == "instruction"
    assert detail_b["predecessor_codes"] == ["STEP-A"]
    assert detail_b["evidence_requirements"] == []


# ---------------------------------------------------------------------------
# SG-047/SG-048 further partial resolution (2026-09-09) — step-scoped hold/resume, production-complete
# ---------------------------------------------------------------------------


async def _sign_batch(client, token, batch_id, action):
    resp = await client.post(
        f"/batches/v1/{batch_id}/signature-challenges",
        json={"action": action},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["challenge_id"]


async def _complete_step_no_params(client, token, batch_id, step_id, expected_version):
    """Helper for the production-complete tests below -- completes a step with no required parameters
    (the default test recipe's STEP-A/STEP-B carry none unless step_a_parameters is passed)."""
    challenge_id = await _sign_step(client, token, batch_id, step_id, "complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": expected_version,
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["resulting_version"]


async def test_hold_step_requires_reason(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "hold1")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-HOLD-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    challenge_id = await _sign_step(client, admin_token, batch_id, ready_step["step_id"], "hold")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/hold",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"] + 1, "reason": "",
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_hold_and_resume_step_blocks_and_restores_progress(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "hold2",
        step_a_parameters=[{"parameter_code": "WEIGHT", "data_type": "numeric", "uom": "kg", "source_type": "manual", "required": True}],
    )
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-HOLD-2"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = resp.json()["resulting_version"]

    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "hold")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/hold",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": step_version, "reason": "waiting on a fresh balance calibration",
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = resp.json()["resulting_version"]
    assert resp.json()["signature_id"] is not None

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    held = next(s for s in view["steps"] if s["step_id"] == step_id)
    assert held["state"] == "on_hold"
    assert view["active_hold_by_step_id"][step_id]["reason"] == "waiting on a fresh balance calibration"

    # Blocked while on hold: results and complete both require "in_progress".
    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "results")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/results",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": step_version, "results": [{"parameter_code": "WEIGHT", "value_numeric": "10"}],
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"

    # Resume — a different meaning (Approved), same signature machinery.
    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "resume")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/resume",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": step_version, "reason": "balance recalibrated, verified",
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = resp.json()["resulting_version"]

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    resumed = next(s for s in view["steps"] if s["step_id"] == step_id)
    assert resumed["state"] == "in_progress"
    assert step_id not in view["active_hold_by_step_id"]

    # Now genuinely completable.
    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "results")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/results",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": step_version, "results": [{"parameter_code": "WEIGHT", "value_numeric": "10"}],
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text


async def test_production_complete_blocked_until_every_step_is_complete(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "prod1")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-PROD-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    assert ready_step["recipe_step_code"] == "STEP-A"
    await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    await _complete_step_no_params(client, admin_token, batch_id, ready_step["step_id"], ready_step["version"] + 1)
    # STEP-B is now "ready" but never started/completed -- production-complete must refuse.

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    batch_version = view["batch"]["version"]
    challenge_id = await _sign_batch(client, admin_token, batch_id, "production_complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/production-complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "expected_version": batch_version,
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == "PRODUCTION_NOT_COMPLETE"
    assert body["details"]["incomplete_step_codes"] == ["STEP-B"]


async def test_production_complete_happy_path_and_can_still_be_held(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "prod2")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-PROD-2"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_a_id, step_a_version = ready_step["step_id"], ready_step["version"]
    await client.post(
        f"/batches/v1/{batch_id}/steps/{step_a_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step_a_id, "expected_version": step_a_version},
        headers=auth_headers(admin_token),
    )
    await _complete_step_no_params(client, admin_token, batch_id, step_a_id, step_a_version + 1)

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    step_b = next(s for s in view["steps"] if s["recipe_step_code"] == "STEP-B")
    assert step_b["state"] == "ready"
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_b['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step_b["step_id"], "expected_version": step_b["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    await _complete_step_no_params(client, admin_token, batch_id, step_b["step_id"], step_b["version"] + 1)

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    batch_version = view["batch"]["version"]
    challenge_id = await _sign_batch(client, admin_token, batch_id, "production_complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/production-complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "expected_version": batch_version,
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None

    detail = (await client.get(f"/batches/v1/{batch_id}", headers=auth_headers(admin_token))).json()
    assert detail["state"] == "production_complete"

    # BAT-FR-020: a batch found to need attention after production is nominally complete can still be held.
    resp = await client.post(
        f"/batches/v1/{batch_id}/hold",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": detail["version"], "reason": "late deviation found"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert (await client.get(f"/batches/v1/{batch_id}", headers=auth_headers(admin_token))).json()["state"] == "on_hold"


async def test_hold_step_requires_signature(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "hold3")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-HOLD-3"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/hold",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"] + 1, "reason": "balance drifting out of tolerance",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


async def test_production_complete_rejected_from_a_state_it_is_not_allowed_from(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "prod3")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-PROD-3"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    # Still "planned" -- never issued/started. production-complete is not a legal transition from here.
    challenge_id = await _sign_batch(client, admin_token, batch_id, "production_complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/production-complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1,
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


# ---------------------------------------------------------------------------
# SG-047 (gxp_step_evidence_link) -- unsigned by design (no Document 106 policy row for an evidence-link
# action; a capture, not a release/disposition decision).
# ---------------------------------------------------------------------------

async def test_link_step_evidence_succeeds_on_in_progress_step(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "evlink1")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-EVLINK-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = ready_step["version"] + 1

    evidence_id = str(uuid.uuid4())
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/evidence-links",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": step_version,
            "links": [
                {
                    "evidence_id": evidence_id, "evidence_version": 1,
                    "evidence_sha256": "a" * 64, "media_type": "image/jpeg", "requirement_code": "PHOTO",
                }
            ],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is None


async def test_link_step_evidence_rejects_empty_links(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "evlink2")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-EVLINK-2"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = ready_step["version"] + 1

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/evidence-links",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": step_version, "links": [],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_link_step_evidence_rejects_step_not_in_progress(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "evlink3")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-EVLINK-3"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/evidence-links",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"],
            "links": [{"evidence_id": str(uuid.uuid4()), "evidence_sha256": "b" * 64}],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


# ---------------------------------------------------------------------------
# BAT-FR-015 evidence half -- SG-048 #015 partial resolution (2026-09-14). The parameter half of
# complete_step's completion gate was already built (test_complete_step_blocked_without_required_
# parameter_result above); this proves the sibling evidence-count gate against RecipeEvidenceRequirement.
# ---------------------------------------------------------------------------


async def test_complete_step_blocked_without_required_evidence_then_succeeds_after_linking(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "ev1",
        step_a_evidence=[{"evidence_type": "PHOTO", "required_count": 1}],
    )
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-EV-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = ready_step["version"] + 1

    challenge_id = await _sign_step(client, admin_token, batch_id, ready_step["step_id"], "complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": step_version,
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert body["details"]["missing_evidence_types"] == ["PHOTO"]

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/evidence-links",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": step_version,
            "links": [{"evidence_id": str(uuid.uuid4()), "evidence_sha256": "c" * 64, "requirement_code": "PHOTO"}],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version += 1

    challenge_id = await _sign_step(client, admin_token, batch_id, ready_step["step_id"], "complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": step_version,
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# Client requirement #12 -- a step's declared required in-process QC test(s) must reach a passing result
# before the step can be marked complete. Same completion-gate shape as the parameter/evidence checks
# above.
# ---------------------------------------------------------------------------


async def test_complete_step_blocked_without_required_qc_test_then_succeeds_after_passing_result(client, seeded, db):
    import uuid as uuid_mod

    from app.modules.qc.models import (
        QcResult,
        QcSample,
        QcTestDefinition,
        QcTestOrder,
        QcTestRun,
        QcTestSpecification,
    )

    async with db.begin():
        spec = QcTestSpecification(
            spec_code="SPEC-BATQC1", version_no=1, scope_type="in_process",
            scope_version_id=uuid_mod.uuid4(), status="released",
        )
        db.add(spec)
        await db.flush()
        spec_id = spec.id
        definition = QcTestDefinition(
            specification_id=spec.id, test_code="IPC-WEIGHT", test_name="In-process weight check",
            result_data_type="numeric", required=True, release_blocking=True,
        )
        db.add(definition)
        await db.flush()
        definition_id = definition.id

    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "qc1",
        step_a_qc_requirements=[{"qc_test_specification_id": str(spec_id), "required": True}],
    )
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-QC-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = ready_step["version"] + 1

    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": step_version, "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    body = resp.json()
    assert body["code"] == "VALIDATION_FAILED"
    assert body["details"]["missing_qc_test_specification_ids"] == [str(spec_id)]

    async with db.begin():
        sample = QcSample(
            sample_number=f"SMP-BATQC1-{uuid_mod.uuid4().hex[:6]}", sample_type="in_process",
            source_type="batch_step", source_id=uuid_mod.UUID(step_id), state="testing_complete",
        )
        db.add(sample)
        await db.flush()
        order = QcTestOrder(sample_id=sample.id, test_definition_id=definition_id, state="reviewed", blocking=True)
        db.add(order)
        await db.flush()
        run = QcTestRun(test_order_id=order.id)
        db.add(run)
        await db.flush()
        db.add(QcResult(test_order_id=order.id, test_run_id=run.id, result_type="numeric", outcome="pass"))

    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": step_version, "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text


async def test_complete_step_unaffected_when_no_qc_requirement_declared(client, seeded, db):
    """Regression check: a step with no RecipeStepQcRequirement rows completes exactly as before."""
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "qc2")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-QC-2"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = ready_step["version"] + 1

    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": step_version, "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text


# ---------------------------------------------------------------------------
# BAT-FR-023 -- SG-048 #023 partial resolution (2026-09-14). 2-step, 2-signature correction ceremony,
# Document 106 row 20 ("Authorized corrector + independent approver", corrector and approver MUST differ,
# mandatory reason).
# ---------------------------------------------------------------------------


async def _sign_step_result(client, token, batch_id, step_id, result_id, action):
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/results/{result_id}/signature-challenges",
        json={"action": action},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["challenge_id"]


async def test_step_result_correction_two_signature_flow(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "corr1",
        step_a_parameters=[{"parameter_code": "WEIGHT", "data_type": "numeric", "uom": "kg", "source_type": "manual", "required": True}],
    )
    async with db.begin():
        await _make_user_with_role(db, seeded, "sup.corr1", "Supervisor")
    sup_token = await login(client, "sup.corr1")

    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-CORR-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = ready_step["version"] + 1

    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "results")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/results",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": step_version,
            "results": [{"parameter_code": "WEIGHT", "value_numeric": "1.50000000", "uom": "kg"}],
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version += 1

    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": step_version,
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    result_id = view["results_by_step_id"][step_id][0]["result_id"]

    request_challenge_id = await _sign_step_result(client, admin_token, batch_id, step_id, result_id, "correct_request")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/correct",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "result_id": result_id,
            "reason_text": "Balance recalibration found the original reading high by 0.2kg",
            "corrected_value_numeric": "1.30000000",
            "challenge_id": request_challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    correction_id = resp.json()["aggregate_id"]

    # SoD: the same actor who requested the correction cannot approve it.
    same_actor_challenge_id = await _sign_step_result(client, admin_token, batch_id, step_id, result_id, "correct_approve")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/corrections/{correction_id}/approve",
        json={
            "idempotency_key": idem(), "correction_id": correction_id,
            "challenge_id": same_actor_challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert "independent" in resp.json()["message"].lower()

    approve_challenge_id = await _sign_step_result(client, sup_token, batch_id, step_id, result_id, "correct_approve")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/corrections/{correction_id}/approve",
        json={
            "idempotency_key": idem(), "correction_id": correction_id,
            "challenge_id": approve_challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(sup_token),
    )
    assert resp.status_code == 200, resp.text
    new_result_id = resp.json()["aggregate_id"]
    assert new_result_id != result_id

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    results = view["results_by_step_id"][step_id]
    assert len(results) == 2
    corrected = next(r for r in results if r["result_id"] == new_result_id)
    assert corrected["value_numeric"] == "1.30000000"


async def test_request_step_result_correction_rejected_before_step_is_complete(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "corr2",
        step_a_parameters=[{"parameter_code": "WEIGHT", "data_type": "numeric", "uom": "kg", "source_type": "manual", "required": True}],
    )
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-CORR-2"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = ready_step["version"] + 1

    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "results")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/results",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": step_version,
            "results": [{"parameter_code": "WEIGHT", "value_numeric": "1.50000000", "uom": "kg"}],
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    result_id = view["results_by_step_id"][step_id][0]["result_id"]

    request_challenge_id = await _sign_step_result(client, admin_token, batch_id, step_id, result_id, "correct_request")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/correct",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "result_id": result_id,
            "reason_text": "attempted correction before completion",
            "corrected_value_numeric": "1.30000000",
            "challenge_id": request_challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_request_step_result_correction_requires_signature(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "corr3",
        step_a_parameters=[{"parameter_code": "WEIGHT", "data_type": "numeric", "uom": "kg", "source_type": "manual", "required": True}],
    )
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-CORR-3"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = ready_step["version"] + 1

    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "results")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/results",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": step_version,
            "results": [{"parameter_code": "WEIGHT", "value_numeric": "1.50000000", "uom": "kg"}],
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version += 1

    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "complete")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/complete",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": step_version,
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    result_id = view["results_by_step_id"][step_id][0]["result_id"]

    # No challenge_id/reauth_password supplied -- login/MFA alone is never accepted as a signature.
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/correct",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "result_id": result_id,
            "reason_text": "attempted correction without a signature",
            "corrected_value_numeric": "1.30000000",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"


# ---------------------------------------------------------------------------
# BAT-FR-014 -- SG-048 #014 partial resolution (2026-09-14). RecipeStep.required_qualification_code,
# frozen onto BatchStep at issue, enforced against iam.qualifications at both start and complete.
# ---------------------------------------------------------------------------


async def test_start_step_blocked_without_required_qualification_then_succeeds_once_granted(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "qual1", step_a_qualification_code="WEIGH_CERT",
    )
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-QUAL-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 403, resp.text
    body = resp.json()
    assert body["code"] == "QUALIFICATION_MISSING"
    assert body["details"]["qualification_code"] == "WEIGH_CERT"

    async with db.begin():
        admin = (await db.execute(select(User).where(User.username == "admin.batchqual1"))).scalar_one()
        db.add(Qualification(user_id=admin.id, qualification_code="WEIGH_CERT", expires_at=None))

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text


async def test_start_step_blocked_when_qualification_expired(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "qual2", step_a_qualification_code="WEIGH_CERT",
    )
    async with db.begin():
        admin = (await db.execute(select(User).where(User.username == "admin.batchqual2"))).scalar_one()
        db.add(Qualification(
            user_id=admin.id, qualification_code="WEIGH_CERT",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        ))

    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-QUAL-2"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "QUALIFICATION_EXPIRED"


# ---------------------------------------------------------------------------
# BAT-FR-009/011 -- SG-048 #009/#011 partial resolution (2026-09-14). quality_status computed from the
# recipe parameter's own min_value/max_value; source_type additionally accepts 'device_transcribed'.
# ---------------------------------------------------------------------------


async def test_record_step_results_computes_quality_status_and_accepts_device_transcribed_source(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "qs1",
        step_a_parameters=[
            {
                "parameter_code": "WEIGHT", "data_type": "numeric", "uom": "kg", "source_type": "manual",
                "required": True, "min_value": "1.0", "max_value": "2.0",
            },
        ],
    )
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-QS-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = ready_step["version"] + 1

    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "results")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/results",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": step_version,
            "results": [{"parameter_code": "WEIGHT", "value_numeric": "2.50000000", "uom": "kg", "source_type": "device_transcribed"}],
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    result = view["results_by_step_id"][step_id][0]
    assert result["quality_status"] == "out_of_range"
    assert result["source_type"] == "device_transcribed"


async def test_record_step_results_rejects_unknown_source_type(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "qs2",
        step_a_parameters=[{"parameter_code": "WEIGHT", "data_type": "numeric", "uom": "kg", "source_type": "manual", "required": True}],
    )
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-QS-2"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = ready_step["version"] + 1

    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "results")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/results",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": step_version,
            "results": [{"parameter_code": "WEIGHT", "value_numeric": "1.50000000", "uom": "kg", "source_type": "edge_automated"}],
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


# ---------------------------------------------------------------------------
# BAT-FR-034 -- SG-048 #034 partial resolution (2026-09-14). Structured, append-only step comments.
# ---------------------------------------------------------------------------


async def test_add_step_comment_succeeds(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "cmt1")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-CMT-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/comments",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": ready_step["version"], "comment_text": "Balance recalibrated mid-step per SOP-42.",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is None

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    comments = view["comments_by_step_id"][step_id]
    assert len(comments) == 1
    assert comments[0]["comment_text"] == "Balance recalibrated mid-step per SOP-42."


async def test_add_step_comment_rejects_empty_text(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "cmt2")
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-CMT-2"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/comments",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": ready_step["version"], "comment_text": "   ",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


# ---------------------------------------------------------------------------
# BAT-FR-025 -- SG-048 #025 partial resolution (2026-09-14, project-owner-directed: unsigned/RBAC-gated
# interim scope, pending a real Document 106 addendum).
# ---------------------------------------------------------------------------


async def test_handover_step_succeeds_without_changing_prior_attribution(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "ho1")
    async with db.begin():
        await _make_user_with_role(db, seeded, "sup.ho1", "Supervisor")
    async with db.begin():
        sup = (await db.execute(select(User).where(User.username == "sup.ho1"))).scalar_one()
        sup_user_id = str(sup.id)

    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-HO-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = ready_step["version"] + 1

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/handover",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": step_version, "to_user_id": sup_user_id, "reason": "End of shift",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is None

    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    step = next(s for s in view["steps"] if s["step_id"] == step_id)
    assert step["assigned_subject_id"] == sup_user_id
    handovers = view["handovers_by_step_id"][step_id]
    assert len(handovers) == 1
    assert handovers[0]["to_subject_id"] == sup_user_id
    assert handovers[0]["reason"] == "End of shift"


async def test_handover_step_rejected_when_not_in_progress(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "ho2")
    async with db.begin():
        await _make_user_with_role(db, seeded, "sup.ho2", "Supervisor")
        sup = (await db.execute(select(User).where(User.username == "sup.ho2"))).scalar_one()
        sup_user_id = str(sup.id)

    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-HO-2"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]

    # Step is still "ready", never started -- handover only applies to an in-progress step.
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/handover",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id,
            "expected_version": ready_step["version"], "to_user_id": sup_user_id,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_start_step_blocked_without_required_equipment_then_succeeds_with_eligible_asset(client, seeded, db):
    """Known-limitations fix (docs/testing/demo-gujarati/08 §8.8, and this module's own docstring naming
    "Equipment master eligibility wiring" as not-yet-built): RecipeEquipmentRequirement is frozen onto
    BatchStepEquipmentRequirement at issue and enforced at step-start via
    commands.py::_enforce_step_equipment, reusing equipment.commands.get_eligibility() rather than
    reinventing calibration/qualification currency checks."""
    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "equip1",
        step_a_equipment_requirements=[{"equipment_class": "balance", "require_current_qualification": True}],
    )
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-EQUIP-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)

    # The frozen requirement is visible on the execution view (surfaced for the step-start UI).
    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    step = next(s for s in view["steps"] if s["step_id"] == ready_step["step_id"])
    assert step["equipment_requirements"] == [
        {
            "equipment_class": "balance", "equipment_class_id": None, "exact_equipment_optional": True,
            "require_current_calibration": False, "require_current_qualification": True, "require_current_cleaning": False,
        }
    ]

    # No equipment_asset_ids supplied at all -> the requirement can't be satisfied.
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "EQUIPMENT_REQUIREMENT_NOT_MET"

    async with db.begin():
        asset = EquipmentAsset(
            site_id=seeded["site_id"], equipment_code="BAL-EQUIP-1", state="QUALIFIED_AVAILABLE",
            qualification_status=None,
        )
        db.add(asset)
        await db.flush()
        asset_id = str(asset.id)

    # A supplied asset that fails the declared eligibility check (not qualified) -> still blocked.
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"], "equipment_asset_ids": [asset_id],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "EQUIPMENT_NOT_QUALIFIED"

    async with db.begin():
        row = (await db.execute(select(EquipmentAsset).where(EquipmentAsset.id == uuid.UUID(asset_id)))).scalar_one()
        row.qualification_status = QUALIFIED_MARKER

    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"], "equipment_asset_ids": [asset_id],
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    # 2026-09-19, project-owner-directed: the asset that satisfied the requirement is now persisted
    # (EquipmentUseLog, log_type="production") -- previously checked live here and discarded, so
    # qa_review/release had no record of which equipment a batch actually used (see their own
    # _equipment_signals docstrings).
    from app.modules.equipment.models import EquipmentUseLog

    async with db.begin():
        use_log = (
            await db.execute(select(EquipmentUseLog).where(EquipmentUseLog.equipment_asset_id == uuid.UUID(asset_id)))
        ).scalar_one()
        assert use_log.batch_id == uuid.UUID(batch_id)
        assert use_log.step_id == uuid.UUID(ready_step["step_id"])
        assert use_log.log_type == "production"


async def test_out_of_range_result_auto_opens_a_deviation(client, seeded, db):
    """Known-limitations fix (docs/testing/demo-gujarati/08 §8.8 item 2), project-owner-directed
    2026-09-18: an in-process result outside min/max now automatically opens a DeviationRecord (OPEN,
    unassigned owner, severity=minor, deviation_type=process) instead of staying purely informational.
    An in-range result on the same step must NOT open one."""
    admin_token, product_version_id, recipe_version_id = await _released_pair(
        db, client, seeded, "oor1",
        step_a_parameters=[
            {
                "parameter_code": "WEIGHT", "data_type": "numeric", "uom": "kg", "source_type": "manual",
                "required": True, "min_value": "1.0", "max_value": "2.0",
            },
        ],
    )
    resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-OOR-1"),
        headers=auth_headers(admin_token),
    )
    batch_id = resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    step_id = ready_step["step_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    step_version = ready_step["version"] + 1

    challenge_id = await _sign_step(client, admin_token, batch_id, step_id, "results")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/results",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": step_version,
            "results": [{"parameter_code": "WEIGHT", "value_numeric": "2.50000000", "uom": "kg", "source_type": "manual"}],
            "challenge_id": challenge_id, "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    deviations = (
        await client.get(f"/qms/v1/deviations?site_id={seeded['site_id']}", headers=auth_headers(admin_token))
    ).json()["items"]
    auto_opened = [d for d in deviations if d["deviation_number"].startswith("DEV-AUTO-BAT-OOR-1-")]
    assert len(auto_opened) == 1, deviations
    deviation = auto_opened[0]
    assert deviation["state"] == "OPEN"
    assert deviation["severity"] == "minor"
    assert deviation["deviation_type"] == "process"
    assert deviation["source_type"] == "batch"
    assert deviation["source_id"] == batch_id
    assert deviation["owner_subject_id"] is None

    # A second, in-range result recorded against the (now version-bumped) step must not open a second
    # deviation.
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{step_id}/results",
        json={
            "idempotency_key": idem(), "batch_id": batch_id, "step_id": step_id, "expected_version": step_version + 1,
            "results": [{"parameter_code": "WEIGHT", "value_numeric": "1.50000000", "uom": "kg", "source_type": "manual"}],
            "challenge_id": await _sign_step(client, admin_token, batch_id, step_id, "results"),
            "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    deviations_after = (
        await client.get(f"/qms/v1/deviations?site_id={seeded['site_id']}", headers=auth_headers(admin_token))
    ).json()["items"]
    still_auto_opened = [d for d in deviations_after if d["deviation_number"].startswith("DEV-AUTO-BAT-OOR-1-")]
    assert len(still_auto_opened) == 1, deviations_after
