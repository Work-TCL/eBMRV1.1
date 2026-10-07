"""0138_organization_onboarding_dismissed

Revision ID: 3cccd6646cd7
Revises: f5c7e9b1d3a8
Create Date: 2026-10-06 00:00:00.000000

Admin onboarding wizard (client gap-analysis follow-up, 2026-10-06): Company/Sites/Users/Roles step
completion is derived from existing `audit.audit_events` rows (organization "Changed", site/user
"Created", user_site_role "Created") -- no new column needed for those four. The one thing that genuinely
needs persisting is an explicit skip/dismiss decision, which is not derivable from any existing table.
`iam.organizations` is a true global singleton (exactly one row, ADR-0006), so this is a plain nullable
column on it rather than a new table.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '3cccd6646cd7'
down_revision: Union[str, Sequence[str], None] = 'f5c7e9b1d3a8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'organizations',
        sa.Column('onboarding_dismissed_at', sa.DateTime(), nullable=True),
        schema='iam',
    )


def downgrade() -> None:
    op.drop_column('organizations', 'onboarding_dismissed_at', schema='iam')
