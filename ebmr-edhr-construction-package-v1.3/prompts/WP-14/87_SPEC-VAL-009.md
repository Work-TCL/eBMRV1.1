# Claude Code prompt — WP-14 / Document 87: Data Migration, Conversion, Cutover & Reconciliation Validation

TASK:
Implement the Data Migration, Conversion, Cutover & Reconciliation Validation module (SPEC-VAL-009) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_87_Data_Migration_Conversion_Cutover_Reconciliation_Validation_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: MIGV-FR-001..022 (22)
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
- `validation` and its tests
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
validation/src/            # domain services, command handlers, repositories
validation/migrations/     # owned entities only
validation/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-val-009.yaml
contracts/events/spec-val-009/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-val-009/
```

REQUIREMENTS TO IMPLEMENT (22):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| MIGV-FR-001 | Migration plan | Define source, scope, cutoff, transformations, owners and acceptance. | Controlled conversion. |
| MIGV-FR-002 | Source snapshot | Identify/freeze exact source export/cutoff/hash. | Reproducibility. |
| MIGV-FR-003 | Profiling | Assess completeness, duplicates, orphans, invalid values. | Risk awareness. |
| MIGV-FR-004 | Mapping | Source→target entity/field/UOM/status mapping versioned/approved. | Clarity. |
| MIGV-FR-005 | Transformation code | Scripts/version reviewed and testable. | Controlled logic. |
| MIGV-FR-006 | Regulated history | Preserve needed history/provenance or controlled legacy archive. | Continuity. |
| MIGV-FR-007 | Identity mapping | Legacy ID→new ID mapping retained. | Trace. |
| MIGV-FR-008 | Reference integrity | Relationships reconciled after import. | Integrity. |
| MIGV-FR-009 | Counts/totals | Counts, hashes, quantities/control totals by data class. | Completeness. |
| MIGV-FR-010 | Sampling/full compare | Use full automated compare for critical fields where feasible, otherwise risk-based sampling. | Evidence. |
| MIGV-FR-011 | Attachments | Evidence object counts/hashes/links reconciled. | Evidence. |
| MIGV-FR-012 | Legacy signatures | Preserve/migrate signature evidence without recreating historic signature as new signing. | Integrity. |
| MIGV-FR-013 | Legacy audit | Import provenance-marked audit/history or retain accessible legacy archive. | History. |
| MIGV-FR-014 | Timezones | Source timezone/precision semantics explicitly handled. | Chronology. |
| MIGV-FR-015 | Decimal/UOM | Conversion precision and UOM rules tested. | Accuracy. |
| MIGV-FR-016 | Dry runs | Material migration uses rehearsal(s) based on risk/scale. | Cutover confidence. |
| MIGV-FR-017 | Cutover delta | Final delta/change-freeze strategy reconciles late changes. | Completeness. |
| MIGV-FR-018 | Errors | Rejected records retained with reason/disposition. | No silent loss. |
| MIGV-FR-019 | Rollback | Fallback strategy avoids losing post-cutover transactions. | Operational safety. |
| MIGV-FR-020 | Approval | Final migration accepted only after reconciliation/deviation disposition. | Gate. |
| MIGV-FR-021 | Legacy access | Post-cutover legacy read-only retrieval strategy documented. | Inspection. |
| MIGV-FR-022 | Evidence retention | Scripts/config/logs/source hashes/reconciliations retained. | Audit. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createMigrationValidationPlan() | Data/Validation | source; target; scope; cutoff; mappings; reconciliation rules | MigrationValidationPlan | MigrationValidationPlanCreated |
| profileMigrationSource() | Migration tool | source snapshot/ref | SourceProfile | MigrationSourceProfiled |
| executeMigrationDryRun() | Migration service | plan/version; snapshot; sandbox | MigrationRun | MigrationDryRunCompleted |
| reconcileMigrationRun() | Validation/Data | migration run; reconciliation profile | MigrationReconciliation | MigrationReconciled |
| approveMigrationCutover() | System Owner/QA | final run; reconciliation; deviations; signature | MigrationAcceptance | MigrationAccepted |
| verifyLegacyRecordTrace() | Inspection test | legacy_id | LegacyTraceResult | LEGACY_TRACE_MISSING |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `migration_validation_plan` | 7 | PostgreSQL (GxP Core, authoritative) |
| `migration_run` | 5 | PostgreSQL (GxP Core, authoritative) |
| `migration_reconciliation` | 1 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (4):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /validation/v1/migrations/plans` | yes | — |
| `POST /validation/v1/migrations/runs` | yes | — |
| `POST /validation/v1/migrations/{id}/reconcile` | yes | — |
| `POST /validation/v1/migrations/{id}/approve` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (4):
| Event type | Producer | Dedupe key |
|---|---|---|
| `MigrationSourceProfiled` | SPEC-VAL-009 | event_id |
| `MigrationDryRunCompleted` | SPEC-VAL-009 | event_id |
| `MigrationReconciled` | SPEC-VAL-009 | event_id |
| `MigrationAccepted` | SPEC-VAL-009 | event_id |

UI SURFACES:
- Migration Plan
- Source Profile
- Dry Runs
- Reconciliation
- Cutover
- Legacy Trace

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- duplicate legacy ID
- timezone conversion
- historic signature
- missing attachment
- quantity mismatch
- rejected record
- final delta
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-14/Document_87_SPEC-VAL-009_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-VAL-009/<test_case_id>/`.
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
