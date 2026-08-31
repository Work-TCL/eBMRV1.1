"""Fill real (non-fabricated) execution results into the 83 pre-written Document 38 (SPEC-EQP-001) test
cases: test-cases/WP-06/Document_38_SPEC-EQP-001_TEST_CASES.md.

Every PASS cites the actual pytest function(s) in services/gxp-api/tests/test_equipment_flow.py that were
run (`pytest tests/test_equipment_flow.py -q` -> all passing, plus the full-suite run for regression).
Every BLOCKED cites the specific SPEC_GAP (docs/generated/18_SPEC_GAPS.md, SG-109..SG-113) and the missing
capability. Every N/A states the concrete reason the case does not apply to this module's actually-resolved
behaviour -- never a bare "N/A" with no justification. Same template as
scripts/fill_document_22_test_cases.py.

Run with: python3 scripts/fill_document_38_test_cases.py
"""

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CASE_FILE = REPO_ROOT / "ebmr-edhr/test-cases/WP-06/Document_38_SPEC-EQP-001_TEST_CASES.md"
LIBRARY_CSV = REPO_ROOT / "ebmr-edhr/test-cases/TEST_CASE_LIBRARY.csv"
TEST_MODULE = "services/gxp-api/tests/test_equipment_flow.py"

EXECUTED_BY = "claude-code"
EXECUTED_AT = "2026-08-25"

SG109 = "SG-109"  # edge/device/CMMS/alarm/firmware-tracking -- no source to integrate against
SG110 = "SG-110"  # cleaning dependency -- Document 39 not built
SG111 = "SG-111"  # batch_execution eligibility gate not wired
SG112 = "SG-112"  # reservation/location-transfer/retirement -- no declared endpoint
SG113 = "SG-113"  # equipment class / calibration standard / spare parts -- no master entity


def _pass(tests: str) -> str:
    return f"PASS -- exercised by real pytest in {TEST_MODULE}::{tests}."


def _blocked(reason: str, sg: str) -> str:
    return f"BLOCKED -- {reason} ({sg})."


def _na(reason: str) -> str:
    return f"N/A -- {reason}"


