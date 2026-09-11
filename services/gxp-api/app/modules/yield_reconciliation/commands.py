"""Document 17 (SPEC-EBMR-008) commands. Yield/potency calculation delegates the actual arithmetic to
Document 08's released-rule engine (`rules_commands.evaluate_rule`) rather than embedding a formula here
(spec §3 "do not embed formula in UI", module docstring in models.py) -- the manufacturing-specific state
(scope, source-quantity references, verification, supersession) lives in this module's own two tables.

Document 106 row 40 is the one real signature in this document: `verify` requires a "Qualified independent
verifier" who is not the performer (SIG-FR-018) -- the only genuinely signed action in WP-03/WP-07's
combined build so far outside the pre-existing WP-01/02 modules.
"""

import uuid
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.security import verify_password
from app.modules.batch_execution.models import Batch
from app.modules.device import service as device_service
from app.modules.erp import commands as erp_commands
from app.modules.iam.models import User
from app.modules.packaging import service as packaging_service
from app.modules.qms import service as qms_service
from app.modules.rules import commands as rules_commands
from app.modules.rules import service as rules_service
from app.modules.rules.models import RuleEvaluation
from app.modules.signature import service as signature_service
from app.modules.yield_reconciliation.models import (
    COMPONENT_QUANTITY_CATEGORIES,
    QUANTITY_CATEGORIES,
    RECONCILIATION_TYPES,
    SCOPE_TYPES,
    ManufacturingCalculation,
    ReconciliationRecord,
)
from app.mutation.errors import (
    MissingSignatureError,
    NotFoundError,
    StaleVersionError,
    UomUnknownError,
    ValidationFailedError,
)
from app.mutation.gateway import check_idempotency, record_command_receipt, write_audit_event, write_outbox_event
from app.mutation.hashing import sha256_hex
from app.mutation.schemas import CommandEnvelope, MutationReceipt

YIELD_RULE_ID = "yield_percent"  # seeded platform-floor rule -- see scripts/seed.py; formula is the
# literal one Document 17 §3 gives, not an invention (YLD-FR-001/003/007).


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


async def _load_batch_site_id(session: AsyncSession, batch_id: uuid.UUID) -> uuid.UUID:
    """Every calculation/reconciliation row is scoped to the batch's own site (there is no separate
    site input on any of this module's commands) -- `site_id` is not nullable, so a batch that does not
    resolve fails closed rather than writing an orphaned row."""
    batch = await session.get(Batch, batch_id)
    if batch is None:
        raise NotFoundError("Batch not found", batch_id=str(batch_id))
    return batch.site_id


async def _resolve_uom_id(session: AsyncSession, uom: str | None) -> uuid.UUID | None:
    """SG-146 (remainder), MIG-FR-004 expand step: best-effort dual-write onto the Document 110 §3
    controlled UOM master. `uom` (the free-text column) stays authoritative and this module's own
    validation never depends on the result -- an unresolved code (no released rules.gxp_uom row yet, or
    a value that will never be a controlled unit) simply leaves `uom_id` NULL rather than rejecting the
    calculation/reconciliation. That is the whole point of the expand phase: no existing caller breaks
    while the UOM master is still being populated."""
    if not uom:
        return None
    try:
        row = await rules_service.resolve_uom(session, uom)
    except UomUnknownError:
        return None
    return row.uom_id


def calculation_record_hash(calc: ManufacturingCalculation) -> str:
    return sha256_hex({"id": str(calc.id), "version": calc.version, "state": calc.state})


def reconciliation_record_hash(rec: ReconciliationRecord) -> str:
    return sha256_hex({"id": str(rec.id), "version": rec.version, "state": rec.state})


# ---------------------------------------------------------------------------------------------------
# Yield / potency — YLD-FR-001..008/015/016/022/031. Unsigned (Document 106 has no row for the
# calculation itself, only for `verify`).
# ---------------------------------------------------------------------------------------------------


class EvaluateYieldCommand(CommandEnvelope):
    batch_id: uuid.UUID
    scope_type: str = "BATCH"
    scope_id: uuid.UUID | None = None
    phase_code: str | None = None
    theoretical_quantity: str
    actual_quantity: str
    uom: str
    min_percent: str | None = None
    max_percent: str | None = None
    manual_source: str | None = None
    manual_reason: str | None = None
    input_refs: dict = {}


