"""0088_repair_verification_product_prd_smoke

Revision ID: d4f6b8c0e2a5
Revises: c3e5a7b9d1f4
Create Date: 2026-09-08 00:00:01.000000

Controlled repair (MIG-FR-005 / MIG-FR-026), companion to 0087. Verifying the 2026-09-08 Product Master
author != releaser split (Decision 2) end-to-end against the live `ebmr_new_gxp` database left one
throwaway product behind:

    PRD-SMOKE-1788848422  (released, pharma draft, no constituents)

Confirmed before writing this migration: no `ebmr.gxp_product_constituent`,
`ebmr.gxp_constituent_compatibility_version` or `ebmr.gxp_recipe_version` row references this
`gxp_product_version` id, and `product_family_id` is NULL (create_draft never auto-creates a family).

Deletes `gxp_product_constituent` -> `gxp_constituent_compatibility_version` -> `gxp_product_version`
for the exact `product_business_id`. `audit.audit_events` / `vault.*` are NOT touched (AG-08 append-only,
MIG-FR-013) -- the Created/Released audit trail plus this repair remain the correct record.

Idempotent (exact `product_business_id`, no-op elsewhere -- fresh installs, the test database, customer
environments). Forward-only: `downgrade()` is a documented no-op (MIG-FR-005 / MIG-FR-031).
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'd4f6b8c0e2a5'
down_revision: Union[str, Sequence[str], None] = 'c3e5a7b9d1f4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BUSINESS_ID = "PRD-SMOKE-1788848422"


def upgrade() -> None:
    ver = (
        f"(SELECT id FROM ebmr.gxp_product_version WHERE product_business_id = '{_BUSINESS_ID}')"
    )
    op.execute(f"DELETE FROM ebmr.gxp_product_constituent WHERE product_version_id IN {ver} OR constituent_version_id IN {ver}")
    op.execute(
        f"DELETE FROM ebmr.gxp_constituent_compatibility_version "
        f"WHERE drug_constituent_version_id IN {ver} OR device_constituent_version_id IN {ver}"
    )
    op.execute(f"DELETE FROM ebmr.gxp_product_version WHERE product_business_id = '{_BUSINESS_ID}'")


def downgrade() -> None:
    """Forward-only repair -- disposed regulated rows are not resurrected (MIG-FR-005 / MIG-FR-031)."""
