"""0061_machine_integration_mapping_pin_historian_ref

Revision ID: 2927a9a503a9
Revises: 5eb949131d37
Create Date: 2026-08-31 00:00:00.000000

Document 47 (SPEC-EDGE-005) -- SG-127/SG-129 follow-up closure. Three nullable columns, all additive to
already-owned `machine_integration` tables; no existing row is rewritten (AG-08).

- `machine_integration.batch_contexts.mapping_id` (FK to `machine_integration.signal_mappings`): MAP-FR-027
  -- the SignalMapping version `ingest_machine_evidence()` first pins for this OPEN context, reused for
  every subsequent call against it even if a newer version is released mid-batch ("open batches keep
  issued mapping version").
- `machine_integration.cycle_evidence_manifests.historian_instance_ref` (MAP-FR-024) and
  `.aggregation_rule_ref` (MAP-FR-011): captured references only, same "captured, unenforced" precedent as
  the table's existing `raw_evidence_ref` -- Document 47 §9 places the actual aggregation rule/query filter
  with the historian's own query, an external system this codebase does not have.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = '2927a9a503a9'
down_revision: Union[str, Sequence[str], None] = '5eb949131d37'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        'batch_contexts',
        sa.Column('mapping_id', sa.UUID(), nullable=True),
        schema='machine_integration',
    )
    op.create_foreign_key(
        'fk_batch_contexts_mapping', 'batch_contexts', 'signal_mappings',
        ['mapping_id'], ['id'], source_schema='machine_integration', referent_schema='machine_integration',
    )

    op.add_column(
        'cycle_evidence_manifests',
        sa.Column('historian_instance_ref', sa.String(length=200), nullable=True),
        schema='machine_integration',
    )
    op.add_column(
        'cycle_evidence_manifests',
        sa.Column('aggregation_rule_ref', sa.String(length=200), nullable=True),
        schema='machine_integration',
    )


def downgrade() -> None:
    op.drop_column('cycle_evidence_manifests', 'aggregation_rule_ref', schema='machine_integration')
    op.drop_column('cycle_evidence_manifests', 'historian_instance_ref', schema='machine_integration')

    op.drop_constraint('fk_batch_contexts_mapping', 'batch_contexts', schema='machine_integration', type_='foreignkey')
    op.drop_column('batch_contexts', 'mapping_id', schema='machine_integration')
