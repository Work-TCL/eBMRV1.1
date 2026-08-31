"""Update the SPEC-EQP-002 module entry in status/build-status.json with this pass's real build/test
results. requirements_state/test_pass/test_fail/test_blocked are recomputed by tooling/status/rollup.py
from TEST_CASE_LIBRARY.csv afterwards -- this script only sets the fields rollup.py doesn't touch.

Run with: python3 scripts/update_document_39_build_status.py
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
STATUS_PATH = REPO_ROOT / "ebmr-edhr/status/build-status.json"


def main() -> None:
    data = json.loads(STATUS_PATH.read_text())
    module = next(m for m in data["modules"] if m["module"] == "SPEC-EQP-002")

    module["code_location"] = "services/gxp-api/app/modules/equipment"
    module["entities"] = 4  # cleaning_procedure_version, cleaning_execution, line_clearance + equipment_area
    module["test_cases"] = 73
    module["stage"] = "IN_DEVELOPMENT"
    module["stage_history"].append({
        "stage": "IN_DEVELOPMENT",
        "at": "2026-08-25",
        "by": "Claude Code",
        "note": (
            "Second WP-06 document, additive to app/modules/equipment/ alongside Document 38 (cleaning_"
            "models.py/cleaning_commands.py/cleaning_router.py). Also introduces `equipment_area` -- a new "
            "shared master (no area/room entity existed anywhere in this codebase before this pass), "
            "consumed by Documents 40/41 later in this same pass. Built: create/complete/verify cleaning "
            "execution (Document 106 rows 109/110, independent-verifier enforced), create/complete line "
            "clearance (row 111), dirty/clean-hold-time computation on read, cleanliness_status mirrored "
            "onto Document 38's equipment_asset (closing part of SG-113). 9 new tests, all passing "
            "(tests/test_cleaning_flow.py). Not built: scheduler-driven due-date triggers, duplicate-"
            "active-execution guard, swab/rinse QC sampling link, post-clean protection-state tracking, "
            "equipment-status cross-check on line clearance, campaign boundaries, CIP/SIP link to "
            "Document 42 -- see SG-114."
        ),
    })
    module["owner"] = "Claude Code"
    module["started_at"] = "2026-08-25"
    module["open_defects"] = 0
    module["blockers"] = ["SG-114"]

    STATUS_PATH.write_text(json.dumps(data, indent=1) + "\n")
    print("updated SPEC-EQP-002 module entry")


if __name__ == "__main__":
    main()
