"""Contract conformance tests for Document 101 (SPEC-ENG-005) / Document 113 (SPEC-ENG-009).

These are the executable form of Document 113 §8's test catalogue items that can be checked against the
committed contracts themselves rather than against a running transaction. They are deliberately
*static*: they read `contracts/openapi/*.yaml` and the app's own route table, and touch no database, so
they run in the CI contract gate without fixtures.

Scope: the five WP-01 GxP Core contracts committed this pass (spec-gxp-001/002/003/004/006). The eight
contracts written before the gate existed carry 107 known violations recorded under SG-013; asserting
over them here would either fail the suite for pre-existing debt or require weakening the assertion, so
they are covered by a separate reporting test that records the count without failing.
"""

import sys
from pathlib import Path

import pytest
import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_DIR = REPO_ROOT / "contracts" / "openapi"
TOOLING = REPO_ROOT / "ebmr-edhr" / "tooling" / "contracts"

sys.path.insert(0, str(TOOLING))
import validate as contract_validate  # noqa: E402

WP01_CONTRACTS = [
    "spec-gxp-001.yaml",
    "spec-gxp-002.yaml",
    "spec-gxp-003.yaml",
    "spec-gxp-004.yaml",
    "spec-gxp-006.yaml",
]

# The surfaces the WP-01 contracts claim to cover completely.
WP01_SURFACES = ("/audit/v1", "/vault/v1", "/rules/v1")


def _load(name: str) -> dict:
    return yaml.safe_load((CONTRACT_DIR / name).read_text())


@pytest.fixture(scope="module")
def docs() -> dict[str, dict]:
    return {name: _load(name) for name in WP01_CONTRACTS}


@pytest.fixture(scope="module")
def all_docs() -> dict[str, dict]:
    """Every parseable contract, needed so cross-file $refs resolve."""
    out = {}
    for path in sorted(CONTRACT_DIR.glob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text())
        except yaml.YAMLError:
            continue
        if isinstance(doc, dict):
            out[path.name] = doc
    return out


@pytest.fixture(scope="module")
def implemented() -> set[tuple[str, str]]:
    from app.main import app

    spec = app.openapi()
    return {
        (path, method.upper())
        for path, item in spec["paths"].items()
        for method in item
        if method in contract_validate.HTTP_METHODS
    }


# --- Parseability and OpenAPI 3.1 (Document 113 §1) -------------------------------------------------


@pytest.mark.parametrize("name", WP01_CONTRACTS)
def test_contract_is_parseable_openapi_31(name: str, docs: dict[str, dict]) -> None:
    doc = docs[name]
    assert str(doc["openapi"]).startswith("3.1"), f"{name} must declare OpenAPI 3.1"
    assert any(k in doc for k in ("paths", "components", "webhooks")), name
    assert doc["info"]["title"].startswith("SPEC-GXP-"), name


@pytest.mark.parametrize("name", WP01_CONTRACTS)
def test_every_ref_resolves(name: str, docs: dict[str, dict], all_docs: dict[str, dict]) -> None:
    """Local and cross-file $refs both resolve. The cross-file case is what makes the shared-envelope
    decision safe: spec-gxp-003/004/006 $ref spec-gxp-001 by relative path.
    """
    findings = contract_validate.Findings()
    contract_validate.check_refs(name, docs[name], all_docs, findings)
    assert findings.items == [], findings.items


# --- CTRC-FR-003 / MUT-FR-005 / Document 113 §3 F6 -------------------------------------------------


@pytest.mark.parametrize("name", WP01_CONTRACTS)
def test_command_payloads_are_closed(name: str, docs: dict[str, dict]) -> None:
    findings = contract_validate.Findings()
    contract_validate.check_closed_payloads(name, docs[name], findings)
    assert findings.items == [], findings.items


