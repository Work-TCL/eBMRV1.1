"""0060_em_sterilization_aseptic_gap_followup_fields

Revision ID: 5eb949131d37
Revises: e94a9d0e22d5
Create Date: 2026-08-30 00:00:00.000000

Documents 41/42/40 (SPEC-EQP-004/005/003) -- SG-115/116/117 follow-up closure. All columns nullable and
additive to already-owned tables; no existing row is rewritten (AG-08).

- `equipment.em_samples_or_readings`: `media_reagent_ref` (EM-FR-007), `incubation_conditions` (EM-FR-009)
  -- both captured JSONB, not enumerated/enforced, same "captured, not enumerated" precedent as
  `equipment_areas.area_type`.
- `equipment.process_cycles`: `indicator_results` (STR-FR-011, captured JSONB) and
  `reprocessing_authorization_ref` (STR-FR-026, captured JSONB reference -- structurally required by
  `create_process_cycle()` when reprocessing a previously FAILED load, not content-validated).
- `equipment.aseptic_operations`: `media_fill_reference` (ASP-FR-018, captured JSONB) and
  `qc_test_order_id`/`qc_result_id` (ASP-FR-019, FK to `ebmr.qc_test_order`/`ebmr.qc_result` --
  existence-checked at `complete_operation()`, not content-validated).
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision: str = '5eb949131d37'
down_revision: Union[str, Sequence[str], None] = 'e94a9d0e22d5'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'em_samples_or_readings',
        sa.Column('media_reagent_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema='equipment',
    )
    op.add_column(
        'em_samples_or_readings',
        sa.Column('incubation_conditions', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema='equipment',
    )

    op.add_column(
        'process_cycles',
        sa.Column('indicator_results', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema='equipment',
    )
    op.add_column(
        'process_cycles',
        sa.Column('reprocessing_authorization_ref', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema='equipment',
    )

    op.add_column(
        'aseptic_operations',
        sa.Column('media_fill_reference', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        schema='equipment',
    )
    op.add_column(
        'aseptic_operations',
        sa.Column('qc_test_order_id', sa.UUID(), nullable=True),
        schema='equipment',
    )
    op.add_column(
        'aseptic_operations',
        sa.Column('qc_result_id', sa.UUID(), nullable=True),
        schema='equipment',
    )
    op.create_foreign_key(
        'fk_aseptic_operations_qc_test_order', 'aseptic_operations', 'qc_test_order',
        ['qc_test_order_id'], ['id'], source_schema='equipment', referent_schema='ebmr',
    )
    op.create_foreign_key(
        'fk_aseptic_operations_qc_result', 'aseptic_operations', 'qc_result',
        ['qc_result_id'], ['id'], source_schema='equipment', referent_schema='ebmr',
    )


def downgrade() -> None:
    op.drop_constraint('fk_aseptic_operations_qc_result', 'aseptic_operations', schema='equipment', type_='foreignkey')
    op.drop_constraint('fk_aseptic_operations_qc_test_order', 'aseptic_operations', schema='equipment', type_='foreignkey')
    op.drop_column('aseptic_operations', 'qc_result_id', schema='equipment')
    op.drop_column('aseptic_operations', 'qc_test_order_id', schema='equipment')
    op.drop_column('aseptic_operations', 'media_fill_reference', schema='equipment')

    op.drop_column('process_cycles', 'reprocessing_authorization_ref', schema='equipment')
    op.drop_column('process_cycles', 'indicator_results', schema='equipment')

    op.drop_column('em_samples_or_readings', 'incubation_conditions', schema='equipment')
    op.drop_column('em_samples_or_readings', 'media_reagent_ref', schema='equipment')
