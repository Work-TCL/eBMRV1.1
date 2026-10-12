import uuid

from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.batch_execution.models import Batch
from app.modules.device.models import DeviceUnit
from app.modules.iam.models import User
from app.modules.packaging.models import PackagingRun
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import create_challenge
from app.modules.yield_reconciliation import commands as yr_commands
from app.modules.yield_reconciliation.models import ManufacturingCalculation, ReconciliationRecord
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(tags=["yield-reconciliation"])


async def _resolve_summary_refs(session: AsyncSession, summary: dict) -> dict:
    """Augments `get_batch_summary()`'s calculation/reconciliation rows with human-readable labels for
    their user and device-unit foreign keys -- same one-query-per-referenced-table shape as cleaning's
    own `_resolve_execution_refs`. `commands.py` stays the pure data layer; resolution lives in the
    router like every other module in this codebase."""
    rows = summary["calculations"] + summary["reconciliations"]
    if not rows:
        return summary

    user_ids = {uuid.UUID(r["evaluated_by_user_id"]) for r in rows if r.get("evaluated_by_user_id")}
    user_ids |= {uuid.UUID(r["verified_by_user_id"]) for r in rows if r.get("verified_by_user_id")}
    device_unit_ids = {uuid.UUID(r["device_unit_id"]) for r in rows if r.get("device_unit_id")}

    user_by_id: dict[uuid.UUID, tuple[str, str]] = {}
    if user_ids:
        user_by_id = {
            row.id: (row.full_name, row.username)
            for row in (await session.execute(select(User.id, User.full_name, User.username).where(User.id.in_(user_ids)))).all()
        }
    serial_by_id: dict[uuid.UUID, str | None] = {}
    if device_unit_ids:
        serial_by_id = dict(
            (await session.execute(select(DeviceUnit.id, DeviceUnit.serial_number).where(DeviceUnit.id.in_(device_unit_ids)))).all()
        )

    for r in rows:
        evaluated_by = user_by_id.get(uuid.UUID(r["evaluated_by_user_id"])) if r.get("evaluated_by_user_id") else None
        verified_by = user_by_id.get(uuid.UUID(r["verified_by_user_id"])) if r.get("verified_by_user_id") else None
        device_unit_id = uuid.UUID(r["device_unit_id"]) if r.get("device_unit_id") else None
        r["evaluated_by_username"] = evaluated_by[1] if evaluated_by else None
        r["verified_by_username"] = verified_by[1] if verified_by else None
        r["device_unit_serial"] = serial_by_id.get(device_unit_id) if device_unit_id else None
    return summary


