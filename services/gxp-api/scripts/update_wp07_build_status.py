"""Update the six SPEC-ERP-00x module entries in status/build-status.json. requirements_state/test_pass/
test_fail/test_blocked are recomputed by tooling/status/rollup.py from TEST_CASE_LIBRARY.csv afterwards.

Run with: python3 scripts/update_wp07_build_status.py
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
STATUS_PATH = REPO_ROOT / "ebmr-edhr/status/build-status.json"

NOTE = (
    "WP-07 built as services/gxp-api/app/modules/erp/ (ADR-0009), not a separate services/integration-"
    "gateway deployment. Provisional entity schema (10 tables under a new `erp` PostgreSQL schema) "
    "authored per ADR-0009/SG-121 since the frozen catalogue and Document 112 declare zero entities for "
    "any of the six WP-07 documents. Built and tested: the vendor-neutral ERPProvider contract, instance "
    "registry, external mapping propose/approve/conflict/checkpoint, the full Document 53 shared "
    "reliability model (command ledger, retry/backoff, circuit breaker, dead-letter, corrected-command, "
    "inbound event ledger, reconciliation run/difference/resolve), and one real httpx-based adapter per "
    "vendor (ERPNext/SAP S/4HANA/Oracle Fusion/Dynamics 365/generic) over a shared operation subset "
    "(material/supplier sync, goods receipt/consumption/return/scrap/finished-goods, production-order "
    "reference, quality-status posting). 22 new tests, all passing (tests/test_erp_flow.py), plus 0 "
    "regressions across the full platform regression suite (see the completion report for the exact "
    "final count). Not built this pass: the automated master-data pull "
    "pipeline, deep per-vendor field mapping beyond the shared operation set, SOAP/file/DB adapters, "
    "secret-manager integration, and several Document 53 observability/chaos-testing items -- see SG-126. "
    "Signature: SG-122 (Document 106 has zero rows for any SPEC-ERP-00x action; resolved to "
    "signature_required=False, resolved via real policy rows, not a code conditional). Retry/circuit-"
    "breaker thresholds are provisional defaults -- SG-123. Reconciliation never auto-resolves -- SG-124. "
    "No credentialed vendor sandbox was reachable from this environment -- SG-125 (mock-transport tests "
    "only, same SG-109 precedent)."
)

MODULES = {
    "SPEC-ERP-001": 120,
    "SPEC-ERP-002": 98,
    "SPEC-ERP-003": 76,
    "SPEC-ERP-004": 84,
    "SPEC-ERP-005": 98,
    "SPEC-ERP-006": 100,
}


def main() -> None:
    data = json.loads(STATUS_PATH.read_text())
    for module_id, test_case_count in MODULES.items():
        module = next(m for m in data["modules"] if m["module"] == module_id)
        module["code_location"] = "services/gxp-api/app/modules/erp"
        module["test_cases"] = test_case_count
        module["stage"] = "IN_DEVELOPMENT"
        module["stage_history"].append({
            "stage": "IN_DEVELOPMENT",
            "at": "2026-08-26",
            "by": "Claude Code",
            "note": NOTE,
        })
        module["owner"] = "Claude Code"
        module["started_at"] = "2026-08-26"
        module["open_defects"] = 0
        module["blockers"] = ["SG-121", "SG-122", "SG-123", "SG-124", "SG-125", "SG-126"]

    STATUS_PATH.write_text(json.dumps(data, indent=1) + "\n")
    print(f"updated {len(MODULES)} module entries")


if __name__ == "__main__":
    main()
