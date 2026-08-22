"""0002_append_only_privilege_lockdown

Revision ID: 329495c9e651
Revises: d462ab05fac3
Create Date: 2026-08-21 10:13:57.042200

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '329495c9e651'
down_revision: Union[str, Sequence[str], None] = 'd462ab05fac3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APP_ROLE = "ebmr_new_gxp_app"

# Schemas the runtime app role may read/write freely (DML only, no DDL — MIG-FR-020 / PG-FR-005).
DML_SCHEMAS = ("iam", "mutation", "signature", "vault", "ebmr")

# Tables that are append-only for the runtime app role — AG-08 / AUD-FR-014: INSERT + SELECT only,
# no UPDATE/DELETE, enforced at the database privilege level, not just by application discipline.
APPEND_ONLY_TABLES = (
    "audit.audit_events",
    "signature.signatures",
    "vault.vault_versions",
)


def upgrade() -> None:
    """Upgrade schema."""
    for schema in DML_SCHEMAS:
        op.execute(f"GRANT USAGE ON SCHEMA {schema} TO {APP_ROLE}")
        op.execute(
            f"GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA {schema} TO {APP_ROLE}"
        )
    op.execute(f"GRANT USAGE ON SCHEMA audit TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT ON audit.audit_events TO {APP_ROLE}")

    for qualified_table in APPEND_ONLY_TABLES:
        op.execute(f"REVOKE UPDATE, DELETE ON {qualified_table} FROM {APP_ROLE}")

    # No DDL for the app role anywhere in this database.
    for schema in (*DML_SCHEMAS, "audit"):
        op.execute(f"REVOKE CREATE ON SCHEMA {schema} FROM {APP_ROLE}")


def downgrade() -> None:
    """Downgrade schema."""
    for qualified_table in APPEND_ONLY_TABLES:
        op.execute(f"GRANT UPDATE, DELETE ON {qualified_table} TO {APP_ROLE}")
    for schema in (*DML_SCHEMAS, "audit"):
        op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA {schema} FROM {APP_ROLE}")
        op.execute(f"REVOKE USAGE ON SCHEMA {schema} FROM {APP_ROLE}")
