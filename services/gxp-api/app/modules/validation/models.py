"""WP-12 (Documents 79, 80, 81, 82, 83, 84, 86, 88, 89, 90, 91, 92, 93, 94, 96) -- new `validation`
PostgreSQL schema. Every table below is exactly the entity `04_DATA_MODEL_CATALOGUE.md` declares for
its source document, with the catalogue's terse field bullets expanded into concrete typed columns.

**No `tenant_id`** (ADR-0006, single-organization platform -- same deviation as every other module in
this codebase). `site_id` is kept nullable: most WP-12 records are platform/product-level (a Validation
Master Plan, a function risk assessment, a requirement) rather than site-scoped, but a customer
deployment's IQ/infrastructure/DR/interface qualification is naturally site-scoped, so the column is
present and enforced only where the record class is genuinely site-bound.

Every table carries `id, state, version, created_at, updated_at` (Doc 70 aggregate baseline minus the
dropped `tenant_id`). `version` is the Doc 70/MUT-FR-009 optimistic-concurrency bigint. Durations are
`BigInteger` seconds, sizes/counts `BigInteger`, coverage/percentage metrics are `BigInteger` basis
points (never `float`, never a bare percent) -- same numeric-integrity discipline as every other module.

Retention/legal-hold periods are **not** assigned a numeric value here: Document 108 supplies retention
*classes*, not this table's own default period, and no approved baseline gives WP-12 evidence a
concrete number of years (SG-005, already open). `retention_class` is a free-text label column callers
can populate from Document 108's controlled catalogue; enforcement of an actual purge schedule against
it is out of scope for this pass (same posture as every other module carrying SG-005).
"""

import uuid
from datetime import datetime

from sqlalchemy import BigInteger, Boolean, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

SCHEMA = "validation"


def _pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)


# =====================================================================================================
# Document 79 (SPEC-VAL-001) -- Validation Master Plan & Computer Software Assurance Strategy
# =====================================================================================================

VMP_STATES = ("DRAFT", "RELEASED", "SUPERSEDED")


class ValidationMasterPlan(Base):
    """VAL-FR-001..008/023/025/027: the single controlled VMP/CSA strategy document, versioned and
    released like every other controlled record in this codebase (never edited in place once released
    -- a change creates a new DRAFT that supersedes it)."""

    __tablename__ = "validation_master_plan"
    __table_args__ = (UniqueConstraint("plan_number", "version"), {"schema": SCHEMA})

    id: Mapped[uuid.UUID] = _pk()
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    plan_number: Mapped[str] = mapped_column(String(60), nullable=False)
    scope: Mapped[str] = mapped_column(Text, nullable=False)
    regulatory_profiles: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    methodology: Mapped[str] = mapped_column(Text, nullable=False)
    responsibilities: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    retention_class: Mapped[str | None] = mapped_column(String(80))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    released_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    released_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class ValidationDeliverableRequirement(Base):
    """VAL-FR-006/008: one required artifact class for a plan -- artifact type, the risk condition that
    makes it required, owner, whether it needs review/signature, evidence type and whether missing it
    blocks release (VAL-FR-020/024)."""

    __tablename__ = "validation_deliverable_requirement"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    plan_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    artifact_type: Mapped[str] = mapped_column(String(80), nullable=False)
    risk_condition: Mapped[str] = mapped_column(String(200), nullable=False)
    owner: Mapped[str] = mapped_column(String(120), nullable=False)
    review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    signature_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    evidence_type: Mapped[str] = mapped_column(String(80), nullable=False)
    release_blocker: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="REQUIRED")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class ValidationReleaseGate(Base):
    """VAL-FR-020/024: the recorded gate decision evaluated at a release attempt -- release/config/
    environment scope, which required artefacts were satisfied vs. outstanding (`blockers`), and the
    decision references (VSR/change/deviation IDs) the decision relied on. Written by
    `release_master_plan()` at the moment a release is attempted (Document 79 declares only a GET for
    this entity -- see `commands_plan.py` module docstring for why the write happens there)."""

    __tablename__ = "validation_release_gate"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    release_scope: Mapped[str] = mapped_column(String(120), nullable=False)
    environment: Mapped[str] = mapped_column(String(80), nullable=False)
    required_artifact_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    blockers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    decision_refs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EVALUATED")  # EVALUATED | PASSED | BLOCKED
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 80 (SPEC-VAL-002) -- Intended Use, GxP Criticality & Software Function Risk Classification
# =====================================================================================================

