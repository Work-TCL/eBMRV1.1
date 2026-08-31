"""0068_security_incident_forensics_schema

Revision ID: e5b3d9a2c7f4
Revises: d4a2c8f1b6e3
Create Date: 2026-08-31 00:00:00.000000

Document 67 (SPEC-SEC-007) -- Security Logging, Monitoring, Incident Response & Forensic Evidence. Same
`security` schema Documents 61-66 created; adds the 2 owned entities `04_DATA_MODEL_CATALOGUE.md` lists:
`security_incident`, `forensic_evidence`. `security_event` is NOT an owned table -- security telemetry
is the transactional outbox, kept distinct from the GxP audit ledger (MON-FR-002). See
app/modules/security/incident_models.py for the Document 106 row 140 signature resolution (incident
close -> Approved, independent QA Releaser) and why only `close` is signed.

Same deviations as prior additive `security.*` migrations: no `tenant_id` (ADR-0006), no `site_id`
(affected scope, including sites, is JSONB). No binary float.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e5b3d9a2c7f4'
down_revision: Union[str, Sequence[str], None] = 'd4a2c8f1b6e3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'security_incident',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('incident_number', sa.String(length=40), nullable=False),
        sa.Column('title', sa.String(length=300), nullable=False),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='OPEN'),
        sa.Column('owner_subject_id', sa.UUID(), nullable=False),
        sa.Column('affected_scope', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='{}'),
        sa.Column('alert_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('detected_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('contained_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('recovered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('closed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('containment_actions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('gxp_impact_state', sa.String(length=30), nullable=False, server_default='NOT_ASSESSED'),
        sa.Column('gxp_impact', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('root_cause', sa.Text(), nullable=True),
        sa.Column('corrective_actions', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('residual_risk', sa.String(length=200), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['owner_subject_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('incident_number'),
        schema='security',
    )
    op.create_index('ix_security_incident_state', 'security_incident', ['state'], schema='security')

    op.create_table(
        'forensic_evidence',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('incident_id', sa.UUID(), nullable=False),
        sa.Column('source', sa.String(length=300), nullable=False),
        sa.Column('acquisition_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('acquired_by', sa.UUID(), nullable=False),
        sa.Column('hash_algorithm', sa.String(length=20), nullable=False, server_default='SHA-256'),
        sa.Column('digest', sa.String(length=128), nullable=False),
        sa.Column('object_ref', sa.String(length=300), nullable=True),
        sa.Column('chain_of_custody', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['incident_id'], ['security.security_incident.id']),
        sa.ForeignKeyConstraint(['acquired_by'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='security',
    )
    op.create_index('ix_forensic_evidence_incident', 'forensic_evidence', ['incident_id'], schema='security')

    for t in ('security_incident', 'forensic_evidence'):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON security.{t} TO {APP_ROLE}")


def downgrade() -> None:
    for t in ('forensic_evidence', 'security_incident'):
        op.execute(f"REVOKE ALL ON security.{t} FROM {APP_ROLE}")
    op.drop_index('ix_forensic_evidence_incident', table_name='forensic_evidence', schema='security')
    op.drop_table('forensic_evidence', schema='security')
    op.drop_index('ix_security_incident_state', table_name='security_incident', schema='security')
    op.drop_table('security_incident', schema='security')
