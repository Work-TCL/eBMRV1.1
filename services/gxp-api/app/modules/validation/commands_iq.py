"""Document 83 (SPEC-VAL-005) Mutation Gateway command handlers -- Installation Qualification (IQ) &
Installed Baseline Verification. Document 106 row 149: `executions/{id}/complete` requires a `Performed`
signature from the qualified performer (no dedicated role/independence/reason). Row 148: `executions/
{id}/approve` requires an `Approved` signature from an independent QA Releaser, reason mandatory.
`iq/protocols` (defining the expected baseline) carries no Document 106 row -- unsigned.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import IqExecution, IqProtocol
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

RECORD_TYPE_IQ_EXEC = "iq_execution"


class CreateIqProtocolCommand(CommandEnvelope):
    environment: str
    release_ref: str
    deployment_profile: str
    expected_components: list[dict] = []
    checks: list[dict] = []
    acceptance_criteria: str


async def create_iq_protocol(
    session: AsyncSession, cmd: CreateIqProtocolCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = IqProtocol(
        site_id=site_id, environment=cmd.environment, release_ref=cmd.release_ref,
        deployment_profile=cmd.deployment_profile, expected_components=cmd.expected_components,
        checks=cmd.checks, acceptance_criteria=cmd.acceptance_criteria, state="EFFECTIVE", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="iq_protocol", aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"environment": row.environment, "release_ref": row.release_ref},
        event_type="IqProtocolDefined", expected_version=None, command_type="CreateIqProtocol", site_id=site_id,
    )


class StartIqExecutionCommand(CommandEnvelope):
    protocol_id: uuid.UUID
    installed_inventory: dict
    check_results: list[dict] = []
    is_delta_iq: bool = False
    performer_user_id: uuid.UUID | None = None


async def start_iq_execution(
    session: AsyncSession, cmd: StartIqExecutionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    protocol = await session.get(IqProtocol, cmd.protocol_id)
    if protocol is None:
        raise NotFoundError("IQ protocol not found")
    if not cmd.installed_inventory:
        raise ValidationFailedError("installed_inventory must not be empty (IQ-FR-001)")

    # IQ-FR-018: any mismatch against the protocol's declared expected components becomes a deviation --
    # never silently ignored.
    deviations = []
    expected_by_name = {c.get("name"): c for c in protocol.expected_components}
    for name, expected in expected_by_name.items():
        actual = cmd.installed_inventory.get(name)
        if actual is not None and expected.get("version") and actual != expected.get("version"):
            deviations.append({"component": name, "expected": expected.get("version"), "actual": actual})

    row = IqExecution(
        protocol_id=protocol.id, protocol_version=protocol.version, installed_inventory=cmd.installed_inventory,
        check_results=cmd.check_results, deviations=deviations, performer_user_id=cmd.performer_user_id or actor_user_id,
        status="IN_PROGRESS", is_delta_iq=cmd.is_delta_iq, version=1,
    )
    session.add(row)
    await session.flush()

    await write_outbox_event(
        session, event_type="IQPrerequisitesVerified", aggregate_type=RECORD_TYPE_IQ_EXEC, aggregate_id=row.id,
        aggregate_version=1, payload={"check_results": cmd.check_results}, correlation_id=uuid.uuid4(),
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_IQ_EXEC, aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"protocol_id": str(protocol.id), "deviation_count": len(deviations)},
        event_type="InstalledInventoryCaptured", expected_version=None, command_type="StartIqExecution",
        site_id=site_id,
    )


class CompleteIqExecutionCommand(CommandEnvelope):
    execution_id: uuid.UUID
    expected_version: int
    evidence_manifest: list[dict] = []
    result: str  # PASS | FAIL
    challenge_id: uuid.UUID
    reauth_password: str


async def complete_iq_execution(
    session: AsyncSession, cmd: CompleteIqExecutionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)
    if cmd.result not in ("PASS", "FAIL"):
        raise ValidationFailedError("result must be PASS or FAIL")
    await verify_evidence_refs(session, cmd.evidence_manifest)  # AG-12/OBJ-FR-004

    row = await session.get(IqExecution, cmd.execution_id)
    if row is None:
        raise NotFoundError("IQ execution not found")
    if row.status != "IN_PROGRESS":
        raise InvalidTransitionError("IQ execution is not IN_PROGRESS", current_state=row.status)
    if row.version != cmd.expected_version:
        raise StaleVersionError("IQ execution changed since this request was prepared", current_version=row.version)

    policy = await resolve_signature(session, record_type=RECORD_TYPE_IQ_EXEC, action="complete")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.evidence_manifest = cmd.evidence_manifest
    row.status = cmd.result
    row.completed_at = datetime.now(timezone.utc)
    row.version += 1

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_IQ_EXEC, aggregate_id=row.id,
        version=row.version, action="Performed", actor_user_id=actor_user_id, reason=None,
        old_value={"status": "IN_PROGRESS"}, new_value={"status": cmd.result}, event_type="IQCompleted",
        expected_version=cmd.expected_version, command_type="CompleteIqExecution", site_id=site_id,
        signature_id=signature_id,
    )


class ApproveIqExecutionCommand(CommandEnvelope):
    execution_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_iq_execution(
    session: AsyncSession, cmd: ApproveIqExecutionCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = await session.get(IqExecution, cmd.execution_id)
    if row is None:
        raise NotFoundError("IQ execution not found")
    if row.status not in ("PASS", "FAIL"):
        raise InvalidTransitionError("IQ execution is not complete", current_state=row.status)
    if row.version != cmd.expected_version:
        raise StaleVersionError("IQ execution changed since this request was prepared", current_version=row.version)
    if row.deviations and not cmd.reason:
        raise ValidationFailedError("reason is required to approve an IQ execution with open deviations (IQ-FR-021)")
    if not cmd.reason:
        raise ValidationFailedError("reason is required to approve an IQ execution")
    if actor_user_id == row.performer_user_id:
        raise ValidationFailedError("Approver must be independent of the performer (Document 106 row 148)")

    policy = await resolve_signature(session, record_type=RECORD_TYPE_IQ_EXEC, action="approve")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.approved_by_user_id = actor_user_id
    row.approved_at = datetime.now(timezone.utc)
    row.version += 1

    # Document 06 (VLT-FR-001): an approved IQ execution is a regulated final record -- real vault
    # snapshot in the same transaction as the approval.
    from app.modules.vault import service as vault_service
    await vault_service.release_master(
        session, object_type=RECORD_TYPE_IQ_EXEC, business_id=str(row.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "protocol_id": str(row.protocol_id), "installed_inventory": row.installed_inventory,
            "check_results": row.check_results, "deviations": row.deviations, "status": row.status,
        },
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_IQ_EXEC, aggregate_id=row.id,
        version=row.version, action="Approved", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value=None, new_value={"approved": True}, event_type="IQApproved",
        expected_version=cmd.expected_version, command_type="ApproveIqExecution", site_id=site_id,
        signature_id=signature_id,
    )
