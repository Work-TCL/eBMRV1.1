"""0130_inventory_reservation_fefo_override

Revision ID: e1f3a5c7d9b2
Revises: d9f1b3a5c7e8
Create Date: 2026-10-02 00:00:00.000000

Client_Decisions_Neededanswers Topic 8 (SG-083): a supervisor may request a non-FEFO lot for a
documented, justified exception, but the override requires approval from an authorized Quality/QA
person before the reservation actually holds stock. Adds `fefo_overridden`/`override_reason`/
`fefo_default_lot_id`/`override_approved_by_user_id`/`override_approved_at`/`override_signature_id` to
`inventory_reservations`. Purely additive -- `fefo_overridden` defaults to false, the rest are nullable
-- no backfill needed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e1f3a5c7d9b2'
down_revision: Union[str, Sequence[str], None] = 'd9f1b3a5c7e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'inventory_reservations',
        sa.Column('fefo_overridden', sa.Boolean(), nullable=False, server_default='false'),
        schema='materials',
    )
    op.add_column(
        'inventory_reservations',
        sa.Column('override_reason', sa.String(1000), nullable=True),
        schema='materials',
    )
    op.add_column(
        'inventory_reservations',
        sa.Column('fefo_default_lot_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='materials',
    )
    op.add_column(
        'inventory_reservations',
        sa.Column('override_approved_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='materials',
    )
    op.create_foreign_key(
        'fk_inventory_reservations_override_approved_by_user_id',
        'inventory_reservations', 'users',
        ['override_approved_by_user_id'], ['id'],
        source_schema='materials', referent_schema='iam',
    )
    op.add_column(
        'inventory_reservations',
        sa.Column('override_approved_at', sa.DateTime(timezone=True), nullable=True),
        schema='materials',
    )
    op.add_column(
        'inventory_reservations',
        sa.Column('override_signature_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='materials',
    )


def downgrade() -> None:
    op.drop_column('inventory_reservations', 'override_signature_id', schema='materials')
    op.drop_column('inventory_reservations', 'override_approved_at', schema='materials')
    op.drop_constraint('fk_inventory_reservations_override_approved_by_user_id', 'inventory_reservations', schema='materials', type_='foreignkey')
    op.drop_column('inventory_reservations', 'override_approved_by_user_id', schema='materials')
    op.drop_column('inventory_reservations', 'fefo_default_lot_id', schema='materials')
    op.drop_column('inventory_reservations', 'override_reason', schema='materials')
    op.drop_column('inventory_reservations', 'fefo_overridden', schema='materials')
