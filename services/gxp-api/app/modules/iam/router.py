import uuid

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestForm
from pydantic import BaseModel
from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import get_session
from app.core.pagination import PageParams, page_params, paginate
from app.core.security import AuthenticatedActor, create_access_token, get_current_actor
from app.modules.iam.commands import (
    AssignUserRoleCommand,
    CreateRoleCommand,
    CreateSiteCommand,
    CreateUserCommand,
    DeleteRoleCommand,
    DeleteSiteCommand,
    SetRolePermissionsCommand,
    SetUserStatusCommand,
    UpdateOrganizationCommand,
    UpdateRoleCommand,
    UpdateSiteCommand,
    UpdateUserCommand,
    assign_user_role,
    create_role,
    create_site,
    create_user,
    deactivate_user,
    delete_role,
    delete_site,
    reactivate_user,
    set_role_permissions,
    update_organization,
    update_role,
    update_site,
    update_user,
)
from app.modules.iam.models import Organization, Permission, Role, RolePermission, Site, User, UserSiteRole
from app.modules.iam.service import authenticate, get_permission_codes, get_role_names
from app.modules.policy.service import effective_role_names, evaluate_policy
from app.modules.security import identity_commands as security_identity_commands
from app.mutation.errors import GxPError, NotFoundError, ValidationFailedError
from app.mutation.schemas import MutationReceipt

router = APIRouter(prefix="/auth", tags=["auth"])
organization_router = APIRouter(prefix="/organization", tags=["iam"])
sites_router = APIRouter(prefix="/sites", tags=["iam"])
users_router = APIRouter(prefix="/users", tags=["iam"])
roles_router = APIRouter(prefix="/roles", tags=["iam"])
permissions_router = APIRouter(prefix="/permissions", tags=["iam"])
policy_router = APIRouter(prefix="/policy", tags=["iam"])


@router.post("/token")
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    session: AsyncSession = Depends(get_session),
) -> dict:
    # Document 62 (SPEC-SEC-002) IAMSEC-FR-001's own permitted "approved isolated deployment" password
    # fallback path -- now real createApplicationSession() wiring (IAMSEC-FR-006/007) rather than a bare
    # stateless JWT: every login creates a revocable `security.application_session` row and binds it into
    # the issued token (see app/core/security.py::get_current_actor).
    async with session.begin():
        user = await authenticate(session, form_data.username, form_data.password)
        role_names = await effective_role_names(session, user.id, None)
        mfa = security_identity_commands.evaluate_mfa_requirement_sync(role_names)
        app_session = await security_identity_commands.create_application_session(
            session, subject_id=user.id,
            auth_strength={"methods": ["PASSWORD"], "mfa_required": mfa["mfa_required"], "mfa_completed": False},
            actor_user_id=user.id,
        )
    token = create_access_token(user.id, user.username, session_id=app_session.id)
    return {"access_token": token, "token_type": "bearer"}


