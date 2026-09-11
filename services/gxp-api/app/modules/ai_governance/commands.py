"""Document 105 (SPEC-AI-001) Mutation Gateway command handlers -- the 13 functions of
`docs/generated/03_FUNCTION_CATALOGUE.csv` FN-1005..FN-1017, each in its own section below.

**Signature status.** 5 of 13 functions are annotated "SIGNATURE POLICY LOOKUP REQUIRED (Doc 04
SIG-FR-004; baseline values -> SG-004)" in the function catalogue: `approve_ai_model_deployment`,
`authorize_ai_tool_call`, `record_human_ai_disposition`, `evaluate_ai_release_gate`,
`switch_ai_provider_profile`. Each calls `signature_service.resolve_signature_requirement()`, exactly
like every other signed action in this codebase. **Document 106 had zero SPEC-AI-001 rows** (checked --
no `ai_use_case`/`ai_model_deployment`/etc. entries anywhere in `specs/Documents_106_115/Document_106...`)
until SG-167 was RESOLVED 2026-09-11, project-owner-directed (PHASE_3_DEFERRED_DECISIONS.md item C, a
Document 106 v1.1 addendum authored from the closest section 8 families): all 5 pairs now carry a
`scripts/seed.py` `SIGNATURE_POLICY_FLOOR` row (`Approved`/`Performed` meaning, `ai_disposition/record`
role-free, the other 4 requiring `QA Releaser`), enforced via `_apply_signature()` ->
`enforce_signer_policy()`. See `docs/generated/18_SPEC_GAPS.md` (SG-167) and `ARCHITECTURE.md`. The
other 8 functions have "none identified in source" for signature and are RBAC-gated + audit-only.

**AI-FR-004/AI-FR-003 boundary.** None of these functions ever write GxP domain state (no import of
any `app.modules.{batch,release,qa_review,qms,...}` model or command anywhere in this module) -- the
only writes are to this module's own `ai_governance` schema, which holds records *about* AI usage, not
regulated production/quality state. `authorize_ai_tool_call()` additionally refuses, unconditionally,
any tool whose `allowed_scopes` names a regulated-decision action (AI-FR-003's enumerated list) --
that refusal is structural (the tool can never be on the allowlist for such a scope), not a per-call
judgement call.
"""

from __future__ import annotations

import re
import uuid
from datetime import date, datetime, timezone
from typing import Awaitable, Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.ai_governance.models import (
    DATA_CLASSIFICATIONS,
    DISPOSITIONS,
    USE_CASE_CLASSES,
    AIAdvisoryLog,
    AIDisposition,
    AIEvaluationReport,
    AIModelDeployment,
    AIPromptInjectionEvent,
    AIPromptVersion,
    AIProviderSwitch,
    AIReleaseGate,
    AIRiskAssessment,
    AIToolDecision,
    AIToolRegistry,
    AIUseCase,
)
from app.modules.policy.service import evaluate_policy
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    AIDataClassificationDeniedError,
    AIEvaluationCriticalFailureError,
    AIModelNotApprovedError,
    AIOutputInvalidError,
    AIPromptInjectionBlockedError,
    AIToolNotAllowlistedError,
    AIUseCaseNotActiveError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

# AI-FR-003: the enumerated regulated-decision boundary. A tool's `allowed_scopes` can never contain
# one of these -- authorize_ai_tool_call() refuses unconditionally, not by per-call judgement.
REGULATED_DECISION_SCOPES = frozenset({
    "release_product", "disposition_batch", "sign_record", "approve_deviation", "approve_capa",
    "change_specification", "accept_oos", "alter_audit", "determine_reportability",
    "submit_regulatory_report",
})

