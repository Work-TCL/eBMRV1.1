"""0021_qc_schema

Revision ID: 4b6e8f0a1c2d
Revises: 9a3d6c1f7e2b
Create Date: 2026-08-24 00:00:00.000000

Document 23 (SPEC-QC-001) -- Native Basic QC & Sampling Specification. Creates the 6 catalogued entities
(`qc_test_specification`, `qc_test_definition`, `qc_sample`, `qc_test_order`, `qc_test_run`, `qc_result`)
plus `qc_result_correction`, a join/staging table implementing the 2-signature correction ceremony
Document 106 row 57 requires (corrector + independent approver) -- not one of the 6 catalogued entities,
same class of addition as Document 18's `supplier_qualification_evidence`.

`qc_test_specification`/`qc_sample`/`qc_result` are DDL-ready in docs/generated/04_DATA_MODEL_CATALOGUE.md;
`qc_test_definition`/`qc_test_order`/`qc_test_run` are prose-only field-name lists, typed here directly as
an ordinary engineering decision (SG-045's precedent, same as every prior additive module).

Real blockers found and NOT built this pass (see SG-057, extended, and new SG-063 in
docs/generated/18_SPEC_GAPS.md): `qc_test_specification.scope_type=='material'` is rejected at the command
layer (no material-specification-version entity exists anywhere in this codebase); `qc_result.
oos_record_id`/`oot_record_id` are unenforced logical-reference columns (Document 25, OOS/OOT Management,
not built yet); `qc_test_run.instrument_ref` is an unenforced logical-reference column (WP-06 Equipment
not built); no Method-master entity exists for QC-FR-004's controlled method-modification workflow.

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
Tables placed in the shared `ebmr` schema, matching the genealogy/qa_review/packaging/supplier_quality/qms
precedent (not a new dedicated schema per module).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '4b6e8f0a1c2d'
down_revision: Union[str, Sequence[str], None] = '9a3d6c1f7e2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'qc_test_specification',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('spec_code', sa.String(length=120), nullable=False),
        sa.Column('version_no', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('scope_type', sa.String(length=40), nullable=False),
        sa.Column('scope_version_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='draft'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sampling_plan', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('released_vault_object_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['released_vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('spec_code', 'version_no'),
        schema='ebmr',
    )

    op.create_table(
        'qc_test_definition',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('specification_id', sa.UUID(), nullable=False),
        sa.Column('test_code', sa.String(length=80), nullable=False),
        sa.Column('test_name', sa.String(length=200), nullable=False),
        sa.Column('method_version', sa.String(length=80), nullable=True),
        sa.Column('result_data_type', sa.String(length=40), nullable=False),
        sa.Column('uom', sa.String(length=40), nullable=True),
        sa.Column('acceptance_rule_business_id', sa.String(length=160), nullable=True),
        sa.Column('trend_rule_business_id', sa.String(length=160), nullable=True),
        sa.Column('required', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('release_blocking', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('review_policy', sa.String(length=80), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['specification_id'], ['ebmr.qc_test_specification.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_qc_test_definition_spec', 'qc_test_definition', ['specification_id'], schema='ebmr')

    op.create_table(
        'qc_sample',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('sample_number', sa.String(length=160), nullable=False),
        sa.Column('sample_type', sa.String(length=50), nullable=False),
        sa.Column('source_type', sa.String(length=50), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=True),
        sa.Column('source_location_ref', sa.String(length=200), nullable=True),
        sa.Column('lot_batch_serial_ref', sa.String(length=200), nullable=True),
        sa.Column('sample_quantity', sa.Numeric(24, 8), nullable=True),
        sa.Column('sample_uom', sa.String(length=40), nullable=True),
        sa.Column('sampled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('sampler_subject_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='planned'),
        sa.Column('stability_study_ref', sa.String(length=160), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sampler_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('sample_number'),
        schema='ebmr',
    )

    op.create_table(
        'qc_test_order',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('sample_id', sa.UUID(), nullable=False),
        sa.Column('test_definition_id', sa.UUID(), nullable=False),
        sa.Column('assigned_analyst_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='created'),
        sa.Column('blocking', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['sample_id'], ['ebmr.qc_sample.id']),
        sa.ForeignKeyConstraint(['test_definition_id'], ['ebmr.qc_test_definition.id']),
        sa.ForeignKeyConstraint(['assigned_analyst_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_qc_test_order_sample', 'qc_test_order', ['sample_id'], schema='ebmr')

    op.create_table(
        'qc_test_run',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('test_order_id', sa.UUID(), nullable=False),
        sa.Column('method_version', sa.String(length=80), nullable=True),
        sa.Column('instrument_ref', sa.String(length=160), nullable=True),
        sa.Column('analyst_id', sa.UUID(), nullable=True),
        sa.Column('sample_amount', sa.Numeric(24, 8), nullable=True),
        sa.Column('reference_standards', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('system_suitability', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_evidence_vault_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('calculation_rule_object_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['test_order_id'], ['ebmr.qc_test_order.id']),
        sa.ForeignKeyConstraint(['analyst_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['calculation_rule_object_id'], ['rules.gxp_rule_definition.rule_object_id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_qc_test_run_order', 'qc_test_run', ['test_order_id'], schema='ebmr')

    op.create_table(
        'qc_result',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('test_order_id', sa.UUID(), nullable=False),
        sa.Column('test_run_id', sa.UUID(), nullable=False),
        sa.Column('result_version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('result_type', sa.String(length=40), nullable=False),
        sa.Column('value_decimal', sa.Numeric(30, 12), nullable=True),
        sa.Column('value_text', sa.Text(), nullable=True),
        sa.Column('value_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('uom', sa.String(length=40), nullable=True),
        sa.Column('acceptance_rule_id', sa.UUID(), nullable=True),
        sa.Column('outcome', sa.String(length=40), nullable=False, server_default='pending'),
        sa.Column('oos_record_id', sa.UUID(), nullable=True),
        sa.Column('oot_record_id', sa.UUID(), nullable=True),
        sa.Column('supersedes_result_id', sa.UUID(), nullable=True),
        sa.Column('recorded_by_user_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['test_order_id'], ['ebmr.qc_test_order.id']),
        sa.ForeignKeyConstraint(['test_run_id'], ['ebmr.qc_test_run.id']),
        sa.ForeignKeyConstraint(['acceptance_rule_id'], ['rules.gxp_rule_definition.rule_object_id']),
        sa.ForeignKeyConstraint(['supersedes_result_id'], ['ebmr.qc_result.id']),
        sa.ForeignKeyConstraint(['recorded_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_qc_result_order', 'qc_result', ['test_order_id'], schema='ebmr')

    op.create_table(
        'qc_result_correction',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('original_result_id', sa.UUID(), nullable=False),
        sa.Column('reason_text', sa.String(length=2000), nullable=False),
        sa.Column('corrected_value_decimal', sa.Numeric(30, 12), nullable=True),
        sa.Column('corrected_value_text', sa.Text(), nullable=True),
        sa.Column('corrected_value_json', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='requested'),
        sa.Column('requested_by_user_id', sa.UUID(), nullable=False),
        sa.Column('requested_signature_id', sa.UUID(), nullable=True),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_signature_id', sa.UUID(), nullable=True),
        sa.Column('resulting_result_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['original_result_id'], ['ebmr.qc_result.id']),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['resulting_result_id'], ['ebmr.qc_result.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )

    # Mutable versioned aggregates: their command handlers UPDATE an existing row (status/state/version).
    for table in ('qc_test_specification', 'qc_sample', 'qc_test_order', 'qc_result_correction'):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.{table} TO {APP_ROLE}")

    # Append-only once written: `qc_test_definition` is fixed at spec-authoring time; `qc_test_run` is a
    # new row per raw-data submission, never edited afterward; `qc_result` is never edited after its
    # creation transaction -- a correction creates a new superseding row (QC-FR-024), so no code path ever
    # needs UPDATE on an already-committed result. No UPDATE grant enforces that at the database privilege
    # level (AG-08), the same pattern `supplier_qualification_evidence` (SG-057's module) already uses.
    for table in ('qc_test_definition', 'qc_test_run', 'qc_result'):
        op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.{table} TO {APP_ROLE}")


def downgrade() -> None:
    for table in (
        'qc_result_correction', 'qc_result', 'qc_test_run', 'qc_test_order',
        'qc_sample', 'qc_test_definition', 'qc_test_specification',
    ):
        op.execute(f"REVOKE ALL ON ebmr.{table} FROM {APP_ROLE}")
    op.drop_table('qc_result_correction', schema='ebmr')
    op.drop_table('qc_result', schema='ebmr')
    op.drop_table('qc_test_run', schema='ebmr')
    op.drop_table('qc_test_order', schema='ebmr')
    op.drop_table('qc_sample', schema='ebmr')
    op.drop_table('qc_test_definition', schema='ebmr')
    op.drop_table('qc_test_specification', schema='ebmr')
