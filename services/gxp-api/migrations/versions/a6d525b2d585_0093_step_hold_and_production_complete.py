"""0093_step_hold_and_production_complete

Revision ID: a6d525b2d585
Revises: db47f27cf18b
Create Date: 2026-09-09 00:00:00.000000

Document 11 (SPEC-EBMR-002) — SG-047/SG-048 further partial resolution, project-owner-directed (asked
which of the six remaining demo gaps to build; chose step-level hold + Production Complete batch state,
deferred material/equipment linkage pending an SG-045 schema decision).

Two additive, independent changes:

1. `gxp_batch_step_hold` — a narrow, step-scoped slice of the still-open `gxp_batch_hold` entity
   (BAT-FR-020). One row per hold episode (`released_at IS NULL` = currently active); both hold and
   release are signed, reusing Document 106 row 14/17's shapes (the nearest analogous batch-level
   actions — no step-scoped row exists in Document 106 itself). Not the full `gxp_batch_hold` generality
   (arbitrary scope, quality-event linkage) — SG-047 stays open for that.
2. `ebmr.gxp_batch.state` gains `'production_complete'`, reachable from `'in_execution'` once every
   `gxp_batch_step` is `'complete'` (BAT-FR-026's steps-completeness sub-clause only — yield/reconciliation
   and other "production blockers" the requirement also names have no Document 17 linkage to check against
   yet, SG-048 #026 stays open for those). No column change needed — `state` is already a free-text
   varchar; `production_completed_at` (already a catalogued `gxp_batch` column, unused until now) is
   populated on this transition.

Mutable in-execution state (same privilege shape as `gxp_batch`/`gxp_batch_step` themselves, migration
f264272f2f0b_0012): SELECT/INSERT/UPDATE/TRUNCATE granted, no DELETE. UPDATE is needed to set
`released_at`/etc. on the *same* row when the hold is released (a release-in-place status field on an
open episode, not editing settled history); TRUNCATE matches every other mutable regulated-state table in
this schema and is what the test suite's `clean_database` fixture needs between runs.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a6d525b2d585'
down_revision: Union[str, Sequence[str], None] = 'db47f27cf18b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_batch_step_hold',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('reason', sa.String(length=2000), nullable=False),
        sa.Column('held_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('held_by', sa.UUID(), nullable=False),
        sa.Column('hold_signature_id', sa.UUID(), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('released_by', sa.UUID(), nullable=True),
        sa.Column('release_reason', sa.String(length=2000), nullable=True),
        sa.Column('release_signature_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['step_id'], ['ebmr.gxp_batch_step.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.gxp_batch.id']),
        sa.ForeignKeyConstraint(['held_by'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['released_by'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['hold_signature_id'], ['signature.signatures.id']),
        sa.ForeignKeyConstraint(['release_signature_id'], ['signature.signatures.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_gxp_batch_step_hold_step_id', 'gxp_batch_step_hold', ['step_id'], schema='ebmr')
    op.create_index('ix_gxp_batch_step_hold_batch_id', 'gxp_batch_step_hold', ['batch_id'], schema='ebmr')

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.gxp_batch_step_hold TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.gxp_batch_step_hold FROM {APP_ROLE}")
    op.drop_index('ix_gxp_batch_step_hold_batch_id', table_name='gxp_batch_step_hold', schema='ebmr')
    op.drop_index('ix_gxp_batch_step_hold_step_id', table_name='gxp_batch_step_hold', schema='ebmr')
    op.drop_table('gxp_batch_step_hold', schema='ebmr')
