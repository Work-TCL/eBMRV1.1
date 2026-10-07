"""0122_workflow_notification_schema

Revision ID: c3e5a7b9d1f2
Revises: b7c9d1e3f5a7
Create Date: 2026-09-23 00:00:00.000000

Workflow Handoff Notifications (project-owner-directed; no Document/SPEC-xxx baseline id -- see
app/modules/notifications/models.py's module docstring). New `notifications` schema, same
"Postgres-tracked, rebuildable, non-authoritative read model" tier and grant shape as `readmodels.*`
(migration d1a6f3c8b5e2_0073): two brand-new tables, no existing table altered, no backfill, reversible.

`workflow_notification` -- one row per (aggregate_type, aggregate_id, category); `required_permission_code`
+ `site_id` are the audience key resolved live against `iam.role_permissions`/`iam.user_site_roles` at read
time, never a stored recipient list. `workflow_notification_read` -- per-viewer read state, FK'd to the
notification row and to `iam.users`.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'c3e5a7b9d1f2'
down_revision: Union[str, Sequence[str], None] = 'b7c9d1e3f5a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"
_TABLES = ("workflow_notification", "workflow_notification_read")


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS notifications")

    op.create_table(
        'workflow_notification',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('aggregate_type', sa.String(length=80), nullable=False),
        sa.Column('aggregate_id', sa.UUID(), nullable=False),
        sa.Column('category', sa.String(length=80), nullable=False),
        sa.Column('required_permission_code', sa.String(length=100), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('excluded_actor_id', sa.UUID(), nullable=True),
        sa.Column('entity_label', sa.String(length=300), nullable=False),
        sa.Column('link_path', sa.String(length=300), nullable=False),
        sa.Column('source_event_id', sa.UUID(), nullable=True),
        sa.Column('opened_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('aggregate_type', 'aggregate_id', 'category', name='uq_workflow_notification_identity'),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['excluded_actor_id'], ['iam.users.id']),
        schema='notifications',
    )
    op.create_index(
        'ix_workflow_notification_audience', 'workflow_notification',
        ['required_permission_code', 'site_id', 'resolved_at'], schema='notifications',
    )

    op.create_table(
        'workflow_notification_read',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('notification_id', sa.UUID(), nullable=False),
        sa.Column('user_id', sa.UUID(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('notification_id', 'user_id', name='uq_workflow_notification_read_identity'),
        sa.ForeignKeyConstraint(['notification_id'], ['notifications.workflow_notification.id']),
        sa.ForeignKeyConstraint(['user_id'], ['iam.users.id']),
        schema='notifications',
    )

    op.execute(f"GRANT USAGE ON SCHEMA notifications TO {APP_ROLE}")
    for t in _TABLES:
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON notifications.{t} TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA notifications FROM {APP_ROLE}")


def downgrade() -> None:
    for t in _TABLES:
        op.execute(f"REVOKE ALL ON notifications.{t} FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA notifications FROM {APP_ROLE}")
    op.drop_table('workflow_notification_read', schema='notifications')
    op.drop_index('ix_workflow_notification_audience', table_name='workflow_notification', schema='notifications')
    op.drop_table('workflow_notification', schema='notifications')
    op.execute("DROP SCHEMA IF EXISTS notifications")
