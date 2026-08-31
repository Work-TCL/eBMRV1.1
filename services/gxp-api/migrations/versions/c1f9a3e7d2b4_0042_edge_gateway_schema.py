"""0042_edge_gateway_schema

Revision ID: c1f9a3e7d2b4
Revises: 8b3e2f5a91c7
Create Date: 2026-08-26 00:00:00.000000

Document 43 (SPEC-EDGE-001) — Edge Gateway Runtime Architecture, server-side slice only (see
app/modules/edge/models.py's module docstring for the scope split). New `edge` schema. Also adds
`iam.service_identities` (SG-120 minimal non-human identity primitive) since it is a precondition for
this module doing anything at all, same "signature policy tables ride along with their consuming module's
migration" precedent as prior WP-06 passes.

`tenant_id` dropped throughout (single-organization platform, ADR-0006). `edge_observations`,
`edge_health_snapshots`, `edge_security_events` and `edge_certificate_rotations` are append-only (AG-08):
no UPDATE grant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c1f9a3e7d2b4'
down_revision: Union[str, Sequence[str], None] = '8b3e2f5a91c7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS edge")

    op.create_table(
        'service_identities',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('identity_type', sa.String(length=40), nullable=False, server_default='edge_gateway'),
        sa.Column('subject_ref', sa.UUID(), nullable=False),
        sa.Column('credential_hash', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        schema='iam',
    )

    # edge_gateways.active_config_version_id and edge_config_snapshots.gateway_id reference each other --
    # create edge_gateways without the forward FK, add it after edge_config_snapshots exists.
    op.create_table(
        'edge_gateways',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('host_identity', sa.String(length=255), nullable=False),
        sa.Column('certificate_fingerprint', sa.String(length=255), nullable=False),
        sa.Column('certificate_expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('enrolled_by_user_id', sa.UUID(), nullable=False),
        sa.Column('lifecycle_state', sa.String(length=30), nullable=False, server_default='ENROLLED'),
        sa.Column('last_reported_operational_state', sa.String(length=30), nullable=True),
        sa.Column('active_config_version_id', sa.UUID(), nullable=True),
        sa.Column('last_health_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_observation_sequence', sa.BigInteger(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['enrolled_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='edge',
    )

    op.create_table(
        'edge_enrollment_tokens',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('token_hash', sa.String(length=255), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='unused'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_by_gateway_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['consumed_by_gateway_id'], ['edge.edge_gateways.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('token_hash'),
        schema='edge',
    )

    op.create_table(
        'edge_config_snapshots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('gateway_id', sa.UUID(), nullable=False),
        sa.Column('config_version', sa.String(length=60), nullable=False),
        sa.Column('payload_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('checksum', sa.String(length=128), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('activated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['gateway_id'], ['edge.edge_gateways.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('gateway_id', 'config_version'),
        schema='edge',
    )

    op.create_foreign_key(
        'fk_edge_gateways_active_config_version_id', 'edge_gateways', 'edge_config_snapshots',
        ['active_config_version_id'], ['id'], source_schema='edge', referent_schema='edge',
    )

    op.create_table(
        'edge_observations',
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('gateway_id', sa.UUID(), nullable=False),
        sa.Column('gateway_sequence', sa.BigInteger(), nullable=False),
        sa.Column('connector_id', sa.String(length=120), nullable=True),
        sa.Column('device_id', sa.String(length=120), nullable=True),
        sa.Column('mapping_id', sa.String(length=120), nullable=True),
        sa.Column('mapping_version', sa.String(length=60), nullable=True),
        sa.Column('source', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('gateway_received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('clock_quality', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('quality', sa.String(length=20), nullable=False),
        sa.Column('raw', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('normalized', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('correlation_id', sa.String(length=120), nullable=True),
        sa.Column('batch_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['gateway_id'], ['edge.edge_gateways.id']),
        sa.PrimaryKeyConstraint('event_id'),
        sa.UniqueConstraint('gateway_id', 'gateway_sequence'),
        schema='edge',
    )
    op.create_index('ix_edge_observations_gateway', 'edge_observations', ['gateway_id', 'accepted_at'], schema='edge')

    op.create_table(
        'edge_health_snapshots',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('gateway_id', sa.UUID(), nullable=False),
        sa.Column('reported_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('operational_state', sa.String(length=30), nullable=True),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('clock_quality', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cert_expiry_days', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['gateway_id'], ['edge.edge_gateways.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='edge',
    )
    op.create_index('ix_edge_health_snapshots_gateway', 'edge_health_snapshots', ['gateway_id', 'reported_at'], schema='edge')

    op.create_table(
        'edge_security_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('gateway_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=80), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reported_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['gateway_id'], ['edge.edge_gateways.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='edge',
    )
    op.create_index('ix_edge_security_events_gateway', 'edge_security_events', ['gateway_id', 'reported_at'], schema='edge')

    op.create_table(
        'edge_certificate_rotations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('gateway_id', sa.UUID(), nullable=False),
        sa.Column('old_fingerprint', sa.String(length=255), nullable=False),
        sa.Column('new_fingerprint', sa.String(length=255), nullable=False),
        sa.Column('requested_by_user_id', sa.UUID(), nullable=False),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('rotated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['gateway_id'], ['edge.edge_gateways.id']),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='edge',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON iam.service_identities TO {APP_ROLE}")

    op.execute(f"GRANT USAGE ON SCHEMA edge TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON edge.edge_gateways TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON edge.edge_enrollment_tokens TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON edge.edge_config_snapshots TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON edge.edge_observations TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON edge.edge_health_snapshots TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON edge.edge_security_events TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON edge.edge_certificate_rotations TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA edge FROM {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON edge.edge_certificate_rotations FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON edge.edge_security_events FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON edge.edge_health_snapshots FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON edge.edge_observations FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON edge.edge_config_snapshots FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON edge.edge_enrollment_tokens FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON edge.edge_gateways FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA edge FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON iam.service_identities FROM {APP_ROLE}")

    op.drop_table('edge_certificate_rotations', schema='edge')
    op.drop_table('edge_security_events', schema='edge')
    op.drop_table('edge_health_snapshots', schema='edge')
    op.drop_table('edge_observations', schema='edge')
    op.drop_constraint('fk_edge_gateways_active_config_version_id', 'edge_gateways', schema='edge', type_='foreignkey')
    op.drop_table('edge_config_snapshots', schema='edge')
    op.drop_table('edge_enrollment_tokens', schema='edge')
    op.drop_table('edge_gateways', schema='edge')
    op.execute("DROP SCHEMA IF EXISTS edge")
    op.drop_table('service_identities', schema='iam')
