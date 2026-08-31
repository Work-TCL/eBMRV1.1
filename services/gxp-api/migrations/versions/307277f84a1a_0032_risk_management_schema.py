"""0032_risk_management_schema

Revision ID: 307277f84a1a
Revises: bb7e61b309ce
Create Date: 2026-08-25 00:00:00.000000

Document 33 (SPEC-QMS-008) — Risk Management. Same owner service as Documents 26-32
(services/gxp-api/src/modules/qms), so `risk_record` and `risk_assessment_version` are added to the
existing `qms` schema. Both typed directly this pass -- see app/modules/qms/risk_models.py's module
docstring (SG-045's precedent) and docs/generated/18_SPEC_GAPS.md SG-099/SG-100 for what is deliberately
deferred. `methodology_id` is a real FK into the existing `rules.gxp_rule_definition` table (Document 08)
rather than a new methodology master (AG-05).

Same deviation as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '307277f84a1a'
down_revision: Union[str, Sequence[str], None] = 'bb7e61b309ce'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'risk_record',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('quality_event_id', sa.UUID(), nullable=False),
        sa.Column('risk_number', sa.String(length=120), nullable=False),
        sa.Column('risk_type', sa.String(length=50), nullable=False),
        sa.Column('methodology_id', sa.UUID(), nullable=True),
        sa.Column('context', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('hazard_problem', sa.Text(), nullable=False),
        sa.Column('potential_effect', sa.Text(), nullable=False),
        sa.Column('owner_subject_id', sa.UUID(), nullable=False),
        sa.Column('next_review_due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='DRAFT'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['methodology_id'], ['rules.gxp_rule_definition.rule_object_id']),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quality_event_id'),
        sa.UniqueConstraint('risk_number'),
        schema='qms',
    )
    op.create_index('ix_risk_record_state', 'risk_record', ['site_id', 'state', 'risk_type'], schema='qms')

    op.create_table(
        'risk_assessment_version',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('risk_record_id', sa.UUID(), nullable=False),
        sa.Column('cycle_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('methodology_id', sa.UUID(), nullable=True),
        sa.Column('methodology_version', sa.String(length=40), nullable=True),
        sa.Column('scoring_inputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('initial_score', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('controls', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('mitigation_actions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('residual_inputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('residual_score', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('acceptance_criteria', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('acceptance', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('review_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('is_current', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['risk_record_id'], ['qms.risk_record.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('risk_record_id', 'cycle_number'),
        schema='qms',
    )
    op.create_index('ix_risk_assessment_version_current', 'risk_assessment_version', ['risk_record_id', 'is_current'], schema='qms')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.risk_record TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.risk_assessment_version TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON qms.risk_assessment_version FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.risk_record FROM {APP_ROLE}")
    op.drop_table('risk_assessment_version', schema='qms')
    op.drop_table('risk_record', schema='qms')
