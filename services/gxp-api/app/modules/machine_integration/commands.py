"""Document 47 (SPEC-EDGE-005) server-side slice. See `models.py`'s module docstring for the scope split
and the two SPEC_GAP-recorded boundary decisions (SG-129/SG-130): machine-driven ingestion never signs
(Doc 106 P7) and never calls `batch.complete_step()`/`equipment.hold_equipment()` (MAP-FR-016 -- no
"approved orchestration rule" mechanism exists in this codebase). `release_signal_mapping`,
`submit_approved_machine_command` and `replay_historical_evidence` are the three human-authorized,
signed actions (SG-127/SG-128/SG-131); `ingest_machine_evidence`, `build_cycle_evidence_manifest` and
`finalize_machine_command` are service-identity-authenticated (SG-129), same shape as
`app.modules.edge.commands.accept_observation_batch`. `open_batch_context`/`close_batch_context` are
human-authenticated but unsigned (bookkeeping correlation, not a regulated state change).
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import AuthenticatedServiceIdentity, verify_password
from app.modules.edge.models import EdgeObservation
from app.modules.iam.models import User
from app.modules.machine_integration.models import (
    BatchContext,
    CycleEvidenceManifest,
    MachineAlarmEvent,
    MachineCommandProfile,
    MachineCommandRequest,
    MachineEvidenceCandidate,
    MachineReplayJob,
    MachineSource,
    SignalMapping,
)
from app.modules.rules import service as rules_service
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    BatchContextAmbiguousError,
    CommandNotAllowedError,
    InvalidTransitionError,
    MappingValidationIncompleteError,
    MissingSignatureError,
    NotFoundError,
    StaleVersionError,
    UomConversionUnavailableError,
    UomUnknownError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

# MAP-FR-014: which evidence classes create a MachineEvidenceCandidate vs. an alarm vs. neither. Unrelated
# high-frequency telemetry (HISTORIAN_ONLY, EQUIPMENT_STATE) is deliberately never given its own GxP row
# here (§13 acceptance: "unrelated high-frequency telemetry remains outside Frappe/GxP transactional
# tables") -- routed but not persisted as a new candidate row.
CANDIDATE_EVIDENCE_CLASSES = ("STEP_RESULT", "PROCESS_EVIDENCE", "EM_RESULT")

# MAP-FR-004: `SignalMapping.native_type` is a free-text driver type name (no fixed enum anywhere in this
# codebase or Document 47's own data model -- e.g. the OPC UA "Double" already used by existing fixtures).
# Rather than invent an exhaustive taxonomy the spec never enumerates, this classifies by substring against
# the handful of type families §4/§7's driver catalogue actually implies (numeric, boolean); anything that
# doesn't match either family is treated as opaque/untyped and passed through unvalidated -- deliberately
# conservative: this never rejects a legitimate mapping over an unrecognized type name, it only catches the
# unambiguous case Document 44 DRV-FR-009/Document 47 MAP-FR-004 both name explicitly: "no implicit casts."
_NUMERIC_TYPE_MARKERS = ("double", "float", "real", "int", "dint", "word", "dword", "short", "long", "byte")
_BOOLEAN_TYPE_MARKERS = ("bool",)


def _classify_native_type(native_type: str) -> str:
    lowered = native_type.lower()
    if any(marker in lowered for marker in _BOOLEAN_TYPE_MARKERS):
        return "boolean"
    if any(marker in lowered for marker in _NUMERIC_TYPE_MARKERS):
        return "numeric"
    return "opaque"


class MappedValueResult:
    """MAP-FR-004/005/006 outcome for one observation's `value` against its released `SignalMapping`.
    `rejection_code` set means the event must be rejected (never partially applied); `canonical` is set
    only when a unit conversion actually ran (MAP-FR-005/006), leaving the caller free to retain the raw
    value untouched otherwise (raw-value/provenance retention, same principle as Document 110's rule
    evaluator keeping the caller's original `inputs` alongside its converted copy)."""

    def __init__(self, rejection_code: str | None = None, canonical_value: str | None = None, canonical_unit: str | None = None):
        self.rejection_code = rejection_code
        self.canonical_value = canonical_value
        self.canonical_unit = canonical_unit


async def _validate_and_convert_value(session: AsyncSession, mapping: SignalMapping, raw_value: object, as_of: datetime) -> MappedValueResult:
    """MAP-FR-004 (type validation, no implicit casts) then MAP-FR-005/006 (engineering-unit conversion
    through the Document 110 released UOM/conversion tables -- the same `resolve_uom`/`resolve_conversion`
    + `Decimal(str(value)) * conversion.factor` pattern `app.modules.rules.commands._apply_unit_policy`
    already applies for rule inputs; not a new conversion mechanism). A missing `value` (key absent or
    JSON null) is left unvalidated and unconverted -- Document 47/44 do not define an accept/reject policy
    for "no reading", and this pass does not invent one; the caller's existing behaviour (pass the null
    through) is unchanged.
    """
    if raw_value is None:
        return MappedValueResult()

    family = _classify_native_type(mapping.native_type)
    if family == "boolean":
        if not isinstance(raw_value, bool):
            return MappedValueResult(rejection_code="TYPE_VALIDATION_FAILED")
        return MappedValueResult()
    if family == "numeric":
        if isinstance(raw_value, bool):  # bool is a numeric subtype in Python/JSON -- explicitly excluded
            return MappedValueResult(rejection_code="TYPE_VALIDATION_FAILED")
        try:
            parsed = Decimal(str(raw_value))
        except (InvalidOperation, ValueError, TypeError):
            return MappedValueResult(rejection_code="TYPE_VALIDATION_FAILED")

        if not mapping.raw_unit or not mapping.canonical_unit or mapping.raw_unit == mapping.canonical_unit:
            return MappedValueResult()
        try:
            await rules_service.resolve_uom(session, mapping.raw_unit)
            await rules_service.resolve_uom(session, mapping.canonical_unit)
            conversion = await rules_service.resolve_conversion(session, mapping.raw_unit, mapping.canonical_unit, as_of)
        except (UomUnknownError, UomConversionUnavailableError):
            return MappedValueResult(rejection_code="UOM_CONVERSION_UNAVAILABLE")
        return MappedValueResult(canonical_value=str(parsed * conversion.factor), canonical_unit=mapping.canonical_unit)

    return MappedValueResult()


def mapping_record_hash(mapping: SignalMapping) -> str:
    return sha256_hex({"id": str(mapping.id), "row_version": mapping.row_version, "lifecycle_state": mapping.lifecycle_state})


async def _load_mapping_for_update(session: AsyncSession, mapping_id: uuid.UUID, expected_version: int) -> SignalMapping:
    result = await session.execute(select(SignalMapping).where(SignalMapping.id == mapping_id).with_for_update())
    mapping = result.scalar_one_or_none()
    if mapping is None:
        raise NotFoundError("Signal mapping not found")
    if mapping.row_version != expected_version:
        raise StaleVersionError(
            "Signal mapping was modified since it was read", expected_version=expected_version, current_version=mapping.row_version
        )
    return mapping


async def _load_source_for_update(session: AsyncSession, source_id: uuid.UUID, expected_version: int) -> MachineSource:
    result = await session.execute(select(MachineSource).where(MachineSource.id == source_id).with_for_update())
    source = result.scalar_one_or_none()
    if source is None:
        raise NotFoundError("Machine source not found")
    if source.version != expected_version:
        raise StaleVersionError(
            "Machine source was modified since it was read", expected_version=expected_version, current_version=source.version
        )
    return source


async def _load_context_for_update(session: AsyncSession, context_id: uuid.UUID, expected_version: int) -> BatchContext:
    result = await session.execute(select(BatchContext).where(BatchContext.id == context_id).with_for_update())
    context = result.scalar_one_or_none()
    if context is None:
        raise NotFoundError("Batch context not found")
    if context.version != expected_version:
        raise StaleVersionError(
            "Batch context was modified since it was read", expected_version=expected_version, current_version=context.version
        )
    return context


async def _load_command_request_for_update(session: AsyncSession, request_id: uuid.UUID, expected_version: int) -> MachineCommandRequest:
    result = await session.execute(select(MachineCommandRequest).where(MachineCommandRequest.id == request_id).with_for_update())
    request = result.scalar_one_or_none()
    if request is None:
        raise NotFoundError("Machine command request not found")
    if request.version != expected_version:
        raise StaleVersionError(
            "Machine command request was modified since it was read", expected_version=expected_version, current_version=request.version
        )
    return request


async def resolve_batch_context(session: AsyncSession, source_id: uuid.UUID) -> BatchContext | None:
    """MAP-FR-012/013/§6 step 3/5. Returns the sole OPEN context for this source, `None` if there is
    none (mapping's `batch_context_policy` decides whether that is acceptable), or raises
    `BatchContextAmbiguousError` if more than one is open -- never guessed from timestamp proximity."""
    result = await session.execute(select(BatchContext).where(BatchContext.source_id == source_id, BatchContext.status == "OPEN"))
    contexts = result.scalars().all()
    if len(contexts) > 1:
        raise BatchContextAmbiguousError("More than one batch context is open for this source", source_id=str(source_id))
    return contexts[0] if contexts else None


# ---------------------------------------------------------------------------
# ReleaseSignalMapping — MAP-FR-002..008/017/027/028. Signature per SG-127 (interim baseline: QA
# Releaser, independent of the drafting actor, reason required) -- no Document 106 row exists.
# ---------------------------------------------------------------------------


class ReleaseSignalMappingCommand(CommandEnvelope):
    mapping_id: uuid.UUID
    expected_version: int
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def release_signal_mapping(
    session: AsyncSession, cmd: ReleaseSignalMappingCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return MutationReceipt(
            command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
            audit_event_id=existing.id, correlation_id=existing.id,
        )

    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required to release a signal mapping")

    mapping = await _load_mapping_for_update(session, cmd.mapping_id, cmd.expected_version)
    if mapping.lifecycle_state not in ("draft", "tested"):
        raise InvalidTransitionError("Mapping is not eligible for release", current_state=mapping.lifecycle_state)
    if mapping.source_address is None or mapping.domain_code is None or mapping.evidence_class is None:
        raise MappingValidationIncompleteError("Mapping is missing required fields for release")

    policy = await signature_service.resolve_signature_requirement(session, record_type="signal_mapping", action="release")
    if policy.signature_required and actor_user_id == mapping.drafted_by_user_id:
        raise InvalidTransitionError(
            "Signer must be independent of the actor who drafted this mapping (SG-127 SoD)"
        )
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id, record_version=mapping.row_version,
            record_hash=mapping_record_hash(mapping),
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    old_state = mapping.lifecycle_state
    mapping.lifecycle_state = "released"
    mapping.effective_from = datetime.now(timezone.utc)
    mapping.released_by_user_id = actor_user_id
    mapping.signature_id = signature_id
    mapping.row_version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=mapping.site_id, aggregate_type="signal_mapping", aggregate_id=mapping.id,
        aggregate_version=mapping.row_version, action="Released", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=cmd.reason, old_value={"lifecycle_state": old_state}, new_value={"lifecycle_state": mapping.lifecycle_state},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="SignalMappingReleased", aggregate_type="signal_mapping", aggregate_id=mapping.id,
        aggregate_version=mapping.row_version, payload={"id": str(mapping.id), "mapping_key": mapping.mapping_key, "version": mapping.version},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=mapping.site_id, command_type="ReleaseSignalMapping", aggregate_type="signal_mapping",
        aggregate_id=mapping.id, expected_version=cmd.expected_version, resulting_version=mapping.row_version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=mapping.id, resulting_version=mapping.row_version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# OpenBatchContext / CloseBatchContext — MAP-FR-012/013/§6. Human-authenticated, unsigned (bookkeeping
# correlation, not a regulated state change -- no Document 106 row needed, same class as read-only/
# administrative actions elsewhere with no signature policy row).
# ---------------------------------------------------------------------------


class OpenBatchContextCommand(CommandEnvelope):
    source_id: uuid.UUID
    batch_id: uuid.UUID
    batch_step_id: uuid.UUID | None = None


async def open_batch_context(
    session: AsyncSession, cmd: OpenBatchContextCommand, actor_user_id: uuid.UUID
) -> dict:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return {"context_id": str(existing.aggregate_id), "status": "OPEN"}

    source = await session.get(MachineSource, cmd.source_id)
    if source is None:
        raise NotFoundError("Machine source not found")

    context = BatchContext(
        site_id=source.site_id, source_id=source.id, batch_id=cmd.batch_id, batch_step_id=cmd.batch_step_id,
        status="OPEN", opened_by_user_id=actor_user_id,
    )
    session.add(context)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=source.site_id, aggregate_type="batch_context", aggregate_id=context.id,
        aggregate_version=context.version, action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        new_value={"batch_id": str(cmd.batch_id), "source_id": str(cmd.source_id)},
    )
    await write_outbox_event(
        session, event_type="BatchContextOpened", aggregate_type="batch_context", aggregate_id=context.id,
        aggregate_version=context.version, payload={"id": str(context.id)}, correlation_id=correlation_id,
    )
    await record_command_receipt(
        session, site_id=source.site_id, command_type="OpenBatchContext", aggregate_type="batch_context",
        aggregate_id=context.id, expected_version=None, resulting_version=context.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return {"context_id": str(context.id), "status": "OPEN", "audit_event_id": str(audit_event.id)}


class CloseBatchContextCommand(CommandEnvelope):
    context_id: uuid.UUID
    expected_version: int


async def close_batch_context(
    session: AsyncSession, cmd: CloseBatchContextCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return MutationReceipt(
            command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
            audit_event_id=existing.id, correlation_id=existing.id,
        )

    context = await _load_context_for_update(session, cmd.context_id, cmd.expected_version)
    if context.status != "OPEN":
        raise InvalidTransitionError("Batch context is not open", current_status=context.status)

    context.status = "CLOSED"
    context.closed_at = datetime.now(timezone.utc)
    context.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=context.site_id, aggregate_type="batch_context", aggregate_id=context.id,
        aggregate_version=context.version, action="StatusChanged", actor_id=actor_user_id, correlation_id=correlation_id,
        old_value={"status": "OPEN"}, new_value={"status": "CLOSED"},
    )
    await write_outbox_event(
        session, event_type="BatchContextClosed", aggregate_type="batch_context", aggregate_id=context.id,
        aggregate_version=context.version, payload={"id": str(context.id)}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=context.site_id, command_type="CloseBatchContext", aggregate_type="batch_context",
        aggregate_id=context.id, expected_version=cmd.expected_version, resulting_version=context.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=context.id, resulting_version=context.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# IngestMachineEvidence — MAP-FR-009..014/030 (`evaluateEvidenceRouting()` + `createStepResultCandidate()`
# + `createMachineAlarmEvent()` combined into one batch-ingest pipeline, service-identity-authenticated,
# signature_required=False per SG-129/Doc 106 P7). Consumes already-accepted `edge.edge_observations`
# rows by event_id -- never writes the `edge` schema.
# ---------------------------------------------------------------------------


class IngestMachineEvidenceCommand(CommandEnvelope):
    expected_version: int
    event_ids: list[uuid.UUID]


async def ingest_machine_evidence(
    session: AsyncSession, source_id: uuid.UUID, cmd: IngestMachineEvidenceCommand, service_identity: AuthenticatedServiceIdentity
) -> dict:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return {
            "command_id": str(existing.id), "resulting_version": existing.resulting_version,
            "candidates_created": [], "alarms_created": [], "rejected": [],
        }

    source = await _load_source_for_update(session, source_id, cmd.expected_version)
    if service_identity.subject_ref != source.gateway_id:
        raise NotFoundError("Machine source not found")

    candidates: list[uuid.UUID] = []
    alarms: list[uuid.UUID] = []
    rejected: list[dict] = []

    for event_id in cmd.event_ids:
        observation = await session.get(EdgeObservation, event_id)
        if observation is None or observation.mapping_id is None:
            rejected.append({"event_id": str(event_id), "code": "SOURCE_MAPPING_NOT_FOUND"})
            continue
        mapping = (
            await session.execute(
                select(SignalMapping).where(
                    SignalMapping.mapping_key == observation.mapping_id, SignalMapping.source_id == source.id,
                    SignalMapping.lifecycle_state == "released",
                ).order_by(SignalMapping.version.desc()).limit(1)
            )
        ).scalar_one_or_none()
        if mapping is None:
            any_mapping = (
                await session.execute(select(SignalMapping.id).where(SignalMapping.mapping_key == observation.mapping_id))
            ).scalar_one_or_none()
            code = "SOURCE_NOT_ALLOWED" if any_mapping is not None else "MAPPING_NOT_EFFECTIVE"
            rejected.append({"event_id": str(event_id), "code": code})
            continue

        already = (
            await session.execute(select(MachineEvidenceCandidate.id).where(MachineEvidenceCandidate.event_id == event_id))
        ).scalar_one_or_none() or (
            await session.execute(select(MachineAlarmEvent.id).where(MachineAlarmEvent.event_id == event_id))
        ).scalar_one_or_none()
        if already is not None:
            continue  # already routed by a prior call -- idempotent no-op, not a rejection

        batch_context = None
        if mapping.batch_context_policy in ("REQUIRED", "DETERMINISTIC"):
            try:
                batch_context = await resolve_batch_context(session, source.id)
            except BatchContextAmbiguousError:
                rejected.append({"event_id": str(event_id), "code": "BATCH_CONTEXT_AMBIGUOUS"})
                continue
            if batch_context is None and mapping.batch_context_policy == "REQUIRED":
                # §6 step 5: ambiguity (none *or* more than one open context) fails closed for a
                # REQUIRED policy -- resolveBatchContext()'s only declared error code covers both.
                rejected.append({"event_id": str(event_id), "code": "BATCH_CONTEXT_AMBIGUOUS"})
                continue
            if batch_context is not None:
                # MAP-FR-027: "open batches keep issued mapping version" -- pin the mapping version this
                # context first routes evidence with, and never silently pick up a newer release for the
                # remaining life of this same OPEN context.
                if batch_context.mapping_id is None:
                    batch_context.mapping_id = mapping.id
                elif batch_context.mapping_id != mapping.id:
                    pinned_mapping = await session.get(SignalMapping, batch_context.mapping_id)
                    if pinned_mapping is not None:
                        mapping = pinned_mapping

        if observation.quality in ("BAD", "COMM_ERROR"):
            rejected.append({"event_id": str(event_id), "code": "FRESHNESS_FAILED"})
            continue

        if mapping.evidence_class == "ALARM":
            alarm = MachineAlarmEvent(
                site_id=source.site_id, event_id=event_id, mapping_id=mapping.id,
                alarm_code=str((observation.normalized or observation.raw or {}).get("alarm_code", mapping.domain_code)),
                severity=str((observation.normalized or observation.raw or {}).get("severity", "WARNING")),
                batch_context_id=batch_context.id if batch_context else None,
            )
            session.add(alarm)
            await session.flush()
            alarms.append(alarm.id)
        elif mapping.evidence_class in CANDIDATE_EVIDENCE_CLASSES:
            payload = observation.normalized or observation.raw or {}
            mapped = await _validate_and_convert_value(session, mapping, payload.get("value"), datetime.now(timezone.utc))
            if mapped.rejection_code is not None:
                rejected.append({"event_id": str(event_id), "code": mapped.rejection_code})
                continue
            value = dict(payload)
            if mapped.canonical_value is not None:
                # MAP-FR-005/006: `value` retains the raw reading/unit as received (raw-value/provenance
                # retention, same principle as Document 110's rule evaluator) and additionally carries the
                # canonical reading -- never overwrites or discards the raw figure.
                value["canonical_value"] = mapped.canonical_value
                value["canonical_unit"] = mapped.canonical_unit
            candidate = MachineEvidenceCandidate(
                site_id=source.site_id, event_id=event_id, mapping_id=mapping.id, evidence_class=mapping.evidence_class,
                batch_context_id=batch_context.id if batch_context else None, domain_code=mapping.domain_code,
                value=value, quality=observation.quality,
                freshness="LATE" if observation.quality == "STALE" else "CURRENT",
            )
            session.add(candidate)
            await session.flush()
            candidates.append(candidate.id)
        # HISTORIAN_ONLY/EQUIPMENT_STATE/CYCLE_DATA: routed (mapping resolved, no rejection) but no new
        # GxP row here -- CYCLE_DATA is handled by build_cycle_evidence_manifest() separately; the other
        # two deliberately stay outside Frappe/GxP transactional tables (§13 acceptance).

    source.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=source.site_id, aggregate_type="machine_source", aggregate_id=source.id,
        aggregate_version=source.version, action="IntegrationAccepted", actor_id=service_identity.identity_id,
        actor_type="service", correlation_id=correlation_id,
        new_value={"candidates": len(candidates), "alarms": len(alarms), "rejected": len(rejected)},
    )
    for cand_id in candidates:
        await write_outbox_event(
            session, event_type="StepResultCandidateCreated", aggregate_type="machine_evidence_candidate",
            aggregate_id=cand_id, aggregate_version=1, payload={"id": str(cand_id)}, correlation_id=correlation_id,
        )
    for alarm_id in alarms:
        await write_outbox_event(
            session, event_type="MachineAlarmDetected", aggregate_type="machine_alarm_event",
            aggregate_id=alarm_id, aggregate_version=1, payload={"id": str(alarm_id)}, correlation_id=correlation_id,
        )
    receipt = await record_command_receipt(
        session, site_id=source.site_id, command_type="IngestMachineEvidence", aggregate_type="machine_source",
        aggregate_id=source.id, expected_version=cmd.expected_version, resulting_version=source.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=service_identity.identity_id,
        payload_hash=payload_hash,
    )
    return {
        "command_id": str(receipt.id), "resulting_version": source.version, "audit_event_id": str(audit_event.id),
        "candidates_created": [str(c) for c in candidates], "alarms_created": [str(a) for a in alarms], "rejected": rejected,
    }


# ---------------------------------------------------------------------------
# BuildCycleEvidenceManifest — MAP-FR-025/026. Service-identity, signature_required=False per SG-129.
# Immutable once written (no update path exposed anywhere in the app layer).
# ---------------------------------------------------------------------------


class BuildCycleEvidenceManifestCommand(CommandEnvelope):
    expected_version: int
    cycle_id: str
    event_ids: list[uuid.UUID]
    cycle_start: datetime | None = None
    cycle_end: datetime | None = None
    statistics: dict | None = None
    raw_evidence_ref: str | None = None
    historian_instance_ref: str | None = None
    aggregation_rule_ref: str | None = None
    mapping_id: uuid.UUID | None = None


async def build_cycle_evidence_manifest(
    session: AsyncSession, source_id: uuid.UUID, cmd: BuildCycleEvidenceManifestCommand, service_identity: AuthenticatedServiceIdentity
) -> dict:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return {"command_id": str(existing.id), "manifest_id": str(existing.aggregate_id)}

    source = await _load_source_for_update(session, source_id, cmd.expected_version)
    if service_identity.subject_ref != source.gateway_id:
        raise NotFoundError("Machine source not found")

    batch_context = await resolve_batch_context(session, source.id)
    manifest_hash = sha256_hex({
        "cycle_id": cmd.cycle_id, "event_ids": sorted(str(e) for e in cmd.event_ids), "statistics": cmd.statistics,
    })
    manifest = CycleEvidenceManifest(
        site_id=source.site_id, source_id=source.id, cycle_id=cmd.cycle_id,
        batch_context_id=batch_context.id if batch_context else None, mapping_id=cmd.mapping_id,
        cycle_start=cmd.cycle_start, cycle_end=cmd.cycle_end, event_ids=[str(e) for e in cmd.event_ids],
        statistics=cmd.statistics, raw_evidence_ref=cmd.raw_evidence_ref,
        historian_instance_ref=cmd.historian_instance_ref, aggregation_rule_ref=cmd.aggregation_rule_ref,
        manifest_hash=manifest_hash,
    )
    session.add(manifest)
    await session.flush()
    source.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=source.site_id, aggregate_type="cycle_evidence_manifest", aggregate_id=manifest.id,
        aggregate_version=1, action="Created", actor_id=service_identity.identity_id, actor_type="service",
        correlation_id=correlation_id, new_value={"cycle_id": cmd.cycle_id, "manifest_hash": manifest_hash},
    )
    await write_outbox_event(
        session, event_type="CycleEvidenceCreated", aggregate_type="cycle_evidence_manifest", aggregate_id=manifest.id,
        aggregate_version=1, payload={"id": str(manifest.id), "cycle_id": cmd.cycle_id}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=source.site_id, command_type="BuildCycleEvidenceManifest", aggregate_type="machine_source",
        aggregate_id=source.id, expected_version=cmd.expected_version, resulting_version=source.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=service_identity.identity_id,
        payload_hash=payload_hash,
    )
    return {
        "command_id": str(receipt.id), "manifest_id": str(manifest.id), "manifest_hash": manifest_hash,
        "audit_event_id": str(audit_event.id),
    }


# ---------------------------------------------------------------------------
# GetMachineEvidenceExport — MAP-FR-031. Read-only composition (no new regulated write, same "read
# query added to serve a real need beyond the declared op list" precedent as
# `equipment.commands.get_equipment_history`/`aseptic_commands.get_review_summary`). Nothing in Document
# 47's own function catalogue (§3) names an export function, so this never becomes a signed/regulated
# action of its own -- it only composes already-committed rows for inspection.
# ---------------------------------------------------------------------------


async def get_machine_evidence_export(session: AsyncSession, manifest_id: uuid.UUID) -> dict:
    manifest = await session.get(CycleEvidenceManifest, manifest_id)
    if manifest is None:
        raise NotFoundError("Cycle evidence manifest not found")

    covered_ids = [uuid.UUID(e) for e in manifest.event_ids]
    candidates = (
        await session.execute(select(MachineEvidenceCandidate).where(MachineEvidenceCandidate.event_id.in_(covered_ids)))
    ).scalars().all() if covered_ids else []
    alarms = (
        await session.execute(select(MachineAlarmEvent).where(MachineAlarmEvent.event_id.in_(covered_ids)))
    ).scalars().all() if covered_ids else []

    return {
        "manifest_id": str(manifest.id),
        "cycle_id": manifest.cycle_id,
        "cycle_start": manifest.cycle_start.isoformat() if manifest.cycle_start else None,
        "cycle_end": manifest.cycle_end.isoformat() if manifest.cycle_end else None,
        "manifest_hash": manifest.manifest_hash,
        "raw_evidence_ref": manifest.raw_evidence_ref,
        "historian_instance_ref": manifest.historian_instance_ref,
        "aggregation_rule_ref": manifest.aggregation_rule_ref,
        "statistics": manifest.statistics,
        "event_ids": manifest.event_ids,
        "candidates": [
            {"id": str(c.id), "event_id": str(c.event_id), "domain_code": c.domain_code, "evidence_class": c.evidence_class, "value": c.value}
            for c in candidates
        ],
        "alarms": [
            {"id": str(a.id), "event_id": str(a.event_id), "alarm_code": a.alarm_code, "severity": a.severity}
            for a in alarms
        ],
    }


# ---------------------------------------------------------------------------
# SubmitApprovedMachineCommand — MAP-FR-018/019/020/021. Signature per SG-128 (interim baseline:
# Equipment Administrator, independent=False, reason required) -- no Document 106 row exists. No
# released MachineCommandProfile for the requested operation = COMMAND_NOT_ALLOWED, a real "disabled by
# default" (MAP-FR-019).
# ---------------------------------------------------------------------------


class SubmitApprovedMachineCommandCommand(CommandEnvelope):
    source_id: uuid.UUID
    operation_code: str
    parameters: dict | None = None
    batch_id: uuid.UUID | None = None
    batch_state: str | None = None
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def submit_approved_machine_command(
    session: AsyncSession, cmd: SubmitApprovedMachineCommandCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return MutationReceipt(
            command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
            audit_event_id=existing.id, correlation_id=existing.id,
        )

    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required to submit a machine command")

    source = await session.get(MachineSource, cmd.source_id)
    if source is None:
        raise NotFoundError("Machine source not found")

    profile = (
        await session.execute(
            select(MachineCommandProfile).where(
                MachineCommandProfile.operation_code == cmd.operation_code, MachineCommandProfile.lifecycle_state == "released"
            ).order_by(MachineCommandProfile.version.desc()).limit(1)
        )
    ).scalar_one_or_none()
    if profile is None:
        raise CommandNotAllowedError("No released command profile authorizes this operation", operation_code=cmd.operation_code)
    if profile.allowed_batch_states and cmd.batch_state not in profile.allowed_batch_states:
        raise CommandNotAllowedError("Batch is not in a state this command profile allows", batch_state=cmd.batch_state)

    policy = await signature_service.resolve_signature_requirement(session, record_type="machine_command_profile", action="submit")
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        pre_hash = sha256_hex({"source_id": str(cmd.source_id), "operation_code": cmd.operation_code, "parameters": cmd.parameters})
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id, record_version=0, record_hash=pre_hash,
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    request = MachineCommandRequest(
        site_id=source.site_id, command_profile_id=profile.id, source_id=source.id, batch_id=cmd.batch_id,
        parameters=cmd.parameters, requested_by_user_id=actor_user_id, signature_id=signature_id, status="PENDING",
        expires_at=datetime.now(timezone.utc) + timedelta(milliseconds=profile.timeout_ms),
    )
    session.add(request)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=source.site_id, aggregate_type="machine_command_request", aggregate_id=request.id,
        aggregate_version=request.version, action="Created", actor_id=actor_user_id, correlation_id=correlation_id,
        reason=cmd.reason, new_value={"operation_code": cmd.operation_code, "status": "PENDING"}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="MachineCommandRequested", aggregate_type="machine_command_request", aggregate_id=request.id,
        aggregate_version=request.version, payload={"id": str(request.id), "operation_code": cmd.operation_code},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=source.site_id, command_type="SubmitApprovedMachineCommand", aggregate_type="machine_command_request",
        aggregate_id=request.id, expected_version=None, resulting_version=request.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=request.id, resulting_version=request.version,
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# FinalizeMachineCommand — MAP-FR-021/022. Service-identity, signature_required=False per SG-129 (P7 --
# the caller is the gateway reporting an EdgeCommandReceipt, no human in the loop). Records the outcome
# only; never itself writes Batch/Equipment state (module docstring boundary decision).
# ---------------------------------------------------------------------------


class FinalizeMachineCommandCommand(CommandEnvelope):
    expected_version: int
    outcome_status: str
    native_response: dict | None = None
    evidence_ref: str | None = None


_TERMINAL_OUTCOMES = ("COMPLETED", "READBACK_MISMATCH", "TIMEOUT", "FAILED", "DENIED")


async def finalize_machine_command(
    session: AsyncSession, request_id: uuid.UUID, cmd: FinalizeMachineCommandCommand, service_identity: AuthenticatedServiceIdentity
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return MutationReceipt(
            command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
            audit_event_id=existing.id, correlation_id=existing.id,
        )

    request = await _load_command_request_for_update(session, request_id, cmd.expected_version)
    if request.status not in ("PENDING", "SENT"):
        raise InvalidTransitionError("Command request is already finalized", current_status=request.status)
    if cmd.outcome_status not in _TERMINAL_OUTCOMES:
        raise ValidationFailedError("Unrecognized outcome_status", outcome_status=cmd.outcome_status, allowed=list(_TERMINAL_OUTCOMES))

    source = await session.get(MachineSource, request.source_id)
    if source is None or service_identity.subject_ref != source.gateway_id:
        raise NotFoundError("Machine command request not found")

    old_status = request.status
    request.status = cmd.outcome_status
    request.native_response = cmd.native_response
    request.evidence_ref = cmd.evidence_ref
    request.finalized_at = datetime.now(timezone.utc)
    request.version += 1

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=request.site_id, aggregate_type="machine_command_request", aggregate_id=request.id,
        aggregate_version=request.version, action="StatusChanged", actor_id=service_identity.identity_id,
        actor_type="service", correlation_id=correlation_id, old_value={"status": old_status},
        new_value={"status": request.status},
    )
    event_type = "MachineCommandCompleted" if cmd.outcome_status == "COMPLETED" else "MachineCommandFailed"
    await write_outbox_event(
        session, event_type=event_type, aggregate_type="machine_command_request", aggregate_id=request.id,
        aggregate_version=request.version, payload={"id": str(request.id), "outcome_status": cmd.outcome_status},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=request.site_id, command_type="FinalizeMachineCommand", aggregate_type="machine_command_request",
        aggregate_id=request.id, expected_version=cmd.expected_version, resulting_version=request.version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=service_identity.identity_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=request.id, resulting_version=request.version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# ReplayHistoricalEvidence — MAP-FR-029. Signature per SG-131 (interim baseline: Integration
# Administrator, independent=False -- no dedicated second role exists, same "no role pair" precedent as
# `destruction_record.execute`; reason required per MUT-FR-026).
# ---------------------------------------------------------------------------


class ReplayHistoricalEvidenceCommand(CommandEnvelope):
    event_ids: list[uuid.UUID]
    mode: str
    reason: str
    challenge_id: uuid.UUID
    reauth_password: str


async def replay_historical_evidence(
    session: AsyncSession, site_id: uuid.UUID, cmd: ReplayHistoricalEvidenceCommand, actor_user_id: uuid.UUID
) -> dict:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return {"command_id": str(existing.id), "job_id": str(existing.aggregate_id)}

    if not cmd.reason.strip():
        raise ValidationFailedError("reason is required to replay historical evidence")
    if cmd.mode not in ("BACKFILL", "REPLAY"):
        raise ValidationFailedError("mode must be BACKFILL or REPLAY", mode=cmd.mode)

    policy = await signature_service.resolve_signature_requirement(session, record_type="machine_replay_job", action="replay")
    signature_id = None
    if policy.signature_required:
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        pre_hash = sha256_hex({"event_ids": sorted(str(e) for e in cmd.event_ids), "mode": cmd.mode})
        challenge = await signature_service.consume_challenge(
            session, challenge_id=cmd.challenge_id, user_id=actor_user_id, record_version=0, record_hash=pre_hash,
        )
        signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
        signature_id = signature.id

    job = MachineReplayJob(
        site_id=site_id, requested_by_user_id=actor_user_id, signature_id=signature_id, reason=cmd.reason,
        mode=cmd.mode, event_ids=[str(e) for e in cmd.event_ids], status="REQUESTED",
    )
    session.add(job)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=site_id, aggregate_type="machine_replay_job", aggregate_id=job.id, aggregate_version=1,
        action="Created", actor_id=actor_user_id, correlation_id=correlation_id, reason=cmd.reason,
        new_value={"mode": cmd.mode, "event_count": len(cmd.event_ids)}, signature_id=signature_id,
    )
    await write_outbox_event(
        session, event_type="HistoricalReplayStarted", aggregate_type="machine_replay_job", aggregate_id=job.id,
        aggregate_version=1, payload={"id": str(job.id), "mode": cmd.mode}, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=site_id, command_type="ReplayHistoricalEvidence", aggregate_type="machine_replay_job",
        aggregate_id=job.id, expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return {
        "command_id": str(receipt.id), "job_id": str(job.id), "audit_event_id": str(audit_event.id),
        "signature_id": str(signature_id) if signature_id else None,
    }
