import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qc.commands import (
    ApproveDispositionCommand,
    ApproveResultCorrectionCommand,
    AuthorizeResamplePlanCommand,
    AuthorizeRetestPlanCommand,
    ClassifyLabCauseCommand,
    CloseOosCommand,
    CloseOotCommand,
    CompleteTestOrderCommand,
    CreateQcMethodDraftCommand,
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
    ReleaseQcMethodVersionCommand,
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
    create_qc_method_draft,
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
    release_qc_method_version,
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
    QcMethodVersion,
    QcResult,
    QcSample,
    QcTestDefinition,
    QcTestOrder,
    QcTestRun,
    QcTestSpecification,
)
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/qc/v1", tags=["qc"])
oos_router = APIRouter(prefix="/quality", tags=["oos_oot"])


SPECIFICATION_SORTABLE = {
    "spec_code": QcTestSpecification.spec_code,
    "created_at": QcTestSpecification.created_at,
}


def _specification_dict(spec: QcTestSpecification, definitions: list[QcTestDefinition]) -> dict:
    return {
        "id": str(spec.id), "spec_code": spec.spec_code, "version_no": spec.version_no, "status": spec.status,
        "scope_type": spec.scope_type, "scope_version_id": str(spec.scope_version_id), "version": spec.version,
        "test_definitions": [
            {
                "id": str(d.id), "test_code": d.test_code, "test_name": d.test_name,
                "result_data_type": d.result_data_type, "uom": d.uom,
            }
            for d in definitions
        ],
    }


@router.get("/specifications")
async def list_specifications(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params),
) -> dict:
    """Real picker data for every place that needs a test specification/definition -- /qc's own "Add
    test order" (previously free-text 'Test definition ID' entry) and the browsable list a spec/release
    UI needs to exist at all; there was no way to see what specifications existed, only create one blind
    via a direct API call. Same SG-081 read-side precedent as everywhere else this pass. Paginated (shared
    envelope) so the frontend's DataTable can page/search/sort it like every other list; no site scoping
    on this table (see model docstring)."""
    async with session.begin():
        stmt = select(QcTestSpecification)
        if params.q:
            stmt = stmt.where(QcTestSpecification.spec_code.ilike(f"%{params.q}%"))
        rows, envelope = await paginate(
            session, stmt, params, sortable=SPECIFICATION_SORTABLE, default_sort=QcTestSpecification.created_at
        )
        specs = [s for (s,) in rows]
        defs_by_spec: dict[str, list[QcTestDefinition]] = {}
        if specs:
            def_rows = (
                await session.execute(
                    select(QcTestDefinition).where(QcTestDefinition.specification_id.in_([s.id for s in specs]))
                )
            ).scalars().all()
            for d in def_rows:
                defs_by_spec.setdefault(str(d.specification_id), []).append(d)
        return {**envelope, "items": [_specification_dict(s, defs_by_spec.get(str(s.id), [])) for s in specs]}


SAMPLE_SORTABLE = {
    "sample_number": QcSample.sample_number,
    "created_at": QcSample.created_at,
}


@router.get("/samples")
async def list_samples(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params),
) -> dict:
    """Browsable list for /qc's own "Samples" section -- previously no way to see what samples existed
    at all, only open one already-known by id. Same SG-081 read-side precedent as everywhere else this
    pass. No site scoping on this table (see model docstring)."""
    async with session.begin():
        stmt = select(QcSample)
        if params.q:
            stmt = stmt.where(QcSample.sample_number.ilike(f"%{params.q}%"))
        rows, envelope = await paginate(session, stmt, params, sortable=SAMPLE_SORTABLE, default_sort=QcSample.created_at)
        samples = [s for (s,) in rows]
        return {
            **envelope,
            "items": [
                {
                    "id": str(s.id), "sample_number": s.sample_number, "sample_type": s.sample_type,
                    "source_type": s.source_type, "state": s.state,
                }
                for s in samples
            ],
        }


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


