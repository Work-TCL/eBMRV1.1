"""0137_equipment_phase7_fields

Revision ID: f5c7e9b1d3a8
Revises: e3a5c7f9b1d6
Create Date: 2026-10-05 00:00:00.000000

Client gap-analysis Phase 7: (1) `equipment_assets.is_computer_operated` -- new mandatory-at-creation
question distinguishing a computer-operated asset from a manual one (the detailed Computer System
Validation questionnaire itself stays explicitly deferred, per the client's own request -- this is just
the flag); (2) `equipment_assets.recalibration_required` -- set when a breakdown maintenance event is
recorded and not flagged non-critical, cleared only once a new calibration is recorded and approved, same
two-step bar `calibration_status`'s own CALIBRATION_APPROVAL_PENDING gate (migration 0134) already uses;
(3) `maintenance_work_orders.non_critical` -- the breakdown-only override that skips the recalibration
requirement above (detailed critical/non-critical rules stay deferred -- this is the binary flag only);
(4) `maintenance_work_orders.activities` -- a JSONB repeatable Activity/Result checklist for Plan
maintenance, same "captured JSONB array, not a new table" precedent this column's own neighbor
`parts_used` already uses -- the equipment module's own docstring declares exactly 4 authoritative
entities ("no 5th table is added"), and `EquipmentClass` was already routed to a different module
specifically to preserve that freeze, so a new `MaintenanceActivity` table would have broken a boundary
this codebase has deliberately protected before. All four columns additive/nullable-or-defaulted, no
backfill needed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f5c7e9b1d3a8'
down_revision: Union[str, Sequence[str], None] = 'e3a5c7f9b1d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'equipment_assets',
        sa.Column('is_computer_operated', sa.Boolean(), nullable=False, server_default=sa.false()),
        schema='equipment',
    )
    op.add_column(
        'equipment_assets',
        sa.Column('recalibration_required', sa.Boolean(), nullable=False, server_default=sa.false()),
        schema='equipment',
    )
    op.add_column(
        'maintenance_work_orders',
        sa.Column('non_critical', sa.Boolean(), nullable=False, server_default=sa.false()),
        schema='equipment',
    )
    op.add_column(
        'maintenance_work_orders',
        sa.Column('activities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema='equipment',
    )


def downgrade() -> None:
    op.drop_column('maintenance_work_orders', 'activities', schema='equipment')
    op.drop_column('maintenance_work_orders', 'non_critical', schema='equipment')
    op.drop_column('equipment_assets', 'recalibration_required', schema='equipment')
    op.drop_column('equipment_assets', 'is_computer_operated', schema='equipment')
