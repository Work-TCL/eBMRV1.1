"""0027_material_receipt_quality_status_schema

Revision ID: 35fca517ebb6
Revises: 4c8e2a6f1d9b
Create Date: 2026-08-24 00:00:00.000000

Document 19 (SPEC-MAT-002A) -- Material Receipt, Quarantine & Quality Status. Extends the already-built
`materials` module (owner service confirmed by docs/generated/04_DATA_MODEL_CATALOGUE.md for all 5
entities): `material_receipt` (DDL-ready), `material_lot` extensions (DDL-ready columns this document
adds), `material_container`/`sampling_order`/`material_quality_disposition` (prose-only field lists, typed
as an ordinary engineering decision -- SG-045's precedent).

`material_lot.material_spec_version_id` carries no FK constraint -- no "material specification version"
entity exists anywhere in this codebase (SG-057); same unenforced-reference treatment already used for
`qc.QcTestDefinition.method_version`.

Real gaps NOT built this pass (see docs/generated/18_SPEC_GAPS.md, new entries this document adds):
RCV-FR-001's PO/transfer-expectation entity (SG-057/058), RCV-FR-005's material-specific approved-source
matrix (SG-057), RCV-FR-010's UOM conversion engine, RCV-FR-014/021's real edge/equipment integration
(WP-06, not built), RCV-FR-016's warehouse/location master (Document 20, not yet built), RCV-FR-023/024/
025's material-scoped QC test specification (SG-057/SG-063), RCV-FR-031's ERP reconciliation sync (no
WP-07 module exists). RCV-FR-028 (conditional/under-deviation use) is deliberately not implemented -- the
spec's own default is disabled.

Append-only-vs-mutable privilege split decided per table against the actual command code in
app/modules/material/commands.py: `material_quality_disposition` is genuinely append-only (every write
path is an INSERT; no command in this pass updates an existing disposition row) -- SELECT/INSERT/TRUNCATE
only, same discipline as `material_lot_dispositions` (migration 0003) and `oos_investigation_activity`
(migration 0025). `material_receipt`, `material_container` and `sampling_order` all have fields mutated in
place by later commands (`examine_receipt`, `collect_sample`, disposition partial-container overrides) --
all three get UPDATE too. `material_lots` already has schema-wide UPDATE from migration 0004
(materials_privilege_lockdown), so its 5 new columns need no additional grant.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '35fca517ebb6'
down_revision: Union[str, Sequence[str], None] = '4c8e2a6f1d9b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

APP_ROLE = "ebmr_new_gxp_app"


def upgrade() -> None:
    op.create_table(
        'material_receipts',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('site_id', sa.UUID(), nullable=False),
        sa.Column('receipt_number', sa.String(length=120), nullable=False),
        sa.Column('po_reference', sa.String(length=160), nullable=True),
        sa.Column('material_id', sa.UUID(), nullable=False),
        sa.Column('supplier_id', sa.UUID(), nullable=True),
        sa.Column('manufacturer_id', sa.UUID(), nullable=True),
        sa.Column('supplier_lot', sa.String(length=200), nullable=True),
        sa.Column('manufacturer_lot', sa.String(length=200), nullable=True),
        sa.Column('carrier_reference', sa.String(length=160), nullable=True),
        sa.Column('received_gross_quantity', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('received_net_quantity', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('accepted_quantity', sa.Numeric(precision=18, scale=6), nullable=True),
        sa.Column('uom', sa.String(length=20), nullable=False),
        sa.Column('manufacture_date', sa.Date(), nullable=True),
        sa.Column('expiry_date', sa.Date(), nullable=True),
        sa.Column('retest_date', sa.Date(), nullable=True),
        sa.Column('shipment_condition_status', sa.String(length=40), nullable=True),
        sa.Column('coa_vault_object_id', sa.UUID(), nullable=True),
        sa.Column('coa_document_hash', sa.String(length=128), nullable=True),
        sa.Column('receiver_subject_id', sa.UUID(), nullable=False),
        sa.Column('received_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('state', sa.String(length=40), nullable=False, server_default='received'),
        sa.Column('labeling_ok', sa.Boolean(), nullable=True),
        sa.Column('damage_observed', sa.Boolean(), nullable=True),
        sa.Column('seal_broken', sa.Boolean(), nullable=True),
        sa.Column('contamination_observed', sa.Boolean(), nullable=True),
        sa.Column('examination_notes', sa.String(length=2000), nullable=True),
        sa.Column('examined_by_user_id', sa.UUID(), nullable=True),
        sa.Column('examined_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('discrepancy_type', sa.String(length=60), nullable=True),
        sa.Column('discrepancy_reason', sa.String(length=2000), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['site_id'], ['iam.sites.id']),
        sa.ForeignKeyConstraint(['material_id'], ['materials.materials.id']),
        sa.ForeignKeyConstraint(['supplier_id'], ['ebmr.supplier.id']),
        sa.ForeignKeyConstraint(['manufacturer_id'], ['ebmr.supplier.id']),
        sa.ForeignKeyConstraint(['coa_vault_object_id'], ['vault.gxp_vault_object.object_id']),
        sa.ForeignKeyConstraint(['receiver_subject_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['examined_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('site_id', 'receipt_number'),
        schema='materials',
    )

    op.create_table(
        'material_containers',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('material_lot_id', sa.UUID(), nullable=False),
        sa.Column('container_code', sa.String(length=120), nullable=False),
        sa.Column('received_quantity', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('current_quantity', sa.Numeric(precision=18, scale=6), nullable=False),
        sa.Column('uom', sa.String(length=20), nullable=False),
        sa.Column('location_zone', sa.String(length=160), nullable=True),
        sa.Column('quality_status_override', sa.String(length=40), nullable=True),
        sa.Column('sampled', sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column('seal_status', sa.String(length=40), nullable=False, server_default='intact'),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['material_lot_id'], ['materials.material_lots.id']),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('material_lot_id', 'container_code'),
        schema='materials',
    )

    op.create_table(
        'sampling_orders',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('material_lot_id', sa.UUID(), nullable=False),
        sa.Column('sampling_plan_ref', sa.String(length=160), nullable=True),
        sa.Column('selected_container_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
        sa.Column('sample_quantities', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('assigned_sampler_user_id', sa.UUID(), nullable=False),
        sa.Column('status', sa.String(length=40), nullable=False, server_default='requested'),
        sa.Column('aseptic_evidence_ref', sa.String(length=200), nullable=True),
        sa.Column('qc_sample_id', sa.UUID(), nullable=True),
        sa.Column('version', sa.BigInteger(), nullable=False, server_default='1'),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['material_lot_id'], ['materials.material_lots.id']),
        sa.ForeignKeyConstraint(['assigned_sampler_user_id'], ['iam.users.id']),
        sa.ForeignKeyConstraint(['qc_sample_id'], ['ebmr.qc_sample.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='materials',
    )

    op.create_table(
        'material_quality_dispositions',
        sa.Column('id', sa.UUID(), nullable=False),
        sa.Column('material_lot_id', sa.UUID(), nullable=False),
        sa.Column('container_ids', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('decision', sa.String(length=20), nullable=False),
        sa.Column('evidence_refs', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column('reason', sa.String(length=2000), nullable=True),
        sa.Column('signature_id', sa.UUID(), nullable=True),
        sa.Column('effective_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.Column('disposed_by_user_id', sa.UUID(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['material_lot_id'], ['materials.material_lots.id']),
        sa.ForeignKeyConstraint(['disposed_by_user_id'], ['iam.users.id']),
        sa.PrimaryKeyConstraint('id'),
        schema='materials',
    )

    op.add_column('material_lots', sa.Column('material_spec_version_id', sa.UUID(), nullable=True), schema='materials')
    op.add_column('material_lots', sa.Column('receipt_id', sa.UUID(), nullable=True), schema='materials')
    op.add_column('material_lots', sa.Column('manufacture_date', sa.Date(), nullable=True), schema='materials')
    op.add_column('material_lots', sa.Column('released_at', sa.DateTime(timezone=True), nullable=True), schema='materials')
    op.add_column('material_lots', sa.Column('release_signature_id', sa.UUID(), nullable=True), schema='materials')
    op.create_foreign_key(
        'fk_material_lots_receipt', 'material_lots', 'material_receipts', ['receipt_id'], ['id'],
        source_schema='materials', referent_schema='materials',
    )

    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON materials.material_receipts TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON materials.material_containers TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE, TRUNCATE ON materials.sampling_orders TO {APP_ROLE}")
    op.execute(f"GRANT SELECT, INSERT, TRUNCATE ON materials.material_quality_dispositions TO {APP_ROLE}")


def downgrade() -> None:
    op.drop_constraint('fk_material_lots_receipt', 'material_lots', schema='materials', type_='foreignkey')
    op.drop_column('material_lots', 'release_signature_id', schema='materials')
    op.drop_column('material_lots', 'released_at', schema='materials')
    op.drop_column('material_lots', 'manufacture_date', schema='materials')
    op.drop_column('material_lots', 'receipt_id', schema='materials')
    op.drop_column('material_lots', 'material_spec_version_id', schema='materials')

    for table in ('material_quality_dispositions', 'sampling_orders', 'material_containers', 'material_receipts'):
        op.execute(f"REVOKE ALL ON materials.{table} FROM {APP_ROLE}")
        op.drop_table(table, schema='materials')
