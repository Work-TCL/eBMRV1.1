import uuid
from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qms.quality_metrics_commands import (
    CalculateSnapshotCommand,
    CreateEffectivenessCheckCommand,
    CreateMetricDefinitionCommand,
    EvaluateEffectivenessCheckCommand,
    FreezeManagementReviewPackageCommand,
    ReleaseMetricDefinitionCommand,
    calculate_snapshot,
    create_effectiveness_check,
    create_metric_definition,
    evaluate_effectiveness_check,
    freeze_management_review_package,
    release_metric_definition,
)
from app.modules.qms.quality_metrics_models import QualityMetricDefinition, QualityMetricSnapshot
from app.modules.qms.signature_support import SignatureChallengeRequest, create_qms_signature_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

quality_metrics_router = APIRouter(prefix="/quality-metrics/v1", tags=["qms-quality-metrics"])
effectiveness_router = APIRouter(prefix="/effectiveness/v1", tags=["qms-quality-metrics"])

METRIC_DEFINITION_SIGNATURE_ACTIONS = ("release",)
METRIC_SNAPSHOT_SIGNATURE_ACTIONS = ("management_review",)


class ManagementReviewSignatureChallengeRequest(SignatureChallengeRequest):
    snapshot_ids: list[uuid.UUID]


@quality_metrics_router.post("/definitions", response_model=MutationReceipt)
async def post_create_metric_definition(
    cmd: CreateMetricDefinitionCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="quality_metric.definition.create", site_id=cmd.site_id)
        return await create_metric_definition(session, cmd, actor.user_id)


@quality_metrics_router.post("/definitions/{definition_id}/release", response_model=MutationReceipt)
async def post_release_metric_definition(
    definition_id: uuid.UUID, cmd: ReleaseMetricDefinitionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.definition_id != definition_id:
        raise ValidationFailedError("definition_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="quality_metric.definition.release", site_id=None)
        return await release_metric_definition(session, cmd, actor.user_id)


@quality_metrics_router.post("/definitions/{definition_id}/signature-challenges")
async def post_definition_signature_challenge(
    definition_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        definition = await session.get(QualityMetricDefinition, definition_id)
        if definition is None:
            raise NotFoundError("Quality metric definition not found")
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="quality_metric_definition", record=definition,
            action=body.action, allowed_actions=METRIC_DEFINITION_SIGNATURE_ACTIONS,
        )


@quality_metrics_router.post("/calculate", response_model=MutationReceipt)
async def post_calculate_snapshot(
    cmd: CalculateSnapshotCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="quality_metric.calculate", site_id=cmd.site_id)
        return await calculate_snapshot(session, cmd, actor.user_id)


@quality_metrics_router.get("/dashboard")
async def get_dashboard(
    site_id: uuid.UUID, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """MET-FR-016/021/022/024: a rebuildable, non-authoritative read (AG-11) -- the underlying
    quality_metric_definition/quality_metric_snapshot rows remain the authority for any decision.
    """
    await evaluate_policy(session, actor.user_id, action="quality_metric.dashboard.view", site_id=site_id)
    definitions = (
        await session.execute(select(QualityMetricDefinition).where(QualityMetricDefinition.site_id == site_id, QualityMetricDefinition.state == "RELEASED"))
    ).scalars().all()

    rows = []
    for definition in definitions:
        latest = (
            await session.execute(
                select(QualityMetricSnapshot)
                .where(QualityMetricSnapshot.metric_definition_id == definition.id)
                .order_by(QualityMetricSnapshot.created_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()
        rows.append({
            "metric_code": definition.metric_code, "version_no": definition.version_no,
            "latest_result": latest.result if latest else None,
            "source_cutoff": latest.source_cutoff.isoformat() if latest else None,
            "threshold_exceeded": latest.threshold_exceeded if latest else False,
            "freshness_seconds": (datetime.now(timezone.utc) - latest.source_cutoff.replace(tzinfo=timezone.utc)).total_seconds() if latest else None,
        })
    return {"site_id": str(site_id), "metrics": rows}


@quality_metrics_router.post("/management-review-packages", response_model=MutationReceipt)
async def post_freeze_management_review_package(
    cmd: FreezeManagementReviewPackageCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="quality_metric.management_review", site_id=cmd.site_id)
        return await freeze_management_review_package(session, cmd, actor.user_id)


@quality_metrics_router.post("/management-review-packages/signature-challenges")
async def post_management_review_signature_challenge(
    body: ManagementReviewSignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """No path id: freeze_management_review_package() signs the whole snapshot_ids package as one
    decision, resolved against the first snapshot (see quality_metrics_commands.py's own comment at its
    call site) -- mirrored here rather than requiring a representative id the client would have to
    invent."""
    if not body.snapshot_ids:
        raise ValidationFailedError("snapshot_ids must name at least one snapshot")
    async with session.begin():
        snapshot = await session.get(QualityMetricSnapshot, body.snapshot_ids[0])
        if snapshot is None:
            raise NotFoundError("Quality metric snapshot not found", snapshot_id=str(body.snapshot_ids[0]))
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="quality_metric_snapshot", record=snapshot,
            action=body.action, allowed_actions=METRIC_SNAPSHOT_SIGNATURE_ACTIONS,
        )


@effectiveness_router.post("/checks", response_model=MutationReceipt)
async def post_create_effectiveness_check(
    cmd: CreateEffectivenessCheckCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="effectiveness_check.create", site_id=cmd.site_id)
        return await create_effectiveness_check(session, cmd, actor.user_id)


@effectiveness_router.post("/checks/{check_id}/evaluate", response_model=MutationReceipt)
async def post_evaluate_effectiveness_check(
    check_id: uuid.UUID, cmd: EvaluateEffectivenessCheckCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.check_id != check_id:
        raise ValidationFailedError("check_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="effectiveness_check.evaluate", site_id=None)
        return await evaluate_effectiveness_check(session, cmd, actor.user_id)
