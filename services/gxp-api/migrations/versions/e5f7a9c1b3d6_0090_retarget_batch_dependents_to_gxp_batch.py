"""0090_retarget_batch_dependents_to_gxp_batch

Revision ID: e5f7a9c1b3d6
Revises: a3f7c9e1d8b4
Create Date: 2026-09-08 00:00:00.000000

SG-149 / SG-173 (Document 11, AG-05) -- project-owner-directed cutover, chosen explicitly ("prefer
[Document 11's batch_execution] for batch", "database is not on demo and test mode... delete data for
existing batch"): `ebmr.batches` (legacy `app/modules/batch`) and `ebmr.gxp_batch`
(`app/modules/batch_execution`) were two disjoint, unreconciled authoritative stores for the same
regulated Batch entity. DDCP (11 columns), material (9), equipment (7) and machine_integration (5) --
32 columns total across 4 modules -- all FK'd `batch_id`/`batch_step_id` into the *scaffold* legacy
table (`ebmr.batches`/`ebmr.batch_steps`) instead of the approved `gxp_`-prefixed one every other
consumer (packaging/qc/qa_review/release/yield_reconciliation/device) already used. This migration
retargets all 32 to `ebmr.gxp_batch`/`ebmr.gxp_batch_step`, making `batch_execution` the single
authoritative Batch store every module in the platform now agrees on.

Confirmed before writing this migration (2026-09-08, live `ebmr_new_gxp` DB): every one of the 32
dependent columns is coupled only at the schema/FK level or through `.id`/`.site_id`/`.status` reads --
no dependent module reads `batch.product_id`/`batch.recipe_id` (fields that don't exist on `gxp_batch`),
so the retarget is safe at the code level too (paired application-code changes swap the Python import
from `app.modules.batch.models` to `app.modules.batch_execution.models` and the one `.status` -> `.state`
attribute rename in `ddcp/commands.py::get_readiness()` -- both state machines already share the string
values `"planned"`/`"issued"`/`"in_execution"`).

**Data deleted first, in FK-safe child-to-parent order** -- this is demo/code-testing data confirmed to
be the *only* rows on either side of the 32 relationships (checked every dependent table's row count
against these exact batch/step ids before writing this migration):
  - `ddcp.constituent_handoff` (3 rows, batch `BATCH-PFS-DEMO-001`)
  - `equipment.equipment_use_logs` (1 row), `materials.inventory_reservations` (1 row)
  - `ebmr.batch_steps` (6 rows), `ebmr.batches` (2 rows: `BATCH-PFS-DEMO-001`, `MJ-PFS-B-SMOKE-01`)
  - `ebmr.recipe_steps` (6), `ebmr.recipes` (2), `ebmr.products` (2) (`PFS-DEMO-PROD`, `MJ-PFS-40MG`) --
    the legacy Product/Recipe rows that existed solely to support these two legacy batches; nothing else
    in the platform reads `ebmr.products`/`ebmr.recipes` (SG-173: "nothing outside the product/recipe
    modules themselves has an FK into ebmr.products or ebmr.recipes").

Deliberately NOT touched (AG-08 append-only, MIG-FR-013): `audit.audit_events`, `vault.*`,
`mutation.outbox_events`, `mutation.command_receipts`. The audit trail still shows these rows being
created and now removed by this controlled repair.

**Legacy `app/modules/batch`/`product`/`recipe` code, routes and tables (`batches`, `batch_steps`,
`batch_reviews`, `batch_releases`, `products`, `recipes`, `recipe_steps`) are deliberately NOT dropped by
this migration** -- only their data and their *dependents'* FK targets. Removing the legacy module's own
schema/routes is a separate "contract" step (Document 100 expand -> migrate -> contract) left for a
follow-up pass once the frontend cutover (retiring `/batches`, `/batches/new`, `/batches/[id]`) is
verified working end-to-end against `gxp_batch`.

Forward-only: `downgrade()` cannot resurrect disposed regulated rows (MIG-FR-005/MIG-FR-031) and does not
attempt to; it only reverses the FK-constraint retarget (schema-only, safe either direction since both
tables are empty of cross-referencing rows at every point this migration runs).
"""
from typing import Sequence, Union

from alembic import op


