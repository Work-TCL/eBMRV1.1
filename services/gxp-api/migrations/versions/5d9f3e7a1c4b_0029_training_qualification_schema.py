"""0029_training_qualification_schema

Revision ID: 5d9f3e7a1c4b
Revises: 8f1c3d5a7b2e
Create Date: 2026-08-25 00:00:00.000000

Document 31 (SPEC-QMS-006) — Training & Personnel Qualification. Same owner service as Documents 26-30
(services/gxp-api/src/modules/qms), so `training_requirement`, `training_assignment`,
`qualification_record` and `training_waiver` are added to the existing `qms` schema. All four typed
directly this pass — see app/modules/qms/training_models.py's module docstring (SG-045's precedent) and
docs/generated/18_SPEC_GAPS.md SG-086..SG-090 for what is deliberately deferred.

`training_requirement.content_document_version_id` and `training_assignment.source_version_id` are real
enforced FKs to `qms.controlled_document_version` (Document 30, built in the prior pass).

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '5d9f3e7a1c4b'
down_revision: Union[str, Sequence[str], None] = '8f1c3d5a7b2e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'training_requirement',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('source_type', sa.String(length=40), nullable=False),
        sa.Column('source_reference_id', sa.UUID(), nullable=True),
        sa.Column('training_type', sa.String(length=40), nullable=False),
        sa.Column('content_document_version_id', sa.UUID(), nullable=True),
        sa.Column('recurrence_interval_days', sa.Integer(), nullable=True),
        sa.Column('requires_assessment', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('pass_score', sa.Numeric(5, 2), nullable=True),
        sa.Column('required_trainer_qualification_code', sa.String(length=100), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['content_document_version_id'], ['qms.controlled_document_version.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )

    op.create_table(
        'training_waiver',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('subject_id', sa.UUID(), nullable=False),
        sa.Column('requirement_id', sa.UUID(), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['subject_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['requirement_id'], ['qms.training_requirement.id']),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )

    op.create_table(
        'training_assignment',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('subject_id', sa.UUID(), nullable=False),
        sa.Column('requirement_id', sa.UUID(), nullable=False),
        sa.Column('source_version_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='ASSIGNED'),
        sa.Column('assigned_by_user_id', sa.UUID(), nullable=False),
        sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('due_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('result', sa.String(length=40), nullable=True),
        sa.Column('trainer_user_id', sa.UUID(), nullable=True),
        sa.Column('score', sa.Numeric(5, 2), nullable=True),
        sa.Column('attempt_number', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('practical_checklist', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('evidence_vault_object_id', sa.UUID(), nullable=True),
        sa.Column('equivalency_credit', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('equivalency_evidence', sa.Text(), nullable=True),
        sa.Column('equivalency_approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('waiver_id', sa.UUID(), nullable=True),
        sa.Column('retrain_of_assignment_id', sa.UUID(), nullable=True),
        sa.Column('retraining_trigger', sa.String(length=40), nullable=True),
        sa.Column('external_source', sa.String(length=200), nullable=True),
        sa.Column('external_reference', sa.String(length=200), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['subject_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['requirement_id'], ['qms.training_requirement.id']),
        sa.ForeignKeyConstraint(['source_version_id'], ['qms.controlled_document_version.id']),
        sa.ForeignKeyConstraint(['assigned_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['trainer_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['evidence_vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.ForeignKeyConstraint(['equivalency_approved_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['waiver_id'], ['qms.training_waiver.id']),
        sa.ForeignKeyConstraint(['retrain_of_assignment_id'], ['qms.training_assignment.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_training_assignment_subject', 'training_assignment', ['subject_id'], schema='qms')
    op.create_index('ix_training_assignment_requirement', 'training_assignment', ['requirement_id'], schema='qms')

    op.create_table(
        'qualification_record',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('subject_id', sa.UUID(), nullable=False),
        sa.Column('qualification_code', sa.String(length=100), nullable=False),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='QUALIFIED'),
        sa.Column('evaluator_user_id', sa.UUID(), nullable=True),
        sa.Column('source_assignment_id', sa.UUID(), nullable=True),
        sa.Column('renewed_from_qualification_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['subject_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['evaluator_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['source_assignment_id'], ['qms.training_assignment.id']),
        sa.ForeignKeyConstraint(['renewed_from_qualification_id'], ['qms.qualification_record.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_qualification_record_subject', 'qualification_record', ['subject_id', 'qualification_code'], schema='qms')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.training_requirement TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.training_waiver TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.training_assignment TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.qualification_record TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON qms.qualification_record FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.training_assignment FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.training_waiver FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.training_requirement FROM {APP_ROLE}")
    op.drop_table('qualification_record', schema='qms')
    op.drop_table('training_assignment', schema='qms')
    op.drop_table('training_waiver', schema='qms')
    op.drop_table('training_requirement', schema='qms')