DETECTABILITY_LEVELS = ("LOW", "MEDIUM", "HIGH")
AUTOMATION_ROLES = ("enforcement_gating", "calculation", "enforcement", "advisory", "informational")
RISK_CATEGORIES = ("HIGHER-PROCESS-RISK", "STANDARD-RISK")
ASSURANCE_METHODS = (
    "scripted, independently reviewed, mandatory negative/failure evidence",
    "hybrid/unscripted with automated regression evidence",
)


class IntendedUse(Base):
    """RISK-FR-001/007/008/009: documented intended use at system/module/function/deployment level --
    the regulated process affected, the users, and whether the function creates/touches a predicate-rule
    record or a legally binding signature (Part 11 scope input for Document 88)."""

    __tablename__ = "intended_use"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    scope_ref: Mapped[str] = mapped_column(String(160), nullable=False)  # system | module:X | function:Y
    scope_version: Mapped[str] = mapped_column(String(40), nullable=False)
    regulated_process: Mapped[str] = mapped_column(Text, nullable=False)
    users: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    record_relevance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    signature_relevance: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class FunctionRiskAssessment(Base):
    """RISK-FR-002..006/010/011/017/019/020: risk classification for one function/version. `risk_category`
    and `assurance_method` are **mechanically derived** at creation from the caller-declared inputs using
    Document 111 section 1's own approved derivation rule (never invented -- see
    `commands_risk.py::_derive_risk_category`), not a free-text opinion field."""

    __tablename__ = "function_risk_assessment"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    function_ref: Mapped[str] = mapped_column(String(160), nullable=False)
    function_version: Mapped[str] = mapped_column(String(40), nullable=False)
    failure_modes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    impacts: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    detectability: Mapped[str] = mapped_column(String(10), nullable=False)
    automation_role: Mapped[str] = mapped_column(String(30), nullable=False)
    has_release_or_disposition: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_signature_role: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_audit_immutability_role: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    has_enforcement_role: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    controls: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    risk_category: Mapped[str] = mapped_column(String(30), nullable=False)
    assurance_method: Mapped[str] = mapped_column(Text, nullable=False)
    residual_risk: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")  # DRAFT | APPROVED
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 81 (SPEC-VAL-003) -- Requirements, Design Inputs & Validation Traceability Management
# =====================================================================================================


class ValidationRequirement(Base):
    """REQ-FR-001/002/004/005/011: one stable requirement -- source doc/section/version, class,
    regulatory-source binding status, and its own current version (superseded requirements stay
    retained, never deleted -- REQ-FR-011)."""

    __tablename__ = "validation_requirement"
    __table_args__ = (UniqueConstraint("requirement_code", "version"), {"schema": SCHEMA})

    id: Mapped[uuid.UUID] = _pk()
    requirement_code: Mapped[str] = mapped_column(String(40), nullable=False)  # e.g. BAT-FR-003
    source_document: Mapped[str] = mapped_column(String(80), nullable=False)
    source_section: Mapped[str] = mapped_column(String(120), nullable=False)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    requirement_class: Mapped[str] = mapped_column(String(40), nullable=False)
    regulatory_source: Mapped[str | None] = mapped_column(String(120))
    binding_status: Mapped[str] = mapped_column(String(20), nullable=False, default="BINDING")  # BINDING | GUIDANCE
    acceptance_criteria: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")  # EFFECTIVE | SUPERSEDED
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


