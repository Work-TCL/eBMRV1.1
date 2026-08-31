"""WP-07 (Documents 48-53) Mutation Gateway command handlers. Every write here is unsigned
(SG-122: Document 106 has zero rows for any SPEC-ERP-00x action) but still RBAC/SoD-gated through
`evaluate_policy` at the router layer, same as every other unsigned command in this codebase.

`dispatch_erp_command` is genuinely new shape for this codebase: it is the first command that performs
real external I/O, and `.claude/rules/01-gxp-mutation-rules.md` forbids external I/O *inside* the
Mutation Gateway transaction. It therefore runs as two separate committed transactions around the HTTP
call (ERP-ARC-023 "async default", ERP-ARC-024 "no distributed 2PC") instead of the one-transaction
shape every other command handler in this codebase uses -- see its docstring below.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.db import SessionLocal
from app.modules.erp import reliability
from app.modules.erp.adapters.dynamics365 import Dynamics365Adapter
from app.modules.erp.adapters.erpnext import ERPNextAdapter
from app.modules.erp.adapters.generic import GenericErpAdapter
from app.modules.erp.adapters.oracle_fusion import OracleFusionAdapter
from app.modules.erp.adapters.sap import SapS4HanaAdapter
from app.modules.erp.models import (
    BULK_JOB_TYPES,
    DIFFERENCE_TYPES,
    ERP_VENDORS,
    MAPPING_ENTITY_TYPES,
    ErpExternalMapping,
    ErpInstance,
    ErpMappingConflict,
    ErpMigrationPackage,
    ErpSyncCheckpoint,
    IntegrationBulkJob,
    IntegrationCommand,
    IntegrationCommandAttempt,
    IntegrationInboundEvent,
    IntegrationReconciliationDifference,
    IntegrationReconciliationRun,
    IntegrationSecurityEvent,
)
from app.modules.erp.provider import AdapterConfig, CanonicalOutboundCommand, ERPProvider
from app.modules.iam.models import User
from app.modules.signature import service as signature_service
from app.core.security import verify_password
from app.mutation.errors import (
    ErpCapabilityUnsupportedError,
    ErpExternalConflictError,
    ErpInstanceInvalidError,
    ErpMappingConflictError,
    ErpMappingNotFoundError,
    ErpThrottledError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    StaleVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

# ENXT-FR-020: known evidence-blob-shaped payload keys queue_erp_command() rejects unless the instance
# explicitly opts in. Not exhaustive (payload is opaque JSONB by design), but names the obvious/known
# ways a caller might embed a file inline -- a real, checkable guard rather than an unenforceable policy
# statement.
_EMBEDDED_EVIDENCE_PAYLOAD_KEYS = frozenset({"file_content", "attachment_blob", "evidence_blob", "base64_content"})

ADAPTER_REGISTRY: dict[str, type[ERPProvider]] = {
    "ERPNEXT": ERPNextAdapter,
    "SAP_S4HANA": SapS4HanaAdapter,
    "ORACLE_FUSION": OracleFusionAdapter,
    "DYNAMICS_365": Dynamics365Adapter,
    "GENERIC": GenericErpAdapter,
}


def build_adapter(instance: ErpInstance) -> ERPProvider:
    """ERP-ARC-001/003. Resolves the vendor-neutral contract from `ErpInstance.vendor` -- no vendor type
    leaks past this one function into command.py's own logic."""

    adapter_cls = ADAPTER_REGISTRY[instance.vendor]
    config = AdapterConfig(
        base_url=instance.base_url,
        auth_method=instance.auth_method,
        # ERP-ARC-028: auth_secret_ref is an opaque secret-manager reference, never the raw secret at
        # rest. Phase 1 has no secret-manager integration (out of scope this pass, see SG-126) -- the
        # referenced value is used directly as the credential, which is why it is never logged/audited.
        auth_secret=instance.auth_secret_ref,
        contract_version=instance.contract_version,
        extra=(
            {"endpoint_map": (instance.capabilities or {}).get("endpoint_map", {})} if instance.vendor == "GENERIC"
            # SAP-FR-010: movement type codes are per-customer configuration, not hardcoded across
            # customers -- an instance's capabilities JSONB may override any of this vendor's defaults.
            else {"movement_type_overrides": (instance.capabilities or {}).get("movement_type_overrides", {})} if instance.vendor == "SAP_S4HANA"
            else {}
        ),
    )
    return adapter_cls(config)


async def _record_security_event_durably(
    *, erp_instance_id: uuid.UUID, event_type: str, severity: str, detail: dict, correlation_id: uuid.UUID | None = None,
) -> None:
    """INT-FR-025. A payload-hash conflict, idempotency-key reuse or source-identity mismatch is
    detected right where the caller is about to raise a hard failure back to the client -- but the
    caller's own transaction is about to roll back (that is what the raise does), so writing this row
    in the same transaction would discard it along with everything else. A brand-new session/transaction,
    committed independently before the caller raises, is the only way this security signal survives the
    failure it is recording (same reasoning AUD-FR-027 gives for keeping a security trail distinct from
    the regulated audit ledger it would otherwise be rolled back with)."""

    async with SessionLocal() as security_session:
        async with security_session.begin():
            security_session.add(IntegrationSecurityEvent(
                erp_instance_id=erp_instance_id, event_type=event_type, severity=severity,
                detail=detail, correlation_id=correlation_id,
            ))


def _is_source_version_stale(previous: str | None, incoming: str | None) -> bool | None:
    """INT-FR-011. True = incoming is not newer than previous (stale, must not overwrite); False =
    incoming is newer; None = the comparison cannot be safely made, so nothing is rejected (Document 47/
    52/53 do not define `source_version`'s representation, and guessing an ordering rule here is exactly
    the invented-precision behaviour AG-15 exists to prevent). Tries the two unambiguous, well-understood
    representations a vendor "modified"/"version" field is realistically ever encoded as -- a plain
    number, or an ISO-8601 timestamp -- and nothing else."""

    if previous is None or incoming is None:
        return None
    for parse in (lambda v: Decimal(v), lambda v: datetime.fromisoformat(v.replace("Z", "+00:00"))):
        try:
            prev_val, new_val = parse(previous), parse(incoming)
        except (InvalidOperation, ValueError, TypeError, AttributeError):
            continue
        return new_val <= prev_val
    return None


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
        audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _write_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, site_id: uuid.UUID | None,
    aggregate_type: str, aggregate_id: uuid.UUID, version: int, action: str, actor_user_id: uuid.UUID,
    reason: str | None, old_state: str | None, event_type: str, event_payload: dict,
    expected_version: int | None, command_type: str,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=site_id, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state} if old_state else None, new_value=event_payload,
    )
    await write_outbox_event(
        session, event_type=event_type, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, payload=event_payload, correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=site_id, command_type=command_type, aggregate_type=aggregate_type,
        aggregate_id=aggregate_id, expected_version=expected_version, resulting_version=version,
        idempotency_key=cmd.idempotency_key, command_hash=payload_hash, actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id, aggregate_id=aggregate_id, resulting_version=version,
        audit_event_id=audit_event.id, correlation_id=correlation_id,
    )


