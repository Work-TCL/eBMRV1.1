"""Document 63 (SPEC-SEC-003) REST surface, prefix `/security/v1`."""

import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.security import AuthenticatedActor, get_current_actor
from app.modules.security import privileged_access_commands as commands
from app.modules.security.privileged_access_models import PrivilegedAccessRequest, PrivilegedSession
from app.modules.policy.service import evaluate_policy
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/security/v1", tags=["security-privileged-access"])


@router.post("/privileged-access/requests", response_model=MutationReceipt)
async def post_request_privileged_access(
    cmd: commands.RequestPrivilegedAccessCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="privileged_access.request", site_id=None)
        return await commands.request_privileged_access(session, cmd, actor.user_id)


@router.post("/privileged-access/requests/{request_id}/approve", response_model=MutationReceipt)
async def post_approve_privileged_access(
    request_id: uuid.UUID, cmd: commands.ApprovePrivilegedAccessCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.request_id != request_id:
        raise ValidationFailedError("request_id in path and body must match")
    async with session.begin():
        request = await session.get(PrivilegedAccessRequest, request_id)
        if request is None:
            raise NotFoundError("Privileged access request not found")
        await evaluate_policy(session, actor.user_id, action="privileged_access.approve", site_id=None)
        return await commands.approve_privileged_access(session, cmd, actor.user_id)


@router.get("/privileged-access/evaluate")
async def get_evaluate_privileged_grant(
    subject_id: uuid.UUID, requested_role: str, resource: str | None = None,
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="privileged_access.view", site_id=None)
        return await commands.evaluate_privileged_grant(session, subject_id=subject_id, requested_role=requested_role, resource=resource)


@router.post("/support-sessions", response_model=MutationReceipt)
async def post_open_support_session(
    cmd: commands.OpenSupportSessionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="privileged_session.open_support", site_id=None)
        return await commands.open_support_session(session, cmd, actor.user_id)


@router.post("/break-glass", response_model=MutationReceipt)
async def post_activate_break_glass(
    cmd: commands.ActivateBreakGlassCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="privileged_session.break_glass", site_id=None)
        return await commands.activate_break_glass(session, cmd, actor.user_id)


@router.post("/admin-commands/{command_code}:execute", response_model=MutationReceipt)
async def post_execute_controlled_admin_command(
    command_code: str, cmd: commands.ExecuteControlledAdminCommandCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.command_code != command_code:
        raise ValidationFailedError("command_code in path and body must match")
    async with session.begin():
        privileged_session = await session.get(PrivilegedSession, cmd.privileged_session_id)
        if privileged_session is None:
            raise NotFoundError("Privileged session not found")
        await evaluate_policy(session, actor.user_id, action="privileged_session.execute_command", site_id=None)
        return await commands.execute_controlled_admin_command(session, cmd, actor.user_id)


@router.post("/privileged-sessions/{privileged_session_id}/close", response_model=MutationReceipt)
async def post_close_privileged_session(
    privileged_session_id: uuid.UUID, cmd: commands.ClosePrivilegedSessionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.privileged_session_id != privileged_session_id:
        raise ValidationFailedError("privileged_session_id in path and body must match")
    async with session.begin():
        privileged_session = await session.get(PrivilegedSession, privileged_session_id)
        if privileged_session is None:
            raise NotFoundError("Privileged session not found")
        await evaluate_policy(session, actor.user_id, action="privileged_session.close", site_id=None)
        return await commands.close_privileged_session(session, cmd, actor.user_id)


@router.post("/privileged-sessions/{privileged_session_id}/review", response_model=MutationReceipt)
async def post_review_privileged_session(
    privileged_session_id: uuid.UUID, cmd: commands.ReviewPrivilegedSessionCommand, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.privileged_session_id != privileged_session_id:
        raise ValidationFailedError("privileged_session_id in path and body must match")
    async with session.begin():
        privileged_session = await session.get(PrivilegedSession, privileged_session_id)
        if privileged_session is None:
            raise NotFoundError("Privileged session not found")
        await evaluate_policy(session, actor.user_id, action="privileged_session.review", site_id=None)
        return await commands.review_privileged_session(session, cmd, actor.user_id)
