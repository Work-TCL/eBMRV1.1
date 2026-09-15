"""Document 60 (SPEC-PM-003) — Combination-Product Postmarket Regulatory Coordination, Information
Sharing & Regulatory Calendar. Same `postmarket` schema, 5 owned entities per Document 112 +
Document 60's own `# 10` (regulatory_obligation is Document 60's own 12-field entity, not Document 112's).

ADR-0006: `tenant_id` dropped throughout; `site_id` kept. No `retention_class` column beyond what
Document 60 itself asks this module to track as *data* (PMO-FR-025/026 -- see `retention_basis` below),
consistent with SG-005.

**`regulatory_obligation` is a generic obligation-tracking entity** covering Field Alert and BPDR tracks,
neither of which has its own dedicated table in the approved 5-entity list -- `obligation_type`
distinguishes PART4_SHARING/CORRECTION_REMOVAL_806/FIELD_ALERT/BPDR/PERIODIC_REPORT/FDA_REQUEST.
Document 60's own 12-field schema (`# 10`) has no content field for the type-specific facts PMO-FR-015
names ("distributed batches, issue type, facility, specifications/contamination/mix-up facts") -- `details`
(JSONB) is added directly, same "genuinely unambiguous, type directly" latitude used for
`qms.DeviationImpactLink` (SG-045's precedent) and Document 58's own `SafetyCase.seriousness_attributes`.
`decision`/`decision_rationale`/`decision_by`/`decision_signature_id` are likewise added for the two
obligation types that require an explicit reportability decision (CORRECTION_REMOVAL_806, FIELD_ALERT).

**PMO-FR-024 (deadline override) preserves `original_due_at`/`current_due_at` as distinct columns already
in Document 60's own schema** -- no extra history list is needed; `deadline_override_evidence` (JSONB)
records the agency evidence/authority/reason for the override itself.

**PMO-FR-025..028 (retention/hold) are stored as data on the obligation**, not derived from a numeric
retention table this codebase does not have (SG-005: no numeric retention periods are approved anywhere
in the baseline) -- `retention_basis` records the applicable regimes/rule versions/calculated durations/
selected-longest-rule structure Document 60 itself demands be transparent, without this module inventing
what those durations actually are.

**No Document 106 signature resolution exists for most of this module's actions.** Rows for
applicant-relationship configuration, Part 4 sharing evaluation/package creation, field-alert/BPDR
creation, periodic-cycle generation/freeze, FDA-request creation and retention calculation have no row at
all -- these stay open (SG-160). Rows 129/130 ("Authorized corrector + independent approver", count=2)
ARE built (2026-09-14, project-owner-directed): `assessment_approval_signatures`/
`decision_approval_signatures` below back a 2-signature chain reusing
`vault/commands.py::complete_correction()`'s own already-reviewed mechanism
(`signature_service.enforce_chain_signer_policy()`) -- SG-160's original claim that no multi-signature
mechanism existed anywhere in this codebase was already false when written. Row 131 ("Elevated authority
defined by the record class") remains open -- no dispatch table exists to resolve that phrase into an
actual role. See docs/generated/18_SPEC_GAPS.md SG-160 for the full remaining list.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

OBLIGATION_TYPES = (
    "PART4_SHARING", "CORRECTION_REMOVAL_806", "FIELD_ALERT", "BPDR", "PERIODIC_REPORT", "FDA_REQUEST",
)
OBLIGATION_STATES = ("OPEN", "CLOCK_SET", "DECIDED", "SUBMITTED", "CLOSED")
OBLIGATION_TRANSITIONS: dict[str, set[str]] = {
    "OPEN": {"CLOCK_SET", "DECIDED"},
    "CLOCK_SET": {"DECIDED"},
    "DECIDED": {"DECIDED", "SUBMITTED", "CLOSED"},
    "SUBMITTED": {"CLOSED"},
    "CLOSED": set(),
}

APPLICANT_ROLES = ("COMBINATION_PRODUCT_APPLICANT", "CONSTITUENT_PART_APPLICANT")
SHARE_STATES = ("PENDING", "SHARED", "FAILED", "ESCALATED")
CORRECTION_REGIMES = ("PART_806_REPORT", "PART_806_20_RECORD")
CORRECTION_ASSESSMENT_STATES = ("REPORTABLE", "NON_REPORTABLE")
CYCLE_TYPES = ("QUARTERLY", "ANNUAL", "FDA_CONFIGURED")
CYCLE_STATES = ("SCHEDULED", "DATA_COLLECTION", "FROZEN", "ANALYSIS", "APPROVED", "SUBMITTED", "ACK", "ARCHIVE")
CYCLE_TRANSITIONS: dict[str, set[str]] = {
    "SCHEDULED": {"DATA_COLLECTION"},
    "DATA_COLLECTION": {"FROZEN"},
    "FROZEN": {"ANALYSIS"},
    "ANALYSIS": {"APPROVED"},
    "APPROVED": {"SUBMITTED"},
    "SUBMITTED": {"ACK"},
    "ACK": {"ARCHIVE"},
    "ARCHIVE": set(),
}


class RegulatoryObligation(Base):
    __tablename__ = "regulatory_obligation"
    __table_args__ = (
        Index("ix_regulatory_obligation_type_due", "site_id", "obligation_type", "current_due_at"),
        {"schema": "postmarket"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    obligation_type: Mapped[str] = mapped_column(String(40), nullable=False)
    source_type: Mapped[str | None] = mapped_column(String(60))
    source_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    source_version: Mapped[int | None] = mapped_column()
    application_id: Mapped[str | None] = mapped_column(String(120))
    rule_version_id: Mapped[str | None] = mapped_column(String(40))
    clock_start_at: Mapped[datetime | None] = mapped_column()
    original_due_at: Mapped[datetime | None] = mapped_column()
    current_due_at: Mapped[datetime | None] = mapped_column()
    calendar_profile_id: Mapped[str | None] = mapped_column(String(40))
    # See module docstring -- type-specific facts (PMO-FR-015 etc.), never fabricated.
    details: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    decision: Mapped[str | None] = mapped_column(String(30))
    decision_rationale: Mapped[str | None] = mapped_column(Text)
    decision_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    decision_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    deadline_override_evidence: Mapped[dict | None] = mapped_column(JSONB)
    retention_basis: Mapped[dict | None] = mapped_column(JSONB)
    legal_hold: Mapped[bool] = mapped_column(nullable=False, default=False)
    legal_hold_reason: Mapped[str | None] = mapped_column(Text)
    legal_hold_authority: Mapped[str | None] = mapped_column(String(120))
    legal_hold_at: Mapped[datetime | None] = mapped_column()
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")
    owner_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ApplicantRelationship(Base):
    __tablename__ = "applicant_relationship"
    __table_args__ = {"schema": "postmarket"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    product_version_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    applicant_role: Mapped[str] = mapped_column(String(60), nullable=False)
    applicant_name: Mapped[str] = mapped_column(String(200), nullable=False)
    application_type: Mapped[str | None] = mapped_column(String(40))
    application_number: Mapped[str | None] = mapped_column(String(60))
    address: Mapped[dict] = mapped_column(JSONB, nullable=False)
    contact: Mapped[dict] = mapped_column(JSONB, nullable=False)
    sharing_channel: Mapped[str | None] = mapped_column(String(80))
    valid_from: Mapped[datetime] = mapped_column(server_default=func.now())
    valid_to: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)


class ConstituentInformationShare(Base):
    __tablename__ = "constituent_information_share"
    __table_args__ = (
        Index("ix_constituent_share_state_due", "site_id", "state", "due_at"),
        {"schema": "postmarket"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    safety_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("postmarket.safety_case.id"), nullable=False)
    applicant_relationship_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("postmarket.applicant_relationship.id"), nullable=False)
    applicant_relationship_version: Mapped[int] = mapped_column(nullable=False)
    company_receipt_at: Mapped[datetime] = mapped_column(nullable=False)
    due_at: Mapped[datetime] = mapped_column(nullable=False)
    package_content: Mapped[dict | None] = mapped_column(JSONB)
    package_digest: Mapped[str | None] = mapped_column(String(128))
    package_version: Mapped[int] = mapped_column(nullable=False, default=0)
    shared_at: Mapped[datetime | None] = mapped_column()
    shared_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    sharing_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    delivery_evidence: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="PENDING")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)


class CorrectionRemovalRegulatoryRecord(Base):
    __tablename__ = "correction_removal_regulatory_record"
    __table_args__ = (
        Index("ix_correction_removal_state_due", "site_id", "state", "due_at"),
        {"schema": "postmarket"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    field_action_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    assessment_state: Mapped[str | None] = mapped_column(String(40))
    regime: Mapped[str | None] = mapped_column(String(40))
    initiation_at: Mapped[datetime] = mapped_column(nullable=False)
    due_at: Mapped[datetime | None] = mapped_column()
    calendar_version: Mapped[str | None] = mapped_column(String(40))
    required_facts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    decision_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    decision_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    scope_amendments: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    retention_class_code: Mapped[str] = mapped_column(String(40), nullable=False, default="RC-806")
    # SG-160 partial resolution (2026-09-14): Document 106 rows 129/130 each require a 2-signature chain
    # ("Authorized corrector + independent approver") -- one for assessment creation (row 130), a separate
    # one for the reportability decision (row 129), tracked independently since they happen at different
    # points in this record's life. Same shape as vault.RecordCorrection.approved_by_signatures.
    assessment_approval_signatures: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    decision_approval_signatures: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # State machine: PENDING_ASSESSMENT_APPROVAL (create_correction_removal_assessment() has consumed
    # chain position 1; the record exists but is not yet usable) -> OPEN (assessment fully signed --
    # same meaning "OPEN" always had: assessment exists, no decision yet) -> PENDING_DECISION_APPROVAL
    # (decide_correction_removal_reportability() has consumed decision-chain position 1) -> DECIDED
    # (decision fully signed and applied: due_at computed, regime set).
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="PENDING_ASSESSMENT_APPROVAL")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)


class PeriodicReportingCycle(Base):
    __tablename__ = "periodic_reporting_cycle"
    __table_args__ = (UniqueConstraint("site_id", "application_reference", "cycle_type", "period_start"), {"schema": "postmarket"})

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    application_reference: Mapped[str] = mapped_column(String(120), nullable=False)
    cycle_type: Mapped[str] = mapped_column(String(40), nullable=False)
    period_start: Mapped[datetime] = mapped_column(nullable=False)
    period_end: Mapped[datetime] = mapped_column(nullable=False)
    data_cutoff_at: Mapped[datetime | None] = mapped_column()
    dataset_snapshot_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    inclusion_rules_version: Mapped[str | None] = mapped_column(String(40))
    part4_augmentation_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="SCHEDULED")
    approved_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    approval_signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    submission_reference: Mapped[dict | None] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
