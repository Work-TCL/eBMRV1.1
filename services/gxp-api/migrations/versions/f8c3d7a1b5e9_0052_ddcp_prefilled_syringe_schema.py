"""0052_ddcp_prefilled_syringe_schema

Revision ID: f8c3d7a1b5e9
Revises: e7b3f9a2c6d4
Create Date: 2026-08-29 00:00:00.000000

WP-08 (Document 54, SPEC-DDCP-001, PFS-FR-001..030) — Prefilled Syringe & Injectable DDCP Manufacturing
Profile. New `ddcp` schema, nine tables. Unlike WP-07's provisional ERP schema, Document 112 (Entity
Schema Completion & Migration Contract Addendum) already approves the DDL for this module -- see
docs/generated/18_SPEC_GAPS.md SG-148 for the two deliberate deviations from Document 112's literal DDL
(tenant_id dropped per ADR-0006, site_id added per Document 54's own universal-aggregate text) and the
module docstring in `app/modules/ddcp/models.py` for the full rationale.

`tenant_id` dropped throughout (single-organization platform, ADR-0006), same as every prior module.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f8c3d7a1b5e9'
down_revision: Union[str, Sequence[str], None] = 'e7b3f9a2c6d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS ddcp")
    op.execute(f"GRANT USAGE ON SCHEMA ddcp TO {APP_ROLE}")

    op.create_table(
        'ddcp_profile_version',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('profile_code', sa.String(length=80), nullable=False),
        sa.Column('subtype', sa.String(length=80), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='DRAFT'),
        sa.Column('dosage_form', sa.String(length=80), nullable=True),
        sa.Column('presentation', sa.String(length=80), nullable=True),
        sa.Column('constituent_architecture', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('required_controls', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('release_checkpoint_set', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('vault_object_id', sa.UUID(), nullable=True),
        sa.Column('released_by', sa.UUID(), nullable=True),
        sa.Column('release_signature_id', sa.UUID(), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['released_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id', 'profile_code', 'version'),
        schema='ddcp',
    )

    op.create_table(
        'constituent_requirement',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('ddcp_profile_version_id', sa.UUID(), nullable=False),
        sa.Column('constituent_type', sa.String(length=40), nullable=False),
        sa.Column('component_role', sa.String(length=80), nullable=False),
        sa.Column('required_state', sa.String(length=60), nullable=False),
        sa.Column('material_spec_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('attribute_requirements', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('mandatory', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('sequence_no', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['ddcp_profile_version_id'], ['ddcp.ddcp_profile_version.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('ddcp_profile_version_id', 'component_role', 'sequence_no'),
        schema='ddcp',
    )
    op.create_index('ix_constituent_requirement_profile', 'constituent_requirement', ['ddcp_profile_version_id', 'constituent_type'], schema='ddcp')

    op.create_table(
        'constituent_handoff',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('from_constituent', sa.String(length=40), nullable=False),
        sa.Column('to_constituent', sa.String(length=80), nullable=False),
        sa.Column('source_batch_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('attributes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('accepted_by', sa.UUID(), nullable=True),
        sa.Column('acceptance_signature_id', sa.UUID(), nullable=True),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='PENDING'),
        sa.Column('rejection_reason', sa.Text(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['accepted_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ddcp',
    )
    op.create_index('ix_constituent_handoff_batch', 'constituent_handoff', ['batch_id'], schema='ddcp')
    op.create_index('ix_constituent_handoff_state', 'constituent_handoff', ['state'], schema='ddcp')

    op.create_table(
        'fill_operation',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('line_id', sa.UUID(), nullable=False),
        sa.Column('filler_equipment_id', sa.UUID(), nullable=False),
        sa.Column('fill_program_id', sa.String(length=120), nullable=False),
        sa.Column('fill_program_version', sa.String(length=40), nullable=False),
        sa.Column('product_contact_path', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('target_fill', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('target_fill_uom', sa.String(length=20), nullable=False),
        sa.Column('target_fill_uom_id', sa.UUID(), nullable=True),
        sa.Column('cycle_group', sa.String(length=80), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('line_readiness_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('machine_count_start', sa.BigInteger(), nullable=True),
        sa.Column('machine_count_end', sa.BigInteger(), nullable=True),
        sa.Column('interventions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('alarms', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('requires_deviation', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='SETUP'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('ended_at IS NULL OR ended_at >= started_at', name='ck_fill_operation_end_after_start'),
        sa.CheckConstraint('target_fill > 0', name='ck_fill_operation_target_fill_positive'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['line_id'], ['equipment.equipment_areas.id']),
        sa.ForeignKeyConstraint(['filler_equipment_id'], ['equipment.equipment_assets.id']),
        sa.ForeignKeyConstraint(['target_fill_uom_id'], ['rules.gxp_uom.uom_id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ddcp',
    )
    op.create_index('ix_fill_operation_batch', 'fill_operation', ['batch_id'], schema='ddcp')
    op.create_index('ix_fill_operation_line_started', 'fill_operation', ['line_id', 'started_at'], schema='ddcp')

    op.create_table(
        'production_count_ledger',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('count_type', sa.String(length=60), nullable=False),
        sa.Column('source', sa.String(length=40), nullable=False),
        sa.Column('quantity', sa.BigInteger(), nullable=False),
        sa.Column('uom', sa.String(length=20), nullable=False, server_default='EA'),
        sa.Column('recorded_by', sa.UUID(), nullable=True),
        sa.Column('device_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reason_code', sa.String(length=80), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('correction_of_id', sa.UUID(), nullable=True),
        sa.Column('source_event_id', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('quantity >= 0', name='ck_production_count_ledger_quantity_non_negative'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['recorded_by'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['correction_of_id'], ['ddcp.production_count_ledger.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ddcp',
    )
    op.create_index('ix_production_count_ledger_batch_type', 'production_count_ledger', ['batch_id', 'count_type'], schema='ddcp')
    op.create_index('ix_production_count_ledger_occurred', 'production_count_ledger', ['occurred_at'], schema='ddcp')
    op.create_index('ix_production_count_ledger_source_event', 'production_count_ledger', ['batch_id', 'source_event_id'], schema='ddcp')

    op.create_table(
        'device_assembly_record',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('unit_identifier', sa.String(length=120), nullable=True),
        sa.Column('assembly_step', sa.String(length=80), nullable=False),
        sa.Column('component_lot_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('equipment_id', sa.UUID(), nullable=True),
        sa.Column('process_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('performed_by', sa.UUID(), nullable=True),
        sa.Column('performed_signature_id', sa.UUID(), nullable=True),
        sa.Column('verified_by', sa.UUID(), nullable=True),
        sa.Column('verified_signature_id', sa.UUID(), nullable=True),
        sa.Column('result', sa.String(length=30), nullable=False),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.CheckConstraint('verified_by IS NULL OR verified_by <> performed_by', name='ck_device_assembly_independent_verify'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.equipment_assets.id']),
        sa.ForeignKeyConstraint(['performed_by'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['verified_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ddcp',
    )
    op.create_index('ix_device_assembly_record_batch', 'device_assembly_record', ['batch_id'], schema='ddcp')
    op.create_index('ix_device_assembly_record_unit', 'device_assembly_record', ['unit_identifier'], schema='ddcp')

    op.create_table(
        'device_functional_test_link',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('test_type', sa.String(length=80), nullable=False),
        sa.Column('qc_record_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('sample_plan_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('method_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('result_state', sa.String(length=30), nullable=False, server_default='PENDING'),
        sa.Column('blocks_release', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('linked_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ddcp',
    )
    op.create_index('ix_device_functional_test_link_batch_state', 'device_functional_test_link', ['batch_id', 'result_state'], schema='ddcp')

    op.create_table(
        'ddcp_release_checkpoint',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('checkpoint_code', sa.String(length=80), nullable=False),
        sa.Column('required_evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('blocker_state', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='OPEN'),
        sa.Column('decided_by', sa.UUID(), nullable=True),
        sa.Column('decision_signature_id', sa.UUID(), nullable=True),
        sa.Column('decided_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['decided_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_id', 'checkpoint_code'),
        schema='ddcp',
    )
    op.create_index('ix_ddcp_release_checkpoint_batch_state', 'ddcp_release_checkpoint', ['batch_id', 'state'], schema='ddcp')

    op.create_table(
        'batch_evidence_manifest',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('manifest_version', sa.BigInteger(), nullable=False),
        sa.Column('evidence_set', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('digest', sa.String(length=128), nullable=False),
        sa.Column('generated_by', sa.UUID(), nullable=False),
        sa.Column('generated_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('vault_object_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='DRAFT'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['generated_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_id', 'manifest_version'),
        schema='ddcp',
    )
    op.create_index('ix_batch_evidence_manifest_batch_state', 'batch_evidence_manifest', ['batch_id', 'state'], schema='ddcp')

    for table in (
        'ddcp_profile_version', 'constituent_requirement', 'constituent_handoff', 'fill_operation',
        'production_count_ledger', 'device_assembly_record', 'device_functional_test_link',
        'ddcp_release_checkpoint', 'batch_evidence_manifest',
    ):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ddcp.{table} TO {APP_ROLE}")


def downgrade() -> None:
    for table in (
        'batch_evidence_manifest', 'ddcp_release_checkpoint', 'device_functional_test_link',
        'device_assembly_record', 'production_count_ledger', 'fill_operation', 'constituent_handoff',
        'constituent_requirement', 'ddcp_profile_version',
    ):
        op.execute(f"REVOKE ALL ON ddcp.{table} FROM {APP_ROLE}")
        op.drop_table(table, schema='ddcp')
    op.execute(f"REVOKE USAGE ON SCHEMA ddcp FROM {APP_ROLE}")
    op.execute("DROP SCHEMA IF EXISTS ddcp")
