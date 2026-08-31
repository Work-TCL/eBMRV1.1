"""0026_document_control_schema

Revision ID: 4c8e2a6f1d9b
Revises: 9d2f4a6c8e0b
Create Date: 2026-08-24 00:00:06.000000

Document 30 (SPEC-QMS-005) — Document Control. Same owner service as Documents 26-29
(services/gxp-api/src/modules/qms), so `controlled_document`, `controlled_document_version` and
`controlled_copy` are added to the existing `qms` schema. All three typed directly this pass — see
app/modules/qms/document_models.py's module docstring (SG-045's precedent) and
docs/generated/18_SPEC_GAPS.md SG-074..SG-076 for what is deliberately deferred.

`controlled_document_version.change_control_id` is a real enforced FK to `qms.change_control` (built in
this same pass, Document 29) rather than an unenforced logical reference.

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '4c8e2a6f1d9b'
down_revision: Union[str, Sequence[str], None] = '9d2f4a6c8e0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'controlled_document',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('document_code', sa.String(length=120), nullable=False),
        sa.Column('document_type', sa.String(length=60), nullable=False),
        sa.Column('owner_subject_id', sa.UUID(), nullable=False),
        sa.Column('department_id', sa.UUID(), nullable=True),
        sa.Column('site_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('is_external', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('external_source', sa.String(length=200), nullable=True),
        sa.Column('external_revision', sa.String(length=60), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_code'),
        schema='qms',
    )

    op.create_table(
        'controlled_document_version',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_id', sa.UUID(), nullable=False),
        sa.Column('version_label', sa.String(length=60), nullable=False),
        sa.Column('vault_object_id', sa.UUID(), nullable=True),
        sa.Column('content_hash', sa.String(length=64), nullable=False),
        sa.Column('rendition_hash', sa.String(length=64), nullable=True),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='DRAFT'),
        sa.Column('review_workflow', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('training_impact', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('acknowledgment_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('source_relationships', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('change_control_id', sa.UUID(), nullable=True),
        sa.Column('periodic_review_due', sa.DateTime(timezone=True), nullable=True),
        sa.Column('superseded_by_version_id', sa.UUID(), nullable=True),
        sa.Column('retirement_reason', sa.Text(), nullable=True),
        sa.Column('retired_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['document_id'], ['qms.controlled_document.id']),
        sa.ForeignKeyConstraint(['vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.ForeignKeyConstraint(['change_control_id'], ['qms.change_control.id']),
        sa.ForeignKeyConstraint(['superseded_by_version_id'], ['qms.controlled_document_version.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_controlled_document_version_document', 'controlled_document_version', ['document_id'], schema='qms')
    op.create_index('ix_controlled_document_version_state', 'controlled_document_version', ['document_id', 'state'], schema='qms')

    op.create_table(
        'controlled_copy',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('document_version_id', sa.UUID(), nullable=False),
        sa.Column('copy_number', sa.String(length=60), nullable=False),
        sa.Column('recipient', sa.String(length=200), nullable=False),
        sa.Column('location', sa.String(length=200), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='issued'),
        sa.Column('issued_by', sa.UUID(), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('returned_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('destroyed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['document_version_id'], ['qms.controlled_document_version.id']),
        sa.ForeignKeyConstraint(['issued_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_version_id', 'copy_number'),
        schema='qms',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.controlled_document TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.controlled_document_version TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.controlled_copy TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON qms.controlled_copy FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.controlled_document_version FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.controlled_document FROM {APP_ROLE}")
    op.drop_table('controlled_copy', schema='qms')
    op.drop_table('controlled_document_version', schema='qms')
    op.drop_table('controlled_document', schema='qms')