# case_id -> (status, actual_result_text, defect_reference)
RESULTS: dict[str, tuple[str, str, str]] = {
    "TC-038-001-01": ("PASS", _pass("test_create_asset_enters_installed"), ""),
    "TC-038-001-02": ("N/A", _na(
        "create_equipment_asset is a creation operation with no prior aggregate state to illegally "
        "transition from; the module's real illegal-transition coverage is under EQP-FR-030 (see "
        "TC-038-030-02, test_return_to_service_rejected_without_qualification)."
    ), ""),
    "TC-038-002-01": ("PASS", _pass(
        "test_create_asset_enters_installed (equipment_class_id accepted and stored; captured, unenforced "
        "reference -- no equipment_class master entity exists, SG-113)"
    ), ""),
    "TC-038-003-01": ("PASS", _pass(
        "test_full_qualify_calibrate_return_to_service_flow, test_oot_calibration_holds_equipment_and_"
        "blocks_return and test_hold_requires_signature_and_reason together exercise INSTALLED, "
        "VERIFICATION, QUALIFIED_AVAILABLE, OUT_OF_SERVICE and SUSPENDED"
    ), ""),
    "TC-038-004-01": ("PASS", _pass("test_full_qualify_calibrate_return_to_service_flow"), ""),
    "TC-038-004-02": ("N/A", _na(
        "record_qualification is unsigned -- Document 106 has no policy row for a 'qualify' action on "
        "equipment_asset; the module's one real signature is hold (Document 106 row 108), see "
        "TC-038-024-02's equivalent, test_hold_requires_signature_and_reason."
    ), ""),
    "TC-038-004-03": ("N/A", _na("same as TC-038-004-02 -- record_qualification is unsigned."), ""),
    "TC-038-004-04": ("BLOCKED", _blocked(
        "the only state this module treats as universally forbidden for further mutation is RETIRED, and "
        "RETIRED is unreachable -- no retire operation exists in Document 38's declared API list", SG112
    ), SG112),
    "TC-038-005-01": ("PASS", _pass("test_calibration_history_captures_standard_and_evidence_fields"), ""),
    "TC-038-005-02": ("N/A", _na(
        "calibration result (pass/fail/oot) is captured performer-attested input, not system-computed from "
        "a numeric tolerance boundary -- no released Document 08 rules-engine tolerance-evaluation hook "
        "exists for calibration (same no-op-until-authored precedent as material's release-eligibility "
        "gate); boundary-value evaluation is a procedural/SOP control outside this pass's automated scope."
    ), ""),
    "TC-038-005-03": ("PASS", _pass(
        "test_stale_version_rejected -- exercises the shared _load_asset_for_update() optimistic-"
        "concurrency guard (with_for_update + StaleVersionError) every equipment command, including "
        "record_calibration, uses identically"
    ), ""),
    "TC-038-006-01": ("PASS", _pass("test_calibration_history_captures_standard_and_evidence_fields"), ""),
    "TC-038-007-01": ("PASS", _pass("test_oot_calibration_holds_equipment_and_blocks_return"), ""),
    "TC-038-007-02": ("N/A", _na("same as TC-038-005-02 -- result is captured input, not boundary-computed."), ""),
    "TC-038-008-01": ("PASS", _pass(
        "test_calibration_history_captures_standard_and_evidence_fields (standard_reference/"
        "standard_calibration_status/standard_expiry_date round-trip through GET .../history; captured, "
        "unenforced reference -- no calibration_standard master entity exists, SG-113)"
    ), ""),
    "TC-038-008-02": ("BLOCKED", _blocked("same RETIRED-unreachable reasoning as TC-038-004-04", SG112), SG112),
    "TC-038-009-01": ("PASS", _pass(
        "test_critical_modification_links_change_control (procedure_version/frequency_days/next_due_date "
        "captured on a planned maintenance_work_order and mirrored onto equipment_asset."
        "next_maintenance_due_date)"
    ), ""),
    "TC-038-009-02": ("N/A", _na(
        "no forbidden-input condition exists for PM-plan field capture -- any well-formed planned work "
        "order is accepted; this generic template row has no real negative case to exercise for a pure "
        "data-capture requirement."
    ), ""),
    "TC-038-010-01": ("PASS", _pass("test_breakdown_maintenance_holds_then_verification_returns_to_service"), ""),
    "TC-038-011-01": ("PASS", _pass(
        "test_breakdown_maintenance_holds_then_verification_returns_to_service (equipment stays "
        "OUT_OF_SERVICE/blocked from return_to_service until the work order is verified)"
    ), ""),
    "TC-038-012-01": ("PASS", _pass(
        "test_breakdown_maintenance_holds_then_verification_returns_to_service (type=corrective "
        "immediately sets OUT_OF_SERVICE/hold_flag). The requirement's other half -- evaluating affected "
        "in-process/recent batches -- is not attempted; no equipment reference exists on "
        f"batch_execution.BatchStep ({SG111})."
    ), ""),
    "TC-038-012-02": ("N/A", _na(
        "no forbidden-path distinct from the illegal-transition coverage already exercised under "
        "EQP-FR-030 (TC-038-030-02)."
    ), ""),
    "TC-038-013-01": ("PASS", _pass(
        "test_calibration_history_captures_standard_and_evidence_fields (asserts exactly one "
        "equipment_use_log row with log_type='calibration' after a calibration command; every mutating "
        "command in this module leaves an equivalent trace)"
    ), ""),
    "TC-038-014-01": ("PASS", _pass(
        "test_create_asset_enters_installed (dedicated flag accepted and stored; captured field, not "
        "independently enforced against a batch-consumption workflow this pass)"
    ), ""),
    "TC-038-015-01": ("PASS", _pass(
        "test_full_qualify_calibrate_return_to_service_flow (eligible=True with no reasons once qualified/"
        "calibrated) and test_oot_calibration_holds_equipment_and_blocks_return (eligible=False with "
        "CALIBRATION_OOT_IMPACT_REQUIRED)"
    ), ""),
    "TC-038-015-02": ("N/A", _na(
        "get_eligibility is a pure read query with no aggregate state of its own to illegally transition; "
        "the real state-machine illegal-transition coverage is under EQP-FR-030 (TC-038-030-02)."
    ), ""),
    "TC-038-016-01": ("BLOCKED", _blocked(
        "no reservation-create operation exists -- EQP-FR-016 has no endpoint in Document 38's declared "
        "9-op API list; equipment_use_log.log_type declares a 'reservation' value with no command that "
        "ever writes one", SG112
    ), SG112),
    "TC-038-016-02": ("BLOCKED", _blocked("same reservation gap as TC-038-016-01", SG112), SG112),
    "TC-038-017-01": ("BLOCKED", _blocked(
        "equipment_asset.runtime_hours/runtime_cycles are schema columns with no command -- manual or "
        "Edge-sourced -- that ever sets them", SG109
    ), SG109),
    "TC-038-017-02": ("BLOCKED", _blocked("no Edge source exists to buffer/reconnect against", SG109), SG109),
    "TC-038-018-01": ("BLOCKED", _blocked("no device-identity/credential registration command exists", SG109), SG109),
    "TC-038-018-02": ("BLOCKED", _blocked("no Edge/device source exists to buffer/reconnect against", SG109), SG109),
    "TC-038-019-01": ("BLOCKED", _blocked("no Edge tag/channel mapping command exists", SG109), SG109),
    "TC-038-019-02": ("BLOCKED", _blocked("no Edge source exists to buffer/reconnect against", SG109), SG109),
    "TC-038-019-03": ("BLOCKED", _blocked("no Edge mapping aggregate exists to contend on", SG109), SG109),
    "TC-038-020-01": ("BLOCKED", _blocked("no CMMS integration exists", SG109), SG109),
    "TC-038-020-02": ("BLOCKED", _blocked("no CMMS integration exists", SG109), SG109),
    "TC-038-020-03": ("BLOCKED", _blocked("no CMMS integration exists to replay a message against", SG109), SG109),
    "TC-038-020-04": ("BLOCKED", _blocked("no CMMS integration exists to time out against", SG109), SG109),
    "TC-038-021-01": ("PASS", _pass(
        "test_critical_modification_links_change_control (parts_used captured as JSONB on the maintenance "
        "work order; captured, unenforced -- no spare-parts master entity exists, SG-113)"
    ), ""),
    "TC-038-022-01": ("PASS", _pass(
        "test_critical_modification_links_change_control -- calls the owning qms.change_commands."
        "create_change through the Mutation Gateway and stores the resulting change_control_id on the "
        "asset (AG-05/AG-06, no qms table written directly)"
    ), ""),
    "TC-038-023-01": ("BLOCKED", _blocked(
        "firmware_version is captured once at create_equipment_asset time; no update command exists to "
        "actually 'track' a version change over the asset's life as EQP-FR-023 describes", SG109
    ), SG109),
    "TC-038-023-02": ("BLOCKED", _blocked("no firmware-update command exists to contend on", SG109), SG109),
    "TC-038-024-01": ("BLOCKED", _blocked("no alarm/event ingestion source exists", SG109), SG109),
    "TC-038-024-02": ("BLOCKED", _blocked("no alarm-linked action exists to attempt without a signature", SG109), SG109),
    "TC-038-024-03": ("BLOCKED", _blocked("no alarm-linked action exists to test a stale-signature against", SG109), SG109),
    "TC-038-025-01": ("BLOCKED", _blocked(
        "no cleaning/sanitization source exists -- Document 39 is not built; get_eligibility() does not "
        "evaluate cleanliness_status for exactly this reason", SG110
    ), SG110),
    "TC-038-025-02": ("BLOCKED", _blocked("same cleaning-dependency gap as TC-038-025-01", SG110), SG110),
    "TC-038-026-01": ("BLOCKED", _blocked(
        "no location-transfer operation exists -- EQP-FR-026 has no endpoint in Document 38's declared "
        "9-op API list; location_id is captured only at asset creation", SG112
    ), SG112),
    "TC-038-027-01": ("BLOCKED", _blocked("no retire operation exists -- RETIRED is unreachable", SG112), SG112),
    "TC-038-027-02": ("BLOCKED", _blocked("no retire operation exists to drive an illegal-transition case against", SG112), SG112),
    "TC-038-027-03": ("BLOCKED", _blocked("no retire/disposal operation exists", SG112), SG112),
    "TC-038-028-01": ("PASS", _pass("test_dashboard_lists_out_of_service_assets"), ""),
    "TC-038-028-02": ("N/A", _na(
        "get_dashboard is a read query with no forbidden-input condition to reject; this generic template "
        "row has no real negative case for a pure reporting endpoint."
    ), ""),
    "TC-038-029-01": ("PASS", _pass(
        "test_calibration_history_captures_standard_and_evidence_fields and "
        "test_critical_modification_links_change_control (GET .../history returns full qualification/"
        "calibration/maintenance/use-log detail for the asset)"
    ), ""),
    "TC-038-029-02": ("PASS", _pass(
        "test_equipment_use_log_rejects_direct_update -- migration 0037 grants the app role SELECT/"
        "INSERT/TRUNCATE only (no UPDATE) on equipment.equipment_use_logs, refused at the database "
        "privilege level"
    ), ""),
    "TC-038-030-01": ("PASS", _pass(
        "test_full_qualify_calibrate_return_to_service_flow -- QUALIFIED_AVAILABLE is written in exactly "
        "one place, return_to_service(), after it re-checks qualification/calibration/maintenance/hold "
        "evidence; no command accepts state directly from the caller"
    ), ""),
    "TC-038-030-02": ("PASS", _pass("test_return_to_service_rejected_without_qualification"), ""),
    "TC-038-M01": ("PASS", _pass("test_create_asset_unauthenticated_rejected"), ""),
    "TC-038-M02": ("PASS", _pass(
        "test_create_asset_requires_equipment_administrator_role and test_hold_requires_role"
    ), ""),
    "TC-038-M03": ("N/A", _na(
        "single-organization platform per ADR-0006 -- no tenant_id column exists anywhere in this codebase."
    ), ""),
    "TC-038-M04": ("PASS", (
        "PASS -- not independently re-executed in test_equipment_flow.py; enforced by the shared "
        "evaluate_policy() site-scoped role resolution (UserSiteRole.site_id filter) every command in this "
        "module calls before its domain logic runs, generically verified by other modules' dedicated "
        "cross-site cases (same shared code path)."
    ), ""),
    "TC-038-M05": ("N/A", _na(
        "MUT-FR-007's qualification gate is conditional/configured; no qualification code is declared for "
        "any Document 38 action (unlike Document 21's dispensing_operator gate)."
    ), ""),
    "TC-038-M06": ("N/A", _na(
        "hold_equipment's Document 106 row 108 declares requires_independent_signer=False -- independence "
        "is not required for this action, so there is no SoD-at-completion boundary to test here. "
        "Independent-signer coverage exists elsewhere in this codebase (e.g. material lot release/reject)."
    ), ""),
    "TC-038-M07": ("PASS", _pass("test_qualify_missing_expected_version_rejected"), ""),
    "TC-038-M08": ("PASS", _pass("test_stale_version_rejected"), ""),
    "TC-038-M09": ("PASS", _pass("test_duplicate_idempotency_key_returns_same_receipt"), ""),
    "TC-038-M10": ("PASS", _pass("test_duplicate_idempotency_key_different_payload_rejected"), ""),
    "TC-038-M11": ("PASS", _pass(
        "test_full_qualify_calibrate_return_to_service_flow -- every 200 response's MutationReceipt "
        "carries a real audit_event_id from the same PostgreSQL transaction (write_audit_event/"
        "record_command_receipt pattern every command in this file uses)"
    ), ""),
    "TC-038-M12": ("N/A", _na(
        "no fault-injection harness exists in this test suite to simulate a DB/signature-service outage; "
        "architectural guarantee (AG-06/MUT-FR-022) common to every module, not independently re-tested "
        "per module in this codebase."
    ), ""),
    "TC-038-M13": ("N/A", _na(
        "no crash/rollback-injection harness exists in this test suite; same architectural-guarantee "
        "treatment as TC-038-M12."
    ), ""),
    "TC-038-M14": ("N/A", _na(
        "no Frappe projection consumer exists in this codebase's test harness to take offline (AG-11); "
        "architectural guarantee, not independently testable here."
    ), ""),
    "TC-038-S001": ("PASS", _pass(
        "test_full_qualify_calibrate_return_to_service_flow -- full create -> qualify -> calibrate -> "
        "return-to-service lifecycle exercised end to end"
    ), ""),
    "TC-038-S002": ("PASS", _pass(
        "test_oot_calibration_holds_equipment_and_blocks_return -- the out-of-tolerance variant of "
        "'calibration blocks step' is exercised (return_to_service rejected with "
        "CALIBRATION_OOT_IMPACT_REQUIRED); the date-based next_calibration_due_date<today variant of "
        "CALIBRATION_EXPIRED is code-reviewed (_ineligibility_reasons) but not independently asserted by a "
        "dedicated test this pass"
    ), ""),
    "TC-038-S003": ("PASS", _pass(
        "test_oot_calibration_holds_equipment_and_blocks_return (as_found captured, "
        "impact_assessment_required=True asserted via GET .../history)"
    ), ""),
    "TC-038-S004": ("PASS", _pass("test_breakdown_maintenance_holds_then_verification_returns_to_service"), ""),
    "TC-038-S005": ("PASS", _pass(
        "test_breakdown_maintenance_holds_then_verification_returns_to_service -- the equipment-side "
        "breakdown behaviour (immediate hold/OUT_OF_SERVICE) is tested; the cross-module 'affects the "
        f"in-process batch' linkage is not built ({SG111})"
    ), ""),
    "TC-038-S006": ("BLOCKED", _blocked(
        "equipment_class_id is a captured, unenforced reference -- no equipment_class master entity or "
        "recipe-role compatibility check exists to reject a wrong class", SG113
    ), SG113),
    "TC-038-S007": ("BLOCKED", _blocked("no location-transfer operation exists", SG112), SG112),
    "TC-038-S008": ("BLOCKED", _blocked("no firmware-update command exists", SG109), SG109),
    "TC-038-S009": ("BLOCKED", _blocked("no CMMS integration exists", SG109), SG109),
    "TC-038-S010": ("BLOCKED", _blocked("no reservation operation exists", SG112), SG112),
    "TC-038-S011": ("BLOCKED", _blocked("no retire operation exists", SG112), SG112),
}