def test_every_command_schema_requires_an_idempotency_key(docs: dict[str, dict]) -> None:
    """Document 113 §5 I1: every state-changing operation accepts an idempotency key."""
    checked = 0
    for name, doc in docs.items():
        for schema_name, schema in ((doc.get("components") or {}).get("schemas") or {}).items():
            if not schema_name.endswith("Command"):
                continue
            checked += 1
            assert "idempotency_key" in (schema.get("required") or []), f"{name}:{schema_name}"
    assert checked >= 8, f"expected the WP-01 command schemas, found {checked}"


# --- CTRC-FR-009 / CTR-FR-032 ----------------------------------------------------------------------


@pytest.mark.parametrize("name", WP01_CONTRACTS)
def test_schemas_and_operations_carry_requirement_ids(name: str, docs: dict[str, dict]) -> None:
    findings = contract_validate.Findings()
    contract_validate.check_traceability(name, docs[name], findings)
    assert findings.items == [], findings.items


@pytest.mark.parametrize("name", WP01_CONTRACTS)
def test_requirement_ids_use_a_known_namespace(name: str, docs: dict[str, dict]) -> None:
    """A traceability link is only useful if it points at a real requirement namespace."""
    # CALC-FR- added closing SG-146: Document 110's requirement namespace, first referenced in
    # spec-gxp-006.yaml's UOM authoring operations (CR-003).
    known = (
        "MUT-FR-", "SIG-FR-", "AUD-FR-", "VLT-FR-", "RUL-FR-", "CTR-FR-", "CTRC-FR-", "DATA-FR-", "CALC-FR-",
    )
    doc = docs[name]
    ids: list[str] = []
    for _p, _m, op in contract_validate.iter_operations(doc):
        ids += op.get("x-requirement-ids") or []
    for schema in ((doc.get("components") or {}).get("schemas") or {}).values():
        if isinstance(schema, dict):
            ids += schema.get("x-requirement-ids") or []
    assert ids, name
    bad = [i for i in ids if not i.startswith(known)]
    assert bad == [], f"{name}: unknown requirement namespaces {sorted(set(bad))}"


# --- CTR-FR-002 ------------------------------------------------------------------------------------


def test_operation_ids_are_unique_across_all_contracts(all_docs: dict[str, dict]) -> None:
    findings = contract_validate.Findings()
    contract_validate.check_operation_ids(all_docs, findings)
    assert findings.items == [], findings.items


# --- CTRC-FR-002 envelope conformance --------------------------------------------------------------


@pytest.mark.parametrize("name", WP01_CONTRACTS)
def test_envelopes_are_canonical(name: str, docs: dict[str, dict]) -> None:
    findings = contract_validate.Findings()
    contract_validate.check_envelopes(name, docs[name], findings)
    assert findings.items == [], findings.items


def test_canonical_envelopes_are_defined_exactly_once(docs: dict[str, dict]) -> None:
    """The shared-envelope decision: only spec-gxp-001 defines them; the rest $ref it."""
    for envelope in ("CommandEnvelope", "MutationReceipt", "ErrorResponse", "PageEnvelope"):
        owners = [
            name
            for name, doc in docs.items()
            if envelope in ((doc.get("components") or {}).get("schemas") or {})
        ]
        assert owners == ["spec-gxp-001.yaml"], f"{envelope} defined in {owners}"


def test_mutation_receipt_matches_the_built_pydantic_model() -> None:
    """CTRC-FR-002 against the code rather than another document: the committed MutationReceipt must
    have exactly the fields `app.mutation.schemas.MutationReceipt` returns.
    """
    from app.mutation.schemas import MutationReceipt

    schema = _load("spec-gxp-001.yaml")["components"]["schemas"]["MutationReceipt"]
    assert set(schema["properties"]) == set(MutationReceipt.model_fields)
    built_required = {n for n, f in MutationReceipt.model_fields.items() if f.is_required()}
    assert set(schema["required"]) == built_required


def test_command_envelope_matches_the_built_pydantic_model() -> None:
    from app.mutation.schemas import CommandEnvelope

    schema = _load("spec-gxp-001.yaml")["components"]["schemas"]["CommandEnvelope"]
    assert set(schema["properties"]) == set(CommandEnvelope.model_fields)
    assert schema["additionalProperties"] is False
    assert CommandEnvelope.model_config["extra"] == "forbid"


