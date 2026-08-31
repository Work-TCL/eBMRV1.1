"""0030_scar_schema

Revision ID: 46aa9ec6eeb6
Revises: 2c6a9e4f1b7d
Create Date: 2026-08-25 00:00:00.000000

Document 32 (SPEC-QMS-007) — Supplier Quality / SCAR. Same owner service as Documents 26-31
(services/gxp-api/src/modules/qms), so `supplier_quality_case` and `scar_record` are added to the
existing `qms` schema. Both typed directly this pass -- see app/modules/qms/scar_models.py's module
docstring (SG-045's precedent) and docs/generated/18_SPEC_GAPS.md SG-091 for what is deliberately
deferred.

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '46aa9ec6eeb6'
down_revision: Union[str, Sequence[str], None] = '2c6a9e4f1b7d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'supplier_quality_case',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('quality_event_id', sa.UUID(), nullable=False),
        sa.Column('case_number', sa.String(length=120), nullable=False),
        sa.Column('source_type', sa.String(length=40), nullable=True),
        sa.Column('source_id', sa.UUID(), nullable=True),
        sa.Column('source_version', sa.Integer(), nullable=True),
        sa.Column('supplier_id', sa.UUID(), nullable=False),
        sa.Column('supplier_site_id', sa.UUID(), nullable=True),
        sa.Column('material_id', sa.UUID(), nullable=True),
        sa.Column('material_spec_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('affected_lots', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('defect_code', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=40), nullable=False),
        sa.Column('containment', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('asl_impact', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('internal_owner_subject_id', sa.UUID(), nullable=False),
        sa.Column('alternate_source_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='OPEN'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['supplier_id'], ['ebmr.supplier.id']),
        sa.ForeignKeyConstraint(['supplier_site_id'], ['ebmr.supplier_site.id']),
        sa.ForeignKeyConstraint(['material_id'], ['materials.materials.id']),
        sa.ForeignKeyConstraint(['internal_owner_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quality_event_id'),
        sa.UniqueConstraint('case_number'),
        schema='qms',
    )
    op.create_index('ix_supplier_quality_case_state', 'supplier_quality_case', ['site_id', 'state', 'supplier_id'], schema='qms')

    op.create_table(
        'scar_record',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('case_id', sa.UUID(), nullable=False),
        sa.Column('scar_number', sa.String(length=120), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('due_date', sa.DateTime(timezone=True), nullable=True),
        sa.Column('problem_statement', sa.Text(), nullable=False),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('acknowledgment', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('supplier_root_cause', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('supplier_actions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('internal_review', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('review_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('effectiveness', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('effectiveness_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('requalification_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('requalification_rationale', sa.Text(), nullable=True),
        sa.Column('source_status_decision', sa.String(length=20), nullable=True),
        sa.Column('capa_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('capa_rationale', sa.Text(), nullable=True),
        sa.Column('is_repeat_issue', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('related_case_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='SCAR_ISSUED'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('closure_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['case_id'], ['qms.supplier_quality_case.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('scar_number'),
        schema='qms',
    )
    op.create_index('ix_scar_record_case', 'scar_record', ['case_id'], schema='qms')
    op.create_index('ix_scar_record_state', 'scar_record', ['site_id', 'state'], schema='qms')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.supplier_quality_case TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.scar_record TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON qms.scar_record FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.supplier_quality_case FROM {APP_ROLE}")
    op.drop_table('scar_record', schema='qms')
    op.drop_table('supplier_quality_case', schema='qms')
