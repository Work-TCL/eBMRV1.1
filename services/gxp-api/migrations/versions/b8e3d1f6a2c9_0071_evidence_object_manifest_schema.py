"""0071_evidence_object_manifest_schema

Revision ID: b8e3d1f6a2c9
Revises: a7d2f4b9c1e8
Create Date: 2026-08-31 00:00:00.000000

Document 72 (SPEC-DATA-004) -- Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle.
New `evidence` schema, exactly the 2 owned entities `04_DATA_MODEL_CATALOGUE.md` lists:
`evidence_object` (16 fields) and `evidence_manifest` (5). PostgreSQL holds the metadata / hash /
ownership / retention / legal-hold record; the raw bytes live in the object store (Phase-1
`LocalEvidenceStore`). See app/modules/evidence/models.py for the state machine and why only
`apply_evidence_legal_hold()` is signed (Document 106 row 142, `equipment_asset/hold` precedent -- no
SPEC_GAP).

**Expand-only** -- two brand-new tables in a brand-new schema, no existing table altered, no backfill.
Grants: `USAGE` + `SELECT/INSERT/UPDATE/TRUNCATE` (no `DELETE` -- OBJ-FR-019: purge is a controlled
state change to PURGED, never a row delete; enforced at the DB privilege level). `retention_policy_id`
is a nullable reference, never a numeric duration (SG-005). All sizes are `BigInteger`; no float.
Forward + downgrade + re-upgrade tested on the restored test database. Reversible: `downgrade()` drops
both tables, the indexes and the schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b8e3d1f6a2c9'
down_revision: Union[str, Sequence[str], None] = 'a7d2f4b9c1e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"
_TABLES = ("evidence_object", "evidence_manifest")


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS evidence")

    op.create_table(
        'evidence_object',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('owner_type', sa.String(length=80), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('owner_version', sa.BigInteger(), nullable=True),
        sa.Column('provider', sa.String(length=20), nullable=False, server_default='LOCAL'),
        sa.Column('bucket', sa.String(length=200), nullable=False),
        sa.Column('object_key', sa.String(length=400), nullable=False),
        sa.Column('provider_version_id', sa.String(length=200), nullable=True),
        sa.Column('size_bytes', sa.BigInteger(), nullable=True),
        sa.Column('mime_type', sa.String(length=160), nullable=False),
        sa.Column('filename', sa.String(length=400), nullable=True),
        sa.Column('hash_algorithm', sa.String(length=20), nullable=False, server_default='SHA-256'),
        sa.Column('expected_hash', sa.String(length=128), nullable=True),
        sa.Column('content_hash', sa.String(length=128), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='STAGED'),
        sa.Column('retention_policy_id', sa.UUID(), nullable=True),
        sa.Column('retention_until', sa.DateTime(timezone=True), nullable=True),
        sa.Column('legal_hold', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('legal_hold_ref', sa.String(length=120), nullable=True),
        sa.Column('provenance', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('superseded_by', sa.UUID(), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        schema='evidence',
    )
    op.create_index('ix_evidence_object_owner', 'evidence_object', ['owner_type', 'owner_id'], schema='evidence')
    op.create_index('ix_evidence_object_state', 'evidence_object', ['state'], schema='evidence')
    op.create_index('ix_evidence_object_content_hash', 'evidence_object', ['content_hash'], schema='evidence')

    op.create_table(
        'evidence_manifest',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('owner_type', sa.String(length=80), nullable=False),
        sa.Column('owner_id', sa.UUID(), nullable=False),
        sa.Column('owner_version', sa.BigInteger(), nullable=True),
        sa.Column('manifest_type', sa.String(length=20), nullable=False),
        sa.Column('manifest_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('items', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('canonical_hash', sa.String(length=128), nullable=False),
        sa.Column('renderer_version', sa.String(length=80), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('owner_type', 'owner_id', 'manifest_type', 'manifest_version',
                            name='uq_evidence_manifest_identity'),
        schema='evidence',
    )
    op.create_index('ix_evidence_manifest_owner', 'evidence_manifest', ['owner_type', 'owner_id'], schema='evidence')

    op.execute(f"GRANT USAGE ON SCHEMA evidence TO {APP_ROLE}")
    for t in _TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON evidence.{t} TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA evidence FROM {APP_ROLE}")


def downgrade() -> None:
    for t in _TABLES:
        op.execute(f"REVOKE ALL ON evidence.{t} FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA evidence FROM {APP_ROLE}")
    op.drop_index('ix_evidence_manifest_owner', table_name='evidence_manifest', schema='evidence')
    op.drop_table('evidence_manifest', schema='evidence')
    op.drop_index('ix_evidence_object_content_hash', table_name='evidence_object', schema='evidence')
    op.drop_index('ix_evidence_object_state', table_name='evidence_object', schema='evidence')
    op.drop_index('ix_evidence_object_owner', table_name='evidence_object', schema='evidence')
    op.drop_table('evidence_object', schema='evidence')
    op.execute("DROP SCHEMA IF EXISTS evidence")
