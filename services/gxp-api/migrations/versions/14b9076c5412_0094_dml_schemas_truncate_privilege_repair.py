"""0094_dml_schemas_truncate_privilege_repair

Revision ID: 14b9076c5412
Revises: a6d525b2d585
Create Date: 2026-09-10 00:00:00.000000

**Repair migration, not new development** (MIG-FR-026: "manual DDL/DML in production prohibited except
controlled emergency repair captured into subsequent migration/change record" -- this is that record).
Found 2026-09-10 rebuilding `ebmr_new_gxp_test` end-to-end (`alembic downgrade base` then `alembic
upgrade head`, PHASE_2_BACKBONE.md Sec 4 item 4): `tests/conftest.py`'s autouse `clean_database` fixture
-- every single test in the suite depends on it -- TRUNCATEs the full regulated table set as the
`{APP_ROLE}` runtime role, and Postgres requires the TRUNCATE privilege specifically (not implied by
SELECT/INSERT/UPDATE/DELETE) on every named table.

Root cause: the two earliest privilege-setup migrations -- 0002 (`append_only_privilege_lockdown`,
`iam`/`mutation`/`signature`/`vault`/`ebmr`/`audit`) and 0004 (`materials_privilege_lockdown`,
`materials`) -- each grant `{APP_ROLE}` `SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA <schema>` with no
TRUNCATE, and no later migration re-grants TRUNCATE for the tables that already existed at that point
(every materials-schema/iam/mutation/ebmr table added from migration ~0009 onward *does* follow the
correct, later-established `GRANT SELECT, INSERT, UPDATE, TRUNCATE ON <table> TO {APP_ROLE}` per-table
convention -- 0002/0004 simply predate that convention). Confirmed empirically against the freshly
rebuilt database with `has_table_privilege('ebmr_new_gxp_app', <table>, 'TRUNCATE')` for every table in
`tests/conftest.py`'s `APP_TABLES` list: 24 tables lack it. 22 of the 24 are ordinary mutable
master/execution data, safe to grant TRUNCATE on (matches the established per-table convention). The
other 2 -- `audit.audit_events` and `signature.signatures` -- are exactly the two tables migration 0002
already deliberately revoked UPDATE/DELETE on to make them append-only (AG-08: "Audit / Vault / evidence
history is immutable and superseding"); TRUNCATE is at least as destructive as DELETE and must **not** be
granted to the runtime app role for either, in test or production -- granting it here would quietly
weaken the exact guarantee migration 0002 established. Those two are handled instead by a companion fix
to `tests/conftest.py` (same commit): the cleanup fixture now truncates them via the migration role,
which already has unrestricted DDL/DML access for test-harness purposes (see
`GXP_MIGRATION_DATABASE_URL`/`settings.migration_database_url`, already used the same way by
`test_audit_review.py`/`test_vault.py`/`test_batch_flow.py`), leaving the app role's grants identical in
test and production.

The live `ebmr_new_gxp_test` this project has been testing against never hit this 24-table gap, meaning
some earlier session applied the missing (22-table) grants by hand directly against that one database,
never captured in a migration, and silently lost by this rebuild -- the exact "hidden state, not
reproducible from migrations alone" defect class this rebuild was run to find.

No data/schema change: privilege-only, additive (on the 22 tables), immediately reversible.
"""
from typing import Sequence, Union

from alembic import op


revision: str = '14b9076c5412'
down_revision: Union[str, Sequence[str], None] = 'a6d525b2d585'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"

# Ordinary mutable tables from the two earliest (pre-per-table-TRUNCATE-convention) privilege-lockdown
# migrations (0002, 0004) that never got a TRUNCATE grant. Deliberately excludes audit.audit_events and
# signature.signatures -- see this migration's docstring.
TRUNCATE_GRANT_TABLES = (
    "materials.materials",
    "materials.material_lots",
    "materials.material_lot_dispositions",
    "materials.material_issues",
    "iam.organizations",
    "iam.sites",
    "iam.roles",
    "iam.users",
    "iam.user_site_roles",
    "iam.qualifications",
    "mutation.idempotency_keys",
    "mutation.outbox_events",
    "mutation.command_receipts",
    "ebmr.products",
    "ebmr.recipes",
    "ebmr.recipe_steps",
    "ebmr.batches",
    "ebmr.batch_steps",
    "ebmr.batch_reviews",
    "ebmr.batch_releases",
    "signature.signature_challenges",
    "signature.signature_policies",
)


def upgrade() -> None:
    """Upgrade schema."""
    for qualified_table in TRUNCATE_GRANT_TABLES:
        op.execute(f"GRANT TRUNCATE ON {qualified_table} TO {APP_ROLE}")


def downgrade() -> None:
    """Downgrade schema."""
    for qualified_table in TRUNCATE_GRANT_TABLES:
        op.execute(f"REVOKE TRUNCATE ON {qualified_table} FROM {APP_ROLE}")
