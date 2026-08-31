"""0066_crypto_secrets_pki_schema

Revision ID: c3f8a1d7e5b2
Revises: b1e7c4a9d2f6
Create Date: 2026-08-31 00:00:00.000000

Document 65 (SPEC-SEC-005) -- Secrets Management, PKI, Cryptography & Key Lifecycle. Same `security`
schema Documents 61-64 created; adds the 3 owned entities `04_DATA_MODEL_CATALOGUE.md` lists:
`secret_metadata`, `certificate_metadata`, `crypto_profile`. Metadata only -- no key material ever
stored (Document 65 # 14). See app/modules/security/crypto_models.py for the Document 106 rows 137-139
signature resolution (certificate issue/rotate/revoke -> Released, QA Releaser, independent).

Same deviations as prior additive `security.*` migrations: no `tenant_id` (ADR-0006), no `site_id`
(platform-level). Integer columns for every interval / validity / key size -- never binary float.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'c3f8a1d7e5b2'
down_revision: Union[str, Sequence[str], None] = 'b1e7c4a9d2f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'secret_metadata',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('secret_ref', sa.String(length=200), nullable=False),
        sa.Column('provider', sa.String(length=60), nullable=False),
        sa.Column('purpose', sa.Text(), nullable=False),
        sa.Column('owner', sa.String(length=120), nullable=False),
        sa.Column('consumer_identities', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('rotation_interval_days', sa.BigInteger(), nullable=False, server_default='90'),
        sa.Column('last_rotated_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('next_rotation_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('incident_ref', sa.String(length=120), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='ACTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('secret_ref'),
        schema='security',
    )
    op.create_index('ix_secret_metadata_state', 'secret_metadata', ['state'], schema='security')

    op.create_table(
        'certificate_metadata',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('serial', sa.String(length=120), nullable=False),
        sa.Column('subject_sans', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('identity_id', sa.UUID(), nullable=True),
        sa.Column('profile', sa.String(length=60), nullable=False),
        sa.Column('issued_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='REQUESTED'),
        sa.Column('issuer_ref', sa.String(length=200), nullable=False),
        sa.Column('supersedes_id', sa.UUID(), nullable=True),
        sa.Column('revocation_reason', sa.String(length=40), nullable=True),
        sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['supersedes_id'], ['security.certificate_metadata.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('serial'),
        schema='security',
    )
    op.create_index('ix_certificate_metadata_state', 'certificate_metadata', ['state'], schema='security')

    op.create_table(
        'crypto_profile',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('profile_name', sa.String(length=80), nullable=False),
        sa.Column('tls_baseline', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('hash_algorithms', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('symmetric_algorithms', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('asymmetric_algorithms', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('key_sizes', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('migration_notes', sa.Text(), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='DRAFT'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('profile_name', 'version'),
        schema='security',
    )

    for t in ('secret_metadata', 'certificate_metadata', 'crypto_profile'):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.{t} TO {APP_ROLE}")


def downgrade() -> None:
    for t in ('crypto_profile', 'certificate_metadata', 'secret_metadata'):
        op.execute(f"REVOKE ALL ON security.{t} FROM {APP_ROLE}")
    op.drop_table('crypto_profile', schema='security')
    op.drop_index('ix_certificate_metadata_state', table_name='certificate_metadata', schema='security')
    op.drop_table('certificate_metadata', schema='security')
    op.drop_index('ix_secret_metadata_state', table_name='secret_metadata', schema='security')
    op.drop_table('secret_metadata', schema='security')
