"""0015_qa_review_schema

Revision ID: d05689ef6618
Revises: 5e23e1067790
Create Date: 2026-08-24 00:00:00.000000

Document 14 (SPEC-EBMR-005) — Review-by-Exception & QA Review. Creates 1 new table (`qa_review_package`)
in the existing `ebmr` schema. No legacy QA-review module exists in this codebase.

Per docs/generated/04_DATA_MODEL_CATALOGUE.md, only 1 of Document 14's 3 owned entities is DDL-ready:
`qa_review_package`, typed here directly. `qa_review_item` and `qa_review_comment` are prose-only
field-name lists -- deferred as SG-053, same resolution path as SG-045/047/049.

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform);
`site_id` added (the catalogue's own boilerplate footer calls for it on every table but the field list
omits it, same deviation already used for gxp_batch/device_unit); `UNIQUE(batch_id)` added -- one review
package per batch, matching "at Production Complete create versioned QA review package" (singular).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd05689ef6618'
down_revision: Union[str, Sequence[str], None] = '5e23e1067790'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'qa_review_package',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('batch_version', sa.BigInteger(), nullable=False),
        sa.Column('record_hash', sa.String(length=64), nullable=False),
        sa.Column('checklist_version_id', sa.UUID(), nullable=True),
        sa.Column('exception_index_version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('completeness_status', sa.String(length=40), nullable=False),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='READY_FOR_REVIEW'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.gxp_batch.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('batch_id'),
        schema='ebmr',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.qa_review_package TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON ebmr.qa_review_package FROM {APP_ROLE}")
    op.drop_table('qa_review_package', schema='ebmr')
