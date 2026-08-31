"""0062_security_threat_model_schema

Revision ID: b650a504fe77
Revises: 2927a9a503a9
Create Date: 2026-08-31 00:00:00.000000

Document 61 (SPEC-SEC-001) — Security Architecture, Threat Model & Control Framework. New `security`
schema, 4 owned entities. See app/modules/security/models.py's module docstring for why only 4 tables
exist for the module's 8 functions, and for the SG-161 signature-policy gap.

Same deviations as prior additive migrations: `tenant_id` and `site_id` dropped (ADR-0006 / see
models.py's own "No `site_id`" note).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b650a504fe77'
down_revision: Union[str, Sequence[str], None] = '2927a9a503a9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS security")

    op.create_table(
        'security_threat_model_version',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('system_version', sa.String(length=60), nullable=False),
        sa.Column('methodology_version', sa.String(length=60), nullable=False),
        sa.Column('deployment_profile', sa.String(length=30), nullable=False),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('assets', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('boundaries', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='DRAFT'),
        sa.Column('review_triggers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('vault_ref', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='security',
    )

    op.create_table(
        'security_threat',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('threat_model_version_id', sa.UUID(), nullable=False),
        sa.Column('asset_or_boundary', sa.String(length=200), nullable=False),
        sa.Column('threat_type', sa.String(length=40), nullable=False),
        sa.Column('abuse_case', sa.Text(), nullable=False),
        sa.Column('attack_preconditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('impacted_attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('control_mappings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('inherent_risk', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('residual_risk', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('risk_calculation_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('residual_risk_acceptance', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='OPEN'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['threat_model_version_id'], ['security.security_threat_model_version.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='security',
    )
    op.create_index('ix_security_threat_model_version', 'security_threat', ['threat_model_version_id'], schema='security')

    op.create_table(
        'security_control',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('control_code', sa.String(length=100), nullable=False),
        sa.Column('objective', sa.Text(), nullable=True),
        sa.Column('implementation_owner', sa.String(length=200), nullable=True),
        sa.Column('evidence_source', sa.String(length=200), nullable=True),
        sa.Column('test_owner', sa.String(length=200), nullable=True),
        sa.Column('framework_mappings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('control_code'),
        schema='security',
    )

    op.create_table(
        'security_exception',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('control_or_requirement', sa.String(length=200), nullable=False),
        sa.Column('risk_assessment_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('compensating_controls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expiry', sa.DateTime(timezone=True), nullable=False),
        sa.Column('approvers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('remediation_target', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='OPEN'),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('opened_by', sa.UUID(), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['opened_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='security',
    )
    op.create_index('ix_security_exception_state', 'security_exception', ['state', 'expiry'], schema='security')

    op.execute(f"GRANT USAGE ON SCHEMA security TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.security_threat_model_version TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.security_threat TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.security_control TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.security_exception TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA security FROM {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON security.security_exception FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON security.security_control FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON security.security_threat FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON security.security_threat_model_version FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA security FROM {APP_ROLE}")
    op.drop_table('security_exception', schema='security')
    op.drop_table('security_control', schema='security')
    op.drop_table('security_threat', schema='security')
    op.drop_table('security_threat_model_version', schema='security')
    op.execute("DROP SCHEMA IF EXISTS security")
