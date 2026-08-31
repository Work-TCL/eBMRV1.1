"""0033_internal_audit_schema

Revision ID: 5c378cce7939
Revises: 307277f84a1a
Create Date: 2026-08-25 00:00:00.000000

Document 34 (SPEC-QMS-009) — Internal Audit Management. Same owner service as Documents 26-33
(services/gxp-api/src/modules/qms), so `internal_audit` and `audit_finding` are added to the existing
`qms` schema. Both typed directly this pass -- see app/modules/qms/internal_audit_models.py's module
docstring (SG-045's precedent) and docs/generated/18_SPEC_GAPS.md SG-101/SG-102 for what is deliberately
deferred.

Same deviation as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '5c378cce7939'
down_revision: Union[str, Sequence[str], None] = '307277f84a1a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'internal_audit',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('quality_event_id', sa.UUID(), nullable=False),
        sa.Column('audit_number', sa.String(length=120), nullable=False),
        sa.Column('program_ref', sa.String(length=120), nullable=False),
        sa.Column('site_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('process_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('criteria_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('lead_auditor_id', sa.UUID(), nullable=False),
        sa.Column('team', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('auditees', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('actual_start_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('actual_end_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='SCHEDULED'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['lead_auditor_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quality_event_id'),
        sa.UniqueConstraint('audit_number'),
        schema='qms',
    )
    op.create_index('ix_internal_audit_state', 'internal_audit', ['site_id', 'state'], schema='qms')

    op.create_table(
        'audit_finding',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('audit_id', sa.UUID(), nullable=False),
        sa.Column('finding_number', sa.String(length=120), nullable=False),
        sa.Column('requirement_ref', sa.String(length=200), nullable=False),
        sa.Column('observation', sa.Text(), nullable=False),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('severity', sa.String(length=50), nullable=False),
        sa.Column('owner_subject_id', sa.UUID(), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('capa_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('capa_rationale', sa.Text(), nullable=True),
        sa.Column('is_repeat_finding', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('verification', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='OPEN'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['audit_id'], ['qms.internal_audit.id']),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('finding_number'),
        schema='qms',
    )
    op.create_index('ix_audit_finding_audit', 'audit_finding', ['audit_id'], schema='qms')
    op.create_index('ix_audit_finding_state', 'audit_finding', ['site_id', 'state'], schema='qms')
    op.create_index('ix_audit_finding_requirement_ref', 'audit_finding', ['requirement_ref'], schema='qms')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.internal_audit TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.audit_finding TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON qms.audit_finding FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.internal_audit FROM {APP_ROLE}")
    op.drop_table('audit_finding', schema='qms')
    op.drop_table('internal_audit', schema='qms')
