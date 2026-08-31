import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.referential import find_blocking_reference
from app.core.security import hash_password
from app.modules.batch.models import Batch
from app.modules.iam.models import Organization, Permission, Role, RolePermission, Site, User, UserSiteRole
from app.modules.material.models import Material, MaterialLot
from app.modules.product.models import Product
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

    blocker = await find_blocking_reference(
        session,
        [
            (Product, Product.site_id, site.id, "product"),
            (Material, Material.site_id, site.id, "material"),
            (MaterialLot, MaterialLot.site_id, site.id, "material lot"),
            (Batch, Batch.site_id, site.id, "batch"),
            (UserSiteRole, UserSiteRole.site_id, site.id, "role assignment"),
        ],
    )
    if blocker is not None:
        raise ValidationFailedError(f"Cannot delete site: referenced by {blocker}")

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
