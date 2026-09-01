"""Document 86 (SPEC-VAL-008) Mutation Gateway command handlers -- Infrastructure, Cloud, Platform &
Environment Qualification. Document 106 row 152: `infrastructure/{id}/approve` requires an `Approved`
signature from an independent QA Releaser, reason mandatory (binds to the `infrastructure_fingerprint`
row -- the actually-executed check -- not the profile, which is only the declared baseline).
`infrastructure/profiles` carries no Document 106 row -- unsigned.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import InfrastructureFingerprint, InfrastructureQualificationProfile
from app.modules.validation.shared import finalize, receipt_from_existing, resolve_signature, verify_reauth_and_consume
from app.mutation.errors import InvalidTransitionError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_FINGERPRINT = "infrastructure_fingerprint"


class CreateInfrastructureProfileCommand(CommandEnvelope):
    deployment_profile: str
    provider: str
    required_components: list[dict] = []
    control_tests: list[dict] = []
    supplier_evidence_refs: list[dict] = []
    change_triggers: list[str] = []


async def create_infrastructure_profile(
    session: AsyncSession, cmd: CreateInfrastructureProfileCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = InfrastructureQualificationProfile(
        site_id=site_id, deployment_profile=cmd.deployment_profile, provider=cmd.provider,
        required_components=cmd.required_components, control_tests=cmd.control_tests,
        supplier_evidence_refs=cmd.supplier_evidence_refs, change_triggers=cmd.change_triggers,
        state="EFFECTIVE", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="infrastructure_qualification_profile",
        aggregate_id=row.id, version=row.version, action="Created", actor_user_id=actor_user_id, reason=None,
        old_value=None, new_value={"provider": row.provider, "deployment_profile": row.deployment_profile},
        event_type="InfrastructureProfileDefined", expected_version=None,
        command_type="CreateInfrastructureProfile", site_id=site_id,
    )


def _detect_drift(profile: InfrastructureQualificationProfile, captured_versions: dict) -> list[dict]:
    drift = []
    for component in profile.required_components:
        name, expected = component.get("name"), component.get("version")
        actual = captured_versions.get(name)
        if expected and actual is not None and actual != expected:
            drift.append({"component": name, "expected": expected, "actual": actual})
    return drift


class CaptureInfrastructureFingerprintCommand(CommandEnvelope):
    profile_id: uuid.UUID
    captured_versions: dict
    config_hashes: dict = {}
    resource_sizing: dict = {}
    network_security_refs: dict = {}
    time_backup_refs: dict = {}


async def capture_infrastructure_fingerprint(
    session: AsyncSession, cmd: CaptureInfrastructureFingerprintCommand, actor_user_id: uuid.UUID,
    site_id: uuid.UUID | None,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    profile = await session.get(InfrastructureQualificationProfile, cmd.profile_id)
    if profile is None:
        raise NotFoundError("Infrastructure qualification profile not found")

    drift = _detect_drift(profile, cmd.captured_versions)
    row = InfrastructureFingerprint(
        profile_id=profile.id, profile_version=profile.version, captured_versions=cmd.captured_versions,
        config_hashes=cmd.config_hashes, resource_sizing=cmd.resource_sizing,
        network_security_refs=cmd.network_security_refs, time_backup_refs=cmd.time_backup_refs,
        drift_detected=bool(drift), drift_detail=drift, status="CAPTURED", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_FINGERPRINT, aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"profile_id": str(profile.id), "drift_detected": row.drift_detected},
        event_type="InfrastructureFingerprintCaptured", expected_version=None,
        command_type="CaptureInfrastructureFingerprint", site_id=site_id,
    )


class RunInfrastructureControlTestsCommand(CommandEnvelope):
    fingerprint_id: uuid.UUID
    expected_version: int


async def run_infrastructure_control_tests(
    session: AsyncSession, cmd: RunInfrastructureControlTestsCommand, actor_user_id: uuid.UUID,
    site_id: uuid.UUID | None,
) -> MutationReceipt:
    """INFQ-FR-004..016/018/019: re-evaluate a captured fingerprint against its profile's current
    `required_components` -- e.g. after the profile itself changed. Always emits
    `InfrastructureQualificationDifferenceDetected`; an empty `drift_detail` in the payload is itself
    the (negative) result of the evaluation, not the absence of one."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = await session.get(InfrastructureFingerprint, cmd.fingerprint_id)
    if row is None:
        raise NotFoundError("Infrastructure fingerprint not found")
    if row.version != cmd.expected_version:
        raise StaleVersionError("Fingerprint changed since this request was prepared", current_version=row.version)
    profile = await session.get(InfrastructureQualificationProfile, row.profile_id)
    if profile is None:
        raise NotFoundError("Infrastructure qualification profile not found")

    drift = _detect_drift(profile, row.captured_versions)
    row.profile_version = profile.version
    row.drift_detected = bool(drift)
    row.drift_detail = drift
    row.version += 1

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_FINGERPRINT, aggregate_id=row.id,
        version=row.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_value=None, new_value={"drift_detected": row.drift_detected, "drift_detail": drift},
        event_type="InfrastructureQualificationDifferenceDetected", expected_version=cmd.expected_version,
        command_type="RunInfrastructureControlTests", site_id=site_id,
    )


class ApproveInfrastructureFingerprintCommand(CommandEnvelope):
    fingerprint_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_infrastructure_fingerprint(
    session: AsyncSession, cmd: ApproveInfrastructureFingerprintCommand, actor_user_id: uuid.UUID,
    site_id: uuid.UUID | None,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = await session.get(InfrastructureFingerprint, cmd.fingerprint_id)
    if row is None:
        raise NotFoundError("Infrastructure fingerprint not found")
    if row.drift_detected:
        raise InvalidTransitionError("Cannot approve a fingerprint with unresolved drift", drift=row.drift_detail)
    if row.version != cmd.expected_version:
        raise StaleVersionError("Fingerprint changed since this request was prepared", current_version=row.version)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to approve an infrastructure fingerprint")

    policy = await resolve_signature(session, record_type=RECORD_TYPE_FINGERPRINT, action="approve")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.status = "APPROVED"
    row.approved_by_user_id = actor_user_id
    row.approved_at = datetime.now(timezone.utc)
    row.version += 1

    # Document 06 (VLT-FR-001): an approved infrastructure fingerprint is a regulated final record.
    from app.modules.vault import service as vault_service
    await vault_service.release_master(
        session, object_type=RECORD_TYPE_FINGERPRINT, business_id=str(row.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "profile_id": str(row.profile_id), "captured_versions": row.captured_versions,
            "config_hashes": row.config_hashes,
        },
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_FINGERPRINT, aggregate_id=row.id,
        version=row.version, action="Approved", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value={"status": "CAPTURED"}, new_value={"status": "APPROVED"}, event_type="InfrastructureQualified",
        expected_version=cmd.expected_version, command_type="ApproveInfrastructureFingerprint", site_id=site_id,
        signature_id=signature_id,
    )
