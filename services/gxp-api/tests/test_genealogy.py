"""Document 13 (SPEC-EBMR-004) -- the graph engine: node/edge creation (called directly, standing in for
the domain-event consumer Document 13 SS8 describes -- no producer exists yet, SG-052), correction,
consistency/cycle rules, and the 5 read-only query APIs. New module. Everything needing a third entity
this document's own 2-entity data model doesn't define (impact assessments, exports) is out of scope
this pass -- SG-051.
"""

import uuid
from decimal import Decimal

from app.core.security import hash_password
from app.modules.genealogy import service as genealogy_service
from app.modules.iam.models import User, UserSiteRole
from app.mutation.errors import GxPError
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username="admin.genealogy"):
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


async def _build_chain(db, seeded, admin, *, tag):
    """MAT-LOT -> CONSUMED_IN -> BATCH -> FILLED_INTO -> DEVICE_UNIT -> ASSEMBLED_INTO -> COMBO_LOT"""
    async with db.begin():
        mat = await genealogy_service.create_node(
            db, site_id=seeded["site_id"], node_type="material_lot", business_ref=f"MAT-{tag}", actor_user_id=admin.id
        )
        batch = await genealogy_service.create_node(
            db, site_id=seeded["site_id"], node_type="drug_batch", business_ref=f"BATCH-{tag}", actor_user_id=admin.id
        )
        unit = await genealogy_service.create_node(
            db, site_id=seeded["site_id"], node_type="device_unit", business_ref=f"SN-{tag}", actor_user_id=admin.id
        )
        combo = await genealogy_service.create_node(
            db, site_id=seeded["site_id"], node_type="combination_product_lot", business_ref=f"COMBO-{tag}", actor_user_id=admin.id
        )
        await genealogy_service.create_edge(
            db, from_node_id=mat.id, to_node_id=batch.id, edge_type="CONSUMED_IN", quantity=Decimal("10.5"), uom="kg", actor_user_id=admin.id
        )
        await genealogy_service.create_edge(db, from_node_id=batch.id, to_node_id=unit.id, edge_type="FILLED_INTO", actor_user_id=admin.id)
        edge3 = await genealogy_service.create_edge(
            db, from_node_id=unit.id, to_node_id=combo.id, edge_type="ASSEMBLED_INTO", actor_user_id=admin.id
        )
    return {"mat": mat, "batch": batch, "unit": unit, "combo": combo, "edge3": edge3}


async def test_unauthorized_without_token_rejected(client):
    resp = await client.get("/genealogy/v1/nodes/lookup", params={"site_id": str(uuid.uuid4())})
    assert resp.status_code == 401


