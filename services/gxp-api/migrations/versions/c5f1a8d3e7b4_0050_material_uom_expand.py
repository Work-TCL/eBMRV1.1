"""0050_material_uom_expand

Revision ID: c5f1a8d3e7b4
Revises: b2e7f4a9c3d6
Create Date: 2026-08-27 00:00:00.000000

SG-146 (remainder, module 3 of 8) — the MIG-FR-004 *expand* step for Document 19/20/21/22's thirteen
free-text UOM columns, same pattern `yield_reconciliation` (migration `a4d9e6c2f8b1`) and QC (migration
`b2e7f4a9c3d6`) established: a nullable `*_id` FK to `rules.gxp_uom.uom_id`, alongside the existing
free-text column (unchanged, still authoritative). No contract step attempted.

Grant classification decided per table against the actual per-table GRANT statements already in this
schema's own migration history (`221dc58877f5` 0004's schema-wide blanket UPDATE grant for the four
original tables, then `35fca517ebb6` 0027 / `8f1c3d5a7b2e` 0028 / `2c6a9e4f1b7d` 0029 /
`bb7e61b309ce` 0031's per-table splits for everything added later — each of those migrations already
documents its own append-only-vs-mutable reasoning against `app/modules/material/commands.py`) —
**not re-derived or guessed here**:

- Mutable (UPDATE granted) — dual-write AND a real chunked/resumable backfill, same as
  `yield_reconciliation`'s tables: `materials`, `material_lots`, `material_issues`,
  `material_receipts`, `material_containers`, `inventory_reservations`, `dispensing_orders`,
  `dispensed_containers`, `destruction_records`.
- Append-only (no UPDATE grant, AG-08) — dual-write only, same as `qc_test_definition`/`qc_result`:
  `inventory_transactions`, `weighing_readings`, `material_consumptions`, `material_returns`.

`app/modules/material/commands.py` dual-writes the new column at every one of this module's ~25 row-
creation sites via a single shared `_resolve_uom_id()` helper. Backfill for the nine mutable tables is
`app/modules/material/uom_backfill.py` (+ CLI `scripts/backfill_material_uom.py`), generic over
(model, uom_field, uom_id_field) rather than nine near-duplicate functions.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5f1a8d3e7b4'
down_revision: Union[str, Sequence[str], None] = 'b2e7f4a9c3d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, id_column, fk_name)
_COLUMNS = [
    ('materials', 'uom_id', 'fk_materials_uom_id'),
    ('material_lots', 'uom_id', 'fk_material_lots_uom_id'),
    ('material_issues', 'uom_id', 'fk_material_issues_uom_id'),
    ('material_receipts', 'uom_id', 'fk_material_receipts_uom_id'),
    ('material_containers', 'uom_id', 'fk_material_containers_uom_id'),
    ('inventory_reservations', 'uom_id', 'fk_inventory_reservations_uom_id'),
    ('dispensing_orders', 'target_uom_id', 'fk_dispensing_orders_target_uom_id'),
    ('dispensed_containers', 'uom_id', 'fk_dispensed_containers_uom_id'),
    ('destruction_records', 'uom_id', 'fk_destruction_records_uom_id'),
    ('inventory_transactions', 'uom_id', 'fk_inventory_transactions_uom_id'),
    ('weighing_readings', 'uom_id', 'fk_weighing_readings_uom_id'),
    ('material_consumptions', 'uom_id', 'fk_material_consumptions_uom_id'),
    ('material_returns', 'uom_id', 'fk_material_returns_uom_id'),
]


def upgrade() -> None:
    for table, column, fk_name in _COLUMNS:
        op.add_column(table, sa.Column(column, sa.UUID(), nullable=True), schema='materials')
        op.create_foreign_key(
            fk_name, table, 'gxp_uom', [column], ['uom_id'], source_schema='materials', referent_schema='rules',
        )


def downgrade() -> None:
    for table, column, fk_name in reversed(_COLUMNS):
        op.drop_constraint(fk_name, table, schema='materials', type_='foreignkey')
        op.drop_column(table, column, schema='materials')
