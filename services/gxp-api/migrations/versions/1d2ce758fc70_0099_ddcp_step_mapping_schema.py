"""0099_ddcp_step_mapping_schema

Revision ID: 1d2ce758fc70
Revises: 2e0dcac852aa
Create Date: 2026-09-11 00:00:03.000000

SG-180 (option B, project-owner-directed 2026-09-11): a declarative mapping from a DDCP execution action
to the generic recipe step (`gxp_recipe_step.stable_step_code`) it corresponds to, scoped per recipe
version (step codes are only unique within a recipe version -- migration d0a1a1bdfaef's own
UniqueConstraint). Read-only/visibility use this pass; see DdcpStepMapping's docstring for why the
write-side auto-completion path was not built (Document 106's `(batch_step, complete)`/`(batch_step,
results)` signature policy is unconditionally `signature_required=True`, so it would be permanently inert).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '1d2ce758fc70'
down_revision: Union[str, Sequence[str], None] = '2e0dcac852aa'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_ddcp_step_mapping',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('recipe_version_id', sa.UUID(), nullable=False),
        sa.Column('ddcp_action', sa.String(length=80), nullable=False),
        sa.Column('stable_step_code', sa.String(length=80), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['recipe_version_id'], ['ebmr.gxp_recipe_version.id']),
        sa.ForeignKeyConstraint(['created_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recipe_version_id', 'ddcp_action'),
        schema='ddcp',
    )

    op.execute(f"GRANT SELECT, INSERT, DELETE, TRUNCATE ON ddcp.gxp_ddcp_step_mapping TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ddcp.gxp_ddcp_step_mapping FROM {APP_ROLE}")
    op.drop_table('gxp_ddcp_step_mapping', schema='ddcp')