TRACE_LINK_TYPES = ("RISK", "DESIGN", "TEST", "DEFECT")


class TraceLink(Base):
    """REQ-FR-006..009/013: one edge in the traceability graph -- source artifact/version to target
    artifact/version plus the relation type. `source_type`/`target_type` name the artifact class
    (requirement, function_risk_assessment, function_catalogue_entry, validation_test_definition,
    validation_exception, ...) since links cross multiple owning tables."""

    __tablename__ = "trace_link"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    source_type: Mapped[str] = mapped_column(String(60), nullable=False)
    source_id: Mapped[str] = mapped_column(String(120), nullable=False)
    source_version: Mapped[str] = mapped_column(String(40), nullable=False)
    target_type: Mapped[str] = mapped_column(String(60), nullable=False)
    target_id: Mapped[str] = mapped_column(String(120), nullable=False)
    target_version: Mapped[str] = mapped_column(String(40), nullable=False)
    relation_type: Mapped[str] = mapped_column(String(20), nullable=False)  # TRACE_LINK_TYPES
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class RequirementBaseline(Base):
    """REQ-FR-010/021: a frozen, hashed set of requirement versions in scope for one release/customer,
    with excluded requirements and their rationale (REQ-FR-020's SPEC_GAP-as-tracked-exclusion). Freezing
    also evaluates traceability gaps (REQ-FR-014) -- see `commands_trace.py::freeze_requirement_baseline`."""

    __tablename__ = "requirement_baseline"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    release_scope: Mapped[str] = mapped_column(String(120), nullable=False)
    customer_scope: Mapped[str | None] = mapped_column(String(120))
    requirement_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # [{code, version}]
    exclusions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # [{code, rationale}]
    baseline_hash: Mapped[str] = mapped_column(String(64), nullable=False)
    vault_object_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    gaps_detected: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="FROZEN")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 82 (SPEC-VAL-004) -- Validation Test Strategy, Test Methods & Objective Evidence Governance
# =====================================================================================================

TEST_METHODS = ("AUTOMATED", "SCRIPTED_MANUAL", "EXPLORATORY", "REVIEW_INSPECTION", "ANALYSIS", "SUPPLIER_EVIDENCE")
EXECUTION_STATUSES = ("IN_PROGRESS", "PASS", "FAIL", "BLOCKED", "SKIPPED")


class ValidationTestDefinition(Base):
    """TST-FR-001..007: one versioned, immutable-once-approved test definition -- method, requirement/
    risk links, preconditions/data, procedure or exploratory charter, expected results and the review
    rule (independent review required or not, per VMP/risk -- TST-FR-011/017)."""

    __tablename__ = "validation_test_definition"
    __table_args__ = (UniqueConstraint("test_code", "version"), {"schema": SCHEMA})

    id: Mapped[uuid.UUID] = _pk()
    test_code: Mapped[str] = mapped_column(String(40), nullable=False)
    method: Mapped[str] = mapped_column(String(30), nullable=False)  # TEST_METHODS
    requirement_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    preconditions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    procedure: Mapped[str] = mapped_column(Text, nullable=False)
    expected_results: Mapped[str] = mapped_column(Text, nullable=False)
    independent_review_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")  # DRAFT | APPROVED | SUPERSEDED
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class ValidationTestExecution(Base):
    """TST-FR-008..010/013..016/018/020..022: one executed run against the exact test/environment --
    tester or CI identity, observations, final status, evidence manifest and defect/deviation links.
    A failure is never overwritten (TST-FR-013): a retest is a new row, never an edit of this one."""

    __tablename__ = "validation_test_execution"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    test_definition_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    test_definition_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    environment_fingerprint: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    performer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    ci_run_ref: Mapped[str | None] = mapped_column(String(200))
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column()
    observations: Mapped[str | None] = mapped_column(Text)
    actual_result: Mapped[str | None] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")  # EXECUTION_STATUSES
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    evidence_manifest: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    defect_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column()
    flaky: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 83 (SPEC-VAL-005) -- Installation Qualification (IQ) & Installed Baseline Verification
