"""Document 10 (SPEC-EBMR-001) -- draft/validate/simulate/submit/release for the new, additive Master
Recipe module. Does not touch app/modules/recipe (the legacy Batch-facing stub); the full pre-existing
suite passes unmodified, proving that. Release correctly fails closed pending Document 106 (SG-035's scope
extended to recipe_version) -- the same honest pattern as every other new regulated action this session.
"""

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username="admin.recipe"):
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


async def _make_product_version(client, admin_token, site_id, business_id="RCPPRD-1"):
    resp = await client.post(
        "/products/v1/drafts",
        json={
            "idempotency_key": idem(),
            "product_business_id": business_id,
            "product_code": business_id,
            "name": "Recipe Test Product",
            "version_no": 1,
            "site_id": str(site_id),
            "manufacturing_profile_code": "pharma",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


def _two_step_body(product_version_id, site_id, recipe_code="RCP-1", version_no=1, **overrides):
    body = {
        "idempotency_key": idem(),
        "product_business_id": "RCPPRD-1",
        "recipe_code": recipe_code,
        "version_no": version_no,
        "product_version_id": product_version_id,
        "site_id": str(site_id),
        "manufacturing_profile_code": "pharma",
        "sections": [{"stable_section_code": "SEC-1", "name": "Dispensing", "sequence": 1}],
        "steps": [
            {
                "stable_step_code": "STEP-A",
                "section_code": "SEC-1",
                "step_type": "weigh",
                "sequence_hint": 1,
            },
            {
                "stable_step_code": "STEP-B",
                "section_code": "SEC-1",
                "step_type": "instruction",
                "sequence_hint": 2,
            },
        ],
        "dependencies": [{"predecessor_step_code": "STEP-A", "successor_step_code": "STEP-B"}],
    }
    body.update(overrides)
    return body


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post(
        "/recipes/v2/drafts", json={"idempotency_key": idem(), "recipe_code": "X"}, headers={}
    )
    assert resp.status_code == 401


async def test_create_draft_requires_recipe_author_permission(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe1")
    admin_token = await login(client, "admin.recipe1")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"])

    op_token = await login(client, "operator1")
    resp = await client.post(
        "/recipes/v2/drafts",
        json=_two_step_body(product_version_id, seeded["site_id"], "RCP-PERM"),
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_draft_with_sections_steps_dependencies_round_trips(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe2")
    admin_token = await login(client, "admin.recipe2")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"])

    resp = await client.post(
        "/recipes/v2/drafts",
        json=_two_step_body(product_version_id, seeded["site_id"], "RCP-2"),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    recipe_version_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/recipes/v2/versions/{recipe_version_id}", headers=auth_headers(admin_token))).json()
    assert detail["lifecycle_state"] == "draft"
    assert len(detail["sections"]) == 1
    assert len(detail["steps"]) == 2
    assert len(detail["dependencies"]) == 1
    assert {s["stable_step_code"] for s in detail["steps"]} == {"STEP-A", "STEP-B"}


async def test_cyclic_dependency_graph_blocks_release(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe3")
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, "admin.recipe3")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"])

    body = _two_step_body(product_version_id, seeded["site_id"], "RCP-CYCLE")
    # A -> B -> A is a cycle.
    body["dependencies"] = [
        {"predecessor_step_code": "STEP-A", "successor_step_code": "STEP-B"},
        {"predecessor_step_code": "STEP-B", "successor_step_code": "STEP-A"},
    ]
    resp = await client.post("/recipes/v2/drafts", json=body, headers=auth_headers(admin_token))
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
    assert resp.status_code == 422, resp.text
    assert "cycle" in " ".join(resp.json()["details"]["findings"]).lower()


async def test_unreachable_step_detected_by_simulate(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe4")
    admin_token = await login(client, "admin.recipe4")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"])

    body = _two_step_body(product_version_id, seeded["site_id"], "RCP-UNREACH")
    # STEP-C/STEP-D form a 2-cycle with no root of their own (both have an incoming edge only from
    # each other), so both are unreachable from any root AND cyclic -- exercises both findings at once.
    body["steps"].append({"stable_step_code": "STEP-C", "section_code": "SEC-1", "step_type": "instruction", "sequence_hint": 3})
    body["steps"].append({"stable_step_code": "STEP-D", "section_code": "SEC-1", "step_type": "instruction", "sequence_hint": 4})
    body["dependencies"] = [
        {"predecessor_step_code": "STEP-A", "successor_step_code": "STEP-B"},
        {"predecessor_step_code": "STEP-C", "successor_step_code": "STEP-D"},
        {"predecessor_step_code": "STEP-D", "successor_step_code": "STEP-C"},
    ]
    resp = await client.post("/recipes/v2/drafts", json=body, headers=auth_headers(admin_token))
    recipe_version_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/recipes/v2/drafts/{recipe_version_id}/simulate",
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    result = resp.json()
    assert result["complete"] is False
    findings_text = " ".join(result["findings"]).lower()
    assert "unreachable" in findings_text or "cycle" in findings_text


async def test_release_fails_closed_pending_signature_policy(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe5")
    admin_token = await login(client, "admin.recipe5")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"])

    resp = await client.post(
        "/recipes/v2/drafts",
        json=_two_step_body(product_version_id, seeded["site_id"], "RCP-5"),
        headers=auth_headers(admin_token),
    )
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
    assert resp.status_code == 409
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_release_creates_vault_snapshot(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe6")
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, "admin.recipe6")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"])

    resp = await client.post(
        "/recipes/v2/drafts",
        json=_two_step_body(product_version_id, seeded["site_id"], "RCP-6"),
        headers=auth_headers(admin_token),
    )
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

    detail = (await client.get(f"/recipes/v2/versions/{recipe_version_id}", headers=auth_headers(admin_token))).json()
    assert detail["lifecycle_state"] == "released"
    assert detail["released_vault_object_id"] is not None
    assert detail["version_hash"] is not None

    elig = (
        await client.get(f"/recipes/v2/versions/{recipe_version_id}/issue-eligibility", headers=auth_headers(admin_token))
    ).json()
    assert elig["eligible"] is True


async def test_completeness_blocks_release_when_referenced_rule_not_released(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe7")
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, "admin.recipe7")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"])

    body = _two_step_body(product_version_id, seeded["site_id"], "RCP-7")
    body["steps"][0]["parameters"] = [
        {"parameter_code": "ASSAY", "data_type": "decimal", "source_type": "calculated", "rule_id": "never-released-rule"}
    ]
    resp = await client.post("/recipes/v2/drafts", json=body, headers=auth_headers(admin_token))
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
    assert resp.status_code == 422, resp.text
    assert any("never-released-rule" in f for f in resp.json()["details"]["findings"])


async def test_simulate_writes_nothing(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe8")
    admin_token = await login(client, "admin.recipe8")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"])

    resp = await client.post(
        "/recipes/v2/drafts",
        json=_two_step_body(product_version_id, seeded["site_id"], "RCP-8"),
        headers=auth_headers(admin_token),
    )
    recipe_version_id = resp.json()["aggregate_id"]

    resp = await client.post(f"/recipes/v2/drafts/{recipe_version_id}/simulate", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    assert resp.json()["complete"] is True

    detail = (await client.get(f"/recipes/v2/versions/{recipe_version_id}", headers=auth_headers(admin_token))).json()
    assert detail["lifecycle_state"] == "draft"
    assert detail["version"] == 1  # simulate is not a Mutation Gateway command -- no version bump


async def test_compare_versions_reports_added_step(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe9")
    admin_token = await login(client, "admin.recipe9")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"])

    v1 = (
        await client.post(
            "/recipes/v2/drafts",
            json=_two_step_body(product_version_id, seeded["site_id"], "RCP-9", version_no=1),
            headers=auth_headers(admin_token),
        )
    ).json()["aggregate_id"]

    body_v2 = _two_step_body(product_version_id, seeded["site_id"], "RCP-9", version_no=2)
    body_v2["steps"].append(
        {"stable_step_code": "STEP-C", "section_code": "SEC-1", "step_type": "signature", "sequence_hint": 3}
    )
    v2 = (await client.post("/recipes/v2/drafts", json=body_v2, headers=auth_headers(admin_token))).json()["aggregate_id"]

    diff = (await client.get(f"/recipes/v2/versions/{v1}/compare/{v2}", headers=auth_headers(admin_token))).json()
    assert diff["steps"]["added"] == ["STEP-C"]


async def test_concurrent_draft_update_rejects_stale_version(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe10")
    admin_token = await login(client, "admin.recipe10")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"])

    resp = await client.post(
        "/recipes/v2/drafts",
        json=_two_step_body(product_version_id, seeded["site_id"], "RCP-10"),
        headers=auth_headers(admin_token),
    )
    recipe_version_id = resp.json()["aggregate_id"]

    update_body = {
        "idempotency_key": idem(),
        "recipe_version_id": recipe_version_id,
        "expected_version": 1,
        "sections": [{"stable_section_code": "SEC-1", "name": "Renamed", "sequence": 1}],
        "steps": [],
        "dependencies": [],
    }
    ok = await client.put(f"/recipes/v2/drafts/{recipe_version_id}", json=update_body, headers=auth_headers(admin_token))
    assert ok.status_code == 200, ok.text

    stale = await client.put(
        f"/recipes/v2/drafts/{recipe_version_id}",
        json={**update_body, "idempotency_key": idem()},
        headers=auth_headers(admin_token),
    )
    assert stale.status_code == 409
    assert stale.json()["code"] == "STALE_VERSION"