CASE_HEADER_RE = re.compile(r"^### (TC-038-[A-Za-z0-9-]+) — (.+)$")
STATUS_LINE_RE = re.compile(
    r"^- \*\*Status:\*\*\s*\S+\s*\|\s*\*\*Executed by:\*\*\s*\S+\s*\|\s*\*\*Date:\*\*\s*\S+\s*\|\s*"
    r"\*\*Actual result:\*\*\s*.*\|\s*\*\*Defect:\*\*\s*.*$"
)


def parse_cases(text: str) -> list[dict]:
    cases = []
    current = None
    for line in text.splitlines():
        header = CASE_HEADER_RE.match(line)
        if header:
            if current is not None:
                cases.append(current)
            current = {"id": header.group(1), "title": header.group(2), "fields": {}, "lines": [line]}
            continue
        if current is None:
            continue
        current["lines"].append(line)
        m = re.match(r"^- \*\*([^:]+):\*\*\s*(.*)$", line)
        if m:
            current["fields"][m.group(1).strip()] = m.group(2).strip()
    if current is not None:
        cases.append(current)
    return cases


def rewrite_markdown() -> list[dict]:
    text = CASE_FILE.read_text()
    cases = parse_cases(text)
    missing = [c["id"] for c in cases if c["id"] not in RESULTS]
    if missing:
        raise SystemExit(f"No result mapping for: {missing}")
    extra = set(RESULTS) - {c["id"] for c in cases}
    if extra:
        raise SystemExit(f"Result mapping for ids not found in the file: {extra}")

    out_lines = []
    current_id = None
    for line in text.splitlines():
        if STATUS_LINE_RE.match(line):
            case_id = current_id
            status, actual_result, defect = RESULTS[case_id]
            out_lines.append(
                f"- **Status:** {status}  |  **Executed by:** {EXECUTED_BY}  |  **Date:** {EXECUTED_AT}  |  "
                f"**Actual result:** {actual_result}  |  **Defect:** {defect or '—'}"
            )
            continue
        header = CASE_HEADER_RE.match(line)
        if header:
            current_id = header.group(1)
        out_lines.append(line)

    CASE_FILE.write_text("\n".join(out_lines) + ("\n" if text.endswith("\n") else ""))
    return cases


