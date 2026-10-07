"""0127_oos_reopen_change_control_retest_cap

Revision ID: b5d7f9a1c3e6
Revises: a3c5e7f9b1d4
Create Date: 2026-10-02 00:00:00.000000

Client_Decisions_Neededanswers Topic 3 (SG-074): closed OOS investigations had no reopen path, no
Change-Control link column, and no enforced retest cap. Adds `reopen_history`/`change_control_id` to
`oos_record` (mirroring `OotRecord.reopen_history`/`CapaRecord.reopen_history`) and `max_retests` to
`qc_test_definition` (per-test/SOP policy, consulted by `authorize_retest_plan`). Purely additive --
`reopen_history` defaults to an empty JSON array, the other two columns are nullable -- no backfill
needed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'b5d7f9a1c3e6'
down_revision: Union[str, Sequence[str], None] = 'a3c5e7f9b1d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'oos_record',
        sa.Column('reopen_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        schema='ebmr',
    )
    op.add_column(
        'oos_record',
        sa.Column('change_control_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='ebmr',
    )
    op.create_foreign_key(
        'fk_oos_record_change_control_id',
        'oos_record', 'change_control',
        ['change_control_id'], ['id'],
        source_schema='ebmr', referent_schema='qms',
    )
    op.add_column(
        'qc_test_definition',
        sa.Column('max_retests', sa.Integer(), nullable=True),
        schema='ebmr',
    )


def downgrade() -> None:
    op.drop_column('qc_test_definition', 'max_retests', schema='ebmr')
    op.drop_constraint('fk_oos_record_change_control_id', 'oos_record', schema='ebmr', type_='foreignkey')
    op.drop_column('oos_record', 'change_control_id', schema='ebmr')
    op.drop_column('oos_record', 'reopen_history', schema='ebmr')
