"""0141_ncr_reopen_history

Revision ID: 1366477a0962
Revises: f3b8d6a9c2e4
Create Date: 2026-10-09 00:00:00.000000

SG-069 resolved (project-owner-directed): adds a `reopen_history` column to `qms.nonconformance_record`,
the same append-only-array shape as `qms.deviation_record.reopen_history`/`qms.capa_record.reopen_history`
(Document 106-style reopen ceremony: reason + new_evidence, permission-gated, unsigned) -- NCR-FR-016
names the capability but Document 28's own 6-op API list never defined a reopen operation, unlike
Documents 26/27 which both did. Mirrors that existing, already-approved pattern exactly rather than
inventing a new contract. Additive, NOT NULL with a `'[]'::jsonb` default so no existing row needs
rewriting (AG-08).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '1366477a0962'
down_revision: Union[str, Sequence[str], None] = 'f3b8d6a9c2e4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'nonconformance_record',
        sa.Column('reopen_history', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        schema='qms',
    )


def downgrade() -> None:
    op.drop_column('nonconformance_record', 'reopen_history', schema='qms')
