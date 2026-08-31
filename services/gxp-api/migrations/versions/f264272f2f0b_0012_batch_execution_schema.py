"""0012_batch_execution_schema

Revision ID: f264272f2f0b
Revises: d0a1a1bdfaef
Create Date: 2026-08-24 00:00:00.000000

Document 11 (SPEC-EBMR-002) — Batch Execution Engine & State Machine. Additive only: creates 2 new tables
(`gxp_batch`, `gxp_batch_step`) in the existing `ebmr` schema; does not touch `ebmr.batches`,
`ebmr.batch_steps`, `ebmr.batch_reviews`, `ebmr.batch_releases`, `ebmr.products`, `ebmr.recipes` at all.
`Batch`/`BatchStep` (app/modules/batch) keep using the legacy stub tables unmodified this pass — SG-044's
Batch/Recipe cutover, now technically unblocked since Document 10 exists, is still its own future body of
work, not bundled into this migration.

Per docs/generated/04_DATA_MODEL_CATALOGUE.md, only 2 of Document 11's 5 owned entities are DDL-ready:
`gxp_batch` and `gxp_batch_step`, both typed here directly. The other 3 (`gxp_step_result`,
`gxp_step_evidence_link`, `gxp_batch_hold`) are prose-only field-name lists with no types — deferred as
SG-047, same resolution path as Document 10's SG-045.

Same deviations as prior additive migrations (d5d48a66187f, d0a1a1bdfaef): `tenant_id` dropped
(single-organization platform), `version` bigint (optimistic concurrency) kept explicit on both tables.
One addition beyond the catalogue's own column list: `gxp_batch.recipe_version_id`, a live FK to
`ebmr.gxp_recipe_version.id` — required to read the released recipe's step graph at issue time; the
catalogue's own `recipe_vault_object_id` column is also kept and populated from
`RecipeVersion.released_vault_object_id` at batch-creation time. `gxp_batch_step.branch_status`,
`.exception_state` and `.temporal_workflow_ref` are created as specified but are not written by any
command this pass (see models.py docstring) — their producing requirements (BAT-FR-021/022/028) are
deferred by SG-048.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f264272f2f0b'
down_revision: Union[str, Sequence[str], None] = 'd0a1a1bdfaef'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_batch',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_number', sa.String(length=120), nullable=False),
        sa.Column('product_version_id', sa.UUID(), nullable=False),
        sa.Column('recipe_version_id', sa.UUID(), nullable=False),
        sa.Column('recipe_vault_object_id', sa.UUID(), nullable=True),
        sa.Column('execution_snapshot_id', sa.UUID(), nullable=True),
        sa.Column('target_qty', sa.Numeric(24, 8), nullable=False),
        sa.Column('target_uom', sa.String(length=40), nullable=False),
        sa.Column('state', sa.String(length=50), nullable=False, server_default='planned'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('production_order_ref', sa.String(length=160), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('production_completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('qa_review_started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['product_version_id'], ['ebmr.gxp_product_version.id']),
        sa.ForeignKeyConstraint(['recipe_version_id'], ['ebmr.gxp_recipe_version.id']),
        sa.ForeignKeyConstraint(['recipe_vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.ForeignKeyConstraint(['execution_snapshot_id'], ['vault.gxp_vault_object.object_id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id', 'batch_number'),
        schema='ebmr',
    )

    op.create_table(
        'gxp_batch_step',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('recipe_step_code', sa.String(length=120), nullable=False),
        sa.Column('scope_type', sa.String(length=40), nullable=False, server_default='batch'),
        sa.Column('scope_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='pending'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('assigned_subject_id', sa.UUID(), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('branch_status', sa.String(length=40), nullable=True),
        sa.Column('exception_state', sa.String(length=40), nullable=True),
        sa.Column('temporal_workflow_ref', sa.String(length=255), nullable=True),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.gxp_batch.id']),
        sa.ForeignKeyConstraint(['assigned_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_id', 'recipe_step_code'),
        schema='ebmr',
    )

    # Mutable in-execution state, same reasoning as gxp_product_version/gxp_recipe_version -- immutability
    # of the *released* execution snapshot comes from its Vault object (VLT-FR-001), not DB-privilege
    # revocation on the live rows.
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.gxp_batch TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.gxp_batch_step TO {APP_ROLE}")


def downgrade() -> None:
    for table in ('gxp_batch_step', 'gxp_batch'):
        op.execute(f"REVOKE ALL ON ebmr.{table} FROM {APP_ROLE}")
    op.drop_table('gxp_batch_step', schema='ebmr')
    op.drop_table('gxp_batch', schema='ebmr')
