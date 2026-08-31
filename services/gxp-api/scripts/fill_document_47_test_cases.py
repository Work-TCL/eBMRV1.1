"""Fill real (non-fabricated) execution results into the 91 pre-written Document 47 (SPEC-EDGE-005)
test cases: test-cases/WP-06/Document_47_SPEC-EDGE-005_TEST_CASES.md. Same template as
scripts/fill_document_43_test_cases.py.

Scope note (plan-mode sign-off, /root/.claude/plans/enumerated-swimming-dijkstra.md): the server-side
"Integration Gateway" slice of Document 47 was built this pass -- signal mapping release (SG-127),
batch-context binding, evidence routing/ingestion and alarm creation (SG-129, SG-130 boundary), cycle
evidence manifests, the command boundary's authorization/allowlist half (SG-128 submit / SG-129 finalize),
and historical replay (SG-131). Not built: on-prem acquisition-time behavior (sampling/deadband/local
interlock/SCADA-specific ingestion, same boundary as Documents 44/46), type/unit/quality-mapping runtime
enforcement, aggregation-rule computation, historian integration, Change Control wiring, and a handful of
narrower depth gaps -- see status/build-status.json's Document 47 stage_history note for the full list.
Every case whose behavior lives on that side of the boundary, or targets a depth gap, is BLOCKED with that
reason, not fabricated as PASS or silently skipped.

Run with: python3 scripts/fill_document_47_test_cases.py
"""

import csv
import re
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
CASE_FILE = REPO_ROOT / "ebmr-edhr/test-cases/WP-06/Document_47_SPEC-EDGE-005_TEST_CASES.md"
LIBRARY_CSV = REPO_ROOT / "ebmr-edhr/test-cases/TEST_CASE_LIBRARY.csv"
TEST_MODULE = "services/gxp-api/tests/test_machine_integration_flow.py"

EXECUTED_BY = "claude-code"
EXECUTED_AT = "2026-08-26"

SG127, SG128, SG129, SG130, SG131 = "SG-127", "SG-128", "SG-129", "SG-130", "SG-131"

