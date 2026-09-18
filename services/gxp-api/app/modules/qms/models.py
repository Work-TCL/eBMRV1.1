"""Document 26 (SPEC-QMS-001) — Deviation & Investigation Management. New module, new `qms` schema (same
USAGE + DML grant pattern as `rules`/`materials` — see migration 0018_qms_deviation_schema).

Both owned entities are typed directly this pass. `deviation_record`'s 19-field list in
docs/generated/04_DATA_MODEL_CATALOGUE.md is DDL-ready as given. `deviation_impact_link` is a prose
field-name list ("impacted record type/ID/version, impact category, hold/disposition reference") but --
like release_evaluation/release_decision (SG-045's precedent) -- genuinely unambiguous: it is typed
directly as an ordinary engineering decision and reused for both the evidence graph (DEV-FR-009, links
created with impact_category=NULL) and the formal impact assessment (DEV-FR-011, impact_category set).

Several sub-shapes referenced by Document 26's requirement text but not given a JSON shape are typed here
as concrete keys taken directly from that requirement text, not guessed content (same latitude Document 15
used for its one semi-structured field, `blockers`):
  - `planned_scope`   (DEV-FR-016: "bounded by scope/date/batches")            -> scope/start_date/end_date/batch_ids
  - `immediate_correction` (DEV-FR-004)                                        -> description/performed_by/performed_at
  - `containment`     (DEV-FR-005: "batch/material/equipment/area on hold")    -> list of {target_type,target_id,description}
  - `investigation_plan` (DEV-FR-007: "records, interviews, batches/products, technical evidence")
  - `root_cause`      (DEV-FR-010: "configurable root-cause methods and 'no assignable cause'")
  - `impact_assessment` (DEV-FR-011: "quality, patient/user, released/distributed product, validation,
     data integrity and regulatory impact" -- the six named categories become the six required keys)

Document 26 §9 states plainly: "Source batch/QC/material/equipment records are never edited from QMS
screens." Containment is therefore always a *record* of what was done, never a write into batch/material/
equipment state -- this module never imports or writes another module's tables.

Deferred this pass (see docs/generated/18_SPEC_GAPS.md SG-059..SG-062):
  - DEV-FR-002/022: automatic candidate creation from other modules, and wiring deviations into the
    release module's eligibility check, are cross-module integration work no other module performs yet.
  - DEV-FR-014/015: Change Control and Training/Qualification-action are recorded as a flag + rationale
    only -- no Change Control or training-action entity exists anywhere in this codebase to link to.
  - DEV-FR-016's DRAFT->PREAPPROVED->ACTIVE planned-deviation lifecycle, DEV-FR-021's recurrence search
    and DEV-FR-024's export have no operation in Document 26's own 9-op API list.
  - DEV-FR-023: no notification/escalation worker infrastructure exists anywhere in this codebase yet.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# DEV-FR-001: the source types Document 26 itself enumerates ("batch, QC, material, equipment,
# environment, supplier, document or system source").
SOURCE_TYPES = ("batch", "qc", "material", "equipment", "environment", "supplier", "document", "system")

# Document 26 §4's own state notation, used verbatim (upper-case matches the spec's own arrows).
DEVIATION_STATES = (
    "OPEN",
    "TRIAGE",
    "CONTAINMENT",
    "INVESTIGATION",
    "IMPACT_ASSESSMENT",
    "DISPOSITION",
    "CLOSED",
    "REOPENED",
)

# DEV-FR-012: the disposition outcomes Document 26 itself enumerates ("Continue/hold/reject/rework/
# reprocess/additional test/destroy/field-action assessment").
DISPOSITION_CODES = (
    "CONTINUE",
    "HOLD",
    "REJECT",
    "REWORK",
    "REPROCESS",
    "ADDITIONAL_TEST",
    "DESTROY",
    "FIELD_ACTION_ASSESSMENT",
)

# The linear pipeline the 9-op API list drives, plus REOPENED re-entering it (DEV-FR-020: "reopens
# through controlled action" -- Document 26 doesn't say where reopened work resumes, so REOPENED is
# accepted as an entry state everywhere CONTAINMENT is, letting the same forward pipeline run again).
ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"TRIAGE"},
    "TRIAGE": {"CONTAINMENT"},
    "CONTAINMENT": {"INVESTIGATION"},
    "INVESTIGATION": {"INVESTIGATION", "IMPACT_ASSESSMENT"},
    "IMPACT_ASSESSMENT": {"IMPACT_ASSESSMENT", "DISPOSITION"},
    "DISPOSITION": {"DISPOSITION", "CLOSED"},
    "CLOSED": {"REOPENED"},
    "REOPENED": {"CONTAINMENT", "INVESTIGATION", "IMPACT_ASSESSMENT", "DISPOSITION", "CLOSED"},
}


class DeviationRecord(Base):
    __tablename__ = "deviation_record"
    __table_args__ = (
        UniqueConstraint("quality_event_id"),
        UniqueConstraint("deviation_number"),
        Index("ix_deviation_record_severity", "site_id", "severity", "state"),
        Index("ix_deviation_record_state_due", "site_id", "state", "due_date"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    quality_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    deviation_number: Mapped[str] = mapped_column(String(120), nullable=False)
    deviation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_version: Mapped[int | None] = mapped_column()
    severity: Mapped[str] = mapped_column(String(40), nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="OPEN")
    # Nullable since the auto-deviation-on-out-of-range-result fix (docs/testing/demo-gujarati/08 §8.8
    # item 2, project-owner-directed 2026-09-18): a system-opened deviation starts unassigned -- a human
    # (Supervisor/QA Reviewer) triages and claims it, same as investigator_subject_id already works.
    owner_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    investigator_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    planned: Mapped[bool] = mapped_column(nullable=False, default=False)
    planned_scope: Mapped[dict | None] = mapped_column(JSONB)
    immediate_correction: Mapped[dict | None] = mapped_column(JSONB)
    containment: Mapped[dict | None] = mapped_column(JSONB)
    investigation_plan: Mapped[dict | None] = mapped_column(JSONB)
    cross_batch_ids: Mapped[list | None] = mapped_column(JSONB)
    root_cause: Mapped[dict | None] = mapped_column(JSONB)
    impact_assessment: Mapped[dict | None] = mapped_column(JSONB)
    disposition_code: Mapped[str | None] = mapped_column(String(80))
    disposition_rationale: Mapped[str | None] = mapped_column(Text)
    capa_required: Mapped[bool | None] = mapped_column()
    capa_rationale: Mapped[str | None] = mapped_column(Text)
    # DEV-FR-014/015 -- SG-060 (WP-05 pass): the flag/rationale stay (a change/training need can be
    # flagged before the linked record exists), and the actual link is now a real FK, filled in via
    # DispositionCommand once the caller knows the id (or later, once one is created) -- both
    # `qms.change_control` and `qms.training_assignment` exist now (they didn't when this flag was
    # first built), the same follow-up SG-060 itself anticipated.
    change_control_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    change_control_rationale: Mapped[str | None] = mapped_column(Text)
    change_control_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.change_control.id"))
    training_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    training_rationale: Mapped[str | None] = mapped_column(Text)
    training_assignment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.training_assignment.id"))
    due_date: Mapped[datetime | None] = mapped_column()
    # DEV-FR-017: "old due date retained" -- append-only history, never overwritten.
    extension_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # DEV-FR-020: "preserving prior closure" -- every closure (first and any after a reopen) is appended
    # here; `closed_at` itself is only ever set on the *first* closure and is never overwritten.
    closure_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    reopen_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()


class DeviationImpactLink(Base):
    """Insert-only graph edges -- DEV-FR-009's evidence graph (`impact_category` NULL) and DEV-FR-011's
    formal impact links (`impact_category` set) are the same table; nothing here is ever updated in
    place, matching the append-only discipline used everywhere else in this codebase.
    """

    __tablename__ = "deviation_impact_link"
    __table_args__ = (
        Index("ix_deviation_impact_link_deviation", "deviation_id"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    deviation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.deviation_record.id"), nullable=False)
    impacted_record_type: Mapped[str] = mapped_column(String(60), nullable=False)
    impacted_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    impacted_record_version: Mapped[int | None] = mapped_column()
    impact_category: Mapped[str | None] = mapped_column(String(60))
    hold_disposition_reference: Mapped[str | None] = mapped_column(String(200))
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
