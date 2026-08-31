"""Update the 161 pre-scaffolded WP-07 rows (ERP-ARC-001..030, ENXT-FR-001..024, SAP-FR-001..025,
MULTI-FR-001..024, MDS-FR-001..028, INT-FR-001..030) in traceability/TRACEABILITY_MASTER.csv. Verdicts
mirror scripts/fill_wp07_test_cases.py's requirement-level classification (see that file's docstring for
the methodology note on WP-07's requirement-level, not case-level, grain).

Run with: python3 scripts/update_wp07_traceability.py
"""

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = REPO_ROOT / "ebmr-edhr/traceability/TRACEABILITY_MASTER.csv"

OLD_CODE_LOCATION = "services/integration-gateway"
NEW_CODE_LOCATION = "services/gxp-api/app/modules/erp"

SG121, SG126 = "SG-121", "SG-126"

PASS_REQS = {
    "ERP-ARC-001", "ERP-ARC-002", "ERP-ARC-003", "ERP-ARC-004", "ERP-ARC-005", "ERP-ARC-009", "ERP-ARC-010",
    "ERP-ARC-012", "ERP-ARC-013", "ERP-ARC-014", "ERP-ARC-015", "ERP-ARC-017", "ERP-ARC-018", "ERP-ARC-019",
    "ERP-ARC-021", "ERP-ARC-022", "ERP-ARC-023", "ERP-ARC-024", "ERP-ARC-025", "ERP-ARC-026", "ERP-ARC-027",
    "ERP-ARC-029", "ERP-ARC-030",
    "ENXT-FR-001", "ENXT-FR-002", "ENXT-FR-003", "ENXT-FR-004", "ENXT-FR-005", "ENXT-FR-007", "ENXT-FR-008",
    "ENXT-FR-009", "ENXT-FR-011", "ENXT-FR-012", "ENXT-FR-013", "ENXT-FR-014", "ENXT-FR-016", "ENXT-FR-017",
    "ENXT-FR-018", "ENXT-FR-019", "ENXT-FR-020", "ENXT-FR-021", "ENXT-FR-022", "ENXT-FR-023", "ENXT-FR-024",
    "SAP-FR-001", "SAP-FR-002", "SAP-FR-003", "SAP-FR-005", "SAP-FR-006", "SAP-FR-007", "SAP-FR-009",
    "SAP-FR-011", "SAP-FR-012", "SAP-FR-014", "SAP-FR-015", "SAP-FR-017", "SAP-FR-019", "SAP-FR-021",
    "SAP-FR-022", "SAP-FR-023", "SAP-FR-024", "SAP-FR-025",
    "MULTI-FR-001", "MULTI-FR-002", "MULTI-FR-003", "MULTI-FR-004", "MULTI-FR-006", "MULTI-FR-007",
    "MULTI-FR-008", "MULTI-FR-009", "MULTI-FR-010", "MULTI-FR-012", "MULTI-FR-013", "MULTI-FR-014",
    "MULTI-FR-016", "MULTI-FR-017", "MULTI-FR-018", "MULTI-FR-019", "MULTI-FR-020", "MULTI-FR-021",
    "MDS-FR-001", "MDS-FR-002", "MDS-FR-003", "MDS-FR-006", "MDS-FR-009", "MDS-FR-010", "MDS-FR-011",
    "MDS-FR-012", "MDS-FR-013", "MDS-FR-014", "MDS-FR-015", "MDS-FR-016", "MDS-FR-018", "MDS-FR-019",
    "MDS-FR-020", "MDS-FR-021", "MDS-FR-022", "MDS-FR-023", "MDS-FR-025", "MDS-FR-027",
    "INT-FR-001", "INT-FR-002", "INT-FR-003", "INT-FR-004", "INT-FR-005", "INT-FR-006", "INT-FR-007",
    "INT-FR-008", "INT-FR-009", "INT-FR-010", "INT-FR-012", "INT-FR-013", "INT-FR-014", "INT-FR-015",
    "INT-FR-017", "INT-FR-018", "INT-FR-019", "INT-FR-020", "INT-FR-022", "INT-FR-026", "INT-FR-027",
    "INT-FR-030",
}

# Requirements genuinely satisfied by omission/structural absence (never built a path that could violate
# them) -- same VERIFIED treatment WP-06 gave requirements whose own test cases were N/A.
NA_AS_VERIFIED_REQS = {"ENXT-FR-018", "ENXT-FR-020", "ENXT-FR-023", "MULTI-FR-006", "MULTI-FR-014", "MULTI-FR-016", "SAP-FR-023"}

BLOCKED_REQS = {
    "ERP-ARC-006": SG126, "ERP-ARC-007": SG126, "ERP-ARC-008": SG126, "ERP-ARC-011": SG126, "ERP-ARC-016": SG126,
    "ERP-ARC-020": SG126, "ERP-ARC-028": SG126,
    "ENXT-FR-006": SG126, "ENXT-FR-010": SG126, "ENXT-FR-015": SG126,
    "SAP-FR-004": SG126, "SAP-FR-008": SG126, "SAP-FR-010": SG126, "SAP-FR-013": SG126, "SAP-FR-016": SG126,
    "SAP-FR-018": SG126, "SAP-FR-020": SG126,
    "MULTI-FR-005": SG126, "MULTI-FR-011": SG126, "MULTI-FR-015": SG126, "MULTI-FR-022": SG126,
    "MULTI-FR-023": SG126, "MULTI-FR-024": SG126,
    "MDS-FR-004": SG126, "MDS-FR-005": SG126, "MDS-FR-007": SG126, "MDS-FR-008": SG126, "MDS-FR-017": SG126,
    "MDS-FR-024": SG126, "MDS-FR-026": SG126, "MDS-FR-028": SG126,
    "INT-FR-011": SG126, "INT-FR-016": SG126, "INT-FR-021": SG126, "INT-FR-023": SG126, "INT-FR-024": SG126,
    "INT-FR-025": SG126, "INT-FR-028": SG121, "INT-FR-029": SG126,
}


def main() -> None:
    with open(CSV_PATH, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    all_reqs = PASS_REQS | NA_AS_VERIFIED_REQS | set(BLOCKED_REQS)
    present = {row["requirement_id"] for row in rows if row["work_package"] == "WP-07"}
    missing = all_reqs - present
    if missing:
        raise SystemExit(f"Requirement ids not found in traceability master under WP-07: {sorted(missing)}")
    extra = present - all_reqs
    if extra:
        raise SystemExit(f"WP-07 requirement ids present but not classified by this script: {sorted(extra)}")

    updated = 0
    for row in rows:
        req = row["requirement_id"]
        if row["work_package"] != "WP-07":
            continue
        if row["code_location"] == OLD_CODE_LOCATION:
            row["code_location"] = NEW_CODE_LOCATION

        if req in PASS_REQS or req in NA_AS_VERIFIED_REQS:
            row["build_stage"] = "CODE_COMPLETE"
            row["verification_state"] = "VERIFIED"
            row["gap_reference"] = ""
        else:
            row["build_stage"] = "NOT_STARTED"
            row["verification_state"] = "BLOCKED"
            row["gap_reference"] = BLOCKED_REQS[req]
        updated += 1

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"updated {updated} rows in {CSV_PATH}")


if __name__ == "__main__":
    main()
