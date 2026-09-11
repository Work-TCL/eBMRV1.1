"""0053_erp_wp07_completion_extensions

Revision ID: b7d3e9a4c1f6
Revises: f8c3d7a1b5e9
Create Date: 2026-08-29 00:00:00.000000

WP-07 (Documents 48-53, SPEC-ERP-001..006) completion pass -- closes the 38 requirements build-status.json
tracked NOT_STARTED. Extends the provisional `erp` schema from migration 0043 (SG-121: schema remains
provisional pending a human amendment to Document 112).

- `integration_inbound_events.external_entity_id` (INT-FR-011): the specific external record an inbound
  event concerns, so a later event for the same record can be compared against the last-processed one for
  staleness. NULL for events this column predates or that carry no per-record identity.
- `integration_circuit_breakers.rate_window_started_at`/`rate_window_count` (INT-FR-024/ERP-ARC-028): a
  proactive per-(instance, operation) quota window, reusing the existing per-operation breaker row rather
  than a new table -- the breaker is already the authoritative per-(instance, operation) reliability state.
- New `integration_security_events` (INT-FR-025): same shape/precedent as `edge.edge_security_events`
  (EDGE-FR-027) -- a payload-hash conflict, idempotency-key reuse with a different payload, or a source
  identity mismatch is a data-integrity/security signal, not an ordinary business rejection.
- New `integration_bulk_jobs` (INT-FR-023): bulk import/export job tracking with a resumable cursor and a
  bounded `failed_records` JSONB list (successes are counted, not individually retained -- the record-level
  detail that actually matters for investigation is which ones failed and why).
- `integration_commands.compensates_command_id`/`gxp_authorization_reference` (INT-FR-016): an external
  reversal is a brand-new command (never a mutation of the original, same "corrections never edit"
  discipline `correction_of_id` already applies), linked to the SUCCEEDED command it reverses and required
  to carry a reference to the authorizing GxP correction/disposition record.
- New `erp_migration_packages` (MDS-FR-028): customer onboarding mapping/import package provenance --
  source file identity, checksum and approval reference. No dedicated function exists in Document 52's own
  catalogue for this; the table is the requirement's full scope (a provenance record, not a workflow).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b7d3e9a4c1f6'
down_revision: Union[str, Sequence[str], None] = 'f8c3d7a1b5e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    # MULTI-FR-024: a GENERIC (custom) instance cannot post writes until explicitly validated -- see
    # commands.py::validate_erp_instance(). NOT NULL DEFAULT false so every pre-existing row (and every
    # named-vendor instance, which never goes through this gate) stays semantically "not yet validated"
    # rather than an ambiguous NULL.
    op.add_column('erp_instances', sa.Column('validated', sa.Boolean(), nullable=False, server_default=sa.false()), schema='erp')
    op.add_column('erp_instances', sa.Column('validated_by_user_id', sa.UUID(), nullable=True), schema='erp')
    op.add_column('erp_instances', sa.Column('validated_at', sa.DateTime(timezone=True), nullable=True), schema='erp')
    op.create_foreign_key(
        'fk_erp_instances_validated_by', 'erp_instances', 'users',
        ['validated_by_user_id'], ['id'], source_schema='erp', referent_schema='iam',
    )

    op.add_column('integration_inbound_events', sa.Column('external_entity_id', sa.String(length=200), nullable=True), schema='erp')
    op.create_index(
        'ix_integration_inbound_events_entity',
        'integration_inbound_events', ['erp_instance_id', 'entity_type', 'external_entity_id'],
        schema='erp',
    )

    op.add_column('integration_circuit_breakers', sa.Column('rate_window_started_at', sa.DateTime(timezone=True), nullable=True), schema='erp')
    op.add_column('integration_circuit_breakers', sa.Column('rate_window_count', sa.Integer(), nullable=False, server_default='0'), schema='erp')

    op.create_table(
        'integration_security_events',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('erp_instance_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=80), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('detail', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('correlation_id', sa.UUID(), nullable=True),
        sa.Column('reported_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['erp_instance_id'], ['erp.erp_instances.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='erp',
    )
    op.create_index('ix_integration_security_events_instance', 'integration_security_events', ['erp_instance_id'], schema='erp')

    op.create_table(
        'integration_bulk_jobs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('erp_instance_id', sa.UUID(), nullable=False),
        sa.Column('job_type', sa.String(length=20), nullable=False),
        sa.Column('entity_type', sa.String(length=40), nullable=False),
        sa.Column('idempotency_key', sa.String(length=200), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='RUNNING'),
        sa.Column('total_records', sa.Integer(), nullable=True),
        sa.Column('succeeded_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('failed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('resume_cursor', sa.String(length=200), nullable=True),
        sa.Column('failed_records', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('started_by_user_id', sa.UUID(), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['erp_instance_id'], ['erp.erp_instances.id']),
        sa.ForeignKeyConstraint(['started_by_user_id'], ['iam.users.id']),
        sa.UniqueConstraint('erp_instance_id', 'idempotency_key', name='uq_integration_bulk_job_idempotency'),
        sa.PrimaryKeyConstraint('id'),
        schema='erp',
    )

    op.add_column('integration_commands', sa.Column('compensates_command_id', sa.UUID(), nullable=True), schema='erp')
    op.add_column('integration_commands', sa.Column('gxp_authorization_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=True), schema='erp')
    op.create_foreign_key(
        'fk_integration_commands_compensates', 'integration_commands', 'integration_commands',
        ['compensates_command_id'], ['id'], source_schema='erp', referent_schema='erp',
    )

    op.create_table(
        'erp_migration_packages',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('erp_instance_id', sa.UUID(), nullable=True),
        sa.Column('package_name', sa.String(length=200), nullable=False),
        sa.Column('source_checksum', sa.String(length=128), nullable=False),
        sa.Column('entity_types', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('imported_by_user_id', sa.UUID(), nullable=False),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approval_reference', sa.String(length=200), nullable=True),
        sa.Column('imported_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['erp_instance_id'], ['erp.erp_instances.id']),
        sa.ForeignKeyConstraint(['imported_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='erp',
    )

    for table in ('integration_security_events', 'integration_bulk_jobs', 'erp_migration_packages'):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON erp.{table} TO {APP_ROLE}")


def downgrade() -> None:
    for table in ('erp_migration_packages', 'integration_bulk_jobs', 'integration_security_events'):
        op.execute(f"REVOKE ALL ON erp.{table} FROM {APP_ROLE}")
        op.drop_table(table, schema='erp')

    op.drop_constraint('fk_integration_commands_compensates', 'integration_commands', schema='erp', type_='foreignkey')
    op.drop_column('integration_commands', 'gxp_authorization_reference', schema='erp')
    op.drop_column('integration_commands', 'compensates_command_id', schema='erp')

    op.drop_column('integration_circuit_breakers', 'rate_window_count', schema='erp')
    op.drop_column('integration_circuit_breakers', 'rate_window_started_at', schema='erp')

    op.drop_index('ix_integration_inbound_events_entity', table_name='integration_inbound_events', schema='erp')
    op.drop_column('integration_inbound_events', 'external_entity_id', schema='erp')

    # IF EXISTS, not op.drop_constraint()/op.drop_column(): migration 0083 (repair migration for this
    # same FK + these same 3 columns, d78ea4eb751a_0083_erp_instances_repair_0053_drift.py) downgrades
    # ahead of this one in a full `alembic downgrade base` walk and already drops all four -- found
    # 2026-09-10 rebuilding ebmr_new_gxp_test end-to-end (PHASE_2_BACKBONE.md Sec 4 item 4). Matches
    # 0083's own DROP ... IF EXISTS idiom so the two stay downgrade-order-independent of each other.
    op.execute("ALTER TABLE erp.erp_instances DROP CONSTRAINT IF EXISTS fk_erp_instances_validated_by")
    op.execute("ALTER TABLE erp.erp_instances DROP COLUMN IF EXISTS validated_at")
    op.execute("ALTER TABLE erp.erp_instances DROP COLUMN IF EXISTS validated_by_user_id")
    op.execute("ALTER TABLE erp.erp_instances DROP COLUMN IF EXISTS validated")
