# Claude Code prompt — WP-06 / Document 47: Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary

TASK:
Implement the Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary module (SPEC-EDGE-005) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_47_PLC_SCADA_Data_Acquisition_Evidence_Mapping_Command_Boundary_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: MAP-FR-001..032 (32)
- Approved baselines: Document 106 (signature policy), 107 (SoD), 108 (retention), 109 (SLO/RPO),
  110 (precision/UOM), 111 (risk class), 112 (schemas/migrations), 113 (contracts), 114 (glossary)
- Phase-0 artefacts: `docs/generated/03_FUNCTION_CATALOGUE.csv`, `04_DATA_MODEL_CATALOGUE.md`,
  `05_DATABASE_OWNERSHIP_MATRIX.md`, `06_API_CATALOGUE.yaml`, `07_EVENT_CATALOGUE.yaml`,
  `14_ERROR_CODE_REGISTRY.md`, `28_INTENDED_USE_GXP_RISK_MATRIX.md`

RISK CLASS: **HIGHER-PROCESS-RISK** → scripted tests, independent review, mandatory negative and failure evidence

ARCHITECTURE CONSTRAINTS:
- Frappe is UI/configuration only; no core fork or edit.
- PostgreSQL is authoritative for regulated state; MariaDB holds read-only projections.
- Every regulated write goes through the Mutation Gateway → one PostgreSQL transaction carrying
  domain state + record version + audit event + outbox event.
- Signatures follow Document 04 + the approved Document 106 policy; login/MFA is never a signature.
- Audit, vault and evidence history is append-only and superseding.
- Outbox is the authoritative event source; NATS is transport; Temporal is orchestration only.
- Caches, projections, search and reports are rebuildable and never a regulated decision source.
- Adapters and edge never write GxP tables; they submit integration commands.
- AI is advisory; it cannot sign, release, disposition, approve, alter audit or submit reports.

PRECONDITIONS:
- WP-00 foundations exist (contracts tooling, guardrails, CI gates).
- WP-01 GxP Core is available (mutation, policy, signature, audit, vault, rules).
- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `edge` and its tests
- `contracts/` entries owned by this module
- migrations for entities owned by this module
- Frappe UI surfaces for this module in `apps/ebmr_frappe/`

DO NOT:
- Do not modify anything under `specs/`.
- Do not implement a signature requirement not present in the approved Document 106 policy set
  (emit a policy row and reference the gap instead).
- Do not create a second authoritative store for an entity owned elsewhere.
- Do not add an endpoint to a module whose exposure boundary is "no independent API" (Document 113 §6).
- Do not write a migration for an entity absent from `docs/generated/04_DATA_MODEL_CATALOGUE.md`.
- Do not use binary floating point for a regulated quantity.
- Do not fabricate a test run, scan result or qualification record.
- Do not start work in another work package.

