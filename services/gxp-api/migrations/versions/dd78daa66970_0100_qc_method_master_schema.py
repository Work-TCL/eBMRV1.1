"""0100_qc_method_master_schema

Revision ID: dd78daa66970
Revises: 1d2ce758fc70
Create Date: 2026-09-12 00:00:00.000000

SG-066 (QC-FR-003/004, Document 23) — the Method-master entity Document 23 never defines. QC-FR-003:
each test references an approved method/version, a compendial/internal/validated method type and a
suitability/validation evidence reference. QC-FR-004: a modified method requires a controlled version,
reason, validation/suitability evidence and approval, with the original method retained. Mirrors
`material_specification.MaterialSpecificationVersion`'s master+immutable-version split exactly (same
architectural pattern already approved for Product/Recipe/MaterialSpecification).

`qc_test_definition.method_version_id` is an additive, nullable FK -- `method_version` (the existing
free-text field) is untouched. Dual-written best-effort at spec-authoring time (same MIG-FR-004 expand-
step pattern already used for `uom_id`); no backfill for pre-existing rows (`qc_test_definition` has no
UPDATE grant -- migration 4b6e8f0a1c2d, append-only).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'dd78daa66970'
down_revision: Union[str, Sequence[str], None] = '1d2ce758fc70'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'qc_method_version',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('method_code', sa.String(length=80), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('method_type', sa.String(length=40), nullable=False),
        sa.Column('validation_evidence_reference', sa.String(length=255), nullable=True),
        sa.Column('modification_reason', sa.Text(), nullable=True),
        sa.Column('lifecycle_state', sa.String(length=40), nullable=False, server_default='draft'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('released_vault_object_id', sa.UUID(), nullable=True),
        sa.Column('version_hash', sa.String(length=64), nullable=True),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['released_vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('method_code', 'version_no'),
        schema='ebmr',
    )

    op.add_column(
        'qc_test_definition',
        sa.Column('method_version_id', sa.UUID(), nullable=True),
        schema='ebmr',
    )
    op.create_foreign_key(
        'fk_qc_test_definition_method_version_id',
        'qc_test_definition', 'qc_method_version',
        ['method_version_id'], ['id'],
        source_schema='ebmr', referent_schema='ebmr',
    )

    # Mutable pre-release (draft -> released), same reasoning as gxp_product_version/
    # gxp_material_specification_version.
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.qc_method_version TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.qc_method_version FROM {APP_ROLE}")
    op.drop_constraint('fk_qc_test_definition_method_version_id', 'qc_test_definition', schema='ebmr', type_='foreignkey')
    op.drop_column('qc_test_definition', 'method_version_id', schema='ebmr')
    op.drop_table('qc_method_version', schema='ebmr')
