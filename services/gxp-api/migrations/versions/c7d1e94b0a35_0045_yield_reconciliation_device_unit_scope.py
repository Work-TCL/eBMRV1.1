"""0045_yield_reconciliation_device_unit_scope

Revision ID: c7d1e94b0a35
Revises: 8b0a2368600c
Create Date: 2026-08-27 00:00:00.000000

Document 17 (SPEC-EBMR-008) — YLD-FR-013/026 (SG-132 partial resolution). Adds the per-unit device scope
this module was missing: `device_unit_id` on both `ebmr.manufacturing_calculations` and
`ebmr.reconciliation_records`, foreign-keyed to Document 12's `ebmr.device_unit`.

Additive and nullable, so it is backward-compatible with every row written by 0044: MATERIAL/PACKAGING/
LABEL reconciliation is batch- or run-scoped and legitimately has no device unit. No data migration is
needed and no existing row changes (AG-08 — nothing already written is rewritten).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c7d1e94b0a35'
down_revision: Union[str, Sequence[str], None] = '8b0a2368600c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'manufacturing_calculations',
        sa.Column('device_unit_id', sa.UUID(), nullable=True),
        schema='ebmr',
    )
    op.create_foreign_key(
        'fk_manufacturing_calculations_device_unit', 'manufacturing_calculations', 'device_unit',
        ['device_unit_id'], ['id'], source_schema='ebmr', referent_schema='ebmr',
    )

    op.add_column(
        'reconciliation_records',
        sa.Column('device_unit_id', sa.UUID(), nullable=True),
        schema='ebmr',
    )
    op.create_foreign_key(
        'fk_reconciliation_records_device_unit', 'reconciliation_records', 'device_unit',
        ['device_unit_id'], ['id'], source_schema='ebmr', referent_schema='ebmr',
    )
    # YLD-FR-026 aggregates reconciliation rows per device unit; without this the summary read is a
    # sequential scan of every reconciliation row in the batch.
    op.create_index(
        'ix_reconciliation_records_device_unit', 'reconciliation_records', ['device_unit_id'], schema='ebmr',
    )


def downgrade() -> None:
    op.drop_index('ix_reconciliation_records_device_unit', 'reconciliation_records', schema='ebmr')
    op.drop_constraint('fk_reconciliation_records_device_unit', 'reconciliation_records', schema='ebmr', type_='foreignkey')
    op.drop_column('reconciliation_records', 'device_unit_id', schema='ebmr')
    op.drop_constraint('fk_manufacturing_calculations_device_unit', 'manufacturing_calculations', schema='ebmr', type_='foreignkey')
    op.drop_column('manufacturing_calculations', 'device_unit_id', schema='ebmr')