# =====================================================================================================


class IqProtocol(Base):
    """IQ-FR-001..002/004/005: the expected installation baseline for an environment/release/deployment
    profile -- expected components, checks to run and acceptance criteria."""

    __tablename__ = "iq_protocol"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    environment: Mapped[str] = mapped_column(String(80), nullable=False)
    release_ref: Mapped[str] = mapped_column(String(80), nullable=False)
    deployment_profile: Mapped[str] = mapped_column(String(40), nullable=False)  # cloud | private_cloud | on_prem
    expected_components: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    checks: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class IqExecution(Base):
    """IQ-FR-003/006..018/020: one executed IQ run -- the installed-inventory fingerprint actually
    captured, per-check results, deviations raised for any mismatch (IQ-FR-018: no silent variance) and
    the evidence manifest."""

    __tablename__ = "iq_execution"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    protocol_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    protocol_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    installed_inventory: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    check_results: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    deviations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evidence_manifest: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    performer_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    completed_at: Mapped[datetime | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")  # IN_PROGRESS|PASS|FAIL
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column()
    is_delta_iq: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 84 (SPEC-VAL-006) -- Operational Qualification (OQ) & Functional Control Verification
# =====================================================================================================


class OqSuite(Base):
    """OQ-FR-001/012/013/016: the selected set of tests/automated evidence forming one OQ suite against
    a baseline, with any exclusion and its rationale, and the environment fingerprint the suite runs
    against."""

    __tablename__ = "oq_suite"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    baseline_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)  # requirement_baseline.id
    selected_test_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    selected_evidence_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    exclusions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # [{ref, rationale}]
    environment_fingerprint: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DERIVED")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class OqExecution(Base):
    """OQ-FR-002..011/014..018: one OQ execution against a suite version -- the test refs actually
    executed, coverage (basis points of higher-risk requirements in the suite with objective evidence,
    OQ-FR-016), deviations and approval."""

    __tablename__ = "oq_execution"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    suite_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    suite_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    executed_test_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    coverage_basis_points: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    deviations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column()
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 86 (SPEC-VAL-008) -- Infrastructure, Cloud, Platform & Environment Qualification
# =====================================================================================================


class InfrastructureQualificationProfile(Base):
    """INFQ-FR-001..003/017/020: the qualified baseline for one deployment/provider -- required
    components and their approved config ranges, the control tests that verify them, supplier-evidence
    references and the change triggers that force requalification."""

    __tablename__ = "infrastructure_qualification_profile"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    deployment_profile: Mapped[str] = mapped_column(String(40), nullable=False)  # cloud|private_cloud|on_prem
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    required_components: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    control_tests: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    supplier_evidence_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    change_triggers: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class InfrastructureFingerprint(Base):
    """INFQ-FR-004..016/018/019: one captured fingerprint of the actual running infrastructure --
    component versions, config hashes, resource sizing and network/security/time/backup references --
    compared against its profile's `required_components` to detect drift (INFQ-FR-018)."""

    __tablename__ = "infrastructure_fingerprint"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    captured_versions: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    config_hashes: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    resource_sizing: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    network_security_refs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    time_backup_refs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    drift_detected: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    drift_detail: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="CAPTURED")  # CAPTURED|APPROVED
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 88 (SPEC-VAL-010) -- 21 CFR Part 11 Electronic Records & Electronic Signature Validation
# =====================================================================================================


