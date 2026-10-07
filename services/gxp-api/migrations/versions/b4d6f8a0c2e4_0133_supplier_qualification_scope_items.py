"""0133_supplier_qualification_scope_items

Revision ID: b4d6f8a0c2e4
Revises: a2c4e6f8b0d1
Create Date: 2026-10-05 00:00:00.000000

Client gap-analysis Phase 3 (Supplier UX, 2026-10-05): `supplier_qualification.scope` was a free-text
JSONB label/value blob with no link to an actual Material record. This adds the structured join the
client asked for (an "Add Material" control instead of free text) -- also the MAT-003 "Approved Supplier
List" material-to-approved-supplier relationship named in the architecture rules extract, not a bespoke
UI-only table. Purely additive: `scope` is left in place for freeform notes (per project-owner direction,
both are kept), no existing column changes.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b4d6f8a0c2e4'
down_revision: Union[str, Sequence[str], None] = 'a2c4e6f8b0d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'supplier_qualification_scope_item',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('supplier_qualification_id', sa.UUID(), nullable=False),
        sa.Column('material_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['supplier_qualification_id'], ['ebmr.supplier_qualification.id']),
        sa.ForeignKeyConstraint(['material_id'], ['materials.materials.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('supplier_qualification_id', 'material_id'),
        schema='ebmr',
    )
    op.create_index(
        'ix_supplier_qualification_scope_item_qual',
        'supplier_qualification_scope_item',
        ['supplier_qualification_id'],
        schema='ebmr',
    )
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.supplier_qualification_scope_item TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.supplier_qualification_scope_item FROM {APP_ROLE}")
    op.drop_table('supplier_qualification_scope_item', schema='ebmr')
