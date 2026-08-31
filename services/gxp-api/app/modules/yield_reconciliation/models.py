"""Document 17 (SPEC-EBMR-008) — Yield, Calculations & Manufacturing Reconciliation. `ebmr` schema,
alongside every other WP-02/03 eBMR-family entity (genealogy/qa_review/release/packaging).

Document 08 (SPEC-GXP-006) owns the generic rules/calculation engine (`rules.gxp_rule_definition`/
`rules.gxp_rule_evaluation`) -- this module never embeds a calculation formula itself (spec §3 "do not
embed formula in UI", applied literally to the backend too). `evaluate_yield()`/`evaluate_potency()` in
commands.py resolve a *released* rule and delegate the actual arithmetic to
`app/modules/rules/expression.py::evaluate()`; these two tables record the manufacturing semantics,
source-quantity references and verification state around that call (YLD-FR-001/007/023/031).

Two deliberate substitutions from the spec's literal §4 field list, same restraint as every prior
document:
- `tenant_id` dropped (single-organization platform, ADR-0006).
- `manufacturing_calculation.rule_object_id`/`rule_evaluation_id` added (not in the spec's literal field
  list) -- the actual FK linkage to Document 08's rule/evaluation rows the spec's own §1 objective
  ("Document 08 owns the ... engine") requires but doesn't enumerate as a column.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, Numeric, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

CALCULATION_TYPES = ("YIELD", "POTENCY")
CALCULATION_STATES = (
    "PENDING_INPUT", "READY", "CALCULATED", "VERIFICATION_REQUIRED", "VERIFIED",
    "FAILED", "OUT_OF_LIMIT", "SUPERSEDED",
)
RECONCILIATION_TYPES = ("MATERIAL", "PACKAGING", "LABEL", "COMPONENT")
RECONCILIATION_STATES = ("CALCULATED", "ACCEPTABLE", "OUT_OF_TOLERANCE", "VERIFIED", "FAILED", "SUPERSEDED")
SCOPE_TYPES = ("BATCH", "PHASE", "SUB_LOT", "SERIAL_GROUP")

# Document 17 §3's mass-balance categories, the default for MATERIAL/PACKAGING/LABEL.
QUANTITY_CATEGORIES = ("consumed", "returned", "samples", "rejected", "destroyed", "approved_loss")

# YLD-FR-013 names its own category set literally -- "issued/assembled/rejected/scrapped/returned" -- so
# COMPONENT reconciliation adds `assembled` and `scrapped` rather than forcing device components through
# the material vocabulary. Both extra names come from the requirement text, not from this module.
COMPONENT_QUANTITY_CATEGORIES = QUANTITY_CATEGORIES + ("assembled", "scrapped")


class ManufacturingCalculation(Base):
    """YLD-FR-001..008/015/016/022/023/031. `input_hash` is sha256 over `input_refs` (YLD-FR-002 "no
    untraceable number" -- the hash lets a later audit prove the recorded inputs were never altered).
    `supersedes_id` implements YLD-FR-022 "correction preserves original": a correction is always a new
    row, never an UPDATE of `result`/`state` on an existing one (AG-08)."""

    __tablename__ = "manufacturing_calculations"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"), nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, default="BATCH")
    scope_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    calculation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # YLD-FR-026: a SERIAL_GROUP-scoped calculation names the device unit it belongs to, so serial-level
    # results aggregate to a parent without losing which unit produced an exception (Document 12 owns the
    # per-unit identity; this is a foreign key to it, never a copy of its serial_number).
    device_unit_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.device_unit.id"))
    phase_code: Mapped[str | None] = mapped_column(String(80))
    rule_object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_rule_definition.rule_object_id"))
    rule_evaluation_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_rule_evaluation.evaluation_id"))
    input_refs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    input_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    theoretical_quantity: Mapped[object | None] = mapped_column(Numeric(20, 6))
    actual_quantity: Mapped[object | None] = mapped_column(Numeric(20, 6))
    uom: Mapped[str | None] = mapped_column(String(20))
    # SG-146 (remainder), MIG-FR-004 expand step: the free-text `uom` string above is still
    # authoritative; `uom_id` is dual-written best-effort where `uom` resolves against a *released*
    # rules.gxp_uom row at write time (app.modules.yield_reconciliation.commands._resolve_uom_id).
    # References a specific released version (VLT-FR-006/007's "freeze the exact reference" discipline),
    # never a floating code. Migration 0048.
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))
    min_percent: Mapped[object | None] = mapped_column(Numeric(9, 4))
    max_percent: Mapped[object | None] = mapped_column(Numeric(9, 4))
    manual_source: Mapped[str | None] = mapped_column(String(200))
    manual_reason: Mapped[str | None] = mapped_column(String(400))
    result: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING_INPUT")
    evaluated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    evaluated_at: Mapped[datetime | None] = mapped_column()
    verified_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    verified_at: Mapped[datetime | None] = mapped_column()
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.manufacturing_calculations.id"))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ReconciliationRecord(Base):
    """YLD-FR-009..014/019..021/024..027. `quantities` carries the mass-balance categories from spec §3
    (issued/dispensed, consumed, returned, samples, rejected, destroyed, approved_loss) as decimal
    strings, plus the computed `unexplained_variance` -- never a binary float (AG-15). `external_reference`
    is YLD-FR-027's ERP/WMS comparison: informational only, and this module never lets it overwrite the
    GxP-computed `variance` column."""

    __tablename__ = "reconciliation_records"
    __table_args__ = {"schema": "ebmr"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    batch_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_batch.id"), nullable=False)
    reconciliation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    # YLD-FR-013/026: COMPONENT reconciliation of a serialized/critical component is scoped to Document
    # 12's `device_unit` rather than the generic `item_ref` blob. Nullable because MATERIAL/PACKAGING/LABEL
    # reconciliation is batch- or run-scoped and has no per-unit identity.
    device_unit_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.device_unit.id"))
    item_ref: Mapped[dict] = mapped_column(JSONB, nullable=False)
    quantities: Mapped[dict] = mapped_column(JSONB, nullable=False)
    uom: Mapped[str | None] = mapped_column(String(20))
    # SG-146 (remainder) — same dual-write discipline as ManufacturingCalculation.uom_id above.
    uom_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_uom.uom_id"))
    tolerance_rule: Mapped[dict | None] = mapped_column(JSONB)
    variance: Mapped[object | None] = mapped_column(Numeric(20, 6))
    # YLD-FR-021 "Document controlled reasons/categories for process loss, sample, spill, reject,
    # destruction" -- one entry per documented reason behind the `approved_loss` quantity, so the loss is
    # explained rather than merely counted. The category vocabulary is customer-controlled and no
    # catalogue entity exists in the baseline (SG-135): the structure is enforced, the values are not.
    loss_reasons: Mapped[list | None] = mapped_column(JSONB)
    external_reference: Mapped[dict | None] = mapped_column(JSONB)
    # YLD-FR-027: the outcome of comparing `external_reference`'s ERP/WMS quantity against the
    # GxP-computed total. Records that a comparison happened and what it found; it never feeds back into
    # `variance` -- "ERP never overwrites GxP evidence automatically".
    external_comparison: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="CALCULATED")
    linked_quality_event_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    evaluated_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    verified_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    verified_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    verified_at: Mapped[datetime | None] = mapped_column()
    supersedes_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.reconciliation_records.id"))
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
