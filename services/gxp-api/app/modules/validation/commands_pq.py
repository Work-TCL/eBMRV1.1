"""Document 85 (SPEC-VAL-007) Mutation Gateway command handlers -- Performance Qualification (PQ),
UAT & Business Process Verification.

Signature policy (Document 106):
  * Row 151 -- `POST /validation/v1/pq/{id}/approve` requires an `Approved` signature from an
    independent QA Releaser (the "Module approver role (QA Manager / Head of Quality per record class)"
    signer class, resolved to `QA Releaser` -- the same mapping WP-12 uses for rows 145/147/148/150/
    152/154-158), reason mandatory, signer independent of the scenario author.
  * `pq/scenarios`, `pq/scenarios/{id}/participants`, `pq/executions` carry no Document 106 row --
    unsigned, RBAC-gated only.

`record_pq_usability_observation()` (function catalogue FN-0826) has no dedicated endpoint in Document
85 §7 (which lists exactly four APIs). Usability observations (PQ-FR-015) are therefore captured as
part of `execute_pq_scenario()` -- each entry in the execution's `observations` list produces its own
`PQUsabilityObservationRecorded` outbox event against the `pq_execution` aggregate. This mirrors the
WP-12 precedent where a spec's §7 enumerates only the state-changing POSTs and a derived domain
function is reached from inside another handler.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models_wp14 import PqExecution, PqScenario
from app.modules.validation.shared import (
    finalize,
    receipt_from_existing,
    resolve_signature,
    verify_evidence_refs,
    verify_reauth_and_consume,
)
from app.mutation.errors import (
    InvalidTransitionError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_PQ_SCENARIO = "pq_scenario"
RECORD_TYPE_PQ_EXECUTION = "pq_execution"

_VALID_PROCESS_AREAS = (
    "material_flow", "qc_flow", "deviation_flow", "signature_flow", "edge_device_flow",
    "erp_lims_flow", "shift_handoff", "business_process", "exception_recovery",
)
_VALID_PROFILES = ("prefilled_syringe", "injector", "inhalation", "coated_device")


# =====================================================================================================
# createPQScenario() -- FN-0823
# =====================================================================================================

class CreatePqScenarioCommand(CommandEnvelope):
    scenario_number: str
    process_area: str
    intended_workflow: str
    acceptance_criteria: str
    product_profile: str | None = None
    representative_roles: list[str] = []
    training_prerequisites: list[dict] = []
    prerequisites: list[dict] = []
    steps: list[dict] = []
    interfaces_equipment: list[dict] = []
    exception_paths: list[dict] = []
    is_uat: bool = False
    vmp_equivalence_ref: str | None = None
    is_template: bool = False
    retention_class: str | None = None


async def create_pq_scenario(
    session: AsyncSession, cmd: CreatePqScenarioCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    if cmd.process_area not in _VALID_PROCESS_AREAS:
        raise ValidationFailedError("process_area is not a recognised PQ process area", process_area=cmd.process_area)
    if cmd.product_profile is not None and cmd.product_profile not in _VALID_PROFILES:
        # PQ-FR-006: a product profile is included only when applicable -- but when named it must be real.
        raise ValidationFailedError("product_profile is not a recognised profile", product_profile=cmd.product_profile)
    if not cmd.intended_workflow.strip():
        raise ValidationFailedError("intended_workflow is required (PQ-FR-001/003)")
    if not cmd.acceptance_criteria.strip():
        raise ValidationFailedError("acceptance_criteria is required (PQ-FR-018)")
    if cmd.is_uat and not cmd.vmp_equivalence_ref:
        # PQ-FR-017: a controlled UAT may satisfy PQ evidence only if the VMP equivalence criteria are recorded.
        raise ValidationFailedError("vmp_equivalence_ref is required when is_uat is true (PQ-FR-017)")

    row = PqScenario(
        site_id=site_id, scenario_number=cmd.scenario_number, product_profile=cmd.product_profile,
        process_area=cmd.process_area, intended_workflow=cmd.intended_workflow,
        representative_roles=cmd.representative_roles, training_prerequisites=cmd.training_prerequisites,
        prerequisites=cmd.prerequisites, steps=cmd.steps, interfaces_equipment=cmd.interfaces_equipment,
        exception_paths=cmd.exception_paths, acceptance_criteria=cmd.acceptance_criteria,
        is_uat=cmd.is_uat, vmp_equivalence_ref=cmd.vmp_equivalence_ref, is_template=cmd.is_template,
        participants=[], authored_by_user_id=actor_user_id, retention_class=cmd.retention_class,
        state="DRAFT", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_PQ_SCENARIO,
        aggregate_id=row.id, version=row.version, action="Created", actor_user_id=actor_user_id,
        reason=None, old_value=None,
        new_value={"scenario_number": row.scenario_number, "process_area": row.process_area,
                   "is_uat": row.is_uat, "is_template": row.is_template},
        event_type="PQScenarioCreated", expected_version=None, command_type="CreatePQScenario",
        site_id=site_id,
    )


# =====================================================================================================
# assignPQParticipants() -- FN-0824
# =====================================================================================================

class AssignPqParticipantsCommand(CommandEnvelope):
    scenario_id: uuid.UUID
    expected_version: int
    participants: list[dict]  # [{user_id, role, training_refs: [...], trained: bool}]


async def assign_pq_participants(
    session: AsyncSession, cmd: AssignPqParticipantsCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = await session.get(PqScenario, cmd.scenario_id)
    if row is None:
        raise NotFoundError("PQ scenario not found")
    if row.state not in ("DRAFT", "PARTICIPANTS_ASSIGNED"):
        raise InvalidTransitionError("participants can only be assigned before execution", current_state=row.state)
    if row.version != cmd.expected_version:
        raise StaleVersionError("PQ scenario changed since this request was prepared", current_version=row.version)
    if not cmd.participants:
        raise ValidationFailedError("at least one participant is required (PQ-FR-004)")
    for p in cmd.participants:
        if not p.get("user_id") or not p.get("role"):
            raise ValidationFailedError("each participant needs user_id and role (PQ-FR-004)")

    row.participants = cmd.participants
    row.state = "PARTICIPANTS_ASSIGNED"
    row.version += 1

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_PQ_SCENARIO,
        aggregate_id=row.id, version=row.version, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_value={"state": "DRAFT"},
        new_value={"state": row.state, "participant_count": len(cmd.participants)},
        event_type="PQParticipantsAssigned", expected_version=cmd.expected_version,
        command_type="AssignPQParticipants", site_id=site_id,
    )


# =====================================================================================================
# executePQScenario() -- FN-0825 (+ recordPQUsabilityObservation() FN-0826, folded in)
# =====================================================================================================

class ExecutePqScenarioCommand(CommandEnvelope):
    scenario_id: uuid.UUID
    environment: str
    config_ref: str
    participant_identities: list[str]
    dataset_ref: str | None = None
    step_results: list[dict] = []          # [{step, outcome: PASS|FAIL, notes}]
    observations: list[dict] = []          # [{observation, severity, impact, change_candidate: bool}]
    deviations: list[dict] = []            # [{ref, severity, critical: bool, resolved: bool}]
    evidence_manifest: list[dict] = []
    result: str                           # COMPLETED | FAILED | INTERRUPTED
    prior_execution_id: uuid.UUID | None = None


async def execute_pq_scenario(
    session: AsyncSession, cmd: ExecutePqScenarioCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    if cmd.result not in ("COMPLETED", "FAILED", "INTERRUPTED"):
        raise ValidationFailedError("result must be COMPLETED, FAILED or INTERRUPTED")

    scenario = await session.get(PqScenario, cmd.scenario_id)
    if scenario is None:
        raise NotFoundError("PQ scenario not found")
    if scenario.state not in ("PARTICIPANTS_ASSIGNED", "IN_EXECUTION", "READY_FOR_ACCEPTANCE"):
        raise InvalidTransitionError(
            "PQ scenario must have participants assigned before execution (PQ-FR-005/018)",
            current_state=scenario.state,
        )
    if not cmd.participant_identities:
        raise ValidationFailedError("participant_identities is required (PQ-FR-004)")

    # PQ-FR-005 / PQ-FR-018: every executing identity must be a trained participant on this scenario.
    trained = {str(p.get("user_id")) for p in scenario.participants if p.get("trained")}
    untrained = [u for u in cmd.participant_identities if str(u) not in trained]

    # Document 85 §11: an evidence-upload / DB failure must not produce a PASS. Any evidence_manifest
    # entry that names a real Evidence Store object must be FINALIZED/ARCHIVED before COMPLETED.
    if cmd.result == "COMPLETED":
        await verify_evidence_refs(session, cmd.evidence_manifest)
        if untrained:
            raise ValidationFailedError(
                "a COMPLETED PQ execution cannot include untrained participant identities (PQ-FR-005)",
                untrained=untrained,
            )

    critical_unresolved = [d for d in cmd.deviations if d.get("critical") and not d.get("resolved")]
    go_live_blocker = bool(critical_unresolved) or bool(untrained) or cmd.result != "COMPLETED"

    row = PqExecution(
        scenario_id=scenario.id, scenario_version=scenario.version,
        prior_execution_id=cmd.prior_execution_id, participant_identities=cmd.participant_identities,
        environment=cmd.environment, config_ref=cmd.config_ref, dataset_ref=cmd.dataset_ref,
        step_results=cmd.step_results, observations=cmd.observations, deviations=cmd.deviations,
        evidence_manifest=cmd.evidence_manifest, result=cmd.result, go_live_blocker=go_live_blocker,
        completed_at=datetime.now(timezone.utc) if cmd.result != "IN_PROGRESS" else None,
        state=cmd.result, version=1,
    )
    session.add(row)
    await session.flush()

    if scenario.state == "PARTICIPANTS_ASSIGNED":
        scenario.state = "IN_EXECUTION"
        scenario.version += 1

    # PQ-FR-015: each usability observation is its own recorded validation observation / change
    # candidate -- one PQUsabilityObservationRecorded event per entry (recordPQUsabilityObservation,
    # FN-0826, has no dedicated §7 endpoint).
    for i, obs in enumerate(cmd.observations):
        await write_outbox_event(
            session, event_type="PQUsabilityObservationRecorded", aggregate_type=RECORD_TYPE_PQ_EXECUTION,
            aggregate_id=row.id, aggregate_version=1,
            payload={"observation_index": i, "severity": obs.get("severity"),
                     "impact": obs.get("impact"), "change_candidate": bool(obs.get("change_candidate"))},
            correlation_id=uuid.uuid4(),
        )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_PQ_EXECUTION,
        aggregate_id=row.id, version=row.version, action="Performed", actor_user_id=actor_user_id,
        reason=None, old_value=None,
        new_value={"scenario_id": str(scenario.id), "result": cmd.result,
                   "go_live_blocker": go_live_blocker, "observation_count": len(cmd.observations)},
        event_type="PQScenarioCompleted", expected_version=None, command_type="ExecutePQScenario",
        site_id=site_id,
    )


# =====================================================================================================
# approvePQ() -- FN-0827
# =====================================================================================================

class ApprovePqCommand(CommandEnvelope):
    scenario_id: uuid.UUID
    expected_version: int
    reason: str
    decision: str = "ACCEPTED"   # ACCEPTED | REJECTED
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_pq(
    session: AsyncSession, cmd: ApprovePqCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    if cmd.decision not in ("ACCEPTED", "REJECTED"):
        raise ValidationFailedError("decision must be ACCEPTED or REJECTED")
    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required to approve/reject PQ (Document 106 row 151)")

    row = await session.get(PqScenario, cmd.scenario_id)
    if row is None:
        raise NotFoundError("PQ scenario not found")
    if row.state not in ("IN_EXECUTION", "READY_FOR_ACCEPTANCE"):
        raise InvalidTransitionError("PQ scenario has no completed executions to accept", current_state=row.state)
    if row.version != cmd.expected_version:
        raise StaleVersionError("PQ scenario changed since this request was prepared", current_version=row.version)
    # PQ-FR-019 / Document 106 row 151 SoD: the approver is independent of the scenario author.
    if actor_user_id == row.authored_by_user_id:
        raise ValidationFailedError(
            "the PQ approver must be independent of the scenario author (Document 106 row 151)"
        )

    prior_state = row.state

    # PQ-FR-018: a critical process/procedure/training failure blocks PQ acceptance. An ACCEPTED
    # decision requires at least one COMPLETED execution and no execution left as a go-live blocker.
    executions = list(
        (await session.execute(select(PqExecution).where(PqExecution.scenario_id == row.id))).scalars()
    )
    completed = [e for e in executions if e.result == "COMPLETED"]
    blockers = [e for e in executions if e.go_live_blocker]
    if cmd.decision == "ACCEPTED":
        if not completed:
            raise ValidationFailedError("cannot accept PQ with no COMPLETED execution (PQ-FR-018)")
        if blockers:
            raise ValidationFailedError(
                "cannot accept PQ while an execution is a go-live blocker (PQ-FR-018)",
                blocking_executions=[str(e.id) for e in blockers],
            )

    policy = await resolve_signature(session, record_type=RECORD_TYPE_PQ_SCENARIO, action="approve")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.state = "ACCEPTED" if cmd.decision == "ACCEPTED" else "REJECTED"
    row.approved_by_user_id = actor_user_id
    row.approved_at = datetime.now(timezone.utc)
    row.signature_id = signature_id
    row.version += 1

    if cmd.decision == "ACCEPTED":
        # Document 06 (VLT-FR-001): an accepted PQ / site acceptance is a regulated final record.
        from app.modules.vault import service as vault_service
        await vault_service.release_master(
            session, object_type=RECORD_TYPE_PQ_SCENARIO, business_id=str(row.id), site_id=site_id,
            actor_user_id=actor_user_id,
            canonical_payload={
                "scenario_number": row.scenario_number, "process_area": row.process_area,
                "intended_workflow": row.intended_workflow, "acceptance_criteria": row.acceptance_criteria,
                "participants": row.participants, "completed_executions": [str(e.id) for e in completed],
            },
        )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_PQ_SCENARIO,
        aggregate_id=row.id, version=row.version, action="Approved", actor_user_id=actor_user_id,
        reason=cmd.reason, old_value={"state": prior_state},
        new_value={"state": row.state, "decision": cmd.decision}, event_type="PQApproved",
        expected_version=cmd.expected_version, command_type="ApprovePQ", site_id=site_id,
        signature_id=signature_id,
    )
