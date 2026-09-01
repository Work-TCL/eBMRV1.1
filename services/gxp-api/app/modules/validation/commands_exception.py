"""Document 94 (SPEC-VAL-016) Mutation Gateway command handlers -- Validation Defect, Deviation, Test
Exception & Remediation Management.

**SG-167 resolved (2026-09-01).** Document 106 rows 162/164/165 (`exceptions` create,
`exceptions/{id}/retest-plan`, `exceptions/{id}/triage`) name signer class "Elevated authority defined
by the record class" -- the same phrase Document 106 uses for Document 61's `security/v1/exceptions`
(SG-161, still open) and Document 60's `regulatory_obligation.override_deadline` (SG-160, still open).
For Document 94 specifically, the project owner resolved "elevated authority" to this codebase's
existing `QA Releaser` role -- the same role already seeded as the signer for row 163's disposition
action, so one elevated-authority role covers the whole exception lifecycle rather than introducing a
new role. RBAC codes `validation.exception.create`/`.triage`/`.retest_plan` were moved from
`VAL_REVIEWER_CODES` to `VAL_RELEASER_CODES` in `scripts/seed.py`/`tests/conftest.py` so only a QA
Releaser can call (and therefore sign) these endpoints. "MUST be independent of the requester" is
enforced by `requested_by_user_id` (captured at `create_exception()` time) compared against the signing
actor on all three actions -- the same pattern `material/commands.py`, `supplier_quality/commands.py`
and `lims_integration/commands.py` already use for the identical Document 106 independence phrase.
SG-160/SG-161 remain open (different modules, out of this pass's scope by the project owner's own
decision) -- do not treat this file as precedent for silently resolving those without the same
explicit sign-off.

Row 163 (`exceptions/{id}/disposition`) resolves for real: `Released` signature from an independent QA
Releaser, reason mandatory -- identical shape to `batch.release`.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import VEX_DISPOSITIONS, VEX_TYPES, ValidationException
from app.modules.validation.shared import finalize, receipt_from_existing, resolve_signature, verify_reauth_and_consume
from app.mutation.errors import InvalidTransitionError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_EXCEPTION = "validation_exception"


class CreateExceptionCommand(CommandEnvelope):
    release_ref: str | None = None
    exception_type: str
    source_execution_type: str
    source_execution_id: uuid.UUID
    original_evidence: dict
    affected_requirement_refs: list[str] = []
    severity: str
    gxp_impact: bool = False
    release_impact: str = "BLOCKING"
    # SG-167: the person who identified/is requesting the exception be raised (e.g. the operator whose
    # test failed) -- may differ from `actor_user_id`, the QA Releaser who signs the exception into
    # existence. Independence is checked between the two below (Document 106 row 162).
    requested_by_user_id: uuid.UUID
    new_record_id: uuid.UUID | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def create_exception(
    session: AsyncSession, cmd: CreateExceptionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    """VEX-FR-001..003: a critical failed test can create this automatically (see e.g.
    `commands_test.py::complete_test_execution` on a FAIL status -- callers wire that linkage), or a
    human raises one directly through this command. `original_evidence` is captured once and never
    edited (VEX-FR-003). Document 106 row 162 signs this create action itself (`Approved`, QA Releaser,
    independent of the requester) -- same pre-generated-id shape as
    `commands_performance.py::create_performance_scenario` since the challenge must bind to the row's
    real id before it exists."""
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if cmd.exception_type not in VEX_TYPES:
        raise ValidationFailedError(f"exception_type must be one of {VEX_TYPES}")
    if not cmd.original_evidence:
        raise ValidationFailedError("original_evidence must not be empty (VEX-FR-003)")
    if actor_user_id == cmd.requested_by_user_id:
        raise ValidationFailedError("Signer must be independent of the requester (Document 106 row 162)")

    row = ValidationException(
        id=cmd.new_record_id or uuid.uuid4(),
        release_ref=cmd.release_ref, exception_type=cmd.exception_type,
        source_execution_type=cmd.source_execution_type, source_execution_id=cmd.source_execution_id,
        original_evidence=cmd.original_evidence, affected_requirement_refs=cmd.affected_requirement_refs,
        severity=cmd.severity, gxp_impact=cmd.gxp_impact, release_impact=cmd.release_impact,
        requested_by_user_id=cmd.requested_by_user_id, disposition="OPEN", version=1,
    )
    session.add(row)
    await session.flush()

    policy = await resolve_signature(session, record_type=RECORD_TYPE_EXCEPTION, action="create")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_EXCEPTION, aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"exception_type": row.exception_type, "severity": row.severity},
        event_type="ValidationExceptionCreated", expected_version=None, command_type="CreateException",
        site_id=site_id, signature_id=signature_id,
    )


class TriageExceptionCommand(CommandEnvelope):
    exception_id: uuid.UUID
    expected_version: int
    severity: str
    gxp_impact: bool
    release_impact: str
    root_cause: str | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def triage_exception(
    session: AsyncSession, cmd: TriageExceptionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = await session.get(ValidationException, cmd.exception_id)
    if row is None:
        raise NotFoundError("Validation exception not found")
    if row.version != cmd.expected_version:
        raise StaleVersionError("Exception changed since this request was prepared", current_version=row.version)
    if actor_user_id == row.requested_by_user_id:
        raise ValidationFailedError("Signer must be independent of the requester (Document 106 row 165)")

    policy = await resolve_signature(session, record_type=RECORD_TYPE_EXCEPTION, action="triage")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.severity = cmd.severity
    row.gxp_impact = cmd.gxp_impact
    row.release_impact = cmd.release_impact
    row.root_cause = cmd.root_cause
    row.triaged_by_user_id = actor_user_id
    row.triaged_at = datetime.now(timezone.utc)
    row.version += 1

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_EXCEPTION, aggregate_id=row.id,
        version=row.version, action="Changed", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"severity": cmd.severity, "gxp_impact": cmd.gxp_impact}, event_type="ValidationExceptionTriaged",
        expected_version=cmd.expected_version, command_type="TriageException", site_id=site_id,
        signature_id=signature_id,
    )


class DefineRetestScopeCommand(CommandEnvelope):
    exception_id: uuid.UUID
    expected_version: int
    retest_plan: dict
    fix_ref: str | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def define_retest_scope(
    session: AsyncSession, cmd: DefineRetestScopeCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if not cmd.retest_plan:
        raise ValidationFailedError("retest_plan must not be empty")

    row = await session.get(ValidationException, cmd.exception_id)
    if row is None:
        raise NotFoundError("Validation exception not found")
    if row.version != cmd.expected_version:
        raise StaleVersionError("Exception changed since this request was prepared", current_version=row.version)
    if actor_user_id == row.requested_by_user_id:
        raise ValidationFailedError("Signer must be independent of the requester (Document 106 row 164)")

    policy = await resolve_signature(session, record_type=RECORD_TYPE_EXCEPTION, action="retest_plan")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.retest_plan = cmd.retest_plan
    row.issue_ref = cmd.fix_ref or row.issue_ref
    row.disposition = "RETEST"
    row.version += 1

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_EXCEPTION, aggregate_id=row.id,
        version=row.version, action="Approved", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"retest_plan": cmd.retest_plan}, event_type="ValidationRetestScopeDefined",
        expected_version=cmd.expected_version, command_type="DefineRetestScope", site_id=site_id,
        signature_id=signature_id,
    )


class DispositionExceptionCommand(CommandEnvelope):
    exception_id: uuid.UUID
    expected_version: int
    disposition: str
    residual_risk_rationale: str | None = None
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def disposition_exception(
    session: AsyncSession, cmd: DispositionExceptionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if cmd.disposition not in VEX_DISPOSITIONS:
        raise ValidationFailedError(f"disposition must be one of {VEX_DISPOSITIONS}")
    if cmd.disposition == "ACCEPTED_WITH_RATIONALE" and not cmd.residual_risk_rationale:
        raise ValidationFailedError("residual_risk_rationale is required for ACCEPTED_WITH_RATIONALE (VEX-FR-015)")
    if not cmd.reason:
        raise ValidationFailedError("reason is required to disposition a validation exception")

    row = await session.get(ValidationException, cmd.exception_id)
    if row is None:
        raise NotFoundError("Validation exception not found")
    if row.disposition == "CLOSED":
        old_history = list(row.reopen_history)
        old_history.append({"reopened_by": str(actor_user_id), "at": datetime.now(timezone.utc).isoformat()})
        row.reopen_history = old_history  # VEX-FR-020: reopening keeps history, never erases it
    if row.version != cmd.expected_version:
        raise StaleVersionError("Exception changed since this request was prepared", current_version=row.version)
    if actor_user_id == row.triaged_by_user_id:
        raise ValidationFailedError("Dispositioner must be independent of the triager (Document 106 row 163)")

    policy = await resolve_signature(session, record_type=RECORD_TYPE_EXCEPTION, action="disposition")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    old_disposition = row.disposition
    row.disposition = cmd.disposition
    row.residual_risk_rationale = cmd.residual_risk_rationale
    row.dispositioned_by_user_id = actor_user_id
    row.dispositioned_at = datetime.now(timezone.utc)
    row.version += 1

    # Document 06 (VLT-FR-001): a signed disposition decision is a regulated final record of this
    # dispositioning event, whatever the chosen outcome (including a "needs retest" routing decision).
    from app.modules.vault import service as vault_service
    await vault_service.release_master(
        session, object_type=RECORD_TYPE_EXCEPTION, business_id=str(row.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "exception_type": row.exception_type, "disposition": row.disposition,
            "residual_risk_rationale": row.residual_risk_rationale,
        },
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_EXCEPTION, aggregate_id=row.id,
        version=row.version, action="Released", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value={"disposition": old_disposition}, new_value={"disposition": cmd.disposition},
        event_type="ValidationExceptionDispositioned", expected_version=cmd.expected_version,
        command_type="DispositionException", site_id=site_id, signature_id=signature_id,
    )


async def get_exception_gate(session: AsyncSession, release_ref: str) -> dict:
    """Read-only: every open BLOCKING exception for a release (VEX-FR-016/022). ACCEPTED_WITH_RATIONALE
    exceptions are included too (VEX-FR-022: "open/accepted deviations automatically included in VSR")
    but do not themselves count as a `blocker` unless still OPEN or RETEST."""
    rows = (
        await session.execute(
            select(ValidationException).where(
                ValidationException.release_ref == release_ref, ValidationException.release_impact == "BLOCKING"
            )
        )
    ).scalars().all()
    blockers = [str(r.id) for r in rows if r.disposition in ("OPEN", "RETEST", "DEFERRED_BLOCKING")]
    accepted = [str(r.id) for r in rows if r.disposition == "ACCEPTED_WITH_RATIONALE"]
    return {
        "release_ref": release_ref, "gate_state": "BLOCKED" if blockers else "PASSED",
        "blockers": blockers, "accepted_with_rationale": accepted,
    }
