"""Document 58 (SPEC-PM-001) REST surface, prefix `/postmarket/v1`.

`findProbableDuplicates()`, `calculateSurveillanceMetric()` and `evaluateSignalRules()` are named
functions with their own events in Document 58's contract catalogue but are missing from its terse
11-op `# 9. APIs` list -- exposed here as extra read/analytics operations (same precedent Document 54
used for its genealogy/review-summary endpoints), not the 11 that section names verbatim.
"""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from pydantic import BaseModel

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.postmarket import commands
from app.modules.postmarket.commands import _signal_hash
from app.modules.postmarket.models import SafetyCase, SafetySignal
from app.modules.signature.service import create_challenge, resolve_signature_requirement
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/postmarket/v1", tags=["postmarket"])


async def _create_signature_challenge(
    session: AsyncSession, *, actor: AuthenticatedActor, record_type: str, record_id: uuid.UUID,
    record_version: int, record_hash: str, action: str,
) -> dict:
    """Same shape as `app.modules.security.router._create_signature_challenge`, but resolves `meaning`
    from the Document 106 policy row instead of hardcoding it, so the challenge can never advertise a
    meaning the policy doesn't actually require (`app.modules.validation.signature_support` precedent)."""
    policy = await resolve_signature_requirement(session, record_type=record_type, action=action)
    challenge = await create_challenge(
        session, user_id=actor.user_id, record_type=record_type, record_id=record_id,
        record_version=record_version, record_hash=record_hash, meaning=policy.meaning,
    )
    return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


class OpenSignalChallengeRequest(BaseModel):
    """`safety_signal.open` signs a not-yet-created record (SG-156): the challenge binds to
    `sha256_hex({"signal_code": ...})` and `record_version=1`, exactly the hash
    `commands.open_safety_signal()` recomputes at consume time -- so the caller must supply the
    `signal_code` it is about to open before the record exists to load."""

    signal_code: str


@router.post("/sources", response_model=MutationReceipt)
async def post_register_source(
    cmd: commands.RegisterPostmarketSourceCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="postmarket_source.register", site_id=cmd.site_id)
        return await commands.register_postmarket_source(session, cmd, actor.user_id)


@router.post("/safety-cases", response_model=MutationReceipt)
async def post_create_safety_case(
    cmd: commands.CreateSafetyCaseLinkCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="safety_case.create", site_id=cmd.site_id)
        return await commands.create_safety_case_link(session, cmd, actor.user_id)


