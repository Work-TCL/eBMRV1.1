"""Document 72 (SPEC-DATA-004) Mutation Gateway command handlers for the evidence lifecycle.

State machine: `STAGED -> FINALIZED -> ARCHIVED`, with `STAGED -> QUARANTINE` on a hash mismatch and
`FINALIZED/ARCHIVED -> MISSING` when integrity verification cannot find the backing object, and
`FINALIZED/ARCHIVED -> PURGED` only through `purge_expired_evidence()` (never a row DELETE).

Signature: only `apply_evidence_legal_hold()` is signed (Document 106 row 142 -- `Performed`,
role pair "Authorized holder (Production / QA)" => `required_role_id=None` + RBAC `evidence.legal_hold`,
independence None, reason required; exact precedent = `equipment_asset/hold`). Everything else is
RBAC-gated + audit-only (Document 106 has no other SPEC-DATA-004 row).
"""

from __future__ import annotations

import base64
import uuid
from datetime import datetime, timezone

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.evidence.models import EvidenceManifest, EvidenceObject
from app.modules.evidence.store import content_key, get_store, sha256_bytes
from app.modules.iam.models import User
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    EvidenceHashMismatchError,
    EvidenceMissingError,
    EvidenceNotFinalizedError,
    EvidencePurgeBlockedError,
    EvidenceUploadDeniedError,
    MissingSignatureError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

_BUCKET = "gxp-evidence"
# OBJ-FR-015: MIME allowlist for regulated evidence. Filenames are metadata only.
_ALLOWED_MIME = {
    "application/pdf", "application/json", "application/xml", "text/plain", "text/csv",
    "image/png", "image/jpeg", "image/tiff",
    "application/zip", "application/octet-stream",
    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}
# OBJ-FR-003/015 -- no approved numeric cap baseline (SG-164 family). Engineering-default floor,
# fully overridable per deployment; not a guessed regulated value.
_DEFAULT_MAX_BYTES = 256 * 1024 * 1024  # 256 MiB