async def evaluate_yield(
    session: AsyncSession, cmd: EvaluateYieldCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.scope_type not in SCOPE_TYPES:
        raise ValidationFailedError("Unrecognized scope_type", allowed=list(SCOPE_TYPES))
    if cmd.manual_source and not cmd.manual_reason:
        raise ValidationFailedError("manual_reason is required when manual_source is supplied (YLD-FR-008)")

    site_id = await _load_batch_site_id(session, cmd.batch_id)

    # YLD-FR-001/003/007: the formula itself is never embedded here -- resolve the released
    # "yield_percent" rule (Document 17 §3's literal formula, seeded as platform-floor data) and delegate
    # to Document 08's engine.
    rule = await rules_service.get_effective_released_rule(session, YIELD_RULE_ID)
    inner_key = f"{cmd.idempotency_key}:rule-eval"
    rule_receipt = await rules_commands.evaluate_rule(
        session,
        rules_commands.EvaluateRuleCommand(
            idempotency_key=inner_key, rule_id=YIELD_RULE_ID,
            inputs={"actual_yield": cmd.actual_quantity, "theoretical_yield": cmd.theoretical_quantity},
        ),
        actor_user_id,
    )
    evaluation = await session.get(RuleEvaluation, rule_receipt.aggregate_id)

    input_refs = {**cmd.input_refs, "theoretical_quantity": cmd.theoretical_quantity, "actual_quantity": cmd.actual_quantity}
    calc = ManufacturingCalculation(
        site_id=site_id, batch_id=cmd.batch_id, scope_type=cmd.scope_type, scope_id=cmd.scope_id,
        calculation_type="YIELD", phase_code=cmd.phase_code, rule_object_id=rule.rule_object_id,
        rule_evaluation_id=evaluation.evaluation_id, input_refs=input_refs, input_hash=sha256_hex(input_refs),
        theoretical_quantity=cmd.theoretical_quantity, actual_quantity=cmd.actual_quantity, uom=cmd.uom,
        uom_id=await _resolve_uom_id(session, cmd.uom),
        min_percent=cmd.min_percent, max_percent=cmd.max_percent, manual_source=cmd.manual_source,
        manual_reason=cmd.manual_reason, evaluated_by_user_id=actor_user_id,
        evaluated_at=datetime.now(timezone.utc), version=1,
    )

    if evaluation.outcome == "ERROR":
        calc.state = "FAILED"
        calc.result = evaluation.result
        event_type = "YieldCalculated"
    else:
        # CC-4 (Document 110 §2): 6dp intermediate, 2dp reported, half-up, rounded at presentation.
        # app/modules/rules/precision.py applies this inside evaluate_rule() itself, driven by the
        # rule's own precision_policy.calculation_class -- evaluation.result is already the
        # presentation-rounded value and evaluation.raw_result is the pre-rounding one (CALC-FR-002).
        # This module no longer re-derives reported_dp/mode from rounding_policy or re-quantizes; doing
        # so here as well as in the engine was two divergent rounding pathways for the same number
        # (SG-143's resolution note, closed by SG-146). A yield_percent rule drafted without a resolvable
        # calculation_class (defensive only -- the seeded floor rule always declares CC-4) leaves
        # raw_result null; the unrounded evaluation.result is then reported as-is rather than silently
        # re-rounded by this module.
        try:
            reported_percent = Decimal(str(evaluation.result.get("value", evaluation.result)))
        except (InvalidOperation, AttributeError, TypeError):
            reported_percent = Decimal(str(evaluation.result))
        raw_percent = Decimal(str(evaluation.raw_result["value"])) if evaluation.raw_result else reported_percent
        calc.result = {"yield_percent": str(reported_percent), "raw_percent": str(raw_percent)}

        out_of_limit = False
        if cmd.min_percent is not None and reported_percent < Decimal(cmd.min_percent):
            out_of_limit = True
        if cmd.max_percent is not None and reported_percent > Decimal(cmd.max_percent):
            out_of_limit = True
        calc.state = "OUT_OF_LIMIT" if out_of_limit else "CALCULATED"
        event_type = "YieldOutOfLimit" if out_of_limit else "YieldCalculated"

    session.add(calc)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=calc.site_id, aggregate_type="manufacturing_calculation",
        aggregate_id=calc.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type=event_type, event_payload={"id": str(calc.id), "state": calc.state, "result": calc.result},
        expected_version=None, command_type="EvaluateYield",
    )


class EvaluatePotencyCommand(CommandEnvelope):
    batch_id: uuid.UUID
    scope_type: str = "BATCH"
    scope_id: uuid.UUID | None = None
    phase_code: str | None = None
    rule_id: str
    inputs: dict
    uom: str | None = None


