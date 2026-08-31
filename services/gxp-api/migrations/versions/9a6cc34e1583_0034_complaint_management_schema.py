"""0034_complaint_management_schema

Revision ID: 9a6cc34e1583
Revises: 5c378cce7939
Create Date: 2026-08-25 00:00:00.000000

Document 35 (SPEC-QMS-010) — Complaint Management. Same owner service as Documents 26-34
(services/gxp-api/src/modules/qms), so `complaint_record`, `complaint_reportability_assessment` and
`complaint_communication` are added to the existing `qms` schema. All three typed directly this pass --
see app/modules/qms/complaint_models.py's module docstring (SG-045's precedent) and
docs/generated/18_SPEC_GAPS.md SG-103/SG-104 for what is deliberately deferred. `product_ref` is a
nullable FK into the existing `ebmr.gxp_product_version` table (Document 09) rather than a second product
master (AG-05); nullable because CMP-FR-004 sends unresolved product/lot/serial IDs to a reconciliation
queue rather than blocking intake.

Same deviation as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '9a6cc34e1583'
down_revision: Union[str, Sequence[str], None] = '5c378cce7939'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'complaint_record',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('quality_event_id', sa.UUID(), nullable=False),
        sa.Column('complaint_number', sa.String(length=120), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('source_channel', sa.String(length=40), nullable=False),
        sa.Column('product_ref', sa.UUID(), nullable=True),
        sa.Column('lot_batch_serial_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('complainant_info', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('nature_code', sa.String(length=100), nullable=False),
        sa.Column('description', sa.Text(), nullable=False),
        sa.Column('constituent_classification', sa.String(length=60), nullable=True),
        sa.Column('triage', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('investigation_required', sa.Boolean(), nullable=True),
        sa.Column('no_investigation_reason', sa.Text(), nullable=True),
        sa.Column('investigation_findings', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('investigation_conclusion', sa.Text(), nullable=True),
        sa.Column('is_potential_duplicate', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('related_complaint_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='RECEIVED'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['product_ref'], ['ebmr.gxp_product_version.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quality_event_id'),
        sa.UniqueConstraint('complaint_number'),
        schema='qms',
    )
    op.create_index('ix_complaint_record_state', 'complaint_record', ['site_id', 'state'], schema='qms')
    op.create_index('ix_complaint_record_nature_product', 'complaint_record', ['nature_code', 'product_ref'], schema='qms')

    op.create_table(
        'complaint_reportability_assessment',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('complaint_id', sa.UUID(), nullable=False),
        sa.Column('applicable_regimes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('assessment_inputs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('trigger_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('reviewer_subject_id', sa.UUID(), nullable=False),
        sa.Column('submission_reference', sa.String(length=200), nullable=True),
        sa.Column('submission_status', sa.String(length=60), nullable=True),
        sa.Column('capa_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('capa_rationale', sa.Text(), nullable=True),
        sa.Column('field_action_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('field_action_rationale', sa.Text(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['complaint_id'], ['qms.complaint_record.id']),
        sa.ForeignKeyConstraint(['reviewer_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_complaint_reportability_complaint', 'complaint_reportability_assessment', ['complaint_id'], schema='qms')

    op.create_table(
        'complaint_communication',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('complaint_id', sa.UUID(), nullable=False),
        sa.Column('direction', sa.String(length=20), nullable=False),
        sa.Column('communication_type', sa.String(length=20), nullable=False),
        sa.Column('recipient', sa.String(length=200), nullable=True),
        sa.Column('channel', sa.String(length=40), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('reference', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['complaint_id'], ['qms.complaint_record.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_complaint_communication_complaint', 'complaint_communication', ['complaint_id'], schema='qms')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.complaint_record TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.complaint_reportability_assessment TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.complaint_communication TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON qms.complaint_communication FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.complaint_reportability_assessment FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.complaint_record FROM {APP_ROLE}")
    op.drop_table('complaint_communication', schema='qms')
    op.drop_table('complaint_reportability_assessment', schema='qms')
    op.drop_table('complaint_record', schema='qms')
