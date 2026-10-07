"""0134_equipment_calibration_approval

Revision ID: c6e8f0a2d4b6
Revises: b4d6f8a0c2e4
Create Date: 2026-10-05 00:00:00.000000

Client gap-analysis Phase 4 (2026-10-05): a separate QA/QC approval step on EquipmentCalibration, on top
of the existing objective `result` (pass/fail/oot) field -- the client's own stated distinction between
"Pass/Fail" and "Approved/Not-Approved". Purely additive, all three columns nullable, no backfill needed
(existing calibration rows simply have `approved=NULL`, read as "not yet reviewed").
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c6e8f0a2d4b6'
down_revision: Union[str, Sequence[str], None] = 'b4d6f8a0c2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'equipment_calibrations',
        sa.Column('approved', sa.Boolean(), nullable=True),
        schema='equipment',
    )
    op.add_column(
        'equipment_calibrations',
        sa.Column('approved_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='equipment',
    )
    op.create_foreign_key(
        'fk_equipment_calibrations_approved_by_user_id',
        'equipment_calibrations', 'users',
        ['approved_by_user_id'], ['id'],
        source_schema='equipment', referent_schema='iam',
    )
    op.add_column(
        'equipment_calibrations',
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        schema='equipment',
    )


def downgrade() -> None:
    op.drop_column('equipment_calibrations', 'approved_at', schema='equipment')
    op.drop_constraint(
        'fk_equipment_calibrations_approved_by_user_id', 'equipment_calibrations', schema='equipment',
        type_='foreignkey',
    )
    op.drop_column('equipment_calibrations', 'approved_by_user_id', schema='equipment')
    op.drop_column('equipment_calibrations', 'approved', schema='equipment')
