"""0117_equipment_calibration_type_schema

Revision ID: 93daec01f75f
Revises: 4fcee4fe8c23
Create Date: 2026-09-21 00:00:00.000000

Client requirement #7: EquipmentCalibration gains calibration_type (internal|external, default
'internal' -- history predates this column and was always performed by an internal actor), plus
provider_name and certificate_reference, meaningful only when external. Expand-only, no backfill needed
beyond the default.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '93daec01f75f'
down_revision: Union[str, Sequence[str], None] = '4fcee4fe8c23'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'equipment_calibrations',
        sa.Column('calibration_type', sa.String(length=20), nullable=False, server_default='internal'),
        schema='equipment',
    )
    op.add_column(
        'equipment_calibrations',
        sa.Column('provider_name', sa.String(length=255), nullable=True),
        schema='equipment',
    )
    op.add_column(
        'equipment_calibrations',
        sa.Column('certificate_reference', sa.String(length=160), nullable=True),
        schema='equipment',
    )


def downgrade() -> None:
    op.drop_column('equipment_calibrations', 'certificate_reference', schema='equipment')
    op.drop_column('equipment_calibrations', 'provider_name', schema='equipment')
    op.drop_column('equipment_calibrations', 'calibration_type', schema='equipment')
