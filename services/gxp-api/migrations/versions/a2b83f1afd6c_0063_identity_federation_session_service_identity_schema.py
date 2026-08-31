"""0063_identity_federation_session_service_identity_schema

Revision ID: a2b83f1afd6c
Revises: b650a504fe77
Create Date: 2026-08-31 00:00:00.000000

Document 62 (SPEC-SEC-002) — Identity Federation, SSO, MFA, Sessions & Service Identities. Same
`security` schema Document 61 created (migration 0062); adds the 3 owned entities Document 62 itself
lists: `identity_provider_config`, `application_session`, `service_identity`. See
app/modules/security/identity_models.py's module docstring for why `service_identity` here is distinct
from the pre-existing `iam.service_identities` (Document 43, edge-only credential store).

Same deviations as prior additive migrations: `tenant_id` dropped (ADR-0006); `application_session`/
`identity_provider_config` also have no `site_id` (platform-level, same as the security.* tables migration
0062 created); `service_identity` keeps a nullable `site_id` per its own Doc 62 field list ("tenant/site
scope").
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a2b83f1afd6c'
down_revision: Union[str, Sequence[str], None] = 'b650a504fe77'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'identity_provider_config',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('deployment_label', sa.String(length=120), nullable=False),
        sa.Column('issuer', sa.String(length=500), nullable=False),
        sa.Column('protocol', sa.String(length=20), nullable=False),
        sa.Column('trust_metadata', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('claim_mapping_version', sa.String(length=40), nullable=False),
        sa.Column('claim_mapping', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('identity_mappings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='security',
    )

    op.create_table(
        'application_session',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('subject_id', sa.UUID(), nullable=False),
        sa.Column('auth_time', sa.DateTime(timezone=True), nullable=False),
        sa.Column('auth_strength', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('idle_expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('revoked_reason', sa.Text(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='security',
    )
    op.create_index('ix_application_session_subject_state', 'application_session', ['subject_id', 'state'], schema='security')

    op.create_table(
        'service_identity',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('service_name', sa.String(length=120), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('allowed_audiences', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('allowed_scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('auth_method', sa.String(length=30), nullable=False),
        sa.Column('credential_ref', sa.String(length=300), nullable=False),
        sa.Column('lifecycle_status', sa.String(length=20), nullable=False, server_default='PROVISIONED'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('service_name'),
        schema='security',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.identity_provider_config TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.application_session TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.service_identity TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON security.service_identity FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON security.application_session FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON security.identity_provider_config FROM {APP_ROLE}")
    op.drop_table('service_identity', schema='security')
    op.drop_table('application_session', schema='security')
    op.drop_table('identity_provider_config', schema='security')
