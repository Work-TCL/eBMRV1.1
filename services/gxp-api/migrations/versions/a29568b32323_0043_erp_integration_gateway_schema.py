"""0043_erp_integration_gateway_schema

Revision ID: a29568b32323
Revises: c1f9a3e7d2b4
Create Date: 2026-08-26 00:00:00.000000

WP-07 (Documents 48-53, SPEC-ERP-001..006) — Enterprise ERP Integration Architecture, adapter contracts,
master-data sync and the shared integration reliability model. New `erp` schema, ten tables.

**Provisional schema** (SG-121 / ADR-0009): the frozen Phase-0 data model catalogue declares zero
entities for all six WP-07 documents, and Document 112 does not cover ERP either. See ADR-0009 for the
full rationale and docs/generated/18_SPEC_GAPS.md SG-121 for the open human-approval gap this migration
is pending.

`tenant_id` dropped throughout (single-organization platform, ADR-0006), same as every prior module.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a29568b32323'
down_revision: Union[str, Sequence[str], None] = 'c1f9a3e7d2b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS erp")
    op.execute(f"GRANT USAGE ON SCHEMA erp TO {APP_ROLE}")

    op.create_table(
        'erp_instances',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('instance_name', sa.String(length=120), nullable=False),
        sa.Column('vendor', sa.String(length=20), nullable=False),
        sa.Column('environment', sa.String(length=20), nullable=False, server_default='SANDBOX'),
        sa.Column('base_url', sa.String(length=500), nullable=False),
        sa.Column('auth_method', sa.String(length=40), nullable=False),
        sa.Column('auth_secret_ref', sa.String(length=200), nullable=True),
        sa.Column('capabilities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('contract_version', sa.String(length=40), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instance_name'),
        schema='erp',
    )

    op.create_table(
        'erp_external_mappings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('erp_instance_id', sa.UUID(), nullable=False),
        sa.Column('entity_type', sa.String(length=40), nullable=False),
        sa.Column('internal_id', sa.UUID(), nullable=True),
        sa.Column('internal_code', sa.String(length=120), nullable=True),
        sa.Column('external_id', sa.String(length=120), nullable=False),
        sa.Column('external_code', sa.String(length=120), nullable=True),
        sa.Column('field_ownership', sa.String(length=10), nullable=False, server_default='ERP'),
        sa.Column('mapping_status', sa.String(length=20), nullable=False, server_default='PROPOSED'),
        sa.Column('match_method', sa.String(length=20), nullable=False, server_default='MANUAL'),
        sa.Column('confidence', sa.Numeric(precision=5, scale=4), nullable=True),
        sa.Column('uom_conversion_factor', sa.Numeric(precision=24, scale=10), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('mapping_hash', sa.String(length=64), nullable=True),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['erp_instance_id'], ['erp.erp_instances.id']),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('erp_instance_id', 'entity_type', 'external_id', name='uq_erp_mapping_external'),
        schema='erp',
    )
    op.create_index('ix_erp_external_mappings_internal', 'erp_external_mappings', ['erp_instance_id', 'entity_type', 'internal_id'], schema='erp')

    op.create_table(
        'erp_mapping_conflicts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('mapping_id', sa.UUID(), nullable=False),
        sa.Column('field_name', sa.String(length=80), nullable=False),
        sa.Column('source_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('proposed_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('current_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='OPEN'),
        sa.Column('requires_qa_review', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('resolution', sa.String(length=400), nullable=True),
        sa.Column('resolution_reason', sa.String(length=400), nullable=True),
        sa.Column('resolved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['mapping_id'], ['erp.erp_external_mappings.id']),
        sa.ForeignKeyConstraint(['resolved_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='erp',
    )
    op.create_index('ix_erp_mapping_conflicts_mapping', 'erp_mapping_conflicts', ['mapping_id'], schema='erp')

    op.create_table(
        'erp_sync_checkpoints',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('erp_instance_id', sa.UUID(), nullable=False),
        sa.Column('entity_type', sa.String(length=40), nullable=False),
        sa.Column('cursor_value', sa.String(length=200), nullable=True),
        sa.Column('last_batch_id', sa.UUID(), nullable=True),
        sa.Column('last_synced_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['erp_instance_id'], ['erp.erp_instances.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('erp_instance_id', 'entity_type', name='uq_erp_sync_checkpoint'),
        schema='erp',
    )

    op.create_table(
        'integration_commands',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('erp_instance_id', sa.UUID(), nullable=False),
        sa.Column('command_type', sa.String(length=80), nullable=False),
        sa.Column('source_event_id', sa.UUID(), nullable=True),
        sa.Column('source_aggregate_type', sa.String(length=80), nullable=True),
        sa.Column('source_aggregate_id', sa.UUID(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=200), nullable=False),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('payload_hash', sa.String(length=64), nullable=False),
        sa.Column('correlation_id', sa.UUID(), nullable=False),
        sa.Column('causation_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('external_reference', sa.String(length=200), nullable=True),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('next_attempt_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_error_category', sa.String(length=30), nullable=True),
        sa.Column('last_error_detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('required_next_action', sa.String(length=400), nullable=True),
        sa.Column('correction_of_id', sa.UUID(), nullable=True),
        sa.Column('cancelled_reason', sa.String(length=400), nullable=True),
        sa.Column('cancelled_by_user_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['erp_instance_id'], ['erp.erp_instances.id']),
        sa.ForeignKeyConstraint(['correction_of_id'], ['erp.integration_commands.id']),
        sa.ForeignKeyConstraint(['cancelled_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('erp_instance_id', 'idempotency_key', name='uq_integration_command_idempotency'),
        schema='erp',
    )
    op.create_index('ix_integration_commands_state', 'integration_commands', ['erp_instance_id', 'state'], schema='erp')

    op.create_table(
        'integration_command_attempts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('command_id', sa.UUID(), nullable=False),
        sa.Column('attempt_no', sa.Integer(), nullable=False),
        sa.Column('attempted_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('outcome', sa.String(length=20), nullable=False),
        sa.Column('error_category', sa.String(length=30), nullable=True),
        sa.Column('error_detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('http_status', sa.Integer(), nullable=True),
        sa.Column('backoff_seconds', sa.Integer(), nullable=True),
        sa.Column('external_reference', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['command_id'], ['erp.integration_commands.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='erp',
    )
    op.create_index('ix_integration_command_attempts_command', 'integration_command_attempts', ['command_id'], schema='erp')

    op.create_table(
        'integration_inbound_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('erp_instance_id', sa.UUID(), nullable=False),
        sa.Column('external_event_id', sa.String(length=200), nullable=False),
        sa.Column('entity_type', sa.String(length=40), nullable=True),
        sa.Column('source_version', sa.String(length=80), nullable=True),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('payload_hash', sa.String(length=64), nullable=False),
        sa.Column('processing_state', sa.String(length=20), nullable=False, server_default='RECEIVED'),
        sa.Column('error_category', sa.String(length=30), nullable=True),
        sa.Column('error_detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('correlation_id', sa.UUID(), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('applied_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['erp_instance_id'], ['erp.erp_instances.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('erp_instance_id', 'external_event_id', name='uq_integration_inbound_event'),
        schema='erp',
    )

    op.create_table(
        'integration_reconciliation_runs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('erp_instance_id', sa.UUID(), nullable=False),
        sa.Column('scope', sa.String(length=80), nullable=False),
        sa.Column('reconciliation_type', sa.String(length=40), nullable=False),
        sa.Column('cutoff_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('query_keys', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('mapping_version_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='RUNNING'),
        sa.Column('started_by_user_id', sa.UUID(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('difference_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['erp_instance_id'], ['erp.erp_instances.id']),
        sa.ForeignKeyConstraint(['started_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='erp',
    )

    op.create_table(
        'integration_reconciliation_differences',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('difference_type', sa.String(length=30), nullable=False),
        sa.Column('internal_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('external_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('field_name', sa.String(length=80), nullable=True),
        sa.Column('internal_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('external_value', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('requires_qa_hold', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('resolution_status', sa.String(length=20), nullable=False, server_default='OPEN'),
        sa.Column('resolution_reason', sa.String(length=400), nullable=True),
        sa.Column('resolved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['erp.integration_reconciliation_runs.id']),
        sa.ForeignKeyConstraint(['resolved_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='erp',
    )
    op.create_index('ix_integration_reconciliation_differences_run', 'integration_reconciliation_differences', ['run_id'], schema='erp')

    op.create_table(
        'integration_circuit_breakers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('erp_instance_id', sa.UUID(), nullable=False),
        sa.Column('operation', sa.String(length=80), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='CLOSED'),
        sa.Column('failure_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('opened_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('last_probe_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['erp_instance_id'], ['erp.erp_instances.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('erp_instance_id', 'operation', name='uq_integration_circuit_breaker'),
        schema='erp',
    )

    for table in (
        'erp_instances', 'erp_external_mappings', 'erp_mapping_conflicts', 'erp_sync_checkpoints',
        'integration_commands', 'integration_command_attempts', 'integration_inbound_events',
        'integration_reconciliation_runs', 'integration_reconciliation_differences', 'integration_circuit_breakers',
    ):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON erp.{table} TO {APP_ROLE}")


def downgrade() -> None:
    for table in (
        'integration_circuit_breakers', 'integration_reconciliation_differences', 'integration_reconciliation_runs',
        'integration_inbound_events', 'integration_command_attempts', 'integration_commands',
        'erp_sync_checkpoints', 'erp_mapping_conflicts', 'erp_external_mappings', 'erp_instances',
    ):
        op.execute(f"REVOKE ALL ON erp.{table} FROM {APP_ROLE}")
        op.drop_table(table, schema='erp')
    op.execute(f"REVOKE USAGE ON SCHEMA erp FROM {APP_ROLE}")
    op.execute("DROP SCHEMA IF EXISTS erp")
