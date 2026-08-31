"""0019_qms_deviation_schema

Revision ID: 7f4c9a1e2b3d
Revises: 1a2b3c4d5e6f
Create Date: 2026-08-24 00:00:02.000000

Document 26 (SPEC-QMS-001) — Deviation & Investigation Management. New `qms` schema (same USAGE + DML
grant pattern as `rules`/`materials`, migration 0009's precedent). Creates the module's 2 owned entities,
both typed directly this pass — see app/modules/qms/models.py's module docstring for the field-shape
reasoning (SG-045's precedent) and for what is deliberately deferred (SG-059..SG-062 in
docs/generated/18_SPEC_GAPS.md).

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '7f4c9a1e2b3d'
down_revision: Union[str, Sequence[str], None] = '1a2b3c4d5e6f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS qms")

    op.create_table(
        'deviation_record',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('quality_event_id', sa.UUID(), nullable=False),
        sa.Column('deviation_number', sa.String(length=120), nullable=False),
        sa.Column('deviation_type', sa.String(length=40), nullable=False),
        sa.Column('source_type', sa.String(length=40), nullable=False),
        sa.Column('source_id', sa.UUID(), nullable=False),
        sa.Column('source_version', sa.Integer(), nullable=True),
        sa.Column('severity', sa.String(length=40), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='OPEN'),
        sa.Column('owner_subject_id', sa.UUID(), nullable=False),
        sa.Column('investigator_subject_id', sa.UUID(), nullable=True),
        sa.Column('planned', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('planned_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('immediate_correction', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('containment', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('investigation_plan', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('cross_batch_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('root_cause', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('impact_assessment', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('disposition_code', sa.String(length=80), nullable=True),
        sa.Column('disposition_rationale', sa.Text(), nullable=True),
        sa.Column('capa_required', sa.Boolean(), nullable=True),
        sa.Column('capa_rationale', sa.Text(), nullable=True),
        sa.Column('change_control_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('change_control_rationale', sa.Text(), nullable=True),
        sa.Column('training_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('training_rationale', sa.Text(), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('extension_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('closure_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('reopen_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['investigator_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quality_event_id'),
        sa.UniqueConstraint('deviation_number'),
        schema='qms',
    )
    op.create_index('ix_deviation_record_state_due', 'deviation_record', ['site_id', 'state', 'due_date'], schema='qms')
    op.create_index('ix_deviation_record_severity', 'deviation_record', ['site_id', 'severity', 'state'], schema='qms')

    op.create_table(
        'deviation_impact_link',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('deviation_id', sa.UUID(), nullable=False),
        sa.Column('impacted_record_type', sa.String(length=60), nullable=False),
        sa.Column('impacted_record_id', sa.UUID(), nullable=False),
        sa.Column('impacted_record_version', sa.Integer(), nullable=True),
        sa.Column('impact_category', sa.String(length=60), nullable=True),
        sa.Column('hold_disposition_reference', sa.String(length=200), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['deviation_id'], ['qms.deviation_record.id']),
        sa.ForeignKeyConstraint(['created_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_deviation_impact_link_deviation', 'deviation_impact_link', ['deviation_id'], schema='qms')

    op.execute(f"GRANT USAGE ON SCHEMA qms TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.deviation_record TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON qms.deviation_impact_link TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA qms FROM {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON qms.deviation_impact_link FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.deviation_record FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA qms FROM {APP_ROLE}")
    op.drop_table('deviation_impact_link', schema='qms')
    op.drop_table('deviation_record', schema='qms')
    op.execute("DROP SCHEMA IF EXISTS qms")
