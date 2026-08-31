"""Document 32 (SPEC-QMS-007) — Supplier Quality / SCAR. Same owner service as Documents 26-31
(`services/gxp-api/src/modules/qms`), so `supplier_quality_case` and `scar_record` are added to the
existing `qms` schema.

Both entities' field lists in docs/generated/04_DATA_MODEL_CATALOGUE.md are prose-only, but -- like
capa_action/ncr_disposition (SG-045's precedent) -- genuinely unambiguous: typed directly as an ordinary
engineering decision. `supplier_id`/`supplier_site_id`/`material_id` are real FKs into the existing
`ebmr.supplier`/`ebmr.supplier_site` (Document 18, `app/modules/supplier_quality/models.py`) and
`materials.materials` (Document 17) tables -- this module reads that scope, it never writes those tables
(AG-05: one authoritative owner per entity).

Document 32's own 6-op API list is far shorter than its 9-state workflow text
(`OPEN -> CONTAINMENT -> SCAR_ISSUED -> SUPPLIER_RESPONSE -> INTERNAL_REVIEW -> IMPLEMENTATION ->
EFFECTIVENESS -> SOURCE_STATUS_DECISION -> CLOSED`), so the same fold-in pattern used throughout this
module family applies:
  - CONTAINMENT (SCAR-FR-003) has no dedicated endpoint -- it is an optional block on case creation
    (`POST /qms/v1/supplier-cases`); if given, the case starts in CONTAINMENT instead of OPEN.
  - INTERNAL_REVIEW is not a resting state: `review()` is the decision point itself, moving
    SUPPLIER_RESPONSE straight to IMPLEMENTATION (accepted) or back to SUPPLIER_RESPONSE (rejected,
    recorded in `review_history` -- SCAR-FR-008 "accepts/rejects ... with rationale/signature").
  - SOURCE_STATUS_DECISION is folded into `close()`: `source_status_decision` is a required field on the
    close command, matching the Acceptance Criteria text that closure requires a source decision, not
    merely a supplier response (SCAR-FR-016).

`supplier_quality_case.state` only tracks OPEN/CONTAINMENT/SCAR_ISSUED/CLOSED (the case-level envelope);
`scar_record.state` carries the SCAR_ISSUED..CLOSED chain since Document 32's own field list puts
"issued/due dates, supplier response, root cause/action, internal review, effectiveness, closure
signature" on `scar_record`, not the case.

Deferred this pass (see docs/generated/18_SPEC_GAPS.md SG-091, same discipline as SG-059..SG-062):
  - SCAR-FR-011: `source_status_decision == "suspend"` is recorded locally and blocks *new case creation*
    against that supplier from this module (a defensible, conservative fail-closed reading of "Procurement
    gate" within this module's own scope), but does not write `ebmr.supplier.status` and does not gate
    material receipt/use anywhere in the materials module -- that cross-module wiring has no owning
    command to call yet (same shape as SG-059's release-blocker deferral).
  - SCAR-FR-017 (supplier scorecard/performance impact) and SCAR-FR-018 (export) have no operation in
    Document 32's own 6-op API list; export is served by the existing generic audit export path
    (AUD-FR-022), scorecard aggregation is cross-module analytics out of scope this pass.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# SCAR-FR-001: the source types Document 32 itself enumerates ("incoming reject, deviation, complaint,
# audit, trend or manufacturing defect").
SCAR_SOURCE_TYPES = ("incoming_reject", "deviation", "complaint", "audit", "trend", "manufacturing_defect")

CASE_STATES = ("OPEN", "CONTAINMENT", "SCAR_ISSUED", "CLOSED")

SCAR_STATES = ("SCAR_ISSUED", "SUPPLIER_RESPONSE", "IMPLEMENTATION", "EFFECTIVENESS", "CLOSED")

# SCAR-FR-010/011: the source-status decisions Document 32's own vocabulary supports ("requalification",
# "source suspension"); "no_change"/"reinstate" are the two remaining outcomes needed to make the decision
# exhaustive without inventing new regulated categories.
SOURCE_STATUS_DECISIONS = ("no_change", "requalify", "suspend", "reinstate")


class SupplierQualityCase(Base):
    __tablename__ = "supplier_quality_case"
    __table_args__ = (
        UniqueConstraint("quality_event_id"),
        UniqueConstraint("case_number"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    quality_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    case_number: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(40))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_version: Mapped[int | None] = mapped_column()
    supplier_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.supplier.id"), nullable=False)
    supplier_site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.supplier_site.id"))
    material_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("materials.materials.id"))
    material_spec_ref: Mapped[dict | None] = mapped_column(JSONB)
    affected_lots: Mapped[list] = mapped_column(JSONB, nullable=False)
    defect_code: Mapped[str] = mapped_column(String(100), nullable=False)
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    containment: Mapped[dict | None] = mapped_column(JSONB)
    asl_impact: Mapped[dict | None] = mapped_column(JSONB)
    internal_owner_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    # SCAR-FR-012: "Emergency alternative source links deviation/change" -- captured as a reference block,
    # not a FK, since neither target type is fixed (deviation OR change control record).
    alternate_source_ref: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="OPEN")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()


class ScarRecord(Base):
    __tablename__ = "scar_record"
    __table_args__ = (UniqueConstraint("scar_number"), {"schema": "qms"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.supplier_quality_case.id"), nullable=False)
    scar_number: Mapped[str] = mapped_column(String(120), nullable=False)
    issued_at: Mapped[datetime] = mapped_column(nullable=False)
    due_date: Mapped[datetime | None] = mapped_column()
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    # SCAR-FR-005: acknowledgment/contact tracking.
    acknowledgment: Mapped[dict | None] = mapped_column(JSONB)
    # SCAR-FR-006: "supplier statement, not automatically accepted fact" -- kept in its own field,
    # distinct from `internal_review`, which is where Quality forms an accepted/rejected judgement on it.
    supplier_root_cause: Mapped[dict | None] = mapped_column(JSONB)
    # SCAR-FR-007: corrections/corrective actions + implementation evidence.
    supplier_actions: Mapped[dict | None] = mapped_column(JSONB)
    internal_review: Mapped[dict | None] = mapped_column(JSONB)
    review_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    effectiveness: Mapped[dict | None] = mapped_column(JSONB)
    effectiveness_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    requalification_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    requalification_rationale: Mapped[str | None] = mapped_column(Text)
    source_status_decision: Mapped[str | None] = mapped_column(String(20))
    # SCAR-FR-013 -- same flag+rationale treatment as deviation/NCR's capa_required (no FK: an internal
    # CAPA record already exists in this codebase (Document 27), but this module family has never FK'd to
    # it directly, consistently treating "internal CAPA required" as a cross-referenced flag, not an
    # owned relationship).
    capa_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    capa_rationale: Mapped[str | None] = mapped_column(Text)
    is_repeat_issue: Mapped[bool] = mapped_column(nullable=False, default=False)
    related_case_ids: Mapped[list | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="SCAR_ISSUED")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    closure_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()