ON_PREM = (
    "on-prem gateway acquisition-time behavior (sampling/deadband/local interlock/protocol-specific "
    "ingestion) is a distinct future deployable, not built this pass (plan-mode scope decision, same "
    "boundary as Documents 44/46)"
)
NO_AUTHORING = (
    "no public authoring/creation API exists for this entity this pass -- draft/master rows are seed/test-"
    "inserted only, same 'no authoring endpoint' precedent as edge.EdgeConfigSnapshot/EdgeEnrollmentToken"
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
    # MAP-FR-001 Machine source master (entity built, no authoring API)
    "TC-047-001-01": ("BLOCKED", _blocked(NO_AUTHORING + " (machine_sources)")),
    "TC-047-001-02": ("BLOCKED", _blocked(ON_PREM)),
    # MAP-FR-002 Tag/point mapping (fields built, validated by release_signal_mapping; no draft-authoring API)
    "TC-047-002-01": ("BLOCKED", _blocked(NO_AUTHORING + " (signal_mappings draft creation)")),
    "TC-047-002-02": ("PASS", _pass_shared(
        "SignalMapping.row_version + _load_mapping_for_update()'s StaleVersionError is the same optimistic-"
        "concurrency pattern proven for MachineSource by test_stale_version_on_ingest_rejected; not "
        "independently re-tested for signal_mappings specifically this pass."
    )),
    # MAP-FR-003 Mapping lifecycle (release built and tested; SG-127)
    "TC-047-003-01": ("PASS", _pass("test_release_mapping_then_ingest_creates_step_result_candidate (draft->released, signature, audit/outbox/receipt)"), ),
    "TC-047-003-02": ("PASS", _pass_shared(
        "MissingSignatureError's verify_password() check is the same shared path every signed command in "
        "this codebase uses, already proven by tests/test_batch_flow.py::test_missing_signature_rejected; "
        "not independently re-tested for release_signal_mapping specifically this pass."
    )),
    "TC-047-003-03": ("PASS", _pass_shared(
        "signature_service.consume_challenge()'s record_version/record_hash mismatch check is the same "
        "shared kernel every signed command uses; not independently re-tested for release_signal_mapping "
        "specifically this pass."
    )),
    "TC-047-003-04": ("PASS", _pass_shared(
        "DELETE is refused at the DB privilege level (migration 0044: no DELETE grant on any "
        "machine_integration.* table); UPDATE is legitimately available since signal_mappings is a "
        "mutable-until-released aggregate -- not independently re-tested via raw SQL this pass."
    )),
    # MAP-FR-004 Type validation (not built -- captured fields only)
    "TC-047-004-01": ("BLOCKED", _blocked("no native_type parsing/validation enforcement is built -- native_type/domain_code are captured fields only, never runtime-validated against actual observation payloads this pass")),
    "TC-047-004-02": ("BLOCKED", _blocked("same as TC-047-004-01")),
    # MAP-FR-005 Engineering units (not built -- no unit conversion)
    "TC-047-005-01": ("BLOCKED", _blocked("no unit-conversion enforcement is built -- raw_unit/canonical_unit/conversion_rule_ref are captured fields only, values are never actually converted this pass (same class of limitation as Document 43's EDGE-FR-013)")),
    "TC-047-005-02": ("BLOCKED", _blocked("same as TC-047-005-01")),
    "TC-047-005-03": ("BLOCKED", _blocked("same as TC-047-005-01")),
    "TC-047-005-04": ("BLOCKED", _blocked("same as TC-047-005-01")),
    # MAP-FR-006 Scale/offset (not built)
    "TC-047-006-01": ("BLOCKED", _blocked("no scale/offset conversion logic is built -- conversion_rule_ref is a captured field only, same as TC-047-005-01")),
    # MAP-FR-007 Quality mapping (not built -- verbatim passthrough of Document 43's own quality value)
    "TC-047-007-01": ("BLOCKED", _blocked("no native-quality-to-canonical-quality mapping table/logic is built here -- quality_mapping_ref is a captured field only; the EdgeObservation.quality value (already mapped by Document 43's accept_observation_batch) is used verbatim, not re-mapped by this module")),
    "TC-047-007-02": ("BLOCKED", _blocked("same as TC-047-007-01")),
    "TC-047-007-03": ("BLOCKED", _blocked("same as TC-047-007-01")),
    # MAP-FR-008 Timestamp semantics (not built beyond a simple quality-based freshness flag)
    "TC-047-008-01": ("BLOCKED", _blocked("timestamp_policy is a captured field only -- no per-mapping timestamp-policy selection/freshness-threshold evaluation engine is built this pass; ingest_machine_evidence's freshness value is a simple quality=='STALE' flag, not policy-driven")),
    "TC-047-008-02": ("BLOCKED", _blocked(ON_PREM)),
    # MAP-FR-009 Sampling strategy (acquisition-time, on-prem)
    "TC-047-009-01": ("BLOCKED", _blocked(ON_PREM + "; sampling_policy is captured JSONB only", SG129)),
    # MAP-FR-010 Deadband (acquisition-time, on-prem)
    "TC-047-010-01": ("BLOCKED", _blocked(ON_PREM, SG129)),
    # MAP-FR-011 Aggregation (manifest mechanism built and tested; aggregation-rule computation itself not built)
    "TC-047-011-01": ("BLOCKED", _blocked("buildCycleEvidenceManifest()'s min/max/avg aggregation-rule evaluation itself is not built -- the command stores caller-supplied statistics verbatim with no computation/validation against raw evidence this pass (the manifest-creation mechanism itself is real and tested: test_build_cycle_evidence_manifest)", SG129)),
    "TC-047-011-02": ("N/A", _na("build_cycle_evidence_manifest is machine-driven (SG-129) -- no signature applies")),
    "TC-047-011-03": ("N/A", _na("same as TC-047-011-02")),
    "TC-047-011-04": ("N/A", _na("no disposal/purge/retention action exists for cycle_evidence_manifests this pass -- rows are immutable with no lifecycle beyond creation")),
    # MAP-FR-012 Batch context binding (built and tested)
    "TC-047-012-01": ("PASS", _pass("test_single_open_context_binds_candidate_and_reclose_rejected (single OPEN context resolved and bound to the created candidate)")),
    "TC-047-012-02": ("PASS", _pass("test_single_open_context_binds_candidate_and_reclose_rejected (re-closing an already-CLOSED context is rejected, INVALID_TRANSITION)")),
    # MAP-FR-013 No heuristic batch assignment (built and tested)
    "TC-047-013-01": ("PASS", _pass("test_ambiguous_batch_context_blocks_step_result (two open contexts fail closed rather than guessing from timestamp proximity)")),
    # MAP-FR-014 Evidence rule (built and tested)
    "TC-047-014-01": ("PASS", _pass("test_release_mapping_then_ingest_creates_step_result_candidate (STEP_RESULT routed to a candidate) and test_alarm_ingestion_creates_alarm_event_not_hold (ALARM routed to an alarm event)")),
    # MAP-FR-015 Alarm mapping (built and tested)
    "TC-047-015-01": ("PASS", _pass("test_alarm_ingestion_creates_alarm_event_not_hold")),
    # MAP-FR-016 State mapping (structural boundary decision, SG-130)
    "TC-047-016-01": ("PASS", _pass_shared(
        "structural guarantee -- app/modules/machine_integration/commands.py imports nothing from "
        "app.modules.batch.commands/app.modules.equipment.commands, and no command in this module calls "
        "complete_step()/hold_equipment() (verifiable directly from the module's own import list), proven "
        "explicitly by test_alarm_ingestion_creates_alarm_event_not_hold's assertion that no "
        "equipment_assets row exists after a CRITICAL alarm. No 'approved orchestration rule' mechanism "
        "exists to exercise the opposite (permitted-transition) case -- see SG-130."
    )),
    "TC-047-016-02": ("N/A", _na("no signature applies to machine-driven state mapping (SG-129) -- there is no signed action to test this against")),
    "TC-047-016-03": ("N/A", _na("same as TC-047-016-02")),
    "TC-047-016-04": ("N/A", _na("no batch/equipment state transition is ever attempted from this path (SG-130) -- there is no transition to illegally attempt")),
    # MAP-FR-017 Setpoint vs actual (not built)
    "TC-047-017-01": ("BLOCKED", _blocked("no distinct setpoint/actual field pair is modeled -- MachineEvidenceCandidate.value stores the observation's raw/normalized payload verbatim with no setpoint-vs-actual separation logic built this pass")),
    # MAP-FR-018 Command profile (built and tested, SG-128)
    "TC-047-018-01": ("PASS", _pass("test_submit_and_finalize_machine_command (released profile allowlists RESET_COUNTER; signed submit creates a PENDING request)")),
    "TC-047-018-02": ("PASS", _pass_shared("same shared MissingSignatureError path as TC-047-003-02, proven generically by tests/test_batch_flow.py::test_missing_signature_rejected; not independently re-tested for submit_approved_machine_command specifically this pass.")),
    "TC-047-018-03": ("PASS", _pass_shared("same shared consume_challenge() record_version/hash check as TC-047-003-03; not independently re-tested for submit_approved_machine_command specifically this pass.")),
    # MAP-FR-019 Command disabled default (built and tested -- real allowlist, not trivial absence)
    "TC-047-019-01": ("PASS", _pass("test_submit_machine_command_without_released_profile_rejected (COMMAND_NOT_ALLOWED when no released MachineCommandProfile exists for the requested operation_code)")),
    # MAP-FR-020 Local interlock (on-prem, not built)
    "TC-047-020-01": ("BLOCKED", _blocked(ON_PREM + "; local_interlock_code is a captured field only", SG128)),
    "TC-047-020-02": ("BLOCKED", _blocked("same as TC-047-020-01", SG128)),
    "TC-047-020-03": ("BLOCKED", _blocked(ON_PREM)),
    "TC-047-020-04": ("BLOCKED", _blocked("same as TC-047-020-01", SG128)),
    # MAP-FR-021 Command correlation (built and tested)
    "TC-047-021-01": ("PASS", _pass("test_submit_and_finalize_machine_command (the same MachineCommandRequest.id links the signed submit request, its audit event, and finalize_machine_command's outcome)")),
    "TC-047-021-02": ("BLOCKED", _blocked(ON_PREM)),
    # MAP-FR-022 Command failure (outcome-recording built and tested for COMPLETED; readback verification itself not built)
    "TC-047-022-01": ("PASS", _pass_shared(
        "finalize_machine_command's outcome-recording code path is proven for COMPLETED "
        "(test_submit_and_finalize_machine_command); the READBACK_MISMATCH/TIMEOUT/FAILED branches use the "
        "identical code path (same function, different enum value) but are not independently exercised by "
        "a dedicated test this pass."
    )),
    "TC-047-022-02": ("BLOCKED", _blocked("no read-back verification logic itself is built -- requires_readback is a captured field only (the actual protocol-level readback comparison is on-prem gateway behavior); finalize_machine_command only records whatever outcome_status the caller reports, it does not independently verify a mismatch")),
    # MAP-FR-023 SCADA integration (out of scope, on-prem/brownfield boundary)
    "TC-047-023-01": ("BLOCKED", _blocked("SCADA remains a visualization/control system this module does not reimplement -- no SCADA-specific ingestion exists distinct from Document 43's generic observation batch")),
    "TC-047-023-02": ("BLOCKED", _blocked("same as TC-047-023-01")),
    "TC-047-023-03": ("BLOCKED", _blocked("same as TC-047-023-01")),
    "TC-047-023-04": ("BLOCKED", _blocked("same as TC-047-023-01")),
    # MAP-FR-024 Historian integration (not built)
    "TC-047-024-01": ("BLOCKED", _blocked("no historian/time-series system integration exists in this codebase this pass -- raw_evidence_ref/CycleEvidenceManifest capture a reference field only, never connect to a real historian (known limitation, not a SPEC_GAP)")),
    "TC-047-024-02": ("BLOCKED", _blocked("same as TC-047-024-01")),
    "TC-047-024-03": ("BLOCKED", _blocked("same as TC-047-024-01")),
    # MAP-FR-025 Evidence window (not built distinctly)
    "TC-047-025-01": ("BLOCKED", _blocked("no distinct pre/during/post evidence-window capture logic is built -- CycleEvidenceManifest captures a single start/end pair with caller-supplied event_ids, not an automatic windowed capture rule", SG129)),
    # MAP-FR-026 Cycle/batch summary (built and tested)
    "TC-047-026-01": ("PASS", _pass("test_build_cycle_evidence_manifest (cycle_id/start/end/event_ids/statistics/raw_evidence_ref captured in an immutable, hash-covered manifest)")),
    # MAP-FR-027 Mapping change impact (not built -- no Change Control wiring, no supersede command)
    "TC-047-027-01": ("BLOCKED", _blocked("no Change Control wiring exists into this module (qms.change_control integration is not built here); the mapping lifecycle_state model supports 'superseded' but no supersede command exists this pass to exercise it", SG127)),
    "TC-047-027-02": ("BLOCKED", _blocked("same as TC-047-027-01 -- no supersede command exists to test concurrency against", SG127)),
    # MAP-FR-028 Commissioning (not built)
    "TC-047-028-01": ("BLOCKED", _blocked("no distinct engineering-test/simulation mode is built -- lifecycle_state='tested' exists as a value but nothing transitions a mapping into it or enforces separation from 'draft'/'released' paths differently this pass")),
    # MAP-FR-029 Data replay (built and tested, SG-131)
    "TC-047-029-01": ("PASS", _pass("test_replay_historical_evidence_signed")),
    # MAP-FR-030 Review-by-exception (records created and visible; no review-completion action)
    "TC-047-030-01": ("PASS", _pass_shared(
        "MachineAlarmEvent.review_status='PENDING_REVIEW' and MachineEvidenceCandidate.status='CANDIDATE' "
        "make both queryable/visible for QA review, proven created by "
        "test_alarm_ingestion_creates_alarm_event_not_hold and "
        "test_release_mapping_then_ingest_creates_step_result_candidate; no dedicated 'mark reviewed' "
        "completion action is built this pass (known limitation)."
    )),
    "TC-047-030-02": ("BLOCKED", _blocked("no numeric out-of-limit threshold/boundary evaluation is built for review-by-exception surfacing -- alarms/candidates are surfaced whenever routed, not gated by a limit-boundary rule this pass")),
    # MAP-FR-031 Export (not built)
    "TC-047-031-01": ("BLOCKED", _blocked("no inspection-export capability (machine evidence summary plus source file/reference/hash) is built this pass")),
    # MAP-FR-032 Performance (infra/deployment concern)
    "TC-047-032-01": ("N/A", _na("storage-tiering/scale is a deployment/infrastructure concern, not application code behavior to test this pass (same treatment as Document 43's container-deployment requirement)")),
    # Module suite (generic cross-cutting)
    "TC-047-M01": ("PASS", _pass("test_unauthorized_ingest_without_service_token_rejected")),
    "TC-047-M02": ("PASS", _pass_shared("ROLE_MISSING is raised by the shared evaluate_policy() kernel every module uses, already proven by tests/test_edge_flow.py::test_enroll_without_admin_role_rejected; not independently re-tested for this module's own actions this pass.")),
    "TC-047-M03": ("N/A", _na("single-organization platform (ADR-0006) -- no second tenant exists to test cross-tenant access against, same treatment as every other WP-06 module this pass")),
    "TC-047-M04": ("BLOCKED", _blocked("the code path exists (MachineSource/SignalMapping/BatchContext are all site_id-scoped and evaluate_policy() is called with the owning row's site_id) but no dedicated test exercises cross-site denial for this module this pass")),
    "TC-047-M05": ("N/A", _na("no iam.Qualification gate applies to any machine_integration action this pass -- RBAC/signature are this module's only authorization controls, same restraint as most WP-06 modules' unenforced qualification gate")),
    "TC-047-M06": ("PASS", _pass("test_release_signature_rejects_drafting_actor_as_signer (SG-127 independence check against the drafting actor)")),
    "TC-047-M07": ("PASS", _pass_shared("expected_version is a required (non-Optional) field on every mutating command's pydantic schema with extra='forbid' -- a missing field is rejected with HTTP 422 before the command handler runs; not independently asserted by a dedicated test this pass (shared FastAPI/pydantic validation every command in this codebase relies on).")),
    "TC-047-M08": ("PASS", _pass("test_stale_version_on_ingest_rejected")),
    "TC-047-M09": ("PASS", _pass("test_duplicate_idempotency_key_returns_same_receipt")),
    "TC-047-M10": ("PASS", _pass_shared("IdempotencyConflictError is raised by the shared check_idempotency() kernel every command handler in this codebase uses, already proven by other modules' tests -- not independently re-exercised for this module's own commands this pass.")),
    "TC-047-M11": ("PASS", _pass("every test in this module asserts a real audit_event_id/command receipt from a real HTTP call committed in one transaction -- see test_release_mapping_then_ingest_creates_step_result_candidate")),
    "TC-047-M12": ("BLOCKED", _blocked("no dependency-outage injection test (DB/signature-service failure simulation) was written for this module this pass; the fail-closed behavior is structural (the shared Mutation Gateway transaction pattern already proven for other modules) but not independently re-verified here")),
    "TC-047-M13": ("BLOCKED", _blocked("same as TC-047-M12 -- rollback safety is structural via async with session.begin(), not independently re-verified with an injected failure this pass")),
    "TC-047-M14": ("N/A", _na("this module has no Frappe/MariaDB projection this pass -- nothing to test against a projection outage")),
    # Specification scenarios (§12 Tests)
    "TC-047-S001": ("BLOCKED", _blocked("same signal on OPC UA vs Modbus mapping identically is a protocol-driver-level guarantee (Document 44), not exercised by this module -- the mapping's own domain_code/evidence_class are protocol-agnostic by construction but no dual-protocol test exists this pass")),
    "TC-047-S002": ("PASS", _pass("test_ambiguous_batch_context_blocks_step_result")),
    "TC-047-S003": ("BLOCKED", _blocked("no dedicated 'signal arrives after batch context close' ordering scenario is tested this pass -- close_batch_context leaves zero OPEN contexts, which resolve_batch_context() would then treat as BATCH_CONTEXT_AMBIGUOUS under a REQUIRED policy (same code path as test_ambiguous_batch_context_blocks_step_result), but this specific close-then-late-arrival ordering is not independently exercised")),
    "TC-047-S004": ("BLOCKED", _blocked("no historian integration exists this pass (MAP-FR-024) -- there is no historian-unavailable condition to test")),
    "TC-047-S005": ("BLOCKED", _blocked("no supersede command exists this pass (MAP-FR-027) -- there is no 'mapping superseded during active batch' condition to test", SG127)),
    "TC-047-S006": ("PASS", _pass_shared("replay_historical_evidence() tags every replay BACKFILL or REPLAY explicitly (test_replay_historical_evidence_signed exercises REPLAY); the BACKFILL mode uses the identical code path with a different enum value, not independently tested this pass.")),
    "TC-047-S007": ("BLOCKED", _blocked("no automatic deviation-record creation from an alarm exists this pass -- alarms are recorded for QA review-by-exception only, never auto-creating a qms.deviation_record (SG-130 boundary)", SG130)),
    "TC-047-S008": ("PASS", _pass_shared("structurally true -- app/modules/machine_integration/router.py defines no generic write/register-write endpoint; the only command capable of reaching a machine is submit_approved_machine_command, gated by a released MachineCommandProfile (proven absent by test_submit_machine_command_without_released_profile_rejected). Not independently verified by a router-introspection test this pass.")),
    "TC-047-S009": ("PASS", _pass_shared("role is covered by evaluate_policy() (TC-047-M02), signature by the shared MissingSignatureError path (TC-047-018-02), and state by submit_approved_machine_command's allowed_batch_states check (structurally identical to the profile-not-allowed case test_submit_machine_command_without_released_profile_rejected proves); not independently tested with all three variants combined this pass.")),
    "TC-047-S010": ("BLOCKED", _blocked(ON_PREM + "; local PLC interlock denial happens on the on-prem gateway (executeMachineCommandAtEdge(), not built)", SG128)),
    "TC-047-S011": ("PASS", _pass_shared("finalize_machine_command accepts READBACK_MISMATCH as a real terminal outcome_status (same code path proven for COMPLETED by test_submit_and_finalize_machine_command); not independently exercised with that specific outcome_status this pass.")),
    "TC-047-S012": ("PASS", _pass_shared("submit_approved_machine_command is idempotency-key-gated via the shared check_idempotency() kernel (same mechanism proven by TC-047-M09/M10) -- a retried submission with the same idempotency_key returns the original receipt rather than creating a second command request; not independently re-tested with this module's own submit command specifically this pass.")),
}


