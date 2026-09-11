"""Document 27 (SPEC-QMS-002) — CAPA Management. Same owner service as Document 26
(`services/gxp-api/src/modules/qms` per docs/generated/05_DATABASE_OWNERSHIP_MATRIX.md), so these three
entities live in the same `qms` schema (migration 0020_capa_schema) as `deviation_record`.

`capa_record`'s 11-field list in docs/generated/04_DATA_MODEL_CATALOGUE.md is DDL-ready as given.
`capa_action` and `capa_effectiveness_check` are prose field-name lists but -- like deviation_impact_link
(SG-045's precedent) -- genuinely unambiguous, typed directly as an ordinary engineering decision.

Several columns beyond the catalogue's literal field count are added, each traced directly to requirement
text rather than guessed content (same latitude used throughout this codebase, e.g. deviation_record's
extension_history/closure_history/reopen_history):
  - `source_type/source_id/source_version` (CAPA-FR-001: "create from deviation/OOS/OOT/NCR/complaint/
    audit/supplier/risk/trend/security/validation source")
  - `scope_type`/`scope_refs` (CAPA-FR-019: "site/product/process/enterprise")
  - `corrective_action`/`preventive_action` (CAPA-FR-005/006, captured at /plan)
  - `recurrence_links` (CAPA-FR-018: "link new quality events to prior CAPA")
  - `cancel_reason`/`cancelled_at` (CAPA-FR-016 -- see the CANCELLED state note below)
  - `extension_history`/`closure_history`/`reopen_history` (CAPA-FR-013/015/017, same append-only
    history pattern as deviation_record)

State model (real Document 27 §4 names a fuller list: OPEN -> PROBLEM_CONFIRMED -> PLAN -> APPROVED ->
IMPLEMENTATION -> IMPLEMENTATION_VERIFIED -> EFFECTIVENESS_MONITORING -> EFFECTIVENESS_REVIEW ->
QA_CLOSURE -> CLOSED, EFFECTIVENESS_FAILED -> REOPEN/NEW_ACTION). Document 27's own 8-op API list has no
operation to drive PROBLEM_CONFIRMED, APPROVED or QA_CLOSURE as separately reachable phases -- exactly the
same "fold sub-phases into the one endpoint that actually exists" pattern Document 26's QA_REVIEW and
Document 15's PENDING_SIGNATURE used (SG-055's reasoning): problem confirmation is inherent in create()
requiring problem_statement/root_cause_ref; plan approval is inherent in plan() itself (no separate
"approve" op, and Document 27 §6 marks plan's Signature column "-- ", so there is no distinct authority
step to model as its own state); QA_CLOSURE is folded into close()'s own completeness gates + signature
ceremony. CAPA_STATES below is the honestly-reachable subset.

CANCELLED (CAPA-FR-016) has no dedicated endpoint in Document 27's own 8-op API list either. Rather than
invent a new one, close() is reused for it: a `cancellation_reason` on the close command produces a
CANCELLED terminal state instead of CLOSED, skipping the normal completeness gates -- the same "reuse an
existing signed endpoint for a closely related terminal disposition" decision Document 15's release module
made for post-release hold (REL-FR-031 reusing hold_scope), not a new invented operation.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# CAPA-FR-001: the source types Document 27 itself enumerates.
CAPA_SOURCE_TYPES = (
    "deviation", "oos", "oot", "ncr", "complaint", "audit", "supplier", "risk", "trend", "security", "validation",
)

# CAPA-FR-019: the scope types Document 27 itself enumerates.
CAPA_SCOPE_TYPES = ("site", "product", "process", "enterprise")

CAPA_STATES = (
    "OPEN", "PLAN", "IMPLEMENTATION", "IMPLEMENTATION_VERIFIED", "EFFECTIVENESS_MONITORING",
    "EFFECTIVENESS_REVIEW", "EFFECTIVENESS_FAILED", "CLOSED", "CANCELLED", "REOPENED",
)

NON_CANCELLABLE_STATES = ("CLOSED", "CANCELLED")

CAPA_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"PLAN"},
    "PLAN": {"IMPLEMENTATION"},
    "IMPLEMENTATION": {"IMPLEMENTATION", "IMPLEMENTATION_VERIFIED"},
    "IMPLEMENTATION_VERIFIED": {"EFFECTIVENESS_MONITORING"},
    "EFFECTIVENESS_MONITORING": {"EFFECTIVENESS_MONITORING", "EFFECTIVENESS_REVIEW", "EFFECTIVENESS_FAILED"},
    "EFFECTIVENESS_REVIEW": {"CLOSED"},
    # CAPA-FR-012: failed effectiveness reopens through a controlled action, or accepts a new action
    # directly (Document 27 §4's own "EFFECTIVENESS_FAILED -> REOPEN/NEW_ACTION").
    "EFFECTIVENESS_FAILED": {"REOPENED", "IMPLEMENTATION"},
    "CLOSED": {"REOPENED"},
    "REOPENED": {"IMPLEMENTATION", "EFFECTIVENESS_MONITORING", "EFFECTIVENESS_REVIEW", "CLOSED"},
    "CANCELLED": set(),
}

ACTION_TYPES = ("corrective", "preventive", "systemic")
ACTION_STATES = ("open", "completed")
EFFECTIVENESS_RESULTS = ("pass", "fail", "inconclusive")


class CapaRecord(Base):
    __tablename__ = "capa_record"
    __table_args__ = (
        UniqueConstraint("quality_event_id"),
        UniqueConstraint("capa_number"),
        Index("ix_capa_record_state_target", "site_id", "state", "target_date"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    quality_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    capa_number: Mapped[str] = mapped_column(String(120), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_version: Mapped[int | None] = mapped_column()
    problem_statement: Mapped[str] = mapped_column(Text, nullable=False)
    scope_type: Mapped[str] = mapped_column(String(20), nullable=False, default="site")
    scope_refs: Mapped[list | None] = mapped_column(JSONB)
    risk_class: Mapped[str] = mapped_column(String(40), nullable=False)
    root_cause_ref: Mapped[dict] = mapped_column(JSONB, nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="OPEN")
    owner_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    target_date: Mapped[datetime] = mapped_column(nullable=False)
    effectiveness_plan: Mapped[dict | None] = mapped_column(JSONB)
    corrective_action: Mapped[dict | None] = mapped_column(JSONB)
    preventive_action: Mapped[dict | None] = mapped_column(JSONB)
    recurrence_links: Mapped[list | None] = mapped_column(JSONB)
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_at: Mapped[datetime | None] = mapped_column()
    extension_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    closure_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    reopen_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()


class CapaAction(Base):
    __tablename__ = "capa_action"
    __table_args__ = (
        Index("ix_capa_action_capa", "capa_id"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.capa_record.id"), nullable=False)
    action_type: Mapped[str] = mapped_column(String(20), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    due_date: Mapped[datetime] = mapped_column(nullable=False)
    # CAPA-FR-008: dependency_type in {"change_control","training","validation","supplier",
    # "software_release","equipment","capa_action"}. Only "capa_action" (another action within the same
    # CAPA) is enforced by ACTION_DEPENDENCY_OPEN -- see SG-063 for why the others are unenforced
    # logical references.
    dependency_links: Mapped[list | None] = mapped_column(JSONB)
    implementation_evidence: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="open")
    verification_status: Mapped[str | None] = mapped_column(String(20))
    verified_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    verified_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class CapaEffectivenessCheck(Base):
    __tablename__ = "capa_effectiveness_check"
    __table_args__ = (
        Index("ix_capa_effectiveness_check_capa", "capa_id"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    capa_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.capa_record.id"), nullable=False)
    criterion: Mapped[str] = mapped_column(Text, nullable=False)
    data_source: Mapped[str] = mapped_column(String(200), nullable=False)
    observation_start: Mapped[datetime] = mapped_column(nullable=False)
    observation_end: Mapped[datetime] = mapped_column(nullable=False)
    due_date: Mapped[datetime] = mapped_column(nullable=False)
    result: Mapped[str | None] = mapped_column(String(20))
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    reviewer_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    evaluated_at: Mapped[datetime | None] = mapped_column()
