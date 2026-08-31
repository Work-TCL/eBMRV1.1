"""0031_material_consumption_return_adjustment_destruction_reconciliation_schema

Revision ID: bb7e61b309ce
Revises: 46aa9ec6eeb6
Create Date: 2026-08-25 00:00:00.000000

Document 22 (SPEC-MAT-002D) -- Material Consumption, Return, Adjustment, Destruction & Reconciliation.
Extends the already-built `materials` module (owner service confirmed by
docs/generated/04_DATA_MODEL_CATALOGUE.md / 05_DATABASE_OWNERSHIP_MATRIX.md for all 5 entities):
`material_consumptions`, `material_returns`, `inventory_adjustment_requests`, `destruction_records`,
`material_reconciliations`, plus one new `dispensed_containers.remaining_quantity` column (CON-FR-004 --
Document 21 never tracked post-dispense balance on that row; this session is the first consumer).

No `tenant_id` column on any new table (ADR-0006, single-organization platform -- same deviation as every
other additive migration this project). All quantity columns use the Document 20/21 ledger family's
numeric(24,8), matching `inventory_transactions.quantity`/`dispensed_containers.remaining_quantity` (the
new column) rather than the older Document 18/19 numeric(18,6) container/lot fields this migration does
not touch.

`material_reconciliations.linked_deviation_id` FKs to `qms.deviation_record` -- the first cross-schema FK
from `materials` into `qms` in this codebase (AG-06's owning-command call from
`evaluate_material_reconciliation` into `qms.commands.create_deviation` is the write path; this FK is
read-only referential integrity on top of that).

Real gaps NOT built this pass (see docs/generated/18_SPEC_GAPS.md, new entry SG-098): CON-FR-003's
automatic/validated-integration consumption source (no edge/rules-engine source, WP-06 not built);
CON-FR-021's released Document 08/17 tolerance/rounding rule (Document 17 not built -- `tolerance_value`
is caller-supplied captured input, same treatment SG-094 established for dispensing tolerance);
CON-FR-022/028's auto-deviation severity/owner and the batch-completion-gate block (cross-module, not
wired into app/modules/batch/commands.py this pass); CON-FR-025/026's ERP posting/discrepancy integration
(WP-07 not built, same root cause as SG-077/082).

Append-only-vs-mutable privilege split decided per table against the actual command code in
app/modules/material/commands.py: `material_consumptions` and `material_returns` are genuinely append-only
(every write path is an INSERT; CON-FR-023/024 forbid editing a transaction, correction is reversal +
new record) -- SELECT/INSERT/TRUNCATE only, same discipline as `inventory_transactions` (migration 0028).
`inventory_adjustment_requests` and `destruction_records` are mutable aggregates (status/signature fields
transition in place on approve/execute) -- both get UPDATE. `material_reconciliations` is append-only by
design (CON-FR-023's correction pattern is "insert a new row per re-evaluation, never edit") -- SELECT/
INSERT/TRUNCATE only. `dispensed_containers` already has schema-wide UPDATE from migration 0029
(dispensing_weighing_schema), so its 1 new column needs no additional grant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'bb7e61b309ce'
down_revision: Union[str, Sequence[str], None] = '46aa9ec6eeb6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.add_column(
        'dispensed_containers',
        sa.Column('remaining_quantity', sa.Numeric(precision=24, scale=8), nullable=False, server_default='0'),
        schema='materials',
    )
    op.execute("UPDATE materials.dispensed_containers SET remaining_quantity = actual_quantity")

    op.create_table(
        'material_consumptions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('step_id', sa.UUID(), nullable=True),
        sa.Column('dispensed_container_id', sa.UUID(), nullable=False),
        sa.Column('material_lot_id', sa.UUID(), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('uom', sa.String(length=40), nullable=False),
        sa.Column('source_type', sa.String(length=40), nullable=False, server_default='manual'),
        sa.Column('source_id', sa.String(length=255), nullable=True),
        sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('transaction_id', sa.UUID(), nullable=False),
        sa.Column('recorded_by_user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['step_id'], ['ebmr.batch_steps.id']),
        sa.ForeignKeyConstraint(['dispensed_container_id'], ['materials.dispensed_containers.id']),
        sa.ForeignKeyConstraint(['material_lot_id'], ['materials.material_lots.id']),
        sa.ForeignKeyConstraint(['transaction_id'], ['materials.inventory_transactions.id']),
        sa.ForeignKeyConstraint(['recorded_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('quantity > 0', name='ck_material_consumptions_quantity_positive'),
        schema='materials',
    )
    op.create_index(
        'ix_material_consumptions_batch', 'material_consumptions', ['batch_id'], schema='materials',
    )
    op.create_index(
        'ix_material_consumptions_dispensed_container', 'material_consumptions', ['dispensed_container_id'],
        schema='materials',
    )

    op.create_table(
        'material_returns',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('dispensed_container_id', sa.UUID(), nullable=False),
        sa.Column('material_lot_id', sa.UUID(), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('uom', sa.String(length=40), nullable=False),
        sa.Column('container_condition', sa.String(length=60), nullable=False),
        sa.Column('storage_exposure_evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('target_location_id', sa.UUID(), nullable=True),
        sa.Column('resulting_status', sa.String(length=20), nullable=False),
        sa.Column('transaction_id', sa.UUID(), nullable=False),
        sa.Column('returned_by_user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['dispensed_container_id'], ['materials.dispensed_containers.id']),
        sa.ForeignKeyConstraint(['material_lot_id'], ['materials.material_lots.id']),
        sa.ForeignKeyConstraint(['target_location_id'], ['materials.warehouse_locations.id']),
        sa.ForeignKeyConstraint(['transaction_id'], ['materials.inventory_transactions.id']),
        sa.ForeignKeyConstraint(['returned_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('quantity > 0', name='ck_material_returns_quantity_positive'),
        schema='materials',
    )
    op.create_index(
        'ix_material_returns_batch', 'material_returns', ['batch_id'], schema='materials',
    )

    op.create_table(
        'inventory_adjustment_requests',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('material_lot_id', sa.UUID(), nullable=False),
        sa.Column('container_id', sa.UUID(), nullable=True),
        sa.Column('location_id', sa.UUID(), nullable=False),
        sa.Column('expected_quantity', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('observed_quantity', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('variance', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('reason', sa.String(length=2000), nullable=False),
        sa.Column('evidence', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='requested'),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('resulting_transaction_id', sa.UUID(), nullable=True),
        sa.Column('requested_by_user_id', sa.UUID(), nullable=False),
        sa.Column('approved_by_user_id', sa.UUID(), nullable=True),
        sa.Column('approved_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['material_lot_id'], ['materials.material_lots.id']),
        sa.ForeignKeyConstraint(['container_id'], ['materials.material_containers.id']),
        sa.ForeignKeyConstraint(['location_id'], ['materials.warehouse_locations.id']),
        sa.ForeignKeyConstraint(['resulting_transaction_id'], ['materials.inventory_transactions.id']),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['approved_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='materials',
    )

    op.create_table(
        'destruction_records',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('material_lot_id', sa.UUID(), nullable=True),
        sa.Column('container_id', sa.UUID(), nullable=True),
        sa.Column('dispensed_container_id', sa.UUID(), nullable=True),
        sa.Column('quantity', sa.Numeric(precision=24, scale=8), nullable=False),
        sa.Column('uom', sa.String(length=40), nullable=False),
        sa.Column('reason', sa.String(length=2000), nullable=False),
        sa.Column('method', sa.String(length=200), nullable=True),
        sa.Column('vendor_name', sa.String(length=200), nullable=True),
        sa.Column('manifest_reference', sa.String(length=200), nullable=True),
        sa.Column('certificate_vault_object_id', sa.UUID(), nullable=True),
        sa.Column('witnesses', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('status', sa.String(length=20), nullable=False, server_default='requested'),
        sa.Column('transaction_id', sa.UUID(), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('requested_by_user_id', sa.UUID(), nullable=False),
        sa.Column('executed_by_user_id', sa.UUID(), nullable=True),
        sa.Column('executed_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['material_lot_id'], ['materials.material_lots.id']),
        sa.ForeignKeyConstraint(['container_id'], ['materials.material_containers.id']),
        sa.ForeignKeyConstraint(['dispensed_container_id'], ['materials.dispensed_containers.id']),
        sa.ForeignKeyConstraint(['certificate_vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.ForeignKeyConstraint(['transaction_id'], ['materials.inventory_transactions.id']),
        sa.ForeignKeyConstraint(['requested_by_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['executed_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.CheckConstraint('quantity > 0', name='ck_destruction_records_quantity_positive'),
        schema='materials',
    )

    op.create_table(
        'material_reconciliations',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('batch_id', sa.UUID(), nullable=False),
        sa.Column('material_id', sa.UUID(), nullable=True),
        sa.Column('dispensed_total', sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column('consumed_total', sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column('returned_total', sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column('sampled_total', sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column('rejected_total', sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column('destroyed_total', sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column('approved_loss_total', sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column('unexplained_variance', sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column('tolerance_value', sa.Numeric(precision=24, scale=6), nullable=False),
        sa.Column('outcome', sa.String(length=20), nullable=False),
        sa.Column('calculation_rule_version', sa.String(length=40), nullable=False, server_default='CC-4-v1'),
        sa.Column('linked_deviation_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('evaluated_by_user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['batch_id'], ['ebmr.batches.id']),
        sa.ForeignKeyConstraint(['material_id'], ['materials.materials.id']),
        sa.ForeignKeyConstraint(['linked_deviation_id'], ['qms.deviation_record.id']),
        sa.ForeignKeyConstraint(['evaluated_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='materials',
    )
    op.create_index(
        'ix_material_reconciliations_batch', 'material_reconciliations', ['batch_id', 'version'],
        schema='materials',
    )

    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON materials.material_consumptions TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON materials.material_returns TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON materials.inventory_adjustment_requests TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON materials.destruction_records TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON materials.material_reconciliations TO {APP_ROLE}")


def downgrade() -> None:
    op.execute(f"REVOKE ALL ON materials.material_reconciliations FROM {APP_ROLE}")
    op.drop_index('ix_material_reconciliations_batch', table_name='material_reconciliations', schema='materials')
    op.drop_table('material_reconciliations', schema='materials')

    op.execute(f"REVOKE ALL ON materials.destruction_records FROM {APP_ROLE}")
    op.drop_table('destruction_records', schema='materials')

    op.execute(f"REVOKE ALL ON materials.inventory_adjustment_requests FROM {APP_ROLE}")
    op.drop_table('inventory_adjustment_requests', schema='materials')

    op.execute(f"REVOKE ALL ON materials.material_returns FROM {APP_ROLE}")
    op.drop_index('ix_material_returns_batch', table_name='material_returns', schema='materials')
    op.drop_table('material_returns', schema='materials')

    op.execute(f"REVOKE ALL ON materials.material_consumptions FROM {APP_ROLE}")
    op.drop_index('ix_material_consumptions_dispensed_container', table_name='material_consumptions', schema='materials')
    op.drop_index('ix_material_consumptions_batch', table_name='material_consumptions', schema='materials')
    op.drop_table('material_consumptions', schema='materials')

    op.drop_column('dispensed_containers', 'remaining_quantity', schema='materials')
