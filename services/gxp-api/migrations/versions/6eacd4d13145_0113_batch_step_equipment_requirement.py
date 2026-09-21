"""0113_batch_step_equipment_requirement

Revision ID: 6eacd4d13145
Revises: 820e95fa606e
Create Date: 2026-09-18 00:00:00.000000

Known-limitations fix (docs/testing/demo-gujarati/08 §8.8, and recipe_master's own
RecipeEquipmentRequirement docstring, and this module's own docstring naming "Equipment master
eligibility wiring" as not-yet-built): adds `ebmr.gxp_batch_step_equipment_requirement`, frozen at
`issue_batch()` time from `recipe_master.RecipeEquipmentRequirement`, the same "freeze at issue" treatment
`BatchStep.required_role_code`/`.required_qualification_code` already use. A child table, not scalar
columns on `gxp_batch_step`, because a step can carry more than one equipment requirement.

Append-only from the application's perspective (written once at issue, read at step-start) -- no UPDATE
grant, same precedent as `gxp_step_result`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '6eacd4d13145'
down_revision: Union[str, Sequence[str], None] = '820e95fa606e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_batch_step_equipment_requirement',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('batch_step_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ebmr.gxp_batch_step.id'), nullable=False),
        sa.Column('equipment_class', sa.String(80), nullable=False),
        sa.Column('equipment_class_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('exact_equipment_optional', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('require_current_calibration', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('require_current_qualification', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('require_current_cleaning', sa.Boolean(), nullable=False, server_default=sa.false()),
        schema='ebmr',
    )
    op.create_index(
        'ix_gxp_batch_step_equipment_requirement_batch_step_id',
        'gxp_batch_step_equipment_requirement', ['batch_step_id'], schema='ebmr',
    )
    op.execute(f"GRANT SELECT, INSERT ON ebmr.gxp_batch_step_equipment_requirement TO {APP_ROLE}")


def downgrade() -> None:
    op.drop_index(
        'ix_gxp_batch_step_equipment_requirement_batch_step_id',
        table_name='gxp_batch_step_equipment_requirement', schema='ebmr',
    )
    op.drop_table('gxp_batch_step_equipment_requirement', schema='ebmr')
