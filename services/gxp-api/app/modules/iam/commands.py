import hashlib
import secrets
import uuid
from datetime import datetime, timedelta, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.reference_resolution import build_code_index
from app.core.referential import find_all_blocking_references, find_blocking_reference
from app.core.security import hash_password
from app.modules.iam.models import (
    Organization,
    Permission,
    Role,
    RolePermission,
    Site,
    User,
    UserInvite,
    UserSiteRole,
)
from app.modules.security import identity_commands as security_identity_commands
from app.modules.security import privileged_access_commands as security_privileged_access_commands
from app.mutation.errors import NotFoundError, ValidationFailedError
from app.mutation.gateway import (
    check_idempotency,
    record_command_receipt,
    write_audit_event,
    write_outbox_event,
)
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


# ---------------------------------------------------------------------------
# CreateUser — not site-scoped (User has no site_id; site scope comes from
# UserSiteRole assignment), so no signature required (not in the Document 106 floor).
# ---------------------------------------------------------------------------


class CreateUserCommand(CommandEnvelope):
    username: str
    email: str
    full_name: str
    password: str


async def create_user(
    session: AsyncSession, cmd: CreateUserCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    existing_user = (
        await session.execute(select(User).where(User.username == cmd.username))
    ).scalar_one_or_none()
    if existing_user is not None:
        raise ValidationFailedError("A user with this username already exists", username=cmd.username)

    user = User(
        username=cmd.username,
        email=cmd.email,
        full_name=cmd.full_name,
        password_hash=hash_password(cmd.password),
        status="active",
    )
    session.add(user)
    await session.flush()

    correlation_id = uuid.uuid4()
    # new_value never carries the password or its hash (security rule: secrets never in audit/logs).
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="user",
        aggregate_id=user.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "status": user.status,
        },
    )
    await write_outbox_event(
        session,
        event_type="UserCreated",
        aggregate_type="user",
        aggregate_id=user.id,
        aggregate_version=1,
        payload={"id": str(user.id), "username": user.username},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="CreateUser",
        aggregate_type="user",
        aggregate_id=user.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=user.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CreateRole
# ---------------------------------------------------------------------------


class CreateRoleCommand(CommandEnvelope):
    name: str
    description: str | None = None


async def create_role(
    session: AsyncSession, cmd: CreateRoleCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    existing_role = (
        await session.execute(select(Role).where(Role.name == cmd.name))
    ).scalar_one_or_none()
    if existing_role is not None:
        raise ValidationFailedError("A role with this name already exists", name=cmd.name)

    role = Role(name=cmd.name, description=cmd.description)
    session.add(role)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="role",
        aggregate_id=role.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"name": role.name, "description": role.description},
    )
    await write_outbox_event(
        session,
        event_type="RoleCreated",
        aggregate_type="role",
        aggregate_id=role.id,
        aggregate_version=1,
        payload={"id": str(role.id), "name": role.name},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="CreateRole",
        aggregate_type="role",
        aggregate_id=role.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=role.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# AssignUserRole — site-scoped (UserSiteRole), unlike the two commands above.
# ---------------------------------------------------------------------------


class AssignUserRoleCommand(CommandEnvelope):
    user_id: uuid.UUID
    site_id: uuid.UUID
    role_id: uuid.UUID
    # Additive (Client gap-analysis Phase 1, 2026-10-05): bulk-imported rows may carry their own
    # effective/expiry dates (Document 07 iam_role_assignment is already time-bounded -- UserSiteRole
    # already has both columns; no existing caller passes them, so both default to the column's own
    # existing default/None behavior and every pre-existing call site is unaffected.
    effective_from: datetime | None = None
    expires_at: datetime | None = None


async def assign_user_role(
    session: AsyncSession, cmd: AssignUserRoleCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    user = await session.get(User, cmd.user_id)
    if user is None:
        raise NotFoundError("User not found")
    role = await session.get(Role, cmd.role_id)
    if role is None:
        raise NotFoundError("Role not found")

    existing_assignment = (
        await session.execute(
            select(UserSiteRole).where(
                UserSiteRole.user_id == cmd.user_id,
                UserSiteRole.site_id == cmd.site_id,
                UserSiteRole.role_id == cmd.role_id,
            )
        )
    ).scalar_one_or_none()
    if existing_assignment is not None:
        raise ValidationFailedError("This user already holds this role at this site")

    assignment = UserSiteRole(user_id=cmd.user_id, site_id=cmd.site_id, role_id=cmd.role_id)
    if cmd.effective_from is not None:
        assignment.effective_from = cmd.effective_from
    if cmd.expires_at is not None:
        assignment.expires_at = cmd.expires_at
    session.add(assignment)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=cmd.site_id,
        aggregate_type="user_site_role",
        aggregate_id=assignment.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={
            "user_id": str(cmd.user_id),
            "site_id": str(cmd.site_id),
            "role_id": str(cmd.role_id),
            "role_name": role.name,
        },
    )
    await write_outbox_event(
        session,
        event_type="UserRoleAssigned",
        aggregate_type="user_site_role",
        aggregate_id=assignment.id,
        aggregate_version=1,
        payload={"user_id": str(cmd.user_id), "site_id": str(cmd.site_id), "role_id": str(cmd.role_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=cmd.site_id,
        command_type="AssignUserRole",
        aggregate_type="user_site_role",
        aggregate_id=assignment.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=assignment.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# UpdateOrganization — single-tenant (ADR-0006): there is exactly one row, edited in place, never
# created or deleted through this API.
# ---------------------------------------------------------------------------


class UpdateOrganizationCommand(CommandEnvelope):
    name: str


async def update_organization(
    session: AsyncSession, cmd: UpdateOrganizationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    org = (await session.execute(select(Organization).limit(1))).scalar_one_or_none()
    if org is None:
        raise NotFoundError("No organization exists yet")
    old_name = org.name
    org.name = cmd.name

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="organization",
        aggregate_id=org.id,
        aggregate_version=1,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"name": old_name},
        new_value={"name": org.name},
    )
    await write_outbox_event(
        session,
        event_type="OrganizationChanged",
        aggregate_type="organization",
        aggregate_id=org.id,
        aggregate_version=1,
        payload={"id": str(org.id), "name": org.name},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="UpdateOrganization",
        aggregate_type="organization",
        aggregate_id=org.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=org.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# DismissOnboarding — single-tenant (ADR-0006), same shape as UpdateOrganization above. The onboarding
# wizard's four step statuses (Company/Sites/Users/Roles) are derived read-only from audit_events
# (see GET /onboarding in router.py) and never written here; this command only records the one thing
# that isn't derivable -- the admin chose to skip the wizard.
# ---------------------------------------------------------------------------


class DismissOnboardingCommand(CommandEnvelope):
    pass


async def dismiss_onboarding(
    session: AsyncSession, cmd: DismissOnboardingCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    org = (await session.execute(select(Organization).limit(1))).scalar_one_or_none()
    if org is None:
        raise NotFoundError("No organization exists yet")
    org.onboarding_dismissed_at = datetime.now(timezone.utc)

    correlation_id = uuid.uuid4()
    # Deliberately NOT action="Changed" on aggregate_type="organization" -- GET /onboarding's
    # "company_done" status is derived from exactly that (aggregate_type, action) pair (from
    # update_organization above), and reusing it here would spuriously mark the Company step done the
    # moment the wizard is skipped, before the admin has actually touched the company record.
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="organization",
        aggregate_id=org.id,
        aggregate_version=1,
        action="OnboardingDismissed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"onboarding_dismissed_at": org.onboarding_dismissed_at.isoformat()},
    )
    await write_outbox_event(
        session,
        event_type="OnboardingDismissed",
        aggregate_type="organization",
        aggregate_id=org.id,
        aggregate_version=1,
        payload={"id": str(org.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="DismissOnboarding",
        aggregate_type="organization",
        aggregate_id=org.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=org.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Site
# ---------------------------------------------------------------------------


class CreateSiteCommand(CommandEnvelope):
    code: str
    name: str


async def create_site(
    session: AsyncSession, cmd: CreateSiteCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    org = (await session.execute(select(Organization).limit(1))).scalar_one_or_none()
    if org is None:
        raise NotFoundError("No organization exists yet")

    existing_site = (await session.execute(select(Site).where(Site.code == cmd.code))).scalar_one_or_none()
    if existing_site is not None:
        raise ValidationFailedError("A site with this code already exists", code=cmd.code)

    site = Site(organization_id=org.id, code=cmd.code, name=cmd.name)
    session.add(site)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site.id,
        aggregate_type="site",
        aggregate_id=site.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"code": site.code, "name": site.name},
    )
    await write_outbox_event(
        session,
        event_type="SiteCreated",
        aggregate_type="site",
        aggregate_id=site.id,
        aggregate_version=1,
        payload={"id": str(site.id), "code": site.code},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site.id,
        command_type="CreateSite",
        aggregate_type="site",
        aggregate_id=site.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=site.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


class UpdateSiteCommand(CommandEnvelope):
    site_id: uuid.UUID
    code: str
    name: str


async def update_site(
    session: AsyncSession, cmd: UpdateSiteCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    site = await session.get(Site, cmd.site_id)
    if site is None:
        raise NotFoundError("Site not found")
    if cmd.code != site.code:
        conflict = (await session.execute(select(Site).where(Site.code == cmd.code))).scalar_one_or_none()
        if conflict is not None:
            raise ValidationFailedError("A site with this code already exists", code=cmd.code)

    old_value = {"code": site.code, "name": site.name}
    site.code = cmd.code
    site.name = cmd.name

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site.id,
        aggregate_type="site",
        aggregate_id=site.id,
        aggregate_version=1,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value=old_value,
        new_value={"code": site.code, "name": site.name},
    )
    await write_outbox_event(
        session,
        event_type="SiteChanged",
        aggregate_type="site",
        aggregate_id=site.id,
        aggregate_version=1,
        payload={"id": str(site.id), "code": site.code},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site.id,
        command_type="UpdateSite",
        aggregate_type="site",
        aggregate_id=site.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=site.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


class DeleteSiteCommand(CommandEnvelope):
    site_id: uuid.UUID


async def delete_site(
    session: AsyncSession, cmd: DeleteSiteCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    site = await session.get(Site, cmd.site_id)
    if site is None:
        raise NotFoundError("Site not found")

    # Schema-driven, not a hand-maintained model list (`iam.sites` has 112 FK columns across every
    # module in the platform as of 2026-09-08 — see `find_all_blocking_references()`'s own docstring).
    # A hand-maintained list here previously checked only 6 of those 112 tables; a site with real data
    # in any of the other 106 (equipment, DDCP, QMS, machine_integration, postmarket, ...) would pass
    # this guard and then fail as a raw, unhandled FK-violation 500 at the `session.delete(site)` below
    # instead of the clean error this function exists to produce.
    blockers = await find_all_blocking_references(session, "iam", "sites", site.id)
    if blockers:
        raise ValidationFailedError(f"Cannot delete site: referenced by {', '.join(blockers)}")

    old_value = {"code": site.code, "name": site.name}
    site_id = site.id
    await session.delete(site)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=site_id,
        aggregate_type="site",
        aggregate_id=site_id,
        aggregate_version=1,
        action="Deleted",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value=old_value,
    )
    await write_outbox_event(
        session,
        event_type="SiteDeleted",
        aggregate_type="site",
        aggregate_id=site_id,
        aggregate_version=1,
        payload={"id": str(site_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=site_id,
        command_type="DeleteSite",
        aggregate_type="site",
        aggregate_id=site_id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=site_id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# UpdateRole / DeleteRole
# ---------------------------------------------------------------------------


class UpdateRoleCommand(CommandEnvelope):
    role_id: uuid.UUID
    name: str
    description: str | None = None


async def update_role(
    session: AsyncSession, cmd: UpdateRoleCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    role = await session.get(Role, cmd.role_id)
    if role is None:
        raise NotFoundError("Role not found")
    # Admin is the one role this deployment defines, not a customer -- every other role is data a
    # customer creates/renames/deletes freely via /admin/roles. Renaming or redescribing it would break
    # every isAdminAnywhere()/"Admin" break-glass check across the app (frontend and backend alike), so
    # it is the sole role name still allowed to be hardcoded anywhere in this codebase -- and the sole
    # role this endpoint refuses to touch (2026-09-18, project-owner-directed).
    if role.name == "Admin":
        raise ValidationFailedError("The Admin role is the system's default role and cannot be edited")
    if cmd.name != role.name:
        conflict = (await session.execute(select(Role).where(Role.name == cmd.name))).scalar_one_or_none()
        if conflict is not None:
            raise ValidationFailedError("A role with this name already exists", name=cmd.name)

    old_value = {"name": role.name, "description": role.description}
    role.name = cmd.name
    role.description = cmd.description

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="role",
        aggregate_id=role.id,
        aggregate_version=1,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value=old_value,
        new_value={"name": role.name, "description": role.description},
    )
    await write_outbox_event(
        session,
        event_type="RoleChanged",
        aggregate_type="role",
        aggregate_id=role.id,
        aggregate_version=1,
        payload={"id": str(role.id), "name": role.name},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="UpdateRole",
        aggregate_type="role",
        aggregate_id=role.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=role.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


class DeleteRoleCommand(CommandEnvelope):
    role_id: uuid.UUID


async def delete_role(
    session: AsyncSession, cmd: DeleteRoleCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    role = await session.get(Role, cmd.role_id)
    if role is None:
        raise NotFoundError("Role not found")
    # Same Admin protection as update_role above -- deleting it would strand the system with no
    # break-glass superuser at all, and every "user assignment" blocker below would only catch this if
    # someone had already unassigned every Admin-role user first.
    if role.name == "Admin":
        raise ValidationFailedError("The Admin role is the system's default role and cannot be deleted")

    from app.modules.iam.models import SodRule
    from app.modules.signature.models import SignaturePolicy

    blocker = await find_blocking_reference(
        session,
        [
            (UserSiteRole, UserSiteRole.role_id, role.id, "user assignment"),
            (SodRule, SodRule.role_a, role.name, "SoD rule"),
            (SodRule, SodRule.role_b, role.name, "SoD rule"),
            (SignaturePolicy, SignaturePolicy.required_role_id, role.id, "signature policy"),
        ],
    )
    if blocker is not None:
        raise ValidationFailedError(f"Cannot delete role: referenced by {blocker}")

    old_value = {"name": role.name, "description": role.description}
    role_id = role.id

    # Role permission assignments carry no meaning once the role itself is gone — cascade-clear them
    # before the role delete (no ORM relationship links them, so this must be explicit, same as the
    # recipe/recipe_step pattern in recipe/commands.py).
    role_permission_rows = (
        await session.execute(select(RolePermission).where(RolePermission.role_id == role.id))
    ).scalars().all()
    for rp in role_permission_rows:
        await session.delete(rp)
    await session.flush()

    await session.delete(role)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="role",
        aggregate_id=role_id,
        aggregate_version=1,
        action="Deleted",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value=old_value,
    )
    await write_outbox_event(
        session,
        event_type="RoleDeleted",
        aggregate_type="role",
        aggregate_id=role_id,
        aggregate_version=1,
        payload={"id": str(role_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="DeleteRole",
        aggregate_type="role",
        aggregate_id=role_id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=role_id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# UpdateUser / Deactivate / Reactivate — no delete (see plan Context: a user is an audit-trail actor,
# not disposable master data; deactivation blocks login while preserving every historical reference).
# ---------------------------------------------------------------------------


class UpdateUserCommand(CommandEnvelope):
    user_id: uuid.UUID
    email: str
    full_name: str


async def update_user(
    session: AsyncSession, cmd: UpdateUserCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    user = await session.get(User, cmd.user_id)
    if user is None:
        raise NotFoundError("User not found")

    old_value = {"email": user.email, "full_name": user.full_name}
    user.email = cmd.email
    user.full_name = cmd.full_name

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="user",
        aggregate_id=user.id,
        aggregate_version=1,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value=old_value,
        new_value={"email": user.email, "full_name": user.full_name},
    )
    await write_outbox_event(
        session,
        event_type="UserChanged",
        aggregate_type="user",
        aggregate_id=user.id,
        aggregate_version=1,
        payload={"id": str(user.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="UpdateUser",
        aggregate_type="user",
        aggregate_id=user.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=user.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


class SetUserStatusCommand(CommandEnvelope):
    user_id: uuid.UUID


async def _set_user_status(
    session: AsyncSession, cmd: SetUserStatusCommand, actor_user_id: uuid.UUID, *, new_status: str, command_type: str
) -> MutationReceipt:
    payload_hash = sha256_hex({**cmd.model_dump(mode="json"), "command_type": command_type})
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    user = await session.get(User, cmd.user_id)
    if user is None:
        raise NotFoundError("User not found")

    old_status = user.status
    user.status = new_status

    # Document 62 (SPEC-SEC-002) IAMSEC-FR-010/013: disabling a user immediately revokes any active
    # application sessions in the same transaction, rather than only blocking future logins.
    if new_status == "disabled":
        await security_identity_commands.revoke_user_sessions(
            session,
            security_identity_commands.RevokeUserSessionsCommand(
                idempotency_key=f"{cmd.idempotency_key}:revoke-sessions", subject_id=user.id,
                reason="User deactivated (IAMSEC-FR-010/013)",
            ),
            actor_user_id,
        )
        # Document 63 (SPEC-SEC-003) PAM-FR-025: offboarding also revokes active JIT/break-glass grants,
        # not only application sessions.
        await security_privileged_access_commands.revoke_active_grants_for_subject(
            session, subject_id=user.id, reason="User deactivated (PAM-FR-025)",
        )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="user",
        aggregate_id=user.id,
        aggregate_version=1,
        action="StatusChanged",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"status": old_status},
        new_value={"status": user.status},
    )
    await write_outbox_event(
        session,
        event_type="UserStatusChanged",
        aggregate_type="user",
        aggregate_id=user.id,
        aggregate_version=1,
        payload={"id": str(user.id), "status": user.status},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type=command_type,
        aggregate_type="user",
        aggregate_id=user.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=user.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


async def deactivate_user(
    session: AsyncSession, cmd: SetUserStatusCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    return await _set_user_status(
        session, cmd, actor_user_id, new_status="disabled", command_type="DeactivateUser"
    )


async def reactivate_user(
    session: AsyncSession, cmd: SetUserStatusCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    return await _set_user_status(
        session, cmd, actor_user_id, new_status="active", command_type="ReactivateUser"
    )


# ---------------------------------------------------------------------------
# SetRolePermissions — bulk replace-semantics assignment (IAM-FR-006): the table "assign permissions
# to a role" means, exposed as one idempotent set operation rather than incremental add/remove.
# ---------------------------------------------------------------------------


class SetRolePermissionsCommand(CommandEnvelope):
    role_id: uuid.UUID
    permission_ids: list[uuid.UUID]


async def set_role_permissions(
    session: AsyncSession, cmd: SetRolePermissionsCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    role = await session.get(Role, cmd.role_id)
    if role is None:
        raise NotFoundError("Role not found")
    # Same Admin protection as update_role/delete_role above -- stripping Admin's own grants through
    # this UI could lock every operator out of the one role that can re-grant anything (no other role
    # holds platform.administer), so its permission set stays fixed (scripts/seed.py ROLE_PERMISSIONS,
    # re-applied by scripts/sync_permissions.py) rather than editable here.
    if role.name == "Admin":
        raise ValidationFailedError("The Admin role's permissions are fixed and cannot be changed here")

    requested_ids = set(cmd.permission_ids)
    if requested_ids:
        found = (
            await session.execute(select(Permission.id).where(Permission.id.in_(requested_ids)))
        ).scalars().all()
        missing = requested_ids - set(found)
        if missing:
            raise ValidationFailedError(
                "Unknown permission id(s)", permission_ids=[str(p) for p in missing]
            )

    existing_rows = (
        await session.execute(
            select(RolePermission, Permission.code)
            .join(Permission, Permission.id == RolePermission.permission_id)
            .where(RolePermission.role_id == role.id)
        )
    ).all()
    old_codes = sorted(code for _row, code in existing_rows)
    for row, _code in existing_rows:
        await session.delete(row)
    await session.flush()

    for permission_id in requested_ids:
        session.add(RolePermission(role_id=role.id, permission_id=permission_id))
    await session.flush()

    new_codes = sorted(
        (
            await session.execute(select(Permission.code).where(Permission.id.in_(requested_ids)))
        ).scalars().all()
    )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="role",
        aggregate_id=role.id,
        aggregate_version=1,
        action="PermissionsChanged",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"permissions": old_codes},
        new_value={"permissions": new_codes},
    )
    await write_outbox_event(
        session,
        event_type="RolePermissionsChanged",
        aggregate_type="role",
        aggregate_id=role.id,
        aggregate_version=1,
        payload={"id": str(role.id), "permissions": new_codes},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="SetRolePermissions",
        aggregate_type="role",
        aggregate_id=role.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=role.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# InviteUser / AcceptInvite / BulkImportUsers — client gap-analysis Phase 1 (2026-10-05): bulk
# onboarding. A user created this way has no password yet (status="pending_activation") and activates
# their own account via a single-use, time-limited token (iam.UserInvite) emailed to them -- see
# app/core/email.py. Deliberately separate from create_user (which always requires an admin-supplied
# password and status="active") rather than overloading that command's contract.
# ---------------------------------------------------------------------------


class InviteUserCommand(CommandEnvelope):
    username: str
    email: str
    full_name: str


class InviteUserResult(MutationReceipt):
    """`raw_invite_token` is returned exactly once, to the caller only -- it must be used solely to build
    the accept-invite email and must never be logged, persisted anywhere else, or included in any HTTP
    response (CTR-FR-018). Only `UserInvite.token_hash` is ever stored."""

    user_id: uuid.UUID
    email: str
    full_name: str
    raw_invite_token: str


async def invite_user(
    session: AsyncSession, cmd: InviteUserCommand, actor_user_id: uuid.UUID
) -> InviteUserResult:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        # A replay cannot re-mint a usable raw token (only its hash was ever stored) -- this is a safe
        # no-op response for the (expected to be rare, since each row mints a fresh key) case of a direct
        # duplicate call, not the normal bulk-import path.
        return InviteUserResult(
            command_id=existing_receipt.id,
            aggregate_id=existing_receipt.aggregate_id,
            resulting_version=existing_receipt.resulting_version,
            audit_event_id=existing_receipt.id,
            correlation_id=existing_receipt.id,
            user_id=existing_receipt.aggregate_id,
            email=cmd.email,
            full_name=cmd.full_name,
            raw_invite_token="",
        )

    existing_user = (
        await session.execute(select(User).where(User.username == cmd.username))
    ).scalar_one_or_none()
    if existing_user is not None:
        raise ValidationFailedError("A user with this username already exists", username=cmd.username)

    # password_hash is NOT NULL and no real password exists yet -- a random, never-communicated
    # placeholder makes login impossible until accept_invite() overwrites it.
    placeholder_password = secrets.token_urlsafe(32)
    user = User(
        username=cmd.username,
        email=cmd.email,
        full_name=cmd.full_name,
        password_hash=hash_password(placeholder_password),
        status="pending_activation",
    )
    session.add(user)
    await session.flush()

    raw_token = secrets.token_urlsafe(32)
    invite = UserInvite(
        user_id=user.id,
        token_hash=hashlib.sha256(raw_token.encode("utf-8")).hexdigest(),
        expires_at=datetime.now(timezone.utc) + timedelta(hours=settings.invite_token_expire_hours),
        created_by_user_id=actor_user_id,
    )
    session.add(invite)
    await session.flush()

    correlation_id = uuid.uuid4()
    # new_value never carries the placeholder password, its hash, or the raw invite token (secrets never
    # in audit/logs -- same rule create_user's own comment states).
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="user",
        aggregate_id=user.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "status": user.status,
        },
    )
    await write_outbox_event(
        session,
        event_type="UserInvited",
        aggregate_type="user",
        aggregate_id=user.id,
        aggregate_version=1,
        payload={"id": str(user.id), "username": user.username},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="InviteUser",
        aggregate_type="user",
        aggregate_id=user.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return InviteUserResult(
        command_id=receipt.id,
        aggregate_id=user.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
        user_id=user.id,
        email=user.email,
        full_name=user.full_name,
        raw_invite_token=raw_token,
    )


class AcceptInviteCommand(CommandEnvelope):
    token: str
    password: str


async def accept_invite(session: AsyncSession, cmd: AcceptInviteCommand) -> MutationReceipt:
    """Unauthenticated by design (there is no actor to authenticate yet) -- the single-use token itself
    is the proof of authority, same role `SignatureChallenge`'s nonce plays elsewhere in this codebase.
    The user being activated is the actor of record for audit purposes (they are the one taking the
    action), matching how a self-service action is always attributed to its own subject."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        return _receipt_from_existing(existing_receipt)

    token_hash = hashlib.sha256(cmd.token.encode("utf-8")).hexdigest()
    invite = (
        await session.execute(select(UserInvite).where(UserInvite.token_hash == token_hash))
    ).scalar_one_or_none()
    if invite is None or invite.consumed_at is not None:
        raise ValidationFailedError("This invite link is invalid or has already been used")
    expires_at = invite.expires_at
    if expires_at.tzinfo is None:
        expires_at = expires_at.replace(tzinfo=timezone.utc)
    if datetime.now(timezone.utc) > expires_at:
        raise ValidationFailedError("This invite link has expired")

    user = await session.get(User, invite.user_id)
    if user is None:
        raise NotFoundError("User not found")

    old_status = user.status
    user.password_hash = hash_password(cmd.password)
    user.status = "active"
    invite.consumed_at = datetime.now(timezone.utc)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="user",
        aggregate_id=user.id,
        aggregate_version=1,
        action="StatusChanged",
        actor_id=user.id,
        correlation_id=correlation_id,
        old_value={"status": old_status},
        new_value={"status": user.status},
    )
    await write_outbox_event(
        session,
        event_type="UserActivated",
        aggregate_type="user",
        aggregate_id=user.id,
        aggregate_version=1,
        payload={"id": str(user.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="AcceptInvite",
        aggregate_type="user",
        aggregate_id=user.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=user.id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=user.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# BulkImportUsers — validate-then-commit, all-or-nothing per batch (no partial imports: either every row
# is valid and every user+role-assignment is created in one transaction, or nothing is).
# ---------------------------------------------------------------------------


class BulkImportUserRow(BaseModel):
    full_name: str
    email: str
    role_name: str
    site_code: str
    effective_from: datetime | None = None
    expires_at: datetime | None = None


class BulkImportRowValidation(BaseModel):
    row_index: int
    email: str
    ok: bool
    error: str | None = None


async def validate_bulk_import_rows(
    session: AsyncSession, rows: list[BulkImportUserRow]
) -> list[BulkImportRowValidation]:
    """Read-only. Used by both the preview endpoint and (defense in depth) bulk_import_users itself right
    before committing, since rows can go stale between a client's preview call and its commit call (a
    referenced role/site could be deleted meanwhile, or two previews could race on the same email)."""
    results: list[BulkImportRowValidation] = []
    seen_emails: set[str] = set()
    role_names = set(build_code_index((await session.execute(select(Role))).scalars().all(), "name"))
    site_codes = set(build_code_index((await session.execute(select(Site))).scalars().all(), "code"))
    candidate_emails = {row.email for row in rows}
    existing_usernames = (
        {
            u
            for u in (
                await session.execute(select(User.username).where(User.username.in_(candidate_emails)))
            ).scalars().all()
        }
        if candidate_emails
        else set()
    )

    for idx, row in enumerate(rows):
        email_lower = row.email.strip().lower()
        if not row.full_name.strip():
            results.append(
                BulkImportRowValidation(row_index=idx, email=row.email, ok=False, error="full_name is required")
            )
            continue
        if "@" not in row.email or not row.email.strip():
            results.append(
                BulkImportRowValidation(row_index=idx, email=row.email, ok=False, error="email looks invalid")
            )
            continue
        if email_lower in seen_emails:
            results.append(
                BulkImportRowValidation(
                    row_index=idx, email=row.email, ok=False, error="duplicate email within this import"
                )
            )
            continue
        seen_emails.add(email_lower)
        if row.email in existing_usernames:
            results.append(
                BulkImportRowValidation(
                    row_index=idx, email=row.email, ok=False, error="a user with this email already exists"
                )
            )
            continue
        if row.role_name not in role_names:
            results.append(
                BulkImportRowValidation(
                    row_index=idx, email=row.email, ok=False, error=f"unknown role '{row.role_name}'"
                )
            )
            continue
        if row.site_code not in site_codes:
            results.append(
                BulkImportRowValidation(
                    row_index=idx, email=row.email, ok=False, error=f"unknown site '{row.site_code}'"
                )
            )
            continue
        results.append(BulkImportRowValidation(row_index=idx, email=row.email, ok=True))
    return results


class BulkImportUsersCommand(CommandEnvelope):
    rows: list[BulkImportUserRow]


class BulkImportedUser(BaseModel):
    row_index: int
    user_id: uuid.UUID
    email: str
    full_name: str
    raw_invite_token: str


class BulkImportUsersResult(BaseModel):
    command_id: uuid.UUID
    correlation_id: uuid.UUID
    created: list[BulkImportedUser]


async def bulk_import_users(
    session: AsyncSession, cmd: BulkImportUsersCommand, actor_user_id: uuid.UUID
) -> BulkImportUsersResult:
    if not cmd.rows:
        raise ValidationFailedError("No rows to import")

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing_receipt = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing_receipt is not None:
        # Batch already committed under this key -- raw tokens were never persisted, so there is nothing
        # left to email; the original emails were already sent at the original commit.
        return BulkImportUsersResult(command_id=existing_receipt.id, correlation_id=existing_receipt.id, created=[])

    validations = await validate_bulk_import_rows(session, cmd.rows)
    errors = [v for v in validations if not v.ok]
    if errors:
        raise ValidationFailedError(
            "One or more rows failed validation -- no users were created",
            errors=[{"row_index": e.row_index, "email": e.email, "error": e.error} for e in errors],
        )

    role_by_name = build_code_index((await session.execute(select(Role))).scalars().all(), "name")
    site_by_code = build_code_index((await session.execute(select(Site))).scalars().all(), "code")

    correlation_id = uuid.uuid4()
    created: list[BulkImportedUser] = []
    for idx, row in enumerate(cmd.rows):
        invite_result = await invite_user(
            session,
            InviteUserCommand(
                idempotency_key=f"{cmd.idempotency_key}:row-{idx}",
                username=row.email,
                email=row.email,
                full_name=row.full_name,
            ),
            actor_user_id,
        )
        role = role_by_name[row.role_name]
        site = site_by_code[row.site_code]
        await assign_user_role(
            session,
            AssignUserRoleCommand(
                idempotency_key=f"{cmd.idempotency_key}:row-{idx}:role",
                user_id=invite_result.user_id,
                site_id=site.id,
                role_id=role.id,
                effective_from=row.effective_from,
                expires_at=row.expires_at,
            ),
            actor_user_id,
        )
        created.append(
            BulkImportedUser(
                row_index=idx,
                user_id=invite_result.user_id,
                email=invite_result.email,
                full_name=invite_result.full_name,
                raw_invite_token=invite_result.raw_invite_token,
            )
        )

    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="BulkImportUsers",
        aggregate_type="user_bulk_import",
        aggregate_id=uuid.uuid4(),
        expected_version=None,
        resulting_version=len(created),
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return BulkImportUsersResult(command_id=receipt.id, correlation_id=correlation_id, created=created)
