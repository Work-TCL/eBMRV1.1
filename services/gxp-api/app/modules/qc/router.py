import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import and_, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.batch_execution.models import BatchStep
from app.modules.material_specification.models import MaterialSpecificationVersion
from app.modules.policy.service import evaluate_policy, resolve_site_scope
from app.modules.product_master.models import ProductVersion
from app.modules.qms.read_support import filtered, iso, sid
from app.modules.recipe_master.models import RecipeFamily, RecipeVersion
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
    LinkOosChangeControlCommand,
    OpenOosFromResultCommand,
    ReceiveSampleCommand,
    RecordImpactAssessmentCommand,
    RecordLabInvestigationCommand,
    RecordRawDataCommand,
    RecordResultCommand,
    ReleaseQcMethodVersionCommand,
    ReleaseTestSpecificationCommand,
    ReopenOosCommand,
    ReopenOotCommand,
    RequestResultCorrectionCommand,
    ReviewTestOrderCommand,
    StartExtendedInvestigationCommand,
    StartTestOrderCommand,
    _check_qc_analyst_qualification,
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
    get_oos_linked_capas,
    link_oos_change_control,
    open_oos_from_result,
    receive_sample,
    record_impact_assessment,
    record_lab_investigation,
    record_raw_data,
    record_result,
    release_qc_method_version,
    release_test_specification,
    reopen_oos,
    reopen_oot,
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
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
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


async def _resolve_scope_label(session: AsyncSession, scope_type: str, scope_version_id: uuid.UUID) -> dict | None:
    """Client gap-analysis follow-up: a QC test specification's `scope_version_id` is a bare, opaque UUID
    in the detail response -- a QA reviewer opening a spec created off a material/product/recipe release
    (see material_specification.commands.release_material_spec_version's QC-FR-001 bridge) had no way to
    get back to the record it was generated from short of copying that UUID into a DB query. Mirrors
    SCOPE_TABLE_BY_TYPE in qc.commands (the same scope_type -> owning-table mapping used to validate the
    id on create) but resolves a human business-id/version label instead of just existence.
    """
    if scope_type in ("product", "device"):
        version = await session.get(ProductVersion, scope_version_id)
        if version is None:
            return None
        return {
            "label": f"{version.product_business_id} v{version.version_no}",
            "href": f"/product-master?product_version_id={version.id}",
        }
    if scope_type == "material":
        version = await session.get(MaterialSpecificationVersion, scope_version_id)
        if version is None:
            return None
        return {
            "label": f"{version.material_spec_business_id} v{version.version_no}",
            "href": f"/material-specifications?material_spec_version_id={version.id}",
        }
    if scope_type == "in_process":
        version = await session.get(RecipeVersion, scope_version_id)
        if version is None:
            return None
        recipe_code = await session.scalar(select(RecipeFamily.recipe_code).where(RecipeFamily.id == version.recipe_family_id))
        return {
            "label": f"{recipe_code or 'recipe'} v{version.version_no}",
            "href": f"/recipe-master/{version.id}",
        }
    return None


