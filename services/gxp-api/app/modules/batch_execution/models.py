"""Document 11 (SPEC-EBMR-002) — Batch Execution Engine & State Machine. New, additive module: does not
touch app/modules/batch (the legacy stub still referencing ebmr.products/ebmr.recipes) at all. See
migration f264272f2f0b_0012_batch_execution_schema for the schema deviations from
docs/generated/04_DATA_MODEL_CATALOGUE.md.

Only 2 of Document 11's 5 owned entities (gxp_batch, gxp_batch_step) were DDL-ready in the catalogue; the
other 3 (gxp_step_result, gxp_step_evidence_link, gxp_batch_hold) were prose-only field-name lists with no
types, same problem as Document 10's SG-045 -- deferred as SG-047. SG-047 is now PARTIALLY resolved
(2026-09-09, project-owner-directed): `gxp_step_result` is built (migration db47f27cf18b_0092), typed
against `gxp_recipe_parameter`'s own already-declared data_type/precision rather than inventing a new
Document 110 policy -- see that migration's docstring. A narrow, step-scoped slice of `gxp_batch_hold` is
also now built (`StepHold` below, migration <pending>_0093) -- BAT-FR-020's "signature" field resolved by
reusing Document 106 row 14's own signature shape (nearest analogous action), not a new invented policy;
the entity's full generality (arbitrary scope, quality-event linkage the real gxp_batch_hold prose also
names) stays open. `gxp_step_evidence_link` remains open in full. The other absent infrastructure SG-048
lists (Temporal, Material Service consumption/reservation, Equipment master eligibility wiring,
qualification schema, exception/rework/branch entities) is still not built.

Lifecycle: BAT-FR-004 names a fuller state list (Planned, Created/Snapshot Locked, Issued, Ready, In
Execution, On Hold, Exception Pending, Production Complete, QA Review, Released/Rejected, Closed) than
this pass reaches -- Ready/Exception Pending/Production Complete/QA Review/Released/Rejected/Closed all
depend on capabilities gapped by SG-047/SG-048 (step results, exceptions, yield reconciliation, QA
signatures). BATCH_STATES below is the honest buildable subset; extending it is exactly the future work
SG-048 describes.
"""

import uuid
from datetime import datetime
from decimal import Decimal

from sqlalchemy import BigInteger, ForeignKey, Index, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# BAT-FR-026 (2026-09-09, project-owner-directed, SG-048 #026 partial resolution): "production_complete"
# added -- reachable once every gxp_batch_step is "complete" (the steps-completeness sub-clause of
# BAT-FR-026 only; yield/reconciliation and other "production blockers" BAT-FR-026 also names stay
# deferred, no Document 17 linkage exists to check them against). A batch found to need attention after
# production is nominally complete can still be put "on_hold" (line clearance issue found late, etc.) --
# same allowed-target shape as release/models.py's own "released": {"hold"}, an established precedent in
# this exact codebase for a near-terminal state that can still be pulled back for a hold.
BATCH_STATES = ("planned", "issued", "in_execution", "on_hold", "aborted", "production_complete")

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "planned": {"issued", "aborted"},
    "issued": {"in_execution", "aborted"},
    "in_execution": {"on_hold", "aborted", "production_complete"},
    "on_hold": {"in_execution", "aborted"},
    "aborted": set(),
    "production_complete": {"on_hold"},
}

# BAT-FR-006/007/009/015 (SG-047 partial resolution, project-owner-directed, 2026-09-09): a step with no
# predecessor is "ready" at issue; a step with a predecessor stays "pending" until every predecessor
# reaches "complete" (service.recompute_readiness, called after each StepCompleted). "in_progress" ->
# "complete" is StepCompleted (commands.complete_step); "ready" -> "in_progress" is StepStarted, unchanged.
# "in_progress" <-> "on_hold" is StepHeld/StepResumed (commands.hold_step/resume_step, BAT-FR-020
# step-scope, SG-047 partial resolution, 2026-09-09) -- a held step blocks its own start/results/complete
# (all three require "in_progress"/"ready" specifically) without stopping the whole batch or any other
# step, matching BAT-FR-020's literal "whole batch or scoped stage/step" wording.
BATCH_STEP_STATES = ("pending", "ready", "in_progress", "on_hold", "complete")


