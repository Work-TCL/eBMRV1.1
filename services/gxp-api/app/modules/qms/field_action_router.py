import uuid

from fastapi import APIRouter, Depends
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.policy.service import evaluate_policy
from app.modules.qms.field_action_commands import (
    ApproveFieldActionCommand,
    CloseFieldActionCommand,
    CreateFieldActionCommand,
    DefineScopeCommand,
    EffectivenessCommand,
    ReconcileCommand,
    RecordCommunicationCommand,
    ReportabilityCommand,
    approve_field_action,
    assess_field_action_reportability,
    close_field_action,
    create_field_action,
    define_scope,
    reconcile_field_action,
    record_field_action_communication,
    record_field_action_effectiveness,
)
from app.modules.qms.field_action_models import (
    FieldAction,
    FieldActionCommunication,
    FieldActionReconciliation,
    FieldActionScopeItem,
)
from app.modules.qms.read_support import filtered, iso, sid
from app.modules.qms.signature_support import SignatureChallengeRequest, create_qms_signature_challenge
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

field_action_router = APIRouter(prefix="/qms/v1/field-actions", tags=["qms-field-action"])

FIELD_ACTION_SIGNATURE_ACTIONS = ("reportability", "approve", "close")


@field_action_router.post("", response_model=MutationReceipt)
async def post_create_field_action(
    cmd: CreateFieldActionCommand, session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="field_action.create", site_id=cmd.site_id)
        return await create_field_action(session, cmd, actor.user_id)


