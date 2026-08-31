"""Document 11 (SPEC-EBMR-002) -- the buildable slice: create/issue/start/hold/resume/abort a batch and
claim/start a batch step, against real released product_master/recipe_master versions. New, additive
module -- does not touch app/modules/batch (the legacy Batch-facing stub); the full pre-existing suite
passes unmodified, proving that. Everything gated on gxp_step_result/gxp_step_evidence_link/
gxp_batch_hold or on absent infrastructure (Temporal, Material Service, Equipment, qualification schema,
exception/rework/branch entities) is out of scope this pass -- SG-047/SG-048.
"""

import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.batch_execution.models import Batch
from app.modules.iam.models import User, UserSiteRole
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


async def _make_released_product_and_recipe(client, admin_token, site_id, tag):
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
                {"stable_step_code": "STEP-A", "section_code": "SEC-1", "step_type": "weigh", "sequence_hint": 1},
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


async def _released_pair(db, client, seeded, tag):
    async with db.begin():
        await _make_admin(db, seeded, f"admin.batch{tag}")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, f"admin.batch{tag}")
    product_version_id, recipe_version_id = await _make_released_product_and_recipe(client, admin_token, seeded["site_id"], tag)
    return admin_token, product_version_id, recipe_version_id


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

    # SG-146 (remainder, module 4 of 8): "kg" has no released rules.gxp_uom row in this environment --
    # the dual-write is a no-op (expand-phase contract, nothing breaks).
    batch_row = await db.get(Batch, uuid.UUID(batch_id))
    assert batch_row.target_uom == "kg"
    assert batch_row.target_uom_id is None

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
