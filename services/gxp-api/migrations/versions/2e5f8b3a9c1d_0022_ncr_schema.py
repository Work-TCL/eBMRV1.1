"""0022_ncr_schema

Revision ID: 2e5f8b3a9c1d
Revises: 4b6e8f0a1c2d
Create Date: 2026-08-24 00:00:04.000000

Document 28 (SPEC-QMS-003) — Nonconformance Management. Same owner service as Documents 26/27
(services/gxp-api/src/modules/qms), so `nonconformance_record` and `ncr_disposition` are added to the
existing `qms` schema. Both typed directly this pass — see app/modules/qms/ncr_models.py's module
docstring (SG-045's precedent) and docs/generated/18_SPEC_GAPS.md SG-066 for what is deliberately deferred.

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '2e5f8b3a9c1d'
down_revision: Union[str, Sequence[str], None] = '4b6e8f0a1c2d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'nonconformance_record',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('quality_event_id', sa.UUID(), nullable=False),
        sa.Column('ncr_number', sa.String(length=120), nullable=False),
        sa.Column('source_type', sa.String(length=40), nullable=True),
        sa.Column('source_id', sa.UUID(), nullable=True),
        sa.Column('source_version', sa.Integer(), nullable=True),
        sa.Column('scope_type', sa.String(length=50), nullable=False),
        sa.Column('scope_records', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('requirement_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('defect_code', sa.String(length=100), nullable=False),
        sa.Column('severity', sa.String(length=40), nullable=False),
        sa.Column('owner_subject_id', sa.UUID(), nullable=False),
        sa.Column('segregation', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('evaluation', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('supplier_link', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('capa_required', sa.Boolean(), nullable=True),
        sa.Column('capa_rationale', sa.Text(), nullable=True),
        sa.Column('release_blocker_active', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('verification', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='OPEN'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('closure_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quality_event_id'),
        sa.UniqueConstraint('ncr_number'),
        schema='qms',
    )
    op.create_index('ix_nonconformance_record_state', 'nonconformance_record', ['site_id', 'state', 'severity'], schema='qms')

    op.create_table(
        'ncr_disposition',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('ncr_id', sa.UUID(), nullable=False),
        sa.Column('affected_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('serials', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('disposition_type', sa.String(length=20), nullable=False),
        sa.Column('justification', sa.Text(), nullable=False),
        sa.Column('rework_route', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('follow_up_test_requirements', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('use_as_is_authorized_by', sa.UUID(), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ncr_id'], ['qms.nonconformance_record.id']),
        sa.ForeignKeyConstraint(['use_as_is_authorized_by'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['created_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_ncr_disposition_ncr', 'ncr_disposition', ['ncr_id'], schema='qms')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.nonconformance_record TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON qms.ncr_disposition TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON qms.ncr_disposition FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.nonconformance_record FROM {APP_ROLE}")
    op.drop_table('ncr_disposition', schema='qms')
    op.drop_table('nonconformance_record', schema='qms')
