"""0084_material_lot_supplier_link

Revision ID: a1b3c5d7e9f2
Revises: d78ea4eb751a
Create Date: 2026-09-03 00:00:00.000000

Adds a nullable `supplier_id` FK (-> `ebmr.supplier.id`, same target `material_receipts.supplier_id`
already uses per migration `35fca517ebb6` 0027) to `materials.material_lots`, for the quick "Receive
lot" path (`ReceiveMaterialLotCommand`) — informational/traceability only, exactly like the pre-existing
free-text `supplier_lot` column it sits alongside. It does **not** run the RCV-FR-005 supplier-approval
check that `examine_receipt()` runs on the Document 19 Receipt -> Examine path; that check stays the
single source of truth for whether an unapproved supplier blocks a lot. Grant classification: mutable
(UPDATE already granted on `material_lots` per migration `c5f1a8d3e7b4` 0050's table split) — a plain
column add needs no new grant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b3c5d7e9f2'
down_revision: Union[str, Sequence[str], None] = 'd78ea4eb751a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('material_lots', sa.Column('supplier_id', sa.UUID(), nullable=True), schema='materials')
    op.create_foreign_key(
        'fk_material_lots_supplier_id', 'material_lots', 'supplier', ['supplier_id'], ['id'],
        source_schema='materials', referent_schema='ebmr',
    )


def downgrade() -> None:
    op.drop_constraint('fk_material_lots_supplier_id', 'material_lots', schema='materials', type_='foreignkey')
    op.drop_column('material_lots', 'supplier_id', schema='materials')
