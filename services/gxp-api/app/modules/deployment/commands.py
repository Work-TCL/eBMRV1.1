"""Document 77 (SPEC-DATA-009) Mutation Gateway command handlers. No signature (Document 106 has no
SPEC-DATA-009 row). **No HTTP router** -- 0 owned APIs; CI/installer tooling calls these directly.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.deployment.models import CLOUD_PROVIDERS, ENVIRONMENTS, HA_PROFILES, DeploymentProfile
from app.mutation.errors import StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version, audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _finalize(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, aggregate_id: uuid.UUID,
    version: int, action: str, actor_user_id: uuid.UUID, reason: str | None, old_value: dict | None,
    new_value: dict, event_type: str, expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="deployment_profile", aggregate_id=aggregate_id,
        aggregate_version=version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value=old_value, new_value=new_value,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="deployment_profile", aggregate_id=aggregate_id,
        aggregate_version=version, payload=new_value, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type=command_type, aggregate_type="deployment_profile",
        aggregate_id=aggregate_id, expected_version=expected_version, resulting_version=version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=aggregate_id, resulting_version=version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


class RegisterDeploymentProfileCommand(CommandEnvelope):
    profile_name: str
    environment: str
    cloud_provider: str
    region: str | None = None
    k8s_namespace: str | None = None
    image_digest: str | None = None
    iac_state_ref: str | None = None
    ha_profile: str = "HA"
    expected_version: int | None = None
    reason: str


async def register_deployment_profile(
    session: AsyncSession, cmd: RegisterDeploymentProfileCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """`renderInfrastructurePlan()`/`applyInfrastructurePlan()`'s recorded outcome -- DEP-FR-004/005/006.
    Actually rendering/applying Terraform/Helm is deployment tooling this codebase does not run; this
    command is the durable record of what profile is currently declared/applied."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.environment not in ENVIRONMENTS:
        raise ValidationFailedError(f"environment must be one of {ENVIRONMENTS}")
    if cmd.cloud_provider not in CLOUD_PROVIDERS:
        raise ValidationFailedError(f"cloud_provider must be one of {CLOUD_PROVIDERS}")
    if cmd.ha_profile not in HA_PROFILES:
        raise ValidationFailedError(f"ha_profile must be one of {HA_PROFILES}")
    if not cmd.profile_name or not cmd.reason:
        raise ValidationFailedError("profile_name and reason are required")

    row = (
        await session.execute(select(DeploymentProfile).where(DeploymentProfile.profile_name == cmd.profile_name))
    ).scalar_one_or_none()
    created = row is None
    old_value = None
    if created:
        row = DeploymentProfile(
            profile_name=cmd.profile_name, environment=cmd.environment, cloud_provider=cmd.cloud_provider,
            region=cmd.region, k8s_namespace=cmd.k8s_namespace, image_digest=cmd.image_digest,
            iac_state_ref=cmd.iac_state_ref, ha_profile=cmd.ha_profile, state="EFFECTIVE", version=1,
        )
        session.add(row)
    else:
        if cmd.expected_version is None or row.version != cmd.expected_version:
            raise StaleVersionError("Deployment profile changed since this request was prepared", current_version=row.version)
        old_value = {"image_digest": row.image_digest, "iac_state_ref": row.iac_state_ref}
        row.environment = cmd.environment
        row.cloud_provider = cmd.cloud_provider
        row.region = cmd.region
        row.k8s_namespace = cmd.k8s_namespace
        row.image_digest = cmd.image_digest
        row.iac_state_ref = cmd.iac_state_ref
        row.ha_profile = cmd.ha_profile
        row.version += 1
    await session.flush()

    new_value = {"profile_name": row.profile_name, "environment": row.environment,
                 "cloud_provider": row.cloud_provider, "image_digest": row.image_digest, "ha_profile": row.ha_profile}
    return await _finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=row.id, version=row.version,
        action="Created" if created else "Changed", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value=old_value, new_value=new_value, event_type="InfrastructureApplied",
        expected_version=None if created else cmd.expected_version, command_type="RegisterDeploymentProfile",
    )


class RecordPlatformUpgradeCommand(CommandEnvelope):
    profile_name: str
    expected_version: int
    from_image_digest: str | None
    to_image_digest: str
    migration_from_revision: str
    migration_to_revision: str
    reason: str


async def record_platform_upgrade(
    session: AsyncSession, cmd: RecordPlatformUpgradeCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """`performRollingUpgrade()` -- DEP-FR-025/026/030. Records the upgrade outcome (migration
    revision before/after, image digest before/after); the actual rollout is a deployment-pipeline
    concern this codebase does not execute."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    row = (
        await session.execute(select(DeploymentProfile).where(DeploymentProfile.profile_name == cmd.profile_name))
    ).scalar_one_or_none()
    if row is None:
        raise ValidationFailedError("Unknown deployment profile; register it before recording an upgrade")
    if row.version != cmd.expected_version:
        raise StaleVersionError("Deployment profile changed since this request was prepared", current_version=row.version)
    if not cmd.migration_from_revision or not cmd.migration_to_revision:
        raise ValidationFailedError("migration_from_revision and migration_to_revision are required (DEP-FR-026)")

    old_value = {"image_digest": row.image_digest}
    row.image_digest = cmd.to_image_digest
    row.version += 1
    await session.flush()

    new_value = {
        "profile_name": row.profile_name, "from_image_digest": cmd.from_image_digest,
        "to_image_digest": cmd.to_image_digest, "migration_from_revision": cmd.migration_from_revision,
        "migration_to_revision": cmd.migration_to_revision,
    }
    return await _finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=row.id, version=row.version,
        action="Changed", actor_user_id=actor_user_id, reason=cmd.reason, old_value=old_value,
        new_value=new_value, event_type="PlatformUpgraded", expected_version=cmd.expected_version,
        command_type="RecordPlatformUpgrade",
    )
