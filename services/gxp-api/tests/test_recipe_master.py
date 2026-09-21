"""Document 10 (SPEC-EBMR-001) -- draft/validate/simulate/submit/release for the new, additive Master
Recipe module. Does not touch app/modules/recipe (the legacy Batch-facing stub); the full pre-existing
suite passes unmodified, proving that. Release correctly fails closed pending Document 106 (SG-035's scope
extended to recipe_version) -- the same honest pattern as every other new regulated action this session.
"""

import uuid

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.material.models import Material
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


async def test_create_draft_without_recipe_code_auto_generates_new_family(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe.autocode")
    admin_token = await login(client, "admin.recipe.autocode")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"], "RCPPRD-AUTOCODE")

    body = _two_step_body(product_version_id, seeded["site_id"])
    body["product_business_id"] = "RCPPRD-AUTOCODE"
    body.pop("recipe_code")
    resp = await client.post("/recipes/v2/drafts", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    version_id = resp.json()["aggregate_id"]

    detail = (await client.get(f"/recipes/v2/versions/{version_id}", headers=auth_headers(admin_token))).json()
    families_resp = (await client.get("/recipes/v2/families", headers=auth_headers(admin_token))).json()
    family = next(f for f in families_resp if f["recipe_family_id"] == detail["recipe_family_id"])
    assert family["recipe_code"].startswith("RCP-")


async def test_draft_rejects_unknown_product_version_with_404(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe1b")
    admin_token = await login(client, "admin.recipe1b")
    resp = await client.post(
        "/recipes/v2/drafts",
        json=_two_step_body(str(uuid.uuid4()), seeded["site_id"], "RCP-NOPV"),
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


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


async def test_families_listing_summarises_each_recipe_family(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe11")
    admin_token = await login(client, "admin.recipe11")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"])

    # Two versions in one family (RCP-FAM), plus a separate single-version family (RCP-SOLO).
    fam_v1 = (
        await client.post(
            "/recipes/v2/drafts",
            json=_two_step_body(product_version_id, seeded["site_id"], "RCP-FAM", version_no=1),
            headers=auth_headers(admin_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        "/recipes/v2/drafts",
        json=_two_step_body(product_version_id, seeded["site_id"], "RCP-FAM", version_no=2),
        headers=auth_headers(admin_token),
    )
    await client.post(
        "/recipes/v2/drafts",
        json=_two_step_body(product_version_id, seeded["site_id"], "RCP-SOLO", version_no=1),
        headers=auth_headers(admin_token),
    )

    resp = await client.get("/recipes/v2/families", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    by_code = {row["recipe_code"]: row for row in resp.json()}

    assert by_code["RCP-FAM"]["version_count"] == 2
    assert by_code["RCP-FAM"]["latest_version_no"] == 2
    assert by_code["RCP-FAM"]["latest_lifecycle_state"] == "draft"
    assert by_code["RCP-FAM"]["latest_recipe_version_id"] is not None
    assert by_code["RCP-FAM"]["has_released"] is False
    assert by_code["RCP-FAM"]["product_business_id"] == "RCPPRD-1"
    assert by_code["RCP-SOLO"]["version_count"] == 1

    # The listed family id round-trips through the existing per-family versions endpoint.
    fam_id = by_code["RCP-FAM"]["recipe_family_id"]
    versions = (await client.get(f"/recipes/v2/{fam_id}/versions", headers=auth_headers(admin_token))).json()
    assert {v["recipe_version_id"] for v in versions} >= {fam_v1}


async def test_families_listing_rejects_unauthenticated(client):
    resp = await client.get("/recipes/v2/families", headers={})
    assert resp.status_code == 401


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


async def test_process_engineer_authors_but_a_separate_role_releases(client, seeded, db):
    """SG-178 authoring-SoD half: Process Engineer holds recipe.author (draft/edit/submit) but not
    recipe.release; a distinct role (QA Releaser) holds recipe.release. author != releaser."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe12")
        await _make_user_with_role(db, seeded, "pe.recipe12", "Process Engineer")
        await _make_user_with_role(db, seeded, "releaser.recipe12", "QA Releaser")
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, "admin.recipe12")
    pe_token = await login(client, "pe.recipe12")
    releaser_token = await login(client, "releaser.recipe12")

    # Admin owns the product master; the Process Engineer only authors the recipe against it.
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"], business_id="RCPPE-1")

    resp = await client.post(
        "/recipes/v2/drafts",
        json=_two_step_body(product_version_id, seeded["site_id"], "RCP-PE"),
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text
    recipe_version_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/recipes/v2/drafts/{recipe_version_id}/submit",
        json={"idempotency_key": idem(), "recipe_version_id": recipe_version_id, "expected_version": 1},
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text

    # The author cannot release.
    resp = await client.post(
        f"/recipes/v2/drafts/{recipe_version_id}/release",
        json={"idempotency_key": idem(), "recipe_version_id": recipe_version_id, "expected_version": 2},
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"

    # A separate role can.
    resp = await client.post(
        f"/recipes/v2/drafts/{recipe_version_id}/release",
        json={"idempotency_key": idem(), "recipe_version_id": recipe_version_id, "expected_version": 2},
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/recipes/v2/versions/{recipe_version_id}", headers=auth_headers(pe_token))).json()
    assert detail["lifecycle_state"] == "released"


async def test_recipe_release_is_signed_by_an_independent_qa_releaser(client, seeded, db):
    """recipe_version/release signature policy (2026-09-08): signature_required + required_role
    'QA Releaser' + requires_independent_signer. The author cannot sign their own release even if they
    also hold the releasing role."""
    async with db.begin():
        # One person who can BOTH author and (role-wise) release — proves independence still blocks them.
        dual = await _make_user_with_role(db, seeded, "dual.recipe13", "Process Engineer")
        db.add(UserSiteRole(user_id=dual.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Releaser"].id))
        await _make_admin(db, seeded, "admin.recipe13")
        await _make_user_with_role(db, seeded, "releaser.recipe13", "QA Releaser")
        db.add(
            SignaturePolicy(
                record_type="recipe_version",
                action="release",
                meaning="Released",
                required_role_id=seeded["roles"]["QA Releaser"].id,
                requires_independent_signer=True,
                signature_required=True,
            )
        )
    admin_token = await login(client, "admin.recipe13")
    dual_token = await login(client, "dual.recipe13")
    releaser_token = await login(client, "releaser.recipe13")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"], business_id="RCPSIG-1")

    rv = (
        await client.post(
            "/recipes/v2/drafts",
            json=_two_step_body(product_version_id, seeded["site_id"], "RCP-SIG"),
            headers=auth_headers(dual_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/recipes/v2/drafts/{rv}/submit",
        json={"idempotency_key": idem(), "recipe_version_id": rv, "expected_version": 1},
        headers=auth_headers(dual_token),
    )

    body = {"idempotency_key": idem(), "recipe_version_id": rv, "expected_version": 2}

    # Author (who also holds QA Releaser) tries to release their own recipe -> independence blocks it.
    resp = await client.post(f"/recipes/v2/drafts/{rv}/release", json=body, headers=auth_headers(dual_token))
    assert resp.status_code == 409
    assert resp.json()["code"] == "SOD_CONFLICT"

    # Independent QA Releaser, unsigned -> 428.
    resp = await client.post(
        f"/recipes/v2/drafts/{rv}/release", json={**body, "idempotency_key": idem()}, headers=auth_headers(releaser_token)
    )
    assert resp.status_code == 428

    # Independent QA Releaser, signed -> released.
    ch = (
        await client.post(
            f"/recipes/v2/drafts/{rv}/signature-challenges", json={"action": "release"}, headers=auth_headers(releaser_token)
        )
    ).json()
    resp = await client.post(
        f"/recipes/v2/drafts/{rv}/release",
        json={**body, "idempotency_key": idem(), "challenge_id": ch["challenge_id"], "reauth_password": DEMO_PASSWORD},
        headers=auth_headers(releaser_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/recipes/v2/versions/{rv}", headers=auth_headers(releaser_token))).json()
    assert detail["lifecycle_state"] == "released"
    assert detail["released_vault_object_id"] is not None


async def test_material_and_equipment_requirements_round_trip(client, seeded, db):

    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe.reqs")
    admin_token = await login(client, "admin.recipe.reqs")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"], "RCPPRD-REQS")

    async with db.begin():
        material = Material(site_id=seeded["site_id"], code="MAT-RCP-REQ-1", name="Recipe Req Material", uom="kg")
        db.add(material)
    material_id = material.id

    mat_spec_resp = await client.post(
        "/material-specifications/v1/drafts",
        json={
            "idempotency_key": idem(), "material_spec_business_id": "RCPMAT-REQ-1", "version_no": 1,
            "material_id": str(material_id), "name": "Recipe Req Material Spec", "site_id": str(seeded["site_id"]),
        },
        headers=auth_headers(admin_token),
    )
    assert mat_spec_resp.status_code == 200, mat_spec_resp.text
    material_spec_version_id = mat_spec_resp.json()["aggregate_id"]

    body = _two_step_body(product_version_id, seeded["site_id"], "RCP-REQS")
    body["steps"][0]["material_requirements"] = [
        {
            "material_spec_version_id": material_spec_version_id,
            "target_value": "10.0", "min_value": "9.5", "max_value": "10.5", "uom": "kg",
            "substitution_allowed": False, "consume_mode": "full", "genealogy_required": True,
        }
    ]
    body["steps"][0]["equipment_requirements"] = [
        {
            "equipment_class": "mixer", "exact_equipment_optional": True,
            "require_current_calibration": True, "require_current_qualification": True,
        }
    ]

    resp = await client.post("/recipes/v2/drafts", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    rv = resp.json()["aggregate_id"]

    detail = (await client.get(f"/recipes/v2/versions/{rv}", headers=auth_headers(admin_token))).json()
    assert len(detail["material_requirements"]) == 1
    mreq = detail["material_requirements"][0]
    assert mreq["material_spec_version_id"] == material_spec_version_id
    assert mreq["min_value"] == "9.50000000"
    assert mreq["max_value"] == "10.50000000"
    assert mreq["genealogy_required"] is True

    assert len(detail["equipment_requirements"]) == 1
    ereq = detail["equipment_requirements"][0]
    assert ereq["equipment_class"] == "mixer"
    assert ereq["require_current_calibration"] is True
    assert ereq["require_current_qualification"] is True
    assert ereq["require_current_cleaning"] is False


async def test_material_requirement_rejects_unknown_material_spec_version_id(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe.reqs2")
    admin_token = await login(client, "admin.recipe.reqs2")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"], "RCPPRD-REQS2")

    body = _two_step_body(product_version_id, seeded["site_id"], "RCP-REQS2")
    body["steps"][0]["material_requirements"] = [
        {"material_spec_version_id": str(uuid.uuid4()), "genealogy_required": True}
    ]

    resp = await client.post("/recipes/v2/drafts", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_update_draft_replaces_material_and_equipment_requirements(client, seeded, db):

    async with db.begin():
        await _make_admin(db, seeded, "admin.recipe.reqs3")
    admin_token = await login(client, "admin.recipe.reqs3")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"], "RCPPRD-REQS3")

    async with db.begin():
        material = Material(site_id=seeded["site_id"], code="MAT-RCP-REQ-3", name="Recipe Req Material 3", uom="kg")
        db.add(material)
    material_id = material.id

    mat_spec_resp = await client.post(
        "/material-specifications/v1/drafts",
        json={
            "idempotency_key": idem(), "material_spec_business_id": "RCPMAT-REQ-3", "version_no": 1,
            "material_id": str(material_id), "name": "Recipe Req Material Spec 3", "site_id": str(seeded["site_id"]),
        },
        headers=auth_headers(admin_token),
    )
    material_spec_version_id = mat_spec_resp.json()["aggregate_id"]

    body = _two_step_body(product_version_id, seeded["site_id"], "RCP-REQS3")
    body["steps"][0]["equipment_requirements"] = [{"equipment_class": "mixer"}]
    create = await client.post("/recipes/v2/drafts", json=body, headers=auth_headers(admin_token))
    assert create.status_code == 200, create.text
    rv = create.json()["aggregate_id"]

    steps = [dict(s) for s in body["steps"]]
    steps[0] = dict(steps[0])
    steps[0]["equipment_requirements"] = []
    steps[0]["material_requirements"] = [
        {"material_spec_version_id": material_spec_version_id, "genealogy_required": False}
    ]
    update_body = {
        "idempotency_key": idem(),
        "recipe_version_id": rv,
        "expected_version": 1,
        "sections": body["sections"],
        "steps": steps,
        "dependencies": body["dependencies"],
    }
    update = await client.put(f"/recipes/v2/drafts/{rv}", json=update_body, headers=auth_headers(admin_token))
    assert update.status_code == 200, update.text

    detail = (await client.get(f"/recipes/v2/versions/{rv}", headers=auth_headers(admin_token))).json()
    assert detail["equipment_requirements"] == []
    assert len(detail["material_requirements"]) == 1
    assert detail["material_requirements"][0]["genealogy_required"] is False


async def _release_recipe(client, admin_token, rv, expected_version):
    """Uses the global recipe_version/release signature policy conftest.py already seeds for every
    other test in this file that doesn't override it locally."""
    ch = (
        await client.post(
            f"/recipes/v2/drafts/{rv}/signature-challenges", json={"action": "release"}, headers=auth_headers(admin_token)
        )
    ).json()
    return await client.post(
        f"/recipes/v2/drafts/{rv}/release",
        json={
            "idempotency_key": idem(), "recipe_version_id": rv, "expected_version": expected_version,
            "challenge_id": ch["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )


async def test_recipe_obsolete_and_supersede(client, seeded, db):
    """Known-limitations fix (docs/testing/demo-gujarati/07 §7.9 item 1), corrected per SG-208: Recipe
    Master had no suspend/reinstate/obsolete/supersede at all before this. Uses the global recipe_version
    signature policy rows conftest.py seeds. `obsolete`/`supersede` match Document 106 §8's "cancel/
    abort/void" family (Approved, QA Releaser, independent of the author) -- the author (admin, even
    though also granted QA Releaser directly) cannot obsolete/supersede their own draft; a separate,
    independent QA Releaser can, once signed."""
    async with db.begin():
        author = await _make_admin(db, seeded, "admin.recipe.obsolete")
        # Also grant the author QA Releaser directly so the independence check is exercised specifically
        # (not just a role they happen to lack) -- same trick
        # test_reinstate_wrong_role_no_challenge_and_independent_success uses.
        db.add(UserSiteRole(user_id=author.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Releaser"].id))
        await _make_user_with_role(db, seeded, "qa.recipe.obsolete", "QA Releaser")
        db.add(
            SignaturePolicy(
                record_type="recipe_version", action="release", meaning="Released",
                required_role_id=seeded["roles"]["Admin"].id, requires_independent_signer=False,
                signature_required=True, reason_required=False,
            )
        )
    admin_token = await login(client, "admin.recipe.obsolete")
    qa_token = await login(client, "qa.recipe.obsolete")
    product_version_id = await _make_product_version(client, admin_token, seeded["site_id"], business_id="RCPOBS-1")

    rv1 = (
        await client.post(
            "/recipes/v2/drafts",
            json=_two_step_body(product_version_id, seeded["site_id"], "RCP-OBS", version_no=1),
            headers=auth_headers(admin_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/recipes/v2/drafts/{rv1}/submit",
        json={"idempotency_key": idem(), "recipe_version_id": rv1, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert (await _release_recipe(client, admin_token, rv1, 2)).status_code == 200

    # The author (admin), despite also holding QA Releaser, is not independent of themselves.
    not_independent = await client.post(
        f"/recipes/v2/{rv1}/obsolete",
        json={"idempotency_key": idem(), "recipe_version_id": rv1, "expected_version": 3, "reason": "discontinued"},
        headers=auth_headers(admin_token),
    )
    assert not_independent.status_code == 409, not_independent.text
    assert not_independent.json()["code"] == "SOD_INDEPENDENCE_REQUIRED"

    # Obsolete: unsigned -> 428, signed -> success, then terminal.
    unsigned = await client.post(
        f"/recipes/v2/{rv1}/obsolete",
        json={"idempotency_key": idem(), "recipe_version_id": rv1, "expected_version": 3, "reason": "discontinued"},
        headers=auth_headers(qa_token),
    )
    assert unsigned.status_code == 428, unsigned.text

    ch = (
        await client.post(
            f"/recipes/v2/drafts/{rv1}/signature-challenges", json={"action": "obsolete"}, headers=auth_headers(qa_token),
        )
    ).json()
    assert ch["meaning"] == "Approved"
    resp = await client.post(
        f"/recipes/v2/{rv1}/obsolete",
        json={
            "idempotency_key": idem(), "recipe_version_id": rv1, "expected_version": 3, "reason": "discontinued",
            "challenge_id": ch["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/recipes/v2/versions/{rv1}", headers=auth_headers(qa_token))).json()
    assert detail["lifecycle_state"] == "obsolete"

    retry = await client.post(
        f"/recipes/v2/{rv1}/suspend",
        json={"idempotency_key": idem(), "recipe_version_id": rv1, "expected_version": 4, "reason": "x"},
        headers=auth_headers(admin_token),
    )
    assert retry.status_code == 409
    assert retry.json()["code"] == "INVALID_TRANSITION"

    # Supersede: a second released version of the same family.
    rv2 = (
        await client.post(
            "/recipes/v2/drafts",
            json=_two_step_body(product_version_id, seeded["site_id"], "RCP-OBS", version_no=2),
            headers=auth_headers(admin_token),
        )
    ).json()["aggregate_id"]
    await client.post(
        f"/recipes/v2/drafts/{rv2}/submit",
        json={"idempotency_key": idem(), "recipe_version_id": rv2, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert (await _release_recipe(client, admin_token, rv2, 2)).status_code == 200

    rv3 = (
        await client.post(
            "/recipes/v2/drafts",
            json=_two_step_body(product_version_id, seeded["site_id"], "RCP-OBS", version_no=3),
            headers=auth_headers(admin_token),
        )
    ).json()["aggregate_id"]

    ch2 = (
        await client.post(
            f"/recipes/v2/drafts/{rv2}/signature-challenges", json={"action": "supersede"}, headers=auth_headers(qa_token),
        )
    ).json()
    assert ch2["meaning"] == "Approved"

    # A draft (not released) successor is rejected.
    bad = await client.post(
        f"/recipes/v2/{rv2}/supersede",
        json={
            "idempotency_key": idem(), "recipe_version_id": rv2, "expected_version": 3, "reason": "replaced",
            "superseding_version_id": rv3, "challenge_id": ch2["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert bad.status_code == 422, bad.text

    # Release rv3 too, then a real supersede of rv2 by rv3 succeeds.
    await client.post(
        f"/recipes/v2/drafts/{rv3}/submit",
        json={"idempotency_key": idem(), "recipe_version_id": rv3, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert (await _release_recipe(client, admin_token, rv3, 2)).status_code == 200

    ch3 = (
        await client.post(
            f"/recipes/v2/drafts/{rv2}/signature-challenges", json={"action": "supersede"}, headers=auth_headers(qa_token),
        )
    ).json()
    good = await client.post(
        f"/recipes/v2/{rv2}/supersede",
        json={
            "idempotency_key": idem(), "recipe_version_id": rv2, "expected_version": 3,
            "reason": "replaced", "superseding_version_id": rv3,
            "challenge_id": ch3["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(qa_token),
    )
    assert good.status_code == 200, good.text
    detail2 = (await client.get(f"/recipes/v2/versions/{rv2}", headers=auth_headers(qa_token))).json()
    assert detail2["lifecycle_state"] == "superseded"
    assert detail2["superseded_by_version_id"] == rv3
