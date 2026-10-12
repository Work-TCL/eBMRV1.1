"""0143_audit_finding_batch_source

Revision ID: 6aab486e47a9
Revises: 6ef7e014cb45
Create Date: 2026-10-09 00:00:00.000000

Project-owner-directed: Internal Audit findings had no structured way to attribute a finding to a
specific batch, so release/service.py had no signal to check -- adds a nullable `source_type`/`source_id`
pair to `qms.audit_finding`, the same generic-reference convention `deviation_record`/`capa_record`/
`nonconformance_record` already use for `source_type="batch"` attribution. Additive, both columns
nullable so no existing row needs a value (a finding not attributed to a batch simply has neither set,
same as before).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = '6aab486e47a9'
down_revision: Union[str, Sequence[str], None] = '6ef7e014cb45'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('audit_finding', sa.Column('source_type', sa.String(length=40), nullable=True), schema='qms')
    op.add_column('audit_finding', sa.Column('source_id', postgresql.UUID(as_uuid=True), nullable=True), schema='qms')


def downgrade() -> None:
    op.drop_column('audit_finding', 'source_id', schema='qms')
    op.drop_column('audit_finding', 'source_type', schema='qms')
