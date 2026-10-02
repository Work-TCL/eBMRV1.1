"""REMEDIATION_R1 FIX 2 — tenancy is single-tenant-per-deployment (ADR-0006 Option A). Isolation is
transitive (row -> site -> organization) rather than row-level, so what actually needs proving is: (1)
an actor scoped to one organization's site cannot act on a record belonging to another organization's
site, and (2) the startup guard that keeps the single-tenant assumption from silently rotting actually
fires when a second organization appears.

Ported off the retired `app.modules.batch`/`product`/`recipe` legacy trio (SG-044/SG-173 Phase 4/5,
ADR-0013) onto the authoritative `product_master`/`recipe_master`/`batch_execution` modules -- same
RBAC-isolation guarantee (UserSiteRole is scoped to a specific site, never inherited across
organizations), same assertion, different (current) endpoints.

SG-213 (found while porting, 2026-09-23): `batch_execution.router`'s step-start endpoint (and 19 of its
other 20 non-create endpoints) calls `evaluate_policy(..., site_id=None)` -- "does the actor hold this
role at ANY site", not "at this batch's site" -- unlike the retired legacy `/batches` router, which was
site-scoped. `test_cross_organization_access_denied` reproduces this deterministically (200, not the
expected 403) and is left `xfail(strict=True)` citing SG-213 rather than silently weakened to match
today's behaviour or deleted. Whether this is a real defect or an intended platform-wide-by-role
authorization model (ADR-0006) is a project-owner decision, not something this pass can resolve
unilaterally -- see SG-213 for the full analysis (confirmed as a platform-wide pattern across ~24 modules,
not batch_execution-specific).
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.db import SessionLocal, assert_single_organization
from app.core.security import hash_password
from app.modules.batch_execution.models import Batch
from app.modules.iam.models import Organization, Role, Site, User, UserSiteRole
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def test_assert_single_organization_raises_on_second_organization(db):
    async with db.begin():
        db.add(Organization(name="Org A"))
        db.add(Organization(name="Org B"))
    with pytest.raises(RuntimeError, match="Single-tenant deployment"):
        await assert_single_organization(db)


@pytest.mark.xfail(
    reason="SG-213: batch_execution's step-start endpoint authorizes via evaluate_policy(site_id=None) -- "
    "any actor holding the role at ANY site can act on ANY site's batch. Real, deterministic, not a flake. "
    "Left failing/xfail(strict) rather than weakened or deleted -- see docs/generated/18_SPEC_GAPS.md SG-213.",
    strict=True,
)
async def test_cross_organization_access_denied(client, seeded, db):
    """An actor holding a role only at org A's site cannot act on a batch belonging to org B's site —
    enforced by the existing RBAC check (UserSiteRole is scoped to a specific site, never inherited
    across organizations), which is what "isolation by deployment boundary" actually relies on.
    """
    site_a = seeded["site_id"]
    async with db.begin():
        admin_user = User(
            username="admin.tenancy", email="admin.tenancy@example.com", full_name="Tenancy Admin",
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(admin_user)
        await db.flush()
        db.add(UserSiteRole(user_id=admin_user.id, site_id=site_a, role_id=seeded["roles"]["Admin"].id))
        db.add(SignaturePolicy(record_type="product_version", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="recipe_version", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, "admin.tenancy")

    resp = await client.post(
        "/products/v1/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": "TENPRD-1", "product_code": "TENPRD-1",
            "name": "Tenancy Test Product", "version_no": 1, "site_id": str(site_a),
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
            "idempotency_key": idem(), "product_business_id": "TENPRD-1", "recipe_code": "TENRCP-1",
            "version_no": 1, "product_version_id": product_version_id, "site_id": str(site_a),
            "manufacturing_profile_code": "pharma",
            "sections": [{"stable_section_code": "SEC-1", "name": "Dispensing", "sequence": 1}],
            "steps": [{"stable_step_code": "STEP-A", "section_code": "SEC-1", "step_type": "weigh", "sequence_hint": 1}],
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

    resp = await client.post(
        "/batches/v1",
        json={
            "idempotency_key": idem(), "site_id": str(site_a), "batch_number": "B-TENANCY-A",
            "product_version_id": product_version_id, "recipe_version_id": recipe_version_id,
            "target_qty": "10.0", "target_uom": "kg",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    batch_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/batches/v1/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    resp = await client.post(
        f"/batches/v1/{batch_id}/start",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 2},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    view = (await client.get(f"/batches/v1/{batch_id}/execution-view", headers=auth_headers(admin_token))).json()
    ready_step = next(s for s in view["steps"] if s["state"] == "ready")

    # A second organization/site/operator, holding no role anywhere near org A's site.
    async with db.begin():
        org_b = Organization(name="Org B")
        db.add(org_b)
        await db.flush()
        site_b = Site(organization_id=org_b.id, code="T2", name="Test Site B")
        db.add(site_b)
        await db.flush()
        role_b = (await db.execute(select(Role).where(Role.name == "Operator"))).scalar_one()
        user_b = User(
            username="operator.orgb",
            email="operator.orgb@example.com",
            full_name="Operator Org B",
            password_hash=hash_password(DEMO_PASSWORD),
            status="active",
        )
        db.add(user_b)
        await db.flush()
        db.add(UserSiteRole(user_id=user_b.id, site_id=site_b.id, role_id=role_b.id))

    org_b_token = await login(client, "operator.orgb")
    resp = await client.post(
        f"/batches/v1/{batch_id}/steps/{ready_step['step_id']}/start",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "step_id": ready_step["step_id"],
            "expected_version": ready_step["version"],
        },
        headers=auth_headers(org_b_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"

    async with SessionLocal() as fresh:
        batch = await fresh.get(Batch, uuid.UUID(batch_id))
        assert batch.version == 3  # unchanged — org B's actor never touched it (create + issue + start)
