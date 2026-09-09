"""0087_repair_verification_recipe_families

Revision ID: c3e5a7b9d1f4
Revises: b2d4f6a8c0e1
Create Date: 2026-09-08 00:00:00.000000

Controlled repair (MIG-FR-005 / MIG-FR-026 / CLAUDE.md "no production DB fix outside a controlled
migration/repair mechanism"). During the 2026-09-08 Recipe Master work, three throwaway recipe families
were left in the live `ebmr_new_gxp` database by end-to-end `curl` verification runs:

    RCP-SMOKE-1788843389   (draft,   authored against MERIDIJECT-PFS)
    RCP-SMOKE2-1788843413  (released, authored against MERIDIJECT-PFS)
    RCP-PICKER-1788844367  (draft,   authored against MERIDIJECT-PFS)

They are verification-only data, not part of any demo script. Confirmed before writing this migration:
zero rows in `ebmr.gxp_batch` (or anywhere else) reference these `gxp_recipe_version` ids, so nothing in
genealogy / batch execution depends on them.

Scope of deletion — the recipe domain rows only, by exact `recipe_code`, children first:
`gxp_recipe_step_dependency` -> `gxp_recipe_parameter` -> `gxp_recipe_evidence_requirement`
-> `gxp_recipe_step` -> `gxp_recipe_section` -> `gxp_recipe_version` -> `gxp_recipe_family`.

Deliberately NOT touched (AG-08 append-only, MIG-FR-013): `audit.audit_events`, `vault.*`,
`mutation.outbox_events`. The audit trail therefore still shows these families being Created (and
RCP-SMOKE2 Released) and now removed by this controlled repair — the correct, non-destructive record.

Idempotent: the `WHERE recipe_code IN (...)` predicate is a no-op on any deployment that never ran those
verification calls (fresh installs, the test database, customer environments). Forward-only — a
`downgrade()` cannot resurrect disposed regulated rows (MIG-FR-005 / MIG-FR-031); it is a documented
no-op.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'c3e5a7b9d1f4'
down_revision: Union[str, Sequence[str], None] = 'b2d4f6a8c0e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_CODES = ("RCP-SMOKE-1788843389", "RCP-SMOKE2-1788843413", "RCP-PICKER-1788844367")


def upgrade() -> None:
    codes = ", ".join(f"'{c}'" for c in _CODES)
    fam = f"(SELECT id FROM ebmr.gxp_recipe_family WHERE recipe_code IN ({codes}))"
    ver = f"(SELECT id FROM ebmr.gxp_recipe_version WHERE recipe_family_id IN {fam})"
    stp = f"(SELECT id FROM ebmr.gxp_recipe_step WHERE recipe_version_id IN {ver})"
    op.execute(
        f"DELETE FROM ebmr.gxp_recipe_step_dependency "
        f"WHERE predecessor_step_id IN {stp} OR successor_step_id IN {stp}"
    )
    op.execute(f"DELETE FROM ebmr.gxp_recipe_parameter WHERE step_id IN {stp}")
    op.execute(f"DELETE FROM ebmr.gxp_recipe_evidence_requirement WHERE step_id IN {stp}")
    op.execute(f"DELETE FROM ebmr.gxp_recipe_step WHERE recipe_version_id IN {ver}")
    op.execute(f"DELETE FROM ebmr.gxp_recipe_section WHERE recipe_version_id IN {ver}")
    op.execute(f"DELETE FROM ebmr.gxp_recipe_version WHERE recipe_family_id IN {fam}")
    op.execute(f"DELETE FROM ebmr.gxp_recipe_family WHERE recipe_code IN ({codes})")


def downgrade() -> None:
    """Forward-only repair — disposed regulated rows are not resurrected (MIG-FR-005 / MIG-FR-031)."""
