"""Document 47 (SPEC-EDGE-005) — server-side "Integration Gateway" routes. Human-authenticated routes
(`release`, `open`/`close` batch context, `submit` machine command, `replay`) go through `get_current_actor`
+ `evaluate_policy`, exactly like every other module. The 3 machine-driven routes (`ingest`, `cycle-
manifest`, `finalize`) go through `get_service_identity` (SG-120's mechanism, reused — same shape as
`app.modules.edge.router`'s 3 machine-driven routes) instead; the ownership check each command performs
(`service_identity.subject_ref` must equal the owning `MachineSource.gateway_id`) is this module's
authorization decision for those three.
"""

import uuid

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, AuthenticatedServiceIdentity, get_current_actor, get_service_identity
from app.modules.machine_integration.commands import (
    BuildCycleEvidenceManifestCommand,
    CloseBatchContextCommand,
    FinalizeMachineCommandCommand,
    IngestMachineEvidenceCommand,
    OpenBatchContextCommand,
    ReleaseSignalMappingCommand,
    ReplayHistoricalEvidenceCommand,
    SubmitApprovedMachineCommandCommand,
    build_cycle_evidence_manifest,
    close_batch_context,
    finalize_machine_command,
    get_machine_evidence_export,
    ingest_machine_evidence,
    mapping_record_hash,
    open_batch_context,
    release_signal_mapping,
    replay_historical_evidence,
    submit_approved_machine_command,
)
from app.modules.machine_integration.models import (
    BatchContext,
    MachineAlarmEvent,
    MachineCommandRequest,
    MachineEvidenceCandidate,
    MachineSource,
    SignalMapping,
)
from app.modules.policy.service import evaluate_policy
from app.modules.signature.service import create_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/machine-integration/v1", tags=["machine-integration"])


class SignalMappingChallengeRequest(BaseModel):
    mapping_id: uuid.UUID


