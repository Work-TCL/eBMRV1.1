"""Document 33 (SPEC-QMS-008) — Risk Management. Same owner service as Documents 26-32
(`services/gxp-api/src/modules/qms`), so `risk_record` and `risk_assessment_version` are added to the
existing `qms` schema.

Both entities' field lists in docs/generated/04_DATA_MODEL_CATALOGUE.md are prose-only, but -- like
capa_action/ncr_disposition (SG-045's precedent) and scar_record/supplier_quality_case (Document 32) --
genuinely unambiguous: typed directly as an ordinary engineering decision.

State model (Document 33 §4), state names kept verbatim (slashes -> underscores):
`DRAFT -> INITIAL_ASSESSMENT -> CONTROLS_MITIGATION -> RESIDUAL_ASSESSMENT -> ACCEPTANCE_REVIEW ->
ACCEPTED -> PERIODIC_REVIEW / TRIGGERED_REVIEW -> NEW_VERSION`. Document 33's own 6-op API list is
shorter than this 9-state text, so the same fold-in pattern used throughout this module family applies:
  - ACCEPTANCE_REVIEW has no dedicated endpoint -- `accept()` (RSK-FR-007) represents entering and
    completing acceptance review in one step, the same way `review_scar()` folds SCAR's INTERNAL_REVIEW.
  - PERIODIC_REVIEW/TRIGGERED_REVIEW are not resting states: `review()` (RSK-FR-013/014) is the decision
    point itself, recording the review and moving ACCEPTED back to ACCEPTED (still current) or forward to
    NEW_VERSION (reassessment required). `trigger_type` on the command records which of the two applies.
  - NEW_VERSION is a resting state: it signals that `add_assessment()` must be called again to open a new
    assessment cycle (RSK-FR-012 versioning) -- it does not implicitly re-run assessment itself.

Versioning (RSK-FR-012, "never overwrite prior risk score when methodology changes" -- Document 33 §15):
each assessment cycle gets its own `risk_assessment_version` row (`cycle_number` incrementing). Within one
cycle, `add_assessment()` may update the SAME row in place for its initial->residual progression (the row
is not yet historical); once a review sends the risk to NEW_VERSION, that row is marked `is_current=False`
with `closed_at` set and is never edited again -- the next `add_assessment()` call creates a new row.

`methodology_id` (RSK-FR-002/015, "select approved risk methodology; formula/version controlled... no
universal hardcoded FMEA") is a real FK into the existing `rules.gxp_rule_definition` table (Document 08),
reused with `rule_type='risk_methodology'` rather than inventing a second methodology/matrix master --
AG-05 (one authoritative owner per entity). The methodology's `rule_object_id` + `semantic_version` are
snapshotted onto each `risk_assessment_version` at the moment it is bound, satisfying the Acceptance
Criteria text ("historical risk values remain reproducible under the exact methodology/version used at the
time") even if the referenced rule is later superseded.

Deferred this pass (see docs/generated/18_SPEC_GAPS.md SG-099/SG-100, same discipline as SG-091):
  - RSK-FR-007: no risk-level-tiered acceptance-authority escalation matrix (which role/how many approvers
    for LOW vs HIGH residual risk) is defined anywhere in the baseline. Acceptance is implemented as a
    single RBAC-gated action (`risk.accept`) plus a mandatory rationale, not a tiered escalation.
  - RSK-FR-009/010/014: cross-module automatic triggering (Deviation/OOS/Complaint/Audit auto-invoking a
    risk review; Change Control auto-requiring reassessment before its own approval) has no owning command
    to call yet -- this module exposes `review()` as a manually-invoked action any authorized caller can
    use, with an optional `trigger_source_ref` to record what quality event or change prompted it, but no
    other module command calls it automatically.
  - RSK-FR-018 (export) has no operation in Document 33's own 6-op API list; served by the existing
    generic audit export path (AUD-FR-022), same treatment as SCAR-FR-018 (SG-091).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# RSK-FR-001: "product/process/system/supplier/equipment/software" risk, verbatim from Document 33.
RISK_TYPES = ("product", "process", "system", "supplier", "equipment", "software")

RISK_RECORD_STATES = (
    "DRAFT",
    "INITIAL_ASSESSMENT",
    "CONTROLS_MITIGATION",
    "RESIDUAL_ASSESSMENT",
    "ACCEPTED",
    "NEW_VERSION",
)

REVIEW_TRIGGER_TYPES = ("periodic", "triggered")


class RiskRecord(Base):
    __tablename__ = "risk_record"
    __table_args__ = (
        UniqueConstraint("quality_event_id"),
        UniqueConstraint("risk_number"),
        Index("ix_risk_record_state", "site_id", "state", "risk_type"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    quality_event_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, default=uuid.uuid4)
    risk_number: Mapped[str] = mapped_column(String(120), nullable=False)
    risk_type: Mapped[str] = mapped_column(String(50), nullable=False)
    # RSK-FR-002/015: FK into the existing rules module (rule_type='risk_methodology'), not a new master.
    methodology_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("rules.gxp_rule_definition.rule_object_id")
    )
    # RSK-FR-011: object mapping -- product/version, recipe/step, equipment, supplier, software component.
    context: Mapped[dict | None] = mapped_column(JSONB)
    hazard_problem: Mapped[str] = mapped_column(Text, nullable=False)
    potential_effect: Mapped[str] = mapped_column(Text, nullable=False)
    owner_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    # RSK-FR-013: periodic review cycle -- next due date, surfaced by the dashboard's overdue flag
    # (RSK-FR-017). Set at accept()/review() time; no background scheduler exists in this codebase to
    # auto-detect overdue reviews (RISK_REVIEW_OVERDUE is declared in Document 33 §16 but no code path
    # raises it this pass, same "don't register a code nothing throws" discipline as SG-074/SG-088).
    next_review_due_at: Mapped[datetime | None] = mapped_column()
    state: Mapped[str] = mapped_column(String(50), nullable=False, default="DRAFT")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class RiskAssessmentVersion(Base):
    __tablename__ = "risk_assessment_version"
    __table_args__ = (
        UniqueConstraint("risk_record_id", "cycle_number"),
        Index("ix_risk_assessment_version_current", "risk_record_id", "is_current"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    risk_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.risk_record.id"), nullable=False)
    cycle_number: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # Snapshot of the methodology bound at the moment this cycle's initial assessment was recorded --
    # kept even if risk_record.methodology_id is later rebound for a subsequent cycle (RSK-FR-012).
    methodology_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    methodology_version: Mapped[str | None] = mapped_column(String(40))
    scoring_inputs: Mapped[dict | None] = mapped_column(JSONB)
    initial_score: Mapped[dict | None] = mapped_column(JSONB)
    # RSK-FR-005: preventive/detective controls + evidence.
    controls: Mapped[list | None] = mapped_column(JSONB)
    # RSK-FR-008: "Link CAPA/change/tasks" -- cross-referenced, not FK'd (same treatment as SCAR's
    # capa_required/capa_rationale flag: no owning command exists yet to enforce the link).
    mitigation_actions: Mapped[list | None] = mapped_column(JSONB)
    residual_inputs: Mapped[dict | None] = mapped_column(JSONB)
    residual_score: Mapped[dict | None] = mapped_column(JSONB)
    acceptance_criteria: Mapped[dict | None] = mapped_column(JSONB)
    # RSK-FR-007: "approver/signature" per Document 33's own field list -- captured as a structured
    # role/authority/rationale block; no actual e-signature ceremony is wired for accept() (see the module
    # docstring's deferred-scope note / SG-099: Document 106's register has no resolved row for it).
    acceptance: Mapped[dict | None] = mapped_column(JSONB)
    review_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_current: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()
