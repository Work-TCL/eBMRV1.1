"""Document 105 (SPEC-AI-001) -- AI Governance for Regulated Manufacturing.

New `ai_governance` PostgreSQL schema. **The source specification and the WP-13 sub-prompt's own "DATA
MODEL (0 entities)" / "APIS (0)" / "EVENTS (0)" lines are a Phase-0 generation gap, not a deliberate
zero-storage design** -- resolved the same way Document 76/78's internal event-name inconsistencies were
resolved in WP-11: the more specific, operationally-detailed source wins. Here that source is
`docs/generated/03_FUNCTION_CATALOGUE.csv` (FN-1005..FN-1017), which is unambiguous for all 13 functions:
"single PostgreSQL transaction: domain + version + audit + outbox (MUT-FR-015)", a named output type, and
a named emitted event. A function that commits a MUT-FR-015 transaction and returns `AIUseCase` needs an
`AIUseCase` row to commit. `04_DATA_MODEL_CATALOGUE.md` / `05_DATABASE_OWNERSHIP_MATRIX.md` /
`06_API_CATALOGUE.yaml` / `07_EVENT_CATALOGUE.yaml` have no SPEC-AI-001 rows at all (checked) -- an
incomplete Phase-0 artefact, not a contradiction to resolve against. See `ARCHITECTURE.md` for the full
reasoning and the location decision (this module lives in `services/gxp-api/app/modules/ai_governance/`,
reusing the existing Mutation Gateway/audit/outbox/signature kernel, not a standalone `services/ai-gateway`
microservice -- MUT-FR-015's single-PostgreSQL-transaction requirement cannot span two separate services).

Every table below maps directly to one function's stated Inputs/Output in the function catalogue; no
field was invented beyond what that catalogue (or the requirement text it cites) already states. Three
tables are genuinely mutable aggregates with optimistic-concurrency `version` (`ai_use_case`,
`ai_model_deployment`, `ai_tool_registry`); the rest are append-only records of something that happened
(evaluation ran, a tool call was allowed/denied, a human disposed of an advisory) and are create-once.

No `tenant_id` (ADR-0006). `site_id` is nullable -- AI governance records are not all site-scoped (a
use-case or model deployment may be org-wide).
"""

import uuid
from datetime import date, datetime

from sqlalchemy import BigInteger, Boolean, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.core.db import Base

# AI-FR-002
USE_CASE_CLASSES = (
    "DEVELOPMENT_ASSISTANT", "DOCUMENT_ASSISTANT", "SEARCH_SUMMARY", "ANALYTICS_ADVISORY",
    "OPERATOR_ADVISORY", "QUALITY_ADVISORY", "REGULATORY_ADVISORY",
)
USE_CASE_STATES = ("DRAFT", "RISK_ASSESSED", "ACTIVE", "RETIRED")
# AI-FR-011
DATA_CLASSIFICATIONS = ("GxP", "PII", "CONFIDENTIAL", "SECURITY", "PUBLIC")
DEPLOYMENT_TYPES = ("CLOUD_API", "PRIVATE", "ON_PREM")
DEPLOYMENT_STATES = ("APPROVED", "SUSPENDED", "RETIRED")
TOOL_RISK_CLASSES = ("READ", "WRITE_LOW_RISK")
ADVISORY_STATES = ("GENERATED", "INVALID", "UNAVAILABLE")
TOOL_DECISIONS = ("ALLOWED", "DENIED")
# AI-FR-034 disposition values (source function catalogue FN-1011)
DISPOSITIONS = ("ACCEPTED_AS_INPUT", "REJECTED", "EDITED", "NOT_USED")
RELEASE_GATE_DECISIONS = ("PASS", "BLOCK", "REVIEW")