def test_platform_error_codes_match_the_raised_exception_classes() -> None:
    """CTRC-FR-004: the registry contains every code the platform kernel can return, and no code that
    nothing raises. Module-specific codes live in their own module's contract, so only the classes
    defined at the platform level are compared.
    """
    from app.mutation import errors

    declared = set(_load("spec-gxp-001.yaml")["components"]["schemas"]["PlatformErrorCode"]["enum"])
    # The platform classes, i.e. everything above the first module-specific registry in errors.py.
    platform = {
        errors.GxPError, errors.UnauthorizedError, errors.ForbiddenError, errors.ValidationFailedError,
        errors.StaleVersionError, errors.InvalidTransitionError, errors.MissingSignatureError,
        errors.SignatureChallengeInvalidError, errors.RoleMissingError, errors.SodConflictError,
        errors.SignaturePolicyUnresolvedError, errors.IdempotencyConflictError,
        errors.DependencyUnavailableError, errors.NotFoundError, errors.QualificationExpiredError,
        errors.QualificationMissingError, errors.RuleGateFailedError,
    }
    assert declared == {cls.code for cls in platform}


# --- CTRC-FR-001 coverage of the WP-01 surfaces ----------------------------------------------------


def test_wp01_contracts_cover_every_implemented_wp01_operation(
    docs: dict[str, dict], implemented: set[tuple[str, str]]
) -> None:
    """The three path-bearing WP-01 contracts claim to be complete for their surfaces. Prove it."""
    committed = {
        (path, method.upper())
        for doc in docs.values()
        for path, method, _op in contract_validate.iter_operations(doc)
    }
    live = {(p, m) for p, m in implemented if p.startswith(WP01_SURFACES)}
    assert live - committed == set(), "implemented but not committed"
    assert committed - live == set(), "committed but not implemented"


def test_gxp001_and_gxp002_declare_no_paths(docs: dict[str, dict]) -> None:
    """SG-139: neither module has an HTTP surface of its own. If a path is ever added to either file,
    this test must be revisited together with Document 113 §6 — an endpoint appearing here would be
    exactly the exposure creep CTRC-FR-010 exists to catch.
    """
    for name in ("spec-gxp-001.yaml", "spec-gxp-002.yaml"):
        assert not (docs[name].get("paths") or {}), name
    from app.main import app

    live = set(app.openapi()["paths"])
    assert not [p for p in live if p.startswith(("/gxp/", "/signature/"))]


# --- CTR-FR-033 / CTR-FR-036 -----------------------------------------------------------------------


@pytest.mark.parametrize("name", ("spec-gxp-003.yaml", "spec-gxp-004.yaml", "spec-gxp-006.yaml"))
def test_every_operation_declares_its_security_scheme(name: str, docs: dict[str, dict]) -> None:
    for path, method, op in contract_validate.iter_operations(docs[name]):
        assert op.get("security") == [{"bearerAuth": []}], f"{name} {method.upper()} {path}"


# --- Reporting only: the pre-existing contracts (SG-013) -------------------------------------------


def test_report_preexisting_contract_debt(capsys) -> None:
    """Not an assertion about quality — a recorded count. The eight contracts written before this gate
    carry known violations (SG-013). This test fails only if that debt *grows* past the recorded
    baseline, which would mean a new contract was added without meeting the gate.
    """
    findings = contract_validate.Findings()
    docs = contract_validate.load_contracts(findings)
    for name, doc in docs.items():
        contract_validate.check_openapi_version(name, doc, findings)
        contract_validate.check_refs(name, doc, docs, findings)
        contract_validate.check_traceability(name, doc, findings)
        contract_validate.check_closed_payloads(name, doc, findings)
        contract_validate.check_envelopes(name, doc, findings)
    contract_validate.check_operation_ids(docs, findings)

    offenders = {item["contract"] for item in findings.items}
    assert not (offenders & set(WP01_CONTRACTS)), (
        f"a WP-01 contract regressed: {sorted(offenders & set(WP01_CONTRACTS))}"
    )
    # Baseline recorded 2026-08-27. Raise only with a documented reason.
    assert len(findings.items) <= 85, (
        f"pre-existing contract debt grew to {len(findings.items)}: {findings.by_rule()}"
    )


