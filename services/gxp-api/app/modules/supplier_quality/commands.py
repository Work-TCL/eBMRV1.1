import uuid
from datetime import datetime

from pydantic import BaseModel
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.codegen import service as codegen_service
from app.modules.iam.models import User
from app.modules.policy.service import evaluate_policy
from app.modules.signature import service as signature_service
from app.modules.supplier_quality.models import (
    Supplier,
    SupplierQualification,
    SupplierQualificationEvidence,
    SupplierSite,
)
from app.modules.vault.models import VaultObject
from app.mutation.errors import (
    DuplicateSupplierError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import (
    check_idempotency,
    record_command_receipt,
    write_audit_event,
    write_outbox_event,
)
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def qualification_record_hash(qualification: SupplierQualification) -> str:
    return sha256_hex(
        {"id": str(qualification.id), "version": qualification.version, "status": qualification.status}
    )


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


# ---------------------------------------------------------------------------
# CreateSupplier -- SUP-FR-001/002/029: POST /suppliers/v1. Document 18 §7 declares no separate
# site-creation endpoint, so sites are embedded in this one command rather than inventing a new endpoint.
# ---------------------------------------------------------------------------


class SupplierSiteInput(BaseModel):
    site_name: str
    address_line1: str | None = None
    address_line2: str | None = None
    city: str | None = None
    state_province: str | None = None
    postal_code: str | None = None
    country: str | None = None
    manufacturer_flag: bool = False
    certification_refs: dict | None = None


class CreateSupplierCommand(CommandEnvelope):
    supplier_code: str | None = None
    legal_name: str
    role_type: str  # supplier | manufacturer | both
    country: str | None = None
    external_mappings: dict | None = None
    sites: list[SupplierSiteInput] = []


async def create_supplier(
    session: AsyncSession, cmd: CreateSupplierCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.role_type not in ("supplier", "manufacturer", "both"):
        raise ValidationFailedError("role_type must be 'supplier', 'manufacturer' or 'both'")

    # SUP-FR-029: detect a likely duplicate legal identity before creation. Exact supplier_code
    # collisions are already rejected by the unique constraint; this catches the same legal entity
    # proposed under a different code.
    normalized_name = " ".join(cmd.legal_name.strip().lower().split())
    dup_stmt = select(Supplier).where(func.lower(Supplier.legal_name) == normalized_name)
    if cmd.country:
        dup_stmt = dup_stmt.where(Supplier.country == cmd.country)
    duplicate = (await session.execute(dup_stmt)).scalars().first()
    if duplicate is not None:
        raise DuplicateSupplierError(
            "A supplier with this legal name and country already exists",
            existing_supplier_id=str(duplicate.id),
        )

    if cmd.supplier_code and cmd.supplier_code.strip():
        code_conflict = (
            await session.execute(select(Supplier).where(Supplier.supplier_code == cmd.supplier_code))
        ).scalar_one_or_none()
        if code_conflict is not None:
            raise ValidationFailedError("supplier_code is already in use", supplier_code=cmd.supplier_code)
        supplier_code = cmd.supplier_code
    else:
        supplier_code = await codegen_service.next_code(session, entity_type="SUPPLIER", prefix="SUP")

    supplier = Supplier(
        supplier_code=supplier_code,
        legal_name=cmd.legal_name,
        role_type=cmd.role_type,
        status="draft",
        country=cmd.country,
        external_mappings=cmd.external_mappings,
        version=1,
    )
    session.add(supplier)
    await session.flush()

    for site_input in cmd.sites:
        session.add(
            SupplierSite(
                supplier_id=supplier.id,
                site_name=site_input.site_name,
                address_line1=site_input.address_line1,
                address_line2=site_input.address_line2,
                city=site_input.city,
                state_province=site_input.state_province,
                postal_code=site_input.postal_code,
                country=site_input.country,
                manufacturer_flag=site_input.manufacturer_flag,
                certification_refs=site_input.certification_refs,
                status="active",
                version=1,
            )
        )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="supplier",
        aggregate_id=supplier.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"supplier_code": supplier.supplier_code, "legal_name": supplier.legal_name},
    )
    await write_outbox_event(
        session,
        event_type="SupplierCreated",
        aggregate_type="supplier",
        aggregate_id=supplier.id,
        aggregate_version=1,
        payload={"id": str(supplier.id), "supplier_code": supplier.supplier_code},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="CreateSupplier",
        aggregate_type="supplier",
        aggregate_id=supplier.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=supplier.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CreateSupplierQualification -- SUP-FR-003/004/005/009/013: POST /suppliers/{id}/qualifications.
# ---------------------------------------------------------------------------


class QualificationEvidenceInput(BaseModel):
    vault_object_id: uuid.UUID
    evidence_category: str


class CreateSupplierQualificationCommand(CommandEnvelope):
    supplier_id: uuid.UUID
    supplier_site_id: uuid.UUID
    scope: dict | None = None
    risk_class: str | None = None
    effective_from: datetime | None = None
    expires_at: datetime | None = None
    quality_agreement_vault_id: uuid.UUID | None = None
    evidence: list[QualificationEvidenceInput] = []


async def create_supplier_qualification(
    session: AsyncSession, cmd: CreateSupplierQualificationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    supplier = await session.get(Supplier, cmd.supplier_id)
    if supplier is None:
        raise NotFoundError("Supplier not found")
    if supplier.status == "disqualified":
        raise InvalidTransitionError(
            "A disqualified supplier cannot be requalified through this path",
            current_status=supplier.status,
        )

    site = await session.get(SupplierSite, cmd.supplier_site_id)
    if site is None or site.supplier_id != supplier.id:
        raise NotFoundError("Supplier site not found for this supplier")

    if cmd.quality_agreement_vault_id is not None:
        vault_obj = await session.get(VaultObject, cmd.quality_agreement_vault_id)
        if vault_obj is None:
            raise NotFoundError("quality_agreement_vault_id does not reference an existing vault object")

    qualification = SupplierQualification(
        supplier_site_id=site.id,
        requested_by_user_id=actor_user_id,
        scope=cmd.scope,
        risk_class=cmd.risk_class,
        status="requested",
        effective_from=cmd.effective_from,
        expires_at=cmd.expires_at,
        quality_agreement_vault_id=cmd.quality_agreement_vault_id,
        version=1,
    )
    session.add(qualification)
    await session.flush()

    for evidence_input in cmd.evidence:
        evidence_vault_obj = await session.get(VaultObject, evidence_input.vault_object_id)
        if evidence_vault_obj is None:
            raise NotFoundError(
                "Evidence vault_object_id does not reference an existing vault object",
                vault_object_id=str(evidence_input.vault_object_id),
            )
        session.add(
            SupplierQualificationEvidence(
                supplier_qualification_id=qualification.id,
                vault_object_id=evidence_input.vault_object_id,
                evidence_category=evidence_input.evidence_category,
            )
        )

    old_supplier_status = supplier.status
    if supplier.status in ("draft", "approved", "suspended"):
        supplier.status = "under_qualification"
    supplier.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="supplier_qualification",
        aggregate_id=qualification.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"supplier_id": str(supplier.id), "status": qualification.status},
    )
    await write_audit_event(
        session,
        site_id=None,
        aggregate_type="supplier",
        aggregate_id=supplier.id,
        aggregate_version=supplier.version,
        action="StatusChanged",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"status": old_supplier_status},
        new_value={"status": supplier.status},
    )
    await write_outbox_event(
        session,
        event_type="SupplierQualificationRequested",
        aggregate_type="supplier_qualification",
        aggregate_id=qualification.id,
        aggregate_version=1,
        payload={"id": str(qualification.id), "supplier_id": str(supplier.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="CreateSupplierQualification",
        aggregate_type="supplier_qualification",
        aggregate_id=qualification.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=qualification.id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ApproveSupplierQualification -- SUP-FR-007 (approval)/009 (requalification->approval)/012 (conditional):
# POST /supplier-qualifications/{id}/approve. Signed per Document 106 row 43 (meaning "Approved", 1
# signature, independent of the requester). `decision` also carries "rejected", the same way
# `disposition_material_lot` handles both released/rejected under one signed endpoint.
# ---------------------------------------------------------------------------


class ApproveSupplierQualificationCommand(CommandEnvelope):
    qualification_id: uuid.UUID
    expected_version: int
    decision: str  # "approved" | "conditional" | "rejected"
    justification: str | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_supplier_qualification(
    session: AsyncSession,
    cmd: ApproveSupplierQualificationCommand,
    actor_user_id: uuid.UUID,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.decision not in ("approved", "conditional", "rejected"):
        raise ValidationFailedError("decision must be 'approved', 'conditional' or 'rejected'")
    if cmd.decision == "conditional" and not cmd.justification:
        raise ValidationFailedError("conditional approval requires a justification (SUP-FR-012)")

    result = await session.execute(
        select(SupplierQualification)
        .where(SupplierQualification.id == cmd.qualification_id)
        .with_for_update()
    )
    qualification = result.scalar_one_or_none()
    if qualification is None:
        raise NotFoundError("Supplier qualification not found")
    if qualification.version != cmd.expected_version:
        raise StaleVersionError(
            "Supplier qualification was modified by another actor since it was read",
            expected_version=cmd.expected_version,
            current_version=qualification.version,
        )
    if qualification.status not in ("requested", "in_review"):
        raise InvalidTransitionError(
            "Only a requested or in-review qualification can be approved",
            current_status=qualification.status,
        )

    await evaluate_policy(session, actor_user_id, action="supplier_qualification.approve", site_id=None)
    if actor_user_id == qualification.requested_by_user_id:
        raise InvalidTransitionError(
            "Approver must be independent of the requester for this qualification (SoD)"
        )

    policy = await signature_service.resolve_signature_requirement(
        session, record_type="supplier_qualification", action="approve"
    )
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session,
            challenge_id=cmd.challenge_id,
            user_id=actor_user_id,
            record_version=qualification.version,
            record_hash=qualification_record_hash(qualification),
        )
        signature = await signature_service.sign(
            session, challenge=challenge, auth_context={"method": "password_reauth"}
        )
        signature_id = signature.id

    site = await session.get(SupplierSite, qualification.supplier_site_id)
    supplier = await session.get(Supplier, site.supplier_id)

    old_status = qualification.status
    qualification.status = cmd.decision
    qualification.justification = cmd.justification
    qualification.version += 1

    old_supplier_status = supplier.status
    if cmd.decision in ("approved", "conditional"):
        supplier.status = "approved"
    supplier.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="supplier_qualification",
        aggregate_id=qualification.id,
        aggregate_version=qualification.version,
        action="Approved" if cmd.decision != "rejected" else "Rejected",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"status": old_status},
        new_value={"status": qualification.status},
        signature_id=signature_id,
        reason=cmd.justification,
    )
    await write_audit_event(
        session,
        site_id=None,
        aggregate_type="supplier",
        aggregate_id=supplier.id,
        aggregate_version=supplier.version,
        action="StatusChanged",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"status": old_supplier_status},
        new_value={"status": supplier.status},
        signature_id=signature_id,
    )
    if cmd.decision in ("approved", "conditional"):
        await write_outbox_event(
            session,
            event_type="SupplierQualificationApproved",
            aggregate_type="supplier_qualification",
            aggregate_id=qualification.id,
            aggregate_version=qualification.version,
            payload={
                "id": str(qualification.id),
                "supplier_id": str(supplier.id),
                "decision": cmd.decision,
            },
            correlation_id=correlation_id,
        )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="ApproveSupplierQualification",
        aggregate_type="supplier_qualification",
        aggregate_id=qualification.id,
        expected_version=cmd.expected_version,
        resulting_version=qualification.version,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=qualification.id,
        resulting_version=qualification.version,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )
