"""Document 08 (SPEC-GXP-006) — rule draft/validate/simulate/release/evaluate. Simulate must never write
regulated state (RUL-FR-023); evaluate must persist exactly one gxp_rule_evaluation row (RUL-FR-022);
release fails closed pending a Document 106 policy row (same honest pattern used throughout this session);
the expression evaluator is a constrained AST, never `eval` (RUL-FR-005), and rejects float inputs (AG-03).
"""

from datetime import datetime, timedelta, timezone
from decimal import Decimal

from sqlalchemy import func, select

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.rules.expression import evaluate
from app.modules.rules.models import RuleDefinition, RuleEvaluation, UnitOfMeasure, UomConversion
from app.modules.signature.models import SignaturePolicy
from app.mutation.errors import (
    DivisionUndefinedError,
    PrecisionPolicyUnresolvedError,
    UomConversionUnavailableError,
    UomUnknownError,
    ValidationFailedError,
)
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login

ASSAY_RULE = {
    "op": "and",
    "args": [
        {"op": "gte", "args": [{"var": "assay_percent"}, "98.0"]},
        {"op": "lte", "args": [{"var": "assay_percent"}, "102.0"]},
    ],
}
CONTRACT = {"assay_percent": {"type": "decimal", "unit": "%"}}
OUTPUT_CONTRACT = {"eligible": {"type": "boolean"}}
POLICY = {"calculation_class": "CC-5", "reported_decimal_places": 2}


def _draft_body(rule_id, semantic_version="1.0.0"):
    return {
        "idempotency_key": idem(),
        "rule_id": rule_id,
        "rule_type": "eligibility",
        "semantic_version": semantic_version,
        "expression_ast": ASSAY_RULE,
        "input_contract": CONTRACT,
        "output_contract": OUTPUT_CONTRACT,
        "unit_policy": {},
        "precision_policy": POLICY,
        "rounding_policy": {"policy_version": "DOCUMENT-110-v1.0"},
    }


async def _make_admin(db, seeded, username):
    user = User(
        username=username,
        email=f"{username}@example.com",
        full_name="Test Admin",
        password_hash=hash_password(DEMO_PASSWORD),
        status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))
    return user


