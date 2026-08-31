"""Document 59 (SPEC-PM-002) — Regulatory Reportability Assessment & Electronic Safety Submission
Management. Same `postmarket` schema as Document 58 (both are SPEC-PM-00x modules of one work package),
4 owned entities per Document 112: `reportability_track`, `regulatory_report`,
`regulatory_submission_attempt`, `regulatory_submission_ack`.

ADR-0006: `tenant_id` dropped throughout; `site_id` kept. No `retention_class` column, consistent with
every other module (SG-005).

**Deadline calculation is caller-supplied duration, not hardcoded legal logic (REG-FR-003).** Document 59
explicitly forbids hardcoding "30 days"/"5 work days"/"15 days" as code -- report-type durations are
"effective-dated configuration" this codebase has no report-type-catalogue table for (not one of the 4
owned entities). `calculate_regulatory_deadline()` therefore takes `duration_days` and `calendar_type` as
explicit caller inputs (the caller resolves the actual number from whatever external/configured report-type
catalogue applies) and only performs the generic calendar arithmetic Document 59 itself names
(CALENDAR_DAY/WORK_DAY/WORKING_DAY/AGENCY_SPECIFIED) -- `rule_version` is carried through as pure
provenance, never evaluated by this module. WORK_DAY/WORKING_DAY exclude Saturday/Sunday only; no holiday
calendar is approved anywhere in the baseline (see docs/generated/18_SPEC_GAPS.md SG-158) so federal
holidays are not excluded -- a real, documented limitation, not a silent guess.

**No signature policy exists for `reportability_track.decide` or `regulatory_report.approve`**
(Document 106 rows 123-128 cover track creation, report creation, followups, payload generation and
submission, but not the decision itself; row 124's approver is "per record class" with no dispatch table
supplied). Both fail closed with SIGNATURE_POLICY_UNRESOLVED until Document 106 is amended. See SG-157.
"""

import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# Document 112's own comment list for reportability_track.report_type_code, plus FOLLOWUP for REG-FR-013.
REPORT_TYPE_CODES = (
    "MDR_30", "MDR_5", "MALFUNCTION", "DRUG_EXPEDITED_15", "BIOLOGIC_EXPEDITED_15", "PART4_30", "FOLLOWUP",
)

CLOCK_START_BASES = ("SOURCE_RECEIPT", "COMPANY_AWARENESS", "AGENCY_REQUEST")

# Document 58/59's own calendar vocabulary (PMS/REG-FR text + Document 112 schema comment).
CALENDAR_TYPES = ("CALENDAR_DAY", "WORK_DAY", "WORKING_DAY", "AGENCY_SPECIFIED")

DECISION_VALUES = ("REPORTABLE", "NOT_REPORTABLE")

TRACK_STATES = ("OPEN", "CLOCK_SET", "DECIDED", "CLOSED")
# REG-FR-004 (decision) and REG-FR-005 (clock start) are independent requirements Document 59 does not
# sequence -- deciding reportability does not require the deadline to already be calculated (a reviewer
# may reasonably decide REPORTABLE first and start the clock once that's settled, or the reverse).
TRACK_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"CLOCK_SET", "DECIDED"},
    "CLOCK_SET": {"DECIDED"},
    "DECIDED": {"DECIDED", "CLOSED"},
    "CLOSED": set(),
}

REPORT_STATES = ("DRAFT", "APPROVED", "SUBMITTED", "SUPERSEDED")

SUBMISSION_CHANNELS = ("EMDR", "ESG_NEXTGEN", "SRP", "MANUAL")
TRANSPORT_RESULTS = ("SENT", "FAILED", "TIMEOUT_UNCERTAIN")

ACK_LEVELS = ("TRANSPORT", "PROCESSING", "AGENCY_ACCEPTANCE")
ACK_STATES = ("ACCEPTED", "REJECTED", "PENDING")

# REG-FR-021: E2B is effective-dated config, not one permanent format -- the standard version is data
# the caller supplies per submission, never a hardcoded branch in this module's own code.
E2B_STANDARD_VERSIONS = ("R2", "R3")


