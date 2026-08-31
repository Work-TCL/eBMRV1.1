"""Document 58 (SPEC-PM-001) Mutation Gateway command handlers.

`calculateSurveillanceMetric()` and `buildPeriodicSafetyDataset()` need an immutable, reproducible
snapshot but the approved schema baseline gives this module exactly 4 owned entities, none of them a
metric/dataset table (see models.py's module docstring). Both are implemented by calling
`vault_service.release_master()` directly (AG-08/AG-12: Vault already owns "immutable, hash-controlled,
versioned released snapshot of arbitrary content" as a cross-cutting concern) rather than inventing a
parallel table -- the same reuse precedent `qms`/`ddcp` modules use for evidence packaging.

`escalateSignalToQMSOrRegulatory()` dispatches to the real QMS creation command for CAPA/Change
Control/Risk Review/Field Action (`target_command` is validated against that module's own Command schema,
not re-invented here) and stores the resulting receipt's aggregate id as a cross-link. `REPORTABILITY_TRACK`
is a valid `target_module` per PMS-FR-024 but Document 59 (SPEC-PM-002) is not built yet in this pass --
raises `ValidationFailedError` until it is (tracked, not a SPEC_GAP: this is sequencing, not ambiguity).
"""

import uuid
from datetime import datetime, timezone

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.postmarket.models import (
    CONSTITUENT_ATTRIBUTIONS,
    ESCALATION_TARGET_MODULES,
    IDENTITY_RESOLUTION_STATES,
    POSTMARKET_SOURCE_TYPES,
    SAFETY_CASE_TRANSITIONS,
    SIGNAL_DETECTION_SOURCES,
    SIGNAL_TRANSITIONS,
    PostmarketSource,
    SafetyCase,
    SafetyCaseFollowup,
    SafetySignal,
)
from app.modules.qms import capa_commands, change_commands, field_action_commands, risk_commands
from app.modules.signature import service as signature_service
from app.modules.vault import service as vault_service
from app.modules.vault.models import VaultObject
from app.mutation.errors import (
    ExpectednessReferenceRequiredError,
    InvalidTransitionError,
    MissingSignatureError,
    NotFoundError,
    PmsCaseDuplicateSourceError,
    PmsSourceInvalidError,
    ProductUnresolvedError,
    SafetyClassificationIncompleteError,
    SignalScopeInvalidError,
    StaleSafetyCaseVersionError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
        audit_event_id=existing.id, correlation_id=existing.id,
    )


async def _write_receipt(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, site_id: uuid.UUID | None,
    aggregate_type: str, aggregate_id: uuid.UUID, version: int, action: str, actor_user_id: uuid.UUID,
    reason: str | None, old_state: str | None, event_type: str, event_payload: dict,
    expected_version: int | None, command_type: str, signature_id: uuid.UUID | None = None,
) -> MutationReceipt:
    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session, site_id=site_id, aggregate_type=aggregate_type, aggregate_id=aggregate_id,
        aggregate_version=version, action=action, actor_id=actor_user_id, correlation_id=correlation_id,
        reason=reason, old_value={"state": old_state} if old_state else None, new_value=event_payload,
        signature_id=signature_id,
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
        audit_event_id=audit_event.id, signature_id=signature_id, correlation_id=correlation_id,
    )


async def _resolve_signature(
    session: AsyncSession, *, record_type: str, action: str, actor_user_id: uuid.UUID,
    record_version: int, record_hash: str, challenge_id: uuid.UUID | None, reauth_password: str | None,
) -> uuid.UUID | None:
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


def _case_hash(case: SafetyCase) -> str:
    return sha256_hex({"id": str(case.id), "version": case.version, "state": case.state})


def _signal_hash(signal: SafetySignal) -> str:
    return sha256_hex({"id": str(signal.id), "version": signal.version, "state": signal.state})


