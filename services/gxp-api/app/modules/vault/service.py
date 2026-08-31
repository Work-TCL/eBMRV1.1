"""Document 06 (SPEC-GXP-004) — the vault's core mechanics: creating an immutable snapshot on release,
reading it back, verifying its integrity, and the correction (amendment) workflow. `release_master` is a
plain internal function, not itself signature-gated — callers (domain command handlers like
`release_batch`) have already run their own authorization/signature ceremony; this only creates the
immutable side-effect, inside the same transaction (AG-06/MUT-FR-015).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.vault.models import RecordCorrection, VaultEvidence, VaultObject
from app.mutation.errors import ConcurrentVaultReleaseError, NotFoundError, ValidationFailedError
from app.mutation.hashing import sha256_hex


async def release_master(
    session: AsyncSession,
    *,
    object_type: str,
    business_id: str,
    canonical_payload: dict,
    actor_user_id: uuid.UUID | None = None,
    site_id: uuid.UUID | None = None,
    business_version_label: str | None = None,
    retention_class: str | None = None,
    evidence: list[dict] | None = None,
    corrected_from_object_id: uuid.UUID | None = None,
) -> VaultObject:
    """Creates the next immutable version for (object_type, business_id) — VLT-FR-001/002/003/004/009.
    `evidence` is a list of {"evidence_id": UUID, "evidence_sha256": str, "media_type": str | None,
    "sequence": int | None} dicts (VLT-FR-005). Pass `corrected_from_object_id` only when this release is
    completing a correction (VLT-FR-010), not for an ordinary release.
    """
    latest = (
        await session.execute(
            select(VaultObject)
            .where(VaultObject.object_type == object_type, VaultObject.business_id == business_id)
            .order_by(VaultObject.internal_version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    internal_version = (latest.internal_version + 1) if latest else 1
    digest = sha256_hex(canonical_payload)

    obj = VaultObject(
        site_id=site_id,
        object_type=object_type,
        business_id=business_id,
        internal_version=internal_version,
        business_version_label=business_version_label,
        canonical_payload=canonical_payload,
        digest=digest,
        status="released",
        effective_from=datetime.now(timezone.utc),
        supersedes_object_id=latest.object_id if latest else None,
        corrected_from_object_id=corrected_from_object_id,
        retention_class=retention_class,
        created_by_subject=actor_user_id,
    )
    # UNIQUE(object_type, business_id, internal_version) (migration 616aed1058e9) is the real guard
    # against two concurrent releases silently colliding on the same next version -- a nested transaction
    # (SAVEPOINT) lets us catch just this INSERT's IntegrityError and convert it to a clean, retryable
    # domain error without poisoning the caller's outer transaction.
    try:
        async with session.begin_nested():
            session.add(obj)
            await session.flush()
    except IntegrityError as exc:
        raise ConcurrentVaultReleaseError(
            "Another release was committed concurrently for this object_type/business_id -- retry",
            object_type=object_type,
            business_id=business_id,
        ) from exc

    for item in evidence or []:
        session.add(
            VaultEvidence(
                vault_object_id=obj.object_id,
                evidence_id=item["evidence_id"],
                evidence_version=item.get("evidence_version", 1),
                evidence_sha256=item["evidence_sha256"],
                media_type=item.get("media_type"),
                sequence=item.get("sequence"),
            )
        )
    return obj


async def get_object(session: AsyncSession, object_id: uuid.UUID) -> VaultObject:
    obj = await session.get(VaultObject, object_id)
    if obj is None:
        raise NotFoundError("Vault object not found")
    return obj


async def list_versions_for_business_id(
    session: AsyncSession, *, object_type: str, business_id: str
) -> list[VaultObject]:
    return (
        (
            await session.execute(
                select(VaultObject)
                .where(VaultObject.object_type == object_type, VaultObject.business_id == business_id)
                .order_by(VaultObject.internal_version)
            )
        )
        .scalars()
        .all()
    )


async def verify_integrity(session: AsyncSession, object_id: uuid.UUID) -> dict:
    """Recomputes the digest from the stored canonical_payload (detects content tampering) and confirms
    `supersedes_object_id` still points at a real prior version with a lower internal_version (detects
    relinking/deletion) — the same two-part check as the audit module's `verify_chain`, applied to vault
    objects instead of audit events.
    """
    obj = await get_object(session, object_id)
    digest_valid = sha256_hex(obj.canonical_payload) == obj.digest

    link_valid = True
    if obj.supersedes_object_id is not None:
        prior = await session.get(VaultObject, obj.supersedes_object_id)
        link_valid = (
            prior is not None
            and prior.object_type == obj.object_type
            and prior.business_id == obj.business_id
            and prior.internal_version == obj.internal_version - 1
        )
    return {"object_id": str(object_id), "digest_valid": digest_valid, "link_valid": link_valid}


async def request_correction(
    session: AsyncSession,
    *,
    record_object_id: uuid.UUID,
    reason_code: str | None,
    reason_text: str,
    requested_by: uuid.UUID,
) -> RecordCorrection:
    """VLT-FR-010/011 — a correction is requested against an existing released object; completing it
    (see `complete_correction` / `app.modules.vault.commands.complete_correction`) is a separate, signed
    step that creates the new superseding/corrected version."""
    record = await get_object(session, record_object_id)
    if record.status != "released":
        raise ValidationFailedError(
            "Only a released vault object can have a correction requested against it",
            current_status=record.status,
        )
    correction = RecordCorrection(
        record_object_id=record.object_id,
        status="requested",
        reason_code=reason_code,
        reason_text=reason_text,
        requested_by=requested_by,
    )
    session.add(correction)
    await session.flush()
    return correction


async def get_correction(session: AsyncSession, correction_id: uuid.UUID) -> RecordCorrection:
    correction = await session.get(RecordCorrection, correction_id)
    if correction is None:
        raise NotFoundError("Correction not found")
    return correction
