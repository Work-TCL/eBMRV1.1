"""0020_capa_schema

Revision ID: 9a3d6c1f7e2b
Revises: 7f4c9a1e2b3d
Create Date: 2026-08-24 00:00:03.000000

Document 27 (SPEC-QMS-002) — CAPA Management. Same owner service as Document 26
(services/gxp-api/src/modules/qms), so `capa_record`, `capa_action` and `capa_effectiveness_check` are
added to the existing `qms` schema (created by migration 7f4c9a1e2b3d) rather than a new one. All three
typed directly this pass — see app/modules/qms/capa_models.py's module docstring (SG-045's precedent) and
docs/generated/18_SPEC_GAPS.md SG-063/SG-064/SG-065 for what is deliberately deferred.

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '9a3d6c1f7e2b'
down_revision: Union[str, Sequence[str], None] = '7f4c9a1e2b3d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'capa_record',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('quality_event_id', sa.UUID(), nullable=False),
        sa.Column('capa_number', sa.String(length=120), nullable=False),
        sa.Column('source_type', sa.String(length=40), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('source_version', sa.Integer(), nullable=True),
        sa.Column('problem_statement', sa.Text(), nullable=False),
        sa.Column('scope_type', sa.String(length=20), nullable=False, server_default='site'),
        sa.Column('scope_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('risk_class', sa.String(length=40), nullable=False),
        sa.Column('root_cause_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='OPEN'),
        sa.Column('owner_subject_id', sa.UUID(), nullable=False),
        sa.Column('target_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effectiveness_plan', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('corrective_action', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('preventive_action', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('recurrence_links', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cancel_reason', sa.Text(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extension_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('closure_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('reopen_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quality_event_id'),
        sa.UniqueConstraint('capa_number'),
        schema='qms',
    )
    op.create_index('ix_capa_record_state_target', 'capa_record', ['site_id', 'state', 'target_date'], schema='qms')

    op.create_table(
        'capa_action',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('capa_id', sa.UUID(), nullable=False),
        sa.Column('action_type', sa.String(length=20), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('owner_subject_id', sa.UUID(), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('dependency_links', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('implementation_evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('verification_status', sa.String(length=20), nullable=True),
        sa.Column('verified_by', sa.UUID(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['capa_id'], ['qms.capa_record.id']),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['verified_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_capa_action_capa', 'capa_action', ['capa_id'], schema='qms')

    op.create_table(
        'capa_effectiveness_check',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('capa_id', sa.UUID(), nullable=False),
        sa.Column('criterion', sa.Text(), nullable=False),
        sa.Column('data_source', sa.String(length=200), nullable=False),
        sa.Column('observation_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('observation_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('result', sa.String(length=20), nullable=True),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reviewer_subject_id', sa.UUID(), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['capa_id'], ['qms.capa_record.id']),
        sa.ForeignKeyConstraint(['reviewer_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_capa_effectiveness_check_capa', 'capa_effectiveness_check', ['capa_id'], schema='qms')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.capa_record TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.capa_action TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.capa_effectiveness_check TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON qms.capa_effectiveness_check FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.capa_action FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.capa_record FROM {APP_ROLE}")
    op.drop_table('capa_effectiveness_check', schema='qms')
    op.drop_table('capa_action', schema='qms')
    op.drop_table('capa_record', schema='qms')
