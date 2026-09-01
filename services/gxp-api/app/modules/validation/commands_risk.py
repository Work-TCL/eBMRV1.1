"""Document 80 (SPEC-VAL-002) Mutation Gateway command handlers -- Intended Use, GxP Criticality &
Software Function Risk Classification. `risk_category`/`assurance_method` are never a free-text opinion:
they are mechanically derived from caller-declared boolean inputs using Document 111 section 1's own
approved, auditable derivation rule (`risk category := HIGHER-PROCESS-RISK if (release|disposition) or
signature or audit-immutability or (calculation AND enforcement) appears in the requirements`) -- the
same rule Document 111 itself used to classify every module in the 01-105 baseline, applied here at
function granularity per Document 111's own "function-level classification inherits the module
classification unless a work package raises it."

Document 106 row 145: `approve` requires an `Approved` signature from an independent QA Releaser
("Module approver role"), reason mandatory. `intended_use`/`function_risks` create actions carry no
Document 106 row of their own -- RBAC-gated only.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.validation.models import ASSURANCE_METHODS, FunctionRiskAssessment, IntendedUse
from app.modules.validation.shared import finalize, receipt_from_existing, resolve_signature, verify_reauth_and_consume
from app.mutation.errors import InvalidTransitionError, NotFoundError, StaleVersionError, ValidationFailedError
from app.mutation.gateway import check_idempotency, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

RECORD_TYPE_FUNCTION_RISK = "function_risk_assessment"


def derive_risk_category(
    *, automation_role: str, has_release_or_disposition: bool, has_signature_role: bool,
    has_audit_immutability_role: bool, has_enforcement_role: bool,
) -> tuple[str, str]:
    """Document 111 section 1's derivation rule, verbatim. Returns (risk_category, assurance_method)."""
    higher = (
        has_release_or_disposition or has_signature_role or has_audit_immutability_role
        or (automation_role == "calculation" and has_enforcement_role)
    )
    if higher:
        return "HIGHER-PROCESS-RISK", ASSURANCE_METHODS[0]
    return "STANDARD-RISK", ASSURANCE_METHODS[1]


class CreateIntendedUseCommand(CommandEnvelope):
    scope_ref: str
    scope_version: str
    regulated_process: str
    users: list[str] = []
    record_relevance: bool = False
    signature_relevance: bool = False


async def create_intended_use(
    session: AsyncSession, cmd: CreateIntendedUseCommand, actor_user_id: uuid.UUID, site_id: uuid.UUID | None
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = IntendedUse(
        site_id=site_id, scope_ref=cmd.scope_ref, scope_version=cmd.scope_version,
        regulated_process=cmd.regulated_process, users=cmd.users, record_relevance=cmd.record_relevance,
        signature_relevance=cmd.signature_relevance, state="EFFECTIVE", version=1,
    )
    session.add(row)
    await session.flush()

    new_value = {"scope_ref": row.scope_ref, "scope_version": row.scope_version}
    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type="intended_use", aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value=new_value, event_type="IntendedUseCreated", expected_version=None,
        command_type="CreateIntendedUse", site_id=site_id,
    )


class CreateFunctionRiskAssessmentCommand(CommandEnvelope):
    function_ref: str
    function_version: str
    failure_modes: list[str] = []
    impacts: dict = {}
    detectability: str
    automation_role: str
    has_release_or_disposition: bool = False
    has_signature_role: bool = False
    has_audit_immutability_role: bool = False
    has_enforcement_role: bool = False
    controls: list[str] = []


async def create_function_risk_assessment(
    session: AsyncSession, cmd: CreateFunctionRiskAssessmentCommand, actor_user_id: uuid.UUID,
    site_id: uuid.UUID | None,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    from app.modules.validation.models import AUTOMATION_ROLES, DETECTABILITY_LEVELS
    if cmd.detectability not in DETECTABILITY_LEVELS:
        raise ValidationFailedError(f"detectability must be one of {DETECTABILITY_LEVELS}")
    if cmd.automation_role not in AUTOMATION_ROLES:
        raise ValidationFailedError(f"automation_role must be one of {AUTOMATION_ROLES}")

    risk_category, assurance_method = derive_risk_category(
        automation_role=cmd.automation_role, has_release_or_disposition=cmd.has_release_or_disposition,
        has_signature_role=cmd.has_signature_role, has_audit_immutability_role=cmd.has_audit_immutability_role,
        has_enforcement_role=cmd.has_enforcement_role,
    )

    row = FunctionRiskAssessment(
        function_ref=cmd.function_ref, function_version=cmd.function_version, failure_modes=cmd.failure_modes,
        impacts=cmd.impacts, detectability=cmd.detectability, automation_role=cmd.automation_role,
        has_release_or_disposition=cmd.has_release_or_disposition, has_signature_role=cmd.has_signature_role,
        has_audit_immutability_role=cmd.has_audit_immutability_role, has_enforcement_role=cmd.has_enforcement_role,
        controls=cmd.controls, risk_category=risk_category, assurance_method=assurance_method,
        state="DRAFT", version=1,
    )
    session.add(row)
    await session.flush()

    # AssuranceLevelDerived is the same moment as FunctionRiskAssessed (the assurance method is derived,
    # not separately decided) -- a secondary outbox event in the same transaction, not a second _finalize.
    await write_outbox_event(
        session, event_type="AssuranceLevelDerived", aggregate_type=RECORD_TYPE_FUNCTION_RISK,
        aggregate_id=row.id, aggregate_version=1,
        payload={"function_ref": row.function_ref, "risk_category": risk_category, "assurance_method": assurance_method},
        correlation_id=uuid.uuid4(),
    )

    new_value = {"function_ref": row.function_ref, "risk_category": risk_category}
    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_FUNCTION_RISK, aggregate_id=row.id,
        version=row.version, action="Created", actor_user_id=actor_user_id, reason=None, old_value=None,
        new_value=new_value, event_type="FunctionRiskAssessed", expected_version=None,
        command_type="CreateFunctionRiskAssessment", site_id=site_id,
    )