def evidence_record_hash(obj: EvidenceObject) -> str:
    return sha256_hex(
        {
            "id": str(obj.id), "owner_type": obj.owner_type, "owner_id": str(obj.owner_id),
            "content_hash": obj.content_hash, "state": obj.state, "version": obj.version,
        }
    )


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version, audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _finalize_tx(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, aggregate_id: uuid.UUID,
    version: int, action: str, actor_user_id: uuid.UUID, reason: str | None, old_value: dict | None,
    new_value: dict, event_type: str, expected_version: int | None, command_type: str,
    site_id: uuid.UUID | None = None, signature_id: uuid.UUID | None = None,
    aggregate_type: str = "evidence_object",
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=site_id, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value=old_value, new_value=new_value, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, payload=new_value, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=site_id, command_type=command_type, aggregate_type=aggregate_type,
        aggregate_id=aggregate_id, expected_version=expected_version, resulting_version=version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=aggregate_id, resulting_version=version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# =================================================================================================
# stageEvidenceUpload() -- OBJ-FR-003/015/025
# =================================================================================================


class StageEvidenceUploadCommand(CommandEnvelope):
    owner_type: str
    owner_id: uuid.UUID
    owner_version: int | None = None
    site_id: uuid.UUID | None = None
    filename: str
    mime_type: str
    declared_size_bytes: int | None = None
    expected_hash: str | None = None
    provenance: dict = {}
    reason: str


async def stage_evidence_upload(
    session: AsyncSession, cmd: StageEvidenceUploadCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.owner_type or not cmd.filename or not cmd.reason:
        raise ValidationFailedError("owner_type, filename and reason are required")
    if cmd.mime_type not in _ALLOWED_MIME:
        raise EvidenceUploadDeniedError(f"MIME type {cmd.mime_type!r} is not in the evidence allowlist")
    if cmd.declared_size_bytes is not None and (
        not isinstance(cmd.declared_size_bytes, int) or cmd.declared_size_bytes < 0
        or cmd.declared_size_bytes > _DEFAULT_MAX_BYTES
    ):
        raise EvidenceUploadDeniedError(
            "declared_size_bytes is missing/negative or exceeds the configured cap",
            max_bytes=_DEFAULT_MAX_BYTES,
        )

    obj = EvidenceObject(
        site_id=cmd.site_id, owner_type=cmd.owner_type, owner_id=cmd.owner_id,
        owner_version=cmd.owner_version, provider=get_store().provider, bucket=_BUCKET,
        object_key=f"staging/{uuid.uuid4()}", size_bytes=cmd.declared_size_bytes,
        mime_type=cmd.mime_type, filename=cmd.filename, hash_algorithm="SHA-256",
        expected_hash=cmd.expected_hash, state="STAGED",
        provenance={**cmd.provenance, "uploaded_by": str(actor_user_id),
                    "staged_at": datetime.now(timezone.utc).isoformat()},
        version=1,
    )
    session.add(obj)
    await session.flush()

    return await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=obj.id, version=obj.version,
        action="Created", actor_user_id=actor_user_id, reason=cmd.reason, old_value=None,
        new_value={"evidence_id": str(obj.id), "owner_type": obj.owner_type, "owner_id": str(obj.owner_id),
                   "state": obj.state, "mime_type": obj.mime_type},
        event_type="EvidenceUploadStaged", expected_version=None, command_type="StageEvidenceUpload",
        site_id=cmd.site_id,
    )


# =================================================================================================
# finalizeEvidenceUpload() -- OBJ-FR-002/004/016
# =================================================================================================


class FinalizeEvidenceUploadCommand(CommandEnvelope):
    evidence_id: uuid.UUID
    expected_version: int
    content_base64: str
    reason: str


async def finalize_evidence_upload(
    session: AsyncSession, cmd: FinalizeEvidenceUploadCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    obj = await session.get(EvidenceObject, cmd.evidence_id)
    if obj is None:
        raise NotFoundError("Evidence object not found")
    if obj.version != cmd.expected_version:
        raise StaleVersionError("Evidence object changed since this request was prepared",
                                current_version=obj.version)
    if obj.state not in ("STAGED", "QUARANTINE"):
        raise EvidenceNotFinalizedError(f"Cannot finalize an evidence object in state {obj.state}")

    try:
        data = base64.b64decode(cmd.content_base64, validate=True)
    except Exception as exc:  # noqa: BLE001
        raise ValidationFailedError("content_base64 is not valid base64") from exc

    digest = sha256_bytes(data)
    old_state = obj.state
    if obj.expected_hash and obj.expected_hash.lower() != digest.lower():
        obj.state = "QUARANTINE"
        obj.version += 1
        await session.flush()
        receipt = await _finalize_tx(
            session, cmd=cmd, payload_hash=payload_hash, aggregate_id=obj.id, version=obj.version,
            action="StatusChanged", actor_user_id=actor_user_id, reason=cmd.reason,
            old_value={"state": old_state}, new_value={"state": "QUARANTINE", "computed_hash": digest,
                                                       "expected_hash": obj.expected_hash},
            event_type="EvidenceHashMismatch", expected_version=cmd.expected_version,
            command_type="FinalizeEvidenceUpload", site_id=obj.site_id,
        )
        raise EvidenceHashMismatchError(
            "Uploaded bytes do not match the declared hash; object quarantined",
            evidence_id=str(obj.id), expected_hash=obj.expected_hash, computed_hash=digest,
            receipt_command_id=str(receipt.command_id),
        )

    key = content_key(digest)
    put_result = await get_store().put(_BUCKET, key, data)

    obj.object_key = key
    obj.provider_version_id = put_result.get("provider_version_id")
    obj.content_hash = digest
    obj.size_bytes = put_result["size_bytes"]
    obj.state = "FINALIZED"
    obj.version += 1
    await session.flush()

    return await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=obj.id, version=obj.version,
        action="StatusChanged", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value={"state": old_state},
        new_value={"evidence_id": str(obj.id), "state": "FINALIZED", "content_hash": digest,
                   "size_bytes": obj.size_bytes, "object_key": key},
        event_type="EvidenceFinalized", expected_version=cmd.expected_version,
        command_type="FinalizeEvidenceUpload", site_id=obj.site_id,
    )


# =================================================================================================
# createEvidenceManifest() -- OBJ-FR-008/027
# =================================================================================================


class CreateEvidenceManifestCommand(CommandEnvelope):
    owner_type: str
    owner_id: uuid.UUID
    owner_version: int | None = None
    manifest_type: str
    evidence_ids: list[uuid.UUID]
    renderer_version: str | None = None
    reason: str


async def create_evidence_manifest(
    session: AsyncSession, cmd: CreateEvidenceManifestCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.manifest_type not in ("RELEASE", "EXPORT", "BATCH_ISSUE", "RENDITION"):
        raise ValidationFailedError("manifest_type must be RELEASE, EXPORT, BATCH_ISSUE or RENDITION")
    if not cmd.evidence_ids:
        raise ValidationFailedError("a manifest must reference at least one evidence object")

    items: list[dict] = []
    for eid in cmd.evidence_ids:
        ev = await session.get(EvidenceObject, eid)
        if ev is None:
            raise NotFoundError(f"Evidence object {eid} not found")
        if ev.state not in ("FINALIZED", "ARCHIVED"):
            raise EvidenceNotFinalizedError(f"Evidence object {eid} is {ev.state}, not FINALIZED")
        items.append({
            "evidence_id": str(ev.id), "content_hash": ev.content_hash,
            "hash_algorithm": ev.hash_algorithm, "mime_type": ev.mime_type, "size_bytes": ev.size_bytes,
        })
    canonical_hash = sha256_hex({"manifest_type": cmd.manifest_type, "items": items})

    prior = (
        await session.execute(
            select(EvidenceManifest).where(
                EvidenceManifest.owner_type == cmd.owner_type,
                EvidenceManifest.owner_id == cmd.owner_id,
                EvidenceManifest.manifest_type == cmd.manifest_type,
                EvidenceManifest.state == "ACTIVE",
            )
        )
    ).scalars().all()
    next_mv = 1
    for p in prior:
        p.state = "SUPERSEDED"
        p.version += 1
        next_mv = max(next_mv, p.manifest_version + 1)

    manifest = EvidenceManifest(
        owner_type=cmd.owner_type, owner_id=cmd.owner_id, owner_version=cmd.owner_version,
        manifest_type=cmd.manifest_type, manifest_version=next_mv, items=items,
        canonical_hash=canonical_hash, renderer_version=cmd.renderer_version, state="ACTIVE", version=1,
    )
    session.add(manifest)
    await session.flush()

    return await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=manifest.id, version=manifest.version,
        action="Created", actor_user_id=actor_user_id, reason=cmd.reason, old_value=None,
        new_value={"manifest_id": str(manifest.id), "manifest_type": cmd.manifest_type,
                   "manifest_version": next_mv, "canonical_hash": canonical_hash, "item_count": len(items)},
        event_type="EvidenceManifestCreated", expected_version=None,
        command_type="CreateEvidenceManifest", aggregate_type="evidence_manifest",
    )


# =================================================================================================
# applyEvidenceLegalHold() -- OBJ-FR-018. SIGNED (Document 106 row 142).
# =================================================================================================


class ApplyEvidenceLegalHoldCommand(CommandEnvelope):
    evidence_id: uuid.UUID
    expected_version: int
    hold_ref: str
    reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def apply_evidence_legal_hold(
    session: AsyncSession, cmd: ApplyEvidenceLegalHoldCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    obj = await session.get(EvidenceObject, cmd.evidence_id)
    if obj is None:
        raise NotFoundError("Evidence object not found")
    if obj.version != cmd.expected_version:
        raise StaleVersionError("Evidence object changed since this request was prepared",
                                current_version=obj.version)
    if obj.state not in ("FINALIZED", "ARCHIVED"):
        raise EvidenceNotFinalizedError("A legal hold can only be placed on a finalized/archived object")
    if not cmd.hold_ref or not cmd.reason:
        raise ValidationFailedError("hold_ref and reason are required")

    policy = await signature_service.resolve_signature_requirement(
        session, record_type="evidence_object", action="legal_hold"
    )
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not cmd.reauth_password or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        if cmd.challenge_id is None:
            raise MissingSignatureError("challenge_id is required for a signed legal hold")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
            record_version=obj.version, record_hash=evidence_record_hash(obj),
        )
        signature = await signature_service.sign(
            session, challenge=challenge, auth_context={"method": "password_reauth"}
        )
        signature_id = signature.id

    old = {"legal_hold": obj.legal_hold}
    obj.legal_hold = True
    obj.legal_hold_ref = cmd.hold_ref
    obj.signature_id = signature_id
    obj.version += 1
    await session.flush()

    return await _finalize_tx(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_id=obj.id, version=obj.version,
        action="StatusChanged", actor_user_id=actor_user_id, reason=cmd.reason, old_value=old,
        new_value={"evidence_id": str(obj.id), "legal_hold": True, "hold_ref": cmd.hold_ref},
        event_type="EvidenceLegalHoldApplied", expected_version=cmd.expected_version,
        command_type="ApplyEvidenceLegalHold", site_id=obj.site_id, signature_id=signature_id,
    )


# =================================================================================================
# verifyEvidenceIntegrity() -- OBJ-FR-016/023
# =================================================================================================


class VerifyEvidenceIntegrityCommand(CommandEnvelope):
    evidence_ids: list[uuid.UUID] | None = None
    owner_type: str | None = None
    owner_id: uuid.UUID | None = None
    mode: str = "full"
    reason: str


async def verify_evidence_integrity(
    session: AsyncSession, cmd: VerifyEvidenceIntegrityCommand, actor_user_id: uuid.UUID
) -> dict:
    """Not a single-aggregate mutation: it checks a scope and flips any broken object to MISSING (one
    audit + outbox per flipped object). Returns an IntegrityReport."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))

    stmt = select(EvidenceObject).where(EvidenceObject.state.in_(("FINALIZED", "ARCHIVED")))
    if cmd.evidence_ids:
        stmt = stmt.where(EvidenceObject.id.in_(cmd.evidence_ids))
    elif cmd.owner_type and cmd.owner_id:
        stmt = stmt.where(EvidenceObject.owner_type == cmd.owner_type, EvidenceObject.owner_id == cmd.owner_id)
    objs = (await session.execute(stmt)).scalars().all()

    checked, missing, mismatched = 0, [], []
    store = get_store()
    for obj in objs:
        checked += 1
        head = await store.head(obj.bucket, obj.object_key)
        if head is None:
            obj.state = "MISSING"
            obj.version += 1
            correlation_id = uuid.uuid4()
            await write_audit_event(
                session, site_id=obj.site_id, aggregate_type="evidence_object", aggregate_id=obj.id,
                aggregate_version=obj.version, action="StatusChanged", actor_id=actor_user_id,
                correlation_id=correlation_id, reason=cmd.reason,
                old_value={"state": "FINALIZED"}, new_value={"state": "MISSING"},
            )
            await write_outbox_event(
                session, event_type="EvidenceMissing", aggregate_type="evidence_object",
                aggregate_id=obj.id, aggregate_version=obj.version,
                payload={"evidence_id": str(obj.id), "object_key": obj.object_key}, correlation_id=correlation_id,
            )
            missing.append(str(obj.id))
        elif obj.content_hash and head["content_hash"].lower() != obj.content_hash.lower():
            correlation_id = uuid.uuid4()
            await write_outbox_event(
                session, event_type="EvidenceHashMismatch", aggregate_type="evidence_object",
                aggregate_id=obj.id, aggregate_version=obj.version,
                payload={"evidence_id": str(obj.id), "stored_hash": head["content_hash"],
                         "expected_hash": obj.content_hash}, correlation_id=correlation_id,
            )
            mismatched.append(str(obj.id))

    healthy = not missing and not mismatched
    report = {
        "mode": cmd.mode, "checked": checked, "missing": missing, "mismatched": mismatched,
        "healthy": healthy, "checked_at": datetime.now(timezone.utc).isoformat(),
    }
    if not healthy:
        raise EvidenceMissingError(
            "Evidence integrity check found missing or mismatched objects",
            missing=missing, mismatched=mismatched, report=report,
        )
    return report


# =================================================================================================
# purgeExpiredEvidence() -- OBJ-FR-018/019 (retention worker; no HTTP endpoint)
# =================================================================================================


class PurgeExpiredEvidenceCommand(CommandEnvelope):
    evidence_ids: list[uuid.UUID]
    policy_version: str
    reason: str


async def purge_expired_evidence(
    session: AsyncSession, cmd: PurgeExpiredEvidenceCommand, actor_user_id: uuid.UUID
) -> dict:
    """For each candidate: block on legal hold, an unexpired retention window, or an ACTIVE manifest
    still referencing it; otherwise transition to PURGED (state change, not a row delete) and emit
    `EvidencePurged`."""
    now = datetime.now(timezone.utc)
    purged, blocked = [], []
    for eid in cmd.evidence_ids:
        obj = await session.get(EvidenceObject, eid)
        if obj is None:
            blocked.append({"evidence_id": str(eid), "reason": "not_found"})
            continue
        if obj.legal_hold:
            blocked.append({"evidence_id": str(eid), "reason": "legal_hold"})
            continue
        if obj.retention_until and obj.retention_until.replace(tzinfo=timezone.utc) > now:
            blocked.append({"evidence_id": str(eid), "reason": "retention_not_elapsed"})
            continue
        ref = (
            await session.execute(
                select(func.count()).select_from(EvidenceManifest).where(
                    EvidenceManifest.state == "ACTIVE",
                    EvidenceManifest.items.contains([{"evidence_id": str(eid)}]),
                )
            )
        ).scalar_one()
        if ref:
            blocked.append({"evidence_id": str(eid), "reason": "referenced_by_active_manifest"})
            continue

        old_state = obj.state
        obj.state = "PURGED"
        obj.version += 1
        correlation_id = uuid.uuid4()
        await write_audit_event(
            session, site_id=obj.site_id, aggregate_type="evidence_object", aggregate_id=obj.id,
            aggregate_version=obj.version, action="StatusChanged", actor_id=actor_user_id,
            correlation_id=correlation_id, reason=cmd.reason,
            old_value={"state": old_state}, new_value={"state": "PURGED", "policy_version": cmd.policy_version},
        )
        await write_outbox_event(
            session, event_type="EvidencePurged", aggregate_type="evidence_object", aggregate_id=obj.id,
            aggregate_version=obj.version, payload={"evidence_id": str(obj.id), "policy_version": cmd.policy_version},
            correlation_id=correlation_id,
        )
        purged.append(str(obj.id))

    if not purged and blocked:
        raise EvidencePurgeBlockedError("No candidate was eligible for purge", blocked=blocked)
    return {"purged": purged, "blocked": blocked, "policy_version": cmd.policy_version}
