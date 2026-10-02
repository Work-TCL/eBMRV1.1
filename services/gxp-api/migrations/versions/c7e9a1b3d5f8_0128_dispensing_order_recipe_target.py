"""0128_dispensing_order_recipe_target

Revision ID: c7e9a1b3d5f8
Revises: b5d7f9a1c3e6
Create Date: 2026-10-02 00:00:00.000000

Client_Decisions_Neededanswers Topic 5 (SG-094): `create_dispensing_order` now derives target_qty/
target_uom/tolerance_low/tolerance_high from the batch's released recipe `RecipeMaterialRequirement`
instead of accepting caller-supplied values. Adds `target_from_recipe` (tracks which path produced the
stored values; existing rows predate this feature and get `false`) and the override-audit columns
`override_reason`/`overridden_by_user_id`/`overridden_at` for the new Supervisor/Admin-only
`override_dispensing_order_target` command (RBAC + mandatory reason, no signature). Purely additive --
no backfill needed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c7e9a1b3d5f8'
down_revision: Union[str, Sequence[str], None] = 'b5d7f9a1c3e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'dispensing_orders',
        sa.Column('target_from_recipe', sa.Boolean(), nullable=False, server_default='false'),
        schema='materials',
    )
    op.add_column(
        'dispensing_orders',
        sa.Column('override_reason', sa.String(1000), nullable=True),
        schema='materials',
    )
    op.add_column(
        'dispensing_orders',
        sa.Column('overridden_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='materials',
    )
    op.create_foreign_key(
        'fk_dispensing_orders_overridden_by_user_id',
        'dispensing_orders', 'users',
        ['overridden_by_user_id'], ['id'],
        source_schema='materials', referent_schema='iam',
    )
    op.add_column(
        'dispensing_orders',
        sa.Column('overridden_at', sa.DateTime(timezone=True), nullable=True),
        schema='materials',
    )


def downgrade() -> None:
    op.drop_column('dispensing_orders', 'overridden_at', schema='materials')
    op.drop_constraint('fk_dispensing_orders_overridden_by_user_id', 'dispensing_orders', schema='materials', type_='foreignkey')
    op.drop_column('dispensing_orders', 'overridden_by_user_id', schema='materials')
    op.drop_column('dispensing_orders', 'override_reason', schema='materials')
    op.drop_column('dispensing_orders', 'target_from_recipe', schema='materials')