async def test_lookup_requires_permission(client, seeded, db):
    # Every seeded role already grants genealogy.view (it's a broad read permission) -- the simplest
    # negative case is a user with no site role at all.
    async with db.begin():
        bare = User(
            username="bare.genealogy", email="bare.genealogy@example.com", full_name="Bare",
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(bare)
    token = await login(client, "bare.genealogy")
    resp = await client.get("/genealogy/v1/nodes/lookup", params={"site_id": str(seeded["site_id"])}, headers=auth_headers(token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_create_traverse_and_lookup(client, seeded, db):
    async with db.begin():
        admin = await _make_admin(db, seeded, "admin.genealogy2")
    admin_token = await login(client, "admin.genealogy2")
    chain = await _build_chain(db, seeded, admin, tag="2")

    resp = await client.get(
        "/genealogy/v1/nodes/lookup",
        params={"site_id": str(seeded["site_id"]), "business_ref": "BATCH-2"},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert len(resp.json()) == 1
    assert resp.json()[0]["node_type"] == "drug_batch"

    resp = await client.get(f"/genealogy/v1/nodes/{chain['unit'].id}/ancestors", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    ancestor_refs = {n["business_ref"] for n in resp.json()["nodes"]}
    assert ancestor_refs == {"BATCH-2", "MAT-2"}

    resp = await client.get(f"/genealogy/v1/nodes/{chain['batch'].id}/descendants", headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    descendant_refs = {n["business_ref"] for n in resp.json()["nodes"]}
    assert descendant_refs == {"SN-2", "COMBO-2"}

    resp = await client.get(
        "/genealogy/v1/serial/SN-2/full-trace", params={"site_id": str(seeded["site_id"])}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert {n["business_ref"] for n in body["ancestors"]["nodes"]} == {"BATCH-2", "MAT-2"}
    assert {n["business_ref"] for n in body["descendants"]["nodes"]} == {"COMBO-2"}

    resp = await client.get(
        "/genealogy/v1/material-lot/MAT-2/affected-products", params={"site_id": str(seeded["site_id"])}, headers=auth_headers(admin_token)
    )
    assert resp.status_code == 200, resp.text
    affected_refs = {n["business_ref"] for n in resp.json()["affected_products"]}
    assert affected_refs == {"SN-2", "COMBO-2"}  # both are FINAL_PRODUCT_NODE_TYPES


async def test_self_loop_edge_rejected(db, seeded):
    async with db.begin():
        admin = await _make_admin(db, seeded, "admin.genealogy3")
    async with db.begin():
        node = await genealogy_service.create_node(
            db, site_id=seeded["site_id"], node_type="material_lot", business_ref="SELF-3", actor_user_id=admin.id
        )
    try:
        async with db.begin():
            await genealogy_service.create_edge(
                db, from_node_id=node.id, to_node_id=node.id, edge_type="DERIVED_FROM", actor_user_id=admin.id
            )
        assert False, "expected ValidationFailedError"
    except GxPError as exc:
        assert exc.code == "VALIDATION_FAILED"


async def test_cycle_edge_rejected(db, seeded):
    async with db.begin():
        admin = await _make_admin(db, seeded, "admin.genealogy4")
    async with db.begin():
        a = await genealogy_service.create_node(db, site_id=seeded["site_id"], node_type="material_lot", business_ref="A-4", actor_user_id=admin.id)
        b = await genealogy_service.create_node(db, site_id=seeded["site_id"], node_type="drug_batch", business_ref="B-4", actor_user_id=admin.id)
        await genealogy_service.create_edge(db, from_node_id=a.id, to_node_id=b.id, edge_type="CONSUMED_IN", actor_user_id=admin.id)
    try:
        async with db.begin():
            # B is already a descendant of A -- linking B back to A would close a cycle.
            await genealogy_service.create_edge(db, from_node_id=b.id, to_node_id=a.id, edge_type="DERIVED_FROM", actor_user_id=admin.id)
        assert False, "expected ValidationFailedError"
    except GxPError as exc:
        assert exc.code == "VALIDATION_FAILED"


async def test_duplicate_edge_rejected(db, seeded):
    async with db.begin():
        admin = await _make_admin(db, seeded, "admin.genealogy5")
    async with db.begin():
        a = await genealogy_service.create_node(db, site_id=seeded["site_id"], node_type="material_lot", business_ref="A-5", actor_user_id=admin.id)
        b = await genealogy_service.create_node(db, site_id=seeded["site_id"], node_type="drug_batch", business_ref="B-5", actor_user_id=admin.id)
        await genealogy_service.create_edge(db, from_node_id=a.id, to_node_id=b.id, edge_type="CONSUMED_IN", actor_user_id=admin.id)
    try:
        async with db.begin():
            await genealogy_service.create_edge(db, from_node_id=a.id, to_node_id=b.id, edge_type="CONSUMED_IN", actor_user_id=admin.id)
        assert False, "expected ValidationFailedError"
    except GxPError as exc:
        assert exc.code == "VALIDATION_FAILED"


async def test_edge_idempotent_by_source_event_id(db, seeded):
    async with db.begin():
        admin = await _make_admin(db, seeded, "admin.genealogy6")
    source_event_id = uuid.uuid4()
    async with db.begin():
        a = await genealogy_service.create_node(db, site_id=seeded["site_id"], node_type="material_lot", business_ref="A-6", actor_user_id=admin.id)
        b = await genealogy_service.create_node(db, site_id=seeded["site_id"], node_type="drug_batch", business_ref="B-6", actor_user_id=admin.id)
        edge1 = await genealogy_service.create_edge(
            db, from_node_id=a.id, to_node_id=b.id, edge_type="CONSUMED_IN", source_event_id=source_event_id, actor_user_id=admin.id
        )
    async with db.begin():
        edge2 = await genealogy_service.create_edge(
            db, from_node_id=a.id, to_node_id=b.id, edge_type="CONSUMED_IN", source_event_id=source_event_id, actor_user_id=admin.id
        )
    assert edge1.id == edge2.id


async def test_correct_edge_supersedes_original(client, seeded, db):
    async with db.begin():
        admin = await _make_admin(db, seeded, "admin.genealogy7")
    admin_token = await login(client, "admin.genealogy7")
    async with db.begin():
        a = await genealogy_service.create_node(db, site_id=seeded["site_id"], node_type="material_lot", business_ref="A-7", actor_user_id=admin.id)
        wrong_b = await genealogy_service.create_node(db, site_id=seeded["site_id"], node_type="drug_batch", business_ref="WRONG-7", actor_user_id=admin.id)
        right_b = await genealogy_service.create_node(db, site_id=seeded["site_id"], node_type="drug_batch", business_ref="RIGHT-7", actor_user_id=admin.id)
        wrong_edge = await genealogy_service.create_edge(db, from_node_id=a.id, to_node_id=wrong_b.id, edge_type="CONSUMED_IN", actor_user_id=admin.id)

    async with db.begin():
        correction = await genealogy_service.correct_edge(
            db,
            edge_id=wrong_edge.id,
            correct_from_node_id=a.id,
            correct_to_node_id=right_b.id,
            correct_edge_type="CONSUMED_IN",
            reason="wrong drug batch recorded",
            actor_user_id=admin.id,
        )
    assert correction.supersedes_edge_id == wrong_edge.id

    resp = await client.get(f"/genealogy/v1/nodes/{a.id}/descendants", headers=auth_headers(admin_token))
    descendant_refs = {n["business_ref"] for n in resp.json()["nodes"]}
    assert descendant_refs == {"RIGHT-7"}  # the superseded edge to WRONG-7 no longer contributes
