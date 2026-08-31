"""0075_sre_slo_capacity_schema

Revision ID: f3d8a5c2b7e1
Revises: e2b7c4a9f1d6
Create Date: 2026-08-31 00:00:00.000000

Document 78 (SPEC-DATA-010) -- Performance, Capacity, Observability, SLOs & SRE Operations. New `sre`
schema, exactly the 2 owned entities `04_DATA_MODEL_CATALOGUE.md` lists: `slo_definition`,
`capacity_forecast`. Numbers seeded from Document 109 (SPEC-DATA-012, APPROVED) -- see
app/modules/sre/registry.py. No signature (Document 106 has no SPEC-DATA-010 row). **0 owned HTTP
APIs** -- both tables are CI/SRE-tooling-populated (`commands.py`, no router), same "no independent
API" shape as Document 68's `release_security_evidence`. No `tenant_id`/`site_id` (platform-wide). All
numeric targets `BigInteger`; percentages stored as integer basis points, never float.

**Expand-only** -- two brand-new tables in a brand-new schema, no existing table altered, no backfill.
Grants: `USAGE` + `SELECT/INSERT/UPDATE/TRUNCATE` (no `DELETE`). Forward + downgrade + re-upgrade
tested on the restored test database. Reversible: `downgrade()` drops both tables and the schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3d8a5c2b7e1'
down_revision: Union[str, Sequence[str], None] = 'e2b7c4a9f1d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"
_TABLES = ("slo_definition", "capacity_forecast")


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS sre")

    op.create_table(
        'slo_definition',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('operation_class', sa.String(length=20), nullable=False),
        sa.Column('sli_name', sa.String(length=160), nullable=False),
        sa.Column('p95_target_ms', sa.BigInteger(), nullable=False),
        sa.Column('p99_target_ms', sa.BigInteger(), nullable=False),
        sa.Column('window', sa.String(length=40), nullable=False, server_default='steady-state'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('operation_class'),
        schema='sre',
    )

    op.create_table(
        'capacity_forecast',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('dimension', sa.String(length=120), nullable=False),
        sa.Column('reference_value', sa.BigInteger(), nullable=False),
        sa.Column('current_value', sa.BigInteger(), nullable=True),
        sa.Column('growth_rate_pct', sa.BigInteger(), nullable=True),
        sa.Column('horizon_days', sa.BigInteger(), nullable=False, server_default='90'),
        sa.Column('forecasted_value', sa.BigInteger(), nullable=True),
        sa.Column('headroom_pct', sa.BigInteger(), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='sre',
    )

    op.execute(f"GRANT USAGE ON SCHEMA sre TO {APP_ROLE}")
    for t in _TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON sre.{t} TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA sre FROM {APP_ROLE}")


def downgrade() -> None:
    for t in _TABLES:
        op.execute(f"REVOKE ALL ON sre.{t} FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA sre FROM {APP_ROLE}")
    op.drop_table('capacity_forecast', schema='sre')
    op.drop_table('slo_definition', schema='sre')
    op.execute("DROP SCHEMA IF EXISTS sre")
