import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qms.internal_audit_commands import (
    AddFindingCommand,
    CloseInternalAuditCommand,
    CreateInternalAuditCommand,
    RespondToFindingCommand,
    StartInternalAuditCommand,
    VerifyFindingCommand,
    add_finding,
    close_internal_audit,
    create_internal_audit,
    respond_to_finding,
    start_internal_audit,
    verify_finding,
)
from app.modules.qms.internal_audit_models import AuditFinding, InternalAudit
from app.modules.qms.read_support import filtered, iso
from app.modules.qms.signature_support import SignatureChallengeRequest, create_qms_signature_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

internal_audit_router = APIRouter(prefix="/qms/v1/audits", tags=["qms-internal-audit"])
audit_finding_router = APIRouter(prefix="/qms/v1/findings", tags=["qms-internal-audit"])

INTERNAL_AUDIT_SIGNATURE_ACTIONS = ("start", "close")
AUDIT_FINDING_SIGNATURE_ACTIONS = ("verify",)


@internal_audit_router.post("", response_model=MutationReceipt)
async def post_create_internal_audit(
    cmd: CreateInternalAuditCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="internal_audit.create", site_id=cmd.site_id)
        return await create_internal_audit(session, cmd, actor.user_id)


@internal_audit_router.post("/{audit_id}/start", response_model=MutationReceipt)
async def post_start_internal_audit(
    audit_id: uuid.UUID, cmd: StartInternalAuditCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.audit_id != audit_id:
        raise ValidationFailedError("audit_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="internal_audit.start", site_id=None)
        return await start_internal_audit(session, cmd, actor.user_id)


@internal_audit_router.post("/{audit_id}/findings", response_model=MutationReceipt)
async def post_add_finding(
    audit_id: uuid.UUID, cmd: AddFindingCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.audit_id != audit_id:
        raise ValidationFailedError("audit_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="internal_audit.finding.add", site_id=None)
        return await add_finding(session, cmd, actor.user_id)


@audit_finding_router.post("/{finding_id}/response", response_model=MutationReceipt)
async def post_respond_to_finding(
    finding_id: uuid.UUID, cmd: RespondToFindingCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.finding_id != finding_id:
        raise ValidationFailedError("finding_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="internal_audit.finding.response", site_id=None)
        return await respond_to_finding(session, cmd, actor.user_id)


@audit_finding_router.post("/{finding_id}/signature-challenges")
async def post_finding_signature_challenge(
    finding_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        finding = await session.get(AuditFinding, finding_id)
        if finding is None:
            raise NotFoundError("Audit finding not found")
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="audit_finding", record=finding,
            action=body.action, allowed_actions=AUDIT_FINDING_SIGNATURE_ACTIONS,
        )


@audit_finding_router.post("/{finding_id}/verify", response_model=MutationReceipt)
async def post_verify_finding(
    finding_id: uuid.UUID, cmd: VerifyFindingCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.finding_id != finding_id:
        raise ValidationFailedError("finding_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="internal_audit.finding.verify", site_id=None)
        return await verify_finding(session, cmd, actor.user_id)


@internal_audit_router.post("/{audit_id}/signature-challenges")
async def post_signature_challenge(
    audit_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        audit = await session.get(InternalAudit, audit_id)
        if audit is None:
            raise NotFoundError("Internal audit not found")
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="internal_audit", record=audit,
            action=body.action, allowed_actions=INTERNAL_AUDIT_SIGNATURE_ACTIONS,
        )


@internal_audit_router.post("/{audit_id}/close", response_model=MutationReceipt)
async def post_close_internal_audit(
    audit_id: uuid.UUID, cmd: CloseInternalAuditCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.audit_id != audit_id:
        raise ValidationFailedError("audit_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="internal_audit.close", site_id=None)
        return await close_internal_audit(session, cmd, actor.user_id)


# --- Read side ---------------------------------------------------------------------------------

AUDIT_SORTABLE = {
    "audit_number": InternalAudit.audit_number,
    "state": InternalAudit.state,
    "scheduled_at": InternalAudit.scheduled_at,
    "created_at": InternalAudit.created_at,
}
FINDING_SORTABLE = {
    "finding_number": AuditFinding.finding_number,
    "severity": AuditFinding.severity,
    "state": AuditFinding.state,
    "due_date": AuditFinding.due_date,
    "created_at": AuditFinding.created_at,
}


def _audit_dict(record: InternalAudit) -> dict:
    return {
        "id": str(record.id),
        "site_id": str(record.site_id),
        "quality_event_id": str(record.quality_event_id),
        "audit_number": record.audit_number,
        "program_ref": record.program_ref,
        "lead_auditor_id": str(record.lead_auditor_id),
        "team": record.team,
        "auditees": record.auditees,
        "scheduled_at": iso(record.scheduled_at),
        "actual_start_at": iso(record.actual_start_at),
        "actual_end_at": iso(record.actual_end_at),
        "state": record.state,
        "version": record.version,
        "created_at": iso(record.created_at),
    }


def _finding_dict(record: AuditFinding) -> dict:
    return {
        "id": str(record.id),
        "site_id": str(record.site_id),
        "audit_id": str(record.audit_id),
        "finding_number": record.finding_number,
        "requirement_ref": record.requirement_ref,
        "observation": record.observation,
        "evidence": record.evidence,
        "severity": record.severity,
        "owner_subject_id": str(record.owner_subject_id),
        "due_date": iso(record.due_date),
        "response": record.response,
        "capa_required": record.capa_required,
        "capa_rationale": record.capa_rationale,
        "is_repeat_finding": record.is_repeat_finding,
        "verification": record.verification,
        "state": record.state,
        "version": record.version,
        "created_at": iso(record.created_at),
        "closed_at": iso(record.closed_at),
    }


@internal_audit_router.get("")
async def list_internal_audits(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    state: str | None = None,
) -> dict:
    await evaluate_policy(session, actor.user_id, action="internal_audit.view", site_id=site_id)
    stmt = filtered(
        InternalAudit, params, search_column=InternalAudit.audit_number, site_id=site_id, state=state
    )
    rows, envelope = await paginate(
        session, stmt, params, sortable=AUDIT_SORTABLE, default_sort=InternalAudit.scheduled_at
    )
    return {**envelope, "items": [_audit_dict(r) for (r,) in rows]}


@internal_audit_router.get("/{audit_id}")
async def get_internal_audit(
    audit_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    record = await session.get(InternalAudit, audit_id)
    if record is None:
        raise NotFoundError("Internal audit not found")
    await evaluate_policy(session, actor.user_id, action="internal_audit.view", site_id=record.site_id)
    findings = (
        await session.execute(select(AuditFinding).where(AuditFinding.audit_id == audit_id))
    ).scalars().all()
    return {
        **_audit_dict(record),
        "site_scope": record.site_scope,
        "process_scope": record.process_scope,
        "criteria_refs": record.criteria_refs,
        "findings": [_finding_dict(f) for f in findings],
    }


@audit_finding_router.get("")
async def list_audit_findings(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    state: str | None = None,
    audit_id: uuid.UUID | None = None,
) -> dict:
    """Cross-audit finding worklist (AUD-FR-018 open-findings view), or one audit's findings."""
    await evaluate_policy(session, actor.user_id, action="internal_audit.view", site_id=site_id)
    stmt = filtered(
        AuditFinding, params, search_column=AuditFinding.finding_number, site_id=site_id, state=state
    )
    if audit_id is not None:
        stmt = stmt.where(AuditFinding.audit_id == audit_id)
    rows, envelope = await paginate(
        session, stmt, params, sortable=FINDING_SORTABLE, default_sort=AuditFinding.created_at
    )
    return {**envelope, "items": [_finding_dict(r) for (r,) in rows]}


@audit_finding_router.get("/{finding_id}")
async def get_audit_finding(
    finding_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    record = await session.get(AuditFinding, finding_id)
    if record is None:
        raise NotFoundError("Audit finding not found")
    await evaluate_policy(session, actor.user_id, action="internal_audit.view", site_id=record.site_id)
    return _finding_dict(record)
