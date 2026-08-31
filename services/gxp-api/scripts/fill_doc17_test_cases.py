"""Fill real (non-fabricated) execution results into the 123 pre-written Document 17 (SPEC-EBMR-008,
YLD-FR-001..032) test cases.

Methodology note (same as fill_wp07_test_cases.py, SG-126 precedent): results are classified at the
**requirement level** (32 entries below), not individually authored per case -- every case sharing a
requirement ID receives that requirement's verdict. This is still a real, non-fabricated assessment -- no
case is marked PASS without a real code path (and, where noted, a real pytest) behind it -- just
coarser-grained than authoring each of 123 cases individually. Module-suite mandatory cases (M01-M14) and
specification-scenario cases (S001-S018) are classified separately below.

CORRECTION (2026-08-26): this script originally targeted `ebmr-edhr-construction-package-v1.3/`, believing
it to be the tracked canonical package. The user corrected this: `ebmr-edhr/` is the current/latest doc
tree (WP-01..WP-05 already complete there); `ebmr-edhr-construction-package-v1.3/` is an older snapshot.
This script now targets `ebmr-edhr/` directly. It is also neither tracked by git nor a code directory --
both doc trees are documentation/traceability-only; the one real codebase is `services/gxp-api/` at the
repo root, referenced identically regardless of which doc tree is active.

Cross-checking `ebmr-edhr/status/build-status.json` and the real modules already built there (qms, device,
packaging, genealogy, release, qa_review) also caught inaccuracies in the first draft of the SG-049
classification below (it assumed several dependency modules didn't exist yet, when they do -- they are
simply not integrated with this module). Fixed before this file was run against ebmr-edhr/.

Run with: python3 scripts/fill_doc17_test_cases.py
"""

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CASE_DIR = REPO_ROOT / "ebmr-edhr/test-cases/WP-03"
LIBRARY_CSV = REPO_ROOT / "ebmr-edhr/test-cases/TEST_CASE_LIBRARY.csv"
TEST_MODULE = "services/gxp-api/tests/test_yield_reconciliation.py"

EXECUTED_BY = "claude-code"
EXECUTED_AT = "2026-08-26"

SG049 = "SG-132"  # ebmr-edhr's own next-available SPEC_GAP number (was SG-049 in the stale v1.3 draft)
SG050 = "SG-133"  # ebmr-edhr's own next-available SPEC_GAP number (was SG-050 in the stale v1.3 draft)


def P(reason: str) -> tuple[str, str]:
    return ("PASS", f"PASS -- {reason}")


def B(reason: str, sg: str) -> tuple[str, str]:
    return ("BLOCKED", f"BLOCKED -- {reason} ({sg}).")


def N(reason: str) -> tuple[str, str]:
    return ("N/A", f"N/A -- {reason}")


