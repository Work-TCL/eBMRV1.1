"""0051_batch_genealogy_recipe_product_uom_expand

Revision ID: e7b3f9a2c6d4
Revises: c5f1a8d3e7b4
Create Date: 2026-08-27 00:00:00.000000

SG-146 (remainder, modules 4-8 of 8, all in one migration) — the MIG-FR-004 *expand* step for the last
six free-text UOM columns across five modules. All six tables are mutable (UPDATE granted) — checked
against each table's own GRANT statement, not re-derived — so every column gets both dual-write
(`app/modules/<module>/commands.py` or `service.py`, each via its own `_resolve_uom_id()`) and a real
chunked/resumable backfill (`app/modules/<module>/uom_backfill.py` + `scripts/backfill_<module>_uom.py`).
No contract step attempted (MIG-FR-004: at least two releases between expand and contract).

- `ebmr.batches.uom_id` — `app/modules/batch` is a *separate, still-live* legacy Batch implementation
  from `app/modules/batch_execution` (confirmed: both routers are mounted in `app/main.py`, at `/batches`
  and `/batches/v1` respectively) — not the same table, both needed their own column.
- `ebmr.gxp_batch.target_uom_id` — `app/modules/batch_execution`, the current Batch Execution Engine
  (the one `yield_reconciliation`/`qc` actually FK into).
- `ebmr.genealogy_edge.uom_id` — `app/modules/genealogy`; the one write site lives in `service.py`, not
  `commands.py` (this module has no command layer of its own yet, Document 13 §8).
- `ebmr.gxp_recipe_version.batch_size_uom_id` and `ebmr.gxp_recipe_parameter.uom_id` —
  `app/modules/recipe_master`, two columns, two write sites, one shared `uom_backfill.py`.
- `ebmr.gxp_product_version.strength_uom_id` — `app/modules/product_master`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'e7b3f9a2c6d4'
down_revision: Union[str, Sequence[str], None] = 'c5f1a8d3e7b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (table, id_column, fk_name)
_COLUMNS = [
    ('batches', 'uom_id', 'fk_batches_uom_id'),
    ('gxp_batch', 'target_uom_id', 'fk_gxp_batch_target_uom_id'),
    ('genealogy_edge', 'uom_id', 'fk_genealogy_edge_uom_id'),
    ('gxp_recipe_version', 'batch_size_uom_id', 'fk_gxp_recipe_version_batch_size_uom_id'),
    ('gxp_recipe_parameter', 'uom_id', 'fk_gxp_recipe_parameter_uom_id'),
    ('gxp_product_version', 'strength_uom_id', 'fk_gxp_product_version_strength_uom_id'),
]


def upgrade() -> None:
    for table, column, fk_name in _COLUMNS:
        op.add_column(table, sa.Column(column, sa.UUID(), nullable=True), schema='ebmr')
        op.create_foreign_key(
            fk_name, table, 'gxp_uom', [column], ['uom_id'], source_schema='ebmr', referent_schema='rules',
        )


def downgrade() -> None:
    for table, column, fk_name in reversed(_COLUMNS):
        op.drop_constraint(fk_name, table, schema='ebmr', type_='foreignkey')
        op.drop_column(table, column, schema='ebmr')
