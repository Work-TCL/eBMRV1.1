"""0086_batch_step_required_role_code

Revision ID: b2d4f6a8c0e1
Revises: 0ee74a161068
Create Date: 2026-09-08 00:00:00.000000

SG-178 (Document 10/11) -- RecipeStep.required_role_code was declared and shown but never enforced at
step start. Enforcement now happens in the regulated batch_execution path against a copy frozen into the
batch's issue snapshot (BAT-FR-003 / VLT-FR-006/007 -- the snapshot must carry the exact released
references the execution depends on). This migration adds that one column to the owned
`ebmr.gxp_batch_step` table. Additive, nullable, no existing row rewritten (AG-08); a step the recipe
left unrestricted stays NULL and behaves exactly as before.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2d4f6a8c0e1'
down_revision: Union[str, Sequence[str], None] = '0ee74a161068'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'gxp_batch_step',
        sa.Column('required_role_code', sa.String(length=80), nullable=True),
        schema='ebmr',
    )


def downgrade() -> None:
    op.drop_column('gxp_batch_step', 'required_role_code', schema='ebmr')
