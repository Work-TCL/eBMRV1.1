"""0013_device_schema

Revision ID: 0cb6e2ece7c0
Revises: f264272f2f0b
Create Date: 2026-08-24 00:00:00.000000

Document 12 (SPEC-EBMR-003) — eDHR / Device Production History. Creates 1 new table (`device_unit`) in
the existing `ebmr` schema. No legacy device/DHR module or table exists in this codebase, so there is no
additive-alongside-a-stub story here (unlike product/recipe/batch) -- this is simply the module's schema.

Per docs/generated/04_DATA_MODEL_CATALOGUE.md, only 1 of Document 12's 5 owned entities is DDL-ready:
`device_unit`, typed here directly. The other 4 (`device_component_usage`, `device_test_result`,
`device_defect`, `device_evidence_inheritance`) are prose-only field-name lists — deferred as SG-049,
same resolution path as SG-045/SG-047.

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform),
`version` bigint (optimistic concurrency) kept explicit. `device_lot_id` is a self-referential FK to
`device_unit.id` (a lot-scope row, `serial_number IS NULL`, referenced by its serial-scope children).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '0cb6e2ece7c0'
down_revision: Union[str, Sequence[str], None] = 'f264272f2f0b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'device_unit',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('product_version_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=True),
        sa.Column('device_lot_id', sa.UUID(), nullable=True),
        sa.Column('serial_number', sa.String(length=200), nullable=True),
        sa.Column('udi_di', sa.String(length=120), nullable=True),
        sa.Column('udi_pi', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='created'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('release_status', sa.String(length=40), nullable=False, server_default='not_released'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['product_version_id'], ['ebmr.gxp_product_version.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.gxp_batch.id']),
        sa.ForeignKeyConstraint(['device_lot_id'], ['ebmr.device_unit.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id', 'serial_number'),
        schema='ebmr',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.device_unit TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.device_unit FROM {APP_ROLE}")
    op.drop_table('device_unit', schema='ebmr')
