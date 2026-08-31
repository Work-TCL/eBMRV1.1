"""Fill real (non-fabricated) execution results into the 70 pre-written Document 44 (SPEC-EDGE-002)
test cases: test-cases/WP-06/Document_44_SPEC-EDGE-002_TEST_CASES.md.

Scope decision (fast triage this pass, confirming the working assumption against the full spec text --
not assumed from the title): Document 44 defines the on-prem gateway runtime's protocol driver layer
(OPC UA / Modbus / MQTT / SNMP / serial / REST-file client drivers, §4's `EdgeDriver` interface, §11's
`edge/plugins/` repository layout). Its own architectural principles (repeated verbatim from Document 43)
state "Edge and protocol code is not the GxP system of record" and its Claude Code Prohibitions (§14)
state "Do not import OPC UA/Modbus/MQTT libraries into GxP Core packages" and "No protocol driver writes
directly to business/GxP tables." This is the same on-prem deployable Document 43's session explicitly
scoped out ("the on-prem gateway runtime itself... is a distinct future deployable and is not built
here" -- see app/modules/edge/models.py's module docstring, and SG-118/SG-119/SG-120's precedent for
recording a resolved scope/policy decision as data rather than leaving it silently unresolved). Nothing in
Document 44's function catalogue (§3) describes a server-side surface beyond what Document 43 already
built (accept_observation_batch, health, security-events) -- every operation here (connect/disconnect/
readOnce/subscribe/browse/write/healthCheck/decodePayload/mapNativeQuality/reconnect/testMapping) runs
inside the gateway process itself, calling out to the server only through the envelope Document 43's API
already accepts.

This is recorded as a resolved scope decision in status/build-status.json / status/BUILD_STATUS.md (same
treatment as Document 43's own on-prem exclusion), not as a new entry in docs/generated/18_SPEC_GAPS.md --
there is no ambiguity about regulated behavior to flag; the whole document describes a deployable outside
this pass's boundary. Every one of the 70 pre-written cases is therefore BLOCKED with that reason, not
fabricated as PASS or silently skipped.

Run with: python3 scripts/fill_document_44_test_cases.py
"""

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CASE_FILE = REPO_ROOT / "ebmr-edhr/test-cases/WP-06/Document_44_SPEC-EDGE-002_TEST_CASES.md"
LIBRARY_CSV = REPO_ROOT / "ebmr-edhr/test-cases/TEST_CASE_LIBRARY.csv"
MODULE = "SPEC-EDGE-002"

EXECUTED_BY = "claude-code"
EXECUTED_AT = "2026-08-26"

REASON = (
    "BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer "
    "(OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- "
    "entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode "
    "sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct "
    "future deployable, not built this pass; confirmed against Document 44's full text, not assumed from "
    "its title. No server-side code exists to execute this case against; recorded as a resolved scope "
    "decision in status/build-status.json, not a SPEC_GAP."
)


def main() -> None:
    text = CASE_FILE.read_text()

    case_ids = sorted(set(re.findall(r"### (TC-044-(?:\d{3}-\d{2}|M\d{2}|S\d{3})) —", text)))
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

    pattern = re.compile(r"### (TC-044-(?:\d{3}-\d{2}|M\d{2}|S\d{3})) — .*?(?=\n### |\Z)", re.S)
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
