"""SG-146 (remainder, module 3 of 8) — the `material` module's UOM expand step. Same pattern
`test_yield_reconciliation.py`/`test_qc_uom.py` establish, applied to the generic
`app.modules.material.uom_backfill.backfill_table()` covering nine mutable tables.

Not one test per table (25 write sites across 13 tables would be excessive) — `Material`/`MaterialLot`
cover the dual-write path (representative of the "fresh caller-supplied uom" and "copied from an
already-resolved entity" cases respectively), and the generic backfill function is exercised across two
different models to prove it is genuinely generic, not table-specific.
"""

import uuid
from decimal import Decimal

from app.modules.material.models import Material, MaterialLot
from app.modules.material.uom_backfill import backfill_table
from app.modules.rules.models import UnitOfMeasure
from tests.conftest import auth_headers, idem, login
from tests.test_material_flow import _create_material, _receive_lot


async def test_create_material_dual_writes_uom_id_when_a_released_uom_resolves(client, seeded, db):
    async with db.begin():
        db.add(UnitOfMeasure(code="kg-mat1", dimension="MASS", base_unit="kg-mat1", factor=Decimal("1"), precision_dp=4, status="released"))
    op_token = await login(client, "operator1")

    material_id = await _create_material(client, seeded["site_id"], code="RM-UOM-1", uom="kg-mat1")
    material = await db.get(Material, uuid.UUID(material_id))
    assert material.uom == "kg-mat1"
    assert material.uom_id is not None


async def test_create_material_rejects_unresolvable_uom(client, seeded, db):
    """Client requirements #2/#3 (2026-09-21): create_material now hardens uom resolution via
    `_resolve_uom_id_strict` since the UI only ever submits a code drawn from the released list --
    superseding the old best-effort "leaves uom_id null" behavior for this specific, now UI-enforced
    call site (other, purely internal `_resolve_uom_id` call sites in this module are unaffected)."""
    # material.create is Process Engineer/Admin-only (RBAC gap closure, 2026-09-18) -- author as
    # process.engineer, same as the _create_material helper this file's other tests use.
    pe_token = await login(client, "process.engineer")

    resp = await client.post(
        "/materials",
        json={
            "idempotency_key": idem(), "site_id": str(seeded["site_id"]), "code": "RM-UOM-2",
            "name": "Unresolvable UOM Material", "uom": "not-a-real-unit",
        },
        headers=auth_headers(pe_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_receive_lot_dual_writes_uom_id_when_a_released_uom_resolves(client, seeded, db):
    """MaterialLot.uom is a fresh caller-supplied value on ReceiveMaterialLotCommand (not copied from
    another entity), same as Material.uom."""
    async with db.begin():
        db.add(UnitOfMeasure(code="g-mat3", dimension="MASS", base_unit="g-mat3", factor=Decimal("1"), precision_dp=4, status="released"))
    op_token = await login(client, "operator1")
    material_id = await _create_material(client, seeded["site_id"], code="RM-UOM-3")

    resp = await client.post(
        f"/materials/{material_id}/lots",
        json={
            "idempotency_key": idem(), "material_id": material_id, "site_id": str(seeded["site_id"]),
            "internal_lot": "LOT-UOM-3", "received_quantity": "10.000000", "uom": "g-mat3",
        },
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 200, resp.text
    lot = await db.get(MaterialLot, uuid.UUID(resp.json()["aggregate_id"]))
    assert lot.uom == "g-mat3"
    assert lot.uom_id is not None


async def test_backfill_table_is_generic_across_models_idempotent_and_never_guesses(seeded, db):
    async with db.begin():
        db.add(UnitOfMeasure(code="mL-mat4", dimension="VOLUME", base_unit="mL-mat4", factor=Decimal("1"), precision_dp=4, status="released"))

    # A Material row created before the UOM existed (simulated by inserting directly with the
    # free-text column set and no dual-write, matching a pre-existing regulated row).
    async with db.begin():
        pre_existing = Material(
            site_id=seeded["site_id"], code="RM-UOM-BF", name="Backfill Material", uom="mL-mat4", version=1,
        )
        unresolvable = Material(
            site_id=seeded["site_id"], code="RM-UOM-BF-2", name="Unresolvable Material", uom="not-a-real-unit", version=1,
        )
        db.add_all([pre_existing, unresolvable])
        await db.flush()
        pre_existing_id, unresolvable_id = pre_existing.id, unresolvable.id

    async with db.begin():
        result = await backfill_table(db, Material, "uom", "uom_id", batch_size=500)
    assert result.matched >= 1
    assert result.unmatched >= 1

    matched_row = await db.get(Material, pre_existing_id)
    unmatched_row = await db.get(Material, unresolvable_id)
    assert matched_row.uom_id is not None
    assert unmatched_row.uom_id is None

    # Idempotent: a second pass only revisits the still-unresolved row.
    async with db.begin():
        second = await backfill_table(db, Material, "uom", "uom_id", batch_size=500)
    assert second.processed == second.unmatched

    # Genericity: the same function against a different model (MaterialLot) with no fixture data
    # processes zero rows cleanly rather than erroring on a different schema shape.
    async with db.begin():
        empty = await backfill_table(db, MaterialLot, "uom", "uom_id", batch_size=500)
    assert empty.processed == 0
