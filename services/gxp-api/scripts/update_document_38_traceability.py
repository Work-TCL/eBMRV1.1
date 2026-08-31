"""Update the 30 pre-scaffolded EQP-FR-001..030 rows in traceability/TRACEABILITY_MASTER.csv with the
real build/verification state from this pass. Rows already exist (Phase-0 scaffold) with correct
requirement_id/test_case_ids/entities/api_operations -- only code_location (stale src/ path),
build_stage, verification_state and gap_reference are updated in place; no rows are added or removed.

Run with: python3 scripts/update_document_38_traceability.py
"""

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = REPO_ROOT / "ebmr-edhr/traceability/TRACEABILITY_MASTER.csv"

OLD_CODE_LOCATION = "services/gxp-api/src/modules/equipment"
NEW_CODE_LOCATION = "services/gxp-api/app/modules/equipment"

# requirement_id -> (build_stage, verification_state, gap_reference)
# Derived programmatically from scripts/fill_document_38_test_cases.py's RESULTS against each case's
# Requirement field in the test-case book: VERIFIED iff no case for that requirement is BLOCKED (N/A cases
# don't count against it); IMPLEMENTED iff a mix of PASS and BLOCKED cases exists; BLOCKED iff every case
# for that requirement is BLOCKED. gap_reference is populated from the BLOCKED case(s)' cited SPEC_GAP, or
# added informationally (state still VERIFIED) where SG-111/SG-113 name the requirement without any of its
# own test cases being blocked (e.g. EQP-FR-002/012/015/021 -- captured-field or cross-module-wiring gaps
# that don't fail this document's own test-case book).
UPDATES: dict[str, tuple[str, str, str]] = {
    "EQP-FR-001": ("CODE_COMPLETE", "VERIFIED", ""),
    "EQP-FR-002": ("CODE_COMPLETE", "VERIFIED", "SG-113"),
    "EQP-FR-003": ("CODE_COMPLETE", "VERIFIED", ""),
    "EQP-FR-004": ("CODE_COMPLETE", "IMPLEMENTED", "SG-112"),
    "EQP-FR-005": ("CODE_COMPLETE", "VERIFIED", ""),
    "EQP-FR-006": ("CODE_COMPLETE", "VERIFIED", ""),
    "EQP-FR-007": ("CODE_COMPLETE", "VERIFIED", ""),
    "EQP-FR-008": ("CODE_COMPLETE", "IMPLEMENTED", "SG-112"),
    "EQP-FR-009": ("CODE_COMPLETE", "VERIFIED", ""),
    "EQP-FR-010": ("CODE_COMPLETE", "VERIFIED", ""),
    "EQP-FR-011": ("CODE_COMPLETE", "VERIFIED", ""),
    "EQP-FR-012": ("CODE_COMPLETE", "VERIFIED", "SG-111"),
    "EQP-FR-013": ("CODE_COMPLETE", "VERIFIED", ""),
    "EQP-FR-014": ("CODE_COMPLETE", "VERIFIED", ""),
    "EQP-FR-015": ("CODE_COMPLETE", "VERIFIED", "SG-111"),
    "EQP-FR-016": ("NOT_STARTED", "BLOCKED", "SG-112"),
    "EQP-FR-017": ("NOT_STARTED", "BLOCKED", "SG-109"),
    "EQP-FR-018": ("NOT_STARTED", "BLOCKED", "SG-109"),
    "EQP-FR-019": ("NOT_STARTED", "BLOCKED", "SG-109"),
    "EQP-FR-020": ("NOT_STARTED", "BLOCKED", "SG-109"),
    "EQP-FR-021": ("CODE_COMPLETE", "VERIFIED", "SG-113"),
    "EQP-FR-022": ("CODE_COMPLETE", "VERIFIED", ""),
    "EQP-FR-023": ("NOT_STARTED", "BLOCKED", "SG-109"),
    "EQP-FR-024": ("NOT_STARTED", "BLOCKED", "SG-109"),
    "EQP-FR-025": ("NOT_STARTED", "BLOCKED", "SG-110"),
    "EQP-FR-026": ("NOT_STARTED", "BLOCKED", "SG-112"),
    "EQP-FR-027": ("NOT_STARTED", "BLOCKED", "SG-112"),
    "EQP-FR-028": ("CODE_COMPLETE", "VERIFIED", ""),
    "EQP-FR-029": ("CODE_COMPLETE", "VERIFIED", ""),
    "EQP-FR-030": ("CODE_COMPLETE", "VERIFIED", ""),
}


def main() -> None:
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    missing = set(UPDATES) - {row["requirement_id"] for row in rows}
    if missing:
        raise SystemExit(f"Requirement ids not found in traceability master: {missing}")

    updated = 0
    for row in rows:
        req = row["requirement_id"]
        if req not in UPDATES:
            continue
        if row["code_location"] == OLD_CODE_LOCATION:
            row["code_location"] = NEW_CODE_LOCATION
        build_stage, verification_state, gap_reference = UPDATES[req]
        row["build_stage"] = build_stage
        row["verification_state"] = verification_state
        row["gap_reference"] = gap_reference
        updated += 1

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"updated {updated} rows in {CSV_PATH}")


if __name__ == "__main__":
    main()
