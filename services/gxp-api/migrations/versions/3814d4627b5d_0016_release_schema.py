"""0016_release_schema

Revision ID: 3814d4627b5d
Revises: d05689ef6618
Create Date: 2026-08-24 00:00:00.000000

Document 15 (SPEC-EBMR-006) — Release / Disposition Engine. Creates 3 new tables (`release_scope`,
`release_evaluation`, `release_decision`) in the existing `ebmr` schema. No legacy release module exists
outside the Batch stub's own `release_batch`/`BatchRelease` (app/modules/batch), which this migration
does not touch.

`release_scope` is DDL-ready in docs/generated/04_DATA_MODEL_CATALOGUE.md. `release_evaluation` and
`release_decision` are prose-only field-name lists there, but -- like 5 of Document 10's 9 entities
(SG-045's reasoning) -- both are genuinely unambiguous (no polymorphic value typing, no missing
referenced entity); typed here directly as an ordinary engineering decision. Document 15 §6 supplies a
concrete JSON shape for `release_evaluation.blockers`.

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform).
`release_scope.current_evaluation_id` has no FK constraint (avoids a circular dependency with
release_evaluation.release_scope_id, which already enforces the real relationship from the other side) --
a plain pointer column, same latitude already used for other logical-reference columns in this codebase.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '3814d4627b5d'
down_revision: Union[str, Sequence[str], None] = 'd05689ef6618'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'release_scope',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('scope_type', sa.String(length=40), nullable=False),
        sa.Column('scope_id', sa.UUID(), nullable=False),
        sa.Column('product_version_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='draft_evaluation'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('current_evaluation_id', sa.UUID(), nullable=True),
        sa.Column('released_vault_object_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('decision_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['product_version_id'], ['ebmr.gxp_product_version.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.gxp_batch.id']),
        sa.ForeignKeyConstraint(['released_vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('scope_type', 'scope_id'),
        schema='ebmr',
    )

    op.create_table(
        'release_evaluation',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('release_scope_id', sa.UUID(), nullable=False),
        sa.Column('scope_version', sa.BigInteger(), nullable=False),
        sa.Column('rule_set_version', sa.String(length=40), nullable=True),
        sa.Column('evaluated_batch_version', sa.BigInteger(), nullable=False),
        sa.Column('blockers', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('warnings', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('eligible', sa.Boolean(), nullable=False),
        sa.Column('evaluation_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['release_scope_id'], ['ebmr.release_scope.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )

    op.create_table(
        'release_decision',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('release_scope_id', sa.UUID(), nullable=False),
        sa.Column('evaluation_id', sa.UUID(), nullable=False),
        sa.Column('decision_code', sa.String(length=40), nullable=False),
        sa.Column('reason', sa.String(length=2000), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('decision_time', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('release_package_hash', sa.String(length=64), nullable=True),
        sa.ForeignKeyConstraint(['release_scope_id'], ['ebmr.release_scope.id']),
        sa.ForeignKeyConstraint(['evaluation_id'], ['ebmr.release_evaluation.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.release_scope TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.release_evaluation TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.release_decision TO {APP_ROLE}")


def downgrade() -> None:
    for table in ('release_decision', 'release_evaluation', 'release_scope'):
        op.execute(f"REVOKE ALL ON ebmr.{table} FROM {APP_ROLE}")
    op.drop_table('release_decision', schema='ebmr')
    op.drop_table('release_evaluation', schema='ebmr')
    op.drop_table('release_scope', schema='ebmr')
