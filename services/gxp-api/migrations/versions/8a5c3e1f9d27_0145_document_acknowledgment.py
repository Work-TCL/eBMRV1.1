"""0145_document_acknowledgment

Revision ID: 8a5c3e1f9d27
Revises: 1cc842ed7e64
Create Date: 2026-10-09 00:00:00.000000

DOC-FR-014/SG-079 resolved (project-owner-directed: "Simple unsigned log"). New insert-only
`qms.document_acknowledgment` table recording a per-user read-and-understand acknowledgment of a
controlled document version -- deliberately not a Part 11 signature (AG-07). Unique on
(document_version_id, user_id) so re-acknowledging is idempotent, not a conflict.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '8a5c3e1f9d27'
down_revision: Union[str, Sequence[str], None] = '1cc842ed7e64'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'document_acknowledgment',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('document_version_id', postgresql.UUID(as_uuid=True),
                  sa.ForeignKey('qms.controlled_document_version.id'), nullable=False),
        sa.Column('user_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('iam.users.id'), nullable=False),
        sa.Column('statement', sa.Text(), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('document_version_id', 'user_id', name='uq_document_acknowledgment_version_user'),
        schema='qms',
    )
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON qms.document_acknowledgment TO {APP_ROLE}")


def downgrade() -> None:
    op.drop_table('document_acknowledgment', schema='qms')
