"""0097_recipe_material_equipment_requirement_schema

Revision ID: 4c2d52d2b8a2
Revises: d2d738c7f191
Create Date: 2026-09-11 00:00:01.000000

SG-045 — `recipe_material_requirement`/`recipe_equipment_requirement` (Document 10), the two Document 10
entities left prose-only because their fields describe policy concepts, not a column list. Field shapes are
reused from already-approved precedent rather than invented:
  - `target_value`/`min_value`/`max_value`/`uom`/`uom_id` mirror `gxp_recipe_parameter`'s own tolerance
    columns exactly (same "no rule-execution engine exists" state SG-089 already documents).
  - `alternative_material_spec_version_id`/`substitution_allowed`/`consume_mode` are captured, unenforced
    fields -- same class as `equipment_class_id` elsewhere in this codebase.
  - `equipment_class`/`require_current_calibration`/`require_current_qualification`/
    `require_current_cleaning` are captured; the calibration/qualification gates are declared for a future
    BAT-FR-012/013 batch_execution wiring (SG-048 #012/#013), not enforced by this migration.

`material_spec_version_id` FKs migration d2d738c7f191's new SG-057 entity.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '4c2d52d2b8a2'
down_revision: Union[str, Sequence[str], None] = 'd2d738c7f191'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_recipe_material_requirement',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=False),
        sa.Column('material_spec_version_id', sa.UUID(), nullable=False),
        sa.Column('target_value', sa.Numeric(24, 8), nullable=True),
        sa.Column('min_value', sa.Numeric(24, 8), nullable=True),
        sa.Column('max_value', sa.Numeric(24, 8), nullable=True),
        sa.Column('uom', sa.String(length=40), nullable=True),
        sa.Column('uom_id', sa.UUID(), nullable=True),
        sa.Column('alternative_material_spec_version_id', sa.UUID(), nullable=True),
        sa.Column('substitution_allowed', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('consume_mode', sa.String(length=40), nullable=True),
        sa.Column('genealogy_required', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['step_id'], ['ebmr.gxp_recipe_step.id']),
        sa.ForeignKeyConstraint(['material_spec_version_id'], ['ebmr.gxp_material_specification_version.id']),
        sa.ForeignKeyConstraint(['alternative_material_spec_version_id'], ['ebmr.gxp_material_specification_version.id']),
        sa.ForeignKeyConstraint(['uom_id'], ['rules.gxp_uom.uom_id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )

    op.create_table(
        'gxp_recipe_equipment_requirement',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=False),
        sa.Column('equipment_class', sa.String(length=80), nullable=False),
        sa.Column('exact_equipment_optional', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('require_current_calibration', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('require_current_qualification', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('require_current_cleaning', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['step_id'], ['ebmr.gxp_recipe_step.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )

    # Wholesale delete+recreate on draft update, same reasoning as gxp_recipe_parameter/
    # gxp_recipe_evidence_requirement (migration d0a1a1bdfaef).
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ebmr.gxp_recipe_material_requirement TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ebmr.gxp_recipe_equipment_requirement TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.gxp_recipe_equipment_requirement FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON ebmr.gxp_recipe_material_requirement FROM {APP_ROLE}")
    op.drop_table('gxp_recipe_equipment_requirement', schema='ebmr')
    op.drop_table('gxp_recipe_material_requirement', schema='ebmr')
