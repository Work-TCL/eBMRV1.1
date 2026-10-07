"""0139_supplier_delete_privilege

Revision ID: a7c9e1b3d5f0
Revises: 3cccd6646cd7
Create Date: 2026-10-06 00:00:00.000000

Project-owner-directed (2026-10-06): a draft Supplier (and its still-draft SupplierSite rows) can now be
deleted through the new DeleteSupplier command, same "guarded delete on narrow master-data tables" shape
migration 0006 already established for sites/roles/products/materials/recipes. `ebmr.supplier` and
`ebmr.supplier_site` were never in that original list -- this grants DELETE on exactly those two tables,
nothing else (no DELETE grant on supplier_qualification/supplier_qualification_evidence/
supplier_qualification_scope_item -- those stay append-only, matching AG-08/DATA-FR-023, since a
qualification record existing is itself the signal this command refuses to delete through, per
DeleteSupplierCommand's own status=="draft" + referenced-qualification checks).
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'a7c9e1b3d5f0'
down_revision: Union[str, Sequence[str], None] = '3cccd6646cd7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"

DELETE_GRANT_TABLES = (
    "ebmr.supplier",
    "ebmr.supplier_site",
)


def upgrade() -> None:
    for qualified_table in DELETE_GRANT_TABLES:
        op.execute(f"GRANT DELETE ON {qualified_table} TO {APP_ROLE}")


def downgrade() -> None:
    for qualified_table in DELETE_GRANT_TABLES:
        op.execute(f"REVOKE DELETE ON {qualified_table} FROM {APP_ROLE}")
