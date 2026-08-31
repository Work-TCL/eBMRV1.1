"""0039_environmental_monitoring_schema

Revision ID: 47264b022543
Revises: 9267c84c368c
Create Date: 2026-08-25 00:00:00.000000

Document 41 (SPEC-EQP-004) — Environmental Monitoring & Cleanroom State Control. Same `equipment` schema
as Documents 38/39 (AG-05). `em_location` references `equipment.equipment_areas` (Document 39).

`tenant_id` dropped throughout (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '47264b022543'
down_revision: Union[str, Sequence[str], None] = '9267c84c368c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'em_program_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('program_number', sa.String(length=120), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('monitoring_types', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('method_version', sa.String(length=80), nullable=True),
        sa.Column('frequency', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('alert_limits', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('action_limits', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('operation_shift_coverage', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('review_trend_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='RELEASED'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('program_number', 'version_no'),
        schema='equipment',
    )

    op.create_table(
        'em_locations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('area_id', sa.UUID(), nullable=False),
        sa.Column('location_code', sa.String(length=120), nullable=False),
        sa.Column('criticality', sa.String(length=20), nullable=True),
        sa.Column('sample_types', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['area_id'], ['equipment.equipment_areas.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('location_code'),
        schema='equipment',
    )

    op.create_table(
        'em_samples_or_readings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('program_version_id', sa.UUID(), nullable=False),
        sa.Column('location_id', sa.UUID(), nullable=False),
        sa.Column('monitoring_type', sa.String(length=60), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('aseptic_operation_id', sa.UUID(), nullable=True),
        sa.Column('instrument_or_media_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('scheduled_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('sampled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('alert_action_status', sa.String(length=20), nullable=True),
        sa.Column('operator_user_id', sa.UUID(), nullable=True),
        sa.Column('reviewer_user_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='SAMPLE_TASK'),
        sa.Column('requires_deviation', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deviation_reference_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['program_version_id'], ['equipment.em_program_versions.id']),
        sa.ForeignKeyConstraint(['location_id'], ['equipment.em_locations.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['operator_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['reviewer_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment',
    )
    op.create_index('ix_em_samples_location', 'em_samples_or_readings', ['location_id', 'created_at'], schema='equipment')

    op.create_table(
        'em_excursions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('sample_id', sa.UUID(), nullable=False),
        sa.Column('area_id', sa.UUID(), nullable=False),
        sa.Column('affected_time_start', sa.DateTime(timezone=True), nullable=True),
        sa.Column('affected_time_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('affected_batch_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('organism_details', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('disposition', sa.String(length=40), nullable=True),
        sa.Column('impact_assessed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('impact_assessed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requires_deviation', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('deviation_reference_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['sample_id'], ['equipment.em_samples_or_readings.id']),
        sa.ForeignKeyConstraint(['area_id'], ['equipment.equipment_areas.id']),
        sa.ForeignKeyConstraint(['impact_assessed_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment',
    )
    op.create_index('ix_em_excursions_area', 'em_excursions', ['area_id'], schema='equipment')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.em_program_versions TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.em_locations TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.em_samples_or_readings TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.em_excursions TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON equipment.em_excursions FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.em_samples_or_readings FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.em_locations FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.em_program_versions FROM {APP_ROLE}")
    op.drop_table('em_excursions', schema='equipment')
    op.drop_table('em_samples_or_readings', schema='equipment')
    op.drop_table('em_locations', schema='equipment')
    op.drop_table('em_program_versions', schema='equipment')
