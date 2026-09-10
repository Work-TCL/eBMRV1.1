"""SG-146 (remainder, module 3 of 8) — the MIG-FR-004 *migrate/backfill* step for the nine mutable
`materials` schema tables' UOM columns (migration `c5f1a8d3e7b4` added all thirteen, nullable).

Generic over `(model, uom_field, uom_id_field)` rather than nine near-duplicate functions — the module
has too many tables for QC/yield_reconciliation's one-function-per-table shape to stay readable. Only
the nine tables with an UPDATE grant get an entry here; `inventory_transactions`, `weighing_readings`,
`material_consumptions` and `material_returns` have no UPDATE grant (append-only, AG-08 — see each
table's own migration, 0028/0029/0031) and are dual-written at INSERT time only
(`app/modules/material/commands.py::_resolve_uom_id`), never backfilled.

Same chunked/resumable/idempotent shape as `yield_reconciliation`/`qc`'s backfills (MIG-FR-012):
`uom_id_field IS NULL` alone guarantees idempotency; `after_id` only bounds each batch. Additive
linkage only — never rewrites the free-text column or any other regulated field (AG-08); no
signature/audit-event ceremony applies (MIG-FR-013's migration-provenance carve-out).
"""

import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.material.models import (
    DestructionRecord,
    DispensedContainer,
    DispensingOrder,
    InventoryReservation,
    Material,
    MaterialContainer,
    MaterialIssue,
    MaterialLot,
    MaterialReceipt,
)
from app.modules.rules import service as rules_service
from app.mutation.errors import UomUnknownError

# (label, model, free-text field name, id field name)
BACKFILL_TARGETS = [
    ("materials", Material, "uom", "uom_id"),
    ("material_lots", MaterialLot, "uom", "uom_id"),
    ("material_issues", MaterialIssue, "uom", "uom_id"),
    ("material_receipts", MaterialReceipt, "uom", "uom_id"),
    ("material_containers", MaterialContainer, "uom", "uom_id"),
    ("inventory_reservations", InventoryReservation, "uom", "uom_id"),
    ("dispensing_orders", DispensingOrder, "target_uom", "target_uom_id"),
    ("dispensed_containers", DispensedContainer, "uom", "uom_id"),
    ("destruction_records", DestructionRecord, "uom", "uom_id"),
]


@dataclass(frozen=True)
class BackfillResult:
    processed: int
    matched: int
    unmatched: int
    last_id: uuid.UUID | None


async def backfill_table(
    session: AsyncSession,
    model,
    uom_field: str,
    uom_id_field: str,
    *,
    batch_size: int = 500,
    after_id: uuid.UUID | None = None,
) -> BackfillResult:
    id_col = getattr(model, uom_id_field)
    uom_col = getattr(model, uom_field)
    query = select(model).where(id_col.is_(None), uom_col.is_not(None)).order_by(model.id).limit(batch_size)
    if after_id is not None:
        query = query.where(model.id > after_id)
    rows = (await session.execute(query)).scalars().all()

    matched = unmatched = 0
    last_id: uuid.UUID | None = None
    for row in rows:
        try:
            resolved = await rules_service.resolve_uom(session, getattr(row, uom_field))
        except UomUnknownError:
            unmatched += 1
            last_id = row.id
            continue
        setattr(row, uom_id_field, resolved.uom_id)
        matched += 1
        last_id = row.id
    await session.flush()
    return BackfillResult(processed=len(rows), matched=matched, unmatched=unmatched, last_id=last_id)
