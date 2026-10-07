"""0129_warehouse_location_lock

Revision ID: d9f1b3a5c7e8
Revises: c7e9a1b3d5f8
Create Date: 2026-10-02 00:00:00.000000

Client_Decisions_Neededanswers Topic 7 Q14 (SG-084): adds a temporary lock to `warehouse_locations` so a
physical count can block other stock movements in/out of a location while it is in progress. Purely
additive -- `locked` defaults to false, the other three columns are nullable -- no backfill needed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd9f1b3a5c7e8'
down_revision: Union[str, Sequence[str], None] = 'c7e9a1b3d5f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'warehouse_locations',
        sa.Column('locked', sa.Boolean(), nullable=False, server_default='false'),
        schema='materials',
    )
    op.add_column(
        'warehouse_locations',
        sa.Column('lock_reason', sa.String(1000), nullable=True),
        schema='materials',
    )
    op.add_column(
        'warehouse_locations',
        sa.Column('locked_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='materials',
    )
    op.create_foreign_key(
        'fk_warehouse_locations_locked_by_user_id',
        'warehouse_locations', 'users',
        ['locked_by_user_id'], ['id'],
        source_schema='materials', referent_schema='iam',
    )
    op.add_column(
        'warehouse_locations',
        sa.Column('locked_at', sa.DateTime(timezone=True), nullable=True),
        schema='materials',
    )


def downgrade() -> None:
    op.drop_column('warehouse_locations', 'locked_at', schema='materials')
    op.drop_constraint('fk_warehouse_locations_locked_by_user_id', 'warehouse_locations', schema='materials', type_='foreignkey')
    op.drop_column('warehouse_locations', 'locked_by_user_id', schema='materials')
    op.drop_column('warehouse_locations', 'lock_reason', schema='materials')
    op.drop_column('warehouse_locations', 'locked', schema='materials')
