"""Update the 30 pre-scaffolded STR-FR-001..030 rows in traceability/TRACEABILITY_MASTER.csv. Same pattern
as update_document_41_traceability.py -- states derived from fill_document_42_test_cases.py's RESULTS.

Run with: python3 scripts/update_document_42_traceability.py
"""

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = REPO_ROOT / "ebmr-edhr/traceability/TRACEABILITY_MASTER.csv"

OLD_CODE_LOCATION = "services/gxp-api/src/modules/equipment"
NEW_CODE_LOCATION = "services/gxp-api/app/modules/equipment"

SG109 = "SG-109"
SG116 = "SG-116"

UPDATES: dict[str, tuple[str, str, str]] = {
    "STR-FR-001": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-002": ("CODE_COMPLETE", "PARTIAL", SG116),
    "STR-FR-003": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-004": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-005": ("NOT_STARTED", "BLOCKED", SG116),
    "STR-FR-006": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-007": ("CODE_COMPLETE", "PARTIAL", SG109),
    "STR-FR-008": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-009": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-010": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-011": ("NOT_STARTED", "BLOCKED", SG116),
    "STR-FR-012": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-013": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-014": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-015": ("NOT_STARTED", "BLOCKED", SG116),
    "STR-FR-016": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-017": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-018": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-019": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-020": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-021": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-022": ("NOT_STARTED", "BLOCKED", SG116),
    "STR-FR-023": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-024": ("NOT_STARTED", "BLOCKED", SG116),
    "STR-FR-025": ("NOT_STARTED", "BLOCKED", SG109),
    "STR-FR-026": ("NOT_STARTED", "BLOCKED", SG116),
    "STR-FR-027": ("CODE_COMPLETE", "VERIFIED", ""),
    "STR-FR-028": ("NOT_STARTED", "BLOCKED", SG116),
    "STR-FR-029": ("NOT_STARTED", "BLOCKED", SG116),
    "STR-FR-030": ("CODE_COMPLETE", "VERIFIED", ""),
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
