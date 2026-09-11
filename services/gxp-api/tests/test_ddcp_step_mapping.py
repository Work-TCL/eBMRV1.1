"""SG-180 (option B, project-owner-directed 2026-09-11) -- the DDCP action <-> generic recipe step
declarative mapping, and the read-only sync-status view that joins it against BatchStep.state. No
write-side auto-completion is built (see DdcpStepMapping's model docstring for why); this covers the
mapping CRUD and the read that actually fixes SG-180's root cause.
"""

from tests.conftest import auth_headers, idem, login
from tests.test_batch_execution import (
    _create_body,
    _issue_start_and_get_ready_step,
    _released_pair,
)


async def test_create_step_mapping_succeeds_and_is_listable(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "ddcpmap1")

    resp = await client.post(
        "/ddcp/v1/prefilled-syringe/step-mappings",
        json={
            "idempotency_key": idem(), "recipe_version_id": recipe_version_id,
            "ddcp_action": "constituent_handoff.accept", "stable_step_code": "STEP-A",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    listing = await client.get(
        f"/ddcp/v1/prefilled-syringe/step-mappings?recipe_version_id={recipe_version_id}",
        headers=auth_headers(admin_token),
    )
    assert listing.status_code == 200
    rows = listing.json()
    assert len(rows) == 1
    assert rows[0]["ddcp_action"] == "constituent_handoff.accept"
    assert rows[0]["stable_step_code"] == "STEP-A"


async def test_create_step_mapping_rejects_unknown_step_code(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "ddcpmap2")

    resp = await client.post(
        "/ddcp/v1/prefilled-syringe/step-mappings",
        json={
            "idempotency_key": idem(), "recipe_version_id": recipe_version_id,
            "ddcp_action": "filling_stage.complete", "stable_step_code": "NOT-A-REAL-STEP",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


async def test_create_step_mapping_rejects_unknown_ddcp_action(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "ddcpmap3")

    resp = await client.post(
        "/ddcp/v1/prefilled-syringe/step-mappings",
        json={
            "idempotency_key": idem(), "recipe_version_id": recipe_version_id,
            "ddcp_action": "not.a.real.action", "stable_step_code": "STEP-A",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_create_step_mapping_requires_ddcp_profile_author_permission(client, seeded, db):
    from app.core.security import hash_password
    from app.modules.iam.models import User, UserSiteRole
    from tests.conftest import DEMO_PASSWORD

    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "ddcpmap4")

    async with db.begin():
        user = User(
            username="qa.reviewer.ddcpmap", email="qa.reviewer.ddcpmap@example.com", full_name="x",
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(user)
        await db.flush()
        db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Reviewer"].id))
    token = await login(client, "qa.reviewer.ddcpmap")

    resp = await client.post(
        "/ddcp/v1/prefilled-syringe/step-mappings",
        json={
            "idempotency_key": idem(), "recipe_version_id": recipe_version_id,
            "ddcp_action": "device_assembly.verify", "stable_step_code": "STEP-A",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_batch_step_sync_status_joins_mapping_against_batch_step_state(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "ddcpmap5")

    mapping = await client.post(
        "/ddcp/v1/prefilled-syringe/step-mappings",
        json={
            "idempotency_key": idem(), "recipe_version_id": recipe_version_id,
            "ddcp_action": "constituent_handoff.accept", "stable_step_code": "STEP-A",
        },
        headers=auth_headers(admin_token),
    )
    assert mapping.status_code == 200, mapping.text

    batch_resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-DDCPMAP-5"),
        headers=auth_headers(admin_token),
    )
    batch_id = batch_resp.json()["aggregate_id"]
    ready_step = await _issue_start_and_get_ready_step(client, admin_token, batch_id)
    assert ready_step["recipe_step_code"] == "STEP-A"

    status = await client.get(
        f"/ddcp/v1/prefilled-syringe/batches/{batch_id}/step-sync-status", headers=auth_headers(admin_token)
    )
    assert status.status_code == 200, status.text
    body = status.json()
    assert body["batch_id"] == batch_id
    assert len(body["mappings"]) == 1
    row = body["mappings"][0]
    assert row["ddcp_action"] == "constituent_handoff.accept"
    assert row["stable_step_code"] == "STEP-A"
    assert row["generic_step_state"] == "ready"

    # Start the step -- the sync view should reflect the state change.
    start = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "step_id": ready_step["step_id"], "expected_version": ready_step["version"]},
        headers=auth_headers(admin_token),
    )
    assert start.status_code == 200, start.text

    status2 = await client.get(
        f"/ddcp/v1/prefilled-syringe/batches/{batch_id}/step-sync-status", headers=auth_headers(admin_token)
    )
    assert status2.json()["mappings"][0]["generic_step_state"] == "in_progress"


async def test_batch_step_sync_status_returns_empty_mappings_when_none_declared(client, seeded, db):
    admin_token, product_version_id, recipe_version_id = await _released_pair(db, client, seeded, "ddcpmap6")
    batch_resp = await client.post(
        "/batches/v1",
        json=_create_body(seeded["site_id"], product_version_id, recipe_version_id, "BAT-DDCPMAP-6"),
        headers=auth_headers(admin_token),
    )
    batch_id = batch_resp.json()["aggregate_id"]

    status = await client.get(
        f"/ddcp/v1/prefilled-syringe/batches/{batch_id}/step-sync-status", headers=auth_headers(admin_token)
    )
    assert status.status_code == 200
    assert status.json()["mappings"] == []
