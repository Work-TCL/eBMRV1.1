"""0065_appsec_secure_runtime_schema

Revision ID: b1e7c4a9d2f6
Revises: 075190b47469
Create Date: 2026-08-31 00:00:00.000000

Document 64 (SPEC-SEC-004) — Application, API, UI & Secure Runtime Engineering. Same `security` schema
Documents 61/62/63 created; adds the 3 owned entities Document 64's data model (# 6) lists:
`api_security_policy`, `outbound_destination`, `webhook_profile`. See
app/modules/security/appsec_models.py's module docstring for why this document is mostly cross-cutting
hardening (appsec.py + app/main.py middleware) with only a small config backbone here, and why there is
no signature policy row (Document 106 has none for any SPEC-SEC-004 action).

Same deviations as prior additive `security.*` migrations: no `tenant_id` (ADR-0006), no `site_id`
(platform-level). Numeric columns are integers (BigInteger) — never binary float — for any limit/window.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b1e7c4a9d2f6'
down_revision: Union[str, Sequence[str], None] = '075190b47469'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'api_security_policy',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('operation_id', sa.String(length=120), nullable=False),
        sa.Column('auth_mode', sa.String(length=30), nullable=False, server_default='BEARER_JWT'),
        sa.Column('allowed_roles_scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('object_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('writable_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('readable_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('rate_resource_limits', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('file_export_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('cors_csrf_profile', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('deprecation', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('operation_id'),
        schema='security',
    )

    op.create_table(
        'outbound_destination',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('service_id', sa.String(length=120), nullable=False),
        sa.Column('schemes_hosts_ports', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('ip_range_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('redirect_policy', sa.String(length=20), nullable=False, server_default='BLOCK'),
        sa.Column('auth_secret_ref', sa.String(length=200), nullable=True),
        sa.Column('purpose', sa.Text(), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('service_id'),
        schema='security',
    )
    op.create_index('ix_outbound_destination_state', 'outbound_destination', ['state'], schema='security')

    op.create_table(
        'webhook_profile',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('provider', sa.String(length=120), nullable=False),
        sa.Column('auth_mechanism', sa.String(length=30), nullable=False, server_default='HMAC_SHA256'),
        sa.Column('replay_window_seconds', sa.BigInteger(), nullable=False, server_default='300'),
        sa.Column('schema_version', sa.String(length=20), nullable=False, server_default='1.0'),
        sa.Column('max_body_bytes', sa.BigInteger(), nullable=False, server_default='1048576'),
        sa.Column('signing_secret_ref', sa.String(length=200), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('provider'),
        schema='security',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.api_security_policy TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.outbound_destination TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.webhook_profile TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON security.webhook_profile FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON security.outbound_destination FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON security.api_security_policy FROM {APP_ROLE}")
    op.drop_table('webhook_profile', schema='security')
    op.drop_index('ix_outbound_destination_state', table_name='outbound_destination', schema='security')
    op.drop_table('outbound_destination', schema='security')
    op.drop_table('api_security_policy', schema='security')
