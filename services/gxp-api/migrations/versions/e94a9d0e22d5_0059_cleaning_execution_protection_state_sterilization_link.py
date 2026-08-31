"""0059_cleaning_execution_protection_state_sterilization_link

Revision ID: e94a9d0e22d5
Revises: f5a8b1c4d7e0
Create Date: 2026-08-30 00:00:00.000000

Document 39 (SPEC-EQP-002) — CLN-FR-014/025 (SG-114 follow-up). Adds two columns to the already-owned
`equipment.cleaning_executions` table:

- `protection_state` (JSONB, nullable): CLN-FR-014's cover/closure/storage state, captured as recorded --
  not an enforced/gated enum, no controlled vocabulary exists for it in any approved baseline (same
  "captured, not enumerated" precedent as `equipment_areas.area_type`).
- `sterilization_cycle_id` (UUID, nullable, FK to `equipment.process_cycles`): CLN-FR-025's link to a
  Document 42 CIP/SIP process cycle that may evidence part of this cleaning record "through a validated
  interface" -- a reference only; `verify_cleaning()`'s own signature step still independently governs
  this record's completion.

Additive and nullable, so it is backward-compatible with every row written before this migration -- no
data migration needed, no existing row changes (AG-08).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e94a9d0e22d5'
down_revision: Union[str, Sequence[str], None] = 'f5a8b1c4d7e0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'cleaning_executions',
        sa.Column('protection_state', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema='equipment',
    )
    op.add_column(
        'cleaning_executions',
        sa.Column('sterilization_cycle_id', sa.UUID(), nullable=True),
        schema='equipment',
    )
    op.create_foreign_key(
        'fk_cleaning_executions_sterilization_cycle', 'cleaning_executions', 'process_cycles',
        ['sterilization_cycle_id'], ['id'], source_schema='equipment', referent_schema='equipment',
    )


def downgrade() -> None:
    op.drop_constraint('fk_cleaning_executions_sterilization_cycle', 'cleaning_executions', schema='equipment', type_='foreignkey')
    op.drop_column('cleaning_executions', 'sterilization_cycle_id', schema='equipment')
    op.drop_column('cleaning_executions', 'protection_state', schema='equipment')
