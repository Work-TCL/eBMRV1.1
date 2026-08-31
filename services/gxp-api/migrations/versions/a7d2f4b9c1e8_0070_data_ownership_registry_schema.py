"""0070_data_ownership_registry_schema

Revision ID: a7d2f4b9c1e8
Revises: f6c4e0b1a8d5
Create Date: 2026-08-31 00:00:00.000000

Document 69 (SPEC-DATA-001) -- Enterprise Data Ownership, Persistence Topology & Data Lineage. New
`dataops` schema, exactly the 3 owned entities `04_DATA_MODEL_CATALOGUE.md` lists:
`data_ownership_registry`, `projection_checkpoint`, `migration_batch`. See
app/modules/dataops/models.py for why there is no signature anywhere (Document 106 # 10 exempts
projection rebuilds / reads) and why there is no `tenant_id` / `site_id` (ADR-0006 + platform-level
governance metadata; `tenant_scoped`/`site_scoped` are *attributes describing an entity*, not scoping
of the registry row).

`retention_policy_id` is a nullable reference to a Document 108 retention policy -- never a numeric
duration (SG-005, the open retention-period gap). Every count / size / version column is BigInteger;
no float columns.

**Expand-only** -- three brand-new tables in a brand-new schema, no existing table altered, no
backfill. Grants: SELECT/INSERT/UPDATE/TRUNCATE (no DELETE -- DATA-FR-023: no hard delete of
regulated/history rows through generic CRUD, enforced at the DB privilege level). Forward + downgrade +
re-upgrade tested on the restored test database. Reversible: `downgrade()` drops all three tables and
the schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a7d2f4b9c1e8'
down_revision: Union[str, Sequence[str], None] = 'f6c4e0b1a8d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"
_TABLES = ("data_ownership_registry", "projection_checkpoint", "migration_batch")


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS dataops")

    op.create_table(
        'data_ownership_registry',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('entity_type', sa.String(length=160), nullable=False),
        sa.Column('authoritative_service', sa.String(length=120), nullable=False),
        sa.Column('authoritative_store', sa.String(length=20), nullable=False),
        sa.Column('projection_targets', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('tenant_scoped', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('site_scoped', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('classification', sa.String(length=20), nullable=False, server_default='GXP'),
        sa.Column('retention_policy_id', sa.UUID(), nullable=True),
        sa.Column('encryption_profile_id', sa.UUID(), nullable=True),
        sa.Column('source_reference', sa.String(length=200), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type'),
        schema='dataops',
    )

    op.create_table(
        'projection_checkpoint',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('projection_type', sa.String(length=120), nullable=False),
        sa.Column('source_stream', sa.String(length=160), nullable=False),
        sa.Column('last_source_event_id', sa.UUID(), nullable=True),
        sa.Column('last_source_version', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('projected_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='IDLE'),
        sa.Column('error', sa.Text(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('projection_type'),
        schema='dataops',
    )
    op.create_index(
        'ix_projection_checkpoint_source_stream', 'projection_checkpoint', ['source_stream'], schema='dataops'
    )

    op.create_table(
        'migration_batch',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('batch_ref', sa.String(length=120), nullable=False),
        sa.Column('source_system', sa.String(length=160), nullable=False),
        sa.Column('source_artifact', sa.String(length=300), nullable=False),
        sa.Column('source_hash', sa.String(length=160), nullable=False),
        sa.Column('transform_version', sa.String(length=80), nullable=False),
        sa.Column('destination_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('source_row_count', sa.BigInteger(), nullable=True),
        sa.Column('loaded_row_count', sa.BigInteger(), nullable=True),
        sa.Column('reconciliation_hash', sa.String(length=160), nullable=True),
        sa.Column('reconciliation_status', sa.String(length=20), nullable=False, server_default='PENDING'),
        sa.Column('approver', sa.String(length=120), nullable=False),
        sa.Column('evidence_ref', sa.String(length=300), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='RECORDED'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_ref'),
        schema='dataops',
    )

    op.execute(f"GRANT USAGE ON SCHEMA dataops TO {APP_ROLE}")
    for t in _TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON dataops.{t} TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA dataops FROM {APP_ROLE}")


def downgrade() -> None:
    for t in _TABLES:
        op.execute(f"REVOKE ALL ON dataops.{t} FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA dataops FROM {APP_ROLE}")
    op.drop_index('ix_projection_checkpoint_source_stream', table_name='projection_checkpoint', schema='dataops')
    op.drop_table('migration_batch', schema='dataops')
    op.drop_table('projection_checkpoint', schema='dataops')
    op.drop_table('data_ownership_registry', schema='dataops')
    op.execute("DROP SCHEMA IF EXISTS dataops")
