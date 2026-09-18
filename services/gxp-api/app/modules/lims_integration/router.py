from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.lims_integration.commands import (
    CancelLimsSampleCommand,
    IngestLimsResultCommand,
    IngestLimsStatusCommand,
    ReconcileLimsInstanceCommand,
    RequestLimsSampleCommand,
    _get_instance,
    _record_hash,
    cancel_lims_sample,
    ingest_lims_result,
    ingest_lims_status,
    reconcile_lims_instance,
    request_lims_sample,
)
from app.modules.lims_integration.models import LimsInstance, LimsMapping, LimsMessage
from app.modules.qc.models import QcSample
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/integrations/lims", tags=["lims_integration"])

INSTANCE_SORTABLE = {"instance_code": LimsInstance.instance_code, "created_at": LimsInstance.created_at}


def _instance_summary_dict(instance: LimsInstance) -> dict:
    return {
        "id": str(instance.id), "instance_code": instance.instance_code, "provider_type": instance.provider_type,
        "status": instance.status,
    }


# Read-only list — LIMS instances are provisioned as configuration data with no create endpoint (see the
# `LimsInstance` docstring), so this lets the frontend offer a "pick an instance" selector instead of
# requiring the operator to already have the instance id in hand.
@router.get("")
async def list_instances(session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params)) -> dict:
    stmt = select(LimsInstance)
    if params.q:
        stmt = stmt.where(LimsInstance.instance_code.ilike(f"%{params.q}%"))
    rows, envelope = await paginate(session, stmt, params, sortable=INSTANCE_SORTABLE, default_sort=LimsInstance.created_at)
    return {**envelope, "items": [_instance_summary_dict(i) for (i,) in rows]}


@router.post("/{instance_id}/samples", response_model=MutationReceipt)
async def post_request_sample(
    instance_id: str,
    cmd: RequestLimsSampleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.instance_id) != instance_id:
        raise ValidationFailedError("instance_id in path and body must match")
    async with session.begin():
        return await request_lims_sample(session, cmd, actor.user_id)


class SampleSignatureChallengeRequest(BaseModel):
    action: str  # "cancel"