# --- Runtime conformance: the contract's claims checked against a live request ----------------------
#
# Document 113 §8's test catalogue items 2, 3 and 4 cannot be satisfied statically. These execute
# against a real command endpoint (`POST /rules/v1/drafts`, chosen because it is a create command with
# no signature policy dependency, so it exercises the envelope without failing closed first).

from app.core.security import hash_password  # noqa: E402
from app.modules.iam.models import User, UserSiteRole  # noqa: E402
from tests.conftest import DEMO_PASSWORD, auth_headers, idem, login  # noqa: E402

_DRAFT = {
    "rule_type": "eligibility",
    "semantic_version": "1.0.0",
    "expression_ast": {"op": "gte", "args": [{"var": "assay_percent"}, "98.0"]},
    "input_contract": {"assay_percent": {"type": "decimal", "unit": "%"}},
    "output_contract": {"eligible": {"type": "boolean"}},
    "unit_policy": {},
    "precision_policy": {"calculation_class": "CC-5", "reported_decimal_places": 2},
    "rounding_policy": {"policy_version": "DOCUMENT-110-v1.0"},
}


async def _admin(db, seeded, username: str) -> None:
    async with db.begin():
        user = User(
            username=username,
            email=f"{username}@example.com",
            full_name="Contract Test Admin",
            password_hash=hash_password(DEMO_PASSWORD),
            status="active",
        )
        db.add(user)
        await db.flush()
        db.add(
            UserSiteRole(
                user_id=user.id, site_id=seeded["site_id"], role_id=seeded["roles"]["Admin"].id
            )
        )


async def test_extra_field_on_a_command_payload_is_rejected(client, seeded, db) -> None:
    """CTRC-FR-003 negative / Document 113 §8 item 2 / CTR-FR-005. The contract declares
    `additionalProperties: false` on CreateRuleDraftCommand; prove the server enforces it.
    """
    await _admin(db, seeded, "contract.extra")
    token = await login(client, "contract.extra")

    body = {"idempotency_key": idem(), "rule_id": "CONTRACT-EXTRA", **_DRAFT}
    ok = await client.post("/rules/v1/drafts", json=body, headers=auth_headers(token))
    assert ok.status_code == 200, ok.text

    tampered = {
        "idempotency_key": idem(),
        "rule_id": "CONTRACT-EXTRA-2",
        **_DRAFT,
        "status": "released",  # a field the client must never be able to set
    }
    resp = await client.post("/rules/v1/drafts", json=tampered, headers=auth_headers(token))
    assert resp.status_code == 422, resp.text


async def test_simulate_accepts_an_unknown_field_sg144(client, seeded, db) -> None:
    """SG-144, recorded as executed evidence rather than asserted as correct.

    `SimulateRuleRequest` is a plain BaseModel with no `extra="forbid"`, so it accepts and discards
    unknown top-level fields — the one request body in WP-01 that is not closed. This test pins the
    CURRENT behaviour so the gap is visible and so closing SG-144 fails this test loudly rather than
    passing silently. When SG-144 is fixed, invert the assertion to 422 and update the gap.
    """
    await _admin(db, seeded, "contract.sim")
    token = await login(client, "contract.sim")

    created = await client.post(
        "/rules/v1/drafts",
        json={"idempotency_key": idem(), "rule_id": "CONTRACT-SIM", **_DRAFT},
        headers=auth_headers(token),
    )
    assert created.status_code == 200, created.text
    rule_object_id = created.json()["aggregate_id"]

    resp = await client.post(
        f"/rules/v1/{rule_object_id}/simulate",
        json={"inputs": {"assay_percent": "99.0"}, "unexpected_field": "ignored"},
        headers=auth_headers(token),
    )
    assert resp.status_code == 200, resp.text
    assert resp.json()["simulated"] is True