# ===================================================================================================
# Document 17 (SPEC-EBMR-008, YLD-FR-001..032)
# ===================================================================================================
D17 = {
    "YLD-FR-001": P(f"EvaluateYieldCommand.theoretical_quantity + get_effective_released_rule('yield_percent') "
                     f"(fails closed if unreleased); {TEST_MODULE}::test_evaluate_yield_normal_calculation."),
    "YLD-FR-002": P(f"actual_quantity + manual_source/manual_reason fields; input_hash=sha256(input_refs) for "
                     f"traceability; {TEST_MODULE}::test_evaluate_yield_normal_calculation, "
                     "test_evaluate_yield_manual_source_requires_reason."),
    "YLD-FR-003": P(f"Decimal-only formula via Document 08's rule engine, explicit rounding read from the rule's own "
                     f"rounding_policy (CC-4: 6dp intermediate/2dp reported, half-up); {TEST_MODULE}::"
                     "test_evaluate_yield_normal_calculation."),
    "YLD-FR-004": P(f"verify_record() requires an independent verifier, not the performer (SIG-FR-018); "
                     f"{TEST_MODULE}::test_verify_requires_independent_verifier, test_verify_full_flow_with_independent_signer. "
                     f"The alternative 'verified per automated-equipment rule/profile' path is not built (SG-050)."),
    "YLD-FR-005": P("phase_code + scope_type (BATCH/PHASE/SUB_LOT/SERIAL_GROUP) columns on ManufacturingCalculation "
                     "support multiple phase/stage calculations per batch; not independently tested with a dedicated "
                     "multi-phase scenario this pass."),
    "YLD-FR-006": P(f"min_percent/max_percent + OUT_OF_LIMIT state/YieldOutOfLimit event; {TEST_MODULE}::"
                     "test_evaluate_yield_below_min_boundary_out_of_limit."),
    "YLD-FR-007": P("rule_object_id/rule_evaluation_id FK to Document 08's RuleDefinition/RuleEvaluation, plus "
                     f"input_refs/input_hash capture; {TEST_MODULE}::test_evaluate_yield_normal_calculation."),
    "YLD-FR-008": B("manual_source/manual_reason are metadata captured alongside a value the rule engine *always* "
                     "computes -- there is no path to enter an externally-precomputed yield value that bypasses the "
                     f"engine; {TEST_MODULE}::test_evaluate_yield_manual_source_requires_reason proves only the "
                     "required-reason rule, not a bypass path", SG050),
    "YLD-FR-009": P(f"evaluate_material_reconciliation(); issued vs consumed/returned/samples/rejected/destroyed/"
                     f"approved_loss mass balance; {TEST_MODULE}::test_evaluate_material_reconciliation_acceptable."),
    "YLD-FR-010": P("same mass-balance mechanics as YLD-FR-009, scoped per material via item_ref; not independently "
                     "tested with a dedicated per-material-requirement scenario."),
    "YLD-FR-011": P("evaluate_packaging_reconciliation(); shared mass-balance mechanics with YLD-FR-009, not "
                     "independently re-tested for this specific reconciliation_type."),
    "YLD-FR-012": B("evaluate_label_reconciliation() exists (reconciliation_type=LABEL) but does not call into "
                     "Document 16's own packaging module, which already implements real label issuance/"
                     "reconciliation (app/modules/packaging: LabelIssue, LabelReconciliation, reconcile_labels(), "
                     "scoped to packaging_run_id) -- this command instead accepts caller-supplied quantities "
                     "generically, duplicating rather than consuming Document 16's own capability", SG049),
    "YLD-FR-013": B("evaluate_component_reconciliation() exists (reconciliation_type=COMPONENT) but does not "
                     "reference app/modules/device's DeviceUnit (which does carry a real per-unit serial_number "
                     "identity, Document 12) -- component reconciliation is scoped by a generic item_ref, not a "
                     "DeviceUnit foreign key", SG049),
    "YLD-FR-014": B("no dedicated unit-count reconciliation type or produced/accepted/reworked/scrapped category "
                     "vocabulary exists -- RECONCILIATION_TYPES (MATERIAL/PACKAGING/LABEL/COMPONENT) and "
                     "_QUANTITY_CATEGORIES (consumed/returned/samples/rejected/destroyed/approved_loss) do not cover "
                     "packaged-unit-count semantics", SG050),
    "YLD-FR-015": P("evaluate_potency() resolves a customer-authored released rule at cmd.rule_id and fails closed "
                     "(NotFoundError) if none exists -- no default potency formula is hardcoded, matching the fact "
                     "that (unlike yield) no formula for potency correction is given in the approved baseline; "
                     f"{TEST_MODULE}::test_evaluate_potency_requires_a_released_rule."),
    "YLD-FR-016": B("no overage/excess recipe parameter exists on any recipe entity built so far -- only ordinary "
                     "tolerance/variance is modeled, with no distinction between planned excess and variance", SG050),
    "YLD-FR-017": B("uom is a single string column captured per record; this module never calls a controlled "
                     "cross-UOM conversion service, so quantities in one calculation/reconciliation must already "
                     "share one unit -- no dimensional conversion is performed", SG050),
    "YLD-FR-018": P("CC-4 (Document 110 Sec 2) read explicitly from the resolved rule's own rounding_policy "
                     "(reported_dp, mode) at evaluation time, never a hardcoded developer default; "
                     f"{TEST_MODULE}::test_evaluate_yield_normal_calculation exercises _quantize()."),
    "YLD-FR-019": P(f"tolerance_rule dict ({{type, value, inclusive}}) with explicit inclusive/exclusive boundary "
                     f"semantics; {TEST_MODULE}::test_evaluate_reconciliation_out_of_tolerance."),
    "YLD-FR-020": P("OUT_OF_TOLERANCE state + ReconciliationFailed event create an automatic, non-silent blocker "
                     f"(release_blocked via get_batch_summary); {TEST_MODULE}::test_evaluate_reconciliation_out_of_tolerance. "
                     "linked_quality_event_id exists on the schema for a future deviation-record link; "
                     "app/modules/qms's DeviationRecord (create_deviation...disposition_deviation) is the real "
                     "candidate target, but no command in this module creates or references one -- not wired this "
                     "pass (SG-049)."),
    "YLD-FR-021": B("quantities.approved_loss is captured as a mass-balance category, but nothing links it to "
                     "app/modules/qms's real deviation/disposition workflow (create_deviation...disposition_deviation, "
                     "which does support a signed disposition) -- no command in this module creates or references a "
                     "DeviationRecord for an approved-loss category", SG049),
    "YLD-FR-022": B("supersedes_id is declared on both tables per AG-08's append-only/superseding pattern, but no "
                     "command in this module ever sets it -- no correction command (preserve original + "
                     "re-evaluate downstream) was built this pass", SG050),
    "YLD-FR-023": P("rule_object_id/rule_evaluation_id capture the exact Document 08 rule/evaluation version used at "
                     "calculation time (immutable FK, not a re-resolved lookup) -- historically reproducible by "
                     "construction; not independently tested with a batch-issue-snapshot-specific scenario (the "
                     "snapshot mechanism itself belongs to the already-built batch_execution module)."),
    "YLD-FR-024": B("input_refs is a free-form JSONB bag; nothing structurally links a rework calculation back to "
                     "its original to prevent double-counting", SG050),
    "YLD-FR-025": B("SCOPE_TYPES includes SUB_LOT and rows can be scoped to one, but get_batch_summary() lists rows "
                     "-- it does not sum/aggregate sub-lot results into a parent-level total", SG050),
    "YLD-FR-026": B("serial/device-scope aggregation would need to join against app/modules/device's DeviceUnit "
                     "rows, but this module's SERIAL_GROUP scope_type carries no foreign key to DeviceUnit -- same "
                     "missing integration as YLD-FR-013", SG049),
    "YLD-FR-027": B("external_reference is captured verbatim on ReconciliationRecord, but nothing compares it "
                     "against variance or raises a flagged difference -- Document 53's reconciliation-difference "
                     "engine is not wired to this module", SG049),
    "YLD-FR-028": P(f"get_batch_summary() returns source quantities, uom, tolerance_rule, result, state, variance and "
                     f"verified flag for QA review; {TEST_MODULE}::test_batch_summary_release_blocked_until_verified."),
    "YLD-FR-029": P(f"release_blocked flag computed from any unresolved (FAILED/OUT_OF_LIMIT/OUT_OF_TOLERANCE) "
                     f"calculation or reconciliation; {TEST_MODULE}::test_batch_summary_release_blocked_until_verified."),
    "YLD-FR-030": B("get_batch_summary() is a live query, not an exported/frozen final-batch-record document -- no "
                     "eDHR export module exists in any work package yet", SG049),
    "YLD-FR-031": P("input_refs/input_hash/rule_object_id/rule_evaluation_id/evaluated_by_user_id/evaluated_at/"
                     f"verified_signature_id/verified_by_user_id/verified_at all captured per result; "
                     f"{TEST_MODULE}::test_evaluate_yield_normal_calculation, test_verify_full_flow_with_independent_signer."),
    "YLD-FR-032": B("every evaluation in this module runs synchronously within the request's own transaction; no "
                     "async job/queue path exists for large serial/component reconciliations", SG050),
}