@router.get("/specifications/{spec_id}")
async def get_specification(
    spec_id: str,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Detail read backing the /qc/specifications/{id} page — no single-record GET existed before this
    (only the list above), so a detail page had to resolve the id against the already-loaded list page's
    picker data instead. Reuses _specification_dict, the same shaping the list endpoint already uses."""
    spec = await session.get(QcTestSpecification, spec_id)
    if spec is None:
        raise NotFoundError("Test specification not found")
    definitions = (
        await session.execute(select(QcTestDefinition).where(QcTestDefinition.specification_id == spec.id))
    ).scalars().all()
    return {
        **_specification_dict(spec, list(definitions)),
        "scope_record": await _resolve_scope_label(session, spec.scope_type, spec.scope_version_id),
    }


SAMPLE_SORTABLE = {
    "sample_number": QcSample.sample_number,
    "created_at": QcSample.created_at,
}


@router.get("/samples")
async def list_samples(
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
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


METHOD_SORTABLE = {
    "method_code": QcMethodVersion.method_code,
    "created_at": QcMethodVersion.created_at,
}


@router.get("/methods")
async def list_qc_methods(
    session: AsyncSession = Depends(get_session),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """Browsable list of every method VERSION row (not deduplicated by method_code -- each version is
    its own regulated record) backing /qc's "QC method master" section. Previously this had no list-all
    endpoint at all -- only "versions by method_code" and "single by id" -- so the UI was a deliberate
    code-lookup console rather than a browsable table (see that page's own comment). Same qc_method.view
    policy gate as the other two method reads."""
    # SG-213: site_id=None here used to mean "any site holding qc_method.view anywhere" -- resolve_site_scope
    # turns an omitted site_id into only the sites the actor actually holds the action at.
    site_scope = await resolve_site_scope(session, actor.user_id, site_id, action="qc_method.view")
    stmt = select(QcMethodVersion).where(QcMethodVersion.site_id.in_(site_scope))
    if params.q:
        stmt = stmt.where(QcMethodVersion.method_code.ilike(f"%{params.q}%"))
    rows, envelope = await paginate(session, stmt, params, sortable=METHOD_SORTABLE, default_sort=QcMethodVersion.created_at)
    return {**envelope, "items": [_qc_method_dict(m) for (m,) in rows]}


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
    site_id: uuid.UUID | None = None,
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    # SG-213: same resolve_site_scope treatment as list_qc_methods above -- this is a list (every version
    # row for a method_code), not a single-record fetch, so it needs the site-scope filter, not a
    # record.site_id check.
    site_scope = await resolve_site_scope(session, actor.user_id, site_id, action="qc_method.view")
    versions = (
        await session.execute(
            select(QcMethodVersion)
            .where(QcMethodVersion.method_code == method_code, QcMethodVersion.site_id.in_(site_scope))
            .order_by(QcMethodVersion.version_no)
        )
    ).scalars().all()
    return [_qc_method_dict(v) for v in versions]


@router.get("/methods/{method_version_id}")
async def get_qc_method_version_detail(
    method_version_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    method = await session.get(QcMethodVersion, method_version_id)
    if method is None:
        raise NotFoundError("QC method version not found")
    await evaluate_policy(session, actor.user_id, action="qc_method.view", site_id=method.site_id)
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
        method = await session.get(QcMethodVersion, method_version_id)
        if method is None:
            raise NotFoundError("QC method version not found")
        await evaluate_policy(session, actor.user_id, action="qc_method.release", site_id=method.site_id)
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
    # SG-213 NOT mechanically fixable: qc_sample carries no site_id column at all (models.py) -- its only
    # site signal is the polymorphic source_type/source_id (batch/batch_step/material_lot resolve to a
    # site via another module's table; reserve/environmental/investigation don't resolve to any entity,
    # per QcSample's own docstring). Picking a resolution rule here is an authorization-semantics decision,
    # not a wrong-argument fix -- flagged for a human call rather than guessed.
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qc_sample.receive", site_id=None)
        return await receive_sample(session, cmd, actor.user_id)


@router.get("/samples/{sample_id}/record")
async def get_sample_record(
    sample_id: str,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
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
            "external_provider_id": str(order.external_provider_id) if order.external_provider_id else None,
            "external_report_hash": order.external_report_hash,
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
async def list_results_for_batch(
    batch_id: str,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    """Real picker data for any field that references a `qc_result` row by id -- DDCP's "Link a device
    functional test" `qc_record_reference` (ddcp/commands.py's own comment: "References the owning
    qc.qc_result row, never duplicates it") is the first caller, previously free-text UUID entry with no
    way to discover a real one. Same SG-081 read-side precedent as every other picker added this pass.

    `QcSample.source_id` is a polymorphic reference (see that model's own docstring) validated only for
    a handful of source_types -- 'batch' and 'batch_step' both resolve to this batch (a step-level
    in-process sample's source_id points at its `gxp_batch_step` row, not the batch directly), so both
    are matched rather than only the direct 'batch' source_type -- the OOS "Open from result" picker was
    otherwise empty for every batch whose only QC sampling was step-level. Newest first."""
    rows = (
        await session.execute(
            select(QcResult, QcTestDefinition.test_name)
            .join(QcTestOrder, QcTestOrder.id == QcResult.test_order_id)
            .join(QcSample, QcSample.id == QcTestOrder.sample_id)
            .join(QcTestDefinition, QcTestDefinition.id == QcTestOrder.test_definition_id)
            .outerjoin(
                BatchStep,
                and_(QcSample.source_type == "batch_step", QcSample.source_id == BatchStep.id),
            )
            .where(
                or_(
                    and_(QcSample.source_type == "batch", QcSample.source_id == batch_id),
                    and_(QcSample.source_type == "batch_step", BatchStep.batch_id == batch_id),
                )
            )
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
async def get_release_readiness(
    sample_id: str,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
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


# --- SG-066 Task 4 Part 3 (2026-09-23): read-only dashboard/export, no new regulated decision -- same
# shape as SG-074 Task 3 Part B's oos/oot dashboard/export. -------------------------------------------


@router.get("/dashboard")
async def get_qc_dashboard(session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor)) -> dict:
    by_state = dict(
        (await session.execute(select(QcTestOrder.state, func.count()).group_by(QcTestOrder.state))).all()
    )
    open_oos = (
        await session.execute(select(func.count()).select_from(OosRecord).where(OosRecord.state != "closed"))
    ).scalar_one()
    open_oot = (
        await session.execute(select(func.count()).select_from(OotRecord).where(OotRecord.state != "closed"))
    ).scalar_one()
    return {"test_orders_by_state": by_state, "open_oos": open_oos, "open_oot": open_oot}


@router.get("/export")
async def get_qc_export(session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor)) -> list[dict]:
    rows = (
        await session.execute(
            select(QcTestOrder, QcSample.sample_number)
            .join(QcSample, QcSample.id == QcTestOrder.sample_id)
            .order_by(QcTestOrder.created_at)
        )
    ).all()
    return [
        {
            "id": str(order.id), "sample_number": sample_number, "state": order.state, "blocking": order.blocking,
            "started_at": order.started_at.isoformat() if order.started_at else None,
            "completed_at": order.completed_at.isoformat() if order.completed_at else None,
        }
        for order, sample_number in rows
    ]


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
    # SG-213 NOT mechanically fixable: qc_test_order carries no site_id column (models.py); its only site
    # signal is two hops away (test_order -> sample -> polymorphic source), same unresolved-resolution-rule
    # gap as post_receive_sample above -- flagged for a human call rather than guessed.
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="qc_test_order.start", site_id=None)
        await _check_qc_analyst_qualification(session, actor.user_id)
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
    # SG-213 NOT mechanically fixable: same qc_test_order-has-no-site_id gap as post_start_test_order above.
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
    # SG-213 NOT mechanically fixable: same qc_test_order-has-no-site_id gap as post_start_test_order above
    # (qc_result itself also has no site_id -- models.py).
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


OOS_SORTABLE = {"oos_number": OosRecord.oos_number, "opened_at": OosRecord.opened_at, "state": OosRecord.state}


def _oos_summary_dict(r: OosRecord) -> dict:
    return {
        "id": sid(r.id), "oos_number": r.oos_number, "batch_id": sid(r.batch_id),
        "material_lot_id": sid(r.material_lot_id), "state": r.state, "severity": r.severity,
        "final_classification": r.final_classification, "opened_at": iso(r.opened_at), "closed_at": iso(r.closed_at),
    }


# List page for a new browsable /quality/oos DataTable (no such read existed before -- only dashboard/
# export/detail-by-id) -- same filtered()/paginate() envelope every other list endpoint in this codebase
# uses, and the same "no evaluate_policy call" precedent as the dashboard/export/detail reads right below.
@oos_router.get("/oos/v1")
async def list_oos_records(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    state: str | None = None,
) -> dict:
    stmt = filtered(OosRecord, params, search_column=OosRecord.oos_number, site_id=site_id, state=state)
    rows, envelope = await paginate(session, stmt, params, sortable=OOS_SORTABLE, default_sort=OosRecord.opened_at)
    return {**envelope, "items": [_oos_summary_dict(r) for (r,) in rows]}


# --- SG-074 Task 3 Part B: read-only dashboard/export, no new regulated decision (same shape as any other
# module's list endpoint; unauthenticated-permission-check precedent already set by get_oos_record below,
# which has no evaluate_policy call of its own either). Registered BEFORE the /oos/v1/{oos_id} path-param
# route -- Starlette matches in registration order, so "dashboard"/"export" would otherwise be swallowed
# by {oos_id} (same class of ordering bug app/main.py's batch_execution_router/batch_router comment
# documents). ------------------------------------------------------------------------------------------


@oos_router.get("/oos/v1/dashboard")
async def get_oos_dashboard(session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor)) -> dict:
    by_state = dict(
        (await session.execute(select(OosRecord.state, func.count()).group_by(OosRecord.state))).all()
    )
    by_severity = dict(
        (await session.execute(select(OosRecord.severity, func.count()).group_by(OosRecord.severity))).all()
    )
    return {"total": sum(by_state.values()), "by_state": by_state, "by_severity": by_severity}


@oos_router.get("/oos/v1/export")
async def get_oos_export(session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor)) -> list[dict]:
    records = (await session.execute(select(OosRecord).order_by(OosRecord.opened_at))).scalars().all()
    return [
        {
            "id": str(r.id), "oos_number": r.oos_number, "batch_id": str(r.batch_id) if r.batch_id else None,
            "material_lot_id": str(r.material_lot_id) if r.material_lot_id else None, "state": r.state,
            "severity": r.severity, "final_classification": r.final_classification,
            "opened_at": r.opened_at.isoformat() if r.opened_at else None,
            "closed_at": r.closed_at.isoformat() if r.closed_at else None,
        }
        for r in records
    ]


@oos_router.get("/oot/v1/dashboard")
async def get_oot_dashboard(session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor)) -> dict:
    by_state = dict(
        (await session.execute(select(OotRecord.state, func.count()).group_by(OotRecord.state))).all()
    )
    return {"total": sum(by_state.values()), "by_state": by_state}


@oos_router.get("/oot/v1/export")
async def get_oot_export(session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor)) -> list[dict]:
    records = (await session.execute(select(OotRecord).order_by(OotRecord.opened_at))).scalars().all()
    return [
        {
            "id": str(r.id), "source_result_id": str(r.source_result_id), "state": r.state,
            "investigation_owner_user_id": str(r.investigation_owner_user_id) if r.investigation_owner_user_id else None,
            "opened_at": r.opened_at.isoformat() if r.opened_at else None,
            "closed_at": r.closed_at.isoformat() if r.closed_at else None,
        }
        for r in records
    ]


OOT_SORTABLE = {"opened_at": OotRecord.opened_at, "state": OotRecord.state}


def _oot_summary_dict(r: OotRecord) -> dict:
    return {
        "id": sid(r.id), "source_result_id": sid(r.source_result_id), "state": r.state,
        "investigation_owner_user_id": sid(r.investigation_owner_user_id),
        "opened_at": iso(r.opened_at), "closed_at": iso(r.closed_at),
    }


# List page for a new browsable /quality/oot DataTable. OotRecord has no site_id column (Document 25 §7
# is prose-only for this entity, see the model's own docstring) so this can't use filtered()'s site scope
# the way OOS/CAPA do -- state filter and paging only, no free-text search column exists to offer either.
@oos_router.get("/oot/v1")
async def list_oot_records(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    state: str | None = None,
) -> dict:
    stmt = select(OotRecord)
    if state:
        stmt = stmt.where(OotRecord.state == state)
    rows, envelope = await paginate(session, stmt, params, sortable=OOT_SORTABLE, default_sort=OotRecord.opened_at)
    return {**envelope, "items": [_oot_summary_dict(r) for (r,) in rows]}


# No GET /oot/v1/{oot_id} existed before this (only evaluate/signature-challenges/close/reopen) -- the
# frontend detail page below needs one to read a single record back after navigating from the list.
@oos_router.get("/oot/v1/{oot_id}")
async def get_oot_record(
    oot_id: str,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    oot = await session.get(OotRecord, oot_id)
    if oot is None:
        raise NotFoundError("OOT record not found")
    return {
        "id": sid(oot.id), "source_result_id": sid(oot.source_result_id),
        "trend_rule_id": sid(oot.trend_rule_id), "trend_rule_version": oot.trend_rule_version,
        "baseline_ref": oot.baseline_ref, "trigger_details": oot.trigger_details,
        "state": oot.state, "investigation_notes": oot.investigation_notes,
        "impact_assessment": oot.impact_assessment,
        "investigation_owner_user_id": sid(oot.investigation_owner_user_id),
        "hold_status": oot.hold_status, "version": oot.version,
        "opened_at": iso(oot.opened_at), "closed_at": iso(oot.closed_at),
        "reopen_history": oot.reopen_history,
    }


@oos_router.get("/oos/v1/{oos_id}")
async def get_oos_record(
    oos_id: str,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
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
        "change_control_id": str(oos.change_control_id) if oos.change_control_id else None,
        "reopen_history": oos.reopen_history,
        "linked_capas": await get_oos_linked_capas(session, oos.id),
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


@oos_router.post("/oos/v1/{oos_id}/reopen", response_model=MutationReceipt)
async def post_reopen_oos(
    oos_id: str,
    cmd: ReopenOosCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.oos_record_id) != oos_id:
        raise ValidationFailedError("oos_id in path and body must match")
    async with session.begin():
        return await reopen_oos(session, cmd, actor.user_id)


@oos_router.post("/oos/v1/{oos_id}/change-control", response_model=MutationReceipt)
async def post_link_oos_change_control(
    oos_id: str,
    cmd: LinkOosChangeControlCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.oos_record_id) != oos_id:
        raise ValidationFailedError("oos_id in path and body must match")
    async with session.begin():
        return await link_oos_change_control(session, cmd, actor.user_id)


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


@oos_router.post("/oot/v1/{oot_id}/reopen", response_model=MutationReceipt)
async def post_reopen_oot(
    oot_id: str,
    cmd: ReopenOotCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.oot_record_id) != oot_id:
        raise ValidationFailedError("oot_id in path and body must match")
    async with session.begin():
        return await reopen_oot(session, cmd, actor.user_id)


