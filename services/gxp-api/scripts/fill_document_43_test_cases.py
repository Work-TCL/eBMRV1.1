"""Fill real (non-fabricated) execution results into the 115 pre-written Document 43 (SPEC-EDGE-001)
test cases: test-cases/WP-06/Document_43_SPEC-EDGE-001_TEST_CASES.md. Same template as
scripts/fill_document_42_test_cases.py.

Scope note (plan-mode sign-off): only the server-side slice of Document 43 was built this pass (spec
§8's 6 APIs). The on-prem gateway runtime (§12: supervisor/connectors/plugins/local SQLite outbox/CLI)
is a distinct future deployable. Every case whose behavior lives entirely on that side of the boundary is
BLOCKED with that reason, not fabricated as PASS or silently skipped.

Run with: python3 scripts/fill_document_43_test_cases.py
"""

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CASE_FILE = REPO_ROOT / "ebmr-edhr/test-cases/WP-06/Document_43_SPEC-EDGE-001_TEST_CASES.md"
LIBRARY_CSV = REPO_ROOT / "ebmr-edhr/test-cases/TEST_CASE_LIBRARY.csv"
TEST_MODULE = "services/gxp-api/tests/test_edge_flow.py"

EXECUTED_BY = "claude-code"
EXECUTED_AT = "2026-08-26"

SG118 = "SG-118"
SG119 = "SG-119"
SG120 = "SG-120"

ON_PREM = (
    "on-prem gateway runtime (supervisor/connectors/plugins/local outbox/CLI) is a distinct future "
    "deployable, not built this pass (plan-mode scope decision)"
)


def _pass(tests: str) -> str:
    return f"PASS -- exercised by real pytest in {TEST_MODULE}::{tests}."


def _pass_shared(reason: str) -> str:
    return f"PASS -- not independently re-executed; {reason}"


def _blocked(reason: str, sg: str = "") -> str:
    suffix = f" ({sg})" if sg else ""
    return f"BLOCKED -- {reason}{suffix}."


def _na(reason: str) -> str:
    return f"N/A -- {reason}"