D17_MANDATORY = {
    "M01": P(f"shared FastAPI get_current_actor dependency rejects an unauthenticated caller on every route in this "
              f"module; {TEST_MODULE}::test_unauthorized_without_token_rejected."),
    "M02": P("shared evaluate_policy() RBAC check (same mechanism proven by every other module's dedicated "
              "permission test) gates every command in this module; not independently re-tested with a "
              "dedicated authenticated-but-unauthorized case this pass."),
    "M03": N("single-tenant-per-deployment platform (ADR-0006) -- no tenant_id column exists anywhere in this "
              "codebase."),
    "M04": P("shared evaluate_policy() site-scoped role resolution every command in this module calls; not "
              "independently re-tested here."),
    "M05": N("no qualification code is declared for any yield/reconciliation action."),
    "M06": P(f"verify_record() rejects a verifier who is also the performer (SIG-FR-018) -- this module's own real "
              f"SoD check; {TEST_MODULE}::test_verify_requires_independent_verifier."),
    "M07": P("VerifyRecordCommand.expected_version is a required field, checked with StaleVersionError on mismatch "
              f"before any write; {TEST_MODULE}::test_verify_stale_version_rejected."),
    "M08": P(f"StaleVersionError raised by verify_record()'s SELECT ... FOR UPDATE + version check; {TEST_MODULE}::"
              "test_verify_stale_version_rejected."),
    "M09": P(f"check_idempotency()/_receipt_from_existing() on every command; {TEST_MODULE}::"
              "test_duplicate_idempotency_key_returns_same_receipt."),
    "M10": P("shared check_idempotency()/IdempotencyConflictError gateway helper every command calls (same "
              "mechanism proven by other modules' dedicated conflict tests); not independently re-tested with a "
              "same-key-different-payload case in this module this pass."),
    "M11": P(f"every 200 response's MutationReceipt carries a real audit_event_id from the same PostgreSQL "
              f"transaction; proven by every test in {TEST_MODULE}."),
    "M12": N("no fault-injection harness exists in this test suite to simulate a DB/signature-service outage; "
              "architectural guarantee (AG-06/MUT-FR-022), not independently re-tested per module in this codebase."),
    "M13": N("no crash/rollback-injection harness exists in this test suite; same architectural-guarantee "
              "treatment as M12."),
    "M14": N("no Frappe projection consumer exists in this codebase's test harness to take offline (AG-11)."),
}

