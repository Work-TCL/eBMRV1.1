"""0005_signature_policy_failclosed

Revision ID: b270544f6fb0
Revises: 221dc58877f5
Create Date: 2026-08-22 00:00:00.000000

REMEDIATION_R1 FIX 1: signature policy must fail closed (Doc 106 SIGP-FR-004). A row's absence used
to mean "no signature needed" (fail open); after this migration, absence is only distinguishable from
an explicit "no signature" decision via `signature_required`, and the resolver treats an absent row as
a hard stop rather than a permission.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b270544f6fb0'
down_revision: Union[str, Sequence[str], None] = '221dc58877f5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        'signature_policies',
        sa.Column('signature_required', sa.Boolean(), nullable=False, server_default=sa.true()),
        schema='signature',
    )
    op.add_column(
        'signature_policies',
        sa.Column('signature_count', sa.SmallInteger(), nullable=False, server_default='1'),
        schema='signature',
    )
    op.add_column(
        'signature_policies',
        sa.Column('policy_source', sa.String(length=30), nullable=False, server_default='PLATFORM_FLOOR'),
        schema='signature',
    )
    op.add_column(
        'signature_policies',
        sa.Column('reason_required', sa.Boolean(), nullable=False, server_default=sa.false()),
        schema='signature',
    )
    op.create_check_constraint(
        'ck_signature_policies_count',
        'signature_policies',
        'signature_count BETWEEN 1 AND 4',
        schema='signature',
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint('ck_signature_policies_count', 'signature_policies', schema='signature', type_='check')
    op.drop_column('signature_policies', 'reason_required', schema='signature')
    op.drop_column('signature_policies', 'policy_source', schema='signature')
    op.drop_column('signature_policies', 'signature_count', schema='signature')
    op.drop_column('signature_policies', 'signature_required', schema='signature')
