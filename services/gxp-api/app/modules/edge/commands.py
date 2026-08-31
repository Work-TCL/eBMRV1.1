"""Document 43 (SPEC-EDGE-001) — server-side slice only (see `models.py` module docstring for the scope
split). Exactly the 6 declared server APIs (§8), no invented endpoint, same discipline as every prior
WP-06 module. `enroll_gateway`/`rotate_gateway_certificate` are human-authenticated (`get_current_actor`);
`accept_observation_batch`/`report_health`/`report_security_event` are service-identity-authenticated
(`get_service_identity`, SG-120) and structurally never touch the signature ceremony (Document 106 P7).

`EdgeGateway.version` is bumped on every accepted mutation (including the 3 machine ops) so
`expected_version` optimistic concurrency applies uniformly, matching every op's declared
`expected_version: required` in `docs/generated/06_API_CATALOGUE.yaml`.
"""

import uuid
from datetime import datetime, timezone

from pydantic import BaseModel, ConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import (
    AuthenticatedServiceIdentity,
    format_service_bearer_token,
    generate_service_credential,
    verify_password,
)
from app.modules.edge.models import (
    OBSERVATION_QUALITIES,
    SECURITY_EVENT_SEVERITIES,
    EdgeCertificateRotation,
    EdgeConfigSnapshot,
    EdgeEnrollmentToken,
    EdgeGateway,
    EdgeHealthSnapshot,
    EdgeObservation,
    EdgeSecurityEvent,
)
from app.modules.iam.models import ServiceIdentity, User
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    CertRotationFailedError,
    DuplicateGatewayError,
    EnrollmentTokenInvalidError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

# EDGE-FR-003/017/025: a gateway that has been pulled out of trust cannot submit new evidence.
BLOCKED_FOR_INGESTION_STATES = ("SECURITY_HOLD", "DECOMMISSIONED", "SUSPENDED")


def gateway_record_hash(gateway: EdgeGateway) -> str:
    return sha256_hex({"id": str(gateway.id), "version": gateway.version, "lifecycle_state": gateway.lifecycle_state})


async def _load_gateway_for_update(session: AsyncSession, gateway_id: uuid.UUID, expected_version: int) -> EdgeGateway:
    result = await session.execute(select(EdgeGateway).where(EdgeGateway.id == gateway_id).with_for_update())
    gateway = result.scalar_one_or_none()
    if gateway is None:
        raise NotFoundError("Edge gateway not found")
    if gateway.version != expected_version:
        raise StaleVersionError(
            "Edge gateway was modified since it was read", expected_version=expected_version, current_version=gateway.version
        )
    return gateway


# ---------------------------------------------------------------------------
# EnrollGateway — EDGE-FR-001/002/003. Signature per SG-118 (Admin signs, independent=False,
# reason_required=True) — interim baseline, no Document 106 row exists for this action.
# ---------------------------------------------------------------------------


class EnrollGatewayCommand(CommandEnvelope):
    bootstrap_token: str
    site_id: uuid.UUID
    gateway_fingerprint: str
    csr: str | None = None
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


class GatewayEnrollmentResult(MutationReceipt):
    """§4's `GatewayEnrollmentResult{gateway_id,cert_chain,config_endpoint,expires_at}`, adapted: no real
    PKI issuance exists in this codebase (`cert_chain` -> the fingerprint captured at enrollment, same
    "captured, unenforced" precedent as `equipment.firmware_version`), and `bearer_token` is the SG-120
    service credential, returned exactly once and never persisted in plaintext or logged."""

    gateway_id: uuid.UUID
    bearer_token: str | None = None
    config_endpoint: str


