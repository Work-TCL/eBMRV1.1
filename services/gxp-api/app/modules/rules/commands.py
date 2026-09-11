import uuid
from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.iam.models import User
from app.modules.rules import precision
from app.modules.rules import service as rules_service
from app.modules.rules.expression import evaluate, referenced_variables
from app.modules.rules.models import RuleDefinition, RuleEvaluation
from app.modules.signature import service as signature_service
from app.modules.vault import service as vault_service
from app.mutation.errors import (
    DivisionUndefinedError,
    MissingSignatureError,
    NotFoundError,
    NumericOverflowError,
    PrecisionPolicyUnresolvedError,
    RuleGateFailedError,
    UomConversionUnavailableError,
    UomUnknownError,
    ValidationFailedError,
)
from app.mutation.gateway import (
    check_idempotency,
    record_command_receipt,
    write_audit_event,
    write_outbox_event,
)
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

# Document 110 (SG-143) errors that can occur while evaluating a released rule's expression or
# resolving its unit_policy. RUL-FR-021's established discipline (see EvaluateRuleCommand's contract
# description) is that a failed evaluation is itself a recorded ERROR outcome, not a dropped request —
# these join ValidationFailedError in evaluate_rule's catch for exactly that reason. Simulate is
# different (RUL-FR-023): it has no persisted row to attach an ERROR outcome to, so these still surface
# as ordinary HTTP errors there.
_EVALUATION_FAILURE_ERRORS = (
    ValidationFailedError,
    DivisionUndefinedError,
    NumericOverflowError,
    UomUnknownError,
    UomConversionUnavailableError,
)


def _resolve_class_policy(precision_policy: dict) -> precision.ClassPolicy | None:
    """Document 110 governs a rule going forward from the moment `create_draft` starts requiring
    `precision_policy.calculation_class` (RUL-FR-002-style additive requirement). A rule row that
    predates that requirement, or was inserted directly bypassing the Mutation Gateway (test fixtures
    only — production has no such path, AG-06), has no class to resolve; evaluation then proceeds
    exactly as it did before this pass rather than failing an already-released, immutable rule against a
    requirement it was never drafted against."""
    try:
        return precision.resolve_class_policy(precision_policy or {})
    except PrecisionPolicyUnresolvedError:
        return None


async def _apply_unit_policy(
    session: AsyncSession, rule: RuleDefinition, inputs: dict, *, as_of: datetime
) -> dict:
    """Document 110 §3/CALC-FR-006 — validates and, where declared, converts each input the rule's
    `unit_policy` names. `unit_policy[var]` is either a bare UOM code (captured/compared in that unit,
    no conversion) or `{"uom": code, "convert_to": code}` (converted before the expression sees it).
    Returns a copy of `inputs` with converted values substituted; the caller retains the original
    `inputs` unchanged for raw-value/provenance retention (N3/CALC-FR-002)."""
    unit_policy = rule.unit_policy or {}
    if not unit_policy:
        return inputs
    converted = dict(inputs)
    for var, spec in unit_policy.items():
        if var not in inputs:
            continue
        code = spec if isinstance(spec, str) else spec.get("uom")
        convert_to = None if isinstance(spec, str) else spec.get("convert_to")
        if not code:
            continue
        await rules_service.resolve_uom(session, code)
        if convert_to and convert_to != code:
            await rules_service.resolve_uom(session, convert_to)
            conversion = await rules_service.resolve_conversion(session, code, convert_to, as_of)
            converted[var] = str(Decimal(str(inputs[var])) * conversion.factor)
    return converted


def _receipt_from_existing(existing) -> MutationReceipt:
    return MutationReceipt(
        command_id=existing.id,
        aggregate_id=existing.aggregate_id,
        resulting_version=existing.resulting_version,
        audit_event_id=existing.id,
        correlation_id=existing.id,
    )


# ---------------------------------------------------------------------------
# CreateDraft
# ---------------------------------------------------------------------------


class CreateRuleDraftCommand(CommandEnvelope):
    rule_id: str
    rule_type: str
    semantic_version: str
    expression_ast: dict
    input_contract: dict
    output_contract: dict
    unit_policy: dict
    precision_policy: dict
    rounding_policy: dict
    reason_codes: dict | None = None
    scope: dict | None = None


