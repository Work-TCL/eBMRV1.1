"""Document 105 (SPEC-AI-001) REST surface, prefix `/ai-governance/v1`.

**Resolves the "APIS (0)" gap** documented in `models.py` / `ARCHITECTURE.md`: the source spec text and
the WP-13 sub-prompt both say "APIS (0)", but `04_DATA_MODEL_CATALOGUE.md` / `05_DATABASE_OWNERSHIP_
MATRIX.md` / `06_API_CATALOGUE.yaml` have zero SPEC-AI-001 rows at all -- an incomplete Phase-0
artefact (see `models.py`'s own docstring), not a deliberate zero-HTTP-surface design (contrast with
`app.modules.deployment`, which explicitly states "0 HTTP APIs -- CI/installer tooling calls these
directly" and correctly has no router). `03_FUNCTION_CATALOGUE.csv` FN-1005..FN-1017 is unambiguous
that every one of these 13 functions is a Mutation Gateway command; a Mutation Gateway command with no
HTTP entry point is unreachable by any caller, which cannot be what either source intended. One route
per function, plus signature-challenge endpoints for the 5 SIGNATURE POLICY LOOKUP REQUIRED functions
(same SG-138/SG-138-family pattern `app.modules.validation.signature_support` and
`app.modules.qms.signature_support` already established), plus read endpoints for the three
highest-value browse surfaces (use cases, model deployments, advisories) -- not all 11 tables, matching
the proportionality every other "module built this pass" phase used.

**No live AI provider.** `execute_ai_advisory()` and `run_ai_evaluation_suite()` take caller-injected
`model_client`/`evaluator` callables (see `commands.py` / `ARCHITECTURE.md` "Known limitations") --
this environment has none configured, so this router passes stand-ins that always raise
`DependencyUnavailableError`. AI-FR-041 fail-closed: `execute_ai_advisory()` catches that, writes an
`AIAdvisoryLog` row with `status=UNAVAILABLE`, and raises `AIOutputInvalidError` -- never a guessed
result. `run_ai_evaluation_suite()` has no such catch (the evaluator's return value is the only source
of its metrics -- a suite with no real evaluator has nothing honest to insert), so its raise propagates
to `main.py`'s `GxPError` handler as a plain 503. Neither path ever fabricates an AI output or an
evaluation score (CLAUDE.md `SS5` / this repo's evidence-honesty rule).
"""

from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.ai_governance import commands as ai
from app.modules.ai_governance.models import AIAdvisoryLog, AIModelDeployment, AIUseCase
from app.modules.signature.service import create_challenge, resolve_signature_requirement
from app.mutation.errors import DependencyUnavailableError, NotFoundError
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/ai-governance/v1", tags=["ai-governance"])


async def _no_live_model_client(context_ref: dict) -> dict:
    """No live LLM provider is configured in this environment (ARCHITECTURE.md). Raising here routes
    through `execute_ai_advisory()`'s existing fail-closed handling -- an `AIAdvisoryLog` row is still
    written (`status=UNAVAILABLE`) and the call raises `AIOutputInvalidError`, never a guessed result."""
    raise DependencyUnavailableError("No live AI model provider is configured in this environment")


async def _no_live_evaluator(dataset_ref: str, scenario_classes: list[str]) -> dict[str, int]:
    """No live AI evaluation harness is configured in this environment (ARCHITECTURE.md)."""
    raise DependencyUnavailableError("No live AI evaluation harness is configured in this environment")


def _use_case_dict(uc: AIUseCase) -> dict:
    return {
        "use_case_id": str(uc.id), "site_id": str(uc.site_id) if uc.site_id else None, "name": uc.name,
        "use_case_class": uc.use_case_class, "purpose": uc.purpose, "users": uc.users,
        "data_classes": uc.data_classes, "decision_impact": uc.decision_impact,
        "proposed_tools": uc.proposed_tools, "proposed_models": uc.proposed_models, "state": uc.state,
        "latest_risk_assessment_id": str(uc.latest_risk_assessment_id) if uc.latest_risk_assessment_id else None,
        "retirement_reason": uc.retirement_reason, "retirement_replacement": uc.retirement_replacement,
        "retirement_effective_date": uc.retirement_effective_date.isoformat() if uc.retirement_effective_date else None,
        "retired_at": uc.retired_at.isoformat() if uc.retired_at else None,
        "version": uc.version, "created_at": uc.created_at.isoformat() if uc.created_at else None,
    }


