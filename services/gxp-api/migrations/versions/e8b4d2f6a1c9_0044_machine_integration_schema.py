"""0044_machine_integration_schema

Revision ID: e8b4d2f6a1c9
Revises: a29568b32323
Create Date: 2026-08-26 00:00:00.000000

Document 47 (SPEC-EDGE-005) — PLC/SCADA Data Acquisition, Evidence Mapping & Command Boundary, server-side
slice only (see app/modules/machine_integration/models.py's module docstring for the scope split). New
`machine_integration` schema. `tenant_id` dropped throughout (single-organization platform, ADR-0006).

`machine_evidence_candidates`/`machine_alarm_events`/`cycle_evidence_manifests` are append-only (AG-08):
no UPDATE grant -- they are evidence of what was observed/routed, never corrected in place.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e8b4d2f6a1c9'
down_revision: Union[str, Sequence[str], None] = 'a29568b32323'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS machine_integration")

    op.create_table(
        'machine_sources',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('source_code', sa.String(length=120), nullable=False),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('equipment_id', sa.UUID(), nullable=True),
        sa.Column('gateway_id', sa.UUID(), nullable=True),
        sa.Column('protocol_connector', sa.String(length=120), nullable=True),
        sa.Column('line_or_area', sa.String(length=120), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.equipment_assets.id']),
        sa.ForeignKeyConstraint(['gateway_id'], ['edge.edge_gateways.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id', 'source_code'),
        schema='machine_integration',
    )

    op.create_table(
        'signal_mappings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('mapping_key', sa.String(length=120), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('source_address', sa.String(length=255), nullable=False),
        sa.Column('native_type', sa.String(length=60), nullable=False),
        sa.Column('domain_code', sa.String(length=120), nullable=False),
        sa.Column('evidence_class', sa.String(length=30), nullable=False),
        sa.Column('raw_unit', sa.String(length=30), nullable=True),
        sa.Column('canonical_unit', sa.String(length=30), nullable=True),
        sa.Column('conversion_rule_ref', sa.String(length=120), nullable=True),
        sa.Column('quality_mapping_ref', sa.String(length=120), nullable=True),
        sa.Column('timestamp_policy', sa.String(length=60), nullable=True),
        sa.Column('sampling_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('batch_context_policy', sa.String(length=20), nullable=False, server_default='REQUIRED'),
        sa.Column('lifecycle_state', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('drafted_by_user_id', sa.UUID(), nullable=True),
        sa.Column('released_by_user_id', sa.UUID(), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('row_version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['source_id'], ['machine_integration.machine_sources.id']),
        sa.ForeignKeyConstraint(['drafted_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['released_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('mapping_key', 'version'),
        schema='machine_integration',
    )

    op.create_table(
        'batch_contexts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('batch_step_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=10), nullable=False, server_default='OPEN'),
        sa.Column('opened_by_user_id', sa.UUID(), nullable=False),
        sa.Column('opened_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['source_id'], ['machine_integration.machine_sources.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['batch_step_id'], ['ebmr.batch_steps.id']),
        sa.ForeignKeyConstraint(['opened_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='machine_integration',
    )
    op.create_index('ix_batch_contexts_source_status', 'batch_contexts', ['source_id', 'status'], schema='machine_integration')

    op.create_table(
        'machine_evidence_candidates',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('mapping_id', sa.UUID(), nullable=False),
        sa.Column('evidence_class', sa.String(length=30), nullable=False),
        sa.Column('batch_context_id', sa.UUID(), nullable=True),
        sa.Column('domain_code', sa.String(length=120), nullable=False),
        sa.Column('value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('quality', sa.String(length=20), nullable=True),
        sa.Column('freshness', sa.String(length=20), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='CANDIDATE'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['event_id'], ['edge.edge_observations.event_id']),
        sa.ForeignKeyConstraint(['mapping_id'], ['machine_integration.signal_mappings.id']),
        sa.ForeignKeyConstraint(['batch_context_id'], ['machine_integration.batch_contexts.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id'),
        schema='machine_integration',
    )

    op.create_table(
        'machine_alarm_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('mapping_id', sa.UUID(), nullable=False),
        sa.Column('alarm_code', sa.String(length=120), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('batch_context_id', sa.UUID(), nullable=True),
        sa.Column('review_status', sa.String(length=20), nullable=False, server_default='PENDING_REVIEW'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['event_id'], ['edge.edge_observations.event_id']),
        sa.ForeignKeyConstraint(['mapping_id'], ['machine_integration.signal_mappings.id']),
        sa.ForeignKeyConstraint(['batch_context_id'], ['machine_integration.batch_contexts.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id'),
        schema='machine_integration',
    )

    op.create_table(
        'cycle_evidence_manifests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('cycle_id', sa.String(length=120), nullable=False),
        sa.Column('batch_context_id', sa.UUID(), nullable=True),
        sa.Column('mapping_id', sa.UUID(), nullable=True),
        sa.Column('cycle_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cycle_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('event_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('statistics', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_evidence_ref', sa.Text(), nullable=True),
        sa.Column('manifest_hash', sa.String(length=64), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['source_id'], ['machine_integration.machine_sources.id']),
        sa.ForeignKeyConstraint(['batch_context_id'], ['machine_integration.batch_contexts.id']),
        sa.ForeignKeyConstraint(['mapping_id'], ['machine_integration.signal_mappings.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('source_id', 'cycle_id'),
        schema='machine_integration',
    )

    op.create_table(
        'machine_command_profiles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('operation_code', sa.String(length=120), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('lifecycle_state', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('allowed_equipment_classes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('parameter_schema', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('required_role_name', sa.String(length=100), nullable=True),
        sa.Column('allowed_batch_states', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('timeout_ms', sa.Integer(), nullable=False, server_default='30000'),
        sa.Column('requires_readback', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('local_interlock_code', sa.String(length=120), nullable=True),
        sa.Column('mapping_key', sa.String(length=120), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('operation_code', 'version'),
        schema='machine_integration',
    )

    op.create_table(
        'machine_command_requests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('command_profile_id', sa.UUID(), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('requested_by_user_id', sa.UUID(), nullable=False),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('native_response', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('evidence_ref', sa.Text(), nullable=True),
        sa.Column('finalized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['command_profile_id'], ['machine_integration.machine_command_profiles.id']),
        sa.ForeignKeyConstraint(['source_id'], ['machine_integration.machine_sources.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='machine_integration',
    )

    op.create_table(
        'machine_replay_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('requested_by_user_id', sa.UUID(), nullable=False),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('mode', sa.String(length=20), nullable=False),
        sa.Column('event_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='REQUESTED'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='machine_integration',
    )

    op.execute(f"GRANT USAGE ON SCHEMA machine_integration TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON machine_integration.machine_sources TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON machine_integration.signal_mappings TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON machine_integration.batch_contexts TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON machine_integration.machine_evidence_candidates TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON machine_integration.machine_alarm_events TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON machine_integration.cycle_evidence_manifests TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON machine_integration.machine_command_profiles TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON machine_integration.machine_command_requests TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON machine_integration.machine_replay_jobs TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA machine_integration FROM {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON machine_integration.machine_replay_jobs FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON machine_integration.machine_command_requests FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON machine_integration.machine_command_profiles FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON machine_integration.cycle_evidence_manifests FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON machine_integration.machine_alarm_events FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON machine_integration.machine_evidence_candidates FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON machine_integration.batch_contexts FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON machine_integration.signal_mappings FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON machine_integration.machine_sources FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA machine_integration FROM {APP_ROLE}")

    op.drop_table('machine_replay_jobs', schema='machine_integration')
    op.drop_table('machine_command_requests', schema='machine_integration')
    op.drop_table('machine_command_profiles', schema='machine_integration')
    op.drop_table('cycle_evidence_manifests', schema='machine_integration')
    op.drop_table('machine_alarm_events', schema='machine_integration')
    op.drop_table('machine_evidence_candidates', schema='machine_integration')
    op.drop_table('batch_contexts', schema='machine_integration')
    op.drop_table('signal_mappings', schema='machine_integration')
    op.drop_table('machine_sources', schema='machine_integration')
    op.execute("DROP SCHEMA IF EXISTS machine_integration")
