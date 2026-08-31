"""0064_privileged_access_break_glass_schema

Revision ID: 075190b47469
Revises: a2b83f1afd6c
Create Date: 2026-08-31 00:00:00.000000

Document 63 (SPEC-SEC-003) — Privileged Access, Support Access, Break-Glass & Administrative Security.
Same `security` schema Documents 61/62 created; adds the 3 owned entities Document 63 itself lists:
`privileged_access_request`, `privileged_grant`, `privileged_session`. See
app/modules/security/privileged_access_models.py's module docstring for the Document 106 rows 134-136
signature resolution.

Same deviations as prior additive migrations: `tenant_id` dropped (ADR-0006); no `site_id` (platform-level,
same as every other `security.*` table).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '075190b47469'
down_revision: Union[str, Sequence[str], None] = 'a2b83f1afd6c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'privileged_access_request',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('subject_id', sa.UUID(), nullable=False),
        sa.Column('requested_role', sa.String(length=100), nullable=False),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('ticket_ref', sa.String(length=120), nullable=True),
        sa.Column('requested_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('requested_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='PENDING_APPROVAL'),
        sa.Column('approver_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['subject_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['approver_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='security',
    )

    op.create_table(
        'privileged_grant',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('request_id', sa.UUID(), nullable=True),
        sa.Column('grant_type', sa.String(length=20), nullable=False),
        sa.Column('role', sa.String(length=100), nullable=False),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('expiry', sa.DateTime(timezone=True), nullable=False),
        sa.Column('auth_strength', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('incident_ref', sa.String(length=120), nullable=True),
        sa.Column('granted_by', sa.UUID(), nullable=False),
        sa.Column('subject_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['request_id'], ['security.privileged_access_request.id']),
        sa.ForeignKeyConstraint(['granted_by'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='security',
    )
    op.create_index('ix_privileged_grant_subject_state', 'privileged_grant', ['subject_id', 'state'], schema='security')

    op.create_table(
        'privileged_session',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('grant_id', sa.UUID(), nullable=False),
        sa.Column('session_type', sa.String(length=20), nullable=False),
        sa.Column('customer_scope_ref', sa.String(length=120), nullable=True),
        sa.Column('support_case_ref', sa.String(length=120), nullable=True),
        sa.Column('opened_by', sa.UUID(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('connection_source', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('recording_evidence_ref', sa.String(length=300), nullable=True),
        sa.Column('review_status', sa.String(length=20), nullable=False, server_default='NOT_REQUIRED'),
        sa.Column('review', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('close_outcome', sa.String(length=200), nullable=True),
        sa.Column('closed_by', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['grant_id'], ['security.privileged_grant.id']),
        sa.ForeignKeyConstraint(['opened_by'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['closed_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='security',
    )
    op.create_index('ix_privileged_session_state', 'privileged_session', ['state'], schema='security')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.privileged_access_request TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.privileged_grant TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.privileged_session TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON security.privileged_session FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON security.privileged_grant FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON security.privileged_access_request FROM {APP_ROLE}")
    op.drop_table('privileged_session', schema='security')
    op.drop_table('privileged_grant', schema='security')
    op.drop_table('privileged_access_request', schema='security')
