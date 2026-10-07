"""0136_phase6_receipt_fields_provider_refs

Revision ID: e3a5c7f9b1d6
Revises: d8f0a2c4e6b8
Create Date: 2026-10-05 00:00:00.000000

Client gap-analysis Phase 6: (1) splits `material_receipts.damage_observed` into
`shipping_damage_observed`/`container_damage_observed` -- the old column stays and is now derived
server-side as their OR (MIG-FR-004 expand step, no drop this release); (2) adds an optional
`provider_supplier_id` FK on `equipment_calibrations` so an external calibration can reference a known
Supplier (role_type can now be "service_provider") instead of only free-text `provider_name`, which is
kept for providers not yet onboarded as a Supplier record; (3) adds optional `external_provider_id` FK +
`external_report_hash` on `qc_test_order` so an external-lab test can record who performed it and a hash
of the report relied upon. All columns nullable/additive -- no backfill needed.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = 'e3a5c7f9b1d6'
down_revision: Union[str, Sequence[str], None] = 'd8f0a2c4e6b8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'material_receipts',
        sa.Column('shipping_damage_observed', sa.Boolean(), nullable=True),
        schema='materials',
    )
    op.add_column(
        'material_receipts',
        sa.Column('container_damage_observed', sa.Boolean(), nullable=True),
        schema='materials',
    )
    op.add_column(
        'equipment_calibrations',
        sa.Column('provider_supplier_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='equipment',
    )
    op.create_foreign_key(
        'fk_equipment_calibrations_provider_supplier',
        'equipment_calibrations', 'supplier',
        ['provider_supplier_id'], ['id'],
        source_schema='equipment', referent_schema='ebmr',
    )
    op.add_column(
        'qc_test_order',
        sa.Column('external_provider_id', postgresql.UUID(as_uuid=True), nullable=True),
        schema='ebmr',
    )
    op.add_column(
        'qc_test_order',
        sa.Column('external_report_hash', sa.String(length=128), nullable=True),
        schema='ebmr',
    )
    op.create_foreign_key(
        'fk_qc_test_order_external_provider',
        'qc_test_order', 'supplier',
        ['external_provider_id'], ['id'],
        source_schema='ebmr', referent_schema='ebmr',
    )


def downgrade() -> None:
    op.drop_constraint('fk_qc_test_order_external_provider', 'qc_test_order', schema='ebmr', type_='foreignkey')
    op.drop_column('qc_test_order', 'external_report_hash', schema='ebmr')
    op.drop_column('qc_test_order', 'external_provider_id', schema='ebmr')
    op.drop_constraint(
        'fk_equipment_calibrations_provider_supplier', 'equipment_calibrations', schema='equipment', type_='foreignkey'
    )
    op.drop_column('equipment_calibrations', 'provider_supplier_id', schema='equipment')
    op.drop_column('material_receipts', 'container_damage_observed', schema='materials')
    op.drop_column('material_receipts', 'shipping_damage_observed', schema='materials')
