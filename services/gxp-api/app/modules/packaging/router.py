import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.packaging.models import LabelIssue, LabelReconciliation, PackageNode, PackagingRun
from app.modules.policy.service import evaluate_policy
from app.modules.qms.read_support import iso, sid
from app.modules.packaging.commands import (
    CompletePackagingRunCommand,
    CreatePackagingRunCommand,
    IssueLabelCommand,
    LineClearanceCommand,
    ReconcileLabelsCommand,
    ReconcilePackagingCommand,
    complete_packaging_run,
    create_packaging_run,
    issue_label,
    reconcile_labels,
    reconcile_packaging,
    complete_line_clearance,
)
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
        await evaluate_policy(session, actor.user_id, action="packaging.execute", site_id=None)
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
        await evaluate_policy(session, actor.user_id, action="packaging.execute", site_id=None)
        return await complete_line_clearance(session, cmd, actor.user_id)


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
        await evaluate_policy(session, actor.user_id, action="packaging.execute", site_id=None)
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
        await evaluate_policy(session, actor.user_id, action="packaging.execute", site_id=None)
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
        await evaluate_policy(session, actor.user_id, action="packaging.execute", site_id=None)
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
        await evaluate_policy(session, actor.user_id, action="packaging.execute", site_id=None)
        return await complete_packaging_run(session, cmd, actor.user_id)


# --- Read side (Document 16) -------------------------------------------------------------------

RUN_SORTABLE = {
    "state": PackagingRun.state,
    "reconciliation_state": PackagingRun.reconciliation_state,
    "started_at": PackagingRun.started_at,
    "created_at": PackagingRun.created_at,
}


def _run_dict(run: PackagingRun) -> dict:
    return {
        "id": str(run.id),
        "site_id": str(run.site_id),
        "batch_id": str(run.batch_id),
        "product_version_id": str(run.product_version_id),
        "line_ref": run.line_ref,
        "state": run.state,
        "version": run.version,
        "line_clearance_completed": run.line_clearance_completed,
        "reconciliation_state": run.reconciliation_state,
        "started_at": iso(run.started_at),
        "ended_at": iso(run.ended_at),
        "created_at": iso(run.created_at),
    }


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
    return {**envelope, "items": [_run_dict(r) for (r,) in rows]}


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
    return {
        **_run_dict(run),
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
