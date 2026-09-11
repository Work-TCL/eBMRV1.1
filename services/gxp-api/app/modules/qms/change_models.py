"""Document 29 (SPEC-QMS-004) — Change Control. Same owner service as Documents 26-28
(`services/gxp-api/src/modules/qms`), so these three entities live in the same `qms` schema
(migration 0023_change_schema). Building this module is the concrete follow-up SG-060 (Document 26) and
SG-063 (Document 27) both anticipated: a real Change Control entity now exists to link CAPA/deviation
dispositions against, though wiring those existing modules' `change_control_required` flags to actually
create/link a `ChangeControl` row is itself cross-module work out of scope this pass -- see this module's
own SG-072 for the same-shaped gap in the other direction.

`change_control`'s 14-field list in docs/generated/04_DATA_MODEL_CATALOGUE.md is DDL-ready as given.
`change_affected_object` and `change_task` are prose field-name lists but -- like ncr_disposition
(SG-045's precedent) -- genuinely unambiguous, typed directly as an ordinary engineering decision.

Extra columns beyond the catalogue's literal field list are each traced directly to requirement text:
  - `reason` (CHG-FR-003: "reason/business need")
  - `impact_assessment` (CHG-FR-006/010/011: quality/open-batch-inventory/data-migration impact --
    the data model catalogue only names regulatory_impact/validation_impact/training_impact as their own
    columns; the other three impact categories become keys of this one catch-all jsonb column, the same
    "unnamed categories become dict keys" pattern deviation_record's impact_assessment used for DEV-FR-011)
  - `emergency`/`emergency_reason`/`retrospective_review`/`retrospective_review_completed` (CHG-FR-014)
  - `cancel_reason`/`cancelled_at`, `closure_history` (CHG-FR-020/021, same append-only pattern as every
    other module in this family)

State model (real Document 29 section 4: DRAFT -> IMPACT_ASSESSMENT -> RISK_REVIEW -> APPROVAL ->
IMPLEMENTATION -> VERIFICATION/VALIDATION -> EFFECTIVE -> POST_IMPLEMENTATION_REVIEW -> CLOSED, plus a
parallel EMERGENCY -> IMPLEMENT -> RETROSPECTIVE_REVIEW lane). Document 29's own 8-op API list has no
operation to drive RISK_REVIEW or POST_IMPLEMENTATION_REVIEW as separately reachable phases -- the same
fold-in pattern used throughout this module family: RISK_REVIEW is folded into the one `impact` endpoint
(CHG-FR-008's risk_ref is captured there alongside every other impact category); POST_IMPLEMENTATION_REVIEW
is folded into close()'s own gate (CHG-FR-018).

CHG-FR-019 (rollback) has **no operation** anywhere in Document 29's own 8-op API list and, unlike
CAPA-FR-016's cancellation, is not a natural extension of an existing endpoint either -- a rollback is a
materially different, backward-branching operation (preserving both the old and new version as live
evidence) from anything close()/make-effective() do. Not built this pass -- see SG-073.

CHG-FR-021 (cancellation) *is* handled the same way CAPA-FR-016 was: close() accepts a `cancellation_reason`
that produces a CANCELLED terminal state instead of CLOSED, skipping the normal completeness gates, reusing
the module's one signature-gated terminal endpoint rather than inventing a new one (Document 15's
`hold_scope` reuse precedent).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# CHG-FR-001: the change types Document 29 itself enumerates.
CHANGE_TYPES = (
    "product", "process", "recipe", "spec", "material", "source", "equipment", "facility", "software",
    "document", "method", "label", "supplier",
)

# CHG-FR-002: "Temporary/permanent" classification Document 29 itself names.
CHANGE_CLASSIFICATIONS = ("temporary", "permanent")

CHANGE_STATES = (
    "DRAFT", "IMPACT_ASSESSMENT", "APPROVAL", "IMPLEMENTATION", "VERIFICATION", "EFFECTIVE", "CLOSED", "CANCELLED",
)

NON_CANCELLABLE_STATES = ("CLOSED", "CANCELLED")

CHANGE_ALLOWED_TRANSITIONS: dict[str, set[str]] = {
    "DRAFT": {"IMPACT_ASSESSMENT"},
    "IMPACT_ASSESSMENT": {"IMPACT_ASSESSMENT", "APPROVAL"},
    "APPROVAL": {"IMPLEMENTATION"},
    # CHG-FR-014: the emergency path implements directly from DRAFT/IMPACT_ASSESSMENT, bypassing
    # pre-approval; the retrospective review is recorded later via approve() without a further state
    # transition (state has already moved on) -- see change_commands.py's implement_change()/
    # approve_change().
    "IMPLEMENTATION": {"IMPLEMENTATION", "VERIFICATION"},
    "VERIFICATION": {"EFFECTIVE"},
    "EFFECTIVE": {"CLOSED"},
    "CLOSED": set(),
    "CANCELLED": set(),
}

TASK_STATUSES = ("pending", "done")


class ChangeControl(Base):
    __tablename__ = "change_control"
    __table_args__ = (
        UniqueConstraint("quality_event_id"),
        UniqueConstraint("change_number"),
        Index("ix_change_control_state", "site_id", "state", "classification"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    quality_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    change_number: Mapped[str] = mapped_column(String(120), nullable=False)
    change_type: Mapped[str] = mapped_column(String(50), nullable=False)
    classification: Mapped[str] = mapped_column(String(40), nullable=False)
    current_state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    proposed_state: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT")
    owner_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    risk_ref: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    regulatory_impact: Mapped[dict | None] = mapped_column(JSONB)
    validation_impact: Mapped[dict | None] = mapped_column(JSONB)
    training_impact: Mapped[dict | None] = mapped_column(JSONB)
    impact_assessment: Mapped[dict | None] = mapped_column(JSONB)
    emergency: Mapped[bool] = mapped_column(nullable=False, default=False)
    emergency_reason: Mapped[str | None] = mapped_column(Text)
    retrospective_review: Mapped[dict | None] = mapped_column(JSONB)
    retrospective_review_completed: Mapped[bool] = mapped_column(nullable=False, default=False)
    effective_at: Mapped[datetime | None] = mapped_column()
    cancel_reason: Mapped[str | None] = mapped_column(Text)
    cancelled_at: Mapped[datetime | None] = mapped_column()
    closure_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()


class ChangeAffectedObject(Base):
    """Insert-only: CHG-FR-004's impact graph is additive evidence, never edited in place."""

    __tablename__ = "change_affected_object"
    __table_args__ = (
        Index("ix_change_affected_object_change", "change_id"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    change_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.change_control.id"), nullable=False)
    object_type: Mapped[str] = mapped_column(String(60), nullable=False)
    object_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    object_version: Mapped[int | None] = mapped_column()
    impact_category: Mapped[str] = mapped_column(String(60), nullable=False)
    action_required: Mapped[str] = mapped_column(Text, nullable=False)
    created_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ChangeTask(Base):
    __tablename__ = "change_task"
    __table_args__ = (
        Index("ix_change_task_change", "change_id"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    change_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.change_control.id"), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    owner_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    due_date: Mapped[datetime] = mapped_column(nullable=False)
    dependency_links: Mapped[list | None] = mapped_column(JSONB)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="pending")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    completed_at: Mapped[datetime | None] = mapped_column()
