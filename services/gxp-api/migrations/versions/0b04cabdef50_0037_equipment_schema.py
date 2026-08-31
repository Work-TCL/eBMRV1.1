"""0037_equipment_schema

Revision ID: 0b04cabdef50
Revises: a70420cdcf3f
Create Date: 2026-08-25 00:00:00.000000

Document 38 (SPEC-EQP-001) — Equipment, Calibration, Qualification & Maintenance. First document in
WP-06; new `equipment` schema. Exactly the 4 authoritative entities the spec's own §5 Data Model and
`docs/generated/05_DATABASE_OWNERSHIP_MATRIX.md` declare -- see app/modules/equipment/models.py's module
docstring for what is captured-not-enforced instead of a 5th table.

`tenant_id` dropped throughout (single-organization platform, ADR-0006), same deviation as every additive
migration since 0002. `equipment_use_logs` is append-only (AG-08): no UPDATE grant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '0b04cabdef50'
down_revision: Union[str, Sequence[str], None] = 'a70420cdcf3f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS equipment")

    op.create_table(
        'equipment_assets',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('equipment_code', sa.String(length=120), nullable=False),
        sa.Column('equipment_class_id', sa.UUID(), nullable=True),
        sa.Column('manufacturer', sa.String(length=255), nullable=True),
        sa.Column('model', sa.String(length=160), nullable=True),
        sa.Column('serial_no', sa.String(length=160), nullable=True),
        sa.Column('location_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='PLANNED'),
        sa.Column('qualification_status', sa.String(length=40), nullable=True),
        sa.Column('qualification_effective_date', sa.Date(), nullable=True),
        sa.Column('qualification_expiry_date', sa.Date(), nullable=True),
        sa.Column('qualification_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('calibration_status', sa.String(length=40), nullable=True),
        sa.Column('next_calibration_due_date', sa.Date(), nullable=True),
        sa.Column('maintenance_status', sa.String(length=40), nullable=True),
        sa.Column('next_maintenance_due_date', sa.Date(), nullable=True),
        sa.Column('cleanliness_status', sa.String(length=40), nullable=True),
        sa.Column('dedicated', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('firmware_version', sa.String(length=80), nullable=True),
        sa.Column('runtime_hours', sa.Numeric(18, 2), nullable=True),
        sa.Column('runtime_cycles', sa.Integer(), nullable=True),
        sa.Column('hold_flag', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('hold_reason', sa.String(length=2000), nullable=True),
        sa.Column('hold_source', sa.String(length=20), nullable=True),
        sa.Column('change_control_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['change_control_id'], ['qms.change_control.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('equipment_code'),
        schema='equipment',
    )
    op.create_index('ix_equipment_assets_site_state', 'equipment_assets', ['site_id', 'state'], schema='equipment')

    op.create_table(
        'equipment_calibrations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('equipment_asset_id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('calibration_plan_ref', sa.String(length=160), nullable=True),
        sa.Column('procedure_version', sa.String(length=80), nullable=True),
        sa.Column('frequency_days', sa.Integer(), nullable=True),
        sa.Column('tolerance', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('due_date', sa.Date(), nullable=False),
        sa.Column('performed_date', sa.Date(), nullable=True),
        sa.Column('as_found', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('adjustments', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('as_left', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('standard_reference', sa.String(length=160), nullable=True),
        sa.Column('standard_calibration_status', sa.String(length=40), nullable=True),
        sa.Column('standard_expiry_date', sa.Date(), nullable=True),
        sa.Column('performer_user_id', sa.UUID(), nullable=True),
        sa.Column('reviewer_user_id', sa.UUID(), nullable=True),
        sa.Column('result', sa.String(length=20), nullable=True),
        sa.Column('impact_assessment_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deviation_reference_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='due'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['equipment_asset_id'], ['equipment.equipment_assets.id']),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['performer_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['reviewer_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment',
    )
    op.create_index('ix_equipment_calibrations_asset', 'equipment_calibrations', ['equipment_asset_id'], schema='equipment')

    op.create_table(
        'maintenance_work_orders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('equipment_asset_id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('type', sa.String(length=20), nullable=False),
        sa.Column('fault_description', sa.Text(), nullable=True),
        sa.Column('diagnosis', sa.Text(), nullable=True),
        sa.Column('work_performed', sa.Text(), nullable=True),
        sa.Column('parts_used', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('procedure_version', sa.String(length=80), nullable=True),
        sa.Column('frequency_days', sa.Integer(), nullable=True),
        sa.Column('next_due_date', sa.Date(), nullable=True),
        sa.Column('expected_downtime_hours', sa.Numeric(10, 2), nullable=True),
        sa.Column('technician_user_id', sa.UUID(), nullable=False),
        sa.Column('post_maintenance_verification_required', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_by_user_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='open'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['equipment_asset_id'], ['equipment.equipment_assets.id']),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['technician_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['verified_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment',
    )
    op.create_index('ix_maintenance_work_orders_asset', 'maintenance_work_orders', ['equipment_asset_id'], schema='equipment')

    op.create_table(
        'equipment_use_logs',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('equipment_asset_id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('log_type', sa.String(length=20), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('step_id', sa.UUID(), nullable=True),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('operation', sa.String(length=200), nullable=True),
        sa.Column('operator_user_id', sa.UUID(), nullable=True),
        sa.Column('source', sa.String(length=20), nullable=False, server_default='manual'),
        sa.Column('cleaning_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('event_reference', sa.String(length=200), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['equipment_asset_id'], ['equipment.equipment_assets.id']),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['step_id'], ['ebmr.batch_steps.id']),
        sa.ForeignKeyConstraint(['operator_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment',
    )
    op.create_index('ix_equipment_use_logs_asset', 'equipment_use_logs', ['equipment_asset_id', 'occurred_at'], schema='equipment')

    op.execute(f"GRANT USAGE ON SCHEMA equipment TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.equipment_assets TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.equipment_calibrations TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.maintenance_work_orders TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON equipment.equipment_use_logs TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA equipment FROM {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON equipment.equipment_use_logs FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.maintenance_work_orders FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.equipment_calibrations FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.equipment_assets FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA equipment FROM {APP_ROLE}")
    op.drop_table('equipment_use_logs', schema='equipment')
    op.drop_table('maintenance_work_orders', schema='equipment')
    op.drop_table('equipment_calibrations', schema='equipment')
    op.drop_table('equipment_assets', schema='equipment')
    op.execute("DROP SCHEMA IF EXISTS equipment")