def _model_deployment_dict(d: AIModelDeployment) -> dict:
    return {
        "model_deployment_id": str(d.id), "use_case_id": str(d.use_case_id) if d.use_case_id else None,
        "provider": d.provider, "model": d.model, "model_version": d.model_version,
        "deployment_type": d.deployment_type, "endpoint": d.endpoint, "context_window": d.context_window,
        "data_terms": d.data_terms, "evaluation_report_id": str(d.evaluation_report_id) if d.evaluation_report_id else None,
        "state": d.state, "effective_from": d.effective_from.isoformat() if d.effective_from else None,
        "signature_id": str(d.signature_id) if d.signature_id else None, "version": d.version,
    }


def _advisory_dict(log: AIAdvisoryLog) -> dict:
    return {
        "advisory_id": str(log.id), "use_case_id": str(log.use_case_id),
        "model_deployment_id": str(log.model_deployment_id) if log.model_deployment_id else None,
        "prompt_version_id": str(log.prompt_version_id) if log.prompt_version_id else None,
        "context_ref": log.context_ref, "output_hash": log.output_hash, "output_json": log.output_json,
        "status": log.status, "user_id": str(log.user_id), "correlation_id": str(log.correlation_id),
        "created_at": log.created_at.isoformat() if log.created_at else None,
    }


# =====================================================================================================
# FN-1005/1006/1016 -- AI use cases
# =====================================================================================================


@router.post("/use-cases", response_model=MutationReceipt)
async def post_use_cases(
    cmd: ai.RegisterAIUseCaseCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        return await ai.register_ai_use_case(session, cmd, actor.user_id)


@router.get("/use-cases")
async def list_use_cases(
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params), state: str | None = None,
) -> dict:
    stmt = select(AIUseCase)
    if state:
        stmt = stmt.where(AIUseCase.state == state)
    if params.q:
        stmt = stmt.where(AIUseCase.name.ilike(f"%{params.q}%"))
    rows, envelope = await paginate(
        session, stmt, params, sortable={"name": AIUseCase.name, "state": AIUseCase.state},
        default_sort=AIUseCase.created_at,
    )
    return {**envelope, "items": [_use_case_dict(r) for (r,) in rows]}


