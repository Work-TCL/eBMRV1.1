"""Document 89 (SPEC-VAL-011) Mutation Gateway command handlers -- Audit Trail, Record Version Vault &
Data Integrity Validation. Document 106 row 155: `data-integrity/{id}/approve` requires an `Approved`
signature from an independent QA Releaser, reason mandatory -- binds to the `data_integrity_test_profile`
(the overall qualification verdict for one data class), aggregating every test execution against it.
`data-integrity/suites` carries no Document 106 row -- unsigned.

Document 79's API list gives one write operation (`data-integrity/tamper-tests`) for three declared
event types (`AuditTamperTestCompleted`, `VaultCanonicalizationVerified`, `ArchiveRetrievalVerified`) --
the profile's `tamper_action` field selects which of the three fires, since all three are the same shape
(an isolated snapshot, an action, a verifier version, a detection/verification result).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import DataIntegrityTestProfile, TamperTestExecution
from app.modules.validation.shared import finalize, receipt_from_existing, resolve_signature, verify_reauth_and_consume
from app.mutation.errors import InvalidTransitionError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_PROFILE = "data_integrity_test_profile"

_EVENT_BY_ACTION = {
    "canonicalize": "VaultCanonicalizationVerified",
    "archive_retrieve": "ArchiveRetrievalVerified",
}
_DEFAULT_EVENT = "AuditTamperTestCompleted"  # reorder | delete | edit | overwrite, etc.


class CreateDataIntegrityProfileCommand(CommandEnvelope):
    data_class: str
    lifecycle: str
    threats: list[str] = []
    controls: list[str] = []
    tests: list[str] = []


async def create_data_integrity_profile(
    session: AsyncSession, cmd: CreateDataIntegrityProfileCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = DataIntegrityTestProfile(
        data_class=cmd.data_class, lifecycle=cmd.lifecycle, threats=cmd.threats, controls=cmd.controls,
        tests=cmd.tests, state="EFFECTIVE", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_PROFILE, aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"data_class": row.data_class}, event_type="DataIntegrityProfileDefined",
        expected_version=None, command_type="CreateDataIntegrityProfile", site_id=site_id,
    )


class RecordTamperTestCommand(CommandEnvelope):
    profile_id: uuid.UUID
    isolated_snapshot_ref: str
    tamper_action: str
    verifier_version: str
    detected: bool | None = None
    detection_evidence: dict = {}


async def record_tamper_test(
    session: AsyncSession, cmd: RecordTamperTestCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    profile = await session.get(DataIntegrityTestProfile, cmd.profile_id)
    if profile is None:
        raise NotFoundError("Data integrity test profile not found")

    status = "IN_PROGRESS"
    if cmd.detected is not None:
        # DIV-FR-005: on a genuine tamper action, detected=False is a critical *failure*, not a pass.
        is_tamper_action = cmd.tamper_action not in _EVENT_BY_ACTION
        status = "PASS" if (cmd.detected or not is_tamper_action) else "FAIL"

    row = TamperTestExecution(
        profile_id=profile.id, isolated_snapshot_ref=cmd.isolated_snapshot_ref, tamper_action=cmd.tamper_action,
        verifier_version=cmd.verifier_version, detected=cmd.detected, detection_evidence=cmd.detection_evidence,
        performed_by_user_id=actor_user_id, status=status, version=1,
    )
    session.add(row)
    await session.flush()

    event_type = _EVENT_BY_ACTION.get(cmd.tamper_action, _DEFAULT_EVENT)
    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="tamper_test_execution", aggregate_id=row.id,
        version=row.version, action="Performed", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"tamper_action": cmd.tamper_action, "detected": cmd.detected, "status": status},
        event_type=event_type, expected_version=None, command_type="RecordTamperTest", site_id=site_id,
    )


class ApproveDataIntegrityProfileCommand(CommandEnvelope):
    profile_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_data_integrity_profile(
    session: AsyncSession, cmd: ApproveDataIntegrityProfileCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    profile = await session.get(DataIntegrityTestProfile, cmd.profile_id)
    if profile is None:
        raise NotFoundError("Data integrity test profile not found")
    if profile.version != cmd.expected_version:
        raise StaleVersionError("Profile changed since this request was prepared", current_version=profile.version)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to approve a data integrity qualification")

    executions = (
        await session.execute(select(TamperTestExecution).where(TamperTestExecution.profile_id == profile.id))
    ).scalars().all()
    if not executions:
        raise InvalidTransitionError("No integrity test executions recorded for this profile")
    unresolved = [e.tamper_action for e in executions if e.status != "PASS"]
    if unresolved:
        raise InvalidTransitionError("Unresolved data integrity tests", unresolved=unresolved)

    policy = await resolve_signature(session, record_type=RECORD_TYPE_PROFILE, action="approve")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=profile.id, record_version=profile.version,
        )

    profile.state = "QUALIFIED"
    profile.version += 1

    # Document 06 (VLT-FR-001): a qualified data integrity profile is a regulated final record.
    from app.modules.vault import service as vault_service
    await vault_service.release_master(
        session, object_type=RECORD_TYPE_PROFILE, business_id=str(profile.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={"data_class": profile.data_class, "lifecycle": profile.lifecycle},
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_PROFILE, aggregate_id=profile.id,
        version=profile.version, action="Approved", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value={"state": "EFFECTIVE"}, new_value={"state": "QUALIFIED"},
        event_type="DataIntegrityQualificationApproved", expected_version=cmd.expected_version,
        command_type="ApproveDataIntegrityProfile", site_id=site_id, signature_id=signature_id,
    )