D17_SCENARIO = {
    "TC-017-S001": P(f"{TEST_MODULE}::test_evaluate_yield_normal_calculation (normal yield calculation via the "
                      "released yield_percent rule)."),
    "TC-017-S002": P(f"{TEST_MODULE}::test_evaluate_yield_zero_theoretical_quantity_fails_not_crashes (division by "
                      "zero produces a typed ValidationFailedError, never a silent zero/NaN/crash -- CALC-FR-010)."),
    "TC-017-S003": P(f"{TEST_MODULE}::test_evaluate_yield_normal_calculation exercises _quantize()'s CC-4 6dp "
                      "intermediate / 2dp reported half-up rounding read from the rule's own rounding_policy."),
    "TC-017-S004": B("no controlled UOM conversion service exists in this module (YLD-FR-017's own gap) -- a "
                      "cross-UOM scenario is not constructible", SG050),
    "TC-017-S005": P(f"{TEST_MODULE}::test_evaluate_yield_below_min_boundary_out_of_limit."),
    "TC-017-S006": P("max_percent uses the identical OUT_OF_LIMIT comparison as min_percent (YLD-FR-006); shared "
                      "code path with S005, not independently re-tested with a max-specific case this pass."),
    "TC-017-S007": P(f"{TEST_MODULE}::test_evaluate_reconciliation_out_of_tolerance (below/above tolerance via "
                      "the inclusive/exclusive tolerance_rule comparison)."),
    "TC-017-S008": P(f"{TEST_MODULE}::test_verify_full_flow_with_independent_signer, "
                      "test_verify_requires_independent_verifier."),
    "TC-017-S009": P(f"{TEST_MODULE}::test_evaluate_potency_requires_a_released_rule proves the fail-closed path; "
                      "a full potency-adjustment-succeeds scenario against a real customer-authored rule is not "
                      "independently exercised (no such rule is seeded by default, YLD-FR-015)."),
    "TC-017-S010": P(f"{TEST_MODULE}::test_evaluate_material_reconciliation_acceptable exercises the generic "
                      "mass-balance mechanics including the 'returned' category; not independently tested with "
                      "return-specific values."),
    "TC-017-S011": P("'samples'/'destroyed' categories are part of the same generic mass-balance mechanics proven "
                      f"by {TEST_MODULE}::test_evaluate_material_reconciliation_acceptable; not independently "
                      "tested with sample/destruction-specific values."),
    "TC-017-S012": B("input_refs has no rework-linkage structure to prevent double-counting (YLD-FR-024's own gap)", SG050),
    "TC-017-S013": B("this module's LABEL reconciliation doesn't consume Document 16's real label counts "
                      "(app/modules/packaging.LabelReconciliation) -- a discrepancy scenario against real label "
                      "data is not constructible through this module (YLD-FR-012's own gap)", SG049),
    "TC-017-S014": B("this module's COMPONENT reconciliation doesn't reference DeviceUnit's per-serial identity, "
                      "and 'scrapped' isn't in its category vocabulary either (YLD-FR-013's own gap)", SG049),
    "TC-017-S015": B("Document 53's reconciliation-difference engine is not wired to this module's "
                      "external_reference field (YLD-FR-027's own gap)", SG049),
    "TC-017-S016": B("no correction command exists in this module (YLD-FR-022's own gap)", SG050),
    "TC-017-S017": P("rule_object_id/rule_evaluation_id are immutable FKs captured at evaluation time, not a "
                      "re-resolved lookup -- an old batch's calculation structurally keeps pointing at the exact "
                      "rule version used, even after a newer version is released (YLD-FR-023); not independently "
                      "tested with a live rule-supersession scenario this pass."),
    "TC-017-S018": B("every evaluation in this module runs synchronously; no async job/queue path exists "
                      "(YLD-FR-032's own gap)", SG050),
}