revision: str = 'e5f7a9c1b3d6'
down_revision: Union[str, Sequence[str], None] = 'a3f7c9e1d8b4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# (schema, table, column, constraint_name) for every FK into ebmr.batches / ebmr.batch_steps that this
# migration retargets to ebmr.gxp_batch / ebmr.gxp_batch_step. Confirmed via pg_constraint against the
# live DB, 2026-09-08.
_BATCH_ID_FKS = [
    ("ddcp", "batch_evidence_manifest", "batch_id", "batch_evidence_manifest_batch_id_fkey"),
    ("ddcp", "constituent_handoff", "batch_id", "constituent_handoff_batch_id_fkey"),
    ("ddcp", "ddcp_process_operation", "batch_id", "ddcp_process_operation_batch_id_fkey"),
    ("ddcp", "ddcp_release_checkpoint", "batch_id", "ddcp_release_checkpoint_batch_id_fkey"),
    ("ddcp", "ddcp_unit_binding", "batch_id", "ddcp_unit_binding_batch_id_fkey"),
    ("ddcp", "device_assembly_record", "batch_id", "device_assembly_record_batch_id_fkey"),
    ("ddcp", "device_functional_test_link", "batch_id", "device_functional_test_link_batch_id_fkey"),
    ("ddcp", "drug_coating_usage_ledger", "batch_id", "drug_coating_usage_ledger_batch_id_fkey"),
    ("ddcp", "fill_operation", "batch_id", "fill_operation_batch_id_fkey"),
    ("ddcp", "production_count_ledger", "batch_id", "production_count_ledger_batch_id_fkey"),
    ("ddcp", "reusable_device_pairing", "batch_id", "reusable_device_pairing_batch_id_fkey"),
    ("equipment", "aseptic_operations", "batch_id", "aseptic_operations_batch_id_fkey"),
    ("equipment", "em_samples_or_readings", "batch_id", "em_samples_or_readings_batch_id_fkey"),
    ("equipment", "equipment_use_logs", "batch_id", "equipment_use_logs_batch_id_fkey"),
    ("equipment", "line_clearances", "next_batch_id", "line_clearances_next_batch_id_fkey"),
    ("equipment", "line_clearances", "previous_batch_id", "line_clearances_previous_batch_id_fkey"),
    ("equipment", "process_cycles", "batch_id", "process_cycles_batch_id_fkey"),
    ("equipment", "sterile_filter_uses", "batch_id", "sterile_filter_uses_batch_id_fkey"),
    ("machine_integration", "batch_contexts", "batch_id", "batch_contexts_batch_id_fkey"),
    ("machine_integration", "machine_command_requests", "batch_id", "machine_command_requests_batch_id_fkey"),
    ("materials", "dispensed_containers", "batch_id", "dispensed_containers_batch_id_fkey"),
    ("materials", "dispensing_orders", "batch_id", "dispensing_orders_batch_id_fkey"),
    ("materials", "inventory_reservations", "batch_id", "inventory_reservations_batch_id_fkey"),
    ("materials", "material_consumptions", "batch_id", "material_consumptions_batch_id_fkey"),
    ("materials", "material_issues", "batch_id", "material_issues_batch_id_fkey"),
    ("materials", "material_reconciliations", "batch_id", "material_reconciliations_batch_id_fkey"),
    ("materials", "material_returns", "batch_id", "material_returns_batch_id_fkey"),
]

_BATCH_STEP_ID_FKS = [
    ("equipment", "aseptic_operations", "batch_step_id", "aseptic_operations_batch_step_id_fkey"),
    ("equipment", "equipment_use_logs", "step_id", "equipment_use_logs_step_id_fkey"),
    ("machine_integration", "batch_contexts", "batch_step_id", "batch_contexts_batch_step_id_fkey"),
    ("materials", "material_consumptions", "step_id", "material_consumptions_step_id_fkey"),
    ("materials", "material_issues", "batch_step_id", "material_issues_batch_step_id_fkey"),
]


def _retarget(fks: list[tuple[str, str, str, str]], new_target_schema: str, new_target_table: str) -> None:
    for schema, table, column, constraint in fks:
        op.drop_constraint(constraint, table, schema=schema, type_="foreignkey")
        op.create_foreign_key(
            constraint, table, new_target_table,
            [column], ["id"],
            source_schema=schema, referent_schema=new_target_schema,
        )


def _retarget_back(fks: list[tuple[str, str, str, str]], old_target_schema: str, old_target_table: str) -> None:
    for schema, table, column, constraint in fks:
        op.drop_constraint(constraint, table, schema=schema, type_="foreignkey")
        op.create_foreign_key(
            constraint, table, old_target_table,
            [column], ["id"],
            source_schema=schema, referent_schema=old_target_schema,
        )


def upgrade() -> None:
    # -- Data cleanup (children first) -- demo/code-testing rows only, confirmed above. --
    op.execute("DELETE FROM ddcp.constituent_handoff WHERE batch_id IN (SELECT id FROM ebmr.batches)")
    op.execute("DELETE FROM equipment.equipment_use_logs WHERE batch_id IN (SELECT id FROM ebmr.batches)")
    op.execute("DELETE FROM materials.inventory_reservations WHERE batch_id IN (SELECT id FROM ebmr.batches)")
    op.execute("DELETE FROM ebmr.batch_steps")
    op.execute("DELETE FROM ebmr.batches")
    op.execute("DELETE FROM ebmr.recipe_steps")
    op.execute("DELETE FROM ebmr.recipes")
    op.execute("DELETE FROM ebmr.products")

    # -- FK retarget: legacy scaffold (ebmr.batches / ebmr.batch_steps) -> authoritative (ebmr.gxp_batch /
    #    ebmr.gxp_batch_step). Tables are now empty on both sides of every one of these relationships, so
    #    the retarget itself cannot fail an existing-row check. --
    _retarget(_BATCH_ID_FKS, "ebmr", "gxp_batch")
    _retarget(_BATCH_STEP_ID_FKS, "ebmr", "gxp_batch_step")


def downgrade() -> None:
    """Reverses the FK retarget only -- disposed regulated rows are not resurrected (MIG-FR-005/MIG-FR-031)."""
    _retarget_back(_BATCH_ID_FKS, "ebmr", "batches")
    _retarget_back(_BATCH_STEP_ID_FKS, "ebmr", "batch_steps")
