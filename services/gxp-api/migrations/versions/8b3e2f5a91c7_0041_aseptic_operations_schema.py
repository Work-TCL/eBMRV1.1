"""0041_aseptic_operations_schema

Revision ID: 8b3e2f5a91c7
Revises: 2427157018ec
Create Date: 2026-08-25 00:00:00.000000

Document 40 (SPEC-EQP-003) — Sterile / Aseptic Manufacturing Operations. Same `equipment` schema as
Documents 38/39/41/42 (AG-05). Built last in the WP-06 pass (dependency order 39 -> 41 -> 42 -> 40).

`tenant_id` dropped throughout (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '8b3e2f5a91c7'
down_revision: Union[str, Sequence[str], None] = '2427157018ec'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'aseptic_profile_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('profile_number', sa.String(length=120), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('product_id', sa.UUID(), nullable=True),
        sa.Column('required_area_classification', sa.String(length=40), nullable=True),
        sa.Column('personnel_qualifications', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('sterile_input_requirements', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('intervention_catalogue', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('hold_time_rules', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('em_dependencies', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('filter_sterilization_requirements', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('release_blockers', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_reference', sa.String(length=200), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='RELEASED'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['product_id'], ['ebmr.products.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('profile_number', 'version_no'),
        schema='equipment',
    )

    op.create_table(
        'aseptic_operations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('batch_step_id', sa.UUID(), nullable=True),
        sa.Column('area_id', sa.UUID(), nullable=False),
        sa.Column('profile_version_id', sa.UUID(), nullable=False),
        sa.Column('sterile_input_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('equipment_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='PREPARATION'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('readiness_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('started_by_user_id', sa.UUID(), nullable=True),
        sa.Column('completed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('complete_signature_id', sa.UUID(), nullable=True),
        sa.Column('requires_deviation', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deviation_reference_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['batch_step_id'], ['ebmr.batch_steps.id']),
        sa.ForeignKeyConstraint(['area_id'], ['equipment.equipment_areas.id']),
        sa.ForeignKeyConstraint(['profile_version_id'], ['equipment.aseptic_profile_versions.id']),
        sa.ForeignKeyConstraint(['started_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['completed_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment',
    )
    op.create_index('ix_aseptic_operations_area', 'aseptic_operations', ['area_id', 'created_at'], schema='equipment')

    op.create_table(
        'aseptic_interventions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('operation_id', sa.UUID(), nullable=False),
        sa.Column('intervention_type', sa.String(length=40), nullable=False),
        sa.Column('planned', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('operator_user_id', sa.UUID(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('location', sa.String(length=160), nullable=True),
        sa.Column('reason', sa.String(length=400), nullable=True),
        sa.Column('impacted_unit_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('evidence_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('requires_deviation', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('deviation_reference_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['operation_id'], ['equipment.aseptic_operations.id']),
        sa.ForeignKeyConstraint(['operator_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment',
    )
    op.create_index('ix_aseptic_interventions_operation', 'aseptic_interventions', ['operation_id'], schema='equipment')

    op.create_table(
        'aseptic_event_timeline',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('operation_id', sa.UUID(), nullable=False),
        sa.Column('event_type', sa.String(length=80), nullable=False),
        sa.Column('source', sa.String(length=80), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False, server_default='info'),
        sa.Column('payload', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['operation_id'], ['equipment.aseptic_operations.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='equipment',
    )
    op.create_index('ix_aseptic_event_timeline_operation', 'aseptic_event_timeline', ['operation_id'], schema='equipment')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.aseptic_profile_versions TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.aseptic_operations TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.aseptic_interventions TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON equipment.aseptic_event_timeline TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON equipment.aseptic_event_timeline FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.aseptic_interventions FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.aseptic_operations FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON equipment.aseptic_profile_versions FROM {APP_ROLE}")
    op.drop_table('aseptic_event_timeline', schema='equipment')
    op.drop_table('aseptic_interventions', schema='equipment')
    op.drop_table('aseptic_operations', schema='equipment')
    op.drop_table('aseptic_profile_versions', schema='equipment')