class Part11ScopeAssessment(Base):
    """P11-FR-001/024/025: identifies one record or signature type relied upon electronically under
    predicate rules -- predicate use, the owning system component, whether the deployment/use context is
    open or closed, applicability and customer-responsibility notes."""

    __tablename__ = "part11_scope_assessment"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    record_or_signature_type: Mapped[str] = mapped_column(String(120), nullable=False)
    predicate_use: Mapped[str] = mapped_column(Text, nullable=False)
    system_component: Mapped[str] = mapped_column(String(120), nullable=False)
    context: Mapped[str] = mapped_column(String(10), nullable=False, default="CLOSED")  # CLOSED | OPEN
    applicable: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    customer_responsibilities: Mapped[str | None] = mapped_column(Text)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class Part11ControlEvidence(Base):
    """P11-FR-002..023/026: one objective verification of one §11.10/11.50/11.70/11.100/11.200 control
    citation -- the test/result/evidence produced, the configuration/procedure it verified and any
    deviation raised. The control matrix (P11-FR-026) is this table filtered by scope assessment."""

    __tablename__ = "part11_control_evidence"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    scope_assessment_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    control_citation: Mapped[str] = mapped_column(String(20), nullable=False)  # e.g. "11.10(e)"
    test_ref: Mapped[str | None] = mapped_column(String(120))
    result: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")  # IN_PROGRESS|PASS|FAIL
    evidence_manifest: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    configuration_ref: Mapped[str | None] = mapped_column(String(200))
    procedure_ref: Mapped[str | None] = mapped_column(String(200))
    deviation_ref: Mapped[str | None] = mapped_column(String(120))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")  # DRAFT|APPROVED
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 89 (SPEC-VAL-011) -- Audit Trail, Record Version Vault & Data Integrity Validation
# =====================================================================================================


class DataIntegrityTestProfile(Base):
    """DIV-FR-001..024 (profile half): one data class's lifecycle, the integrity threats it faces
    (tamper, loss, reorder, silent overwrite) and the controls/tests that verify each."""

    __tablename__ = "data_integrity_test_profile"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    data_class: Mapped[str] = mapped_column(String(80), nullable=False)
    lifecycle: Mapped[str] = mapped_column(Text, nullable=False)
    threats: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    controls: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    tests: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class TamperTestExecution(Base):
    """DIV-FR-003..005: one controlled, isolated tamper/removal/reorder simulation against a snapshot --
    the tamper action performed, the verifier (hash-chain/checkpoint) version used to check it, and
    whether detection succeeded. `detected=False` on a genuine tamper attempt is a critical finding, not
    a passing result -- see `commands_integrity.py`."""

    __tablename__ = "tamper_test_execution"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    isolated_snapshot_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    tamper_action: Mapped[str] = mapped_column(String(80), nullable=False)  # e.g. reorder, delete, edit
    verifier_version: Mapped[str] = mapped_column(String(40), nullable=False)
    detected: Mapped[bool | None] = mapped_column(Boolean)
    detection_evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    performed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 90 (SPEC-VAL-012) -- Integration, Edge, Device, Peripheral & Interface Validation
# =====================================================================================================


class InterfaceValidationProfile(Base):
    """IFV-FR-001..007: one interface's validation scope -- provider/device, the exact contract/mapping
    version under test, intended use/risk, and the auth/source/time/quality expectations plus declared
    failure scenarios (IFV-FR-023's simulator inputs)."""

    __tablename__ = "interface_validation_profile"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    provider_or_device: Mapped[str] = mapped_column(String(120), nullable=False)
    contract_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    contract_version: Mapped[str] = mapped_column(String(40), nullable=False)
    intended_use: Mapped[str] = mapped_column(Text, nullable=False)
    risk_category: Mapped[str] = mapped_column(String(30), nullable=False)  # RISK_CATEGORIES
    auth_expectation: Mapped[str] = mapped_column(String(80), nullable=False)
    source_time_quality_expectation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    failure_scenarios: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class InterfaceTestExecution(Base):
    """IFV-FR-008..022: one interface test run -- inputs/raw payloads, canonical outputs, the resulting
    GxP-side effect and any external reconciliation performed (IFV-FR-021)."""

    __tablename__ = "interface_test_execution"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    profile_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    profile_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    scenario: Mapped[str] = mapped_column(String(80), nullable=False)  # e.g. duplicate, out_of_order, edge_outage
    raw_inputs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    canonical_outputs: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    gxp_result: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    external_reconciliation: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    performed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 91 (SPEC-VAL-013) -- Backup, Restore, PITR & Disaster Recovery Qualification
