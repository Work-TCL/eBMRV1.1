"""0006_master_data_delete_privilege

Revision ID: 747afac225e8
Revises: b270544f6fb0
Create Date: 2026-08-22 00:00:00.000000

Migration 0002 (append_only_privilege_lockdown) granted the runtime app role SELECT/INSERT/UPDATE only —
DELETE was never granted on any table, for any schema. That was correct as a starting default, but the
new master-data admin screen (sites, roles, products, materials, recipes) needs guarded delete, and
`session.delete(...)` requires an actual SQL DELETE grant to run.

This grants DELETE narrowly, on exactly the master/reference-data tables the admin screen manages, and
nowhere else. Everything this migration does NOT touch stays exactly as restrictive as before — no DELETE
grant on audit_events/signatures/vault_versions (still append-only, migration 0002), and none on any
regulated execution/evidence table either (batches, batch_steps, batch_reviews, batch_releases,
material_lots, material_lot_dispositions, material_issues, users, organizations) — those still cannot be
deleted by the runtime app role, matching PG-FR-005 (minimum grants) and DATA-FR-023 (regulated/history
records are not hard-deleted through generic CRUD).
"""
from typing import Sequence, Union

from alembic import op


# revision identifiers, used by Alembic.
revision: str = '747afac225e8'
down_revision: Union[str, Sequence[str], None] = 'b270544f6fb0'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"

DELETE_GRANT_TABLES = (
    "iam.sites",
    "iam.roles",
    "ebmr.products",
    "materials.materials",
    "ebmr.recipes",
    "ebmr.recipe_steps",
)


def upgrade() -> None:
    """Upgrade schema."""
    for qualified_table in DELETE_GRANT_TABLES:
        op.execute(f"GRANT DELETE ON {qualified_table} TO {APP_ROLE}")


def downgrade() -> None:
    """Downgrade schema."""
    for qualified_table in DELETE_GRANT_TABLES:
        op.execute(f"REVOKE DELETE ON {qualified_table} FROM {APP_ROLE}")
