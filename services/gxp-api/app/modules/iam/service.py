import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import Permission, Role, RolePermission, User, UserSiteRole
from app.mutation.errors import UnauthorizedError


async def get_user_by_username(session: AsyncSession, username: str) -> User | None:
    result = await session.execute(select(User).where(User.username == username))
    return result.scalar_one_or_none()


async def authenticate(session: AsyncSession, username: str, password: str) -> User:
    user = await get_user_by_username(session, username)
    if user is None or user.status != "active" or not verify_password(password, user.password_hash):
        raise UnauthorizedError("Invalid username or password")
    return user


async def get_role_names(session: AsyncSession, user_id: uuid.UUID, site_id: uuid.UUID) -> set[str]:
    result = await session.execute(
        select(Role.name)
        .join(UserSiteRole, UserSiteRole.role_id == Role.id)
        .where(UserSiteRole.user_id == user_id, UserSiteRole.site_id == site_id)
    )
    return set(result.scalars().all())


# Resolves what a user can actually DO at a site (permission codes), as opposed to get_role_names above
# (which roles), so callers -- chiefly /auth/me -- can hand the frontend the real, dynamic authorization
# boundary instead of role names. Role names are user-editable data (any role but Admin can be renamed,
# deleted, or have its permission set changed at any time via /admin/roles), so a frontend gate hardcoded
# against a role name silently drifts from the backend the moment someone edits that role -- exactly the
# bug class an audit found repeatedly across this app's pages (2026-09-18). Permission codes are the
# stable vocabulary evaluate_policy() itself checks, so they can't drift the same way.
async def get_permission_codes(session: AsyncSession, user_id: uuid.UUID, site_id: uuid.UUID) -> set[str]:
    result = await session.execute(
        select(Permission.code)
        .select_from(UserSiteRole)
        .join(RolePermission, RolePermission.role_id == UserSiteRole.role_id)
        .join(Permission, Permission.id == RolePermission.permission_id)
        .where(UserSiteRole.user_id == user_id, UserSiteRole.site_id == site_id)
    )
    return set(result.scalars().all())


