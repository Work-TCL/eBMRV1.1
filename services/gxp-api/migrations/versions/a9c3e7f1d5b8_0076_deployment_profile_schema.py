"""0076_deployment_profile_schema

Revision ID: a9c3e7f1d5b8
Revises: f3d8a5c2b7e1
Create Date: 2026-08-31 00:00:00.000000

Document 77 (SPEC-DATA-009) -- Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade
Architecture. New `deployment` schema, the 1 owned entity `04_DATA_MODEL_CATALOGUE.md` lists:
`deployment_profile`. Distinct from `security.deployment_security_profile` (Document 66) -- see
app/modules/deployment/models.py module docstring. **0 owned HTTP APIs** -- CI/installer-tooling
populated (`commands.py`, no router). No signature (Document 106 has no SPEC-DATA-009 row). No
`tenant_id`/`site_id` (whole-environment concept, ADR-0006).

**Expand-only** -- one brand-new table in a brand-new schema, no existing table altered, no backfill.
Grants: `USAGE` + `SELECT/INSERT/UPDATE/TRUNCATE` (no `DELETE`). Forward + downgrade + re-upgrade
tested on the restored test database. Reversible: `downgrade()` drops the table and the schema.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a9c3e7f1d5b8'
down_revision: Union[str, Sequence[str], None] = 'f3d8a5c2b7e1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.execute("CREATE SCHEMA IF NOT EXISTS deployment")

    op.create_table(
        'deployment_profile',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('profile_name', sa.String(length=80), nullable=False),
        sa.Column('environment', sa.String(length=20), nullable=False),
        sa.Column('cloud_provider', sa.String(length=20), nullable=False),
        sa.Column('region', sa.String(length=60), nullable=True),
        sa.Column('k8s_namespace', sa.String(length=80), nullable=True),
        sa.Column('image_digest', sa.String(length=160), nullable=True),
        sa.Column('iac_state_ref', sa.String(length=300), nullable=True),
        sa.Column('ha_profile', sa.String(length=20), nullable=False, server_default='HA'),
        sa.Column('state', sa.String(length=20), nullable=False, server_default='EFFECTIVE'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('profile_name'),
        schema='deployment',
    )

    op.execute(f"GRANT USAGE ON SCHEMA deployment TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON deployment.deployment_profile TO {APP_ROLE}")
    op.execute(f"REVOKE CREATE ON SCHEMA deployment FROM {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON deployment.deployment_profile FROM {APP_ROLE}")
    op.execute(f"REVOKE USAGE ON SCHEMA deployment FROM {APP_ROLE}")
    op.drop_table('deployment_profile', schema='deployment')
    op.execute("DROP SCHEMA IF EXISTS deployment")
