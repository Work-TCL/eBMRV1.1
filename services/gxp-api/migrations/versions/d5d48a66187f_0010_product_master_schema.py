"""0010_product_master_schema

Revision ID: d5d48a66187f
Revises: bded27d367f2
Create Date: 2026-08-22 00:00:02.000000

Document 09 (SPEC-EBMR-000) — Product, Constituent & Regulatory Profile Master. Additive only: this
migration creates 4 new tables in the existing `ebmr` schema and does not touch `ebmr.products`,
`ebmr.recipes`, `ebmr.recipe_steps` or `ebmr.batches` at all. `Batch`/`Recipe` keep using the legacy stub
tables unmodified this pass — repointing them at this real model is deferred until Document 10 (Master
Recipe) exists (see docs/generated/18_SPEC_GAPS.md).

Per docs/generated/04_DATA_MODEL_CATALOGUE.md, `product_family`/`product_version`/`product_constituent`/
`constituent_compatibility_version` are DDL-ready; `product_site_admission`/`product_external_mapping` are
prose-only (no types/constraints) and are deferred (SG-043) rather than guessed.

Deviations from the catalogue's literal field list, both ordinary engineering decisions:
  - `tenant_id` is dropped from every table: this platform is single-organization by design
    (app.core.db.assert_single_organization) and no other module's tables (vault, rules, audit, signature)
    carry a tenant_id column either — the catalogue's tenant_id is generic Document-70 boilerplate that
    doesn't match this codebase's actual architecture.
  - `product_version.product_family_id` gets a real FK to `gxp_product_family.id` (the catalogue left it a
    bare uuid column); `product_constituent.constituent_version_id`/`.product_version_id` and
    `constituent_compatibility_version.drug_constituent_version_id`/`.device_constituent_version_id` get
    real FKs to `gxp_product_version.id` (self-referential — V1 has no separate Drug/Device master module,
    so a constituent *is* another product_version row, per PRD-FR-004's "V1 actively supports Drug + Device").
  - `product_version.version` (bigint, optimistic concurrency) is added: the catalogue's own boilerplate
    footer calls for it on every table ("Versioning: version bigint optimistic concurrency"), it was simply
    missing from the 23-column list.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd5d48a66187f'
down_revision: Union[str, Sequence[str], None] = 'bded27d367f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_product_family',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('family_code', sa.String(length=80), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('profile_code', sa.String(length=80), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('family_code'),
        schema='ebmr',
    )

    op.create_table(
        'gxp_product_version',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_business_id', sa.String(length=120), nullable=False),
        sa.Column('version_no', sa.BigInteger(), nullable=False),
        sa.Column('product_code', sa.String(length=120), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('product_family_id', sa.UUID(), nullable=True),
        sa.Column('lifecycle_state', sa.String(length=40), nullable=False, server_default='draft'),
        sa.Column('manufacturing_profile_code', sa.String(length=80), nullable=False),
        sa.Column('combination_product_type', sa.String(length=40), nullable=True),
        sa.Column('pmoa_reference', sa.String(length=255), nullable=True),
        sa.Column('part4_profile_code', sa.String(length=80), nullable=True),
        sa.Column('sterile_profile_id', sa.UUID(), nullable=True),
        sa.Column('finished_tracking_strategy', sa.String(length=40), nullable=True),
        sa.Column('udi_applicable', sa.Boolean(), nullable=True),
        sa.Column('strength_value', sa.Numeric(24, 8), nullable=True),
        sa.Column('strength_uom', sa.String(length=40), nullable=True),
        sa.Column('device_model_code', sa.String(length=120), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('released_vault_object_id', sa.UUID(), nullable=True),
        sa.Column('version_hash', sa.String(length=64), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_family_id'], ['ebmr.gxp_product_family.id']),
        sa.ForeignKeyConstraint(['released_vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('product_business_id', 'version_no'),
        sa.UniqueConstraint('product_code', 'version_no'),
        schema='ebmr',
    )

    op.create_table(
        'gxp_product_constituent',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_version_id', sa.UUID(), nullable=False),
        sa.Column('constituent_type', sa.String(length=40), nullable=False),
        sa.Column('role_code', sa.String(length=40), nullable=True),
        sa.Column('constituent_business_id', sa.String(length=120), nullable=False),
        sa.Column('constituent_version_id', sa.UUID(), nullable=False),
        sa.Column('source_site_id', sa.UUID(), nullable=True),
        sa.Column('tracking_strategy', sa.String(length=40), nullable=True),
        sa.Column('sequence_no', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['product_version_id'], ['ebmr.gxp_product_version.id']),
        sa.ForeignKeyConstraint(['constituent_version_id'], ['ebmr.gxp_product_version.id']),
        sa.ForeignKeyConstraint(['source_site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )

    op.create_table(
        'gxp_constituent_compatibility_version',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('compatibility_code', sa.String(length=120), nullable=False),
        sa.Column('version_no', sa.BigInteger(), nullable=False),
        sa.Column('drug_constituent_version_id', sa.UUID(), nullable=False),
        sa.Column('device_constituent_version_id', sa.UUID(), nullable=False),
        sa.Column('interface_constraints', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='draft'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('vault_object_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['drug_constituent_version_id'], ['ebmr.gxp_product_version.id']),
        sa.ForeignKeyConstraint(['device_constituent_version_id'], ['ebmr.gxp_product_version.id']),
        sa.ForeignKeyConstraint(['vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('compatibility_code', 'version_no'),
        schema='ebmr',
    )

    # Mutable pre-release (draft -> under_review -> released), same reasoning as rules.gxp_rule_definition
    # (migration bded27d367f2): immutability of a *released* version comes from its vault snapshot
    # (VLT-FR-001), not from revoking UPDATE on the draft-mutable table.
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.gxp_product_family TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.gxp_product_version TO {APP_ROLE}")
    # Constituents also need DELETE: editing a draft's constituent list is a wholesale replace, same
    # reasoning as the existing DELETE grant on ebmr.recipe_steps (migration 747afac225e8).
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ebmr.gxp_product_constituent TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.gxp_constituent_compatibility_version TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.gxp_constituent_compatibility_version FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON ebmr.gxp_product_constituent FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON ebmr.gxp_product_version FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON ebmr.gxp_product_family FROM {APP_ROLE}")
    op.drop_table('gxp_constituent_compatibility_version', schema='ebmr')
    op.drop_table('gxp_product_constituent', schema='ebmr')
    op.drop_table('gxp_product_version', schema='ebmr')
    op.drop_table('gxp_product_family', schema='ebmr')
