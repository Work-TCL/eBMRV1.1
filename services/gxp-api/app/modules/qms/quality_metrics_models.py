"""Document 37 (SPEC-QMS-012) — Quality Metrics, Trending & Effectiveness Checks. Same owner service as
Documents 26-36 (`services/gxp-api/src/modules/qms`), so `quality_metric_definition`,
`quality_metric_snapshot` and `effectiveness_check` are added to the existing `qms` schema.

All three entities' field lists in docs/generated/04_DATA_MODEL_CATALOGUE.md are prose-only, but -- like
every prior module in this family (SG-045's precedent) -- genuinely unambiguous: typed directly as an
ordinary engineering decision. `formula_rule_id` is a nullable FK into the existing `rules.gxp_rule_definition`
(Document 08), reused the same way Document 33's `risk_record.methodology_id` reuses it (AG-05, no second
formula-authoring master).

State model (Document 37 §4): three independent lifecycles.
`METRIC: DRAFT -> RELEASED/EFFECTIVE -> SUPERSEDED`, `SNAPSHOT: CALCULATING -> COMPLETE -> APPROVED/FROZEN`,
`EFFECTIVENESS: PLANNED -> OBSERVATION -> EVALUATION -> PASS/FAIL/INCONCLUSIVE`. Document 37's own 7-op API
list folds several of these:
  - `release()` moves a metric definition DRAFT -> RELEASED, and (MET-FR-002 "no trend distortion")
    supersedes the PRIOR released version of the same `metric_code`, if one exists -- the old row is never
    edited, only its `state` moves to SUPERSEDED, preserving it for historical reproducibility.
  - `calculate()` creates a `quality_metric_snapshot` directly in COMPLETE state (CALCULATING is not a
    resting state reachable by any endpoint) -- MET-FR-023 ("late/corrected data... recalculation creates
    new snapshot/version") is satisfied by construction: every `calculate()` call inserts a NEW snapshot
    row, never updates an existing one.
  - There is no `quality_management_review_package` entity anywhere in
    docs/generated/04_DATA_MODEL_CATALOGUE.md for this document (only the 3 entities above are declared).
    `management_review_packages()` (MET-FR-016/023, "freeze periodic quality summary... prior approved
    package immutable") is implemented WITHOUT inventing a fourth table: it groups a caller-supplied list
    of already-COMPLETE `quality_metric_snapshot` rows under a shared `review_package_id` and moves them
    all to the already-declared terminal snapshot state `FROZEN` in one transaction -- reusing
    `quality_metric_snapshot.state`'s own "APPROVED/FROZEN" branch rather than a new entity.
  - `checks()` (create) lands an `effectiveness_check` directly in OBSERVATION (PLANNED is not a resting
    state reachable by any endpoint -- there is no separate "start observation" op); `evaluate()` moves
    OBSERVATION -> EVALUATION -> the terminal PASS/FAIL/INCONCLUSIVE state in one call.

Deferred this pass -- the central scoping decision for this module (see docs/generated/18_SPEC_GAPS.md
SG-107, and SG-108 for the smaller items):
  - MET-FR-003..011 (the nine metric families: deviation/CAPA/OOS-OOT/NCR/complaint/supplier/audit/
    training/batch-quality metrics) are NOT computed by this module's own code. `calculate()` accepts a
    caller-supplied `result` payload -- the actual cross-module aggregation query for each metric family
    (each would need deep read access into a different owning module's tables) is out of scope this pass.
    The definition/versioning/snapshot/reproducibility FRAMEWORK around those results (MET-FR-001/002/012/
    013/014/023/024) is fully real and enforced; the arithmetic inside `result` is not computed here.
  - MET-FR-017 (alert/escalation): `calculate()` accepts a caller-supplied `threshold_exceeded` flag and
    fires `QualityTrendThresholdExceeded`/`QualitySignalAssessmentOpened` when set, but there is no
    internal threshold-rule evaluation engine comparing `result` against `threshold_rule_ids` -- the
    caller must already know whether the threshold was exceeded.
  - MET-FR-015 (drilldown) has no dedicated enforcement; `result`/`scope` JSONB can carry source-record
    references at the caller's discretion, but there is no authorization-checked drilldown query path.
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

METRIC_DEFINITION_STATES = ("DRAFT", "RELEASED", "SUPERSEDED")

SNAPSHOT_STATES = ("COMPLETE", "FROZEN")

EFFECTIVENESS_STATES = ("OBSERVATION", "PASS", "FAIL", "INCONCLUSIVE")

EFFECTIVENESS_RESULTS = ("pass", "fail", "inconclusive")


class QualityMetricDefinition(Base):
    __tablename__ = "quality_metric_definition"
    __table_args__ = (
        UniqueConstraint("metric_code", "version_no"),
        Index("ix_quality_metric_definition_state", "site_id", "state", "metric_code"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    metric_code: Mapped[str] = mapped_column(String(120), nullable=False)
    version_no: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    # MET-FR-001: "owner" is required by the requirement text but not among the DM catalogue's 12 declared
    # fields -- added directly (SG-045's precedent for genuinely unambiguous additions).
    owner_subject_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"), nullable=False)
    source_model_id: Mapped[str] = mapped_column(String(120), nullable=False)
    numerator_definition: Mapped[dict] = mapped_column(JSONB, nullable=False)
    denominator_definition: Mapped[dict | None] = mapped_column(JSONB)
    formula_rule_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("rules.gxp_rule_definition.rule_object_id"))
    scope_dimensions: Mapped[dict | None] = mapped_column(JSONB)
    frequency: Mapped[str] = mapped_column(String(40), nullable=False)
    threshold_rule_ids: Mapped[list | None] = mapped_column(JSONB)
    effective_from: Mapped[datetime | None] = mapped_column()
    effective_to: Mapped[datetime | None] = mapped_column()
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="DRAFT")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class QualityMetricSnapshot(Base):
    __tablename__ = "quality_metric_snapshot"
    __table_args__ = (
        Index("ix_quality_metric_snapshot_definition", "metric_definition_id"),
        Index("ix_quality_metric_snapshot_package", "review_package_id"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    metric_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.quality_metric_definition.id"), nullable=False)
    period_start: Mapped[datetime] = mapped_column(nullable=False)
    period_end: Mapped[datetime] = mapped_column(nullable=False)
    scope: Mapped[dict | None] = mapped_column(JSONB)
    source_cutoff: Mapped[datetime] = mapped_column(nullable=False)
    result: Mapped[dict] = mapped_column(JSONB, nullable=False)
    formula_version: Mapped[str] = mapped_column(String(40), nullable=False)
    threshold_exceeded: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    # MET-FR-016/023: grouping key for a frozen management review package -- see module docstring for why
    # this reuses quality_metric_snapshot.state instead of a fourth, undeclared entity.
    review_package_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="COMPLETE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class EffectivenessCheck(Base):
    __tablename__ = "effectiveness_check"
    __table_args__ = (
        Index("ix_effectiveness_check_source", "source_module", "source_record_id"),
        Index("ix_effectiveness_check_state", "site_id", "state"),
        {"schema": "qms"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.sites.id"), nullable=False)
    # MET-FR-018: shared framework for CAPA/SCAR/field action -- source_module/source_record_id are an
    # unenforced polymorphic reference (no single owning table), same treatment as every cross-module
    # reference elsewhere in this codebase that doesn't have one fixed target type.
    source_module: Mapped[str] = mapped_column(String(40), nullable=False)
    source_record_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    criterion: Mapped[str] = mapped_column(Text, nullable=False)
    metric_definition_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("qms.quality_metric_definition.id"))
    observation_period_start: Mapped[datetime] = mapped_column(nullable=False)
    observation_period_end: Mapped[datetime] = mapped_column(nullable=False)
    due_date: Mapped[datetime | None] = mapped_column()
    result: Mapped[str | None] = mapped_column(String(20))
    evidence: Mapped[dict | None] = mapped_column(JSONB)
    reviewer_subject_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("iam.users.id"))
    # MET-FR-019: "escalate/reopen/new action according to source policy" -- flag+rationale, same
    # deferred-flag precedent as every prior module's cross-module trigger (SCAR/Audit/Complaint/Field
    # Action) rather than an owning escalation command call.
    escalation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    escalation_rationale: Mapped[str | None] = mapped_column(Text)
    next_observation_due: Mapped[datetime | None] = mapped_column()
    state: Mapped[str] = mapped_column(String(40), nullable=False, default="OBSERVATION")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    evaluated_at: Mapped[datetime | None] = mapped_column()
