"""Update the 26 pre-scaffolded EM-FR-001..026 rows in traceability/TRACEABILITY_MASTER.csv. Same pattern
as update_document_38_traceability.py -- states derived programmatically from
fill_document_41_test_cases.py's RESULTS.

Run with: python3 scripts/update_document_41_traceability.py
"""

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = REPO_ROOT / "ebmr-edhr/traceability/TRACEABILITY_MASTER.csv"

OLD_CODE_LOCATION = "services/gxp-api/src/modules/equipment"
NEW_CODE_LOCATION = "services/gxp-api/app/modules/equipment"

SG109 = "SG-109"
SG115 = "SG-115"

UPDATES: dict[str, tuple[str, str, str]] = {
    "EM-FR-001": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-002": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-003": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-004": ("NOT_STARTED", "BLOCKED", SG115),
    "EM-FR-005": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-006": ("NOT_STARTED", "BLOCKED", SG115),
    "EM-FR-007": ("CODE_COMPLETE", "VERIFIED", SG115),
    "EM-FR-008": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-009": ("NOT_STARTED", "BLOCKED", SG115),
    "EM-FR-010": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-011": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-012": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-013": ("NOT_STARTED", "BLOCKED", SG115),
    "EM-FR-014": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-015": ("NOT_STARTED", "BLOCKED", SG109),
    "EM-FR-016": ("NOT_STARTED", "BLOCKED", SG115),
    "EM-FR-017": ("CODE_COMPLETE", "VERIFIED", SG115),
    "EM-FR-018": ("NOT_STARTED", "BLOCKED", SG115),
    "EM-FR-019": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-020": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-021": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-022": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-023": ("NOT_STARTED", "BLOCKED", SG109),
    "EM-FR-024": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-025": ("CODE_COMPLETE", "VERIFIED", ""),
    "EM-FR-026": ("CODE_COMPLETE", "VERIFIED", ""),
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
