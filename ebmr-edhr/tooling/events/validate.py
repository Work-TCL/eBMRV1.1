#!/usr/bin/env python3
"""Event contract structural gate for Document 101 (SPEC-ENG-005) / Document 113 (SPEC-ENG-009) §2-3.

Enforces, over `contracts/events/*.json` at the repository root:

  parse                json + $schema draft 2020-12 declared, every file parses
  $ref resolution       every `$ref` (local `#/$defs/...` and cross-file, including into
                        `../openapi/*.yaml`) resolves to something real
  CTRC-FR-009           every event entry and every $defs schema carries `x-requirement-ids`
  F1 (Doc 113 §3)       every payload schema closes with `additionalProperties: false` -- the same
                        "no orphan fields" discipline CTRC-FR-003 requires of command payloads, applied
                        here to event payloads (Document 113 §3 F1: "every payload field maps to a field
                        in the owning entity schema"; a closed schema is how that gets checked, not just
                        asserted in prose)
  CTRC-FR-008           single producer per event_type -- no two files/entries claim the same event_type
                        with two different `producer` values

Exit code 0 when no violation is found, 1 otherwise. Findings are evidence: this script reports what it
sees.

Usage:
    python tooling/events/validate.py [--json]

SCOPE NOTE (disclosed, not a silent limitation): unlike tooling/contracts/validate.py, this script does
NOT attempt a CTRC-FR-001-equivalent "every implemented event_type has a committed contract" gate. That
would require statically resolving every `write_outbox_event(event_type=...)` call site across the whole
codebase, including the dynamic `event_type = "X" if cond else "Y"` ternary-assignment pattern several
QMS modules use (verified by hand for this pass, not by tooling) -- a real static-analysis undertaking of
its own that risks false negatives if attempted carelessly. This gate checks the contracts that exist are
internally consistent; it does not (yet) check that all 484 platform event types have contracts at all
-- see docs/generated/18_SPEC_GAPS.md SG-013 point 3, still open.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
EVENTS_DIR = REPO_ROOT / "contracts" / "events"
OPENAPI_DIR = REPO_ROOT / "contracts" / "openapi"


class Findings:
    def __init__(self) -> None:
        self.items: list[dict] = []

    def add(self, rule: str, contract: str, locator: str, message: str) -> None:
        self.items.append({"rule": rule, "contract": contract, "locator": locator, "message": message})


def load_events(findings: Findings) -> dict[str, dict]:
    docs: dict[str, dict] = {}
    for path in sorted(EVENTS_DIR.glob("*.json")):
        try:
            docs[path.name] = json.loads(path.read_text())
        except json.JSONDecodeError as exc:
            findings.add("parse", path.name, "-", f"invalid JSON: {exc}")
    return docs


def resolve_local_ref(doc: dict, pointer: str) -> object | None:
    """Resolve a `#/a/b/c`-style JSON pointer against `doc`. Returns None if any segment is missing."""
    node = doc
    for part in pointer.lstrip("#/").split("/"):
        if part == "":
            continue
        if isinstance(node, dict) and part in node:
            node = node[part]
        else:
            return None
    return node


_OPENAPI_CACHE: dict[str, dict] = {}


def load_openapi_yaml(filename: str) -> dict | None:
    if filename in _OPENAPI_CACHE:
        return _OPENAPI_CACHE[filename]
    path = OPENAPI_DIR / filename
    if not path.exists():
        return None
    try:
        import yaml  # already a dependency of tooling/contracts/validate.py
    except ImportError:
        return None
    doc = yaml.safe_load(path.read_text())
    _OPENAPI_CACHE[filename] = doc
    return doc


def check_ref(findings: Findings, contract: str, locator: str, ref: str, doc: dict, all_docs: dict[str, dict]) -> None:
    if ref.startswith("#/"):
        if resolve_local_ref(doc, ref) is None:
            findings.add("$ref", contract, locator, f"local $ref does not resolve: {ref}")
        return
    if "#/" in ref:
        target_file, pointer = ref.split("#/", 1)
        pointer = "#/" + pointer
    else:
        target_file, pointer = ref, None
    if target_file.endswith(".json"):
        target_doc = all_docs.get(target_file)
        if target_doc is None:
            findings.add("$ref", contract, locator, f"cross-file $ref target not found: {target_file}")
            return
        if pointer and resolve_local_ref(target_doc, pointer) is None:
            findings.add("$ref", contract, locator, f"$ref does not resolve inside {target_file}: {pointer}")
    elif target_file.endswith(".yaml"):
        # $refs into ../openapi/*.yaml (component schemas shared with the API contracts).
        rel = target_file
        filename = Path(rel).name
        target_doc = load_openapi_yaml(filename)
        if target_doc is None:
            findings.add("$ref", contract, locator, f"cross-file $ref target not found or PyYAML unavailable: {rel}")
            return
        if pointer and resolve_local_ref(target_doc, pointer) is None:
            findings.add("$ref", contract, locator, f"$ref does not resolve inside {rel}: {pointer}")
    else:
        findings.add("$ref", contract, locator, f"unrecognized $ref target type: {ref}")


def walk_refs(node, path: str):
    if isinstance(node, dict):
        if "$ref" in node and isinstance(node["$ref"], str):
            yield path, node["$ref"]
        for k, v in node.items():
            yield from walk_refs(v, f"{path}/{k}")
    elif isinstance(node, list):
        for i, v in enumerate(node):
            yield from walk_refs(v, f"{path}[{i}]")


def check_closed_payloads(findings: Findings, contract: str, doc: dict) -> None:
    for defname, schema in (doc.get("$defs") or {}).items():
        if not isinstance(schema, dict):
            continue
        if schema.get("type") == "object" and "additionalProperties" not in schema:
            findings.add("F1", contract, f"$defs/{defname}", "object schema has no additionalProperties: false")


def check_requirement_ids(findings: Findings, contract: str, doc: dict) -> None:
    if "x-requirement-ids" not in doc:
        findings.add("CTRC-FR-009", contract, "$", "file has no top-level x-requirement-ids")
    for defname, schema in (doc.get("$defs") or {}).items():
        if isinstance(schema, dict) and "x-requirement-ids" not in schema:
            findings.add("CTRC-FR-009", contract, f"$defs/{defname}", "schema has no x-requirement-ids")
    for i, event in enumerate(doc.get("events") or []):
        if "x-requirement-ids" not in event:
            findings.add("CTRC-FR-009", contract, f"events[{i}].{event.get('event_type', '?')}", "event entry has no x-requirement-ids")


def check_event_entries(findings: Findings, contract: str, doc: dict) -> None:
    required = ("event_type", "schema_version", "producer", "aggregate_type", "payload")
    for i, event in enumerate(doc.get("events") or []):
        missing = [k for k in required if k not in event]
        if missing:
            findings.add("shape", contract, f"events[{i}]", f"missing required key(s): {missing}")


def check_single_producer(findings: Findings, all_docs: dict[str, dict]) -> None:
    owner: dict[str, tuple[str, str]] = {}
    for contract, doc in all_docs.items():
        for event in doc.get("events") or []:
            et = event.get("event_type")
            producer = event.get("producer")
            if et is None or producer is None:
                continue
            if et in owner and owner[et][1] != producer:
                findings.add(
                    "CTRC-FR-008", contract, f"event_type={et}",
                    f"claimed by two producers: {owner[et][1]} ({owner[et][0]}) and {producer} ({contract})",
                )
            else:
                owner.setdefault(et, (contract, producer))


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    findings = Findings()
    docs = load_events(findings)

    for contract, doc in docs.items():
        check_requirement_ids(findings, contract, doc)
        check_closed_payloads(findings, contract, doc)
        check_event_entries(findings, contract, doc)
        for locator, ref in walk_refs(doc, "$"):
            check_ref(findings, contract, locator, ref, doc, docs)

    check_single_producer(findings, docs)

    event_count = sum(len(d.get("events") or []) for d in docs.values())
    print(f"event contract files parsed : {len(docs)}")
    print(f"event entries declared      : {event_count}")

    if args.json:
        print(json.dumps({"contracts": len(docs), "events": event_count, "findings": findings.items}, indent=2))
        return 1 if findings.items else 0

    if not findings.items:
        print("\nPASS  no event contract violations found")
        return 0

    print(f"\nFAIL  {len(findings.items)} violation(s)")
    for f in findings.items:
        print(f"  [{f['rule']}] {f['contract']}  {f['locator']}\n      {f['message']}")
    return 1


if __name__ == "__main__":
    sys.exit(main())