class ApproveFunctionRiskAssessmentCommand(CommandEnvelope):
    assessment_id: uuid.UUID
    expected_version: int
    reason: str
    residual_risk: str | None = None
    challenge_id: uuid.UUID
    reauth_password: str


async def approve_function_risk_assessment(
    session: AsyncSession, cmd: ApproveFunctionRiskAssessmentCommand, actor_user_id: uuid.UUID,
    site_id: uuid.UUID | None,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return receipt_from_existing(existing)

    row = await session.get(FunctionRiskAssessment, cmd.assessment_id)
    if row is None:
        raise NotFoundError("Function risk assessment not found")
    if row.state != "DRAFT":
        raise InvalidTransitionError("Assessment is not DRAFT", current_state=row.state)
    if row.version != cmd.expected_version:
        raise StaleVersionError("Assessment changed since this request was prepared", current_version=row.version)
    if not cmd.reason:
        raise ValidationFailedError("reason is required to approve a function risk assessment")

    policy = await resolve_signature(session, record_type=RECORD_TYPE_FUNCTION_RISK, action="approve")
    signature_id = None
    if policy.signature_required:
        signature_id = await verify_reauth_and_consume(
            session, actor_user_id=actor_user_id, challenge_id=cmd.challenge_id,
            reauth_password=cmd.reauth_password, record_id=row.id, record_version=row.version,
        )

    row.state = "APPROVED"
    row.residual_risk = cmd.residual_risk
    row.approved_by_user_id = actor_user_id
    row.approved_at = datetime.now(timezone.utc)
    row.version += 1

    # Document 06 (VLT-FR-001): an approved function risk classification is a controlled record that
    # drives every downstream CSA decision -- immutable vault snapshot in the same transaction.
    from app.modules.vault import service as vault_service
    await vault_service.release_master(
        session, object_type=RECORD_TYPE_FUNCTION_RISK, business_id=str(row.id), site_id=site_id,
        actor_user_id=actor_user_id,
        canonical_payload={
            "function_ref": row.function_ref, "function_version": row.function_version,
            "risk_category": row.risk_category, "assurance_method": row.assurance_method,
            "residual_risk": row.residual_risk,
        },
    )

    return await finalize(
        session, cmd=cmd, payload_hash=payload_hash, aggregate_type=RECORD_TYPE_FUNCTION_RISK, aggregate_id=row.id,
        version=row.version, action="Approved", actor_user_id=actor_user_id, reason=cmd.reason,
        old_value={"state": "DRAFT"}, new_value={"state": "APPROVED", "residual_risk": cmd.residual_risk},
        event_type="RiskAssessmentApproved", expected_version=cmd.expected_version,
        command_type="ApproveFunctionRiskAssessment", site_id=site_id, signature_id=signature_id,
    )


async def get_function_assurance(session: AsyncSession, function_ref: str) -> dict:
    """Read-only: the latest approved (or, absent one, latest draft) risk classification for a
    function_ref -- RISK-FR-011's "risk drives testing style, depth, independence and evidence"."""
    from sqlalchemy import select
    row = (
        await session.execute(
            select(FunctionRiskAssessment)
            .where(FunctionRiskAssessment.function_ref == function_ref)
            .order_by(FunctionRiskAssessment.version.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    if row is None:
        raise NotFoundError("No function risk assessment found for this function_ref")
    return {
        "function_ref": row.function_ref, "state": row.state, "risk_category": row.risk_category,
        "assurance_method": row.assurance_method, "residual_risk": row.residual_risk,
    }
