"""0140_em_excursion_disposition_widen

Revision ID: f3b8d6a9c2e4
Revises: a7c9e1b3d5f0
Create Date: 2026-10-08 00:00:00.000000

Found live while testing the EM module (docs/testing/demo-gujarati session): `equipment.em_excursions.
disposition` is `VARCHAR(40)`, but `RecordExcursionImpactCommand.disposition` (app/modules/equipment/
em_commands.py) is a plain unbounded `str | None` with no length validation anywhere above the database --
any realistic disposition narrative ("Area re-sampled, result within limit - no batch impact confirmed",
66 chars) truncates at the DB layer with an uncaught `StringDataRightTruncationError`, surfacing to the
caller as an opaque 500 `SYSTEM_FAULT` rather than a clean validation error. Same bug class as migration
0124 (material_lots.status widen) -- a column too narrow for a value the application layer already
produces. Widened to `TEXT` (unbounded) rather than a larger fixed VARCHAR, matching the equipment
module's own precedent for narrative fields of unpredictable length (`equipment_assets.fault_description`/
`diagnosis`/`work_performed`, all `Text()`) -- a disposition write-up has no natural length cap either.
Additive-safe: widening a column never rewrites existing rows or loses data.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f3b8d6a9c2e4'
down_revision: Union[str, Sequence[str], None] = 'a7c9e1b3d5f0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column(
        'em_excursions', 'disposition', type_=sa.Text(), existing_type=sa.String(length=40),
        existing_nullable=True, schema='equipment',
    )


def downgrade() -> None:
    op.alter_column(
        'em_excursions', 'disposition', type_=sa.String(length=40), existing_type=sa.Text(),
        existing_nullable=True, schema='equipment',
    )
