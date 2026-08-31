"""0014_genealogy_schema

Revision ID: 5e23e1067790
Revises: 0cb6e2ece7c0
Create Date: 2026-08-24 00:00:00.000000

Document 13 (SPEC-EBMR-004) — Genealogy & Traceability Engine. Creates 2 new tables (`genealogy_node`,
`genealogy_edge`) in the existing `ebmr` schema. No legacy genealogy module exists in this codebase.

Both entities are DDL-ready in docs/generated/04_DATA_MODEL_CATALOGUE.md and are typed here directly
(the best ratio of any module built so far -- Documents 09-12 each had 1-7 of their owned entities
prose-only). Same deviation as prior additive migrations: `tenant_id` dropped (single-organization
platform). Neither table carries a `version` column -- unlike every other module's tables, the source DDL
genuinely omits one here: `genealogy_node` rows are pure insert-only facts (GEN-FR-016, no update path at
all), and `genealogy_edge` rows are corrected by flipping `state` to SUPERSEDED and inserting a new row
referencing `supersedes_edge_id` (GEN-FR-017), not by incrementing a version counter.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '5e23e1067790'
down_revision: Union[str, Sequence[str], None] = '0cb6e2ece7c0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'genealogy_node',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('node_type', sa.String(length=60), nullable=False),
        sa.Column('business_ref', sa.String(length=200), nullable=True),
        sa.Column('authoritative_record_type', sa.String(length=80), nullable=True),
        sa.Column('authoritative_record_id', sa.UUID(), nullable=True),
        sa.Column('authoritative_version', sa.BigInteger(), nullable=True),
        sa.Column('record_hash', sa.String(length=64), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_genealogy_node_type_ref', 'genealogy_node', ['node_type', 'business_ref'], schema='ebmr')
    op.create_index('ix_genealogy_node_authoritative', 'genealogy_node', ['authoritative_record_id'], schema='ebmr')

    op.create_table(
        'genealogy_edge',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('from_node_id', sa.UUID(), nullable=False),
        sa.Column('to_node_id', sa.UUID(), nullable=False),
        sa.Column('edge_type', sa.String(length=60), nullable=False),
        sa.Column('quantity', sa.Numeric(24, 8), nullable=True),
        sa.Column('uom', sa.String(length=40), nullable=True),
        sa.Column('step_id', sa.UUID(), nullable=True),
        sa.Column('source_event_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='ACTIVE'),
        sa.Column('supersedes_edge_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['from_node_id'], ['ebmr.genealogy_node.id']),
        sa.ForeignKeyConstraint(['to_node_id'], ['ebmr.genealogy_node.id']),
        sa.ForeignKeyConstraint(['supersedes_edge_id'], ['ebmr.genealogy_edge.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('from_node_id', 'to_node_id', 'edge_type', 'source_event_id'),
        schema='ebmr',
    )
    op.create_index('ix_genealogy_edge_from', 'genealogy_edge', ['from_node_id', 'edge_type'], schema='ebmr')
    op.create_index('ix_genealogy_edge_to', 'genealogy_edge', ['to_node_id', 'edge_type'], schema='ebmr')
    op.create_index('ix_genealogy_edge_step', 'genealogy_edge', ['step_id'], schema='ebmr')

    # genealogy_edge.state is corrected via controlled UPDATE (correct_edge()), same reasoning as
    # gxp_product_version/gxp_recipe_version/gxp_batch/device_unit -- immutability of a fact comes from
    # the append-only audit trail and the superseding-row pattern, not DB-privilege revocation.
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.genealogy_node TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.genealogy_edge TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.genealogy_edge FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON ebmr.genealogy_node FROM {APP_ROLE}")
    op.drop_table('genealogy_edge', schema='ebmr')
    op.drop_table('genealogy_node', schema='ebmr')
