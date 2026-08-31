"""0055_ddcp_documents_55_56_57_common_schema

Revision ID: c2d5f8a3e7b1
Revises: a1c4e8f2d6b3
Create Date: 2026-08-29 00:00:00.000000

WP-08 (Documents 55/56/57, SPEC-DDCP-002/003/004) — SG-150: no Document 112 schema exists for any of these
three documents. Adds the four new tables the provisional schema needs (`ddcp_process_operation`,
`ddcp_unit_binding`, `reusable_device_pairing`, `drug_coating_usage_ledger`) into the existing `ddcp` schema
(created by migration 0052). Document 54's own nine tables are reused unchanged by all three documents --
see docs/generated/18_SPEC_GAPS.md SG-150 for the full reuse-vs-new-table rationale.

`tenant_id` dropped throughout (single-organization platform, ADR-0006), same as every prior module.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c2d5f8a3e7b1'
down_revision: Union[str, Sequence[str], None] = 'a1c4e8f2d6b3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'ddcp_process_operation',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('operation_type', sa.String(length=40), nullable=False),
        sa.Column('line_id', sa.UUID(), nullable=True),
        sa.Column('equipment_id', sa.UUID(), nullable=True),
        sa.Column('program_id', sa.String(length=120), nullable=True),
        sa.Column('program_version', sa.String(length=40), nullable=True),
        sa.Column('process_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('environment_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('readiness_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('interventions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('alarms', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('requires_deviation', sa.Boolean(), nullable=False, server_default='false'),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='SETUP'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['line_id'], ['equipment.equipment_areas.id']),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.equipment_assets.id']),
        sa.CheckConstraint('ended_at IS NULL OR ended_at >= started_at', name='ck_ddcp_process_operation_end_after_start'),
        schema='ddcp',
    )
    op.create_index('ix_ddcp_process_operation_batch_id', 'ddcp_process_operation', ['batch_id'], schema='ddcp')

    op.create_table(
        'ddcp_unit_binding',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('binding_type', sa.String(length=60), nullable=False),
        sa.Column('primary_unit_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('bound_constituent_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='BOUND'),
        sa.Column('bound_by', sa.UUID(), nullable=True),
        sa.Column('bound_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['bound_by'], ['iam.users.id']),
        schema='ddcp',
    )
    op.create_index('ix_ddcp_unit_binding_batch_id', 'ddcp_unit_binding', ['batch_id'], schema='ddcp')

    op.create_table(
        'reusable_device_pairing',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('reusable_device_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('cartridge_lot_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('compatibility_status', sa.String(length=30), nullable=False, server_default='PENDING_REVIEW'),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('paired_by', sa.UUID(), nullable=True),
        sa.Column('paired_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['paired_by'], ['iam.users.id']),
        schema='ddcp',
    )

    op.create_table(
        'drug_coating_usage_ledger',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('usage_type', sa.String(length=30), nullable=False),
        sa.Column('quantity', sa.Numeric(18, 6), nullable=False),
        sa.Column('uom', sa.String(length=20), nullable=False),
        sa.Column('recorded_by', sa.UUID(), nullable=True),
        sa.Column('reason_code', sa.String(length=80), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('correction_of_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['recorded_by'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['correction_of_id'], ['ddcp.drug_coating_usage_ledger.id']),
        sa.CheckConstraint('quantity >= 0', name='ck_drug_coating_usage_ledger_quantity_non_negative'),
        schema='ddcp',
    )
    op.create_index('ix_drug_coating_usage_ledger_batch_id', 'drug_coating_usage_ledger', ['batch_id'], schema='ddcp')

    for table in ('ddcp_process_operation', 'ddcp_unit_binding', 'reusable_device_pairing', 'drug_coating_usage_ledger'):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ddcp.{table} TO ebmr_new_gxp_app")


def downgrade() -> None:
    op.drop_table('drug_coating_usage_ledger', schema='ddcp')
    op.drop_table('reusable_device_pairing', schema='ddcp')
    op.drop_table('ddcp_unit_binding', schema='ddcp')
    op.drop_table('ddcp_process_operation', schema='ddcp')
