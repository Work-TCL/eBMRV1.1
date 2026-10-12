"""0146_packaging_label_master_print_job

Revision ID: c4e8b2a6f1d9
Revises: 8a5c3e1f9d27
Create Date: 2026-10-09 00:00:00.000000

PKG-FR-003/006/SG-056 resolved (project-owner-directed, client gap-closure item #10: "Build a minimal
version"). Adds `ebmr.label_master` (the "label template/artwork version" Document 16 section 5's own
Label Job Contract names but never models as an entity) and `ebmr.print_job` (named by
`POST /packaging/v1/print-jobs` in Document 16's own 10-op API list, but with no entity to persist
against before this pass). `label_issue.label_version_id`/`print_job_id` -- previously unenforced UUID
columns, nullable, no existing rows reference anything not yet in these new tables -- now carry real FK
constraints.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = 'c4e8b2a6f1d9'
down_revision: Union[str, Sequence[str], None] = '8a5c3e1f9d27'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'label_master',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('iam.sites.id'), nullable=False),
        sa.Column('label_code', sa.String(120), nullable=False),
        sa.Column('version_label', sa.String(60), nullable=False),
        sa.Column('product_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ebmr.gxp_product_version.id'), nullable=True),
        sa.Column('content_hash', sa.String(64), nullable=False),
        sa.Column('state', sa.String(20), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.UniqueConstraint('label_code', 'version_label', name='uq_label_master_code_version'),
        schema='ebmr',
    )
    op.create_table(
        'print_job',
        sa.Column('id', postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column('site_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('iam.sites.id'), nullable=False),
        sa.Column('packaging_run_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ebmr.packaging_run.id'), nullable=False),
        sa.Column('label_version_id', postgresql.UUID(as_uuid=True), sa.ForeignKey('ebmr.label_master.id'), nullable=False),
        sa.Column('quantity', sa.BigInteger(), nullable=False),
        sa.Column('variable_data', postgresql.JSONB(), nullable=True),
        sa.Column('printer_ref', sa.String(120), nullable=True),
        sa.Column('requested_by', postgresql.UUID(as_uuid=True), sa.ForeignKey('iam.users.id'), nullable=False),
        sa.Column('output_hash', sa.String(64), nullable=True),
        sa.Column('state', sa.String(20), nullable=False, server_default='printed'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now()),
        schema='ebmr',
    )
    op.create_index('ix_print_job_run', 'print_job', ['packaging_run_id'], schema='ebmr')

    op.create_foreign_key(
        'fk_label_issue_label_version_id', 'label_issue', 'label_master',
        ['label_version_id'], ['id'], source_schema='ebmr', referent_schema='ebmr',
    )
    op.create_foreign_key(
        'fk_label_issue_print_job_id', 'label_issue', 'print_job',
        ['print_job_id'], ['id'], source_schema='ebmr', referent_schema='ebmr',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.label_master TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.print_job TO {APP_ROLE}")


def downgrade() -> None:
    op.drop_constraint('fk_label_issue_print_job_id', 'label_issue', schema='ebmr', type_='foreignkey')
    op.drop_constraint('fk_label_issue_label_version_id', 'label_issue', schema='ebmr', type_='foreignkey')
    op.drop_table('print_job', schema='ebmr')
    op.drop_table('label_master', schema='ebmr')
