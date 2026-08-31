"""0007_iam_policy_engine

Revision ID: 531f6f3cbbf8
Revises: 747afac225e8
Create Date: 2026-08-22 00:00:00.000000

WP-01 Document 07 (SPEC-IAM-001) — the real, specified core. Extends `iam.users` (= `iam_subject`) and
`iam.user_site_roles` (= `iam_role_assignment`) with the fields their Document 07 schemas add, per
docs/generated/04_DATA_MODEL_CATALOGUE.md. Adds a real permission catalog and role->permission mapping
(iam.permissions / iam.role_permissions) — the data-driven replacement for hardcoded require_role() name
checks. Replaces the previously unused, differently-shaped `iam.sod_rules` (FK-based role pair, zero rows,
zero enforcement) with the actual Document 107-specified schema and adds `iam.sod_exceptions`, per
Document 107 §3 (an approved gap-resolution baseline, precedence above the Phase-0 docs/generated/
compilation that never listed sod_rule/sod_exception at all).

`iam_qualification` and `iam_temporary_authorization` are NOT built here — their schemas are not
specified in the source baseline (see docs/generated/18_SPEC_GAPS.md new entries). `expires_at` on
user_site_roles covers the one small time-bounding need this pass actually has.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '531f6f3cbbf8'
down_revision: Union[str, Sequence[str], None] = '747afac225e8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    """Upgrade schema."""
    # --- iam_subject fields on iam.users --------------------------------------------------
    op.add_column('users', sa.Column('external_issuer', sa.String(length=500), nullable=True), schema='iam')
    op.add_column('users', sa.Column('external_subject', sa.String(length=255), nullable=True), schema='iam')
    op.add_column(
        'users',
        sa.Column('subject_type', sa.String(length=40), nullable=False, server_default='human'),
        schema='iam',
    )
    op.add_column(
        'users',
        sa.Column('identity_verified', sa.Boolean(), nullable=False, server_default=sa.false()),
        schema='iam',
    )
    op.add_column(
        'users',
        sa.Column('signing_entitled', sa.Boolean(), nullable=False, server_default=sa.true()),
        schema='iam',
    )
    op.add_column('users', sa.Column('disabled_at', sa.DateTime(timezone=True), nullable=True), schema='iam')

    # --- iam_role_assignment fields on iam.user_site_roles --------------------------------
    op.add_column(
        'user_site_roles',
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        schema='iam',
    )
    op.add_column(
        'user_site_roles', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True), schema='iam'
    )
    op.add_column(
        'user_site_roles',
        sa.Column('status', sa.String(length=40), nullable=False, server_default='active'),
        schema='iam',
    )
    op.add_column(
        'user_site_roles',
        sa.Column('approved_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='iam',
    )
    op.create_foreign_key(
        'fk_user_site_roles_approved_by_user_id',
        'user_site_roles', 'users',
        ['approved_by_user_id'], ['id'],
        source_schema='iam', referent_schema='iam',
    )

    # --- permission catalog + role->permission mapping -------------------------------------
    op.create_table(
        'permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=100), nullable=False),
        sa.Column('action', sa.String(length=60), nullable=False),
        sa.Column('resource_type', sa.String(length=60), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code'),
        schema='iam',
    )
    op.create_table(
        'role_permissions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('permission_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.ForeignKeyConstraint(['role_id'], ['iam.roles.id']),
        sa.ForeignKeyConstraint(['permission_id'], ['iam.permissions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('role_id', 'permission_id'),
        schema='iam',
    )

    # --- SoD: replace the unused FK-based table with Document 107's actual schema ----------
    op.drop_table('sod_rules', schema='iam')
    op.create_table(
        'sod_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('code', sa.String(length=80), nullable=False),
        sa.Column('rule_type', sa.String(length=20), nullable=False),
        sa.Column('role_a', sa.String(length=120), nullable=True),
        sa.Column('role_b', sa.String(length=120), nullable=True),
        sa.Column('record_class', sa.String(length=80), nullable=True),
        sa.Column('action', sa.String(length=120), nullable=True),
        sa.Column('independent_of', postgresql.JSONB(), nullable=True),
        sa.Column('severity', sa.String(length=20), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=False),
        sa.Column('source_reference', sa.String(length=200), nullable=False),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=False, server_default=sa.text('now()')),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('policy_source', sa.String(length=30), nullable=False, server_default='PLATFORM_FLOOR'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('code', 'effective_from'),
        sa.CheckConstraint(
            "rule_type <> 'STANDING_ROLE_PAIR' OR (role_a IS NOT NULL AND role_b IS NOT NULL)",
            name='ck_sod_rules_standing_pair_roles',
        ),
        schema='iam',
    )
    op.create_table(
        'sod_exceptions',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('subject_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('sod_rule_code', sa.String(length=80), nullable=False),
        sa.Column('reason', sa.Text(), nullable=False),
        sa.Column('scope', postgresql.JSONB(), nullable=False),
        sa.Column('requested_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approved_by_user_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('approval_signature_id', postgresql.UUID(as_uuid=True), nullable=True),
        sa.Column('valid_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('valid_to', sa.DateTime(timezone=True), nullable=False),
        sa.Column('review_due', sa.DateTime(timezone=True), nullable=True),
        sa.Column('state', sa.String(length=30), nullable=False, server_default='active'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['subject_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='iam',
    )

    # --- privileges: SELECT/INSERT/UPDATE/TRUNCATE on the new tables (matches what every pre-existing
    # table in this database already carries — TRUNCATE is used by the test suite's between-test
    # cleanup, not by application code); DELETE on role_permissions only, for the bulk-set "assign
    # permissions to a role" endpoint (replace semantics) ------------------------------------------
    for table in ('permissions', 'role_permissions', 'sod_rules', 'sod_exceptions'):
        op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON iam.{table} TO {APP_ROLE}")
    op.execute(f"GRANT DELETE ON iam.role_permissions TO {APP_ROLE}")


def downgrade() -> None:
    """Downgrade schema."""
    op.execute(f"REVOKE DELETE ON iam.role_permissions FROM {APP_ROLE}")
    for table in ('permissions', 'role_permissions', 'sod_rules', 'sod_exceptions'):
        op.execute(f"REVOKE SELECT, INSERT, UPDATE, TRUNCATE ON iam.{table} FROM {APP_ROLE}")

    op.drop_table('sod_exceptions', schema='iam')
    op.drop_table('sod_rules', schema='iam')
    op.create_table(
        'sod_rules',
        sa.Column('id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_a_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('role_b_id', postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column('description', sa.String(length=500), nullable=True),
        sa.ForeignKeyConstraint(['role_a_id'], ['iam.roles.id']),
        sa.ForeignKeyConstraint(['role_b_id'], ['iam.roles.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='iam',
    )

    op.drop_table('role_permissions', schema='iam')
    op.drop_table('permissions', schema='iam')

    op.drop_constraint('fk_user_site_roles_approved_by_user_id', 'user_site_roles', schema='iam', type_='foreignkey')
    op.drop_column('user_site_roles', 'approved_by_user_id', schema='iam')
    op.drop_column('user_site_roles', 'status', schema='iam')
    op.drop_column('user_site_roles', 'expires_at', schema='iam')
    op.drop_column('user_site_roles', 'effective_from', schema='iam')

    op.drop_column('users', 'disabled_at', schema='iam')
    op.drop_column('users', 'signing_entitled', schema='iam')
    op.drop_column('users', 'identity_verified', schema='iam')
    op.drop_column('users', 'subject_type', schema='iam')
    op.drop_column('users', 'external_subject', schema='iam')
    op.drop_column('users', 'external_issuer', schema='iam')
