"""0115_codegen_sequence_schema

Revision ID: 3a0708405e7f
Revises: 9da2e9e4d481
Create Date: 2026-09-21 00:00:00.000000

Client requirement #1 (auto-generate vs. manual entry for unique codes). New `codegen` schema, one
table: `code_sequence_counter`, a plain monotonic counter keyed by `(entity_type, site_id, prefix)`.
Not itself a regulated/audited entity -- it never appears in an audit event or outbox payload; it is
consumed inside the same transaction as whichever create command needs a fresh code (Material, Product,
Recipe, Equipment asset/area, Supplier). `site_id` uses the nil UUID for entity types whose real
uniqueness constraint is table-wide rather than per-site (every affected entity except `Material.code`
today), so two sites never legitimately mint the identical code string.

Expand-only -- one new table in a brand-new schema. Grants: `SELECT/INSERT/UPDATE` (no `DELETE` --
gaps from a rolled-back reservation are an accepted property of a sequence, not something to compact).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3a0708405e7f'
down_revision: Union[str, Sequence[str], None] = '9da2e9e4d481'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS codegen")

    op.create_table(
        'code_sequence_counter',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('entity_type', sa.String(length=40), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('prefix', sa.String(length=10), nullable=False),
        sa.Column('last_value', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('entity_type', 'site_id', 'prefix', name='uq_code_sequence_counter_key'),
        schema='codegen',
    )

    op.execute(f"GRANT USAGE ON SCHEMA codegen TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON codegen.code_sequence_counter TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA codegen FROM {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON codegen.code_sequence_counter FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA codegen FROM {APP_ROLE}")
    op.drop_table('code_sequence_counter', schema='codegen')
    op.execute("DROP SCHEMA IF EXISTS codegen")