# =====================================================================================================


class DrQualificationScenario(Base):
    """DRV-FR-001: one DR scenario -- failure type, the components it exercises, the recovery method,
    target RPO/RTO (seconds -- never invented, read from `disaster_recovery.recovery_objective_profile`
    at scenario definition time per component, Document 76/109), restore order and acceptance
    criteria."""

    __tablename__ = "dr_qualification_scenario"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    failure_type: Mapped[str] = mapped_column(String(80), nullable=False)
    components: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    recovery_method: Mapped[str] = mapped_column(String(80), nullable=False)
    target_rpo_seconds: Mapped[int | None] = mapped_column(BigInteger)
    target_rto_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False)
    restore_order: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    acceptance_criteria: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="EFFECTIVE")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class DrQualificationExecution(Base):
    """DRV-FR-002..021: one executed DR qualification drill -- the backup set/restore point used, the
    *measured* achieved RPO/RTO (never invented -- computed from timestamps the same way
    `disaster_recovery.commands.execute_postgres_restore_test` does), integrity/GxP-smoke results and
    deviations if the achieved objective misses the scenario's target."""

    __tablename__ = "dr_qualification_execution"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scenario_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    backup_set_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    restore_point: Mapped[datetime | None] = mapped_column()
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column()
    rpo_achieved_seconds: Mapped[int | None] = mapped_column(BigInteger)
    rto_achieved_seconds: Mapped[int | None] = mapped_column(BigInteger)
    integrity_checks: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    gxp_smoke_results: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    deviations: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 92 (SPEC-VAL-014) -- Security Qualification, Vulnerability Verification & Penetration Testing
# =====================================================================================================


class SecurityQualificationSuite(Base):
    """SECQ-FR-001/017/023: one security qualification suite for a release/deployment -- the Documents
    61-68 threat/control baseline in scope and the planned tests."""

    __tablename__ = "security_qualification_suite"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    release_ref: Mapped[str] = mapped_column(String(80), nullable=False)
    deployment_profile: Mapped[str] = mapped_column(String(40), nullable=False)
    threat_control_baseline_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    planned_tests: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="PLANNED")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


FINDING_SEVERITIES = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
FINDING_STATES = ("OPEN", "RETEST", "ACCEPTED_WITH_EXCEPTION", "CLOSED")


class SecurityQualificationFinding(Base):
    """SECQ-FR-002..016/018..022/024: one finding from a control test, scan or pen test -- source,
    control violated, severity, affected release, links to vulnerability/change/deviation records and
    retest/exception state. SECQ-FR-020: an OPEN CRITICAL/HIGH finding blocks release (see
    `commands_security.py::evaluate_security_gate`)."""

    __tablename__ = "security_qualification_finding"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    suite_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    source: Mapped[str] = mapped_column(String(40), nullable=False)  # SAST|SCA|IAC|CONTAINER|PENTEST|MANUAL
    control_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)  # FINDING_SEVERITIES
    affected_release: Mapped[str] = mapped_column(String(80), nullable=False)
    vulnerability_ref: Mapped[str | None] = mapped_column(String(120))
    change_ref: Mapped[str | None] = mapped_column(String(120))
    deviation_ref: Mapped[str | None] = mapped_column(String(120))
    state: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")  # FINDING_STATES
    exception_rationale: Mapped[str | None] = mapped_column(Text)
    retest_ref: Mapped[str | None] = mapped_column(String(120))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 93 (SPEC-VAL-015) -- Performance, Load, Capacity & Reliability Qualification
# =====================================================================================================