class Batch(Base):
    __tablename__ = "gxp_batch"
    __table_args__ = (UniqueConstraint("site_id", "batch_number"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_number: Mapped[str] = mapped_column(String(120), nullable=False)
    product_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_product_version.id"), nullable=False
    )
    # Deviation from the catalogue (documented in the migration, same practice as recipe_master's own
    # product_version_id addition): a live FK to the released recipe version is required to read its step
    # graph at issue time. `recipe_vault_object_id` below is still the catalogue's own column, copied from
    # RecipeVersion.released_vault_object_id at creation time.
    recipe_version_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ebmr.gxp_recipe_version.id"), nullable=False
    )
    recipe_vault_object_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    execution_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("vault.gxp_vault_object.object_id")
    )
    target_qty: Mapped[Decimal] = mapped_column(Numeric(24, 8), nullable=False)
    target_uom: Mapped[str] = mapped_column(String(40), nullable=False)
    # SG-146 (remainder, module 4 of 8), MIG-FR-004 expand step: dual-written best-effort, backfillable
    # (ebmr.gxp_batch is mutable — UPDATE granted, migration f264272f2f0b 0012).
    target_uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="planned")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    production_order_ref: Mapped[str | None] = mapped_column(String(160))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    issued_at: Mapped[datetime | None] = mapped_column()
    started_at: Mapped[datetime | None] = mapped_column()
    production_completed_at: Mapped[datetime | None] = mapped_column()
    qa_review_started_at: Mapped[datetime | None] = mapped_column()
    closed_at: Mapped[datetime | None] = mapped_column()


class BatchStep(Base):
    __tablename__ = "gxp_batch_step"
    __table_args__ = (UniqueConstraint("batch_id", "recipe_step_code"), {"schema": "ebmr"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"), nullable=False)
    recipe_step_code: Mapped[str] = mapped_column(String(120), nullable=False)
    # SG-178: frozen at issue time from RecipeStep.required_role_code (Document 10). The actor starting
    # this step must hold this role name, or a batch_step.role_override holder must supply a documented
    # reason. Nullable — a step the recipe left unrestricted carries NULL and is startable by any
    # batch_execution.execute holder, as before.
    required_role_code: Mapped[str | None] = mapped_column(String(80))
    scope_type: Mapped[str] = mapped_column(String(40), nullable=False, default="batch")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    assigned_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    started_at: Mapped[datetime | None] = mapped_column()
    completed_at: Mapped[datetime | None] = mapped_column()
    # branch_status/exception_state/temporal_workflow_ref: catalogued DDL-ready columns kept for schema
    # completeness, but nothing in this pass writes them -- their producing requirements (BAT-FR-022
    # conditional branch, BAT-FR-021 exception generation, BAT-FR-028 Temporal orchestration) are all
    # deferred by SG-048.
    branch_status: Mapped[str | None] = mapped_column(String(40))
    exception_state: Mapped[str | None] = mapped_column(String(40))
    temporal_workflow_ref: Mapped[str | None] = mapped_column(String(255))


class StepResult(Base):
    """BAT-FR-009/010 (SG-047 partial resolution). Append-only -- no UPDATE grant (migration
    db47f27cf18b_0092); a correction chain (BAT-FR-023, supersedes_result_id) is not built this pass.
    `data_type` is copied from the `gxp_recipe_parameter` row the value is captured against, so a result
    row is self-describing without rejoining to a recipe version that may since have been superseded.
    """

    __tablename__ = "gxp_step_result"
    __table_args__ = (
        Index("ix_gxp_step_result_step_id", "step_id"),
        {"schema": "ebmr"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch_step.id"), nullable=False)
    parameter_code: Mapped[str] = mapped_column(String(80), nullable=False)
    data_type: Mapped[str] = mapped_column(String(40), nullable=False)
    result_version: Mapped[int] = mapped_column(nullable=False, default=1)
    value_numeric: Mapped[Decimal | None] = mapped_column(Numeric(24, 8))
    value_text: Mapped[str | None] = mapped_column(String(2000))
    value_bool: Mapped[bool | None] = mapped_column()
    uom: Mapped[str | None] = mapped_column(String(40))
    # BAT-FR-010: fixed 'manual' this pass -- device/edge sourcing (BAT-FR-011) is SG-048 #011, not built.
    source_type: Mapped[str] = mapped_column(String(40), nullable=False, default="manual")
    source_timestamp: Mapped[datetime | None] = mapped_column()
    received_at: Mapped[datetime] = mapped_column(server_default=func.now())
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("signature.signatures.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class StepHold(Base):
    """BAT-FR-020, step scope only (SG-047 partial resolution, 2026-09-09, project-owner-directed).
    One row per hold episode: `released_at IS NULL` means the hold is currently active on `step_id`. Both
    the hold and the release are signed (Document 106 row 14/17's shapes, the nearest analogous batch-level
    actions -- no step-scoped row exists in Document 106 itself). Not a general-purpose `gxp_batch_hold` --
    no arbitrary scope, no quality-event linkage (SG-047 stays open for that fuller entity).
    """

    __tablename__ = "gxp_batch_step_hold"
    __table_args__ = (
        Index("ix_gxp_batch_step_hold_batch_id", "batch_id"),
        Index("ix_gxp_batch_step_hold_step_id", "step_id"),
        {"schema": "ebmr"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    step_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch_step.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"), nullable=False)
    reason: Mapped[str] = mapped_column(String(2000), nullable=False)
    held_at: Mapped[datetime] = mapped_column(server_default=func.now())
    held_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    hold_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("signature.signatures.id"))
    released_at: Mapped[datetime | None] = mapped_column()
    released_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    release_reason: Mapped[str | None] = mapped_column(String(2000))
    release_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("signature.signatures.id"))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
