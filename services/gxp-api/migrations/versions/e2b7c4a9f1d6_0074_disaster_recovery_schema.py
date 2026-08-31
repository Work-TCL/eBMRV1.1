"""0074_disaster_recovery_schema

Revision ID: e2b7c4a9f1d6
Revises: d1a6f3c8b5e2
Create Date: 2026-08-31 00:00:00.000000

Document 76 (SPEC-DATA-008) -- Backup, Restore, Point-in-Time Recovery & Disaster Recovery. New
`disaster_recovery` schema, exactly the 3 owned entities `04_DATA_MODEL_CATALOGUE.md` lists:
`recovery_objective_profile`, `backup_inventory`, `restore_test`. RPO/RTO numbers come from Document
109 (SPEC-DATA-012, APPROVED, closes SG-006/008/016) -- see app/modules/disaster_recovery/registry.py.
No signature (Document 106 has no SPEC-DATA-008 row). No `tenant_id` (ADR-0006); `site_id` nullable on
`recovery_objective_profile` (T5 edge objectives are per-site). All durations/sizes are `BigInteger`.

**Expand-only** -- three brand-new tables in a brand-new schema, no existing table altered, no backfill.
Grants: `USAGE` + `SELECT/INSERT/UPDATE/TRUNCATE` (no `DELETE` -- backup/restore history is append-only
evidence). Forward + downgrade + re-upgrade tested on the restored test database. Reversible:
`downgrade()` drops all three tables and the schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e2b7c4a9f1d6'
down_revision: Union[str, Sequence[str], None] = 'd1a6f3c8b5e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"
_TABLES = ("recovery_objective_profile", "backup_inventory", "restore_test")


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS disaster_recovery")

    op.create_table(
        'recovery_objective_profile',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('component', sa.String(length=80), nullable=False),
        sa.Column('tier', sa.String(length=4), nullable=False),
        sa.Column('rpo_seconds', sa.BigInteger(), nullable=True),
        sa.Column('rto_seconds', sa.BigInteger(), nullable=False),
        sa.Column('approved_by', sa.String(length=160), nullable=False, server_default='Document 109 platform default'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('component'),
        schema='disaster_recovery',
    )

    op.create_table(
        'backup_inventory',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('component', sa.String(length=80), nullable=False),
        sa.Column('backup_type', sa.String(length=20), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('checksum', sa.String(length=160), nullable=True),
        sa.Column('manifest_ref', sa.String(length=300), nullable=True),
        sa.Column('encrypted', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='disaster_recovery',
    )
    op.create_index('ix_backup_inventory_component', 'backup_inventory', ['component'], schema='disaster_recovery')

    op.create_table(
        'restore_test',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('backup_id', sa.UUID(), nullable=False),
        sa.Column('target_environment', sa.String(length=80), nullable=False),
        sa.Column('pitr_target', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('rpo_achieved_seconds', sa.BigInteger(), nullable=True),
        sa.Column('rto_achieved_seconds', sa.BigInteger(), nullable=True),
        sa.Column('integrity_checks', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('result', sa.String(length=20), nullable=False, server_default='IN_PROGRESS'),
        sa.Column('evidence_ref', sa.String(length=300), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='disaster_recovery',
    )
    op.create_index('ix_restore_test_backup_id', 'restore_test', ['backup_id'], schema='disaster_recovery')

    op.execute(f"GRANT USAGE ON SCHEMA disaster_recovery TO {APP_ROLE}")
    for t in _TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON disaster_recovery.{t} TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA disaster_recovery FROM {APP_ROLE}")


def downgrade() -> None:
    for t in _TABLES:
        op.execute(f"REVOKE ALL ON disaster_recovery.{t} FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA disaster_recovery FROM {APP_ROLE}")
    op.drop_index('ix_restore_test_backup_id', table_name='restore_test', schema='disaster_recovery')
    op.drop_table('restore_test', schema='disaster_recovery')
    op.drop_index('ix_backup_inventory_component', table_name='backup_inventory', schema='disaster_recovery')
    op.drop_table('backup_inventory', schema='disaster_recovery')
    op.drop_table('recovery_objective_profile', schema='disaster_recovery')
    op.execute("DROP SCHEMA IF EXISTS disaster_recovery")
