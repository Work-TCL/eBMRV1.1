"""0046_reconciliation_loss_reasons_external_comparison

Revision ID: d4a8f2c60b19
Revises: c7d1e94b0a35
Create Date: 2026-08-27 00:00:00.000000

Document 17 (SPEC-EBMR-008) — YLD-FR-021/027 (SG-132 partial resolution, second pass).

- `loss_reasons` (YLD-FR-021): the documented reasons/categories behind an `approved_loss` quantity, so
  the loss is explained rather than merely counted. JSONB list of {category, description, quantity?}.
- `external_comparison` (YLD-FR-027): the outcome of comparing an ERP/WMS quantity against the
  GxP-computed total. Evidence that the comparison ran and what it found; it never feeds back into
  `variance`, which stays the GxP-authoritative number.

Both additive and nullable on `ebmr.reconciliation_records` — no rewrite, no backfill, no existing row
altered (AG-08). Rows written before this revision legitimately carry NULL for both.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'd4a8f2c60b19'
down_revision: Union[str, Sequence[str], None] = 'c7d1e94b0a35'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'reconciliation_records',
        sa.Column('loss_reasons', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema='ebmr',
    )
    op.add_column(
        'reconciliation_records',
        sa.Column('external_comparison', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema='ebmr',
    )


def downgrade() -> None:
    op.drop_column('reconciliation_records', 'external_comparison', schema='ebmr')
    op.drop_column('reconciliation_records', 'loss_reasons', schema='ebmr')
