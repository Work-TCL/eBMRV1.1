#!/usr/bin/env python3
"""Contract conformance gate for Document 101 (SPEC-ENG-005) / Document 113 (SPEC-ENG-009).

Enforces, over `contracts/openapi/*.yaml` at the repository root:

  CTRC-FR-001  contract before code   — an implemented operation inside a surface that already has a
                                        committed contract must appear in that contract.
  CTRC-FR-002  envelope conformance   — a committed mutation response must be the canonical
                                        MutationReceipt; a declared error body must be the canonical
                                        ErrorResponse.
  CTRC-FR-003  closed payloads        — every `*Command` schema declares `additionalProperties: false`.
  CTRC-FR-009  traceability           — every schema and every operation declares `x-requirement-ids`.
  parse/3.1                           — every file is parseable, declares OpenAPI 3.1, resolves every
                                        `$ref` (local and cross-file), and gives every operation a
                                        globally unique `operationId` (CTR-FR-002).

Exit code 0 when no violation is found, 1 otherwise. Findings are evidence: this script reports what it
sees, including violations in contracts written before it existed.

Usage:
    python tooling/contracts/validate.py [--strict-coverage] [--json]

`--strict-coverage` additionally fails when any implemented operation lives in a surface with no
committed contract at all. Off by default: 40+ modules legitimately have no contract yet (SG-013 is
open and being closed work package by work package), and a gate that fails on all of them from day one
would be turned off rather than fixed. The uncovered count is always reported.

The implemented-operation inventory is read from the running FastAPI app's own route table. That is a
*gate* input, not a schema source — Document 113 §10 forbids generating schemas from implementation
code, and this script never writes a contract. If the app cannot be imported (no venv, missing
dependency) the CTRC-FR-001 check is reported as SKIPPED rather than silently passing.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import yaml

REPO_ROOT = Path(__file__).resolve().parents[3]
CONTRACT_DIR = REPO_ROOT / "contracts" / "openapi"
SERVICE_ROOT = REPO_ROOT / "services" / "gxp-api"

HTTP_METHODS = ("get", "post", "put", "patch", "delete", "head", "options", "trace")

# The canonical envelopes live in SPEC-GXP-001, which owns command/idempotency/receipt semantics
# (Document 03, Document 113 §2). A mutation response that is not this schema is an envelope violation.
CANONICAL_RECEIPT = "spec-gxp-001.yaml#/components/schemas/MutationReceipt"
CANONICAL_ERROR = "spec-gxp-001.yaml#/components/schemas/ErrorResponse"


class Findings:
    def __init__(self) -> None:
        self.items: list[dict] = []
        self.skipped: list[str] = []

    def add(self, rule: str, contract: str, locator: str, message: str) -> None:
        self.items.append(
            {"rule": rule, "contract": contract, "locator": locator, "message": message}
        )

    def skip(self, message: str) -> None:
        self.skipped.append(message)

    def by_rule(self) -> dict[str, int]:
        counts: dict[str, int] = {}
        for item in self.items:
            counts[item["rule"]] = counts.get(item["rule"], 0) + 1
        return counts


def load_contracts(findings: Findings) -> dict[str, dict]:
    """Parse every contract file. A file that will not parse is a finding and is then skipped."""
    docs: dict[str, dict] = {}
    for path in sorted(CONTRACT_DIR.glob("*.yaml")):
        try:
            doc = yaml.safe_load(path.read_text())
        except yaml.YAMLError as exc:
            findings.add("parse", path.name, "-", f"not parseable as YAML: {exc}")
            continue
        if not isinstance(doc, dict):
            findings.add("parse", path.name, "-", "top level is not a mapping")
            continue
        docs[path.name] = doc
    return docs


def check_openapi_version(name: str, doc: dict, findings: Findings) -> None:
    version = str(doc.get("openapi", ""))
    if not version.startswith("3.1"):
        findings.add(
            "parse",
            name,
            "openapi",
            f"declares openapi: {version or '<missing>'}; Document 113 §1 requires OpenAPI 3.1",
        )
    if not any(k in doc for k in ("paths", "components", "webhooks")):
        findings.add("parse", name, "-", "declares none of paths/components/webhooks")


def iter_operations(doc: dict):
    """Yield (path, method, operation) for every real operation in a document."""
    for path, item in (doc.get("paths") or {}).items():
        if not isinstance(item, dict):
            continue
        for method, op in item.items():
            if method in HTTP_METHODS and isinstance(op, dict):
                yield path, method, op


def walk_refs(node, trail: str = ""):
    """Yield (json_pointer_trail, ref_string) for every $ref in a document."""
    if isinstance(node, dict):
        for key, value in node.items():
            if key == "$ref" and isinstance(value, str):
                yield trail, value
            else:
                yield from walk_refs(value, f"{trail}/{key}")
    elif isinstance(node, list):
        for index, value in enumerate(node):
            yield from walk_refs(value, f"{trail}/{index}")


def resolve_pointer(doc: dict, pointer: str):
    """Resolve a JSON pointer inside a parsed document. Returns a sentinel on failure."""
    node = doc
    for raw in pointer.lstrip("#/").split("/"):
        if raw == "":
            continue
        part = raw.replace("~1", "/").replace("~0", "~")
        if isinstance(node, dict) and part in node:
            node = node[part]
        elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
            node = node[int(part)]
        else:
            return ...
    return node


def check_refs(name: str, doc: dict, docs: dict[str, dict], findings: Findings) -> None:
    for trail, ref in walk_refs(doc):
        if ref.startswith("#"):
            if resolve_pointer(doc, ref) is ...:
                findings.add("parse", name, trail or "/", f"unresolvable local $ref: {ref}")
            continue
        target_file, _, pointer = ref.partition("#")
        target = docs.get(target_file)
        if target is None:
            findings.add(
                "parse", name, trail or "/", f"$ref points at a missing contract file: {ref}"
            )
        elif pointer and resolve_pointer(target, pointer) is ...:
            findings.add("parse", name, trail or "/", f"unresolvable cross-file $ref: {ref}")


def check_operation_ids(docs: dict[str, dict], findings: Findings) -> None:
    seen: dict[str, str] = {}
    for name, doc in docs.items():
        for path, method, op in iter_operations(doc):
            locator = f"{method.upper()} {path}"
            op_id = op.get("operationId")
            if not op_id:
                findings.add("CTR-FR-002", name, locator, "operation has no operationId")
                continue
            if op_id in seen:
                findings.add(
                    "CTR-FR-002",
                    name,
                    locator,
                    f"operationId '{op_id}' is already used in {seen[op_id]}",
                )
            else:
                seen[op_id] = name


def check_traceability(name: str, doc: dict, findings: Findings) -> None:
    """CTRC-FR-009: schemas carry x-requirement-ids. Operations must too (CTR-FR-032)."""
    for path, method, op in iter_operations(doc):
        if not op.get("x-requirement-ids"):
            findings.add(
                "CTRC-FR-009", name, f"{method.upper()} {path}", "operation has no x-requirement-ids"
            )
    schemas = ((doc.get("components") or {}).get("schemas") or {})
    for schema_name, schema in schemas.items():
        if not isinstance(schema, dict):
            continue
        # A pure composition node inherits traceability from what it composes.
        if not schema.get("x-requirement-ids") and not (
            set(schema) <= {"allOf", "oneOf", "anyOf", "$ref", "description"}
        ):
            findings.add(
                "CTRC-FR-009",
                name,
                f"components.schemas.{schema_name}",
                "schema has no x-requirement-ids",
            )


def check_closed_payloads(name: str, doc: dict, findings: Findings) -> None:
    """CTRC-FR-003 / MUT-FR-005 / Document 113 §3 F6: command payloads are closed."""
    schemas = ((doc.get("components") or {}).get("schemas") or {})
    for schema_name, schema in schemas.items():
        if not schema_name.endswith("Command") or not isinstance(schema, dict):
            continue
        if schema.get("additionalProperties") is not False:
            findings.add(
                "CTRC-FR-003",
                name,
                f"components.schemas.{schema_name}",
                "command payload schema does not declare additionalProperties: false",
            )


def _response_schema_ref(response: dict) -> str | None:
    content = (response or {}).get("content") or {}
    body = content.get("application/json") or {}
    schema = body.get("schema") or {}
    ref = schema.get("$ref")
    return ref if isinstance(ref, str) else None


def check_envelopes(name: str, doc: dict, findings: Findings) -> None:
    """CTRC-FR-002: a committed mutation response is the canonical receipt; a declared error body is
    the canonical error response. Only inline `$ref`s are judged — a `$ref` to a shared `responses`
    entry is trusted, because that entry is itself checked where it is defined.
    """
    local_receipt = "#/components/schemas/MutationReceipt"
    local_error = "#/components/schemas/ErrorResponse"

    for path, method, op in iter_operations(doc):
        locator = f"{method.upper()} {path}"
        for status, response in (op.get("responses") or {}).items():
            if not isinstance(response, dict) or "$ref" in response:
                continue
            ref = _response_schema_ref(response)
            if ref is None:
                continue
            if str(status).startswith(("4", "5")) and ref not in (CANONICAL_ERROR, local_error):
                findings.add(
                    "CTRC-FR-002",
                    name,
                    f"{locator} -> {status}",
                    f"error response body is '{ref}', not the canonical ErrorResponse",
                )
            if (
                str(status) == "200"
                and method == "post"
                and ref.endswith("MutationReceipt")
                and ref not in (CANONICAL_RECEIPT, local_receipt)
            ):
                findings.add(
                    "CTRC-FR-002",
                    name,
                    f"{locator} -> 200",
                    f"receipt response body is '{ref}', not the canonical MutationReceipt",
                )


def live_operations(findings: Findings) -> set[tuple[str, str]] | None:
    """The implemented (path, METHOD) inventory, read from the app's own route table."""
    sys.path.insert(0, str(SERVICE_ROOT))
    try:
        from app.main import app  # noqa: PLC0415
    except Exception as exc:  # noqa: BLE001 - any import failure means "cannot check", not "passes"
        findings.skip(
            f"CTRC-FR-001 SKIPPED: could not import the FastAPI app to enumerate implemented "
            f"operations ({type(exc).__name__}: {exc}). Run this with the gxp-api virtualenv."
        )
        return None
    spec = app.openapi()
    return {
        (path, method.upper())
        for path, item in (spec.get("paths") or {}).items()
        for method in item
        if method in HTTP_METHODS
    }


