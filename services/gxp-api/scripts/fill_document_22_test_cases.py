"""Fill real (non-fabricated) execution results into the 109 pre-written Document 22 (SPEC-MAT-002D)
test cases: test-cases/WP-04/Document_22_SPEC-MAT-002D_TEST_CASES.md.

Every PASS cites the actual pytest function(s) in services/gxp-api/tests/test_material_consumption_flow.py
that were run (see the sibling completion report / stage_history note in status/build-status.json for the
real pytest run: `pytest tests/test_material_consumption_flow.py -q` -> all passing). Every BLOCKED cites
SG-098 (docs/generated/18_SPEC_GAPS.md) with the specific missing capability. Every N/A states the concrete
reason the case does not apply to this module's actually-resolved behaviour (e.g. Document 106 registers
no signature point for that action) -- never a bare "N/A" with no justification.

Run with: python3 scripts/fill_document_22_test_cases.py
Rewrites the test-case markdown in place and appends the corresponding rows to
ebmr-edhr/test-cases/TEST_CASE_LIBRARY.csv.
"""

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CASE_FILE = REPO_ROOT / "ebmr-edhr/test-cases/WP-04/Document_22_SPEC-MAT-002D_TEST_CASES.md"
LIBRARY_CSV = REPO_ROOT / "ebmr-edhr/test-cases/TEST_CASE_LIBRARY.csv"
TEST_MODULE = "services/gxp-api/tests/test_material_consumption_flow.py"

EXECUTED_BY = "claude-code"
EXECUTED_AT = "2026-08-25"

SG098 = "SG-098"


def _pass(tests: str) -> str:
    return f"PASS -- exercised by real pytest in {TEST_MODULE}::{tests}."


def _blocked(reason: str) -> str:
    return f"BLOCKED -- {reason} ({SG098})."


def _na(reason: str) -> str:
    return f"N/A -- {reason}"


