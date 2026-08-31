"""0057_regulatory_reportability_schema

Revision ID: e4f7a0b3c6d9
Revises: d3e6f9a2b5c8
Create Date: 2026-08-30 00:00:01.000000

Document 59 (SPEC-PM-002) — Regulatory Reportability Assessment & Electronic Safety Submission
Management. Same `postmarket` schema as migration 0056 (Document 58), 4 owned entities per Document 112:
`reportability_track`, `regulatory_report`, `regulatory_submission_attempt`, `regulatory_submission_ack`.
See app/modules/postmarket/reportability_models.py's module docstring for the caller-supplied-duration
deadline design (REG-FR-003) and the unresolved-signature-policy notes (SG-157).

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e4f7a0b3c6d9'
down_revision: Union[str, Sequence[str], None] = 'd3e6f9a2b5c8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'reportability_track',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('safety_case_id', sa.UUID(), nullable=False),
        sa.Column('report_type_code', sa.String(length=80), nullable=False),
        sa.Column('report_type_version', sa.String(length=40), nullable=False),
        sa.Column('application_context', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('clock_start_basis', sa.String(length=80), nullable=True),
        sa.Column('clock_start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('clock_start_rationale', sa.Text(), nullable=True),
        sa.Column('calendar_type', sa.String(length=20), nullable=True),
        sa.Column('calendar_version', sa.String(length=40), nullable=True),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('original_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decision', sa.String(length=30), nullable=True),
        sa.Column('decision_by', sa.UUID(), nullable=True),
        sa.Column('decision_signature_id', sa.UUID(), nullable=True),
        sa.Column('decision_rationale', sa.Text(), nullable=True),
        sa.Column('decision_evidence_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('rule_version', sa.String(length=40), nullable=True),
        sa.Column('parent_track_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='OPEN'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['safety_case_id'], ['postmarket.safety_case.id']),
        sa.ForeignKeyConstraint(['decision_by'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['parent_track_id'], ['postmarket.reportability_track.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='postmarket',
    )
    op.create_index('ix_reportability_track_state_due', 'reportability_track', ['site_id', 'state', 'due_at'], schema='postmarket')
    op.create_index('ix_reportability_track_case', 'reportability_track', ['safety_case_id'], schema='postmarket')

    op.create_table(
        'regulatory_report',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('reportability_track_id', sa.UUID(), nullable=False),
        sa.Column('report_version', sa.BigInteger(), nullable=False),
        sa.Column('schema_code', sa.String(length=60), nullable=False),
        sa.Column('schema_version', sa.String(length=40), nullable=False),
        sa.Column('content', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('field_provenance', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('missing_information', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('narrative_version', sa.Integer(), nullable=True),
        sa.Column('approved_by', sa.UUID(), nullable=True),
        sa.Column('approval_signature_id', sa.UUID(), nullable=True),
        sa.Column('payload_digest', sa.String(length=128), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='DRAFT'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['reportability_track_id'], ['postmarket.reportability_track.id']),
        sa.ForeignKeyConstraint(['approved_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('reportability_track_id', 'report_version'),
        schema='postmarket',
    )
    op.create_index('ix_regulatory_report_state', 'regulatory_report', ['site_id', 'state'], schema='postmarket')

    op.create_table(
        'regulatory_submission_attempt',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('regulatory_report_id', sa.UUID(), nullable=False),
        sa.Column('attempt_no', sa.Integer(), nullable=False),
        sa.Column('channel', sa.String(length=60), nullable=False),
        sa.Column('endpoint_profile', sa.String(length=120), nullable=True),
        sa.Column('payload_version', sa.String(length=40), nullable=False),
        sa.Column('payload_digest', sa.String(length=128), nullable=False),
        sa.Column('sender_identity', sa.String(length=120), nullable=False),
        sa.Column('authorized_by', sa.UUID(), nullable=False),
        sa.Column('authorization_signature_id', sa.UUID(), nullable=True),
        sa.Column('attempted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('transport_result', sa.String(length=30), nullable=False),
        sa.Column('failure_detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('manual_evidence_id', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['regulatory_report_id'], ['postmarket.regulatory_report.id']),
        sa.ForeignKeyConstraint(['authorized_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('regulatory_report_id', 'attempt_no'),
        schema='postmarket',
    )
    op.create_index('ix_submission_attempt_result', 'regulatory_submission_attempt', ['site_id', 'attempted_at'], schema='postmarket')

    op.create_table(
        'regulatory_submission_ack',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('submission_attempt_id', sa.UUID(), nullable=False),
        sa.Column('ack_level', sa.String(length=30), nullable=False),
        sa.Column('ack_state', sa.String(length=30), nullable=False),
        sa.Column('ack_reference', sa.String(length=200), nullable=True),
        sa.Column('ack_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('ack_received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('rejection_reason', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(['submission_attempt_id'], ['postmarket.regulatory_submission_attempt.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='postmarket',
    )
    op.create_index('ix_submission_ack_attempt', 'regulatory_submission_ack', ['submission_attempt_id', 'ack_level'], schema='postmarket')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON postmarket.reportability_track TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON postmarket.regulatory_report TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON postmarket.regulatory_submission_attempt TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON postmarket.regulatory_submission_ack TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON postmarket.regulatory_submission_ack FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON postmarket.regulatory_submission_attempt FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON postmarket.regulatory_report FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON postmarket.reportability_track FROM {APP_ROLE}")
    op.drop_table('regulatory_submission_ack', schema='postmarket')
    op.drop_table('regulatory_submission_attempt', schema='postmarket')
    op.drop_table('regulatory_report', schema='postmarket')
    op.drop_table('reportability_track', schema='postmarket')