@field_action_router.post("/{field_action_id}/scope", response_model=MutationReceipt)
async def post_define_scope(
    field_action_id: uuid.UUID, cmd: DefineScopeCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.field_action_id != field_action_id:
        raise ValidationFailedError("field_action_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="field_action.scope", site_id=None)
        return await define_scope(session, cmd, actor.user_id)


@field_action_router.post("/{field_action_id}/reportability", response_model=MutationReceipt)
async def post_assess_reportability(
    field_action_id: uuid.UUID, cmd: ReportabilityCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.field_action_id != field_action_id:
        raise ValidationFailedError("field_action_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="field_action.reportability", site_id=None)
        return await assess_field_action_reportability(session, cmd, actor.user_id)


@field_action_router.post("/{field_action_id}/approve", response_model=MutationReceipt)
async def post_approve_field_action(
    field_action_id: uuid.UUID, cmd: ApproveFieldActionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.field_action_id != field_action_id:
        raise ValidationFailedError("field_action_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="field_action.approve", site_id=None)
        return await approve_field_action(session, cmd, actor.user_id)


@field_action_router.post("/{field_action_id}/communications", response_model=MutationReceipt)
async def post_record_communication(
    field_action_id: uuid.UUID, cmd: RecordCommunicationCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.field_action_id != field_action_id:
        raise ValidationFailedError("field_action_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="field_action.communications", site_id=None)
        return await record_field_action_communication(session, cmd, actor.user_id)


@field_action_router.post("/{field_action_id}/reconcile", response_model=MutationReceipt)
async def post_reconcile(
    field_action_id: uuid.UUID, cmd: ReconcileCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.field_action_id != field_action_id:
        raise ValidationFailedError("field_action_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="field_action.reconcile", site_id=None)
        return await reconcile_field_action(session, cmd, actor.user_id)


@field_action_router.post("/{field_action_id}/effectiveness", response_model=MutationReceipt)
async def post_effectiveness(
    field_action_id: uuid.UUID, cmd: EffectivenessCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.field_action_id != field_action_id:
        raise ValidationFailedError("field_action_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="field_action.effectiveness", site_id=None)
        return await record_field_action_effectiveness(session, cmd, actor.user_id)


@field_action_router.post("/{field_action_id}/signature-challenges")
async def post_signature_challenge(
    field_action_id: uuid.UUID, body: SignatureChallengeRequest, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        field_action = await session.get(FieldAction, field_action_id)
        if field_action is None:
            raise NotFoundError("Field action not found")
        return await create_qms_signature_challenge(
            session, actor_user_id=actor.user_id, record_type="field_action", record=field_action,
            action=body.action, allowed_actions=FIELD_ACTION_SIGNATURE_ACTIONS,
        )


@field_action_router.post("/{field_action_id}/close", response_model=MutationReceipt)
async def post_close_field_action(
    field_action_id: uuid.UUID, cmd: CloseFieldActionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.field_action_id != field_action_id:
        raise ValidationFailedError("field_action_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="field_action.close", site_id=None)
        return await close_field_action(session, cmd, actor.user_id)


# --- Read side ---------------------------------------------------------------------------------

FIELD_ACTION_SORTABLE = {
    "action_number": FieldAction.action_number,
    "action_type": FieldAction.action_type,
    "state": FieldAction.state,
    "created_at": FieldAction.created_at,
}


def _field_action_dict(record: FieldAction) -> dict:
    return {
        "id": str(record.id),
        "site_id": str(record.site_id),
        "quality_event_id": str(record.quality_event_id),
        "action_number": record.action_number,
        "action_type": record.action_type,
        "risk_assessment_ref": sid(record.risk_assessment_ref),
        "capa_required": record.capa_required,
        "capa_rationale": record.capa_rationale,
        "scope_snapshot_id": sid(record.scope_snapshot_id),
        "revision": record.revision,
        "state": record.state,
        "version": record.version,
        "created_at": iso(record.created_at),
        "closed_at": iso(record.closed_at),
    }


@field_action_router.get("")
async def list_field_actions(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
    params: PageParams = Depends(page_params),
    site_id: uuid.UUID | None = None,
    state: str | None = None,
) -> dict:
    await evaluate_policy(session, actor.user_id, action="field_action.view", site_id=site_id)
    stmt = filtered(
        FieldAction, params, search_column=FieldAction.action_number, site_id=site_id, state=state
    )
    rows, envelope = await paginate(
        session, stmt, params, sortable=FIELD_ACTION_SORTABLE, default_sort=FieldAction.created_at
    )
    return {**envelope, "items": [_field_action_dict(r) for (r,) in rows]}


@field_action_router.get("/{field_action_id}")
async def get_field_action(
    field_action_id: uuid.UUID,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    record = await session.get(FieldAction, field_action_id)
    if record is None:
        raise NotFoundError("Field action not found")
    await evaluate_policy(session, actor.user_id, action="field_action.view", site_id=record.site_id)
    scope_items = (
        await session.execute(
            select(FieldActionScopeItem).where(FieldActionScopeItem.field_action_id == field_action_id)
        )
    ).scalars().all()
    communications = (
        await session.execute(
            select(FieldActionCommunication).where(
                FieldActionCommunication.field_action_id == field_action_id
            )
        )
    ).scalars().all()
    reconciliation = (
        await session.execute(
            select(FieldActionReconciliation)
            .where(FieldActionReconciliation.field_action_id == field_action_id)
            .order_by(FieldActionReconciliation.created_at.desc())
        )
    ).scalars().first()
    return {
        **_field_action_dict(record),
        "trigger_ref": record.trigger_ref,
        "reportability_assessment": record.reportability_assessment,
        "effectiveness_check": record.effectiveness_check,
        "scope_items": [
            {
                "id": str(i.id),
                "product_ref": sid(i.product_ref),
                "lot_batch_serial_refs": i.lot_batch_serial_refs,
                "distribution_ref": i.distribution_ref,
                "distribution_hold": i.distribution_hold,
                "status": i.status,
                "action_required": i.action_required,
                "action_completed": i.action_completed,
            }
            for i in scope_items
        ],
        "communications": [
            {
                "id": str(c.id),
                "package_version": c.package_version,
                "recipient": c.recipient,
                "channel": c.channel,
                "message": c.message,
                "sent_at": iso(c.sent_at),
                "delivery_status": c.delivery_status,
                "ack_status": c.ack_status,
            }
            for c in communications
        ],
        "reconciliation": (
            {
                "affected_count": reconciliation.affected_count,
                "contacted_count": reconciliation.contacted_count,
                "returned_count": reconciliation.returned_count,
                "corrected_count": reconciliation.corrected_count,
                "destroyed_count": reconciliation.destroyed_count,
                "unavailable_count": reconciliation.unavailable_count,
                "outstanding_count": reconciliation.outstanding_count,
                "created_at": iso(reconciliation.created_at),
            }
            if reconciliation
            else None
        ),
    }
