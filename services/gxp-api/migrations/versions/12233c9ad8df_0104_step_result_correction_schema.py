"""0104_step_result_correction_schema

Revision ID: 12233c9ad8df
Revises: c3f7a9d2b6e4
Create Date: 2026-09-14 00:00:00.000000

Document 11 (SPEC-EBMR-002) -- BAT-FR-023, SG-048 #023 partial resolution. Migration db47f27cf18b_0092
("gxp_step_result") deliberately deferred a correction chain, naming the exact shape this migration now
builds: `supersedes_result_id` on `gxp_step_result` (nullable -- NULL on every ordinarily-recorded result,
set only on the new row a correction produces) plus a new `gxp_step_result_correction` staging table for
the 2-signature `POST /batches/{id}/steps/{stepId}/correct` ceremony Document 106 row 20 requires
("Authorized corrector + independent approver", 2 signatures, corrector and approver MUST differ,
mandatory reason-for-change).

Same additive-staging-table pattern as `qc_result_correction` (migration 4b6e8f0a1c2d_0021, Document 106
row 57's identical shape) -- not one of Document 11's own catalogued entities, an ordinary engineering
decision to reuse an already-reviewed correction-ceremony shape rather than invent a new one.

`gxp_step_result` keeps its existing SELECT/INSERT/TRUNCATE-only grant (append-only, AG-08) -- the new
column is only ever set on INSERT, never by UPDATE. `gxp_step_result_correction` is mutable (its `status`
transitions requested -> completed) and gets the same SELECT/INSERT/UPDATE/TRUNCATE grant
`qc_result_correction` has.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '12233c9ad8df'
down_revision: Union[str, Sequence[str], None] = 'c3f7a9d2b6e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.add_column(
        'gxp_step_result',
        sa.Column('supersedes_result_id', sa.UUID(), nullable=True),
        schema='ebmr',
    )
    op.create_foreign_key(
        'fk_gxp_step_result_supersedes_result_id',
        'gxp_step_result', 'gxp_step_result',
        ['supersedes_result_id'], ['id'],
        source_schema='ebmr', referent_schema='ebmr',
    )

    op.create_table(
        'gxp_step_result_correction',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('original_result_id', sa.UUID(), nullable=False),
        sa.Column('reason_text', sa.String(length=2000), nullable=False),
        sa.Column('corrected_value_numeric', sa.Numeric(24, 8), nullable=True),
        sa.Column('corrected_value_text', sa.String(length=2000), nullable=True),
        sa.Column('corrected_value_bool', sa.Boolean(), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='requested'),
        sa.Column('requested_by_user_id', sa.UUID(), nullable=False),
        sa.Column('requested_signature_id', sa.UUID(), nullable=True),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_signature_id', sa.UUID(), nullable=True),
        sa.Column('resulting_result_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['original_result_id'], ['ebmr.gxp_step_result.id']),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['requested_signature_id'], ['signature.signatures.id']),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['approved_signature_id'], ['signature.signatures.id']),
        sa.ForeignKeyConstraint(['resulting_result_id'], ['ebmr.gxp_step_result.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index(
        'ix_gxp_step_result_correction_original_result_id',
        'gxp_step_result_correction', ['original_result_id'], schema='ebmr',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.gxp_step_result_correction TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.gxp_step_result_correction FROM {APP_ROLE}")
    op.drop_index('ix_gxp_step_result_correction_original_result_id', table_name='gxp_step_result_correction', schema='ebmr')
    op.drop_table('gxp_step_result_correction', schema='ebmr')
    op.drop_constraint('fk_gxp_step_result_supersedes_result_id', 'gxp_step_result', schema='ebmr', type_='foreignkey')
    op.drop_column('gxp_step_result', 'supersedes_result_id', schema='ebmr')