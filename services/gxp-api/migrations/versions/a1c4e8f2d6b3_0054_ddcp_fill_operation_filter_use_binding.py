"""0054_ddcp_fill_operation_filter_use_binding

Revision ID: a1c4e8f2d6b3
Revises: b7d3e9a4c1f6
Create Date: 2026-08-29 00:00:00.000000

WP-08 (Document 54, SPEC-DDCP-001, PFS-FR-008) — "If process uses sterile filtration, bind filter
lot/serial, pre/post integrity status, filtration parameters and evidence." `complete_filling_stage()`
already validates an optional `filter_use_id` against Document 42's `sterile_filter_uses` (via
`sterilization_commands.get_item_status`) before this migration, but never persisted the reference --
there was nothing to read back for a review/genealogy composition. Document 112's literal DDL for
`fill_operation` has no `filter_use_id` column; adding one here is the same class of additive,
non-destructive deviation SG-148 already recorded for `site_id` on all nine DDCP tables (see
docs/generated/18_SPEC_GAPS.md SG-148) -- filling in a real requirement the approved DDL omitted, not
reinterpreting anything Document 112 does specify. Nullable, no backfill needed (no prior row could have
had this reference), no data-loss risk.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1c4e8f2d6b3'
down_revision: Union[str, Sequence[str], None] = 'b7d3e9a4c1f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('fill_operation', sa.Column('filter_use_id', sa.UUID(), nullable=True), schema='ddcp')
    op.create_foreign_key(
        'fk_fill_operation_filter_use_id', 'fill_operation', 'sterile_filter_uses', ['filter_use_id'], ['id'],
        source_schema='ddcp', referent_schema='equipment',
    )


def downgrade() -> None:
    op.drop_constraint('fk_fill_operation_filter_use_id', 'fill_operation', schema='ddcp', type_='foreignkey')
    op.drop_column('fill_operation', 'filter_use_id', schema='ddcp')
