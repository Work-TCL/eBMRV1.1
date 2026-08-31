"""Document 30 (SPEC-QMS-005) — the buildable slice of Document Control: the linear
DRAFT -> REVIEW -> RELEASED -> EFFECTIVE -> OBSOLETE pipeline Document 30 §4 describes (APPROVED folds
into RELEASED, matching this module family's fold-in precedent), matching the module's own 7-op API list
exactly (`/documents/v1` prefix, not `/qms/v1`). CANCELLED is named only in the state diagram, not by any
DOC-FR requirement, and has no operation either -- nothing is built or gapped for it. DOC-FR-021
(retirement) is folded into obsolete_version(). See document_models.py's module docstring and
docs/generated/18_SPEC_GAPS.md SG-078..SG-080 for what is deliberately not built this pass.
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.qms import change_service
from app.modules.qms.document_models import (
    DOCUMENT_TYPES,
    VERSION_ALLOWED_TRANSITIONS,
    ControlledCopy,
    ControlledDocument,
    ControlledDocumentVersion,
)
from app.modules.signature import service as signature_service
from app.modules.vault import service as vault_service
from app.mutation.errors import (
    ControlledCopyConflictError,
    DocumentReviewIncompleteError,
    DocumentSignatureRequiredError,
    DocumentVersionObsoleteError,
    EffectivePrerequisitesIncompleteError,
    InvalidTransitionError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
        audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _load_version_for_update(session: AsyncSession, version_id: uuid.UUID, expected_version: int) -> ControlledDocumentVersion:
    result = await session.execute(select(ControlledDocumentVersion).where(ControlledDocumentVersion.id == version_id).with_for_update())
    version = result.scalar_one_or_none()
    if version is None:
        raise NotFoundError("Controlled document version not found")
    if version.version != expected_version:
        raise StaleVersionError(
            "Controlled document version was modified by another actor since it was read",
            expected_version=expected_version, current_version=version.version,
        )
    return version


def _record_hash(version: ControlledDocumentVersion) -> str:
    return sha256_hex({"id": str(version.id), "version": version.version})


async def _write_version_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, version: ControlledDocumentVersion, action: str,
    actor_user_id: uuid.UUID, reason: str | None, old_state: str, event_type: str, event_payload: dict,
    signature_id: uuid.UUID | None, expected_version: int | None, command_type: str, site_id: uuid.UUID,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=site_id, aggregate_type="controlled_document_version", aggregate_id=version.id,
        aggregate_version=version.version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state}, new_value={"state": version.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="controlled_document_version", aggregate_id=version.id,
        aggregate_version=version.version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=site_id, command_type=command_type, aggregate_type="controlled_document_version",
        aggregate_id=version.id, expected_version=expected_version, resulting_version=version.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=version.id, resulting_version=version.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Create draft — DOC-FR-001/002/003/004(partial)/016/017/018
# ---------------------------------------------------------------------------


class CreateDocumentDraftCommand(CommandEnvelope):
    site_id: uuid.UUID
    document_code: str
    document_type: str
    owner_subject_id: uuid.UUID
    version_label: str
    content_hash: str
    department_id: uuid.UUID | None = None
    site_scope: list | None = None
    rendition_hash: str | None = None
    source_relationships: list | None = None
    is_external: bool = False
    external_source: str | None = None
    external_revision: str | None = None


async def create_draft(session: AsyncSession, cmd: CreateDocumentDraftCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.document_type not in DOCUMENT_TYPES:
        raise ValidationFailedError("Unrecognized document_type", document_type=cmd.document_type, allowed=list(DOCUMENT_TYPES))
    if not cmd.content_hash.strip():
        raise ValidationFailedError("content_hash is required")
    if cmd.is_external and not cmd.external_source:
        raise ValidationFailedError("external_source is required for an external document")

    document = (
        await session.execute(select(ControlledDocument).where(ControlledDocument.document_code == cmd.document_code))
    ).scalar_one_or_none()
    created_document = document is None
    if created_document:
        document = ControlledDocument(
            site_id=cmd.site_id, document_code=cmd.document_code, document_type=cmd.document_type,
            owner_subject_id=cmd.owner_subject_id, department_id=cmd.department_id, site_scope=cmd.site_scope,
            is_external=cmd.is_external, external_source=cmd.external_source, external_revision=cmd.external_revision,
        )
        session.add(document)
        await session.flush()

    conflict = (
        await session.execute(
            select(ControlledDocumentVersion).where(
                ControlledDocumentVersion.document_id == document.id, ControlledDocumentVersion.version_label == cmd.version_label,
            )
        )
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("version_label is already in use for this document", version_label=cmd.version_label)

    version = ControlledDocumentVersion(
        document_id=document.id, version_label=cmd.version_label, content_hash=cmd.content_hash,
        rendition_hash=cmd.rendition_hash, source_relationships=cmd.source_relationships, state="DRAFT",
    )
    session.add(version)
    await session.flush()

    return await _write_version_receipt(
        session, cmd=cmd, payload_hash=payload_hash, version=version, action="Created", actor_user_id=actor_user_id,
        reason=None, old_state="DRAFT", event_type="DocumentVersionReleased",
        event_payload={"id": str(version.id), "document_code": document.document_code, "version_label": version.version_label},
        signature_id=None, expected_version=None, command_type="CreateDocumentDraft", site_id=document.site_id,
    )


# ---------------------------------------------------------------------------
# Submit — DOC-FR-005
# ---------------------------------------------------------------------------


class SubmitDocumentDraftCommand(CommandEnvelope):
    document_version_id: uuid.UUID
    expected_version: int
    reviewers: list[dict]
    reason: str | None = None


async def submit_draft(session: AsyncSession, cmd: SubmitDocumentDraftCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_version_for_update(session, cmd.document_version_id, cmd.expected_version)
    if "REVIEW" not in VERSION_ALLOWED_TRANSITIONS.get(version.state, set()):
        raise InvalidTransitionError("Illegal document version transition", current_state=version.state, requested="REVIEW")
    if not cmd.reviewers:
        raise ValidationFailedError("At least one reviewer is required")

    document = await session.get(ControlledDocument, version.document_id)

    old_state = version.state
    version.review_workflow = {"reviewers": cmd.reviewers, "completed": False}
    version.state = "REVIEW"
    version.version += 1

    return await _write_version_receipt(
        session, cmd=cmd, payload_hash=payload_hash, version=version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="DocumentVersionReleased",
        event_payload={"id": str(version.id), "state": "REVIEW"}, signature_id=None,
        expected_version=cmd.expected_version, command_type="SubmitDocumentDraft", site_id=document.site_id,
    )


# ---------------------------------------------------------------------------
# Release — DOC-FR-006 (signed)/015
# ---------------------------------------------------------------------------


class ReleaseDocumentDraftCommand(CommandEnvelope):
    document_version_id: uuid.UUID
    expected_version: int
    review_completed: bool = False
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    change_control_id: uuid.UUID | None = None
    training_impact: dict | None = None
    acknowledgment_required: bool = False
    periodic_review_due: datetime | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def release_draft(session: AsyncSession, cmd: ReleaseDocumentDraftCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_version_for_update(session, cmd.document_version_id, cmd.expected_version)
    if "RELEASED" not in VERSION_ALLOWED_TRANSITIONS.get(version.state, set()):
        raise InvalidTransitionError("Illegal document version transition", current_state=version.state, requested="RELEASED")
    if not version.review_workflow or not cmd.review_completed:
        raise DocumentReviewIncompleteError("Review must be recorded and confirmed complete before release")

    document = await session.get(ControlledDocument, version.document_id)
    if cmd.change_control_id is not None:
        await change_service.get_change(session, cmd.change_control_id)  # DOC-FR-015: real FK, validated to exist

    policy = await signature_service.resolve_signature_requirement(session, record_type="controlled_document_version", action="release")
    signature_id = None
    if policy.signature_required:
        if cmd.challenge_id is None or not cmd.reauth_password:
            raise DocumentSignatureRequiredError("Releasing a document version requires a signature", required_meaning=policy.meaning)
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise DocumentSignatureRequiredError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id, record_version=version.version,
            record_hash=_record_hash(version),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    old_state = version.state
    version.review_workflow = {**version.review_workflow, "completed": True}
    version.effective_from = cmd.effective_from
    version.effective_to = cmd.effective_to
    version.change_control_id = cmd.change_control_id
    version.training_impact = cmd.training_impact
    version.acknowledgment_required = cmd.acknowledgment_required
    version.periodic_review_due = cmd.periodic_review_due
    version.state = "RELEASED"
    version.version += 1

    vault_object = await vault_service.release_master(
        session, object_type="controlled_document_version", business_id=document.document_code, site_id=document.site_id,
        actor_user_id=actor_user_id, business_version_label=version.version_label,
        canonical_payload={
            "document_code": document.document_code, "version_label": version.version_label,
            "content_hash": version.content_hash, "rendition_hash": version.rendition_hash,
            "signature_id": str(signature_id) if signature_id else None,
        },
    )
    version.vault_object_id = vault_object.object_id

    return await _write_version_receipt(
        session, cmd=cmd, payload_hash=payload_hash, version=version, action="Released", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="DocumentVersionReleased",
        event_payload={"id": str(version.id)}, signature_id=signature_id, expected_version=cmd.expected_version,
        command_type="ReleaseDocumentDraft", site_id=document.site_id,
    )


# ---------------------------------------------------------------------------
# Make effective — DOC-FR-007/008
# ---------------------------------------------------------------------------


class MakeDocumentVersionEffectiveCommand(CommandEnvelope):
    document_version_id: uuid.UUID
    expected_version: int
    training_confirmed: bool = False
    reason: str | None = None


async def make_effective(session: AsyncSession, cmd: MakeDocumentVersionEffectiveCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_version_for_update(session, cmd.document_version_id, cmd.expected_version)
    if "EFFECTIVE" not in VERSION_ALLOWED_TRANSITIONS.get(version.state, set()):
        raise InvalidTransitionError("Illegal document version transition", current_state=version.state, requested="EFFECTIVE")
    if version.effective_from is not None:
        effective_from = version.effective_from if version.effective_from.tzinfo is not None else version.effective_from.replace(tzinfo=timezone.utc)
        if effective_from > datetime.now(timezone.utc):
            raise EffectivePrerequisitesIncompleteError("effective_from is still in the future")
    if version.training_impact and version.training_impact.get("required") and not cmd.training_confirmed:
        raise EffectivePrerequisitesIncompleteError("training_impact marked training as required and it has not been confirmed complete")

    document = await session.get(ControlledDocument, version.document_id)

    # DOC-FR-008: supersede the document's current EFFECTIVE version, if one exists.
    prior = (
        await session.execute(
            select(ControlledDocumentVersion).where(
                ControlledDocumentVersion.document_id == document.id, ControlledDocumentVersion.state == "EFFECTIVE",
            )
        )
    ).scalar_one_or_none()

    old_state = version.state
    now = datetime.now(timezone.utc)
    version.state = "EFFECTIVE"
    if version.effective_from is None:
        version.effective_from = now
    version.version += 1
    await session.flush()

    if prior is not None:
        prior.state = "SUPERSEDED"
        prior.effective_to = now
        prior.superseded_by_version_id = version.id
        prior.version += 1
        await write_audit_event(
            session, site_id=document.site_id, aggregate_type="controlled_document_version", aggregate_id=prior.id,
            aggregate_version=prior.version, action="Changed", actor_id=actor_user_id, correlation_id=uuid.uuid4(),
            reason="Superseded by a newly effective version", old_value={"state": "EFFECTIVE"}, new_value={"state": "SUPERSEDED"},
        )
        await write_outbox_event(
            session, event_type="DocumentVersionSuperseded", aggregate_type="controlled_document_version", aggregate_id=prior.id,
            aggregate_version=prior.version, payload={"id": str(prior.id), "superseded_by": str(version.id)}, correlation_id=uuid.uuid4(),
        )

    return await _write_version_receipt(
        session, cmd=cmd, payload_hash=payload_hash, version=version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="DocumentVersionEffective",
        event_payload={"id": str(version.id)}, signature_id=None, expected_version=cmd.expected_version,
        command_type="MakeDocumentVersionEffective", site_id=document.site_id,
    )


# ---------------------------------------------------------------------------
# Obsolete — DOC-FR-009/021 (retirement folded in)
# ---------------------------------------------------------------------------


class ObsoleteDocumentVersionCommand(CommandEnvelope):
    document_version_id: uuid.UUID
    expected_version: int
    retirement_reason: str
    retire_document: bool = False
    reason: str | None = None


async def obsolete_version(session: AsyncSession, cmd: ObsoleteDocumentVersionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_version_for_update(session, cmd.document_version_id, cmd.expected_version)
    if "OBSOLETE" not in VERSION_ALLOWED_TRANSITIONS.get(version.state, set()):
        raise InvalidTransitionError("Illegal document version transition", current_state=version.state, requested="OBSOLETE")
    if not cmd.retirement_reason.strip():
        raise ValidationFailedError("retirement_reason is required")

    document = await session.get(ControlledDocument, version.document_id)

    old_state = version.state
    now = datetime.now(timezone.utc)
    version.retirement_reason = cmd.retirement_reason
    version.retired_at = now
    version.state = "OBSOLETE"
    version.version += 1
    if cmd.retire_document:
        document.status = "retired"

    return await _write_version_receipt(
        session, cmd=cmd, payload_hash=payload_hash, version=version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.retirement_reason, old_state=old_state, event_type="DocumentObsoleted",
        event_payload={"id": str(version.id)}, signature_id=None, expected_version=cmd.expected_version,
        command_type="ObsoleteDocumentVersion", site_id=document.site_id,
    )


# ---------------------------------------------------------------------------
# Controlled copies — DOC-FR-010/020(audited via the standard receipt)
# ---------------------------------------------------------------------------


class IssueControlledCopyCommand(CommandEnvelope):
    document_version_id: uuid.UUID
    expected_version: int
    copy_number: str
    recipient: str
    location: str | None = None
    reason: str | None = None


async def issue_controlled_copy(session: AsyncSession, cmd: IssueControlledCopyCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    version = await _load_version_for_update(session, cmd.document_version_id, cmd.expected_version)
    if version.state != "EFFECTIVE":
        raise DocumentVersionObsoleteError("Controlled copies can only be issued against an EFFECTIVE version", current_state=version.state)
    if not cmd.recipient.strip():
        raise ValidationFailedError("recipient is required")

    conflict = (
        await session.execute(
            select(ControlledCopy).where(
                ControlledCopy.document_version_id == version.id, ControlledCopy.copy_number == cmd.copy_number,
            )
        )
    ).scalar_one_or_none()
    if conflict is not None:
        raise ControlledCopyConflictError("copy_number is already in use for this document version", copy_number=cmd.copy_number)

    document = await session.get(ControlledDocument, version.document_id)

    copy = ControlledCopy(
        document_version_id=version.id, copy_number=cmd.copy_number, recipient=cmd.recipient, location=cmd.location,
        issued_by=actor_user_id, status="issued",
    )
    session.add(copy)

    old_state = version.state
    version.version += 1
    await session.flush()

    return await _write_version_receipt(
        session, cmd=cmd, payload_hash=payload_hash, version=version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="ControlledCopyIssued",
        event_payload={"id": str(version.id), "copy_id": str(copy.id), "copy_number": cmd.copy_number},
        signature_id=None, expected_version=cmd.expected_version, command_type="IssueControlledCopy", site_id=document.site_id,
    )
