"""0105_batch_step_required_qualification_code

Revision ID: 0f714e883102
Revises: 12233c9ad8df
Create Date: 2026-09-14 00:00:00.000000

Document 11 (SPEC-EBMR-002) -- BAT-FR-014, SG-048 #014 partial resolution, project-owner-directed. Adds a
new `required_qualification_code` column to `ebmr.gxp_recipe_step` and `ebmr.gxp_batch_step`, exactly
mirroring `required_role_code`'s own already-reviewed shape/precedent (SG-178, migration
b2d4f6a8c0e1_0086): declared on the recipe, frozen onto the batch step at issue time, nullable (a step the
recipe leaves unrestricted stays NULL and behaves exactly as before), no existing row rewritten (AG-08).

This is a *new* column, not an attempt to resolve `RecipeStep.qualification_policy_id` (which stays
exactly as unenforced/uninterpreted as it already was -- that UUID has no backing entity anywhere in this
codebase to resolve against, and inventing one would be exactly the guessed-schema-shape risk AG-15
forbids). `required_qualification_code` instead matches `iam.qualifications.qualification_code`'s own
already-DDL-ready string shape, the same one `material/commands.py::_check_dispensing_qualification`
already uses in production for an identical "does this actor hold qualification X right now" check --
that pre-existing pattern (and its two named error codes, `QualificationMissingError`/
`QualificationExpiredError`, already declared in `app/mutation/errors.py` and otherwise unused) is what
`batch_execution` now reuses, over the training-service alternative (`qms.QualificationRecord` +
`training_service.has_active_qualification()`), an ordinary engineering pick given SG-086 already
documents this codebase has two competing qualification stores and leaves choosing between them an open
question -- SG-086 itself stays open, this migration does not attempt to reconcile the two stores.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '0f714e883102'
down_revision: Union[str, Sequence[str], None] = '12233c9ad8df'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'gxp_recipe_step',
        sa.Column('required_qualification_code', sa.String(length=100), nullable=True),
        schema='ebmr',
    )
    op.add_column(
        'gxp_batch_step',
        sa.Column('required_qualification_code', sa.String(length=100), nullable=True),
        schema='ebmr',
    )


def downgrade() -> None:
    op.drop_column('gxp_batch_step', 'required_qualification_code', schema='ebmr')
    op.drop_column('gxp_recipe_step', 'required_qualification_code', schema='ebmr')