@router.get("/use-cases/{use_case_id}")
async def get_use_case(
    use_case_id: uuid.UUID, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    uc = await session.get(AIUseCase, use_case_id)
    if uc is None:
        raise NotFoundError("AI use case not found")
    return _use_case_dict(uc)


@router.post("/use-cases/{use_case_id}/risk-assessments", response_model=MutationReceipt)
async def post_use_case_risk_assessment(
    use_case_id: uuid.UUID, cmd: ai.AssessAIUseCaseRiskCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.use_case_id = use_case_id
    async with session.begin():
        return await ai.assess_ai_use_case_risk(session, cmd, actor.user_id)


@router.post("/use-cases/{use_case_id}/retire", response_model=MutationReceipt)
async def post_use_case_retire(
    use_case_id: uuid.UUID, cmd: ai.RetireAIUseCaseCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    cmd.use_case_id = use_case_id
    async with session.begin():
        return await ai.retire_ai_use_case(session, cmd, actor.user_id)


@router.post("/use-cases/{use_case_id}/governance-package")
async def post_use_case_governance_package(
    use_case_id: uuid.UUID, cmd: ai.GenerateAIGovernancePackageCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    cmd.use_case_id = use_case_id
    async with session.begin():
        return await ai.generate_ai_governance_package(session, cmd, actor.user_id)


# =====================================================================================================
# FN-1007 approveAIModelDeployment() -- SIGNED (ai_model_deployment/approve, SG-167)
# =====================================================================================================


class ApproveAIModelDeploymentChallengeBody(BaseModel):
    """Mirrors `ApproveAIModelDeploymentCommand` minus the transport-only `challenge_id`/
    `reauth_password`/`idempotency_key` fields -- see `commands.py::content_challenge_hash()`."""

    provider: str
    model: str
    model_version: str
    deployment_type: str
    use_case_id: uuid.UUID | None = None
    endpoint: str | None = None
    context_window: int | None = None
    data_terms: dict = {}
    evaluation_report_id: uuid.UUID | None = None
    reason: str


@router.post("/model-deployments/signature-challenges")
async def post_model_deployment_signature_challenge(
    body: ApproveAIModelDeploymentChallengeBody, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Signed-CREATE, content-hash-bound (SG-167). `body` must carry the exact same field values the
    client then submits to `POST /model-deployments` -- any difference invalidates the challenge."""
    async with session.begin():
        policy = await resolve_signature_requirement(session, record_type="ai_model_deployment", action="approve")
        record_id = body.use_case_id or uuid.uuid4()
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="ai_model_deployment", record_id=record_id,
            record_version=1, record_hash=sha256_hex(body.model_dump(mode="json")), meaning=policy.meaning,
        )
        return {
            "challenge_id": str(challenge.id), "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


@router.post("/model-deployments", response_model=MutationReceipt)
async def post_model_deployments(
    cmd: ai.ApproveAIModelDeploymentCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        return await ai.approve_ai_model_deployment(session, cmd, actor.user_id)


@router.get("/model-deployments")
async def list_model_deployments(
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params), use_case_id: uuid.UUID | None = None, state: str | None = None,
) -> dict:
    stmt = select(AIModelDeployment)
    if use_case_id:
        stmt = stmt.where(AIModelDeployment.use_case_id == use_case_id)
    if state:
        stmt = stmt.where(AIModelDeployment.state == state)
    rows, envelope = await paginate(
        session, stmt, params, sortable={"provider": AIModelDeployment.provider, "state": AIModelDeployment.state},
        default_sort=AIModelDeployment.created_at,
    )
    return {**envelope, "items": [_model_deployment_dict(r) for (r,) in rows]}


@router.get("/model-deployments/{model_deployment_id}")
async def get_model_deployment(
    model_deployment_id: uuid.UUID, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    d = await session.get(AIModelDeployment, model_deployment_id)
    if d is None:
        raise NotFoundError("AI model deployment not found")
    return _model_deployment_dict(d)


# =====================================================================================================
# FN-1008 buildAIRequestContext() -- not signed
# =====================================================================================================


@router.post("/context-packages")
async def post_context_packages(
    cmd: ai.BuildAIRequestContextCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        return await ai.build_ai_request_context(session, cmd, actor.user_id, caller_site_id=getattr(actor, "site_id", None))


# =====================================================================================================
# FN-1009 executeAIAdvisory() -- not signed; no live model provider (see module docstring)
# =====================================================================================================


@router.post("/advisories", response_model=MutationReceipt)
async def post_advisories(
    cmd: ai.ExecuteAIAdvisoryCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        return await ai.execute_ai_advisory(session, cmd, actor.user_id, model_client=_no_live_model_client)


@router.get("/advisories")
async def list_advisories(
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params), use_case_id: uuid.UUID | None = None,
) -> dict:
    stmt = select(AIAdvisoryLog)
    if use_case_id:
        stmt = stmt.where(AIAdvisoryLog.use_case_id == use_case_id)
    rows, envelope = await paginate(
        session, stmt, params, sortable={"status": AIAdvisoryLog.status}, default_sort=AIAdvisoryLog.created_at,
    )
    return {**envelope, "items": [_advisory_dict(r) for (r,) in rows]}


@router.get("/advisories/{advisory_id}")
async def get_advisory(
    advisory_id: uuid.UUID, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    log = await session.get(AIAdvisoryLog, advisory_id)
    if log is None:
        raise NotFoundError("AI advisory not found")
    return _advisory_dict(log)


# =====================================================================================================
# FN-1010 authorizeAIToolCall() -- SIGNED (ai_tool_call/authorize, SG-167)
# =====================================================================================================


class AuthorizeAIToolCallChallengeBody(BaseModel):
    use_case_id: uuid.UUID
    tool_name: str
    args: dict = {}
    advisory_id: uuid.UUID | None = None
    reason: str


@router.post("/tool-decisions/signature-challenges")
async def post_tool_decision_signature_challenge(
    body: AuthorizeAIToolCallChallengeBody, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        policy = await resolve_signature_requirement(session, record_type="ai_tool_call", action="authorize")
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="ai_tool_call", record_id=body.use_case_id,
            record_version=1, record_hash=sha256_hex(body.model_dump(mode="json")), meaning=policy.meaning,
        )
        return {
            "challenge_id": str(challenge.id), "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


@router.post("/tool-decisions", response_model=MutationReceipt)
async def post_tool_decisions(
    cmd: ai.AuthorizeAIToolCallCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        return await ai.authorize_ai_tool_call(session, cmd, actor.user_id)


# =====================================================================================================
# FN-1011 recordHumanAIDisposition() -- SIGNED (ai_disposition/record, SG-167)
# =====================================================================================================


class RecordHumanAIDispositionChallengeBody(BaseModel):
    advisory_id: uuid.UUID
    disposition: str
    comments: str | None = None
    downstream_record_ref: str | None = None
    reason: str


@router.post("/dispositions/signature-challenges")
async def post_disposition_signature_challenge(
    body: RecordHumanAIDispositionChallengeBody, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        policy = await resolve_signature_requirement(session, record_type="ai_disposition", action="record")
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="ai_disposition", record_id=body.advisory_id,
            record_version=1, record_hash=sha256_hex(body.model_dump(mode="json")), meaning=policy.meaning,
        )
        return {
            "challenge_id": str(challenge.id), "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


@router.post("/dispositions", response_model=MutationReceipt)
async def post_dispositions(
    cmd: ai.RecordHumanAIDispositionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        return await ai.record_human_ai_disposition(session, cmd, actor.user_id)


# =====================================================================================================
# FN-1012 runAIEvaluationSuite() -- not signed; no live evaluator (see module docstring)
# =====================================================================================================


@router.post("/evaluation-reports", response_model=MutationReceipt)
async def post_evaluation_reports(
    cmd: ai.RunAIEvaluationSuiteCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        return await ai.run_ai_evaluation_suite(session, cmd, actor.user_id, evaluator=_no_live_evaluator)


# =====================================================================================================
# FN-1013 evaluateAIReleaseGate() -- SIGNED (ai_release_gate/evaluate, SG-167)
# =====================================================================================================


class EvaluateAIReleaseGateChallengeBody(BaseModel):
    use_case_id: uuid.UUID
    evaluation_report_id: uuid.UUID
    incidents_ref: list[str] = []
    vendor_security_status: str | None = None
    reason: str


@router.post("/release-gates/signature-challenges")
async def post_release_gate_signature_challenge(
    body: EvaluateAIReleaseGateChallengeBody, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        policy = await resolve_signature_requirement(session, record_type="ai_release_gate", action="evaluate")
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="ai_release_gate", record_id=body.use_case_id,
            record_version=1, record_hash=sha256_hex(body.model_dump(mode="json")), meaning=policy.meaning,
        )
        return {
            "challenge_id": str(challenge.id), "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


@router.post("/release-gates", response_model=MutationReceipt)
async def post_release_gates(
    cmd: ai.EvaluateAIReleaseGateCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        return await ai.evaluate_ai_release_gate(session, cmd, actor.user_id)


# =====================================================================================================
# FN-1014 detectPromptInjection() -- not signed
# =====================================================================================================


@router.post("/injection-screens")
async def post_injection_screens(
    cmd: ai.DetectPromptInjectionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        return await ai.detect_prompt_injection(session, cmd, actor.user_id)


# =====================================================================================================
# FN-1015 switchAIProviderProfile() -- SIGNED (ai_provider_switch/switch, SG-167)
# =====================================================================================================


class SwitchAIProviderProfileChallengeBody(BaseModel):
    use_case_id: uuid.UUID
    to_model_deployment_id: uuid.UUID
    from_model_deployment_id: uuid.UUID | None = None
    reason: str


@router.post("/provider-switches/signature-challenges")
async def post_provider_switch_signature_challenge(
    body: SwitchAIProviderProfileChallengeBody, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        policy = await resolve_signature_requirement(session, record_type="ai_provider_switch", action="switch")
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="ai_provider_switch", record_id=body.use_case_id,
            record_version=1, record_hash=sha256_hex(body.model_dump(mode="json")), meaning=policy.meaning,
        )
        return {
            "challenge_id": str(challenge.id), "meaning": challenge.meaning,
            "expires_at": challenge.expires_at.isoformat(),
        }


@router.post("/provider-switches", response_model=MutationReceipt)
async def post_provider_switches(
    cmd: ai.SwitchAIProviderProfileCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        return await ai.switch_ai_provider_profile(session, cmd, actor.user_id)
