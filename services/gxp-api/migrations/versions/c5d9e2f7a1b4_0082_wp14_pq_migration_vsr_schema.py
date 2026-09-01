"""0082_wp14_pq_migration_vsr_schema

Revision ID: c5d9e2f7a1b4
Revises: e1a2b3c4d5e6
Create Date: 2026-09-01 00:00:00.000000

WP-14 (Documents 85 / 87 / 95 -- SPEC-VAL-007 / 009 / 017) -- Customer Deployment / PQ / Go-Live.
Seven tables *added to the existing `validation` schema* WP-12 created in migration 0079 (see
`app/modules/validation/models_wp14.py`):

  Document 85 -- `pq_scenario`, `pq_execution`
  Document 87 -- `migration_validation_plan`, `migration_run`, `migration_reconciliation`
  Document 95 -- `validation_summary_report`, `validated_release_authorization`

These are exactly the entities `04_DATA_MODEL_CATALOGUE.md` lists for Documents 85/87/95 -- WP-12
deliberately excluded them (they belong to WP-14, see `app/modules/validation/__init__.py`). The
function catalogue FN-0823..FN-0928 confirms every one of these 16 functions commits a
domain+version+audit+outbox transaction.

**Expand-only** -- seven brand-new tables in the already-existing `validation` schema, no existing
table altered, no backfill. The schema, its `USAGE` grant and its `REVOKE CREATE` are already in
place from migration 0079, so this migration only creates tables and grants
`SELECT/INSERT/UPDATE/TRUNCATE` (no `DELETE` -- validation evidence is append/supersede, never
deleted). All counts/sizes are `BigInteger`; no float columns. Forward + `downgrade -1` +
re-`upgrade head` tested on the restored test database. Reversible: `downgrade()` drops the seven
tables and their indexes only (the `validation` schema itself is left in place -- WP-12 owns it).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c5d9e2f7a1b4'
down_revision: Union[str, Sequence[str], None] = 'e1a2b3c4d5e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"
SCHEMA = "validation"
_TABLES = (
    "pq_scenario", "pq_execution",
    "migration_validation_plan", "migration_run", "migration_reconciliation",
    "validation_summary_report", "validated_release_authorization",
)


def _common_tail() -> list:
    return [
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    ]


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    # ---- Document 85 (SPEC-VAL-007) -------------------------------------------------------------------
    op.create_table(
        'pq_scenario',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('scenario_number', sa.String(length=60), nullable=False),
        sa.Column('product_profile', sa.String(length=40), nullable=True),
        sa.Column('process_area', sa.String(length=40), nullable=False),
        sa.Column('intended_workflow', sa.Text(), nullable=False),
        sa.Column('representative_roles', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('training_prerequisites', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('prerequisites', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('steps', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('interfaces_equipment', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('exception_paths', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('acceptance_criteria', sa.Text(), nullable=False),
        sa.Column('is_uat', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('vmp_equivalence_ref', sa.String(length=200), nullable=True),
        sa.Column('is_template', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('participants', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('authored_by_user_id', sa.UUID(), nullable=True),
        sa.Column('retention_class', sa.String(length=80), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='DRAFT'),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        *_common_tail(),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('scenario_number', 'version', name='uq_pq_scenario_number_version'),
        schema=SCHEMA,
    )
    op.create_index('ix_pq_scenario_state', 'pq_scenario', ['state'], schema=SCHEMA)

    op.create_table(
        'pq_execution',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scenario_id', sa.UUID(), nullable=False),
        sa.Column('scenario_version', sa.BigInteger(), nullable=False),
        sa.Column('prior_execution_id', sa.UUID(), nullable=True),
        sa.Column('participant_identities', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('environment', sa.String(length=120), nullable=False),
        sa.Column('config_ref', sa.String(length=200), nullable=False),
        sa.Column('dataset_ref', sa.String(length=200), nullable=True),
        sa.Column('step_results', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('observations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('deviations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('evidence_manifest', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('result', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('go_live_blocker', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
        *_common_tail(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['scenario_id'], [f'{SCHEMA}.pq_scenario.id']),
        schema=SCHEMA,
    )
    op.create_index('ix_pq_execution_scenario', 'pq_execution', ['scenario_id'], schema=SCHEMA)

    # ---- Document 87 (SPEC-VAL-009) -----------------------------------------------------------------
    op.create_table(
        'migration_validation_plan',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('plan_number', sa.String(length=60), nullable=False),
        sa.Column('source_system', sa.String(length=120), nullable=False),
        sa.Column('target_system', sa.String(length=120), nullable=False, server_default='eBMR/eDHR platform'),
        sa.Column('scope', sa.Text(), nullable=False),
        sa.Column('cutoff_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_snapshot_ref', sa.String(length=300), nullable=False),
        sa.Column('source_snapshot_hash', sa.String(length=128), nullable=False),
        sa.Column('source_timezone', sa.String(length=60), nullable=True),
        sa.Column('mappings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('mapping_version', sa.String(length=40), nullable=False),
        sa.Column('transform_version', sa.String(length=40), nullable=False),
        sa.Column('reconciliation_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('acceptance_criteria', sa.Text(), nullable=False),
        sa.Column('source_profile', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('authored_by_user_id', sa.UUID(), nullable=True),
        sa.Column('regulated_history_strategy', sa.Text(), nullable=False),
        sa.Column('rollback_strategy', sa.Text(), nullable=False),
        sa.Column('legacy_access_strategy', sa.Text(), nullable=False),
        sa.Column('retention_class', sa.String(length=80), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='DRAFT'),
        *_common_tail(),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_number', 'version', name='uq_migration_plan_number_version'),
        schema=SCHEMA,
    )
    op.create_index('ix_migration_plan_state', 'migration_validation_plan', ['state'], schema=SCHEMA)

    op.create_table(
        'migration_run',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('plan_id', sa.UUID(), nullable=False),
        sa.Column('plan_version', sa.BigInteger(), nullable=False),
        sa.Column('run_type', sa.String(length=20), nullable=False),
        sa.Column('run_number', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('prior_run_id', sa.UUID(), nullable=True),
        sa.Column('source_hash', sa.String(length=128), nullable=False),
        sa.Column('is_delta', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('sandbox', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('scripts_config', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('counts', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('control_totals', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('identity_map', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('rejected_records', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('attachments', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('legacy_signatures', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('legacy_audit', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('target_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='RUNNING'),
        sa.Column('retention_class', sa.String(length=80), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='RUNNING'),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        *_common_tail(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['plan_id'], [f'{SCHEMA}.migration_validation_plan.id']),
        schema=SCHEMA,
    )
    op.create_index('ix_migration_run_plan', 'migration_run', ['plan_id'], schema=SCHEMA)

    op.create_table(
        'migration_reconciliation',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('run_id', sa.UUID(), nullable=False),
        sa.Column('run_version', sa.BigInteger(), nullable=False),
        sa.Column('reconciliation_profile', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('count_comparison', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('hash_comparison', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('control_total_comparison', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('critical_field_comparison', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('attachment_comparison', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('reference_integrity', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('deviations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('outcome', sa.String(length=10), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='COMPLETED'),
        *_common_tail(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['run_id'], [f'{SCHEMA}.migration_run.id']),
        schema=SCHEMA,
    )
    op.create_index('ix_migration_reconciliation_run', 'migration_reconciliation', ['run_id'], schema=SCHEMA)

    # ---- Document 95 (SPEC-VAL-017) ---------------------------------------------------------------
    op.create_table(
        'validation_summary_report',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('report_number', sa.String(length=60), nullable=False),
        sa.Column('release_ref', sa.String(length=200), nullable=False),
        sa.Column('customer', sa.String(length=200), nullable=True),
        sa.Column('environment', sa.String(length=120), nullable=False),
        sa.Column('intended_use', sa.Text(), nullable=False),
        sa.Column('config_scope', sa.Text(), nullable=False),
        sa.Column('baselines', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('execution_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('traceability_status', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('deviations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('security_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('performance_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('dr_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('migration_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('part11_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('customer_responsibilities', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('known_limitations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('recommendation', sa.String(length=40), nullable=False),
        sa.Column('recommendation_by_user_id', sa.UUID(), nullable=True),
        sa.Column('recommendation_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('evidence_manifest_ref', sa.String(length=200), nullable=False),
        sa.Column('decision', sa.String(length=20), nullable=True),
        sa.Column('decision_conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('vault_object_id', sa.UUID(), nullable=True),
        sa.Column('retention_class', sa.String(length=80), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='DRAFT'),
        *_common_tail(),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('report_number', 'version', name='uq_vsr_number_version'),
        schema=SCHEMA,
    )
    op.create_index('ix_vsr_state', 'validation_summary_report', ['state'], schema=SCHEMA)

    op.create_table(
        'validated_release_authorization',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('vsr_id', sa.UUID(), nullable=False),
        sa.Column('vsr_version', sa.BigInteger(), nullable=False),
        sa.Column('authorization_number', sa.String(length=60), nullable=False),
        sa.Column('release_identity', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('artifact_digests', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('config_fingerprint', sa.String(length=128), nullable=False),
        sa.Column('environment', sa.String(length=120), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('go_live_readiness', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('decision', sa.String(length=20), nullable=False),
        sa.Column('conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('authorized_by_user_id', sa.UUID(), nullable=True),
        sa.Column('authorized_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('deployment_check', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('post_go_live', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('retention_class', sa.String(length=80), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='AUTHORIZED'),
        *_common_tail(),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['vsr_id'], [f'{SCHEMA}.validation_summary_report.id']),
        sa.UniqueConstraint('authorization_number', 'version', name='uq_release_auth_number_version'),
        schema=SCHEMA,
    )
    op.create_index('ix_release_auth_state', 'validated_release_authorization', ['state'], schema=SCHEMA)

    for t in _TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON {SCHEMA}.{t} TO {APP_ROLE}")


def downgrade() -> None:
    for t in _TABLES:
        op.execute(f"REVOKE ALL ON {SCHEMA}.{t} FROM {APP_ROLE}")

    op.drop_index('ix_release_auth_state', table_name='validated_release_authorization', schema=SCHEMA)
    op.drop_table('validated_release_authorization', schema=SCHEMA)
    op.drop_index('ix_vsr_state', table_name='validation_summary_report', schema=SCHEMA)
    op.drop_table('validation_summary_report', schema=SCHEMA)
    op.drop_index('ix_migration_reconciliation_run', table_name='migration_reconciliation', schema=SCHEMA)
    op.drop_table('migration_reconciliation', schema=SCHEMA)
    op.drop_index('ix_migration_run_plan', table_name='migration_run', schema=SCHEMA)
    op.drop_table('migration_run', schema=SCHEMA)
    op.drop_index('ix_migration_plan_state', table_name='migration_validation_plan', schema=SCHEMA)
    op.drop_table('migration_validation_plan', schema=SCHEMA)
    op.drop_index('ix_pq_execution_scenario', table_name='pq_execution', schema=SCHEMA)
    op.drop_table('pq_execution', schema=SCHEMA)
    op.drop_index('ix_pq_scenario_state', table_name='pq_scenario', schema=SCHEMA)
    op.drop_table('pq_scenario', schema=SCHEMA)
