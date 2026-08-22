"""0004_materials_privilege_lockdown

Revision ID: 221dc58877f5
Revises: 3d221863a71e
Create Date: 2026-08-21 12:22:38.895693

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '221dc58877f5'
down_revision: Union[str, Sequence[str], None] = '3d221863a71e'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    """Upgrade schema."""
    op.execute(f"GRANT USAGE ON SCHEMA materials TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON ALL TABLES IN SCHEMA materials TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA materials FROM {APP_ROLE}")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA materials FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA materials FROM {APP_ROLE}")