FILES TO CREATE/MODIFY:
```text
edge/src/            # domain services, command handlers, repositories
edge/migrations/     # owned entities only
edge/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-edge-005.yaml
contracts/events/spec-edge-005/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-edge-005/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| MAP-FR-001 | Machine source master | Define machine/PLC/SCADA source identity, equipment link, protocol connector and site/line. | Canonical source. |
| MAP-FR-002 | Tag/point mapping | Versioned mapping from native tag/node/register/topic to domain parameter/evidence code. | Stable semantics. |
| MAP-FR-003 | Mapping lifecycle | Draft, engineering test, review, released/effective, superseded/suspended. | Controlled configuration. |
| MAP-FR-004 | Type validation | Mapping defines native type, expected type, parsing and null/invalid handling. | No implicit casts. |
| MAP-FR-005 | Engineering units | Raw unit, canonical unit and approved conversion reference. | Reproducible. |
| MAP-FR-006 | Scale/offset | Scaling defined explicitly; test vectors required. | No hidden conversion. |
| MAP-FR-007 | Quality mapping | Native quality/status to canonical quality mapping versioned. | Integrity. |
| MAP-FR-008 | Timestamp semantics | Choose source/server/gateway timestamp usage and freshness thresholds by point. | Time clarity. |
| MAP-FR-009 | Sampling strategy | Poll/subscription/event-only/deadband/aggregation semantics explicit. | Acquisition behavior. |
| MAP-FR-010 | Deadband | Engineering deadband may reduce telemetry but cannot suppress events required as regulated evidence. | Completeness. |
| MAP-FR-011 | Aggregation | High-frequency raw data may aggregate min/max/avg/end/event window only under approved rule, with raw evidence retention policy. | Scalable evidence. |
| MAP-FR-012 | Batch context binding | Mapping can bind observation to active batch/step/operation by server-issued context token or deterministic line state. | Correct association. |
| MAP-FR-013 | No heuristic batch assignment | Do not guess batch solely from time proximity when explicit context is required. | Trace. |
| MAP-FR-014 | Evidence rule | Define which observations become GxP step results, process evidence, alarms, EM events or historian-only telemetry. | Clear data ownership. |
| MAP-FR-015 | Alarm mapping | Machine alarms mapped to severity/event code and batch/equipment impact rule. | Exception handling. |
| MAP-FR-016 | State mapping | Machine state/run/idle/fault/changeover may feed execution timeline but does not independently transition GxP batch state unless approved orchestration rule does. | Authority boundary. |
| MAP-FR-017 | Setpoint vs actual | Store/map setpoint and measured actual separately. | Evidence clarity. |
| MAP-FR-018 | Command profile | Machine commands defined as allowlisted operation with typed parameters, target, preconditions, authorization, signature, timeout and read-back verification. | Safe commands. |
| MAP-FR-019 | Command disabled default | No generic tag/register write endpoint exposed to normal UI/API. | Security. |
| MAP-FR-020 | Local interlock | Command execution requires PLC/machine local safety/interlock; software never bypasses physical control logic. | Safety. |
| MAP-FR-021 | Command correlation | Command ID links request, approval, machine write, acknowledgement/read-back and resulting evidence. | Trace. |
| MAP-FR-022 | Command failure | Timeout/readback mismatch produces failure/hold/deviation according to profile, not optimistic success. | Fail safe. |
| MAP-FR-023 | SCADA integration | Existing SCADA may remain visualization/control system; eBMR consumes approved data/events through Edge. | Brownfield friendly. |
| MAP-FR-024 | Historian integration | Raw/high-frequency data can be persisted in historian/time-series and referenced by evidence manifest/checksum. | Scale. |
| MAP-FR-025 | Evidence window | For critical operation, capture pre/during/post time window or cycle dataset reference according to mapping. | Context. |
| MAP-FR-026 | Cycle/batch summary | Machine cycle produces summary with cycle ID, start/end, parameters, alarms and raw evidence reference. | Sterile/device/process. |
| MAP-FR-027 | Mapping change impact | Change mapping requires Change Control/validation impact when GxP-relevant; open batches keep issued mapping version. | Validated state. |
| MAP-FR-028 | Commissioning | Engineering test/simulation path clearly separated from production GxP data. | No test contamination. |
| MAP-FR-029 | Data replay | Historian/backfill replay tagged and idempotent; cannot silently appear as live data. | Semantics. |
| MAP-FR-030 | Review-by-exception | Out-of-limit machine data, alarms, gaps, manual fallback and mapping changes visible in QA review. | Quality awareness. |
| MAP-FR-031 | Export | Inspection export can include machine evidence summary plus source file/reference/hash. | Reproducible. |
| MAP-FR-032 | Performance | Millions of telemetry points/day do not require millions of Frappe rows; appropriate storage tiers enforced. | Scale. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| releaseSignalMapping() | Integration Engineer + QA/Validation | mapping_draft_id; signatures | ReleasedSignalMapping | SignalMappingReleased; MAPPING_VALIDATION_INCOMPLETE |
| resolveBatchContext() | Integration Gateway | gateway/device/line; context token or active-operation reference; observation | BatchContext\ | null |
| evaluateEvidenceRouting() | Integration Gateway | observation; released mapping | EvidenceRouteDecision | EvidenceRouted; MAPPING_NOT_EFFECTIVE |
| createStepResultCandidate() | Integration Gateway | observation; batch/step context; parameter mapping | GxPCommandEnvelope | StepResultCandidateCreated; SOURCE_NOT_ALLOWED/FRESHNESS_FAILED |
| createMachineAlarmEvent() | Integration Gateway | alarm observation; mapping | AlarmEventCommand | MachineAlarmDetected |
| buildCycleEvidenceManifest() | Cycle aggregator | cycle_id; observation/event refs; start/end; profile | CycleEvidenceManifest | CycleEvidenceCreated |
| submitApprovedMachineCommand() | GxP service | command_profile_id; target; typed params; actor/signature/context | CommandRequestReceipt | MachineCommandRequested; COMMAND_NOT_ALLOWED |
| executeMachineCommandAtEdge() | Edge command handler | command_id; signed request; target; params | EdgeCommandReceipt | MachineCommandExecuted/COMMAND_INTERLOCK_DENIED |
| finalizeMachineCommand() | GxP Integration service | EdgeCommandReceipt | MachineCommandOutcome | MachineCommandCompleted/READBACK_MISMATCH |
| replayHistoricalEvidence() | Integration Admin | evidence IDs/time range; reason; target mapping mode | ReplayJobReceipt | HistoricalReplayStarted |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (0 entities owned by this module):
_none declared in the source specifications_

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (0):
_none declared in the source specifications_

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- none declared

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
Fail closed on any compliance-critical dependency outage; no degraded-mode commit.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- same signal on OPC UA and Modbus maps identically
- ambiguous batch context blocks step result
- signal late after batch close
- historian unavailable
- mapping superseded during active batch
- backfill does not look live
- alarm creates deviation rule
- generic write endpoint absent
- command wrong role/signature/state
- local PLC interlock denies command
- successful write but readback mismatch
- retry command does not duplicate effect when device supports idempotency/command correlation
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-06/Document_47_SPEC-EDGE-005_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EDGE-005/<test_case_id>/`.
- A failed case is evidence: never delete it, re-run over it, or edit the expected result to make it pass.
  Raise a defect, record the reference, re-execute as a new dated execution.

