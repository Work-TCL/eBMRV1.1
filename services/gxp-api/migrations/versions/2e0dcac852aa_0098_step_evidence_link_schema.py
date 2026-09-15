"""0098_step_evidence_link_schema

Revision ID: 2e0dcac852aa
Revises: 4c2d52d2b8a2
Create Date: 2026-09-11 00:00:02.000000

SG-047 (`gxp_step_evidence_link` half). Document 11's prose gave only "step / evidence ID/version/hash /
requirement code" with no types -- reused `vault.gxp_vault_evidence`'s already-approved shape
(evidence_id/evidence_version/evidence_sha256/media_type) exactly, per SG-047's own requirement that this
table "agree with Document 06's Vault evidence manifest shape, not a guessed one."

Append-only: SELECT/INSERT only, same as gxp_step_result (migration db47f27cf18b) -- a step's evidence
trail is never edited in place (AG-08).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2e0dcac852aa'
down_revision: Union[str, Sequence[str], None] = '4c2d52d2b8a2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_step_evidence_link',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=False),
        sa.Column('evidence_id', sa.UUID(), nullable=False),
        sa.Column('evidence_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('evidence_sha256', sa.String(length=64), nullable=False),
        sa.Column('media_type', sa.String(length=120), nullable=True),
        sa.Column('requirement_code', sa.String(length=80), nullable=True),
        sa.Column('linked_by', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['step_id'], ['ebmr.gxp_batch_step.id']),
        sa.ForeignKeyConstraint(['linked_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_gxp_step_evidence_link_step_id', 'gxp_step_evidence_link', ['step_id'], schema='ebmr')

    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.gxp_step_evidence_link TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.gxp_step_evidence_link FROM {APP_ROLE}")
    op.drop_index('ix_gxp_step_evidence_link_step_id', table_name='gxp_step_evidence_link', schema='ebmr')
    op.drop_table('gxp_step_evidence_link', schema='ebmr')
