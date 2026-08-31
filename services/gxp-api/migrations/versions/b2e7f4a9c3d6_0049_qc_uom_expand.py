"""0049_qc_uom_expand

Revision ID: b2e7f4a9c3d6
Revises: a4d9e6c2f8b1
Create Date: 2026-08-27 00:00:00.000000

SG-146 (remainder, module 2 of 8) — the MIG-FR-004 *expand* step for Document 23's three free-text UOM
columns, same pattern `yield_reconciliation` established (migration `a4d9e6c2f8b1`): a nullable
`*_id` FK to `rules.gxp_uom.uom_id`, alongside the existing free-text column (unchanged, still
authoritative). No contract step attempted (MIG-FR-004: at least two releases between expand and
contract).

Two of the three tables differ from `yield_reconciliation` in one important way: `ebmr.qc_test_definition`
and `ebmr.qc_result` have **no UPDATE grant** (migration `4b6e8f0a1c2d` 0021 — append-only once written,
AG-08, the same discipline `qc_result_correction`'s "a correction is a new row" pattern already
enforces). That is a deliberate database-privilege-level control, not loosened here: `uom_id`/`uom_id`
on those two tables can only ever be populated at INSERT time by
`app/modules/qc/commands.py::_resolve_uom_id()`; there is no backfill path for a row written before
this column existed, and none is attempted. `ebmr.qc_sample` is mutable (UPDATE granted) and gets both
dual-write and a real backfill, exactly like `yield_reconciliation`'s tables.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'b2e7f4a9c3d6'
down_revision: Union[str, Sequence[str], None] = 'a4d9e6c2f8b1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('qc_test_definition', sa.Column('uom_id', sa.UUID(), nullable=True), schema='ebmr')
    op.create_foreign_key(
        'fk_qc_test_definition_uom_id', 'qc_test_definition', 'gxp_uom',
        ['uom_id'], ['uom_id'], source_schema='ebmr', referent_schema='rules',
    )
    op.add_column('qc_sample', sa.Column('sample_uom_id', sa.UUID(), nullable=True), schema='ebmr')
    op.create_foreign_key(
        'fk_qc_sample_sample_uom_id', 'qc_sample', 'gxp_uom',
        ['sample_uom_id'], ['uom_id'], source_schema='ebmr', referent_schema='rules',
    )
    op.add_column('qc_result', sa.Column('uom_id', sa.UUID(), nullable=True), schema='ebmr')
    op.create_foreign_key(
        'fk_qc_result_uom_id', 'qc_result', 'gxp_uom',
        ['uom_id'], ['uom_id'], source_schema='ebmr', referent_schema='rules',
    )


def downgrade() -> None:
    op.drop_constraint('fk_qc_result_uom_id', 'qc_result', schema='ebmr', type_='foreignkey')
    op.drop_column('qc_result', 'uom_id', schema='ebmr')
    op.drop_constraint('fk_qc_sample_sample_uom_id', 'qc_sample', schema='ebmr', type_='foreignkey')
    op.drop_column('qc_sample', 'sample_uom_id', schema='ebmr')
    op.drop_constraint('fk_qc_test_definition_uom_id', 'qc_test_definition', schema='ebmr', type_='foreignkey')
    op.drop_column('qc_test_definition', 'uom_id', schema='ebmr')
