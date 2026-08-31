"""0009_rules_schema

Revision ID: bded27d367f2
Revises: 616aed1058e9
Create Date: 2026-08-22 00:00:01.000000

Document 08 (SPEC-GXP-006). `gxp_rule_definition`/`gxp_rule_evaluation`, per
docs/generated/04_DATA_MODEL_CATALOGUE.md — both fully specified, no schema gap unlike Document 07/05.
`rules` is a new schema; needs the same USAGE + DML grant pattern migration 0002 established for the
existing five (iam/mutation/signature/vault/ebmr).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'bded27d367f2'
down_revision: Union[str, Sequence[str], None] = '616aed1058e9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS rules")

    op.create_table(
        'gxp_rule_definition',
        sa.Column('rule_object_id', sa.UUID(), nullable=False),
        sa.Column('rule_id', sa.String(length=160), nullable=False),
        sa.Column('rule_type', sa.String(length=60), nullable=False),
        sa.Column('semantic_version', sa.String(length=40), nullable=False),
        sa.Column('schema_version', sa.String(length=20), nullable=False, server_default='1'),
        sa.Column('scope', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='draft'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('expression_ast', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('input_contract', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('output_contract', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('unit_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('precision_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('rounding_policy', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('reason_codes', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('engine_compatibility', sa.String(length=80), nullable=True),
        sa.Column('released_vault_object_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['released_vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.PrimaryKeyConstraint('rule_object_id'),
        sa.UniqueConstraint('rule_id', 'semantic_version'),
        schema='rules',
    )
    op.create_table(
        'gxp_rule_evaluation',
        sa.Column('evaluation_id', sa.UUID(), nullable=False),
        sa.Column('rule_object_id', sa.UUID(), nullable=False),
        sa.Column('aggregate_type', sa.String(length=100), nullable=True),
        sa.Column('aggregate_id', sa.UUID(), nullable=True),
        sa.Column('aggregate_version', sa.Integer(), nullable=True),
        sa.Column('input_hash', sa.String(length=64), nullable=False),
        sa.Column('inputs_or_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('result', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('outcome', sa.String(length=40), nullable=False),
        sa.Column('evaluated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('engine_version', sa.String(length=40), nullable=False, server_default='1'),
        sa.Column('correlation_id', sa.UUID(), nullable=False),
        sa.ForeignKeyConstraint(['rule_object_id'], ['rules.gxp_rule_definition.rule_object_id']),
        sa.PrimaryKeyConstraint('evaluation_id'),
        schema='rules',
    )

    op.execute(f"GRANT USAGE ON SCHEMA rules TO {APP_ROLE}")
    # gxp_rule_definition needs UPDATE too: draft -> validated -> released is an in-place status/
    # effective-dating transition on the same row (unlike vault, which never updates a released row).
    # TRUNCATE on both: matches every pre-existing regulated table (see migration 0008's comment on the
    # same discovery) — the test suite's between-test cleanup needs it.
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON rules.gxp_rule_definition TO {APP_ROLE}")
    # Evaluations are append-only (AG-08-style — a persisted regulated result is never edited).
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON rules.gxp_rule_evaluation TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA rules FROM {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON rules.gxp_rule_evaluation FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON rules.gxp_rule_definition FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA rules FROM {APP_ROLE}")
    op.drop_table('gxp_rule_evaluation', schema='rules')
    op.drop_table('gxp_rule_definition', schema='rules')
    op.execute("DROP SCHEMA IF EXISTS rules")
