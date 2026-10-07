"""0131_deviation_preapproval

Revision ID: f3a5c7e9b1d4
Revises: e1f3a5c7d9b2
Create Date: 2026-10-02 00:00:00.000000

Client_Decisions_Neededanswers Topic 11 (SG-061): a planned deviation now requires formal pre-approval
by an authorized Quality/QA person before it can be used (any forward-pipeline transition). Adds
`preapproved_by_user_id`/`preapproved_at`/`preapproval_signature_id` to `qms.deviation_record`. Purely
additive -- all three columns are nullable -- no backfill needed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f3a5c7e9b1d4'
down_revision: Union[str, Sequence[str], None] = 'e1f3a5c7d9b2'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'deviation_record',
        sa.Column('preapproved_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='qms',
    )
    op.create_foreign_key(
        'fk_deviation_record_preapproved_by_user_id',
        'deviation_record', 'users',
        ['preapproved_by_user_id'], ['id'],
        source_schema='qms', referent_schema='iam',
    )
    op.add_column(
        'deviation_record',
        sa.Column('preapproved_at', sa.DateTime(timezone=True), nullable=True),
        schema='qms',
    )
    op.add_column(
        'deviation_record',
        sa.Column('preapproval_signature_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='qms',
    )


def downgrade() -> None:
    op.drop_column('deviation_record', 'preapproval_signature_id', schema='qms')
    op.drop_column('deviation_record', 'preapproved_at', schema='qms')
    op.drop_constraint('fk_deviation_record_preapproved_by_user_id', 'deviation_record', schema='qms', type_='foreignkey')
    op.drop_column('deviation_record', 'preapproved_by_user_id', schema='qms')
