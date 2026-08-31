"""0058_combination_product_obligation_schema

Revision ID: f5a8b1c4d7e0
Revises: e4f7a0b3c6d9
Create Date: 2026-08-30 00:00:02.000000

Document 60 (SPEC-PM-003) — Combination-Product Postmarket Regulatory Coordination, Information
Sharing & Regulatory Calendar. Same `postmarket` schema, 5 owned entities: `regulatory_obligation`
(Document 60's own 12-field schema, extended -- see app/modules/postmarket/obligation_models.py's module
docstring), `applicant_relationship`, `constituent_information_share`, `correction_removal_regulatory_
record`, `periodic_reporting_cycle` (all per Document 112).

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f5a8b1c4d7e0'
down_revision: Union[str, Sequence[str], None] = 'e4f7a0b3c6d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'applicant_relationship',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('product_version_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('applicant_role', sa.String(length=60), nullable=False),
        sa.Column('applicant_name', sa.String(length=200), nullable=False),
        sa.Column('application_type', sa.String(length=40), nullable=True),
        sa.Column('application_number', sa.String(length=60), nullable=True),
        sa.Column('address', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('contact', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('sharing_channel', sa.String(length=80), nullable=True),
        sa.Column('valid_from', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='postmarket',
    )

    op.create_table(
        'regulatory_obligation',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('obligation_type', sa.String(length=40), nullable=False),
        sa.Column('source_type', sa.String(length=60), nullable=True),
        sa.Column('source_id', sa.UUID(), nullable=True),
        sa.Column('source_version', sa.Integer(), nullable=True),
        sa.Column('application_id', sa.String(length=120), nullable=True),
        sa.Column('rule_version_id', sa.String(length=40), nullable=True),
        sa.Column('clock_start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('original_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('current_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('calendar_profile_id', sa.String(length=40), nullable=True),
        sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('decision', sa.String(length=30), nullable=True),
        sa.Column('decision_rationale', sa.Text(), nullable=True),
        sa.Column('decision_by', sa.UUID(), nullable=True),
        sa.Column('decision_signature_id', sa.UUID(), nullable=True),
        sa.Column('deadline_override_evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('retention_basis', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('legal_hold', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('legal_hold_reason', sa.Text(), nullable=True),
        sa.Column('legal_hold_authority', sa.String(length=120), nullable=True),
        sa.Column('legal_hold_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='OPEN'),
        sa.Column('owner_subject_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['decision_by'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='postmarket',
    )
    op.create_index('ix_regulatory_obligation_type_due', 'regulatory_obligation', ['site_id', 'obligation_type', 'current_due_at'], schema='postmarket')

    op.create_table(
        'constituent_information_share',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('safety_case_id', sa.UUID(), nullable=False),
        sa.Column('applicant_relationship_id', sa.UUID(), nullable=False),
        sa.Column('applicant_relationship_version', sa.Integer(), nullable=False),
        sa.Column('company_receipt_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('package_content', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('package_digest', sa.String(length=128), nullable=True),
        sa.Column('package_version', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('shared_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('shared_by', sa.UUID(), nullable=True),
        sa.Column('sharing_signature_id', sa.UUID(), nullable=True),
        sa.Column('delivery_evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='PENDING'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['safety_case_id'], ['postmarket.safety_case.id']),
        sa.ForeignKeyConstraint(['applicant_relationship_id'], ['postmarket.applicant_relationship.id']),
        sa.ForeignKeyConstraint(['shared_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='postmarket',
    )
    op.create_index('ix_constituent_share_state_due', 'constituent_information_share', ['site_id', 'state', 'due_at'], schema='postmarket')

    op.create_table(
        'correction_removal_regulatory_record',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('field_action_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('assessment_state', sa.String(length=40), nullable=True),
        sa.Column('regime', sa.String(length=40), nullable=True),
        sa.Column('initiation_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('calendar_version', sa.String(length=40), nullable=True),
        sa.Column('required_facts', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('decision_by', sa.UUID(), nullable=True),
        sa.Column('decision_signature_id', sa.UUID(), nullable=True),
        sa.Column('scope_amendments', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('retention_class_code', sa.String(length=40), nullable=False, server_default='RC-806'),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='OPEN'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['decision_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='postmarket',
    )
    op.create_index('ix_correction_removal_state_due', 'correction_removal_regulatory_record', ['site_id', 'state', 'due_at'], schema='postmarket')

    op.create_table(
        'periodic_reporting_cycle',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('application_reference', sa.String(length=120), nullable=False),
        sa.Column('cycle_type', sa.String(length=40), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('data_cutoff_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dataset_snapshot_id', sa.UUID(), nullable=True),
        sa.Column('inclusion_rules_version', sa.String(length=40), nullable=True),
        sa.Column('part4_augmentation_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='SCHEDULED'),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('approval_signature_id', sa.UUID(), nullable=True),
        sa.Column('submission_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id', 'application_reference', 'cycle_type', 'period_start'),
        schema='postmarket',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON postmarket.applicant_relationship TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON postmarket.regulatory_obligation TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON postmarket.constituent_information_share TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON postmarket.correction_removal_regulatory_record TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON postmarket.periodic_reporting_cycle TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON postmarket.periodic_reporting_cycle FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON postmarket.correction_removal_regulatory_record FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON postmarket.constituent_information_share FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON postmarket.regulatory_obligation FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON postmarket.applicant_relationship FROM {APP_ROLE}")
    op.drop_table('periodic_reporting_cycle', schema='postmarket')
    op.drop_table('correction_removal_regulatory_record', schema='postmarket')
    op.drop_table('constituent_information_share', schema='postmarket')
    op.drop_table('regulatory_obligation', schema='postmarket')
    op.drop_table('applicant_relationship', schema='postmarket')
