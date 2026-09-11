"""HTTP-facing, signature-policy-gated state-changing operations for Document 06. `release_master`/
`request_correction` in `service.py` are the reusable internals other modules call directly inside their
own transaction; the three commands here are what `POST /vault/v1/...` actually invokes, each going
through the normal Mutation Gateway pattern (idempotency, audit, outbox, receipt).
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.signature import service as signature_service
from app.modules.vault import service as vault_service
from app.modules.vault.models import RecordCorrection
from app.mutation.errors import MissingSignatureError, NotFoundError, ValidationFailedError
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


class EvidenceItem(BaseModel):
    evidence_id: uuid.UUID
    evidence_sha256: str
    media_type: str | None = None
    sequence: int | None = None


class CreateVaultReleaseCommand(CommandEnvelope):
    object_type: str
    business_id: str
    canonical_payload: dict
    business_version_label: str | None = None
    evidence: list[EvidenceItem] = []
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def create_vault_release(
    session: AsyncSession, cmd: CreateVaultReleaseCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    # No Document 106 floor row exists for this action — correctly fails closed
    # (SIGNATURE_POLICY_UNRESOLVED) until a human decides whether the *generic* release endpoint needs a
    # signature. Domain modules that already run their own ceremony (release_batch, disposition_material_lot)
    # call vault_service.release_master directly and never reach this endpoint.
    policy = await signature_service.resolve_signature_requirement(
        session, record_type="vault_object", action="release"
    )
    signature_id = None
    if policy.signature_required:
        # SG-035 (2026-09-10, project-owner-directed): Document 106 section 9 row 2 -- the generic vault
        # master release is `Released` by a "QA Approver / Batch Release" -> "QA Releaser", "independent
        # of every production performer on the record". This endpoint has no site and no prior mutable
        # record, so the required role is enforced (at any site) and the independence clause has no data
        # source here -- same honest limitation recorded for qa_review_package/complete.
        await signature_service.enforce_signer_policy(
            session, policy=policy, actor_user_id=actor_user_id, site_id=None,
            action_label="vault_object.release",
        )
        if cmd.challenge_id is None or not cmd.reauth_password:
            raise MissingSignatureError("This release requires a signature", required_meaning=policy.meaning)
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        # Bound to the canonical_payload's own hash rather than a mutable aggregate's version/hash pair,
        # since a vault release has no prior mutable record to bind to.
        challenge = await signature_service.consume_challenge(
            session,
            challenge_id=cmd.challenge_id,
            user_id=actor_user_id,
            record_version=1,
            record_hash=sha256_hex(cmd.canonical_payload),
        )
        signature = await signature_service.sign(
            session, challenge=challenge, auth_context={"method": "password_reauth"}
        )
        signature_id = signature.id

    obj = await vault_service.release_master(
        session,
        object_type=cmd.object_type,
        business_id=cmd.business_id,
        canonical_payload=cmd.canonical_payload,
        actor_user_id=actor_user_id,
        business_version_label=cmd.business_version_label,
        evidence=[e.model_dump() for e in cmd.evidence],
    )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="vault_object",
        aggregate_id=obj.object_id,
        aggregate_version=obj.internal_version,
        action="Released",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"object_type": obj.object_type, "business_id": obj.business_id, "digest": obj.digest},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="VaultObjectReleased",
        aggregate_type="vault_object",
        aggregate_id=obj.object_id,
        aggregate_version=obj.internal_version,
        payload={"id": str(obj.object_id), "object_type": obj.object_type, "business_id": obj.business_id},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="CreateVaultRelease",
        aggregate_type="vault_object",
        aggregate_id=obj.object_id,
        expected_version=None,
        resulting_version=obj.internal_version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=obj.object_id,
        resulting_version=obj.internal_version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


class RequestCorrectionCommand(CommandEnvelope):
    record_object_id: uuid.UUID
    reason_code: str | None = None
    reason_text: str


async def request_correction(
    session: AsyncSession, cmd: RequestCorrectionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    correction = await vault_service.request_correction(
        session,
        record_object_id=cmd.record_object_id,
        reason_code=cmd.reason_code,
        reason_text=cmd.reason_text,
        requested_by=actor_user_id,
    )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="record_correction",
        aggregate_id=correction.correction_id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"record_object_id": str(cmd.record_object_id), "reason_code": cmd.reason_code},
        reason=cmd.reason_text,
    )
    await write_outbox_event(
        session,
        event_type="RecordCorrectionRequested",
        aggregate_type="record_correction",
        aggregate_id=correction.correction_id,
        aggregate_version=1,
        payload={"id": str(correction.correction_id), "record_object_id": str(cmd.record_object_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="RequestCorrection",
        aggregate_type="record_correction",
        aggregate_id=correction.correction_id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=correction.correction_id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


class CompleteCorrectionCommand(CommandEnvelope):
    correction_id: uuid.UUID
    corrected_canonical_payload: dict
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def _load_correction_for_update(session: AsyncSession, correction_id: uuid.UUID) -> RecordCorrection:
    """`with_for_update()` serializes concurrent completion attempts on the same correction -- Document
    106 section 13 test #12 ("two signers complete simultaneously on a 2-signature chain -> exactly one
    valid ordering persists"): the second transaction blocks until the first commits, then correctly sees
    the first signature already recorded and resolves to chain position 2, not a duplicate position 1."""
    result = await session.execute(
        select(RecordCorrection).where(RecordCorrection.correction_id == correction_id).with_for_update()
    )
    correction = result.scalar_one_or_none()
    if correction is None:
        raise NotFoundError("Correction not found")
    return correction


async def complete_correction(
    session: AsyncSession, cmd: CompleteCorrectionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """SG-035 pair 4, RESOLVED 2026-09-11, project-owner-directed (PHASE_3_DEFERRED_DECISIONS.md item D).
    Document 106 section 9 row 1: `Approved`, "Authorized corrector + independent approver", count 2,
    "Corrector and approver MUST differ", reason mandatory (already captured at `request_correction()`
    time). This command is now called once per chain position -- the same `CompleteCorrectionCommand`
    shape, resubmitted with a fresh `challenge_id`/`reauth_password` by the second signer -- and only
    applies the correction (`vault_service.release_master()`) once the chain is fully signed; an
    incomplete chain leaves the correction in `awaiting_second_signature` with no domain-state change
    yet, matching VLT-FR-010/011's "completing a correction creates the new corrected version" only
    happening once, not once per signature.
    """
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    correction = await _load_correction_for_update(session, cmd.correction_id)
    if correction.status not in ("requested", "awaiting_second_signature"):
        raise ValidationFailedError("Correction is not awaiting completion", current_status=correction.status)
    original = await vault_service.get_object(session, correction.record_object_id)

    policy = await signature_service.resolve_signature_requirement(
        session, record_type="record_correction", action="complete"
    )
    signature_id = None
    if policy.signature_required:
        record_hash = sha256_hex(cmd.corrected_canonical_payload)
        prior_signatures = await signature_service.chain_signatures_so_far(
            session, record_type="record_correction", record_id=correction.correction_id, record_version=1,
        )
        position = len(prior_signatures) + 1
        if position > policy.signature_count:
            raise ValidationFailedError(
                "This correction has already collected every required signature",
                signature_count=policy.signature_count,
            )
        if prior_signatures and record_hash != prior_signatures[0].record_hash:
            raise ValidationFailedError(
                "corrected_canonical_payload must match what the earlier signer(s) in this chain approved"
            )
        await signature_service.enforce_chain_signer_policy(
            session, policy=policy, position=position, actor_user_id=actor_user_id, site_id=original.site_id,
            action_label="record_correction.complete", prior_signer_ids=[s.user_id for s in prior_signatures],
        )
        if cmd.challenge_id is None or not cmd.reauth_password:
            raise MissingSignatureError(
                f"Signature {position} of {policy.signature_count} is required to complete this correction",
                required_meaning=policy.meaning,
            )
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
            record_version=1, record_hash=record_hash,
        )
        signature = await signature_service.sign(
            session, challenge=challenge, auth_context={"method": "password_reauth"}
        )
        signature_id = signature.id
        correction.approved_by_signatures = [*(correction.approved_by_signatures or []), str(signature_id)]

        if position < policy.signature_count:
            # Chain incomplete -- record this signature and stop; the correction is not applied until
            # every position has signed (SIGP-FR-007 ordered chains).
            old_status = correction.status
            correction.status = "awaiting_second_signature"
            correlation_id = uuid.uuid4()
            audit_event = await write_audit_event(
                session, site_id=None, aggregate_type="record_correction", aggregate_id=correction.correction_id,
                aggregate_version=1 + position, action="Signed", actor_id=actor_user_id, correlation_id=correlation_id,
                reason=None, old_value={"status": old_status},
                new_value={"status": "awaiting_second_signature", "chain_position": position, "signature_count": policy.signature_count},
                signature_id=signature_id,
            )
            await write_outbox_event(
                session, event_type="RecordCorrectionSigned", aggregate_type="record_correction",
                aggregate_id=correction.correction_id, aggregate_version=1 + position,
                payload={"id": str(correction.correction_id), "chain_position": position},
                correlation_id=correlation_id,
            )
            receipt = await record_command_receipt(
                session, site_id=None, command_type="CompleteCorrection", aggregate_type="record_correction",
                aggregate_id=correction.correction_id, expected_version=None, resulting_version=1 + position,
                idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
                payload_hash=payload_hash,
            )
            return MutationReceipt(
                command_id=receipt.id, aggregate_id=correction.correction_id, resulting_version=1 + position,
                audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
            )
        # position == signature_count (or signature_required is False): the chain is complete (or no
        # signature is required at all) -- fall through and apply the correction.

    new_object = await vault_service.release_master(
        session,
        object_type=original.object_type,
        business_id=original.business_id,
        canonical_payload=cmd.corrected_canonical_payload,
        actor_user_id=actor_user_id,
        site_id=original.site_id,
        corrected_from_object_id=original.object_id,
    )
    old_status = correction.status
    correction.status = "completed"
    correction.resulting_object_id = new_object.object_id
    correction.completed_at = datetime.now(timezone.utc)

    resulting_version = 1 + (policy.signature_count if policy.signature_required else 1)
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="record_correction",
        aggregate_id=correction.correction_id,
        aggregate_version=resulting_version,
        action="Corrected",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"status": old_status},
        new_value={"status": "completed", "resulting_object_id": str(new_object.object_id)},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="RecordCorrectionCompleted",
        aggregate_type="record_correction",
        aggregate_id=correction.correction_id,
        aggregate_version=resulting_version,
        payload={"id": str(correction.correction_id), "resulting_object_id": str(new_object.object_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="CompleteCorrection",
        aggregate_type="record_correction",
        aggregate_id=correction.correction_id,
        expected_version=None,
        resulting_version=resulting_version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=correction.correction_id,
        resulting_version=resulting_version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )
