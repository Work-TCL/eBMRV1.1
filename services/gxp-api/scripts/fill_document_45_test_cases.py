"""Fill real (non-fabricated) execution results into the 66 pre-written Document 45 (SPEC-EDGE-003)
test cases: test-cases/WP-06/Document_45_SPEC-EDGE-003_TEST_CASES.md.

Scope decision (fast triage this pass, confirming the working assumption against the full spec text --
not assumed from the title): Document 45 defines the on-prem gateway's durable store-and-forward buffer
(§4's SQLite `edge_outbox` WAL schema), outage/retry/replay behavior and freshness computation -- all of
it gateway-local runtime behavior (`appendEnvelope`, `selectForwardBatch`, `sendBatch`, `recoverInFlight`,
`computeDiskPressure`, `purgeAcked`, `verifyBufferIntegrity`, `storeEvidenceFile`). Its architectural
principles and prohibitions are the same verbatim text as Document 43/44: "Edge and protocol code is not
the GxP system of record"; §12 forbids deleting unacked PENDING/IN_FLIGHT evidence, overwriting source
timestamps and renumbering sequence gaps -- all gateway-side guarantees over the gateway's own local
SQLite store, not the PostgreSQL server. The one server-side counterpart this document assumes --
accepting a batch, applying idempotent acknowledgement by (gateway_id, event_id) and detecting a payload-
hash conflict on replay -- is exactly what Document 43's `accept_observation_batch()` already implements
and already has its own test coverage (test-cases/WP-06/Document_43_SPEC-EDGE-001_TEST_CASES.md). This is
the same on-prem deployable Document 43's session explicitly scoped out (see
app/modules/edge/models.py's module docstring; SG-118/SG-119/SG-120's precedent for recording a resolved
scope/policy decision as data).

Recorded as a resolved scope decision in status/build-status.json / status/BUILD_STATUS.md, not a new
docs/generated/18_SPEC_GAPS.md entry -- there is no regulated-behavior ambiguity here, the whole document
describes a deployable outside this pass's boundary. Every one of the 66 pre-written cases is BLOCKED with
that reason, not fabricated as PASS or silently skipped.

Run with: python3 scripts/fill_document_45_test_cases.py
"""

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CASE_FILE = REPO_ROOT / "ebmr-edhr/test-cases/WP-06/Document_45_SPEC-EDGE-003_TEST_CASES.md"
LIBRARY_CSV = REPO_ROOT / "ebmr-edhr/test-cases/TEST_CASE_LIBRARY.csv"
MODULE = "SPEC-EDGE-003"

EXECUTED_BY = "claude-code"
EXECUTED_AT = "2026-08-26"

REASON = (
    "BLOCKED -- Document 45 (SPEC-EDGE-003) is the on-prem gateway's durable store-and-forward buffer "
    "(local SQLite WAL outbox, retry/backoff, disk-pressure, replay and freshness computation) -- entirely "
    "gateway-local runtime behavior, distinct from the PostgreSQL transactional outbox (AG-09) the server "
    "already uses. The one server-side counterpart it assumes (idempotent batch acknowledgement by "
    "(gateway_id, event_id) with payload-hash conflict detection) is already built and tested under "
    "Document 43 (accept_observation_batch()). Per Document 43's session's plan-mode sign-off "
    "(app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future "
    "deployable, not built this pass; confirmed against Document 45's full text, not assumed from its "
    "title. No server-side code exists to execute this case against; recorded as a resolved scope decision "
    "in status/build-status.json, not a SPEC_GAP."
)


def main() -> None:
    text = CASE_FILE.read_text()

    case_ids = sorted(set(re.findall(r"### (TC-045-(?:\d{3}-\d{2}|M\d{2}|S\d{3})) —", text)))
    if not case_ids:
        raise SystemExit("No case IDs found in the book -- check the file/pattern.")

    def replace_case(match: re.Match) -> str:
        block = match.group(0)
        block = re.sub(r"\*\*Status:\*\*\s*NOT_STARTED", "**Status:** BLOCKED", block)
        block = re.sub(r"\*\*Executed by:\*\*\s*____", f"**Executed by:** {EXECUTED_BY}", block)
        block = re.sub(r"\*\*Date:\*\*\s*____", f"**Date:** {EXECUTED_AT}", block)
        block = re.sub(r"\*\*Actual result:\*\*\s*____", f"**Actual result:** {REASON}", block)
        block = re.sub(r"\*\*Defect:\*\*\s*____", "**Defect:** —", block)
        return block

    pattern = re.compile(r"### (TC-045-(?:\d{3}-\d{2}|M\d{2}|S\d{3})) — .*?(?=\n### |\Z)", re.S)
    new_text, n = pattern.subn(replace_case, text)
    if n != len(case_ids):
        raise SystemExit(f"Expected to update {len(case_ids)} cases, updated {n}")
    CASE_FILE.write_text(new_text)
    print(f"updated {n} cases in {CASE_FILE}")

    with open(LIBRARY_CSV, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    lib_updated = 0
    case_id_set = set(case_ids)
    for row in rows:
        if row.get("module") != MODULE:
            continue
        case_id = row.get("test_case_id")
        if case_id in case_id_set:
            row["status"] = "BLOCKED"
            row["executed_by"] = EXECUTED_BY
            row["executed_at"] = EXECUTED_AT
            row["actual_result"] = REASON
            row["defect_reference"] = ""
            lib_updated += 1

    with open(LIBRARY_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"updated {lib_updated} rows in {LIBRARY_CSV}")


if __name__ == "__main__":
    main()
