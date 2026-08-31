"""Document 35 (SPEC-QMS-010) — Complaint Management. Same owner service as Documents 26-34
(`services/gxp-api/src/modules/qms`), so `complaint_record`, `complaint_reportability_assessment` and
`complaint_communication` are added to the existing `qms` schema.

All three entities' field lists in docs/generated/04_DATA_MODEL_CATALOGUE.md are prose-only, but -- like
every prior module in this family (SG-045's precedent) -- genuinely unambiguous: typed directly as an
ordinary engineering decision.

State model (Document 35 §4):
`RECEIVED -> TRIAGE -> INVESTIGATION_DECISION -> (NO_INVESTIGATION_JUSTIFIED | INVESTIGATION) ->
REPORTABILITY_ASSESSMENT -> CAPA/FIELD_ACTION if required -> RESPONSE -> QA_CLOSURE -> CLOSED`. Document
35's own 7-op API list is shorter than this text, so the same fold-in pattern used throughout this module
family applies:
  - INVESTIGATION_DECISION is not a resting state: `investigation_decision()` is the decision point itself,
    landing directly on NO_INVESTIGATION_JUSTIFIED or INVESTIGATION (CMP-FR-007/008).
  - `investigation()` is a single decisive call (findings + conclusion), not an iterative one: it moves
    INVESTIGATION straight to REPORTABILITY_ASSESSMENT (CMP-FR-009/010/011 folded into one `findings` jsonb
    bundle -- batch/device/QC/deviation/material/equipment/service/returned-product references are
    unenforced JSONB, not FKs into those owning modules' tables, same treatment as RiskRecord.context/
    AuditFinding.evidence).
  - `reportability()` is reachable from EITHER branch: from NO_INVESTIGATION_JUSTIFIED directly (a
    no-investigation complaint can still need a reportability determination, CMP-FR-012 is a "separate
    authorized assessment" independent of whether an investigation happened), or from
    REPORTABILITY_ASSESSMENT (the state `investigation()` already lands on). Its own resting state is named
    "RESPONSE" (matching the spec's next listed step) since `investigation-decision`/`investigation` do
    the actual reportability work.
  - "CAPA/FIELD_ACTION if required" is not a resting state: `capa_required`/`field_action_required` flags
    + rationale are captured on `reportability()`'s call, matching every prior QMS module's CAPA-flag
    precedent (SCAR/Audit) -- no owning command is called.
  - QA_CLOSURE is not a separate resting state from CLOSED: `close()` performs it in one step.

`complaint_communication` serves BOTH CMP-FR-003 (acknowledgment) and CMP-FR-019 (response) -- there is no
separate acknowledge endpoint in Document 35's own 7-op list, so `POST /qms/v1/complaints/{id}/response` is
the one mechanism for logging any outbound/inbound communication, differentiated by a `communication_type`
field ("acknowledgment" | "response" | "update"). It is callable at any state except CLOSED and never
mutates `complaint_record.state` itself.

Deferred this pass (see docs/generated/18_SPEC_GAPS.md SG-103/SG-104, same discipline as SG-097/SG-101):
  - CMP-FR-011 (genealogy lookup), CMP-FR-016 (trend), CMP-FR-017/018 (CAPA/field-action -- flag+rationale
    only, no owning command called) and CMP-FR-024 (export, served by the generic audit export path) have
    no operation in Document 35's own 7-op API list, or (genealogy) no cross-module call wired.
  - CMP-FR-013/014/015: the DATA CAPTURE half is real (`applicable_regimes`/`submission_reference`/
    `submission_status` on `complaint_reportability_assessment`); the external MDR/eMDR/FAERS/Part 4 PMSR
    SUBMISSION integration itself does not exist (WP-07 territory).
  - CMP-FR-022 (privacy): no field-level encryption/redaction mechanism exists in this codebase for
    complainant PII beyond ordinary RBAC-gated table access -- see SG-104.
"""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# CMP-FR-001: the intake medium, verbatim from Document 35.
SOURCE_CHANNELS = ("oral", "written", "electronic")

