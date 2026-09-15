"""0023_lims_integration_schema

Revision ID: 7c9d1e3f5a2b
Revises: 2e5f8b3a9c1d
Create Date: 2026-08-24 00:00:00.000000

Document 24 (SPEC-QC-002) -- LIMS Integration Architecture & Generic Adapter Contract. Creates the 3
prose-only entities Document 24's own §6 "Mapping Tables" section defines (`lims_instance`,
`lims_mapping`, `lims_message`), typed directly as an ordinary engineering decision (SG-045's precedent).
Document 24 declares no entities at all in docs/generated/04_DATA_MODEL_CATALOGUE.md and never defines its
own "result" table -- this module is an adapter in front of the already-built `qc` module
(services/gxp-api/app/modules/qc): every accepted LIMS result is written via `qc.commands.record_raw_data`
+ `record_result`, reusing that module's acceptance/trend-rule classification and append-only result
versioning unmodified, never touching `qc_*` tables directly (Document 24 §18: "Never let adapter write
GxP tables directly").

Real blockers NOT built this pass (see SG-070 and the extended SG-066 in docs/generated/18_SPEC_GAPS.md):
LIMS-FR-013 (real mTLS/OAuth/workload-identity source authentication -- no service/machine-identity
mechanism exists anywhere in this codebase; endpoints instead reuse the existing human bearer-token auth),
LIMS-FR-016/020 (OOS record creation/retest linkage -- Document 25 not built yet), LIMS-FR-017
(LIMS_MANAGED_WITH_SYNC/HYBRID ownership modes -- only GXP_MANAGED is implemented; the other two are
explicitly rejected, not silently treated as GXP_MANAGED), LIMS-FR-034 (sandbox/simulator + contract test
suite -- a tooling deliverable, not runtime behavior).

Same deviations as prior additive migrations: `tenant_id` dropped (single-organization platform, ADR-0006).
Tables in the shared `ebmr` schema. `lims_mapping` gets an UPDATE grant (result-revision ingestion updates
an existing mapping row's `mapping_version`/`internal_object_id` in place); `lims_instance` and
`lims_message` do not -- neither is ever mutated after creation by any code path this pass (the same
append-only-where-actually-append-only discipline Document 23's `qc_result` privilege fix established).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '7c9d1e3f5a2b'
down_revision: Union[str, Sequence[str], None] = '2e5f8b3a9c1d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'lims_instance',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('instance_code', sa.String(length=80), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=True),
        sa.Column('provider_type', sa.String(length=60), nullable=False),
        sa.Column('provider_version', sa.String(length=40), nullable=True),
        sa.Column('endpoint_url', sa.String(length=300), nullable=True),
        sa.Column('auth_method', sa.String(length=40), nullable=True),
        sa.Column('ownership_mode', sa.String(length=40), nullable=False, server_default='gxp_managed'),
        sa.Column('service_actor_user_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='active'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['service_actor_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instance_code'),
        schema='ebmr',
    )

    op.create_table(
        'lims_mapping',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('instance_id', sa.UUID(), nullable=False),
        sa.Column('internal_object_type', sa.String(length=60), nullable=False),
        sa.Column('internal_object_id', sa.UUID(), nullable=True),
        sa.Column('internal_object_version', sa.Integer(), nullable=True),
        sa.Column('external_entity_type', sa.String(length=60), nullable=False),
        sa.Column('external_entity_id', sa.String(length=160), nullable=False),
        sa.Column('mapping_version', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='active'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['ebmr.lims_instance.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instance_id', 'external_entity_type', 'external_entity_id'),
        schema='ebmr',
    )
    op.create_index('ix_lims_mapping_internal', 'lims_mapping', ['internal_object_type', 'internal_object_id'], schema='ebmr')

    op.create_table(
        'lims_message',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('instance_id', sa.UUID(), nullable=False),
        sa.Column('direction', sa.String(length=20), nullable=False),
        sa.Column('external_event_id', sa.String(length=160), nullable=False),
        sa.Column('internal_correlation_id', sa.UUID(), nullable=True),
        sa.Column('payload_hash', sa.String(length=64), nullable=True),
        sa.Column('schema_version', sa.String(length=20), nullable=True),
        sa.Column('adapter_version', sa.String(length=40), nullable=True),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='pending'),
        sa.Column('error_code', sa.String(length=80), nullable=True),
        sa.Column('retry_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('received_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['instance_id'], ['ebmr.lims_instance.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('instance_id', 'external_event_id'),
        schema='ebmr',
    )

    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.lims_instance TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.lims_mapping TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON ebmr.lims_message TO {APP_ROLE}")


def downgrade() -> None:
    for table in ('lims_message', 'lims_mapping', 'lims_instance'):
        op.execute(f"REVOKE ALL ON ebmr.{table} FROM {APP_ROLE}")
    op.drop_table('lims_message', schema='ebmr')
    op.drop_table('lims_mapping', schema='ebmr')
    op.drop_table('lims_instance', schema='ebmr')
