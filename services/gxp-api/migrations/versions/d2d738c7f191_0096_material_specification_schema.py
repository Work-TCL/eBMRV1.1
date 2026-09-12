"""0096_material_specification_schema

Revision ID: d2d738c7f191
Revises: 34927659a971
Create Date: 2026-09-11 00:00:00.000000

SG-057 (architecture rule C-014, Specification Master): `approved_supplier_material`,
`purchase_requisition`, `purchase_order_ref` (Document 18) and `recipe_material_requirement` (Document 10,
SG-045) all key on a "material specification version" entity distinct from the flat raw-material master
(C-013, `materials.materials`) this codebase already has. This migration adds that entity, mirroring
`product_master.ProductVersion`'s master+immutable-version split exactly (business_id + version_no
identity, draft/released lifecycle, effective dating, release through the generic Vault surface,
version_hash) rather than inventing a new pattern.

`acceptance_criteria` is a captured JSONB field, not a typed parameter-range schema — same precedent as
`yield_reconciliation.tolerance_rule`/`packaging.tolerance_rule`: no acceptance-range execution engine
exists yet (QC method master, a separate open item), so this pass declares but does not interpret it.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd2d738c7f191'
down_revision: Union[str, Sequence[str], None] = '34927659a971'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_material_specification_version',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('material_spec_business_id', sa.String(length=120), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False),
        sa.Column('material_id', sa.UUID(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('lifecycle_state', sa.String(length=40), nullable=False, server_default='draft'),
        sa.Column('acceptance_criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('released_vault_object_id', sa.UUID(), nullable=True),
        sa.Column('version_hash', sa.String(length=64), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['material_id'], ['materials.materials.id']),
        sa.ForeignKeyConstraint(['released_vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('material_spec_business_id', 'version_no'),
        schema='ebmr',
    )

    # Mutable pre-release (draft -> released), same reasoning as gxp_product_version (migration
    # d5d48a66187f): immutability of a *released* version comes from its Vault snapshot (VLT-FR-001), not
    # from revoking UPDATE on the draft-mutable table.
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.gxp_material_specification_version TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.gxp_material_specification_version FROM {APP_ROLE}")
    op.drop_table('gxp_material_specification_version', schema='ebmr')