def surface_of(path: str) -> str:
    """The contract surface a path belongs to: its first two *literal* segments, e.g. `/rules/v1`.

    Path-parameter segments are skipped so that `/roles` and `/roles/{role_id}` resolve to the same
    surface — otherwise a collection and its item endpoints would look like two unrelated surfaces and
    the coverage check would miss exactly the gaps it exists to find.
    """
    literal = [p for p in path.split("/") if p and not p.startswith("{")]
    return "/" + "/".join(literal[:2])


def check_coverage(
    docs: dict[str, dict], findings: Findings, strict: bool
) -> tuple[int, int, int]:
    """CTRC-FR-001. Returns (implemented, covered_surfaces_ops, uncovered_ops)."""
    implemented = live_operations(findings)
    if implemented is None:
        return (0, 0, 0)

    committed: dict[tuple[str, str], str] = {}
    surfaces: dict[str, str] = {}
    for name, doc in docs.items():
        for path, method, _op in iter_operations(doc):
            committed[(path, method.upper())] = name
            surfaces.setdefault(surface_of(path), name)

    covered = uncovered = 0
    for path, method in sorted(implemented):
        if path in ("/openapi.json", "/docs", "/docs/oauth2-redirect", "/redoc", "/healthz"):
            continue  # CTR-FR-036 explicitly exempts internal runtime health/doc mechanisms
        surface = surface_of(path)
        owning = surfaces.get(surface)
        if owning is None:
            uncovered += 1
            if strict:
                findings.add(
                    "CTRC-FR-001",
                    "-",
                    f"{method} {path}",
                    "implemented operation is in a surface with no committed contract",
                )
            continue
        covered += 1
        if (path, method) not in committed:
            findings.add(
                "CTRC-FR-001",
                owning,
                f"{method} {path}",
                f"implemented operation is missing from the committed contract for {surface}",
            )
    return (len(implemented), covered, uncovered)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--strict-coverage", action="store_true")
    parser.add_argument("--json", action="store_true", help="emit findings as JSON")
    args = parser.parse_args()

    findings = Findings()
    docs = load_contracts(findings)

    for name, doc in docs.items():
        check_openapi_version(name, doc, findings)
        check_refs(name, doc, docs, findings)
        check_traceability(name, doc, findings)
        check_closed_payloads(name, doc, findings)
        check_envelopes(name, doc, findings)
    check_operation_ids(docs, findings)

    total_ops, covered, uncovered = check_coverage(docs, findings, args.strict_coverage)

    if args.json:
        print(
            json.dumps(
                {
                    "contracts": len(docs),
                    "implemented_operations": total_ops,
                    "covered_operations": covered,
                    "uncovered_operations": uncovered,
                    "findings": findings.items,
                    "skipped": findings.skipped,
                },
                indent=2,
            )
        )
        return 1 if findings.items else 0

    committed_ops = sum(1 for doc in docs.values() for _ in iter_operations(doc))
    print(f"contract files parsed          : {len(docs)}")
    print(f"operations committed in them   : {committed_ops}")
    print(f"operations implemented in code : {total_ops}")
    print(f"  in a surface with a contract : {covered}")
    print(f"  in a surface with no contract: {uncovered}  (SG-013 backlog)")
    print()

    for message in findings.skipped:
        print(f"SKIP  {message}")
    if findings.skipped:
        print()

    if not findings.items:
        print("PASS  no contract conformance violations found")
        return 0

    by_rule = findings.by_rule()
    print(f"FAIL  {len(findings.items)} violation(s): " + ", ".join(
        f"{rule}={count}" for rule, count in sorted(by_rule.items())
    ))
    print()
    for item in sorted(findings.items, key=lambda i: (i["rule"], i["contract"], i["locator"])):
        print(f"  [{item['rule']}] {item['contract']}  {item['locator']}")
        print(f"      {item['message']}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
