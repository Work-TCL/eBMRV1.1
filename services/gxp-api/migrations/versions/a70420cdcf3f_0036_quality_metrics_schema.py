"""0036_quality_metrics_schema

Revision ID: a70420cdcf3f
Revises: 804cf667aa18
Create Date: 2026-08-25 00:00:00.000000

Document 37 (SPEC-QMS-012) — Quality Metrics, Trending & Effectiveness Checks. Same owner service as
Documents 26-36 (services/gxp-api/src/modules/qms), so `quality_metric_definition`,
`quality_metric_snapshot` and `effectiveness_check` are added to the existing `qms` schema. All three
typed directly this pass -- see app/modules/qms/quality_metrics_models.py's module docstring (SG-045's
precedent) and docs/generated/18_SPEC_GAPS.md SG-107/SG-108 for what is deliberately deferred.
`formula_rule_id` is a nullable FK into the existing `rules.gxp_rule_definition` (Document 08) rather than
a second formula master (AG-05).

Same deviation as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a70420cdcf3f'
down_revision: Union[str, Sequence[str], None] = '804cf667aa18'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'quality_metric_definition',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('metric_code', sa.String(length=120), nullable=False),
        sa.Column('version_no', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('owner_subject_id', sa.UUID(), nullable=False),
        sa.Column('source_model_id', sa.String(length=120), nullable=False),
        sa.Column('numerator_definition', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('denominator_definition', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('formula_rule_id', sa.UUID(), nullable=True),
        sa.Column('scope_dimensions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('frequency', sa.String(length=40), nullable=False),
        sa.Column('threshold_rule_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='DRAFT'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['formula_rule_id'], ['rules.gxp_rule_definition.rule_object_id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('metric_code', 'version_no'),
        schema='qms',
    )
    op.create_index('ix_quality_metric_definition_state', 'quality_metric_definition', ['site_id', 'state', 'metric_code'], schema='qms')

    op.create_table(
        'quality_metric_snapshot',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('metric_definition_id', sa.UUID(), nullable=False),
        sa.Column('period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_cutoff', sa.DateTime(timezone=True), nullable=False),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('formula_version', sa.String(length=40), nullable=False),
        sa.Column('threshold_exceeded', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('review_package_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='COMPLETE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['metric_definition_id'], ['qms.quality_metric_definition.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_quality_metric_snapshot_definition', 'quality_metric_snapshot', ['metric_definition_id'], schema='qms')
    op.create_index('ix_quality_metric_snapshot_package', 'quality_metric_snapshot', ['review_package_id'], schema='qms')

    op.create_table(
        'effectiveness_check',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('source_module', sa.String(length=40), nullable=False),
        sa.Column('source_record_id', sa.UUID(), nullable=False),
        sa.Column('criterion', sa.Text(), nullable=False),
        sa.Column('metric_definition_id', sa.UUID(), nullable=True),
        sa.Column('observation_period_start', sa.DateTime(timezone=True), nullable=False),
        sa.Column('observation_period_end', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result', sa.String(length=20), nullable=True),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reviewer_subject_id', sa.UUID(), nullable=True),
        sa.Column('escalation_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('escalation_rationale', sa.Text(), nullable=True),
        sa.Column('next_observation_due', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='OBSERVATION'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['metric_definition_id'], ['qms.quality_metric_definition.id']),
        sa.ForeignKeyConstraint(['reviewer_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_effectiveness_check_source', 'effectiveness_check', ['source_module', 'source_record_id'], schema='qms')
    op.create_index('ix_effectiveness_check_state', 'effectiveness_check', ['site_id', 'state'], schema='qms')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.quality_metric_definition TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.quality_metric_snapshot TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.effectiveness_check TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON qms.effectiveness_check FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.quality_metric_snapshot FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.quality_metric_definition FROM {APP_ROLE}")
    op.drop_table('effectiveness_check', schema='qms')
    op.drop_table('quality_metric_snapshot', schema='qms')
    op.drop_table('quality_metric_definition', schema='qms')
