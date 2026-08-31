from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.qc.commands import (
    ApproveDispositionCommand,
    ApproveResultCorrectionCommand,
    AuthorizeResamplePlanCommand,
    AuthorizeRetestPlanCommand,
    ClassifyLabCauseCommand,
    CloseOosCommand,
    CloseOotCommand,
    CompleteTestOrderCommand,
    CreateSampleCommand,
    CreateTestOrderCommand,
    CreateTestSpecificationDraftCommand,
    EvaluateOotCommand,
    OpenOosFromResultCommand,
    ReceiveSampleCommand,
    RecordImpactAssessmentCommand,
    RecordLabInvestigationCommand,
    RecordRawDataCommand,
    RecordResultCommand,
    ReleaseTestSpecificationCommand,
    RequestResultCorrectionCommand,
    ReviewTestOrderCommand,
    StartExtendedInvestigationCommand,
    StartTestOrderCommand,
    _record_hash,
    approve_disposition,
    approve_result_correction,
    authorize_resample_plan,
    authorize_retest_plan,
    classify_lab_cause,
    close_oos,
    close_oot,
    complete_test_order,
    create_sample,
    create_test_order,
    create_test_specification_draft,
    evaluate_oot,
    open_oos_from_result,
    receive_sample,
    record_impact_assessment,
    record_lab_investigation,
    record_raw_data,
    record_result,
    release_test_specification,
    request_result_correction,
    review_test_order,
    start_extended_investigation,
    start_test_order,
)
from app.modules.qc.models import (
    OosInvestigationActivity,
    OosRecord,
    OosResamplePlan,
    OosRetestPlan,
    OotRecord,
    QcResult,
    QcSample,
    QcTestOrder,
    QcTestRun,
    QcTestSpecification,
)
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/qc/v1", tags=["qc"])
oos_router = APIRouter(prefix="/quality", tags=["oos_oot"])