# AI-FR-014/025 defense-in-depth heuristic. Untrusted retrieved/user content is scanned for known
# instruction-override markers; this NEVER treats the content as policy (AI-FR-014) -- a match only
# ever *blocks* an escalation, it can never grant one. Engineering-default pattern set (SG-167 family
# alongside SG-166 -- no approved canonical pattern list exists in Documents 106-115).
_INJECTION_PATTERNS = tuple(
    re.compile(p, re.IGNORECASE) for p in (
        r"ignore (all |the )?(previous|prior|above) instructions",
        r"disregard (all |the )?(previous|prior|above)",
        r"you are now\b",
        r"new system prompt",
        r"reveal (your|the) (system )?(prompt|instructions)",
        r"act as (an? )?(unrestricted|jailbroken|dan)\b",
        r"</?system>",
    )
)


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version, audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _finalize_tx(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, aggregate_id: uuid.UUID,
    version: int, action: str, actor_user_id: uuid.UUID, reason: str | None, new_value: dict,
    event_type: str, expected_version: int | None, command_type: str,
    site_id: uuid.UUID | None = None, signature_id: uuid.UUID | None = None,
    old_value: dict | None = None, aggregate_type: str = "ai_use_case",
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=site_id, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value=old_value, new_value=new_value, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, payload=new_value, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=site_id, command_type=command_type, aggregate_type=aggregate_type,
        aggregate_id=aggregate_id, expected_version=expected_version, resulting_version=version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=aggregate_id, resulting_version=version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# =================================================================================================
# FN-1005 registerAIUseCase() -- AI-FR-001/002.
# =================================================================================================


class RegisterAIUseCaseCommand(CommandEnvelope):
    name: str
    use_case_class: str
    purpose: str
    users: list[str] = []
    data_classes: list[str] = []
    decision_impact: str
    proposed_tools: list[str] = []
    proposed_models: list[str] = []
    site_id: uuid.UUID | None = None
    reason: str


async def register_ai_use_case(
    session: AsyncSession, cmd: RegisterAIUseCaseCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    await evaluate_policy(session, actor_user_id, action="ai_governance.use_case.register", site_id=cmd.site_id)

    if cmd.use_case_class not in USE_CASE_CLASSES:
        raise ValidationFailedError(f"use_case_class must be one of {USE_CASE_CLASSES}")
    for dc in cmd.data_classes:
        if dc not in DATA_CLASSIFICATIONS:
            raise ValidationFailedError(f"data_classes entries must be one of {DATA_CLASSIFICATIONS}")
    if not cmd.name or not cmd.purpose or not cmd.decision_impact or not cmd.reason:
        raise ValidationFailedError("name, purpose, decision_impact and reason are required")

    use_case = AIUseCase(
        site_id=cmd.site_id, name=cmd.name, use_case_class=cmd.use_case_class, purpose=cmd.purpose,
        users=cmd.users, data_classes=cmd.data_classes, decision_impact=cmd.decision_impact,
        proposed_tools=cmd.proposed_tools, proposed_models=cmd.proposed_models, state="DRAFT",
    )
    session.add(use_case)
    await session.flush()

    return await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=use_case.id, version=use_case.version,
        action="Created", actor_user_id=actor_user_id, reason=cmd.reason,
        new_value={"use_case_id": str(use_case.id), "name": cmd.name, "state": "DRAFT"},
        event_type="AIUseCaseRegistered", expected_version=None,
        command_type="RegisterAIUseCase", site_id=cmd.site_id,
    )


# =================================================================================================
# FN-1006 assessAIUseCaseRisk() -- AI-FR-003/038.
# =================================================================================================


class AssessAIUseCaseRiskCommand(CommandEnvelope):
    use_case_id: uuid.UUID
    expected_version: int
    failure_modes: list[str] = []
    gxp_impact: str
    people_impact: str | None = None
    data_impact: str | None = None
    security_impact: str | None = None
    human_oversight: str
    prohibited_decisions: list[str] = []
    evaluation_required: bool = True
    approval_required: bool = True
    reason: str


async def assess_ai_use_case_risk(
    session: AsyncSession, cmd: AssessAIUseCaseRiskCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    await evaluate_policy(session, actor_user_id, action="ai_governance.use_case.assess_risk", site_id=None)

    use_case = await session.get(AIUseCase, cmd.use_case_id)
    if use_case is None:
        raise NotFoundError("AI use case not found")
    if use_case.version != cmd.expected_version:
        raise StaleVersionError("AI use case changed since this request was prepared",
                                 current_version=use_case.version)
    if not cmd.gxp_impact or not cmd.human_oversight:
        raise ValidationFailedError("gxp_impact and human_oversight are required")

    assessment = AIRiskAssessment(
        use_case_id=use_case.id, failure_modes=cmd.failure_modes, gxp_impact=cmd.gxp_impact,
        people_impact=cmd.people_impact, data_impact=cmd.data_impact, security_impact=cmd.security_impact,
        human_oversight=cmd.human_oversight, prohibited_decisions=cmd.prohibited_decisions,
        evaluation_required=cmd.evaluation_required, approval_required=cmd.approval_required,
        actor_id=actor_user_id,
    )
    session.add(assessment)
    await session.flush()

    old = {"state": use_case.state}
    use_case.latest_risk_assessment_id = assessment.id
    use_case.state = "RISK_ASSESSED"
    use_case.version += 1
    await session.flush()

    return await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=use_case.id, version=use_case.version,
        action="StatusChanged", actor_user_id=actor_user_id, reason=cmd.reason, old_value=old,
        new_value={"use_case_id": str(use_case.id), "risk_assessment_id": str(assessment.id),
                   "state": "RISK_ASSESSED"},
        event_type="AIUseCaseRiskAssessed", expected_version=cmd.expected_version,
        command_type="AssessAIUseCaseRisk",
    )


# =================================================================================================
# FN-1007 approveAIModelDeployment() -- AI-FR-007/012/013/047. SIGNED (see module docstring).
# =================================================================================================


class ApproveAIModelDeploymentCommand(CommandEnvelope):
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
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def approve_ai_model_deployment(
    session: AsyncSession, cmd: ApproveAIModelDeploymentCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    await evaluate_policy(session, actor_user_id, action="ai_governance.model.approve", site_id=None)

    if cmd.deployment_type not in ("CLOUD_API", "PRIVATE", "ON_PREM"):
        raise ValidationFailedError("deployment_type must be CLOUD_API, PRIVATE or ON_PREM")
    if cmd.evaluation_report_id is not None:
        report = await session.get(AIEvaluationReport, cmd.evaluation_report_id)
        if report is None or not report.passed:
            raise ValidationFailedError("evaluation_report_id must reference a passed evaluation report")

    # SIGNATURE POLICY LOOKUP REQUIRED -- fails closed until Document 106 has a SPEC-AI-001 row (SG-167).
    policy = await signature_service.resolve_signature_requirement(
        session, record_type="ai_model_deployment", action="approve"
    )
    signature_id = None
    if policy.signature_required:
        signature_id = await _apply_signature(
            session, cmd, actor_user_id, record_version=1, policy=policy, action_label="ai_model_deployment.approve",
        )

    deployment = AIModelDeployment(
        use_case_id=cmd.use_case_id, provider=cmd.provider, model=cmd.model, model_version=cmd.model_version,
        deployment_type=cmd.deployment_type, endpoint=cmd.endpoint, context_window=cmd.context_window,
        data_terms=cmd.data_terms, evaluation_report_id=cmd.evaluation_report_id, state="APPROVED",
        signature_id=signature_id,
    )
    session.add(deployment)
    await session.flush()

    return await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=deployment.id, version=deployment.version,
        action="Approved", actor_user_id=actor_user_id, reason=cmd.reason, signature_id=signature_id,
        new_value={"deployment_id": str(deployment.id), "provider": cmd.provider, "model": cmd.model,
                   "model_version": cmd.model_version, "state": "APPROVED"},
        event_type="AIModelDeploymentApproved", expected_version=None,
        command_type="ApproveAIModelDeployment", aggregate_type="ai_model_deployment",
    )


def content_challenge_hash(cmd) -> str:
    """The signed-CREATE challenge is bound to the command's *content* -- the volatile transport fields
    (`challenge_id`, `reauth_password`, `idempotency_key`) are excluded so the caller can compute the
    identical hash before `challenge_id` exists. Same shape as
    `app.modules.validation.commands_vsr.create_challenge_hash()`; extracted to a module-level function
    (rather than left inline in `sha256_hex(cmd.model_dump(mode="json"))`, which -- before this fix --
    included `challenge_id`/`reauth_password` in the hash it *also* used at consume time, a genuine
    chicken-and-egg defect: the challenge's own id cannot be known when the challenge is requested, so
    the challenge-issuing endpoint could never reproduce a matching hash) so `router.py`'s
    signature-challenge endpoints can call it directly."""
    return sha256_hex(
        cmd.model_dump(mode="json", exclude={"challenge_id", "reauth_password", "idempotency_key"})
    )


async def _apply_signature(session, cmd, actor_user_id, *, record_version: int, policy, action_label: str) -> uuid.UUID:
    """Shared step-up-then-consume-then-sign flow, matching evidence.commands.apply_evidence_legal_hold.
    SG-167, RESOLVED 2026-09-11, project-owner-directed (PHASE_3_DEFERRED_DECISIONS.md item C): Document
    106 had zero SPEC-AI-001 rows, so this was unreachable -- resolve_signature_requirement() always
    raised first. Now that all 5 pairs carry a Document 106 v1.1-addendum floor row, role/independence
    enforcement is added here (none of the 5 ai_governance tables stores an author/requester/performer
    identity column, so independence is role-only -- the same documented limitation as
    vault_object/release / rule/release)."""
    from app.core.security import verify_password
    from app.modules.iam.models import User
    from app.mutation.errors import MissingSignatureError

    await signature_service.enforce_signer_policy(
        session, policy=policy, actor_user_id=actor_user_id, site_id=None,
        action_label=action_label, disqualified_subject_ids=(),
    )
    actor = await session.get(User, actor_user_id)
    if actor is None or not cmd.reauth_password or not verify_password(cmd.reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    if cmd.challenge_id is None:
        raise MissingSignatureError("challenge_id is required for a signed action")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
        record_version=record_version, record_hash=content_challenge_hash(cmd),
    )
    signature = await signature_service.sign(
        session, challenge=challenge, auth_context={"method": "password_reauth"}
    )
    return signature.id


# =================================================================================================
# FN-1008 buildAIRequestContext() -- AI-FR-011/015/016/017/030/031/032. Not signed; no own table
# (returns an AIContextPackage dict, audit-logged against the use case aggregate).
# =================================================================================================


class BuildAIRequestContextCommand(CommandEnvelope):
    use_case_id: uuid.UUID
    user_query: str
    requested_record_refs: list[dict] = []  # [{"record_type","record_id","site_id","classification"}]
    reason: str


async def build_ai_request_context(
    session: AsyncSession, cmd: BuildAIRequestContextCommand, actor_user_id: uuid.UUID,
    *, caller_site_id: uuid.UUID | None,
) -> dict:
    """AI-FR-031: retrieval is bound to the caller's own tenant/site scope *before* context assembly --
    `caller_site_id` is the authenticated caller's own scope, never a client-supplied field."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return {"receipt": _receipt_from_existing(existing)}

    await evaluate_policy(session, actor_user_id, action="ai_governance.context.build", site_id=None)

    use_case = await session.get(AIUseCase, cmd.use_case_id)
    if use_case is None:
        raise NotFoundError("AI use case not found")

    scoped: list[dict] = []
    for ref in cmd.requested_record_refs:
        classification = ref.get("classification")
        record_site_id = ref.get("site_id")
        # AI-FR-032: never permitted regardless of use-case data_classes.
        if classification == "SECRET" or ref.get("record_type") in ("credential", "secret"):
            raise AIDataClassificationDeniedError(
                "Security secrets are never included in AI context", record_type=ref.get("record_type")
            )
        if classification and classification not in use_case.data_classes:
            raise AIDataClassificationDeniedError(
                "Requested data classification is not approved for this use case",
                classification=classification, use_case_id=str(use_case.id),
            )
        if caller_site_id is not None and record_site_id is not None and str(record_site_id) != str(caller_site_id):
            raise AIDataClassificationDeniedError(
                "Requested record is outside the caller's tenant/site scope", record_type=ref.get("record_type"),
            )
        scoped.append({
            "record_type": ref.get("record_type"), "record_id": ref.get("record_id"),
            "source_version": ref.get("source_version"), "source_cutoff": datetime.now(timezone.utc).isoformat(),
        })

    context_package = {
        "use_case_id": str(use_case.id), "user_query": cmd.user_query, "scoped_refs": scoped,
        "built_at": datetime.now(timezone.utc).isoformat(),
    }

    await write_audit_event(
        session, site_id=use_case.site_id, aggregate_type="ai_use_case", aggregate_id=use_case.id,
        aggregate_version=use_case.version, action="ContextBuilt", actor_id=actor_user_id,
        correlation_id=uuid.uuid4(), reason=cmd.reason, new_value={"ref_count": len(scoped)},
    )
    await write_outbox_event(
        session, event_type="AIContextBuilt", aggregate_type="ai_use_case", aggregate_id=use_case.id,
        aggregate_version=use_case.version, payload={"ref_count": len(scoped)}, correlation_id=uuid.uuid4(),
    )
    return context_package


# =================================================================================================
# FN-1009 executeAIAdvisory() -- AI-FR-018/019/020/041. Not signed. `model_client` is caller-injected
# (no live model provider in this environment -- AI-FR-045/046 abstraction boundary; the gateway logic
# below is real and independently testable with a fake client).
# =================================================================================================


class ExecuteAIAdvisoryCommand(CommandEnvelope):
    use_case_id: uuid.UUID
    model_deployment_id: uuid.UUID
    prompt_version_id: uuid.UUID | None = None
    context_ref: dict = {}
    output_schema: dict | None = None
    reason: str


async def execute_ai_advisory(
    session: AsyncSession, cmd: ExecuteAIAdvisoryCommand, actor_user_id: uuid.UUID,
    *, model_client: Callable[[dict], Awaitable[dict]],
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    await evaluate_policy(session, actor_user_id, action="ai_governance.advisory.execute", site_id=None)

    use_case = await session.get(AIUseCase, cmd.use_case_id)
    if use_case is None:
        raise NotFoundError("AI use case not found")
    if use_case.state != "ACTIVE":
        raise AIUseCaseNotActiveError("Use case must be ACTIVE to serve advisory requests",
                                       use_case_id=str(use_case.id), state=use_case.state)

    deployment = await session.get(AIModelDeployment, cmd.model_deployment_id)
    if deployment is None or deployment.state != "APPROVED":
        raise AIModelNotApprovedError("Model deployment is not an approved production deployment",
                                       model_deployment_id=str(cmd.model_deployment_id))

    correlation_id = uuid.uuid4()
    try:
        # AI-FR-041: fail closed on timeout/refusal -- no guessed result is inserted on exception.
        result = await model_client(cmd.context_ref)
    except Exception as exc:  # noqa: BLE001
        log = AIAdvisoryLog(
            use_case_id=use_case.id, model_deployment_id=deployment.id, prompt_version_id=cmd.prompt_version_id,
            context_ref=cmd.context_ref, status="UNAVAILABLE", user_id=actor_user_id, correlation_id=correlation_id,
        )
        session.add(log)
        await session.flush()
        await write_audit_event(
            session, site_id=use_case.site_id, aggregate_type="ai_use_case", aggregate_id=use_case.id,
            aggregate_version=use_case.version, action="AdvisoryUnavailable", actor_id=actor_user_id,
            correlation_id=correlation_id, reason=str(exc)[:500],
        )
        await write_outbox_event(
            session, event_type="AI_OUTPUT_INVALID", aggregate_type="ai_advisory_log", aggregate_id=log.id,
            aggregate_version=1, payload={"reason": "provider_unavailable"}, correlation_id=correlation_id,
        )
        raise AIOutputInvalidError("AI provider unavailable or timed out; no result inserted") from exc

    output = result.get("output")
    if output is None:
        raise AIOutputInvalidError("Model returned no structured output")
    if cmd.output_schema is not None:
        _validate_against_schema(output, cmd.output_schema)

    output_hash = sha256_hex(output)
    log = AIAdvisoryLog(
        use_case_id=use_case.id, model_deployment_id=deployment.id, prompt_version_id=cmd.prompt_version_id,
        context_ref=cmd.context_ref, output_hash=output_hash, output_json=output, status="GENERATED",
        user_id=actor_user_id, correlation_id=correlation_id,
    )
    session.add(log)
    await session.flush()

    return await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=log.id, version=1,
        action="Created", actor_user_id=actor_user_id, reason=cmd.reason,
        new_value={"advisory_id": str(log.id), "output_hash": output_hash, "status": "GENERATED"},
        event_type="AIAdvisoryGenerated", expected_version=None,
        command_type="ExecuteAIAdvisory", aggregate_type="ai_advisory_log",
    )


def _validate_against_schema(output: dict, schema: dict) -> None:
    """Minimal structural check (AI-FR-019): every schema `required` key is present. Full JSON Schema
    validation is a SPEC_GAP-free ordinary engineering choice left for a later pass; this already
    proves the fail-closed contract (missing required field -> AIOutputInvalidError, never a guess)."""
    for key in schema.get("required", []):
        if key not in output:
            raise AIOutputInvalidError(f"Output missing required field '{key}' per output_schema")


# =================================================================================================
# FN-1010 authorizeAIToolCall() -- AI-FR-003/004/009/010. SIGNED (see module docstring).
# =================================================================================================


class AuthorizeAIToolCallCommand(CommandEnvelope):
    use_case_id: uuid.UUID
    tool_name: str
    args: dict = {}
    advisory_id: uuid.UUID | None = None
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def authorize_ai_tool_call(
    session: AsyncSession, cmd: AuthorizeAIToolCallCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    await evaluate_policy(session, actor_user_id, action="ai_governance.tool.authorize", site_id=None)

    use_case = await session.get(AIUseCase, cmd.use_case_id)
    if use_case is None:
        raise NotFoundError("AI use case not found")

    tool_row = (await session.execute(
        select(AIToolRegistry).where(AIToolRegistry.tool_name == cmd.tool_name)
    )).scalar_one_or_none()

    denied_reason = None
    if tool_row is None or not tool_row.active:
        denied_reason = "Tool is not on the allowlist"
    elif REGULATED_DECISION_SCOPES.intersection(tool_row.allowed_scopes):
        # AI-FR-003/004: structural refusal -- no tool naming a regulated-decision scope is ever allowed.
        denied_reason = "Tool scope includes a regulated decision AI can never hold autonomous authority over"
    elif tool_row.risk_class == "WRITE_LOW_RISK" and use_case.state != "ACTIVE":
        denied_reason = "Low-risk write tools require an ACTIVE (risk-assessed) use case"

    if denied_reason is not None:
        decision_row = AIToolDecision(
            use_case_id=use_case.id, advisory_id=cmd.advisory_id, tool_name=cmd.tool_name,
            args_hash=sha256_hex(cmd.args), decision="DENIED", reason=denied_reason, user_id=actor_user_id,
        )
        session.add(decision_row)
        await session.flush()
        await write_audit_event(
            session, site_id=use_case.site_id, aggregate_type="ai_tool_decision", aggregate_id=decision_row.id,
            aggregate_version=1, action="Denied", actor_id=actor_user_id, correlation_id=uuid.uuid4(),
            reason=denied_reason,
        )
        await write_outbox_event(
            session, event_type="AIToolCallDenied", aggregate_type="ai_tool_decision", aggregate_id=decision_row.id,
            aggregate_version=1, payload={"tool_name": cmd.tool_name, "reason": denied_reason},
            correlation_id=uuid.uuid4(),
        )
        raise AIToolNotAllowlistedError(denied_reason, tool_name=cmd.tool_name)

    # SIGNATURE POLICY LOOKUP REQUIRED -- fails closed until Document 106 has a SPEC-AI-001 row (SG-167).
    policy = await signature_service.resolve_signature_requirement(
        session, record_type="ai_tool_call", action="authorize"
    )
    signature_id = None
    if policy.signature_required:
        signature_id = await _apply_signature(
            session, cmd, actor_user_id, record_version=1, policy=policy, action_label="ai_tool_call.authorize",
        )

    decision_row = AIToolDecision(
        use_case_id=use_case.id, advisory_id=cmd.advisory_id, tool_name=cmd.tool_name,
        args_hash=sha256_hex(cmd.args), decision="ALLOWED", reason=cmd.reason, user_id=actor_user_id,
    )
    session.add(decision_row)
    await session.flush()

    return await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=decision_row.id, version=1,
        action="Allowed", actor_user_id=actor_user_id, reason=cmd.reason, signature_id=signature_id,
        new_value={"tool_name": cmd.tool_name, "decision": "ALLOWED"},
        event_type="AIToolCallAllowed", expected_version=None,
        command_type="AuthorizeAIToolCall", aggregate_type="ai_tool_decision",
    )


# =================================================================================================
# FN-1011 recordHumanAIDisposition() -- AI-FR-005/034. SIGNED (see module docstring).
# =================================================================================================


class RecordHumanAIDispositionCommand(CommandEnvelope):
    advisory_id: uuid.UUID
    disposition: str
    comments: str | None = None
    downstream_record_ref: str | None = None
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def record_human_ai_disposition(
    session: AsyncSession, cmd: RecordHumanAIDispositionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    await evaluate_policy(session, actor_user_id, action="ai_governance.disposition.record", site_id=None)

    advisory = await session.get(AIAdvisoryLog, cmd.advisory_id)
    if advisory is None:
        raise NotFoundError("AI advisory not found")
    if cmd.disposition not in DISPOSITIONS:
        raise ValidationFailedError(f"disposition must be one of {DISPOSITIONS}")

    # SIGNATURE POLICY LOOKUP REQUIRED -- fails closed until Document 106 has a SPEC-AI-001 row (SG-167).
    policy = await signature_service.resolve_signature_requirement(
        session, record_type="ai_disposition", action="record"
    )
    signature_id = None
    if policy.signature_required:
        signature_id = await _apply_signature(
            session, cmd, actor_user_id, record_version=1, policy=policy, action_label="ai_disposition.record",
        )

    # AI-FR-034: this is an INSERT -- the original advisory (`advisory.output_json`) is never edited.
    row = AIDisposition(
        advisory_id=advisory.id, disposition=cmd.disposition, comments=cmd.comments,
        downstream_record_ref=cmd.downstream_record_ref, signature_id=signature_id, user_id=actor_user_id,
    )
    session.add(row)
    await session.flush()

    return await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=row.id, version=1,
        action="Created", actor_user_id=actor_user_id, reason=cmd.reason, signature_id=signature_id,
        new_value={"advisory_id": str(advisory.id), "disposition": cmd.disposition},
        event_type="AIAdvisoryDispositionRecorded", expected_version=None,
        command_type="RecordHumanAIDisposition", aggregate_type="ai_disposition",
    )


# =================================================================================================
# FN-1012 runAIEvaluationSuite() -- AI-FR-022/023/024. Not signed. `evaluator` is caller-injected (no
# live judge model in this environment); metrics are integer basis points, never float.
# =================================================================================================


class RunAIEvaluationSuiteCommand(CommandEnvelope):
    use_case_id: uuid.UUID
    model_deployment_id: uuid.UUID | None = None
    prompt_version_id: uuid.UUID | None = None
    dataset_ref: str
    scenario_classes: list[str] = []
    # AI-FR-024: per-dimension pass/fail thresholds in basis points (0-10000); dimensions named here
    # that come back below their threshold land in critical_failures regardless of the overall average.
    critical_thresholds_bp: dict[str, int] = {}
    reason: str


async def run_ai_evaluation_suite(
    session: AsyncSession, cmd: RunAIEvaluationSuiteCommand, actor_user_id: uuid.UUID,
    *, evaluator: Callable[[str, list[str]], Awaitable[dict[str, int]]],
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    await evaluate_policy(session, actor_user_id, action="ai_governance.evaluation.run", site_id=None)

    use_case = await session.get(AIUseCase, cmd.use_case_id)
    if use_case is None:
        raise NotFoundError("AI use case not found")
    if not cmd.dataset_ref:
        raise ValidationFailedError("dataset_ref is required")

    metrics_bp = await evaluator(cmd.dataset_ref, cmd.scenario_classes)
    critical_failures = [
        dim for dim, threshold in cmd.critical_thresholds_bp.items()
        if metrics_bp.get(dim, 0) < threshold
    ]
    passed = not critical_failures

    report = AIEvaluationReport(
        use_case_id=use_case.id, model_deployment_id=cmd.model_deployment_id,
        prompt_version_id=cmd.prompt_version_id, dataset_ref=cmd.dataset_ref,
        scenario_classes=cmd.scenario_classes, metrics=metrics_bp, critical_failures=critical_failures,
        passed=passed, actor_id=actor_user_id,
    )
    session.add(report)
    await session.flush()

    return await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=report.id, version=1,
        action="Created", actor_user_id=actor_user_id, reason=cmd.reason,
        new_value={"report_id": str(report.id), "passed": passed, "critical_failures": critical_failures},
        event_type="AIEvaluationCompleted", expected_version=None,
        command_type="RunAIEvaluationSuite", aggregate_type="ai_evaluation_report",
    )


# =================================================================================================
# FN-1013 evaluateAIReleaseGate() -- AI-FR-021/024. SIGNED (see module docstring).
# =================================================================================================


class EvaluateAIReleaseGateCommand(CommandEnvelope):
    use_case_id: uuid.UUID
    evaluation_report_id: uuid.UUID
    incidents_ref: list[str] = []
    vendor_security_status: str | None = None
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def evaluate_ai_release_gate(
    session: AsyncSession, cmd: EvaluateAIReleaseGateCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    await evaluate_policy(session, actor_user_id, action="ai_governance.release_gate.evaluate", site_id=None)

    report = await session.get(AIEvaluationReport, cmd.evaluation_report_id)
    if report is None:
        raise NotFoundError("Evaluation report not found")

    # SIGNATURE POLICY LOOKUP REQUIRED -- fails closed until Document 106 has a SPEC-AI-001 row (SG-167).
    policy = await signature_service.resolve_signature_requirement(
        session, record_type="ai_release_gate", action="evaluate"
    )
    signature_id = None
    if policy.signature_required:
        signature_id = await _apply_signature(
            session, cmd, actor_user_id, record_version=1, policy=policy, action_label="ai_release_gate.evaluate",
        )

    if report.critical_failures:
        # AI-FR-024: a critical failure class blocks release regardless of the overall average.
        decision, reason = "BLOCK", f"Critical evaluation failure: {report.critical_failures}"
    elif cmd.incidents_ref:
        decision, reason = "REVIEW", "Open incident references require human review before release"
    else:
        decision, reason = "PASS", cmd.reason

    gate = AIReleaseGate(
        use_case_id=cmd.use_case_id, evaluation_report_id=report.id, incidents_ref=cmd.incidents_ref,
        vendor_security_status=cmd.vendor_security_status, decision=decision, reason=reason,
        signature_id=signature_id, decided_by=actor_user_id,
    )
    session.add(gate)
    await session.flush()

    receipt = await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=gate.id, version=1,
        action="Created", actor_user_id=actor_user_id, reason=reason, signature_id=signature_id,
        new_value={"gate_id": str(gate.id), "decision": decision},
        event_type="AIReleaseGateEvaluated", expected_version=None,
        command_type="EvaluateAIReleaseGate", aggregate_type="ai_release_gate",
    )
    if decision == "BLOCK":
        # Real defect surfaced 2026-09-11 while resolving SG-167 (this raise was unreachable before --
        # resolve_signature_requirement() always raised SignaturePolicyUnresolvedError first, so a real
        # BLOCK evaluation could never previously reach this line). Raising here, inside the caller's
        # still-open `session.begin()` (router.py's post_release_gates), rolls the whole transaction
        # back -- the gate row just written above, its audit event, outbox event, receipt, and the
        # signature that was just consumed all vanish, exactly the "audit is immutable" guarantee AG-08
        # exists to protect. A critical-failure BLOCK is itself the record most worth keeping (AI-FR-024:
        # "cannot be forced to PASS around it" means the *decision* must stand, not that evidence of it
        # is allowed to disappear). Explicitly commit what has already been written before raising, so
        # the caller still receives the error (the HTTP response and behaviour AI-FR-024's test expects
        # are unchanged) but the gate/audit/outbox/signature are durable regardless.
        await session.commit()
        raise AIEvaluationCriticalFailureError(reason, evaluation_report_id=str(report.id))
    return receipt


# =================================================================================================
# FN-1014 detectPromptInjection() -- AI-FR-014/025. Not signed. Real deterministic pattern-matching
# defense-in-depth; NEVER treats matched content as policy (AI-FR-014) -- a match only ever blocks.
# =================================================================================================


class DetectPromptInjectionCommand(CommandEnvelope):
    use_case_id: uuid.UUID
    content: str
    block_on_detect: bool = True
    reason: str = "automated content screen"


async def detect_prompt_injection(
    session: AsyncSession, cmd: DetectPromptInjectionCommand, actor_user_id: uuid.UUID
) -> dict:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return {"receipt": _receipt_from_existing(existing)}

    await evaluate_policy(session, actor_user_id, action="ai_governance.injection.detect", site_id=None)

    matched = [p.pattern for p in _INJECTION_PATTERNS if p.search(cmd.content)]
    detected = bool(matched)
    action_taken = "BLOCKED" if (detected and cmd.block_on_detect) else "ALLOWED"

    event = AIPromptInjectionEvent(
        use_case_id=cmd.use_case_id, content_hash=sha256_hex(cmd.content), detected=detected,
        matched_patterns=matched, action_taken=action_taken,
    )
    session.add(event)
    await session.flush()

    await write_audit_event(
        session, site_id=None, aggregate_type="ai_prompt_injection_event", aggregate_id=event.id,
        aggregate_version=1, action="Created", actor_id=actor_user_id, correlation_id=uuid.uuid4(),
        reason=cmd.reason, new_value={"detected": detected, "action_taken": action_taken},
    )
    await write_outbox_event(
        session, event_type="PromptInjectionDetected", aggregate_type="ai_prompt_injection_event",
        aggregate_id=event.id, aggregate_version=1,
        payload={"detected": detected, "action_taken": action_taken}, correlation_id=uuid.uuid4(),
    )

    if action_taken == "BLOCKED":
        raise AIPromptInjectionBlockedError(
            "Retrieved/user content matched a known instruction-override pattern; escalation blocked",
            matched_patterns=matched,
        )
    return {"detected": detected, "matched_patterns": matched, "action_taken": action_taken}


# =================================================================================================
# FN-1015 switchAIProviderProfile() -- AI-FR-054. SIGNED (see module docstring).
# =================================================================================================


class SwitchAIProviderProfileCommand(CommandEnvelope):
    use_case_id: uuid.UUID
    to_model_deployment_id: uuid.UUID
    from_model_deployment_id: uuid.UUID | None = None
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def switch_ai_provider_profile(
    session: AsyncSession, cmd: SwitchAIProviderProfileCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    await evaluate_policy(session, actor_user_id, action="ai_governance.provider.switch", site_id=None)

    target = await session.get(AIModelDeployment, cmd.to_model_deployment_id)
    if target is None or target.state != "APPROVED":
        raise AIModelNotApprovedError("Target model deployment is not an approved deployment",
                                       model_deployment_id=str(cmd.to_model_deployment_id))

    # SIGNATURE POLICY LOOKUP REQUIRED -- fails closed until Document 106 has a SPEC-AI-001 row (SG-167).
    policy = await signature_service.resolve_signature_requirement(
        session, record_type="ai_provider_switch", action="switch"
    )
    signature_id = None
    if policy.signature_required:
        signature_id = await _apply_signature(
            session, cmd, actor_user_id, record_version=1, policy=policy, action_label="ai_provider_switch.switch",
        )

    switch = AIProviderSwitch(
        use_case_id=cmd.use_case_id, from_model_deployment_id=cmd.from_model_deployment_id,
        to_model_deployment_id=target.id, reason=cmd.reason, signature_id=signature_id,
        switched_by=actor_user_id,
    )
    session.add(switch)
    await session.flush()

    return await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=switch.id, version=1,
        action="Created", actor_user_id=actor_user_id, reason=cmd.reason, signature_id=signature_id,
        new_value={"use_case_id": str(cmd.use_case_id), "to_model_deployment_id": str(target.id)},
        event_type="AIProviderProfileChanged", expected_version=None,
        command_type="SwitchAIProviderProfile", aggregate_type="ai_provider_switch",
    )


# =================================================================================================
# FN-1016 retireAIUseCase() -- AI-FR-053. Not signed.
# =================================================================================================


class RetireAIUseCaseCommand(CommandEnvelope):
    use_case_id: uuid.UUID
    expected_version: int
    reason: str
    replacement: str | None = None
    effective_date: date | None = None


async def retire_ai_use_case(
    session: AsyncSession, cmd: RetireAIUseCaseCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    await evaluate_policy(session, actor_user_id, action="ai_governance.use_case.retire", site_id=None)

    use_case = await session.get(AIUseCase, cmd.use_case_id)
    if use_case is None:
        raise NotFoundError("AI use case not found")
    if use_case.version != cmd.expected_version:
        raise StaleVersionError("AI use case changed since this request was prepared",
                                 current_version=use_case.version)
    if use_case.state == "RETIRED":
        raise ValidationFailedError("Use case is already retired")

    old = {"state": use_case.state}
    use_case.state = "RETIRED"
    use_case.retirement_reason = cmd.reason
    use_case.retirement_replacement = cmd.replacement
    use_case.retirement_effective_date = cmd.effective_date
    use_case.retired_at = datetime.now(timezone.utc)
    use_case.version += 1
    await session.flush()

    return await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=use_case.id, version=use_case.version,
        action="Retired", actor_user_id=actor_user_id, reason=cmd.reason, old_value=old,
        new_value={"use_case_id": str(use_case.id), "state": "RETIRED"},
        event_type="AIUseCaseRetired", expected_version=cmd.expected_version,
        command_type="RetireAIUseCase",
    )


# =================================================================================================
# FN-1017 generateAIGovernancePackage() -- AI-FR-028/052. Not signed; read-only aggregation, no own
# table (audit-logged against the use case aggregate, matching build_ai_request_context's pattern).
# =================================================================================================


class GenerateAIGovernancePackageCommand(CommandEnvelope):
    use_case_id: uuid.UUID
    reason: str = "governance package export"


async def generate_ai_governance_package(
    session: AsyncSession, cmd: GenerateAIGovernancePackageCommand, actor_user_id: uuid.UUID
) -> dict:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return {"receipt": _receipt_from_existing(existing)}

    await evaluate_policy(session, actor_user_id, action="ai_governance.package.generate", site_id=None)

    use_case = await session.get(AIUseCase, cmd.use_case_id)
    if use_case is None:
        raise NotFoundError("AI use case not found")

    risk_assessments = (await session.execute(
        select(AIRiskAssessment).where(AIRiskAssessment.use_case_id == use_case.id)
    )).scalars().all()
    deployments = (await session.execute(
        select(AIModelDeployment).where(AIModelDeployment.use_case_id == use_case.id)
    )).scalars().all()
    evaluations = (await session.execute(
        select(AIEvaluationReport).where(AIEvaluationReport.use_case_id == use_case.id)
    )).scalars().all()
    gates = (await session.execute(
        select(AIReleaseGate).where(AIReleaseGate.use_case_id == use_case.id)
    )).scalars().all()
    prompts = (await session.execute(
        select(AIPromptVersion).where(AIPromptVersion.use_case_id == use_case.id)
    )).scalars().all()

    package = {
        "use_case": {"id": str(use_case.id), "name": use_case.name, "state": use_case.state,
                      "use_case_class": use_case.use_case_class},
        "risk_assessments": [str(r.id) for r in risk_assessments],
        "model_deployments": [str(d.id) for d in deployments],
        "prompt_versions": [str(p.id) for p in prompts],
        "evaluation_reports": [{"id": str(e.id), "passed": e.passed} for e in evaluations],
        "release_gates": [{"id": str(g.id), "decision": g.decision} for g in gates],
        "generated_at": datetime.now(timezone.utc).isoformat(),
    }

    await write_audit_event(
        session, site_id=use_case.site_id, aggregate_type="ai_use_case", aggregate_id=use_case.id,
        aggregate_version=use_case.version, action="GovernancePackageGenerated", actor_id=actor_user_id,
        correlation_id=uuid.uuid4(), reason=cmd.reason,
    )
    await write_outbox_event(
        session, event_type="AIGovernancePackageGenerated", aggregate_type="ai_use_case",
        aggregate_id=use_case.id, aggregate_version=use_case.version,
        payload={"evaluation_count": len(evaluations), "gate_count": len(gates)}, correlation_id=uuid.uuid4(),
    )
    return package
