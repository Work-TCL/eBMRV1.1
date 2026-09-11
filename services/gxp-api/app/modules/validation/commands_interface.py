"""Document 90 (SPEC-VAL-012) Mutation Gateway command handlers -- Integration, Edge, Device, Peripheral
& Interface Validation. Document 106 row 156: `interfaces/{id}/approve` requires an `Approved` signature
from an independent QA Releaser, reason mandatory -- binds to `interface_validation_profile` (the
overall qualification verdict for one interface), aggregating every test execution against it.
`interfaces/profiles` carries no Document 106 row -- unsigned.
"""

from __future__ import annotations

import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import InterfaceTestExecution, InterfaceValidationProfile
from app.modules.validation.shared import finalize, receipt_from_existing, resolve_signature, verify_reauth_and_consume
from app.mutation.errors import InvalidTransitionError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_PROFILE = "interface_validation_profile"


class CreateInterfaceProfileCommand(CommandEnvelope):
    provider_or_device: str
    contract_ref: str
    contract_version: str
    intended_use: str
    risk_category: str
    auth_expectation: str
    source_time_quality_expectation: dict = {}
    failure_scenarios: list[str] = []


async def create_interface_profile(
    session: AsyncSession, cmd: CreateInterfaceProfileCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    from app.modules.validation.models import RISK_CATEGORIES
    if cmd.risk_category not in RISK_CATEGORIES:
        raise ValidationFailedError(f"risk_category must be one of {RISK_CATEGORIES}")

    row = InterfaceValidationProfile(
        provider_or_device=cmd.provider_or_device, contract_ref=cmd.contract_ref, contract_version=cmd.contract_version,
        intended_use=cmd.intended_use, risk_category=cmd.risk_category, auth_expectation=cmd.auth_expectation,
        source_time_quality_expectation=cmd.source_time_quality_expectation, failure_scenarios=cmd.failure_scenarios,
        state="EFFECTIVE", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_PROFILE, aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"provider_or_device": row.provider_or_device, "contract_version": row.contract_version},
        event_type="InterfaceProfileDefined", expected_version=None, command_type="CreateInterfaceProfile",
        site_id=site_id,
    )


async def _record_interface_test(
    session: AsyncSession, cmd, actor_user_id: uuid.UUID, site_id: uuid.UUID | None, event_type: str,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    profile = await session.get(InterfaceValidationProfile, cmd.profile_id)
    if profile is None:
        raise NotFoundError("Interface validation profile not found")

    row = InterfaceTestExecution(
        profile_id=profile.id, profile_version=profile.version, scenario=cmd.scenario, raw_inputs=cmd.raw_inputs,
        canonical_outputs=cmd.canonical_outputs, gxp_result=cmd.gxp_result,
        external_reconciliation=cmd.external_reconciliation, performed_by_user_id=actor_user_id,
        status=cmd.status, version=1,
    )
    session.add(row)
    await session.flush()

    if cmd.external_reconciliation:
        await write_outbox_event(
            session, event_type="InterfaceReconciliationVerified", aggregate_type="interface_test_execution",
            aggregate_id=row.id, aggregate_version=1, payload=cmd.external_reconciliation, correlation_id=uuid.uuid4(),
        )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="interface_test_execution", aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"profile_id": str(profile.id), "scenario": cmd.scenario, "status": cmd.status},
        event_type=event_type, expected_version=None, command_type="RecordInterfaceTest", site_id=site_id,
    )


class RecordInterfaceTestCommand(CommandEnvelope):
    profile_id: uuid.UUID
    scenario: str
    raw_inputs: dict = {}
    canonical_outputs: dict = {}
    gxp_result: dict = {}
    external_reconciliation: dict = {}
    status: str = "PASS"


async def record_interface_test(
    session: AsyncSession, cmd: RecordInterfaceTestCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    return await _record_interface_test(session, cmd, actor_user_id, site_id, "InterfaceContractTestsCompleted")


class RecordEdgeOutageTestCommand(CommandEnvelope):
    profile_id: uuid.UUID
    scenario: str = "edge_outage"
    raw_inputs: dict = {}
    canonical_outputs: dict = {}
    gxp_result: dict = {}
    external_reconciliation: dict = {}
    status: str = "PASS"


async def record_edge_outage_test(
    session: AsyncSession, cmd: RecordEdgeOutageTestCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    return await _record_interface_test(session, cmd, actor_user_id, site_id, "EdgeOutageQualificationCompleted")


class ApproveInterfaceProfileCommand(CommandEnvelope):
    profile_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_interface_profile(
    session: AsyncSession, cmd: ApproveInterfaceProfileCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    profile = await session.get(InterfaceValidationProfile, cmd.profile_id)
    if profile is None:
        raise NotFoundError("Interface validation profile not found")
    if profile.version != cmd.expected_version:
        raise StaleVersionError("Profile changed since this request was prepared", current_version=profile.version)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to approve an interface qualification")

    executions = (
        await session.execute(select(InterfaceTestExecution).where(InterfaceTestExecution.profile_id == profile.id))
    ).scalars().all()
    if not executions:
        raise InvalidTransitionError("No interface test executions recorded for this profile")
    unresolved = [e.scenario for e in executions if e.status != "PASS"]
    if unresolved:
        raise InvalidTransitionError("Unresolved interface test scenarios", unresolved=unresolved)

    policy = await resolve_signature(session, record_type=RECORD_TYPE_PROFILE, action="approve")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=profile.id, record_version=profile.version,
        )

    profile.state = "QUALIFIED"
    profile.version += 1

    # Document 06 (VLT-FR-001): a qualified interface profile is a regulated final record.
    from app.modules.vault import service as vault_service
    await vault_service.release_master(
        session, object_type=RECORD_TYPE_PROFILE, business_id=str(profile.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "provider_or_device": profile.provider_or_device, "contract_ref": profile.contract_ref,
            "contract_version": profile.contract_version,
        },
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_PROFILE, aggregate_id=profile.id,
        version=profile.version, action="Approved", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value={"state": "EFFECTIVE"}, new_value={"state": "QUALIFIED"}, event_type="InterfaceQualificationApproved",
        expected_version=cmd.expected_version, command_type="ApproveInterfaceProfile", site_id=site_id,
        signature_id=signature_id,
    )