async def enroll_gateway(
    session: AsyncSession, cmd: EnrollGatewayCommand, actor_user_id: uuid.UUID
) -> GatewayEnrollmentResult:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        # SG-120 known limitation: a replayed enrollment cannot re-issue the one-time bearer credential
        # (it was never stored in recoverable form) -- the receipt confirms the prior commit only.
        return GatewayEnrollmentResult(
            command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
            audit_event_id=existing.id, correlation_id=existing.id, gateway_id=existing.aggregate_id,
            bearer_token=None, config_endpoint=f"/edge/v1/gateways/{existing.aggregate_id}/configuration",
        )

    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required to enroll a gateway")

    token_hash = sha256_hex(cmd.bootstrap_token)
    token_result = await session.execute(
        select(EdgeEnrollmentToken).where(EdgeEnrollmentToken.token_hash == token_hash).with_for_update()
    )
    token = token_result.scalar_one_or_none()
    if token is None or token.status != "unused":
        raise EnrollmentTokenInvalidError("Bootstrap token is invalid, unknown, or already used")
    if token.expires_at.replace(tzinfo=timezone.utc) < datetime.now(timezone.utc):
        raise EnrollmentTokenInvalidError("Bootstrap token has expired")
    if token.site_id != cmd.site_id:
        raise EnrollmentTokenInvalidError("Bootstrap token is not scoped to this site")

    conflict = (
        await session.execute(select(EdgeGateway).where(EdgeGateway.certificate_fingerprint == cmd.gateway_fingerprint))
    ).scalar_one_or_none()
    if conflict is not None:
        raise DuplicateGatewayError("A gateway with this fingerprint is already enrolled", fingerprint=cmd.gateway_fingerprint)

    policy = await signature_service.resolve_signature_requirement(session, record_type="edge_gateway", action="enroll")
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        # No prior aggregate version exists yet (this is a creation command) -- bind the challenge to the
        # consumed token and requested fingerprint instead, same "creation command has no expected_version"
        # precedent CommandEnvelope's own docstring states.
        pre_hash = sha256_hex({"bootstrap_token_id": str(token.id), "gateway_fingerprint": cmd.gateway_fingerprint})
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id, record_version=0, record_hash=pre_hash,
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    gateway = EdgeGateway(
        site_id=cmd.site_id, host_identity=cmd.gateway_fingerprint, certificate_fingerprint=cmd.gateway_fingerprint,
        enrolled_by_user_id=actor_user_id, lifecycle_state="ENROLLED", version=1,
    )
    session.add(gateway)
    await session.flush()

    token.status = "consumed"
    token.consumed_by_gateway_id = gateway.id

    raw_secret, credential_hash = generate_service_credential()
    identity = ServiceIdentity(
        identity_type="edge_gateway", subject_ref=gateway.id, credential_hash=credential_hash, status="active"
    )
    session.add(identity)
    await session.flush()
    bearer_token = format_service_bearer_token(identity.id, raw_secret)

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=gateway.site_id, aggregate_type="edge_gateway", aggregate_id=gateway.id,
        aggregate_version=gateway.version, action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=cmd.reason, old_value=None, new_value={"lifecycle_state": gateway.lifecycle_state}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="GatewayEnrolled", aggregate_type="edge_gateway", aggregate_id=gateway.id,
        aggregate_version=gateway.version, payload={"id": str(gateway.id), "site_id": str(gateway.site_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=gateway.site_id, command_type="EnrollGateway", aggregate_type="edge_gateway",
        aggregate_id=gateway.id, expected_version=None, resulting_version=gateway.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return GatewayEnrollmentResult(
        command_id=receipt.id, aggregate_id=gateway.id, resulting_version=gateway.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
        gateway_id=gateway.id, bearer_token=bearer_token,
        config_endpoint=f"/edge/v1/gateways/{gateway.id}/configuration",
    )


# ---------------------------------------------------------------------------
# GetGatewayConfiguration — read-only, no signature policy row (matches
# docs/generated/06_API_CATALOGUE.yaml's own signature_required: false for this op).
# ---------------------------------------------------------------------------


async def get_gateway_configuration(session: AsyncSession, gateway_id: uuid.UUID) -> dict:
    gateway = await session.get(EdgeGateway, gateway_id)
    if gateway is None:
        raise NotFoundError("Edge gateway not found")
    if gateway.active_config_version_id is None:
        raise NotFoundError("No active configuration snapshot exists for this gateway")
    snapshot = await session.get(EdgeConfigSnapshot, gateway.active_config_version_id)
    return {
        "gateway_id": str(gateway.id),
        "config_version": snapshot.config_version,
        "payload": snapshot.payload_json,
        "checksum": snapshot.checksum,
        "activated_at": snapshot.activated_at.isoformat(),
    }


# ---------------------------------------------------------------------------
# AcceptObservationBatch — EDGE-FR-009..016. Service-identity path; `signature_required=False` per
# SG-119 (P7: a device identity can never satisfy a signature). Per-envelope idempotency: a duplicate
# event_id is reported back, not an error for the whole batch (EDGE-FR-015/016).
# ---------------------------------------------------------------------------


class ObservationEnvelopeIn(BaseModel):
    model_config = ConfigDict(extra="forbid")

    event_id: uuid.UUID
    gateway_sequence: int
    connector_id: str | None = None
    device_id: str | None = None
    mapping_id: str | None = None
    mapping_version: str | None = None
    source: dict | None = None
    source_timestamp: datetime | None = None
    gateway_received_at: datetime | None = None
    clock_quality: dict | None = None
    quality: str
    raw: dict | None = None
    normalized: dict | None = None
    correlation_id: str | None = None
    batch_context: dict | None = None


class AcceptObservationBatchCommand(CommandEnvelope):
    expected_version: int
    observations: list[ObservationEnvelopeIn]


class ObservationBatchResult(MutationReceipt):
    accepted_event_ids: list[uuid.UUID]
    duplicate_event_ids: list[uuid.UUID]
    rejected: list[dict]


async def accept_observation_batch(
    session: AsyncSession, gateway_id: uuid.UUID, cmd: AcceptObservationBatchCommand, service_identity: AuthenticatedServiceIdentity
) -> ObservationBatchResult:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return ObservationBatchResult(
            command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
            audit_event_id=existing.id, correlation_id=existing.id,
            accepted_event_ids=[], duplicate_event_ids=[], rejected=[],
        )

    gateway = await _load_gateway_for_update(session, gateway_id, cmd.expected_version)
    if gateway.lifecycle_state in BLOCKED_FOR_INGESTION_STATES:
        raise InvalidTransitionError("Gateway is not eligible to submit observations", current_state=gateway.lifecycle_state)
    if service_identity.subject_ref != gateway.id:
        raise NotFoundError("Edge gateway not found")

    accepted_ids: list[uuid.UUID] = []
    duplicate_ids: list[uuid.UUID] = []
    rejected: list[dict] = []
    max_sequence = gateway.last_observation_sequence or 0

    for envelope in cmd.observations:
        if envelope.quality not in OBSERVATION_QUALITIES:
            rejected.append({"event_id": str(envelope.event_id), "code": "ENVELOPE_INVALID"})
            continue
        existing_row = await session.get(EdgeObservation, envelope.event_id)
        if existing_row is not None:
            duplicate_ids.append(envelope.event_id)
            continue
        session.add(
            EdgeObservation(
                event_id=envelope.event_id, gateway_id=gateway.id, gateway_sequence=envelope.gateway_sequence,
                connector_id=envelope.connector_id, device_id=envelope.device_id, mapping_id=envelope.mapping_id,
                mapping_version=envelope.mapping_version, source=envelope.source, source_timestamp=envelope.source_timestamp,
                gateway_received_at=envelope.gateway_received_at, clock_quality=envelope.clock_quality,
                quality=envelope.quality, raw=envelope.raw, normalized=envelope.normalized,
                correlation_id=envelope.correlation_id, batch_context=envelope.batch_context,
            )
        )
        accepted_ids.append(envelope.event_id)
        max_sequence = max(max_sequence, envelope.gateway_sequence)

    gateway.last_observation_sequence = max_sequence
    gateway.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=gateway.site_id, aggregate_type="edge_gateway", aggregate_id=gateway.id,
        aggregate_version=gateway.version, action="IntegrationAccepted", actor_id=service_identity.identity_id,
        actor_type="service", correlation_id=correlation_id,
        new_value={"accepted": len(accepted_ids), "duplicate": len(duplicate_ids), "rejected": len(rejected)},
    )
    await write_outbox_event(
        session, event_type="EdgeObservationsAccepted", aggregate_type="edge_gateway", aggregate_id=gateway.id,
        aggregate_version=gateway.version, payload={"gateway_id": str(gateway.id), "event_ids": [str(e) for e in accepted_ids]},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=gateway.site_id, command_type="AcceptObservationBatch", aggregate_type="edge_gateway",
        aggregate_id=gateway.id, expected_version=cmd.expected_version, resulting_version=gateway.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=service_identity.identity_id,
        payload_hash=payload_hash,
    )
    return ObservationBatchResult(
        command_id=receipt.id, aggregate_id=gateway.id, resulting_version=gateway.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
        accepted_event_ids=accepted_ids, duplicate_event_ids=duplicate_ids, rejected=rejected,
    )


# ---------------------------------------------------------------------------
# ReportHealth — EDGE-FR-017/026. Service-identity path, signature_required=False per SG-119.
# ---------------------------------------------------------------------------


class ReportHealthCommand(CommandEnvelope):
    expected_version: int
    operational_state: str | None = None
    metrics: dict | None = None
    clock_quality: dict | None = None
    cert_expiry_days: int | None = None


async def report_health(
    session: AsyncSession, gateway_id: uuid.UUID, cmd: ReportHealthCommand, service_identity: AuthenticatedServiceIdentity
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return MutationReceipt(
            command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
            audit_event_id=existing.id, correlation_id=existing.id,
        )

    gateway = await _load_gateway_for_update(session, gateway_id, cmd.expected_version)
    if service_identity.subject_ref != gateway.id:
        raise NotFoundError("Edge gateway not found")

    now = datetime.now(timezone.utc)
    session.add(
        EdgeHealthSnapshot(
            gateway_id=gateway.id, reported_at=now, operational_state=cmd.operational_state, metrics=cmd.metrics,
            clock_quality=cmd.clock_quality, cert_expiry_days=cmd.cert_expiry_days,
        )
    )
    gateway.last_reported_operational_state = cmd.operational_state
    gateway.last_health_at = now
    gateway.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=gateway.site_id, aggregate_type="edge_gateway", aggregate_id=gateway.id,
        aggregate_version=gateway.version, action="Changed", actor_id=service_identity.identity_id,
        actor_type="service", correlation_id=correlation_id, new_value={"operational_state": cmd.operational_state},
    )
    await write_outbox_event(
        session, event_type="GatewayHealthReported", aggregate_type="edge_gateway", aggregate_id=gateway.id,
        aggregate_version=gateway.version, payload={"gateway_id": str(gateway.id), "operational_state": cmd.operational_state},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=gateway.site_id, command_type="ReportHealth", aggregate_type="edge_gateway",
        aggregate_id=gateway.id, expected_version=cmd.expected_version, resulting_version=gateway.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=service_identity.identity_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=gateway.id, resulting_version=gateway.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ReportSecurityEvent — EDGE-FR-027. Service-identity path, signature_required=False per SG-119. A
# CRITICAL event authoritatively moves the gateway to SECURITY_HOLD in the same transaction.
# ---------------------------------------------------------------------------


class ReportSecurityEventCommand(CommandEnvelope):
    expected_version: int
    event_type: str
    severity: str
    evidence: dict | None = None


async def report_security_event(
    session: AsyncSession, gateway_id: uuid.UUID, cmd: ReportSecurityEventCommand, service_identity: AuthenticatedServiceIdentity
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return MutationReceipt(
            command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
            audit_event_id=existing.id, correlation_id=existing.id,
        )

    if cmd.severity not in SECURITY_EVENT_SEVERITIES:
        raise ValidationFailedError("Unrecognized severity", severity=cmd.severity, allowed=list(SECURITY_EVENT_SEVERITIES))

    gateway = await _load_gateway_for_update(session, gateway_id, cmd.expected_version)
    if service_identity.subject_ref != gateway.id:
        raise NotFoundError("Edge gateway not found")
    old_state = gateway.lifecycle_state

    session.add(
        EdgeSecurityEvent(
            gateway_id=gateway.id, event_type=cmd.event_type, severity=cmd.severity, evidence=cmd.evidence,
        )
    )
    if cmd.severity == "CRITICAL":
        gateway.lifecycle_state = "SECURITY_HOLD"
    gateway.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=gateway.site_id, aggregate_type="edge_gateway", aggregate_id=gateway.id,
        aggregate_version=gateway.version, action="StatusChanged" if cmd.severity == "CRITICAL" else "Changed",
        actor_id=service_identity.identity_id, actor_type="service", correlation_id=correlation_id,
        old_value={"lifecycle_state": old_state}, new_value={"lifecycle_state": gateway.lifecycle_state, "event_type": cmd.event_type},
    )
    await write_outbox_event(
        session, event_type="GatewaySecurityEventReported", aggregate_type="edge_gateway", aggregate_id=gateway.id,
        aggregate_version=gateway.version, payload={"gateway_id": str(gateway.id), "severity": cmd.severity},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=gateway.site_id, command_type="ReportSecurityEvent", aggregate_type="edge_gateway",
        aggregate_id=gateway.id, expected_version=cmd.expected_version, resulting_version=gateway.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=service_identity.identity_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=gateway.id, resulting_version=gateway.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# RotateGatewayCertificate — Document 106 row 119: QA Releaser, independent, reason required. The one
# operation this module resolves against a real Document 106 row rather than an interim SPEC_GAP baseline.
# ---------------------------------------------------------------------------


class RotateGatewayCertificateCommand(CommandEnvelope):
    expected_version: int
    new_fingerprint: str
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def rotate_gateway_certificate(
    session: AsyncSession, gateway_id: uuid.UUID, cmd: RotateGatewayCertificateCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return MutationReceipt(
            command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
            audit_event_id=existing.id, correlation_id=existing.id,
        )

    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required to rotate a gateway certificate")

    gateway = await _load_gateway_for_update(session, gateway_id, cmd.expected_version)
    if gateway.lifecycle_state == "DECOMMISSIONED":
        raise InvalidTransitionError("Gateway is decommissioned", current_state=gateway.lifecycle_state)

    policy = await signature_service.resolve_signature_requirement(session, record_type="edge_gateway", action="certificate_rotation")
    if policy.signature_required and actor_user_id == gateway.enrolled_by_user_id:
        raise InvalidTransitionError(
            "Signer must be independent of the actor who enrolled this gateway (Document 106 row 119 SoD)"
        )
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id, record_version=gateway.version,
            record_hash=gateway_record_hash(gateway),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    old_fingerprint = gateway.certificate_fingerprint
    if old_fingerprint == cmd.new_fingerprint:
        raise CertRotationFailedError("New fingerprint must differ from the current one")
    gateway.certificate_fingerprint = cmd.new_fingerprint
    gateway.version += 1

    session.add(
        EdgeCertificateRotation(
            gateway_id=gateway.id, old_fingerprint=old_fingerprint, new_fingerprint=cmd.new_fingerprint,
            requested_by_user_id=actor_user_id, signature_id=signature_id,
        )
    )

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=gateway.site_id, aggregate_type="edge_gateway", aggregate_id=gateway.id,
        aggregate_version=gateway.version, action="Changed", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=cmd.reason, old_value={"certificate_fingerprint": old_fingerprint},
        new_value={"certificate_fingerprint": gateway.certificate_fingerprint}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="GatewayCertificateRotated", aggregate_type="edge_gateway", aggregate_id=gateway.id,
        aggregate_version=gateway.version, payload={"gateway_id": str(gateway.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=gateway.site_id, command_type="RotateGatewayCertificate", aggregate_type="edge_gateway",
        aggregate_id=gateway.id, expected_version=cmd.expected_version, resulting_version=gateway.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=gateway.id, resulting_version=gateway.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )
