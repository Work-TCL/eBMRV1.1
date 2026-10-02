"""The Policy Decision Point (WP-01 Document 07, SPEC-IAM-001 / Document 107) — the data-driven
replacement for what used to be hardcoded role-name string checks scattered across every module
(`require_role(session, actor, site_id, "QA Releaser")` and friends). Authorization is now: does the
actor's currently-effective role set grant a `Permission` for this action (IAM-FR-006), and does that
role set violate a `PROHIBITED` standing-role-pair SoD rule (Document 107 §2/§4, SODB-FR-002's first
evaluation point). Dynamic/action-independence SoD evaluation (Document 107's second control type) is not
implemented here — see docs/generated/18_SPEC_GAPS.md.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.iam.models import Permission, Role, RolePermission, SodRule, UserSiteRole
from app.mutation.errors import RoleMissingError, SodConflictError


async def effective_role_names(
    session: AsyncSession, user_id: uuid.UUID, site_id: uuid.UUID | None
) -> set[str]:
    """Role names currently effective for this actor (respects effective_from/expires_at/status —
    IAM-FR-017 time-bounded assignment). `site_id=None` means "at any site" — the replacement for
    require_admin_anywhere's "anywhere" semantics; a concrete site_id means "at this site only" — the
    replacement for require_role's site-scoped semantics.
    """
    now = datetime.now(timezone.utc)
    stmt = select(Role.name).join(UserSiteRole, UserSiteRole.role_id == Role.id).where(
        UserSiteRole.user_id == user_id,
        UserSiteRole.status == "active",
        UserSiteRole.effective_from <= now,
        (UserSiteRole.expires_at.is_(None)) | (UserSiteRole.expires_at > now),
    )
    if site_id is not None:
        stmt = stmt.where(UserSiteRole.site_id == site_id)
    return set((await session.execute(stmt)).scalars().all())


async def evaluate_policy(
    session: AsyncSession, actor_user_id: uuid.UUID, *, action: str, site_id: uuid.UUID | None
) -> None:
    """Raises on denial (ROLE_MISSING or SOD_CONFLICT); returns normally on allow. Fail-closed: no
    held role, no permission grant, or a standing SoD conflict all deny.
    """
    role_names = await effective_role_names(session, actor_user_id, site_id)
    if not role_names:
        raise RoleMissingError("Actor holds no role at this scope", action=action)

    granted = (
        await session.execute(
            select(Permission.id)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .join(Role, Role.id == RolePermission.role_id)
            .where(Permission.code == action, Role.name.in_(role_names))
            .limit(1)
        )
    ).first()
    if granted is None:
        raise RoleMissingError(
            "Actor's roles do not grant this action", action=action, held_roles=sorted(role_names)
        )

    now = datetime.now(timezone.utc)
    standing_rules = (
        await session.execute(
            select(SodRule).where(
                SodRule.rule_type == "STANDING_ROLE_PAIR",
                SodRule.severity == "PROHIBITED",
                SodRule.effective_from <= now,
                (SodRule.effective_to.is_(None)) | (SodRule.effective_to > now),
            )
        )
    ).scalars().all()
    for rule in standing_rules:
        if rule.role_a in role_names and rule.role_b in role_names:
            raise SodConflictError(
                "Actor holds two roles this platform's SoD policy prohibits together",
                rule_code=rule.code,
                role_a=rule.role_a,
                role_b=rule.role_b,
            )


async def resolve_actor_site_ids(session: AsyncSession, user_id: uuid.UUID) -> set[uuid.UUID]:
    """Every site the actor currently holds any active role at (IAM-FR-017 time-bounded assignment).

    Used to turn an *omitted* `site_id` on a list endpoint into "my own assigned sites" instead of
    the `effective_role_names(site_id=None)` "any site" semantics `evaluate_policy` itself uses for a
    single capability check -- the two must stay separate, or an actor who merely holds a role
    *somewhere* ends up with every site's records unfiltered (client-reported cross-site leak).
    """
    now = datetime.now(timezone.utc)
    stmt = select(UserSiteRole.site_id).where(
        UserSiteRole.user_id == user_id,
        UserSiteRole.status == "active",
        UserSiteRole.effective_from <= now,
        (UserSiteRole.expires_at.is_(None)) | (UserSiteRole.expires_at > now),
    ).distinct()
    return set((await session.execute(stmt)).scalars().all())


async def resolve_site_scope(
    session: AsyncSession, actor_user_id: uuid.UUID, site_id: uuid.UUID | None, *, action: str
) -> list[uuid.UUID]:
    """Resolve the concrete site(s) a list/read endpoint should filter to for `action`.

    A caller-supplied `site_id` is validated the normal way (the actor must hold `action` there).
    An *omitted* `site_id` must never fall through to `filtered()`/a raw query as `None` -- that
    silently returns every site's rows to anyone holding the permission at any single site. Instead
    it resolves to every site the actor actually holds `action` at (usually one), still fail-closed
    if that set is empty.
    """
    if site_id is not None:
        await evaluate_policy(session, actor_user_id, action=action, site_id=site_id)
        return [site_id]

    allowed: list[uuid.UUID] = []
    for candidate in sorted(await resolve_actor_site_ids(session, actor_user_id)):
        try:
            await evaluate_policy(session, actor_user_id, action=action, site_id=candidate)
        except (RoleMissingError, SodConflictError):
            continue
        allowed.append(candidate)
    if not allowed:
        raise RoleMissingError("Actor holds no role granting this action at any assigned site", action=action)
    return allowed
