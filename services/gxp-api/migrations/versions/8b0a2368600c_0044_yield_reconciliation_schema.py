"""0044_yield_reconciliation_schema

Revision ID: 8b0a2368600c
Revises: e8b4d2f6a1c9
Create Date: 2026-08-26 00:00:00.000000

Document 17 (SPEC-EBMR-008) — Yield, Calculations & Manufacturing Reconciliation. `ebmr` schema
(existing, shared with genealogy/qa_review/release/packaging), two new tables per the spec's own §4 data
model: `manufacturing_calculations`, `reconciliation_records`.

`tenant_id` dropped throughout (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '8b0a2368600c'
down_revision: Union[str, Sequence[str], None] = 'e8b4d2f6a1c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'manufacturing_calculations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('scope_type', sa.String(length=20), nullable=False, server_default='BATCH'),
        sa.Column('scope_id', sa.UUID(), nullable=True),
        sa.Column('calculation_type', sa.String(length=20), nullable=False),
        sa.Column('phase_code', sa.String(length=80), nullable=True),
        sa.Column('rule_object_id', sa.UUID(), nullable=True),
        sa.Column('rule_evaluation_id', sa.UUID(), nullable=True),
        sa.Column('input_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('theoretical_quantity', sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column('actual_quantity', sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column('uom', sa.String(length=20), nullable=True),
        sa.Column('min_percent', sa.Numeric(precision=9, scale=4), nullable=True),
        sa.Column('max_percent', sa.Numeric(precision=9, scale=4), nullable=True),
        sa.Column('manual_source', sa.String(length=200), nullable=True),
        sa.Column('manual_reason', sa.String(length=400), nullable=True),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='PENDING_INPUT'),
        sa.Column('evaluated_by_user_id', sa.UUID(), nullable=True),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('verified_signature_id', sa.UUID(), nullable=True),
        sa.Column('verified_by_user_id', sa.UUID(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('supersedes_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.gxp_batch.id']),
        sa.ForeignKeyConstraint(['rule_object_id'], ['rules.gxp_rule_definition.rule_object_id']),
        sa.ForeignKeyConstraint(['rule_evaluation_id'], ['rules.gxp_rule_evaluation.evaluation_id']),
        sa.ForeignKeyConstraint(['evaluated_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['verified_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['supersedes_id'], ['ebmr.manufacturing_calculations.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_manufacturing_calculations_batch', 'manufacturing_calculations', ['batch_id'], schema='ebmr')

    op.create_table(
        'reconciliation_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('reconciliation_type', sa.String(length=20), nullable=False),
        sa.Column('item_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('quantities', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('uom', sa.String(length=20), nullable=True),
        sa.Column('tolerance_rule', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('variance', sa.Numeric(precision=20, scale=6), nullable=True),
        sa.Column('external_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='CALCULATED'),
        sa.Column('linked_quality_event_id', sa.UUID(), nullable=True),
        sa.Column('evaluated_by_user_id', sa.UUID(), nullable=True),
        sa.Column('verified_signature_id', sa.UUID(), nullable=True),
        sa.Column('verified_by_user_id', sa.UUID(), nullable=True),
        sa.Column('verified_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('supersedes_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.gxp_batch.id']),
        sa.ForeignKeyConstraint(['evaluated_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['verified_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['supersedes_id'], ['ebmr.reconciliation_records.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_reconciliation_records_batch', 'reconciliation_records', ['batch_id'], schema='ebmr')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.manufacturing_calculations TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.reconciliation_records TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.reconciliation_records FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON ebmr.manufacturing_calculations FROM {APP_ROLE}")
    op.drop_table('reconciliation_records', schema='ebmr')
    op.drop_table('manufacturing_calculations', schema='ebmr')
