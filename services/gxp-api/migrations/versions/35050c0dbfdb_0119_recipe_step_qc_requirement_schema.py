"""0119_recipe_step_qc_requirement_schema

Revision ID: 35050c0dbfdb
Revises: b01146cf4bf2
Create Date: 2026-09-21 00:00:00.000000

Client requirement #12: `gxp_recipe_step_qc_requirement` links a recipe step to the specific in-process
QC test specification(s) required before that step can be marked complete. Same shape and same
wholesale-delete+recreate-on-draft-update grant pattern as the sibling `gxp_recipe_evidence_requirement`/
`gxp_recipe_material_requirement` tables (migrations d0a1a1bdfaef/4c2d52d2b8a2).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '35050c0dbfdb'
down_revision: Union[str, Sequence[str], None] = 'b01146cf4bf2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_recipe_step_qc_requirement',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=False),
        sa.Column('qc_test_specification_id', sa.UUID(), nullable=False),
        sa.Column('required', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['step_id'], ['ebmr.gxp_recipe_step.id']),
        sa.ForeignKeyConstraint(['qc_test_specification_id'], ['ebmr.qc_test_specification.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ebmr.gxp_recipe_step_qc_requirement TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.gxp_recipe_step_qc_requirement FROM {APP_ROLE}")
    op.drop_table('gxp_recipe_step_qc_requirement', schema='ebmr')
