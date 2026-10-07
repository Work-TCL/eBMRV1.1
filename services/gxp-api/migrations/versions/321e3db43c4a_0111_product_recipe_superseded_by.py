"""0111_product_recipe_superseded_by

Revision ID: 321e3db43c4a
Revises: 09322681e7ac
Create Date: 2026-09-18 00:00:00.000000

Known-limitations fix (docs/testing/demo-gujarati/06 §6.8 item 1, 07 §7.9 item 1): `obsolete`/
`superseded` were already legal states in both `product_master`'s and `recipe_master`'s
LIFECYCLE_STATES/ALLOWED_TRANSITIONS tables, but no command ever reached them. This adds the one piece
of schema the new `supersede_*` commands need that didn't already exist: a queryable pointer from a
superseded version to the version that replaced it (the audit trail records the transition either way,
but without this column there is no way to list "what superseded X" without scanning audit events).

Nullable, additive (AG-08, MIG-FR-004 expand step) -- no existing row rewritten. FK targets the same
table (self-referential), same treatment as any other optional cross-reference in this schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '321e3db43c4a'
down_revision: Union[str, Sequence[str], None] = '09322681e7ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'gxp_product_version',
        sa.Column('superseded_by_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='ebmr',
    )
    op.create_foreign_key(
        'fk_gxp_product_version_superseded_by',
        'gxp_product_version', 'gxp_product_version',
        ['superseded_by_version_id'], ['id'],
        source_schema='ebmr', referent_schema='ebmr',
    )
    op.add_column(
        'gxp_recipe_version',
        sa.Column('superseded_by_version_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='ebmr',
    )
    op.create_foreign_key(
        'fk_gxp_recipe_version_superseded_by',
        'gxp_recipe_version', 'gxp_recipe_version',
        ['superseded_by_version_id'], ['id'],
        source_schema='ebmr', referent_schema='ebmr',
    )


def downgrade() -> None:
    op.drop_constraint('fk_gxp_recipe_version_superseded_by', 'gxp_recipe_version', schema='ebmr', type_='foreignkey')
    op.drop_column('gxp_recipe_version', 'superseded_by_version_id', schema='ebmr')
    op.drop_constraint('fk_gxp_product_version_superseded_by', 'gxp_product_version', schema='ebmr', type_='foreignkey')
    op.drop_column('gxp_product_version', 'superseded_by_version_id', schema='ebmr')
