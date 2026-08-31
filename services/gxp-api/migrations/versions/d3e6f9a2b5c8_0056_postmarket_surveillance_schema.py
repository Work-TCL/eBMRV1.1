"""0056_postmarket_surveillance_schema

Revision ID: d3e6f9a2b5c8
Revises: c2d5f8a3e7b1
Create Date: 2026-08-30 00:00:00.000000

Document 58 (SPEC-PM-001) — Postmarket Surveillance, Safety Case & Signal Management. New `postmarket`
schema, 4 owned entities. See app/modules/postmarket/models.py's module docstring for the SG-154
(postmarket_source field-set conflict between Document 58 and Document 112) and classification-versioning
design notes.

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd3e6f9a2b5c8'
down_revision: Union[str, Sequence[str], None] = 'c2d5f8a3e7b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS postmarket")

    op.create_table(
        'postmarket_source',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('source_type', sa.String(length=40), nullable=False),
        sa.Column('organization_or_system', sa.String(length=200), nullable=False),
        sa.Column('channel', sa.String(length=120), nullable=False),
        sa.Column('ingestion_profile_id', sa.UUID(), nullable=True),
        sa.Column('owner_subject_id', sa.UUID(), nullable=False),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='ACTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='postmarket',
    )
    op.create_index('ix_postmarket_source_type', 'postmarket_source', ['site_id', 'source_type'], schema='postmarket')

    op.create_table(
        'safety_case',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('safety_case_number', sa.String(length=120), nullable=False),
        sa.Column('source_record_type', sa.String(length=60), nullable=False),
        sa.Column('source_record_id', sa.UUID(), nullable=False),
        sa.Column('source_record_version', sa.Integer(), nullable=False),
        sa.Column('source_receipt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('company_initial_receipt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('regulatory_clock_candidate_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('system_ingested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('marketed_product_id', sa.UUID(), nullable=True),
        sa.Column('application_profile_id', sa.UUID(), nullable=True),
        sa.Column('product_resolution', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('identity_resolution_state', sa.String(length=30), nullable=False, server_default='UNKNOWN_QUEUE'),
        sa.Column('reporter_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('citation', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('external_reference', sa.String(length=200), nullable=True),
        sa.Column('seriousness_attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('constituent_attribution', sa.String(length=30), nullable=True),
        sa.Column('constituent_classification', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('classification_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('current_classification_version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('canonical_case_id', sa.UUID(), nullable=True),
        sa.Column('duplicate_link_rationale', sa.Text(), nullable=True),
        sa.Column('reassessment_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('reportability_referral_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='RECEIVED'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['canonical_case_id'], ['postmarket.safety_case.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('safety_case_number'),
        schema='postmarket',
    )
    op.create_index('ix_safety_case_source', 'safety_case', ['source_record_type', 'source_record_id', 'source_record_version'], schema='postmarket')
    op.create_index('ix_safety_case_state', 'safety_case', ['site_id', 'state'], schema='postmarket')

    op.create_table(
        'safety_case_followup',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('safety_case_id', sa.UUID(), nullable=False),
        sa.Column('followup_no', sa.Integer(), nullable=False),
        sa.Column('followup_receipt_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('new_information', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reassessment_flags', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('expectedness_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recorded_by', sa.UUID(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['safety_case_id'], ['postmarket.safety_case.id']),
        sa.ForeignKeyConstraint(['recorded_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('safety_case_id', 'followup_no'),
        schema='postmarket',
    )
    op.create_index('ix_safety_case_followup_case', 'safety_case_followup', ['safety_case_id', 'followup_no'], schema='postmarket')

    op.create_table(
        'safety_signal',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('signal_code', sa.String(length=120), nullable=False),
        sa.Column('detection_source', sa.String(length=40), nullable=False),
        sa.Column('rule_version', sa.String(length=40), nullable=True),
        sa.Column('trigger_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('population_definition', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('exposure_denominator', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('denominator_uncertain', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('case_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('assessment', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('assessment_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='DETECTED'),
        sa.Column('escalation_links', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('owner_subject_id', sa.UUID(), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id', 'signal_code'),
        schema='postmarket',
    )
    op.create_index('ix_safety_signal_state', 'safety_signal', ['site_id', 'state'], schema='postmarket')

    op.execute(f"GRANT USAGE ON SCHEMA postmarket TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON postmarket.postmarket_source TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON postmarket.safety_case TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON postmarket.safety_case_followup TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON postmarket.safety_signal TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA postmarket FROM {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON postmarket.safety_signal FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON postmarket.safety_case_followup FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON postmarket.safety_case FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON postmarket.postmarket_source FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA postmarket FROM {APP_ROLE}")
    op.drop_table('safety_signal', schema='postmarket')
    op.drop_table('safety_case_followup', schema='postmarket')
    op.drop_table('safety_case', schema='postmarket')
    op.drop_table('postmarket_source', schema='postmarket')
    op.execute("DROP SCHEMA IF EXISTS postmarket")
