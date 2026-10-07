"""0112_equipment_class_master

Revision ID: 820e95fa606e
Revises: 321e3db43c4a
Create Date: 2026-09-18 00:00:00.000000

Known-limitations fix (docs/testing/demo-gujarati/07 §7.9 item 4): `RecipeEquipmentRequirement.
equipment_class` was a free string with no backing entity. Adds `ebmr.gxp_equipment_class` -- a new,
narrow controlled vocabulary living in recipe_master, not `app/modules/equipment`, because that module's
own docstring declares "Exactly 4 authoritative entities ... no 5th table is added" per Document 38 §5;
adding a class table there would silently break that documented boundary (SPEC_GAP logged: whether this
should instead extend Document 38's own model is a real open question).

`equipment_class_id` on `gxp_recipe_equipment_requirement` is a new nullable FK alongside the existing
free-string `equipment_class` column (kept, not backfilled -- no confirmed mapping from old free text to
a new controlled code, same "no guessed backfill" precedent as every other additive column in this
schema). New/edited requirements set the FK; existing rows are left alone.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '820e95fa606e'
down_revision: Union[str, Sequence[str], None] = '321e3db43c4a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'gxp_equipment_class',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('class_code', sa.String(80), nullable=False),
        sa.Column('name', sa.String(255), nullable=False),
        sa.Column('description', sa.String(500), nullable=True),
        sa.Column('status', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.UniqueConstraint('class_code', name='uq_gxp_equipment_class_class_code'),
        schema='ebmr',
    )
    op.execute("GRANT SELECT, INSERT ON ebmr.gxp_equipment_class TO ebmr_new_gxp_app")

    op.add_column(
        'gxp_recipe_equipment_requirement',
        sa.Column('equipment_class_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='ebmr',
    )
    op.create_foreign_key(
        'fk_gxp_recipe_equipment_requirement_equipment_class',
        'gxp_recipe_equipment_requirement', 'gxp_equipment_class',
        ['equipment_class_id'], ['id'],
        source_schema='ebmr', referent_schema='ebmr',
    )


def downgrade() -> None:
    op.drop_constraint(
        'fk_gxp_recipe_equipment_requirement_equipment_class',
        'gxp_recipe_equipment_requirement', schema='ebmr', type_='foreignkey',
    )
    op.drop_column('gxp_recipe_equipment_requirement', 'equipment_class_id', schema='ebmr')
    op.drop_table('gxp_equipment_class', schema='ebmr')