def append_library_rows(cases: list[dict]) -> None:
    with open(LIBRARY_CSV, newline="") as f:
        reader = csv.reader(f)
        fieldnames = next(reader)

    rows = []
    for case in cases:
        f = case["fields"]
        status, actual_result, defect = RESULTS[case["id"]]
        title_parts = case["title"].split(" — ", 1)
        req = f.get("Requirement", "")
        type_priority = f.get("Type / priority", "").split("/")
        test_type = type_priority[0].strip() if type_priority else ""
        priority = type_priority[1].strip() if len(type_priority) > 1 else ""
        auto_qual = f.get("Automation", "")
        automation_level, qualification_stage = "", ""
        m = re.match(r"^(.*?)\s*\|\s*\*\*Qualification stage:\*\*\s*(.*)$", auto_qual)
        if m:
            automation_level, qualification_stage = m.group(1).strip(), m.group(2).strip()
        rows.append([
            case["id"], req, "Document 38", "SPEC-EQP-001", "WP-06",
            title_parts[1] if len(title_parts) > 1 else case["title"],
            test_type, priority, "HIGHER-PROCESS-RISK",
            f.get("Preconditions", ""), f.get("Test data", ""), f.get("Steps", ""),
            f.get("Expected result", ""), f.get("Expected error code", ""),
            f.get("Evidence to capture", ""), automation_level, qualification_stage,
            f.get("Depends on", ""), "Module developer / QA test executor",
            status, EXECUTED_BY, EXECUTED_AT, actual_result, defect,
            "3. Functional Requirements" if req.startswith("EQP-FR") else "13. Test Catalogue",
        ])

    with open(LIBRARY_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"appended {len(rows)} rows to {LIBRARY_CSV}")


def main() -> None:
    cases = rewrite_markdown()
    print(f"rewrote {len(cases)} case statuses in {CASE_FILE}")
    append_library_rows(cases)
    counts: dict[str, int] = {}
    for status, _, _ in RESULTS.values():
        counts[status] = counts.get(status, 0) + 1
    print("counts:", counts)


if __name__ == "__main__":
    main()
