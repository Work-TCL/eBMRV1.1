# Claude Code prompt — WP-04 / Document 24: LIMS Integration Architecture & Generic Adapter Contract

TASK:
Implement the LIMS Integration Architecture & Generic Adapter Contract module (SPEC-QC-002) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_24_LIMS_Integration_Generic_Adapter_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: LIMS-FR-001..034 (34)
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
- `services/gxp-api/src/modules/qc` and its tests
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
services/gxp-api/src/modules/qc/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/qc/migrations/     # owned entities only
services/gxp-api/src/modules/qc/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-qc-002.yaml
contracts/events/spec-qc-002/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-qc-002/
```

REQUIREMENTS TO IMPLEMENT (34):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| LIMS-FR-001 | Provider abstraction | Expose generic LIMSProvider contract independent of LabWare/STARLIMS/openBIS/custom vendor. | Vendor-neutral domain. |
| LIMS-FR-002 | System registry | Register LIMS instances, site scope, auth method, endpoint/version, supported operations and health. | Multiple LIMS supported. |
| LIMS-FR-003 | Master mapping | Map product/material/test method/spec/sample types and external IDs with version/status. | Semantic mapping controlled. |
| LIMS-FR-004 | Sample creation | Send sample/test request with exact source record/version, required tests, priority and correlation ID. | Request attributable. |
| LIMS-FR-005 | External sample ID | Persist LIMS sample/order IDs without replacing internal GxP IDs. | Identity separation. |
| LIMS-FR-006 | Status sync | Receive/poll sample/test statuses using idempotent versioned callbacks. | Workflow current. |
| LIMS-FR-007 | Result ingestion | Receive structured result including test code, value/UOM, method, analyst/system source, completion/review state and external result version. | Complete result contract. |
| LIMS-FR-008 | Raw evidence reference | Receive secure evidence/file/export/reference metadata where integration design supports it. | Original evidence linked. |
| LIMS-FR-009 | Result versioning | Each LIMS result/revision maps to immutable accepted GxP result version; original prior versions retained. | No overwrite. |
| LIMS-FR-010 | Duplicate protection | Use external event/result IDs plus idempotency hash to avoid duplicate accepted results. | Replay safe. |
| LIMS-FR-011 | Ordering | Handle late/out-of-order callbacks by external version/sequence and current GxP state rules. | No stale overwrite. |
| LIMS-FR-012 | Schema validation | Validate required fields, data types, UOM, test mapping, method version and source identity before acceptance. | Bad payload rejected/quarantined. |
| LIMS-FR-013 | Source authentication | Use mTLS/OAuth/workload identity/API signing as supported; anonymous callbacks prohibited. | Trusted source. |
| LIMS-FR-014 | Tenant/site scope | LIMS instance and mapping restricted to authorized customer/site. | Isolation. |
| LIMS-FR-015 | Result acceptance policy | External LIMS 'approved' status is evidence, not automatic final batch release; GxP Release Engine evaluates overall eligibility. | Authority separated. |
| LIMS-FR-016 | OOS trigger | External OOS result creates/links GxP OOS record even if LIMS manages its own investigation; source-of-truth responsibility is configured. | No missed OOS. |
| LIMS-FR-017 | OOS ownership mode | Support GXP_MANAGED, LIMS_MANAGED_WITH_SYNC, or HYBRID integration profile with explicit field/state ownership. | No dual-master conflict. |
| LIMS-FR-018 | OOT sync | Receive OOT/trend flag where external LIMS provides it; GxP may independently evaluate configured OOT rules. | Trend visible. |
| LIMS-FR-019 | Result correction | LIMS revision creates new accepted version; never update prior GxP result row. | Data integrity. |
| LIMS-FR-020 | Retest/resample linkage | External new test/sample must carry relation to originating OOS/investigation when applicable. | Scientific history preserved. |
| LIMS-FR-021 | Cancellation | Sample/test cancellation requires reason/source and may be blocked if required for batch/material release. | No silent missing test. |
| LIMS-FR-022 | Acknowledgement | GxP sends accepted/rejected callback acknowledgement with internal event/result ID. | Reconciliation. |
| LIMS-FR-023 | Retry | Outbound and inbound processing idempotent with exponential backoff and dead-letter/manual reconciliation. | Resilient. |
| LIMS-FR-024 | Dead letter | Unprocessable messages retained with payload hash/reference, error code, retry history and operator action. | No lost result. |
| LIMS-FR-025 | Reconciliation job | Periodically compare expected samples/tests/results between systems and surface missing/duplicate/version mismatch. | Integration integrity. |
| LIMS-FR-026 | Manual reconciliation | Authorized integration admin can map/replay/correct integration metadata, but cannot fabricate/change laboratory result. | Admin boundary. |
| LIMS-FR-027 | Time semantics | Store LIMS source timestamps and GxP received/accepted timestamps separately. | Chronology clear. |
| LIMS-FR-028 | Unit conversion | Only controlled UOM mapping/conversion; incompatible unit rejects result. | No semantic drift. |
| LIMS-FR-029 | Method mapping | Unknown/mismatched method/version is rejected/held for review rather than accepted as equivalent. | Method integrity. |
| LIMS-FR-030 | Attachment security | Files scanned, hashed and content-type validated; external URLs not treated as permanent evidence unless approved architecture preserves accessibility/integrity. | Evidence durable. |
| LIMS-FR-031 | Audit | Audit outbound request, inbound event, validation decision, accepted result version, mapping change and manual reconciliation. | Traceable. |
| LIMS-FR-032 | Monitoring | Health, queue age, error rate, last successful sync, result latency and reconciliation differences exposed. | Operational. |
| LIMS-FR-033 | Adapter versioning | Adapter and contract version recorded with each accepted result/event where needed for investigation. | Historical reproducibility. |
| LIMS-FR-034 | Test environment | Provide sandbox/simulator and contract test suite so vendor adapters can be validated before production. | Implementation safe. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (0 entities owned by this module):
_none declared in the source specifications_

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (6):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /integrations/lims/{instance}/samples` | yes | — |
| `POST /integrations/lims/{instance}/samples/{id}/cancel` | yes | — |
| `POST /integrations/lims/{instance}/reconcile` | yes | — |
| `GET /integrations/lims/{instance}/health` | no | — |
| `POST /integrations/lims/{instance}/events/results` | yes | — |
| `POST /integrations/lims/{instance}/events/status` | yes | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (8):
| Event type | Producer | Dedupe key |
|---|---|---|
| `LIMSSampleRequested` | SPEC-QC-002 | event_id |
| `LIMSStatusReceived` | SPEC-QC-002 | event_id |
| `LIMSResultReceived` | SPEC-QC-002 | event_id |
| `LIMSResultAccepted` | SPEC-QC-002 | event_id |
| `LIMSResultRejected` | SPEC-QC-002 | event_id |
| `LIMSResultRevised` | SPEC-QC-002 | event_id |
| `LIMSIntegrationDeadLettered` | SPEC-QC-002 | event_id |
| `LIMSReconciliationMismatchDetected` | SPEC-QC-002 | event_id |

UI SURFACES:
- LIMS Instances
- Mapping
- Message Monitor
- Dead Letter Queue
- Reconciliation Differences
- Manual Mapping Resolution
- Result History
- Health Dashboard
- correct mapping;
- retry/replay exact stored message;
- acknowledge known duplicate;
- link external/internal IDs.

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
- sample create
- duplicate sample retry
- pass result
- OOS result
- result revision
- stale version
- wrong method
- wrong UOM
- unknown sample
- duplicate event
- out-of-order events
- attachment failure
- source auth failure
- LIMS outage
- dead-letter replay
- reconciliation missing result
- administrator attempts result edit
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-04/Document_24_SPEC-QC-002_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-QC-002/<test_case_id>/`.
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
