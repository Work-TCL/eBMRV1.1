"""0110_recipe_step_expected_hold_duration

Revision ID: 09322681e7ac
Revises: fc212b616386
Create Date: 2026-09-17 00:00:00.000000

SG-048 #018, visibility-only slice, project-owner-directed (asked directly between visibility-only,
full Temporal-based enforcement, or leaving it open -- chose visibility-only). `StepHold` already
records `held_at`; there was no declared "how long should this hold normally take" anywhere to compare
it against, so nothing could be flagged overdue without guessing a universal threshold (forbidden --
AG-15). This adds one nullable, opt-in field a recipe author may declare per step; when unset (the
default for every existing step), no overdue flag is ever computed -- matches the same "declared, not
guessed" precedent as `required_role_code`/`required_qualification_code` on the same table. No
enforcement action results from exceeding it (BAT-FR-021 exception generation stays unbuilt, unchanged);
this is display-only, read at execution time to flag an open hold in the UI.

Nullable, additive (AG-08, MIG-FR-004 expand step) -- no existing row rewritten.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '09322681e7ac'
down_revision: Union[str, Sequence[str], None] = 'fc212b616386'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'gxp_recipe_step',
        sa.Column('expected_hold_duration_minutes', sa.Integer(), nullable=True),
        schema='ebmr',
    )


def downgrade() -> None:
    op.drop_column('gxp_recipe_step', 'expected_hold_duration_minutes', schema='ebmr')
