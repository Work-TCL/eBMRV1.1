"""Document 54 (SPEC-DDCP-001, PFS-FR-001..030) Mutation Gateway command handlers.

Every action here resolves `signature_required=False` from Document 106 policy (no real Document 106 row
exists for any WP-08 action yet -- SG-148, same class of gap as SG-119/SG-122) but is still RBAC-gated at
the router layer through `evaluate_policy`, the same precedent used everywhere else in this codebase.

Two cross-cutting scope decisions, documented once here rather than repeated at every call site:

1. **No `ebmr.batches -> ddcp_profile_version` linkage column exists** (Document 112's schema doesn't add
   one, and this module does not modify `ebmr.batches`, which it does not own -- AG-05/AG-06). Every
   function that needs "the profile for this batch" takes `profile_version_id` as an explicit caller-
   supplied input instead of deriving it. See SG-148.
2. **Fill-weight IPC (PFS-FR-011) has no dedicated entity** in Document 112's approved 9-table schema, and
   routing every in-process fill-weight check through the full QC Sample -> TestOrder -> TestRun -> Result
   pipeline (`app.modules.qc.commands`) would require a sample/test-order per weight reading -- an
   operationally heavy chain no source document actually describes for a high-frequency in-process check.
   `record_fill_ipc_result()` instead evaluates the caller-supplied released rule directly through the
   rules engine (`rules.commands.evaluate_rule`) the same way `qc.commands._evaluate_acceptance` does
   internally, without duplicating a QC table (`rules.RuleEvaluation` is the durable evidence record, not
   a new DDCP-owned copy). See SG-148.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.batch_execution.models import Batch, BatchStep
from app.modules.ddcp.models import (
    ASSEMBLY_STEPS,
    CONSTITUENT_TYPES,
    INJECTABLE_SUBTYPES,
    RELEASE_CHECKPOINT_CODES,
    BatchEvidenceManifest,
    ConstituentHandoff,
    ConstituentRequirement,
    DdcpProfileVersion,
    DdcpReleaseCheckpoint,
    DdcpStepMapping,
    DeviceAssemblyRecord,
    DeviceFunctionalTestLink,
    FillOperation,
    ProductionCountLedger,
)
from app.modules.equipment import cleaning_commands, em_commands, sterilization_commands
from app.modules.equipment import commands as equipment_commands
from app.modules.equipment.models import EquipmentAsset
from app.modules.iam.models import User
from app.modules.material.models import MaterialLot
from app.modules.product_master.models import ProductVersion
from app.modules.recipe_master.models import RecipeStep, RecipeVersion
from app.modules.qms.change_models import ChangeAffectedObject, ChangeControl
from app.modules.qms.models import DeviationRecord
from app.modules.rules import commands as rules_commands
from app.modules.rules import service as rules_service
from app.modules.rules.models import RuleEvaluation
from app.modules.signature import service as signature_service
from app.mutation.errors import (
    BulkHoldTimeExceededError,
    BulkNotReleasedError,
    ConstituentAttributeMissingError,
    ConstituentTypeMismatchError,
    DuplicateSourceEventError,
    FillStageIncompleteError,
    InvalidTransitionError,
    LineNotReadyError,
    MissingSignatureError,
    NotFoundError,
    PfsProfileNotEffectiveError,
    PfsReconciliationFailedError,
    PrimaryComponentNotReleasedError,
    ProfileReleaseBlockedError,
    ProfileSchemaInvalidError,
    ReworkRouteRequiredError,
    SodConflictError,
    StaleVersionError,
    SterileComponentIneligibleError,
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
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, site_id: uuid.UUID,
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


def _profile_hash(profile: DdcpProfileVersion) -> str:
    return sha256_hex({"id": str(profile.id), "version": profile.version, "state": profile.state})


async def _assert_product_version_for_profile(
    session: AsyncSession, *, product_version_id: uuid.UUID, site_id: uuid.UUID,
    expected_manufacturing_profile_code: str | None,
) -> ProductVersion:
    """SG-175 (product_version_id half, project-owner-directed 2026-09-08): every DDCP profile is now
    authored against a real, RELEASED Product Master version, closing the "no FK at all" gap found
    while writing the client demo guide's Product-family-vs-Product-Master comparison. Reused by every
    family's create-profile command (migration 0089 adds the column this checks).

    `expected_manufacturing_profile_code` is only enforced for the two families where Product Master's
    own 5-value `manufacturing_profile_code` vocabulary (Document 09, `SUPPORTED_MANUFACTURING_PROFILES`)
    names the family unambiguously -- `injectable_ddcp` -> PFS, `inhalation_ddcp` -> Inhalation. Neither
    Autoinjector nor Coated device has a corresponding value in that vocabulary at all, so callers for
    those two families pass `expected_manufacturing_profile_code=None` and only the
    existence/released/site checks apply; guessing a mapping for those two would be exactly the kind of
    regulated-record-authority decision CLAUDE.md #4 reserves for a human -- left open as SG-175's
    residual half rather than invented here.
    """
    product_version = await session.get(ProductVersion, product_version_id)
    if product_version is None:
        raise NotFoundError("Product version not found")
    if product_version.lifecycle_state != "released":
        raise ValidationFailedError(
            "A DDCP profile can only be authored against a released product version",
            current_state=product_version.lifecycle_state,
        )
    if product_version.site_id != site_id:
        raise ValidationFailedError("Product version belongs to a different site")
    if expected_manufacturing_profile_code is not None and product_version.manufacturing_profile_code != expected_manufacturing_profile_code:
        raise ProfileSchemaInvalidError(
            "Product version's manufacturing profile does not match this DDCP family",
            expected=expected_manufacturing_profile_code, actual=product_version.manufacturing_profile_code,
        )
    return product_version


# ---------------------------------------------------------------------------------------------------
# DdcpProfileVersion — PFS-FR-001/002/028/029.
# ---------------------------------------------------------------------------------------------------


class CreateInjectableProfileVersionCommand(CommandEnvelope):
    site_id: uuid.UUID
    profile_code: str
    product_version_id: uuid.UUID  # SG-175 -- must be a RELEASED product with manufacturing_profile_code="injectable_ddcp"
    subtype: str | None = None
    dosage_form: str | None = None
    presentation: str | None = None
    constituent_architecture: dict
    required_controls: dict
    release_checkpoint_set: dict = {"checkpoints": list(RELEASE_CHECKPOINT_CODES)}
    constituent_requirements: list[dict] = []  # [{constituent_type, component_role, required_state, ...}]


async def create_injectable_profile_version(
    session: AsyncSession, cmd: CreateInjectableProfileVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.subtype is not None and cmd.subtype not in INJECTABLE_SUBTYPES:
        raise ProfileSchemaInvalidError("Unrecognized subtype", allowed=list(INJECTABLE_SUBTYPES))
    for req in cmd.constituent_requirements:
        if req.get("constituent_type") not in CONSTITUENT_TYPES:
            raise ProfileSchemaInvalidError("Unrecognized constituent_type in constituent_requirements", allowed=list(CONSTITUENT_TYPES))
        if not req.get("component_role"):
            raise ProfileSchemaInvalidError("Every constituent_requirement needs a component_role")
    await _assert_product_version_for_profile(
        session, product_version_id=cmd.product_version_id, site_id=cmd.site_id,
        expected_manufacturing_profile_code="injectable_ddcp",
    )

    next_version = (
        await session.execute(
            select(func.max(DdcpProfileVersion.version)).where(
                DdcpProfileVersion.site_id == cmd.site_id, DdcpProfileVersion.profile_code == cmd.profile_code,
            )
        )
    ).scalar() or 0

    profile = DdcpProfileVersion(
        site_id=cmd.site_id, profile_code=cmd.profile_code, product_version_id=cmd.product_version_id,
        subtype=cmd.subtype, version=next_version + 1,
        state="DRAFT", dosage_form=cmd.dosage_form, presentation=cmd.presentation,
        constituent_architecture=cmd.constituent_architecture, required_controls=cmd.required_controls,
        release_checkpoint_set=cmd.release_checkpoint_set,
    )
    session.add(profile)
    await session.flush()

    for i, req in enumerate(cmd.constituent_requirements):
        session.add(ConstituentRequirement(
            site_id=cmd.site_id, ddcp_profile_version_id=profile.id, constituent_type=req["constituent_type"],
            component_role=req["component_role"], required_state=req.get("required_state", "RELEASED"),
            material_spec_reference=req.get("material_spec_reference"), attribute_requirements=req.get("attribute_requirements"),
            mandatory=req.get("mandatory", True), sequence_no=req.get("sequence_no", i),
        ))
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=cmd.site_id, aggregate_type="ddcp_profile_version",
        aggregate_id=profile.id, version=profile.version, action="Created", actor_user_id=actor_user_id, reason=None,
        old_state=None, event_type="InjectableProfileDraftCreated",
        event_payload={"id": str(profile.id), "profile_code": profile.profile_code, "version": profile.version},
        expected_version=None, command_type="CreateInjectableProfileVersion",
    )


async def _load_profile_for_update(session: AsyncSession, profile_id: uuid.UUID, expected_version: int) -> DdcpProfileVersion:
    result = await session.execute(select(DdcpProfileVersion).where(DdcpProfileVersion.id == profile_id).with_for_update())
    profile = result.scalar_one_or_none()
    if profile is None:
        raise NotFoundError("Injectable profile version not found")
    if profile.version != expected_version:
        raise StaleVersionError("Profile version was modified since it was read", expected_version=expected_version, current_version=profile.version)
    return profile


class ReleaseInjectableProfileVersionCommand(CommandEnvelope):
    profile_id: uuid.UUID
    expected_version: int
    change_ref: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def release_injectable_profile_version(
    session: AsyncSession, cmd: ReleaseInjectableProfileVersionCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """releaseInjectableProfileVersion() -- once RELEASED a profile version is immutable (enforced here,
    not a DB trigger, matching `recipe_master`/`product_master` release; `vault_object_id` stays NULL at
    this pass's depth, same precedent those two modules already set)."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    profile = await _load_profile_for_update(session, cmd.profile_id, cmd.expected_version)
    if profile.state != "DRAFT":
        raise InvalidTransitionError("Only a draft profile version can be released", current_state=profile.state)

    requirement_count = (
        await session.execute(
            select(func.count()).select_from(ConstituentRequirement).where(ConstituentRequirement.ddcp_profile_version_id == profile.id)
        )
    ).scalar()
    if not requirement_count:
        raise ProfileReleaseBlockedError("A profile version needs at least one constituent requirement before release")

    signature_id = await _resolve_signature(
        session, record_type="ddcp_profile_version", action="release", actor_user_id=actor_user_id,
        record_version=profile.version, record_hash=_profile_hash(profile),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = profile.state
    # Superseding the previously-released version of this profile_code, if any (PFS-FR-029 lifecycle).
    previous = (
        await session.execute(
            select(DdcpProfileVersion).where(
                DdcpProfileVersion.site_id == profile.site_id, DdcpProfileVersion.profile_code == profile.profile_code,
                DdcpProfileVersion.state == "RELEASED",
            )
        )
    ).scalar_one_or_none()
    if previous is not None:
        previous.state = "SUPERSEDED"

    profile.state = "RELEASED"
    profile.effective_from = datetime.now(timezone.utc)
    profile.released_by = actor_user_id
    profile.release_signature_id = signature_id

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=profile.site_id, aggregate_type="ddcp_profile_version",
        aggregate_id=profile.id, version=profile.version, action="Released", actor_user_id=actor_user_id,
        reason=cmd.change_ref, old_state=old_state, event_type="InjectableProfileReleased",
        event_payload={"id": str(profile.id), "profile_code": profile.profile_code, "version": profile.version},
        expected_version=cmd.expected_version, command_type="ReleaseInjectableProfileVersion", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------------------------------
# ConstituentHandoff — PFS-FR-003/004, §8. SG-148: `from_constituent` uses the CONSTITUENT_TYPES
# vocabulary (DRUG|BIOLOGIC|DEVICE|PACKAGING|LABEL); `to_constituent` uses the receiving
# `constituent_requirement.component_role` vocabulary -- an ordinary engineering decision to join these
# two tables (neither source document pins the exact join key), not a regulated-behaviour guess.
# ---------------------------------------------------------------------------------------------------


class RecordConstituentHandoffCommand(CommandEnvelope):
    batch_id: uuid.UUID
    from_constituent: str
    to_constituent: str
    source_batch_reference: dict  # {"batch_id": ...} or {"lot_id": ...}
    attributes: dict = {}


async def record_constituent_handoff(
    session: AsyncSession, cmd: RecordConstituentHandoffCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.from_constituent not in CONSTITUENT_TYPES:
        raise ValidationFailedError("Unrecognized from_constituent", allowed=list(CONSTITUENT_TYPES))

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    # Document 112's JSONB-expression uniqueness enforced in application code -- see models.py docstring.
    source_key = cmd.source_batch_reference.get("batch_id") or cmd.source_batch_reference.get("lot_id")
    duplicate = (
        await session.execute(
            select(ConstituentHandoff).where(
                ConstituentHandoff.batch_id == cmd.batch_id, ConstituentHandoff.from_constituent == cmd.from_constituent,
                ConstituentHandoff.to_constituent == cmd.to_constituent,
            )
        )
    ).scalars().all()
    for existing_handoff in duplicate:
        existing_key = existing_handoff.source_batch_reference.get("batch_id") or existing_handoff.source_batch_reference.get("lot_id")
        if existing_key == source_key and existing_handoff.state != "REJECTED":
            raise ValidationFailedError(
                "A handoff for this batch/constituent/source already exists", existing_handoff_id=str(existing_handoff.id),
            )

    handoff = ConstituentHandoff(
        site_id=batch.site_id, batch_id=cmd.batch_id, from_constituent=cmd.from_constituent,
        to_constituent=cmd.to_constituent, source_batch_reference=cmd.source_batch_reference,
        attributes=cmd.attributes, state="PENDING", version=1,
    )
    session.add(handoff)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="constituent_handoff",
        aggregate_id=handoff.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="ConstituentHandoffRecorded", event_payload={"id": str(handoff.id), "batch_id": str(cmd.batch_id)},
        expected_version=None, command_type="RecordConstituentHandoff",
    )


class DecideConstituentHandoffCommand(CommandEnvelope):
    handoff_id: uuid.UUID
    expected_version: int
    decision: str  # ACCEPTED | REJECTED
    rejection_reason: str | None = None
    # PFS-FR-005/016/028: optional, backward compatible (existing callers that omit these get exactly the
    # PFS-FR-003/004 release check that already existed). When a caller supplies profile_version_id, the
    # matching ConstituentRequirement (by component_role == to_constituent) is looked up and three checks
    # apply only when that requirement actually declares something to check -- "according to configured
    # component route" / "when defined" language in Document 54, not an unconditional gate. No requirement
    # row for this component_role -> nothing to verify, not guessed.
    profile_version_id: uuid.UUID | None = None
    sterilization_use_id: uuid.UUID | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def decide_constituent_handoff(
    session: AsyncSession, cmd: DecideConstituentHandoffCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """PFS-FR-003/004: "Require released lots" is enforced here, not merely captured. PFS-FR-003 reads
    literally as "released bulk drug/biologic batch reference" -- but this platform has no capability
    anywhere to create/release a batch record for externally-supplied bulk drug substance; every real
    deployment (including this one, Document 18/19/20) receives it exactly like any other raw material:
    Supplier -> Material Receipt -> Material Lot, QC-released the same way as PFS-FR-004's primary
    components. SG-179 (2026-09-08, project-owner-directed, hit live while demoing): a DRUG/BIOLOGIC
    source now resolves against *either* a `ebmr.gxp_batch` row in state `released` (if a caller ever
    supplies `batch_id` -- kept for the literal PFS-FR-003 wording, though nothing in this codebase can
    produce one yet) *or* a `materials.material_lots` row in status `released` (the path every real
    handoff actually uses today, matching PFS-FR-004's own component check exactly). Any other
    constituent type still only ever resolves to a released material lot. Both cases fail closed
    (BULK_NOT_RELEASED / PRIMARY_COMPONENT_NOT_RELEASED) if the reference is missing or not released.

    PFS-FR-005/016/028 (added this pass, optional `profile_version_id`): component preparation status
    (STERILIZED/DEPYROGENATED/READY_TO_USE), declared attribute presence and constituent_type equivalence
    are all checked against the profile's own `ConstituentRequirement` row for this component_role when
    one is supplied -- see SG-148 for why `profile_version_id` is caller-supplied rather than derived (no
    `ebmr.batches -> ddcp_profile_version` linkage column exists)."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if cmd.decision not in ("ACCEPTED", "REJECTED"):
        raise ValidationFailedError("decision must be ACCEPTED or REJECTED")
    if cmd.decision == "REJECTED" and not cmd.rejection_reason:
        raise ValidationFailedError("rejection_reason is required to reject a constituent handoff")

    result = await session.execute(select(ConstituentHandoff).where(ConstituentHandoff.id == cmd.handoff_id).with_for_update())
    handoff = result.scalar_one_or_none()
    if handoff is None:
        raise NotFoundError("Constituent handoff not found")
    if handoff.version != cmd.expected_version:
        raise StaleVersionError("Handoff was modified since it was read", expected_version=cmd.expected_version, current_version=handoff.version)
    if handoff.state != "PENDING":
        raise InvalidTransitionError("Only a pending handoff can be decided", current_state=handoff.state)

    if cmd.decision == "ACCEPTED":
        is_bulk = handoff.from_constituent in ("DRUG", "BIOLOGIC")
        # source_batch_reference is caller-supplied free-form JSON at handoff-creation time (record_
        # constituent_handoff never validates its shape) -- a non-UUID id typed there previously reached
        # uuid.UUID() unguarded and raised a bare ValueError, caught only by main.py's catch-all
        # unhandled_exception_handler as an opaque SYSTEM_FAULT 500 -- this is a bad *input*, not a
        # system fault, so it gets its own clear, actionable VALIDATION_FAILED instead.
        source_batch_id = handoff.source_batch_reference.get("batch_id")
        source_lot_id = handoff.source_batch_reference.get("lot_id")

        if source_batch_id:
            if not is_bulk:
                raise ValidationFailedError(
                    "batch_id is only a valid source reference for a DRUG/BIOLOGIC handoff; this "
                    "constituent type requires lot_id", from_constituent=handoff.from_constituent
                )
            try:
                source_uuid = uuid.UUID(source_batch_id)
            except (ValueError, AttributeError, TypeError):
                raise ValidationFailedError(
                    "source_batch_reference.batch_id is not a valid UUID", batch_id=source_batch_id
                )
            source = await session.get(Batch, source_uuid)
            if source is None or source.state != "released":
                raise BulkNotReleasedError("Referenced bulk drug/biologic batch is not released", source_batch_id=source_batch_id)
        elif source_lot_id:
            try:
                source_lot_uuid = uuid.UUID(source_lot_id)
            except (ValueError, AttributeError, TypeError):
                raise ValidationFailedError(
                    "source_batch_reference.lot_id is not a valid UUID", lot_id=source_lot_id
                )
            source_lot = await session.get(MaterialLot, source_lot_uuid)
            if source_lot is None or source_lot.status != "released":
                error_cls = BulkNotReleasedError if is_bulk else PrimaryComponentNotReleasedError
                raise error_cls(
                    "Referenced bulk drug/biologic material lot is not released"
                    if is_bulk else "Referenced primary component lot is not released",
                    source_lot_id=source_lot_id,
                )
        else:
            raise ValidationFailedError(
                "source_batch_reference must include batch_id or lot_id", source_batch_reference=handoff.source_batch_reference
            )

        if cmd.profile_version_id is not None:
            requirement = (
                await session.execute(
                    select(ConstituentRequirement).where(
                        ConstituentRequirement.ddcp_profile_version_id == cmd.profile_version_id,
                        ConstituentRequirement.component_role == handoff.to_constituent,
                    )
                )
            ).scalar_one_or_none()
            if requirement is not None:
                # PFS-FR-028: no implicit DRUG/BIOLOGIC (or any other) equivalency against the profile's
                # declared constituent_type for this role.
                if requirement.constituent_type != handoff.from_constituent:
                    raise ConstituentTypeMismatchError(
                        "Handoff constituent_type does not match the profile's declared requirement for this "
                        "component_role -- no implicit equivalency (PFS-FR-028)",
                        required_constituent_type=requirement.constituent_type, provided_constituent_type=handoff.from_constituent,
                    )

                # PFS-FR-005: component preparation status, checked via Document 42's real sterilization
                # tracking (the same cross-module reference `complete_filling_stage` already uses for
                # PFS-FR-008's filter check) rather than trusting an unverified free-text attribute.
                if requirement.required_state in ("STERILIZED", "DEPYROGENATED", "READY_TO_USE"):
                    if cmd.sterilization_use_id is None:
                        raise SterileComponentIneligibleError(
                            "Component preparation status could not be verified: profile requires "
                            f"{requirement.required_state} but no sterilization/depyrogenation reference was supplied",
                            required_state=requirement.required_state,
                        )
                    prep_status = await sterilization_commands.get_item_status(session, cmd.sterilization_use_id)
                    prep_ready = prep_status.get("sterile_status") in (None, "eligible") and prep_status.get("state") in (None, "completed")
                    if not prep_ready:
                        raise SterileComponentIneligibleError(
                            "Referenced component preparation is not in a completed/eligible state",
                            required_state=requirement.required_state, prep_status=prep_status,
                        )
                    handoff.attributes = {**(handoff.attributes or {}), "component_prep_status_reference": prep_status}

                # PFS-FR-016: presence-only check against the profile's declared attribute keys -- no
                # numeric tolerance comparison, since no baseline exists anywhere for silicone/tungsten/
                # particulate acceptance ranges (that would be guessing a regulated limit, not supporting
                # a "when defined" attribute set).
                if requirement.attribute_requirements:
                    missing = [k for k in requirement.attribute_requirements if k not in (handoff.attributes or {})]
                    if missing:
                        raise ConstituentAttributeMissingError(
                            "Handoff is missing attribute(s) the profile's constituent requirement declares",
                            missing_attributes=missing, component_role=handoff.to_constituent,
                        )

    signature_id = await _resolve_signature(
        session, record_type="constituent_handoff", action="decide", actor_user_id=actor_user_id,
        record_version=handoff.version, record_hash=sha256_hex({"id": str(handoff.id), "state": handoff.state}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = handoff.state
    handoff.state = cmd.decision
    handoff.accepted_by = actor_user_id
    handoff.acceptance_signature_id = signature_id
    handoff.accepted_at = datetime.now(timezone.utc)
    handoff.rejection_reason = cmd.rejection_reason
    handoff.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=handoff.site_id, aggregate_type="constituent_handoff",
        aggregate_id=handoff.id, version=handoff.version, action="Changed", actor_user_id=actor_user_id,
        reason=cmd.rejection_reason, old_state=old_state, event_type="ConstituentHandoffDecided",
        event_payload={"id": str(handoff.id), "state": handoff.state}, expected_version=cmd.expected_version,
        command_type="DecideConstituentHandoff", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------------------------------
# Readiness composition — PFS-FR-006/007/008. Reuses the exact cross-module read functions
# `equipment.aseptic_commands._compute_readiness` already composes for the same purpose (line/EM/
# equipment/sterile-item readiness); PFS-adds the constituent-handoff completeness check on top.
# ---------------------------------------------------------------------------------------------------


async def evaluate_injectable_batch_readiness(
    session: AsyncSession, *, batch_id: uuid.UUID, profile_version_id: uuid.UUID,
    line_id: uuid.UUID | None = None, filler_equipment_id: uuid.UUID | None = None,
) -> dict:
    blockers: list[dict] = []

    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")
    if batch.state not in ("issued", "in_execution"):
        blockers.append({"code": "LINE_NOT_READY", "message": f"Batch status is {batch.state}, expected issued/in_execution"})

    profile = await session.get(DdcpProfileVersion, profile_version_id)
    if profile is None:
        raise NotFoundError("Injectable profile version not found")
    if profile.state != "RELEASED":
        blockers.append({"code": "PFS_PROFILE_NOT_EFFECTIVE", "message": f"Profile state is {profile.state}, expected RELEASED"})

    requirements = (
        await session.execute(
            select(ConstituentRequirement).where(ConstituentRequirement.ddcp_profile_version_id == profile_version_id, ConstituentRequirement.mandatory.is_(True))
        )
    ).scalars().all()
    handoffs = (await session.execute(select(ConstituentHandoff).where(ConstituentHandoff.batch_id == batch_id))).scalars().all()
    accepted = {(h.from_constituent, h.to_constituent) for h in handoffs if h.state == "ACCEPTED"}
    for req in requirements:
        if (req.constituent_type, req.component_role) not in accepted:
            code = "BULK_NOT_RELEASED" if req.constituent_type in ("DRUG", "BIOLOGIC") else "PRIMARY_COMPONENT_NOT_RELEASED"
            blockers.append({"code": code, "message": f"No accepted handoff for {req.constituent_type}/{req.component_role}"})

    em_readiness = line_clearance = None
    if line_id is not None:
        em_readiness = await em_commands.get_area_readiness(session, line_id)
        if not em_readiness["ready"]:
            blockers.append({"code": "LINE_NOT_READY", "message": f"EM area status is {em_readiness['status']}"})
        line_clearance = await cleaning_commands.get_area_line_clearance_status(session, line_id)
        if not line_clearance["cleared"]:
            blockers.append({"code": "LINE_NOT_READY", "message": f"Line clearance state is {line_clearance['state']}"})

    equipment_check = None
    if filler_equipment_id is not None:
        equipment_check = await equipment_commands.get_eligibility(session, filler_equipment_id)
        if not equipment_check["eligible"]:
            blockers.append({"code": "LINE_NOT_READY", "message": "Filler equipment is not eligible", "reasons": equipment_check["reasons"]})

    return {
        "batch_id": str(batch_id), "profile_version_id": str(profile_version_id), "ready": not blockers,
        "blockers": blockers, "em_readiness": em_readiness, "line_clearance": line_clearance, "equipment_check": equipment_check,
    }


# ---------------------------------------------------------------------------------------------------
# FillOperation — PFS-FR-006..011.
# ---------------------------------------------------------------------------------------------------


class StartFillingStageCommand(CommandEnvelope):
    batch_id: uuid.UUID
    profile_version_id: uuid.UUID
    line_id: uuid.UUID
    filler_equipment_id: uuid.UUID
    fill_program_id: str
    fill_program_version: str
    product_contact_path: dict
    target_fill: str  # decimal-as-string, AG-15/DATA-FR-019
    target_fill_uom: str
    cycle_group: str | None = None
    # PFS-FR-007: "block when released limits exceeded" names a limit this pass has no authority to
    # invent (no bulk compounding-to-filtration hold-time baseline exists anywhere in Documents 106-115).
    # Same SG-148 pattern PFS-FR-011 already uses: the caller supplies a released Rule id (authored via
    # the rules module, carrying whatever limit the customer's own control strategy actually requires)
    # and this evaluates elapsed hold time through it, exactly like fill-weight IPC. Optional -- omitting
    # it is unchanged prior behaviour, no hold-time check at all.
    bulk_hold_limit_rule_id: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def _resolve_uom_id(session: AsyncSession, uom: str | None) -> uuid.UUID | None:
    if not uom:
        return None
    try:
        resolved = await rules_service.resolve_uom(session, uom)
    except Exception:  # noqa: BLE001 -- UomUnknownError, same "never blocks the write" precedent as material/commands.py
        return None
    return resolved.uom_id


async def start_filling_stage(
    session: AsyncSession, cmd: StartFillingStageCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    readiness = await evaluate_injectable_batch_readiness(
        session, batch_id=cmd.batch_id, profile_version_id=cmd.profile_version_id,
        line_id=cmd.line_id, filler_equipment_id=cmd.filler_equipment_id,
    )
    if not readiness["ready"]:
        first = readiness["blockers"][0]
        if first["code"] == "PFS_PROFILE_NOT_EFFECTIVE":
            raise PfsProfileNotEffectiveError(first["message"])
        if first["code"] in ("BULK_NOT_RELEASED",):
            raise BulkNotReleasedError(first["message"], blockers=readiness["blockers"])
        if first["code"] == "PRIMARY_COMPONENT_NOT_RELEASED":
            raise PrimaryComponentNotReleasedError(first["message"], blockers=readiness["blockers"])
        raise LineNotReadyError(first["message"], blockers=readiness["blockers"])

    active = (
        await session.execute(
            select(FillOperation).where(FillOperation.batch_id == cmd.batch_id, FillOperation.state.in_(("SETUP", "EXECUTION", "HOLD")))
        )
    ).scalar_one_or_none()
    if active is not None:
        raise InvalidTransitionError("Batch already has an active filling stage", existing_fill_operation_id=str(active.id))

    batch = await session.get(Batch, cmd.batch_id)
    fill_start_time = datetime.now(timezone.utc)

    if cmd.bulk_hold_limit_rule_id:
        bulk_handoff = (
            await session.execute(
                select(ConstituentHandoff)
                .where(
                    ConstituentHandoff.batch_id == cmd.batch_id, ConstituentHandoff.from_constituent.in_(("DRUG", "BIOLOGIC")),
                    ConstituentHandoff.state == "ACCEPTED",
                )
                .order_by(ConstituentHandoff.accepted_at.desc())
            )
        ).scalars().first()
        if bulk_handoff is not None and bulk_handoff.accepted_at is not None:
            elapsed_hours = Decimal((fill_start_time - bulk_handoff.accepted_at).total_seconds()) / Decimal(3600)
            eval_receipt = await rules_commands.evaluate_rule(
                session,
                rules_commands.EvaluateRuleCommand(
                    idempotency_key=f"{cmd.idempotency_key}:hold-time-eval", rule_id=cmd.bulk_hold_limit_rule_id,
                    inputs={"elapsed_hours": str(elapsed_hours)}, aggregate_type="constituent_handoff",
                    aggregate_id=bulk_handoff.id, aggregate_version=bulk_handoff.version,
                ),
                actor_user_id,
            )
            hold_evaluation = await session.get(RuleEvaluation, eval_receipt.aggregate_id)
            if hold_evaluation is not None and hold_evaluation.outcome == "FAIL":
                raise BulkHoldTimeExceededError(
                    "Bulk compounding-to-filling hold time exceeds the released limit",
                    elapsed_hours=str(elapsed_hours), handoff_id=str(bulk_handoff.id),
                    rule_evaluation_id=str(eval_receipt.aggregate_id),
                )

    signature_id = await _resolve_signature(
        session, record_type="fill_operation", action="start", actor_user_id=actor_user_id,
        record_version=0, record_hash=sha256_hex({"batch_id": str(cmd.batch_id)}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    target_fill = Decimal(cmd.target_fill)
    fill_op = FillOperation(
        site_id=batch.site_id, batch_id=cmd.batch_id, line_id=cmd.line_id, filler_equipment_id=cmd.filler_equipment_id,
        fill_program_id=cmd.fill_program_id, fill_program_version=cmd.fill_program_version,
        product_contact_path=cmd.product_contact_path, target_fill=target_fill, target_fill_uom=cmd.target_fill_uom,
        target_fill_uom_id=await _resolve_uom_id(session, cmd.target_fill_uom), cycle_group=cmd.cycle_group,
        started_at=fill_start_time, line_readiness_reference=readiness, state="EXECUTION", version=1,
    )
    session.add(fill_op)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="fill_operation",
        aggregate_id=fill_op.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="PFSFillingStarted", event_payload={"id": str(fill_op.id), "batch_id": str(cmd.batch_id)},
        expected_version=None, command_type="StartFillingStage", signature_id=signature_id,
    )


async def _load_fill_operation_for_update(session: AsyncSession, fill_operation_id: uuid.UUID, expected_version: int) -> FillOperation:
    result = await session.execute(select(FillOperation).where(FillOperation.id == fill_operation_id).with_for_update())
    fill_op = result.scalar_one_or_none()
    if fill_op is None:
        raise NotFoundError("Fill operation not found")
    if fill_op.version != expected_version:
        raise StaleVersionError("Fill operation was modified since it was read", expected_version=expected_version, current_version=fill_op.version)
    return fill_op


class RecordFillIpcResultCommand(CommandEnvelope):
    fill_operation_id: uuid.UUID
    expected_version: int
    sample_id: str
    actual_value: str  # decimal-as-string
    uom: str
    method: str | None = None
    source: str = "MANUAL"
    acceptance_rule_id: str


async def record_fill_ipc_result(
    session: AsyncSession, cmd: RecordFillIpcResultCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """recordFillIPCResult() -- SG-148 (module docstring): evaluated via the rules engine directly, not
    the full QC sample/test-order pipeline. Never raises FILL_IPC_OOS itself (recording a valid
    measurement is not a rejected action, same posture as `qc.commands.record_result` never raising on an
    'oos' outcome) -- an OOS result holds the fill operation (`requires_deviation=True`), and
    `complete_filling_stage()` is what actually refuses to proceed while that hold is open."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    fill_op = await _load_fill_operation_for_update(session, cmd.fill_operation_id, cmd.expected_version)
    if fill_op.state not in ("EXECUTION", "HOLD"):
        raise InvalidTransitionError("Fill IPC can only be recorded while a fill operation is executing", current_state=fill_op.state)

    await rules_service.get_effective_released_rule(session, cmd.acceptance_rule_id)
    inputs = {"value": cmd.actual_value, "target": str(fill_op.target_fill)}
    eval_receipt = await rules_commands.evaluate_rule(
        session,
        rules_commands.EvaluateRuleCommand(
            idempotency_key=f"{cmd.idempotency_key}:rule-eval", rule_id=cmd.acceptance_rule_id, inputs=inputs,
            aggregate_type="fill_operation", aggregate_id=fill_op.id, aggregate_version=fill_op.version,
        ),
        actor_user_id,
    )
    evaluation = await session.get(RuleEvaluation, eval_receipt.aggregate_id)
    outcome = evaluation.outcome if evaluation else "ERROR"

    old_state = fill_op.state
    if outcome == "FAIL":
        fill_op.state = "HOLD"
        fill_op.requires_deviation = True
        event_type = "FillIPCOutOfSpec"
    else:
        event_type = "FillIPCRecorded"
    fill_op.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=fill_op.site_id, aggregate_type="fill_operation",
        aggregate_id=fill_op.id, version=fill_op.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_state=old_state, event_type=event_type,
        event_payload={"id": str(fill_op.id), "sample_id": cmd.sample_id, "outcome": outcome, "rule_evaluation_id": str(eval_receipt.aggregate_id)},
        expected_version=cmd.expected_version, command_type="RecordFillIPCResult",
    )


class RecordSyringeUnitOrCountCommand(CommandEnvelope):
    batch_id: uuid.UUID
    count_type: str
    source: str
    quantity: int
    uom: str = "EA"
    device_reference: dict | None = None
    reason_code: str | None = None
    occurred_at: datetime | None = None
    source_event_id: str | None = None


async def record_syringe_unit_or_count(
    session: AsyncSession, cmd: RecordSyringeUnitOrCountCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """recordSyringeUnitOrCount() -- PFS-FR-010/015/022. Append-only ledger row; `source_event_id` replay
    guard is independent of (and in addition to) the standard `idempotency_key` mechanism, matching the
    'count source retry duplicate' mandatory test -- a machine/edge source retrying the exact same physical
    count event must never double-count even under a different idempotency_key."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    if cmd.source_event_id:
        duplicate = (
            await session.execute(
                select(ProductionCountLedger).where(
                    ProductionCountLedger.batch_id == cmd.batch_id, ProductionCountLedger.source_event_id == cmd.source_event_id,
                )
            )
        ).scalar_one_or_none()
        if duplicate is not None:
            raise DuplicateSourceEventError("This source_event_id was already recorded for this batch", existing_id=str(duplicate.id))

    entry = ProductionCountLedger(
        site_id=batch.site_id, batch_id=cmd.batch_id, count_type=cmd.count_type, source=cmd.source, quantity=cmd.quantity,
        uom=cmd.uom, recorded_by=actor_user_id if cmd.source != "MACHINE" else None, device_reference=cmd.device_reference,
        reason_code=cmd.reason_code, occurred_at=cmd.occurred_at or datetime.now(timezone.utc), source_event_id=cmd.source_event_id,
    )
    session.add(entry)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="production_count_ledger",
        aggregate_id=entry.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="SyringeCountRecorded", event_payload={"id": str(entry.id), "count_type": entry.count_type, "quantity": entry.quantity},
        expected_version=None, command_type="RecordSyringeUnitOrCount",
    )


class RecordAsepticInterventionForFillCommand(CommandEnvelope):
    fill_operation_id: uuid.UUID
    expected_version: int
    intervention_type: str
    started_at: datetime | None = None
    ended_at: datetime | None = None
    impacted_unit_scope: dict | None = None
    source_aseptic_intervention_id: uuid.UUID | None = None


async def record_aseptic_intervention_for_fill(
    session: AsyncSession, cmd: RecordAsepticInterventionForFillCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """recordAsepticInterventionForFill() -- caller is the aseptic module (Document 40), linking an
    intervention it already owns into this fill operation's timeline for genealogy/unit-exclusion
    purposes; this function never creates a new `AsepticIntervention` row, only a reference here."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    fill_op = await _load_fill_operation_for_update(session, cmd.fill_operation_id, cmd.expected_version)
    if fill_op.state not in ("EXECUTION", "HOLD"):
        raise InvalidTransitionError("Interventions can only be linked while a fill operation is executing", current_state=fill_op.state)

    entry = {
        "intervention_type": cmd.intervention_type, "actor_user_id": str(actor_user_id),
        "started_at": cmd.started_at.isoformat() if cmd.started_at else None,
        "ended_at": cmd.ended_at.isoformat() if cmd.ended_at else None,
        "impacted_unit_scope": cmd.impacted_unit_scope,
        "source_aseptic_intervention_id": str(cmd.source_aseptic_intervention_id) if cmd.source_aseptic_intervention_id else None,
    }
    old_state = fill_op.state
    fill_op.interventions = {"items": [*((fill_op.interventions or {}).get("items", [])), entry]}
    fill_op.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=fill_op.site_id, aggregate_type="fill_operation",
        aggregate_id=fill_op.id, version=fill_op.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_state=old_state, event_type="PFSInterventionRecorded",
        event_payload={"id": str(fill_op.id), "intervention_type": cmd.intervention_type}, expected_version=cmd.expected_version,
        command_type="RecordAsepticInterventionForFill",
    )


class CompleteFillingStageCommand(CommandEnvelope):
    fill_operation_id: uuid.UUID
    expected_version: int
    machine_count_end: int | None = None
    filter_use_id: uuid.UUID | None = None
    reason: str | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def complete_filling_stage(
    session: AsyncSession, cmd: CompleteFillingStageCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """completeFillingStage() -- PFS-FR-024's reconciliation-completeness gate applied here: no numeric
    reconciliation tolerance is baselined anywhere in Documents 106-115 (same class of gap as SG-123/124),
    so this only checks *structural* completeness (at least one FILLED count exists, no unresolved
    IPC/aseptic hold) -- it never invents a numeric variance tolerance. See SG-148."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    fill_op = await _load_fill_operation_for_update(session, cmd.fill_operation_id, cmd.expected_version)
    if fill_op.state != "EXECUTION":
        if fill_op.state == "HOLD":
            raise FillStageIncompleteError("Fill operation has an unresolved hold (IPC OOS or aseptic intervention)")
        raise InvalidTransitionError("Only an executing fill operation can be completed", current_state=fill_op.state)

    filled_count = (
        await session.execute(
            select(func.coalesce(func.sum(ProductionCountLedger.quantity), 0)).where(
                ProductionCountLedger.batch_id == fill_op.batch_id, ProductionCountLedger.count_type == "FILLED",
            )
        )
    ).scalar()
    if not filled_count:
        raise PfsReconciliationFailedError("No FILLED units recorded for this batch -- reconciliation is not constructible")

    if cmd.filter_use_id is not None:
        filter_status = await sterilization_commands.get_item_status(session, cmd.filter_use_id)
        if filter_status.get("state") not in (None, "completed") and filter_status.get("sterile_status") not in (None, "eligible"):
            raise ValidationFailedError("Referenced sterile filter use is not in a completed/eligible state", filter_status=filter_status)
        # PFS-FR-008: bind, not just check -- persist the reference so pre/post integrity status and
        # filtration evidence can be read back later (genealogy/review composition), see models.py.
        fill_op.filter_use_id = cmd.filter_use_id

    signature_id = await _resolve_signature(
        session, record_type="fill_operation", action="complete", actor_user_id=actor_user_id,
        record_version=fill_op.version, record_hash=sha256_hex({"id": str(fill_op.id), "state": fill_op.state}),
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = fill_op.state
    fill_op.state = "COMPLETE"
    fill_op.ended_at = datetime.now(timezone.utc)
    if cmd.machine_count_end is not None:
        fill_op.machine_count_end = cmd.machine_count_end
    fill_op.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=fill_op.site_id, aggregate_type="fill_operation",
        aggregate_id=fill_op.id, version=fill_op.version, action="Changed", actor_user_id=actor_user_id, reason=cmd.reason,
        old_state=old_state, event_type="PFSFillingCompleted", event_payload={"id": str(fill_op.id), "state": fill_op.state},
        expected_version=cmd.expected_version, command_type="CompleteFillingStage", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------------------------------
# DeviceAssemblyRecord — PFS-FR-012/013/018. No function is named for this entity in Document 54 §4
# (only the entity is declared) -- these two commands are derived to give it a real writer, per the
# task's own "For every function above and every function derived from the API list" instruction.
# ---------------------------------------------------------------------------------------------------


class RecordDeviceAssemblyStepCommand(CommandEnvelope):
    batch_id: uuid.UUID
    assembly_step: str
    component_lot_reference: dict
    unit_identifier: str | None = None
    equipment_id: uuid.UUID | None = None
    process_parameters: dict | None = None
    result: str = "PASS"
    # PFS-FR-027: "default disallowed unless released procedure explicitly permits" -- the literal
    # spec text, not an invented gate. A REWORK result without this reference is rejected.
    rework_procedure_reference: dict | None = None
    occurred_at: datetime | None = None


async def record_device_assembly_step(
    session: AsyncSession, cmd: RecordDeviceAssemblyStepCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if cmd.assembly_step not in ASSEMBLY_STEPS:
        raise ValidationFailedError("Unrecognized assembly_step", allowed=list(ASSEMBLY_STEPS))
    if cmd.result not in ("PASS", "FAIL", "REWORK"):
        raise ValidationFailedError("result must be PASS, FAIL or REWORK")
    if cmd.result == "REWORK" and not cmd.rework_procedure_reference:
        raise ReworkRouteRequiredError(
            "Filled primary container rework/reprocessing is disallowed by default (PFS-FR-027) -- an "
            "explicit released-procedure reference is required to record a REWORK result"
        )

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")
    if cmd.equipment_id is not None and await session.get(EquipmentAsset, cmd.equipment_id) is None:
        raise NotFoundError("Referenced equipment asset not found")

    process_parameters = cmd.process_parameters
    if cmd.result == "REWORK":
        process_parameters = {**(cmd.process_parameters or {}), "rework_procedure_reference": cmd.rework_procedure_reference}

    record = DeviceAssemblyRecord(
        site_id=batch.site_id, batch_id=cmd.batch_id, unit_identifier=cmd.unit_identifier, assembly_step=cmd.assembly_step,
        component_lot_reference=cmd.component_lot_reference, equipment_id=cmd.equipment_id, process_parameters=process_parameters,
        performed_by=actor_user_id, result=cmd.result, occurred_at=cmd.occurred_at or datetime.now(timezone.utc), version=1,
    )
    session.add(record)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="device_assembly_record",
        aggregate_id=record.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="PFSDeviceAssemblyRecorded", event_payload={"id": str(record.id), "assembly_step": record.assembly_step, "result": record.result},
        expected_version=None, command_type="RecordDeviceAssemblyStep",
    )


class VerifyDeviceAssemblyStepCommand(CommandEnvelope):
    record_id: uuid.UUID
    expected_version: int


async def verify_device_assembly_step(
    session: AsyncSession, cmd: VerifyDeviceAssemblyStepCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """IND-001 independence (Document 112's own CHECK constraint) enforced here as a friendly application
    error before the DB constraint would otherwise reject it."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    result = await session.execute(select(DeviceAssemblyRecord).where(DeviceAssemblyRecord.id == cmd.record_id).with_for_update())
    record = result.scalar_one_or_none()
    if record is None:
        raise NotFoundError("Device assembly record not found")
    if record.version != cmd.expected_version:
        raise StaleVersionError("Record was modified since it was read", expected_version=cmd.expected_version, current_version=record.version)
    if record.verified_by is not None:
        raise InvalidTransitionError("Assembly step already verified", current_state="verified")
    if record.performed_by == actor_user_id:
        raise SodConflictError("The performer of an assembly step cannot also verify it (IND-001)")

    record.verified_by = actor_user_id
    record.version += 1

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=record.site_id, aggregate_type="device_assembly_record",
        aggregate_id=record.id, version=record.version, action="Changed", actor_user_id=actor_user_id, reason=None,
        old_state="unverified", event_type="PFSDeviceAssemblyVerified", event_payload={"id": str(record.id)},
        expected_version=cmd.expected_version, command_type="VerifyDeviceAssemblyStep",
    )


# ---------------------------------------------------------------------------------------------------
# DeviceFunctionalTestLink — PFS-FR-014/017. References the owning `qc.qc_result` row, never duplicates
# it (Document 112's own comment).
# ---------------------------------------------------------------------------------------------------


class RecordPfsFunctionalTestCommand(CommandEnvelope):
    batch_id: uuid.UUID
    test_type: str
    qc_record_reference: dict
    result_state: str
    sample_plan_reference: dict | None = None
    method_reference: dict | None = None
    linked_at: datetime | None = None


async def record_pfs_functional_test(
    session: AsyncSession, cmd: RecordPfsFunctionalTestCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if not cmd.test_type:
        raise ValidationFailedError("test_type is required")
    if cmd.result_state not in ("PENDING", "PASS", "FAIL", "OOS"):
        raise ValidationFailedError("Unrecognized result_state", allowed=["PENDING", "PASS", "FAIL", "OOS"])

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    # Document 112's JSONB-expression uniqueness enforced in application code -- see models.py docstring.
    record_id = cmd.qc_record_reference.get("record_id")
    if record_id is not None:
        existing_links = (
            await session.execute(
                select(DeviceFunctionalTestLink).where(
                    DeviceFunctionalTestLink.batch_id == cmd.batch_id, DeviceFunctionalTestLink.test_type == cmd.test_type,
                )
            )
        ).scalars().all()
        for existing_link in existing_links:
            if existing_link.qc_record_reference.get("record_id") == record_id:
                raise ValidationFailedError(
                    "This qc_record_reference is already linked for this batch/test_type", existing_link_id=str(existing_link.id),
                )

    link = DeviceFunctionalTestLink(
        site_id=batch.site_id, batch_id=cmd.batch_id, test_type=cmd.test_type, qc_record_reference=cmd.qc_record_reference,
        sample_plan_reference=cmd.sample_plan_reference, method_reference=cmd.method_reference, result_state=cmd.result_state,
        blocks_release=cmd.result_state != "PASS", linked_at=cmd.linked_at or datetime.now(timezone.utc), version=1,
    )
    session.add(link)
    await session.flush()

    event_type = "DeviceTestFailed" if cmd.result_state in ("FAIL", "OOS") else "PFSFunctionalTestRecorded"
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="device_functional_test_link",
        aggregate_id=link.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type=event_type, event_payload={"id": str(link.id), "test_type": link.test_type, "result_state": link.result_state},
        expected_version=None, command_type="RecordPFSFunctionalTest",
    )


# ---------------------------------------------------------------------------------------------------
# Release readiness / evidence — PFS-FR-023/024/025/030. SG-148: the COMBINED_PRODUCT checkpoint does
# not check open QMS deviations/CAPAs referencing this batch -- no indexed batch-scoped deviation query
# exists in `app.modules.qms` yet (deviations carry `cross_batch_ids` as an unindexed JSONB list).
# ---------------------------------------------------------------------------------------------------


async def evaluate_pfs_release_readiness(session: AsyncSession, batch_id: uuid.UUID, actor_user_id: uuid.UUID) -> dict:
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    handoffs = (await session.execute(select(ConstituentHandoff).where(ConstituentHandoff.batch_id == batch_id))).scalars().all()
    drug_ok = any(h.from_constituent in ("DRUG", "BIOLOGIC") and h.state == "ACCEPTED" for h in handoffs)
    device_handoffs_pending = [h for h in handoffs if h.from_constituent == "DEVICE" and h.state != "ACCEPTED"]

    # Document 54 §14 forbids overwriting an original failed test result after retest -- every attempt
    # stays a permanent row -- so release readiness must look at the *latest* attempt per test_type, not
    # "any historical failure ever recorded" (which would make a retest pointless).
    test_links = (
        await session.execute(select(DeviceFunctionalTestLink).where(DeviceFunctionalTestLink.batch_id == batch_id).order_by(DeviceFunctionalTestLink.linked_at))
    ).scalars().all()
    latest_by_test_type: dict[str, DeviceFunctionalTestLink] = {}
    for link in test_links:
        latest_by_test_type[link.test_type] = link
    failed_tests = [t for t in latest_by_test_type.values() if t.blocks_release and t.result_state != "PASS"]

    fill_ops = (await session.execute(select(FillOperation).where(FillOperation.batch_id == batch_id))).scalars().all()
    open_holds = [f for f in fill_ops if f.requires_deviation]

    filled_count = (
        await session.execute(
            select(func.coalesce(func.sum(ProductionCountLedger.quantity), 0)).where(
                ProductionCountLedger.batch_id == batch_id, ProductionCountLedger.count_type == "FILLED",
            )
        )
    ).scalar()

    checkpoint_results: dict[str, dict] = {}
    checkpoint_results["DRUG_CONSTITUENT"] = (
        {"state": "SATISFIED", "blockers": []} if drug_ok
        else {"state": "BLOCKED", "blockers": [{"code": "BULK_NOT_RELEASED", "message": "No accepted drug/biologic handoff"}]}
    )
    device_blockers = []
    if device_handoffs_pending:
        device_blockers.append({"code": "PRIMARY_COMPONENT_NOT_RELEASED", "message": f"{len(device_handoffs_pending)} device handoff(s) not accepted"})
    for test in failed_tests:
        device_blockers.append({"code": "DEVICE_TEST_FAILED", "message": f"{test.test_type} result is {test.result_state}", "test_link_id": str(test.id)})
    checkpoint_results["DEVICE_CONSTITUENT"] = {"state": "SATISFIED", "blockers": []} if not device_blockers else {"state": "BLOCKED", "blockers": device_blockers}

    combined_blockers = list(checkpoint_results["DRUG_CONSTITUENT"]["blockers"]) + list(checkpoint_results["DEVICE_CONSTITUENT"]["blockers"])
    if open_holds:
        combined_blockers.append({"code": "PFS_RECONCILIATION_FAILED", "message": f"{len(open_holds)} fill operation(s) have an unresolved hold"})
    if not filled_count:
        combined_blockers.append({"code": "PFS_RECONCILIATION_FAILED", "message": "No FILLED units recorded for this batch"})
    checkpoint_results["COMBINED_PRODUCT"] = {"state": "SATISFIED", "blockers": []} if not combined_blockers else {"state": "BLOCKED", "blockers": combined_blockers}

    for code, outcome in checkpoint_results.items():
        existing_checkpoint = (
            await session.execute(select(DdcpReleaseCheckpoint).where(DdcpReleaseCheckpoint.batch_id == batch_id, DdcpReleaseCheckpoint.checkpoint_code == code))
        ).scalar_one_or_none()
        if existing_checkpoint is None:
            session.add(DdcpReleaseCheckpoint(
                site_id=batch.site_id, batch_id=batch_id, checkpoint_code=code, required_evidence={"blockers_at_creation": outcome["blockers"]},
                blocker_state={"blockers": outcome["blockers"]}, state=outcome["state"], version=1,
            ))
        else:
            if existing_checkpoint.state != "WAIVED_BY_APPROVAL":
                existing_checkpoint.blocker_state = {"blockers": outcome["blockers"]}
                existing_checkpoint.state = outcome["state"]
                existing_checkpoint.version += 1
    await session.flush()

    return {
        "batch_id": str(batch_id), "ready": all(v["state"] in ("SATISFIED", "WAIVED_BY_APPROVAL") for v in checkpoint_results.values()),
        "checkpoints": checkpoint_results,
    }


class CreatePfsBatchEvidencePackageCommand(CommandEnvelope):
    batch_id: uuid.UUID


async def create_pfs_batch_evidence_package(
    session: AsyncSession, cmd: CreatePfsBatchEvidencePackageCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    handoffs = (await session.execute(select(ConstituentHandoff.id, ConstituentHandoff.version).where(ConstituentHandoff.batch_id == cmd.batch_id))).all()
    fill_ops = (await session.execute(select(FillOperation.id, FillOperation.version).where(FillOperation.batch_id == cmd.batch_id))).all()
    assembly = (await session.execute(select(DeviceAssemblyRecord.id, DeviceAssemblyRecord.version).where(DeviceAssemblyRecord.batch_id == cmd.batch_id))).all()
    test_links = (await session.execute(select(DeviceFunctionalTestLink.id, DeviceFunctionalTestLink.version).where(DeviceFunctionalTestLink.batch_id == cmd.batch_id))).all()
    checkpoints = (await session.execute(select(DdcpReleaseCheckpoint.id, DdcpReleaseCheckpoint.version).where(DdcpReleaseCheckpoint.batch_id == cmd.batch_id))).all()

    evidence_set = {
        "constituent_handoffs": [{"id": str(i), "version": v} for i, v in handoffs],
        "fill_operations": [{"id": str(i), "version": v} for i, v in fill_ops],
        "device_assembly_records": [{"id": str(i), "version": v} for i, v in assembly],
        "device_functional_test_links": [{"id": str(i), "version": v} for i, v in test_links],
        "ddcp_release_checkpoints": [{"id": str(i), "version": v} for i, v in checkpoints],
    }
    digest = sha256_hex(evidence_set)

    next_version = (
        await session.execute(select(func.max(BatchEvidenceManifest.manifest_version)).where(BatchEvidenceManifest.batch_id == cmd.batch_id))
    ).scalar() or 0

    manifest = BatchEvidenceManifest(
        site_id=batch.site_id, batch_id=cmd.batch_id, manifest_version=next_version + 1, evidence_set=evidence_set,
        digest=digest, generated_by=actor_user_id, generated_at=datetime.now(timezone.utc), state="FROZEN", version=1,
    )
    session.add(manifest)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="batch_evidence_manifest",
        aggregate_id=manifest.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="PFSBatchPackageGenerated", event_payload={"id": str(manifest.id), "manifest_version": manifest.manifest_version, "digest": digest},
        expected_version=None, command_type="CreatePFSBatchEvidencePackage",
    )


# ---------------------------------------------------------------------------------------------------
# Genealogy / batch review package — PFS-FR-021/025. Both are pure read compositions over rows this
# module (and the modules it already legitimately references) already owns; neither writes anything,
# matching the task brief's own framing ("the underlying handoff/assembly/count data already carries
# the batch-scoped references it would need"). Deliberately NOT the generic `app.modules.genealogy`
# graph (GenealogyNode/Edge) -- this module never creates rows there, and Document 54/112 name no
# requirement to backfill that graph from DDCP data; this is its own document-scoped composition, the
# same choice `evaluate_pfs_release_readiness` already makes for checkpoint composition.
# ---------------------------------------------------------------------------------------------------


async def get_pfs_batch_genealogy(session: AsyncSession, batch_id: uuid.UUID) -> dict:
    """PFS-FR-021: "Drug bulk -> component lots -> filled syringe lot/unit/sample -> packaged lot/device
    ID relationships preserved." Composes the four tables that between them already carry every link in
    that chain: `ConstituentHandoff` (drug bulk / component lots feeding the batch),
    `ProductionCountLedger` (filled/sampled/rejected unit counts), `DeviceAssemblyRecord` (per-unit
    device build chain, keyed by `unit_identifier` where recorded), `DeviceFunctionalTestLink`
    (per-unit/per-batch test evidence) and `BatchEvidenceManifest` (the packaged/frozen evidence set, if
    one has been generated). No new join key or entity is invented -- see SG-148 item (5) for the one
    join convention this already required."""

    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    handoffs = (
        await session.execute(select(ConstituentHandoff).where(ConstituentHandoff.batch_id == batch_id).order_by(ConstituentHandoff.version))
    ).scalars().all()
    fill_ops = (
        await session.execute(select(FillOperation).where(FillOperation.batch_id == batch_id).order_by(FillOperation.started_at))
    ).scalars().all()
    counts = (
        await session.execute(select(ProductionCountLedger).where(ProductionCountLedger.batch_id == batch_id).order_by(ProductionCountLedger.occurred_at))
    ).scalars().all()
    assembly = (
        await session.execute(select(DeviceAssemblyRecord).where(DeviceAssemblyRecord.batch_id == batch_id).order_by(DeviceAssemblyRecord.occurred_at))
    ).scalars().all()
    test_links = (
        await session.execute(select(DeviceFunctionalTestLink).where(DeviceFunctionalTestLink.batch_id == batch_id).order_by(DeviceFunctionalTestLink.linked_at))
    ).scalars().all()
    manifests = (
        await session.execute(select(BatchEvidenceManifest).where(BatchEvidenceManifest.batch_id == batch_id).order_by(BatchEvidenceManifest.manifest_version))
    ).scalars().all()

    return {
        "batch_id": str(batch_id),
        "incoming_constituents": [
            {
                "id": str(h.id), "from_constituent": h.from_constituent, "to_constituent": h.to_constituent,
                "source_batch_reference": h.source_batch_reference, "state": h.state, "version": h.version,
            }
            for h in handoffs
        ],
        # Same session-refresh gap `incoming_constituents`/`device_assembly_chain` exist to close (see
        # the frontend's own comment on `genealogyRecordSources`) -- a fill operation's id had no way to
        # be recovered after a page refresh at all, since this document declares no dedicated "list fill
        # operations" endpoint either. Reuses this already-declared genealogy read rather than adding a
        # new one (SG-081 precedent, same as everywhere else this pass added a picker).
        #
        # `version` on every row here (not just id/label) closes a second, sharper edge of the same gap:
        # a mutation that names this id also needs its *current* version for optimistic concurrency
        # (`expected_version`) -- omitting it left the frontend with no honest value to seed but a
        # hardcoded "1" default, a guaranteed STALE_VERSION for any record already past that.
        "fill_operations": [
            {
                "id": str(f.id), "state": f.state, "fill_program_id": f.fill_program_id,
                "target_fill": str(f.target_fill), "target_fill_uom": f.target_fill_uom,
                "started_at": f.started_at.isoformat() if f.started_at else None, "version": f.version,
            }
            for f in fill_ops
        ],
        "production_counts": [
            {"id": str(c.id), "count_type": c.count_type, "source": c.source, "quantity": c.quantity, "device_reference": c.device_reference, "occurred_at": c.occurred_at.isoformat()}
            for c in counts
        ],
        "device_assembly_chain": [
            {
                "id": str(a.id), "unit_identifier": a.unit_identifier, "assembly_step": a.assembly_step,
                "component_lot_reference": a.component_lot_reference, "result": a.result, "occurred_at": a.occurred_at.isoformat(),
                "version": a.version,
            }
            for a in assembly
        ],
        "functional_test_links": [
            {"id": str(t.id), "test_type": t.test_type, "qc_record_reference": t.qc_record_reference, "result_state": t.result_state}
            for t in test_links
        ],
        "evidence_manifests": [
            {"id": str(m.id), "manifest_version": m.manifest_version, "state": m.state, "digest": m.digest}
            for m in manifests
        ],
    }


async def get_pfs_batch_review_summary(session: AsyncSession, batch_id: uuid.UUID) -> dict:
    """PFS-FR-025: "Review shows critical aseptic timeline, filtration, fill IPC, interventions, defects,
    device tests, genealogy and deviations" -- review-by-exception. Shape follows
    `equipment.aseptic_commands.get_review_summary` (this document's own closest analogue named in the
    task brief): one read composition, unplanned/failure counts surfaced at the top so a reviewer sees
    exceptions first, full detail lists underneath.

    Filtration is deliberately absent as its own section: `complete_filling_stage`'s optional
    `filter_use_id` check (PFS-FR-008) is never persisted onto `FillOperation` -- there is nothing stored
    to read back here. That gap is already on record (SG-148 / PFS-FR-008); this function does not
    fabricate a filtration section to paper over it.

    Deviations are matched two ways against `qms.DeviationRecord`: `source_type='batch' AND
    source_id=batch_id` (deviations opened directly against this batch) and a `cross_batch_ids` JSONB
    containment check (deviations opened elsewhere that also name this batch) -- the same unindexed
    JSONB query `evaluate_pfs_release_readiness`'s own comment declines to use as a *release gate* for
    performance reasons (SG-148); a review-by-exception read is not a hot path and is not a regulated
    release gate, so it is fine here."""

    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    fill_ops = (
        await session.execute(select(FillOperation).where(FillOperation.batch_id == batch_id).order_by(FillOperation.started_at))
    ).scalars().all()
    fill_op_ids = [f.id for f in fill_ops]

    ipc_evaluations: list[RuleEvaluation] = []
    if fill_op_ids:
        ipc_evaluations = (
            await session.execute(
                select(RuleEvaluation).where(RuleEvaluation.aggregate_type == "fill_operation", RuleEvaluation.aggregate_id.in_(fill_op_ids)).order_by(RuleEvaluation.evaluated_at)
            )
        ).scalars().all()

    aseptic_timeline: list[dict] = []
    for f in fill_ops:
        for entry in (f.interventions or {}).get("items", []):
            aseptic_timeline.append({"fill_operation_id": str(f.id), **entry})
    aseptic_timeline.sort(key=lambda e: e.get("started_at") or "")

    assembly = (
        await session.execute(select(DeviceAssemblyRecord).where(DeviceAssemblyRecord.batch_id == batch_id))
    ).scalars().all()
    test_links = (
        await session.execute(select(DeviceFunctionalTestLink).where(DeviceFunctionalTestLink.batch_id == batch_id))
    ).scalars().all()
    counts = (
        await session.execute(select(ProductionCountLedger).where(ProductionCountLedger.batch_id == batch_id))
    ).scalars().all()
    checkpoints = (
        await session.execute(select(DdcpReleaseCheckpoint).where(DdcpReleaseCheckpoint.batch_id == batch_id))
    ).scalars().all()
    deviations = (
        await session.execute(
            select(DeviationRecord).where(
                (DeviationRecord.source_type == "batch") & (DeviationRecord.source_id == batch_id)
                | DeviationRecord.cross_batch_ids.contains([str(batch_id)])
            )
        )
    ).scalars().all()

    defect_counts: dict[str, int] = {}
    for c in counts:
        defect_counts[c.count_type] = defect_counts.get(c.count_type, 0) + c.quantity
    failed_assembly = [a for a in assembly if a.result != "PASS"]
    failed_tests = [t for t in test_links if t.result_state not in ("PENDING", "PASS")]
    open_deviations = [d for d in deviations if d.state not in ("CLOSED",)]

    genealogy = await get_pfs_batch_genealogy(session, batch_id)

    return {
        "batch_id": str(batch_id),
        "exception_summary": {
            "fill_operations_on_hold": sum(1 for f in fill_ops if f.requires_deviation),
            "unresolved_interventions": len(aseptic_timeline),
            "fill_ipc_oos_count": sum(1 for e in ipc_evaluations if e.outcome == "FAIL"),
            "device_assembly_exceptions": len(failed_assembly),
            "device_test_exceptions": len(failed_tests),
            "open_deviations": len(open_deviations),
            "checkpoints_blocked": sum(1 for cp in checkpoints if cp.state == "BLOCKED"),
        },
        "aseptic_timeline": aseptic_timeline,
        "fill_ipc_results": [
            {"id": str(e.evaluation_id), "aggregate_id": str(e.aggregate_id), "outcome": e.outcome, "result": e.result, "evaluated_at": e.evaluated_at.isoformat()}
            for e in ipc_evaluations
        ],
        "defect_counts": defect_counts,
        "device_assembly_exceptions": [
            {"id": str(a.id), "unit_identifier": a.unit_identifier, "assembly_step": a.assembly_step, "result": a.result}
            for a in failed_assembly
        ],
        "device_test_exceptions": [
            {"id": str(t.id), "test_type": t.test_type, "result_state": t.result_state} for t in failed_tests
        ],
        "release_checkpoints": [
            {"checkpoint_code": cp.checkpoint_code, "state": cp.state, "blocker_state": cp.blocker_state} for cp in checkpoints
        ],
        "deviations": [
            {"id": str(d.id), "deviation_number": d.deviation_number, "state": d.state, "severity": d.severity} for d in deviations
        ],
        "genealogy": genealogy,
    }


# ---------------------------------------------------------------------------------------------------
# PFS-FR-026 (stability/retain refs), PFS-FR-019 (serialization/UDI support), PFS-FR-029 (Change Control
# linkage) -- closing out Document 54's remaining gaps (SG-148 update).
# ---------------------------------------------------------------------------------------------------


class RecordStabilityRetainReferenceCommand(CommandEnvelope):
    batch_id: uuid.UUID
    plan_reference: dict
    quantity: int
    occurred_at: datetime | None = None


async def record_stability_retain_reference(
    session: AsyncSession, cmd: RecordStabilityRetainReferenceCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """PFS-FR-026: "Create/reference stability/retain sample plans and finished lot samples where
    configured." No dedicated stability/retain-plan entity exists anywhere in Document 112's approved
    schema or this codebase's data model catalogue (same gap class as SG-060's training/qualification-
    action precedent: no entity to link to, so a flag/reference is captured instead of a guessed FK).
    Document 112's own `production_count_ledger.count_type` already declares SAMPLED for exactly this
    concept -- this reuses that table rather than inventing a new one, carrying the plan/sample-plan
    reference as a logical JSONB reference in `device_reference`, the same "reference, never duplicate"
    discipline every other DDCP cross-module reference already follows."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if cmd.quantity < 0:
        raise ValidationFailedError("quantity must not be negative")

    batch = await session.get(Batch, cmd.batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    entry = ProductionCountLedger(
        site_id=batch.site_id, batch_id=cmd.batch_id, count_type="SAMPLED", source="MANUAL", quantity=cmd.quantity,
        recorded_by=actor_user_id, device_reference={"stability_retain_plan_reference": cmd.plan_reference},
        occurred_at=cmd.occurred_at or datetime.now(timezone.utc),
    )
    session.add(entry)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=batch.site_id, aggregate_type="production_count_ledger",
        aggregate_id=entry.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="PFSStabilityRetainSampleRecorded", event_payload={"id": str(entry.id), "batch_id": str(cmd.batch_id)},
        expected_version=None, command_type="RecordStabilityRetainReference",
    )


async def verify_pfs_serialization_compliance(session: AsyncSession, batch_id: uuid.UUID, profile_version_id: uuid.UUID) -> dict:
    """PFS-FR-019: "Support device/combination-product identifier/UDI configuration where applicable;
    actual applicability is regulatory-profile controlled." Reporting-only, pure read, never a release
    gate -- PFS-FR-024's own release-blocker list (evaluate_pfs_release_readiness) does not name
    serialization. No UDI format (GS1 DI, HIBC, ...) is baselined anywhere in Documents 106-115, so this
    checks presence only (`DeviceAssemblyRecord.unit_identifier` populated) when the profile's own
    `required_controls` JSONB declares serialization applicable -- it never invents a format/regex to
    validate against."""

    profile = await session.get(DdcpProfileVersion, profile_version_id)
    if profile is None:
        raise NotFoundError("Injectable profile version not found")

    required = bool((profile.required_controls or {}).get("serialization", {}).get("required"))
    records = (await session.execute(select(DeviceAssemblyRecord).where(DeviceAssemblyRecord.batch_id == batch_id))).scalars().all()
    missing = [str(r.id) for r in records if not r.unit_identifier]

    return {
        "batch_id": str(batch_id), "profile_version_id": str(profile_version_id), "serialization_required": required,
        "total_device_assembly_records": len(records),
        "missing_identifier_count": len(missing) if required else 0,
        "missing_identifier_record_ids": missing if required else [],
    }


async def get_ddcp_change_linkage(session: AsyncSession, object_type: str, object_id: uuid.UUID) -> dict:
    """PFS-FR-029: "Changes to syringe/barrel/stopper/needle/silicone/closure/fill program/filter/control
    strategy link Change Control and risk/validation impact." The write path already exists and is
    correctly owned by `qms.change_commands.assess_impact()` -- its `affected_objects` list already
    accepts an arbitrary `object_type`/`object_id`/`object_version`/`impact_category`/`action_required`
    tuple (AG-05/AG-06: DDCP does not own `qms.change_control`/`change_affected_object` and must not write
    to them directly). This is the DDCP-side read composition confirming the linkage for a given DDCP
    object (e.g. `object_type='ddcp_profile_version'`, `object_id=<profile id>`) -- pure read, no writes.
    `object_type` is caller-supplied, not enumerated here: Document 54 names constituents (barrel,
    stopper, needle, silicone, closure), the fill program and the control strategy as change-sensitive,
    none of which is its own DDCP entity except `ddcp_profile_version`/`constituent_requirement` --
    callers name whichever `object_type` they actually linked via `assess_impact()`."""

    rows = (
        await session.execute(
            select(ChangeAffectedObject, ChangeControl)
            .join(ChangeControl, ChangeAffectedObject.change_id == ChangeControl.id)
            .where(ChangeAffectedObject.object_type == object_type, ChangeAffectedObject.object_id == object_id)
            .order_by(ChangeAffectedObject.created_at)
        )
    ).all()

    return {
        "object_type": object_type, "object_id": str(object_id),
        "changes": [
            {
                "change_id": str(change.id), "change_number": change.change_number, "state": change.state,
                "impact_category": affected.impact_category, "action_required": affected.action_required,
            }
            for affected, change in rows
        ],
    }


# ---------------------------------------------------------------------------
# SG-180 (option B) — DDCP action <-> generic recipe step declarative mapping, read-only sync visibility.
# See DdcpStepMapping's own docstring (app/modules/ddcp/models.py) for why no write-side auto-completion
# was built: Document 106's (batch_step, complete)/(batch_step, results) policy is unconditionally
# signature_required=True, so it would be permanently inert.
# ---------------------------------------------------------------------------

DDCP_MAPPABLE_ACTIONS = ("constituent_handoff.accept", "filling_stage.complete", "device_assembly.verify")


class CreateDdcpStepMappingCommand(CommandEnvelope):
    recipe_version_id: uuid.UUID
    ddcp_action: str
    stable_step_code: str


async def create_step_mapping(
    session: AsyncSession, cmd: CreateDdcpStepMappingCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return MutationReceipt(
            command_id=existing.id, aggregate_id=existing.aggregate_id, resulting_version=existing.resulting_version,
            audit_event_id=None, correlation_id=None,
        )

    if cmd.ddcp_action not in DDCP_MAPPABLE_ACTIONS:
        raise ValidationFailedError(
            "Unknown ddcp_action", ddcp_action=cmd.ddcp_action, allowed=list(DDCP_MAPPABLE_ACTIONS)
        )

    step = (
        await session.execute(
            select(RecipeStep).where(
                RecipeStep.recipe_version_id == cmd.recipe_version_id,
                RecipeStep.stable_step_code == cmd.stable_step_code,
            )
        )
    ).scalar_one_or_none()
    if step is None:
        raise NotFoundError(
            "stable_step_code not found on this recipe version",
            recipe_version_id=str(cmd.recipe_version_id), stable_step_code=cmd.stable_step_code,
        )

    conflict = (
        await session.execute(
            select(DdcpStepMapping).where(
                DdcpStepMapping.recipe_version_id == cmd.recipe_version_id,
                DdcpStepMapping.ddcp_action == cmd.ddcp_action,
            )
        )
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError(
            "A mapping for this recipe_version_id/ddcp_action already exists",
            recipe_version_id=str(cmd.recipe_version_id), ddcp_action=cmd.ddcp_action,
        )

    recipe_version = await session.get(RecipeVersion, cmd.recipe_version_id)

    mapping = DdcpStepMapping(
        recipe_version_id=cmd.recipe_version_id,
        ddcp_action=cmd.ddcp_action,
        stable_step_code=cmd.stable_step_code,
        created_by=actor_user_id,
    )
    session.add(mapping)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=recipe_version.site_id,
        aggregate_type="ddcp_step_mapping", aggregate_id=mapping.id, version=1, action="Created",
        actor_user_id=actor_user_id, reason=None, old_state=None, event_type="DdcpStepMappingCreated",
        event_payload={
            "id": str(mapping.id), "recipe_version_id": str(cmd.recipe_version_id),
            "ddcp_action": cmd.ddcp_action, "stable_step_code": cmd.stable_step_code,
        },
        expected_version=None, command_type="CreateDdcpStepMapping",
    )


async def get_step_mappings(session: AsyncSession, recipe_version_id: uuid.UUID) -> list[dict]:
    rows = (
        await session.execute(select(DdcpStepMapping).where(DdcpStepMapping.recipe_version_id == recipe_version_id))
    ).scalars().all()
    return [
        {
            "id": str(m.id), "recipe_version_id": str(m.recipe_version_id),
            "ddcp_action": m.ddcp_action, "stable_step_code": m.stable_step_code,
        }
        for m in rows
    ]


async def get_batch_ddcp_sync_status(session: AsyncSession, batch_id: uuid.UUID) -> dict:
    """The read that actually addresses SG-180's root cause: for a given batch, which DDCP actions map to
    which generic steps, and what state is each side in right now -- so an operator sees the connection
    instead of two apparently-unrelated progress trackers."""
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found")

    mappings = (
        await session.execute(select(DdcpStepMapping).where(DdcpStepMapping.recipe_version_id == batch.recipe_version_id))
    ).scalars().all()
    if not mappings:
        return {"batch_id": str(batch_id), "mappings": []}

    step_codes = [m.stable_step_code for m in mappings]
    steps_by_code = {
        s.recipe_step_code: s
        for s in (
            await session.execute(
                select(BatchStep).where(BatchStep.batch_id == batch_id, BatchStep.recipe_step_code.in_(step_codes))
            )
        ).scalars().all()
    }

    return {
        "batch_id": str(batch_id),
        "mappings": [
            {
                "ddcp_action": m.ddcp_action,
                "stable_step_code": m.stable_step_code,
                "generic_step_state": steps_by_code[m.stable_step_code].state if m.stable_step_code in steps_by_code else None,
            }
            for m in mappings
        ],
    }
