"""0018_supplier_quality_schema

Revision ID: 1a2b3c4d5e6f
Revises: 8826e8447a2f
Create Date: 2026-08-24 00:00:00.000000

Document 18 (SPEC-MAT-001) -- Procurement & Supplier Quality Specification. Creates the 3 of the
document's 6 entities that are actually buildable this pass: `supplier`, `supplier_site`,
`supplier_qualification` (`supplier`/`supplier_qualification` are DDL-ready in
docs/generated/04_DATA_MODEL_CATALOGUE.md; `supplier_site` is prose-only, typed here directly as an
ordinary engineering decision -- SG-045's precedent, same as Document 16's packaging tables) plus
`supplier_qualification_evidence`, a join table implementing SUP-FR-005 by reusing the existing Vault
release pattern rather than a new evidence mechanism.

`approved_supplier_material`, `purchase_requisition` and `purchase_order_ref` are deliberately NOT created
in this migration: all three depend on a "material specification version" entity (Document 18 §6 / C-014
Specification Master) that does not exist anywhere in this codebase -- see SG-057 in
docs/generated/18_SPEC_GAPS.md. SUP-FR-006/014/015/016/021 (supplier audit, change notification,
performance, SCAR, RFQ) have no entity or, for RFQ, API operation defined anywhere in Document 18 itself --
see SG-058, same pattern as Document 16's SG-056.

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
Tables placed in the shared `ebmr` schema, matching the genealogy/qa_review/packaging precedent (not the
older dedicated `materials` schema, which belongs to the already-built Documents 19-22 module).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '1a2b3c4d5e6f'
down_revision: Union[str, Sequence[str], None] = '8826e8447a2f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'supplier',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('supplier_code', sa.String(length=120), nullable=False),
        sa.Column('legal_name', sa.String(length=255), nullable=False),
        sa.Column('role_type', sa.String(length=40), nullable=False),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='draft'),
        sa.Column('country', sa.String(length=80), nullable=True),
        sa.Column('external_mappings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('supplier_code'),
        schema='ebmr',
    )

    op.create_table(
        'supplier_site',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('site_name', sa.String(length=200), nullable=False),
        sa.Column('address_line1', sa.String(length=200), nullable=True),
        sa.Column('address_line2', sa.String(length=200), nullable=True),
        sa.Column('city', sa.String(length=100), nullable=True),
        sa.Column('state_province', sa.String(length=100), nullable=True),
        sa.Column('postal_code', sa.String(length=30), nullable=True),
        sa.Column('country', sa.String(length=80), nullable=True),
        sa.Column('manufacturer_flag', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('certification_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='active'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['supplier_id'], ['ebmr.supplier.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_supplier_site_supplier', 'supplier_site', ['supplier_id'], schema='ebmr')

    op.create_table(
        'supplier_qualification',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('supplier_site_id', sa.UUID(), nullable=False),
        sa.Column('requested_by_user_id', sa.UUID(), nullable=False),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('risk_class', sa.String(length=40), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='requested'),
        sa.Column('justification', sa.String(length=2000), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('quality_agreement_vault_id', sa.UUID(), nullable=True),
        sa.Column('approval_signatures', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['supplier_site_id'], ['ebmr.supplier_site.id']),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['quality_agreement_vault_id'], ['vault.gxp_vault_object.object_id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index(
        'ix_supplier_qualification_site', 'supplier_qualification', ['supplier_site_id'], schema='ebmr'
    )
    op.create_index(
        'ix_supplier_qualification_expires', 'supplier_qualification', ['expires_at'], schema='ebmr'
    )

    op.create_table(
        'supplier_qualification_evidence',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('supplier_qualification_id', sa.UUID(), nullable=False),
        sa.Column('vault_object_id', sa.UUID(), nullable=False),
        sa.Column('evidence_category', sa.String(length=60), nullable=False),
        sa.Column('added_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['supplier_qualification_id'], ['ebmr.supplier_qualification.id']),
        sa.ForeignKeyConstraint(['vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index(
        'ix_supplier_qualification_evidence_qual',
        'supplier_qualification_evidence',
        ['supplier_qualification_id'],
        schema='ebmr',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.supplier TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.supplier_site TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.supplier_qualification TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.supplier_qualification_evidence TO {APP_ROLE}")


def downgrade() -> None:
    for table in (
        'supplier_qualification_evidence',
        'supplier_qualification',
        'supplier_site',
        'supplier',
    ):
        op.execute(f"REVOKE ALL ON ebmr.{table} FROM {APP_ROLE}")
    op.drop_table('supplier_qualification_evidence', schema='ebmr')
    op.drop_table('supplier_qualification', schema='ebmr')
    op.drop_table('supplier_site', schema='ebmr')
    op.drop_table('supplier', schema='ebmr')
