"""0072_consumer_inbox_outbox_schema_version

Revision ID: c4f9a2e1b7d3
Revises: b8e3d1f6a2c9
Create Date: 2026-08-31 00:00:00.000000

Document 73 (SPEC-DATA-005) -- NATS/JetStream Event Bus, Transactional Outbox & Async Contracts.

Two additive changes, no destructive schema change (MIG-FR-004/005/029):

1. New `eventbus` schema with the one *new* owned entity, `consumer_inbox` (EVT-FR-005/006 dedupe
   record for an at-least-once consumer). `gxp_outbox` already exists as `mutation.outbox_events`
   (WP-01) -- Document 73 does not create a second outbox table (AG-05).
2. `mutation.outbox_events.schema_version` -- nullable-with-default additive column (`server_default
   '1.0'`), the one field EVT-FR-001's canonical envelope needed that the WP-01 table didn't yet carry.
   Existing rows are unaffected (no rewrite, no backfill); `write_outbox_event()` now always sets it.

See app/modules/eventbus/models.py for field rationale. No signature (Document 106 has no
SPEC-DATA-005 row). Grants: `USAGE` + `SELECT/INSERT/UPDATE/TRUNCATE` on `eventbus.consumer_inbox`
(no `DELETE` -- dead-letter disposition is a state change, never a row delete). Forward + downgrade +
re-upgrade tested on the restored test database.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c4f9a2e1b7d3'
down_revision: Union[str, Sequence[str], None] = 'b8e3d1f6a2c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.add_column(
        'outbox_events',
        sa.Column('schema_version', sa.String(length=20), nullable=False, server_default='1.0'),
        schema='mutation',
    )

    op.execute("CREATE SCHEMA IF NOT EXISTS eventbus")
    op.create_table(
        'consumer_inbox',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('consumer_name', sa.String(length=120), nullable=False),
        sa.Column('event_id', sa.UUID(), nullable=False),
        sa.Column('aggregate_version', sa.BigInteger(), nullable=True),
        sa.Column('result', sa.String(length=20), nullable=False, server_default='PROCESSED'),
        sa.Column('detail', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('attempt_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('last_error', sa.Text(), nullable=True),
        sa.Column('processed_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('consumer_name', 'event_id', name='uq_consumer_inbox_identity'),
        schema='eventbus',
    )
    op.create_index('ix_consumer_inbox_result', 'consumer_inbox', ['result'], schema='eventbus')

    op.execute(f"GRANT USAGE ON SCHEMA eventbus TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON eventbus.consumer_inbox TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA eventbus FROM {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON eventbus.consumer_inbox FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA eventbus FROM {APP_ROLE}")
    op.drop_index('ix_consumer_inbox_result', table_name='consumer_inbox', schema='eventbus')
    op.drop_table('consumer_inbox', schema='eventbus')
    op.execute("DROP SCHEMA IF EXISTS eventbus")
    op.drop_column('outbox_events', 'schema_version', schema='mutation')