@router.post("/logout", response_model=MutationReceipt)
async def logout(
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if actor.session_id is None:
        raise ValidationFailedError("This token was not created with session tracking; nothing to log out")
    async with session.begin():
        return await security_identity_commands.revoke_session(
            session,
            security_identity_commands.RevokeSessionCommand(
                idempotency_key=str(uuid.uuid4()), session_id=actor.session_id, reason="User logout",
            ),
            actor.user_id,
        )


@router.get("/me")
async def me(
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    sites = (await session.execute(select(Site))).scalars().all()
    roles_by_site = {
        str(site.id): sorted(await get_role_names(session, actor.user_id, site.id)) for site in sites
    }
    # permissions_by_site is the dynamic authorization surface the frontend should gate UI on -- unlike
    # roles_by_site (role NAMES, which are user-editable data outside Admin), these are the actual
    # permission codes evaluate_policy() itself checks, so a role rename/re-permission can never leave a
    # frontend gate silently stale (2026-09-18, see get_permission_codes docstring).
    permissions_by_site = {
        str(site.id): sorted(await get_permission_codes(session, actor.user_id, site.id)) for site in sites
    }
    return {
        "user_id": str(actor.user_id),
        "username": actor.username,
        "roles_by_site": roles_by_site,
        "permissions_by_site": permissions_by_site,
    }


@organization_router.get("")
async def get_organization(
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor)
) -> dict:
    await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
    org = (await session.execute(select(Organization).limit(1))).scalar_one_or_none()
    if org is None:
        raise NotFoundError("No organization exists yet")
    return {"id": str(org.id), "name": org.name}


@organization_router.patch("", response_model=MutationReceipt)
async def patch_organization(
    cmd: UpdateOrganizationCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await update_organization(session, cmd, actor.user_id)


@sites_router.get("")
async def list_sites(
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor)
) -> list[dict]:
    # Deliberately no evaluate_policy() beyond authentication itself -- `useSiteId()`
    # (frontend/src/lib/hooks.ts) calls this for every signed-in user's site picker, app-wide, not just
    # the Admin-only /admin/sites management page. Gating it behind platform.administer would 403 every
    # non-admin user's site scoping across the entire app.
    del actor
    result = await session.execute(select(Site))
    return [{"id": str(s.id), "code": s.code, "name": s.name} for s in result.scalars().all()]


@sites_router.post("", response_model=MutationReceipt)
async def post_create_site(
    cmd: CreateSiteCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await create_site(session, cmd, actor.user_id)


@sites_router.patch("/{site_id}", response_model=MutationReceipt)
async def patch_site(
    site_id: uuid.UUID,
    cmd: UpdateSiteCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.site_id != site_id:
        raise ValidationFailedError("site_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await update_site(session, cmd, actor.user_id)


@sites_router.delete("/{site_id}", response_model=MutationReceipt)
async def delete_site_endpoint(
    site_id: uuid.UUID,
    cmd: DeleteSiteCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.site_id != site_id:
        raise ValidationFailedError("site_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await delete_site(session, cmd, actor.user_id)


# ---------------------------------------------------------------------------
# Users
# ---------------------------------------------------------------------------

USER_SORTABLE = {
    "username": User.username,
    "email": User.email,
    "full_name": User.full_name,
    "status": User.status,
    "created_at": User.created_at,
}


@users_router.post("", response_model=MutationReceipt)
async def post_create_user(
    cmd: CreateUserCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await create_user(session, cmd, actor.user_id)


@users_router.get("")
async def list_users(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    # Authentication only, deliberately no evaluate_policy() -- `useEntityOptions()`
    # (frontend/src/lib/hooks.ts) calls this app-wide for "assign to user" pickers used by many
    # non-admin roles (deviation triage, CAPA ownership, etc.), not just the Admin-only /admin/users page.
    del actor
    stmt = select(User)
    if params.q:
        needle = f"%{params.q}%"
        stmt = stmt.where(
            or_(User.username.ilike(needle), User.email.ilike(needle), User.full_name.ilike(needle))
        )
    rows, envelope = await paginate(
        session, stmt, params, sortable=USER_SORTABLE, default_sort=User.created_at
    )

    user_ids = [u.id for (u,) in rows]
    roles_by_user: dict[uuid.UUID, list[str]] = {}
    if user_ids:
        role_rows = await session.execute(
            select(UserSiteRole.user_id, Role.name, Site.code)
            .join(Role, Role.id == UserSiteRole.role_id)
            .join(Site, Site.id == UserSiteRole.site_id)
            .where(UserSiteRole.user_id.in_(user_ids))
        )
        for user_id, role_name, site_code in role_rows.all():
            roles_by_user.setdefault(user_id, []).append(f"{role_name} @ {site_code}")

    return {
        **envelope,
        "items": [
            {
                "id": str(u.id),
                "username": u.username,
                "email": u.email,
                "full_name": u.full_name,
                "status": u.status,
                "roles": roles_by_user.get(u.id, []),
            }
            for (u,) in rows
        ],
    }


@users_router.patch("/{user_id}", response_model=MutationReceipt)
async def patch_user(
    user_id: uuid.UUID,
    cmd: UpdateUserCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.user_id != user_id:
        raise ValidationFailedError("user_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await update_user(session, cmd, actor.user_id)


@users_router.post("/{user_id}/deactivate", response_model=MutationReceipt)
async def post_deactivate_user(
    user_id: uuid.UUID,
    cmd: SetUserStatusCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.user_id != user_id:
        raise ValidationFailedError("user_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await deactivate_user(session, cmd, actor.user_id)


@users_router.post("/{user_id}/reactivate", response_model=MutationReceipt)
async def post_reactivate_user(
    user_id: uuid.UUID,
    cmd: SetUserStatusCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.user_id != user_id:
        raise ValidationFailedError("user_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await reactivate_user(session, cmd, actor.user_id)


@users_router.post("/{user_id}/roles", response_model=MutationReceipt)
async def post_assign_user_role(
    user_id: uuid.UUID,
    cmd: AssignUserRoleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.user_id != user_id:
        raise ValidationFailedError("user_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=cmd.site_id)
        return await assign_user_role(session, cmd, actor.user_id)


# ---------------------------------------------------------------------------
# Roles
# ---------------------------------------------------------------------------

ROLE_SORTABLE = {"name": Role.name}


@roles_router.post("", response_model=MutationReceipt)
async def post_create_role(
    cmd: CreateRoleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await create_role(session, cmd, actor.user_id)


@roles_router.get("")
async def list_roles(
    session: AsyncSession = Depends(get_session), params: PageParams = Depends(page_params),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    # Authentication only, deliberately no evaluate_policy() -- `frontend/src/app/recipe-master/
    # shared.tsx` calls this for a role picker used well beyond the Admin-only /admin/roles page.
    del actor
    stmt = select(Role)
    if params.q:
        needle = f"%{params.q}%"
        stmt = stmt.where(or_(Role.name.ilike(needle), Role.description.ilike(needle)))
    rows, envelope = await paginate(session, stmt, params, sortable=ROLE_SORTABLE, default_sort=Role.name)
    return {
        **envelope,
        "items": [{"id": str(r.id), "name": r.name, "description": r.description} for (r,) in rows],
    }


@roles_router.get("/{role_id}")
async def get_role(
    role_id: uuid.UUID, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
    role = await session.get(Role, role_id)
    if role is None:
        raise NotFoundError("Role not found")
    return {"id": str(role.id), "name": role.name, "description": role.description}


@roles_router.patch("/{role_id}", response_model=MutationReceipt)
async def patch_role(
    role_id: uuid.UUID,
    cmd: UpdateRoleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.role_id != role_id:
        raise ValidationFailedError("role_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await update_role(session, cmd, actor.user_id)


@roles_router.delete("/{role_id}", response_model=MutationReceipt)
async def delete_role_endpoint(
    role_id: uuid.UUID,
    cmd: DeleteRoleCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.role_id != role_id:
        raise ValidationFailedError("role_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await delete_role(session, cmd, actor.user_id)


@roles_router.get("/{role_id}/permissions")
async def get_role_permissions(
    role_id: uuid.UUID, session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> list[dict]:
    await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
    rows = await session.execute(
        select(Permission)
        .join(RolePermission, RolePermission.permission_id == Permission.id)
        .where(RolePermission.role_id == role_id)
        .order_by(Permission.code)
    )
    return [
        {"id": str(p.id), "code": p.code, "action": p.action, "resource_type": p.resource_type}
        for p in rows.scalars().all()
    ]


@roles_router.post("/{role_id}/permissions", response_model=MutationReceipt)
async def post_role_permissions(
    role_id: uuid.UUID,
    cmd: SetRolePermissionsCommand,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> MutationReceipt:
    if cmd.role_id != role_id:
        raise ValidationFailedError("role_id in path and body must match")
    async with session.begin():
        await evaluate_policy(session, actor.user_id, action="platform.administer", site_id=None)
        return await set_role_permissions(session, cmd, actor.user_id)


# ---------------------------------------------------------------------------
# Permissions (read-only catalog — seeded, not user-created this pass)
# ---------------------------------------------------------------------------


@permissions_router.get("")
async def list_permissions(
    session: AsyncSession = Depends(get_session), actor: AuthenticatedActor = Depends(get_current_actor)
) -> list[dict]:
    # Authentication only, deliberately no evaluate_policy() -- a read-only reference catalog any
    # authenticated user may list (test_policy_engine.py::test_list_permissions_includes_seeded_catalog
    # already asserts a non-admin operator gets 200 here), same treatment as /sites/users/roles above.
    del actor
    rows = await session.execute(select(Permission).order_by(Permission.code))
    return [
        {
            "id": str(p.id),
            "code": p.code,
            "action": p.action,
            "resource_type": p.resource_type,
            "description": p.description,
        }
        for p in rows.scalars().all()
    ]


# ---------------------------------------------------------------------------
# Policy decisions (Document 07 `POST /policy/v1/decisions`) — a live decision query, not a persisted/
# audited resource: no schema exists for a decision-log entity in the source baseline (see SPEC_GAP),
# so this reports allow/deny + reason without writing a record.
# ---------------------------------------------------------------------------


class PolicyDecisionRequest(BaseModel):
    action: str
    site_id: uuid.UUID | None = None


@policy_router.post("/v1/decisions")
async def post_policy_decision(
    body: PolicyDecisionRequest,
    session: AsyncSession = Depends(get_session),
    actor: AuthenticatedActor = Depends(get_current_actor),
) -> dict:
    async with session.begin():
        held_roles = sorted(await effective_role_names(session, actor.user_id, body.site_id))
        try:
            await evaluate_policy(session, actor.user_id, action=body.action, site_id=body.site_id)
        except GxPError as exc:
            return {
                "decision": "DENY",
                "action": body.action,
                "reason": exc.code,
                "message": exc.message,
                "held_roles": held_roles,
            }
        return {"decision": "ALLOW", "action": body.action, "reason": None, "held_roles": held_roles}