class AIUseCase(Base):
    """FN-1005 `registerAIUseCase()` / FN-1016 `retireAIUseCase()` -- AI-FR-001/002/053. The one
    genuinely mutable use-case aggregate; risk assessment and retirement bump `version` on this row."""

    __tablename__ = "ai_use_case"
    __table_args__ = (
        Index("ix_ai_use_case_state", "state"),
        {"schema": "ai_governance"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    site_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    use_case_class: Mapped[str] = mapped_column(String(30), nullable=False)
    purpose: Mapped[str] = mapped_column(Text, nullable=False)
    users: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    data_classes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    decision_impact: Mapped[str] = mapped_column(Text, nullable=False)
    proposed_tools: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    proposed_models: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="DRAFT")
    latest_risk_assessment_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    retirement_reason: Mapped[str | None] = mapped_column(Text)
    retirement_replacement: Mapped[str | None] = mapped_column(String(200))
    retirement_effective_date: Mapped[date | None] = mapped_column()
    retired_at: Mapped[datetime | None] = mapped_column()
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class AIRiskAssessment(Base):
    """FN-1006 `assessAIUseCaseRisk()` -- AI-FR-003/038. Append-only: a new assessment supersedes the
    previous one on the use case (`latest_risk_assessment_id`), the old row is retained."""

    __tablename__ = "ai_risk_assessment"
    __table_args__ = (
        Index("ix_ai_risk_assessment_use_case", "use_case_id"),
        {"schema": "ai_governance"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_use_case.id"), nullable=False
    )
    failure_modes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    gxp_impact: Mapped[str] = mapped_column(Text, nullable=False)
    people_impact: Mapped[str | None] = mapped_column(Text)
    data_impact: Mapped[str | None] = mapped_column(Text)
    security_impact: Mapped[str | None] = mapped_column(Text)
    human_oversight: Mapped[str] = mapped_column(Text, nullable=False)
    # AI-FR-003: the enumerated regulated-decision boundary this use case must never cross.
    prohibited_decisions: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    evaluation_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    approval_required: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AIModelDeployment(Base):
    """FN-1007 `approveAIModelDeployment()` -- AI-FR-007/012/013/047. Doubles as the model registry
    (AI-FR-007) and the current approved-deployment record. SIGNED (Doc 106 lookup required; no row
    exists yet -- see ARCHITECTURE.md / SPEC_GAP)."""

    __tablename__ = "ai_model_deployment"
    __table_args__ = (
        Index("ix_ai_model_deployment_state", "state"),
        {"schema": "ai_governance"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    use_case_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_use_case.id")
    )
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    model: Mapped[str] = mapped_column(String(120), nullable=False)
    model_version: Mapped[str] = mapped_column(String(40), nullable=False)
    deployment_type: Mapped[str] = mapped_column(String(20), nullable=False)
    endpoint: Mapped[str | None] = mapped_column(String(400))
    context_window: Mapped[int | None] = mapped_column(BigInteger)
    # AI-FR-012: provider retention/training/region/subprocessor terms.
    data_terms: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    evaluation_report_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    state: Mapped[str] = mapped_column(String(20), nullable=False, default="APPROVED")
    effective_from: Mapped[datetime] = mapped_column(server_default=func.now())
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class AIToolRegistry(Base):
    """AI-FR-009/010 -- explicit tool allowlist. `risk_class=WRITE_LOW_RISK` tools additionally require
    the use case to be ACTIVE (past risk assessment) before `authorizeAIToolCall()` allows them."""

    __tablename__ = "ai_tool_registry"
    __table_args__ = ({"schema": "ai_governance"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    risk_class: Mapped[str] = mapped_column(String(20), nullable=False, default="READ")
    allowed_scopes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    description: Mapped[str | None] = mapped_column(Text)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    version: Mapped[int] = mapped_column(BigInteger, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(server_default=func.now(), onupdate=func.now())


class AIPromptVersion(Base):
    """AI-FR-008 -- system prompts / retrieval instructions / tool policies / output schemas, versioned
    and released. Immutable once created (a change is a new row, `active` toggled)."""

    __tablename__ = "ai_prompt_version"
    __table_args__ = ({"schema": "ai_governance"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_use_case.id"), nullable=False
    )
    template_name: Mapped[str] = mapped_column(String(120), nullable=False)
    version_label: Mapped[str] = mapped_column(String(40), nullable=False)
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    released_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AIAdvisoryLog(Base):
    """FN-1009 `executeAIAdvisory()` -- AI-FR-028 (this row IS the mandatory AI audit-log entry:
    use-case, model/prompt version, retrieval refs (`context_ref`), output hash, actor, timestamp).
    `output_json` holds only the *validated structured* output (AI-FR-019); never the raw prompt (AI-FR-
    029 prompt privacy) -- prompts are referenced by `ai_prompt_version`, not re-logged verbatim."""

    __tablename__ = "ai_advisory_log"
    __table_args__ = (
        Index("ix_ai_advisory_log_use_case", "use_case_id"),
        {"schema": "ai_governance"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_use_case.id"), nullable=False
    )
    model_deployment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_model_deployment.id")
    )
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_prompt_version.id")
    )
    # AI-FR-015/016/017: retrieved source record refs with source id + version + cutoff.
    context_ref: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    output_hash: Mapped[str | None] = mapped_column(String(128))
    output_json: Mapped[dict | None] = mapped_column(JSONB)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    correlation_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AIToolDecision(Base):
    """FN-1010 `authorizeAIToolCall()` -- AI-FR-009/010/025 tool-safety decision log (allow/deny)."""

    __tablename__ = "ai_tool_decision"
    __table_args__ = (
        Index("ix_ai_tool_decision_use_case", "use_case_id"),
        {"schema": "ai_governance"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_use_case.id"), nullable=False
    )
    advisory_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_advisory_log.id")
    )
    tool_name: Mapped[str] = mapped_column(String(120), nullable=False)
    args_hash: Mapped[str | None] = mapped_column(String(128))
    decision: Mapped[str] = mapped_column(String(10), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AIDisposition(Base):
    """FN-1011 `recordHumanAIDisposition()` -- AI-FR-005/034. Append-only: "without rewriting historical
    output" means this table is INSERT-only per advisory (multiple dispositions on one advisory over
    time are all retained, not overwritten). SIGNED (Doc 106 lookup required; see ARCHITECTURE.md)."""

    __tablename__ = "ai_disposition"
    __table_args__ = (
        Index("ix_ai_disposition_advisory", "advisory_id"),
        {"schema": "ai_governance"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    advisory_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_advisory_log.id"), nullable=False
    )
    disposition: Mapped[str] = mapped_column(String(20), nullable=False)
    comments: Mapped[str | None] = mapped_column(Text)
    downstream_record_ref: Mapped[str | None] = mapped_column(String(200))
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AIEvaluationReport(Base):
    """FN-1012 `runAIEvaluationSuite()` -- AI-FR-022/023/024. `metrics` carries per-dimension scores as
    integer basis points (never float, matching the codebase-wide "no binary float" convention even for
    a non-regulated-quantity metric); `critical_failures` names any dimension whose failure blocks
    release regardless of the overall average (AI-FR-024)."""

    __tablename__ = "ai_evaluation_report"
    __table_args__ = (
        Index("ix_ai_evaluation_report_use_case", "use_case_id"),
        {"schema": "ai_governance"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_use_case.id"), nullable=False
    )
    model_deployment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_model_deployment.id")
    )
    prompt_version_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_prompt_version.id")
    )
    dataset_ref: Mapped[str] = mapped_column(String(200), nullable=False)
    scenario_classes: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    metrics: Mapped[dict] = mapped_column(JSONB, nullable=False, default=dict)
    critical_failures: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    passed: Mapped[bool] = mapped_column(Boolean, nullable=False)
    actor_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AIReleaseGate(Base):
    """FN-1013 `evaluateAIReleaseGate()` -- AI-FR-021/024. SIGNED (Doc 106 lookup required; see
    ARCHITECTURE.md). `decision=BLOCK` whenever the referenced evaluation report has any
    `critical_failures` entry, regardless of overall metrics (AI-FR-024)."""

    __tablename__ = "ai_release_gate"
    __table_args__ = ({"schema": "ai_governance"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_use_case.id"), nullable=False
    )
    evaluation_report_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_evaluation_report.id"), nullable=False
    )
    incidents_ref: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    vendor_security_status: Mapped[str | None] = mapped_column(Text)
    decision: Mapped[str] = mapped_column(String(10), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    decided_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AIPromptInjectionEvent(Base):
    """FN-1014 `detectPromptInjection()` -- AI-FR-014/025 security log. Content is never stored raw
    (only its hash) -- this is a security control ledger, not a content archive."""

    __tablename__ = "ai_prompt_injection_event"
    __table_args__ = (
        Index("ix_ai_prompt_injection_use_case", "use_case_id"),
        {"schema": "ai_governance"},
    )

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_use_case.id"), nullable=False
    )
    content_hash: Mapped[str] = mapped_column(String(128), nullable=False)
    detected: Mapped[bool] = mapped_column(Boolean, nullable=False)
    matched_patterns: Mapped[list] = mapped_column(JSONB, nullable=False, default=list)
    action_taken: Mapped[str] = mapped_column(String(20), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())


class AIProviderSwitch(Base):
    """FN-1015 `switchAIProviderProfile()` -- AI-FR-054. SIGNED (Doc 106 lookup required; see
    ARCHITECTURE.md)."""

    __tablename__ = "ai_provider_switch"
    __table_args__ = ({"schema": "ai_governance"},)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    use_case_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_use_case.id"), nullable=False
    )
    from_model_deployment_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_model_deployment.id")
    )
    to_model_deployment_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("ai_governance.ai_model_deployment.id"), nullable=False
    )
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    signature_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True))
    switched_by: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False)
    created_at: Mapped[datetime] = mapped_column(server_default=func.now())
