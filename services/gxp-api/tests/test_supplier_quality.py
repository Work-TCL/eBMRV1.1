"""WP-04 / Document 18 (SPEC-MAT-001) thin slice: supplier + site master (SUP-FR-001/002/029) ->
qualification request (SUP-FR-003/004/005/013) -> signed approval (SUP-FR-007/009/012), cascading the
supplier's own DRAFT->UNDER_QUALIFICATION->APPROVED lifecycle (Document 18 §5). `approved_supplier_material`
/ `purchase_requisition` / `purchase_order_ref` are out of scope this pass (SG-057)."""

import uuid

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.iam.models import Role, User, UserSiteRole
from app.modules.material.models import Material
from app.modules.supplier_quality.models import (
    Supplier,
    SupplierQualification,
    SupplierQualificationEvidence,
    SupplierQualificationScopeItem,
    SupplierSite,
)
from app.modules.vault.models import VaultObject
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _promote_to_admin(db, seeded, username):
    """No seeded test user holds "Admin" by default (tests/conftest.py's fixture deliberately keeps
    roles disjoint, unlike the live demo's scripts/seed.py). Same `_promote_to_admin` technique
    test_iam_admin.py/test_equipment_flow.py already use -- grant an existing seeded user Admin too,
    rather than assuming a demo "admin" username that only exists in the live seed script."""
    admin_role = (await db.execute(select(Role).where(Role.name == "Admin"))).scalar_one()
    db.add(UserSiteRole(user_id=seeded["users"][username].id, site_id=seeded["site_id"], role_id=admin_role.id))


