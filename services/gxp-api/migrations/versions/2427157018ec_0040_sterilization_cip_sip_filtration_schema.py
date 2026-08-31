"""0040_sterilization_cip_sip_filtration_schema

Revision ID: 2427157018ec
Revises: 47264b022543
Create Date: 2026-08-25 00:00:00.000000

Document 42 (SPEC-EQP-005) — Sterilization, CIP/SIP & Sterile Filtration Management. Same `equipment`
schema as Documents 38/39/41 (AG-05).

`tenant_id` dropped throughout (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '2427157018ec'
down_revision: Union[str, Sequence[str], None] = '47264b022543'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'process_cycle_profile_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('profile_number', sa.String(length=120), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('process_type', sa.String(length=40), nullable=False),
        sa.Column('equipment_class_id', sa.UUID(), nullable=True),
        sa.Column('load_pattern', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('controller_recipe_ref', sa.String(length=160), nullable=True),
        sa.Column('critical_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('indicator_requirements', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('review_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_reference', sa.String(length=200), nullable=True),
        sa.Column('sterile_status_validity_hours', sa.Integer(), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='RELEASED'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('profile_number', 'version_no'),
        schema='equipment',
    )

    op.create_table(
        'process_cycles',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('process_type', sa.String(length=40), nullable=False),
        sa.Column('equipment_id', sa.UUID(), nullable=False),
        sa.Column('profile_version_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('controller_cycle_id', sa.String(length=160), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('parameter_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('alarm_summary', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('critical_alarm', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('raw_evidence_ref', sa.UUID(), nullable=True),
        sa.Column('started_by_user_id', sa.UUID(), nullable=True),
        sa.Column('reviewer_user_id', sa.UUID(), nullable=True),
        sa.Column('review_signature_id', sa.UUID(), nullable=True),
        sa.Column('requires_deviation', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deviation_reference_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['equipment_id'], ['equipment.equipment_assets.id']),
        sa.ForeignKeyConstraint(['profile_version_id'], ['equipment.process_cycle_profile_versions.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['started_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['reviewer_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment',
    )
    op.create_index('ix_process_cycles_equipment', 'process_cycles', ['equipment_id', 'created_at'], schema='equipment')

    op.create_table(
        'sterilization_load_items',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('cycle_id', sa.UUID(), nullable=False),
        sa.Column('item_type', sa.String(length=40), nullable=False),
        sa.Column('item_reference', sa.String(length=200), nullable=False),
        sa.Column('position', sa.String(length=80), nullable=True),
        sa.Column('sterile_status', sa.String(length=20), nullable=True),
        sa.Column('sterile_status_expiry', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['cycle_id'], ['equipment.process_cycles.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment',
    )
    op.create_index('ix_sterilization_load_items_cycle', 'sterilization_load_items', ['cycle_id'], schema='equipment')

    op.create_table(
        'sterile_filter_uses',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('filter_lot', sa.String(length=120), nullable=True),
        sa.Column('filter_serial', sa.String(length=120), nullable=False),
        sa.Column('filter_type', sa.String(length=80), nullable=True),
        sa.Column('manufacturer', sa.String(length=160), nullable=True),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('sterilization_cycle_id', sa.UUID(), nullable=True),
        sa.Column('housing_location', sa.String(length=160), nullable=True),
        sa.Column('direction', sa.String(length=40), nullable=True),
        sa.Column('installed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('installed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('pre_use_integrity_result', sa.String(length=20), nullable=True),
        sa.Column('pre_use_integrity_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('post_use_integrity_result', sa.String(length=20), nullable=True),
        sa.Column('post_use_integrity_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('process_parameters', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reuse_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='RECEIVED_ELIGIBLE'),
        sa.Column('performer_user_id', sa.UUID(), nullable=True),
        sa.Column('requires_deviation', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deviation_reference_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['sterilization_cycle_id'], ['equipment.process_cycles.id']),
        sa.ForeignKeyConstraint(['installed_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['performer_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.process_cycle_profile_versions TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.process_cycles TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.sterilization_load_items TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.sterile_filter_uses TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON equipment.sterile_filter_uses FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.sterilization_load_items FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.process_cycles FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.process_cycle_profile_versions FROM {APP_ROLE}")
    op.drop_table('sterile_filter_uses', schema='equipment')
    op.drop_table('sterilization_load_items', schema='equipment')
    op.drop_table('process_cycles', schema='equipment')
    op.drop_table('process_cycle_profile_versions', schema='equipment')
