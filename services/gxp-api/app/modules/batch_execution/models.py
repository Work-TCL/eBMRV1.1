"""Document 11 (SPEC-EBMR-002) — Batch Execution Engine & State Machine. New, additive module: does not
touch app/modules/batch (the legacy stub still referencing ebmr.products/ebmr.recipes) at all. See
migration f264272f2f0b_0012_batch_execution_schema for the schema deviations from
docs/generated/04_DATA_MODEL_CATALOGUE.md.

Only 2 of Document 11's 5 owned entities (gxp_batch, gxp_batch_step) are DDL-ready in the catalogue; the
other 3 (gxp_step_result, gxp_step_evidence_link, gxp_batch_hold) are prose-only field-name lists with no
types, same problem as Document 10's SG-045 -- deferred here as SG-047. Consequently this module only
implements the slice of BAT-FR-001..036 buildable against gxp_batch/gxp_batch_step without those three
tables or the other absent infrastructure (Temporal, Material Service, Equipment master, qualification
schema, exception/rework/branch entities) -- see SG-048 for the itemised list of what's deferred and why.

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

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

BATCH_STATES = ("planned", "issued", "in_execution", "on_hold", "aborted")

ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "planned": {"issued", "aborted"},
    "issued": {"in_execution", "aborted"},
    "in_execution": {"on_hold", "aborted"},
    "on_hold": {"in_execution", "aborted"},
    "aborted": set(),
}

# BAT-FR-006 (predecessor slice only): a step with no predecessor is immediately "ready"; steps with a
# predecessor stay "pending" until that predecessor completes -- a capability this pass does not build
# (completion needs gxp_step_result, SG-047), so non-root steps stay "pending" for the life of this pass.
# BAT-FR-007 claim/start moves "ready" -> "in_progress". Completion (-> "completed") is out of scope.
BATCH_STEP_STATES = ("pending", "ready", "in_progress")


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
    version: Mapped[int] = mapped_column(nullable=False, default=1)
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
    scope_type: Mapped[str] = mapped_column(String(40), nullable=False, default="batch")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="pending")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
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
