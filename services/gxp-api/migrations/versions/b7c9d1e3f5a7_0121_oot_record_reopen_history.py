"""0121_oot_record_reopen_history

Revision ID: b7c9d1e3f5a7
Revises: a1b2c3d4e5f6
Create Date: 2026-09-23 00:00:00.000000

SG-074 Task 3 Part B -- adds a `reopen_history` column to `ebmr.oot_record`, the same append-only-array
shape as `qms.deviation_record.reopen_history`/`qms.capa_record.reopen_history` (Document 106-style
reopen ceremony: reason + new_evidence, permission-gated, unsigned). `oot_record` is prose-only/typed as
an ordinary engineering decision (unlike `oos_record`, which is DDL-ready with an exact 17-column list --
no column is added there this pass; see SG-074's register entry for why OOS reopen was deferred instead).
Additive, NOT NULL with a `'[]'::jsonb` default so no existing row needs rewriting (AG-08).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'b7c9d1e3f5a7'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'oot_record',
        sa.Column('reopen_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        schema='ebmr',
    )


def downgrade() -> None:
    op.drop_column('oot_record', 'reopen_history', schema='ebmr')