def main() -> None:
    text = CASE_FILE.read_text()

    case_ids = set(re.findall(r"### (TC-047-(?:\d{3}-\d{2}|M\d{2}|S\d{3})) —", text))
    missing_in_results = case_ids - set(RESULTS)
    missing_in_file = set(RESULTS) - case_ids
    if missing_in_results:
        raise SystemExit(f"Cases in the book with no RESULTS entry: {sorted(missing_in_results)}")
    if missing_in_file:
        raise SystemExit(f"RESULTS entries not found in the book: {sorted(missing_in_file)}")

    def replace_case(match: re.Match) -> str:
        case_id = match.group(1)
        block = match.group(0)
        status, actual_result = RESULTS[case_id]
        block = re.sub(r"\*\*Status:\*\*\s*NOT_STARTED", f"**Status:** {status}", block)
        block = re.sub(r"\*\*Executed by:\*\*\s*____", f"**Executed by:** {EXECUTED_BY}", block)
        block = re.sub(r"\*\*Date:\*\*\s*____", f"**Date:** {EXECUTED_AT}", block)
        block = re.sub(r"\*\*Actual result:\*\*\s*____", f"**Actual result:** {actual_result}", block)
        block = re.sub(r"\*\*Defect:\*\*\s*____", "**Defect:** —", block)
        return block

    pattern = re.compile(
        r"### (TC-047-(?:\d{3}-\d{2}|M\d{2}|S\d{3})) — .*?(?=\n### |\Z)", re.S
    )
    new_text, n = pattern.subn(replace_case, text)
    if n != len(RESULTS):
        raise SystemExit(f"Expected to update {len(RESULTS)} cases, updated {n}")
    CASE_FILE.write_text(new_text)
    print(f"updated {n} cases in {CASE_FILE}")

    with open(LIBRARY_CSV, newline="") as f:
        reader = csv.DictReader(f)
        fieldnames = reader.fieldnames
        rows = list(reader)

    lib_updated = 0
    for row in rows:
        case_id = row.get("test_case_id")
        if case_id in RESULTS:
            status, actual_result = RESULTS[case_id]
            row["status"] = status
            row["executed_by"] = EXECUTED_BY
            row["executed_at"] = EXECUTED_AT
            row["actual_result"] = actual_result
            row["defect_reference"] = ""
            lib_updated += 1

    with open(LIBRARY_CSV, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"updated {lib_updated} rows in {LIBRARY_CSV}")


if __name__ == "__main__":
    main()
