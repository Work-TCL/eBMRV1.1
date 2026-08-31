"""REMEDIATION_R1 FIX 2 — tenancy is single-tenant-per-deployment (ADR-0006 Option A). Isolation is
transitive (row -> site -> organization) rather than row-level, so what actually needs proving is: (1)
an actor scoped to one organization's site cannot act on a record belonging to another organization's
site, and (2) the startup guard that keeps the single-tenant assumption from silently rotting actually
fires when a second organization appears.
"""

import uuid

import pytest
from sqlalchemy import select

from app.core.db import SessionLocal, assert_single_organization
from app.core.security import hash_password
from app.modules.batch.models import Batch
from app.modules.iam.models import Organization, Role, Site, User, UserSiteRole
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def test_assert_single_organization_raises_on_second_organization(db):
    async with db.begin():
        db.add(Organization(name="Org A"))
        db.add(Organization(name="Org B"))
    with pytest.raises(RuntimeError, match="Single-tenant deployment"):
        await assert_single_organization(db)


async def test_cross_organization_access_denied(client, seeded, db):
    """An actor holding a role only at org A's site cannot act on a batch belonging to org B's site —
    enforced by the existing RBAC check (UserSiteRole is scoped to a specific site, never inherited
    across organizations), which is what "isolation by deployment boundary" actually relies on.
    """
    site_a = seeded["site_id"]
    op_token = await login(client, "operator1")

    resp = await client.post(
        "/products",
        json={"idempotency_key": idem(), "site_id": str(site_a), "code": "P-TENANCY", "name": "Tenancy Test"},
        headers=auth_headers(op_token),
    )
    product_id = resp.json()["aggregate_id"]
    resp = await client.post(
        "/recipes",
        json={
            "idempotency_key": idem(),
            "product_id": product_id,
            "version": 1,
            "steps": [{"step_number": 1, "name": "Step 1", "requires_signature": False}],
        },
        headers=auth_headers(op_token),
    )
    recipe_id = resp.json()["aggregate_id"]
    resp = await client.post(
        "/batches",
        json={
            "idempotency_key": idem(),
            "site_id": str(site_a),
            "product_id": product_id,
            "recipe_id": recipe_id,
            "recipe_version": 1,
            "batch_number": "B-TENANCY-A",
            "target_quantity": "10.000000",
            "uom": "kg",
        },
        headers=auth_headers(op_token),
    )
    batch_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/batches/{batch_id}/issue",
        json={"idempotency_key": idem(), "batch_id": batch_id, "expected_version": 1},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    detail = (await client.get(f"/batches/{batch_id}")).json()
    (step1,) = detail["steps"]

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
        f"/batches/{batch_id}/steps/{step1['batch_step_id']}/start",
        json={
            "idempotency_key": idem(),
            "batch_id": batch_id,
            "expected_version": 2,
            "batch_step_id": step1["batch_step_id"],
        },
        headers=auth_headers(org_b_token),
    )
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"

    async with SessionLocal() as fresh:
        batch = await fresh.get(Batch, uuid.UUID(batch_id))
        assert batch.version == 2  # unchanged — org B's actor never touched it