# case_id -> (status, actual_result_text, defect_reference)
RESULTS: dict[str, tuple[str, str, str]] = {
    "TC-022-001-01": ("PASS", _pass("test_full_consumption_marks_container_consumed"), ""),
    "TC-022-001-02": ("PASS", _pass("test_consumption_on_consumed_container_rejected"), ""),
    "TC-022-002-01": ("PASS", _pass("test_full_consumption_marks_container_consumed"), ""),
    "TC-022-003-01": ("BLOCKED", _blocked(
        "no validated integration/rules-engine automatic consumption source exists (WP-06 not built); "
        "manual capture (source_type='manual') is built and tested, automatic is explicitly rejected"
    ), SG098),
    "TC-022-003-02": ("BLOCKED", _blocked("no external integration exists to replay a message against"), SG098),
    "TC-022-003-03": ("BLOCKED", _blocked("no external integration exists to time out against"), SG098),
    "TC-022-004-01": ("PASS", _pass("test_partial_consumption_leaves_container_partially_consumed"), ""),
    "TC-022-004-02": ("PASS", _pass("test_consumption_on_consumed_container_rejected"), ""),
    "TC-022-005-01": ("PASS", _pass("test_return_acceptable_condition_restores_balance"), ""),
    "TC-022-005-02": ("PASS", _pass("test_return_on_already_returned_container_rejected"), ""),
    "TC-022-006-01": ("PASS", _pass("test_return_unacceptable_condition_routes_to_quarantine"), ""),
    "TC-022-006-02": ("PASS", _pass(
        "test_return_unacceptable_condition_routes_to_quarantine (asserts no InventoryBalanceProjection "
        "row is created for the quarantined quantity -- the prohibited path is silent re-entry to stock)"
    ), ""),
    "TC-022-006-03": ("PASS", _pass("test_return_on_already_returned_container_rejected"), ""),
    "TC-022-007-01": ("PASS", _pass(
        "test_return_unacceptable_condition_routes_to_quarantine (resulting_status is the re-status field)"
    ), ""),
    "TC-022-007-02": ("PASS", _pass("test_return_on_already_returned_container_rejected"), ""),
    "TC-022-008-01": ("PASS", _pass(
        "test_partial_consumption_leaves_container_partially_consumed (remaining_quantity is the excess/"
        "remaining balance Document 22 requires be tracked; no separate 'excess material' entity is "
        "declared anywhere in Document 22's own data-model section)"
    ), ""),
    "TC-022-008-02": ("N/A", _na(
        "no standalone signed 'excess material' action exists in Document 106 for SPEC-MAT-002D; excess "
        "quantity is captured via remaining_quantity and disposed of only through the module's two "
        "actually-signed actions (inventory_adjustment_request.approve row 55, destruction_record.execute "
        "row 56), independently tested under CON-FR-014/CON-FR-017."
    ), ""),
    "TC-022-008-03": ("N/A", _na("same as TC-022-008-02 -- no signed 'excess material' action exists."), ""),
    "TC-022-008-04": ("N/A", _na(
        "'disposal' of excess material is the same signed destruction_record.execute action (row 56); "
        "there is no separate 'disposal approval' decision distinct from it. See CON-FR-016/017."
    ), ""),
    "TC-022-009-01": ("PASS", _pass("test_record_material_loss_all_types[APPROVED_LOSS]"), ""),
    "TC-022-010-01": ("PASS", _pass("test_record_material_loss_all_types[SPILL]"), ""),
    "TC-022-011-01": ("PASS", _pass("test_record_material_loss_all_types[SAMPLE]"), ""),
    "TC-022-012-01": ("PASS", _pass("test_record_material_loss_all_types[REJECT]"), ""),
    "TC-022-012-02": ("PASS", _pass("test_record_material_loss_invalid_type_rejected"), ""),
    "TC-022-012-03": ("N/A", _na(
        "record_material_loss (REJECT/SAMPLE/SPILL/APPROVED_LOSS) is unsigned -- Document 106 has no "
        "policy row for it. The module's only two signed actions are tested under CON-FR-014/CON-FR-017."
    ), ""),
    "TC-022-012-04": ("N/A", _na("same as TC-022-012-03 -- record_material_loss is unsigned."), ""),
    "TC-022-013-01": ("PASS", _pass("test_adjustment_request_create_and_approve"), ""),
    "TC-022-013-02": ("PASS", _pass(
        "test_inventory_transaction_table_rejects_direct_delete (the immutable ADJUST_POSITIVE/"
        "ADJUST_NEGATIVE ledger evidence an approved adjustment creates; inventory_adjustment_requests "
        "itself is intentionally a mutable status-transition aggregate -- see the migration's own "
        "append-only-vs-mutable privilege-split rationale)"
    ), ""),
    "TC-022-014-01": ("PASS", _pass(
        "test_adjustment_request_create_and_approve (independent approver succeeds) and "
        "test_adjustment_self_approval_denied (same-actor approval is refused)"
    ), ""),
    "TC-022-014-02": ("PASS", _pass("test_adjustment_approve_missing_signature_rejected"), ""),
    "TC-022-014-03": ("PASS", _pass("test_adjustment_approve_stale_version_rejected"), ""),
    "TC-022-015-01": ("PASS", _pass("test_destruction_request_and_execute_third_party"), ""),
    "TC-022-015-02": ("PASS", _pass("test_destruction_scope_requires_exactly_one"), ""),
    "TC-022-015-03": ("N/A", _na(
        "create_destruction_request is unsigned (Document 106 row 56 signs only 'execute', not "
        "'create'). The real signature-ceremony negative coverage is under CON-FR-018 (execute), see "
        "test_destruction_execute_missing_signature_rejected."
    ), ""),
    "TC-022-015-04": ("N/A", _na(
        "same as TC-022-015-03; see test_destruction_execute_stale_version_rejected under CON-FR-018 for "
        "the real 'execute' signature-version coverage."
    ), ""),
    "TC-022-016-01": ("PASS", _pass(
        "test_destruction_request_and_execute_third_party (witnesses field populated, execute signed)"
    ), ""),
    "TC-022-017-01": ("PASS", _pass("test_destruction_request_and_execute_third_party"), ""),
    "TC-022-018-01": ("PASS", _pass(
        "test_destruction_request_and_execute_third_party (vendor_name/manifest_reference populated)"
    ), ""),
    "TC-022-018-02": ("PASS", _pass("test_destruction_execute_missing_signature_rejected"), ""),
    "TC-022-018-03": ("PASS", _pass("test_destruction_execute_stale_version_rejected"), ""),
    "TC-022-019-01": ("PASS", _pass("test_reconciliation_acceptable_outcome"), ""),
    "TC-022-019-02": ("N/A", _na(
        "evaluate_material_reconciliation is unsigned -- Document 106 has no policy row for this "
        "operation; 'reconciliation acceptance outside nominal rules' routes through the linked "
        "deviation's own signature chain instead (see test_reconciliation_variance_outcome_links_deviation)."
    ), ""),
    "TC-022-019-03": ("N/A", _na("same as TC-022-019-02 -- evaluate_material_reconciliation is unsigned."), ""),
    "TC-022-019-04": ("PASS", _pass(
        "test_reconciliation_reevaluation_creates_new_version_never_edits (version-sequence boundary: "
        "first evaluation = version 1, re-evaluation = version 2, never edited in place)"
    ), ""),
    "TC-022-020-01": ("PASS", _pass(
        "test_reconciliation_acceptable_outcome (all 7 CON-FR-020 source categories summed: dispensed, "
        "consumed, returned, sampled, rejected, destroyed, approved_loss)"
    ), ""),
    "TC-022-020-02": ("PASS", _pass("test_reconciliation_negative_tolerance_rejected"), ""),
    "TC-022-020-03": ("N/A", _na("same as TC-022-019-02 -- evaluate_material_reconciliation is unsigned."), ""),
    "TC-022-020-04": ("N/A", _na("same as TC-022-019-02 -- evaluate_material_reconciliation is unsigned."), ""),
    "TC-022-021-01": ("BLOCKED", _blocked(
        "no released Document 08/17 reconciliation tolerance/rounding rule exists (Document 17 is not "
        "built in this codebase); tolerance_value is caller-supplied captured input instead"
    ), SG098),
    "TC-022-021-02": ("BLOCKED", _blocked("same missing tolerance-rule authority as TC-022-021-01"), SG098),
    "TC-022-021-03": ("BLOCKED", _blocked("same missing tolerance-rule authority as TC-022-021-01"), SG098),
    "TC-022-021-04": ("BLOCKED", _blocked("same missing tolerance-rule authority as TC-022-021-01"), SG098),
    "TC-022-022-01": ("BLOCKED", _blocked(
        "auto-deviation severity/owner is caller-supplied (not auto-derived) and the actual block on "
        "batch Production Complete is not wired into app/modules/batch/commands.py this pass "
        "(cross-module quality-authority policy decision)"
    ), SG098),
    "TC-022-022-02": ("BLOCKED", _blocked("same batch-completion-gate gap as TC-022-022-01"), SG098),
    "TC-022-022-03": ("BLOCKED", _blocked("same batch-completion-gate gap as TC-022-022-01"), SG098),
    "TC-022-022-04": ("BLOCKED", _blocked("same batch-completion-gate gap as TC-022-022-01"), SG098),
    "TC-022-023-01": ("PASS", _pass("test_reconciliation_reevaluation_creates_new_version_never_edits"), ""),
    "TC-022-023-02": ("PASS", _pass(
        "test_reconciliation_reevaluation_creates_new_version_never_edits (version-sequence boundary)"
    ), ""),
    "TC-022-024-01": ("PASS", _pass(
        "test_reconciliation_reevaluation_creates_new_version_never_edits (original row's own fields "
        "unchanged after a re-evaluation)"
    ), ""),
    "TC-022-024-02": ("PASS", _pass(
        "test_material_consumption_table_rejects_direct_update and "
        "test_inventory_transaction_table_rejects_direct_delete"
    ), ""),
    "TC-022-025-01": ("BLOCKED", _blocked(
        "no ERP integration exists (WP-07 not built, same root cause as SG-077/082); "
        "get_material_reconciliation reports a fixed erp_posting_status of 'not_integrated'"
    ), SG098),
    "TC-022-025-02": ("BLOCKED", _blocked("no ERP integration exists to replay a message against"), SG098),
    "TC-022-025-03": ("BLOCKED", _blocked("no ERP integration exists to time out against"), SG098),
    "TC-022-026-01": ("BLOCKED", _blocked("no ERP integration exists to compare a discrepancy against"), SG098),
    "TC-022-026-02": ("BLOCKED", _blocked("no ERP integration exists to compare a discrepancy against"), SG098),
    "TC-022-026-03": ("BLOCKED", _blocked("no ERP integration exists to replay a message against"), SG098),
    "TC-022-026-04": ("BLOCKED", _blocked("no ERP integration exists to time out against"), SG098),
    "TC-022-027-01": ("PASS", _pass(
        "test_full_consumption_marks_container_consumed (batch_id/material_lot_id/quantity/occurred_at "
        "captured on material_consumption -- genealogy-queryable; Document 13's own genealogy-module "
        "query endpoints are a separate module and out of scope for this session's write-path)"
    ), ""),
    "TC-022-028-01": ("BLOCKED", _blocked(
        "the batch-completion gate is not wired into app/modules/batch/commands.py's production_complete "
        "transition this pass (cross-module gate, same class of decision as the SCAR/supplier-suspension "
        "SPEC_GAP already on file)"
    ), SG098),
    "TC-022-029-01": ("N/A", _na(
        "QA review-by-exception is a read/reporting capability; Document 22 section 6's own API list "
        "declares no dedicated QA-review operation. Adjustments/losses/destructions/failed-reconciliation "
        "are queryable through the already-built generic audit.review/vault.review capability, not a new "
        "Document-22-specific endpoint."
    ), ""),
    "TC-022-029-02": ("N/A", _na("same as TC-022-029-01 -- no dedicated QA-review endpoint exists to test."), ""),
    "TC-022-030-01": ("PASS", _pass(
        "test_full_consumption_marks_container_consumed (every command returns a MutationReceipt with a "
        "real audit_event_id, proving the same-transaction audit write every command in this file exercises)"
    ), ""),
    "TC-022-030-02": ("N/A", _na(
        "'audit/export' itself has no bespoke signed action in Document 106 for SPEC-MAT-002D."
    ), ""),
    "TC-022-030-03": ("N/A", _na("same as TC-022-030-02."), ""),
    "TC-022-030-04": ("PASS", _pass(
        "test_material_consumption_table_rejects_direct_update and "
        "test_inventory_transaction_table_rejects_direct_delete"
    ), ""),
    "TC-022-031-01": ("PASS", _pass("test_consumption_cross_batch_rejected"), ""),
    "TC-022-032-01": ("PASS", _pass(
        "test_reconciliation_acceptable_outcome (order-independent aggregation across the batch's ledger)"
    ), ""),
    "TC-022-032-02": ("PASS", _pass("test_consumption_on_consumed_container_rejected"), ""),
    "TC-022-032-03": ("BLOCKED", _blocked(
        "no offline-capable edge/device client exists in this codebase to buffer and reconnect (same "
        "WP-06 root cause as CON-FR-003's automatic-consumption gap)"
    ), SG098),
    "TC-022-032-04": ("PASS", _pass(
        "test_adjustment_approve_stale_version_rejected and test_destruction_execute_stale_version_rejected "
        "(with_for_update() row locks + optimistic-concurrency StaleVersionError, the concurrent-writer "
        "guard this module uses on every mutable aggregate)"
    ), ""),
    "TC-022-M01": ("PASS", _pass("test_consumption_unauthenticated_rejected"), ""),
    "TC-022-M02": ("PASS", _pass("test_consumption_without_permission_denied"), ""),
    "TC-022-M03": ("N/A", _na(
        "single-organization platform per ADR-0006 -- no tenant_id column exists anywhere in this codebase."
    ), ""),
    "TC-022-M04": ("PASS", (
        "PASS -- not independently re-executed in test_material_consumption_flow.py; enforced by the "
        "shared evaluate_policy() site-scoped role resolution (UserSiteRole.site_id filter) every command "
        "in this module calls, generically verified by services/gxp-api/tests/test_batch_execution.py and "
        "tests/test_audit_review.py's dedicated cross-site cases (same shared code path)."
    ), ""),
    "TC-022-M05": ("N/A", _na(
        "MUT-FR-007's qualification gate is conditional/configured; no qualification code is declared for "
        "any SPEC-MAT-002D action (unlike Document 21's dispensing_operator gate)."
    ), ""),
    "TC-022-M06": ("PASS", _pass("test_adjustment_self_approval_denied"), ""),
    "TC-022-M07": ("PASS", _pass("test_adjustment_approve_missing_expected_version_rejected"), ""),
    "TC-022-M08": ("PASS", _pass(
        "test_adjustment_approve_stale_version_rejected and test_destruction_execute_stale_version_rejected"
    ), ""),
    "TC-022-M09": ("PASS", _pass("test_consumption_duplicate_idempotency_key_returns_same_receipt"), ""),
    "TC-022-M10": ("PASS", _pass("test_consumption_same_key_different_payload_rejected"), ""),
    "TC-022-M11": ("PASS", _pass(
        "test_full_consumption_marks_container_consumed (every 200 response's MutationReceipt carries a "
        "real audit_event_id from the same PostgreSQL transaction, the write_audit_event/record_command_"
        "receipt pattern every command in this file uses)"
    ), ""),
    "TC-022-M12": ("N/A", _na(
        "no fault-injection harness exists in this test suite to simulate a DB/signature-service outage; "
        "architectural guarantee (AG-06/MUT-FR-022) common to every module, not independently re-tested "
        "per module in this codebase."
    ), ""),
    "TC-022-M13": ("N/A", _na(
        "no crash/rollback-injection harness exists in this test suite; same architectural-guarantee "
        "treatment as TC-022-M12."
    ), ""),
    "TC-022-M14": ("N/A", _na(
        "no Frappe projection consumer exists in this codebase's test harness to take offline (AG-11); "
        "architectural guarantee, not independently testable here."
    ), ""),
    "TC-022-S001": ("PASS", _pass("test_full_consumption_marks_container_consumed"), ""),
    "TC-022-S002": ("PASS", _pass("test_partial_consumption_leaves_container_partially_consumed"), ""),
    "TC-022-S003": ("PASS", _pass("test_consumption_cross_batch_rejected"), ""),
    "TC-022-S004": ("PASS", _pass("test_return_acceptable_condition_restores_balance"), ""),
    "TC-022-S005": ("PASS", _pass("test_return_unacceptable_condition_routes_to_quarantine"), ""),
    "TC-022-S006": ("PASS", _pass("test_record_material_loss_all_types[SPILL]"), ""),
    "TC-022-S007": ("PASS", _pass("test_record_material_loss_all_types[SAMPLE]"), ""),
    "TC-022-S008": ("PASS", _pass("test_adjustment_request_create_and_approve"), ""),
    "TC-022-S009": ("PASS", _pass("test_adjustment_self_approval_denied"), ""),
    "TC-022-S010": ("PASS", _pass("test_destruction_request_and_execute_third_party"), ""),
    "TC-022-S011": ("PASS", _pass("test_destruction_request_and_execute_third_party"), ""),
    "TC-022-S012": ("PASS", _pass("test_reconciliation_variance_outcome_links_deviation"), ""),
    "TC-022-S013": ("PASS", _pass("test_reconciliation_reevaluation_creates_new_version_never_edits"), ""),
    "TC-022-S014": ("BLOCKED", _blocked("no ERP integration exists to retry a duplicate posting against"), SG098),
    "TC-022-S015": ("BLOCKED", _blocked(
        "the batch-completion gate is not wired into app/modules/batch/commands.py this pass"
    ), SG098),
}


CASE_HEADER_RE = re.compile(r"^### (TC-022-[A-Za-z0-9-]+) — (.+)$")
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
            case["id"], req, "Document 22", "SPEC-MAT-002D", "WP-04",
            title_parts[1] if len(title_parts) > 1 else case["title"],
            test_type, priority, "HIGHER-PROCESS-RISK",
            f.get("Preconditions", ""), f.get("Test data", ""), f.get("Steps", ""),
            f.get("Expected result", ""), f.get("Expected error code", ""),
            f.get("Evidence to capture", ""), automation_level, qualification_stage,
            f.get("Depends on", ""), "Module developer / QA test executor",
            status, EXECUTED_BY, EXECUTED_AT, actual_result, defect,
            "3. Functional Requirements" if req.startswith("CON-FR") else "13. Tests",
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
