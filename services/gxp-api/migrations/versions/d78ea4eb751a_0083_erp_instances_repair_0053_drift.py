"""0083_erp_instances_repair_0053_drift

Revision ID: d78ea4eb751a
Revises: c5d9e2f7a1b4
Create Date: 2026-09-02 00:00:00.000000

**Repair migration, not new development** (MIG-FR-026: "manual DDL/DML in production prohibited
except controlled emergency repair captured into subsequent migration/change record" -- this is that
migration/change record). Found 2026-09-02 while reseeding the `ebmr_new_gxp` demo database:
`alembic current` reported this environment at head (`c5d9e2f7a1b4`), yet
`erp.erp_instances.validated` -- added by migration 0053
(`b7d3e9a4c1f6_0053_erp_wp07_completion_extensions.py`) -- did not exist, and `INSERT` failed with
`UndefinedColumnError`.

A full `alembic.autogenerate.compare_metadata()` diff against `ebmr_new_gxp` (with
`include_schemas=True` -- the default omits every non-`public` schema and falsely reports ~220
unrelated tables "missing", a dead end chased and ruled out first) found the drift is narrow and
contained to exactly what 0053 added to three already-existing tables:

  - `erp.erp_instances` is missing `validated` / `validated_by_user_id` / `validated_at` and their FK.
  - `erp.erp_migration_packages.site_id` and `erp.integration_bulk_jobs.site_id` exist (0053 created
    both tables successfully) but are missing their `iam.sites(id)` FK.

Every other change 0053 made (the three new tables in full, the `integration_inbound_events` /
`integration_circuit_breakers` / `integration_commands` column additions) is present and correct --
this is not a "0053 never ran" situation, it is three specific statements out of one migration that
did not take effect (root cause not recoverable: no application/DB log from whenever this happened is
retained). `ebmr_new_gxp_test` (the test database every `tests/` run uses) does **not** have this
drift, confirmed by the full test suite passing against `erp.erp_instances.validated`-dependent code
paths throughout this project's history -- this migration is idempotent (`IF NOT EXISTS`, guarded
constraint creation) specifically so it is a safe no-op there and anywhere else already correct,
rather than assuming every environment shares `ebmr_new_gxp`'s specific drift.

No data loss possible: additive only (3 new nullable-safe columns + a default, 3 FK constraints on
existing nullable columns), nothing dropped or altered. `downgrade()` is provided but is intentionally
symmetric with 0053's own downgrade (drop what 0053 defined), not a re-introduction of the drift.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd78ea4eb751a'
down_revision: Union[str, Sequence[str], None] = 'c5d9e2f7a1b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Columns: native IF NOT EXISTS, safe no-op where migration 0053 already fully applied.
    op.execute(
        "ALTER TABLE erp.erp_instances ADD COLUMN IF NOT EXISTS validated boolean NOT NULL DEFAULT false"
    )
    op.execute(
        "ALTER TABLE erp.erp_instances ADD COLUMN IF NOT EXISTS validated_by_user_id uuid"
    )
    op.execute(
        "ALTER TABLE erp.erp_instances ADD COLUMN IF NOT EXISTS validated_at timestamptz"
    )

    # Constraints: Postgres has no ADD CONSTRAINT IF NOT EXISTS -- guard with a DO block per 0053's
    # own three FK definitions, matching that migration's exact names so a future downgrade/upgrade
    # cycle stays symmetric with it.
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE erp.erp_instances
                ADD CONSTRAINT fk_erp_instances_validated_by
                FOREIGN KEY (validated_by_user_id) REFERENCES iam.users(id);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE erp.erp_migration_packages
                ADD CONSTRAINT erp_migration_packages_site_id_fkey
                FOREIGN KEY (site_id) REFERENCES iam.sites(id);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)
    op.execute("""
        DO $$ BEGIN
            ALTER TABLE erp.integration_bulk_jobs
                ADD CONSTRAINT integration_bulk_jobs_site_id_fkey
                FOREIGN KEY (site_id) REFERENCES iam.sites(id);
        EXCEPTION WHEN duplicate_object THEN NULL;
        END $$;
    """)


def downgrade() -> None:
    op.execute("ALTER TABLE erp.integration_bulk_jobs DROP CONSTRAINT IF EXISTS integration_bulk_jobs_site_id_fkey")
    op.execute("ALTER TABLE erp.erp_migration_packages DROP CONSTRAINT IF EXISTS erp_migration_packages_site_id_fkey")
    op.execute("ALTER TABLE erp.erp_instances DROP CONSTRAINT IF EXISTS fk_erp_instances_validated_by")
    op.execute("ALTER TABLE erp.erp_instances DROP COLUMN IF EXISTS validated_at")
    op.execute("ALTER TABLE erp.erp_instances DROP COLUMN IF EXISTS validated_by_user_id")
    op.execute("ALTER TABLE erp.erp_instances DROP COLUMN IF EXISTS validated")
