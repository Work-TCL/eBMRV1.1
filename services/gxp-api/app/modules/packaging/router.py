import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.packaging.commands import (
    CompletePackagingRunCommand,
    CreateLabelVersionCommand,
    CreatePackagingRunCommand,
    CreatePrintJobCommand,
    IssueLabelCommand,
    LineClearanceCommand,
    ReconcileLabelsCommand,
    ReconcilePackagingCommand,
    complete_line_clearance,
    complete_packaging_run,
    create_label_version,
    create_packaging_run,
    create_print_job,
    issue_label,
    reconcile_labels,
    reconcile_packaging,
)
from app.modules.batch_execution.models import Batch
from app.modules.packaging import service as packaging_service
from app.modules.packaging.models import LabelIssue, LabelMaster, LabelReconciliation, PackageNode, PackagingRun, PrintJob
from app.modules.policy.service import evaluate_policy
from app.modules.product_master.models import ProductVersion
from app.modules.qms.read_support import iso, sid
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/packaging/v1", tags=["packaging"])


@router.post("/runs", response_model=MutationReceipt)
async def post_create_run(
    cmd: CreatePackagingRunCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        batch = await packaging_service.get_batch(session, cmd.batch_id)
        await evaluate_policy(session, actor.user_id, action="packaging.execute", site_id=batch.site_id)
        return await create_packaging_run(session, cmd, actor.user_id)


@router.post("/runs/{run_id}/line-clearance", response_model=MutationReceipt)
async def post_line_clearance(
    run_id: uuid.UUID,
    cmd: LineClearanceCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.run_id != run_id:
        raise ValidationFailedError("run_id in path and body must match")
    async with session.begin():
        run = await session.get(PackagingRun, run_id)
        if run is None:
            raise NotFoundError("Packaging run not found")
        await evaluate_policy(session, actor.user_id, action="packaging.execute", site_id=run.site_id)
        return await complete_line_clearance(session, cmd, actor.user_id)


@router.post("/label-versions", response_model=MutationReceipt)
async def post_create_label_version(
    cmd: CreateLabelVersionCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="packaging.label_version.create", site_id=cmd.site_id)
        return await create_label_version(session, cmd, actor.user_id)


@router.get("/label-versions")
async def list_label_versions(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    site_id: uuid.UUID | None = None,
) -> list[dict]:
    await evaluate_policy(session, actor.user_id, action="packaging.view", site_id=site_id)
    stmt = select(LabelMaster)
    if site_id is not None:
        stmt = stmt.where(LabelMaster.site_id == site_id)
    rows = (await session.execute(stmt.order_by(LabelMaster.created_at.desc()))).scalars().all()
    return [
        {
            "id": str(r.id), "site_id": str(r.site_id), "label_code": r.label_code, "version_label": r.version_label,
            "product_version_id": sid(r.product_version_id), "content_hash": r.content_hash, "state": r.state,
            "created_at": iso(r.created_at),
        }
        for r in rows
    ]


@router.post("/print-jobs", response_model=MutationReceipt)
async def post_create_print_job(
    cmd: CreatePrintJobCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        run = await session.get(PackagingRun, cmd.run_id)
        if run is None:
            raise NotFoundError("Packaging run not found")
        await evaluate_policy(session, actor.user_id, action="packaging.execute", site_id=run.site_id)
        return await create_print_job(session, cmd, actor.user_id)


@router.get("/print-jobs")
async def list_print_jobs(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    run_id: uuid.UUID | None = None,
) -> list[dict]:
    stmt = select(PrintJob)
    if run_id is not None:
        run = await session.get(PackagingRun, run_id)
        if run is None:
            raise NotFoundError("Packaging run not found")
        await evaluate_policy(session, actor.user_id, action="packaging.view", site_id=run.site_id)
        stmt = stmt.where(PrintJob.packaging_run_id == run_id)
    else:
        await evaluate_policy(session, actor.user_id, action="packaging.view", site_id=None)
    rows = (await session.execute(stmt.order_by(PrintJob.created_at.desc()))).scalars().all()
    return [
        {
            "id": str(p.id), "site_id": str(p.site_id), "packaging_run_id": str(p.packaging_run_id),
            "label_version_id": str(p.label_version_id), "quantity": p.quantity, "variable_data": p.variable_data,
            "printer_ref": p.printer_ref, "requested_by": str(p.requested_by), "output_hash": p.output_hash,
            "state": p.state, "created_at": iso(p.created_at),
        }
        for p in rows
    ]


@router.post("/runs/{run_id}/labels/issue", response_model=MutationReceipt)
async def post_issue_label(
    run_id: uuid.UUID,
    cmd: IssueLabelCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.run_id != run_id:
        raise ValidationFailedError("run_id in path and body must match")
    async with session.begin():
        run = await session.get(PackagingRun, run_id)
        if run is None:
            raise NotFoundError("Packaging run not found")
        await evaluate_policy(session, actor.user_id, action="packaging.execute", site_id=run.site_id)
        return await issue_label(session, cmd, actor.user_id)


@router.post("/runs/{run_id}/reconcile-labels", response_model=MutationReceipt)
async def post_reconcile_labels(
    run_id: uuid.UUID,
    cmd: ReconcileLabelsCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.run_id != run_id:
        raise ValidationFailedError("run_id in path and body must match")
    async with session.begin():
        run = await session.get(PackagingRun, run_id)
        if run is None:
            raise NotFoundError("Packaging run not found")
        await evaluate_policy(session, actor.user_id, action="packaging.execute", site_id=run.site_id)
        return await reconcile_labels(session, cmd, actor.user_id)


@router.post("/runs/{run_id}/reconcile-packaging", response_model=MutationReceipt)
async def post_reconcile_packaging(
    run_id: uuid.UUID,
    cmd: ReconcilePackagingCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.run_id != run_id:
        raise ValidationFailedError("run_id in path and body must match")
    async with session.begin():
        run = await session.get(PackagingRun, run_id)
        if run is None:
            raise NotFoundError("Packaging run not found")
        await evaluate_policy(session, actor.user_id, action="packaging.execute", site_id=run.site_id)
        return await reconcile_packaging(session, cmd, actor.user_id)


@router.post("/runs/{run_id}/complete", response_model=MutationReceipt)
async def post_complete_run(
    run_id: uuid.UUID,
    cmd: CompletePackagingRunCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.run_id != run_id:
        raise ValidationFailedError("run_id in path and body must match")
    async with session.begin():
        run = await session.get(PackagingRun, run_id)
        if run is None:
            raise NotFoundError("Packaging run not found")
        await evaluate_policy(session, actor.user_id, action="packaging.execute", site_id=run.site_id)
        return await complete_packaging_run(session, cmd, actor.user_id)


# --- Read side (Document 16) -------------------------------------------------------------------

RUN_SORTABLE = {
    "state": PackagingRun.state,
    "reconciliation_state": PackagingRun.reconciliation_state,
    "started_at": PackagingRun.started_at,
    "created_at": PackagingRun.created_at,
}


def _run_dict(run: PackagingRun, refs: dict | None = None) -> dict:
    refs = refs or {}
    return {
        "id": str(run.id),
        "site_id": str(run.site_id),
        "batch_id": str(run.batch_id),
        "batch_number": refs.get("batch_number"),
        "product_version_id": str(run.product_version_id),
        "product_code": refs.get("product_code"),
        "product_name": refs.get("product_name"),
        "line_ref": run.line_ref,
        "state": run.state,
        "version": run.version,
        "line_clearance_completed": run.line_clearance_completed,
        "reconciliation_state": run.reconciliation_state,
        "started_at": iso(run.started_at),
        "ended_at": iso(run.ended_at),
        "created_at": iso(run.created_at),
    }


async def _resolve_run_refs(session: AsyncSession, runs: list[PackagingRun]) -> dict[uuid.UUID, dict]:
    """Batch-resolves the batch/product foreign keys `_run_dict` labels for -- same one-query-per-
    referenced-table shape as sterilization's `_resolve_cycle_refs`."""
    if not runs:
        return {}

    batch_ids = {r.batch_id for r in runs}
    batch_by_id = {
        row.id: (row.batch_number, row.product_version_id)
        for row in (await session.execute(select(Batch.id, Batch.batch_number, Batch.product_version_id).where(Batch.id.in_(batch_ids)))).all()
    }
    product_ids = {pv_id for (_, pv_id) in batch_by_id.values() if pv_id}
    product_by_id = {
        row.id: (row.product_code, row.name)
        for row in (
            await session.execute(select(ProductVersion.id, ProductVersion.product_code, ProductVersion.name).where(ProductVersion.id.in_(product_ids)))
        ).all()
    } if product_ids else {}

    resolved: dict[uuid.UUID, dict] = {}
    for r in runs:
        batch_number, product_version_id = batch_by_id.get(r.batch_id, (None, None))
        product_code, product_name = product_by_id.get(product_version_id, (None, None)) if product_version_id else (None, None)
        resolved[r.id] = {"batch_number": batch_number, "product_code": product_code, "product_name": product_name}
    return resolved


@router.get("/runs")
async def list_packaging_runs(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    batch_id: uuid.UUID | None = None,
    state: str | None = None,
) -> dict:
    await evaluate_policy(session, actor.user_id, action="packaging.view", site_id=site_id)
    stmt = select(PackagingRun)
    if site_id is not None:
        stmt = stmt.where(PackagingRun.site_id == site_id)
    if batch_id is not None:
        stmt = stmt.where(PackagingRun.batch_id == batch_id)
    if state:
        stmt = stmt.where(PackagingRun.state == state)
    if params.q:
        stmt = stmt.where(PackagingRun.line_ref.ilike(f"%{params.q}%"))
    rows, envelope = await paginate(
        session, stmt, params, sortable=RUN_SORTABLE, default_sort=PackagingRun.created_at
    )
    runs = [r for (r,) in rows]
    refs = await _resolve_run_refs(session, runs)
    return {**envelope, "items": [_run_dict(r, refs.get(r.id)) for r in runs]}


@router.get("/runs/{run_id}")
async def get_packaging_run(
    run_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    run = await session.get(PackagingRun, run_id)
    if run is None:
        raise NotFoundError("Packaging run not found")
    await evaluate_policy(session, actor.user_id, action="packaging.view", site_id=run.site_id)
    issues = (
        await session.execute(select(LabelIssue).where(LabelIssue.packaging_run_id == run_id))
    ).scalars().all()
    reconciliations = (
        await session.execute(
            select(LabelReconciliation).where(LabelReconciliation.packaging_run_id == run_id)
        )
    ).scalars().all()
    nodes = (
        await session.execute(select(PackageNode).where(PackageNode.batch_id == run.batch_id))
    ).scalars().all()
    refs = await _resolve_run_refs(session, [run])
    return {
        **_run_dict(run, refs.get(run.id)),
        "label_issues": [
            {
                "id": str(i.id),
                "label_version_id": sid(i.label_version_id),
                "quantity_issued": i.quantity_issued,
                "serial_range": i.serial_range,
                "print_job_id": sid(i.print_job_id),
                "issued_by": str(i.issued_by),
                "issued_at": iso(i.issued_at),
                "state": i.state,
            }
            for i in issues
        ],
        "label_reconciliations": [
            {
                "id": str(r.id),
                "issued": r.issued,
                "applied": r.applied,
                "returned": r.returned,
                "destroyed": r.destroyed,
                "rejected": r.rejected,
                "samples": r.samples,
                "calculated_variance": r.calculated_variance,
                "tolerance_rule": r.tolerance_rule,
                "result": r.result,
                "investigation_link": r.investigation_link,
                "created_at": iso(r.created_at),
            }
            for r in reconciliations
        ],
        "package_nodes": [
            {
                "id": str(n.id),
                "package_level": n.package_level,
                "business_ref": n.business_ref,
                "parent_package_id": sid(n.parent_package_id),
                "state": n.state,
            }
            for n in nodes
        ],
    }