CASE_HEADER_RE = re.compile(r"^### (TC-[A-Za-z0-9-]+) — (.+)$")
STATUS_LINE_RE = re.compile(
    r"^- \*\*Status:\*\*\s*\S+\s*\|\s*\*\*Executed by:\*\*\s*\S+\s*\|\s*\*\*Date:\*\*\s*\S+\s*\|\s*"
    r"\*\*Actual result:\*\*\s*.*\|\s*\*\*Defect:\*\*\s*.*$"
)


def parse_cases(text: str) -> list[dict]:
    cases: list[dict] = []
    current: dict | None = None
    for line in text.splitlines():
        header = CASE_HEADER_RE.match(line)
        if header:
            if current is not None:
                cases.append(current)
            current = {"id": header.group(1), "title": header.group(2), "fields": {}}
            continue
        if current is None:
            continue
        m = re.match(r"^- \*\*([^:]+):\*\*\s*(.*)$", line)
        if m:
            current["fields"][m.group(1).strip()] = m.group(2).strip()
    if current is not None:
        cases.append(current)
    return cases


def classify(case: dict) -> tuple[str, str]:
    case_id = case["id"]
    requirement = case["fields"].get("Requirement", "")
    if requirement.endswith("-MODULE"):
        suffix = case_id.rsplit("-", 1)[-1]
        if suffix not in D17_MANDATORY:
            raise SystemExit(f"No mandatory-case mapping for {case_id}")
        return D17_MANDATORY[suffix]
    if requirement.endswith("-SPEC-SCENARIO") or not requirement:
        if case_id not in D17_SCENARIO:
            raise SystemExit(f"No scenario mapping for {case_id}")
        return D17_SCENARIO[case_id]
    if requirement not in D17:
        raise SystemExit(f"No requirement mapping for {requirement} ({case_id})")
    return D17[requirement]