class PerformanceQualificationScenario(Base):
    """PERFQ-FR-001/005/006/023: one performance scenario -- release/environment, the user/process load
    model and data cardinality it targets, planned duration and the thresholds it will be judged
    against (traced to NFR/SLO requirement IDs -- PERFQ-FR-021)."""

    __tablename__ = "performance_qualification_scenario"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    release_ref: Mapped[str] = mapped_column(String(80), nullable=False)
    environment: Mapped[str] = mapped_column(String(80), nullable=False)
    load_model: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    data_cardinality: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    planned_duration_seconds: Mapped[int] = mapped_column(BigInteger, nullable=False)
    thresholds: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    nfr_requirement_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="PLANNED")
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class PerformanceRun(Base):
    """PERFQ-FR-002..004/007..020/022/024: one executed performance run against a scenario -- the
    build/config under test, harness identity, measured metrics/traces/errors/resource use, and the
    headroom/bottleneck evaluation against the scenario's thresholds."""

    __tablename__ = "performance_run"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    scenario_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    scenario_version: Mapped[int] = mapped_column(BigInteger, nullable=False)
    build_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    harness_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    started_at: Mapped[datetime] = mapped_column(nullable=False)
    completed_at: Mapped[datetime | None] = mapped_column()
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    errors: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    resource_usage: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    headroom_basis_points: Mapped[int | None] = mapped_column(BigInteger)
    bottleneck: Mapped[str | None] = mapped_column(String(120))
    acceptance_result: Mapped[str] = mapped_column(String(20), nullable=False, default="IN_PROGRESS")  # ..PASS|FAIL
    performed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 94 (SPEC-VAL-016) -- Validation Defect, Deviation, Test Exception & Remediation Management
# =====================================================================================================

VEX_TYPES = ("DEFECT", "TEST_FAILURE", "PROTOCOL_DEVIATION", "ENVIRONMENT_DEVIATION", "EVIDENCE_ISSUE", "REQUIREMENT_GAP")
VEX_DISPOSITIONS = ("OPEN", "FIX", "RETEST", "ACCEPTED_WITH_RATIONALE", "DEFERRED_BLOCKING", "CLOSED")


class ValidationException(Base):
    """VEX-FR-001..022: one validation exception -- its type, the source execution it came from,
    affected requirements, severity/GxP/release impact, disposition state machine (VEX-FR-014), root
    cause, fix/issue/change links, retest plan and reopen history. `original_evidence` is captured once
    at creation and never edited (VEX-FR-003) -- corrections happen by adding new fields/annotations,
    never by mutating this snapshot."""

    __tablename__ = "validation_exception"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    release_ref: Mapped[str | None] = mapped_column(String(80))  # VEX-FR-016/022: release-blocker scope
    exception_type: Mapped[str] = mapped_column(String(30), nullable=False)  # VEX_TYPES
    source_execution_type: Mapped[str] = mapped_column(String(60), nullable=False)  # e.g. validation_test_execution
    source_execution_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    original_evidence: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    affected_requirement_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    severity: Mapped[str] = mapped_column(String(10), nullable=False)  # FINDING_SEVERITIES
    gxp_impact: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    release_impact: Mapped[str] = mapped_column(String(20), nullable=False, default="BLOCKING")  # BLOCKING|NON_BLOCKING
    disposition: Mapped[str] = mapped_column(String(30), nullable=False, default="OPEN")  # VEX_DISPOSITIONS
    root_cause: Mapped[str | None] = mapped_column(Text)
    issue_ref: Mapped[str | None] = mapped_column(String(200))
    change_ref: Mapped[str | None] = mapped_column(String(120))
    qms_deviation_ref: Mapped[str | None] = mapped_column(String(120))
    retest_plan: Mapped[dict | None] = mapped_column(JSONB)
    retest_execution_refs: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    residual_risk_rationale: Mapped[str | None] = mapped_column(Text)
    reopen_history: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    # SG-167 (resolved): Document 106 rows 162/164/165 require create/triage/retest_plan to be signed
    # `Approved` by "Elevated authority defined by the record class" -- resolved to this codebase's
    # `QA Releaser` role (the established release/disposition-family default, same role already seeded
    # for row 163's disposition signature) -- and "MUST be independent of the requester" is enforced by
    # comparing the signing actor against this column, the same `requested_by_user_id`-vs-`actor_user_id`
    # pattern already used identically in `material/commands.py`, `supplier_quality/commands.py` and
    # `lims_integration/commands.py`. Nullable at the DB level (safe additive column on a table with no
    # other consumers yet); every new row created via `create_exception()` always populates it.
    requested_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    triaged_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    triaged_at: Mapped[datetime | None] = mapped_column()
    dispositioned_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    dispositioned_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


