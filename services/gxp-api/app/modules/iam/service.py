import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import Role, User, UserSiteRole
from app.mutation.errors import ForbiddenError, UnauthorizedError


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


async def require_role(
    session: AsyncSession, user_id: uuid.UUID, site_id: uuid.UUID, *allowed_role_names: str
) -> set[str]:
    """RBAC gate (MUT-FR-006 equivalent). Raises ForbiddenError if the actor holds none of the
    allowed roles at this site. Returns the actor's role set so callers can also use it for SoD checks.
    """
    roles = await get_role_names(session, user_id, site_id)
    if not roles.intersection(allowed_role_names):
        raise ForbiddenError(
            "Actor lacks a required role at this site",
            required_any_of=list(allowed_role_names),
        )
    return roles