async def create_draft(
    session: AsyncSession, cmd: CreateRuleDraftCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    conflict = (
        await session.execute(
            select(RuleDefinition).where(
                RuleDefinition.rule_id == cmd.rule_id, RuleDefinition.semantic_version == cmd.semantic_version
            )
        )
    ).scalar_one_or_none()
    if conflict is not None:
        raise ValidationFailedError(
            "A draft or released version already exists at this rule_id/semantic_version",
            rule_id=cmd.rule_id,
            semantic_version=cmd.semantic_version,
        )

    # Document 110 (SG-143/CALC-FR-004): a rule now declares which of §2's ten calculation classes
    # governs it at draft time, same "explicit, never optional" discipline already applied to
    # precision_policy/rounding_policy/unit_policy themselves (see the RuleDefinition docstring).
    precision.resolve_class_policy(cmd.precision_policy)

    rule = RuleDefinition(
        rule_id=cmd.rule_id,
        rule_type=cmd.rule_type,
        semantic_version=cmd.semantic_version,
        scope=cmd.scope,
        status="draft",
        expression_ast=cmd.expression_ast,
        input_contract=cmd.input_contract,
        output_contract=cmd.output_contract,
        unit_policy=cmd.unit_policy,
        precision_policy=cmd.precision_policy,
        rounding_policy=cmd.rounding_policy,
        reason_codes=cmd.reason_codes,
    )
    session.add(rule)
    await session.flush()

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="rule",
        aggregate_id=rule.rule_object_id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"rule_id": rule.rule_id, "semantic_version": rule.semantic_version, "status": "draft"},
    )
    await write_outbox_event(
        session,
        event_type="RuleDraftCreated",
        aggregate_type="rule",
        aggregate_id=rule.rule_object_id,
        aggregate_version=1,
        payload={"id": str(rule.rule_object_id), "rule_id": rule.rule_id},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="CreateRuleDraft",
        aggregate_type="rule",
        aggregate_id=rule.rule_object_id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=rule.rule_object_id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Validate
# ---------------------------------------------------------------------------


class ValidateRuleCommand(CommandEnvelope):
    rule_object_id: uuid.UUID


async def validate_rule(
    session: AsyncSession, cmd: ValidateRuleCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    rule = await rules_service.get_rule(session, cmd.rule_object_id)
    if rule.status != "draft":
        raise ValidationFailedError("Only a draft rule can be validated", current_status=rule.status)

    declared_inputs = set(rule.input_contract.keys())
    used = referenced_variables(rule.expression_ast)
    undeclared = used - declared_inputs
    if undeclared:
        raise ValidationFailedError(
            "Expression references input(s) not declared in input_contract", undeclared=sorted(undeclared)
        )
    if not rule.output_contract:
        raise ValidationFailedError("output_contract must declare at least the result type/unit")

    old_status = rule.status
    rule.status = "validated"

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="rule",
        aggregate_id=rule.rule_object_id,
        aggregate_version=1,
        action="Changed",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"status": old_status},
        new_value={"status": rule.status},
    )
    await write_outbox_event(
        session,
        event_type="RuleValidated",
        aggregate_type="rule",
        aggregate_id=rule.rule_object_id,
        aggregate_version=1,
        payload={"id": str(rule.rule_object_id)},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="ValidateRule",
        aggregate_type="rule",
        aggregate_id=rule.rule_object_id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=rule.rule_object_id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Simulate — RUL-FR-023: never writes regulated state. Deliberately not a Mutation Gateway command:
# no idempotency key, no audit event, no outbox row, no receipt. Just a direct evaluation result.
# ---------------------------------------------------------------------------


async def simulate_rule(session: AsyncSession, *, rule_object_id: uuid.UUID, inputs: dict) -> dict:
    rule = await rules_service.get_rule(session, rule_object_id)
    if rule.status not in ("draft", "validated"):
        raise ValidationFailedError(
            "Only a draft or validated rule can be simulated — a released rule is evaluated, not simulated",
            current_status=rule.status,
        )
    # Document 110 (SG-143): simulate stays on the identical precision/UOM path as evaluate (RUL-FR-023
    # note in the module docstring) — a simulation that rounds differently from the evaluation it
    # previews would be worse than no simulation.
    class_policy = _resolve_class_policy(rule.precision_policy)
    converted_inputs = await _apply_unit_policy(session, rule, inputs, as_of=datetime.now(timezone.utc))
    result = evaluate(
        rule.expression_ast, converted_inputs, class_policy=class_policy, precision_policy=rule.precision_policy
    )
    if class_policy is not None and isinstance(result, Decimal):
        dp = precision.presentation_dp(class_policy, rule.precision_policy or {})
        if dp is not None:
            result = str(precision.round_at_stage(result, class_policy, dp)[0])
    return {"rule_object_id": str(rule_object_id), "result": result, "simulated": True}


# ---------------------------------------------------------------------------
# Release
# ---------------------------------------------------------------------------


class ReleaseRuleCommand(CommandEnvelope):
    rule_object_id: uuid.UUID
    effective_from: datetime | None = None
    effective_to: datetime | None = None
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def release_rule(
    session: AsyncSession, cmd: ReleaseRuleCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    rule = await rules_service.get_rule(session, cmd.rule_object_id)
    if rule.status != "validated":
        raise ValidationFailedError("Only a validated rule can be released", current_status=rule.status)

    effective_from = cmd.effective_from or datetime.now(timezone.utc)
    if cmd.effective_to is None:
        # Two simultaneously open-ended released versions of the same rule_id would make
        # get_effective_released_rule() ambiguous forever — reject up front rather than defensively
        # failing later at evaluation time. A time-boxed release (effective_to set) skips this check;
        # full interval-overlap validation is out of scope for this pass.
        open_ended_conflict = (
            await session.execute(
                select(RuleDefinition).where(
                    RuleDefinition.rule_id == rule.rule_id,
                    RuleDefinition.status == "released",
                    RuleDefinition.effective_to.is_(None),
                )
            )
        ).scalar_one_or_none()
        if open_ended_conflict is not None:
            raise ValidationFailedError(
                "Another released version of this rule_id has no effective_to — set its effective_to "
                "(supersede it) before releasing a new open-ended version",
                rule_id=rule.rule_id,
            )

    # SG-035 (2026-09-10, project-owner-directed): Document 106 section 9 row 6 -- `rule/release` is
    # `Released` by a "QA Approver / Batch Release" -> "QA Releaser", "independent of every production
    # performer on the record". RuleDefinition stores no author/performer identity, so the required role
    # is enforced (at any site) and the independence clause has no data source -- same honest limitation
    # recorded for qa_review_package/complete.
    policy = await signature_service.resolve_signature_requirement(
        session, record_type="rule", action="release"
    )
    signature_id = None
    if policy.signature_required:
        await signature_service.enforce_signer_policy(
            session, policy=policy, actor_user_id=actor_user_id, site_id=None,
            action_label="rule.release",
        )
        if cmd.challenge_id is None or not cmd.reauth_password:
            raise MissingSignatureError("Releasing a rule requires a signature", required_meaning=policy.meaning)
        actor = await session.get(User, actor_user_id)
        if actor is None or not verify_password(cmd.reauth_password, actor.password_hash):
            raise MissingSignatureError("Fresh step-up authentication failed")
        canonical = {
            "rule_id": rule.rule_id,
            "semantic_version": rule.semantic_version,
            "expression_ast": rule.expression_ast,
        }
        challenge = await signature_service.consume_challenge(
            session,
            challenge_id=cmd.challenge_id,
            user_id=actor_user_id,
            record_version=1,
            record_hash=sha256_hex(canonical),
        )
        signature = await signature_service.sign(
            session, challenge=challenge, auth_context={"method": "password_reauth"}
        )
        signature_id = signature.id

    old_status = rule.status
    rule.status = "released"
    rule.effective_from = effective_from
    rule.effective_to = cmd.effective_to

    vault_object = await vault_service.release_master(
        session,
        object_type="rule",
        business_id=rule.rule_id,
        actor_user_id=actor_user_id,
        business_version_label=rule.semantic_version,
        canonical_payload={
            "rule_id": rule.rule_id,
            "rule_type": rule.rule_type,
            "semantic_version": rule.semantic_version,
            "expression_ast": rule.expression_ast,
            "input_contract": rule.input_contract,
            "output_contract": rule.output_contract,
            "unit_policy": rule.unit_policy,
            "precision_policy": rule.precision_policy,
            "rounding_policy": rule.rounding_policy,
            "signature_id": str(signature_id) if signature_id else None,
        },
    )
    rule.released_vault_object_id = vault_object.object_id

    correlation_id = uuid.uuid4()
    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="rule",
        aggregate_id=rule.rule_object_id,
        aggregate_version=1,
        action="Released",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        old_value={"status": old_status},
        new_value={"status": rule.status},
        signature_id=signature_id,
    )
    await write_outbox_event(
        session,
        event_type="RuleReleased",
        aggregate_type="rule",
        aggregate_id=rule.rule_object_id,
        aggregate_version=1,
        payload={"id": str(rule.rule_object_id), "rule_id": rule.rule_id},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="ReleaseRule",
        aggregate_type="rule",
        aggregate_id=rule.rule_object_id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=rule.rule_object_id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        signature_id=signature_id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Evaluate — the regulated mutation path: resolves the effective released rule, evaluates it, and
# persists the result (RUL-FR-022) rather than letting a caller recompute it later under a newer version.
# ---------------------------------------------------------------------------


class EvaluateRuleCommand(CommandEnvelope):
    rule_id: str
    inputs: dict
    aggregate_type: str | None = None
    aggregate_id: uuid.UUID | None = None
    aggregate_version: int | None = None


async def evaluate_rule(
    session: AsyncSession, cmd: EvaluateRuleCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    rule = await rules_service.get_effective_released_rule(session, cmd.rule_id)

    class_policy = _resolve_class_policy(rule.precision_policy)
    applied_policy_version = precision.DOCUMENT_110_VERSION if class_policy is not None else None
    raw_result: dict | None = None
    try:
        as_of = datetime.now(timezone.utc)
        converted_inputs = await _apply_unit_policy(session, rule, cmd.inputs, as_of=as_of)
        result = evaluate(
            rule.expression_ast, converted_inputs, class_policy=class_policy, precision_policy=rule.precision_policy
        )
        if class_policy is not None and isinstance(result, Decimal):
            dp = precision.presentation_dp(class_policy, rule.precision_policy or {})
            if dp is not None:
                rounded, raw = precision.round_at_stage(result, class_policy, dp)
                raw_result = {"value": str(raw)}
                result = rounded
        outcome = "PASS" if result is True else ("FAIL" if result is False else "COMPUTED")
    except _EVALUATION_FAILURE_ERRORS as exc:
        result = {"error": exc.message, "code": exc.code, "details": exc.details}
        outcome = "ERROR"

    correlation_id = uuid.uuid4()
    evaluation = RuleEvaluation(
        rule_object_id=rule.rule_object_id,
        aggregate_type=cmd.aggregate_type,
        aggregate_id=cmd.aggregate_id,
        aggregate_version=cmd.aggregate_version,
        input_hash=sha256_hex(cmd.inputs),
        inputs_or_refs=cmd.inputs,
        result=result if isinstance(result, dict) else {"value": str(result)},
        outcome=outcome,
        correlation_id=correlation_id,
        raw_result=raw_result,
        applied_policy_version=applied_policy_version,
    )
    session.add(evaluation)
    await session.flush()

    audit_event = await write_audit_event(
        session,
        site_id=None,
        aggregate_type="rule_evaluation",
        aggregate_id=evaluation.evaluation_id,
        aggregate_version=1,
        action="Created",
        actor_id=actor_user_id,
        correlation_id=correlation_id,
        new_value={"rule_id": rule.rule_id, "outcome": outcome},
    )
    await write_outbox_event(
        session,
        event_type="RuleEvaluated",
        aggregate_type="rule_evaluation",
        aggregate_id=evaluation.evaluation_id,
        aggregate_version=1,
        payload={"id": str(evaluation.evaluation_id), "rule_id": rule.rule_id, "outcome": outcome},
        correlation_id=correlation_id,
    )
    receipt = await record_command_receipt(
        session,
        site_id=None,
        command_type="EvaluateRule",
        aggregate_type="rule_evaluation",
        aggregate_id=evaluation.evaluation_id,
        expected_version=None,
        resulting_version=1,
        idempotency_key=cmd.idempotency_key,
        command_hash=payload_hash,
        actor_user_id=actor_user_id,
        payload_hash=payload_hash,
    )
    return MutationReceipt(
        command_id=receipt.id,
        aggregate_id=evaluation.evaluation_id,
        resulting_version=1,
        audit_event_id=audit_event.id,
        correlation_id=correlation_id,
    )


# ---------------------------------------------------------------------------
# Optional release-gating hook (MUT-FR-014/RUL-FR-016) -- a domain module (batch, material lot, ...) calls
# this before finalizing its own release/disposition. If no released rule resolves at `rule_id`, this is a
# no-op: the gate only takes effect once a deployment actually authors and releases one. This is deliberately
# generic wiring, not an invented business rule -- what the rule's own eligibility logic checks is entirely
# up to whoever authors and releases it later.
# ---------------------------------------------------------------------------


async def evaluate_release_gate(
    session: AsyncSession,
    *,
    rule_id: str,
    inputs: dict,
    aggregate_type: str,
    aggregate_id: uuid.UUID,
    aggregate_version: int,
    actor_user_id: uuid.UUID,
) -> None:
    try:
        await rules_service.get_effective_released_rule(session, rule_id=rule_id)
    except NotFoundError:
        return

    receipt = await evaluate_rule(
        session,
        EvaluateRuleCommand(
            idempotency_key=str(uuid.uuid4()),
            rule_id=rule_id,
            inputs=inputs,
            aggregate_type=aggregate_type,
            aggregate_id=aggregate_id,
            aggregate_version=aggregate_version,
        ),
        actor_user_id,
    )
    evaluation = await session.get(RuleEvaluation, receipt.aggregate_id)
    if evaluation.outcome != "PASS":
        raise RuleGateFailedError(
            f"Release blocked by rule '{rule_id}'",
            rule_id=rule_id,
            evaluation_id=str(evaluation.evaluation_id),
            outcome=evaluation.outcome,
        )
