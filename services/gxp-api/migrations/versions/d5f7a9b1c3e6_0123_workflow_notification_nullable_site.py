"""0123_workflow_notification_nullable_site

Revision ID: d5f7a9b1c3e6
Revises: c3e5a7b9d1f2
Create Date: 2026-09-24 00:00:00.000000

Extends the Workflow Handoff Notification projection (migration c3e5a7b9d1f2) to cover aggregates that
are themselves not site-scoped in the real authorization path (`oot_record` has no site_id column at all;
`supplier_qualification`'s own `evaluate_policy(..., site_id=None)` call site already means "any site").
Additive, safe: drops a NOT NULL constraint only, no data loss, no table rewrite.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'd5f7a9b1c3e6'
down_revision: Union[str, Sequence[str], None] = 'c3e5a7b9d1f2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('workflow_notification', 'site_id', nullable=True, schema='notifications')


def downgrade() -> None:
    op.alter_column('workflow_notification', 'site_id', nullable=False, schema='notifications')