# =====================================================================================================
# Document 96 (SPEC-VAL-018) -- Periodic Review, Change Impact, Revalidation & Validated-State Maintenance
# =====================================================================================================

REVALIDATION_LEVELS = ("NONE_WITH_RATIONALE", "DOC_REVIEW", "TARGETED_TEST", "PARTIAL", "FULL_REQUALIFICATION")
VALIDATED_STATE_DECISIONS = ("VALIDATED_CONFIRMED", "ACTION_REQUIRED", "REVALIDATION_REQUIRED", "SUSPENDED")


class ValidatedStateBaseline(Base):
    """VSM-FR-001/024/026: the current inventory of software/services/config/rules/interfaces/
    infrastructure/procedures that are in the validated state for one release/environment, with the VSR
    reference (Document 95, out of WP-12 scope) it was validated under."""

    __tablename__ = "validated_state_baseline"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    release_ref: Mapped[str] = mapped_column(String(80), nullable=False)
    environment: Mapped[str] = mapped_column(String(80), nullable=False)
    vsr_ref: Mapped[str | None] = mapped_column(String(120))
    component_inventory: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="VALIDATED")  # VALIDATED|DECOMMISSIONED
    decommissioned_at: Mapped[datetime | None] = mapped_column()
    decommission_evidence: Mapped[dict | None] = mapped_column(JSONB)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class ValidationChangeImpact(Base):
    """VSM-FR-002/003/004/006..010: one change-impact assessment -- the change reference, every trace
    artifact it touches (requirements/tests/interfaces/data/security/performance/SOP/training) and the
    proportionate revalidation level this assessment recommends, with rationale (never a blanket full
    regression by default -- VSM-FR-006)."""

    __tablename__ = "validation_change_impact"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    change_ref: Mapped[str] = mapped_column(String(120), nullable=False)
    change_type: Mapped[str] = mapped_column(String(40), nullable=False)  # code|config|infra|interface|data|patch
    affected_trace_artifacts: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    is_emergency: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    revalidation_level: Mapped[str] = mapped_column(String(30), nullable=False)  # REVALIDATION_LEVELS
    rationale: Mapped[str] = mapped_column(Text, nullable=False)
    revalidation_ref: Mapped[str | None] = mapped_column(String(120))
    completed_at: Mapped[datetime | None] = mapped_column()
    approved_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    approved_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class PeriodicValidationReview(Base):
    """VSM-FR-011..023/025/027: one periodic validated-state review -- the period covered, every input
    category considered (changes/incidents/CAPA/defects/vulnerabilities/DR/performance/access/vendor-EOL/
    audit trends), findings, follow-up actions and the explicit decision (VSM-FR-021)."""

    __tablename__ = "periodic_validation_review"
    __table_args__ = ({"schema": SCHEMA},)

    id: Mapped[uuid.UUID] = _pk()
    release_ref: Mapped[str] = mapped_column(String(80), nullable=False)
    period_start: Mapped[datetime] = mapped_column(nullable=False)
    period_end: Mapped[datetime] = mapped_column(nullable=False)
    inputs_considered: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    findings: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    actions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)  # [{owner, due_date, ref}]
    decision: Mapped[str | None] = mapped_column(String(30))  # VALIDATED_STATE_DECISIONS
    performed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_by_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    reviewed_at: Mapped[datetime | None] = mapped_column()
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")  # DRAFT|DECIDED
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())