async def _create_supplier(client, token, code="SUP-1", name="Acme Pharma Supply Co.", country="US"):
    resp = await client.post(
        "/suppliers/v1",
        json={
            "idempotency_key": idem(),
            "supplier_code": code,
            "legal_name": name,
            "role_type": "supplier",
            "country": country,
            "sites": [{"site_name": "Main Site", "country": country, "manufacturer_flag": False}],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def _site_id_for(db, supplier_id: str) -> str:
    return str((await db.execute(select(SupplierSite.id).where(SupplierSite.supplier_id == supplier_id))).scalars().first())


async def _create_qualification(client, token, supplier_id, site_id, quality_agreement_vault_id=None):
    body = {
        "idempotency_key": idem(),
        "supplier_id": supplier_id,
        "supplier_site_id": site_id,
        "risk_class": "critical",
    }
    if quality_agreement_vault_id is not None:
        body["quality_agreement_vault_id"] = quality_agreement_vault_id
    resp = await client.post(f"/suppliers/{supplier_id}/qualifications", json=body, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def test_create_supplier_without_code_auto_generates(client, seeded, db):
    pe_token = await login(client, "process.engineer")
    resp1 = await client.post(
        "/suppliers/v1",
        json={
            "idempotency_key": idem(), "legal_name": "Auto Coded Supplier One", "role_type": "supplier",
            "country": "US", "sites": [],
        },
        headers=auth_headers(pe_token),
    )
    assert resp1.status_code == 200, resp1.text
    resp2 = await client.post(
        "/suppliers/v1",
        json={
            "idempotency_key": idem(), "legal_name": "Auto Coded Supplier Two", "role_type": "supplier",
            "country": "US", "sites": [],
        },
        headers=auth_headers(pe_token),
    )
    assert resp2.status_code == 200, resp2.text

    supplier1 = await db.get(Supplier, resp1.json()["aggregate_id"])
    supplier2 = await db.get(Supplier, resp2.json()["aggregate_id"])
    assert supplier1.supplier_code.startswith("SUP-")
    assert supplier2.supplier_code.startswith("SUP-")
    assert supplier1.supplier_code != supplier2.supplier_code


async def test_create_supplier_and_site(client, seeded, db):
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token)

    supplier = await db.get(Supplier, supplier_id)
    assert supplier.status == "draft"
    assert supplier.role_type == "supplier"


async def test_add_site_to_existing_supplier(client, seeded, db):
    # Bug fix: Document 18 §7 only ever declared site creation embedded in CreateSupplier's own command,
    # so there was previously no way to add a site to a supplier that already existed.
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token)

    resp = await client.post(
        f"/suppliers/{supplier_id}/sites",
        json={
            "idempotency_key": idem(),
            "supplier_id": supplier_id,
            "site": {"site_name": "Second Site", "city": "Boston", "country": "US", "manufacturer_flag": True},
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text

    sites = (
        await db.execute(select(SupplierSite).where(SupplierSite.supplier_id == supplier_id))
    ).scalars().all()
    assert len(sites) == 2
    new_site = next(s for s in sites if s.site_name == "Second Site")
    assert new_site.city == "Boston"
    assert new_site.manufacturer_flag is True
    assert new_site.status == "active"


async def test_add_site_requires_role(client, seeded):
    op_token = await login(client, "operator1")
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token)

    resp = await client.post(
        f"/suppliers/{supplier_id}/sites",
        json={
            "idempotency_key": idem(), "supplier_id": supplier_id,
            "site": {"site_name": "Unauthorized Site"},
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_create_manufacturer_supplier(client, seeded, db):
    """SUP-FR-002: role_type distinguishes a manufacturer identity from a commercial supplier."""
    pe_token = await login(client, "process.engineer")
    resp = await client.post(
        "/suppliers/v1",
        json={
            "idempotency_key": idem(),
            "supplier_code": "MFR-1",
            "legal_name": "Precision Manufacturing Inc.",
            "role_type": "manufacturer",
            "country": "US",
            "sites": [{"site_name": "Plant 1", "country": "US", "manufacturer_flag": True}],
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text
    supplier = await db.get(Supplier, resp.json()["aggregate_id"])
    assert supplier.role_type == "manufacturer"

    site = (
        await db.execute(select(SupplierSite).where(SupplierSite.supplier_id == supplier.id))
    ).scalars().first()
    assert site.manufacturer_flag is True


async def test_create_service_provider_supplier(client, seeded, db):
    """Client gap-analysis Phase 6 (2026-10-05): role_type gained "service_provider" so a
    calibration/repair/test-lab vendor -- neither a material supplier nor a manufacturer -- has a proper
    home, reusable as a picker on EquipmentCalibration.provider_supplier_id and
    QcTestOrder.external_provider_id."""
    pe_token = await login(client, "process.engineer")
    resp = await client.post(
        "/suppliers/v1",
        json={
            "idempotency_key": idem(),
            "supplier_code": "SVC-1",
            "legal_name": "Precision Calibration Services LLC",
            "role_type": "service_provider",
            "country": "US",
            "sites": [],
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text
    supplier = await db.get(Supplier, resp.json()["aggregate_id"])
    assert supplier.role_type == "service_provider"


async def test_create_supplier_rejects_unknown_role_type(client, seeded, db):
    pe_token = await login(client, "process.engineer")
    resp = await client.post(
        "/suppliers/v1",
        json={
            "idempotency_key": idem(), "legal_name": "Mystery Vendor", "role_type": "distributor",
            "country": "US", "sites": [],
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_qualification_with_quality_agreement(client, seeded, db):
    """SUP-FR-013: quality_agreement_vault_id references an existing Vault object."""
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-QA")

    async with db.begin():
        vault_obj = VaultObject(
            object_type="quality_agreement",
            business_id="QA-SUP-QA",
            internal_version=1,
            canonical_payload={"terms": "standard"},
            digest="1" * 64,
        )
        db.add(vault_obj)

    site_id = await _site_id_for(db, supplier_id)
    qualification_id = await _create_qualification(
        client, pe_token, supplier_id, site_id, quality_agreement_vault_id=str(vault_obj.object_id)
    )
    qualification = await db.get(SupplierQualification, qualification_id)
    assert str(qualification.quality_agreement_vault_id) == str(vault_obj.object_id)


async def test_duplicate_supplier_candidate_rejected(client, seeded):
    pe_token = await login(client, "process.engineer")
    await _create_supplier(client, pe_token, code="SUP-DUP-1", name="Duplicate Legal Name LLC")

    resp = await client.post(
        "/suppliers/v1",
        json={
            "idempotency_key": idem(),
            "supplier_code": "SUP-DUP-2",
            "legal_name": "duplicate legal name llc",  # same identity, different case/code
            "role_type": "supplier",
            "country": "US",
            "sites": [],
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "DUPLICATE_SUPPLIER_CANDIDATE"


async def test_qualification_request_moves_supplier_under_qualification(client, seeded, db):
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-2")
    supplier = await db.get(Supplier, supplier_id)
    await db.refresh(supplier)
    site_id = await _site_id_for(db, supplier_id)

    qualification_id = await _create_qualification(client, pe_token, supplier_id, site_id)

    await db.refresh(supplier)
    assert supplier.status == "under_qualification"

    qualification = await db.get(SupplierQualification, qualification_id)
    assert qualification.status == "requested"
    assert qualification.risk_class == "critical"


async def test_qualification_evidence_attached(client, seeded, db):
    """SUP-FR-005: qualification evidence is stored as a join against an existing Vault object, not a
    new evidence-storage mechanism."""
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-EVID")

    async with db.begin():
        vault_obj = VaultObject(
            object_type="supplier_qualification_evidence",
            business_id="CERT-ISO-9001",
            internal_version=1,
            canonical_payload={"document": "ISO 9001 certificate"},
            digest="0" * 64,
        )
        db.add(vault_obj)
    vault_object_id = str(vault_obj.object_id)

    site_id = await _site_id_for(db, supplier_id)
    resp = await client.post(
        f"/suppliers/{supplier_id}/qualifications",
        json={
            "idempotency_key": idem(),
            "supplier_id": supplier_id,
            "supplier_site_id": site_id,
            "risk_class": "critical",
            "evidence": [{"vault_object_id": vault_object_id, "evidence_category": "certification"}],
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text
    qualification_id = resp.json()["aggregate_id"]

    rows = (
        await db.execute(
            select(SupplierQualificationEvidence).where(
                SupplierQualificationEvidence.supplier_qualification_id == qualification_id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert rows[0].evidence_category == "certification"
    assert str(rows[0].vault_object_id) == vault_object_id


async def test_qualification_scope_material_ids_attached(client, seeded, db):
    """Client gap-analysis Phase 3: structured scope -- `scope_material_ids` creates FK'd
    SupplierQualificationScopeItem rows (MAT-003 approved-supplier-list relationship), surfaced back on
    the GET detail response with the material's code/name resolved, alongside the untouched free-text
    `scope` JSONB."""
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-SCOPE")

    async with db.begin():
        material = Material(site_id=seeded["site_id"], code="MAT-SCOPE-1", name="Scoped Excipient", uom="kg")
        db.add(material)
    material_id = str(material.id)

    # `_site_id_for` runs a SELECT on `db` -- fetched only after the `db.begin()` block above (same
    # ordering `test_qualification_with_quality_agreement` uses), since a read before an explicit
    # `begin()` would autobegin a transaction on the session and conflict with it.
    site_id = await _site_id_for(db, supplier_id)

    resp = await client.post(
        f"/suppliers/{supplier_id}/qualifications",
        json={
            "idempotency_key": idem(),
            "supplier_id": supplier_id,
            "supplier_site_id": site_id,
            "risk_class": "critical",
            "scope": {"description": "Raw material supply"},
            "scope_material_ids": [material_id],
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text
    qualification_id = resp.json()["aggregate_id"]

    rows = (
        await db.execute(
            select(SupplierQualificationScopeItem).where(
                SupplierQualificationScopeItem.supplier_qualification_id == qualification_id
            )
        )
    ).scalars().all()
    assert len(rows) == 1
    assert str(rows[0].material_id) == material_id

    # Process Engineer holds supplier_qualification.create but not supplier.view (same as production's
    # scripts/seed.py grant) -- QA Releaser is one of the QMS_VIEW_CODES recipients that can read it back.
    qa_releaser_token = await login(client, "qa.releaser")
    detail = await client.get(
        f"/supplier-qualifications/{qualification_id}", headers=auth_headers(qa_releaser_token)
    )
    assert detail.status_code == 200, detail.text
    body = detail.json()
    assert body["scope"] == {"description": "Raw material supply"}
    assert body["scope_items"] == [{"material_id": material_id, "code": "MAT-SCOPE-1", "name": "Scoped Excipient"}]


async def test_qualification_scope_unknown_material_rejected(client, seeded, db):
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-SCOPE-BAD")
    site_id = await _site_id_for(db, supplier_id)

    resp = await client.post(
        f"/suppliers/{supplier_id}/qualifications",
        json={
            "idempotency_key": idem(),
            "supplier_id": supplier_id,
            "supplier_site_id": site_id,
            "risk_class": "critical",
            "scope_material_ids": [str(uuid.uuid4())],
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


async def _approve_flow(client, actor_token, qualification_id, decision="approved", justification=None):
    challenge = (
        await client.post(
            f"/supplier-qualifications/{qualification_id}/signature-challenges",
            json={"action": "approve"},
            headers=auth_headers(actor_token),
        )
    ).json()
    body = {
        "idempotency_key": idem(),
        "qualification_id": qualification_id,
        "expected_version": 1,
        "decision": decision,
        "challenge_id": challenge["challenge_id"],
        "reauth_password": "ChangeMe123!",
    }
    if justification is not None:
        body["justification"] = justification
    return await client.post(
        f"/supplier-qualifications/{qualification_id}/approve",
        json=body,
        headers=auth_headers(actor_token),
    )


async def test_approve_requires_role(client, seeded, db):
    op_token = await login(client, "operator1")
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-3")
    site_id = await _site_id_for(db, supplier_id)
    qualification_id = await _create_qualification(client, pe_token, supplier_id, site_id)

    # Operator holds neither supplier_qualification.create nor .approve -- still the right negative
    # case for "a role without approve permission is refused," independent of the RBAC gaps closed
    # 2026-09-18 above.
    resp = await _approve_flow(client, op_token, qualification_id)
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_approve_by_requester_rejected_sod(client, seeded, db):
    """SUP-FR-007/SIG-FR-018: the approver must be independent of the requester.

    2026-09-18: supplier_qualification.create (Process Engineer/Admin) and .approve (QA Releaser/Admin)
    are now disjoint permission classes (RBAC gap closure), so the "same person requests and tries to
    approve" scenario needs a dual-role user to even reach the approve call -- the SoD check itself is
    identity-based (qualification.requested_by_user_id == actor_user_id), independent of which role(s)
    that identity holds, matching test_product_master.py's own dual-role SoD test pattern."""
    async with db.begin():
        dual = User(
            username="dual.supplier", email="dual.supplier@example.com", full_name="Dual Supplier",
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(dual)
        await db.flush()
        db.add(UserSiteRole(user_id=dual.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Process Engineer"].id))
        db.add(UserSiteRole(user_id=dual.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Releaser"].id))
    dual_token = await login(client, "dual.supplier")

    supplier_id = await _create_supplier(client, dual_token, code="SUP-4")
    site_id = await _site_id_for(db, supplier_id)
    qualification_id = await _create_qualification(client, dual_token, supplier_id, site_id)

    resp = await _approve_flow(client, dual_token, qualification_id)
    assert resp.status_code == 409
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_conditional_approval_requires_justification(client, seeded, db):
    pe_token = await login(client, "process.engineer")
    qa_releaser_token = await login(client, "qa.releaser")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-5")
    site_id = await _site_id_for(db, supplier_id)
    qualification_id = await _create_qualification(client, pe_token, supplier_id, site_id)

    resp = await _approve_flow(client, qa_releaser_token, qualification_id, decision="conditional")
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_conditional_approval_succeeds_with_justification(client, seeded, db):
    pe_token = await login(client, "process.engineer")
    qa_releaser_token = await login(client, "qa.releaser")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-COND")
    site_id = await _site_id_for(db, supplier_id)
    qualification_id = await _create_qualification(client, pe_token, supplier_id, site_id)

    resp = await _approve_flow(
        client,
        qa_releaser_token,
        qualification_id,
        decision="conditional",
        justification="Enhanced incoming inspection required for first 3 lots (SUP-FR-012).",
    )
    assert resp.status_code == 200, resp.text

    qualification = await db.get(SupplierQualification, qualification_id)
    await db.refresh(qualification)
    assert qualification.status == "conditional"
    assert "Enhanced incoming inspection" in qualification.justification

    supplier = await db.get(Supplier, supplier_id)
    await db.refresh(supplier)
    assert supplier.status == "approved"


async def test_full_qualification_approval_flow(client, seeded, db):
    pe_token = await login(client, "process.engineer")
    qa_releaser_token = await login(client, "qa.releaser")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-6")
    site_id = await _site_id_for(db, supplier_id)
    qualification_id = await _create_qualification(client, pe_token, supplier_id, site_id)

    resp = await _approve_flow(client, qa_releaser_token, qualification_id, decision="approved")
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None

    supplier = await db.get(Supplier, supplier_id)
    await db.refresh(supplier)
    assert supplier.status == "approved"

    qualification = await db.get(SupplierQualification, qualification_id)
    await db.refresh(qualification)
    assert qualification.status == "approved"
    assert qualification.version == 2


async def test_approve_stale_version_rejected(client, seeded, db):
    pe_token = await login(client, "process.engineer")
    qa_releaser_token = await login(client, "qa.releaser")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-7")
    site_id = await _site_id_for(db, supplier_id)
    qualification_id = await _create_qualification(client, pe_token, supplier_id, site_id)

    challenge = (
        await client.post(
            f"/supplier-qualifications/{qualification_id}/signature-challenges",
            json={"action": "approve"},
            headers=auth_headers(qa_releaser_token),
        )
    ).json()
    resp = await client.post(
        f"/supplier-qualifications/{qualification_id}/approve",
        json={
            "idempotency_key": idem(),
            "qualification_id": qualification_id,
            "expected_version": 99,
            "decision": "approved",
            "challenge_id": challenge["challenge_id"],
            "reauth_password": "ChangeMe123!",
        },
        headers=auth_headers(qa_releaser_token),
    )
    assert resp.status_code == 409
    assert resp.json()["code"] == "STALE_VERSION"


async def test_update_draft_supplier_succeeds(client, seeded):
    """project-owner-directed (2026-10-06): edit a supplier's own record while it's still draft -- same
    permission as create, same shape as Product/Recipe's own update_draft precedent."""
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-UPD-1", name="Original Legal Name", country="US")

    resp = await client.put(
        f"/suppliers/v1/{supplier_id}",
        json={
            "idempotency_key": idem(), "supplier_id": supplier_id, "expected_version": 1,
            "legal_name": "Renamed Legal Entity Inc.", "role_type": "manufacturer", "country": "CA",
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 200, resp.text

    detail = (await client.get(f"/suppliers/v1/{supplier_id}", headers=auth_headers(pe_token))).json()
    assert detail["legal_name"] == "Renamed Legal Entity Inc."
    assert detail["role_type"] == "manufacturer"
    assert detail["country"] == "CA"
    assert detail["version"] == 2


async def test_update_supplier_rejected_once_qualification_requested(client, seeded, db):
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-UPD-2")
    site_id = await _site_id_for(db, supplier_id)
    await _create_qualification(client, pe_token, supplier_id, site_id)

    resp = await client.put(
        f"/suppliers/v1/{supplier_id}",
        json={
            "idempotency_key": idem(), "supplier_id": supplier_id, "expected_version": 2,
            "legal_name": "Should Not Apply", "role_type": "supplier", "country": None,
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_update_supplier_rejects_duplicate_identity(client, seeded):
    pe_token = await login(client, "process.engineer")
    await _create_supplier(client, pe_token, code="SUP-UPD-3A", name="Collision Target Ltd", country="GB")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-UPD-3B", name="Not Yet Colliding", country="GB")

    resp = await client.put(
        f"/suppliers/v1/{supplier_id}",
        json={
            "idempotency_key": idem(), "supplier_id": supplier_id, "expected_version": 1,
            "legal_name": "Collision Target Ltd", "role_type": "supplier", "country": "GB",
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "DUPLICATE_SUPPLIER_CANDIDATE"


async def test_delete_draft_supplier_succeeds_and_cascades_sites(client, seeded, db):
    async with db.begin():
        await _promote_to_admin(db, seeded, "operator1")
    admin_token = await login(client, "operator1")
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-DEL-1")
    site_id = await _site_id_for(db, supplier_id)
    assert site_id and site_id != "None"

    resp = await client.request(
        "DELETE", f"/suppliers/v1/{supplier_id}",
        json={"idempotency_key": idem(), "supplier_id": supplier_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    get_resp = await client.get(f"/suppliers/v1/{supplier_id}", headers=auth_headers(admin_token))
    assert get_resp.status_code == 404

    remaining_site = await db.get(SupplierSite, site_id)
    assert remaining_site is None


async def test_delete_supplier_requires_platform_administer_not_just_create(client, seeded):
    """Deletion is gated stricter than create/update -- Process Engineer holds supplier.create but not
    platform.administer, same tiering material.delete already established."""
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-DEL-2")

    resp = await client.request(
        "DELETE", f"/suppliers/v1/{supplier_id}",
        json={"idempotency_key": idem(), "supplier_id": supplier_id},
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_delete_supplier_rejected_once_qualification_requested(client, seeded, db):
    async with db.begin():
        await _promote_to_admin(db, seeded, "operator1")
    admin_token = await login(client, "operator1")
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-DEL-3")
    site_id = await _site_id_for(db, supplier_id)
    await _create_qualification(client, pe_token, supplier_id, site_id)

    resp = await client.request(
        "DELETE", f"/suppliers/v1/{supplier_id}",
        json={"idempotency_key": idem(), "supplier_id": supplier_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "INVALID_TRANSITION"


async def test_delete_supplier_blocked_by_material_receipt_reference(client, seeded, db):
    from app.modules.material.models import MaterialReceipt

    async with db.begin():
        await _promote_to_admin(db, seeded, "operator1")
    admin_token = await login(client, "operator1")
    pe_token = await login(client, "process.engineer")
    supplier_id = await _create_supplier(client, pe_token, code="SUP-DEL-4")

    async with db.begin():
        material = Material(site_id=seeded["site_id"], code="MAT-SUP-DEL-4", name="Blocker Material", uom="kg")
        db.add(material)
        await db.flush()
        receipt = MaterialReceipt(
            site_id=seeded["site_id"], receipt_number="RCPT-SUP-DEL-4", material_id=material.id,
            supplier_id=uuid.UUID(supplier_id), received_gross_quantity="10.000000", uom="kg",
            receiver_subject_id=seeded["users"]["process.engineer"].id, state="received", version=1,
        )
        db.add(receipt)

    resp = await client.request(
        "DELETE", f"/suppliers/v1/{supplier_id}",
        json={"idempotency_key": idem(), "supplier_id": supplier_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert "referenced by" in resp.json()["message"]
