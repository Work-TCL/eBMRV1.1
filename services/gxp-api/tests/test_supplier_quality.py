"""WP-04 / Document 18 (SPEC-MAT-001) thin slice: supplier + site master (SUP-FR-001/002/029) ->
qualification request (SUP-FR-003/004/005/013) -> signed approval (SUP-FR-007/009/012), cascading the
supplier's own DRAFT->UNDER_QUALIFICATION->APPROVED lifecycle (Document 18 §5). `approved_supplier_material`
/ `purchase_requisition` / `purchase_order_ref` are out of scope this pass (SG-057)."""

from sqlalchemy import select

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.supplier_quality.models import (
    Supplier,
    SupplierQualification,
    SupplierQualificationEvidence,
    SupplierSite,
)
from app.modules.vault.models import VaultObject
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


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
