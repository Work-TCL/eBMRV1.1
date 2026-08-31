"""0035_field_action_schema

Revision ID: 804cf667aa18
Revises: 9a6cc34e1583
Create Date: 2026-08-25 00:00:00.000000

Document 36 (SPEC-QMS-011) — Recall / Field Action Management. Same owner service as Documents 26-35
(services/gxp-api/src/modules/qms), so `field_action`, `field_action_scope_item`,
`field_action_communication` and `field_action_reconciliation` are added to the existing `qms` schema. All
four typed directly this pass -- see app/modules/qms/field_action_models.py's module docstring (SG-045's
precedent) and docs/generated/18_SPEC_GAPS.md SG-105/SG-106 for what is deliberately deferred.
`risk_assessment_ref` is a nullable FK into the existing `qms.risk_record` (Document 33) rather than a
second risk store (AG-05); `field_action_scope_item.product_ref` is a nullable FK into the existing
`ebmr.gxp_product_version` (Document 09), same pattern as Document 35's `complaint_record.product_ref`.

Same deviation as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '804cf667aa18'
down_revision: Union[str, Sequence[str], None] = '9a6cc34e1583'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'field_action',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('quality_event_id', sa.UUID(), nullable=False),
        sa.Column('action_number', sa.String(length=120), nullable=False),
        sa.Column('action_type', sa.String(length=60), nullable=False),
        sa.Column('trigger_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('risk_assessment_ref', sa.UUID(), nullable=True),
        sa.Column('reportability_assessment', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('effectiveness_check', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('capa_required', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('capa_rationale', sa.Text(), nullable=True),
        sa.Column('scope_snapshot_id', sa.UUID(), nullable=True),
        sa.Column('revision', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='ASSESSMENT'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['risk_assessment_ref'], ['qms.risk_record.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('quality_event_id'),
        sa.UniqueConstraint('action_number'),
        schema='qms',
    )
    op.create_index('ix_field_action_state', 'field_action', ['site_id', 'state'], schema='qms')

    op.create_table(
        'field_action_scope_item',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('field_action_id', sa.UUID(), nullable=False),
        sa.Column('product_ref', sa.UUID(), nullable=True),
        sa.Column('lot_batch_serial_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('distribution_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('distribution_hold', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='identified'),
        sa.Column('action_required', sa.String(length=40), nullable=True),
        sa.Column('action_completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['field_action_id'], ['qms.field_action.id']),
        sa.ForeignKeyConstraint(['product_ref'], ['ebmr.gxp_product_version.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_field_action_scope_item_action', 'field_action_scope_item', ['field_action_id'], schema='qms')

    op.create_table(
        'field_action_communication',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('field_action_id', sa.UUID(), nullable=False),
        sa.Column('package_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('recipient', sa.String(length=200), nullable=False),
        sa.Column('channel', sa.String(length=40), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivery_status', sa.String(length=40), nullable=False, server_default='pending'),
        sa.Column('ack_status', sa.String(length=40), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['field_action_id'], ['qms.field_action.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='qms',
    )
    op.create_index('ix_field_action_communication_action', 'field_action_communication', ['field_action_id'], schema='qms')

    op.create_table(
        'field_action_reconciliation',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('field_action_id', sa.UUID(), nullable=False),
        sa.Column('affected_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('contacted_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('returned_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('corrected_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('destroyed_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('unavailable_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('outstanding_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['field_action_id'], ['qms.field_action.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('field_action_id'),
        schema='qms',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.field_action TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.field_action_scope_item TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.field_action_communication TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON qms.field_action_reconciliation TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON qms.field_action_reconciliation FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.field_action_communication FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.field_action_scope_item FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON qms.field_action FROM {APP_ROLE}")
    op.drop_table('field_action_reconciliation', schema='qms')
    op.drop_table('field_action_communication', schema='qms')
    op.drop_table('field_action_scope_item', schema='qms')
    op.drop_table('field_action', schema='qms')
