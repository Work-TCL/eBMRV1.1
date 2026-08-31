"""0067_netzero_network_flow_schema

Revision ID: d4a2c8f1b6e3
Revises: c3f8a1d7e5b2
Create Date: 2026-08-31 00:00:00.000000

Document 66 (SPEC-SEC-006) -- Network, Tenant, Deployment Isolation & Zero-Trust. Same `security` schema
Documents 61-65 created; adds the 2 owned entities `04_DATA_MODEL_CATALOGUE.md` lists:
`network_flow_definition`, `deployment_security_profile`. Read-only catalogue module -- no state-changing
endpoint, no Mutation Gateway command, no signature (Document 106 has no SPEC-SEC-006 row). See
app/modules/security/netzero_models.py.

Same deviations as prior additive `security.*` migrations: no `tenant_id` (ADR-0006), no `site_id`
(platform-level). Ports are integers.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd4a2c8f1b6e3'
down_revision: Union[str, Sequence[str], None] = 'c3f8a1d7e5b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'network_flow_definition',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('deployment_profile', sa.String(length=40), nullable=False),
        sa.Column('source_zone', sa.String(length=30), nullable=False),
        sa.Column('source_service', sa.String(length=80), nullable=False, server_default='*'),
        sa.Column('destination_zone', sa.String(length=30), nullable=False),
        sa.Column('destination_service', sa.String(length=80), nullable=False, server_default='*'),
        sa.Column('protocol', sa.String(length=16), nullable=False),
        sa.Column('port', sa.BigInteger(), nullable=False),
        sa.Column('purpose', sa.Text(), nullable=False),
        sa.Column('auth_mechanism', sa.String(length=30), nullable=False, server_default='MTLS'),
        sa.Column('effective_from', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('owner', sa.String(length=120), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('deployment_profile', 'source_zone', 'source_service', 'destination_zone',
                            'destination_service', 'protocol', 'port', 'version',
                            name='uq_network_flow_definition_identity'),
        schema='security',
    )
    op.create_index('ix_network_flow_definition_lookup', 'network_flow_definition',
                    ['deployment_profile', 'source_zone', 'destination_zone', 'state'], schema='security')

    op.create_table(
        'deployment_security_profile',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('profile_name', sa.String(length=60), nullable=False),
        sa.Column('deployment_profile', sa.String(length=40), nullable=False),
        sa.Column('ingress_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('egress_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('private_endpoints', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('namespaces', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('service_accounts', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('container_hardening', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('admin_access_pattern', sa.String(length=40), nullable=False, server_default='ZTNA'),
        sa.Column('backup_isolation', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('network_isolation', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('profile_name'),
        schema='security',
    )

    for t in ('network_flow_definition', 'deployment_security_profile'):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.{t} TO {APP_ROLE}")


def downgrade() -> None:
    for t in ('deployment_security_profile', 'network_flow_definition'):
        op.execute(f"REVOKE ALL ON security.{t} FROM {APP_ROLE}")
    op.drop_table('deployment_security_profile', schema='security')
    op.drop_index('ix_network_flow_definition_lookup', table_name='network_flow_definition', schema='security')
    op.drop_table('network_flow_definition', schema='security')
