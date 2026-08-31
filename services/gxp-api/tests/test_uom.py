"""Document 110 (SPEC-GXP-008) §3 / SG-146 — the UOM/conversion authoring command surface. Mirrors
`test_rules.py`'s draft/release coverage of `RuleDefinition`: fails closed pending a Document 106
signature policy row, only a draft can be released, and a released UOM/conversion becomes usable by the
rules evaluator's own `unit_policy` resolution (tying SG-143's evaluator enforcement to SG-146's
authoring surface end to end).
"""

from app.core.security import hash_password
from app.modules.iam.models import User, UserSiteRole
from app.modules.rules.models import UnitOfMeasure, UomConversion
from app.modules.signature.models import SignaturePolicy
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login


async def _make_admin(db, seeded, username):
    user = User(
        username=username, email=f"{username}@example.com", full_name="Test Admin",
        password_hash=hash_password(DEMO_PASSWORD), status="active",
    )
    db.add(user)
    await db.flush()
    db.add(UserSiteRole(user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id))
    return user


def _uom_body(code, version=1, **overrides):
    body = {
        "idempotency_key": idem(), "code": code, "dimension": "MASS", "base_unit": "g",
        "factor": "1", "offset": "0", "precision_dp": 4, "version": version,
    }
    body.update(overrides)
    return body


async def test_uom_draft_release_fails_closed_pending_signature_policy(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.uom1")
    token = await login(client, "admin.uom1")

    resp = await client.post("/rules/v1/uom/drafts", json=_uom_body("MG-1"), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    uom_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/rules/v1/uom/{uom_id}/release",
        json={"idempotency_key": idem(), "uom_id": uom_id},
        headers=auth_headers(token),
    )
    assert resp.status_code == 409, resp.text
    assert resp.json()["code"] == "SIGNATURE_POLICY_UNRESOLVED"


async def test_uom_draft_and_release_happy_path(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.uom2")
        db.add(SignaturePolicy(record_type="uom", action="release", meaning="Released", signature_required=False))
    token = await login(client, "admin.uom2")

    resp = await client.post("/rules/v1/uom/drafts", json=_uom_body("KG-2"), headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    uom_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/rules/v1/uom/{uom_id}/release",
        json={"idempotency_key": idem(), "uom_id": uom_id},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    resp = await client.get("/rules/v1/uom/KG-2/versions", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    versions = resp.json()
    assert len(versions) == 1
    assert versions[0]["status"] == "released"
    # Numeric(38,18) round-trips at full DB precision, not the input's literal string form.
    from decimal import Decimal

    assert Decimal(versions[0]["factor"]) == Decimal("1")


async def test_uom_draft_rejects_duplicate_code_version(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.uom3")
    token = await login(client, "admin.uom3")

    body = _uom_body("L-3")
    resp = await client.post("/rules/v1/uom/drafts", json=body, headers=auth_headers(token))
    assert resp.status_code == 200, resp.text

    body2 = _uom_body("L-3")
    resp = await client.post("/rules/v1/uom/drafts", json=body2, headers=auth_headers(token))
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_uom_draft_rejects_non_positive_factor(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.uom4")
    token = await login(client, "admin.uom4")

    resp = await client.post(
        "/rules/v1/uom/drafts", json=_uom_body("ZERO-4", factor="0"), headers=auth_headers(token)
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_operator_cannot_author_uom(client, seeded):
    op_token = await login(client, "operator1")
    resp = await client.post("/rules/v1/uom/drafts", json=_uom_body("OP-5"), headers=auth_headers(op_token))
    assert resp.status_code == 403
    assert resp.json()["code"] == "ROLE_MISSING"


async def test_uom_conversion_draft_rejects_unknown_code(client, seeded, db):
    async with db.begin():
        await _make_admin(db, seeded, "admin.uom6")
    token = await login(client, "admin.uom6")

    resp = await client.post(
        "/rules/v1/uom-conversions/drafts",
        json={
            "idempotency_key": idem(), "from_code": "NOPE-A", "to_code": "NOPE-B",
            "factor": "1000", "rounding_stage": "none",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 422, resp.text
    assert resp.json()["code"] == "VALIDATION_FAILED"


async def test_uom_conversion_end_to_end_through_the_rules_evaluator(client, seeded, db):
    """Ties SG-146's authoring surface to SG-143's evaluator enforcement: a conversion authored and
    released through these commands is exactly what `rules_service.resolve_conversion` (and therefore a
    released rule's own `unit_policy.convert_to`) resolves against."""
    async with db.begin():
        await _make_admin(db, seeded, "admin.uom7")
        db.add(SignaturePolicy(record_type="uom", action="release", meaning="Released", signature_required=False))
        db.add(SignaturePolicy(record_type="uom_conversion", action="release", meaning="Released", signature_required=False))
    token = await login(client, "admin.uom7")

    for code in ("MG-7", "G-7"):
        resp = await client.post("/rules/v1/uom/drafts", json=_uom_body(code), headers=auth_headers(token))
        assert resp.status_code == 200, resp.text
        uom_id = resp.json()["aggregate_id"]
        resp = await client.post(
            f"/rules/v1/uom/{uom_id}/release", json={"idempotency_key": idem(), "uom_id": uom_id},
            headers=auth_headers(token),
        )
        assert resp.status_code == 200, resp.text

    resp = await client.post(
        "/rules/v1/uom-conversions/drafts",
        json={
            "idempotency_key": idem(), "from_code": "MG-7", "to_code": "G-7",
            "factor": "0.001", "rounding_stage": "none",
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    conversion_id = resp.json()["aggregate_id"]
    resp = await client.post(
        f"/rules/v1/uom-conversions/{conversion_id}/release",
        json={"idempotency_key": idem(), "conversion_id": conversion_id},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text

    # A rule declaring unit_policy = {"measured": {"uom": "MG-7", "convert_to": "G-7"}} now resolves.
    resp = await client.post(
        "/rules/v1/drafts",
        json={
            "idempotency_key": idem(), "rule_id": "UOM-E2E-RULE", "rule_type": "tolerance", "semantic_version": "1.0.0",
            "expression_ast": {"op": "lte", "args": [{"var": "measured"}, {"var": "limit"}]},
            "input_contract": {"measured": {"type": "decimal"}, "limit": {"type": "decimal"}},
            "output_contract": {"within_tolerance": {"type": "boolean"}},
            "unit_policy": {"measured": {"uom": "MG-7", "convert_to": "G-7"}},
            "precision_policy": {"calculation_class": "CC-3"},
            "rounding_policy": {"policy_version": "DOCUMENT-110-v1.0"},
        },
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    rule_object_id = resp.json()["aggregate_id"]

    resp = await client.post(
        f"/rules/v1/{rule_object_id}/simulate",
        json={"inputs": {"measured": "5000", "limit": "10"}},  # 5000 mg -> 5 g, within a 10 g limit
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["result"] is True
