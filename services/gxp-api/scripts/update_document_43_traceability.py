"""Update the 30 pre-scaffolded EDGE-FR-001..030 rows in traceability/TRACEABILITY_MASTER.csv. Same
pattern as update_document_40_traceability.py. Reflects the plan-mode-approved scope split: only the
server-side slice of Document 43 (the 6 §8 APIs) was built this pass; the on-prem gateway runtime
(supervisor/connectors/plugins/local outbox/CLI) is a distinct future deployable, so every requirement
whose behavior lives entirely on that side of the boundary is NOT_STARTED here, not guessed as built.

Run with: python3 scripts/update_document_43_traceability.py
"""

import csv
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CSV_PATH = REPO_ROOT / "ebmr-edhr/traceability/TRACEABILITY_MASTER.csv"

CODE_LOCATION = "services/gxp-api/app/modules/edge"

SG118 = "SG-118"
SG119 = "SG-119"
SG120 = "SG-120"

ENTITIES = (
    "edge_gateway; edge_enrollment_token; edge_config_snapshot; edge_observation; edge_health_snapshot; "
    "edge_security_event; edge_certificate_rotation; iam.service_identity"
)
EVENTS = "GatewayEnrolled; EdgeObservationsAccepted; GatewayHealthReported; GatewaySecurityEventReported; GatewayCertificateRotated"

# requirement_id -> (build_stage, verification_state, gap_reference, signature_relevant, entities, events, error_codes)
UPDATES: dict[str, tuple[str, str, str, str, str, str, str]] = {
    "EDGE-FR-001": ("CODE_COMPLETE", "VERIFIED", "", "no", ENTITIES, EVENTS, ""),
    "EDGE-FR-002": ("CODE_COMPLETE", "VERIFIED", SG118, "yes", ENTITIES, "GatewayEnrolled", "ENROLLMENT_TOKEN_INVALID; DUPLICATE_GATEWAY; MISSING_SIGNATURE"),
    "EDGE-FR-003": ("CODE_COMPLETE", "VERIFIED", "", "no", "edge_gateway", "", ""),
    "EDGE-FR-004": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "edge_config_snapshot", "", ""),
    "EDGE-FR-005": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-006": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-007": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-008": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-009": ("CODE_COMPLETE", "VERIFIED", "", "no", "edge_observation", "EdgeObservationsAccepted", ""),
    "EDGE-FR-010": ("CODE_COMPLETE", "VERIFIED", "", "no", "edge_observation", "EdgeObservationsAccepted", ""),
    "EDGE-FR-011": ("CODE_COMPLETE", "VERIFIED", "", "no", "edge_observation", "EdgeObservationsAccepted", ""),
    "EDGE-FR-012": ("CODE_COMPLETE", "VERIFIED", "", "no", "edge_observation", "EdgeObservationsAccepted", ""),
    "EDGE-FR-013": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-014": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-015": ("CODE_COMPLETE", "VERIFIED", "", "no", "edge_observation", "EdgeObservationsAccepted", ""),
    "EDGE-FR-016": ("CODE_COMPLETE", "VERIFIED", "", "no", "edge_observation", "EdgeObservationsAccepted", "STALE_VERSION"),
    "EDGE-FR-017": ("CODE_COMPLETE", "VERIFIED", "", "no", "edge_health_snapshot; edge_gateway", "GatewayHealthReported", ""),
    "EDGE-FR-018": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-019": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-020": ("CODE_COMPLETE", "VERIFIED", "", "yes", "edge_certificate_rotation", "GatewayCertificateRotated", "CERT_ROTATION_FAILED; MISSING_SIGNATURE; INVALID_TRANSITION"),
    "EDGE-FR-021": ("NOT_STARTED", "NOT_VERIFIED", SG120, "no", "iam.service_identity", "", ""),
    "EDGE-FR-022": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-023": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-024": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-025": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-026": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "edge_observation; edge_health_snapshot", "", ""),
    "EDGE-FR-027": ("CODE_COMPLETE", "VERIFIED", "", "no", "edge_security_event; audit.audit_event", "GatewaySecurityEventReported", ""),
    "EDGE-FR-028": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-029": ("NOT_STARTED", "NOT_VERIFIED", "", "no", "", "", ""),
    "EDGE-FR-030": ("CODE_COMPLETE", "VERIFIED", "", "no", "", "", ""),
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
        build_stage, verification_state, gap_reference, signature_relevant, entities, events, error_codes = UPDATES[req]
        row["code_location"] = CODE_LOCATION
        row["build_stage"] = build_stage
        row["verification_state"] = verification_state
        row["gap_reference"] = gap_reference
        row["signature_relevant"] = signature_relevant
        if entities:
            row["entities"] = entities
        if events:
            row["events"] = events
        if error_codes:
            row["error_codes"] = error_codes
        updated += 1

    with open(CSV_PATH, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)

    print(f"updated {updated} rows in {CSV_PATH}")


if __name__ == "__main__":
    main()