TRACEABILITY & STATUS (mandatory at the end of this prompt):
- Update `traceability/TRACEABILITY_MASTER.csv` for every requirement you touched: `build_stage`,
  `verification_state`, `test_case_ids`, `evidence_location`.
- Update `status/build-status.json`: set this module's `stage`, append to `stage_history`, set
  `requirements_state` per requirement, and set `test_pass` / `test_fail` / `test_blocked` from the
  actual recorded results.
- You may only set stages you can evidence, up to and including CODE_COMPLETE and the test states.
  `REVIEWED`, `OQ_EXECUTED`, `QUALIFIED` and `RELEASED` are set by humans, never by you.
- Run `python tooling/status/rollup.py` and include the printed summary in your completion report.

VALIDATION / TRACEABILITY:
- update `docs/generated/15_TEST_TRACEABILITY_MATRIX.csv` and `29_VALIDATION_TRACEABILITY_MASTER.csv`
- state IQ/OQ/PQ impact; HIGHER-PROCESS-RISK functions need retained objective evidence
- Part 11 impact where signatures are involved (Document 88)

ACCEPTANCE CRITERIA:
- every requirement above implemented, traced and tested
- all listed tests executed with real results
- no architecture guardrail violation
- contracts committed before implementation and compatible

SPEC_GAP RULE:
Do not guess regulated behaviour. Append unresolved decisions to `docs/generated/18_SPEC_GAPS.md`
with affected requirements, risk, options and blocking status, then continue only on unaffected work.

BEFORE COMPLETION:
Run lint, typecheck, unit, contract, integration and guardrail checks. Report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; **test cases executed with PASS/FAIL/BLOCKED counts and
the case ids of every failure**; validation impact; **traceability and status files updated (include the
rollup summary)**; unresolved SPEC_GAPs; known limitations.
