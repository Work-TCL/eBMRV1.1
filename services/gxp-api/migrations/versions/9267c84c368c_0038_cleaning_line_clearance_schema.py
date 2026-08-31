"""0038_cleaning_line_clearance_schema

Revision ID: 9267c84c368c
Revises: 0b04cabdef50
Create Date: 2026-08-25 00:00:00.000000

Document 39 (SPEC-EQP-002) — Cleaning, Sanitization & Line Clearance. Same `equipment` schema as Document
38 (AG-05). `equipment_areas` is a new shared master (no area/room entity existed before this pass) --
consumed later by Documents 40/41's own migrations. `equipment_procedure_versions`/`equipment_areas` are
seed-only (no CRUD endpoint in Document 39's own API list, same precedent as `material.WarehouseLocation`).

`tenant_id` dropped throughout (single-organization platform, ADR-0006), same deviation as every additive
migration since 0002.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '9267c84c368c'
down_revision: Union[str, Sequence[str], None] = '0b04cabdef50'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'equipment_areas',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('area_code', sa.String(length=120), nullable=False),
        sa.Column('area_type', sa.String(length=60), nullable=True),
        sa.Column('classification', sa.String(length=40), nullable=True),
        sa.Column('criticality', sa.String(length=20), nullable=True),
        sa.Column('cleanliness_status', sa.String(length=40), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('area_code'),
        schema='equipment',
    )

    op.create_table(
        'cleaning_procedure_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('procedure_number', sa.String(length=120), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('scope_equipment_id', sa.UUID(), nullable=True),
        sa.Column('scope_area_id', sa.UUID(), nullable=True),
        sa.Column('cleaning_type', sa.String(length=40), nullable=False),
        sa.Column('agents', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('steps', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('disassembly_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('sample_inspection_requirements', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('dirty_hold_limit_minutes', sa.Integer(), nullable=True),
        sa.Column('clean_hold_limit_minutes', sa.Integer(), nullable=True),
        sa.Column('validation_reference', sa.String(length=200), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='RELEASED'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['scope_equipment_id'], ['equipment.equipment_assets.id']),
        sa.ForeignKeyConstraint(['scope_area_id'], ['equipment.equipment_areas.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('procedure_number', 'version_no'),
        schema='equipment',
    )

    op.create_table(
        'cleaning_executions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('equipment_id', sa.UUID(), nullable=True),
        sa.Column('area_id', sa.UUID(), nullable=True),
        sa.Column('procedure_version_id', sa.UUID(), nullable=False),
        sa.Column('batch_context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('critical', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='CLEANING'),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('dirty_since', sa.DateTime(timezone=True), nullable=False),
        sa.Column('clean_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('agents_used', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('steps_log', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('previous_batch_identity_removed', sa.Boolean(), nullable=True),
        sa.Column('disassembly_verified', sa.Boolean(), nullable=True),
        sa.Column('inspection_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('swab_sample_id', sa.UUID(), nullable=True),
        sa.Column('performer_user_id', sa.UUID(), nullable=True),
        sa.Column('reviewer_user_id', sa.UUID(), nullable=True),
        sa.Column('verification_result', sa.String(length=20), nullable=True),
        sa.Column('dirty_hold_exceeded', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('requires_deviation', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deviation_reference_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.equipment_assets.id']),
        sa.ForeignKeyConstraint(['area_id'], ['equipment.equipment_areas.id']),
        sa.ForeignKeyConstraint(['procedure_version_id'], ['equipment.cleaning_procedure_versions.id']),
        sa.ForeignKeyConstraint(['performer_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['reviewer_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment',
    )
    op.create_index('ix_cleaning_executions_equipment', 'cleaning_executions', ['equipment_id', 'created_at'], schema='equipment')
    op.create_index('ix_cleaning_executions_area', 'cleaning_executions', ['area_id', 'created_at'], schema='equipment')

    op.create_table(
        'line_clearances',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('area_id', sa.UUID(), nullable=True),
        sa.Column('previous_batch_id', sa.UUID(), nullable=True),
        sa.Column('next_batch_id', sa.UUID(), nullable=True),
        sa.Column('checklist_version', sa.String(length=80), nullable=True),
        sa.Column('items', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('critical', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('performer_user_id', sa.UUID(), nullable=True),
        sa.Column('verifier_user_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='NOT_STARTED'),
        sa.Column('expiry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['area_id'], ['equipment.equipment_areas.id']),
        sa.ForeignKeyConstraint(['previous_batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['next_batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['performer_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['verifier_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.equipment_areas TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.cleaning_procedure_versions TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.cleaning_executions TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.line_clearances TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON equipment.line_clearances FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.cleaning_executions FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.cleaning_procedure_versions FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.equipment_areas FROM {APP_ROLE}")
    op.drop_table('line_clearances', schema='equipment')
    op.drop_table('cleaning_executions', schema='equipment')
    op.drop_table('cleaning_procedure_versions', schema='equipment')
    op.drop_table('equipment_areas', schema='equipment')
