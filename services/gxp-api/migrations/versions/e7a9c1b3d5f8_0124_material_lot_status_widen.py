"""0124_material_lot_status_widen

Revision ID: e7a9c1b3d5f8
Revises: d5f7a9b1c3e6
Create Date: 2026-09-24 00:00:00.000000

Found incidentally while building Workflow Handoff Notifications (app/modules/notifications), not itself
part of that feature: `materials.material_lots.status` is `VARCHAR(20)`, but `app/modules/material/
models.py::LOT_STATES` already names `"qc_disposition_pending"` (22 chars) as a valid value -- the column
could never actually hold it; any real command that tried to write that exact state would fail closed with
a DB truncation error. Additive-safe: widening a VARCHAR never rewrites existing rows or loses data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7a9c1b3d5f8'
down_revision: Union[str, Sequence[str], None] = 'd5f7a9b1c3e6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'material_lots', 'status', type_=sa.String(length=40), existing_type=sa.String(length=20),
        existing_nullable=False, schema='materials',
    )


def downgrade() -> None:
    op.alter_column(
        'material_lots', 'status', type_=sa.String(length=20), existing_type=sa.String(length=40),
        existing_nullable=False, schema='materials',
    )
