"""Update the 28 pre-scaffolded CLN-FR-001..028 rows in traceability/TRACEABILITY_MASTER.csv with the
real build/verification state from this pass. Same pattern as update_document_38_traceability.py --
states derived programmatically from fill_document_39_test_cases.py's RESULTS (see that derivation script
run during authoring); gap_reference values below match those results.

Run with: python3 scripts/update_document_39_traceability.py
"""

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = REPO_ROOT / "ebmr-edhr/traceability/TRACEABILITY_MASTER.csv"

OLD_CODE_LOCATION = "services/gxp-api/src/modules/equipment"
NEW_CODE_LOCATION = "services/gxp-api/app/modules/equipment"

SG114 = "SG-114"

# requirement_id -> (build_stage, verification_state, gap_reference)
UPDATES: dict[str, tuple[str, str, str]] = {
    "CLN-FR-001": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-002": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-003": ("NOT_STARTED", "BLOCKED", SG114),
    "CLN-FR-004": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-005": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-006": ("CODE_COMPLETE", "IMPLEMENTED", SG114),
    "CLN-FR-007": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-008": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-009": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-010": ("NOT_STARTED", "BLOCKED", SG114),
    "CLN-FR-011": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-012": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-013": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-014": ("NOT_STARTED", "BLOCKED", SG114),
    "CLN-FR-015": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-016": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-017": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-018": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-019": ("NOT_STARTED", "BLOCKED", SG114),
    "CLN-FR-020": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-021": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-022": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-023": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-024": ("NOT_STARTED", "BLOCKED", SG114),
    "CLN-FR-025": ("NOT_STARTED", "BLOCKED", SG114),
    "CLN-FR-026": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-027": ("CODE_COMPLETE", "VERIFIED", ""),
    "CLN-FR-028": ("CODE_COMPLETE", "VERIFIED", ""),
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