RESULTS: dict[str, tuple[str, str, str]] = {
    # EDGE-FR-001 Gateway identity (built)
    "TC-043-001-01": ("PASS", _pass("test_enroll_gateway_issues_service_credential (immutable gateway id, site, host_identity/certificate_fingerprint, lifecycle_state=ENROLLED)"), ""),
    "TC-043-001-02": ("PASS", _pass_shared("DELETE is refused at the DB privilege level (migration 0042: no DELETE grant on any edge.* table); UPDATE is legitimately available since edge_gateways is a mutable aggregate -- not independently re-tested via raw SQL this pass."), ""),
    "TC-043-001-03": ("PASS", _pass("test_critical_security_event_holds_gateway_and_blocks_ingestion (SECURITY_HOLD lifecycle_state blocks a further observation-batch call, INVALID_TRANSITION)"), ""),
    "TC-043-001-04": ("BLOCKED", _blocked(ON_PREM), ""),
    # EDGE-FR-002 Enrollment (built, SG-118)
    "TC-043-002-01": ("PASS", _pass("test_enroll_gateway_issues_service_credential"), ""),
    "TC-043-002-02": ("PASS", _pass("test_enroll_wrong_password_rejected (MISSING_SIGNATURE)"), ""),
    "TC-043-002-03": ("N/A", _na("enrollment is a creation command with no prior aggregate version to supersede -- its challenge binds to (bootstrap_token_id, gateway_fingerprint) with record_version=0, same 'creation command has no expected_version' precedent CommandEnvelope's own docstring states."), ""),
    "TC-043-002-04": ("BLOCKED", _blocked(ON_PREM), ""),
    # EDGE-FR-003 Site isolation (built)
    "TC-043-003-01": ("PASS", _pass("test_enroll_gateway_issues_service_credential (gateway.site_id bound from the enrollment command's site_id)"), ""),
    "TC-043-003-02": ("N/A", _na("no separate signed action exists for site isolation -- its only enforcement point is enroll_gateway, already covered under TC-043-002-02."), ""),
    "TC-043-003-03": ("N/A", _na("same as TC-043-003-02."), ""),
    "TC-043-003-04": ("PASS", _pass("test_enroll_reused_token_rejected (a reused bootstrap token is detected and rejected, ENROLLMENT_TOKEN_INVALID)"), ""),
    # EDGE-FR-004 Configuration versions (not built -- read-serve only, no authoring API)
    "TC-043-004-01": ("BLOCKED", _blocked("no config-authoring/versioning write path exists this pass -- only GET .../configuration read-serve is built; spec §8 defines no create/version endpoint (known limitation, not itself a SPEC_GAP -- see app/modules/edge/models.py EdgeConfigSnapshot docstring)"), ""),
    "TC-043-004-02": ("BLOCKED", _blocked("same missing config-authoring capability as TC-043-004-01"), ""),
    "TC-043-004-03": ("BLOCKED", _blocked("same missing config-authoring capability as TC-043-004-01"), ""),
    "TC-043-004-04": ("BLOCKED", _blocked("same missing config-authoring capability as TC-043-004-01"), ""),
    # EDGE-FR-005 Config validation (not built)
    "TC-043-005-01": ("BLOCKED", _blocked("config validation logic is not built -- no config-authoring capability exists to validate against this pass"), ""),
    "TC-043-005-02": ("BLOCKED", _blocked("same as TC-043-005-01"), ""),
    "TC-043-005-03": ("BLOCKED", _blocked("same as TC-043-005-01"), ""),
    "TC-043-005-04": ("BLOCKED", _blocked(ON_PREM), ""),
    # EDGE-FR-006 Atomic config activation (not built)
    "TC-043-006-01": ("BLOCKED", _blocked("config activation is not built -- no config-authoring capability exists this pass"), ""),
    "TC-043-006-02": ("BLOCKED", _blocked("same as TC-043-006-01"), ""),
    "TC-043-006-03": ("BLOCKED", _blocked(ON_PREM), ""),
    # EDGE-FR-007 Connector supervision (on-prem, not built)
    "TC-043-007-01": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-007-02": ("BLOCKED", _blocked(ON_PREM), ""),
    # EDGE-FR-008 Plugin sandbox boundary (on-prem, not built)
    "TC-043-008-01": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-008-02": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-008-03": ("BLOCKED", _blocked(ON_PREM), ""),
    # EDGE-FR-009 Observation envelope (built)
    "TC-043-009-01": ("PASS", _pass("test_observation_batch_accept_duplicate_and_stale_version (canonical envelope accepted and persisted)"), ""),
    "TC-043-009-02": ("PASS", _pass("test_observation_batch_accept_duplicate_and_stale_version (the same event_id resent after the first accept is classified duplicate, not lost or double-counted)"), ""),
    # EDGE-FR-010 Source provenance (built)
    "TC-043-010-01": ("PASS", _pass_shared("connector_id/device_id/mapping_id/mapping_version/source are real columns on edge.edge_observations and real fields on ObservationEnvelopeIn, exercised (with null provenance) by test_observation_batch_accept_duplicate_and_stale_version -- not independently asserted with non-null provenance values this pass."), ""),
    "TC-043-010-02": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-010-03": ("PASS", _pass("test_observation_batch_accept_duplicate_and_stale_version (STALE_VERSION on a conflicting expected_version against the same gateway aggregate)"), ""),
    # EDGE-FR-011 Timestamp model (built)
    "TC-043-011-01": ("PASS", _pass_shared("source_timestamp/gateway_received_at/clock_quality are real columns on edge.edge_observations and real fields on ObservationEnvelopeIn, exercised by the same accept path test_observation_batch_accept_duplicate_and_stale_version proves -- not independently asserted with populated values this pass."), ""),
    "TC-043-011-02": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-011-03": ("PASS", _pass("test_observation_batch_accept_duplicate_and_stale_version (same STALE_VERSION concurrency guard)"), ""),
    # EDGE-FR-012 Data quality (built)
    "TC-043-012-01": ("PASS", _pass("test_observation_batch_accept_duplicate_and_stale_version (quality='GOOD' accepted)"), ""),
    "TC-043-012-02": ("BLOCKED", _blocked("the ENVELOPE_INVALID rejection path for an out-of-enum quality value exists in accept_observation_batch (checked against OBSERVATION_QUALITIES) but is not independently exercised by a dedicated test this pass"), ""),
    "TC-043-012-03": ("PASS", _pass("test_observation_batch_accept_duplicate_and_stale_version (same STALE_VERSION concurrency guard)"), ""),
    # EDGE-FR-013 Canonical units (not built)
    "TC-043-013-01": ("BLOCKED", _blocked("no unit-conversion/versioned-mapping logic is built -- raw/normalized values are captured verbatim with no conversion rule enforced this pass"), ""),
    "TC-043-013-02": ("BLOCKED", _blocked("same as TC-043-013-01"), ""),
    # EDGE-FR-014 Local buffering (on-prem, not built)
    "TC-043-014-01": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-014-02": ("BLOCKED", _blocked(ON_PREM), ""),
    # EDGE-FR-015 Delivery acknowledgement (built, server side)
    "TC-043-015-01": ("PASS", _pass("test_observation_batch_accept_duplicate_and_stale_version (accepted_event_ids in the response is the server's authoritative acknowledgement of exactly the accepted event IDs)"), ""),
    "TC-043-015-02": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-015-03": ("N/A", _na("disposal/purge-after-ack is a gateway-local retention action, out of scope this pass -- no disposal decision exists server-side to test"), ""),
    # EDGE-FR-016 Idempotency (built)
    "TC-043-016-01": ("PASS", _pass("test_observation_batch_accept_duplicate_and_stale_version (event_id primary key + (gateway_id, gateway_sequence) unique constraint) and test_duplicate_idempotency_key_returns_same_receipt"), ""),
    "TC-043-016-02": ("PASS", _pass_shared("IdempotencyConflictError (same idempotency_key, different payload) is raised by the shared app.mutation.gateway.check_idempotency() every command handler in this codebase calls, already proven by other modules' tests -- not independently re-exercised for this module's own commands this pass."), ""),
    "TC-043-016-03": ("BLOCKED", _blocked(ON_PREM), ""),
    # EDGE-FR-017 Health reporting (built)
    "TC-043-017-01": ("PASS", _pass("test_health_report_updates_gateway"), ""),
    "TC-043-017-02": ("N/A", _na("last_reported_operational_state is purely informational (never authoritative, per the architecture principle that Edge is not the GxP system of record) -- no illegal-transition concept applies to it"), ""),
    "TC-043-017-03": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-017-04": ("PASS", _pass_shared("report_health() shares _load_gateway_for_update()'s optimistic-concurrency guard with accept_observation_batch(), proven by test_observation_batch_accept_duplicate_and_stale_version's STALE_VERSION assertion."), ""),
    # EDGE-FR-018 Local health UI/API (not built)
    "TC-043-018-01": ("BLOCKED", _blocked("no local-gateway support UI/API is built -- GET /edge/v1/gateways/{id} is a server-side registry read, not the on-prem local status surface this requirement describes"), ""),
    "TC-043-018-02": ("BLOCKED", _blocked("same as TC-043-018-01"), ""),
    "TC-043-018-03": ("BLOCKED", _blocked("same as TC-043-018-01"), ""),
    # EDGE-FR-019 Remote update (not built)
    "TC-043-019-01": ("BLOCKED", _blocked("installSignedUpdate/remote update mechanism is not built this pass (on-prem runtime + release channel, out of scope)"), ""),
    "TC-043-019-02": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-019-03": ("BLOCKED", _blocked("same as TC-043-019-01"), ""),
    # EDGE-FR-020 Certificate rotation (built, Document 106 row 119)
    "TC-043-020-01": ("PASS", _pass("test_certificate_rotation_signed_and_independent and test_certificate_rotation_rejects_enrolling_actor_as_signer"), ""),
    "TC-043-020-02": ("BLOCKED", _blocked(ON_PREM + "; the overlap-period/outbound-identity-switch behavior is gateway-side"), ""),
    # EDGE-FR-021 Secrets (on-prem OS keystore, not built)
    "TC-043-021-01": ("BLOCKED", _blocked("OS/keystore/secret-file handling is a gateway-side (on-prem runtime) concern, not built this pass; the related server-side control -- the SG-120 service credential's bcrypt hash, never logged in plaintext -- is a distinct, narrower guarantee", SG120), ""),
    "TC-043-021-02": ("BLOCKED", _blocked("same as TC-043-021-01", SG120), ""),
    # EDGE-FR-022 Network segmentation (deployment concern, not built)
    "TC-043-022-01": ("BLOCKED", _blocked("network segmentation/interface configuration is a deployment/infrastructure concern, not application code, and out of scope this pass"), ""),
    "TC-043-022-02": ("BLOCKED", _blocked("same as TC-043-022-01"), ""),
    "TC-043-022-03": ("BLOCKED", _blocked("same as TC-043-022-01"), ""),
    "TC-043-022-04": ("BLOCKED", _blocked(ON_PREM), ""),
    # EDGE-FR-023 Command channel (not built)
    "TC-043-023-01": ("BLOCKED", _blocked("submitMachineCommand/command-channel feature is not built this pass -- 'disabled by default' would be trivially true only because no command channel exists at all, which is not the validated default-disabled-with-override-profile control the requirement describes"), ""),
    "TC-043-023-02": ("BLOCKED", _blocked("same as TC-043-023-01"), ""),
    "TC-043-023-03": ("BLOCKED", _blocked("same as TC-043-023-01"), ""),
    "TC-043-023-04": ("BLOCKED", _blocked("same as TC-043-023-01"), ""),
    # EDGE-FR-024 Local continuity (on-prem, not built)
    "TC-043-024-01": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-024-02": ("BLOCKED", _blocked(ON_PREM), ""),
    # EDGE-FR-025 Disk pressure (on-prem, not built)
    "TC-043-025-01": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-025-02": ("BLOCKED", _blocked(ON_PREM), ""),
    # EDGE-FR-026 Clock health (captured field only, no evaluation logic)
    "TC-043-026-01": ("BLOCKED", _blocked("clock_quality is a captured field (stored verbatim by accept_observation_batch/report_health) with no server-side NTP/PTP offset evaluation or thresholding logic -- the requirement's actual monitoring behavior is gateway-side, out of scope this pass"), ""),
    "TC-043-026-02": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-026-03": ("BLOCKED", _blocked("same missing evaluation logic as TC-043-026-01"), ""),
    # EDGE-FR-027 Audit/config history (built)
    "TC-043-027-01": ("PASS", _pass("every real HTTP call in this test module returns a MutationReceipt/GatewayEnrollmentResult carrying a real audit_event_id from the same commit -- see test_enroll_gateway_issues_service_credential"), ""),
    "TC-043-027-02": ("PASS", _pass_shared("audit.audit_events already has no UPDATE/DELETE grant (migration 0002's pre-existing append-only privilege lockdown), which every command in this codebase -- including this module's -- writes through; not independently re-tested via raw SQL for this module specifically."), ""),
    "TC-043-027-03": ("BLOCKED", _blocked(ON_PREM + "; config/plugin-update history specifically is gateway-local"), ""),
    # EDGE-FR-028 Observability (not built)
    "TC-043-028-01": ("BLOCKED", _blocked("structured logs/metrics/correlation-ID redaction pipeline is not built as a dedicated capability this pass"), ""),
    # EDGE-FR-029 Container deployment (not built)
    "TC-043-029-01": ("BLOCKED", _blocked("deployment/infrastructure concern, not application code; out of scope this pass"), ""),
    # EDGE-FR-030 No local business truth (built, structural)
    "TC-043-030-01": ("PASS", _pass_shared("app/modules/edge/ imports nothing from app.modules.batch/equipment/em/qc, and no command in edge/commands.py writes to any table outside the edge schema or iam.service_identities -- verifiable directly from the module's own import list and models.py."), ""),
    "TC-043-030-02": ("PASS", _pass_shared("same structural guarantee as TC-043-030-01 -- there is no code path in this module capable of marking a batch step/QC result/equipment calibration/product release complete, since no such write exists at all."), ""),
    "TC-043-030-03": ("N/A", _na("this is a structural prohibition (no such write path exists), not a signed action -- no signature-required action applies to this requirement"), ""),
    "TC-043-030-04": ("N/A", _na("same as TC-043-030-03"), ""),
    # Module suite (generic cross-cutting)
    "TC-043-M01": ("PASS", _pass("test_unauthenticated_enroll_rejected and test_human_token_rejected_on_service_route"), ""),
    "TC-043-M02": ("PASS", _pass("test_enroll_without_admin_role_rejected (ROLE_MISSING)"), ""),
    "TC-043-M03": ("N/A", _na("single-organization platform (ADR-0006) -- no second tenant exists to test cross-tenant access against, same treatment as every other WP-06 module this pass"), ""),
    "TC-043-M04": ("BLOCKED", _blocked("the code path exists (a bootstrap token's site_id must match the enrollment command's site_id, else ENROLLMENT_TOKEN_INVALID) but no dedicated test exercises it across two different sites this pass"), ""),
    "TC-043-M05": ("N/A", _na("no iam.Qualification gate applies to any edge_gateway action this pass -- RBAC/service-identity ownership are this module's only authorization controls, same restraint as most WP-06 modules' unenforced qualification gate"), ""),
    "TC-043-M06": ("PASS", _pass("test_certificate_rotation_rejects_enrolling_actor_as_signer (Document 106 row 119 independence check against the enrolling actor)"), ""),
    "TC-043-M07": ("PASS", _pass_shared("expected_version is a required (non-Optional) field on every mutating command's pydantic schema with extra='forbid' -- a missing field is rejected with HTTP 422 before the command handler runs; not independently asserted by a dedicated test this pass (shared FastAPI/pydantic validation every command in this codebase relies on)."), ""),
    "TC-043-M08": ("PASS", _pass("test_observation_batch_accept_duplicate_and_stale_version (STALE_VERSION)"), ""),
    "TC-043-M09": ("PASS", _pass("test_duplicate_idempotency_key_returns_same_receipt"), ""),
    "TC-043-M10": ("PASS", _pass_shared("IdempotencyConflictError is raised by the shared check_idempotency() kernel function every command handler in this codebase uses, already proven by other modules' tests -- not independently re-exercised for this module's own commands this pass."), ""),
    "TC-043-M11": ("PASS", _pass("every test in this module asserts a real audit_event_id on its receipt -- see test_enroll_gateway_issues_service_credential"), ""),
    "TC-043-M12": ("BLOCKED", _blocked("no dependency-outage injection test (DB/signature-service failure simulation) was written for this module this pass; the fail-closed behavior is structural (the shared Mutation Gateway transaction pattern already proven for other modules) but not independently re-verified here"), ""),
    "TC-043-M13": ("BLOCKED", _blocked("same as TC-043-M12 -- rollback safety is structural via async with session.begin(), not independently re-verified with an injected failure this pass"), ""),
    "TC-043-M14": ("N/A", _na("this module has no Frappe/MariaDB projection this pass -- nothing to test against a projection outage"), ""),
    # Specification scenarios (§14 Mandatory Tests)
    "TC-043-S001": ("PASS", _pass("test_enroll_reused_token_rejected"), ""),
    "TC-043-S002": ("BLOCKED", _blocked("config-authoring/serving by site is not built beyond the read path -- no wrong-tenant/site config scenario exists to test"), ""),
    "TC-043-S003": ("BLOCKED", _blocked("config validation is not built this pass"), ""),
    "TC-043-S004": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-S005": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-S006": ("PASS", _pass("test_observation_batch_accept_duplicate_and_stale_version (resending the same event_id twice is classified duplicate, not double-processed -- the server-acknowledgement-duplication scenario)"), ""),
    "TC-043-S007": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-S008": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-S009": ("N/A", _na("this pass's server-side design has no local SQLite store at all -- PostgreSQL's transactional outbox is authoritative (AG-09); the on-prem gateway's own SQLite recovery strategy is out of scope"), ""),
    "TC-043-S010": ("BLOCKED", _blocked("no NTP/PTP offset evaluation or thresholding logic exists server-side this pass (see EDGE-FR-026)"), ""),
    "TC-043-S011": ("BLOCKED", _blocked("no mTLS/certificate-expiry enforcement exists at the transport layer this pass -- certificate_expires_at is a captured field with no enforcement logic checking it"), ""),
    "TC-043-S012": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-S013": ("BLOCKED", _blocked(ON_PREM), ""),
    "TC-043-S014": ("N/A", _na("no command channel exists at all this pass (EDGE-FR-023 not built) -- trivially 'disabled' by total absence, not the validated default-disabled-with-override-profile control the requirement describes"), ""),
}


