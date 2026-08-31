"""0048_yield_reconciliation_uom_expand

Revision ID: a4d9e6c2f8b1
Revises: f3a8c1e5b7d2
Create Date: 2026-08-27 00:00:00.000000

SG-146 (remainder) — the MIG-FR-004 *expand* step of migrating `ebmr.manufacturing_calculations.uom`/
`ebmr.reconciliation_records.uom` off free text and onto the Document 110 §3 controlled UOM master.

Adds a nullable `uom_id` FK to `rules.gxp_uom.uom_id` on both tables, alongside the existing free-text
`uom` string column — additive, no rewrite, no backfill in this migration (AG-08). `app/modules/
yield_reconciliation/commands.py` now dual-writes `uom_id` on every new row where `uom` resolves against
a *released* UOM code (best-effort: an unresolved code leaves `uom_id` NULL and the free-text column
stays authoritative, exactly the expand-phase contract — no existing caller is broken by an unseeded
UOM master). `uom_id` references a specific released UOM *version* (the row's primary key), not a
floating code, matching the "freeze the exact released reference" discipline `VLT-FR-006`/`VLT-FR-007`
already apply to a batch's recipe/product/rule references.

Per MIG-FR-004, at least two releases must separate this expand step from a future contract step that
drops the `uom` column — not attempted here. Backfilling existing rows is a separate, idempotent,
resumable operation (`app/modules/yield_reconciliation/uom_backfill.py`), not part of this migration,
because it depends on UOM master data that does not yet exist in this environment (SG-146: no master
data is seeded as part of any migration — a specific UOM/factor is a content decision, not a schema one).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a4d9e6c2f8b1'
down_revision: Union[str, Sequence[str], None] = 'f3a8c1e5b7d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'manufacturing_calculations',
        sa.Column('uom_id', sa.UUID(), nullable=True),
        schema='ebmr',
    )
    op.create_foreign_key(
        'fk_manufacturing_calculations_uom_id', 'manufacturing_calculations', 'gxp_uom',
        ['uom_id'], ['uom_id'], source_schema='ebmr', referent_schema='rules',
    )
    op.add_column(
        'reconciliation_records',
        sa.Column('uom_id', sa.UUID(), nullable=True),
        schema='ebmr',
    )
    op.create_foreign_key(
        'fk_reconciliation_records_uom_id', 'reconciliation_records', 'gxp_uom',
        ['uom_id'], ['uom_id'], source_schema='ebmr', referent_schema='rules',
    )


def downgrade() -> None:
    op.drop_constraint('fk_reconciliation_records_uom_id', 'reconciliation_records', schema='ebmr', type_='foreignkey')
    op.drop_column('reconciliation_records', 'uom_id', schema='ebmr')
    op.drop_constraint('fk_manufacturing_calculations_uom_id', 'manufacturing_calculations', schema='ebmr', type_='foreignkey')
    op.drop_column('manufacturing_calculations', 'uom_id', schema='ebmr')
