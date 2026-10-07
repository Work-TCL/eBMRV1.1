"""0120_drop_legacy_product_recipe_batch_trio

Revision ID: a1b2c3d4e5f6
Revises: 35050c0dbfdb
Create Date: 2026-09-23 00:00:00.000000

SG-044/SG-149/SG-173 Phase 4/5 (ADR-0013, 2026-09-09): `product_master`/`recipe_master`/`batch_execution`
are the sole authoritative stores for product/recipe/batch state. Phase 1 (FK repoint) was completed in
migration e5f7a9c1b3d6 (0090). This migration is Phase 4/5: drop the retired `app.modules.{product,
recipe,batch}` trio's tables now that nothing in the codebase references them (`app/main.py` no longer
mounts `product_router`/`recipe_router`/`batch_router`, `app/all_models.py` no longer imports their
models, and a repo-wide grep for `app.modules.product`/`app.modules.recipe`/`app.modules.batch` outside
those three directories returns nothing).

Confirmed against the live `ebmr_new_gxp` database immediately before writing this migration: `ebmr.products`,
`ebmr.recipes`, `ebmr.recipe_steps`, `ebmr.batches`, `ebmr.batch_steps`, `ebmr.batch_reviews`,
`ebmr.batch_releases` are all empty (0 rows each) -- consistent with ADR-0013's characterization of these
as demo/smoke-test artifacts, not customer data.

One external foreign key was found (via `pg_constraint`, not `information_schema` -- a same-schema-only
join there silently misses cross-schema references): `equipment.aseptic_profile_versions.product_id ->
ebmr.products.id`. This column is nullable, optional on its owning commands
(`app/modules/equipment/aseptic_commands.py`), and unpopulated on both existing rows in the live database
(0 of 2). It is a pre-existing, out-of-scope defect -- WP-06's aseptic module was never repointed onto
`product_master.gxp_product_version` the way WP-02's batch/material FKs were in migration e5f7a9c1b3d6
(0090) -- not something this migration invents. This migration only drops the now-orphaned FK constraint
so the referenced table can be dropped; the column itself is left in place (still nullable, now simply
unconstrained) since redefining what it should reference is a WP-06/equipment-module decision outside
this migration's scope. Logged as a known limitation in SG-044/SG-149/SG-173's registration entry.

Controlled repair (MIG-FR-005 / MIG-FR-026), same discipline as 0087/0088's `RCP-SMOKE*`/`PRD-SMOKE*`
cleanup. `audit.audit_events` / `vault.*` are NOT touched (AG-08 append-only, MIG-FR-013) -- whatever
Created/Released audit trail exists for these legacy rows remains the correct historical record; only the
live (already-empty) regulated tables are dropped. Drop order respects the internal FK chain: batch_releases
/ batch_reviews / batch_steps -> batches; recipe_steps -> recipes; batches/recipes -> products.

Idempotent (`IF EXISTS`, no-op on a database that has already run this migration or never had these
tables). Forward-only: `downgrade()` is a documented no-op (MIG-FR-005 / MIG-FR-031) -- recreating the
dropped legacy schema would not restore any lost data (there was none) and would re-introduce a retired,
unsupported code path.
"""
from typing import Sequence, Union

from alembic import op

revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = '35050c0dbfdb'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_TABLES_CHILD_FIRST = (
    "batch_releases",
    "batch_reviews",
    "batch_steps",
    "batches",
    "recipe_steps",
    "recipes",
    "products",
)


def upgrade() -> None:
    op.execute(
        "ALTER TABLE equipment.aseptic_profile_versions "
        "DROP CONSTRAINT IF EXISTS aseptic_profile_versions_product_id_fkey"
    )
    for table in _TABLES_CHILD_FIRST:
        op.execute(f"DROP TABLE IF EXISTS ebmr.{table}")


def downgrade() -> None:
    """Forward-only repair -- the retired legacy schema is not recreated (MIG-FR-005 / MIG-FR-031)."""
