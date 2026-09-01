"""Document 82 (SPEC-VAL-004) Mutation Gateway command handlers -- Validation Test Strategy, Test
Methods & Objective Evidence Governance. Document 106 row 147: `tests/{id}/approve` requires an
`Approved` signature from an independent QA Releaser, reason mandatory. Row 146: `executions/{id}/
complete` requires a `Performed` signature from the qualified performer, no dedicated role/independence/
reason (same "Qualified performer for the task" shape as `batch_step.complete_step`).
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import TEST_METHODS, ValidationTestDefinition, ValidationTestExecution
from app.modules.validation.shared import (
    finalize,
    receipt_from_existing,
    resolve_signature,
    verify_evidence_refs,
    verify_reauth_and_consume,
)
from app.mutation.errors import InvalidTransitionError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_TEST_DEF = "validation_test_definition"
RECORD_TYPE_TEST_EXEC = "validation_test_execution"


class CreateTestDefinitionCommand(CommandEnvelope):
    test_code: str
    method: str
    requirement_refs: list[dict] = []
    preconditions: dict = {}
    procedure: str
    expected_results: str
    independent_review_required: bool = False


async def create_test_definition(
    session: AsyncSession, cmd: CreateTestDefinitionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if cmd.method not in TEST_METHODS:
        raise ValidationFailedError(f"method must be one of {TEST_METHODS}")

    row = ValidationTestDefinition(
        test_code=cmd.test_code, method=cmd.method, requirement_refs=cmd.requirement_refs,
        preconditions=cmd.preconditions, procedure=cmd.procedure, expected_results=cmd.expected_results,
        independent_review_required=cmd.independent_review_required, state="DRAFT", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_TEST_DEF, aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"test_code": row.test_code, "method": row.method}, event_type="ValidationTestDefined",
        expected_version=None, command_type="CreateTestDefinition", site_id=site_id,
    )


class ApproveTestDefinitionCommand(CommandEnvelope):
    test_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_test_definition(
    session: AsyncSession, cmd: ApproveTestDefinitionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = await session.get(ValidationTestDefinition, cmd.test_id)
    if row is None:
        raise NotFoundError("Validation test definition not found")
    if row.state != "DRAFT":
        raise InvalidTransitionError("Test definition is not DRAFT", current_state=row.state)
    if row.version != cmd.expected_version:
        raise StaleVersionError("Test definition changed since this request was prepared", current_version=row.version)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to approve a test definition")

    policy = await resolve_signature(session, record_type=RECORD_TYPE_TEST_DEF, action="approve")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.state = "APPROVED"
    row.approved_by_user_id = actor_user_id
    row.approved_at = datetime.now(timezone.utc)
    row.version += 1

    # Document 06 (VLT-FR-001) / TST-FR-003: an approved test definition is immutable/versioned --
    # gets a real vault snapshot in the same transaction as the approval.
    from app.modules.vault import service as vault_service
    await vault_service.release_master(
        session, object_type=RECORD_TYPE_TEST_DEF, business_id=str(row.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "test_code": row.test_code, "method": row.method, "procedure": row.procedure,
            "expected_results": row.expected_results,
        },
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_TEST_DEF, aggregate_id=row.id,
        version=row.version, action="Approved", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value={"state": "DRAFT"}, new_value={"state": "APPROVED"}, event_type="ValidationTestApproved",
        expected_version=cmd.expected_version, command_type="ApproveTestDefinition", site_id=site_id,
        signature_id=signature_id,
    )


class StartTestExecutionCommand(CommandEnvelope):
    test_definition_id: uuid.UUID
    environment_fingerprint: dict = {}
    ci_run_ref: str | None = None
    performer_user_id: uuid.UUID | None = None


async def start_test_execution(
    session: AsyncSession, cmd: StartTestExecutionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    test_def = await session.get(ValidationTestDefinition, cmd.test_definition_id)
    if test_def is None:
        raise NotFoundError("Validation test definition not found")
    if test_def.state != "APPROVED":
        raise InvalidTransitionError("Test definition is not APPROVED", current_state=test_def.state)

    row = ValidationTestExecution(
        test_definition_id=test_def.id, test_definition_version=test_def.version,
        environment_fingerprint=cmd.environment_fingerprint, performer_user_id=cmd.performer_user_id or actor_user_id,
        ci_run_ref=cmd.ci_run_ref, started_at=datetime.now(timezone.utc), status="IN_PROGRESS", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_TEST_EXEC, aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"test_definition_id": str(test_def.id)}, event_type="ValidationTestExecutionStarted",
        expected_version=None, command_type="StartTestExecution", site_id=site_id,
    )


class CompleteTestExecutionCommand(CommandEnvelope):
    execution_id: uuid.UUID
    expected_version: int
    observations: str | None = None
    actual_result: str
    status: str  # PASS | FAIL | BLOCKED | SKIPPED
    blocked_reason: str | None = None
    evidence_manifest: list[dict] = []
    reviewer_user_id: uuid.UUID | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def complete_test_execution(
    session: AsyncSession, cmd: CompleteTestExecutionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    from app.modules.validation.models import EXECUTION_STATUSES
    if cmd.status not in EXECUTION_STATUSES or cmd.status == "IN_PROGRESS":
        raise ValidationFailedError(f"status must be a terminal state in {EXECUTION_STATUSES}")
    if cmd.status == "BLOCKED" and not cmd.blocked_reason:
        raise ValidationFailedError("blocked_reason is required when status is BLOCKED (TST-FR-014)")
    await verify_evidence_refs(session, cmd.evidence_manifest)  # AG-12/OBJ-FR-004

    row = await session.get(ValidationTestExecution, cmd.execution_id)
    if row is None:
        raise NotFoundError("Validation test execution not found")
    if row.status != "IN_PROGRESS":
        raise InvalidTransitionError("Execution is not IN_PROGRESS", current_state=row.status)
    if row.version != cmd.expected_version:
        raise StaleVersionError("Execution changed since this request was prepared", current_version=row.version)

    policy = await resolve_signature(session, record_type=RECORD_TYPE_TEST_EXEC, action="complete")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.observations = cmd.observations
    row.actual_result = cmd.actual_result
    row.status = cmd.status
    row.blocked_reason = cmd.blocked_reason
    row.evidence_manifest = cmd.evidence_manifest
    row.completed_at = datetime.now(timezone.utc)
    row.version += 1

    test_def = await session.get(ValidationTestDefinition, row.test_definition_id)
    if test_def and test_def.independent_review_required and cmd.reviewer_user_id:
        if cmd.reviewer_user_id == row.performer_user_id:
            raise ValidationFailedError("Reviewer must be independent of the performer (TST-FR-017)")
        row.reviewed_by_user_id = cmd.reviewer_user_id
        row.reviewed_at = datetime.now(timezone.utc)
        await write_outbox_event(
            session, event_type="ValidationTestReviewed", aggregate_type=RECORD_TYPE_TEST_EXEC,
            aggregate_id=row.id, aggregate_version=row.version,
            payload={"reviewer_user_id": str(cmd.reviewer_user_id)}, correlation_id=uuid.uuid4(),
        )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_TEST_EXEC, aggregate_id=row.id,
        version=row.version, action="Performed", actor_user_id=actor_user_id, reason=None,
        old_value={"status": "IN_PROGRESS"}, new_value={"status": cmd.status}, event_type="ValidationTestCompleted",
        expected_version=cmd.expected_version, command_type="CompleteTestExecution", site_id=site_id,
        signature_id=signature_id,
    )


class ImportAutomatedEvidenceCommand(CommandEnvelope):
    execution_id: uuid.UUID
    expected_version: int
    ci_run_ref: str
    result: str  # PASS | FAIL
    evidence_manifest: list[dict]


async def import_automated_evidence(
    session: AsyncSession, cmd: ImportAutomatedEvidenceCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    """TST-FR-009: automated/CI evidence import -- captures test code commit, runner/image and results
    without requiring a human performer (Document 106 has no policy row for this action -- unsigned)."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if cmd.result not in ("PASS", "FAIL"):
        raise ValidationFailedError("result must be PASS or FAIL")

    row = await session.get(ValidationTestExecution, cmd.execution_id)
    if row is None:
        raise NotFoundError("Validation test execution not found")
    if row.version != cmd.expected_version:
        raise StaleVersionError("Execution changed since this request was prepared", current_version=row.version)

    row.ci_run_ref = cmd.ci_run_ref
    row.status = cmd.result
    row.evidence_manifest = list(row.evidence_manifest) + cmd.evidence_manifest
    row.completed_at = datetime.now(timezone.utc)
    row.version += 1

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_TEST_EXEC, aggregate_id=row.id,
        version=row.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_value=None, new_value={"ci_run_ref": cmd.ci_run_ref, "result": cmd.result},
        event_type="AutomatedEvidenceImported", expected_version=cmd.expected_version,
        command_type="ImportAutomatedEvidence", site_id=site_id,
    )