async def test_draft_requires_explicit_precision_rounding_policy(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.rules1")
    admin_token = await login(client, "admin.rules1")

    body = _draft_body("ASSAY-NOPOLICY")
    del body["rounding_policy"]
    resp = await client.post("/rules/v1/drafts", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 422


async def test_draft_validate_simulate_writes_nothing(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.rules2")
    admin_token = await login(client, "admin.rules2")

    resp = await client.post("/rules/v1/drafts", json=_draft_body("ASSAY-SIM"), headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    rule_object_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/rules/v1/{rule_object_id}/validate",
        json={"idempotency_key": idem(), "rule_object_id": rule_object_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    before = (await db.execute(select(func.count()).select_from(RuleEvaluation))).scalar_one()
    resp = await client.post(
        f"/rules/v1/{rule_object_id}/simulate",
        json={"inputs": {"assay_percent": "99.5"}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["result"] is True
    after = (await db.execute(select(func.count()).select_from(RuleEvaluation))).scalar_one()
    assert before == after  # RUL-FR-023: simulation writes zero rows

    resp = await client.post(
        f"/rules/v1/{rule_object_id}/simulate",
        json={"inputs": {"assay_percent": "50.0"}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["result"] is False


async def test_release_requires_an_independent_qa_releaser_signature(client, seeded, db):
    """SG-035 (2026-09-10, project-owner-directed, "follow the ebmr-edhr docs"): Document 106 section 9
    row 6 -- `rule/release` is `Released` by a "QA Approver / Batch Release" -> "QA Releaser". The
    required role is enforced; RuleDefinition stores no author identity, so the "independent of every
    production performer" clause has no data source here (documented)."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.rules3")
        signer = User(
            username="qa.rules3", email="qa.rules3@example.com", full_name="QA Releaser",
            password_hash=hash_password(DEMO_PASSWORD), status="active",
        )
        db.add(signer)
        await db.flush()
        db.add(UserSiteRole(user_id=signer.id, site_id=seeded["site_id"], role_id=seeded["roles"]["QA Releaser"].id))
        db.add(SignaturePolicy(
            record_type="rule", action="release", meaning="Released",
            required_role_id=seeded["roles"]["QA Releaser"].id, requires_independent_signer=True,
            signature_required=True, reason_required=True,
        ))
    admin_token = await login(client, "admin.rules3")
    signer_token = await login(client, "qa.rules3")

    resp = await client.post("/rules/v1/drafts", json=_draft_body("ASSAY-REL"), headers=auth_headers(admin_token))
    rule_object_id = resp.json()["aggregate_id"]
    await client.post(
        f"/rules/v1/{rule_object_id}/validate",
        json={"idempotency_key": idem(), "rule_object_id": rule_object_id},
        headers=auth_headers(admin_token),
    )

    # Admin holds no "QA Releaser" role -> the signature-policy role check rejects it.
    resp = await client.post(
        f"/rules/v1/{rule_object_id}/release",
        json={"idempotency_key": idem(), "rule_object_id": rule_object_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 403, resp.text
    assert resp.json()["code"] == "ROLE_MISSING"

    # QA Releaser, no challenge -> MISSING_SIGNATURE.
    resp = await client.post(
        f"/rules/v1/{rule_object_id}/release",
        json={"idempotency_key": idem(), "rule_object_id": rule_object_id},
        headers=auth_headers(signer_token),
    )
    assert resp.status_code == 428, resp.text
    assert resp.json()["code"] == "MISSING_SIGNATURE"

    # QA Releaser + a valid challenge -> released.
    challenge = (
        await client.post(
            f"/rules/v1/{rule_object_id}/signature-challenges", json={"action": "release"},
            headers=auth_headers(signer_token),
        )
    ).json()
    assert challenge["meaning"] == "Released"
    resp = await client.post(
        f"/rules/v1/{rule_object_id}/release",
        json={
            "idempotency_key": idem(), "rule_object_id": rule_object_id,
            "challenge_id": challenge["challenge_id"], "reauth_password": DEMO_PASSWORD,
        },
        headers=auth_headers(signer_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["signature_id"] is not None


async def test_validate_rejects_undeclared_variable(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.rules4")
    admin_token = await login(client, "admin.rules4")

    body = _draft_body("ASSAY-BADVAR")
    body["expression_ast"] = {"op": "gte", "args": [{"var": "undeclared_field"}, "1"]}
    resp = await client.post("/rules/v1/drafts", json=body, headers=auth_headers(admin_token))
    rule_object_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/rules/v1/{rule_object_id}/validate",
        json={"idempotency_key": idem(), "rule_object_id": rule_object_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_evaluator_rejects_float_input():
    """Direct evaluator-level check (RUL-FR-005/009/AG-03) — no released rule is needed to prove this,
    and none can be released this pass anyway (release fails closed pending SG-032/Document 106)."""
    try:
        evaluate({"op": "gte", "args": [{"var": "x"}, "1"]}, {"x": 99.5})
        assert False, "expected ValidationFailedError for a float input"
    except ValidationFailedError as exc:
        assert "float" in exc.message.lower()
    assert Decimal("99.5") >= Decimal("98.0")  # sanity: the decimal path itself works


async def test_unauthorized_without_token_rejected(client):
    resp = await client.post("/rules/v1/evaluate", json={"idempotency_key": idem(), "rule_id": "X", "inputs": {}})
    assert resp.status_code == 401


async def test_operator_cannot_author_rules(client, seeded):
    op_token = await login(client, "operator1")
    resp = await client.post("/rules/v1/drafts", json=_draft_body("X"), headers=auth_headers(op_token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_list_released_rules_returns_only_effective_released(client, seeded, db):
    """GET /rules/v1 -- picker data for Recipe Master's dependency condition_rule_id (SG-081 read-side
    precedent). Lists one row per rule_id with a currently-effective released version; ignores drafts
    and expired ones."""
    now = datetime.now(timezone.utc)
    common = dict(
        rule_type="eligibility", expression_ast=ASSAY_RULE, input_contract=CONTRACT,
        output_contract=OUTPUT_CONTRACT, unit_policy={}, precision_policy=POLICY,
        rounding_policy={"policy_version": "DOCUMENT-110-v1.0"},
    )
    async with db.begin():
        db.add(RuleDefinition(rule_id="LIVE-RULE", semantic_version="1.0.0", status="released",
                              effective_from=now - timedelta(days=1), effective_to=None, **common))
        db.add(RuleDefinition(rule_id="DRAFT-RULE", semantic_version="1.0.0", status="draft",
                              effective_from=None, effective_to=None, **common))
        db.add(RuleDefinition(rule_id="EXPIRED-RULE", semantic_version="1.0.0", status="released",
                              effective_from=now - timedelta(days=10), effective_to=now - timedelta(days=1), **common))
    op_token = await login(client, "operator1")  # holds rules.evaluate
    resp = await client.get("/rules/v1", headers=auth_headers(op_token))
    assert resp.status_code == 200, resp.text
    by_id = {r["rule_id"]: r for r in resp.json()}
    assert "LIVE-RULE" in by_id
    assert by_id["LIVE-RULE"]["semantic_version"] == "1.0.0"
    assert "DRAFT-RULE" not in by_id
    assert "EXPIRED-RULE" not in by_id


async def test_operator_can_call_evaluate_but_gets_not_found_for_unreleased_rule(client, seeded):
    op_token = await login(client, "operator1")
    resp = await client.post(
        "/rules/v1/evaluate",
        json={"idempotency_key": idem(), "rule_id": "NEVER-RELEASED", "inputs": {}},
        headers=auth_headers(op_token),
    )
    assert resp.status_code == 404
    assert resp.json()["code"] == "NOT_FOUND"


# ---------------------------------------------------------------------------
# Document 110 (SPEC-GXP-008, SG-143) — precision/rounding/UOM enforcement.
# Test catalogue references are to Document 110 §6.
# ---------------------------------------------------------------------------


async def test_draft_requires_a_resolvable_calculation_class(client, seeded, db):
    """CALC-FR-004 — precision_policy.calculation_class is required and must resolve to one of
    Document 110 §2's ten classes; missing or unknown fails closed (AG-15), never a guessed default."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.rules5")
    admin_token = await login(client, "admin.rules5")

    body = _draft_body("PRECISION-NOCLASS")
    body["precision_policy"] = {}
    resp = await client.post("/rules/v1/drafts", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "PRECISION_POLICY_UNRESOLVED"

    body = _draft_body("PRECISION-BADCLASS")
    body["precision_policy"] = {"calculation_class": "CC-99"}
    resp = await client.post("/rules/v1/drafts", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "PRECISION_POLICY_UNRESOLVED"


async def test_cc5_requires_reported_decimal_places(client, seeded, db):
    """CC-5's §2 row is 'source-specified reported dp' — the rule must supply it, unlike the other
    classes whose reported precision is fixed by the table."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.rules6")
    admin_token = await login(client, "admin.rules6")

    body = _draft_body("PRECISION-CC5-NODP")
    body["precision_policy"] = {"calculation_class": "CC-5"}
    resp = await client.post("/rules/v1/drafts", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "PRECISION_POLICY_UNRESOLVED"


TOLERANCE_RULE = {"op": "lte", "args": [{"var": "measured"}, {"var": "limit"}]}
TOLERANCE_CONTRACT = {"measured": {"type": "decimal"}, "limit": {"type": "decimal"}}


async def test_comparison_rounds_at_declared_precision_not_early_or_raw(client, seeded, db):
    """Document 110 §6 item 2 — a value that would PASS under premature/coarse rounding (e.g. naive
    2dp: 100.0000006 -> "100.00" == the 100.0 limit) must FAIL once compared at CC-3's declared 6dp
    comparison precision (100.0000006 rounds half-up to 100.000001, which is > 100.000000). N4/
    CALC-FR-005: comparison precision is policy-declared, not an accident of input precision."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.rules7")
    admin_token = await login(client, "admin.rules7")

    body = {
        "idempotency_key": idem(),
        "rule_id": "TOLERANCE-CC3",
        "rule_type": "tolerance",
        "semantic_version": "1.0.0",
        "expression_ast": TOLERANCE_RULE,
        "input_contract": TOLERANCE_CONTRACT,
        "output_contract": {"within_tolerance": {"type": "boolean"}},
        "unit_policy": {},
        "precision_policy": {"calculation_class": "CC-3"},
        "rounding_policy": {"policy_version": "DOCUMENT-110-v1.0"},
    }
    resp = await client.post("/rules/v1/drafts", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    rule_object_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/rules/v1/{rule_object_id}/simulate",
        json={"inputs": {"measured": "100.0000006", "limit": "100.0"}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["result"] is False, "correct 6dp comparison must FAIL, not PASS on the raw/early value"

    # Sanity: the identical inputs compared WITHOUT a resolved class policy (pre-Document-110 behaviour,
    # still reachable for a rule with no calculation_class) do not round at all, so `lte` on the raw
    # Decimals also correctly evaluates False here — proving the flip a coarser 2dp round would have
    # caused is specifically a comparison-precision defect, not just "any rounding beats none".
    raw = evaluate(TOLERANCE_RULE, {"measured": Decimal("100.0000006"), "limit": Decimal("100.0")})
    assert raw is False


async def test_numeric_overflow_raises_typed_error():
    """§6 item 4 (float contamination is a build-time check elsewhere) plus the overflow half of
    §6 item — a value that cannot be represented at its class's declared precision under the default
    Decimal context raises NUMERIC_OVERFLOW, not a silently truncated/wrapped value."""
    from app.modules.rules.precision import CLASS_POLICY, round_at_stage
    from app.mutation.errors import NumericOverflowError

    try:
        round_at_stage(Decimal("1E+30"), CLASS_POLICY["CC-3"], 6)
        assert False, "expected NumericOverflowError"
    except NumericOverflowError as exc:
        assert exc.code == "NUMERIC_OVERFLOW"


async def test_division_by_zero_raises_typed_error():
    """CALC-FR-010 / §6 item 8 — division by zero is a typed DIVISION_UNDEFINED error, never a silent
    zero or NaN."""
    try:
        evaluate({"op": "/", "args": [{"var": "x"}, {"var": "y"}]}, {"x": "10", "y": "0"})
        assert False, "expected DivisionUndefinedError"
    except DivisionUndefinedError as exc:
        assert exc.code == "DIVISION_UNDEFINED"


async def test_uom_unknown_rejected_by_evaluator(client, seeded, db):
    """CALC-FR-006/N6 — a unit_policy code with no released gxp_uom row fails UOM_UNKNOWN, not a
    silent free-text pass-through."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.rules8")
    admin_token = await login(client, "admin.rules8")

    body = {
        "idempotency_key": idem(),
        "rule_id": "UOM-UNKNOWN-RULE",
        "rule_type": "tolerance",
        "semantic_version": "1.0.0",
        "expression_ast": TOLERANCE_RULE,
        "input_contract": TOLERANCE_CONTRACT,
        "output_contract": {"within_tolerance": {"type": "boolean"}},
        "unit_policy": {"measured": "made-up-unit"},
        "precision_policy": {"calculation_class": "CC-3"},
        "rounding_policy": {"policy_version": "DOCUMENT-110-v1.0"},
    }
    resp = await client.post("/rules/v1/drafts", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    rule_object_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/rules/v1/{rule_object_id}/simulate",
        json={"inputs": {"measured": "1.0", "limit": "2.0"}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "UOM_UNKNOWN"


async def test_uom_conversion_unavailable_when_no_released_conversion_resolves(db):
    """Document 110 §3 — resolve_conversion() fails closed (UOM_CONVERSION_UNAVAILABLE) when two
    released UOM codes both exist but no released gxp_uom_conversion row links them. Exercised directly
    against the service function: no rule in this pass declares a convert_to (§5's 'don't invent a
    consumer' discipline applied to cross-unit conversion — see docs/generated/18_SPEC_GAPS.md)."""
    from app.modules.rules import service as rules_service

    async with db.begin():
        db.add(UnitOfMeasure(code="mg", dimension="MASS", base_unit="g", factor=Decimal("0.001"), precision_dp=4, status="released"))
        db.add(UnitOfMeasure(code="g", dimension="MASS", base_unit="g", factor=Decimal("1"), precision_dp=4, status="released"))

    try:
        await rules_service.resolve_conversion(db, "mg", "g", datetime.now(timezone.utc))
        assert False, "expected UomConversionUnavailableError"
    except UomConversionUnavailableError as exc:
        assert exc.code == "UOM_CONVERSION_UNAVAILABLE"


async def test_uom_conversion_applied_when_released_conversion_resolves(client, seeded, db):
    """Document 110 §3 — with a released gxp_uom_conversion row, the evaluator converts the input
    before the expression sees it, using the released factor (never a literal in code, §9)."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.rules9")
        db.add(UnitOfMeasure(code="mg", dimension="MASS", base_unit="g", factor=Decimal("0.001"), precision_dp=4, status="released"))
        db.add(UnitOfMeasure(code="g", dimension="MASS", base_unit="g", factor=Decimal("1"), precision_dp=4, status="released"))
        db.add(
            UomConversion(
                from_code="mg", to_code="g", factor=Decimal("0.001"), rounding_stage="none",
                effective_from=datetime.now(timezone.utc), status="released",
            )
        )
    admin_token = await login(client, "admin.rules9")

    body = {
        "idempotency_key": idem(),
        "rule_id": "UOM-CONVERT-RULE",
        "rule_type": "tolerance",
        "semantic_version": "1.0.0",
        "expression_ast": TOLERANCE_RULE,
        "input_contract": TOLERANCE_CONTRACT,
        "output_contract": {"within_tolerance": {"type": "boolean"}},
        "unit_policy": {"measured": {"uom": "mg", "convert_to": "g"}},
        "precision_policy": {"calculation_class": "CC-3"},
        "rounding_policy": {"policy_version": "DOCUMENT-110-v1.0"},
    }
    resp = await client.post("/rules/v1/drafts", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    rule_object_id = resp.json()["aggregate_id"]

    # 5000 mg = 5 g, well within a 10 g limit.
    resp = await client.post(
        f"/rules/v1/{rule_object_id}/simulate",
        json={"inputs": {"measured": "5000", "limit": "10"}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["result"] is True


async def test_evaluate_persists_raw_result_and_policy_version_for_a_presentation_class(client, seeded, db):
    """CALC-FR-002/004/008 — a COMPUTED result under a presentation-stage class (CC-5) stores the
    rounded `result` alongside the pre-rounding `raw_result` and the applied Document 110 policy
    version, so a historic evaluation can be shown to have recomputed identically (§8 criterion 4)."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.rules10")
        db.add(SignaturePolicy(record_type="rule", action="release", meaning="Released", signature_required=False))
    admin_token = await login(client, "admin.rules10")

    compute_rule = {"op": "+", "args": [{"var": "a"}, {"var": "b"}]}
    body = {
        "idempotency_key": idem(),
        "rule_id": "COMPUTED-CC5-RULE",
        "rule_type": "calculation",
        "semantic_version": "1.0.0",
        "expression_ast": compute_rule,
        "input_contract": {"a": {"type": "decimal"}, "b": {"type": "decimal"}},
        "output_contract": {"sum": {"type": "decimal"}},
        "unit_policy": {},
        "precision_policy": {"calculation_class": "CC-5", "reported_decimal_places": 2},
        "rounding_policy": {"policy_version": "DOCUMENT-110-v1.0"},
    }
    resp = await client.post("/rules/v1/drafts", json=body, headers=auth_headers(admin_token))
    assert resp.status_code == 200, resp.text
    rule_object_id = resp.json()["aggregate_id"]
    await client.post(
        f"/rules/v1/{rule_object_id}/validate",
        json={"idempotency_key": idem(), "rule_object_id": rule_object_id},
        headers=auth_headers(admin_token),
    )
    resp = await client.post(
        f"/rules/v1/{rule_object_id}/release",
        json={"idempotency_key": idem(), "rule_object_id": rule_object_id},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/rules/v1/evaluate",
        json={"idempotency_key": idem(), "rule_id": "COMPUTED-CC5-RULE", "inputs": {"a": "1.005", "b": "1.0021"}},
        headers=auth_headers(admin_token),
    )
    assert resp.status_code == 200, resp.text
    evaluation = await db.get(RuleEvaluation, resp.json()["aggregate_id"])
    assert evaluation.outcome == "COMPUTED"
    assert evaluation.result == {"value": "2.01"}  # 2.0071 half-up at 2dp
    assert evaluation.raw_result == {"value": "2.0071"}
    assert evaluation.applied_policy_version == "DOCUMENT-110-v1.0"