@router.post("/{instance_id}/samples/{sample_id}/signature-challenges")
async def post_sample_signature_challenge(
    instance_id: str,
    sample_id: str,
    body: SampleSignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        sample = await session.get(QcSample, sample_id)
        if sample is None:
            raise NotFoundError("Sample not found")
        if body.action != "cancel":
            raise ValidationFailedError("Unknown action", action=body.action)
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="lims_sample", record_id=sample.id,
            record_version=sample.version, record_hash=_record_hash(sample, "state"), meaning="Approved",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/{instance_id}/samples/{sample_id}/cancel", response_model=MutationReceipt)
async def post_cancel_sample(
    instance_id: str,
    sample_id: str,
    cmd: CancelLimsSampleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.instance_id) != instance_id or str(cmd.sample_id) != sample_id:
        raise ValidationFailedError("instance_id/sample_id in path and body must match")
    async with session.begin():
        return await cancel_lims_sample(session, cmd, actor.user_id)


@router.post("/{instance_id}/reconcile", response_model=MutationReceipt)
async def post_reconcile(
    instance_id: str,
    cmd: ReconcileLimsInstanceCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.instance_id) != instance_id:
        raise ValidationFailedError("instance_id in path and body must match")
    async with session.begin():
        return await reconcile_lims_instance(session, cmd, actor.user_id)


@router.get("/{instance_id}/health")
async def get_health(instance_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    instance = await _get_instance(session, instance_id)
    pending = (
        await session.execute(
            select(LimsMessage.id).where(LimsMessage.instance_id == instance.id, LimsMessage.status == "pending")
        )
    ).scalars().all()
    dead_lettered = (
        await session.execute(
            select(LimsMessage.id).where(LimsMessage.instance_id == instance.id, LimsMessage.status == "dead_letter")
        )
    ).scalars().all()
    last_message = (
        await session.execute(
            select(LimsMessage).where(LimsMessage.instance_id == instance.id).order_by(LimsMessage.created_at.desc()).limit(1)
        )
    ).scalars().first()
    return {
        "instance_id": str(instance.id),
        "status": instance.status,
        "ownership_mode": instance.ownership_mode,
        "pending_message_count": len(pending),
        "dead_letter_count": len(dead_lettered),
        "last_message_at": last_message.created_at.isoformat() if last_message else None,
    }


def _mapping_dict(m: LimsMapping) -> dict:
    return {
        "id": str(m.id), "instance_id": str(m.instance_id),
        "internal_object_type": m.internal_object_type,
        "internal_object_id": str(m.internal_object_id) if m.internal_object_id else None,
        "internal_object_version": m.internal_object_version,
        "external_entity_type": m.external_entity_type, "external_entity_id": m.external_entity_id,
        "mapping_version": m.mapping_version,
        "effective_from": m.effective_from.isoformat() if m.effective_from else None,
        "effective_to": m.effective_to.isoformat() if m.effective_to else None,
        "status": m.status, "version": m.version, "created_at": m.created_at.isoformat(),
    }


def _message_dict(msg: LimsMessage) -> dict:
    return {
        "id": str(msg.id), "instance_id": str(msg.instance_id), "direction": msg.direction,
        "external_event_id": msg.external_event_id,
        "internal_correlation_id": str(msg.internal_correlation_id) if msg.internal_correlation_id else None,
        "payload_hash": msg.payload_hash, "schema_version": msg.schema_version,
        "adapter_version": msg.adapter_version, "status": msg.status, "error_code": msg.error_code,
        "retry_count": msg.retry_count,
        "sent_at": msg.sent_at.isoformat() if msg.sent_at else None,
        "received_at": msg.received_at.isoformat() if msg.received_at else None,
        "created_at": msg.created_at.isoformat(),
    }


# LIMS-FR-011's ordering ledger — a mapping's own fields (external id, mapping_version, effective window)
# were saved and even read back internally by reconcile_lims_instance(), but no caller could retrieve them.
@router.get("/{instance_id}/mappings")
async def list_mappings(
    instance_id: str, session: AsyncSession = Depends(get_session),
    internal_object_type: str | None = None, external_entity_type: str | None = None,
) -> list[dict]:
    instance = await _get_instance(session, instance_id)
    stmt = select(LimsMapping).where(LimsMapping.instance_id == instance.id)
    if internal_object_type:
        stmt = stmt.where(LimsMapping.internal_object_type == internal_object_type)
    if external_entity_type:
        stmt = stmt.where(LimsMapping.external_entity_type == external_entity_type)
    mappings = (await session.execute(stmt.order_by(LimsMapping.created_at.desc()))).scalars().all()
    return [_mapping_dict(m) for m in mappings]


@router.get("/{instance_id}/mappings/{mapping_id}")
async def get_mapping(instance_id: str, mapping_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    await _get_instance(session, instance_id)
    mapping = await session.get(LimsMapping, mapping_id)
    if mapping is None or str(mapping.instance_id) != instance_id:
        raise NotFoundError("LIMS mapping not found")
    return _mapping_dict(mapping)


# LIMS-FR-024's dead-letter record — get_health() above only ever counted these; an operator troubleshooting
# a stuck/failed integration event had no way to see why (error_code) or which event (external_event_id)
# failed. Optional `status` filter mirrors get_health()'s own pending/dead_letter breakdown.
@router.get("/{instance_id}/messages")
async def list_messages(
    instance_id: str, session: AsyncSession = Depends(get_session), status: str | None = None,
) -> list[dict]:
    instance = await _get_instance(session, instance_id)
    stmt = select(LimsMessage).where(LimsMessage.instance_id == instance.id)
    if status:
        stmt = stmt.where(LimsMessage.status == status)
    messages = (await session.execute(stmt.order_by(LimsMessage.created_at.desc()))).scalars().all()
    return [_message_dict(m) for m in messages]


@router.get("/{instance_id}/messages/{message_id}")
async def get_message(instance_id: str, message_id: str, session: AsyncSession = Depends(get_session)) -> dict:
    await _get_instance(session, instance_id)
    message = await session.get(LimsMessage, message_id)
    if message is None or str(message.instance_id) != instance_id:
        raise NotFoundError("LIMS message not found")
    return _message_dict(message)


@router.post("/{instance_id}/events/results", response_model=MutationReceipt)
async def post_ingest_result(
    instance_id: str,
    cmd: IngestLimsResultCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.instance_id) != instance_id:
        raise ValidationFailedError("instance_id in path and body must match")
    async with session.begin():
        return await ingest_lims_result(session, cmd, actor.user_id)


@router.post("/{instance_id}/events/status", response_model=MutationReceipt)
async def post_ingest_status(
    instance_id: str,
    cmd: IngestLimsStatusCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if str(cmd.instance_id) != instance_id:
        raise ValidationFailedError("instance_id in path and body must match")
    async with session.begin():
        return await ingest_lims_status(session, cmd, actor.user_id)
