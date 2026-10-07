"""0118_equipment_breakdown_maintenance_schema

Revision ID: b01146cf4bf2
Revises: 93daec01f75f
Create Date: 2026-09-21 00:00:00.000000

Client requirement #9: MaintenanceWorkOrder gains actual_downtime_hours (caller-entered at
verification/completion, alongside the existing expected_downtime_hours estimate -- not backend-computed
from started_at/completed_at, since a breakdown's real downtime often predates when the work order was
even logged). `MAINTENANCE_TYPES` gaining "breakdown" (models.py) is a pure Python-tuple change, not a
DB constraint, so no migration is needed for that half of this requirement.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b01146cf4bf2'
down_revision: Union[str, Sequence[str], None] = '93daec01f75f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'maintenance_work_orders',
        sa.Column('actual_downtime_hours', sa.Numeric(10, 2), nullable=True),
        schema='equipment',
    )


def downgrade() -> None:
    op.drop_column('maintenance_work_orders', 'actual_downtime_hours', schema='equipment')