class ReportabilityTrack(Base):
    __tablename__ = "reportability_track"
    __table_args__ = {"schema": "postmarket"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    safety_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("postmarket.safety_case.id"), nullable=False)
    report_type_code: Mapped[str] = mapped_column(String(80), nullable=False)
    report_type_version: Mapped[str] = mapped_column(String(40), nullable=False)
    application_context: Mapped[dict] = mapped_column(JSONB, nullable=False)
    clock_start_basis: Mapped[str | None] = mapped_column(String(80))
    clock_start_at: Mapped[datetime | None] = mapped_column()
    clock_start_rationale: Mapped[str | None] = mapped_column(Text)
    calendar_type: Mapped[str | None] = mapped_column(String(20))
    calendar_version: Mapped[str | None] = mapped_column(String(40))
    due_at: Mapped[datetime | None] = mapped_column()
    # REG-FR-005/Document 112: immutable once first calculated, even if a later correction changes due_at.
    original_due_at: Mapped[datetime | None] = mapped_column()
    decision: Mapped[str | None] = mapped_column(String(30))
    decision_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    decision_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    decision_rationale: Mapped[str | None] = mapped_column(Text)
    decision_evidence_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    rule_version: Mapped[str | None] = mapped_column(String(40))
    parent_track_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("postmarket.reportability_track.id"))
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RegulatoryReport(Base):
    __tablename__ = "regulatory_report"
    __table_args__ = (UniqueConstraint("reportability_track_id", "report_version"), {"schema": "postmarket"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    reportability_track_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("postmarket.reportability_track.id"), nullable=False)
    report_version: Mapped[int] = mapped_column(nullable=False)
    schema_code: Mapped[str] = mapped_column(String(60), nullable=False)
    schema_version: Mapped[str] = mapped_column(String(40), nullable=False)
    content: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # REG-FR-016: per-field source trace -- {field_name: {source_type, source_id, source_version}}.
    field_provenance: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # REG-FR-015: explicit unknown/not-obtained markers, never fabricated.
    missing_information: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    narrative_version: Mapped[int | None] = mapped_column()
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    approval_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    payload_digest: Mapped[str | None] = mapped_column(String(128))
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="DRAFT")
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RegulatorySubmissionAttempt(Base):
    __tablename__ = "regulatory_submission_attempt"
    __table_args__ = (UniqueConstraint("regulatory_report_id", "attempt_no"), {"schema": "postmarket"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    regulatory_report_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("postmarket.regulatory_report.id"), nullable=False)
    attempt_no: Mapped[int] = mapped_column(nullable=False)
    channel: Mapped[str] = mapped_column(String(60), nullable=False)
    endpoint_profile: Mapped[str | None] = mapped_column(String(120))
    payload_version: Mapped[str] = mapped_column(String(40), nullable=False)
    payload_digest: Mapped[str] = mapped_column(String(128), nullable=False)
    sender_identity: Mapped[str] = mapped_column(String(120), nullable=False)
    authorized_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    authorization_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    attempted_at: Mapped[datetime] = mapped_column(server_default=func.now())
    transport_result: Mapped[str] = mapped_column(String(30), nullable=False)
    failure_detail: Mapped[dict | None] = mapped_column(JSONB)
    manual_evidence_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))


class RegulatorySubmissionAck(Base):
    """Append-only -- REG-FR-019: transport success alone never sets AGENCY_ACCEPTANCE."""

    __tablename__ = "regulatory_submission_ack"
    __table_args__ = {"schema": "postmarket"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    submission_attempt_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("postmarket.regulatory_submission_attempt.id"), nullable=False)
    ack_level: Mapped[str] = mapped_column(String(30), nullable=False)
    ack_state: Mapped[str] = mapped_column(String(30), nullable=False)
    ack_reference: Mapped[str | None] = mapped_column(String(200))
    ack_payload: Mapped[dict | None] = mapped_column(JSONB)
    ack_received_at: Mapped[datetime] = mapped_column(server_default=func.now())
    rejection_reason: Mapped[dict | None] = mapped_column(JSONB)
