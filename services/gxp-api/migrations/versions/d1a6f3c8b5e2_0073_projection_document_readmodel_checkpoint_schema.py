"""0073_projection_document_readmodel_checkpoint_schema

Revision ID: d1a6f3c8b5e2
Revises: c4f9a2e1b7d3
Create Date: 2026-08-31 00:00:00.000000

Document 75 (SPEC-DATA-007) -- Caching, Search, Read Models, Reporting Projections & Analytics Data
Access. New `readmodels` schema, exactly the 2 owned entities `04_DATA_MODEL_CATALOGUE.md` lists:
`projection_document_metadata` (per-indexed-document metadata, the Postgres-backed default search
provider -- READ-FR-008/009/012) and `read_model_checkpoint` (per index-type/read-model/export
definition refresh cursor + frozen cutoff -- READ-FR-016/017). Both are, per the catalogue, "Redis /
search / read models (rebuildable, NON-AUTHORITATIVE)"; PostgreSQL tracks governance metadata about
that non-authoritative tier, same shape as (and a different granularity from) Document 69's
`dataops.projection_checkpoint` -- see app/modules/readmodels/models.py module docstring.

No signature (Document 106 has no SPEC-DATA-007 row). No `tenant_id`/`site_id` (platform-level, same
precedent as `security.*`/`dataops.*`). No float columns.

**Expand-only** -- two brand-new tables in a brand-new schema, no existing table altered, no backfill.
Grants: `USAGE` + `SELECT/INSERT/UPDATE/TRUNCATE` (no `DELETE` -- a stale document/checkpoint is
superseded via UPDATE, never hard-deleted through generic CRUD). Forward + downgrade + re-upgrade
tested on the restored test database. Reversible: `downgrade()` drops both tables, the indexes and the
schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd1a6f3c8b5e2'
down_revision: Union[str, Sequence[str], None] = 'c4f9a2e1b7d3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"
_TABLES = ("projection_document_metadata", "read_model_checkpoint")


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS readmodels")

    op.create_table(
        'projection_document_metadata',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('index_type', sa.String(length=80), nullable=False),
        sa.Column('entity_type', sa.String(length=80), nullable=False),
        sa.Column('entity_id', sa.UUID(), nullable=False),
        sa.Column('source_version', sa.BigInteger(), nullable=False),
        sa.Column('indexed_fields', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='LIVE'),
        sa.Column('projected_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('index_type', 'entity_type', 'entity_id', name='uq_projection_document_identity'),
        schema='readmodels',
    )
    op.create_index(
        'ix_projection_document_metadata_index_type', 'projection_document_metadata', ['index_type'], schema='readmodels'
    )

    op.create_table(
        'read_model_checkpoint',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('model_name', sa.String(length=120), nullable=False),
        sa.Column('source_stream', sa.String(length=160), nullable=False),
        sa.Column('source_cutoff', sa.DateTime(timezone=True), nullable=True),
        sa.Column('refreshed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='STALE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('model_name'),
        schema='readmodels',
    )

    op.execute(f"GRANT USAGE ON SCHEMA readmodels TO {APP_ROLE}")
    for t in _TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON readmodels.{t} TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA readmodels FROM {APP_ROLE}")


def downgrade() -> None:
    for t in _TABLES:
        op.execute(f"REVOKE ALL ON readmodels.{t} FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA readmodels FROM {APP_ROLE}")
    op.drop_table('read_model_checkpoint', schema='readmodels')
    op.drop_index('ix_projection_document_metadata_index_type', table_name='projection_document_metadata', schema='readmodels')
    op.drop_table('projection_document_metadata', schema='readmodels')
    op.execute("DROP SCHEMA IF EXISTS readmodels")
