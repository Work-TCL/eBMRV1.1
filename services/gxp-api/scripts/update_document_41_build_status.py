"""Update the SPEC-EQP-004 module entry in status/build-status.json. requirements_state/test_pass/
test_fail/test_blocked are recomputed by tooling/status/rollup.py from TEST_CASE_LIBRARY.csv afterwards.

Run with: python3 scripts/update_document_41_build_status.py
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
STATUS_PATH = REPO_ROOT / "ebmr-edhr/status/build-status.json"


def main() -> None:
    data = json.loads(STATUS_PATH.read_text())
    module = next(m for m in data["modules"] if m["module"] == "SPEC-EQP-004")

    module["code_location"] = "services/gxp-api/app/modules/equipment"
    module["test_cases"] = 70
    module["stage"] = "IN_DEVELOPMENT"
    module["stage_history"].append({
        "stage": "IN_DEVELOPMENT",
        "at": "2026-08-25",
        "by": "Claude Code",
        "note": (
            "Third WP-06 document (built ahead of Document 40/Aseptic per dependency-order build sequence "
            "confirmed with the user), additive to app/modules/equipment/ (em_models.py/em_commands.py/"
            "em_router.py). em_location references Document 39's equipment_area. Built: create EM program "
            "(unsigned), create/collect sampling task, record result (Document 106 row 114) with automatic "
            "EmExcursion creation on action_excursion, independent review (row 115), excursion impact "
            "assessment, and get_area_readiness() -- the real cross-module function Document 40's aseptic "
            "readiness check will call. 8 new tests, all passing (tests/test_em_flow.py). Not built: "
            "instrument-eligibility cross-check, structured media/incubation/organism-ID fields, trend "
            "baseline/statistical detection, data-gap detection, continuous sensors, facility alarms -- "
            "see SG-115 (and SG-109 for the Edge-dependent items)."
        ),
    })
    module["owner"] = "Claude Code"
    module["started_at"] = "2026-08-25"
    module["open_defects"] = 0
    module["blockers"] = ["SG-109", "SG-115"]

    STATUS_PATH.write_text(json.dumps(data, indent=1) + "\n")
    print("updated SPEC-EQP-004 module entry")


if __name__ == "__main__":
    main()
