"""0132_user_invites

Revision ID: a2c4e6f8b0d1
Revises: f3a5c7e9b1d4
Create Date: 2026-10-05 00:00:00.000000

Client gap-analysis Phase 1 (bulk user onboarding, 2026-10-05): a bulk-imported user is created with no
password (`iam.users.status="pending_activation"`) and activates their own account via a single-use,
time-limited invite token. `token_hash` stores only the SHA-256 digest of the emailed token -- the raw
token itself is never persisted anywhere. Purely additive: one new table, no change to `iam.users`'
existing columns (its `status` column is already a free string with no CHECK constraint, so the new
value needs no schema change there).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a2c4e6f8b0d1'
down_revision: Union[str, Sequence[str], None] = 'f3a5c7e9b1d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'user_invites',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('token_hash', sa.String(length=64), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('consumed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()')),
        sa.UniqueConstraint('token_hash', name='uq_user_invites_token_hash'),
        schema='iam',
    )
    op.create_foreign_key(
        'fk_user_invites_user_id',
        'user_invites', 'users',
        ['user_id'], ['id'],
        source_schema='iam', referent_schema='iam',
    )
    op.create_foreign_key(
        'fk_user_invites_created_by_user_id',
        'user_invites', 'users',
        ['created_by_user_id'], ['id'],
        source_schema='iam', referent_schema='iam',
    )
    op.create_index(
        'ix_user_invites_user_id', 'user_invites', ['user_id'], schema='iam',
    )
    # PG-FR-005: runtime role gets minimum SELECT/INSERT/UPDATE needed, no DDL. TRUNCATE is granted for
    # parity with this codebase's other additive tables (e.g. 0013_device_schema's device_unit) -- used
    # only by test fixtures resetting state between runs, never by application code.
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON iam.user_invites TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON iam.user_invites FROM {APP_ROLE}")
    op.drop_index('ix_user_invites_user_id', table_name='user_invites', schema='iam')
    op.drop_constraint('fk_user_invites_created_by_user_id', 'user_invites', schema='iam', type_='foreignkey')
    op.drop_constraint('fk_user_invites_user_id', 'user_invites', schema='iam', type_='foreignkey')
    op.drop_table('user_invites', schema='iam')
