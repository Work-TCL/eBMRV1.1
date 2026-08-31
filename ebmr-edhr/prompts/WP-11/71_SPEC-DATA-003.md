# Claude Code prompt — WP-11 / Document 71: Frappe / MariaDB Operational Database, Projection & UI Data Architecture

TASK:
Implement the Frappe / MariaDB Operational Database, Projection & UI Data Architecture module (SPEC-DATA-003) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_71_Frappe_MariaDB_Operational_Projection_UI_Data_Architecture_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: MDB-FR-001..028 (28)
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
- `infrastructure` and its tests
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
infrastructure/src/            # domain services, command handlers, repositories
infrastructure/migrations/     # owned entities only
infrastructure/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-data-003.yaml
contracts/events/spec-data-003/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-data-003/
```

REQUIREMENTS TO IMPLEMENT (28):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| MDB-FR-001 | Frappe DB boundary | MariaDB contains Frappe framework state/DocTypes/config/projections only according to ownership registry. | Boundary. |
| MDB-FR-002 | No GxP authority | Released batch/QC/release/signature/audit truth is never authoritative solely in MariaDB. | Core integrity. |
| MDB-FR-003 | Projection DocTypes | Projection DocTypes include authoritative_source_id/version/projected_at/status. | Trace. |
| MDB-FR-004 | Projection update | Updates originate from events/API projection worker, not manual operator edits. | Consistency. |
| MDB-FR-005 | Projection immutability | Fields sourced from GxP are read-only in Frappe forms and server hooks reject direct writes. | No UI bypass. |
| MDB-FR-006 | Frappe configuration | Non-regulated UI/config may use normal DocTypes; regulated configuration uses Vault/GxP release workflow where required. | Config classification. |
| MDB-FR-007 | User identity mapping | Frappe user/session mapping is projection/integration of identity, not independent authority for GxP permission. | IAM boundary. |
| MDB-FR-008 | Workflow | Frappe workflow may drive UX but server GxP state machine/policy remains authoritative. | No duplicate workflow truth. |
| MDB-FR-009 | Attachments | Regulated evidence attachment bytes routed to Evidence Store; Frappe stores controlled reference where possible. | Storage boundary. |
| MDB-FR-010 | Background jobs | Frappe jobs that mutate regulated state call GxP APIs; no direct PostgreSQL connection. | Service boundary. |
| MDB-FR-011 | Custom scripts | Client/server scripts cannot bypass APIs or evaluate arbitrary regulated business rules. | Security. |
| MDB-FR-012 | ERPNext optionality | ERPNext DocTypes only present/useful when adapter deployment includes ERPNext; GxP app remains functional without ERPNext. | Decoupling. |
| MDB-FR-013 | Indexes | Projection/list indexes optimized for UI filters/search; migration controlled via Frappe app. | Performance. |
| MDB-FR-014 | Large tables | Do not mirror millions of audit/telemetry rows into MariaDB; expose API/read model summary. | Scale. |
| MDB-FR-015 | Projection rebuild | Projection tables can be truncated/rebuilt in maintenance mode from authoritative source. | Recoverability. |
| MDB-FR-016 | Projection correction | Do not manually edit source-derived projection; repair source mapping/projector and replay. | Consistency. |
| MDB-FR-017 | Backup | MariaDB backed up because it contains operational/UI/config state even if regulated truth is elsewhere. | Continuity. |
| MDB-FR-018 | Restore order | After MariaDB restore, projection freshness/rebuild reconciles against current GxP source before service healthy. | Consistency. |
| MDB-FR-019 | Frappe migrations | Bench/app schema migrations versioned and run through controlled release. | SDLC. |
| MDB-FR-020 | Site config secrets | Secrets excluded from Frappe DB/site config where possible and referenced from secret manager. | Security. |
| MDB-FR-021 | Tenant deployment | Dedicated customer deployment may use one Frappe site/database or documented site topology; cross-customer DB mixing not assumed. | Isolation. |
| MDB-FR-022 | Audit supplement | Frappe Version/activity may support UX/support but is explicitly non-authoritative vs GxP Audit Ledger. | Clear semantics. |
| MDB-FR-023 | Projection lag | UI indicates syncing/stale state rather than showing stale value as current without context. | Transparency. |
| MDB-FR-024 | Transaction hooks | Frappe after_commit/event trigger does not create false distributed atomicity; projector is replay/idempotent. | Reliability. |
| MDB-FR-025 | Permissions | Frappe permissions supplement UI visibility, but Policy Service is mandatory for regulated API action. | Authorization. |
| MDB-FR-026 | Read-only database role | Reporting/support direct MariaDB roles restricted and not used to alter projection/source-derived fields. | Security. |
| MDB-FR-027 | Database health | Monitor replication/backup/storage/slow queries/job queues as deployment requires. | Operations. |
| MDB-FR-028 | No cross-engine joins | Application code does not rely on SQL joins between MariaDB and PostgreSQL. | Portability. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| applyGxPProjection() | Projection worker | source event/entity/version; projection DTO | ProjectionApplyResult | FrappeProjectionApplied; PROJECTION_VERSION_CONFLICT |
| rejectDirectProjectionMutation() | Frappe server hook/API | doctype/document changes; user context | Denied | PROJECTION_FIELD_READ_ONLY |
| rebuildFrappeProjection() | Admin/projector | projection type; scope; source cutoff | ProjectionRebuildResult | FrappeProjectionRebuilt |
| getProjectionStatus() | Frappe UI | entity/source ID | ProjectionStatus | PROJECTION_STALE |
| invokeGxPAction() | Frappe controller | operationId; DTO; AuthContext; idempotency/expected version | GxPActionReceipt | GXP_API_UNAVAILABLE |
| verifyMariaDBAfterRestore() | Recovery runbook | restore timestamp; projection checkpoints | MariaDBRecoveryReport | MARIADB_RECONCILIATION_REQUIRED |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (0 entities owned by this module):
_none declared in the source specifications_

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (1):
| Operation | State-changing | Signature |
|---|---|---|
| `GET /api/method/... projection status/admin operations` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (4):
| Event type | Producer | Dedupe key |
|---|---|---|
| `FrappeProjectionApplied` | SPEC-DATA-003 | event_id |
| `FrappeProjectionRebuilt` | SPEC-DATA-003 | event_id |
| `ProjectionStaleDetected` | SPEC-DATA-003 | event_id |
| `DirectProjectionMutationDenied` | SPEC-DATA-003 | event_id |

UI SURFACES:
- Projection Sync Status
- Frappe DB Health
- Projection Rebuild
- Stale Projection Indicators
- Frappe Migration History

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- A failed infrastructure dependency must produce an explicit degraded/unavailable result; no regulated operation may silently assume success.
- Recovery must preserve idempotency and version/concurrency rules.
- Data repair is performed through controlled tools/commands and evidence, not undocumented database modification.
- Any restore or failover that can affect regulated chronology/integrity requires validation checks before service is declared healthy.
- Background workers must resume from durable state rather than relying on process memory.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- manual edit projected batch state denied
- out-of-order event ignored
- projection rebuild after DB loss
- GxP API unavailable
- MariaDB restored older than PostgreSQL
- ERPNext absent deployment still functions
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-11/Document_71_SPEC-DATA-003_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DATA-003/<test_case_id>/`.
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
