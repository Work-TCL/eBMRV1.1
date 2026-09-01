"""Document 88 (SPEC-VAL-010) Mutation Gateway command handlers -- 21 CFR Part 11 Electronic Records &
Electronic Signature Validation. Document 106 row 154: `part11/{id}/approve` requires an `Approved`
signature from an independent QA Releaser, reason mandatory -- binds to `part11_scope_assessment` (the
overall qualification verdict for one record/signature type), not to an individual control-evidence row.
`part11/assessments` and `part11/{id}/test-suite` carry no Document 106 row -- unsigned.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import Part11ControlEvidence, Part11ScopeAssessment
from app.modules.validation.shared import (
    finalize,
    receipt_from_existing,
    resolve_signature,
    verify_evidence_refs,
    verify_reauth_and_consume,
)
from app.mutation.errors import InvalidTransitionError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_ASSESSMENT = "part11_scope_assessment"


class CreatePart11ScopeAssessmentCommand(CommandEnvelope):
    record_or_signature_type: str
    predicate_use: str
    system_component: str
    context: str = "CLOSED"
    applicable: bool = True
    customer_responsibilities: str | None = None


async def create_part11_scope_assessment(
    session: AsyncSession, cmd: CreatePart11ScopeAssessmentCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if cmd.context not in ("CLOSED", "OPEN"):
        raise ValidationFailedError("context must be CLOSED or OPEN")

    row = Part11ScopeAssessment(
        record_or_signature_type=cmd.record_or_signature_type, predicate_use=cmd.predicate_use,
        system_component=cmd.system_component, context=cmd.context, applicable=cmd.applicable,
        customer_responsibilities=cmd.customer_responsibilities, state="EFFECTIVE", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_ASSESSMENT, aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"record_or_signature_type": row.record_or_signature_type}, event_type="Part11AssessmentCreated",
        expected_version=None, command_type="CreatePart11ScopeAssessment", site_id=site_id,
    )


class DerivePart11TestSuiteCommand(CommandEnvelope):
    assessment_id: uuid.UUID
    control_citations: list[str]  # e.g. ["11.10(a)", "11.10(e)", "11.50", ...]


async def derive_part11_test_suite(
    session: AsyncSession, cmd: DerivePart11TestSuiteCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    assessment = await session.get(Part11ScopeAssessment, cmd.assessment_id)
    if assessment is None:
        raise NotFoundError("Part 11 scope assessment not found")
    if not cmd.control_citations:
        raise ValidationFailedError("control_citations must not be empty")

    created_ids = []
    for citation in cmd.control_citations:
        row = Part11ControlEvidence(
            scope_assessment_id=assessment.id, control_citation=citation, result="IN_PROGRESS",
            status="DRAFT", version=1,
        )
        session.add(row)
        await session.flush()
        created_ids.append(str(row.id))

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_ASSESSMENT,
        aggregate_id=assessment.id, version=assessment.version, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_value=None, new_value={"control_evidence_ids": created_ids},
        event_type="Part11TestSuiteDerived", expected_version=None, command_type="DerivePart11TestSuite",
        site_id=site_id,
    )


class RecordPart11ControlResultCommand(CommandEnvelope):
    control_evidence_id: uuid.UUID
    expected_version: int
    result: str  # PASS | FAIL
    test_ref: str | None = None
    evidence_manifest: list[dict] = []
    configuration_ref: str | None = None
    procedure_ref: str | None = None
    deviation_ref: str | None = None


async def record_part11_control_result(
    session: AsyncSession, cmd: RecordPart11ControlResultCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    """No independent Document 79 API entry -- this is the child-row completion action behind
    `derivePart11TestSuite()`'s created rows, same "internal completion, no separate top-level route"
    shape as several other WP-12 child records. Unsigned (no Document 106 row)."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if cmd.result not in ("PASS", "FAIL"):
        raise ValidationFailedError("result must be PASS or FAIL")
    await verify_evidence_refs(session, cmd.evidence_manifest)  # AG-12/OBJ-FR-004

    row = await session.get(Part11ControlEvidence, cmd.control_evidence_id)
    if row is None:
        raise NotFoundError("Part 11 control evidence row not found")
    if row.version != cmd.expected_version:
        raise StaleVersionError("Control evidence changed since this request was prepared", current_version=row.version)
    if cmd.result == "FAIL" and not cmd.deviation_ref:
        raise ValidationFailedError("deviation_ref is required for a FAIL control result")

    row.result = cmd.result
    row.test_ref = cmd.test_ref
    row.evidence_manifest = cmd.evidence_manifest
    row.configuration_ref = cmd.configuration_ref
    row.procedure_ref = cmd.procedure_ref
    row.deviation_ref = cmd.deviation_ref
    row.status = "APPROVED" if cmd.result == "PASS" else "DRAFT"
    row.version += 1

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="part11_control_evidence", aggregate_id=row.id,
        version=row.version, action="Changed", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"control_citation": row.control_citation, "result": cmd.result},
        event_type="Part11TestSuiteDerived", expected_version=cmd.expected_version,
        command_type="RecordPart11ControlResult", site_id=site_id,
    )


class ApprovePart11AssessmentCommand(CommandEnvelope):
    assessment_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_part11_assessment(
    session: AsyncSession, cmd: ApprovePart11AssessmentCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    assessment = await session.get(Part11ScopeAssessment, cmd.assessment_id)
    if assessment is None:
        raise NotFoundError("Part 11 scope assessment not found")
    if assessment.version != cmd.expected_version:
        raise StaleVersionError("Assessment changed since this request was prepared", current_version=assessment.version)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to approve a Part 11 qualification")

    evidence_rows = (
        await session.execute(
            select(Part11ControlEvidence).where(Part11ControlEvidence.scope_assessment_id == assessment.id)
        )
    ).scalars().all()
    if not evidence_rows:
        raise InvalidTransitionError("No control evidence recorded for this assessment (P11-FR-026)")
    unresolved = [e.control_citation for e in evidence_rows if e.result != "PASS"]
    if unresolved:
        raise InvalidTransitionError("Unresolved Part 11 controls", unresolved=unresolved)

    policy = await resolve_signature(session, record_type=RECORD_TYPE_ASSESSMENT, action="approve")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=assessment.id, record_version=assessment.version,
        )

    assessment.state = "QUALIFIED"
    assessment.version += 1

    # Document 06 (VLT-FR-001): a qualified Part 11 assessment is a regulated final record.
    from app.modules.vault import service as vault_service
    await vault_service.release_master(
        session, object_type=RECORD_TYPE_ASSESSMENT, business_id=str(assessment.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "record_or_signature_type": assessment.record_or_signature_type,
            "predicate_use": assessment.predicate_use, "system_component": assessment.system_component,
        },
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_ASSESSMENT,
        aggregate_id=assessment.id, version=assessment.version, action="Approved", actor_user_id=actor_user_id,
        reason=cmd.reason, old_value={"state": "EFFECTIVE"}, new_value={"state": "QUALIFIED"},
        event_type="Part11QualificationApproved", expected_version=cmd.expected_version,
        command_type="ApprovePart11Assessment", site_id=site_id, signature_id=signature_id,
    )
