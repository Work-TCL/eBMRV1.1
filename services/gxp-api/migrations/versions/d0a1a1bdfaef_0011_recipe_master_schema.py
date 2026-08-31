"""0011_recipe_master_schema

Revision ID: d0a1a1bdfaef
Revises: d5d48a66187f
Create Date: 2026-08-22 00:00:03.000000

Document 10 (SPEC-EBMR-001) — Master Recipe / Master Manufacturing Record. Additive only: creates 7 new
tables in the existing `ebmr` schema; does not touch `ebmr.recipes`, `ebmr.recipe_steps`, `ebmr.products`,
`ebmr.batches` at all. `Batch`/`Recipe` keep using the legacy stub tables unmodified this pass — the actual
cutover is its own future migration (see SG-044).

Per docs/generated/04_DATA_MODEL_CATALOGUE.md, 7 of Document 10's 9 owned entities are prose-only (field
names with no types/constraints) -- worse than Document 09's 2-of-6. Two of those seven
(recipe_material_requirement, recipe_equipment_requirement) are genuinely ambiguous policy descriptions, not
column lists, and are deferred (SG-045). The other five (recipe_family, recipe_section,
recipe_step_dependency, recipe_parameter, recipe_evidence_requirement) are unambiguous field-name lists that
this migration types directly -- the same ordinary-engineering-decision latitude already used for Document
09's typed entities, not a guess at regulated content. `recipe_version`/`recipe_step` were already
(mostly) typed in the catalogue; a few combined/untyped lines in those two are split/typed here too
(e.g. `effective_from/to` -> two timestamptz columns; `qualification_policy_id`/`signature_policy_id`/
`exception_policy_id` typed as nullable uuid logical references, since none of their target tables exist yet).

Same deviations as migration d5d48a66187f: `tenant_id` dropped (single-organization platform), `version`
bigint (optimistic concurrency) added to recipe_version since the catalogue's boilerplate footer calls for
it on every table but omitted it from the field list.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'd0a1a1bdfaef'
down_revision: Union[str, Sequence[str], None] = 'd5d48a66187f'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'gxp_recipe_family',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('product_business_id', sa.String(length=120), nullable=False),
        sa.Column('recipe_code', sa.String(length=120), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('manufacturing_profile_code', sa.String(length=80), nullable=False),
        sa.Column('lifecycle_state', sa.String(length=40), nullable=False, server_default='active'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recipe_code'),
        schema='ebmr',
    )

    op.create_table(
        'gxp_recipe_version',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('recipe_family_id', sa.UUID(), nullable=False),
        sa.Column('version_no', sa.BigInteger(), nullable=False),
        sa.Column('product_version_id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_size_value', sa.Numeric(24, 8), nullable=True),
        sa.Column('batch_size_uom', sa.String(length=40), nullable=True),
        sa.Column('lifecycle_state', sa.String(length=40), nullable=False, server_default='draft'),
        sa.Column('effective_from', sa.DateTime(timezone=True), nullable=True),
        sa.Column('effective_to', sa.DateTime(timezone=True), nullable=True),
        sa.Column('graph_version', sa.String(length=20), nullable=False, server_default='1'),
        sa.Column('released_vault_object_id', sa.UUID(), nullable=True),
        sa.Column('version_hash', sa.String(length=64), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['recipe_family_id'], ['ebmr.gxp_recipe_family.id']),
        sa.ForeignKeyConstraint(['product_version_id'], ['ebmr.gxp_product_version.id']),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['released_vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recipe_family_id', 'version_no'),
        schema='ebmr',
    )

    op.create_table(
        'gxp_recipe_section',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('recipe_version_id', sa.UUID(), nullable=False),
        sa.Column('stable_section_code', sa.String(length=80), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('area_requirement_id', sa.UUID(), nullable=True),
        sa.Column('parallel_group', sa.String(length=40), nullable=True),
        sa.Column('expected_duration_minutes', sa.Integer(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['recipe_version_id'], ['ebmr.gxp_recipe_version.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recipe_version_id', 'stable_section_code'),
        schema='ebmr',
    )

    op.create_table(
        'gxp_recipe_step',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('recipe_version_id', sa.UUID(), nullable=False),
        sa.Column('stable_step_code', sa.String(length=80), nullable=False),
        sa.Column('section_id', sa.UUID(), nullable=False),
        sa.Column('step_type', sa.String(length=60), nullable=False),
        sa.Column('instruction_text', sa.String(length=4000), nullable=True),
        sa.Column('sequence_hint', sa.Integer(), nullable=False),
        sa.Column('required_role_code', sa.String(length=80), nullable=True),
        sa.Column('qualification_policy_id', sa.UUID(), nullable=True),
        sa.Column('signature_policy_id', sa.UUID(), nullable=True),
        sa.Column('exception_policy_id', sa.UUID(), nullable=True),
        sa.Column('is_critical', sa.Boolean(), nullable=False, server_default=sa.text('false')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['recipe_version_id'], ['ebmr.gxp_recipe_version.id']),
        sa.ForeignKeyConstraint(['section_id'], ['ebmr.gxp_recipe_section.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('recipe_version_id', 'stable_step_code'),
        schema='ebmr',
    )

    op.create_table(
        'gxp_recipe_step_dependency',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('predecessor_step_id', sa.UUID(), nullable=False),
        sa.Column('successor_step_id', sa.UUID(), nullable=False),
        sa.Column('condition_rule_id', sa.String(length=160), nullable=True),
        sa.Column('condition_rule_version', sa.String(length=40), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['predecessor_step_id'], ['ebmr.gxp_recipe_step.id']),
        sa.ForeignKeyConstraint(['successor_step_id'], ['ebmr.gxp_recipe_step.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('predecessor_step_id', 'successor_step_id'),
        schema='ebmr',
    )

    op.create_table(
        'gxp_recipe_parameter',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=False),
        sa.Column('parameter_code', sa.String(length=80), nullable=False),
        sa.Column('data_type', sa.String(length=40), nullable=False),
        sa.Column('uom', sa.String(length=40), nullable=True),
        sa.Column('source_type', sa.String(length=40), nullable=False),
        sa.Column('target_value', sa.Numeric(24, 8), nullable=True),
        sa.Column('min_value', sa.Numeric(24, 8), nullable=True),
        sa.Column('max_value', sa.Numeric(24, 8), nullable=True),
        sa.Column('precision_digits', sa.Integer(), nullable=True),
        sa.Column('required', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('rule_id', sa.String(length=160), nullable=True),
        sa.Column('rule_version', sa.String(length=40), nullable=True),
        sa.Column('manual_fallback_policy', sa.String(length=40), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['step_id'], ['ebmr.gxp_recipe_step.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('step_id', 'parameter_code'),
        schema='ebmr',
    )

    op.create_table(
        'gxp_recipe_evidence_requirement',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=False),
        sa.Column('evidence_type', sa.String(length=80), nullable=False),
        sa.Column('required_count', sa.Integer(), nullable=False, server_default='1'),
        sa.Column('allowed_mime_types', sa.String(length=255), nullable=True),
        sa.Column('retention_class', sa.String(length=80), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['step_id'], ['ebmr.gxp_recipe_step.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='ebmr',
    )

    # Mutable pre-release, same reasoning as gxp_product_version/gxp_rule_definition -- immutability of a
    # *released* version comes from its vault snapshot (VLT-FR-001), not DB-privilege revocation.
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.gxp_recipe_family TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON ebmr.gxp_recipe_version TO {APP_ROLE}")
    # Sections/steps/dependencies/parameters/evidence requirements are wholesale-replaced on draft edit
    # (same reasoning as the existing DELETE grant on ebmr.recipe_steps, migration 747afac225e8).
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ebmr.gxp_recipe_section TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ebmr.gxp_recipe_step TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ebmr.gxp_recipe_step_dependency TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ebmr.gxp_recipe_parameter TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, DELETE, TRUNCATE ON ebmr.gxp_recipe_evidence_requirement TO {APP_ROLE}")


def downgrade() -> None:
    for table in (
        'gxp_recipe_evidence_requirement',
        'gxp_recipe_parameter',
        'gxp_recipe_step_dependency',
        'gxp_recipe_step',
        'gxp_recipe_section',
        'gxp_recipe_version',
        'gxp_recipe_family',
    ):
        op.execute(f"REVOKE ALL ON ebmr.{table} FROM {APP_ROLE}")
    op.drop_table('gxp_recipe_evidence_requirement', schema='ebmr')
    op.drop_table('gxp_recipe_parameter', schema='ebmr')
    op.drop_table('gxp_recipe_step_dependency', schema='ebmr')
    op.drop_table('gxp_recipe_step', schema='ebmr')
    op.drop_table('gxp_recipe_section', schema='ebmr')
    op.drop_table('gxp_recipe_version', schema='ebmr')
    op.drop_table('gxp_recipe_family', schema='ebmr')
