"""Document 92 (SPEC-VAL-014) Mutation Gateway command handlers -- Security Qualification, Vulnerability
Verification & Penetration Testing. Document 106 row 158: `security/{id}/approve` requires an `Approved`
signature from an independent QA Releaser, reason mandatory. `security/suites`, `security/tests` and
`security/findings` carry no Document 106 row -- unsigned.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import SecurityQualificationFinding, SecurityQualificationSuite
from app.modules.validation.shared import finalize, receipt_from_existing, resolve_signature, verify_reauth_and_consume
from app.mutation.errors import InvalidTransitionError, NotFoundError, SecurityReleaseBlockedError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_SUITE = "security_qualification_suite"


class CreateSecuritySuiteCommand(CommandEnvelope):
    release_ref: str
    deployment_profile: str
    threat_control_baseline_ref: str
    planned_tests: list[str] = []


async def create_security_suite(
    session: AsyncSession, cmd: CreateSecuritySuiteCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = SecurityQualificationSuite(
        release_ref=cmd.release_ref, deployment_profile=cmd.deployment_profile,
        threat_control_baseline_ref=cmd.threat_control_baseline_ref, planned_tests=cmd.planned_tests,
        state="PLANNED", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_SUITE, aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"release_ref": row.release_ref}, event_type="SecuritySuiteDefined", expected_version=None,
        command_type="CreateSecuritySuite", site_id=site_id,
    )


class RecordSecurityTestCommand(CommandEnvelope):
    suite_id: uuid.UUID
    control_ref: str
    result: str  # PASS | FAIL
    severity_if_failed: str = "MEDIUM"


async def record_security_test(
    session: AsyncSession, cmd: RecordSecurityTestCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    suite = await session.get(SecurityQualificationSuite, cmd.suite_id)
    if suite is None:
        raise NotFoundError("Security qualification suite not found")
    if cmd.result not in ("PASS", "FAIL"):
        raise ValidationFailedError("result must be PASS or FAIL")

    finding_id = None
    if cmd.result == "FAIL":
        from app.modules.validation.models import FINDING_SEVERITIES
        if cmd.severity_if_failed not in FINDING_SEVERITIES:
            raise ValidationFailedError(f"severity_if_failed must be one of {FINDING_SEVERITIES}")
        finding = SecurityQualificationFinding(
            suite_id=suite.id, source="MANUAL", control_ref=cmd.control_ref, severity=cmd.severity_if_failed,
            affected_release=suite.release_ref, state="OPEN", version=1,
        )
        session.add(finding)
        await session.flush()
        finding_id = finding.id

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_SUITE, aggregate_id=suite.id,
        version=suite.version, action="Changed", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value={"control_ref": cmd.control_ref, "result": cmd.result, "finding_id": str(finding_id) if finding_id else None},
        event_type="SecurityControlTestCompleted", expected_version=None, command_type="RecordSecurityTest",
        site_id=site_id,
    )


class ImportFindingCommand(CommandEnvelope):
    suite_id: uuid.UUID
    source: str  # SAST | SCA | IAC | CONTAINER | PENTEST | MANUAL
    control_ref: str
    severity: str
    vulnerability_ref: str | None = None


async def import_finding(
    session: AsyncSession, cmd: ImportFindingCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    suite = await session.get(SecurityQualificationSuite, cmd.suite_id)
    if suite is None:
        raise NotFoundError("Security qualification suite not found")
    from app.modules.validation.models import FINDING_SEVERITIES
    if cmd.severity not in FINDING_SEVERITIES:
        raise ValidationFailedError(f"severity must be one of {FINDING_SEVERITIES}")

    row = SecurityQualificationFinding(
        suite_id=suite.id, source=cmd.source, control_ref=cmd.control_ref, severity=cmd.severity,
        affected_release=suite.release_ref, vulnerability_ref=cmd.vulnerability_ref, state="OPEN", version=1,
    )
    session.add(row)
    await session.flush()

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="security_qualification_finding",
        aggregate_id=row.id, version=row.version, action="Created", actor_user_id=actor_user_id, reason=None,
        old_value=None, new_value={"source": cmd.source, "severity": cmd.severity, "control_ref": cmd.control_ref},
        event_type="PenTestFindingImported", expected_version=None, command_type="ImportFinding", site_id=site_id,
    )


async def _evaluate_gate(session: AsyncSession, suite: SecurityQualificationSuite) -> dict:
    """SECQ-FR-020: an OPEN CRITICAL/HIGH finding blocks release unless a formal, approved exception
    exists (`state == "ACCEPTED_WITH_EXCEPTION"`)."""
    findings = (
        await session.execute(select(SecurityQualificationFinding).where(SecurityQualificationFinding.suite_id == suite.id))
    ).scalars().all()
    blockers = [f.control_ref for f in findings if f.severity in ("HIGH", "CRITICAL") and f.state == "OPEN"]
    return {"blockers": blockers, "gate_state": "BLOCKED" if blockers else "PASSED", "finding_count": len(findings)}


async def get_security_gate(session: AsyncSession, suite_id: uuid.UUID) -> dict:
    suite = await session.get(SecurityQualificationSuite, suite_id)
    if suite is None:
        raise NotFoundError("Security qualification suite not found")
    return await _evaluate_gate(session, suite)


class ApproveSecuritySuiteCommand(CommandEnvelope):
    suite_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_security_suite(
    session: AsyncSession, cmd: ApproveSecuritySuiteCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    suite = await session.get(SecurityQualificationSuite, cmd.suite_id)
    if suite is None:
        raise NotFoundError("Security qualification suite not found")
    if suite.version != cmd.expected_version:
        raise StaleVersionError("Suite changed since this request was prepared", current_version=suite.version)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to approve a security qualification")

    gate = await _evaluate_gate(session, suite)
    await write_outbox_event(
        session, event_type="SecurityQualificationGateEvaluated", aggregate_type=RECORD_TYPE_SUITE,
        aggregate_id=suite.id, aggregate_version=suite.version, payload=gate, correlation_id=uuid.uuid4(),
    )
    if gate["blockers"]:
        raise SecurityReleaseBlockedError("Unresolved critical/high security findings", blockers=gate["blockers"])

    policy = await resolve_signature(session, record_type=RECORD_TYPE_SUITE, action="approve")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=suite.id, record_version=suite.version,
        )

    suite.state = "QUALIFIED"
    suite.version += 1

    # Document 06 (VLT-FR-001): an approved security qualification is a regulated final record.
    from app.modules.vault import service as vault_service
    await vault_service.release_master(
        session, object_type=RECORD_TYPE_SUITE, business_id=str(suite.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "release_ref": suite.release_ref, "deployment_profile": suite.deployment_profile,
            "threat_control_baseline_ref": suite.threat_control_baseline_ref,
        },
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_SUITE, aggregate_id=suite.id,
        version=suite.version, action="Approved", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value=None, new_value={"state": "QUALIFIED"}, event_type="SecurityQualificationApproved",
        expected_version=cmd.expected_version, command_type="ApproveSecuritySuite", site_id=site_id,
        signature_id=signature_id,
    )
