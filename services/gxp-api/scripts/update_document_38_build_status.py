"""Update the SPEC-EQP-001 module entry in status/build-status.json with this pass's real build/test
results. Same per-requirement derivation as scripts/update_document_38_traceability.py.

Run with: python3 scripts/update_document_38_build_status.py
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
STATUS_PATH = REPO_ROOT / "ebmr-edhr/status/build-status.json"

# requirement_id -> module-level functionality state (status/STATUS_MODEL.md's own vocabulary)
REQUIREMENTS_STATE = {
    "EQP-FR-001": "VERIFIED",
    "EQP-FR-002": "VERIFIED",
    "EQP-FR-003": "VERIFIED",
    "EQP-FR-004": "IMPLEMENTED",
    "EQP-FR-005": "VERIFIED",
    "EQP-FR-006": "VERIFIED",
    "EQP-FR-007": "VERIFIED",
    "EQP-FR-008": "IMPLEMENTED",
    "EQP-FR-009": "VERIFIED",
    "EQP-FR-010": "VERIFIED",
    "EQP-FR-011": "VERIFIED",
    "EQP-FR-012": "VERIFIED",
    "EQP-FR-013": "VERIFIED",
    "EQP-FR-014": "VERIFIED",
    "EQP-FR-015": "VERIFIED",
    "EQP-FR-016": "BLOCKED",
    "EQP-FR-017": "BLOCKED",
    "EQP-FR-018": "BLOCKED",
    "EQP-FR-019": "BLOCKED",
    "EQP-FR-020": "BLOCKED",
    "EQP-FR-021": "VERIFIED",
    "EQP-FR-022": "VERIFIED",
    "EQP-FR-023": "BLOCKED",
    "EQP-FR-024": "BLOCKED",
    "EQP-FR-025": "BLOCKED",
    "EQP-FR-026": "BLOCKED",
    "EQP-FR-027": "BLOCKED",
    "EQP-FR-028": "VERIFIED",
    "EQP-FR-029": "VERIFIED",
    "EQP-FR-030": "VERIFIED",
}

TEST_CASES = 83
TEST_PASS = 36
TEST_FAIL = 0
# This repo's convention (verified against every other populated module row: test_pass + test_fail +
# test_blocked == test_cases exactly) folds N/A-justified cases into test_blocked alongside real
# infrastructure-blocked ones -- there is no separate N/A bucket in this schema.
TEST_BLOCKED = 47  # 32 BLOCKED + 15 N/A

BLOCKERS = ["SG-109", "SG-110", "SG-111", "SG-112", "SG-113"]


def main() -> None:
    data = json.loads(STATUS_PATH.read_text())
    module = next(m for m in data["modules"] if m["module"] == "SPEC-EQP-001")

    module["code_location"] = "services/gxp-api/app/modules/equipment"
    module["requirements_state"] = REQUIREMENTS_STATE
    module["test_cases"] = TEST_CASES
    module["stage"] = "IN_DEVELOPMENT"
    module["stage_history"].append({
        "stage": "IN_DEVELOPMENT",
        "at": "2026-08-25",
        "by": "Claude Code",
        "note": (
            "First WP-06 document: a real, net-new Equipment/Calibration/Qualification/Maintenance module "
            "(app/modules/equipment/) -- create asset, record qualification/calibration/maintenance "
            "(plan+execution combined per operation, matching the spec's own 9-op API list), the one "
            "Document 106-signed action (hold, row 108), return-to-service as the single QUALIFIED_"
            "AVAILABLE entry point (EQP-FR-030 no-status-bypass), eligibility/history/dashboard read "
            "queries, and EQP-FR-022's change-control link via the owning qms.change_commands.create_"
            "change (AG-05/AG-06, no qms table written directly). 17 new tests, all passing "
            "(tests/test_equipment_flow.py), plus the full pre-existing 472-test suite passes unmodified. "
            "4 new IAM roles added (Equipment Administrator, Engineering Manager, Calibration Technician, "
            "Maintenance Technician) per explicit user sign-off during planning, since none of the 6 "
            "existing roles map to Document 38's actor list. Edge/device/CMMS/alarm/firmware-tracking "
            "(SG-109), the Document 39 cleaning dependency (SG-110), the batch_execution eligibility-gate "
            "wire (SG-111, explicit scope decision confirmed with the user), reservation/location-transfer/"
            "retirement -- no declared endpoint for any of the three (SG-112), and equipment-class/"
            "calibration-standard/spare-parts master entities (SG-113) are not built this pass."
        ),
    })
    module["owner"] = "Claude Code"
    module["started_at"] = "2026-08-25"
    module["test_pass"] = TEST_PASS
    module["test_fail"] = TEST_FAIL
    module["test_blocked"] = TEST_BLOCKED
    module["open_defects"] = 0
    module["blockers"] = BLOCKERS

    STATUS_PATH.write_text(json.dumps(data, indent=1) + "\n")
    print("updated SPEC-EQP-001 module entry")


if __name__ == "__main__":
    main()
