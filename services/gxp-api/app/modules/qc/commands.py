import uuid
from datetime import datetime, timezone

from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.batch_execution.models import Batch, BatchStep
from app.modules.device.models import DeviceUnit
from app.modules.equipment.cleaning_models import CleaningExecution
from app.modules.iam.models import User
from app.modules.material.models import MaterialLot
from app.modules.policy.service import evaluate_policy
from app.modules.product_master.models import ProductVersion
from app.modules.qc.models import (
    BUILDABLE_SCOPE_TYPES,
    OosInvestigationActivity,
    OosRecord,
    OosResamplePlan,
    OosRetestPlan,
    OotRecord,
    QcMethodVersion,
    QcResult,
    QcResultCorrection,
    QcSample,
    QcTestDefinition,
    QcTestOrder,
    QcTestRun,
    QcTestSpecification,
)
from app.modules.recipe_master.models import RecipeVersion
from app.modules.rules import commands as rules_commands
from app.modules.rules import service as rules_service
from app.modules.signature import service as signature_service
from app.modules.vault import service as vault_service
from app.mutation.errors import (
    ImpactAssessmentRequiredError,
    InvalidTransitionError,
    InvestigationIncompleteError,
    LabCauseEvidenceRequiredError,
    MissingSignatureError,
    NotFoundError,
    OosAlreadyExistsError,
    OotRuleNotReleasedError,
    OriginalResultRequiredError,
    QaApprovalRequiredError,
    RawDataRequiredError,
    ResampleNotAuthorizedError,
    RetestNotAuthorizedError,
    StaleVersionError,
    TestSpecNotEffectiveError,
    UomUnknownError,
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

SOURCE_TABLE_BY_TYPE = {
    "material_lot": MaterialLot,
    "batch": Batch,
    "batch_step": BatchStep,
    "device_unit": DeviceUnit,
    # CLN-FR-010 (Document 39): swab/rinse samples drawn during cleaning verification.
    "cleaning_execution": CleaningExecution,
}
SCOPE_TABLE_BY_TYPE = {
    "product": ProductVersion,
    "device": ProductVersion,
    "in_process": RecipeVersion,
}


async def _resolve_uom_id(session: AsyncSession, uom: str | None) -> uuid.UUID | None:
    """SG-146 (remainder), MIG-FR-004 expand step: best-effort dual-write onto the Document 110 §3
    controlled UOM master, same discipline as `app.modules.yield_reconciliation.commands._resolve_uom_id`.
    `uom` (the free-text column) stays authoritative; an unresolved code leaves `uom_id` NULL rather than
    rejecting the write. `qc_test_definition`/`qc_result` have no UPDATE grant (append-only, AG-08), so
    for those two tables this is the *only* place `uom_id` is ever set -- there is no backfill path."""
    if not uom:
        return None
    try:
        row = await rules_service.resolve_uom(session, uom)
    except UomUnknownError:
        return None
    return row.uom_id


def _record_hash(obj, *fields: str, version_field: str = "version") -> str:
    return sha256_hex({f: str(getattr(obj, f)) for f in ("id", version_field, *fields)})


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


# ---------------------------------------------------------------------------
# CreateTestSpecificationDraft -- QC-FR-001/002: POST /qc/v1/specifications/drafts. scope_type=="material"
# is rejected -- SG-057/SG-063, no material-specification-version entity exists anywhere in this codebase.
# ---------------------------------------------------------------------------


class TestDefinitionInput(BaseModel):
    test_code: str
    test_name: str
    method_version: str | None = None
    method_version_id: uuid.UUID | None = None
    result_data_type: str
    uom: str | None = None
    acceptance_rule_business_id: str | None = None
    trend_rule_business_id: str | None = None
    required: bool = True
    release_blocking: bool = True
    review_policy: str | None = None


class CreateTestSpecificationDraftCommand(CommandEnvelope):
    spec_code: str
    scope_type: str
    scope_version_id: uuid.UUID
    sampling_plan: dict | None = None
    test_definitions: list[TestDefinitionInput] = []


async def create_test_specification_draft(
    session: AsyncSession, cmd: CreateTestSpecificationDraftCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.scope_type == "material":
        raise ValidationFailedError(
            "scope_type='material' is not supported: no material-specification-version entity exists "
            "yet in this codebase (SG-057/SG-063)",
            scope_type=cmd.scope_type,
        )
    if cmd.scope_type not in BUILDABLE_SCOPE_TYPES:
        raise ValidationFailedError("Unknown scope_type", scope_type=cmd.scope_type)

    scope_table = SCOPE_TABLE_BY_TYPE[cmd.scope_type]
    if await session.get(scope_table, cmd.scope_version_id) is None:
        raise NotFoundError("scope_version_id does not reference an existing version", scope_type=cmd.scope_type)

    next_version = 1
    existing_versions = (
        await session.execute(select(QcTestSpecification.version_no).where(QcTestSpecification.spec_code == cmd.spec_code))
    ).scalars().all()
    if existing_versions:
        next_version = max(existing_versions) + 1

    spec = QcTestSpecification(
        spec_code=cmd.spec_code,
        version_no=next_version,
        scope_type=cmd.scope_type,
        scope_version_id=cmd.scope_version_id,
        status="draft",
        sampling_plan=cmd.sampling_plan,
        version=1,
    )
    session.add(spec)
    await session.flush()

    for td in cmd.test_definitions:
        if td.method_version_id is not None and (await session.get(QcMethodVersion, td.method_version_id)) is None:
            raise NotFoundError(
                "test_definition references an unknown method_version_id", method_version_id=str(td.method_version_id)
            )
        session.add(
            QcTestDefinition(
                specification_id=spec.id,
                test_code=td.test_code,
                test_name=td.test_name,
                method_version=td.method_version,
                method_version_id=td.method_version_id,
                result_data_type=td.result_data_type,
                uom=td.uom,
                uom_id=await _resolve_uom_id(session, td.uom),
                acceptance_rule_business_id=td.acceptance_rule_business_id,
                trend_rule_business_id=td.trend_rule_business_id,
                required=td.required,
                release_blocking=td.release_blocking,
                review_policy=td.review_policy,
            )
        )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="qc_test_specification",
        aggregate_id=spec.id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"spec_code": spec.spec_code, "version_no": spec.version_no, "scope_type": spec.scope_type},
    )
    await write_outbox_event(
        session,
        event_type="QCTestSpecificationDrafted",
        aggregate_type="qc_test_specification",
        aggregate_id=spec.id,
        aggregate_version=1,
        payload={"id": str(spec.id), "spec_code": spec.spec_code},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="CreateTestSpecificationDraft",
        aggregate_type="qc_test_specification",
        aggregate_id=spec.id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=spec.id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ReleaseTestSpecification -- QC-FR-002: POST /qc/v1/specifications/{id}/release. Signed per Document 106
# row 58 (meaning Released, QA Approver/Batch Release role, independent of every production performer).
# ---------------------------------------------------------------------------


class ReleaseTestSpecificationCommand(CommandEnvelope):
    specification_id: uuid.UUID
    expected_version: int
    challenge_id: uuid.UUID
    reauth_password: str


async def release_test_specification(
    session: AsyncSession, cmd: ReleaseTestSpecificationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(
        select(QcTestSpecification).where(QcTestSpecification.id == cmd.specification_id).with_for_update()
    )
    spec = result.scalar_one_or_none()
    if spec is None:
        raise NotFoundError("Test specification not found")
    if spec.version != cmd.expected_version:
        raise StaleVersionError(
            "Test specification was modified since it was read",
            expected_version=cmd.expected_version, current_version=spec.version,
        )
    if spec.status != "draft":
        raise InvalidTransitionError("Only a draft specification can be released", current_status=spec.status)

    await evaluate_policy(session, actor_user_id, action="qc_test_specification.release", site_id=None)

    policy = await signature_service.resolve_signature_requirement(
        session, record_type="qc_test_specification", action="release"
    )
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
            record_version=spec.version, record_hash=_record_hash(spec, "status"),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    definitions = (
        await session.execute(select(QcTestDefinition).where(QcTestDefinition.specification_id == spec.id))
    ).scalars().all()
    vault_obj = await vault_service.release_master(
        session,
        object_type="qc_test_specification",
        business_id=spec.spec_code,
        actor_user_id=actor_user_id,
        canonical_payload={
            "spec_code": spec.spec_code,
            "version_no": spec.version_no,
            "scope_type": spec.scope_type,
            "scope_version_id": str(spec.scope_version_id),
            "test_definitions": [
                {"test_code": d.test_code, "test_name": d.test_name, "required": d.required} for d in definitions
            ],
        },
    )

    old_status = spec.status
    spec.status = "released"
    spec.released_vault_object_id = vault_obj.object_id
    spec.effective_from = datetime.now(timezone.utc)
    spec.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="qc_test_specification", aggregate_id=spec.id,
        aggregate_version=spec.version, action="Released", actor_id=actor_user_id,
        correlation_id=correlation_id, old_value={"status": old_status}, new_value={"status": spec.status},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="QCTestSpecificationReleased", aggregate_type="qc_test_specification",
        aggregate_id=spec.id, aggregate_version=spec.version,
        payload={"id": str(spec.id), "spec_code": spec.spec_code}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="ReleaseTestSpecification", aggregate_type="qc_test_specification",
        aggregate_id=spec.id, expected_version=cmd.expected_version, resulting_version=spec.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=spec.id, resulting_version=spec.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CreateQcMethodDraft / ReleaseQcMethodVersion -- SG-066 (QC-FR-003/004): the Method-master entity
# Document 23 never defines. Mirrors CreateTestSpecificationDraft/ReleaseTestSpecification's own shape,
# RBAC-gated at the router (new qc_method.author/.release actions, not this module's older convention of
# no create-time check -- deliberately the stronger, already-established posture used elsewhere this
# session for every other new master-data entity).
# ---------------------------------------------------------------------------


class CreateQcMethodDraftCommand(CommandEnvelope):
    method_code: str
    method_type: str  # compendial | internal | validated
    name: str
    site_id: uuid.UUID
    validation_evidence_reference: str | None = None
    modification_reason: str | None = None


QC_METHOD_TYPES = ("compendial", "internal", "validated")


async def create_qc_method_draft(
    session: AsyncSession, cmd: CreateQcMethodDraftCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.method_type not in QC_METHOD_TYPES:
        raise ValidationFailedError("Unknown method_type", method_type=cmd.method_type, allowed=list(QC_METHOD_TYPES))

    existing_versions = (
        await session.execute(select(QcMethodVersion.version_no).where(QcMethodVersion.method_code == cmd.method_code))
    ).scalars().all()
    next_version = max(existing_versions) + 1 if existing_versions else 1

    # QC-FR-004: a modification (any version after the first) requires a documented reason; the
    # original method is never edited, only superseded by this new draft.
    if next_version > 1 and not cmd.modification_reason:
        raise ValidationFailedError(
            "modification_reason is required when a new version supersedes an existing method_code",
            method_code=cmd.method_code, version_no=next_version,
        )

    method = QcMethodVersion(
        method_code=cmd.method_code,
        version_no=next_version,
        name=cmd.name,
        method_type=cmd.method_type,
        validation_evidence_reference=cmd.validation_evidence_reference,
        modification_reason=cmd.modification_reason,
        site_id=cmd.site_id,
        lifecycle_state="draft",
    )
    session.add(method)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=cmd.site_id, aggregate_type="qc_method_version", aggregate_id=method.id,
        aggregate_version=1, action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"method_code": method.method_code, "version_no": method.version_no},
    )
    await write_outbox_event(
        session, event_type="QcMethodVersionCreated", aggregate_type="qc_method_version",
        aggregate_id=method.id, aggregate_version=1,
        payload={"id": str(method.id), "method_code": method.method_code}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=cmd.site_id, command_type="CreateQcMethodDraft", aggregate_type="qc_method_version",
        aggregate_id=method.id, expected_version=None, resulting_version=1,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=method.id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


class ReleaseQcMethodVersionCommand(CommandEnvelope):
    method_version_id: uuid.UUID
    expected_version: int
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def release_qc_method_version(
    session: AsyncSession, cmd: ReleaseQcMethodVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    method = await session.get(QcMethodVersion, cmd.method_version_id)
    if method is None:
        raise NotFoundError("QC method version not found")
    if method.version != cmd.expected_version:
        raise StaleVersionError(
            "QC method version was modified since it was read",
            expected_version=cmd.expected_version, current_version=method.version,
        )
    if method.lifecycle_state != "draft":
        raise InvalidTransitionError("Only a draft QC method version can be released", current_state=method.lifecycle_state)

    # SG-186 RESOLVED (2026-09-18, project-owner-directed): "Released" by an independent QA Releaser,
    # mirroring qc_test_specification/release (Document 106 row 58) -- the nearest in-module precedent,
    # which itself enforces no bespoke independence check (no single stored "performer" identity to check
    # against; RBAC (qc_method.release: Admin/QA Releaser only) + the signature ceremony are the whole
    # enforcement surface, same as its precedent).
    policy = await signature_service.resolve_signature_requirement(
        session, record_type="qc_method_version", action="release"
    )

    signature_id = None
    if policy.signature_required:
        if cmd.challenge_id is None or not cmd.reauth_password:
            raise MissingSignatureError("Releasing a QC method version requires a signature", required_meaning=policy.meaning)
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
            record_version=method.version, record_hash=_record_hash(method, "lifecycle_state"),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    old_state = method.lifecycle_state
    method.lifecycle_state = "released"
    method.effective_from = datetime.now(timezone.utc)
    method.version += 1

    vault_object = await vault_service.release_master(
        session, object_type="qc_method_version", business_id=method.method_code,
        site_id=method.site_id, actor_user_id=actor_user_id, business_version_label=str(method.version_no),
        canonical_payload={
            "method_code": method.method_code, "version_no": method.version_no, "name": method.name,
            "method_type": method.method_type,
            "validation_evidence_reference": method.validation_evidence_reference,
            "modification_reason": method.modification_reason,
            "signature_id": str(signature_id) if signature_id else None,
        },
    )
    method.released_vault_object_id = vault_object.object_id
    method.version_hash = vault_object.digest

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=method.site_id, aggregate_type="qc_method_version", aggregate_id=method.id,
        aggregate_version=method.version, action="Released", actor_id=actor_user_id,
        correlation_id=correlation_id, old_value={"lifecycle_state": old_state},
        new_value={"lifecycle_state": method.lifecycle_state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="QcMethodVersionReleased", aggregate_type="qc_method_version",
        aggregate_id=method.id, aggregate_version=method.version,
        payload={"id": str(method.id), "method_code": method.method_code}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=method.site_id, command_type="ReleaseQcMethodVersion", aggregate_type="qc_method_version",
        aggregate_id=method.id, expected_version=cmd.expected_version, resulting_version=method.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=method.id, resulting_version=method.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CreateSample / ReceiveSample -- QC-FR-005..009.
# ---------------------------------------------------------------------------


class CreateSampleCommand(CommandEnvelope):
    sample_number: str
    sample_type: str
    source_type: str
    source_id: uuid.UUID | None = None
    source_location_ref: str | None = None
    lot_batch_serial_ref: str | None = None
    sample_quantity: str | None = None
    sample_uom: str | None = None
    sampled_at: datetime | None = None
    stability_study_ref: str | None = None


async def create_sample(session: AsyncSession, cmd: CreateSampleCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    # 2026-09-18: qc_sample.create is enforced at the router (post_create_sample), not here -- this
    # function is also called internally by material/commands.py::collect_sample() and
    # equipment/cleaning_commands.py/lims_integration/commands.py's own already-authorized flows, which
    # must not be blocked by a permission check meant for the direct "log a new QC sample" action.
    if cmd.source_id is not None and cmd.source_type in SOURCE_TABLE_BY_TYPE:
        table = SOURCE_TABLE_BY_TYPE[cmd.source_type]
        if await session.get(table, cmd.source_id) is None:
            raise NotFoundError("source_id does not reference an existing record", source_type=cmd.source_type)

    sample = QcSample(
        sample_number=cmd.sample_number,
        sample_type=cmd.sample_type,
        source_type=cmd.source_type,
        source_id=cmd.source_id,
        source_location_ref=cmd.source_location_ref,
        lot_batch_serial_ref=cmd.lot_batch_serial_ref,
        sample_quantity=cmd.sample_quantity,
        sample_uom=cmd.sample_uom,
        sample_uom_id=await _resolve_uom_id(session, cmd.sample_uom),
        sampled_at=cmd.sampled_at,
        sampler_subject_id=actor_user_id,
        state="collected" if cmd.sampled_at else "planned",
        stability_study_ref=cmd.stability_study_ref,
        version=1,
    )
    session.add(sample)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="qc_sample", aggregate_id=sample.id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"sample_number": sample.sample_number, "state": sample.state},
    )
    await write_outbox_event(
        session, event_type="QCSampleCreated", aggregate_type="qc_sample", aggregate_id=sample.id,
        aggregate_version=1, payload={"id": str(sample.id), "sample_number": sample.sample_number},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="CreateSample", aggregate_type="qc_sample", aggregate_id=sample.id,
        expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=sample.id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


class ReceiveSampleCommand(CommandEnvelope):
    sample_id: uuid.UUID
    expected_version: int


async def receive_sample(session: AsyncSession, cmd: ReceiveSampleCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(QcSample).where(QcSample.id == cmd.sample_id).with_for_update())
    sample = result.scalar_one_or_none()
    if sample is None:
        raise NotFoundError("Sample not found")
    if sample.version != cmd.expected_version:
        raise StaleVersionError(
            "Sample was modified since it was read", expected_version=cmd.expected_version, current_version=sample.version
        )
    if sample.state not in ("planned", "collected"):
        raise InvalidTransitionError("Only a planned or collected sample can be received", current_status=sample.state)

    # 2026-09-18: qc_sample.receive is enforced at the router (post_receive_sample), not here -- also
    # called internally by lims_integration/commands.py's already-authorized LIMS ingestion flow.
    old_state = sample.state
    sample.state = "received"
    sample.received_at = datetime.now(timezone.utc)
    sample.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="qc_sample", aggregate_id=sample.id, aggregate_version=sample.version,
        action="StatusChanged", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": sample.state},
    )
    await write_outbox_event(
        session, event_type="QCSampleReceived", aggregate_type="qc_sample", aggregate_id=sample.id,
        aggregate_version=sample.version, payload={"id": str(sample.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="ReceiveSample", aggregate_type="qc_sample", aggregate_id=sample.id,
        expected_version=cmd.expected_version, resulting_version=sample.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=sample.id, resulting_version=sample.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CancelSample -- not a Document 23 requirement itself; a generic QcSample lifecycle capability the
# owning module (this one) exposes for callers that need to cancel a sample (Document 24's
# LIMS-FR-021 is the first caller). Unsigned here -- Document 106 has no row for qc_sample/cancel;
# LIMS-FR-021's own signature requirement (Doc 106 row 64) is enforced by the caller (lims_integration)
# against its own record_type before this function ever runs.
# ---------------------------------------------------------------------------


class CancelSampleCommand(CommandEnvelope):
    sample_id: uuid.UUID
    expected_version: int
    reason: str


async def cancel_sample(session: AsyncSession, cmd: CancelSampleCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(QcSample).where(QcSample.id == cmd.sample_id).with_for_update())
    sample = result.scalar_one_or_none()
    if sample is None:
        raise NotFoundError("Sample not found")
    if sample.version != cmd.expected_version:
        raise StaleVersionError(
            "Sample was modified since it was read", expected_version=cmd.expected_version, current_version=sample.version
        )
    if sample.state in ("testing_complete", "disposed", "cancelled"):
        raise InvalidTransitionError("Sample is not in a cancellable state", current_status=sample.state)

    blocking_reviewed = (
        await session.execute(
            select(QcTestOrder.id).where(
                QcTestOrder.sample_id == sample.id, QcTestOrder.blocking.is_(True), QcTestOrder.state == "reviewed"
            )
        )
    ).scalars().first()
    if blocking_reviewed is not None:
        raise InvalidTransitionError(
            "Sample has a reviewed release-blocking test order and cannot be cancelled"
        )

    old_state = sample.state
    sample.state = "cancelled"
    sample.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="qc_sample", aggregate_id=sample.id, aggregate_version=sample.version,
        action="StatusChanged", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": sample.state}, reason=cmd.reason,
    )
    await write_outbox_event(
        session, event_type="QCSampleCancelled", aggregate_type="qc_sample", aggregate_id=sample.id,
        aggregate_version=sample.version, payload={"id": str(sample.id), "reason": cmd.reason}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="CancelSample", aggregate_type="qc_sample", aggregate_id=sample.id,
        expected_version=cmd.expected_version, resulting_version=sample.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=sample.id, resulting_version=sample.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CreateTestOrder / StartTestOrder -- QC-FR-010/011.
# ---------------------------------------------------------------------------


class CreateTestOrderCommand(CommandEnvelope):
    sample_id: uuid.UUID
    test_definition_id: uuid.UUID
    assigned_analyst_id: uuid.UUID | None = None


async def create_test_order(session: AsyncSession, cmd: CreateTestOrderCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    sample = await session.get(QcSample, cmd.sample_id)
    if sample is None:
        raise NotFoundError("Sample not found")
    if sample.state != "received":
        raise InvalidTransitionError("Only a received sample is eligible for a test order", current_status=sample.state)

    await evaluate_policy(session, actor_user_id, action="qc_test_order.create", site_id=None)

    definition = await session.get(QcTestDefinition, cmd.test_definition_id)
    if definition is None:
        raise NotFoundError("Test definition not found")
    spec = await session.get(QcTestSpecification, definition.specification_id)
    if spec is None or spec.status != "released":
        raise TestSpecNotEffectiveError("Test definition's specification is not released")

    order = QcTestOrder(
        sample_id=sample.id,
        test_definition_id=definition.id,
        assigned_analyst_id=cmd.assigned_analyst_id,
        state="assigned" if cmd.assigned_analyst_id else "created",
        blocking=definition.release_blocking,
        version=1,
    )
    session.add(order)
    if sample.state == "received":
        sample.state = "in_testing"
        sample.version += 1
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="qc_test_order", aggregate_id=order.id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"sample_id": str(sample.id), "test_definition_id": str(definition.id)},
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="CreateTestOrder", aggregate_type="qc_test_order", aggregate_id=order.id,
        expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=order.id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


class StartTestOrderCommand(CommandEnvelope):
    test_order_id: uuid.UUID
    expected_version: int
    analyst_id: uuid.UUID | None = None


async def start_test_order(session: AsyncSession, cmd: StartTestOrderCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(QcTestOrder).where(QcTestOrder.id == cmd.test_order_id).with_for_update())
    order = result.scalar_one_or_none()
    if order is None:
        raise NotFoundError("Test order not found")
    if order.version != cmd.expected_version:
        raise StaleVersionError(
            "Test order was modified since it was read", expected_version=cmd.expected_version, current_version=order.version
        )
    if order.state not in ("created", "assigned"):
        raise InvalidTransitionError("Only a created or assigned test order can be started", current_status=order.state)

    # 2026-09-18: qc_test_order.start is enforced at the router (post_start_test_order), not here --
    # also called internally by lims_integration/commands.py's already-authorized LIMS ingestion flow.
    old_state = order.state
    if cmd.analyst_id is not None:
        order.assigned_analyst_id = cmd.analyst_id
    order.state = "in_progress"
    order.started_at = datetime.now(timezone.utc)
    order.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="qc_test_order", aggregate_id=order.id, aggregate_version=order.version,
        action="StatusChanged", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": order.state},
    )
    await write_outbox_event(
        session, event_type="QCTestStarted", aggregate_type="qc_test_order", aggregate_id=order.id,
        aggregate_version=order.version, payload={"id": str(order.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="StartTestOrder", aggregate_type="qc_test_order", aggregate_id=order.id,
        expected_version=cmd.expected_version, resulting_version=order.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=order.id, resulting_version=order.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# RecordRawData -- QC-FR-013..017: POST /qc/v1/test-orders/{id}/raw-data.
# ---------------------------------------------------------------------------


class RecordRawDataCommand(CommandEnvelope):
    test_order_id: uuid.UUID
    method_version: str | None = None
    instrument_ref: str | None = None
    sample_amount: str | None = None
    reference_standards: dict | None = None
    system_suitability: dict | None = None
    raw_evidence_vault_ids: list[str] = []


async def record_raw_data(session: AsyncSession, cmd: RecordRawDataCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    order = await session.get(QcTestOrder, cmd.test_order_id)
    if order is None:
        raise NotFoundError("Test order not found")
    if order.state not in ("in_progress",):
        raise InvalidTransitionError("Test order must be in_progress to record raw data", current_status=order.state)

    # 2026-09-18: qc_test_order.record_raw_data is enforced at the router (post_record_raw_data), not
    # here -- also called internally by lims_integration/commands.py's already-authorized flow.
    run = QcTestRun(
        test_order_id=order.id,
        method_version=cmd.method_version,
        instrument_ref=cmd.instrument_ref,
        analyst_id=actor_user_id,
        sample_amount=cmd.sample_amount,
        reference_standards=cmd.reference_standards,
        system_suitability=cmd.system_suitability,
        raw_evidence_vault_ids={"ids": cmd.raw_evidence_vault_ids},
        version=1,
    )
    session.add(run)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="qc_test_run", aggregate_id=run.id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"test_order_id": str(order.id), "instrument_ref": cmd.instrument_ref},
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="RecordRawData", aggregate_type="qc_test_run", aggregate_id=run.id,
        expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=run.id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# RecordResult -- QC-FR-018..020/025/026/032/033: POST /qc/v1/test-orders/{id}/results. Not signed this
# pass (Doc 106: only if the step is flagged critical -- no such flag exists in this document's own data
# model). Acceptance/trend rules are resolved and evaluated via the existing `rules` module -- no rule
# released for a test definition means the result stays "pending" (QC-FR-019's own valid state), not a
# silent pass.
# ---------------------------------------------------------------------------


class RecordResultCommand(CommandEnvelope):
    test_order_id: uuid.UUID
    test_run_id: uuid.UUID
    result_type: str
    value_decimal: str | None = None
    value_text: str | None = None
    value_json: dict | None = None
    uom: str | None = None


async def _evaluate_acceptance(
    session: AsyncSession, *, rule_business_id: str | None, inputs: dict, aggregate_id: uuid.UUID, actor_user_id: uuid.UUID
) -> tuple[str, uuid.UUID | None]:
    """Returns (outcome, resolved_rule_object_id). outcome in {'pending','pass','oos'}."""
    if not rule_business_id:
        return "pending", None
    try:
        rule = await rules_service.get_effective_released_rule(session, rule_business_id)
    except NotFoundError:
        return "pending", None
    receipt = await rules_commands.evaluate_rule(
        session,
        rules_commands.EvaluateRuleCommand(
            idempotency_key=str(uuid.uuid4()), rule_id=rule_business_id, inputs=inputs,
            aggregate_type="qc_result", aggregate_id=aggregate_id, aggregate_version=1,
        ),
        actor_user_id,
    )
    from app.modules.rules.models import RuleEvaluation

    evaluation = await session.get(RuleEvaluation, receipt.aggregate_id)
    outcome = "pass" if evaluation.outcome == "PASS" else "oos" if evaluation.outcome == "FAIL" else "pending"
    return outcome, rule.rule_object_id


async def record_result(session: AsyncSession, cmd: RecordResultCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    order = await session.get(QcTestOrder, cmd.test_order_id)
    if order is None:
        raise NotFoundError("Test order not found")
    run = await session.get(QcTestRun, cmd.test_run_id)
    if run is None or run.test_order_id != order.id:
        raise NotFoundError("Test run not found for this test order")

    # 2026-09-18: qc_result.record is enforced at the router (post_record_result), not here -- also
    # called internally by lims_integration/commands.py's already-authorized flow.
    definition = await session.get(QcTestDefinition, order.test_definition_id)

    # qc_result is append-only (no UPDATE grant, AG-08) -- every field, including the classification
    # outcome, must be resolved before the single INSERT below, never set on an already-flushed row.
    result_id = uuid.uuid4()
    inputs = {"value": cmd.value_decimal or cmd.value_text or cmd.value_json}
    outcome, acceptance_rule_id = await _evaluate_acceptance(
        session, rule_business_id=definition.acceptance_rule_business_id if definition else None,
        inputs=inputs, aggregate_id=result_id, actor_user_id=actor_user_id,
    )

    oot_flagged = False
    if outcome == "pass" and definition and definition.trend_rule_business_id:
        trend_outcome, _ = await _evaluate_acceptance(
            session, rule_business_id=definition.trend_rule_business_id, inputs=inputs,
            aggregate_id=result_id, actor_user_id=actor_user_id,
        )
        if trend_outcome == "oos":  # trend rule "failed" -> flagged as trending out (QC-FR-026)
            outcome = "oot"
            oot_flagged = True

    result = QcResult(
        id=result_id,
        test_order_id=order.id,
        test_run_id=run.id,
        result_version=1,
        result_type=cmd.result_type,
        value_decimal=cmd.value_decimal,
        value_text=cmd.value_text,
        value_json=cmd.value_json,
        uom=cmd.uom,
        uom_id=await _resolve_uom_id(session, cmd.uom),
        acceptance_rule_id=acceptance_rule_id,
        outcome=outcome,
        recorded_by_user_id=actor_user_id,
    )
    session.add(result)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="qc_result", aggregate_id=result.id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"test_order_id": str(order.id), "outcome": result.outcome},
    )
    await write_outbox_event(
        session, event_type="QCResultRecorded", aggregate_type="qc_result", aggregate_id=result.id,
        aggregate_version=1, payload={"id": str(result.id), "outcome": result.outcome}, correlation_id=correlation_id,
    )
    if result.outcome == "oos" or oot_flagged:
        old_order_state = order.state
        order.state = "oot_pending" if oot_flagged else "oos_pending"
        order.version += 1
        await write_audit_event(
            session, site_id=None, aggregate_type="qc_test_order", aggregate_id=order.id,
            aggregate_version=order.version, action="StatusChanged", actor_id=actor_user_id,
            correlation_id=correlation_id, old_value={"state": old_order_state}, new_value={"state": order.state},
        )
    if result.outcome == "oos":
        await write_outbox_event(
            session, event_type="QCResultOOSDetected", aggregate_type="qc_result", aggregate_id=result.id,
            aggregate_version=1, payload={"id": str(result.id)}, correlation_id=correlation_id,
        )
    if oot_flagged:
        await write_outbox_event(
            session, event_type="QCResultOOTDetected", aggregate_type="qc_result", aggregate_id=result.id,
            aggregate_version=1, payload={"id": str(result.id)}, correlation_id=correlation_id,
        )

    receipt = await record_command_receipt(
        session, site_id=None, command_type="RecordResult", aggregate_type="qc_result", aggregate_id=result.id,
        expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=result.id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CompleteTestOrder -- QC-FR-022/031: POST /qc/v1/test-orders/{id}/complete. Not signed this pass.
# ---------------------------------------------------------------------------


class CompleteTestOrderCommand(CommandEnvelope):
    test_order_id: uuid.UUID
    expected_version: int


async def complete_test_order(session: AsyncSession, cmd: CompleteTestOrderCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(QcTestOrder).where(QcTestOrder.id == cmd.test_order_id).with_for_update())
    order = result.scalar_one_or_none()
    if order is None:
        raise NotFoundError("Test order not found")
    if order.version != cmd.expected_version:
        raise StaleVersionError(
            "Test order was modified since it was read", expected_version=cmd.expected_version, current_version=order.version
        )
    if order.state not in ("in_progress", "oos_pending", "oot_pending"):
        raise InvalidTransitionError("Test order is not in a completable state", current_status=order.state)

    await evaluate_policy(session, actor_user_id, action="qc_test_order.complete", site_id=None)

    definition = await session.get(QcTestDefinition, order.test_definition_id)
    if definition and definition.required:
        has_result = (
            await session.execute(select(QcResult.id).where(QcResult.test_order_id == order.id))
        ).scalars().first()
        if has_result is None:
            raise RawDataRequiredError("Required test has no recorded result")

    old_state = order.state
    order.state = "analyst_complete"
    order.completed_at = datetime.now(timezone.utc)
    order.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="qc_test_order", aggregate_id=order.id, aggregate_version=order.version,
        action="StatusChanged", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": order.state},
    )
    await write_outbox_event(
        session, event_type="QCTestAnalystCompleted", aggregate_type="qc_test_order", aggregate_id=order.id,
        aggregate_version=order.version, payload={"id": str(order.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="CompleteTestOrder", aggregate_type="qc_test_order", aggregate_id=order.id,
        expected_version=cmd.expected_version, resulting_version=order.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=order.id, resulting_version=order.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ReviewTestOrder -- QC-FR-023: POST /qc/v1/test-orders/{id}/review. Signed per Document 106 row 61
# (meaning Reviewed, QA Reviewer, independent of the performer).
# ---------------------------------------------------------------------------


class ReviewTestOrderCommand(CommandEnvelope):
    test_order_id: uuid.UUID
    expected_version: int
    challenge_id: uuid.UUID
    reauth_password: str


async def review_test_order(session: AsyncSession, cmd: ReviewTestOrderCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(QcTestOrder).where(QcTestOrder.id == cmd.test_order_id).with_for_update())
    order = result.scalar_one_or_none()
    if order is None:
        raise NotFoundError("Test order not found")
    if order.version != cmd.expected_version:
        raise StaleVersionError(
            "Test order was modified since it was read", expected_version=cmd.expected_version, current_version=order.version
        )
    if order.state != "analyst_complete":
        raise InvalidTransitionError("Only an analyst-complete test order can be reviewed", current_status=order.state)

    await evaluate_policy(session, actor_user_id, action="qc_test_order.review", site_id=None)
    if actor_user_id == order.assigned_analyst_id:
        raise InvalidTransitionError("Reviewer must be independent of the performer for this test order (SoD)")

    policy = await signature_service.resolve_signature_requirement(session, record_type="qc_test_order", action="review")
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
            record_version=order.version, record_hash=_record_hash(order, "state"),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    old_state = order.state
    order.state = "reviewed"
    order.reviewed_at = datetime.now(timezone.utc)
    order.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="qc_test_order", aggregate_id=order.id, aggregate_version=order.version,
        action="Reviewed", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": order.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="QCTestReviewed", aggregate_type="qc_test_order", aggregate_id=order.id,
        aggregate_version=order.version, payload={"id": str(order.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="ReviewTestOrder", aggregate_type="qc_test_order", aggregate_id=order.id,
        expected_version=cmd.expected_version, resulting_version=order.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=order.id, resulting_version=order.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# RequestResultCorrection / ApproveResultCorrection -- QC-FR-024: POST /qc/v1/results/{id}/correct.
# 2-step, 2-signature per Document 106 row 57 (corrector + independent approver, mandatory reason).
# ---------------------------------------------------------------------------


class RequestResultCorrectionCommand(CommandEnvelope):
    result_id: uuid.UUID
    reason_text: str
    corrected_value_decimal: str | None = None
    corrected_value_text: str | None = None
    corrected_value_json: dict | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def request_result_correction(
    session: AsyncSession, cmd: RequestResultCorrectionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.reason_text:
        raise ValidationFailedError("reason_text is required for a result correction")

    original = await session.get(QcResult, cmd.result_id)
    if original is None:
        raise NotFoundError("Result not found")

    await evaluate_policy(session, actor_user_id, action="qc_result.correct", site_id=None)

    policy = await signature_service.resolve_signature_requirement(session, record_type="qc_result", action="correct")
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
            record_version=original.result_version, record_hash=_record_hash(original, "outcome", version_field="result_version"),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    correction = QcResultCorrection(
        original_result_id=original.id,
        reason_text=cmd.reason_text,
        corrected_value_decimal=cmd.corrected_value_decimal,
        corrected_value_text=cmd.corrected_value_text,
        corrected_value_json=cmd.corrected_value_json,
        status="requested",
        requested_by_user_id=actor_user_id,
        requested_signature_id=signature_id,
    )
    session.add(correction)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="qc_result_correction", aggregate_id=correction.id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"original_result_id": str(original.id)}, reason=cmd.reason_text, signature_id=signature_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="RequestResultCorrection", aggregate_type="qc_result_correction",
        aggregate_id=correction.id, expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=correction.id, resulting_version=1,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


class ApproveResultCorrectionCommand(CommandEnvelope):
    correction_id: uuid.UUID
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_result_correction(
    session: AsyncSession, cmd: ApproveResultCorrectionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    correction = await session.get(QcResultCorrection, cmd.correction_id)
    if correction is None:
        raise NotFoundError("Correction not found")
    if correction.status != "requested":
        raise InvalidTransitionError("Correction is not awaiting approval", current_status=correction.status)
    if actor_user_id == correction.requested_by_user_id:
        raise InvalidTransitionError("Approver must be independent of the corrector for this correction (SoD)")

    original = await session.get(QcResult, correction.original_result_id)

    await evaluate_policy(session, actor_user_id, action="qc_result.correct", site_id=None)

    policy = await signature_service.resolve_signature_requirement(session, record_type="qc_result", action="correct")
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
            record_version=original.result_version, record_hash=_record_hash(original, "outcome", version_field="result_version"),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    new_result = QcResult(
        test_order_id=original.test_order_id,
        test_run_id=original.test_run_id,
        result_version=original.result_version + 1,
        result_type=original.result_type,
        value_decimal=correction.corrected_value_decimal if correction.corrected_value_decimal is not None else original.value_decimal,
        value_text=correction.corrected_value_text if correction.corrected_value_text is not None else original.value_text,
        value_json=correction.corrected_value_json if correction.corrected_value_json is not None else original.value_json,
        uom=original.uom,
        uom_id=original.uom_id,  # UOM itself is never corrected, only the value -- no need to re-resolve
        acceptance_rule_id=original.acceptance_rule_id,
        outcome=original.outcome,
        supersedes_result_id=original.id,
        recorded_by_user_id=actor_user_id,
    )
    session.add(new_result)
    await session.flush()

    correction.status = "completed"
    correction.approved_by_user_id = actor_user_id
    correction.approved_signature_id = signature_id
    correction.resulting_result_id = new_result.id
    correction.completed_at = datetime.now(timezone.utc)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="qc_result_correction", aggregate_id=correction.id, aggregate_version=2,
        action="Approved", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"resulting_result_id": str(new_result.id)}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="QCResultCorrected", aggregate_type="qc_result", aggregate_id=new_result.id,
        aggregate_version=1, payload={"id": str(new_result.id), "supersedes": str(original.id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="ApproveResultCorrection", aggregate_type="qc_result_correction",
        aggregate_id=correction.id, expected_version=None, resulting_version=2, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=new_result.id, resulting_version=1,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ===========================================================================
# Document 25 (SPEC-QC-003) -- OOS/OOT Management. Extends this module (docs/generated/04's owner-service
# entry for all 5 Document 25 entities is `qc`). Signed actions per Document 106 rows 65-69: `from-result`
# unsigned unless critical (no critical flag exists, unsigned), `close`/`disposition`/
# `extended-investigation`/`oot/close` signed. The other 7 declared operations have no Document 106 row --
# unsigned, RBAC-ungated, same precedent as every prior undeclared-signature op this session.
# ===========================================================================


async def _oos_independent_actors(session: AsyncSession, oos: "OosRecord") -> set[uuid.UUID]:
    """Actors who must be excluded from a signer role requiring independence from the
    investigator/owner/production-performer on this OOS (Doc 106 rows 66/67/68)."""
    actors: set[uuid.UUID] = set()
    investigators = (
        await session.execute(
            select(OosInvestigationActivity.investigator_user_id).where(OosInvestigationActivity.oos_record_id == oos.id)
        )
    ).scalars().all()
    actors.update(investigators)
    source_result = await session.get(QcResult, oos.source_result_id)
    if source_result and source_result.recorded_by_user_id:
        actors.add(source_result.recorded_by_user_id)
    return actors


# ---------------------------------------------------------------------------
# OpenOosFromResult -- OOS-FR-001/002: POST /quality/oos/v1/from-result/{resultId}. Unsigned (Doc 106 row
# 65: Performed, unless flagged critical -- no such flag exists in this document's own data model).
# ---------------------------------------------------------------------------


class OpenOosFromResultCommand(CommandEnvelope):
    source_result_id: uuid.UUID
    oos_number: str
    site_id: uuid.UUID | None = None
    severity: str | None = None


async def open_oos_from_result(session: AsyncSession, cmd: OpenOosFromResultCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    source_result = await session.get(QcResult, cmd.source_result_id)
    if source_result is None:
        raise OriginalResultRequiredError("source_result_id does not reference an existing result")

    already_open = (
        await session.execute(select(OosRecord.id).where(OosRecord.source_result_id == cmd.source_result_id))
    ).scalars().first()
    if already_open is not None:
        raise OosAlreadyExistsError("An OOS record already exists for this result", source_result_id=str(cmd.source_result_id))

    conflict = (await session.execute(select(OosRecord.id).where(OosRecord.oos_number == cmd.oos_number))).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError("oos_number is already in use", oos_number=cmd.oos_number)

    order = await session.get(QcTestOrder, source_result.test_order_id)
    sample = await session.get(QcSample, order.sample_id) if order else None
    batch_id = sample.source_id if sample and sample.source_type == "batch" else None
    material_lot_id = sample.source_id if sample and sample.source_type == "material_lot" else None

    oos = OosRecord(
        site_id=cmd.site_id,
        oos_number=cmd.oos_number,
        source_result_id=source_result.id,
        sample_id=sample.id if sample else None,
        test_order_id=order.id if order else None,
        batch_id=batch_id,
        material_lot_id=material_lot_id,
        state="open",
        severity=cmd.severity,
        version=1,
    )
    session.add(oos)
    await session.flush()

    # qc_result is append-only (no UPDATE grant, AG-08) -- oos_record_id is never backfilled onto the
    # already-committed result row. oos_record.source_result_id (set above) is the queryable relationship.

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=cmd.site_id, aggregate_type="oos_record", aggregate_id=oos.id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"oos_number": oos.oos_number, "source_result_id": str(source_result.id)},
    )
    await write_outbox_event(
        session, event_type="OOSOpened", aggregate_type="oos_record", aggregate_id=oos.id,
        aggregate_version=1, payload={"id": str(oos.id), "oos_number": oos.oos_number}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=cmd.site_id, command_type="OpenOosFromResult", aggregate_type="oos_record", aggregate_id=oos.id,
        expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=oos.id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# RecordLabInvestigation -- OOS-FR-004: POST /quality/oos/v1/{id}/lab-investigation. Unsigned.
# ---------------------------------------------------------------------------


class RecordLabInvestigationCommand(CommandEnvelope):
    oos_record_id: uuid.UUID
    expected_version: int
    activity_type: str
    checklist_item: str | None = None
    response_text: str | None = None
    evidence_refs: list[str] = []


async def record_lab_investigation(
    session: AsyncSession, cmd: RecordLabInvestigationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(OosRecord).where(OosRecord.id == cmd.oos_record_id).with_for_update())
    oos = result.scalar_one_or_none()
    if oos is None:
        raise NotFoundError("OOS record not found")
    if oos.version != cmd.expected_version:
        raise StaleVersionError("OOS record was modified since it was read", expected_version=cmd.expected_version, current_version=oos.version)
    if oos.state not in ("open", "lab_investigation"):
        raise InvalidTransitionError("Lab investigation can only be recorded while the OOS is open or under lab investigation", current_status=oos.state)

    await evaluate_policy(session, actor_user_id, action="oos_record.lab_investigation", site_id=oos.site_id)

    activity = OosInvestigationActivity(
        oos_record_id=oos.id, phase="lab_investigation", activity_type=cmd.activity_type,
        checklist_item=cmd.checklist_item, response_text=cmd.response_text,
        evidence_refs={"refs": cmd.evidence_refs}, investigator_user_id=actor_user_id, version=1,
    )
    session.add(activity)

    old_state = oos.state
    oos.state = "lab_investigation"
    oos.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=oos.site_id, aggregate_type="oos_record", aggregate_id=oos.id, aggregate_version=oos.version,
        action="Changed", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": oos.state, "activity_type": cmd.activity_type},
    )
    await write_outbox_event(
        session, event_type="OOSLabInvestigationStarted", aggregate_type="oos_record", aggregate_id=oos.id,
        aggregate_version=oos.version, payload={"id": str(oos.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=oos.site_id, command_type="RecordLabInvestigation", aggregate_type="oos_record", aggregate_id=oos.id,
        expected_version=cmd.expected_version, resulting_version=oos.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=oos.id, resulting_version=oos.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ClassifyLabCause -- OOS-FR-006/007: POST /quality/oos/v1/{id}/classify-lab-cause. Unsigned. Folds the
# diagram's INVALID_TEST_DISPOSITION sub-state into QA_REVIEW on the assignable path -- Document 25's own
# API list has no separate endpoint to trigger that intermediate transition.
# ---------------------------------------------------------------------------


class ClassifyLabCauseCommand(CommandEnvelope):
    oos_record_id: uuid.UUID
    expected_version: int
    assignable: bool
    root_cause_code: str | None = None
    evidence_refs: list[str] = []


async def classify_lab_cause(session: AsyncSession, cmd: ClassifyLabCauseCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(OosRecord).where(OosRecord.id == cmd.oos_record_id).with_for_update())
    oos = result.scalar_one_or_none()
    if oos is None:
        raise NotFoundError("OOS record not found")
    if oos.version != cmd.expected_version:
        raise StaleVersionError("OOS record was modified since it was read", expected_version=cmd.expected_version, current_version=oos.version)
    if oos.state not in ("open", "lab_investigation"):
        raise InvalidTransitionError("Only a newly-opened or under-investigation OOS can be classified", current_status=oos.state)

    await evaluate_policy(session, actor_user_id, action="oos_record.classify_lab_cause", site_id=oos.site_id)

    has_activity = (
        await session.execute(select(OosInvestigationActivity.id).where(OosInvestigationActivity.oos_record_id == oos.id))
    ).scalars().first()
    if has_activity is None:
        raise InvestigationIncompleteError("No lab investigation activity has been recorded yet")
    if cmd.assignable and not cmd.evidence_refs:
        raise LabCauseEvidenceRequiredError("Evidence is required to determine an assignable lab cause")

    activity = OosInvestigationActivity(
        oos_record_id=oos.id, phase="lab_investigation", activity_type="classify_lab_cause",
        response_text="assignable" if cmd.assignable else "no_assignable_cause",
        evidence_refs={"refs": cmd.evidence_refs}, investigator_user_id=actor_user_id, version=1,
    )
    session.add(activity)

    old_state = oos.state
    oos.root_cause_code = cmd.root_cause_code
    oos.state = "qa_review" if cmd.assignable else "no_assignable_lab_cause"
    oos.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=oos.site_id, aggregate_type="oos_record", aggregate_id=oos.id, aggregate_version=oos.version,
        action="Changed", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": oos.state, "root_cause_code": oos.root_cause_code},
    )
    await write_outbox_event(
        session, event_type="OOSAssignableCauseDetermined", aggregate_type="oos_record", aggregate_id=oos.id,
        aggregate_version=oos.version, payload={"id": str(oos.id), "assignable": cmd.assignable}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=oos.site_id, command_type="ClassifyLabCause", aggregate_type="oos_record", aggregate_id=oos.id,
        expected_version=cmd.expected_version, resulting_version=oos.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=oos.id, resulting_version=oos.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# StartExtendedInvestigation -- OOS-FR-008: POST /quality/oos/v1/{id}/extended-investigation. Signed per
# Document 106 row 68 (meaning Approved, independent of the OOS owner).
# ---------------------------------------------------------------------------


class StartExtendedInvestigationCommand(CommandEnvelope):
    oos_record_id: uuid.UUID
    expected_version: int
    investigation_notes: str | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def start_extended_investigation(
    session: AsyncSession, cmd: StartExtendedInvestigationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(OosRecord).where(OosRecord.id == cmd.oos_record_id).with_for_update())
    oos = result.scalar_one_or_none()
    if oos is None:
        raise NotFoundError("OOS record not found")
    if oos.version != cmd.expected_version:
        raise StaleVersionError("OOS record was modified since it was read", expected_version=cmd.expected_version, current_version=oos.version)
    if oos.state != "no_assignable_lab_cause":
        raise InvalidTransitionError("Extended investigation requires a no-assignable-lab-cause determination first", current_status=oos.state)

    await evaluate_policy(session, actor_user_id, action="oos_record.extended_investigation", site_id=oos.site_id)
    if actor_user_id in await _oos_independent_actors(session, oos):
        raise InvalidTransitionError("Extended investigation approver must be independent of the OOS owner/investigator (SoD)")

    policy = await signature_service.resolve_signature_requirement(session, record_type="oos_record", action="extended_investigation")
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
            record_version=oos.version, record_hash=_record_hash(oos, "state"),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    session.add(
        OosInvestigationActivity(
            oos_record_id=oos.id, phase="extended_investigation", activity_type="extended_investigation_started",
            response_text=cmd.investigation_notes, investigator_user_id=actor_user_id, version=1,
        )
    )

    old_state = oos.state
    oos.state = "extended_investigation"
    oos.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=oos.site_id, aggregate_type="oos_record", aggregate_id=oos.id, aggregate_version=oos.version,
        action="Approved", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": oos.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="OOSExtendedInvestigationStarted", aggregate_type="oos_record", aggregate_id=oos.id,
        aggregate_version=oos.version, payload={"id": str(oos.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=oos.site_id, command_type="StartExtendedInvestigation", aggregate_type="oos_record", aggregate_id=oos.id,
        expected_version=cmd.expected_version, resulting_version=oos.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=oos.id, resulting_version=oos.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# AuthorizeRetestPlan / AuthorizeResamplePlan -- OOS-FR-010/011/014/015: POST /quality/oos/v1/{id}/retest-plans,
# .../resample-plans. Unsigned (no Document 106 row). Both require the OOS to already be in extended
# investigation -- RETEST_NOT_AUTHORIZED/RESAMPLE_NOT_AUTHORIZED otherwise (§9: "retest plan is
# released/approved before retest execution").
# ---------------------------------------------------------------------------


class AuthorizeRetestPlanCommand(CommandEnvelope):
    oos_record_id: uuid.UUID
    justification: str
    number_of_retests: int
    method_ref: str | None = None
    analyst_criteria: str | None = None
    instrument_criteria: str | None = None
    interpretation_rule: str | None = None


async def authorize_retest_plan(session: AsyncSession, cmd: AuthorizeRetestPlanCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    oos = await session.get(OosRecord, cmd.oos_record_id)
    if oos is None:
        raise NotFoundError("OOS record not found")
    if oos.state != "extended_investigation":
        raise RetestNotAuthorizedError("A retest plan can only be authorized during extended investigation", current_status=oos.state)

    await evaluate_policy(session, actor_user_id, action="oos_record.retest_plan", site_id=oos.site_id)

    plan = OosRetestPlan(
        oos_record_id=oos.id, justification=cmd.justification, number_of_retests=cmd.number_of_retests,
        method_ref=cmd.method_ref, analyst_criteria=cmd.analyst_criteria, instrument_criteria=cmd.instrument_criteria,
        interpretation_rule=cmd.interpretation_rule, status="authorized", version=1,
    )
    session.add(plan)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=oos.site_id, aggregate_type="oos_retest_plan", aggregate_id=plan.id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"oos_record_id": str(oos.id), "number_of_retests": cmd.number_of_retests},
    )
    await write_outbox_event(
        session, event_type="OOSRetestAuthorized", aggregate_type="oos_retest_plan", aggregate_id=plan.id,
        aggregate_version=1, payload={"id": str(plan.id), "oos_record_id": str(oos.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=oos.site_id, command_type="AuthorizeRetestPlan", aggregate_type="oos_retest_plan", aggregate_id=plan.id,
        expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=plan.id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


class AuthorizeResamplePlanCommand(CommandEnvelope):
    oos_record_id: uuid.UUID
    scientific_rationale: str
    sampling_plan_ref: str | None = None
    sampling_plan_version: str | None = None
    source_ref: str | None = None


async def authorize_resample_plan(session: AsyncSession, cmd: AuthorizeResamplePlanCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    oos = await session.get(OosRecord, cmd.oos_record_id)
    if oos is None:
        raise NotFoundError("OOS record not found")
    if oos.state != "extended_investigation":
        raise ResampleNotAuthorizedError("A resample plan can only be authorized during extended investigation", current_status=oos.state)

    await evaluate_policy(session, actor_user_id, action="oos_record.resample_plan", site_id=oos.site_id)

    plan = OosResamplePlan(
        oos_record_id=oos.id, scientific_rationale=cmd.scientific_rationale, sampling_plan_ref=cmd.sampling_plan_ref,
        sampling_plan_version=cmd.sampling_plan_version, source_ref=cmd.source_ref, approver_user_id=actor_user_id,
        status="authorized", version=1,
    )
    session.add(plan)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=oos.site_id, aggregate_type="oos_resample_plan", aggregate_id=plan.id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"oos_record_id": str(oos.id)},
    )
    await write_outbox_event(
        session, event_type="OOSResampleAuthorized", aggregate_type="oos_resample_plan", aggregate_id=plan.id,
        aggregate_version=1, payload={"id": str(plan.id), "oos_record_id": str(oos.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=oos.site_id, command_type="AuthorizeResamplePlan", aggregate_type="oos_resample_plan", aggregate_id=plan.id,
        expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=plan.id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# RecordImpactAssessment -- OOS-FR-009/018: POST /quality/oos/v1/{id}/impact. Unsigned.
# ---------------------------------------------------------------------------


class RecordImpactAssessmentCommand(CommandEnvelope):
    oos_record_id: uuid.UUID
    expected_version: int
    impact_text: str
    hold_status: str | None = None


async def record_impact_assessment(
    session: AsyncSession, cmd: RecordImpactAssessmentCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(OosRecord).where(OosRecord.id == cmd.oos_record_id).with_for_update())
    oos = result.scalar_one_or_none()
    if oos is None:
        raise NotFoundError("OOS record not found")
    if oos.version != cmd.expected_version:
        raise StaleVersionError("OOS record was modified since it was read", expected_version=cmd.expected_version, current_version=oos.version)
    if oos.state not in ("qa_review", "extended_investigation"):
        raise InvalidTransitionError("Impact assessment requires lab or extended investigation to be complete", current_status=oos.state)

    await evaluate_policy(session, actor_user_id, action="oos_record.impact", site_id=oos.site_id)

    session.add(
        OosInvestigationActivity(
            oos_record_id=oos.id, phase="impact_assessment", activity_type="impact_assessment",
            response_text=cmd.impact_text, investigator_user_id=actor_user_id, version=1,
        )
    )

    old_state = oos.state
    oos.hold_status = cmd.hold_status
    oos.state = "final_disposition"
    oos.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=oos.site_id, aggregate_type="oos_record", aggregate_id=oos.id, aggregate_version=oos.version,
        action="Changed", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": oos.state, "hold_status": oos.hold_status},
    )
    await write_outbox_event(
        session, event_type="OOSImpactAssessed", aggregate_type="oos_record", aggregate_id=oos.id,
        aggregate_version=oos.version, payload={"id": str(oos.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=oos.site_id, command_type="RecordImpactAssessment", aggregate_type="oos_record", aggregate_id=oos.id,
        expected_version=cmd.expected_version, resulting_version=oos.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=oos.id, resulting_version=oos.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ApproveDisposition -- OOS-FR-019: POST /quality/oos/v1/{id}/disposition. Signed per Document 106 row 67
# (meaning Released, independent of every production performer).
# ---------------------------------------------------------------------------


class ApproveDispositionCommand(CommandEnvelope):
    oos_record_id: uuid.UUID
    expected_version: int
    final_classification: str
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_disposition(session: AsyncSession, cmd: ApproveDispositionCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(OosRecord).where(OosRecord.id == cmd.oos_record_id).with_for_update())
    oos = result.scalar_one_or_none()
    if oos is None:
        raise NotFoundError("OOS record not found")
    if oos.version != cmd.expected_version:
        raise StaleVersionError("OOS record was modified since it was read", expected_version=cmd.expected_version, current_version=oos.version)
    if oos.state != "final_disposition":
        raise InvalidTransitionError("Only an OOS awaiting final disposition can be dispositioned", current_status=oos.state)

    has_impact = (
        await session.execute(
            select(OosInvestigationActivity.id).where(
                OosInvestigationActivity.oos_record_id == oos.id, OosInvestigationActivity.phase == "impact_assessment"
            )
        )
    ).scalars().first()
    if has_impact is None:
        raise ImpactAssessmentRequiredError("Disposition requires a recorded impact assessment")

    await evaluate_policy(session, actor_user_id, action="oos_record.disposition", site_id=oos.site_id)
    if actor_user_id in await _oos_independent_actors(session, oos):
        raise InvalidTransitionError("Disposition approver must be independent of every production performer on this OOS (SoD)")

    policy = await signature_service.resolve_signature_requirement(session, record_type="oos_record", action="disposition")
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
            record_version=oos.version, record_hash=_record_hash(oos, "state"),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    old_state = oos.state
    oos.final_classification = cmd.final_classification
    oos.state = "qa_approval"
    oos.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=oos.site_id, aggregate_type="oos_record", aggregate_id=oos.id, aggregate_version=oos.version,
        action="Released", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": oos.state, "final_classification": oos.final_classification},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="OOSDispositionApproved", aggregate_type="oos_record", aggregate_id=oos.id,
        aggregate_version=oos.version, payload={"id": str(oos.id), "final_classification": oos.final_classification},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=oos.site_id, command_type="ApproveDisposition", aggregate_type="oos_record", aggregate_id=oos.id,
        expected_version=cmd.expected_version, resulting_version=oos.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=oos.id, resulting_version=oos.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CloseOos -- OOS-FR-022: POST /quality/oos/v1/{id}/close. Signed per Document 106 row 66 (meaning
# Approved, independent of investigator/owner).
# ---------------------------------------------------------------------------


class CloseOosCommand(CommandEnvelope):
    oos_record_id: uuid.UUID
    expected_version: int
    challenge_id: uuid.UUID
    reauth_password: str


async def close_oos(session: AsyncSession, cmd: CloseOosCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(OosRecord).where(OosRecord.id == cmd.oos_record_id).with_for_update())
    oos = result.scalar_one_or_none()
    if oos is None:
        raise NotFoundError("OOS record not found")
    if oos.version != cmd.expected_version:
        raise StaleVersionError("OOS record was modified since it was read", expected_version=cmd.expected_version, current_version=oos.version)
    if oos.state != "qa_approval":
        raise QaApprovalRequiredError("OOS must have an approved disposition before it can be closed", current_status=oos.state)

    await evaluate_policy(session, actor_user_id, action="oos_record.close", site_id=oos.site_id)
    if actor_user_id in await _oos_independent_actors(session, oos):
        raise InvalidTransitionError("Closer must be independent of the investigator/owner for this OOS (SoD)")

    policy = await signature_service.resolve_signature_requirement(session, record_type="oos_record", action="close")
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
            record_version=oos.version, record_hash=_record_hash(oos, "state"),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    old_state = oos.state
    oos.state = "closed"
    oos.closed_at = datetime.now(timezone.utc)
    oos.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=oos.site_id, aggregate_type="oos_record", aggregate_id=oos.id, aggregate_version=oos.version,
        action="Approved", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": oos.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="OOSClosed", aggregate_type="oos_record", aggregate_id=oos.id,
        aggregate_version=oos.version, payload={"id": str(oos.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=oos.site_id, command_type="CloseOos", aggregate_type="oos_record", aggregate_id=oos.id,
        expected_version=cmd.expected_version, resulting_version=oos.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=oos.id, resulting_version=oos.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# EvaluateOot -- OOT-FR-001/002/003/009: POST /quality/oot/v1/evaluate. Unsigned. Reuses
# `_evaluate_acceptance` exactly as Document 23's own acceptance-rule classification -- no released trend
# rule for the test definition is a hard OOT_RULE_NOT_RELEASED error here (unlike record_result's silent
# "pending" no-op), since this endpoint's entire purpose is to run that evaluation on demand.
# ---------------------------------------------------------------------------


class EvaluateOotCommand(CommandEnvelope):
    source_result_id: uuid.UUID


async def evaluate_oot(session: AsyncSession, cmd: EvaluateOotCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    source_result = await session.get(QcResult, cmd.source_result_id)
    if source_result is None:
        raise OriginalResultRequiredError("source_result_id does not reference an existing result")
    order = await session.get(QcTestOrder, source_result.test_order_id)
    definition = await session.get(QcTestDefinition, order.test_definition_id) if order else None
    if definition is None or not definition.trend_rule_business_id:
        raise OotRuleNotReleasedError("No trend rule is configured for this test definition")

    oot_id = uuid.uuid4()
    value = (
        str(source_result.value_decimal) if source_result.value_decimal is not None
        else source_result.value_text or source_result.value_json
    )
    inputs = {"value": value}
    outcome, rule_object_id = await _evaluate_acceptance(
        session, rule_business_id=definition.trend_rule_business_id, inputs=inputs,
        aggregate_id=oot_id, actor_user_id=actor_user_id,
    )
    if outcome == "pending":
        raise OotRuleNotReleasedError("No effective released version resolves for this trend rule", rule_id=definition.trend_rule_business_id)
    triggered = outcome == "oos"

    oot = OotRecord(
        id=oot_id, source_result_id=source_result.id, trend_rule_id=rule_object_id,
        baseline_ref=None, trigger_details={"triggered": triggered, "rule_id": definition.trend_rule_business_id},
        state="open" if triggered else "not_triggered", investigation_owner_user_id=actor_user_id if triggered else None,
        version=1,
    )
    session.add(oot)
    await session.flush()

    # qc_result is append-only (no UPDATE grant, AG-08) -- oot_record_id is never backfilled onto the
    # already-committed result row. oot_record.source_result_id (set above) is the queryable relationship.

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="oot_record", aggregate_id=oot.id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"source_result_id": str(source_result.id), "triggered": triggered},
    )
    if triggered:
        await write_outbox_event(
            session, event_type="OOTDetected", aggregate_type="oot_record", aggregate_id=oot.id,
            aggregate_version=1, payload={"id": str(oot.id), "source_result_id": str(source_result.id)},
            correlation_id=correlation_id,
        )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="EvaluateOot", aggregate_type="oot_record", aggregate_id=oot.id,
        expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=oot.id, resulting_version=1,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# CloseOot -- POST /quality/oot/v1/{id}/close. Signed per Document 106 row 69 (meaning Approved,
# independent of the investigator/owner).
# ---------------------------------------------------------------------------


class CloseOotCommand(CommandEnvelope):
    oot_record_id: uuid.UUID
    expected_version: int
    challenge_id: uuid.UUID
    reauth_password: str


async def close_oot(session: AsyncSession, cmd: CloseOotCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(OotRecord).where(OotRecord.id == cmd.oot_record_id).with_for_update())
    oot = result.scalar_one_or_none()
    if oot is None:
        raise NotFoundError("OOT record not found")
    if oot.version != cmd.expected_version:
        raise StaleVersionError("OOT record was modified since it was read", expected_version=cmd.expected_version, current_version=oot.version)
    if oot.state != "open":
        raise InvalidTransitionError("Only an open OOT record can be closed", current_status=oot.state)

    await evaluate_policy(session, actor_user_id, action="oot_record.close", site_id=None)
    if oot.investigation_owner_user_id is not None and actor_user_id == oot.investigation_owner_user_id:
        raise InvalidTransitionError("Closer must be independent of the investigator/owner for this OOT (SoD)")

    policy = await signature_service.resolve_signature_requirement(session, record_type="oot_record", action="close")
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id,
            record_version=oot.version, record_hash=_record_hash(oot, "state"),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    old_state = oot.state
    oot.state = "closed"
    oot.closed_at = datetime.now(timezone.utc)
    oot.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=None, aggregate_type="oot_record", aggregate_id=oot.id, aggregate_version=oot.version,
        action="Approved", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"state": old_state}, new_value={"state": oot.state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="OOTClosed", aggregate_type="oot_record", aggregate_id=oot.id,
        aggregate_version=oot.version, payload={"id": str(oot.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=None, command_type="CloseOot", aggregate_type="oot_record", aggregate_id=oot.id,
        expected_version=cmd.expected_version, resulting_version=oot.version, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=oot.id, resulting_version=oot.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )
