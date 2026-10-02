"""0126_material_lot_coa_reliance

Revision ID: a3c5e7f9b1d4
Revises: f1b3d5a7c9e2
Create Date: 2026-10-02 00:00:00.000000

Client_Decisions_Neededanswers Topics 1/2 (SG-076 required-test half): `release_material_lot` now blocks
release until every required+release_blocking QC test for the lot's material has a passing reviewed
result, unless QA explicitly relies on the supplier's COA instead (approved supplier + COA on file +
documented reason). Adds the two columns that record when/why that reliance was used. Purely additive,
both nullable/defaulted -- no backfill needed, existing lots are all non-reliance.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a3c5e7f9b1d4'
down_revision: Union[str, Sequence[str], None] = 'f1b3d5a7c9e2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'material_lots',
        sa.Column('coa_reliance', sa.Boolean(), nullable=False, server_default=sa.false()),
        schema='materials',
    )
    op.add_column(
        'material_lots',
        sa.Column('coa_reliance_reason', sa.String(length=2000), nullable=True),
        schema='materials',
    )


def downgrade() -> None:
    op.drop_column('material_lots', 'coa_reliance_reason', schema='materials')
    op.drop_column('material_lots', 'coa_reliance', schema='materials')
