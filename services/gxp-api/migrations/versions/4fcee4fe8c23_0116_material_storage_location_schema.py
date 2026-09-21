"""0116_material_storage_location_schema

Revision ID: 4fcee4fe8c23
Revises: 3a0708405e7f
Create Date: 2026-09-21 00:00:00.000000

Client requirement #4: Material Master gains an `is_in_house` flag and a `default_storage_condition`;
MaterialLot gains an optional `storage_location_id` (FK to the existing `materials.warehouse_locations`
master) and its own `storage_condition` override. Storage condition is a captured, application-validated
list (`STORAGE_CONDITIONS` in `material/models.py`), same "no DB CHECK constraint" precedent as this
schema's own `INVENTORY_TRANSACTION_TYPES`/`LOT_STATES` treatment elsewhere.

Expand-only -- four new nullable-or-defaulted columns on two existing tables, no backfill (no confirmed
source to backfill `is_in_house`/storage condition from for pre-existing rows).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '4fcee4fe8c23'
down_revision: Union[str, Sequence[str], None] = '3a0708405e7f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'materials',
        sa.Column('is_in_house', sa.Boolean(), nullable=False, server_default=sa.false()),
        schema='materials',
    )
    op.add_column(
        'materials',
        sa.Column('default_storage_condition', sa.String(length=40), nullable=True),
        schema='materials',
    )
    op.add_column(
        'material_lots',
        sa.Column('storage_location_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='materials',
    )
    op.add_column(
        'material_lots',
        sa.Column('storage_condition', sa.String(length=40), nullable=True),
        schema='materials',
    )
    op.create_foreign_key(
        'fk_material_lots_storage_location',
        'material_lots', 'warehouse_locations',
        ['storage_location_id'], ['id'],
        source_schema='materials', referent_schema='materials',
    )


def downgrade() -> None:
    op.drop_constraint('fk_material_lots_storage_location', 'material_lots', schema='materials', type_='foreignkey')
    op.drop_column('material_lots', 'storage_condition', schema='materials')
    op.drop_column('material_lots', 'storage_location_id', schema='materials')
    op.drop_column('materials', 'default_storage_condition', schema='materials')
    op.drop_column('materials', 'is_in_house', schema='materials')
