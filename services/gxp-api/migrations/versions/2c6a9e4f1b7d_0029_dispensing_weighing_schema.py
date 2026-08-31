"""0029_dispensing_weighing_schema

Revision ID: 2c6a9e4f1b7d
Revises: 5d9f3e7a1c4b
Create Date: 2026-08-24 00:00:00.000000

Document 21 (SPEC-MAT-002C) -- Material Dispensing & Weighing. Extends the already-built `materials`
module (owner service confirmed by docs/generated/04_DATA_MODEL_CATALOGUE.md /
05_DATABASE_OWNERSHIP_MATRIX.md for all 4 entities): `dispensing_order`, `dispensing_source`,
`weighing_session` (split into `weighing_sessions` + append-only `weighing_readings` -- the spec's own
field list embeds "readings" as a plural collection inside one session object, which is a mutable-list
shape that would violate AG-08's append-only-history discipline for individual readings, DSP-FR-014
"original overweight reading retained"), `dispensed_container`.

No `tenant_id` column on any new table (ADR-0006, single-organization platform -- same deviation as every
other additive migration this project). Quantity columns on the new ledger-adjacent tables
(`dispensing_orders.target_qty`/`tolerance_low`/`tolerance_high`, `dispensing_sources.reserved_quantity`/
`actual_taken_quantity`, `weighing_sessions.tare_value`, `weighing_readings.reading_value`) use the same
numeric(24,8) precision as Document 20's `inventory_transaction`/`inventory_balance_projection` family,
since dispensing directly consumes that ledger (DSP-FR-022 posts an `inventory_transaction` of type
DISPENSE, already declared in `INVENTORY_TRANSACTION_TYPES`). `dispensed_containers.actual_quantity` uses
Numeric(18,6) to match `material_containers`' existing precision, since it's a container-identity entity,
not a ledger row.

`dispensing_orders.batch_step_id`/`material_spec_version_id` carry no FK constraint -- no
`material_requirement` entity exists anywhere in this codebase (SG-089 -- see docs/generated/
18_SPEC_GAPS.md), same unenforced-reference treatment as `material_lots.material_spec_version_id` from
migration 0027. `target_qty`/`tolerance_low`/`tolerance_high` are caller-supplied captured values -- no
target-calculation or tolerance-rule execution mode exists in this codebase (SG-089); the spec's own
`tolerance_rule_id` field is dropped in favor of the two explicit bound columns actually needed to
evaluate against.

`materials.critical` (added to the existing `materials` table) is the material half of DSP-FR-018's
conditional independence trigger ("required where the material or step is flagged critical") -- the step
half has no data source anywhere in the actually-used `batch_steps` -> `recipe_steps` path (only the
disconnected `recipe_master.gxp_recipe_step.is_critical` has one), and the conditional-independence
enforcement itself is deferred (SG-090); this flag is captured for a future pass.

Real gaps NOT built this pass (see docs/generated/18_SPEC_GAPS.md, new entries SG-086..SG-091): the
project-wide unenforced `reason_required` column (SG-086, only this document's own new rows and the one
Document 20 row I own get it wired up); signing the `POST /dispensing/v1/orders` create operation itself
(SG-087 -- no established pattern in this codebase for challenge-binding a signature to a record that
doesn't exist yet; built unsigned/RBAC-gated instead); balance/Edge device adapter, environment-monitoring,
potency/assay-rule execution (SG-088, WP-06 not built); DSP-FR-018's conditional independence and the
missing step-critical data source (SG-090); label-print connector, line/booth clearance entity, genealogy
wiring (SG-091).

Append-only-vs-mutable privilege split decided per table against the actual command code in
app/modules/material/commands.py: `weighing_readings` is genuinely append-only (every write path is an
INSERT; no command in this pass updates or deletes an existing reading row, matching DSP-FR-014's "original
overweight reading retained" rule) -- SELECT/INSERT/TRUNCATE only, same discipline as
`inventory_transactions` (migration 0028). `dispensing_orders`, `dispensing_sources`, `weighing_sessions`
and `dispensed_containers` all have fields mutated in place by later commands (state transitions, actual
quantities, session end/final-net, label print count) -- all four get UPDATE too. `materials` already has
schema-wide UPDATE from migration 0004 (materials_privilege_lockdown), so its 1 new column needs no
additional grant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '2c6a9e4f1b7d'
down_revision: Union[str, Sequence[str], None] = '5d9f3e7a1c4b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.add_column(
        'materials',
        sa.Column('critical', sa.Boolean(), nullable=False, server_default=sa.false()),
        schema='materials',
    )

    op.create_table(
        'dispensing_orders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('batch_step_id', sa.UUID(), nullable=True),
        sa.Column('material_id', sa.UUID(), nullable=False),
        sa.Column('material_spec_version_id', sa.UUID(), nullable=True),
        sa.Column('target_qty', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('target_uom', sa.String(length=40), nullable=False),
        sa.Column('tolerance_low', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('tolerance_high', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='created'),
        sa.Column('performed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('requested_by_user_id', sa.UUID(), nullable=False),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['material_id'], ['materials.materials.id']),
        sa.ForeignKeyConstraint(['performed_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('target_qty > 0', name='ck_dispensing_orders_target_qty_positive'),
        sa.CheckConstraint('tolerance_low <= tolerance_high', name='ck_dispensing_orders_tolerance_order'),
        schema='materials',
    )

    op.create_table(
        'dispensing_sources',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('dispensing_order_id', sa.UUID(), nullable=False),
        sa.Column('material_lot_id', sa.UUID(), nullable=False),
        sa.Column('container_id', sa.UUID(), nullable=True),
        sa.Column('reservation_id', sa.UUID(), nullable=True),
        sa.Column('reserved_quantity', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('actual_taken_quantity', sa.Numeric(precision=24, scale=8), nullable=True),
        sa.Column('eligibility_snapshot', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['dispensing_order_id'], ['materials.dispensing_orders.id']),
        sa.ForeignKeyConstraint(['material_lot_id'], ['materials.material_lots.id']),
        sa.ForeignKeyConstraint(['container_id'], ['materials.material_containers.id']),
        sa.ForeignKeyConstraint(['reservation_id'], ['materials.inventory_reservations.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='materials',
    )

    op.create_table(
        'weighing_sessions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('dispensing_order_id', sa.UUID(), nullable=False),
        sa.Column('operator_user_id', sa.UUID(), nullable=False),
        sa.Column('booth_location_id', sa.UUID(), nullable=True),
        sa.Column('tare_method', sa.String(length=40), nullable=True),
        sa.Column('tare_value', sa.Numeric(precision=24, scale=8), nullable=True),
        sa.Column('started_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('ended_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('final_accepted_net', sa.Numeric(precision=24, scale=8), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.ForeignKeyConstraint(['dispensing_order_id'], ['materials.dispensing_orders.id']),
        sa.ForeignKeyConstraint(['operator_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['booth_location_id'], ['materials.warehouse_locations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('dispensing_order_id'),
        schema='materials',
    )

    op.create_table(
        'weighing_readings',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('weighing_session_id', sa.UUID(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('reading_value', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('uom', sa.String(length=40), nullable=False),
        sa.Column('stable', sa.Boolean(), nullable=False),
        sa.Column('source', sa.String(length=20), nullable=False),
        sa.Column('manual_reason', sa.String(length=500), nullable=True),
        sa.Column('device_id', sa.String(length=100), nullable=True),
        sa.Column('recorded_by_user_id', sa.UUID(), nullable=False),
        sa.Column('recorded_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('accepted', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.ForeignKeyConstraint(['weighing_session_id'], ['materials.weighing_sessions.id']),
        sa.ForeignKeyConstraint(['recorded_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('reading_value >= 0', name='ck_weighing_readings_value_non_negative'),
        schema='materials',
    )

    op.create_table(
        'dispensed_containers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('material_id', sa.UUID(), nullable=False),
        sa.Column('dispensing_order_id', sa.UUID(), nullable=False),
        sa.Column('container_code', sa.String(length=120), nullable=False),
        sa.Column('actual_quantity', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('uom', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('label_print_count', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['material_id'], ['materials.materials.id']),
        sa.ForeignKeyConstraint(['dispensing_order_id'], ['materials.dispensing_orders.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('container_code'),
        schema='materials',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON materials.dispensing_orders TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON materials.dispensing_sources TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON materials.weighing_sessions TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON materials.weighing_readings TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON materials.dispensed_containers TO {APP_ROLE}")


def downgrade() -> None:
    for table in (
        'dispensed_containers', 'weighing_readings', 'weighing_sessions',
        'dispensing_sources', 'dispensing_orders',
    ):
        op.execute(f"REVOKE ALL ON materials.{table} FROM {APP_ROLE}")
        op.drop_table(table, schema='materials')

    op.drop_column('materials', 'critical', schema='materials')
