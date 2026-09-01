"""0079_validation_platform_schema

Revision ID: b3e7d1f4a8c2
Revises: a9c3e7f1d5b8
Create Date: 2026-09-01 00:00:00.000000

WP-12 (Documents 79, 80, 81, 82, 83, 84, 86, 88, 89, 90, 91, 92, 93, 94, 96) -- new `validation` schema,
the 32 owned entities `04_DATA_MODEL_CATALOGUE.md` lists across those documents (see
`app/modules/validation/models.py` for the full field-by-field derivation from each document's terse
catalogue bullets). No `tenant_id` (ADR-0006, same deviation as every other module). `site_id` nullable
on tables whose record class is genuinely site-scoped (VMP, intended-use scope N/A per-plan not
per-table, IQ, infrastructure profile); every other table is platform/product-level.

Signature: Document 106 rows 144-171 (minus the excluded Documents 85/87/95, which belong to WP-14) --
resolved rows are seeded in `scripts/seed.py`/`tests/conftest.py`'s `SIGNATURE_POLICY_FLOOR`. Rows 162/
164/165 (Document 94 "Elevated authority defined by the record class") have no resolvable role or
dispatch table anywhere in this codebase, same as the established SG-160/161 precedent -- deliberately
left unseeded so they fail closed (SIGNATURE_POLICY_UNRESOLVED); see SG-167 in
`docs/generated/18_SPEC_GAPS.md`.

**Expand-only** -- thirty-two brand-new tables in a brand-new schema, no existing table altered, no
backfill. Grants: `USAGE` + `SELECT/INSERT/UPDATE/TRUNCATE` (no `DELETE` -- validation evidence is
append/supersede, never deleted). Reversible: `downgrade()` drops every table and the schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b3e7d1f4a8c2'
down_revision: Union[str, Sequence[str], None] = 'a9c3e7f1d5b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"
SCHEMA = "validation"

_TABLES = (
    "validation_master_plan", "validation_deliverable_requirement", "validation_release_gate",
    "intended_use", "function_risk_assessment",
    "validation_requirement", "trace_link", "requirement_baseline",
    "validation_test_definition", "validation_test_execution",
    "iq_protocol", "iq_execution",
    "oq_suite", "oq_execution",
    "infrastructure_qualification_profile", "infrastructure_fingerprint",
    "part11_scope_assessment", "part11_control_evidence",
    "data_integrity_test_profile", "tamper_test_execution",
    "interface_validation_profile", "interface_test_execution",
    "dr_qualification_scenario", "dr_qualification_execution",
    "security_qualification_suite", "security_qualification_finding",
    "performance_qualification_scenario", "performance_run",
    "validation_exception",
    "validated_state_baseline", "validation_change_impact", "periodic_validation_review",
)


def _std_cols(*, extra_state_default: str = "EFFECTIVE") -> list:
    return [
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    ]


def upgrade() -> None:
    op.execute(f"CREATE SCHEMA IF NOT EXISTS {SCHEMA}")

    # ---- Document 79 --------------------------------------------------------------------------------
    op.create_table(
        'validation_master_plan',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('plan_number', sa.String(length=60), nullable=False),
        sa.Column('scope', sa.Text(), nullable=False),
        sa.Column('regulatory_profiles', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('methodology', sa.Text(), nullable=False),
        sa.Column('responsibilities', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('retention_class', sa.String(length=80), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('released_by_user_id', sa.UUID(), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('plan_number', 'version'),
        schema=SCHEMA,
    )
    op.create_table(
        'validation_deliverable_requirement',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('plan_id', sa.UUID(), nullable=False),
        sa.Column('artifact_type', sa.String(length=80), nullable=False),
        sa.Column('risk_condition', sa.String(length=200), nullable=False),
        sa.Column('owner', sa.String(length=120), nullable=False),
        sa.Column('review_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('signature_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('evidence_type', sa.String(length=80), nullable=False),
        sa.Column('release_blocker', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='REQUIRED'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_val_deliverable_plan_id', 'validation_deliverable_requirement', ['plan_id'], schema=SCHEMA)
    op.create_table(
        'validation_release_gate',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('release_scope', sa.String(length=120), nullable=False),
        sa.Column('environment', sa.String(length=80), nullable=False),
        sa.Column('required_artifact_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('blockers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('decision_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EVALUATED'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )

    # ---- Document 80 --------------------------------------------------------------------------------
    op.create_table(
        'intended_use',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scope_ref', sa.String(length=160), nullable=False),
        sa.Column('scope_version', sa.String(length=40), nullable=False),
        sa.Column('regulated_process', sa.Text(), nullable=False),
        sa.Column('users', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('record_relevance', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('signature_relevance', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_table(
        'function_risk_assessment',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('function_ref', sa.String(length=160), nullable=False),
        sa.Column('function_version', sa.String(length=40), nullable=False),
        sa.Column('failure_modes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('impacts', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('detectability', sa.String(length=10), nullable=False),
        sa.Column('automation_role', sa.String(length=30), nullable=False),
        sa.Column('has_release_or_disposition', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('has_signature_role', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('has_audit_immutability_role', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('has_enforcement_role', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('controls', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('risk_category', sa.String(length=30), nullable=False),
        sa.Column('assurance_method', sa.Text(), nullable=False),
        sa.Column('residual_risk', sa.Text(), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_function_risk_function_ref', 'function_risk_assessment', ['function_ref'], schema=SCHEMA)

    # ---- Document 81 --------------------------------------------------------------------------------
    op.create_table(
        'validation_requirement',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('requirement_code', sa.String(length=40), nullable=False),
        sa.Column('source_document', sa.String(length=80), nullable=False),
        sa.Column('source_section', sa.String(length=120), nullable=False),
        sa.Column('text', sa.Text(), nullable=False),
        sa.Column('requirement_class', sa.String(length=40), nullable=False),
        sa.Column('regulatory_source', sa.String(length=120), nullable=True),
        sa.Column('binding_status', sa.String(length=20), nullable=False, server_default='BINDING'),
        sa.Column('acceptance_criteria', sa.Text(), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('requirement_code', 'version'),
        schema=SCHEMA,
    )
    op.create_table(
        'trace_link',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('source_type', sa.String(length=60), nullable=False),
        sa.Column('source_id', sa.String(length=120), nullable=False),
        sa.Column('source_version', sa.String(length=40), nullable=False),
        sa.Column('target_type', sa.String(length=60), nullable=False),
        sa.Column('target_id', sa.String(length=120), nullable=False),
        sa.Column('target_version', sa.String(length=40), nullable=False),
        sa.Column('relation_type', sa.String(length=20), nullable=False),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_trace_link_source', 'trace_link', ['source_type', 'source_id'], schema=SCHEMA)
    op.create_table(
        'requirement_baseline',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('release_scope', sa.String(length=120), nullable=False),
        sa.Column('customer_scope', sa.String(length=120), nullable=True),
        sa.Column('requirement_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('exclusions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('baseline_hash', sa.String(length=64), nullable=False),
        sa.Column('vault_object_id', sa.UUID(), nullable=True),
        sa.Column('gaps_detected', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='FROZEN'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )

    # ---- Document 82 --------------------------------------------------------------------------------
    op.create_table(
        'validation_test_definition',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('test_code', sa.String(length=40), nullable=False),
        sa.Column('method', sa.String(length=30), nullable=False),
        sa.Column('requirement_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('preconditions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('procedure', sa.Text(), nullable=False),
        sa.Column('expected_results', sa.Text(), nullable=False),
        sa.Column('independent_review_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('test_code', 'version'),
        schema=SCHEMA,
    )
    op.create_table(
        'validation_test_execution',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('test_definition_id', sa.UUID(), nullable=False),
        sa.Column('test_definition_version', sa.BigInteger(), nullable=False),
        sa.Column('environment_fingerprint', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('performer_user_id', sa.UUID(), nullable=True),
        sa.Column('ci_run_ref', sa.String(length=200), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('observations', sa.Text(), nullable=True),
        sa.Column('actual_result', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('blocked_reason', sa.Text(), nullable=True),
        sa.Column('evidence_manifest', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('defect_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('reviewed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('flaky', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_val_test_exec_def_id', 'validation_test_execution', ['test_definition_id'], schema=SCHEMA)

    # ---- Document 83 --------------------------------------------------------------------------------
    op.create_table(
        'iq_protocol',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('environment', sa.String(length=80), nullable=False),
        sa.Column('release_ref', sa.String(length=80), nullable=False),
        sa.Column('deployment_profile', sa.String(length=40), nullable=False),
        sa.Column('expected_components', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('checks', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('acceptance_criteria', sa.Text(), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_table(
        'iq_execution',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('protocol_id', sa.UUID(), nullable=False),
        sa.Column('protocol_version', sa.BigInteger(), nullable=False),
        sa.Column('installed_inventory', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('check_results', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('deviations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('evidence_manifest', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('performer_user_id', sa.UUID(), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('is_delta_iq', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_iq_execution_protocol_id', 'iq_execution', ['protocol_id'], schema=SCHEMA)

    # ---- Document 84 --------------------------------------------------------------------------------
    op.create_table(
        'oq_suite',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('baseline_id', sa.UUID(), nullable=False),
        sa.Column('selected_test_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('selected_evidence_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('exclusions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('environment_fingerprint', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='DERIVED'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_table(
        'oq_execution',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('suite_id', sa.UUID(), nullable=False),
        sa.Column('suite_version', sa.BigInteger(), nullable=False),
        sa.Column('executed_test_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('coverage_basis_points', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('deviations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('reviewed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_oq_execution_suite_id', 'oq_execution', ['suite_id'], schema=SCHEMA)

    # ---- Document 86 --------------------------------------------------------------------------------
    op.create_table(
        'infrastructure_qualification_profile',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('deployment_profile', sa.String(length=40), nullable=False),
        sa.Column('provider', sa.String(length=80), nullable=False),
        sa.Column('required_components', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('control_tests', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('supplier_evidence_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('change_triggers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_table(
        'infrastructure_fingerprint',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('profile_id', sa.UUID(), nullable=False),
        sa.Column('profile_version', sa.BigInteger(), nullable=False),
        sa.Column('captured_versions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('config_hashes', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('resource_sizing', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('network_security_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('time_backup_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('drift_detected', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('drift_detail', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='CAPTURED'),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_infra_fingerprint_profile_id', 'infrastructure_fingerprint', ['profile_id'], schema=SCHEMA)

    # ---- Document 88 --------------------------------------------------------------------------------
    op.create_table(
        'part11_scope_assessment',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('record_or_signature_type', sa.String(length=120), nullable=False),
        sa.Column('predicate_use', sa.Text(), nullable=False),
        sa.Column('system_component', sa.String(length=120), nullable=False),
        sa.Column('context', sa.String(length=10), nullable=False, server_default='CLOSED'),
        sa.Column('applicable', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('customer_responsibilities', sa.Text(), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_table(
        'part11_control_evidence',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scope_assessment_id', sa.UUID(), nullable=False),
        sa.Column('control_citation', sa.String(length=20), nullable=False),
        sa.Column('test_ref', sa.String(length=120), nullable=True),
        sa.Column('result', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('evidence_manifest', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('configuration_ref', sa.String(length=200), nullable=True),
        sa.Column('procedure_ref', sa.String(length=200), nullable=True),
        sa.Column('deviation_ref', sa.String(length=120), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_part11_evidence_assessment_id', 'part11_control_evidence', ['scope_assessment_id'], schema=SCHEMA)

    # ---- Document 89 --------------------------------------------------------------------------------
    op.create_table(
        'data_integrity_test_profile',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('data_class', sa.String(length=80), nullable=False),
        sa.Column('lifecycle', sa.Text(), nullable=False),
        sa.Column('threats', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('controls', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('tests', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_table(
        'tamper_test_execution',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('profile_id', sa.UUID(), nullable=False),
        sa.Column('isolated_snapshot_ref', sa.String(length=200), nullable=False),
        sa.Column('tamper_action', sa.String(length=80), nullable=False),
        sa.Column('verifier_version', sa.String(length=40), nullable=False),
        sa.Column('detected', sa.Boolean(), nullable=True),
        sa.Column('detection_evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('performed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_tamper_test_profile_id', 'tamper_test_execution', ['profile_id'], schema=SCHEMA)

    # ---- Document 90 --------------------------------------------------------------------------------
    op.create_table(
        'interface_validation_profile',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('provider_or_device', sa.String(length=120), nullable=False),
        sa.Column('contract_ref', sa.String(length=120), nullable=False),
        sa.Column('contract_version', sa.String(length=40), nullable=False),
        sa.Column('intended_use', sa.Text(), nullable=False),
        sa.Column('risk_category', sa.String(length=30), nullable=False),
        sa.Column('auth_expectation', sa.String(length=80), nullable=False),
        sa.Column('source_time_quality_expectation', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('failure_scenarios', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_table(
        'interface_test_execution',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('profile_id', sa.UUID(), nullable=False),
        sa.Column('profile_version', sa.BigInteger(), nullable=False),
        sa.Column('scenario', sa.String(length=80), nullable=False),
        sa.Column('raw_inputs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('canonical_outputs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('gxp_result', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('external_reconciliation', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('performed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_iface_test_profile_id', 'interface_test_execution', ['profile_id'], schema=SCHEMA)

    # ---- Document 91 --------------------------------------------------------------------------------
    op.create_table(
        'dr_qualification_scenario',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('failure_type', sa.String(length=80), nullable=False),
        sa.Column('components', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('recovery_method', sa.String(length=80), nullable=False),
        sa.Column('target_rpo_seconds', sa.BigInteger(), nullable=True),
        sa.Column('target_rto_seconds', sa.BigInteger(), nullable=False),
        sa.Column('restore_order', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('acceptance_criteria', sa.Text(), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_table(
        'dr_qualification_execution',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scenario_id', sa.UUID(), nullable=False),
        sa.Column('scenario_version', sa.BigInteger(), nullable=False),
        sa.Column('backup_set_ref', sa.String(length=200), nullable=False),
        sa.Column('restore_point', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rpo_achieved_seconds', sa.BigInteger(), nullable=True),
        sa.Column('rto_achieved_seconds', sa.BigInteger(), nullable=True),
        sa.Column('integrity_checks', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('gxp_smoke_results', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('deviations', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_dr_exec_scenario_id', 'dr_qualification_execution', ['scenario_id'], schema=SCHEMA)

    # ---- Document 92 --------------------------------------------------------------------------------
    op.create_table(
        'security_qualification_suite',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('release_ref', sa.String(length=80), nullable=False),
        sa.Column('deployment_profile', sa.String(length=40), nullable=False),
        sa.Column('threat_control_baseline_ref', sa.String(length=120), nullable=False),
        sa.Column('planned_tests', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='PLANNED'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_table(
        'security_qualification_finding',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('suite_id', sa.UUID(), nullable=False),
        sa.Column('source', sa.String(length=40), nullable=False),
        sa.Column('control_ref', sa.String(length=120), nullable=False),
        sa.Column('severity', sa.String(length=10), nullable=False),
        sa.Column('affected_release', sa.String(length=80), nullable=False),
        sa.Column('vulnerability_ref', sa.String(length=120), nullable=True),
        sa.Column('change_ref', sa.String(length=120), nullable=True),
        sa.Column('deviation_ref', sa.String(length=120), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='OPEN'),
        sa.Column('exception_rationale', sa.Text(), nullable=True),
        sa.Column('retest_ref', sa.String(length=120), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_sec_finding_suite_id', 'security_qualification_finding', ['suite_id'], schema=SCHEMA)

    # ---- Document 93 --------------------------------------------------------------------------------
    op.create_table(
        'performance_qualification_scenario',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('release_ref', sa.String(length=80), nullable=False),
        sa.Column('environment', sa.String(length=80), nullable=False),
        sa.Column('load_model', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('data_cardinality', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('planned_duration_seconds', sa.BigInteger(), nullable=False),
        sa.Column('thresholds', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('nfr_requirement_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='PLANNED'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_table(
        'performance_run',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('scenario_id', sa.UUID(), nullable=False),
        sa.Column('scenario_version', sa.BigInteger(), nullable=False),
        sa.Column('build_ref', sa.String(length=120), nullable=False),
        sa.Column('harness_ref', sa.String(length=120), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('metrics', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('errors', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('resource_usage', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('headroom_basis_points', sa.BigInteger(), nullable=True),
        sa.Column('bottleneck', sa.String(length=120), nullable=True),
        sa.Column('acceptance_result', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('performed_by_user_id', sa.UUID(), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_perf_run_scenario_id', 'performance_run', ['scenario_id'], schema=SCHEMA)

    # ---- Document 94 --------------------------------------------------------------------------------
    op.create_table(
        'validation_exception',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('release_ref', sa.String(length=80), nullable=True),
        sa.Column('exception_type', sa.String(length=30), nullable=False),
        sa.Column('source_execution_type', sa.String(length=60), nullable=False),
        sa.Column('source_execution_id', sa.UUID(), nullable=False),
        sa.Column('original_evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('affected_requirement_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('severity', sa.String(length=10), nullable=False),
        sa.Column('gxp_impact', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('release_impact', sa.String(length=20), nullable=False, server_default='BLOCKING'),
        sa.Column('disposition', sa.String(length=30), nullable=False, server_default='OPEN'),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('issue_ref', sa.String(length=200), nullable=True),
        sa.Column('change_ref', sa.String(length=120), nullable=True),
        sa.Column('qms_deviation_ref', sa.String(length=120), nullable=True),
        sa.Column('retest_plan', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('retest_execution_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('residual_risk_rationale', sa.Text(), nullable=True),
        sa.Column('reopen_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('triaged_by_user_id', sa.UUID(), nullable=True),
        sa.Column('triaged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dispositioned_by_user_id', sa.UUID(), nullable=True),
        sa.Column('dispositioned_at', sa.DateTime(timezone=True), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_val_exception_release_ref', 'validation_exception', ['release_ref'], schema=SCHEMA)

    # ---- Document 96 --------------------------------------------------------------------------------
    op.create_table(
        'validated_state_baseline',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('release_ref', sa.String(length=80), nullable=False),
        sa.Column('environment', sa.String(length=80), nullable=False),
        sa.Column('vsr_ref', sa.String(length=120), nullable=True),
        sa.Column('component_inventory', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='VALIDATED'),
        sa.Column('decommissioned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('decommission_evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_table(
        'validation_change_impact',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('change_ref', sa.String(length=120), nullable=False),
        sa.Column('change_type', sa.String(length=40), nullable=False),
        sa.Column('affected_trace_artifacts', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('is_emergency', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('revalidation_level', sa.String(length=30), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('revalidation_ref', sa.String(length=120), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_table(
        'periodic_validation_review',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('release_ref', sa.String(length=80), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('inputs_considered', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('findings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('actions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('decision', sa.String(length=30), nullable=True),
        sa.Column('performed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('reviewed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='DRAFT'),
        *_std_cols(),
        sa.PrimaryKeyConstraint('id'),
        schema=SCHEMA,
    )
    op.create_index('ix_periodic_review_release_ref', 'periodic_validation_review', ['release_ref'], schema=SCHEMA)

    op.execute(f"GRANT USAGE ON SCHEMA {SCHEMA} TO {APP_ROLE}")
    for t in _TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON {SCHEMA}.{t} TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA {SCHEMA} FROM {APP_ROLE}")


def downgrade() -> None:
    for t in _TABLES:
        op.execute(f"REVOKE ALL ON {SCHEMA}.{t} FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA {SCHEMA} FROM {APP_ROLE}")
    for t in reversed(_TABLES):
        op.drop_table(t, schema=SCHEMA)
    op.execute(f"DROP SCHEMA IF EXISTS {SCHEMA}")