@router.post("/signal-mappings/signature-challenges")
async def post_mapping_signature_challenge(
    body: SignalMappingChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        mapping = await session.get(SignalMapping, body.mapping_id)
        if mapping is None:
            raise NotFoundError("Signal mapping not found")
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="signal_mapping", record_id=mapping.id,
            record_version=mapping.row_version, record_hash=mapping_record_hash(mapping), meaning="Released",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/signal-mappings/{mapping_id}/release", response_model=MutationReceipt)
async def post_release_signal_mapping(
    mapping_id: uuid.UUID,
    cmd: ReleaseSignalMappingCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.mapping_id != mapping_id:
        raise ValidationFailedError("mapping_id in path and body must match")
    async with session.begin():
        mapping = await session.get(SignalMapping, mapping_id)
        if mapping is None:
            raise NotFoundError("Signal mapping not found")
        await evaluate_policy(session, actor.user_id, action="signal_mapping.release", site_id=mapping.site_id)
        return await release_signal_mapping(session, cmd, actor.user_id)


@router.post("/batch-contexts", response_model=dict)
async def post_open_batch_context(
    cmd: OpenBatchContextCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        source = await session.get(MachineSource, cmd.source_id)
        if source is None:
            raise NotFoundError("Machine source not found")
        await evaluate_policy(session, actor.user_id, action="batch_context.open", site_id=source.site_id)
        return await open_batch_context(session, cmd, actor.user_id)


@router.post("/batch-contexts/{context_id}/close", response_model=MutationReceipt)
async def post_close_batch_context(
    context_id: uuid.UUID,
    cmd: CloseBatchContextCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.context_id != context_id:
        raise ValidationFailedError("context_id in path and body must match")
    async with session.begin():
        context = await session.get(BatchContext, context_id)
        if context is None:
            raise NotFoundError("Batch context not found")
        await evaluate_policy(session, actor.user_id, action="batch_context.close", site_id=context.site_id)
        return await close_batch_context(session, cmd, actor.user_id)


@router.post("/machine-sources/{source_id}/evidence:ingest", response_model=dict)
async def post_ingest_machine_evidence(
    source_id: uuid.UUID,
    cmd: IngestMachineEvidenceCommand,
    session: AsyncSession = Depends(get_session),
    service_identity: AuthenticatedServiceIdentity = Depends(get_service_identity),
) -> dict:
    async with session.begin():
        return await ingest_machine_evidence(session, source_id, cmd, service_identity)


@router.post("/machine-sources/{source_id}/cycle-evidence-manifests", response_model=dict)
async def post_build_cycle_evidence_manifest(
    source_id: uuid.UUID,
    cmd: BuildCycleEvidenceManifestCommand,
    session: AsyncSession = Depends(get_session),
    service_identity: AuthenticatedServiceIdentity = Depends(get_service_identity),
) -> dict:
    async with session.begin():
        return await build_cycle_evidence_manifest(session, source_id, cmd, service_identity)


class MachineCommandChallengeRequest(BaseModel):
    source_id: uuid.UUID
    operation_code: str
    parameters: dict | None = None


@router.post("/machine-commands/signature-challenges")
async def post_machine_command_signature_challenge(
    body: MachineCommandChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """No `MachineCommandRequest` row exists yet at approval time (same "creation command, no prior
    version" shape as `edge.router`'s enrollment challenge) -- the challenge binds to the requested
    source/operation/parameters instead, and `submit_approved_machine_command` recomputes the identical
    hash when consuming it."""
    async with session.begin():
        pre_hash = sha256_hex({"source_id": str(body.source_id), "operation_code": body.operation_code, "parameters": body.parameters})
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="machine_command_profile", record_id=body.source_id,
            record_version=0, record_hash=pre_hash, meaning="Approved",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/machine-commands", response_model=MutationReceipt)
async def post_submit_approved_machine_command(
    cmd: SubmitApprovedMachineCommandCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        source = await session.get(MachineSource, cmd.source_id)
        if source is None:
            raise NotFoundError("Machine source not found")
        await evaluate_policy(session, actor.user_id, action="machine_command.submit", site_id=source.site_id)
        return await submit_approved_machine_command(session, cmd, actor.user_id)


@router.post("/machine-commands/{request_id}/finalize", response_model=MutationReceipt)
async def post_finalize_machine_command(
    request_id: uuid.UUID,
    cmd: FinalizeMachineCommandCommand,
    session: AsyncSession = Depends(get_session),
    service_identity: AuthenticatedServiceIdentity = Depends(get_service_identity),
) -> MutationReceipt:
    async with session.begin():
        return await finalize_machine_command(session, request_id, cmd, service_identity)


@router.get("/machine-commands/{request_id}")
async def get_machine_command(request_id: uuid.UUID, session: AsyncSession = Depends(get_session)) -> dict:
    request = await session.get(MachineCommandRequest, request_id)
    if request is None:
        raise NotFoundError("Machine command request not found")
    return {
        "id": str(request.id), "status": request.status, "source_id": str(request.source_id),
        "batch_id": str(request.batch_id) if request.batch_id else None, "version": request.version,
        "native_response": request.native_response, "evidence_ref": request.evidence_ref,
    }


@router.get("/evidence-review")
async def list_evidence_for_review(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    site_id: uuid.UUID | None = None,
    limit: int = Query(50, ge=1, le=200),
) -> dict:
    """MAP-FR-030: out-of-limit machine data and alarms visible in QA review. Read-only visibility only
    -- no "mark reviewed" action exists here. Nothing in Document 47's own function catalogue names a
    review-completion function, and inventing one (a signature/state-machine over what is, in substance,
    a quality disposition) would be guessing a regulated decision CLAUDE.md §4 reserves; known limitation,
    not built this pass, not a SPEC_GAP (the requirement's own acceptance intent -- "visible in QA
    review" -- is fully satisfied by visibility alone).
    """
    await evaluate_policy(session, actor.user_id, action="machine_evidence.review_view", site_id=site_id)

    candidate_stmt = select(MachineEvidenceCandidate).where(MachineEvidenceCandidate.status == "CANDIDATE")
    alarm_stmt = select(MachineAlarmEvent).where(MachineAlarmEvent.review_status == "PENDING_REVIEW")
    if site_id:
        candidate_stmt = candidate_stmt.where(MachineEvidenceCandidate.site_id == site_id)
        alarm_stmt = alarm_stmt.where(MachineAlarmEvent.site_id == site_id)

    candidates = (
        await session.execute(candidate_stmt.order_by(MachineEvidenceCandidate.created_at.desc()).limit(limit))
    ).scalars().all()
    alarms = (
        await session.execute(alarm_stmt.order_by(MachineAlarmEvent.created_at.desc()).limit(limit))
    ).scalars().all()
    return {
        "candidates": [
            {
                "id": str(c.id), "event_id": str(c.event_id), "evidence_class": c.evidence_class,
                "domain_code": c.domain_code, "quality": c.quality, "freshness": c.freshness,
                "batch_context_id": str(c.batch_context_id) if c.batch_context_id else None,
                "created_at": c.created_at.isoformat() if c.created_at else None,
            }
            for c in candidates
        ],
        "alarms": [
            {
                "id": str(a.id), "event_id": str(a.event_id), "alarm_code": a.alarm_code, "severity": a.severity,
                "batch_context_id": str(a.batch_context_id) if a.batch_context_id else None,
                "created_at": a.created_at.isoformat() if a.created_at else None,
            }
            for a in alarms
        ],
    }


@router.get("/cycle-evidence-manifests/{manifest_id}/export")
async def get_machine_evidence_export_route(
    manifest_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    """MAP-FR-031: inspection export composing an already-built manifest with its linked evidence
    candidates/alarms and hash/reference -- reuses the review-visibility grant (`machine_evidence.
    review_view`) rather than a new permission code, since export is the same QA/inspector visibility
    scope the evidence-review listing already grants."""
    async with session.begin():
        from app.modules.machine_integration.models import CycleEvidenceManifest

        manifest = await session.get(CycleEvidenceManifest, manifest_id)
        if manifest is None:
            raise NotFoundError("Cycle evidence manifest not found")
        await evaluate_policy(session, actor.user_id, action="machine_evidence.review_view", site_id=manifest.site_id)
        return await get_machine_evidence_export(session, manifest_id)


class ReplaySignatureChallengeRequest(BaseModel):
    event_ids: list[uuid.UUID]
    mode: str


@router.post("/evidence-replays/signature-challenges")
async def post_replay_signature_challenge(
    body: ReplaySignatureChallengeRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        pre_hash = sha256_hex({"event_ids": sorted(str(e) for e in body.event_ids), "mode": body.mode})
        challenge = await create_challenge(
            session, user_id=actor.user_id, record_type="machine_replay_job", record_id=actor.user_id,
            record_version=0, record_hash=pre_hash, meaning="Approved",
        )
        return {"challenge_id": str(challenge.id), "meaning": challenge.meaning, "expires_at": challenge.expires_at.isoformat()}


@router.post("/sites/{site_id}/evidence-replays", response_model=dict)
async def post_replay_historical_evidence(
    site_id: uuid.UUID,
    cmd: ReplayHistoricalEvidenceCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="machine_replay.create", site_id=site_id)
        return await replay_historical_evidence(session, site_id, cmd, actor.user_id)