async def _release_or_reuse_vault_snapshot(
    session: AsyncSession, *, object_type: str, business_id: str, canonical_payload: dict,
    actor_user_id: uuid.UUID, site_id: uuid.UUID | None, business_version_label: str | None,
) -> VaultObject:
    """`vault_service.release_master()` always creates the *next* version for (object_type, business_id)
    -- it is not itself idempotent by content, so calling it twice for the same key would produce two
    different immutable versions even when nothing about the underlying data changed. "Historical metric
    formula version remains reproducible" means the same key with unchanged content returns the *same*
    stored snapshot; only a genuine content change (a new digest) creates a new version.
    """
    latest = (
        await session.execute(
            select(VaultObject)
            .where(VaultObject.object_type == object_type, VaultObject.business_id == business_id)
            .order_by(VaultObject.internal_version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if latest is not None and latest.digest == sha256_hex(canonical_payload):
        return latest
    return await vault_service.release_master(
        session, object_type=object_type, business_id=business_id, canonical_payload=canonical_payload,
        actor_user_id=actor_user_id, site_id=site_id, business_version_label=business_version_label,
    )


# ---------------------------------------------------------------------------------------------------
# PostmarketSource -- PMS-FR-001.
# ---------------------------------------------------------------------------------------------------


class RegisterPostmarketSourceCommand(CommandEnvelope):
    site_id: uuid.UUID
    source_type: str
    organization_or_system: str
    channel: str
    owner_subject_id: uuid.UUID
    ingestion_profile_id: uuid.UUID | None = None
    reason: str | None = None


async def register_postmarket_source(
    session: AsyncSession, cmd: RegisterPostmarketSourceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.source_type not in POSTMARKET_SOURCE_TYPES:
        raise PmsSourceInvalidError("Unrecognized source_type", allowed=list(POSTMARKET_SOURCE_TYPES))

    source = PostmarketSource(
        site_id=cmd.site_id, source_type=cmd.source_type, organization_or_system=cmd.organization_or_system,
        channel=cmd.channel, owner_subject_id=cmd.owner_subject_id, ingestion_profile_id=cmd.ingestion_profile_id,
        state="ACTIVE", version=1,
    )
    session.add(source)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="postmarket_source",
        aggregate_id=source.id, version=source.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=None, event_type="PostmarketSourceRegistered",
        event_payload={"source_id": str(source.id), "source_type": source.source_type},
        expected_version=None, command_type="RegisterPostmarketSource",
    )


# ---------------------------------------------------------------------------------------------------
# SafetyCase -- PMS-FR-002/003/004/005/006/007/008/009/010/011/012/013/014/015/016/017/029.
# ---------------------------------------------------------------------------------------------------


class CreateSafetyCaseLinkCommand(CommandEnvelope):
    site_id: uuid.UUID
    safety_case_number: str
    source_record_type: str
    source_record_id: uuid.UUID
    source_record_version: int
    source_receipt_at: datetime | None = None
    company_initial_receipt_at: datetime | None = None
    regulatory_clock_candidate_at: datetime | None = None
    reporter_details: dict | None = None
    citation: dict | None = None
    external_reference: str | None = None
    seriousness_attributes: dict | None = None
    reason: str | None = None


async def create_safety_case_link(
    session: AsyncSession, cmd: CreateSafetyCaseLinkCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    # PMS-FR-002: createSafetyCaseLink() is not the duplicate-detection engine (findProbableDuplicates()
    # is) -- this only guards against re-linking the exact same source record/version twice.
    dup = (
        await session.execute(
            select(SafetyCase).where(
                SafetyCase.source_record_type == cmd.source_record_type,
                SafetyCase.source_record_id == cmd.source_record_id,
                SafetyCase.source_record_version == cmd.source_record_version,
            )
        )
    ).scalar_one_or_none()
    if dup is not None:
        raise PmsCaseDuplicateSourceError("Source record/version already linked to a safety case", existing_case_id=str(dup.id))

    case = SafetyCase(
        site_id=cmd.site_id, safety_case_number=cmd.safety_case_number,
        source_record_type=cmd.source_record_type, source_record_id=cmd.source_record_id,
        source_record_version=cmd.source_record_version, source_receipt_at=cmd.source_receipt_at,
        company_initial_receipt_at=cmd.company_initial_receipt_at,
        regulatory_clock_candidate_at=cmd.regulatory_clock_candidate_at,
        reporter_details=cmd.reporter_details, citation=cmd.citation, external_reference=cmd.external_reference,
        seriousness_attributes=cmd.seriousness_attributes, identity_resolution_state="UNKNOWN_QUEUE",
        state="RECEIVED", version=1,
    )
    session.add(case)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="safety_case",
        aggregate_id=case.id, version=case.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=None, event_type="SafetyCaseCreated",
        event_payload={
            "case_id": str(case.id), "safety_case_number": case.safety_case_number,
            "source_record_type": case.source_record_type, "source_record_id": str(case.source_record_id),
        },
        expected_version=None, command_type="CreateSafetyCaseLink",
    )


async def _get_case_for_update(session: AsyncSession, case_id: uuid.UUID, expected_version: int) -> SafetyCase:
    case = await session.get(SafetyCase, case_id)
    if case is None:
        raise NotFoundError("Safety case not found")
    if case.version != expected_version:
        raise StaleSafetyCaseVersionError("Safety case version changed since this request was prepared", current_version=case.version)
    return case


class ResolveMarketedProductCommand(CommandEnvelope):
    case_id: uuid.UUID
    expected_version: int
    marketed_product_id: uuid.UUID | None = None
    application_profile_id: uuid.UUID | None = None
    product_resolution: dict | None = None
    mark_resolved: bool = False
    reason: str | None = None


async def resolve_marketed_product(
    session: AsyncSession, cmd: ResolveMarketedProductCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    case = await _get_case_for_update(session, cmd.case_id, cmd.expected_version)
    old_state = case.state

    if cmd.mark_resolved:
        # PMS-FR-005: unknown identity is an open data-quality task, never discarded -- resolving to
        # RESOLVED requires the caller to actually supply identifiers, or this stays UNKNOWN_QUEUE.
        if cmd.marketed_product_id is None and not cmd.product_resolution:
            raise ProductUnresolvedError("mark_resolved=True requires marketed_product_id or product_resolution")
        case.identity_resolution_state = "RESOLVED"
    case.marketed_product_id = cmd.marketed_product_id or case.marketed_product_id
    case.application_profile_id = cmd.application_profile_id or case.application_profile_id
    if cmd.product_resolution is not None:
        case.product_resolution = cmd.product_resolution
    if case.state == "RECEIVED":
        case.state = "IDENTITY_RESOLUTION"
    case.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=case.site_id, aggregate_type="safety_case",
        aggregate_id=case.id, version=case.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="SafetyProductResolved",
        event_payload={"case_id": str(case.id), "identity_resolution_state": case.identity_resolution_state},
        expected_version=cmd.expected_version, command_type="ResolveMarketedProduct",
    )


class ClassifySafetyCaseCommand(CommandEnvelope):
    case_id: uuid.UUID
    expected_version: int
    classification: dict
    constituent_attribution: str | None = None
    expectedness_reference: dict | None = None
    rationale: str


async def classify_safety_case(
    session: AsyncSession, cmd: ClassifySafetyCaseCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    case = await _get_case_for_update(session, cmd.case_id, cmd.expected_version)
    old_state = case.state

    if not cmd.classification:
        raise SafetyClassificationIncompleteError("classification payload is empty")
    if cmd.constituent_attribution is not None and cmd.constituent_attribution not in CONSTITUENT_ATTRIBUTIONS:
        raise ValidationFailedError("Unrecognized constituent_attribution", allowed=list(CONSTITUENT_ATTRIBUTIONS))
    # PMS-FR-017: expectedness must reference the exact labeling/RSI version used, not be inferred.
    if cmd.classification.get("expectedness") is not None and not cmd.expectedness_reference:
        raise ExpectednessReferenceRequiredError("expectedness assessment requires expectedness_reference")

    if case.constituent_classification is not None:
        case.classification_history = [
            *case.classification_history,
            {"version": case.current_classification_version, "classification": case.constituent_classification, "rationale": None},
        ]
    case.constituent_classification = cmd.classification
    case.current_classification_version += 1
    if cmd.constituent_attribution is not None:
        case.constituent_attribution = cmd.constituent_attribution
    case.reassessment_required = False
    if case.state in ("IDENTITY_RESOLUTION", "RECEIVED"):
        case.state = "INITIAL_CLASSIFICATION"
    case.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=case.site_id, aggregate_type="safety_case",
        aggregate_id=case.id, version=case.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=old_state, event_type="SafetyCaseClassified",
        event_payload={"case_id": str(case.id), "classification_version": case.current_classification_version},
        expected_version=cmd.expected_version, command_type="ClassifySafetyCase",
    )


class AddSafetyCaseFollowupCommand(CommandEnvelope):
    case_id: uuid.UUID
    expected_version: int
    followup_receipt_at: datetime
    source_reference: dict
    new_information: dict
    reassessment_flags: dict = {}
    reason: str | None = None


async def add_safety_case_followup(
    session: AsyncSession, cmd: AddSafetyCaseFollowupCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    # PMS-FR-016/# 12: a follow-up during review forces a version bump so any in-flight reviewer refreshes
    # -- this is why followups take expected_version too, even though they never rewrite prior classification.
    case = await _get_case_for_update(session, cmd.case_id, cmd.expected_version)
    old_state = case.state

    next_no = (
        await session.execute(
            select(SafetyCaseFollowup.followup_no)
            .where(SafetyCaseFollowup.safety_case_id == case.id)
            .order_by(SafetyCaseFollowup.followup_no.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    followup = SafetyCaseFollowup(
        safety_case_id=case.id, followup_no=(next_no or 0) + 1, followup_receipt_at=cmd.followup_receipt_at,
        source_reference=cmd.source_reference, new_information=cmd.new_information,
        reassessment_flags=cmd.reassessment_flags, recorded_by=actor_user_id,
    )
    session.add(followup)
    case.reassessment_required = True
    case.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=case.site_id, aggregate_type="safety_case",
        aggregate_id=case.id, version=case.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="SafetyCaseFollowupReceived",
        event_payload={"case_id": str(case.id), "followup_no": followup.followup_no},
        expected_version=cmd.expected_version, command_type="AddSafetyCaseFollowup",
    )


class FindProbableDuplicatesCommand(CommandEnvelope):
    case_id: uuid.UUID
    matching_policy_version: str = "v1"


async def find_probable_duplicates(session: AsyncSession, cmd: FindProbableDuplicatesCommand) -> list[dict]:
    """Read-only, PMS-FR-014 -- "calculate match features; no merge write". `matching_policy_version`
    "v1" is a same-source-record-type + same-site heuristic: this codebase has no shared identity-matching
    engine to call into, and inventing a real fuzzy-matching algorithm would be guessing regulated
    behaviour with no baseline to check it against. Returned candidates are advisory only (PMS-FR-028);
    linkDuplicateCases() is the human decision.
    """
    case = await session.get(SafetyCase, cmd.case_id)
    if case is None:
        raise NotFoundError("Safety case not found")
    candidates = (
        await session.execute(
            select(SafetyCase).where(
                SafetyCase.id != case.id, SafetyCase.site_id == case.site_id,
                SafetyCase.source_record_type == case.source_record_type,
                SafetyCase.canonical_case_id.is_(None),
            )
        )
    ).scalars().all()
    return [
        {"case_id": str(c.id), "safety_case_number": c.safety_case_number, "match_basis": "same_source_record_type_and_site"}
        for c in candidates
    ]


class LinkDuplicateCasesCommand(CommandEnvelope):
    canonical_case_id: uuid.UUID
    duplicate_case_ids: list[uuid.UUID]
    rationale: str


async def link_duplicate_cases(
    session: AsyncSession, cmd: LinkDuplicateCasesCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    canonical = await session.get(SafetyCase, cmd.canonical_case_id)
    if canonical is None:
        raise NotFoundError("Canonical safety case not found")
    if not cmd.duplicate_case_ids:
        raise ValidationFailedError("duplicate_case_ids must not be empty")

    linked = []
    for dup_id in cmd.duplicate_case_ids:
        if dup_id == cmd.canonical_case_id:
            raise ValidationFailedError("A case cannot be linked as its own duplicate")
        dup = await session.get(SafetyCase, dup_id)
        if dup is None:
            raise NotFoundError(f"Duplicate safety case {dup_id} not found")
        # PMS-FR-015: link without destructive merge -- original source records are retained untouched.
        dup.canonical_case_id = canonical.id
        dup.duplicate_link_rationale = cmd.rationale
        dup.version += 1
        linked.append(str(dup.id))
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=canonical.site_id, aggregate_type="safety_case",
        aggregate_id=canonical.id, version=canonical.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=None, event_type="SafetyCasesLinked",
        event_payload={"canonical_case_id": str(canonical.id), "duplicate_case_ids": linked},
        expected_version=None, command_type="LinkDuplicateCases",
    )


# ---------------------------------------------------------------------------------------------------
# Surveillance metrics / signal rules -- PMS-FR-018/019/020. See module docstring: persisted via Vault,
# not a dedicated table.
# ---------------------------------------------------------------------------------------------------


class CalculateSurveillanceMetricCommand(CommandEnvelope):
    metric_definition_version: str
    scope: dict
    period: dict
    source_cutoff: datetime
    exposure_denominator: dict | None = None
    denominator_uncertain: bool = False


async def calculate_surveillance_metric(
    session: AsyncSession, cmd: CalculateSurveillanceMetricCommand, actor_user_id: uuid.UUID
) -> dict:
    """PMS-FR-018/019: population/time-window scoped count over `safety_case`, frozen as an immutable
    Vault release keyed by (metric_definition_version, scope, period) so a later replay of the same key
    reproduces the same stored snapshot rather than recomputing against since-changed data -- this is what
    satisfies "historical metric formula version remains reproducible".
    """
    site_id = cmd.scope.get("site_id")
    stmt = select(SafetyCase)
    if site_id:
        stmt = stmt.where(SafetyCase.site_id == uuid.UUID(site_id))
    period_start = cmd.period.get("start")
    period_end = cmd.period.get("end")
    if period_start:
        stmt = stmt.where(SafetyCase.system_ingested_at >= period_start)
    if period_end:
        stmt = stmt.where(SafetyCase.system_ingested_at <= period_end)
    numerator = len((await session.execute(stmt)).scalars().all())

    business_id = sha256_hex({"metric_definition_version": cmd.metric_definition_version, "scope": cmd.scope, "period": cmd.period})
    payload = {
        "metric_definition_version": cmd.metric_definition_version, "scope": cmd.scope, "period": cmd.period,
        "source_cutoff": cmd.source_cutoff.isoformat(), "numerator": numerator,
        "exposure_denominator": cmd.exposure_denominator, "denominator_uncertain": cmd.denominator_uncertain or cmd.exposure_denominator is None,
    }
    vault_object = await _release_or_reuse_vault_snapshot(
        session, object_type="postmarket_surveillance_metric_snapshot", business_id=business_id,
        canonical_payload=payload, actor_user_id=actor_user_id, site_id=uuid.UUID(site_id) if site_id else None,
        business_version_label=cmd.metric_definition_version,
    )
    return {"vault_object_id": str(vault_object.object_id), "internal_version": vault_object.internal_version, **payload}


class EvaluateSignalRulesCommand(CommandEnvelope):
    signal_rule_versions: list[str]
    case_scope: dict = {}


async def evaluate_signal_rules(session: AsyncSession, cmd: EvaluateSignalRulesCommand) -> list[dict]:
    """PMS-FR-020: "return triggers/evidence only" -- no owned entity, no side effect. This module has no
    generic statistical rules engine of its own; `app.modules.rules` evaluates numeric-limit rules against
    a single caller-supplied record, not a population trend, so it is not reused here. Recurrence is the
    one trigger this function can honestly compute without inventing a severity/frequency statistical
    model no baseline defines: 2+ non-duplicate cases sharing (site, source_record_type) in scope.
    """
    site_id = cmd.case_scope.get("site_id")
    stmt = select(SafetyCase).where(SafetyCase.canonical_case_id.is_(None))
    if site_id:
        stmt = stmt.where(SafetyCase.site_id == uuid.UUID(site_id))
    cases = (await session.execute(stmt)).scalars().all()
    by_source_type: dict[str, list[SafetyCase]] = {}
    for c in cases:
        by_source_type.setdefault(c.source_record_type, []).append(c)

    triggers = []
    for rule_version in cmd.signal_rule_versions:
        for source_type, group in by_source_type.items():
            if len(group) >= 2:
                triggers.append({
                    "rule_version": rule_version, "trigger_type": "RECURRENCE", "source_record_type": source_type,
                    "case_ids": [str(c.id) for c in group],
                })
    return triggers


# ---------------------------------------------------------------------------------------------------
# SafetySignal -- PMS-FR-021/022/023/024/025.
# ---------------------------------------------------------------------------------------------------


class OpenSafetySignalCommand(CommandEnvelope):
    site_id: uuid.UUID
    signal_code: str
    detection_source: str
    trigger_refs: list[dict]
    population_definition: dict
    case_ids_for_snapshot: list[uuid.UUID]
    rationale: str
    rule_version: str | None = None
    exposure_denominator: dict | None = None
    denominator_uncertain: bool = False
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def open_safety_signal(
    session: AsyncSession, cmd: OpenSafetySignalCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.detection_source not in SIGNAL_DETECTION_SOURCES:
        raise SignalScopeInvalidError("Unrecognized detection_source", allowed=list(SIGNAL_DETECTION_SOURCES))
    if not cmd.population_definition:
        raise SignalScopeInvalidError("population_definition must not be empty")
    dup_open = (
        await session.execute(
            select(SafetySignal).where(SafetySignal.site_id == cmd.site_id, SafetySignal.signal_code == cmd.signal_code)
        )
    ).scalar_one_or_none()
    if dup_open is not None:
        raise ValidationFailedError("A signal with this signal_code already exists at this site", existing_signal_id=str(dup_open.id))

    # PMS-FR-021: frozen case/evidence snapshot at open time.
    snapshot_cases = []
    for case_id in cmd.case_ids_for_snapshot:
        case = await session.get(SafetyCase, case_id)
        if case is None:
            raise NotFoundError(f"Safety case {case_id} not found for snapshot")
        snapshot_cases.append({
            "case_id": str(case.id), "version": case.version, "state": case.state,
            "constituent_classification": case.constituent_classification,
        })

    signature_id = await _resolve_signature(
        session, record_type="safety_signal", action="open", actor_user_id=actor_user_id, record_version=1,
        record_hash=sha256_hex({"signal_code": cmd.signal_code}), challenge_id=cmd.challenge_id,
        reauth_password=cmd.reauth_password,
    )

    signal = SafetySignal(
        site_id=cmd.site_id, signal_code=cmd.signal_code, detection_source=cmd.detection_source,
        rule_version=cmd.rule_version, trigger_refs=cmd.trigger_refs, population_definition=cmd.population_definition,
        exposure_denominator=cmd.exposure_denominator, denominator_uncertain=cmd.denominator_uncertain or cmd.exposure_denominator is None,
        case_snapshot={"cases": snapshot_cases}, rationale=cmd.rationale, owner_subject_id=actor_user_id,
        state="DETECTED", version=1,
    )
    session.add(signal)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="safety_signal",
        aggregate_id=signal.id, version=signal.version, action="Created", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=None, event_type="SafetySignalOpened",
        event_payload={"signal_id": str(signal.id), "signal_code": signal.signal_code},
        expected_version=None, command_type="OpenSafetySignal", signature_id=signature_id,
    )


class AssessSafetySignalCommand(CommandEnvelope):
    signal_id: uuid.UUID
    expected_version: int
    assessment: dict
    next_state: str
    recommended_actions: list[str] = []
    reason: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def assess_safety_signal(
    session: AsyncSession, cmd: AssessSafetySignalCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    signal = await session.get(SafetySignal, cmd.signal_id)
    if signal is None:
        raise NotFoundError("Safety signal not found")
    if signal.version != cmd.expected_version:
        raise StaleSafetyCaseVersionError("Safety signal version changed since this request was prepared", current_version=signal.version)
    if cmd.next_state not in SIGNAL_TRANSITIONS.get(signal.state, set()):
        raise InvalidTransitionError(f"Cannot move signal from {signal.state} to {cmd.next_state}")

    signature_id = await _resolve_signature(
        session, record_type="safety_signal", action="assess", actor_user_id=actor_user_id,
        record_version=signal.version, record_hash=_signal_hash(signal), challenge_id=cmd.challenge_id,
        reauth_password=cmd.reauth_password,
    )

    old_state = signal.state
    if signal.assessment is not None:
        signal.assessment_history = [*signal.assessment_history, {"version": signal.version, "assessment": signal.assessment}]
    signal.assessment = {**cmd.assessment, "recommended_actions": cmd.recommended_actions}
    signal.state = cmd.next_state
    if cmd.next_state == "CLOSED":
        signal.closed_at = datetime.now(timezone.utc)
    signal.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=signal.site_id, aggregate_type="safety_signal",
        aggregate_id=signal.id, version=signal.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.reason, old_state=old_state, event_type="SafetySignalAssessed",
        event_payload={"signal_id": str(signal.id), "state": signal.state},
        expected_version=cmd.expected_version, command_type="AssessSafetySignal", signature_id=signature_id,
    )


_ESCALATION_DISPATCH = {
    "CAPA": (capa_commands.CreateCapaCommand, capa_commands.create_capa),
    "CHANGE_CONTROL": (change_commands.CreateChangeCommand, change_commands.create_change),
    "RISK_REVIEW": (risk_commands.CreateRiskCommand, risk_commands.create_risk),
    "FIELD_ACTION": (field_action_commands.CreateFieldActionCommand, field_action_commands.create_field_action),
}


class EscalateSignalCommand(CommandEnvelope):
    signal_id: uuid.UUID
    expected_version: int
    target_module: str
    target_command: dict
    rationale: str
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def escalate_signal_to_qms_or_regulatory(
    session: AsyncSession, cmd: EscalateSignalCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    signal = await session.get(SafetySignal, cmd.signal_id)
    if signal is None:
        raise NotFoundError("Safety signal not found")
    if signal.version != cmd.expected_version:
        raise StaleSafetyCaseVersionError("Safety signal version changed since this request was prepared", current_version=signal.version)
    if cmd.target_module not in ESCALATION_TARGET_MODULES:
        raise ValidationFailedError("Unrecognized target_module", allowed=list(ESCALATION_TARGET_MODULES))
    if signal.state not in ("CONFIRMED", "ACTION", "ASSESSMENT"):
        raise InvalidTransitionError("A signal must be at least assessed before escalation", current_state=signal.state)
    if cmd.target_module == "REPORTABILITY_TRACK":
        # Document 59 (SPEC-PM-002) is not built yet in this pass -- see commands.py module docstring.
        raise ValidationFailedError("REPORTABILITY_TRACK escalation requires Document 59, not yet implemented in this deployment")

    signature_id = await _resolve_signature(
        session, record_type="safety_signal", action="escalate", actor_user_id=actor_user_id,
        record_version=signal.version, record_hash=_signal_hash(signal), challenge_id=cmd.challenge_id,
        reauth_password=cmd.reauth_password,
    )

    command_cls, handler = _ESCALATION_DISPATCH[cmd.target_module]
    target_payload = {**cmd.target_command, "idempotency_key": str(uuid.uuid4())}
    if cmd.target_module == "CAPA":
        # Only CreateCapaCommand carries a source_type/id/version cross-reference field set; the other
        # three targets' schemas don't (checked against their actual Pydantic fields) -- the reverse link
        # (signal -> target aggregate) is preserved on escalation_links below regardless of target type.
        # CAPA_SOURCE_TYPES (Document 27's own 11-value taxonomy) has no "postmarket signal" entry --
        # "trend" is the closest existing value (a safety signal IS a trend/cluster detection) rather than
        # inventing a new source type in a module WP-09 does not own. Same reasoning applies to
        # FIELD_ACTION's trigger_ref.source_type, which the caller's own target_command must supply.
        target_payload.setdefault("source_type", "trend")
        target_payload.setdefault("source_id", signal.id)
        target_payload.setdefault("source_version", signal.version)
    # CreateChangeCommand is the only target whose own schema happens to have a same-named `reason`
    # field (the change's own reason, not a Mutation Gateway audit reason) -- the caller's target_command
    # supplies whatever each target's own schema actually requires; nothing is injected uniformly here.
    target_cmd = command_cls.model_validate(target_payload)
    target_receipt = await handler(session, target_cmd, actor_user_id)

    old_state = signal.state
    signal.escalation_links = [
        *signal.escalation_links,
        {"target_module": cmd.target_module, "target_aggregate_id": str(target_receipt.aggregate_id), "rationale": cmd.rationale},
    ]
    signal.version += 1
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=signal.site_id, aggregate_type="safety_signal",
        aggregate_id=signal.id, version=signal.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rationale, old_state=old_state, event_type="SafetySignalEscalated",
        event_payload={"signal_id": str(signal.id), "target_module": cmd.target_module, "target_aggregate_id": str(target_receipt.aggregate_id)},
        expected_version=cmd.expected_version, command_type="EscalateSignal", signature_id=signature_id,
    )


class BuildPeriodicSafetyDatasetCommand(CommandEnvelope):
    application_id: str
    interval_start: datetime
    interval_end: datetime
    report_type: str
    cutoff: datetime
    site_id: uuid.UUID | None = None


async def build_periodic_safety_dataset(
    session: AsyncSession, cmd: BuildPeriodicSafetyDatasetCommand, actor_user_id: uuid.UUID
) -> dict:
    """PMS-FR-032: immutable periodic dataset of qualifying cases/signals/actions, persisted via Vault --
    see module docstring."""
    stmt = select(SafetyCase).where(
        SafetyCase.system_ingested_at >= cmd.interval_start, SafetyCase.system_ingested_at <= cmd.interval_end,
    )
    if cmd.site_id:
        stmt = stmt.where(SafetyCase.site_id == cmd.site_id)
    cases = (await session.execute(stmt)).scalars().all()

    business_id = f"{cmd.application_id}:{cmd.report_type}:{cmd.interval_start.isoformat()}:{cmd.interval_end.isoformat()}"
    payload = {
        "application_id": cmd.application_id, "report_type": cmd.report_type,
        "interval_start": cmd.interval_start.isoformat(), "interval_end": cmd.interval_end.isoformat(),
        "cutoff": cmd.cutoff.isoformat(),
        "case_refs": [{"case_id": str(c.id), "version": c.version, "safety_case_number": c.safety_case_number} for c in cases],
    }
    vault_object = await _release_or_reuse_vault_snapshot(
        session, object_type="postmarket_periodic_safety_dataset", business_id=business_id, canonical_payload=payload,
        actor_user_id=actor_user_id, site_id=cmd.site_id, business_version_label=cmd.report_type,
    )
    return {"vault_object_id": str(vault_object.object_id), "internal_version": vault_object.internal_version, **payload}


async def get_postmarket_dashboard(session: AsyncSession, site_id: uuid.UUID | None) -> dict:
    """PMS-FR-033: serious cases, reportability-pending, signal aging, follow-up backlog -- read-only,
    never a regulated decision source (AG-11)."""
    case_stmt = select(SafetyCase)
    signal_stmt = select(SafetySignal)
    if site_id:
        case_stmt = case_stmt.where(SafetyCase.site_id == site_id)
        signal_stmt = signal_stmt.where(SafetySignal.site_id == site_id)
    cases = (await session.execute(case_stmt)).scalars().all()
    signals = (await session.execute(signal_stmt)).scalars().all()
    now = datetime.now(timezone.utc)
    return {
        "open_cases": sum(1 for c in cases if c.state != "CLOSED_FOR_SURVEILLANCE"),
        "reportability_pending": sum(1 for c in cases if c.reportability_referral_required),
        "followup_backlog": sum(1 for c in cases if c.reassessment_required),
        "unknown_identity_queue": sum(1 for c in cases if c.identity_resolution_state == "UNKNOWN_QUEUE"),
        "open_signals": sum(1 for s in signals if s.state != "CLOSED"),
        "signal_aging_days_max": max(
            [(now - (s.opened_at if s.opened_at.tzinfo else s.opened_at.replace(tzinfo=timezone.utc))).days for s in signals if s.state != "CLOSED"],
            default=0,
        ),
    }
