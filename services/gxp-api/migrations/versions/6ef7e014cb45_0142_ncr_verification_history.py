"""0142_ncr_verification_history

Revision ID: 6ef7e014cb45
Revises: 1366477a0962
Create Date: 2026-10-09 00:00:00.000000

Project-owner-directed: `verify_ncr()` previously allowed exactly one verification (VERIFICATION had no
self-loop in NCR_ALLOWED_TRANSITIONS) and overwrote `nonconformance_record.verification` in place on
every call -- a second verification round (e.g. a failed first attempt, or an independent re-check) was
both unreachable and, had it been reachable, would have destroyed the first verification's evidence
(an AG-08 violation: evidence must be append-only, never overwritten). Adds `verification_history`, the
same append-only-array shape as this table's own `closure_history`/`reopen_history` columns --
`verification` itself is kept unchanged (still the latest snapshot, for existing consumers), this is
purely additive. NOT NULL with a `'[]'::jsonb` default so no existing row needs rewriting.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '6ef7e014cb45'
down_revision: Union[str, Sequence[str], None] = '1366477a0962'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'nonconformance_record',
        sa.Column('verification_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        schema='qms',
    )


def downgrade() -> None:
    op.drop_column('nonconformance_record', 'verification_history', schema='qms')
