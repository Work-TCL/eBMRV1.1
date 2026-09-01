"""0080_ai_governance_schema

Revision ID: d4f8b1e6c9a3
Revises: b3e7d1f4a8c2
Create Date: 2026-09-01 00:00:00.000000

Document 105 (SPEC-AI-001) -- AI Governance for Regulated Manufacturing. New `ai_governance` schema,
11 tables -- see app/modules/ai_governance/models.py and ARCHITECTURE.md for why these tables exist
despite the sub-prompt's stale "DATA MODEL (0 entities)" line (Phase-0 generation gap; the function
catalogue FN-1005..FN-1017 is unambiguous that every one of these 13 functions commits a
domain+version+audit+outbox transaction).

**Expand-only** -- eleven brand-new tables in a brand-new schema, no existing table altered, no
backfill. Grants: `USAGE` + `SELECT/INSERT/UPDATE/TRUNCATE` (no `DELETE` -- AI-FR-034/053 "without
rewriting historical output" / "historical logs retained": disposition and advisory rows are
append-only; a purge path does not exist in this pass). All sizes are `BigInteger`; no float columns
(the evaluation-report `metrics` JSONB stores integer basis points, matching the codebase-wide "no
binary float" convention). Forward + downgrade + re-upgrade tested on the restored test database.
Reversible: `downgrade()` drops all eleven tables, their indexes and the schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd4f8b1e6c9a3'
down_revision: Union[str, Sequence[str], None] = 'b3e7d1f4a8c2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"
_TABLES = (
    "ai_use_case", "ai_risk_assessment", "ai_model_deployment", "ai_tool_registry",
    "ai_prompt_version", "ai_advisory_log", "ai_tool_decision", "ai_disposition",
    "ai_evaluation_report", "ai_release_gate", "ai_prompt_injection_event", "ai_provider_switch",
)


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ai_governance")

    op.create_table(
        'ai_use_case',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('name', sa.String(length=200), nullable=False),
        sa.Column('use_case_class', sa.String(length=30), nullable=False),
        sa.Column('purpose', sa.Text(), nullable=False),
        sa.Column('users', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('data_classes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('decision_impact', sa.Text(), nullable=False),
        sa.Column('proposed_tools', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('proposed_models', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('latest_risk_assessment_id', sa.UUID(), nullable=True),
        sa.Column('retirement_reason', sa.Text(), nullable=True),
        sa.Column('retirement_replacement', sa.String(length=200), nullable=True),
        sa.Column('retirement_effective_date', sa.Date(), nullable=True),
        sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='ai_governance',
    )
    op.create_index('ix_ai_use_case_state', 'ai_use_case', ['state'], schema='ai_governance')

    op.create_table(
        'ai_risk_assessment',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('use_case_id', sa.UUID(), nullable=False),
        sa.Column('failure_modes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('gxp_impact', sa.Text(), nullable=False),
        sa.Column('people_impact', sa.Text(), nullable=True),
        sa.Column('data_impact', sa.Text(), nullable=True),
        sa.Column('security_impact', sa.Text(), nullable=True),
        sa.Column('human_oversight', sa.Text(), nullable=False),
        sa.Column('prohibited_decisions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('evaluation_required', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('approval_required', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('actor_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['use_case_id'], ['ai_governance.ai_use_case.id']),
        schema='ai_governance',
    )
    op.create_index('ix_ai_risk_assessment_use_case', 'ai_risk_assessment', ['use_case_id'], schema='ai_governance')

    op.create_table(
        'ai_model_deployment',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('use_case_id', sa.UUID(), nullable=True),
        sa.Column('provider', sa.String(length=80), nullable=False),
        sa.Column('model', sa.String(length=120), nullable=False),
        sa.Column('model_version', sa.String(length=40), nullable=False),
        sa.Column('deployment_type', sa.String(length=20), nullable=False),
        sa.Column('endpoint', sa.String(length=400), nullable=True),
        sa.Column('context_window', sa.BigInteger(), nullable=True),
        sa.Column('data_terms', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('evaluation_report_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='APPROVED'),
        sa.Column('effective_from', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['use_case_id'], ['ai_governance.ai_use_case.id']),
        schema='ai_governance',
    )
    op.create_index('ix_ai_model_deployment_state', 'ai_model_deployment', ['state'], schema='ai_governance')

    op.create_table(
        'ai_tool_registry',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('tool_name', sa.String(length=120), nullable=False),
        sa.Column('risk_class', sa.String(length=20), nullable=False, server_default='READ'),
        sa.Column('allowed_scopes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('tool_name', name='uq_ai_tool_registry_name'),
        schema='ai_governance',
    )

    op.create_table(
        'ai_prompt_version',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('use_case_id', sa.UUID(), nullable=False),
        sa.Column('template_name', sa.String(length=120), nullable=False),
        sa.Column('version_label', sa.String(length=40), nullable=False),
        sa.Column('content_hash', sa.String(length=128), nullable=False),
        sa.Column('active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('released_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['use_case_id'], ['ai_governance.ai_use_case.id']),
        schema='ai_governance',
    )

    op.create_table(
        'ai_advisory_log',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('use_case_id', sa.UUID(), nullable=False),
        sa.Column('model_deployment_id', sa.UUID(), nullable=True),
        sa.Column('prompt_version_id', sa.UUID(), nullable=True),
        sa.Column('context_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('output_hash', sa.String(length=128), nullable=True),
        sa.Column('output_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('correlation_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['use_case_id'], ['ai_governance.ai_use_case.id']),
        sa.ForeignKeyConstraint(['model_deployment_id'], ['ai_governance.ai_model_deployment.id']),
        sa.ForeignKeyConstraint(['prompt_version_id'], ['ai_governance.ai_prompt_version.id']),
        schema='ai_governance',
    )
    op.create_index('ix_ai_advisory_log_use_case', 'ai_advisory_log', ['use_case_id'], schema='ai_governance')

    op.create_table(
        'ai_tool_decision',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('use_case_id', sa.UUID(), nullable=False),
        sa.Column('advisory_id', sa.UUID(), nullable=True),
        sa.Column('tool_name', sa.String(length=120), nullable=False),
        sa.Column('args_hash', sa.String(length=128), nullable=True),
        sa.Column('decision', sa.String(length=10), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['use_case_id'], ['ai_governance.ai_use_case.id']),
        sa.ForeignKeyConstraint(['advisory_id'], ['ai_governance.ai_advisory_log.id']),
        schema='ai_governance',
    )
    op.create_index('ix_ai_tool_decision_use_case', 'ai_tool_decision', ['use_case_id'], schema='ai_governance')

    op.create_table(
        'ai_disposition',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('advisory_id', sa.UUID(), nullable=False),
        sa.Column('disposition', sa.String(length=20), nullable=False),
        sa.Column('comments', sa.Text(), nullable=True),
        sa.Column('downstream_record_ref', sa.String(length=200), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['advisory_id'], ['ai_governance.ai_advisory_log.id']),
        schema='ai_governance',
    )
    op.create_index('ix_ai_disposition_advisory', 'ai_disposition', ['advisory_id'], schema='ai_governance')

    op.create_table(
        'ai_evaluation_report',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('use_case_id', sa.UUID(), nullable=False),
        sa.Column('model_deployment_id', sa.UUID(), nullable=True),
        sa.Column('prompt_version_id', sa.UUID(), nullable=True),
        sa.Column('dataset_ref', sa.String(length=200), nullable=False),
        sa.Column('scenario_classes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('critical_failures', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('actor_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['use_case_id'], ['ai_governance.ai_use_case.id']),
        sa.ForeignKeyConstraint(['model_deployment_id'], ['ai_governance.ai_model_deployment.id']),
        sa.ForeignKeyConstraint(['prompt_version_id'], ['ai_governance.ai_prompt_version.id']),
        schema='ai_governance',
    )
    op.create_index('ix_ai_evaluation_report_use_case', 'ai_evaluation_report', ['use_case_id'], schema='ai_governance')

    op.create_table(
        'ai_release_gate',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('use_case_id', sa.UUID(), nullable=False),
        sa.Column('evaluation_report_id', sa.UUID(), nullable=False),
        sa.Column('incidents_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('vendor_security_status', sa.Text(), nullable=True),
        sa.Column('decision', sa.String(length=10), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('decided_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['use_case_id'], ['ai_governance.ai_use_case.id']),
        sa.ForeignKeyConstraint(['evaluation_report_id'], ['ai_governance.ai_evaluation_report.id']),
        schema='ai_governance',
    )

    op.create_table(
        'ai_prompt_injection_event',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('use_case_id', sa.UUID(), nullable=False),
        sa.Column('content_hash', sa.String(length=128), nullable=False),
        sa.Column('detected', sa.Boolean(), nullable=False),
        sa.Column('matched_patterns', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('action_taken', sa.String(length=20), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['use_case_id'], ['ai_governance.ai_use_case.id']),
        schema='ai_governance',
    )
    op.create_index('ix_ai_prompt_injection_use_case', 'ai_prompt_injection_event', ['use_case_id'], schema='ai_governance')

    op.create_table(
        'ai_provider_switch',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('use_case_id', sa.UUID(), nullable=False),
        sa.Column('from_model_deployment_id', sa.UUID(), nullable=True),
        sa.Column('to_model_deployment_id', sa.UUID(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('switched_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['use_case_id'], ['ai_governance.ai_use_case.id']),
        sa.ForeignKeyConstraint(['from_model_deployment_id'], ['ai_governance.ai_model_deployment.id']),
        sa.ForeignKeyConstraint(['to_model_deployment_id'], ['ai_governance.ai_model_deployment.id']),
        schema='ai_governance',
    )

    op.execute(f"GRANT USAGE ON SCHEMA ai_governance TO {APP_ROLE}")
    for t in _TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ai_governance.{t} TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA ai_governance FROM {APP_ROLE}")


def downgrade() -> None:
    for t in _TABLES:
        op.execute(f"REVOKE ALL ON ai_governance.{t} FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA ai_governance FROM {APP_ROLE}")

    op.drop_table('ai_provider_switch', schema='ai_governance')
    op.drop_index('ix_ai_prompt_injection_use_case', table_name='ai_prompt_injection_event', schema='ai_governance')
    op.drop_table('ai_prompt_injection_event', schema='ai_governance')
    op.drop_table('ai_release_gate', schema='ai_governance')
    op.drop_index('ix_ai_evaluation_report_use_case', table_name='ai_evaluation_report', schema='ai_governance')
    op.drop_table('ai_evaluation_report', schema='ai_governance')
    op.drop_index('ix_ai_disposition_advisory', table_name='ai_disposition', schema='ai_governance')
    op.drop_table('ai_disposition', schema='ai_governance')
    op.drop_index('ix_ai_tool_decision_use_case', table_name='ai_tool_decision', schema='ai_governance')
    op.drop_table('ai_tool_decision', schema='ai_governance')
    op.drop_index('ix_ai_advisory_log_use_case', table_name='ai_advisory_log', schema='ai_governance')
    op.drop_table('ai_advisory_log', schema='ai_governance')
    op.drop_table('ai_prompt_version', schema='ai_governance')
    op.drop_table('ai_tool_registry', schema='ai_governance')
    op.drop_index('ix_ai_model_deployment_state', table_name='ai_model_deployment', schema='ai_governance')
    op.drop_table('ai_model_deployment', schema='ai_governance')
    op.drop_index('ix_ai_risk_assessment_use_case', table_name='ai_risk_assessment', schema='ai_governance')
    op.drop_table('ai_risk_assessment', schema='ai_governance')
    op.drop_index('ix_ai_use_case_state', table_name='ai_use_case', schema='ai_governance')
    op.drop_table('ai_use_case', schema='ai_governance')
    op.execute("DROP SCHEMA IF EXISTS ai_governance")