@router.post("/specifications/drafts", response_model=MutationReceipt)
async def post_create_specification_draft(
    cmd: CreateTestSpecificationDraftCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        return await create_test_specification_draft(session, cmd, actor.user_id)


class SpecificationSignatureChallengeRequest(BaseModel):
    action: str  # "release"


@router.post("/specifications/{specification_id}/signature-challenges")
async def post_specification_signature_challenge(
    specification_id: str,
    body: SpecificationSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        spec = await session.get(QcTestSpecification, specification_id)
        if spec is None:
            raise NotFoundError("Test specification not found")
        if body.action != "release":
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="qc_test_specification", record_id=spec.id,
            record_version=spec.version, record_hash=_record_hash(spec, "status"), meaning="Released",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/specifications/{specification_id}/release", response_model=MutationReceipt)
async def post_release_specification(
    specification_id: str,
    cmd: ReleaseTestSpecificationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.specification_id) != specification_id:
        raise ValidationFailedError("specification_id in path and body must match")
    async with session.begin():
        return await release_test_specification(session, cmd, actor.user_id)


@router.post("/samples", response_model=MutationReceipt)
async def post_create_sample(
    cmd: CreateSampleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        return await create_sample(session, cmd, actor.user_id)


@router.post("/samples/{sample_id}/receive", response_model=MutationReceipt)
async def post_receive_sample(
    sample_id: str,
    cmd: ReceiveSampleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.sample_id) != sample_id:
        raise ValidationFailedError("sample_id in path and body must match")
    async with session.begin():
        return await receive_sample(session, cmd, actor.user_id)


@router.get("/samples/{sample_id}/record")
async def get_sample_record(sample_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    sample = await session.get(QcSample, sample_id)
    if sample is None:
        raise NotFoundError("Sample not found")
    orders = (await session.execute(select(QcTestOrder).where(QcTestOrder.sample_id == sample.id))).scalars().all()
    order_payload = []
    for order in orders:
        runs = (await session.execute(select(QcTestRun).where(QcTestRun.test_order_id == order.id))).scalars().all()
        results = (await session.execute(select(QcResult).where(QcResult.test_order_id == order.id))).scalars().all()
        order_payload.append({
            "id": str(order.id),
            "state": order.state,
            # Every command against a test order carries expected_version (MUT-FR-009). Without it here a
            # client reading this record has no way to supply one and would have to guess -- so the record
            # that drives those commands reports the version they must echo back.
            "version": order.version,
            "assigned_analyst_id": str(order.assigned_analyst_id) if order.assigned_analyst_id else None,
            "runs": [str(r.id) for r in runs],
            "results": [{"id": str(r.id), "outcome": r.outcome, "result_version": r.result_version} for r in results],
        })
    return {
        "id": str(sample.id),
        "sample_number": sample.sample_number,
        "state": sample.state,
        "version": sample.version,
        "source_type": sample.source_type,
        "test_orders": order_payload,
    }


@router.get("/release-readiness")
async def get_release_readiness(sample_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    sample = await session.get(QcSample, sample_id)
    if sample is None:
        raise NotFoundError("Sample not found")
    orders = (await session.execute(select(QcTestOrder).where(QcTestOrder.sample_id == sample.id))).scalars().all()
    blocking_orders = [o for o in orders if o.blocking]
    ready = all(o.state == "reviewed" for o in blocking_orders) if blocking_orders else False
    return {
        "sample_id": str(sample.id),
        "ready": ready,
        "blocking_test_orders": [{"id": str(o.id), "state": o.state} for o in blocking_orders],
    }


@router.post("/test-orders", response_model=MutationReceipt)
async def post_create_test_order(
    cmd: CreateTestOrderCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        return await create_test_order(session, cmd, actor.user_id)


@router.post("/test-orders/{test_order_id}/start", response_model=MutationReceipt)
async def post_start_test_order(
    test_order_id: str,
    cmd: StartTestOrderCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.test_order_id) != test_order_id:
        raise ValidationFailedError("test_order_id in path and body must match")
    async with session.begin():
        return await start_test_order(session, cmd, actor.user_id)


@router.post("/test-orders/{test_order_id}/raw-data", response_model=MutationReceipt)
async def post_record_raw_data(
    test_order_id: str,
    cmd: RecordRawDataCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.test_order_id) != test_order_id:
        raise ValidationFailedError("test_order_id in path and body must match")
    async with session.begin():
        return await record_raw_data(session, cmd, actor.user_id)


@router.post("/test-orders/{test_order_id}/results", response_model=MutationReceipt)
async def post_record_result(
    test_order_id: str,
    cmd: RecordResultCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.test_order_id) != test_order_id:
        raise ValidationFailedError("test_order_id in path and body must match")
    async with session.begin():
        return await record_result(session, cmd, actor.user_id)


@router.post("/test-orders/{test_order_id}/complete", response_model=MutationReceipt)
async def post_complete_test_order(
    test_order_id: str,
    cmd: CompleteTestOrderCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.test_order_id) != test_order_id:
        raise ValidationFailedError("test_order_id in path and body must match")
    async with session.begin():
        return await complete_test_order(session, cmd, actor.user_id)


class TestOrderSignatureChallengeRequest(BaseModel):
    action: str  # "review"


@router.post("/test-orders/{test_order_id}/signature-challenges")
async def post_test_order_signature_challenge(
    test_order_id: str,
    body: TestOrderSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        order = await session.get(QcTestOrder, test_order_id)
        if order is None:
            raise NotFoundError("Test order not found")
        if body.action != "review":
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="qc_test_order", record_id=order.id,
            record_version=order.version, record_hash=_record_hash(order, "state"), meaning="Reviewed",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/test-orders/{test_order_id}/review", response_model=MutationReceipt)
async def post_review_test_order(
    test_order_id: str,
    cmd: ReviewTestOrderCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.test_order_id) != test_order_id:
        raise ValidationFailedError("test_order_id in path and body must match")
    async with session.begin():
        return await review_test_order(session, cmd, actor.user_id)


class ResultSignatureChallengeRequest(BaseModel):
    action: str  # "correct_request" | "correct_approve"


@router.post("/results/{result_id}/signature-challenges")
async def post_result_signature_challenge(
    result_id: str,
    body: ResultSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        result = await session.get(QcResult, result_id)
        if result is None:
            raise NotFoundError("Result not found")
        if body.action not in ("correct_request", "correct_approve"):
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="qc_result", record_id=result.id,
            record_version=result.result_version, record_hash=_record_hash(result, "outcome", version_field="result_version"), meaning="Approved",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/results/{result_id}/correct", response_model=MutationReceipt)
async def post_request_result_correction(
    result_id: str,
    cmd: RequestResultCorrectionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.result_id) != result_id:
        raise ValidationFailedError("result_id in path and body must match")
    async with session.begin():
        return await request_result_correction(session, cmd, actor.user_id)


@router.post("/corrections/{correction_id}/approve", response_model=MutationReceipt)
async def post_approve_result_correction(
    correction_id: str,
    cmd: ApproveResultCorrectionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.correction_id) != correction_id:
        raise ValidationFailedError("correction_id in path and body must match")
    async with session.begin():
        return await approve_result_correction(session, cmd, actor.user_id)


# ===========================================================================
# Document 25 (SPEC-QC-003) -- OOS/OOT Management. Same module, different declared path prefix
# (`/quality/oos/v1`, `/quality/oot/v1` per Document 25 §10 -- not `/qc/v1`).
# ===========================================================================


@oos_router.post("/oos/v1/from-result/{result_id}", response_model=MutationReceipt)
async def post_open_oos_from_result(
    result_id: str,
    cmd: OpenOosFromResultCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.source_result_id) != result_id:
        raise ValidationFailedError("resultId in path and source_result_id in body must match")
    async with session.begin():
        return await open_oos_from_result(session, cmd, actor.user_id)


@oos_router.get("/oos/v1/{oos_id}")
async def get_oos_record(oos_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    oos = await session.get(OosRecord, oos_id)
    if oos is None:
        raise NotFoundError("OOS record not found")
    activities = (
        await session.execute(select(OosInvestigationActivity).where(OosInvestigationActivity.oos_record_id == oos.id))
    ).scalars().all()
    retest_plans = (await session.execute(select(OosRetestPlan).where(OosRetestPlan.oos_record_id == oos.id))).scalars().all()
    resample_plans = (await session.execute(select(OosResamplePlan).where(OosResamplePlan.oos_record_id == oos.id))).scalars().all()
    return {
        "id": str(oos.id),
        "oos_number": oos.oos_number,
        "state": oos.state,
        "severity": oos.severity,
        "hold_status": oos.hold_status,
        "final_classification": oos.final_classification,
        "root_cause_code": oos.root_cause_code,
        "version": oos.version,
        "source_result_id": str(oos.source_result_id),
        "activities": [{"id": str(a.id), "phase": a.phase, "activity_type": a.activity_type} for a in activities],
        "retest_plans": [{"id": str(p.id), "status": p.status} for p in retest_plans],
        "resample_plans": [{"id": str(p.id), "status": p.status} for p in resample_plans],
    }


@oos_router.post("/oos/v1/{oos_id}/lab-investigation", response_model=MutationReceipt)
async def post_record_lab_investigation(
    oos_id: str,
    cmd: RecordLabInvestigationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.oos_record_id) != oos_id:
        raise ValidationFailedError("oos_id in path and body must match")
    async with session.begin():
        return await record_lab_investigation(session, cmd, actor.user_id)


@oos_router.post("/oos/v1/{oos_id}/classify-lab-cause", response_model=MutationReceipt)
async def post_classify_lab_cause(
    oos_id: str,
    cmd: ClassifyLabCauseCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.oos_record_id) != oos_id:
        raise ValidationFailedError("oos_id in path and body must match")
    async with session.begin():
        return await classify_lab_cause(session, cmd, actor.user_id)


class OosSignatureChallengeRequest(BaseModel):
    action: str  # "extended_investigation" | "disposition" | "close"


_OOS_CHALLENGE_MEANING = {"extended_investigation": "Approved", "disposition": "Released", "close": "Approved"}


@oos_router.post("/oos/v1/{oos_id}/signature-challenges")
async def post_oos_signature_challenge(
    oos_id: str,
    body: OosSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        oos = await session.get(OosRecord, oos_id)
        if oos is None:
            raise NotFoundError("OOS record not found")
        if body.action not in _OOS_CHALLENGE_MEANING:
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="oos_record", record_id=oos.id,
            record_version=oos.version, record_hash=_record_hash(oos, "state"),
            meaning=_OOS_CHALLENGE_MEANING[body.action],
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@oos_router.post("/oos/v1/{oos_id}/extended-investigation", response_model=MutationReceipt)
async def post_start_extended_investigation(
    oos_id: str,
    cmd: StartExtendedInvestigationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.oos_record_id) != oos_id:
        raise ValidationFailedError("oos_id in path and body must match")
    async with session.begin():
        return await start_extended_investigation(session, cmd, actor.user_id)


@oos_router.post("/oos/v1/{oos_id}/retest-plans", response_model=MutationReceipt)
async def post_authorize_retest_plan(
    oos_id: str,
    cmd: AuthorizeRetestPlanCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.oos_record_id) != oos_id:
        raise ValidationFailedError("oos_id in path and body must match")
    async with session.begin():
        return await authorize_retest_plan(session, cmd, actor.user_id)


@oos_router.post("/oos/v1/{oos_id}/resample-plans", response_model=MutationReceipt)
async def post_authorize_resample_plan(
    oos_id: str,
    cmd: AuthorizeResamplePlanCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.oos_record_id) != oos_id:
        raise ValidationFailedError("oos_id in path and body must match")
    async with session.begin():
        return await authorize_resample_plan(session, cmd, actor.user_id)


@oos_router.post("/oos/v1/{oos_id}/impact", response_model=MutationReceipt)
async def post_record_impact_assessment(
    oos_id: str,
    cmd: RecordImpactAssessmentCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.oos_record_id) != oos_id:
        raise ValidationFailedError("oos_id in path and body must match")
    async with session.begin():
        return await record_impact_assessment(session, cmd, actor.user_id)


@oos_router.post("/oos/v1/{oos_id}/disposition", response_model=MutationReceipt)
async def post_approve_disposition(
    oos_id: str,
    cmd: ApproveDispositionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.oos_record_id) != oos_id:
        raise ValidationFailedError("oos_id in path and body must match")
    async with session.begin():
        return await approve_disposition(session, cmd, actor.user_id)


@oos_router.post("/oos/v1/{oos_id}/close", response_model=MutationReceipt)
async def post_close_oos(
    oos_id: str,
    cmd: CloseOosCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.oos_record_id) != oos_id:
        raise ValidationFailedError("oos_id in path and body must match")
    async with session.begin():
        return await close_oos(session, cmd, actor.user_id)


@oos_router.post("/oot/v1/evaluate", response_model=MutationReceipt)
async def post_evaluate_oot(
    cmd: EvaluateOotCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        return await evaluate_oot(session, cmd, actor.user_id)


class OotSignatureChallengeRequest(BaseModel):
    action: str  # "close"


@oos_router.post("/oot/v1/{oot_id}/signature-challenges")
async def post_oot_signature_challenge(
    oot_id: str,
    body: OotSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        oot = await session.get(OotRecord, oot_id)
        if oot is None:
            raise NotFoundError("OOT record not found")
        if body.action != "close":
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="oot_record", record_id=oot.id,
            record_version=oot.version, record_hash=_record_hash(oot, "state"), meaning="Approved",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@oos_router.post("/oot/v1/{oot_id}/close", response_model=MutationReceipt)
async def post_close_oot(
    oot_id: str,
    cmd: CloseOotCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.oot_record_id) != oot_id:
        raise ValidationFailedError("oot_id in path and body must match")
    async with session.begin():
        return await close_oot(session, cmd, actor.user_id)