async def test_same_idempotency_key_same_payload_returns_the_original_receipt(
    client, seeded, db
) -> None:
    """Document 113 §5 I1 / §8 item 3 / CTR-FR-008."""
    await _admin(db, seeded, "contract.idem1")
    token = await login(client, "contract.idem1")

    body = {"idempotency_key": idem(), "rule_id": "CONTRACT-IDEM", **_DRAFT}
    first = await client.post("/rules/v1/drafts", json=body, headers=auth_headers(token))
    assert first.status_code == 200, first.text
    second = await client.post("/rules/v1/drafts", json=body, headers=auth_headers(token))
    assert second.status_code == 200, second.text
    assert second.json()["aggregate_id"] == first.json()["aggregate_id"]

    from sqlalchemy import func, select

    from app.modules.audit.models import AuditEvent

    count = (
        await db.execute(
            select(func.count())
            .select_from(AuditEvent)
            .where(AuditEvent.aggregate_id == first.json()["aggregate_id"])
        )
    ).scalar_one()
    assert count == 1, "a replayed command must not create a second audit event"


async def test_same_idempotency_key_different_payload_conflicts(client, seeded, db) -> None:
    """Document 113 §5 I4 / §8 item 4 — never a silent second write."""
    await _admin(db, seeded, "contract.idem2")
    token = await login(client, "contract.idem2")

    key = idem()
    first = await client.post(
        "/rules/v1/drafts",
        json={"idempotency_key": key, "rule_id": "CONTRACT-CONFLICT-A", **_DRAFT},
        headers=auth_headers(token),
    )
    assert first.status_code == 200, first.text

    second = await client.post(
        "/rules/v1/drafts",
        json={"idempotency_key": key, "rule_id": "CONTRACT-CONFLICT-B", **_DRAFT},
        headers=auth_headers(token),
    )
    assert second.status_code == 409, second.text
    assert second.json()["code"] == "IDEMPOTENCY_CONFLICT"


async def test_error_body_matches_the_committed_error_response_schema(client, seeded, db) -> None:
    """CTRC-FR-002 / CTR-FR-006 against a live rejection: the emitted body has exactly the keys
    `spec-gxp-001.yaml#/components/schemas/ErrorResponse` declares, and `code` is in the registry.
    """
    await _admin(db, seeded, "contract.err")
    token = await login(client, "contract.err")

    resp = await client.get(
        "/vault/v1/objects/00000000-0000-0000-0000-000000000000", headers=auth_headers(token)
    )
    assert resp.status_code == 404, resp.text

    schema = _load("spec-gxp-001.yaml")["components"]["schemas"]["ErrorResponse"]
    body = resp.json()
    assert set(body) == set(schema["properties"]), body
    assert set(schema["required"]) <= set(body)
    assert body["code"] == "NOT_FOUND", body
    registry = _load("spec-gxp-001.yaml")["components"]["schemas"]["PlatformErrorCode"]["enum"]
    assert body["code"] in registry, body["code"]


async def test_audit_list_response_matches_the_committed_page_envelope(client, seeded, db) -> None:
    """CTR-FR-012: the shared list envelope the contract declares is what the endpoint returns."""
    await _admin(db, seeded, "contract.page")
    token = await login(client, "contract.page")

    resp = await client.get("/audit/v1/search?page=1&page_size=5", headers=auth_headers(token))
    assert resp.status_code == 200, resp.text
    body = resp.json()

    envelope = _load("spec-gxp-001.yaml")["components"]["schemas"]["PageEnvelope"]
    for field in envelope["required"]:
        assert field in body, field
    assert "items" in body
    assert body["page_size"] == 5
    for item in body["items"]:
        for field in _load("spec-gxp-003.yaml")["components"]["schemas"]["AuditEvent"]["required"]:
            assert field in item, f"AuditEvent.{field} missing from a live response"
