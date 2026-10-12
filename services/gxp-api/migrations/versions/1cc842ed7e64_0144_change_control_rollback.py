"""0144_change_control_rollback

Revision ID: 1cc842ed7e64
Revises: 6aab486e47a9
Create Date: 2026-10-09 00:00:00.000000

CHG-FR-019/SG-071 resolved (project-owner-directed): adds `rollback_reason`/`rolled_back_at`, the same
shape as this table's own `cancel_reason`/`cancelled_at` columns, for the new ROLLED_BACK terminal state
(reachable only from IMPLEMENTATION/VERIFICATION, distinct from CANCELLED which means abandoned before
implementing). Additive, both columns nullable.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = '1cc842ed7e64'
down_revision: Union[str, Sequence[str], None] = '6aab486e47a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('change_control', sa.Column('rollback_reason', sa.Text(), nullable=True), schema='qms')
    op.add_column('change_control', sa.Column('rolled_back_at', sa.DateTime(timezone=True), nullable=True), schema='qms')


def downgrade() -> None:
    op.drop_column('change_control', 'rolled_back_at', schema='qms')
    op.drop_column('change_control', 'rollback_reason', schema='qms')