@router.post("/safety-cases/{case_id}/resolve-product", response_model=MutationReceipt)
async def post_resolve_product(
    case_id: uuid.UUID, cmd: commands.ResolveMarketedProductCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.case_id != case_id:
        raise ValidationFailedError("case_id in path and body must match")
    async with session.begin():
        case = await session.get(SafetyCase, case_id)
        if case is None:
            raise NotFoundError("Safety case not found")
        await evaluate_policy(session, actor.user_id, action="safety_case.resolve_product", site_id=case.site_id)
        return await commands.resolve_marketed_product(session, cmd, actor.user_id)


@router.post("/safety-cases/{case_id}/classifications", response_model=MutationReceipt)
async def post_classify_case(
    case_id: uuid.UUID, cmd: commands.ClassifySafetyCaseCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.case_id != case_id:
        raise ValidationFailedError("case_id in path and body must match")
    async with session.begin():
        case = await session.get(SafetyCase, case_id)
        if case is None:
            raise NotFoundError("Safety case not found")
        await evaluate_policy(session, actor.user_id, action="safety_case.classify", site_id=case.site_id)
        return await commands.classify_safety_case(session, cmd, actor.user_id)


@router.post("/safety-cases/{case_id}/followups", response_model=MutationReceipt)
async def post_add_followup(
    case_id: uuid.UUID, cmd: commands.AddSafetyCaseFollowupCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.case_id != case_id:
        raise ValidationFailedError("case_id in path and body must match")
    async with session.begin():
        case = await session.get(SafetyCase, case_id)
        if case is None:
            raise NotFoundError("Safety case not found")
        await evaluate_policy(session, actor.user_id, action="safety_case.followup", site_id=case.site_id)
        return await commands.add_safety_case_followup(session, cmd, actor.user_id)


@router.get("/safety-cases/{case_id}/duplicate-candidates")
async def get_duplicate_candidates(
    case_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    async with session.begin():
        case = await session.get(SafetyCase, case_id)
        if case is None:
            raise NotFoundError("Safety case not found")
        await evaluate_policy(session, actor.user_id, action="safety_case.view", site_id=case.site_id)
        return await commands.find_probable_duplicates(session, commands.FindProbableDuplicatesCommand(case_id=case_id, idempotency_key=str(uuid.uuid4())))


@router.post("/safety-cases/{case_id}/duplicate-links", response_model=MutationReceipt)
async def post_link_duplicates(
    case_id: uuid.UUID, cmd: commands.LinkDuplicateCasesCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.canonical_case_id != case_id:
        raise ValidationFailedError("case_id in path must match canonical_case_id in body")
    async with session.begin():
        case = await session.get(SafetyCase, case_id)
        if case is None:
            raise NotFoundError("Safety case not found")
        await evaluate_policy(session, actor.user_id, action="safety_case.link_duplicates", site_id=case.site_id)
        return await commands.link_duplicate_cases(session, cmd, actor.user_id)


@router.post("/surveillance-metrics:calculate")
async def post_calculate_surveillance_metric(
    cmd: commands.CalculateSurveillanceMetricCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="safety_signal.view", site_id=None)
        return await commands.calculate_surveillance_metric(session, cmd, actor.user_id)


@router.post("/signal-rules:evaluate")
async def post_evaluate_signal_rules(
    cmd: commands.EvaluateSignalRulesCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="safety_signal.view", site_id=None)
        return await commands.evaluate_signal_rules(session, cmd)


@router.post("/signals/signature-challenges")
async def post_open_signal_signature_challenge(
    body: OpenSignalChallengeRequest, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        return await _create_signature_challenge(
            session, actor=actor, record_type="safety_signal", record_id=uuid.uuid4(),
            record_version=1, record_hash=sha256_hex({"signal_code": body.signal_code}), action="open",
        )


@router.post("/signals", response_model=MutationReceipt)
async def post_open_signal(
    cmd: commands.OpenSafetySignalCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="safety_signal.open", site_id=cmd.site_id)
        return await commands.open_safety_signal(session, cmd, actor.user_id)


@router.post("/signals/{signal_id}/assessment-signature-challenges")
async def post_assess_signal_signature_challenge(
    signal_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        signal = await session.get(SafetySignal, signal_id)
        if signal is None:
            raise NotFoundError("Safety signal not found")
        return await _create_signature_challenge(
            session, actor=actor, record_type="safety_signal", record_id=signal.id,
            record_version=signal.version, record_hash=_signal_hash(signal), action="assess",
        )


@router.post("/signals/{signal_id}/assessments", response_model=MutationReceipt)
async def post_assess_signal(
    signal_id: uuid.UUID, cmd: commands.AssessSafetySignalCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.signal_id != signal_id:
        raise ValidationFailedError("signal_id in path and body must match")
    async with session.begin():
        signal = await session.get(SafetySignal, signal_id)
        if signal is None:
            raise NotFoundError("Safety signal not found")
        await evaluate_policy(session, actor.user_id, action="safety_signal.assess", site_id=signal.site_id)
        return await commands.assess_safety_signal(session, cmd, actor.user_id)


@router.post("/signals/{signal_id}/escalation-signature-challenges")
async def post_escalate_signal_signature_challenge(
    signal_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        signal = await session.get(SafetySignal, signal_id)
        if signal is None:
            raise NotFoundError("Safety signal not found")
        return await _create_signature_challenge(
            session, actor=actor, record_type="safety_signal", record_id=signal.id,
            record_version=signal.version, record_hash=_signal_hash(signal), action="escalate",
        )


@router.post("/signals/{signal_id}/escalations", response_model=MutationReceipt)
async def post_escalate_signal(
    signal_id: uuid.UUID, cmd: commands.EscalateSignalCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.signal_id != signal_id:
        raise ValidationFailedError("signal_id in path and body must match")
    async with session.begin():
        signal = await session.get(SafetySignal, signal_id)
        if signal is None:
            raise NotFoundError("Safety signal not found")
        await evaluate_policy(session, actor.user_id, action="safety_signal.escalate", site_id=signal.site_id)
        return await commands.escalate_signal_to_qms_or_regulatory(session, cmd, actor.user_id)


@router.post("/periodic-datasets:freeze")
async def post_freeze_periodic_dataset(
    cmd: commands.BuildPeriodicSafetyDatasetCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="postmarket_dataset.freeze", site_id=cmd.site_id)
        return await commands.build_periodic_safety_dataset(session, cmd, actor.user_id)


@router.get("/dashboard")
async def get_dashboard(
    site_id: uuid.UUID | None = None, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="safety_signal.view", site_id=site_id)
        return await commands.get_postmarket_dashboard(session, site_id)
