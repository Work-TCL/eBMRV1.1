"""Document 84 (SPEC-VAL-006) Mutation Gateway command handlers -- Operational Qualification (OQ) &
Functional Control Verification. Document 106 row 150: `oq/{id}/approve` requires an `Approved`
signature from an independent QA Releaser, reason mandatory. `oq:suites`/`oq/executions` carry no
Document 106 row -- unsigned.

Coverage (OQ-FR-016) is integer basis points (never `float`) -- (# executed test refs recorded PASS) /
(# selected test refs in the suite) * 10000, computed once at execution-record time and read back
verbatim by the coverage GET, never recomputed with a different formula on read.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import OqExecution, OqSuite
from app.modules.validation.shared import finalize, receipt_from_existing, resolve_signature, verify_reauth_and_consume
from app.mutation.errors import InvalidTransitionError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_OQ_EXEC = "oq_execution"


class CreateOqSuiteCommand(CommandEnvelope):
    baseline_id: uuid.UUID
    selected_test_refs: list[dict]
    selected_evidence_refs: list[dict] = []
    exclusions: list[dict] = []
    environment_fingerprint: dict = {}


async def create_oq_suite(
    session: AsyncSession, cmd: CreateOqSuiteCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if not cmd.selected_test_refs:
        raise ValidationFailedError("selected_test_refs must not be empty (OQ-FR-001)")

    row = OqSuite(
        baseline_id=cmd.baseline_id, selected_test_refs=cmd.selected_test_refs,
        selected_evidence_refs=cmd.selected_evidence_refs, exclusions=cmd.exclusions,
        environment_fingerprint=cmd.environment_fingerprint, state="DERIVED", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="oq_suite", aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"baseline_id": str(cmd.baseline_id), "test_count": len(cmd.selected_test_refs)},
        event_type="OQSuiteDerived", expected_version=None, command_type="CreateOqSuite", site_id=site_id,
    )


class RecordOqExecutionCommand(CommandEnvelope):
    suite_id: uuid.UUID
    executed_test_refs: list[dict]  # [{"test_ref": ..., "result": "PASS"|"FAIL"}]
    deviations: list[dict] = []


async def record_oq_execution(
    session: AsyncSession, cmd: RecordOqExecutionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    suite = await session.get(OqSuite, cmd.suite_id)
    if suite is None:
        raise NotFoundError("OQ suite not found")
    if not cmd.executed_test_refs:
        raise ValidationFailedError("executed_test_refs must not be empty")

    total = len(suite.selected_test_refs) or 1
    passed = sum(1 for r in cmd.executed_test_refs if r.get("result") == "PASS")
    coverage_bp = (passed * 10000) // total
    status = "PASS" if (passed == total and not cmd.deviations) else "FAIL"

    row = OqExecution(
        suite_id=suite.id, suite_version=suite.version, executed_test_refs=cmd.executed_test_refs,
        coverage_basis_points=coverage_bp, deviations=cmd.deviations, status=status, version=1,
    )
    session.add(row)
    await session.flush()

    await write_outbox_event(
        session, event_type="OQCoverageEvaluated", aggregate_type=RECORD_TYPE_OQ_EXEC, aggregate_id=row.id,
        aggregate_version=1, payload={"coverage_basis_points": coverage_bp}, correlation_id=uuid.uuid4(),
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_OQ_EXEC, aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"suite_id": str(suite.id), "coverage_basis_points": coverage_bp, "status": status},
        event_type="OQExecutionCompleted", expected_version=None, command_type="RecordOqExecution",
        site_id=site_id,
    )


async def get_oq_coverage(session: AsyncSession, execution_id: uuid.UUID) -> dict:
    row = await session.get(OqExecution, execution_id)
    if row is None:
        raise NotFoundError("OQ execution not found")
    return {
        "execution_id": str(row.id), "coverage_basis_points": row.coverage_basis_points,
        "status": row.status, "deviation_count": len(row.deviations),
    }


class ApproveOqExecutionCommand(CommandEnvelope):
    execution_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_oq_execution(
    session: AsyncSession, cmd: ApproveOqExecutionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = await session.get(OqExecution, cmd.execution_id)
    if row is None:
        raise NotFoundError("OQ execution not found")
    if row.approved_by_user_id is not None:
        raise InvalidTransitionError("OQ execution already approved")
    if row.version != cmd.expected_version:
        raise StaleVersionError("OQ execution changed since this request was prepared", current_version=row.version)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to approve an OQ execution")

    policy = await resolve_signature(session, record_type=RECORD_TYPE_OQ_EXEC, action="approve")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.reviewed_by_user_id = row.reviewed_by_user_id or actor_user_id
    row.reviewed_at = row.reviewed_at or datetime.now(timezone.utc)
    row.approved_by_user_id = actor_user_id
    row.approved_at = datetime.now(timezone.utc)
    row.version += 1

    # Document 06 (VLT-FR-001): an approved OQ execution is a regulated final record.
    from app.modules.vault import service as vault_service
    await vault_service.release_master(
        session, object_type=RECORD_TYPE_OQ_EXEC, business_id=str(row.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "suite_id": str(row.suite_id), "executed_test_refs": row.executed_test_refs,
            "coverage_basis_points": row.coverage_basis_points, "deviations": row.deviations,
        },
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_OQ_EXEC, aggregate_id=row.id,
        version=row.version, action="Approved", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value=None, new_value={"approved": True}, event_type="OQApproved",
        expected_version=cmd.expected_version, command_type="ApproveOqExecution", site_id=site_id,
        signature_id=signature_id,
    )
