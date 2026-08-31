"""0024_change_control_schema

Revision ID: 3f7a1c9e5b2d
Revises: 7c9d1e3f5a2b
Create Date: 2026-08-24 00:00:05.000000

Document 29 (SPEC-QMS-004) — Change Control. Same owner service as Documents 26-28
(services/gxp-api/src/modules/qms), so `change_control`, `change_affected_object` and `change_task` are
added to the existing `qms` schema. All three typed directly this pass — see
app/modules/qms/change_models.py's module docstring (SG-045's precedent) and
docs/generated/18_SPEC_GAPS.md SG-070..SG-072 for what is deliberately deferred.

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '3f7a1c9e5b2d'
down_revision: Union[str, Sequence[str], None] = '7c9d1e3f5a2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'change_control',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('quality_event_id', sa.UUID(), nullable=False),
        sa.Column('change_number', sa.String(length=120), nullable=False),
        sa.Column('change_type', sa.String(length=50), nullable=False),
        sa.Column('classification', sa.String(length=40), nullable=False),
        sa.Column('current_state', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('proposed_state', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('owner_subject_id', sa.UUID(), nullable=False),
        sa.Column('risk_ref', sa.UUID(), nullable=True),
        sa.Column('regulatory_impact', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('validation_impact', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('training_impact', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('impact_assessment', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('emergency', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('emergency_reason', sa.Text(), nullable=True),
        sa.Column('retrospective_review', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('retrospective_review_completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('effective_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('cancel_reason', sa.Text(), nullable=True),
        sa.Column('cancelled_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closure_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quality_event_id'),
        sa.UniqueConstraint('change_number'),
        schema='qms',
    )
    op.create_index('ix_change_control_state', 'change_control', ['site_id', 'state', 'classification'], schema='qms')

    op.create_table(
        'change_affected_object',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('change_id', sa.UUID(), nullable=False),
        sa.Column('object_type', sa.String(length=60), nullable=False),
        sa.Column('object_id', sa.UUID(), nullable=False),
        sa.Column('object_version', sa.Integer(), nullable=True),
        sa.Column('impact_category', sa.String(length=60), nullable=False),
        sa.Column('action_required', sa.Text(), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['change_id'], ['qms.change_control.id']),
        sa.ForeignKeyConstraint(['created_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_change_affected_object_change', 'change_affected_object', ['change_id'], schema='qms')

    op.create_table(
        'change_task',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('change_id', sa.UUID(), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('owner_subject_id', sa.UUID(), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=False),
        sa.Column('dependency_links', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='pending'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['change_id'], ['qms.change_control.id']),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_change_task_change', 'change_task', ['change_id'], schema='qms')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.change_control TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON qms.change_affected_object TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.change_task TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON qms.change_task FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.change_affected_object FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.change_control FROM {APP_ROLE}")
    op.drop_table('change_task', schema='qms')
    op.drop_table('change_affected_object', schema='qms')
    op.drop_table('change_control', schema='qms')
