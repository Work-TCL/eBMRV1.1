import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qms.risk_commands import (
    AcceptRiskCommand,
    AddAssessmentCommand,
    AddControlsCommand,
    CreateRiskCommand,
    ReviewRiskCommand,
    accept_risk,
    add_assessment,
    add_controls,
    create_risk,
    review_risk,
)
from app.modules.qms.risk_models import RiskAssessmentVersion, RiskRecord
from app.modules.qms.read_support import filtered, iso, sid
from app.modules.qms.signature_support import SignatureChallengeRequest, create_qms_signature_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

risk_router = APIRouter(prefix="/qms/v1/risks", tags=["qms-risk"])

RISK_SIGNATURE_ACTIONS = ("review",)


@risk_router.post("", response_model=MutationReceipt)
async def post_create_risk(
    cmd: CreateRiskCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="risk.create", site_id=cmd.site_id)
        return await create_risk(session, cmd, actor.user_id)


@risk_router.post("/{risk_id}/assessments", response_model=MutationReceipt)
async def post_add_assessment(
    risk_id: uuid.UUID, cmd: AddAssessmentCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.risk_id != risk_id:
        raise ValidationFailedError("risk_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="risk.assessment.add", site_id=None)
        return await add_assessment(session, cmd, actor.user_id)


@risk_router.post("/{risk_id}/controls", response_model=MutationReceipt)
async def post_add_controls(
    risk_id: uuid.UUID, cmd: AddControlsCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.risk_id != risk_id:
        raise ValidationFailedError("risk_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="risk.controls.add", site_id=None)
        return await add_controls(session, cmd, actor.user_id)


@risk_router.post("/{risk_id}/accept", response_model=MutationReceipt)
async def post_accept_risk(
    risk_id: uuid.UUID, cmd: AcceptRiskCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.risk_id != risk_id:
        raise ValidationFailedError("risk_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="risk.accept", site_id=None)
        return await accept_risk(session, cmd, actor.user_id)


@risk_router.post("/{risk_id}/review", response_model=MutationReceipt)
async def post_review_risk(
    risk_id: uuid.UUID, cmd: ReviewRiskCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.risk_id != risk_id:
        raise ValidationFailedError("risk_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="risk.review", site_id=None)
        return await review_risk(session, cmd, actor.user_id)


@risk_router.post("/{risk_id}/signature-challenges")
async def post_signature_challenge(
    risk_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        risk = await session.get(RiskRecord, risk_id)
        if risk is None:
            raise NotFoundError("Risk record not found")
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="risk_record", record=risk,
            action=body.action, allowed_actions=RISK_SIGNATURE_ACTIONS,
        )


@risk_router.get("/dashboard")
async def get_dashboard(
    site_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """RSK-FR-017: heatmap/trends/overdue mitigations. A rebuildable, non-authoritative read (AG-11) --
    the underlying risk_record/risk_assessment_version rows remain the authority for any decision.
    """
    await evaluate_policy(session, actor.user_id, action="risk.dashboard.view", site_id=site_id)
    risks = (await session.execute(select(RiskRecord).where(RiskRecord.site_id == site_id))).scalars().all()
    now = datetime.now(timezone.utc)

    rows = []
    by_state: dict[str, int] = {}
    by_type: dict[str, int] = {}
    overdue_count = 0
    for risk in risks:
        by_state[risk.state] = by_state.get(risk.state, 0) + 1
        by_type[risk.risk_type] = by_type.get(risk.risk_type, 0) + 1
        version = (
            await session.execute(
                select(RiskAssessmentVersion).where(
                    RiskAssessmentVersion.risk_record_id == risk.id, RiskAssessmentVersion.is_current.is_(True)
                )
            )
        ).scalar_one_or_none()
        due = risk.next_review_due_at
        is_overdue = bool(due and due.replace(tzinfo=timezone.utc) < now and risk.state == "ACCEPTED")
        if is_overdue:
            overdue_count += 1
        rows.append({
            "id": str(risk.id), "risk_number": risk.risk_number, "risk_type": risk.risk_type,
            "state": risk.state, "next_review_due_at": due.isoformat() if due else None, "is_overdue": is_overdue,
            "initial_score": version.initial_score if version else None,
            "residual_score": version.residual_score if version else None,
        })

    return {
        "site_id": str(site_id), "risks": rows, "by_state": by_state, "by_type": by_type,
        "overdue_count": overdue_count,
    }


# --- Read side ---------------------------------------------------------------------------------

RISK_SORTABLE = {
    "risk_number": RiskRecord.risk_number,
    "risk_type": RiskRecord.risk_type,
    "state": RiskRecord.state,
    "next_review_due_at": RiskRecord.next_review_due_at,
    "created_at": RiskRecord.created_at,
}


def _risk_dict(record: RiskRecord) -> dict:
    return {
        "id": str(record.id),
        "site_id": str(record.site_id),
        "quality_event_id": str(record.quality_event_id),
        "risk_number": record.risk_number,
        "risk_type": record.risk_type,
        "hazard_problem": record.hazard_problem,
        "potential_effect": record.potential_effect,
        "owner_subject_id": str(record.owner_subject_id),
        "next_review_due_at": iso(record.next_review_due_at),
        "state": record.state,
        "version": record.version,
        "created_at": iso(record.created_at),
    }


@risk_router.get("")
async def list_risks(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    state: str | None = None,
) -> dict:
    await evaluate_policy(session, actor.user_id, action="risk.view", site_id=site_id)
    stmt = filtered(RiskRecord, params, search_column=RiskRecord.risk_number, site_id=site_id, state=state)
    rows, envelope = await paginate(
        session, stmt, params, sortable=RISK_SORTABLE, default_sort=RiskRecord.created_at
    )
    return {**envelope, "items": [_risk_dict(r) for (r,) in rows]}


@risk_router.get("/{risk_id}")
async def get_risk(
    risk_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    record = await session.get(RiskRecord, risk_id)
    if record is None:
        raise NotFoundError("Risk record not found")
    await evaluate_policy(session, actor.user_id, action="risk.view", site_id=record.site_id)
    versions = (
        await session.execute(
            select(RiskAssessmentVersion)
            .where(RiskAssessmentVersion.risk_record_id == risk_id)
            .order_by(RiskAssessmentVersion.cycle_number)
        )
    ).scalars().all()
    return {
        **_risk_dict(record),
        "methodology_id": sid(record.methodology_id),
        "context": record.context,
        "assessment_versions": [
            {
                "id": str(v.id),
                "cycle_number": v.cycle_number,
                "methodology_version": v.methodology_version,
                "scoring_inputs": v.scoring_inputs,
                "initial_score": v.initial_score,
                "controls": v.controls,
                "mitigation_actions": v.mitigation_actions,
                "residual_inputs": v.residual_inputs,
                "residual_score": v.residual_score,
                "acceptance_criteria": v.acceptance_criteria,
                "acceptance": v.acceptance,
                "review_history": v.review_history,
                "is_current": v.is_current,
                "created_at": iso(v.created_at),
                "closed_at": iso(v.closed_at),
            }
            for v in versions
        ],
    }
