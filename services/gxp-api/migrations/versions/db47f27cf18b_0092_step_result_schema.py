"""0092_step_result_schema

Revision ID: db47f27cf18b
Revises: f7a1c3e5b9d2
Create Date: 2026-09-09 00:00:00.000000

Document 11 (SPEC-EBMR-002) — SG-047 partial resolution, project-owner-directed (asked directly after a
live demo batch got stuck at BAT-FR-006's predecessor-only readiness slice with no way to ever complete a
step; chose "build step completion now" over "leave it a documented gap").

SG-047 deferred `gxp_step_result` because its `value_decimal/text/bool/json` line describes a polymorphic
column with no stated discriminator/precision/UOM rule (Document 110 territory). This migration resolves
that narrowly, without inventing a new precision policy: the discriminator is `data_type`, copied verbatim
from the already-DDL-ready `ebmr.gxp_recipe_parameter.data_type` the value is captured against, and the
numeric column reuses that same table's own `Numeric(24, 8)` precision convention (matching
`gxp_recipe_parameter.target_value/min_value/max_value` and `gxp_batch.target_qty`) rather than picking a
new one. `gxp_step_evidence_link` and `gxp_batch_hold` are NOT built here — evidence-manifest alignment
with Document 06 and a hold record's signature-policy binding are separate judgment calls this change does
not make; SG-047 stays open for those two.

Scope kept deliberately narrow (see SG-048's adjacent gaps, still open): `source_type` is fixed to
'manual' (BAT-FR-010; device/edge sourcing is BAT-FR-011, SG-048 #011, not built). No
`supersedes_result_id`/correction chain (BAT-FR-023, SG-048 #023, not built) — `result_version` is kept at
a constant 1 for forward schema compatibility only. No `rule_evaluation_id` linkage (the rules-engine
in-line evaluation BAT-FR-009 also names is not wired to step results this pass).

Append-only by DB privilege (AG-08 evidence-adjacent discipline): SELECT/INSERT/TRUNCATE only, no UPDATE
grant — a captured result is never edited in place.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'db47f27cf18b'
down_revision: Union[str, Sequence[str], None] = 'f7a1c3e5b9d2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_step_result',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=False),
        sa.Column('parameter_code', sa.String(length=80), nullable=False),
        sa.Column('data_type', sa.String(length=40), nullable=False),
        sa.Column('result_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('value_numeric', sa.Numeric(24, 8), nullable=True),
        sa.Column('value_text', sa.String(length=2000), nullable=True),
        sa.Column('value_bool', sa.Boolean(), nullable=True),
        sa.Column('uom', sa.String(length=40), nullable=True),
        sa.Column('source_type', sa.String(length=40), nullable=False, server_default='manual'),
        sa.Column('source_timestamp', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['step_id'], ['ebmr.gxp_batch_step.id']),
        sa.ForeignKeyConstraint(['created_by'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['signature_id'], ['signature.signatures.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_gxp_step_result_step_id', 'gxp_step_result', ['step_id'], schema='ebmr')

    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.gxp_step_result TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.gxp_step_result FROM {APP_ROLE}")
    op.drop_index('ix_gxp_step_result_step_id', table_name='gxp_step_result', schema='ebmr')
    op.drop_table('gxp_step_result', schema='ebmr')
