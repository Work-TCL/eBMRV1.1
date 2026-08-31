"""0028_inventory_warehouse_schema

Revision ID: 8f1c3d5a7b2e
Revises: 35fca517ebb6
Create Date: 2026-08-24 00:00:00.000000

Document 20 (SPEC-MAT-002B) -- Inventory, Lot/Container & Warehouse. Extends the already-built
`materials` module (owner service confirmed by docs/generated/04_DATA_MODEL_CATALOGUE.md /
05_DATABASE_OWNERSHIP_MATRIX.md for all 4 entities): `warehouse_location`, `inventory_transaction`,
`inventory_balance_projection`, `inventory_reservation` (all DDL-ready per the data-model catalogue), plus
three new `material_containers` columns for split/merge provenance (INV-FR-023/024).

No `tenant_id` column on any new table (ADR-0006, single-organization platform -- same deviation as every
other additive migration this project).

`inventory_transaction.quantity`/`inventory_balance_projection.on_hand`/`reserved`/`available`/
`inventory_reservation.quantity` use the spec's own explicit numeric(24,8) for this table family --
deliberately not this module's usual Numeric(18,6), which stays on the pre-existing
`material_lots`/`material_containers` quantity columns Document 18/19 already defined and which this
migration does not touch.

`warehouse_location` has no CRUD operation anywhere in Document 20's own 8-op API list (SG-081) --
master/reference data, seeded like `iam.sites`/`iam.organizations`, never created through the app.
`warehouse_location.environment_profile_id` carries no FK constraint -- no environment-profile entity
exists anywhere in this codebase (same unenforced-reference treatment as
`material_lots.material_spec_version_id` from migration 0027).

Real gaps NOT built this pass (see docs/generated/18_SPEC_GAPS.md, new entries SG-081..SG-085): the
warehouse_location CRUD API itself, barcode/scanner/environmental-monitoring/label-reprint/ERP integration
(WP-06/WP-07, not built), the FEFO/FIFO deviation-override path and material-spec-version-scoped
eligibility (SG-057 family), a cycle-count approval signature (no Document 106 row resolves one) and
physical-count freeze (no entity/operation in Document 20's own API list), and genealogy-module wiring for
split/merge/transfer provenance (cross-module integration, deferred).

Append-only-vs-mutable privilege split decided per table against the actual command code in
app/modules/material/commands.py: `inventory_transactions` is genuinely append-only (every write path is
an INSERT; no command in this pass updates or deletes an existing transaction row) -- SELECT/INSERT/
TRUNCATE only, same discipline as `material_quality_dispositions` (migration 0027). `warehouse_locations`,
`inventory_balance_projections` and `inventory_reservations` all have fields mutated in place by later
commands (balance updates, reservation status transitions) -- all three get UPDATE too.
`material_containers` already has schema-wide UPDATE from migration 0004
(materials_privilege_lockdown), so its 3 new columns need no additional grant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '8f1c3d5a7b2e'
down_revision: Union[str, Sequence[str], None] = '35fca517ebb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'warehouse_locations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('warehouse_code', sa.String(length=100), nullable=False),
        sa.Column('location_code', sa.String(length=120), nullable=False),
        sa.Column('zone_type', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='active'),
        sa.Column('environment_profile_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id', 'warehouse_code', 'location_code'),
        schema='materials',
    )

    op.create_table(
        'inventory_transactions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('material_lot_id', sa.UUID(), nullable=False),
        sa.Column('container_id', sa.UUID(), nullable=True),
        sa.Column('transaction_type', sa.String(length=50), nullable=False),
        sa.Column('quantity', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('uom', sa.String(length=40), nullable=False),
        sa.Column('from_location_id', sa.UUID(), nullable=True),
        sa.Column('to_location_id', sa.UUID(), nullable=True),
        sa.Column('reference_type', sa.String(length=60), nullable=True),
        sa.Column('reference_id', sa.UUID(), nullable=True),
        sa.Column('source_event_id', sa.UUID(), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('actor_type', sa.String(length=40), nullable=False, server_default='human'),
        sa.Column('actor_id', sa.String(length=255), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['material_lot_id'], ['materials.material_lots.id']),
        sa.ForeignKeyConstraint(['container_id'], ['materials.material_containers.id']),
        sa.ForeignKeyConstraint(['from_location_id'], ['materials.warehouse_locations.id']),
        sa.ForeignKeyConstraint(['to_location_id'], ['materials.warehouse_locations.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('quantity > 0', name='ck_inventory_transactions_quantity_positive'),
        schema='materials',
    )
    op.create_index(
        'ix_inventory_transactions_lot', 'inventory_transactions', ['material_lot_id', 'occurred_at'],
        schema='materials',
    )
    op.create_index(
        'ix_inventory_transactions_source_event', 'inventory_transactions', ['source_event_id'],
        unique=True, schema='materials', postgresql_where=sa.text('source_event_id IS NOT NULL'),
    )

    op.create_table(
        'inventory_balance_projections',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('material_lot_id', sa.UUID(), nullable=False),
        sa.Column('container_id', sa.UUID(), nullable=True),
        sa.Column('location_id', sa.UUID(), nullable=False),
        sa.Column('on_hand', sa.Numeric(precision=24, scale=8), nullable=False, server_default='0'),
        sa.Column('reserved', sa.Numeric(precision=24, scale=8), nullable=False, server_default='0'),
        sa.Column('available', sa.Numeric(precision=24, scale=8), nullable=False, server_default='0'),
        sa.Column('last_transaction_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['material_lot_id'], ['materials.material_lots.id']),
        sa.ForeignKeyConstraint(['container_id'], ['materials.material_containers.id']),
        sa.ForeignKeyConstraint(['location_id'], ['materials.warehouse_locations.id']),
        sa.ForeignKeyConstraint(['last_transaction_id'], ['materials.inventory_transactions.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('material_lot_id', 'container_id', 'location_id'),
        sa.CheckConstraint('on_hand >= 0', name='ck_inventory_balance_on_hand_non_negative'),
        sa.CheckConstraint('reserved >= 0', name='ck_inventory_balance_reserved_non_negative'),
        sa.CheckConstraint('available >= 0', name='ck_inventory_balance_available_non_negative'),
        schema='materials',
    )

    op.create_table(
        'inventory_reservations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('material_id', sa.UUID(), nullable=False),
        sa.Column('material_lot_id', sa.UUID(), nullable=True),
        sa.Column('container_id', sa.UUID(), nullable=True),
        sa.Column('location_id', sa.UUID(), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('uom', sa.String(length=20), nullable=False),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='active'),
        sa.Column('expiry_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('requested_by_user_id', sa.UUID(), nullable=False),
        sa.Column('released_by_user_id', sa.UUID(), nullable=True),
        sa.Column('released_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('release_signature_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['material_id'], ['materials.materials.id']),
        sa.ForeignKeyConstraint(['material_lot_id'], ['materials.material_lots.id']),
        sa.ForeignKeyConstraint(['container_id'], ['materials.material_containers.id']),
        sa.ForeignKeyConstraint(['location_id'], ['materials.warehouse_locations.id']),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['released_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('quantity > 0', name='ck_inventory_reservations_quantity_positive'),
        schema='materials',
    )

    op.add_column(
        'material_containers',
        sa.Column('parent_container_id', sa.UUID(), nullable=True),
        schema='materials',
    )
    op.add_column(
        'material_containers',
        sa.Column('source_container_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema='materials',
    )
    op.add_column(
        'material_containers',
        sa.Column('container_status', sa.String(length=20), nullable=False, server_default='active'),
        schema='materials',
    )
    op.create_foreign_key(
        'fk_material_containers_parent', 'material_containers', 'material_containers',
        ['parent_container_id'], ['id'], source_schema='materials', referent_schema='materials',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON materials.warehouse_locations TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON materials.inventory_transactions TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON materials.inventory_balance_projections TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON materials.inventory_reservations TO {APP_ROLE}")


def downgrade() -> None:
    op.drop_constraint('fk_material_containers_parent', 'material_containers', schema='materials', type_='foreignkey')
    op.drop_column('material_containers', 'container_status', schema='materials')
    op.drop_column('material_containers', 'source_container_ids', schema='materials')
    op.drop_column('material_containers', 'parent_container_id', schema='materials')

    for table in ('inventory_reservations', 'inventory_balance_projections'):
        op.execute(f"REVOKE ALL ON materials.{table} FROM {APP_ROLE}")
        op.drop_table(table, schema='materials')

    op.execute(f"REVOKE ALL ON materials.inventory_transactions FROM {APP_ROLE}")
    op.drop_index('ix_inventory_transactions_source_event', table_name='inventory_transactions', schema='materials')
    op.drop_index('ix_inventory_transactions_lot', table_name='inventory_transactions', schema='materials')
    op.drop_table('inventory_transactions', schema='materials')

    op.execute(f"REVOKE ALL ON materials.warehouse_locations FROM {APP_ROLE}")
    op.drop_table('warehouse_locations', schema='materials')