@router.post("/manufacturing-calculations/v1/yield/evaluate", response_model=MutationReceipt)
async def post_evaluate_yield(
    cmd: yr_commands.EvaluateYieldCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        batch = await session.get(Batch, cmd.batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        await evaluate_policy(session, actor.user_id, action="yield_calculation.evaluate", site_id=batch.site_id)
        return await yr_commands.evaluate_yield(session, cmd, actor.user_id)


@router.post("/manufacturing-calculations/v1/potency/evaluate", response_model=MutationReceipt)
async def post_evaluate_potency(
    cmd: yr_commands.EvaluatePotencyCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        batch = await session.get(Batch, cmd.batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        await evaluate_policy(session, actor.user_id, action="yield_calculation.evaluate", site_id=batch.site_id)
        return await yr_commands.evaluate_potency(session, cmd, actor.user_id)


@router.post("/reconciliation/v1/material/evaluate", response_model=MutationReceipt)
async def post_evaluate_material(
    cmd: yr_commands.EvaluateReconciliationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        batch = await session.get(Batch, cmd.batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        await evaluate_policy(session, actor.user_id, action="reconciliation.evaluate", site_id=batch.site_id)
        return await yr_commands.evaluate_material_reconciliation(session, cmd, actor.user_id)


@router.post("/reconciliation/v1/packaging/evaluate", response_model=MutationReceipt)
async def post_evaluate_packaging(
    cmd: yr_commands.EvaluateReconciliationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        batch = await session.get(Batch, cmd.batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        await evaluate_policy(session, actor.user_id, action="reconciliation.evaluate", site_id=batch.site_id)
        return await yr_commands.evaluate_packaging_reconciliation(session, cmd, actor.user_id)


@router.post("/reconciliation/v1/labels/evaluate", response_model=MutationReceipt)
async def post_evaluate_labels(
    cmd: yr_commands.EvaluateLabelReconciliationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        run = await session.get(PackagingRun, cmd.packaging_run_id)
        if run is None:
            raise NotFoundError("Packaging run not found")
        await evaluate_policy(session, actor.user_id, action="reconciliation.evaluate", site_id=run.site_id)
        return await yr_commands.evaluate_label_reconciliation(session, cmd, actor.user_id)


@router.post("/reconciliation/v1/components/evaluate", response_model=MutationReceipt)
async def post_evaluate_components(
    cmd: yr_commands.EvaluateComponentReconciliationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        batch = await session.get(Batch, cmd.batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        await evaluate_policy(session, actor.user_id, action="reconciliation.evaluate", site_id=batch.site_id)
        return await yr_commands.evaluate_component_reconciliation(session, cmd, actor.user_id)


class VerifySignatureChallengeRequest(BaseModel):
    record_kind: str  # "CALCULATION" | "RECONCILIATION"


@router.post("/reconciliation/v1/{record_id}/signature-challenges")
async def post_verify_signature_challenge(
    record_id: uuid.UUID, body: VerifySignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        if body.record_kind == "CALCULATION":
            record = await session.get(ManufacturingCalculation, record_id)
            record_hash = yr_commands.calculation_record_hash(record) if record else None
            record_type = "manufacturing_calculation"
        elif body.record_kind == "RECONCILIATION":
            record = await session.get(ReconciliationRecord, record_id)
            record_hash = yr_commands.reconciliation_record_hash(record) if record else None
            record_type = "reconciliation_record"
        else:
            raise ValidationFailedError("record_kind must be CALCULATION or RECONCILIATION")
        if record is None:
            raise NotFoundError("Record not found")
        # 2026-10-08: this endpoint had no policy check at all -- any authenticated user of any role
        # could mint a "Verified" challenge for any record, unlike every sibling module's own
        # signature-challenges route (qa_review/release both gate the challenge itself, not just the
        # action it enables). The actual POST .../verify below was already correctly gated on
        # reconciliation.verify, so this couldn't complete a verify -- but it leaked record_hash/version
        # to any role and let the challenge table fill with never-redeemable rows. Found alongside the
        # get_batch_summary auth gap while live-testing doc 22's Yield & Reconciliation walkthrough.
        await evaluate_policy(session, actor.user_id, action="reconciliation.verify", site_id=record.site_id)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type=record_type, record_id=record.id,
            record_version=record.version, record_hash=record_hash, meaning="Verified",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/reconciliation/v1/{record_id}/verify", response_model=MutationReceipt)
async def post_verify_record(
    record_id: uuid.UUID, cmd: yr_commands.VerifyRecordCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.record_id != record_id:
        raise ValidationFailedError("record_id in path and body must match")
    async with session.begin():
        if cmd.record_kind == "CALCULATION":
            record = await session.get(ManufacturingCalculation, record_id)
        elif cmd.record_kind == "RECONCILIATION":
            record = await session.get(ReconciliationRecord, record_id)
        else:
            raise ValidationFailedError("record_kind must be CALCULATION or RECONCILIATION")
        if record is None:
            raise NotFoundError("Record not found")
        await evaluate_policy(session, actor.user_id, action="reconciliation.verify", site_id=record.site_id)
        return await yr_commands.verify_record(session, cmd, actor.user_id)


@router.get("/reconciliation/v1/batches/{batch_id}/summary")
async def get_batch_summary(
    batch_id: uuid.UUID, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """2026-10-08: this endpoint had no `actor` dependency and no policy check at all (unlike every
    other read endpoint in this module, e.g. the evaluate/verify routes above) -- found while
    live-testing doc 22's Yield & Reconciliation walkthrough. `reconciliation.view` (new) is granted to
    exactly the role set that already holds qa_review.view/release.view."""
    async with session.begin():
        batch = await session.get(Batch, batch_id)
        if batch is None:
            raise NotFoundError("Batch not found")
        await evaluate_policy(session, actor.user_id, action="reconciliation.view", site_id=batch.site_id)
        summary = await yr_commands.get_batch_summary(session, batch_id)
        return await _resolve_summary_refs(session, summary)
