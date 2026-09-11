"""Document 34 (SPEC-QMS-009) — Internal Audit Management. Same owner service as Documents 26-33
(`services/gxp-api/src/modules/qms`), so `internal_audit` and `audit_finding` are added to the existing
`qms` schema. Named `internal_audit_*` (not `audit_*`) to avoid any confusion with the unrelated
`app/modules/audit` package, which is the Document 05 audit LEDGER (`audit.audit_events`) -- an entirely
different table in a different schema.

Both entities' field lists in docs/generated/04_DATA_MODEL_CATALOGUE.md are prose-only, but -- like every
prior module in this family (SG-045's precedent) -- genuinely unambiguous: typed directly as an ordinary
engineering decision.

State model (Document 34 §4): `PLANNED -> SCHEDULED -> IN_PROGRESS -> REPORT_DRAFT -> REPORT_APPROVED ->
FINDINGS_OPEN -> FOLLOW_UP -> CLOSED`. Document 34's own 6-op API list is far shorter than this 8-state
text, so the same fold-in pattern used throughout this module family applies:
  - PLANNED has no distinguishing data from SCHEDULED (both are just "the plan as captured at create
    time") and no dedicated endpoint separates them, so `create_internal_audit()` lands directly in
    SCHEDULED (AUDIT-FR-001/002).
  - REPORT_DRAFT and REPORT_APPROVED are not resting states reachable by any endpoint: the first
    `add_finding()` call on an audit still IN_PROGRESS represents "the report exists and is approved
    enough to record findings against it" and moves the audit straight to FINDINGS_OPEN, firing
    `AuditReportApproved` once as a secondary event on that same command (AUDIT-FR-010).
  - FOLLOW_UP is operationally identical to FINDINGS_OPEN in this build (both mean "the audit has open
    work: findings being responded to and verified") and is not modelled as a distinct state value --
    `respond_to_finding()` and `verify_finding()` both operate while the audit is in FINDINGS_OPEN.

Auditor independence (AUDIT-FR-003, "policy prevents auditor from auditing own direct work/function") is
enforced concretely only for the literal case a real check can be typed without inventing data: an
`auditees` list is captured on `internal_audit`, and `lead_auditor_id`/any `team` member appearing in that
list is rejected (`AUDITOR_SOD_CONFLICT`). The broader "own function/department" case cannot be checked --
no department/function-ownership model exists anywhere in this codebase to compare against (see
docs/generated/18_SPEC_GAPS.md SG-102).

Deferred this pass (see SG-101, same discipline as SG-097):
  - AUDIT-FR-008 (CAPA link): `capa_required`/`capa_rationale` flag+rationale on the finding response,
    matching every prior QMS module's precedent (SG-067 etc.) -- does not call
    `capa_commands.create_capa()`.
  - AUDIT-FR-012 (reschedule/cancel), AUDIT-FR-015 (metrics) and AUDIT-FR-017 (export) have no operation
    in Document 34's own 6-op API list -- reschedule/metrics are simply not exposed this pass; export is
    served by the existing generic audit export path (AUD-FR-022), same treatment as SCAR-FR-018/
    RSK-FR-018.
  - AUDIT-FR-016 (external audit tracking): no `external_audit`-shaped entity exists anywhere in
    `docs/generated/04_DATA_MODEL_CATALOGUE.md` for Document 34 (only `internal_audit`/`audit_finding` are
    declared) -- genuinely nothing to type without inventing a schema.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

INTERNAL_AUDIT_STATES = ("SCHEDULED", "IN_PROGRESS", "FINDINGS_OPEN", "CLOSED")

FINDING_STATES = ("OPEN", "RESPONSE_SUBMITTED", "VERIFIED")


class InternalAudit(Base):
    __tablename__ = "internal_audit"
    __table_args__ = (
        UniqueConstraint("quality_event_id"),
        UniqueConstraint("audit_number"),
        Index("ix_internal_audit_state", "site_id", "state"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    quality_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    audit_number: Mapped[str] = mapped_column(String(120), nullable=False)
    program_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    site_scope: Mapped[dict | None] = mapped_column(JSONB)
    process_scope: Mapped[dict | None] = mapped_column(JSONB)
    criteria_refs: Mapped[dict] = mapped_column(JSONB, nullable=False)
    lead_auditor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    team: Mapped[list | None] = mapped_column(JSONB)
    # AUDIT-FR-003: the narrow, concretely-typeable half of "auditor independence" -- see module docstring.
    auditees: Mapped[list | None] = mapped_column(JSONB)
    scheduled_at: Mapped[datetime] = mapped_column(nullable=False)
    actual_start_at: Mapped[datetime | None] = mapped_column()
    actual_end_at: Mapped[datetime | None] = mapped_column()
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="SCHEDULED")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AuditFinding(Base):
    __tablename__ = "audit_finding"
    __table_args__ = (
        UniqueConstraint("finding_number"),
        Index("ix_audit_finding_audit", "audit_id"),
        Index("ix_audit_finding_requirement_ref", "requirement_ref"),
        Index("ix_audit_finding_state", "site_id", "state"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    audit_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.internal_audit.id"), nullable=False)
    finding_number: Mapped[str] = mapped_column(String(120), nullable=False)
    requirement_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    observation: Mapped[str] = mapped_column(Text, nullable=False)
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    severity: Mapped[str] = mapped_column(String(50), nullable=False)
    owner_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    due_date: Mapped[datetime | None] = mapped_column()
    response: Mapped[dict | None] = mapped_column(JSONB)
    # AUDIT-FR-008 -- deferred flag+rationale, see module docstring / SG-101.
    capa_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    capa_rationale: Mapped[str | None] = mapped_column(Text)
    # AUDIT-FR-014: computed at creation time by matching requirement_ref against prior findings.
    is_repeat_finding: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    verification: Mapped[dict | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="OPEN")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()
