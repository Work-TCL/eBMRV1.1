"""Update the SPEC-EQP-005 module entry in status/build-status.json. requirements_state/test_pass/
test_fail/test_blocked are recomputed by tooling/status/rollup.py from TEST_CASE_LIBRARY.csv afterwards.

Run with: python3 scripts/update_document_42_build_status.py
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
STATUS_PATH = REPO_ROOT / "ebmr-edhr/status/build-status.json"


def main() -> None:
    data = json.loads(STATUS_PATH.read_text())
    module = next(m for m in data["modules"] if m["module"] == "SPEC-EQP-005")

    module["code_location"] = "services/gxp-api/app/modules/equipment"
    module["test_cases"] = 93
    module["stage"] = "IN_DEVELOPMENT"
    module["stage_history"].append({
        "stage": "IN_DEVELOPMENT",
        "at": "2026-08-25",
        "by": "Claude Code",
        "note": (
            "Fourth WP-06 document (built ahead of Document 40/Aseptic per dependency-order build sequence "
            "confirmed with the user), additive to app/modules/equipment/ (sterilization_models.py/"
            "sterilization_commands.py/sterilization_router.py). process_cycle covers both sterilization "
            "and CIP/SIP cycles (distinguished by process_type). Built: create cycle with load items, start "
            "(Document 106 row 118), record cycle data with critical_alarm auto-hold (STR-FR-009: no "
            "pass/fail field exists on cycle data -- the independent reviewer, not the data-recording "
            "operator, decides accept/reject), independent review (row 117) that issues sterile status + "
            "expiry onto every load item on accept, filter install/integrity-test/complete (row 116). 9 new "
            "tests, all passing (tests/test_sterilization_flow.py), including a direct DB + GET-endpoint "
            "assertion proving STR-FR-012 sterile-status issuance. Not built: sterilizer equipment-"
            "eligibility cross-check, CIP-specific verification, filter reuse-count tracking, hold-time-"
            "limit cross-check, reprocessing authorization, genealogy linkage, release-module cross-check "
            "-- see SG-116 (and SG-109 for the external-sterilizer/Edge-dependent items)."
        ),
    })
    module["owner"] = "Claude Code"
    module["started_at"] = "2026-08-25"
    module["open_defects"] = 0
    module["blockers"] = ["SG-109", "SG-116"]

    STATUS_PATH.write_text(json.dumps(data, indent=1) + "\n")
    print("updated SPEC-EQP-005 module entry")


if __name__ == "__main__":
    main()