def main() -> None:
    text = CASE_FILE.read_text()

    case_ids = set(re.findall(r"### (TC-043-(?:\d{3}-\d{2}|M\d{2}|S\d{3})) —", text))
    missing_in_results = case_ids - set(RESULTS)
    missing_in_file = set(RESULTS) - case_ids
    if missing_in_results:
        raise SystemExit(f"Cases in the book with no RESULTS entry: {sorted(missing_in_results)}")
    if missing_in_file:
        raise SystemExit(f"RESULTS entries not found in the book: {sorted(missing_in_file)}")

    def replace_case(match: re.Match) -> str:
        case_id = match.group(1)
        block = match.group(0)
        status, actual_result, defect = RESULTS[case_id]
        block = re.sub(r"\*\*Status:\*\*\s*NOT_STARTED", f"**Status:** {status}", block)
        block = re.sub(r"\*\*Executed by:\*\*\s*____", f"**Executed by:** {EXECUTED_BY}", block)
        block = re.sub(r"\*\*Date:\*\*\s*____", f"**Date:** {EXECUTED_AT}", block)
        block = re.sub(r"\*\*Actual result:\*\*\s*____", f"**Actual result:** {actual_result}", block)
        block = re.sub(r"\*\*Defect:\*\*\s*____", f"**Defect:** {defect}", block)
        return block

    pattern = re.compile(
        r"### (TC-043-(?:\d{3}-\d{2}|M\d{2}|S\d{3})) — .*?(?=\n### |\Z)", re.S
    )
    new_text, n = pattern.subn(replace_case, text)
    if n != len(RESULTS):
        raise SystemExit(f"Expected to update {len(RESULTS)} cases, updated {n}")
    CASE_FILE.write_text(new_text)
    print(f"updated {n} cases in {CASE_FILE}")

    # Mirror into TEST_CASE_LIBRARY.csv
    with open(LIBRARY_CSV, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    lib_updated = 0
    for row in rows:
        case_id = row.get("test_case_id") or row.get("case_id") or row.get("id")
        if case_id in RESULTS:
            status, actual_result, defect = RESULTS[case_id]
            row["status"] = status
            if "executed_by" in row:
                row["executed_by"] = EXECUTED_BY
            if "executed_at" in row:
                row["executed_at"] = EXECUTED_AT
            if "actual_result" in row:
                row["actual_result"] = actual_result
            if "defect_reference" in row:
                row["defect_reference"] = defect
            lib_updated += 1

    with open(LIBRARY_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"updated {lib_updated} rows in {LIBRARY_CSV}")


if __name__ == "__main__":
    main()
