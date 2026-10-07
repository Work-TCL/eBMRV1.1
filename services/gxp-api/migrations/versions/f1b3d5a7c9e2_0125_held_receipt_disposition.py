"""0125_held_receipt_disposition

Revision ID: f1b3d5a7c9e2
Revises: e7a9c1b3d5f8
Create Date: 2026-10-02 00:00:00.000000

Client_Decisions_Neededanswers Topic 4: a `material_receipts` row held at state="discrepancy_hold" had
no forward path at all (`disposition_held_receipt` adds one). Adds the disposition fields to
`material_receipts` (decision/severity/reason/deviation link/decided-by/decided-at/signature) and the
exception flag to `material_lots` (a lot created from an accepted-despite-discrepancy receipt per Q10
stays visibly flagged rather than entering the normal quarantine flow unmarked). Purely additive, all
columns nullable (or boolean with a safe default) -- no backfill needed, existing rows are all
pre-disposition/non-exception.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f1b3d5a7c9e2'
down_revision: Union[str, Sequence[str], None] = 'e7a9c1b3d5f8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'material_receipts',
        sa.Column('disposition_decision', sa.String(length=30), nullable=True),
        schema='materials',
    )
    op.add_column(
        'material_receipts',
        sa.Column('disposition_severity', sa.String(length=20), nullable=True),
        schema='materials',
    )
    op.add_column(
        'material_receipts',
        sa.Column('disposition_reason', sa.String(length=2000), nullable=True),
        schema='materials',
    )
    op.add_column(
        'material_receipts',
        sa.Column('disposition_deviation_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='materials',
    )
    op.create_foreign_key(
        'fk_material_receipts_disposition_deviation_id',
        'material_receipts', 'deviation_record',
        ['disposition_deviation_id'], ['id'],
        source_schema='materials', referent_schema='qms',
    )
    op.add_column(
        'material_receipts',
        sa.Column('disposition_decided_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='materials',
    )
    op.create_foreign_key(
        'fk_material_receipts_disposition_decided_by_user_id',
        'material_receipts', 'users',
        ['disposition_decided_by_user_id'], ['id'],
        source_schema='materials', referent_schema='iam',
    )
    op.add_column(
        'material_receipts',
        sa.Column('disposition_decided_at', sa.DateTime(timezone=True), nullable=True),
        schema='materials',
    )
    op.add_column(
        'material_receipts',
        sa.Column('disposition_signature_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='materials',
    )
    op.add_column(
        'material_lots',
        sa.Column('is_exception_release', sa.Boolean(), nullable=False, server_default=sa.false()),
        schema='materials',
    )
    op.add_column(
        'material_lots',
        sa.Column('exception_reason', sa.String(length=2000), nullable=True),
        schema='materials',
    )


def downgrade() -> None:
    op.drop_column('material_lots', 'exception_reason', schema='materials')
    op.drop_column('material_lots', 'is_exception_release', schema='materials')
    op.drop_column('material_receipts', 'disposition_signature_id', schema='materials')
    op.drop_column('material_receipts', 'disposition_decided_at', schema='materials')
    op.drop_constraint(
        'fk_material_receipts_disposition_decided_by_user_id', 'material_receipts',
        schema='materials', type_='foreignkey',
    )
    op.drop_column('material_receipts', 'disposition_decided_by_user_id', schema='materials')
    op.drop_constraint(
        'fk_material_receipts_disposition_deviation_id', 'material_receipts',
        schema='materials', type_='foreignkey',
    )
    op.drop_column('material_receipts', 'disposition_deviation_id', schema='materials')
    op.drop_column('material_receipts', 'disposition_reason', schema='materials')
    op.drop_column('material_receipts', 'disposition_severity', schema='materials')
    op.drop_column('material_receipts', 'disposition_decision', schema='materials')
