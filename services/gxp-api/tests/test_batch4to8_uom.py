"""SG-146 (remainder, modules 4-8 of 8) — dual-write/backfill coverage for `product_master`,
`recipe_master` and `genealogy`. `batch`/`batch_execution` got their dual-write assertions added
directly to their existing E2E happy-path tests (`test_batch_flow.py`/`test_batch_execution.py`) instead
of a new file here, since building a batch needs the full product+recipe dependency chain either way.

Not one test per column — representative coverage per module, same discipline as `test_material_uom.py`.
"""

import uuid
from decimal import Decimal

from app.core.security import hash_password
from app.modules.genealogy import service as genealogy_service
from app.modules.iam.models import User, UserSiteRole
from app.modules.product_master.models import ProductVersion
from app.modules.product_master.uom_backfill import backfill_product_versions
from app.modules.recipe_master.models import RecipeParameter, RecipeVersion
from app.modules.rules.models import UnitOfMeasure
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username):
    user = User(
        username=username, email=f"{username}@example.com", full_name="Test Admin",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))
    return user


# --- product_master ---------------------------------------------------------------------------------


async def test_product_draft_dual_writes_strength_uom_id_when_released(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.pm1")
        db.add(UnitOfMeasure(code="mg-pm1", dimension="MASS", base_unit="mg-pm1", factor=Decimal("1"), precision_dp=4, status="released"))
    token = await login(client, "admin.pm1")

    resp = await client.post(
        "/products/v1/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": "PM-UOM-1", "product_code": "PM-UOM-1",
            "name": "UOM Test Product", "version_no": 1, "site_id": str(seeded["site_id"]),
            "manufacturing_profile_code": "pharma", "strength_value": "5", "strength_uom": "mg-pm1",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    version = await db.get(ProductVersion, uuid.UUID(resp.json()["aggregate_id"]))
    assert version.strength_uom == "mg-pm1"
    assert version.strength_uom_id is not None


async def test_product_draft_rejects_unresolvable_strength_uom(client, seeded, db):
    """Client requirements #2/#3 (2026-09-21): create_draft now hardens strength_uom resolution via
    `_resolve_uom_id_strict` since the UI only ever submits a code drawn from the released list --
    superseding the old best-effort "leaves strength_uom_id null" behavior for this specific, now
    UI-enforced call site."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.pm2")
    token = await login(client, "admin.pm2")

    resp = await client.post(
        "/products/v1/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": "PM-UOM-2", "product_code": "PM-UOM-2",
            "name": "UOM Test Product 2", "version_no": 1, "site_id": str(seeded["site_id"]),
            "manufacturing_profile_code": "pharma", "strength_value": "5", "strength_uom": "not-a-real-unit",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_backfill_product_versions_is_idempotent_and_never_guesses(db, seeded):
    async with db.begin():
        db.add(UnitOfMeasure(code="g-pmbf", dimension="MASS", base_unit="g-pmbf", factor=Decimal("1"), precision_dp=4, status="released"))
        resolvable = ProductVersion(
            product_business_id="PM-UOM-BF", version_no=1, product_code="PM-UOM-BF", name="Backfill Product",
            manufacturing_profile_code="pharma", site_id=seeded["site_id"], strength_uom="g-pmbf",
        )
        unresolvable = ProductVersion(
            product_business_id="PM-UOM-BF-2", version_no=1, product_code="PM-UOM-BF-2", name="Unresolvable Product",
            manufacturing_profile_code="pharma", site_id=seeded["site_id"], strength_uom="not-a-real-unit",
        )
        db.add_all([resolvable, unresolvable])
        await db.flush()
        resolvable_id, unresolvable_id = resolvable.id, unresolvable.id

    async with db.begin():
        result = await backfill_product_versions(db, batch_size=500)
    assert result.matched >= 1
    assert result.unmatched >= 1

    assert (await db.get(ProductVersion, resolvable_id)).strength_uom_id is not None
    assert (await db.get(ProductVersion, unresolvable_id)).strength_uom_id is None

    async with db.begin():
        second = await backfill_product_versions(db, batch_size=500)
    assert second.processed == second.unmatched


# --- recipe_master -----------------------------------------------------------------------------------


async def _make_product_version(client, admin_token, site_id, business_id):
    resp = await client.post(
        "/products/v1/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": business_id, "product_code": business_id,
            "name": "Recipe UOM Test Product", "version_no": 1, "site_id": str(site_id),
            "manufacturing_profile_code": "pharma",
        },
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    return resp.json()["aggregate_id"]


async def test_recipe_draft_dual_writes_batch_size_and_parameter_uom_ids(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.rm1")
        db.add(UnitOfMeasure(code="kg-rm1", dimension="MASS", base_unit="kg-rm1", factor=Decimal("1"), precision_dp=4, status="released"))
    token = await login(client, "admin.rm1")
    product_version_id = await _make_product_version(client, token, seeded["site_id"], "RM-UOM-1")

    resp = await client.post(
        "/recipes/v2/drafts",
        json={
            "idempotency_key": idem(), "product_business_id": "RM-UOM-1", "recipe_code": "RCP-UOM-1", "version_no": 1,
            "product_version_id": product_version_id, "site_id": str(seeded["site_id"]),
            "manufacturing_profile_code": "pharma", "batch_size_value": "100", "batch_size_uom": "kg-rm1",
            "sections": [{"stable_section_code": "SEC-1", "name": "Fill", "sequence": 1}],
            "steps": [{
                "stable_step_code": "STEP-A", "section_code": "SEC-1", "step_type": "weigh", "sequence_hint": 1,
                "parameters": [{"parameter_code": "TARGET-WEIGHT", "data_type": "decimal", "uom": "kg-rm1", "source_type": "manual"}],
            }],
            "dependencies": [],
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    recipe_version_id = uuid.UUID(resp.json()["aggregate_id"])

    version = await db.get(RecipeVersion, recipe_version_id)
    assert version.batch_size_uom == "kg-rm1"
    assert version.batch_size_uom_id is not None

    from sqlalchemy import select

    from app.modules.recipe_master.models import RecipeStep

    steps = (await db.execute(select(RecipeStep).where(RecipeStep.recipe_version_id == recipe_version_id))).scalars().all()
    step_ids = [s.id for s in steps]
    params = (await db.execute(select(RecipeParameter).where(RecipeParameter.step_id.in_(step_ids)))).scalars().all()
    assert len(params) == 1
    assert params[0].uom == "kg-rm1"
    assert params[0].uom_id is not None


# --- genealogy -----------------------------------------------------------------------------------


async def test_genealogy_edge_dual_writes_uom_id_when_released(db, seeded):
    async with db.begin():
        admin = await _make_admin(db, seeded, "admin.gen1")
        db.add(UnitOfMeasure(code="kg-gen1", dimension="MASS", base_unit="kg-gen1", factor=Decimal("1"), precision_dp=4, status="released"))

    async with db.begin():
        mat = await genealogy_service.create_node(
            db, site_id=seeded["site_id"], node_type="material_lot", business_ref="MAT-UOM-1", actor_user_id=admin.id
        )
        batch = await genealogy_service.create_node(
            db, site_id=seeded["site_id"], node_type="drug_batch", business_ref="BATCH-UOM-1", actor_user_id=admin.id
        )
        edge = await genealogy_service.create_edge(
            db, from_node_id=mat.id, to_node_id=batch.id, edge_type="CONSUMED_IN",
            quantity=Decimal("10.5"), uom="kg-gen1", actor_user_id=admin.id,
        )
    assert edge.uom == "kg-gen1"
    assert edge.uom_id is not None
