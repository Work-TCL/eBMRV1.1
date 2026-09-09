"""0091_repair_verification_batch_mj_pfs_b_2601

Revision ID: f7a1c3e5b9d2
Revises: e5f7a9c1b3d6
Create Date: 2026-09-08 00:00:00.000000

Controlled repair (MIG-FR-005 / MIG-FR-026 / CLAUDE.md "no production DB fix outside a controlled
migration/repair mechanism"), project-owner-directed ("delete existing batch from batch-execution
page"). `MJ-PFS-B-2601` (`ebmr.gxp_batch` id `5ea45d46-5cb4-4464-af6b-40e4454d27bc`) was the live
end-to-end verification batch created while proving migration `0090`'s FK retarget actually works
(SG-149/SG-173) -- created, issued, started, one real DDCP constituent handoff and one real material
inventory reservation recorded against it. Verification-only, not part of any demo script.

Confirmed before writing this migration (full FK sweep against `ebmr.gxp_batch`/`gxp_batch_step`, same
method as migration `0090`): exactly 3 tables reference this batch/its steps --
`ddcp.constituent_handoff` (1 row), `materials.inventory_reservations` (1 row), `ebmr.gxp_batch_step`
(9 rows, this batch's own steps). Nothing else in the platform (packaging/qc/qa_review/release/
yield_reconciliation/device -- the other `gxp_batch` FK dependents) has a row against it.

Scope of deletion, children first: `ddcp.constituent_handoff` + `materials.inventory_reservations` ->
`ebmr.gxp_batch_step` -> `ebmr.gxp_batch`.

Deliberately NOT touched (AG-08 append-only, MIG-FR-013): `audit.audit_events`, `vault.gxp_vault_object`
(the batch's issue-time execution snapshot), `mutation.outbox_events`, `mutation.command_receipts`. The
audit trail still shows this batch being created/issued/started and now removed by this controlled
repair -- the correct, non-destructive record.

Idempotent: the `WHERE batch_number = ...` predicate is a no-op on any deployment that never created
this exact batch. Forward-only -- `downgrade()` cannot resurrect a disposed regulated row
(MIG-FR-005/MIG-FR-031); it is a documented no-op.
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'f7a1c3e5b9d2'
down_revision: Union[str, Sequence[str], None] = 'e5f7a9c1b3d6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

_BATCH_NUMBER = "MJ-PFS-B-2601"


def upgrade() -> None:
    batch = f"(SELECT id FROM ebmr.gxp_batch WHERE batch_number = '{_BATCH_NUMBER}')"
    steps = f"(SELECT id FROM ebmr.gxp_batch_step WHERE batch_id IN {batch})"
    op.execute(f"DELETE FROM ddcp.constituent_handoff WHERE batch_id IN {batch}")
    op.execute(f"DELETE FROM materials.inventory_reservations WHERE batch_id IN {batch}")
    op.execute(f"DELETE FROM ebmr.gxp_batch_step WHERE id IN {steps}")
    op.execute(f"DELETE FROM ebmr.gxp_batch WHERE batch_number = '{_BATCH_NUMBER}'")


def downgrade() -> None:
    """Forward-only repair — disposed regulated rows are not resurrected (MIG-FR-005 / MIG-FR-031)."""
