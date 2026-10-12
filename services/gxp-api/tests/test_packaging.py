"""Document 16 (SPEC-EBMR-007) -- the buildable slice: create a packaging run against a batch, complete
line clearance (now wired to the real equipment.line_clearances check, SG-056/item #9), create a label
version and print job (SG-056/item #10), issue labels (with duplicate-serial detection), reconcile labels
and packaging (real quantities in, exact-balance default per Document 16 SS10 since no released
tolerance rule exists), and complete (gated on clearance + both reconciliations balanced). Reprint/
application-verification/inspection still have no entity to persist against and remain unbuilt -- SG-056.
"""

import uuid

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.packaging import service as packaging_service
from app.modules.packaging.models import PackagingRun
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username="admin.pkg"):
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


async def _released_product(client, admin_token, site_id, tag):
    resp = await client.post(
        "/products/v1/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": f"PKGPRD-{tag}", "product_code": f"PKGPRD-{tag}",
            "name": "Packaging Test Product", "version_no": 1, "site_id": str(site_id), "manufacturing_profile_code": "pharma",
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
    return product_version_id


async def _released_recipe(client, admin_token, site_id, product_version_id, tag):
    resp = await client.post(
        "/recipes/v2/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": f"PKGPRD-{tag}", "recipe_code": f"PKGRCP-{tag}", "version_no": 1,
            "product_version_id": product_version_id, "site_id": str(site_id), "manufacturing_profile_code": "pharma",
            "sections": [{"stable_section_code": "SEC-1", "name": "Dispensing", "sequence": 1}],
            "steps": [{"stable_step_code": "STEP-A", "section_code": "SEC-1", "step_type": "weigh", "sequence_hint": 1}],
            "dependencies": [],
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
    return recipe_version_id


async def _setup(db, client, seeded, tag):
    from app.modules.signature.models import SignaturePolicy

    async with db.begin():
        await _make_admin(db, seeded, f"admin.pkg{tag}")
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, f"admin.pkg{tag}")
    product_version_id = await _released_product(client, admin_token, seeded["site_id"], tag)
    recipe_version_id = await _released_recipe(client, admin_token, seeded["site_id"], product_version_id, tag)

    resp = await client.post(
        "/batches/v1",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "batch_number": f"BAT-PKG-{tag}",
            "product_version_id": product_version_id, "recipe_version_id": recipe_version_id,
            "target_qty": "10.0", "target_uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["aggregate_id"]
    return admin_token, batch_id


async def _clear_line_for_batch(client, admin_token, site_id, batch_id):
    """Client gap-closure item #9 (2026-10-09, project-owner-directed): packaging's own line-clearance
    endpoint now requires a real, CLEARED equipment.line_clearances row targeting this batch
    (get_batch_line_clearance_status()) -- this helper creates and completes one, same signed ceremony
    as test_cleaning_flow.py::test_line_clearance_full_flow."""
    resp = await client.post(
        "/line-clearance/v1",
        json={"idempotency_key": idem(), "site_id": str(site_id), "next_batch_id": batch_id, "checklist_version": "LC-PKG-1"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    clearance_id = resp.json()["aggregate_id"]
    challenge = (
        await client.post(f"/line-clearance/v1/{clearance_id}/signature-challenges", json={"action": "complete"}, headers=auth_headers(admin_token))
    ).json()
    resp = await client.post(
        f"/line-clearance/v1/{clearance_id}/complete",
        json={
            "idempotency_key": idem(), "clearance_id": clearance_id, "expected_version": 1, "passed": True,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/packaging/v1/runs", json={"idempotency_key": idem()}, headers={})
    assert resp.status_code == 401


async def test_create_run_requires_permission(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "1")
    qc_token = await login(client, "qc.reviewer")  # QC Reviewer is not granted packaging.execute
    resp = await client.post(
        "/packaging/v1/runs",
        json={"idempotency_key": idem(), "batch_id": batch_id},
        headers=auth_headers(qc_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_issue_label_before_line_clearance_rejected(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "2")
    resp = await client.post("/packaging/v1/runs", json={"idempotency_key": idem(), "batch_id": batch_id}, headers=auth_headers(admin_token))
    run_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/labels/issue",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 1, "quantity_issued": 100},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_full_packaging_lifecycle(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "3")
    resp = await client.post("/packaging/v1/runs", json={"idempotency_key": idem(), "batch_id": batch_id}, headers=auth_headers(admin_token))
    run_id = resp.json()["aggregate_id"]

    await _clear_line_for_batch(client, admin_token, seeded["site_id"], batch_id)
    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/line-clearance",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 1, "reason": "line cleared, prior product removed"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/labels/issue",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 2, "quantity_issued": 100, "serial_range": {"serials": ["SN-A1", "SN-A2"]}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/reconcile-labels",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 3, "applied": 95, "returned": 3, "destroyed": 1, "rejected": 1, "samples": 0},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/reconcile-packaging",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 4, "components_issued": 100, "finished_packs": 98, "rejects": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/complete",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 5},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    run = await db.get(PackagingRun, run_id)
    assert run.state == "complete"
    assert run.line_clearance_completed is True
    assert run.reconciliation_state == "balanced"


async def test_duplicate_serial_rejected(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "4")
    resp = await client.post("/packaging/v1/runs", json={"idempotency_key": idem(), "batch_id": batch_id}, headers=auth_headers(admin_token))
    run_id = resp.json()["aggregate_id"]
    await _clear_line_for_batch(client, admin_token, seeded["site_id"], batch_id)
    await client.post(
        f"/packaging/v1/runs/{run_id}/line-clearance",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/labels/issue",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 2, "quantity_issued": 10, "serial_range": {"serials": ["SN-DUP"]}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/labels/issue",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 3, "quantity_issued": 10, "serial_range": {"serials": ["SN-DUP"]}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert "SN-DUP" in str(resp.json()["details"])


async def test_label_version_and_print_job_wired_into_label_issue(client, seeded, db):
    """Client gap-closure item #10 (2026-10-09, project-owner-directed: "Build a minimal version"):
    label_master (PKG-FR-003) and print_job (PKG-FR-006) now exist, and label_issue's label_version_id/
    print_job_id are real enforced FKs rather than unvalidated UUID columns."""
    admin_token, batch_id = await _setup(db, client, seeded, "21")
    resp = await client.post("/packaging/v1/runs", json={"idempotency_key": idem(), "batch_id": batch_id}, headers=auth_headers(admin_token))
    run_id = resp.json()["aggregate_id"]
    await _clear_line_for_batch(client, admin_token, seeded["site_id"], batch_id)
    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/line-clearance",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/packaging/v1/label-versions",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "label_code": "LBL-MJ-PFS-40MG",
            "version_label": "1.0", "content_hash": "b" * 64,
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    label_version_id = resp.json()["aggregate_id"]

    # Unrecognized label_version_id is rejected, not silently stored.
    resp = await client.post(
        "/packaging/v1/print-jobs",
        json={"idempotency_key": idem(), "run_id": run_id, "label_version_id": str(uuid.uuid4()), "quantity": 100},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 404, resp.text

    resp = await client.post(
        "/packaging/v1/print-jobs",
        json={
            "idempotency_key": idem(), "run_id": run_id, "label_version_id": label_version_id, "quantity": 100,
            "variable_data": {"lot": "MJ-PFS-B-2601"}, "printer_ref": "ZEBRA-LINE3-01",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    print_job_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/labels/issue",
        json={
            "idempotency_key": idem(), "run_id": run_id, "expected_version": 2, "quantity_issued": 100,
            "label_version_id": label_version_id, "print_job_id": print_job_id, "serial_range": {"serials": ["SN-LBL-1"]},
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    detail = (await client.get(f"/packaging/v1/runs/{run_id}", headers=auth_headers(admin_token))).json()
    issue = detail["label_issues"][0]
    assert issue["label_version_id"] == label_version_id
    assert issue["print_job_id"] == print_job_id

    listing = (await client.get(f"/packaging/v1/print-jobs?run_id={run_id}", headers=auth_headers(admin_token))).json()
    assert len(listing) == 1
    assert listing[0]["printer_ref"] == "ZEBRA-LINE3-01"


async def test_line_clearance_rejected_without_real_equipment_clearance(client, seeded, db):
    """Client gap-closure item #9 (2026-10-09, project-owner-directed: "Yes, wire to the real check"):
    packaging's own line-clearance can no longer be completed by flag alone -- it now requires a real
    CLEARED equipment.line_clearances row targeting this batch."""
    admin_token, batch_id = await _setup(db, client, seeded, "20")
    resp = await client.post("/packaging/v1/runs", json={"idempotency_key": idem(), "batch_id": batch_id}, headers=auth_headers(admin_token))
    run_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/line-clearance",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "LINE_CLEARANCE_REQUIRED"

    # Now clear the line for real and retry with the same body/version -- succeeds.
    await _clear_line_for_batch(client, admin_token, seeded["site_id"], batch_id)
    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/line-clearance",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text


async def test_complete_rejected_without_line_clearance(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "5")
    resp = await client.post("/packaging/v1/runs", json={"idempotency_key": idem(), "batch_id": batch_id}, headers=auth_headers(admin_token))
    run_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/complete",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_complete_rejected_with_unbalanced_reconciliation(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "6")
    resp = await client.post("/packaging/v1/runs", json={"idempotency_key": idem(), "batch_id": batch_id}, headers=auth_headers(admin_token))
    run_id = resp.json()["aggregate_id"]
    await _clear_line_for_batch(client, admin_token, seeded["site_id"], batch_id)
    await client.post(
        f"/packaging/v1/runs/{run_id}/line-clearance",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    await client.post(
        f"/packaging/v1/runs/{run_id}/labels/issue",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 2, "quantity_issued": 100},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/reconcile-labels",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 3, "applied": 50},  # 50 short -- discrepancy
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    await client.post(
        f"/packaging/v1/runs/{run_id}/reconcile-packaging",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 4, "components_issued": 100, "finished_packs": 100},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/complete",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 5},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_stale_version_rejected(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "7")
    resp = await client.post("/packaging/v1/runs", json={"idempotency_key": idem(), "batch_id": batch_id}, headers=auth_headers(admin_token))
    run_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/packaging/v1/runs/{run_id}/line-clearance",
        json={"idempotency_key": idem(), "run_id": run_id, "expected_version": 99},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "STALE_VERSION"


async def test_duplicate_idempotency_key_returns_same_receipt(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "8")
    key = idem()
    body = {"idempotency_key": key, "batch_id": batch_id}
    resp1 = await client.post("/packaging/v1/runs", json=body, headers=auth_headers(admin_token))
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post("/packaging/v1/runs", json=body, headers=auth_headers(admin_token))
    assert resp2.status_code == 200, resp2.text
    assert resp1.json()["aggregate_id"] == resp2.json()["aggregate_id"]
    assert resp1.json()["command_id"] == resp2.json()["command_id"]


async def test_package_node_hierarchy(client, seeded, db):
    admin_token, batch_id = await _setup(db, client, seeded, "9")
    async with db.begin():
        pallet = await packaging_service.create_package_node(db, package_level="pallet", batch_id=batch_id, business_ref="PALLET-9")
        carton = await packaging_service.create_package_node(db, package_level="carton", batch_id=batch_id, business_ref="CARTON-9", parent_package_id=pallet.id)

    children = await packaging_service.get_package_children(db, pallet.id)
    assert len(children) == 1
    assert children[0].id == carton.id
