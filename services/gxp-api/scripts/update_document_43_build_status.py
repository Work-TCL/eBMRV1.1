"""Update the SPEC-EDGE-001 module entry in status/build-status.json. requirements_state per-requirement
values are set directly (matching traceability/TRACEABILITY_MASTER.csv); test_pass/test_fail/test_blocked
are recomputed by tooling/status/rollup.py from TEST_CASE_LIBRARY.csv afterwards.

Run with: python3 scripts/update_document_43_build_status.py
"""

import json
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
STATUS_PATH = REPO_ROOT / "ebmr-edhr/status/build-status.json"

NOT_STARTED_REQS = {
    "EDGE-FR-004", "EDGE-FR-005", "EDGE-FR-006", "EDGE-FR-007", "EDGE-FR-008", "EDGE-FR-013",
    "EDGE-FR-014", "EDGE-FR-018", "EDGE-FR-019", "EDGE-FR-021", "EDGE-FR-022", "EDGE-FR-023",
    "EDGE-FR-024", "EDGE-FR-025", "EDGE-FR-026", "EDGE-FR-028", "EDGE-FR-029",
}


def main() -> None:
    data = json.loads(STATUS_PATH.read_text())
    module = next(m for m in data["modules"] if m["module"] == "SPEC-EDGE-001")

    module["code_location"] = "services/gxp-api/app/modules/edge"
    for req in module["requirements_state"]:
        module["requirements_state"][req] = "NOT_STARTED" if req in NOT_STARTED_REQS else "CODE_COMPLETE"
    module["entities"] = 8  # 7 edge.* tables + iam.service_identities (SG-120)
    module["events"] = 5
    module["test_cases"] = 115  # corrected from the stale placeholder (87) -- real book has 115 cases
    module["stage"] = "IN_DEVELOPMENT"
    module["stage_history"].append({
        "stage": "IN_DEVELOPMENT",
        "at": "2026-08-26",
        "by": "Claude Code",
        "note": (
            "First document of WP-06's Edge/OT half (Documents 43-47); no edge module existed before "
            "this pass. Plan-mode sign-off scoped this pass to the server-side slice only (spec §8's 6 "
            "APIs) -- the on-prem gateway runtime (§12: supervisor/connectors/plugins/local SQLite "
            "outbox/CLI) is a distinct future deployable, not attempted. Built: app/modules/edge/ "
            "(models.py/commands.py/router.py) -- enroll_gateway (SG-118 interim signature baseline, "
            "Admin, independent=False, reason required), GET configuration (read-only), "
            "accept_observation_batch (per-envelope idempotency on event_id/gateway_sequence, "
            "SG-119 signature_required=false), report_health, report_security_event (CRITICAL -> "
            "SECURITY_HOLD authoritatively), rotate_gateway_certificate (Document 106 row 119, QA "
            "Releaser, independent of the enrolling actor -- real SoD check against "
            "EdgeGateway.enrolled_by_user_id). Added SG-120: a minimal iam.service_identity primitive "
            "(opaque sid_<id>.<secret> bearer credential, bcrypt-hashed, issued once at enrollment) plus "
            "a new get_service_identity auth dependency, since no non-human identity mechanism existed "
            "anywhere in this codebase before this pass -- scoped to edge gateways only, full Document 62 "
            "deferred. Migration 0042_edge_gateway_schema (new edge schema, 7 tables, plus "
            "iam.service_identities). Contract contracts/openapi/spec-edge-001.yaml written before the "
            "router per CTR-FR-001. 14 new tests, all passing (tests/test_edge_flow.py). Not built: the "
            "on-prem runtime itself and everything the 6 server APIs don't cover -- config authoring/"
            "activation (only read-serve exists), connector supervision/plugin sandboxing, unit "
            "conversion, local buffering/disk-pressure/continuity, remote signed update, command channel, "
            "network segmentation/deployment concerns, and dedicated observability/clock-health-evaluation "
            "logic (fields are captured verbatim; no thresholding). See SG-118/SG-119/SG-120."
        ),
    })
    module["owner"] = "Claude Code"
    module["started_at"] = "2026-08-26"
    module["open_defects"] = 0
    module["blockers"] = ["SG-118", "SG-119", "SG-120"]

    STATUS_PATH.write_text(json.dumps(data, indent=1) + "\n")
    print("updated SPEC-EDGE-001 module entry")


if __name__ == "__main__":
    main()
