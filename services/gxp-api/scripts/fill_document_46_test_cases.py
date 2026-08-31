"""Fill real (non-fabricated) execution results into the 76 pre-written Document 46 (SPEC-EDGE-004)
test cases: test-cases/WP-06/Document_46_SPEC-EDGE-004_TEST_CASES.md.

Scope decision (fast triage this pass, confirming the working assumption against the full spec text --
not assumed from the title): Document 46 defines operator-facing peripheral integration -- barcode
scanners, balances, printers, testers, vision systems and file-producing instruments -- all acquired and
adapted by the on-prem gateway runtime (§9's `registerPeripheralSession()`, the USB/serial/HID/network
device access §7 PER-FR-024 restricts to "the gateway service", the peripheral simulators §7 PER-FR-025
describes). Its architectural principles are the same verbatim text shared with Documents 43-45: "Edge and
protocol code is not the GxP system of record"; §12's acceptance statement is explicit that the complete
workflow works "without peripheral code directly mutating batch/release state" -- i.e. the actual
regulated mutation (dispensing quantities, print-label approval, tester/vision result acceptance into
eDHR/QC) is owned by the existing Batch/Material/Packaging/QC modules this document's functions call into,
not a new server module of its own. Every function in §3's catalogue (captureBarcodeScan, validateScanFor
Action, readStableWeight, recordTare, submitManualWeight, createPrintJob, reprintLabel, ingestTesterResult,
ingestVisionResult, registerPeripheralSession) is the gateway-side device-adapter half of an operation
whose regulated acceptance already belongs to another module's existing Mutation Gateway command (AG-05/
AG-06) -- there is no new authoritative entity or command this document defines that isn't either (a) an
on-prem device-I/O concern, or (b) already the owning module's job. This is the same on-prem deployable
Document 43's session explicitly scoped out (see app/modules/edge/models.py's module docstring;
SG-118/SG-119/SG-120's precedent for recording a resolved scope/policy decision as data).

Recorded as a resolved scope decision in status/build-status.json / status/BUILD_STATUS.md, not a new
docs/generated/18_SPEC_GAPS.md entry -- there is no regulated-behavior ambiguity here, the whole document
describes a deployable outside this pass's boundary. Every one of the 76 pre-written cases is BLOCKED with
that reason, not fabricated as PASS or silently skipped.

Run with: python3 scripts/fill_document_46_test_cases.py
"""

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CASE_FILE = REPO_ROOT / "ebmr-edhr/test-cases/WP-06/Document_46_SPEC-EDGE-004_TEST_CASES.md"
LIBRARY_CSV = REPO_ROOT / "ebmr-edhr/test-cases/TEST_CASE_LIBRARY.csv"
MODULE = "SPEC-EDGE-004"

EXECUTED_BY = "claude-code"
EXECUTED_AT = "2026-08-26"

REASON = (
    "BLOCKED -- Document 46 (SPEC-EDGE-004) is the on-prem gateway's peripheral device-adapter layer "
    "(barcode scanner/balance/printer/tester/vision integration) -- device I/O acquired by the gateway "
    "runtime; the document's own acceptance statement (§12) is explicit that regulated mutation happens "
    "'without peripheral code directly mutating batch/release state', i.e. through the existing owning "
    "Batch/Material/Packaging/QC modules' own commands, not a new module this document defines. Per "
    "Document 43's session's plan-mode sign-off (app/modules/edge/models.py module docstring), the "
    "on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against "
    "Document 46's full text, not assumed from its title. No server-side code exists to execute this case "
    "against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP."
)


def main() -> None:
    text = CASE_FILE.read_text()

    case_ids = sorted(set(re.findall(r"### (TC-046-(?:\d{3}-\d{2}|M\d{2}|S\d{3})) —", text)))
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

    pattern = re.compile(r"### (TC-046-(?:\d{3}-\d{2}|M\d{2}|S\d{3})) — .*?(?=\n### |\Z)", re.S)
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
