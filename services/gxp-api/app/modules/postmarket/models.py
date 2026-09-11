"""Document 58 (SPEC-PM-001) — Postmarket Surveillance, Safety Case & Signal Management. New module,
new `postmarket` schema.

ADR-0006: `tenant_id` dropped throughout (single-organization platform, same precedent as every module
built since WP-05); `site_id` kept. Document 108 retention classes are not numerically defined anywhere
in the approved baseline (SG-005, already tracked platform-wide) so no `retention_class` column is typed
here either -- consistent with every other module in this codebase.

**SG-154 — `postmarket_source` field-set conflict between Document 58 and Document 112.** Document 58's
own Data Model section (`# 6`) gives `postmarket_source` a channel-registry shape matching its own
`registerPostmarketSource()` signature exactly: `source_type, organization_or_system, channel,
ingestion_profile_id, state, version`. Document 112's addendum gives a table of the *same name* a
completely different, instance-level intake shape (`source_record_reference, source_receipt_at,
reporter_details, product_resolution, identity_resolution_state, citation, ...`). These are not a
superset/subset of each other -- they describe two different concerns under one name. Per CLAUDE.md's
precedence order Documents 02-105 outrank Documents 106-115, and Document 58's own detailed `safety_case`
schema (`# 6`) already carries `source_receipt_at`/`company_initial_receipt_at`/`system_ingested_at`,
so this module resolves the conflict by: (a) keeping `postmarket_source` as Document 58's channel-registry
shape, and (b) placing Document 112's intake-level fields (`product_resolution`, `identity_resolution_state`,
`reporter_details`, `citation`, `external_reference`) on `safety_case` instead, since Document 58's own
PMS-FR-004/005/026/029 require exactly that data to live somewhere and `safety_case` -- not the channel
registry -- is where a per-case fact belongs. Not blocking; a Platform Architect can retitle/move these
columns without changing any command behaviour. See docs/generated/18_SPEC_GAPS.md SG-154.

**Safety case state model** (Document 58 `# 5`) branches after `INITIAL_CLASSIFICATION` into concurrent
concerns (`FOLLOWUP_PENDING`, `REPORTABILITY_ASSESSMENT_REQUIRED`, `SIGNAL_MONITORING`) that are not
mutually exclusive in practice -- a case can simultaneously await a follow-up AND need a Document 59
reportability track. Modelled here as one linear spine (`RECEIVED -> IDENTITY_RESOLUTION ->
INITIAL_CLASSIFICATION -> CLOSED_FOR_SURVEILLANCE`, `state`) plus independent boolean/JSONB flags for the
concurrent concerns (`reassessment_required`, `reportability_referral_required`) rather than forcing three
concurrent facts into one exclusive enum column -- an ordinary engineering decision, not a guess about
regulated behaviour. `CLOSED_FOR_SURVEILLANCE` has no corresponding operation in Document 58's own 11-op
API list (same shape as several QMS Document-26 diagram states with no reachable op) and is therefore
unreachable this pass -- noted, not a SPEC_GAP.

**Classification versioning** (PMS-FR-016/017): Document 58 gives `safety_case` a `current_classification_
version` counter and a single `constituent_classification` field but only 4 owned entities exist for this
module -- there is no separate `safety_classification` table. Every `classifySafetyCase()` call appends the
prior value onto `classification_history` (append-only JSONB list, same discipline as
`qms.DeviationRecord.closure_history`) and overwrites `constituent_classification`/
`current_classification_version` with the new one, so no classification judgment is ever destroyed.

**No dedicated metric/dataset table** (PMS-FR-018/019/020/032): `04_DATA_MODEL_CATALOGUE.md` lists exactly
4 owned entities for SPEC-PM-001, none of them a metric or periodic-dataset table. `calculateSurveillanceMetric()`
and `buildPeriodicSafetyDataset()` persist their immutable snapshots through `vault_service.release_master()`
instead (AG-08/AG-12: Vault already owns "immutable, hash-controlled, versioned snapshot of arbitrary
content" as a cross-cutting concern) -- see commands.py's module docstring. This satisfies "historical
metric formula version remains reproducible" for real, without a new owned table.

Not built this pass: PMS-FR-020's statistical/business signal rules have no engine or formula baseline
anywhere in this codebase to evaluate against (`app.modules.rules` evaluates a single record against a
numeric limit, not a population trend); `evaluateSignalRules()` computes the one trigger it can do
honestly without guessing a severity/frequency model -- same-source-record-type recurrence (2+ cases).
See docs/generated/18_SPEC_GAPS.md SG-155 for the full signal-rule-formula gap.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# PMS-FR-001: Document 58's own enumerated source types.
POSTMARKET_SOURCE_TYPES = (
    "COMPLAINT", "SERVICE", "REPAIR", "LITERATURE", "REGULATOR", "DISTRIBUTOR",
    "FIELD_ACTION", "MANUFACTURING", "QC", "STUDY",
)

# PMS-FR-005: identity resolution never discards unknowns.
IDENTITY_RESOLUTION_STATES = ("RESOLVED", "UNKNOWN_QUEUE")

# PMS-FR-012: DDCP constituent attribution.
CONSTITUENT_ATTRIBUTIONS = (
    "DRUG", "BIOLOGIC", "DEVICE", "INTERFACE", "PACKAGING_LABEL", "USER_INTERACTION", "UNKNOWN",
)

# Document 58 # 5 -- safety_case linear spine (see module docstring for the concurrency-flag decision).
SAFETY_CASE_STATES = ("RECEIVED", "IDENTITY_RESOLUTION", "INITIAL_CLASSIFICATION", "CLOSED_FOR_SURVEILLANCE")
SAFETY_CASE_TRANSITIONS: dict[str, set[str]] = {
    "RECEIVED": {"IDENTITY_RESOLUTION"},
    "IDENTITY_RESOLUTION": {"INITIAL_CLASSIFICATION"},
    "INITIAL_CLASSIFICATION": {"INITIAL_CLASSIFICATION", "CLOSED_FOR_SURVEILLANCE"},
    "CLOSED_FOR_SURVEILLANCE": set(),
}

# PMS-FR-023 exact state list; MONITORING loops back to ASSESSMENT per Document 58 # 5's own diagram.
SIGNAL_STATES = ("DETECTED", "TRIAGE", "ASSESSMENT", "REFUTED", "MONITORING", "CONFIRMED", "ACTION", "CLOSED")
SIGNAL_TRANSITIONS: dict[str, set[str]] = {
    "DETECTED": {"TRIAGE"},
    "TRIAGE": {"ASSESSMENT"},
    "ASSESSMENT": {"REFUTED", "MONITORING", "CONFIRMED"},
    "REFUTED": {"CLOSED"},
    "MONITORING": {"ASSESSMENT"},
    "CONFIRMED": {"ACTION"},
    "ACTION": {"CLOSED"},
    "CLOSED": set(),
}

SIGNAL_DETECTION_SOURCES = ("RULE", "REVIEWER")

# PMS-FR-024: escalation targets Document 58 itself names.
ESCALATION_TARGET_MODULES = ("CAPA", "CHANGE_CONTROL", "RISK_REVIEW", "FIELD_ACTION", "REPORTABILITY_TRACK")


class PostmarketSource(Base):
    """Channel/registry entity (PMS-FR-001) -- see module docstring SG-154 for why this is the
    channel-registry shape and not the instance-level intake shape.
    """

    __tablename__ = "postmarket_source"
    __table_args__ = (
        Index("ix_postmarket_source_type", "site_id", "source_type"),
        {"schema": "postmarket"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    source_type: Mapped[str] = mapped_column(String(40), nullable=False)
    organization_or_system: Mapped[str] = mapped_column(String(200), nullable=False)
    channel: Mapped[str] = mapped_column(String(120), nullable=False)
    ingestion_profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    owner_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="ACTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SafetyCase(Base):
    __tablename__ = "safety_case"
    __table_args__ = (
        UniqueConstraint("safety_case_number"),
        Index("ix_safety_case_source", "source_record_type", "source_record_id", "source_record_version"),
        Index("ix_safety_case_state", "site_id", "state"),
        {"schema": "postmarket"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    safety_case_number: Mapped[str] = mapped_column(String(120), nullable=False)
    # PMS-FR-002: reference only -- never a second editable copy of the owning QMS/service record.
    source_record_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source_record_version: Mapped[int] = mapped_column(nullable=False)
    source_receipt_at: Mapped[datetime | None] = mapped_column()
    company_initial_receipt_at: Mapped[datetime | None] = mapped_column()
    regulatory_clock_candidate_at: Mapped[datetime | None] = mapped_column()
    system_ingested_at: Mapped[datetime] = mapped_column(server_default=func.now())
    # PMS-FR-004/005 -- product resolution and the never-discarded unknown-identity queue.
    marketed_product_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    application_profile_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    product_resolution: Mapped[dict | None] = mapped_column(JSONB)
    identity_resolution_state: Mapped[str] = mapped_column(String(30), nullable=False, default="UNKNOWN_QUEUE")
    # PMS-FR-029: minimum-necessary, pseudonymised reporter/patient identifiers.
    reporter_details: Mapped[dict | None] = mapped_column(JSONB)
    # PMS-FR-026/027: literature citation / external authority reference.
    citation: Mapped[dict | None] = mapped_column(JSONB)
    external_reference: Mapped[str | None] = mapped_column(String(200))
    # PMS-FR-007..012: structured, non-deciding seriousness/device/drug/manufacturing/constituent inputs.
    seriousness_attributes: Mapped[dict | None] = mapped_column(JSONB)
    constituent_attribution: Mapped[str | None] = mapped_column(String(30))
    # PMS-FR-016/017: current classification + append-only version history (see module docstring).
    constituent_classification: Mapped[dict | None] = mapped_column(JSONB)
    classification_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    current_classification_version: Mapped[int] = mapped_column(nullable=False, default=0)
    # PMS-FR-014/015: duplicate detection/linking without destructive merge.
    canonical_case_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("postmarket.safety_case.id"))
    duplicate_link_rationale: Mapped[str | None] = mapped_column(Text)
    # Concurrency flags for Document 58 # 5's branching states -- see module docstring.
    reassessment_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    reportability_referral_required: Mapped[bool] = mapped_column(nullable=False, default=False)
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="RECEIVED")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SafetyCaseFollowup(Base):
    """Append-only -- PMS-FR-016: every material follow-up is an immutable version."""

    __tablename__ = "safety_case_followup"
    __table_args__ = (
        UniqueConstraint("safety_case_id", "followup_no"),
        Index("ix_safety_case_followup_case", "safety_case_id", "followup_no"),
        {"schema": "postmarket"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    safety_case_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("postmarket.safety_case.id"), nullable=False)
    followup_no: Mapped[int] = mapped_column(nullable=False)
    followup_receipt_at: Mapped[datetime] = mapped_column(nullable=False)
    source_reference: Mapped[dict] = mapped_column(JSONB, nullable=False)
    new_information: Mapped[dict] = mapped_column(JSONB, nullable=False)
    reassessment_flags: Mapped[dict] = mapped_column(JSONB, nullable=False)
    # PMS-FR-017: exact labeling/reference-safety-information version used for expectedness, if applicable.
    expectedness_reference: Mapped[dict | None] = mapped_column(JSONB)
    recorded_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    recorded_at: Mapped[datetime] = mapped_column(server_default=func.now())


class SafetySignal(Base):
    __tablename__ = "safety_signal"
    __table_args__ = (
        UniqueConstraint("site_id", "signal_code"),
        Index("ix_safety_signal_state", "site_id", "state"),
        {"schema": "postmarket"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    signal_code: Mapped[str] = mapped_column(String(120), nullable=False)
    detection_source: Mapped[str] = mapped_column(String(40), nullable=False)
    rule_version: Mapped[str | None] = mapped_column(String(40))
    trigger_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    population_definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    exposure_denominator: Mapped[dict | None] = mapped_column(JSONB)
    denominator_uncertain: Mapped[bool] = mapped_column(nullable=False, default=False)
    # PMS-FR-021: frozen case/evidence snapshot at open time -- never re-read live.
    case_snapshot: Mapped[dict] = mapped_column(JSONB, nullable=False)
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    # PMS-FR-022: append-only assessment version history (same discipline as classification_history).
    assessment: Mapped[dict | None] = mapped_column(JSONB)
    assessment_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="DETECTED")
    # PMS-FR-024: CAPA / Change / Risk / Field Action / reportability-track cross-links.
    escalation_links: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    owner_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    opened_at: Mapped[datetime] = mapped_column(server_default=func.now())
    closed_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