def _qc_method_dict(m: QcMethodVersion) -> dict:
    return {
        "method_version_id": str(m.id),
        "method_code": m.method_code,
        "version_no": m.version_no,
        "name": m.name,
        "method_type": m.method_type,
        "validation_evidence_reference": m.validation_evidence_reference,
        "modification_reason": m.modification_reason,
        "lifecycle_state": m.lifecycle_state,
        "effective_from": m.effective_from.isoformat() if m.effective_from else None,
        "effective_to": m.effective_to.isoformat() if m.effective_to else None,
        "released_vault_object_id": str(m.released_vault_object_id) if m.released_vault_object_id else None,
        "version_hash": m.version_hash,
        "version": m.version,
        "site_id": str(m.site_id),
    }


@router.post("/methods/drafts", response_model=MutationReceipt)
async def post_create_qc_method_draft(
    cmd: CreateQcMethodDraftCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qc_method.author", site_id=cmd.site_id)
        return await create_qc_method_draft(session, cmd, actor.user_id)


@router.get("/methods/{method_code}/versions")
async def get_qc_method_versions(
    method_code: str,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    await evaluate_policy(session, actor.user_id, action="qc_method.view", site_id=None)
    versions = (
        await session.execute(
            select(QcMethodVersion).where(QcMethodVersion.method_code == method_code).order_by(QcMethodVersion.version_no)
        )
    ).scalars().all()
    return [_qc_method_dict(v) for v in versions]


@router.get("/methods/{method_version_id}")
async def get_qc_method_version_detail(
    method_version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="qc_method.view", site_id=None)
    method = await session.get(QcMethodVersion, method_version_id)
    if method is None:
        raise NotFoundError("QC method version not found")
    return _qc_method_dict(method)


class QcMethodSignatureChallengeRequest(BaseModel):
    action: str  # "release"


@router.post("/methods/{method_version_id}/signature-challenges")
async def post_qc_method_signature_challenge(
    method_version_id: uuid.UUID,
    body: QcMethodSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """SG-186 RESOLVED (2026-09-18): qc_method_version/release now has a real Document 106 signature
    policy row (scripts/seed.py SIGNATURE_POLICY_FLOOR) -- "Released" by an independent QA Releaser,
    same shape as the nearest in-module precedent, qc_test_specification/release (row 58)."""
    async with session.begin():
        method = await session.get(QcMethodVersion, method_version_id)
        if method is None:
            raise NotFoundError("QC method version not found")
        if body.action != "release":
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="qc_method_version", record_id=method.id,
            record_version=method.version, record_hash=_record_hash(method, "lifecycle_state"), meaning="Released",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/methods/drafts/{method_version_id}/release", response_model=MutationReceipt)
async def post_release_qc_method_version(
    method_version_id: uuid.UUID,
    cmd: ReleaseQcMethodVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.method_version_id != method_version_id:
        raise ValidationFailedError("method_version_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qc_method.release", site_id=None)
        return await release_qc_method_version(session, cmd, actor.user_id)


@router.post("/samples", response_model=MutationReceipt)
async def post_create_sample(
    cmd: CreateSampleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    # 2026-09-18 RBAC gap closure: gated here, not inside create_sample() itself, because that function
    # is also called internally (already-authorized) by material/commands.py::collect_sample(),
    # equipment/cleaning_commands.py and lims_integration/commands.py.
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qc_sample.create", site_id=None)
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
    # 2026-09-18 RBAC gap closure: gated here (see post_create_sample's comment above) -- also called
    # internally by lims_integration/commands.py's already-authorized flow.
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qc_sample.receive", site_id=None)
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
        "sample_type": sample.sample_type,
        "state": sample.state,
        "version": sample.version,
        "source_type": sample.source_type,
        "source_id": str(sample.source_id) if sample.source_id else None,
        "source_location_ref": sample.source_location_ref,
        "lot_batch_serial_ref": sample.lot_batch_serial_ref,
        "sample_quantity": str(sample.sample_quantity) if sample.sample_quantity is not None else None,
        "sample_uom": sample.sample_uom,
        "sample_uom_id": str(sample.sample_uom_id) if sample.sample_uom_id else None,
        "sampled_at": sample.sampled_at.isoformat() if sample.sampled_at else None,
        "received_at": sample.received_at.isoformat() if sample.received_at else None,
        "sampler_subject_id": str(sample.sampler_subject_id) if sample.sampler_subject_id else None,
        "stability_study_ref": sample.stability_study_ref,
        "test_orders": order_payload,
    }


@router.get("/results")
async def list_results_for_batch(batch_id: str, session: AsyncSession = Depends(get_session)) -> list[dict]:
    """Real picker data for any field that references a `qc_result` row by id -- DDCP's "Link a device
    functional test" `qc_record_reference` (ddcp/commands.py's own comment: "References the owning
    qc.qc_result row, never duplicates it") is the first caller, previously free-text UUID entry with no
    way to discover a real one. Same SG-081 read-side precedent as every other picker added this pass.

    `QcSample.source_id` is a polymorphic reference (see that model's own docstring) validated only for
    a handful of source_types -- 'batch' is one of them, so this filters on exactly that rather than
    guessing at samples pulled some other way. Newest first."""
    rows = (
        await session.execute(
            select(QcResult, QcTestDefinition.test_name)
            .join(QcTestOrder, QcTestOrder.id == QcResult.test_order_id)
            .join(QcSample, QcSample.id == QcTestOrder.sample_id)
            .join(QcTestDefinition, QcTestDefinition.id == QcTestOrder.test_definition_id)
            .where(QcSample.source_type == "batch", QcSample.source_id == batch_id)
            .order_by(QcResult.created_at.desc())
        )
    ).all()
    return [
        {
            "id": str(result.id),
            "label": (
                f"{test_name} — {result.result_type} "
                f"{result.value_decimal if result.value_decimal is not None else (result.value_text or '')} "
                f"({result.outcome})"
            ).strip(),
        }
        for result, test_name in rows
    ]


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
    # 2026-09-18 RBAC gap closure: gated here (see post_create_sample's comment above) -- also called
    # internally by lims_integration/commands.py's already-authorized flow.
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qc_test_order.start", site_id=None)
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
    # 2026-09-18 RBAC gap closure: gated here (see post_create_sample's comment above) -- also called
    # internally by lims_integration/commands.py's already-authorized flow.
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qc_test_order.record_raw_data", site_id=None)
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
    # 2026-09-18 RBAC gap closure: gated here (see post_create_sample's comment above) -- also called
    # internally by lims_integration/commands.py's already-authorized flow.
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qc_result.record", site_id=None)
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
        "site_id": str(oos.site_id) if oos.site_id else None,
        "oos_number": oos.oos_number,
        "source_result_id": str(oos.source_result_id),
        "sample_id": str(oos.sample_id) if oos.sample_id else None,
        "test_order_id": str(oos.test_order_id) if oos.test_order_id else None,
        "batch_id": str(oos.batch_id) if oos.batch_id else None,
        "material_lot_id": str(oos.material_lot_id) if oos.material_lot_id else None,
        "state": oos.state,
        "severity": oos.severity,
        "hold_status": oos.hold_status,
        "final_classification": oos.final_classification,
        "root_cause_code": oos.root_cause_code,
        "version": oos.version,
        "opened_at": oos.opened_at.isoformat() if oos.opened_at else None,
        "closed_at": oos.closed_at.isoformat() if oos.closed_at else None,
        "activities": [
            {
                "id": str(a.id), "phase": a.phase, "activity_type": a.activity_type,
                "checklist_item": a.checklist_item, "response_text": a.response_text,
                "evidence_refs": a.evidence_refs, "investigator_user_id": str(a.investigator_user_id),
                "occurred_at": a.occurred_at.isoformat() if a.occurred_at else None, "version": a.version,
            }
            for a in activities
        ],
        "retest_plans": [
            {
                "id": str(p.id), "justification": p.justification, "number_of_retests": p.number_of_retests,
                "method_ref": p.method_ref, "analyst_criteria": p.analyst_criteria,
                "instrument_criteria": p.instrument_criteria, "interpretation_rule": p.interpretation_rule,
                "status": p.status, "version": p.version,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in retest_plans
        ],
        "resample_plans": [
            {
                "id": str(p.id), "scientific_rationale": p.scientific_rationale,
                "sampling_plan_ref": p.sampling_plan_ref, "sampling_plan_version": p.sampling_plan_version,
                "source_ref": p.source_ref,
                "approver_user_id": str(p.approver_user_id) if p.approver_user_id else None,
                "resulting_sample_ids": p.resulting_sample_ids, "status": p.status, "version": p.version,
                "created_at": p.created_at.isoformat() if p.created_at else None,
            }
            for p in resample_plans
        ],
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
