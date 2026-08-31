"""Update the SPEC-EQP-003 module entry in status/build-status.json. requirements_state/test_pass/
test_fail/test_blocked are recomputed by tooling/status/rollup.py from TEST_CASE_LIBRARY.csv afterwards.

Run with: python3 scripts/update_document_40_build_status.py
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
STATUS_PATH = REPO_ROOT / "ebmr-edhr/status/build-status.json"


def main() -> None:
    data = json.loads(STATUS_PATH.read_text())
    module = next(m for m in data["modules"] if m["module"] == "SPEC-EQP-003")

    module["code_location"] = "services/gxp-api/app/modules/equipment"
    module["test_cases"] = 74
    module["stage"] = "IN_DEVELOPMENT"
    module["stage_history"].append({
        "stage": "IN_DEVELOPMENT",
        "at": "2026-08-25",
        "by": "Claude Code",
        "note": (
            "Final WP-06 document in this pass, built last per the confirmed dependency order "
            "(39 -> 41 -> 42 -> 40) so its readiness composition could call the real functions the other "
            "three documents already built, additive to app/modules/equipment/ (aseptic_models.py/"
            "aseptic_commands.py/aseptic_router.py). aseptic_operation uses a real batch_step_id FK "
            "(not the spec's unanchored recipe_stage_id) and a readiness_snapshot JSONB captured at start "
            "(not a dangling environment_snapshot_ref uuid). Built: create operation, GET .../readiness "
            "(composes real em.commands.get_area_readiness(), the new cleaning.commands."
            "get_area_line_clearance_status() helper, equipment.commands.get_eligibility() and "
            "sterilization.commands.get_item_status() -- proven end to end by "
            "test_full_operation_lifecycle_ready_area_starts_and_completes), start (Document 106 row 113, "
            "refuses to start while not ready), interventions/events (unplanned intervention or critical-"
            "severity event holds the operation and requires a deviation), complete (row 112, refuses "
            "while a deviation is unresolved), GET .../review-summary. 11 new tests, all passing "
            "(tests/test_aseptic_flow.py). Not built: personnel/gowning qualification enforcement, area-"
            "qualification status distinct from classification, a detailed assembly/setup-steps log, open-"
            "exposure/hold-time enforcement, reject-management reconciliation, media-fill qualification "
            "linkage, QC sterility/bioburden test-order linkage, RABS/isolator/glove-integrity modeling, "
            "Release Engine wiring of the review-summary composition -- see SG-117."
        ),
    })
    module["owner"] = "Claude Code"
    module["started_at"] = "2026-08-25"
    module["open_defects"] = 0
    module["blockers"] = ["SG-109", "SG-117"]

    STATUS_PATH.write_text(json.dumps(data, indent=1) + "\n")
    print("updated SPEC-EQP-003 module entry")


if __name__ == "__main__":
    main()
