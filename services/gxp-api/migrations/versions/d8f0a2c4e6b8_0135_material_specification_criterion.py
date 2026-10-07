"""0135_material_specification_criterion

Revision ID: d8f0a2c4e6b8
Revises: c6e8f0a2d4b6
Create Date: 2026-10-05 00:00:00.000000

Client gap-analysis Phase 5 (2026-10-05): structured Test Name / Specification / Acceptance Criteria rows
for a material specification draft, replacing the never-populated `acceptance_criteria` JSONB blob on
`gxp_material_specification_version` (that column is left in place, unreferenced by new code -- MIG-FR-004
expand/contract discipline). Purely additive: one new table, no change to the existing version table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd8f0a2c4e6b8'
down_revision: Union[str, Sequence[str], None] = 'c6e8f0a2d4b6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_material_specification_criterion',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('material_spec_version_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('test_name', sa.String(length=255), nullable=False),
        sa.Column('specification_text', sa.Text(), nullable=False),
        sa.Column('acceptance_criteria_text', sa.Text(), nullable=False),
        sa.Column('fulfillment_path', sa.String(length=20), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        schema='ebmr',
    )
    op.create_foreign_key(
        'fk_material_spec_criterion_version_id',
        'gxp_material_specification_criterion', 'gxp_material_specification_version',
        ['material_spec_version_id'], ['id'],
        source_schema='ebmr', referent_schema='ebmr',
    )
    op.create_index(
        'ix_material_spec_criterion_version', 'gxp_material_specification_criterion',
        ['material_spec_version_id', 'sequence'], schema='ebmr',
    )
    op.execute(
        f"GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ebmr.gxp_material_specification_criterion TO {APP_ROLE}"
    )


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.gxp_material_specification_criterion FROM {APP_ROLE}")
    op.drop_index('ix_material_spec_criterion_version', table_name='gxp_material_specification_criterion', schema='ebmr')
    op.drop_constraint(
        'fk_material_spec_criterion_version_id', 'gxp_material_specification_criterion', schema='ebmr',
        type_='foreignkey',
    )
    op.drop_table('gxp_material_specification_criterion', schema='ebmr')
