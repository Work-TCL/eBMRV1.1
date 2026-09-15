"""0108_step_handover_schema

Revision ID: 164abb1a20dc
Revises: c5ab6dc91f35
Create Date: 2026-09-14 00:00:00.000000

Document 11 (SPEC-EBMR-002) -- BAT-FR-025, SG-048 #025 partial resolution, project-owner-directed (asked
whether to build unsigned/RBAC-gated interim or skip pending a Document 106 addendum; chose build-unsigned,
same interim-scope precedent StepEvidenceLink already established). New `ebmr.gxp_step_handover` table:
"Support controlled operator handover without changing prior attribution." Append-only (SELECT/INSERT/
TRUNCATE only, AG-08) -- a handover event is never edited, only added to.

No Document 106 policy row exists for this action (this is exactly the gap this migration's own commit
message flags for a future addendum) -- unsigned by design, same precedent as `link_step_evidence`. The
"active step may require pause/checklist/signature" clause's conditional signature requirement is
therefore not built; resolving it needs the same kind of human policy decision SG-048 #017/#021 are
already waiting on.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '164abb1a20dc'
down_revision: Union[str, Sequence[str], None] = 'c5ab6dc91f35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_step_handover',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=False),
        sa.Column('from_subject_id', sa.UUID(), nullable=True),
        sa.Column('to_subject_id', sa.UUID(), nullable=False),
        sa.Column('reason', sa.String(length=2000), nullable=True),
        sa.Column('handed_over_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['step_id'], ['ebmr.gxp_batch_step.id']),
        sa.ForeignKeyConstraint(['from_subject_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['to_subject_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['handed_over_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_gxp_step_handover_step_id', 'gxp_step_handover', ['step_id'], schema='ebmr')

    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.gxp_step_handover TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.gxp_step_handover FROM {APP_ROLE}")
    op.drop_index('ix_gxp_step_handover_step_id', table_name='gxp_step_handover', schema='ebmr')
    op.drop_table('gxp_step_handover', schema='ebmr')