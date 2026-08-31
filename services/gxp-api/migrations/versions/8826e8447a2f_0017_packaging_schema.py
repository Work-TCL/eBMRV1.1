"""0017_packaging_schema

Revision ID: 8826e8447a2f
Revises: 3814d4627b5d
Create Date: 2026-08-24 00:00:00.000000

Document 16 (SPEC-EBMR-007) — Packaging, Labeling & Reconciliation. Creates 4 new tables
(`packaging_run`, `label_issue`, `label_reconciliation`, `package_node`) in the existing `ebmr` schema.
No legacy packaging module exists in this codebase.

`label_issue` is DDL-ready in docs/generated/04_DATA_MODEL_CATALOGUE.md. `packaging_run`,
`label_reconciliation` and `package_node` are prose-only field-name lists there, but -- like Document 15's
release_evaluation/release_decision (SG-055) -- all three are genuinely unambiguous; typed here directly
as an ordinary engineering decision (SG-045's precedent).

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform).
`packaging_run.product_version_id` reuses the product-version FK generically as the "packaging
configuration version" (no dedicated packaging-configuration entity exists anywhere in this codebase).
`label_issue.label_version_id` and `.print_job_id` have no FK constraint -- neither a label-master nor a
print_job entity exists anywhere in the data model catalogue, despite both being referenced by Document 16
itself; they are unenforced logical-reference columns (SG-056).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '8826e8447a2f'
down_revision: Union[str, Sequence[str], None] = '3814d4627b5d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'packaging_run',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('product_version_id', sa.UUID(), nullable=False),
        sa.Column('line_ref', sa.String(length=120), nullable=True),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='not_ready'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('line_clearance_completed', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('reconciliation_state', sa.String(length=40), nullable=False, server_default='not_started'),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.gxp_batch.id']),
        sa.ForeignKeyConstraint(['product_version_id'], ['ebmr.gxp_product_version.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )

    op.create_table(
        'label_issue',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('packaging_run_id', sa.UUID(), nullable=False),
        sa.Column('label_version_id', sa.UUID(), nullable=True),
        sa.Column('quantity_issued', sa.BigInteger(), nullable=False),
        sa.Column('serial_range', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('print_job_id', sa.UUID(), nullable=True),
        sa.Column('issued_by', sa.UUID(), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='issued'),
        sa.ForeignKeyConstraint(['packaging_run_id'], ['ebmr.packaging_run.id']),
        sa.ForeignKeyConstraint(['issued_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )
    op.create_index('ix_label_issue_run', 'label_issue', ['packaging_run_id'], schema='ebmr')

    op.create_table(
        'label_reconciliation',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('packaging_run_id', sa.UUID(), nullable=False),
        sa.Column('issued', sa.BigInteger(), nullable=False),
        sa.Column('applied', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('returned', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('destroyed', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('rejected', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('samples', sa.BigInteger(), nullable=False, server_default='0'),
        sa.Column('calculated_variance', sa.BigInteger(), nullable=False),
        sa.Column('tolerance_rule', sa.String(length=120), nullable=True),
        sa.Column('result', sa.String(length=20), nullable=False),
        sa.Column('investigation_link', sa.String(length=200), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['packaging_run_id'], ['ebmr.packaging_run.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )

    op.create_table(
        'package_node',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('package_level', sa.String(length=20), nullable=False),
        sa.Column('business_ref', sa.String(length=120), nullable=True),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('parent_package_id', sa.UUID(), nullable=True),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='created'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.gxp_batch.id']),
        sa.ForeignKeyConstraint(['parent_package_id'], ['ebmr.package_node.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.packaging_run TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.label_issue TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.label_reconciliation TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.package_node TO {APP_ROLE}")


def downgrade() -> None:
    for table in ('package_node', 'label_reconciliation', 'label_issue', 'packaging_run'):
        op.execute(f"REVOKE ALL ON ebmr.{table} FROM {APP_ROLE}")
    op.drop_table('package_node', schema='ebmr')
    op.drop_table('label_reconciliation', schema='ebmr')
    op.drop_table('label_issue', schema='ebmr')
    op.drop_table('packaging_run', schema='ebmr')
