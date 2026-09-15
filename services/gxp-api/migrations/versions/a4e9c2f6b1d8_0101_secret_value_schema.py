"""0101_secret_value_schema

Revision ID: a4e9c2f6b1d8
Revises: dd78daa66970
Create Date: 2026-09-12 00:00:00.000000

SG-126 gap resolution (Document 65, WP-07 pass). Adds `security.secret_value` -- the ON_PREM provider's
encrypted value store. Holds only an AES-256-GCM envelope (nonce/ciphertext/tag), never a plaintext
value (Document 65 # 14 is satisfied the same way `encrypt_sensitive_field()` satisfies it for every
other sensitive field). K8S_SECRET/AWS_SM/VAULT secrets never get a row here.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'a4e9c2f6b1d8'
down_revision: Union[str, Sequence[str], None] = 'dd78daa66970'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'secret_value',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('secret_id', sa.UUID(), nullable=False),
        sa.Column('envelope', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('set_by_user_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['secret_id'], ['security.secret_metadata.id']),
        sa.ForeignKeyConstraint(['set_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('secret_id'),
        schema='security',
    )
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.secret_value TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON security.secret_value FROM {APP_ROLE}")
    op.drop_table('secret_value', schema='security')