async def evaluate_potency(
    session: AsyncSession, cmd: EvaluatePotencyCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """YLD-FR-015. No default potency formula exists anywhere in the approved baseline (unlike yield,
    whose formula Document 17 §3 states literally) -- SG (see docs/generated/18_SPEC_GAPS.md): this
    command always requires a customer-authored, released rule at `rule_id`; `get_effective_released_rule`
    fails closed (NotFoundError) if none exists, exactly like every other unresolved-policy path in this
    codebase. Never a hardcoded pharmaceutical formula."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if cmd.scope_type not in SCOPE_TYPES:
        raise ValidationFailedError("Unrecognized scope_type", allowed=list(SCOPE_TYPES))

    site_id = await _load_batch_site_id(session, cmd.batch_id)

    rule = await rules_service.get_effective_released_rule(session, cmd.rule_id)
    inner_key = f"{cmd.idempotency_key}:rule-eval"
    rule_receipt = await rules_commands.evaluate_rule(
        session,
        rules_commands.EvaluateRuleCommand(idempotency_key=inner_key, rule_id=cmd.rule_id, inputs=cmd.inputs),
        actor_user_id,
    )
    evaluation = await session.get(RuleEvaluation, rule_receipt.aggregate_id)

    calc = ManufacturingCalculation(
        site_id=site_id, batch_id=cmd.batch_id, scope_type=cmd.scope_type, scope_id=cmd.scope_id,
        calculation_type="POTENCY", phase_code=cmd.phase_code, rule_object_id=rule.rule_object_id,
        rule_evaluation_id=evaluation.evaluation_id, input_refs=cmd.inputs, input_hash=sha256_hex(cmd.inputs),
        uom=cmd.uom, uom_id=await _resolve_uom_id(session, cmd.uom), result=evaluation.result,
        evaluated_by_user_id=actor_user_id, evaluated_at=datetime.now(timezone.utc),
        state="FAILED" if evaluation.outcome == "ERROR" else "CALCULATED", version=1,
    )
    session.add(calc)
    await session.flush()

    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=calc.site_id, aggregate_type="manufacturing_calculation",
        aggregate_id=calc.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type="YieldCalculated", event_payload={"id": str(calc.id), "state": calc.state, "result": calc.result},
        expected_version=None, command_type="EvaluatePotency",
    )


# ---------------------------------------------------------------------------------------------------
# Reconciliation — YLD-FR-009..014/019/020/021/024..027. Unsigned (Document 106 has no row for the
# calculation itself, only for `verify`).
# ---------------------------------------------------------------------------------------------------

class EvaluateReconciliationCommand(CommandEnvelope):
    batch_id: uuid.UUID
    reconciliation_type: str
    item_ref: dict
    quantities: dict  # {"issued": "100.000000", "consumed": "...", ...}
    uom: str
    tolerance_rule: dict  # {"type": "percentage"|"absolute", "value": "...", "inclusive": true}
    # YLD-FR-027: {"system": "ERP", "quantity": "...", "erp_run_id": "..."} -- compared after the GxP
    # calculation, never merged into it.
    external_reference: dict | None = None
    loss_reasons: list | None = None              # YLD-FR-021, required when approved_loss > 0
    linked_deviation_id: uuid.UUID | None = None  # YLD-FR-021, an existing QMS deviation


def _validate_loss_reasons(approved_loss: Decimal, loss_reasons: list | None) -> None:
    """YLD-FR-021 "Variance explained". An approved loss that carries no documented reason is an
    unexplained variance wearing an approved label, so a non-zero `approved_loss` fails closed without
    one. Each entry must name a `category` and a `description`; where entries carry a `quantity` they
    must account for the whole approved loss, so a partial explanation cannot pass as a complete one.

    The *category vocabulary* is deliberately not constrained here -- Document 17 says the reasons are
    "controlled" but no controlled-catalogue entity exists anywhere in the baseline to validate against,
    and inventing a closed enum would decide a customer's quality vocabulary for them (SG-135).
    """
    if approved_loss == 0:
        return
    if not loss_reasons:
        raise ValidationFailedError(
            "approved_loss requires at least one documented loss reason (YLD-FR-021)",
            approved_loss=str(approved_loss),
        )
    for i, entry in enumerate(loss_reasons):
        if not isinstance(entry, dict) or not str(entry.get("category", "")).strip() or not str(entry.get("description", "")).strip():
            raise ValidationFailedError(
                "each loss reason requires a non-empty category and description (YLD-FR-021)", index=i,
            )
    quantified = [e for e in loss_reasons if e.get("quantity") is not None]
    if quantified and len(quantified) == len(loss_reasons):
        try:
            total = sum((Decimal(str(e["quantity"])) for e in quantified), Decimal("0"))
        except InvalidOperation as exc:
            raise ValidationFailedError(f"Invalid loss-reason quantity: {exc}") from exc
        if total != approved_loss:
            raise ValidationFailedError(
                "loss reason quantities must account for the whole approved_loss (YLD-FR-021)",
                approved_loss=str(approved_loss), reasons_total=str(total),
            )


async def _compare_external_inventory(
    session: AsyncSession, *, external_reference: dict | None, accounted: Decimal, uom: str,
    reconciliation_type: str, batch_id: uuid.UUID, idempotency_key: str, actor_user_id: uuid.UUID,
) -> dict | None:
    """YLD-FR-027. Compares an ERP/WMS quantity against the GxP-computed total *after* the GxP
    calculation, and flags a discrepancy into Document 53's difference ledger through the ERP module's
    own command (`erp.commands.record_reconciliation_difference`) rather than writing erp tables here.

    The comparison never touches `variance`, `state` or any computed quantity -- "ERP never overwrites
    GxP evidence automatically" is the whole point of the requirement. The returned dict is recorded on
    the reconciliation row as evidence that the comparison ran and what it found.

    Flagging into ERP requires the caller to name the reconciliation run the difference belongs to
    (`external_reference.erp_run_id`); without one the comparison is still performed and recorded here,
    it simply has no ERP run to attach a difference to.
    """
    if not external_reference or external_reference.get("quantity") is None:
        return None
    try:
        external_quantity = Decimal(str(external_reference["quantity"]))
    except InvalidOperation as exc:
        raise ValidationFailedError(f"Invalid external_reference.quantity: {exc}") from exc

    difference = external_quantity - accounted
    result = {
        "system": external_reference.get("system"),
        "external_quantity": str(external_quantity),
        "gxp_accounted": str(accounted),
        "difference": str(difference),
        "uom": uom,
        "matched": difference == 0,
        "compared_at": datetime.now(timezone.utc).isoformat(),
        "erp_difference_id": None,
    }
    if difference == 0:
        return result

    erp_run_id = external_reference.get("erp_run_id")
    if erp_run_id is None:
        result["flagged"] = "not_recorded_in_erp_ledger: no erp_run_id supplied"
        return result

    receipt = await erp_commands.record_reconciliation_difference(
        session,
        erp_commands.RecordReconciliationDifferenceCommand(
            idempotency_key=f"{idempotency_key}:erp-diff",
            run_id=uuid.UUID(str(erp_run_id)),
            difference_type="VALUE_MISMATCH",
            internal_ref={"source": "SPEC-EBMR-008", "reconciliation_type": reconciliation_type, "batch_id": str(batch_id)},
            external_ref={k: v for k, v in external_reference.items() if k != "erp_run_id"},
            field_name="accounted_quantity",
            internal_value={"quantity": str(accounted), "uom": uom},
            external_value={"quantity": str(external_quantity), "uom": uom},
            # SG-124: no auto-resolve rule exists, so the difference opens OPEN and a human resolves it.
            # Whether an inventory mismatch should also hold QA is undefined (SG-136) -- not asserted here.
            requires_qa_hold=False,
        ),
        actor_user_id,
    )
    result["erp_difference_id"] = str(receipt.aggregate_id)
    return result


async def _persist_reconciliation(
    session: AsyncSession, *, cmd: CommandEnvelope, payload_hash: str, batch_id: uuid.UUID, site_id: uuid.UUID,
    reconciliation_type: str, item_ref: dict, quantities: dict, uom: str, tolerance_rule: dict,
    external_reference: dict | None, categories: tuple[str, ...], actor_user_id: uuid.UUID,
    device_unit_id: uuid.UUID | None = None, command_type: str = "EvaluateReconciliation",
    loss_reasons: list | None = None, linked_deviation_id: uuid.UUID | None = None,
) -> MutationReceipt:
    """The shared mass-balance evaluation. Callers resolve their own source quantities first (label
    reconciliation reads Document 16's counts, component reconciliation scopes to a Document 12 device
    unit); everything from the arithmetic down is identical for all four reconciliation types."""

    try:
        issued = Decimal(quantities["issued"])
        amounts = {k: Decimal(quantities.get(k, "0")) for k in categories}
    except (KeyError, InvalidOperation) as exc:
        raise ValidationFailedError(f"Invalid or missing quantity: {exc}") from exc

    # Document 17 §3's mass-balance formula, applied literally -- CALC-FR-010 (Document 110): division/
    # subtraction never silently produces a fabricated zero; Decimal end to end (AG-15).
    accounted = sum(amounts.values(), Decimal("0"))
    variance = issued - accounted

    # YLD-FR-021 -- checked before anything is written, so an unexplained approved loss never persists.
    _validate_loss_reasons(amounts.get("approved_loss", Decimal("0")), loss_reasons)

    # YLD-FR-021: the approval itself belongs to QMS, which owns the deviation lifecycle, the signed
    # disposition and deviation_number uniqueness (AG-05). Document 17 links to a deviation that already
    # exists; it never creates one. `linked_quality_event_id` carries QMS's own `quality_event_id`.
    linked_quality_event_id = None
    if linked_deviation_id is not None:
        deviation = await qms_service.get_deviation(session, linked_deviation_id)
        if deviation.site_id != site_id:
            raise ValidationFailedError(
                "Linked deviation belongs to a different site",
                deviation_id=str(linked_deviation_id), deviation_site_id=str(deviation.site_id), site_id=str(site_id),
            )
        linked_quality_event_id = deviation.quality_event_id

    tolerance_type = tolerance_rule.get("type", "absolute")
    tolerance_value = Decimal(str(tolerance_rule.get("value", "0")))
    inclusive = bool(tolerance_rule.get("inclusive", True))
    if tolerance_type == "percentage" and issued != 0:
        measured = abs(variance) / issued * 100
    else:
        measured = abs(variance)
    within = measured <= tolerance_value if inclusive else measured < tolerance_value

    # YLD-FR-027: strictly after the GxP calculation above, and with no path back into `variance`/`state`.
    external_comparison = await _compare_external_inventory(
        session, external_reference=external_reference, accounted=accounted, uom=uom,
        reconciliation_type=reconciliation_type, batch_id=batch_id,
        idempotency_key=cmd.idempotency_key, actor_user_id=actor_user_id,
    )

    rec = ReconciliationRecord(
        site_id=site_id, batch_id=batch_id, reconciliation_type=reconciliation_type, item_ref=item_ref,
        device_unit_id=device_unit_id, quantities={**quantities, "accounted": str(accounted)}, uom=uom,
        uom_id=await _resolve_uom_id(session, uom),
        tolerance_rule=tolerance_rule, variance=variance, external_reference=external_reference,
        external_comparison=external_comparison, loss_reasons=loss_reasons,
        linked_quality_event_id=linked_quality_event_id,
        evaluated_by_user_id=actor_user_id, state="ACCEPTABLE" if within else "OUT_OF_TOLERANCE", version=1,
    )
    session.add(rec)
    await session.flush()

    event_type = "MaterialReconciliationCalculated" if within else "ReconciliationFailed"
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=rec.site_id, aggregate_type="reconciliation_record",
        aggregate_id=rec.id, version=1, action="Created", actor_user_id=actor_user_id, reason=None, old_state=None,
        event_type=event_type, event_payload={"id": str(rec.id), "state": rec.state, "variance": str(variance)},
        expected_version=None, command_type=command_type,
    )


async def _evaluate_reconciliation(
    session: AsyncSession, cmd: EvaluateReconciliationCommand, actor_user_id: uuid.UUID, *, reconciliation_type: str,
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if reconciliation_type not in RECONCILIATION_TYPES:
        raise ValidationFailedError("Unrecognized reconciliation_type", allowed=list(RECONCILIATION_TYPES))
    if cmd.reconciliation_type != reconciliation_type:
        raise ValidationFailedError(
            "reconciliation_type must match the endpoint", expected=reconciliation_type, got=cmd.reconciliation_type
        )

    site_id = await _load_batch_site_id(session, cmd.batch_id)
    return await _persist_reconciliation(
        session, cmd=cmd, payload_hash=payload_hash, batch_id=cmd.batch_id, site_id=site_id,
        reconciliation_type=reconciliation_type, item_ref=cmd.item_ref, quantities=cmd.quantities, uom=cmd.uom,
        tolerance_rule=cmd.tolerance_rule, external_reference=cmd.external_reference,
        categories=QUANTITY_CATEGORIES, actor_user_id=actor_user_id,
        loss_reasons=cmd.loss_reasons, linked_deviation_id=cmd.linked_deviation_id,
    )


async def evaluate_material_reconciliation(session: AsyncSession, cmd: EvaluateReconciliationCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    return await _evaluate_reconciliation(session, cmd, actor_user_id, reconciliation_type="MATERIAL")


async def evaluate_packaging_reconciliation(session: AsyncSession, cmd: EvaluateReconciliationCommand, actor_user_id: uuid.UUID) -> MutationReceipt:
    return await _evaluate_reconciliation(session, cmd, actor_user_id, reconciliation_type="PACKAGING")


# --- YLD-FR-012: label reconciliation consumes Document 16's counts -----------------------------------


class EvaluateLabelReconciliationCommand(CommandEnvelope):
    """YLD-FR-012 takes a `packaging_run_id`, not quantities: the counts are Document 16's, and a caller
    that could supply its own would make this module a second, competing source of label accountability
    (AG-05). `batch_id` is derived from the packaging run for the same reason."""

    packaging_run_id: uuid.UUID
    tolerance_rule: dict
    # YLD-FR-027: {"system": "ERP", "quantity": "...", "erp_run_id": "..."} -- compared after the GxP
    # calculation, never merged into it.
    external_reference: dict | None = None
    loss_reasons: list | None = None              # YLD-FR-021, required when approved_loss > 0
    linked_deviation_id: uuid.UUID | None = None  # YLD-FR-021, an existing QMS deviation


async def evaluate_label_reconciliation(
    session: AsyncSession, cmd: EvaluateLabelReconciliationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """YLD-FR-012. Reads Document 16's `label_reconciliation` through packaging's own query interface and
    re-evaluates those counts against *this* module's tolerance rule, so a label discrepancy lands in the
    same batch-level release blocker as every other reconciliation type (the requirement's stated intent,
    "unified release blocker").

    Document 16 computes its own `calculated_variance` under an exact-balance default (SG-056, no released
    tolerance rule); Document 17 does not overwrite or trust that value -- it recomputes the mass balance
    from the issued/applied/... counts under the caller's tolerance rule, and records Document 16's own
    result alongside for audit.

    Category mapping: Document 16's `applied` is Document 17's `consumed` (a label applied to a pack is
    consumed); `returned`/`samples`/`rejected`/`destroyed` carry the same name in both. The requirement's
    "applicable waiver/profile rule" has no waiver or profile-rule concept anywhere in the baseline and is
    not implemented here -- see SG-134.
    """
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    source = await packaging_service.get_label_reconciliation_source(session, cmd.packaging_run_id)

    quantities = {
        "issued": str(Decimal(source["issued"])),
        "consumed": str(Decimal(source["applied"])),
        "returned": str(Decimal(source["returned"])),
        "samples": str(Decimal(source["samples"])),
        "rejected": str(Decimal(source["rejected"])),
        "destroyed": str(Decimal(source["destroyed"])),
    }
    item_ref = {
        "packaging_run_id": source["packaging_run_id"],
        "label_reconciliation_id": source["label_reconciliation_id"],
        "packaging_module_result": source["result"],
        "packaging_module_variance": str(source["calculated_variance"]),
    }

    return await _persist_reconciliation(
        session, cmd=cmd, payload_hash=payload_hash, batch_id=source["batch_id"], site_id=source["site_id"],
        reconciliation_type="LABEL", item_ref=item_ref, quantities=quantities, uom="each",
        tolerance_rule=cmd.tolerance_rule, external_reference=cmd.external_reference,
        categories=QUANTITY_CATEGORIES, actor_user_id=actor_user_id, command_type="EvaluateLabelReconciliation",
        loss_reasons=cmd.loss_reasons, linked_deviation_id=cmd.linked_deviation_id,
    )


# --- YLD-FR-013/026: component reconciliation is scoped to a Document 12 device unit ------------------


class EvaluateComponentReconciliationCommand(CommandEnvelope):
    """YLD-FR-013's "serialized/critical components". `device_unit_id` is the serialized case (Document
    12's per-unit identity); it stays optional for the "critical component" half of the requirement, which
    is reconciled at batch level and has no per-unit serial."""

    batch_id: uuid.UUID
    reconciliation_type: str = "COMPONENT"
    device_unit_id: uuid.UUID | None = None
    item_ref: dict
    quantities: dict  # issued/assembled/rejected/scrapped/returned/... (COMPONENT_QUANTITY_CATEGORIES)
    uom: str
    tolerance_rule: dict
    # YLD-FR-027: {"system": "ERP", "quantity": "...", "erp_run_id": "..."} -- compared after the GxP
    # calculation, never merged into it.
    external_reference: dict | None = None
    loss_reasons: list | None = None              # YLD-FR-021, required when approved_loss > 0
    linked_deviation_id: uuid.UUID | None = None  # YLD-FR-021, an existing QMS deviation


async def evaluate_component_reconciliation(
    session: AsyncSession, cmd: EvaluateComponentReconciliationCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    """YLD-FR-013. When a `device_unit_id` is supplied the unit is resolved through Document 12's own
    query interface (`device.service.get_unit`) and must belong to the same batch -- a component
    reconciliation attributed to a unit from another batch is a mis-scoped accountability record, so it
    fails closed rather than being written and reported later."""

    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)

    if cmd.reconciliation_type != "COMPONENT":
        raise ValidationFailedError(
            "reconciliation_type must match the endpoint", expected="COMPONENT", got=cmd.reconciliation_type
        )

    site_id = await _load_batch_site_id(session, cmd.batch_id)

    item_ref = dict(cmd.item_ref)
    if cmd.device_unit_id is not None:
        unit = await device_service.get_unit(session, cmd.device_unit_id)
        if unit.batch_id != cmd.batch_id:
            raise ValidationFailedError(
                "Device unit does not belong to this batch",
                device_unit_id=str(cmd.device_unit_id), unit_batch_id=str(unit.batch_id), batch_id=str(cmd.batch_id),
            )
        # The serial number is Document 12's field; recorded here as a denormalised audit label only --
        # `device_unit_id` remains the authoritative link (AG-05/AG-11).
        item_ref["device_unit_id"] = str(unit.id)
        item_ref["serial_number"] = unit.serial_number

    return await _persist_reconciliation(
        session, cmd=cmd, payload_hash=payload_hash, batch_id=cmd.batch_id, site_id=site_id,
        reconciliation_type="COMPONENT", item_ref=item_ref, quantities=cmd.quantities, uom=cmd.uom,
        tolerance_rule=cmd.tolerance_rule, external_reference=cmd.external_reference,
        categories=COMPONENT_QUANTITY_CATEGORIES, actor_user_id=actor_user_id,
        device_unit_id=cmd.device_unit_id, command_type="EvaluateComponentReconciliation",
        loss_reasons=cmd.loss_reasons, linked_deviation_id=cmd.linked_deviation_id,
    )


# ---------------------------------------------------------------------------------------------------
# Verify — Document 106 row 40. Qualified independent verifier, MUST NOT be the performer (SIG-FR-018).
# The one declared endpoint verifies either entity kind by id (the spec's own API list has exactly one
# `/reconciliation/v1/{id}/verify` operation, not one per entity type).
# ---------------------------------------------------------------------------------------------------


class VerifyRecordCommand(CommandEnvelope):
    record_kind: str  # "CALCULATION" | "RECONCILIATION"
    record_id: uuid.UUID
    expected_version: int
    challenge_id: uuid.UUID | None = None
    reauth_password: str | None = None


async def verify_record(
    session: AsyncSession, cmd: VerifyRecordCommand, actor_user_id: uuid.UUID
) -> MutationReceipt:
    payload_hash = sha256_hex(cmd.model_dump(mode="json"))
    existing = await check_idempotency(session, cmd.idempotency_key, payload_hash)
    if existing is not None:
        return _receipt_from_existing(existing)
    if cmd.record_kind not in ("CALCULATION", "RECONCILIATION"):
        raise ValidationFailedError("record_kind must be CALCULATION or RECONCILIATION")

    model = ManufacturingCalculation if cmd.record_kind == "CALCULATION" else ReconciliationRecord
    record_type = "manufacturing_calculation" if cmd.record_kind == "CALCULATION" else "reconciliation_record"
    result = await session.execute(select(model).where(model.id == cmd.record_id).with_for_update())
    record = result.scalar_one_or_none()
    if record is None:
        raise NotFoundError("Record not found")
    if record.version != cmd.expected_version:
        raise StaleVersionError("Record was modified since it was read", expected_version=cmd.expected_version, current_version=record.version)
    if record.state not in ("CALCULATED", "OUT_OF_LIMIT", "OUT_OF_TOLERANCE"):
        raise ValidationFailedError("Only a calculated (or out-of-limit/tolerance, post-disposition) record can be verified", current_state=record.state)
    if record.evaluated_by_user_id == actor_user_id:
        raise MissingSignatureError("Verifier must be independent of the performer (SIG-FR-018)", performer_id=str(record.evaluated_by_user_id))

    record_hash = calculation_record_hash(record) if cmd.record_kind == "CALCULATION" else reconciliation_record_hash(record)
    signature_id = await _resolve_signature(
        session, record_type=record_type, action="verify", actor_user_id=actor_user_id,
        record_version=record.version, record_hash=record_hash,
        challenge_id=cmd.challenge_id, reauth_password=cmd.reauth_password,
    )

    old_state = record.state
    record.state = "VERIFIED"
    record.verified_signature_id = signature_id
    record.verified_by_user_id = actor_user_id
    record.verified_at = datetime.now(timezone.utc)
    record.version += 1

    event_type = "YieldVerified" if cmd.record_kind == "CALCULATION" else "ReconciliationVerified"
    return await _write_receipt(
        session, cmd=cmd, payload_hash=payload_hash, site_id=record.site_id, aggregate_type=record_type,
        aggregate_id=record.id, version=record.version, action="Approved", actor_user_id=actor_user_id,
        reason=None, old_state=old_state, event_type=event_type, event_payload={"id": str(record.id), "state": record.state},
        expected_version=cmd.expected_version, command_type="VerifyRecord", signature_id=signature_id,
    )


# ---------------------------------------------------------------------------------------------------
# Read — GET /reconciliation/v1/batches/{batchId}/summary. YLD-FR-028/029: QA/Release visibility + the
# release-blocker flag.
# ---------------------------------------------------------------------------------------------------

_UNRESOLVED_STATES = ("FAILED", "OUT_OF_LIMIT", "OUT_OF_TOLERANCE")


def _aggregate_by_device_unit(reconciliations: list[ReconciliationRecord]) -> list[dict]:
    """YLD-FR-026: "aggregate serial-level data without losing exception visibility". Serial-scoped
    reconciliation rows are summed per device unit, and every unresolved row is listed by id on its own
    unit's entry -- an aggregate that only reported totals would hide exactly the exceptions the
    requirement says must stay visible. Decimal throughout; totals are emitted as strings (AG-15).

    This is a derived read over rows already in this transaction, not a stored projection: no regulated
    decision is taken from it (AG-11) -- `release_blocked` is still computed from the rows themselves.
    """
    grouped: dict[uuid.UUID, dict] = {}
    for rec in reconciliations:
        if rec.device_unit_id is None:
            continue
        entry = grouped.setdefault(
            rec.device_unit_id,
            {
                "device_unit_id": str(rec.device_unit_id),
                "serial_number": rec.item_ref.get("serial_number") if rec.item_ref else None,
                "record_count": 0, "totals": {}, "unresolved_record_ids": [],
            },
        )
        entry["record_count"] += 1
        for category, value in (rec.quantities or {}).items():
            try:
                amount = Decimal(str(value))
            except InvalidOperation:
                continue  # a non-numeric annotation in `quantities` is not part of the mass balance
            entry["totals"][category] = str(Decimal(entry["totals"].get(category, "0")) + amount)
        if rec.state in _UNRESOLVED_STATES:
            entry["unresolved_record_ids"].append(str(rec.id))

    return sorted(grouped.values(), key=lambda e: e["device_unit_id"])


async def get_batch_summary(session: AsyncSession, batch_id: uuid.UUID) -> dict:
    calculations = (
        await session.execute(select(ManufacturingCalculation).where(ManufacturingCalculation.batch_id == batch_id))
    ).scalars().all()
    reconciliations = (
        await session.execute(select(ReconciliationRecord).where(ReconciliationRecord.batch_id == batch_id))
    ).scalars().all()

    blocked = any(c.state in _UNRESOLVED_STATES for c in calculations) or any(r.state in _UNRESOLVED_STATES for r in reconciliations)

    return {
        "batch_id": str(batch_id),
        "release_blocked": blocked,
        "by_device_unit": _aggregate_by_device_unit(reconciliations),
        "calculations": [
            {
                "id": str(c.id), "calculation_type": c.calculation_type, "phase_code": c.phase_code,
                "scope_type": c.scope_type, "theoretical_quantity": str(c.theoretical_quantity) if c.theoretical_quantity is not None else None,
                "actual_quantity": str(c.actual_quantity) if c.actual_quantity is not None else None,
                "uom": c.uom, "uom_id": str(c.uom_id) if c.uom_id is not None else None,
                "result": c.result, "state": c.state, "min_percent": str(c.min_percent) if c.min_percent is not None else None,
                "max_percent": str(c.max_percent) if c.max_percent is not None else None,
                "verified": c.state == "VERIFIED", "version": c.version,
            }
            for c in calculations
        ],
        "reconciliations": [
            {
                "id": str(r.id), "reconciliation_type": r.reconciliation_type, "item_ref": r.item_ref,
                "device_unit_id": str(r.device_unit_id) if r.device_unit_id is not None else None,
                "quantities": r.quantities, "uom": r.uom, "uom_id": str(r.uom_id) if r.uom_id is not None else None,
                "tolerance_rule": r.tolerance_rule,
                "variance": str(r.variance) if r.variance is not None else None, "state": r.state,
                "loss_reasons": r.loss_reasons,
                "linked_quality_event_id": str(r.linked_quality_event_id) if r.linked_quality_event_id is not None else None,
                "external_comparison": r.external_comparison,
                "verified": r.state == "VERIFIED", "version": r.version,
            }
            for r in reconciliations
        ],
    }
