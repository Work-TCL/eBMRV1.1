"""0107_step_comment_schema

Revision ID: c5ab6dc91f35
Revises: fbed8e7ccb3e
Create Date: 2026-09-14 00:00:00.000000

Document 11 (SPEC-EBMR-002) -- BAT-FR-034, SG-048 #034 partial resolution, project-owner-directed. New
`ebmr.gxp_step_comment` table: "Structured comments/notes may be added with author/time." Append-only, same
shape as `gxp_step_result`/`gxp_step_evidence_link` (SELECT/INSERT/TRUNCATE only, no UPDATE -- AG-08).
"Corrections to comments preserve history if regulated" is not built -- no correction chain for a comment
itself this pass, the same narrower-than-full-generality scope SG-047's own StepEvidenceLink accepted.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c5ab6dc91f35'
down_revision: Union[str, Sequence[str], None] = 'fbed8e7ccb3e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_step_comment',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=False),
        sa.Column('comment_text', sa.String(length=2000), nullable=False),
        sa.Column('created_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['step_id'], ['ebmr.gxp_batch_step.id']),
        sa.ForeignKeyConstraint(['created_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_gxp_step_comment_step_id', 'gxp_step_comment', ['step_id'], schema='ebmr')

    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.gxp_step_comment TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.gxp_step_comment FROM {APP_ROLE}")
    op.drop_index('ix_gxp_step_comment_step_id', table_name='gxp_step_comment', schema='ebmr')
    op.drop_table('gxp_step_comment', schema='ebmr')