# CMP-FR-005, verbatim from Document 35.
CONSTITUENT_CLASSIFICATIONS = ("drug", "device", "interface", "combination", "packaging", "label", "usability", "unknown")

COMPLAINT_STATES = (
    "RECEIVED",
    "TRIAGE",
    "NO_INVESTIGATION_JUSTIFIED",
    "INVESTIGATION",
    "REPORTABILITY_ASSESSMENT",
    "RESPONSE",
    "CLOSED",
)

COMMUNICATION_DIRECTIONS = ("inbound", "outbound")
COMMUNICATION_TYPES = ("acknowledgment", "response", "update")


class ComplaintRecord(Base):
    __tablename__ = "complaint_record"
    __table_args__ = (
        UniqueConstraint("quality_event_id"),
        UniqueConstraint("complaint_number"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    quality_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    complaint_number: Mapped[str] = mapped_column(String(120), nullable=False)
    received_at: Mapped[datetime] = mapped_column(nullable=False)
    source_channel: Mapped[str] = mapped_column(String(40), nullable=False)
    # CMP-FR-004: unresolved product/lot/serial goes to a reconciliation queue -- nullable, no FK-enforced
    # requirement to be resolved at intake time.
    product_ref: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("ebmr.gxp_product_version.id"))
    lot_batch_serial_refs: Mapped[dict | None] = mapped_column(JSONB)
    # CMP-FR-002/022: complainant contact + reporter_type, kept as one JSONB blob per Document 35's own
    # "complainant_ref/encrypted_fields" field pairing -- see module docstring / SG-104 on field encryption.
    complainant_info: Mapped[dict | None] = mapped_column(JSONB)
    nature_code: Mapped[str] = mapped_column(String(100), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    constituent_classification: Mapped[str | None] = mapped_column(String(60))
    triage: Mapped[dict | None] = mapped_column(JSONB)
    investigation_required: Mapped[bool | None] = mapped_column(Boolean)
    no_investigation_reason: Mapped[str | None] = mapped_column(Text)
    investigation_findings: Mapped[dict | None] = mapped_column(JSONB)
    investigation_conclusion: Mapped[str | None] = mapped_column(Text)
    # CMP-FR-023: link without deleting/blocking the original intake.
    is_potential_duplicate: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    related_complaint_ids: Mapped[list | None] = mapped_column(JSONB)
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="RECEIVED")
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()


class ComplaintReportabilityAssessment(Base):
    __tablename__ = "complaint_reportability_assessment"
    __table_args__ = {"schema": "qms"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    complaint_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.complaint_record.id"), nullable=False)
    # CMP-FR-013/014/015: multiple constituent/application reporting regimes, e.g. ["FDA_MDR","FAERS","PART4_PMSR"].
    applicable_regimes: Mapped[list] = mapped_column(JSONB, nullable=False)
    assessment_inputs: Mapped[dict | None] = mapped_column(JSONB)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    trigger_date: Mapped[datetime | None] = mapped_column()
    due_date: Mapped[datetime | None] = mapped_column()
    reviewer_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    submission_reference: Mapped[str | None] = mapped_column(String(200))
    submission_status: Mapped[str | None] = mapped_column(String(60))
    # CMP-FR-017/018 -- deferred flag+rationale, see module docstring / SG-103.
    capa_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    capa_rationale: Mapped[str | None] = mapped_column(Text)
    field_action_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    field_action_rationale: Mapped[str | None] = mapped_column(Text)
    version: Mapped[int] = mapped_column(nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class ComplaintCommunication(Base):
    __tablename__ = "complaint_communication"
    __table_args__ = {"schema": "qms"}

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    complaint_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.complaint_record.id"), nullable=False)
    direction: Mapped[str] = mapped_column(String(20), nullable=False)
    communication_type: Mapped[str] = mapped_column(String(20), nullable=False)
    recipient: Mapped[str | None] = mapped_column(String(200))
    channel: Mapped[str | None] = mapped_column(String(40))
    occurred_at: Mapped[datetime] = mapped_column(nullable=False)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    reference: Mapped[str | None] = mapped_column(String(200))
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
