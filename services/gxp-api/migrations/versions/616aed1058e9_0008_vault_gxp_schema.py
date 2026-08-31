"""0008_vault_gxp_schema

Revision ID: 616aed1058e9
Revises: 531f6f3cbbf8
Create Date: 2026-08-22 00:00:00.000000

Document 06 (SPEC-GXP-004). Drops the unused `vault.vault_versions` stub from the WP-00 kernel migration
(never wired to any router/service/caller — confirmed by grep before writing this) and replaces it with the
schema Document 112 actually resolved SG-011 to (`gxp_vault_object`/`gxp_vault_evidence`/
`gxp_record_correction`, per docs/generated/04_DATA_MODEL_CATALOGUE.md). Same append-only privilege pattern
as audit_events/signatures for gxp_vault_object/gxp_vault_evidence; gxp_record_correction additionally needs
UPDATE for its own status/completed_at/resulting_object_id as a correction moves requested -> completed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '616aed1058e9'
down_revision: Union[str, Sequence[str], None] = '531f6f3cbbf8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.drop_table('vault_versions', schema='vault')

    op.create_table(
        'gxp_vault_object',
        sa.Column('object_id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('object_type', sa.String(length=100), nullable=False),
        sa.Column('business_id', sa.String(length=160), nullable=False),
        sa.Column('internal_version', sa.Integer(), nullable=False),
        sa.Column('business_version_label', sa.String(length=80), nullable=True),
        sa.Column('schema_version', sa.String(length=30), nullable=False, server_default='1'),
        sa.Column('canonical_payload', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('digest_algorithm', sa.String(length=40), nullable=False, server_default='sha256'),
        sa.Column('digest', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='released'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('supersedes_object_id', sa.UUID(), nullable=True),
        sa.Column('corrected_from_object_id', sa.UUID(), nullable=True),
        sa.Column('retention_class', sa.String(length=80), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('created_by_subject', sa.UUID(), nullable=True),
        sa.ForeignKeyConstraint(['corrected_from_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.ForeignKeyConstraint(['created_by_subject'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['supersedes_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.PrimaryKeyConstraint('object_id'),
        sa.UniqueConstraint('object_type', 'business_id', 'internal_version'),
        schema='vault',
    )
    op.create_table(
        'gxp_vault_evidence',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('vault_object_id', sa.UUID(), nullable=False),
        sa.Column('evidence_id', sa.UUID(), nullable=False),
        sa.Column('evidence_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('evidence_sha256', sa.String(length=64), nullable=False),
        sa.Column('media_type', sa.String(length=120), nullable=True),
        sa.Column('sequence', sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(['vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.PrimaryKeyConstraint('id'),
        schema='vault',
    )
    op.create_table(
        'gxp_record_correction',
        sa.Column('correction_id', sa.UUID(), nullable=False),
        sa.Column('record_object_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='requested'),
        sa.Column('reason_code', sa.String(length=80), nullable=True),
        sa.Column('reason_text', sa.Text(), nullable=True),
        sa.Column('impact_assessment', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('requested_by', sa.UUID(), nullable=True),
        sa.Column('approved_by_signatures', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('resulting_object_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('completed_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['record_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.ForeignKeyConstraint(['requested_by'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['resulting_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.PrimaryKeyConstraint('correction_id'),
        schema='vault',
    )

    # Append-only for the released/evidence tables (AG-08); corrections need UPDATE for their own
    # status/completed_at/resulting_object_id lifecycle (requested -> completed). TRUNCATE is granted on
    # every table here (not just these two) because the test suite's between-test cleanup needs it —
    # matching what every pre-existing regulated table in this database already carries (confirmed via
    # \dp: audit.audit_events has TRUNCATE for the app role despite migration 0002 never granting it
    # explicitly — applied out-of-band at some point; migration 0007 hit the same thing and grants it
    # explicitly for new tables, which this follows).
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON vault.gxp_vault_object TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON vault.gxp_vault_evidence TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON vault.gxp_record_correction TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON vault.gxp_record_correction FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON vault.gxp_vault_evidence FROM {APP_ROLE}")
    op.execute(f"REVOKE ALL ON vault.gxp_vault_object FROM {APP_ROLE}")
    op.drop_table('gxp_record_correction', schema='vault')
    op.drop_table('gxp_vault_evidence', schema='vault')
    op.drop_table('gxp_vault_object', schema='vault')

    op.create_table(
        'vault_versions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('object_type', sa.String(length=100), nullable=False),
        sa.Column('business_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('canonical_json', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('digest', sa.String(length=64), nullable=False),
        sa.Column('status', sa.String(length=30), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('released_by_signature_id', sa.UUID(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('object_type', 'business_id', 'version'),
        schema='vault',
    )
    op.execute(f"GRANT SELECT, INSERT ON vault.vault_versions TO {APP_ROLE}")
