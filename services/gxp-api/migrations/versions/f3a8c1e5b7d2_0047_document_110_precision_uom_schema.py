"""0047_document_110_precision_uom_schema

Revision ID: f3a8c1e5b7d2
Revises: d4a8f2c60b19
Create Date: 2026-08-27 00:00:00.000000

Document 110 (SPEC-GXP-008, SG-143) — additive, nullable throughout (MIG-FR-004 expand step; no
existing row rewritten, AG-08).

- `rules.gxp_uom` / `rules.gxp_uom_conversion` (§3): the controlled UOM master and conversion tables.
  New tables — no backfill needed. Empty at migration time; no regulated master data is seeded here
  (seeding a specific UOM/conversion factor would itself be a content decision — see
  docs/generated/18_SPEC_GAPS.md SG-146). No author/release command exists yet either (same gap);
  rows are written directly by a controlled migration/seed or test fixture until that surface is built.
- `rules.gxp_rule_evaluation.raw_result` / `.applied_policy_version` (CALC-FR-002/004/008): nullable
  columns so every evaluation recorded before this revision reads back exactly as it was written (no
  historical row is touched), and so a rule evaluated under a `precision_policy` with no resolvable
  Document 110 calculation class (a rule drafted before this pass, or a test fixture inserted directly)
  keeps recording NULL for both rather than being retroactively required to have one.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'f3a8c1e5b7d2'
down_revision: Union[str, Sequence[str], None] = 'd4a8f2c60b19'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.add_column(
        'gxp_rule_evaluation',
        sa.Column('raw_result', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema='rules',
    )
    op.add_column(
        'gxp_rule_evaluation',
        sa.Column('applied_policy_version', sa.String(length=40), nullable=True),
        schema='rules',
    )

    op.create_table(
        'gxp_uom',
        sa.Column('uom_id', sa.UUID(), nullable=False),
        sa.Column('code', sa.String(length=20), nullable=False),
        sa.Column('dimension', sa.String(length=40), nullable=False),
        sa.Column('base_unit', sa.String(length=20), nullable=False),
        sa.Column('factor', sa.Numeric(38, 18), nullable=False),
        sa.Column('offset', sa.Numeric(38, 18), nullable=False, server_default='0'),
        sa.Column('precision_dp', sa.Integer(), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('uom_id'),
        sa.UniqueConstraint('code', 'version'),
        schema='rules',
    )
    op.create_table(
        'gxp_uom_conversion',
        sa.Column('conversion_id', sa.UUID(), nullable=False),
        sa.Column('from_code', sa.String(length=20), nullable=False),
        sa.Column('to_code', sa.String(length=20), nullable=False),
        sa.Column('factor', sa.Numeric(38, 18), nullable=False),
        sa.Column('rounding_stage', sa.String(length=40), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='draft'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('conversion_id'),
        sa.UniqueConstraint('from_code', 'to_code', 'version'),
        schema='rules',
    )

    # Reference/master data — same append-mostly shape as gxp_rule_definition (draft -> released is an
    # in-place status transition), so SELECT/INSERT/UPDATE/TRUNCATE, matching migration 0009's grant for
    # gxp_rule_definition (TRUNCATE for the test suite's between-test cleanup, same as every other
    # regulated table per migration 0008's discovery).
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON rules.gxp_uom TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON rules.gxp_uom_conversion TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON rules.gxp_uom_conversion FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON rules.gxp_uom FROM {APP_ROLE}")
    op.drop_table('gxp_uom_conversion', schema='rules')
    op.drop_table('gxp_uom', schema='rules')
    op.drop_column('gxp_rule_evaluation', 'applied_policy_version', schema='rules')
    op.drop_column('gxp_rule_evaluation', 'raw_result', schema='rules')