async def _resolve_signature(
    session: AsyncSession, *, record_type: str, action: str, actor_user_id: uuid.UUID,
    record_version: int, record_hash: str, challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
    """Resolved from Document 106 policy data, never a code conditional (AG-07/rule 02) -- even though
    every WP-07 policy row seeded this pass resolves to `signature_required=False` (SG-122: Document 106
    has zero real rows for any SPEC-ERP-00x action), the resolution still goes through the same fail-
    closed `resolve_signature_requirement()` path every other regulated action uses, so a future policy
    change (a human resolving SG-122) takes effect with no code change here."""

    policy = await signature_service.resolve_signature_requirement(session, record_type=record_type, action=action)
    if not policy.signature_required:
        return None
    if challenge_id is None or not reauth_password:
        raise MissingSignatureError(f"{record_type} '{action}' requires a signature", required_meaning=policy.meaning)
    actor = await session.get(User, actor_user_id)
    if actor is None or not verify_password(reauth_password, actor.password_hash):
        raise MissingSignatureError("Fresh step-up authentication failed")
    challenge = await signature_service.consume_challenge(
        session, challenge_id=challenge_id, user_id=actor_user_id, record_version=record_version, record_hash=record_hash,
    )
    signature = await signature_service.sign(session, challenge=challenge, auth_context={"method": "password_reauth"})
    return signature.id


# ---------------------------------------------------------------------------------------------------
# ErpInstance — ERP-ARC-002. Resolves signature_required=False from policy (SG-122).
# ---------------------------------------------------------------------------------------------------


class RegisterERPInstanceCommand(CommandEnvelope):
    instance_name: str
    vendor: str
    environment: str = "SANDBOX"
    base_url: str
    auth_method: str
    auth_secret_ref: str | None = None
    contract_version: str | None = None
    site_id: uuid.UUID | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def register_erp_instance(
    session: AsyncSession, cmd: RegisterERPInstanceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    await _resolve_signature(
        session, record_type="erp_instance", action="register", actor_user_id=actor_user_id,
        record_version=0, record_hash=sha256_hex({"instance_name": cmd.instance_name, "vendor": cmd.vendor}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    if cmd.vendor not in ERP_VENDORS:
        raise ErpInstanceInvalidError("Unrecognized vendor", allowed=list(ERP_VENDORS))
    if cmd.vendor != "GENERIC" and not ADAPTER_REGISTRY.get(cmd.vendor):
        raise ErpInstanceInvalidError("No adapter registered for this vendor", vendor=cmd.vendor)
    # ERP-ARC-028: TLS is mandatory for every instance -- no plaintext outbound-restriction exception
    # exists in the baseline for any environment, including SANDBOX/TEST.
    if not cmd.base_url.lower().startswith("https://"):
        raise ErpInstanceInvalidError("base_url must use https:// -- plaintext ERP connections are not permitted", base_url=cmd.base_url)

    duplicate = (
        await session.execute(select(ErpInstance.id).where(ErpInstance.instance_name == cmd.instance_name))
    ).first()
    if duplicate is not None:
        raise ErpInstanceInvalidError("instance_name already registered", instance_name=cmd.instance_name)

    adapter_cls = ADAPTER_REGISTRY[cmd.vendor]
    instance = ErpInstance(
        site_id=cmd.site_id, instance_name=cmd.instance_name, vendor=cmd.vendor, environment=cmd.environment,
        base_url=cmd.base_url, auth_method=cmd.auth_method, auth_secret_ref=cmd.auth_secret_ref,
        capabilities={"supported_operations": list(adapter_cls.supported_operations)} if cmd.vendor != "GENERIC" else {"endpoint_map": {}},
        contract_version=cmd.contract_version, status="ACTIVE", version=1,
    )
    session.add(instance)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="erp_instance",
        aggregate_id=instance.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="ERPInstanceRegistered",
        event_payload={"id": str(instance.id), "vendor": instance.vendor, "instance_name": instance.instance_name},
        expected_version=None, command_type="RegisterERPInstance",
    )


_READ_OPERATION_MARKERS = ("SYNC_", "FETCH_", "GET_")


class ValidateERPInstanceCommand(CommandEnvelope):
    instance_id: uuid.UUID
    expected_version: int
    acceptance_reference: str


async def validate_erp_instance(session: AsyncSession, cmd: ValidateERPInstanceCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    """validateERPInstance() -- MULTI-FR-024. Certifies a GENERIC (custom) instance's connector against
    an acceptance profile before it may post any write. Unsigned (SG-122 precedent -- Document 106 has
    zero rows for any WP-07 action); RBAC/reason-gated only. Named-vendor instances (ERPNext/SAP/Oracle/
    Dynamics) never need this -- their adapter code, built and reviewed in this codebase, is their own
    certification; the gate exists specifically because a GENERIC instance's entire behaviour comes from
    customer-supplied configuration this codebase has never seen."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if not cmd.acceptance_reference:
        raise ValidationFailedError("acceptance_reference is required to validate a connector")

    result = await session.execute(select(ErpInstance).where(ErpInstance.id == cmd.instance_id).with_for_update())
    instance = result.scalar_one_or_none()
    if instance is None:
        raise NotFoundError("ERP instance not found")
    if instance.version != cmd.expected_version:
        raise StaleVersionError("Instance was modified since it was read", expected_version=cmd.expected_version, current_version=instance.version)
    if instance.vendor != "GENERIC":
        raise ErpInstanceInvalidError("Only a GENERIC (custom) instance requires validation", vendor=instance.vendor)

    # MULTI-FR-022: a write-capable custom adapter must also declare a read/reconciliation path --
    # otherwise nothing can ever verify what it posted actually landed, so production write capability
    # is not approved for it.
    endpoint_map = (instance.capabilities or {}).get("endpoint_map", {})
    declares_write = any(op.startswith("POST_") for op in endpoint_map)
    declares_read = any(op.startswith(_READ_OPERATION_MARKERS) for op in endpoint_map)
    if declares_write and not declares_read:
        raise ErpInstanceInvalidError(
            "A write-capable custom adapter must also declare a read/reconciliation operation before it can be validated",
            declared_operations=sorted(endpoint_map.keys()),
        )

    old_state = "unvalidated" if not instance.validated else "validated"
    instance.validated = True
    instance.validated_by_user_id = actor_user_id
    instance.validated_at = datetime.now(timezone.utc)
    instance.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id, aggregate_type="erp_instance",
        aggregate_id=instance.id, version=instance.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.acceptance_reference, old_state=old_state, event_type="ERPInstanceValidated",
        event_payload={"id": str(instance.id), "acceptance_reference": cmd.acceptance_reference},
        expected_version=cmd.expected_version, command_type="ValidateERPInstance",
    )


async def get_capabilities(session: AsyncSession, instance_id: uuid.UUID) -> dict:
    """getCapabilities() -- ERP-ARC-003/030, a read query, not a mutation."""

    instance = await session.get(ErpInstance, instance_id)
    if instance is None:
        raise NotFoundError("ERP instance not found")
    adapter = build_adapter(instance)
    reachable = await adapter.probe()
    caps = adapter.capabilities()
    return {
        "instance_id": str(instance_id), "vendor": caps.vendor, "contract_version": caps.contract_version,
        "supported_operations": list(caps.supported_operations), "reachable": reachable,
    }


# ---------------------------------------------------------------------------------------------------
# ErpExternalMapping — ERP-ARC-005..020, MDS-FR-001..017/021. Unsigned (SG-122).
# ---------------------------------------------------------------------------------------------------


class ProposeMappingCommand(CommandEnvelope):
    erp_instance_id: uuid.UUID
    entity_type: str
    internal_id: uuid.UUID | None = None
    internal_code: str | None = None
    external_id: str
    external_code: str | None = None
    field_ownership: str = "ERP"
    match_method: str = "MANUAL"
    confidence: str | None = None  # decimal-as-string, MDS-FR precision discipline (AG-15)
    uom_conversion_factor: str | None = None
    evidence: dict | None = None


async def propose_mapping(
    session: AsyncSession, cmd: ProposeMappingCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.entity_type not in MAPPING_ENTITY_TYPES:
        raise ValidationFailedError("Unrecognized entity_type", allowed=list(MAPPING_ENTITY_TYPES))
    if cmd.internal_id is None and not cmd.internal_code:
        raise ValidationFailedError("Either internal_id or internal_code is required")

    instance = await session.get(ErpInstance, cmd.erp_instance_id)
    if instance is None:
        raise NotFoundError("ERP instance not found")

    # MDS-FR-009: detect and block a duplicate ACTIVE mapping for the same external identity.
    duplicate = (
        await session.execute(
            select(ErpExternalMapping).where(
                ErpExternalMapping.erp_instance_id == cmd.erp_instance_id,
                ErpExternalMapping.entity_type == cmd.entity_type,
                ErpExternalMapping.external_id == cmd.external_id,
                ErpExternalMapping.mapping_status.in_(("PROPOSED", "ACTIVE")),
            )
        )
    ).scalar_one_or_none()
    if duplicate is not None:
        raise ErpMappingConflictError(
            "An active or proposed mapping already exists for this external identity",
            existing_mapping_id=str(duplicate.id),
        )

    mapping = ErpExternalMapping(
        erp_instance_id=cmd.erp_instance_id, entity_type=cmd.entity_type, internal_id=cmd.internal_id,
        internal_code=cmd.internal_code, external_id=cmd.external_id, external_code=cmd.external_code,
        field_ownership=cmd.field_ownership, mapping_status="PROPOSED", match_method=cmd.match_method,
        confidence=cmd.confidence, uom_conversion_factor=cmd.uom_conversion_factor, evidence=cmd.evidence,
        version=1,
    )
    session.add(mapping)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id, aggregate_type="erp_external_mapping",
        aggregate_id=mapping.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="MasterMappingProposed",
        event_payload={"id": str(mapping.id), "entity_type": mapping.entity_type, "external_id": mapping.external_id},
        expected_version=None, command_type="ProposeMapping",
    )


def _mapping_hash(mapping: ErpExternalMapping) -> str:
    return sha256_hex({
        "id": str(mapping.id), "entity_type": mapping.entity_type, "internal_id": str(mapping.internal_id) if mapping.internal_id else None,
        "internal_code": mapping.internal_code, "external_id": mapping.external_id, "external_code": mapping.external_code,
        "field_ownership": mapping.field_ownership,
    })


async def _load_mapping_for_update(session: AsyncSession, mapping_id: uuid.UUID, expected_version: int) -> ErpExternalMapping:
    result = await session.execute(select(ErpExternalMapping).where(ErpExternalMapping.id == mapping_id).with_for_update())
    mapping = result.scalar_one_or_none()
    if mapping is None:
        raise ErpMappingNotFoundError("Mapping not found")
    if mapping.version != expected_version:
        raise StaleVersionError("Mapping was modified since it was read", expected_version=expected_version, current_version=mapping.version)
    return mapping


class ApproveMappingCommand(CommandEnvelope):
    mapping_id: uuid.UUID
    expected_version: int
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def approve_mapping(
    session: AsyncSession, cmd: ApproveMappingCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """MDS-FR-019/020/021. Resolves signature_required=False from policy (SG-122) but RBAC-gated at the
    router; every quality-critical mapping (`requires_qa_review`-style routing is left to the caller's
    own workflow, MDS-FR-020 "cannot be blanket-approved without review profile" -- there is exactly one
    approve action here, no bulk path)."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    mapping = await _load_mapping_for_update(session, cmd.mapping_id, cmd.expected_version)
    if mapping.mapping_status not in ("PROPOSED", "SUSPENDED"):
        raise InvalidTransitionError("Only a proposed or suspended mapping can be approved", current_state=mapping.mapping_status)

    await _resolve_signature(
        session, record_type="erp_external_mapping", action="approve", actor_user_id=actor_user_id,
        record_version=mapping.version, record_hash=_mapping_hash(mapping),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = mapping.mapping_status
    mapping.mapping_status = "ACTIVE"
    mapping.approved_by_user_id = actor_user_id
    mapping.approved_at = datetime.now(timezone.utc)
    mapping.mapping_hash = _mapping_hash(mapping)
    mapping.version += 1

    instance = await session.get(ErpInstance, mapping.erp_instance_id)
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id if instance else None,
        aggregate_type="erp_external_mapping", aggregate_id=mapping.id, version=mapping.version, action="Approved",
        actor_user_id=actor_user_id, reason=None, old_state=old_state, event_type="MasterMappingActivated",
        event_payload={"id": str(mapping.id), "mapping_hash": mapping.mapping_hash}, expected_version=cmd.expected_version,
        command_type="ApproveMapping",
    )


class SuspendMappingCommand(CommandEnvelope):
    mapping_id: uuid.UUID
    expected_version: int
    reason: str


async def suspend_mapping(
    session: AsyncSession, cmd: SuspendMappingCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """suspendMapping() -- MDS-FR-017/024. The transition an ACTIVE mapping takes when its external
    record is reported deactivated/deleted by the vendor (SG-126 gap: "external deletion/deactivation
    maps to inactive/suspended projection; never physically deletes GxP-linked master history"). Never
    deletes the mapping row or any GxP history behind it. Reactivation reuses the existing
    `approve_mapping()` (it already accepts a mapping in `SUSPENDED` state) -- one entry/exit pair for
    this state, not a parallel reactivation command."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to suspend a mapping")

    mapping = await _load_mapping_for_update(session, cmd.mapping_id, cmd.expected_version)
    if mapping.mapping_status != "ACTIVE":
        raise InvalidTransitionError("Only an active mapping can be suspended", current_state=mapping.mapping_status)

    old_state = mapping.mapping_status
    mapping.mapping_status = "SUSPENDED"
    mapping.version += 1

    instance = await session.get(ErpInstance, mapping.erp_instance_id)
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id if instance else None,
        aggregate_type="erp_external_mapping", aggregate_id=mapping.id, version=mapping.version, action="Changed",
        actor_user_id=actor_user_id, reason=cmd.reason, old_state=old_state, event_type="MasterMappingSuspended",
        event_payload={"id": str(mapping.id), "reason": cmd.reason}, expected_version=cmd.expected_version,
        command_type="SuspendMapping",
    )


class ApplyExternalChangeCommand(CommandEnvelope):
    """applyERPProjectionUpdate()/raiseMasterConflict() combined -- MDS-FR-006/007. Sync-processor
    trigger, not typically human-initiated."""

    mapping_id: uuid.UUID
    expected_version: int
    field_name: str
    proposed_value: dict


async def apply_external_change(
    session: AsyncSession, cmd: ApplyExternalChangeCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    mapping = await _load_mapping_for_update(session, cmd.mapping_id, cmd.expected_version)
    old_state = mapping.mapping_status

    if mapping.field_ownership == "GXP":
        # MDS-FR-006: a GxP-owned field changing externally is a conflict, never an overwrite.
        conflict = ErpMappingConflict(
            mapping_id=mapping.id, field_name=cmd.field_name, source_value={"external_code": mapping.external_code},
            proposed_value=cmd.proposed_value, current_value={"external_code": mapping.external_code},
            status="OPEN", requires_qa_review=mapping.entity_type in ("MATERIAL", "PRODUCT"), version=1,
        )
        session.add(conflict)
        mapping.mapping_status = "CONFLICT"
        mapping.version += 1
        event_type, event_payload = "MasterDataConflictDetected", {"mapping_id": str(mapping.id), "conflict_id": str(conflict.id)}
    else:
        mapping.external_code = cmd.proposed_value.get("external_code", mapping.external_code)
        mapping.evidence = {**(mapping.evidence or {}), cmd.field_name: cmd.proposed_value}
        mapping.version += 1
        event_type, event_payload = "ERPProjectionUpdated", {"mapping_id": str(mapping.id), "field_name": cmd.field_name}

    instance = await session.get(ErpInstance, mapping.erp_instance_id)
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id if instance else None,
        aggregate_type="erp_external_mapping", aggregate_id=mapping.id, version=mapping.version, action="Changed",
        actor_user_id=actor_user_id, reason=None, old_state=old_state, event_type=event_type,
        event_payload=event_payload, expected_version=cmd.expected_version, command_type="ApplyExternalChange",
    )


class ResolveMasterConflictCommand(CommandEnvelope):
    conflict_id: uuid.UUID
    expected_version: int
    resolution: str  # ACCEPT_PROPOSED | KEEP_CURRENT | REJECT
    resolution_reason: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def resolve_master_conflict(
    session: AsyncSession, cmd: ResolveMasterConflictCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """MDS-FR-018. Resolves signature_required=False from policy (SG-122). `resolution_reason` is
    mandatory -- a conflict resolution is exactly the kind of controlled correction AUD-FR-008 requires a
    reason for, even without a signature."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if not cmd.resolution_reason:
        raise ValidationFailedError("resolution_reason is required")
    if cmd.resolution not in ("ACCEPT_PROPOSED", "KEEP_CURRENT", "REJECT"):
        raise ValidationFailedError("Unrecognized resolution", allowed=["ACCEPT_PROPOSED", "KEEP_CURRENT", "REJECT"])

    result = await session.execute(select(ErpMappingConflict).where(ErpMappingConflict.id == cmd.conflict_id).with_for_update())
    conflict = result.scalar_one_or_none()
    if conflict is None:
        raise NotFoundError("Mapping conflict not found")
    if conflict.version != cmd.expected_version:
        raise StaleVersionError("Conflict was modified since it was read", expected_version=cmd.expected_version, current_version=conflict.version)
    if conflict.status != "OPEN":
        raise InvalidTransitionError("Only an open conflict can be resolved", current_state=conflict.status)

    await _resolve_signature(
        session, record_type="erp_mapping_conflict", action="resolve", actor_user_id=actor_user_id,
        record_version=conflict.version, record_hash=sha256_hex({"id": str(conflict.id), "status": conflict.status}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    mapping = await session.get(ErpExternalMapping, conflict.mapping_id)
    conflict.status = "RESOLVED" if cmd.resolution != "REJECT" else "REJECTED"
    conflict.resolution = cmd.resolution
    conflict.resolution_reason = cmd.resolution_reason
    conflict.resolved_by_user_id = actor_user_id
    conflict.resolved_at = datetime.now(timezone.utc)
    conflict.version += 1

    if cmd.resolution == "ACCEPT_PROPOSED" and mapping is not None:
        mapping.external_code = (conflict.proposed_value or {}).get("external_code", mapping.external_code)
    if mapping is not None:
        mapping.mapping_status = "ACTIVE"
        mapping.version += 1

    instance = await session.get(ErpInstance, mapping.erp_instance_id) if mapping else None
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id if instance else None,
        aggregate_type="erp_mapping_conflict", aggregate_id=conflict.id, version=conflict.version, action="Approved",
        actor_user_id=actor_user_id, reason=cmd.resolution_reason, old_state="OPEN", event_type="MasterConflictResolved",
        event_payload={"id": str(conflict.id), "resolution": cmd.resolution}, expected_version=cmd.expected_version,
        command_type="ResolveMasterConflict",
    )


class AdvanceSyncCheckpointCommand(CommandEnvelope):
    erp_instance_id: uuid.UUID
    entity_type: str
    cursor_value: str
    last_batch_id: uuid.UUID | None = None


async def advance_sync_checkpoint(
    session: AsyncSession, cmd: AdvanceSyncCheckpointCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """MDS-FR-022/023. Idempotent upsert -- re-processing the same `last_batch_id` (e.g. after a crash
    mid-sync, MDS-FR sync-cursor crash/restart test) is a no-op via the normal idempotency-key check."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    instance = await session.get(ErpInstance, cmd.erp_instance_id)
    if instance is None:
        raise NotFoundError("ERP instance not found")

    result = await session.execute(
        select(ErpSyncCheckpoint).where(
            ErpSyncCheckpoint.erp_instance_id == cmd.erp_instance_id, ErpSyncCheckpoint.entity_type == cmd.entity_type,
        ).with_for_update()
    )
    checkpoint = result.scalar_one_or_none()
    old_state = checkpoint.cursor_value if checkpoint else None
    if checkpoint is None:
        checkpoint = ErpSyncCheckpoint(erp_instance_id=cmd.erp_instance_id, entity_type=cmd.entity_type, version=1)
        session.add(checkpoint)
        await session.flush()
    else:
        checkpoint.version += 1
    checkpoint.cursor_value = cmd.cursor_value
    checkpoint.last_batch_id = cmd.last_batch_id
    checkpoint.last_synced_at = datetime.now(timezone.utc)

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id, aggregate_type="erp_sync_checkpoint",
        aggregate_id=checkpoint.id, version=checkpoint.version, action="Changed", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type="SyncCheckpointAdvanced",
        event_payload={"id": str(checkpoint.id), "cursor_value": checkpoint.cursor_value}, expected_version=None,
        command_type="AdvanceSyncCheckpoint",
    )


async def get_master_data_quality_metrics(session: AsyncSession, erp_instance_id: uuid.UUID) -> dict:
    """getMasterDataQualityMetrics() -- MDS-FR-026. Read/reporting only, same "not a regulated decision"
    footing as `get_integration_sla_metrics` (rule 11 governs decisions read from a projection, not
    observability counts). "Stale" reads `ErpExternalMapping.effective_to` -- an ACTIVE mapping whose own
    declared effective window has already lapsed but was never retired, the one stale signal this schema
    can name without inventing a staleness threshold Document 52 never defines."""

    now = datetime.now(timezone.utc)
    mapping_counts_stmt = (
        select(ErpExternalMapping.mapping_status, func.count())
        .where(ErpExternalMapping.erp_instance_id == erp_instance_id)
        .group_by(ErpExternalMapping.mapping_status)
    )
    mapping_counts = dict((await session.execute(mapping_counts_stmt)).all())

    stale_count = (
        await session.execute(
            select(func.count()).select_from(ErpExternalMapping).where(
                ErpExternalMapping.erp_instance_id == erp_instance_id, ErpExternalMapping.mapping_status == "ACTIVE",
                ErpExternalMapping.effective_to.is_not(None), ErpExternalMapping.effective_to < now,
            )
        )
    ).scalar_one()

    inbound_counts_stmt = (
        select(IntegrationInboundEvent.processing_state, func.count())
        .where(IntegrationInboundEvent.erp_instance_id == erp_instance_id)
        .group_by(IntegrationInboundEvent.processing_state)
    )
    inbound_counts = dict((await session.execute(inbound_counts_stmt)).all())

    return {
        "unmapped_count": mapping_counts.get("UNMAPPED", 0),
        "conflict_count": mapping_counts.get("CONFLICT", 0),
        "stale_count": stale_count,
        "failed_sync_count": inbound_counts.get("SCHEMA_INVALID", 0) + inbound_counts.get("CONFLICT", 0),
        "duplicate_count": inbound_counts.get("DUPLICATE", 0),
        "active_mapping_count": mapping_counts.get("ACTIVE", 0),
    }


# ---------------------------------------------------------------------------------------------------
# IntegrationCommand — ERP-ARC-021/023/024/026/027, INT-FR-001/003..016. Unsigned (SG-122). Document 53's
# shared reliability model used by every adapter (module docstring in models.py).
# ---------------------------------------------------------------------------------------------------


class QueueERPCommandCommand(CommandEnvelope):
    erp_instance_id: uuid.UUID
    command_type: str
    source_event_id: uuid.UUID | None = None
    source_aggregate_type: str | None = None
    source_aggregate_id: uuid.UUID | None = None
    payload: dict


async def queue_erp_command(
    session: AsyncSession, cmd: QueueERPCommandCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """queueERPCommand() -- ERP-ARC-021, INT-FR-001/006. `cmd.idempotency_key` doubles as the ledger's
    own `(erp_instance_id, idempotency_key)` uniqueness (INT-FR-006 "stable idempotency key derived from
    immutable source event/operation semantics") -- callers derive it from the source GxP event, not a
    random value."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    instance = await session.get(ErpInstance, cmd.erp_instance_id)
    if instance is None:
        raise NotFoundError("ERP instance not found")
    if instance.status != "ACTIVE":
        raise ErpInstanceInvalidError("ERP instance is not active", status=instance.status)

    # MDS-FR-007: this IS "approved GxP-owned projection sent outward only if provider profile supports
    # it" -- queueERPCommand() is the only path a GxP-owned outward-directed command reaches an adapter
    # through, and this check already gates every outward call on the instance's own declared
    # capabilities. No separate GXP-vs-ERP field-ownership check is needed on the outward side: the
    # inward side (`apply_external_change`) is where field_ownership actually matters, since only there
    # can an external system attempt to overwrite a GxP-owned value.
    supported = set((instance.capabilities or {}).get("supported_operations", []))
    if instance.vendor != "GENERIC" and cmd.command_type not in supported:
        raise ErpCapabilityUnsupportedError("Adapter does not declare support for this operation", command_type=cmd.command_type)
    # MULTI-FR-024: a GENERIC (custom) connector cannot post any write until it has been through
    # validate_erp_instance()'s acceptance profile -- read/sync operations are unaffected.
    if instance.vendor == "GENERIC" and cmd.command_type.startswith("POST_") and not instance.validated:
        raise ErpInstanceInvalidError("This custom connector has not been validated for write operations", instance_id=str(instance.id))
    # ENXT-FR-020/CTR-FR-019: regulated evidence is transmitted by controlled reference/hash, never
    # embedded inline, unless the instance explicitly opts in (a genuine customer requirement Document
    # 49 names as the only exception -- never assumed).
    embedded_evidence_keys = _EMBEDDED_EVIDENCE_PAYLOAD_KEYS.intersection(cmd.payload)
    if embedded_evidence_keys and not (instance.capabilities or {}).get("allow_embedded_evidence", False):
        raise ValidationFailedError(
            "Regulated evidence must be transmitted by reference, not embedded inline, unless this instance explicitly allows it",
            fields=sorted(embedded_evidence_keys),
        )

    # INT-FR-007: same (instance, idempotency_key) with a different payload hash is a conflict, not a
    # silent duplicate accept.
    conflicting = (
        await session.execute(
            select(IntegrationCommand).where(
                IntegrationCommand.erp_instance_id == cmd.erp_instance_id, IntegrationCommand.idempotency_key == cmd.idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if conflicting is not None:
        if conflicting.payload_hash != payload_hash:
            await _record_security_event_durably(
                erp_instance_id=cmd.erp_instance_id, event_type="IDEMPOTENCY_KEY_REUSED", severity="WARNING",
                detail={"idempotency_key": cmd.idempotency_key, "conflicting_command_id": str(conflicting.id)},
            )
            raise ErpExternalConflictError("Idempotency key reused with a different payload", command_id=str(conflicting.id))
        return _receipt_from_existing_command(conflicting)

    command = IntegrationCommand(
        erp_instance_id=cmd.erp_instance_id, command_type=cmd.command_type, source_event_id=cmd.source_event_id,
        source_aggregate_type=cmd.source_aggregate_type, source_aggregate_id=cmd.source_aggregate_id,
        idempotency_key=cmd.idempotency_key, payload=cmd.payload, payload_hash=payload_hash,
        correlation_id=uuid.uuid4(), state="PENDING", version=1,
    )
    session.add(command)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id, aggregate_type="integration_command",
        aggregate_id=command.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="ERPCommandQueued",
        event_payload={"id": str(command.id), "command_type": command.command_type}, expected_version=None,
        command_type="QueueERPCommand",
    )


def _receipt_from_existing_command(command: IntegrationCommand) -> MutationReceipt:
    return MutationReceipt(command_id=command.id, aggregate_id=command.id, resulting_version=command.version, audit_event_id=command.id, correlation_id=command.correlation_id)


async def _load_command_for_update(session: AsyncSession, command_id: uuid.UUID) -> IntegrationCommand:
    result = await session.execute(select(IntegrationCommand).where(IntegrationCommand.id == command_id).with_for_update())
    command = result.scalar_one_or_none()
    if command is None:
        raise NotFoundError("Integration command not found")
    return command


async def dispatch_erp_command(session: AsyncSession, command_id: uuid.UUID, actor_user_id: uuid.UUID) -> MutationReceipt:
    """dispatchERPCommand() -- ERP-ARC-021/023/024, INT-FR-003/004/008/009/012/025. Deliberately **not**
    `async def dispatch_erp_command(session, cmd: CommandEnvelope, ...)` wrapped in one caller-provided
    transaction like every other handler in this codebase: rule 01 forbids external I/O inside the
    Mutation Gateway transaction, so this function opens and commits two separate transactions itself,
    with the real HTTP call in between and no DB lock held during it:

      1. mark DISPATCHED (so a concurrent dispatch attempt cannot double-send) -- commit.
      2. call the adapter (real httpx, no open transaction / no lock) -- may fail, time out, or succeed.
      3. record the attempt + resulting state (SUCCEEDED/RETRY_WAIT/DEAD_LETTER) -- commit.

    A crash between step 1 and step 3 leaves the command `DISPATCHED` indefinitely -- exactly the
    "uncertain timeout" INT-FR-008 describes; recovering that state is `reconcile_uncertain_commit`,
    which never blindly re-sends (ERP-ARC-024/026, AG-15) and instead requires a human decision.
    """

    async with session.begin():
        command = await _load_command_for_update(session, command_id)
        if command.state not in ("PENDING", "RETRY_WAIT"):
            raise InvalidTransitionError("Only a pending or retry-waiting command can be dispatched", current_state=command.state)

        instance = await session.get(ErpInstance, command.erp_instance_id)
        if instance is None:
            raise NotFoundError("ERP instance not found")

        breaker = await reliability.get_or_create_breaker(session, erp_instance_id=instance.id, operation=command.command_type)
        cb_policy = reliability.DEFAULT_CIRCUIT_BREAKER_POLICY
        if not reliability.breaker_allows_call(breaker, policy=cb_policy):
            raise ErpThrottledError("Circuit breaker is open for this instance/operation", operation=command.command_type)

        # INT-FR-024/ERP-ARC-028: proactive per-(instance, operation) quota, independent of the circuit
        # breaker's reactive failure trip above -- a healthy, closed circuit can still be over quota.
        rl_policy = reliability.resolve_rate_limit_policy(instance.capabilities)
        if not reliability.rate_limit_allows_call(breaker, policy=rl_policy):
            raise ErpThrottledError(
                "Rate limit exceeded for this instance/operation", operation=command.command_type, reason="RATE_LIMIT_EXCEEDED",
            )

        old_state = command.state
        command.state = "DISPATCHED"
        command.version += 1
        site_id = instance.site_id
        canonical = CanonicalOutboundCommand(
            command_type=command.command_type, entity_type=command.source_aggregate_type,
            internal_ref={"source_aggregate_id": str(command.source_aggregate_id) if command.source_aggregate_id else None},
            payload=command.payload, idempotency_key=command.idempotency_key,
        )
        adapter = build_adapter(instance)
        vendor = instance.vendor

    # Step 2 -- real outbound HTTP call, deliberately outside any open transaction (rule 01).
    response = await adapter.dispatch(canonical)
    error_category = None
    if not response.succeeded:
        error_category = reliability.classify_integration_error(
            http_status=response.raw_status, exception_kind=(response.raw_body or {}).get("exception") if isinstance(response.raw_body, dict) else None,
            timed_out=response.timed_out,
        )

    async with session.begin():
        command = await _load_command_for_update(session, command_id)
        breaker = await reliability.get_or_create_breaker(session, erp_instance_id=command.erp_instance_id, operation=command.command_type)
        command.attempt_count += 1
        session.add(IntegrationCommandAttempt(
            command_id=command.id, attempt_no=command.attempt_count,
            outcome="SUCCEEDED" if response.succeeded else ("TIMEOUT_UNCERTAIN" if response.timed_out else "FAILED"),
            error_category=error_category, error_detail=response.raw_body if isinstance(response.raw_body, dict) else None,
            http_status=response.raw_status, external_reference=response.external_reference,
        ))
        reliability.record_breaker_outcome(breaker, succeeded=response.succeeded, error_category=error_category, policy=reliability.DEFAULT_CIRCUIT_BREAKER_POLICY)

        old_state = command.state
        if response.succeeded:
            command.state = "SUCCEEDED"
            command.external_reference = response.external_reference
            command.last_error_category = None
            command.last_error_detail = None
            event_type, event_payload = "ERPCommandSucceeded", {"id": str(command.id), "external_reference": response.external_reference}
        else:
            policy = reliability.resolve_retry_policy(None)
            decision = reliability.compute_retry_decision(
                error_category=error_category, attempt_count=command.attempt_count, policy=policy,
                retry_after_seconds=response.retry_after_seconds,
            )
            command.last_error_category = error_category
            command.last_error_detail = response.raw_body if isinstance(response.raw_body, dict) else {"raw_status": response.raw_status}
            if decision.should_retry:
                command.state = "RETRY_WAIT"
                command.next_attempt_at = decision.next_attempt_at
                event_type, event_payload = "IntegrationRetryScheduled", {"id": str(command.id), "error_category": error_category, "next_attempt_at": decision.next_attempt_at.isoformat() if decision.next_attempt_at else None}
            else:
                command.state = "DEAD_LETTER"
                command.required_next_action = f"Manual review required: {error_category} ({decision.terminal_reason})"
                event_type, event_payload = "ERPCommandFailed", {"id": str(command.id), "error_category": error_category, "terminal_reason": decision.terminal_reason}
        command.version += 1

        return await _write_receipt(
            session, cmd=CommandEnvelope(idempotency_key=f"dispatch:{command.id}:{command.attempt_count}"), payload_hash=command.payload_hash,
            site_id=site_id, aggregate_type="integration_command", aggregate_id=command.id, version=command.version,
            action="Changed", actor_user_id=actor_user_id, reason=None, old_state=old_state, event_type=event_type,
            event_payload=event_payload, expected_version=None, command_type="DispatchERPCommand",
        )


class RetryERPCommandCommand(CommandEnvelope):
    command_id: uuid.UUID
    reason: str


async def retry_erp_command(
    session: AsyncSession, cmd: RetryERPCommandCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """retryERPCommand() -- INT-FR-013/027. Manual replay uses the exact original payload (never
    mutated) -- only `state`/`next_attempt_at` change."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to manually retry an integration command")

    command = await _load_command_for_update(session, cmd.command_id)
    if command.state not in ("FAILED", "DEAD_LETTER", "RETRY_WAIT"):
        raise InvalidTransitionError("Only a failed, dead-lettered or retry-waiting command can be manually retried", current_state=command.state)

    old_state = command.state
    command.state = "PENDING"
    command.next_attempt_at = None
    command.required_next_action = None
    command.version += 1

    instance = await session.get(ErpInstance, command.erp_instance_id)
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id if instance else None,
        aggregate_type="integration_command", aggregate_id=command.id, version=command.version, action="Changed",
        actor_user_id=actor_user_id, reason=cmd.reason, old_state=old_state, event_type="ERPCommandRetried",
        event_payload={"id": str(command.id)}, expected_version=None, command_type="RetryERPCommand",
    )


class CancelPendingERPCommandCommand(CommandEnvelope):
    command_id: uuid.UUID
    reason: str


async def cancel_pending_erp_command(
    session: AsyncSession, cmd: CancelPendingERPCommandCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """cancelPendingERPCommand() -- ERP-ARC-027, INT-FR-015. Only before confirmed external commit --
    `DISPATCHED`/`SUCCEEDED` can never be cancelled (the send may already have taken effect)."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to cancel a pending integration command")

    command = await _load_command_for_update(session, cmd.command_id)
    if command.state not in ("PENDING", "RETRY_WAIT"):
        raise InvalidTransitionError("Only a pending or retry-waiting command can be cancelled", current_state=command.state)

    old_state = command.state
    command.state = "CANCELLED"
    command.cancelled_reason = cmd.reason
    command.cancelled_by_user_id = actor_user_id
    command.version += 1

    instance = await session.get(ErpInstance, command.erp_instance_id)
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id if instance else None,
        aggregate_type="integration_command", aggregate_id=command.id, version=command.version, action="Changed",
        actor_user_id=actor_user_id, reason=cmd.reason, old_state=old_state, event_type="ERPCommandCancelled",
        event_payload={"id": str(command.id)}, expected_version=None, command_type="CancelPendingERPCommand",
    )


class CreateCorrectedCommandCommand(CommandEnvelope):
    original_command_id: uuid.UUID
    corrected_payload: dict
    reason: str


async def create_corrected_command(
    session: AsyncSession, cmd: CreateCorrectedCommandCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """INT-FR-014. A business correction creates a brand-new command linked to the original -- the
    original's payload is never mutated."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to create a corrected command")

    original = await session.get(IntegrationCommand, cmd.original_command_id)
    if original is None:
        raise NotFoundError("Original integration command not found")
    if original.state not in ("DEAD_LETTER", "FAILED", "CANCELLED"):
        raise InvalidTransitionError("Only a terminal (dead-lettered/failed/cancelled) command can be corrected", current_state=original.state)

    corrected_hash = sha256_hex(cmd.corrected_payload)
    corrected = IntegrationCommand(
        erp_instance_id=original.erp_instance_id, command_type=original.command_type,
        source_event_id=original.source_event_id, source_aggregate_type=original.source_aggregate_type,
        source_aggregate_id=original.source_aggregate_id, idempotency_key=f"{original.idempotency_key}:correction:{uuid.uuid4()}",
        payload=cmd.corrected_payload, payload_hash=corrected_hash, correlation_id=uuid.uuid4(),
        state="PENDING", correction_of_id=original.id, version=1,
    )
    session.add(corrected)
    await session.flush()

    instance = await session.get(ErpInstance, original.erp_instance_id)
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id if instance else None,
        aggregate_type="integration_command", aggregate_id=corrected.id, version=1, action="Created",
        actor_user_id=actor_user_id, reason=cmd.reason, old_state=None, event_type="ERPCommandQueued",
        event_payload={"id": str(corrected.id), "correction_of_id": str(original.id)}, expected_version=None,
        command_type="CreateCorrectedCommand",
    )


async def reconcile_uncertain_commit(session: AsyncSession, command_id: uuid.UUID, actor_user_id: uuid.UUID) -> MutationReceipt:
    """reconcileUncertainCommit() -- INT-FR-008. A command stuck in `DISPATCHED` past a crash never
    silently resumes as PENDING (which risks a duplicate send) -- it is always routed to `RETRY_WAIT`
    with `required_next_action` demanding a human external-system lookup first (ERP-ARC-024/026, AG-15:
    no numeric "how long is a lookup allowed to take" policy exists in the baseline, so this never
    guesses -- see SG-123's provisional-defaults framing for the retry side of this same gap)."""

    command = await _load_command_for_update(session, command_id)
    if command.state != "DISPATCHED":
        raise InvalidTransitionError("Only a dispatched (uncertain) command can be reconciled", current_state=command.state)

    old_state = command.state
    command.state = "RETRY_WAIT"
    command.required_next_action = "Uncertain external commit -- verify externally before any replay (INT-FR-008)"
    command.version += 1

    instance = await session.get(ErpInstance, command.erp_instance_id)
    return await _write_receipt(
        session, cmd=CommandEnvelope(idempotency_key=f"reconcile-uncertain:{command.id}:{uuid.uuid4()}"), payload_hash=command.payload_hash,
        site_id=instance.site_id if instance else None, aggregate_type="integration_command", aggregate_id=command.id,
        version=command.version, action="Changed", actor_user_id=actor_user_id, reason=None, old_state=old_state,
        event_type="ExternalCommitNotFound", event_payload={"id": str(command.id)}, expected_version=None,
        command_type="ReconcileUncertainCommit",
    )


class CreateCompensationCommandCommand(CommandEnvelope):
    original_command_id: uuid.UUID
    compensating_command_type: str
    compensating_payload: dict
    gxp_authorization_reference: dict
    reason: str


async def create_compensation_command(
    session: AsyncSession, cmd: CreateCompensationCommandCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """createCompensationCommand() -- INT-FR-016. Distinct from `create_corrected_command`: a correction
    resends the *same* logical operation with fixed data after a failure; a compensation reverses an
    operation that already *succeeded* externally (e.g. a goods receipt posted, then the disposition that
    justified it is overturned) -- it is always a brand-new command, tied to the authorizing GxP
    correction/disposition record (`gxp_authorization_reference`), never a mutation of the original.
    `compensating_command_type`/`compensating_payload` are supplied by the caller (the GxP domain service
    that knows what reversal operation the vendor needs -- e.g. POST_RETURN for a POST_GOODS_RECEIPT),
    not derived here: no generic "reverse this operation" mapping exists in Document 53's own baseline,
    and inventing a blanket per-operation reversal rule would guess exactly the kind of vendor-specific
    business behaviour AG-15 reserves."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to create a compensation command")
    if not cmd.gxp_authorization_reference:
        raise ValidationFailedError("gxp_authorization_reference is required -- a compensation must be tied to an authorizing GxP correction/disposition record")

    original = await session.get(IntegrationCommand, cmd.original_command_id)
    if original is None:
        raise NotFoundError("Original integration command not found")
    if original.state != "SUCCEEDED":
        raise InvalidTransitionError("Only a succeeded command can be compensated -- nothing to reverse otherwise", current_state=original.state)

    compensating_hash = sha256_hex(cmd.compensating_payload)
    compensation = IntegrationCommand(
        erp_instance_id=original.erp_instance_id, command_type=cmd.compensating_command_type,
        source_event_id=original.source_event_id, source_aggregate_type=original.source_aggregate_type,
        source_aggregate_id=original.source_aggregate_id, idempotency_key=f"{original.idempotency_key}:compensation:{uuid.uuid4()}",
        payload=cmd.compensating_payload, payload_hash=compensating_hash, correlation_id=uuid.uuid4(),
        state="PENDING", compensates_command_id=original.id, gxp_authorization_reference=cmd.gxp_authorization_reference, version=1,
    )
    session.add(compensation)
    await session.flush()

    instance = await session.get(ErpInstance, original.erp_instance_id)
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id if instance else None,
        aggregate_type="integration_command", aggregate_id=compensation.id, version=1, action="Created",
        actor_user_id=actor_user_id, reason=cmd.reason, old_state=None, event_type="IntegrationCompensationQueued",
        event_payload={"id": str(compensation.id), "compensates_command_id": str(original.id)}, expected_version=None,
        command_type="CreateCompensationCommand",
    )


async def get_integration_sla_metrics(session: AsyncSession, erp_instance_id: uuid.UUID) -> dict:
    """getIntegrationSLAMetrics() -- INT-FR-021. "SLA/aging" is a read/reporting capability, not a
    regulated decision (rule 11's "no regulated decision read from ... a report" governs *decisions*
    made from a projection, not observability metrics like these) -- all timestamps already exist on
    IntegrationCommand/IntegrationReconciliationRun, so this is a query, not a new state machine."""

    now = datetime.now(timezone.utc)

    def _age_seconds(ts: datetime | None) -> float | None:
        if ts is None:
            return None
        ts = ts if ts.tzinfo else ts.replace(tzinfo=timezone.utc)
        return (now - ts).total_seconds()

    oldest_pending = (
        await session.execute(
            select(IntegrationCommand.created_at).where(
                IntegrationCommand.erp_instance_id == erp_instance_id, IntegrationCommand.state.in_(("PENDING", "RETRY_WAIT")),
            ).order_by(IntegrationCommand.created_at.asc()).limit(1)
        )
    ).scalar_one_or_none()
    oldest_dead_letter = (
        await session.execute(
            select(IntegrationCommand.updated_at).where(
                IntegrationCommand.erp_instance_id == erp_instance_id, IntegrationCommand.state == "DEAD_LETTER",
            ).order_by(IntegrationCommand.updated_at.asc()).limit(1)
        )
    ).scalar_one_or_none()
    oldest_open_run = (
        await session.execute(
            select(IntegrationReconciliationRun.created_at).where(
                IntegrationReconciliationRun.erp_instance_id == erp_instance_id, IntegrationReconciliationRun.status == "RUNNING",
            ).order_by(IntegrationReconciliationRun.created_at.asc()).limit(1)
        )
    ).scalar_one_or_none()
    oldest_open_difference = (
        await session.execute(
            select(IntegrationReconciliationDifference.created_at).join(
                IntegrationReconciliationRun, IntegrationReconciliationRun.id == IntegrationReconciliationDifference.run_id,
            ).where(
                IntegrationReconciliationRun.erp_instance_id == erp_instance_id,
                IntegrationReconciliationDifference.resolution_status == "OPEN",
            ).order_by(IntegrationReconciliationDifference.created_at.asc()).limit(1)
        )
    ).scalar_one_or_none()

    return {
        "oldest_pending_age_seconds": _age_seconds(oldest_pending),
        "oldest_dead_letter_age_seconds": _age_seconds(oldest_dead_letter),
        "oldest_open_reconciliation_run_age_seconds": _age_seconds(oldest_open_run),
        "oldest_open_reconciliation_difference_age_seconds": _age_seconds(oldest_open_difference),
    }


# ---------------------------------------------------------------------------------------------------
# IntegrationInboundEvent — ERP-ARC-022, INT-FR-010/011/025. Unsigned (SG-122).
# ---------------------------------------------------------------------------------------------------


class IngestERPEventCommand(CommandEnvelope):
    erp_instance_id: uuid.UUID
    external_event_id: str
    entity_type: str | None = None
    # INT-FR-011: the specific external record this event concerns -- required for staleness detection;
    # an event with no external_entity_id is processed exactly as before (no ordering to compare).
    external_entity_id: str | None = None
    source_version: str | None = None
    payload: dict


async def ingest_erp_event(
    session: AsyncSession, cmd: IngestERPEventCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.payload)
    instance = await session.get(ErpInstance, cmd.erp_instance_id)
    if instance is None:
        raise NotFoundError("ERP instance not found")

    existing = (
        await session.execute(
            select(IntegrationInboundEvent).where(
                IntegrationInboundEvent.erp_instance_id == cmd.erp_instance_id,
                IntegrationInboundEvent.external_event_id == cmd.external_event_id,
            )
        )
    ).scalar_one_or_none()
    if existing is not None:
        if existing.payload_hash != payload_hash:
            # INT-FR-007/025: same external_event_id, different content -- integrity conflict, not a
            # silent overwrite of the original accepted row.
            await _record_security_event_durably(
                erp_instance_id=cmd.erp_instance_id, event_type="INBOUND_EVENT_ID_REUSED", severity="WARNING",
                detail={"external_event_id": cmd.external_event_id, "conflicting_event_id": str(existing.id)},
            )
            raise ErpExternalConflictError("Inbound event id reused with a different payload", event_id=str(existing.id))
        return MutationReceipt(command_id=existing.id, aggregate_id=existing.id, resulting_version=1, audit_event_id=existing.id, correlation_id=existing.correlation_id)

    # INT-FR-011: out-of-order/stale detection, only possible when the caller names which external
    # record this event concerns. Compares against the most recently *processed* event for the same
    # (instance, entity_type, external_entity_id) -- never against a stale/superseded one, so a run of
    # late arrivals cannot each compare favourably against an already-rejected predecessor.
    processing_state = "PROCESSED"
    if cmd.external_entity_id:
        last_processed = (
            await session.execute(
                select(IntegrationInboundEvent).where(
                    IntegrationInboundEvent.erp_instance_id == cmd.erp_instance_id,
                    IntegrationInboundEvent.entity_type == cmd.entity_type,
                    IntegrationInboundEvent.external_entity_id == cmd.external_entity_id,
                    IntegrationInboundEvent.processing_state == "PROCESSED",
                ).order_by(IntegrationInboundEvent.applied_at.desc()).limit(1)
            )
        ).scalar_one_or_none()
        if last_processed is not None and _is_source_version_stale(last_processed.source_version, cmd.source_version):
            processing_state = "STALE_SUPERSEDED"

    event = IntegrationInboundEvent(
        erp_instance_id=cmd.erp_instance_id, external_event_id=cmd.external_event_id, entity_type=cmd.entity_type,
        external_entity_id=cmd.external_entity_id, source_version=cmd.source_version, payload=cmd.payload,
        payload_hash=payload_hash, processing_state="RECEIVED", correlation_id=uuid.uuid4(),
    )
    session.add(event)
    await session.flush()
    # A STALE_SUPERSEDED event is still recorded (investigation/audit value), just never marked
    # PROCESSED and never contributes to a projection -- exactly INT-FR-011's "stale events cannot
    # overwrite newer projection", not "stale events are discarded".
    event.processing_state = processing_state
    event.applied_at = datetime.now(timezone.utc)

    audit_event = await write_audit_event(
        session, site_id=instance.site_id, aggregate_type="integration_inbound_event", aggregate_id=event.id,
        aggregate_version=1, action="Created", actor_id=actor_user_id, correlation_id=event.correlation_id,
        new_value={"external_event_id": event.external_event_id, "entity_type": event.entity_type},
    )
    await write_outbox_event(
        session, event_type="ERPInboundEventReceived", aggregate_type="integration_inbound_event", aggregate_id=event.id,
        aggregate_version=1, payload={"id": str(event.id), "entity_type": event.entity_type}, correlation_id=event.correlation_id,
    )
    receipt = await record_command_receipt(
        session, site_id=instance.site_id, command_type="IngestERPEvent", aggregate_type="integration_inbound_event",
        aggregate_id=event.id, expected_version=None, resulting_version=1, idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash, actor_user_id=actor_user_id, payload_hash=payload_hash,
    )
    return MutationReceipt(command_id=receipt.id, aggregate_id=event.id, resulting_version=1, audit_event_id=audit_event.id, correlation_id=event.correlation_id)


# ---------------------------------------------------------------------------------------------------
# Reconciliation — ERP-ARC-025, INT-FR-017..021. Unsigned (SG-122). SG-124: never auto-resolves.
# ---------------------------------------------------------------------------------------------------


class CreateReconciliationRunCommand(CommandEnvelope):
    erp_instance_id: uuid.UUID
    scope: str
    reconciliation_type: str
    cutoff_at: datetime
    query_keys: dict | None = None


async def create_reconciliation_run(
    session: AsyncSession, cmd: CreateReconciliationRunCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    instance = await session.get(ErpInstance, cmd.erp_instance_id)
    if instance is None:
        raise NotFoundError("ERP instance not found")

    mapping_versions = (
        await session.execute(
            select(ErpExternalMapping.id, ErpExternalMapping.version).where(ErpExternalMapping.erp_instance_id == cmd.erp_instance_id)
        )
    ).all()
    run = IntegrationReconciliationRun(
        erp_instance_id=cmd.erp_instance_id, scope=cmd.scope, reconciliation_type=cmd.reconciliation_type,
        cutoff_at=cmd.cutoff_at, query_keys=cmd.query_keys,
        mapping_version_snapshot={str(mid): v for mid, v in mapping_versions}, status="RUNNING",
        started_by_user_id=actor_user_id, version=1,
    )
    session.add(run)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id, aggregate_type="integration_reconciliation_run",
        aggregate_id=run.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="ReconciliationStarted", event_payload={"id": str(run.id), "scope": run.scope}, expected_version=None,
        command_type="CreateReconciliationRun",
    )


class RecordReconciliationDifferenceCommand(CommandEnvelope):
    run_id: uuid.UUID
    difference_type: str
    internal_ref: dict | None = None
    external_ref: dict | None = None
    field_name: str | None = None
    internal_value: dict | None = None
    external_value: dict | None = None
    requires_qa_hold: bool = False


async def record_reconciliation_difference(
    session: AsyncSession, cmd: RecordReconciliationDifferenceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if cmd.difference_type not in DIFFERENCE_TYPES:
        raise ValidationFailedError("Unrecognized difference_type", allowed=list(DIFFERENCE_TYPES))

    run = await session.get(IntegrationReconciliationRun, cmd.run_id)
    if run is None:
        raise NotFoundError("Reconciliation run not found")

    # SG-124: no auto-resolve rule exists -- always OPEN, always requires a human resolution call.
    difference = IntegrationReconciliationDifference(
        run_id=run.id, difference_type=cmd.difference_type, internal_ref=cmd.internal_ref, external_ref=cmd.external_ref,
        field_name=cmd.field_name, internal_value=cmd.internal_value, external_value=cmd.external_value,
        requires_qa_hold=cmd.requires_qa_hold, resolution_status="OPEN", version=1,
    )
    session.add(difference)
    run.difference_count += 1
    run.version += 1
    await session.flush()

    instance = await session.get(ErpInstance, run.erp_instance_id)
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id if instance else None,
        aggregate_type="integration_reconciliation_difference", aggregate_id=difference.id, version=1, action="Created",
        actor_user_id=actor_user_id, reason=None, old_state=None, event_type="ReconciliationMismatchDetected",
        event_payload={"id": str(difference.id), "run_id": str(run.id), "difference_type": difference.difference_type},
        expected_version=None, command_type="RecordReconciliationDifference",
    )


class ResolveReconciliationDifferenceCommand(CommandEnvelope):
    difference_id: uuid.UUID
    expected_version: int
    resolution_status: str  # RESOLVED | ESCALATED
    resolution_reason: str


async def resolve_reconciliation_difference(
    session: AsyncSession, cmd: ResolveReconciliationDifferenceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if not cmd.resolution_reason:
        raise ValidationFailedError("resolution_reason is required")
    if cmd.resolution_status not in ("RESOLVED", "ESCALATED"):
        raise ValidationFailedError("resolution_status must be RESOLVED or ESCALATED (never AUTO_RESOLVED here -- SG-124)")

    result = await session.execute(
        select(IntegrationReconciliationDifference).where(IntegrationReconciliationDifference.id == cmd.difference_id).with_for_update()
    )
    difference = result.scalar_one_or_none()
    if difference is None:
        raise NotFoundError("Reconciliation difference not found")
    if difference.version != cmd.expected_version:
        raise StaleVersionError("Difference was modified since it was read", expected_version=cmd.expected_version, current_version=difference.version)
    if difference.resolution_status != "OPEN":
        raise InvalidTransitionError("Only an open difference can be resolved", current_state=difference.resolution_status)

    old_state = difference.resolution_status
    difference.resolution_status = cmd.resolution_status
    difference.resolution_reason = cmd.resolution_reason
    difference.resolved_by_user_id = actor_user_id
    difference.resolved_at = datetime.now(timezone.utc)
    difference.version += 1

    run = await session.get(IntegrationReconciliationRun, difference.run_id)
    instance = await session.get(ErpInstance, run.erp_instance_id) if run else None
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id if instance else None,
        aggregate_type="integration_reconciliation_difference", aggregate_id=difference.id, version=difference.version,
        action="Approved", actor_user_id=actor_user_id, reason=cmd.resolution_reason, old_state=old_state,
        event_type="ReconciliationResolved", event_payload={"id": str(difference.id), "resolution_status": cmd.resolution_status},
        expected_version=cmd.expected_version, command_type="ResolveReconciliationDifference",
    )


class CompleteReconciliationRunCommand(CommandEnvelope):
    run_id: uuid.UUID
    expected_version: int
    status: str  # COMPLETED | FAILED


async def complete_reconciliation_run(
    session: AsyncSession, cmd: CompleteReconciliationRunCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if cmd.status not in ("COMPLETED", "FAILED"):
        raise ValidationFailedError("status must be COMPLETED or FAILED")

    result = await session.execute(select(IntegrationReconciliationRun).where(IntegrationReconciliationRun.id == cmd.run_id).with_for_update())
    run = result.scalar_one_or_none()
    if run is None:
        raise NotFoundError("Reconciliation run not found")
    if run.version != cmd.expected_version:
        raise StaleVersionError("Run was modified since it was read", expected_version=cmd.expected_version, current_version=run.version)
    if run.status != "RUNNING":
        raise InvalidTransitionError("Only a running reconciliation run can be completed", current_state=run.status)

    old_state = run.status
    run.status = cmd.status
    run.completed_at = datetime.now(timezone.utc)
    run.version += 1

    instance = await session.get(ErpInstance, run.erp_instance_id)
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id if instance else None,
        aggregate_type="integration_reconciliation_run", aggregate_id=run.id, version=run.version, action="Changed",
        actor_user_id=actor_user_id, reason=None, old_state=old_state, event_type="ReconciliationCompleted",
        event_payload={"id": str(run.id), "status": run.status, "difference_count": run.difference_count},
        expected_version=cmd.expected_version, command_type="CompleteReconciliationRun",
    )


# ---------------------------------------------------------------------------------------------------
# Bulk jobs — INT-FR-023. Unsigned (SG-122).
# ---------------------------------------------------------------------------------------------------


async def _load_bulk_job_for_update(session: AsyncSession, job_id: uuid.UUID) -> IntegrationBulkJob:
    result = await session.execute(select(IntegrationBulkJob).where(IntegrationBulkJob.id == job_id).with_for_update())
    job = result.scalar_one_or_none()
    if job is None:
        raise NotFoundError("Bulk job not found")
    return job


class StartBulkJobCommand(CommandEnvelope):
    erp_instance_id: uuid.UUID
    job_type: str
    entity_type: str
    total_records: int | None = None


async def start_bulk_job(session: AsyncSession, cmd: StartBulkJobCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    """startBulkJob() -- INT-FR-023. `idempotency_key` is the resume handle: calling this again with the
    same key after a crash returns the *existing* job (with its `resume_cursor`) rather than starting a
    second one -- the caller reads `resume_cursor` off the returned receipt's aggregate to know where to
    continue, same idempotent-resume shape as `ErpSyncCheckpoint`."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if cmd.job_type not in BULK_JOB_TYPES:
        raise ValidationFailedError("job_type must be IMPORT or EXPORT", job_type=cmd.job_type)
    if cmd.entity_type not in MAPPING_ENTITY_TYPES:
        raise ValidationFailedError("Unrecognized entity_type", entity_type=cmd.entity_type)

    instance = await session.get(ErpInstance, cmd.erp_instance_id)
    if instance is None:
        raise NotFoundError("ERP instance not found")

    conflicting = (
        await session.execute(
            select(IntegrationBulkJob).where(
                IntegrationBulkJob.erp_instance_id == cmd.erp_instance_id, IntegrationBulkJob.idempotency_key == cmd.idempotency_key,
            )
        )
    ).scalar_one_or_none()
    if conflicting is not None:
        return MutationReceipt(
            command_id=conflicting.id, aggregate_id=conflicting.id, resulting_version=conflicting.version,
            audit_event_id=conflicting.id, correlation_id=conflicting.id,
        )

    job = IntegrationBulkJob(
        site_id=instance.site_id, erp_instance_id=cmd.erp_instance_id, job_type=cmd.job_type, entity_type=cmd.entity_type,
        idempotency_key=cmd.idempotency_key, total_records=cmd.total_records, started_by_user_id=actor_user_id,
        status="RUNNING", version=1,
    )
    session.add(job)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id, aggregate_type="integration_bulk_job",
        aggregate_id=job.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="BulkJobStarted", event_payload={"id": str(job.id), "job_type": job.job_type, "entity_type": job.entity_type},
        expected_version=None, command_type="StartBulkJob",
    )


class RecordBulkJobProgressCommand(CommandEnvelope):
    job_id: uuid.UUID
    expected_version: int
    succeeded_delta: int = 0
    newly_failed_records: list[dict] | None = None
    resume_cursor: str | None = None


async def record_bulk_job_progress(session: AsyncSession, cmd: RecordBulkJobProgressCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    """recordBulkJobProgress() -- INT-FR-023. Called once per processed chunk. `newly_failed_records`
    (record-level identity + reason, this chunk only) is appended, never replaced -- the running
    `failed_records` list is the record-level failure detail the requirement asks for; successes are
    only ever counted (module docstring)."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    job = await _load_bulk_job_for_update(session, cmd.job_id)
    if job.version != cmd.expected_version:
        raise StaleVersionError("Bulk job was modified since it was read", expected_version=cmd.expected_version, current_version=job.version)
    if job.status != "RUNNING":
        raise InvalidTransitionError("Only a running bulk job accepts progress", current_state=job.status)

    old_state = job.status
    job.succeeded_count += max(cmd.succeeded_delta, 0)
    if cmd.newly_failed_records:
        job.failed_count += len(cmd.newly_failed_records)
        job.failed_records = [*(job.failed_records or []), *cmd.newly_failed_records]
    if cmd.resume_cursor:
        job.resume_cursor = cmd.resume_cursor
    job.version += 1

    instance = await session.get(ErpInstance, job.erp_instance_id)
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id if instance else None,
        aggregate_type="integration_bulk_job", aggregate_id=job.id, version=job.version, action="Changed",
        actor_user_id=actor_user_id, reason=None, old_state=old_state, event_type="BulkJobProgressRecorded",
        event_payload={"id": str(job.id), "succeeded_count": job.succeeded_count, "failed_count": job.failed_count},
        expected_version=cmd.expected_version, command_type="RecordBulkJobProgress",
    )


class CompleteBulkJobCommand(CommandEnvelope):
    job_id: uuid.UUID
    expected_version: int


async def complete_bulk_job(session: AsyncSession, cmd: CompleteBulkJobCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    job = await _load_bulk_job_for_update(session, cmd.job_id)
    if job.version != cmd.expected_version:
        raise StaleVersionError("Bulk job was modified since it was read", expected_version=cmd.expected_version, current_version=job.version)
    if job.status != "RUNNING":
        raise InvalidTransitionError("Only a running bulk job can be completed", current_state=job.status)

    old_state = job.status
    job.status = "COMPLETED_WITH_ERRORS" if job.failed_count > 0 else "COMPLETED"
    job.completed_at = datetime.now(timezone.utc)
    job.version += 1

    instance = await session.get(ErpInstance, job.erp_instance_id)
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=instance.site_id if instance else None,
        aggregate_type="integration_bulk_job", aggregate_id=job.id, version=job.version, action="Changed",
        actor_user_id=actor_user_id, reason=None, old_state=old_state, event_type="BulkJobCompleted",
        event_payload={"id": str(job.id), "status": job.status, "succeeded_count": job.succeeded_count, "failed_count": job.failed_count},
        expected_version=cmd.expected_version, command_type="CompleteBulkJob",
    )


# ---------------------------------------------------------------------------------------------------
# Migration package provenance — MDS-FR-028. Unsigned (SG-122).
# ---------------------------------------------------------------------------------------------------


class RecordMigrationPackageCommand(CommandEnvelope):
    erp_instance_id: uuid.UUID | None = None
    site_id: uuid.UUID | None = None
    package_name: str
    source_checksum: str
    entity_types: list[str] | None = None
    approval_reference: str | None = None


async def record_migration_package(session: AsyncSession, cmd: RecordMigrationPackageCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    """recordMigrationPackage() -- MDS-FR-028. No dedicated function exists in Document 52's own
    catalogue for this (module docstring); the row is the requirement's full scope -- a provenance
    record, not a workflow. `approved_by_user_id` is set only when the caller supplies
    `approval_reference` (an already-approved package being retroactively recorded), never inferred."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if not cmd.package_name or not cmd.source_checksum:
        raise ValidationFailedError("package_name and source_checksum are required")

    for entity_type in cmd.entity_types or []:
        if entity_type not in MAPPING_ENTITY_TYPES:
            raise ValidationFailedError("Unrecognized entity_type in entity_types", entity_type=entity_type)

    package = ErpMigrationPackage(
        site_id=cmd.site_id, erp_instance_id=cmd.erp_instance_id, package_name=cmd.package_name,
        source_checksum=cmd.source_checksum, entity_types=cmd.entity_types,
        imported_by_user_id=actor_user_id, approved_by_user_id=actor_user_id if cmd.approval_reference else None,
        approval_reference=cmd.approval_reference, version=1,
    )
    session.add(package)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="erp_migration_package",
        aggregate_id=package.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="MigrationPackageRecorded", event_payload={"id": str(package.id), "package_name": package.package_name},
        expected_version=None, command_type="RecordMigrationPackage",
    )