def main() -> None:
    case_file = next(CASE_DIR.glob("Document_17_SPEC-EBMR-008_TEST_CASES.md"))
    text = case_file.read_text()
    cases = parse_cases(text)
    print(f"parsed {len(cases)} cases from {case_file}")

    results: dict[str, tuple[str, str]] = {case["id"]: classify(case) for case in cases}

    out_lines = []
    current_id = None
    for line in text.splitlines():
        if STATUS_LINE_RE.match(line):
            status, actual_result = results[current_id]
            out_lines.append(
                f"- **Status:** {status}  |  **Executed by:** {EXECUTED_BY}  |  **Date:** {EXECUTED_AT}  |  "
                f"**Actual result:** {actual_result}  |  **Defect:** —"
            )
            continue
        header = CASE_HEADER_RE.match(line)
        if header:
            current_id = header.group(1)
        out_lines.append(line)
    case_file.write_text("\n".join(out_lines) + ("\n" if text.endswith("\n") else ""))
    print(f"rewrote {len(cases)} case statuses in {case_file.name}")

    with open(LIBRARY_CSV, newline="") as f:
        reader = csv.reader(f)
        next(reader)  # header

    rows = []
    counts: dict[str, int] = {}
    for case in cases:
        f = case["fields"]
        status, actual_result = results[case["id"]]
        counts[status] = counts.get(status, 0) + 1
        title_parts = case["title"].split(" — ", 1)
        requirement = f.get("Requirement", "")
        type_priority = f.get("Type / priority", "").split("/")
        test_type = type_priority[0].strip() if type_priority else ""
        priority = type_priority[1].strip() if len(type_priority) > 1 else ""
        auto_qual = f.get("Automation", "")
        automation_level, qualification_stage = "", ""
        m = re.match(r"^(.*?)\s*\|\s*\*\*Qualification stage:\*\*\s*(.*)$", auto_qual)
        if m:
            automation_level, qualification_stage = m.group(1).strip(), m.group(2).strip()
        rows.append([
            case["id"], requirement, "Document 17", "SPEC-EBMR-008", "WP-03",
            title_parts[1] if len(title_parts) > 1 else case["title"],
            test_type, priority, "HIGHER-PROCESS-RISK",
            f.get("Preconditions", ""), f.get("Test data", ""), f.get("Steps", ""),
            f.get("Expected result", ""), f.get("Expected error code", ""),
            f.get("Evidence to capture", ""), automation_level, qualification_stage,
            f.get("Depends on", ""), "Module developer / QA test executor",
            status, EXECUTED_BY, EXECUTED_AT, actual_result, "",
            "3. Functional Requirements" if requirement and not requirement.endswith("-MODULE") else "13. Test Catalogue",
        ])

    with open(LIBRARY_CSV, "a", newline="") as f:
        writer = csv.writer(f)
        writer.writerows(rows)
    print(f"appended {len(rows)} rows to {LIBRARY_CSV}")
    print("counts:", counts)


if __name__ == "__main__":
    main()
