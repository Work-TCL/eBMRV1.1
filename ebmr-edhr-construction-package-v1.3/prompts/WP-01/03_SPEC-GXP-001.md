# Claude Code prompt — WP-01 / Document 03: GxP Mutation Gateway

TASK:
Implement the GxP Mutation Gateway module (SPEC-GXP-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_03_GxP_Mutation_Gateway_Specification_v1_1_IMPLEMENTATION_READY.md`
- Requirement IDs: MUT-FR-001..032 (32)
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

- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `services/gxp-api/src/modules/mutation` and its tests
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
services/gxp-api/src/modules/mutation/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/mutation/migrations/     # owned entities only
services/gxp-api/src/modules/mutation/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-gxp-001.yaml
contracts/events/spec-gxp-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-gxp-001/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| MUT-FR-001 | Single regulated mutation entry point | Every regulated create, modify, correct, approve, verify, release, reject, hold, resume, disposition, quality-state change and integration write shall enter through the GxP Mutation Gateway. Frappe generic CRUD, direct DB writes, background scripts and adapter | Architectural tests prove no supported bypass path. |
| MUT-FR-002 | Authenticated actor context | Resolve human, service, integration or device identity from trusted server-side authentication context. Ignore client-supplied actor IDs/names for authority decisions. | Spoofed actor fields do not change attribution. |
| MUT-FR-003 | Tenant/site scope enforcement | Resolve customer, legal entity, site and resource scope before business validation. Requests crossing tenant/site boundaries fail closed. | Cross-site negative tests enforced. |
| MUT-FR-004 | Command classification | Each mutation uses a versioned command type such as CompleteBatchStep, CorrectResult, ApproveDeviation, ReleaseBatch, UpdateMaterialStatus or AcceptLIMSResult. | Unknown/unversioned commands rejected. |
| MUT-FR-005 | Schema validation | Validate command envelope and payload against versioned JSON Schema/OpenAPI contract before domain processing. | Malformed/additional prohibited fields rejected. |
| MUT-FR-006 | Authorization decision | Call Policy/Authorization Service using subject, role, site, qualifications, resource state, requested action and SoD context. | Every regulated command has explicit allow/deny evidence. |
| MUT-FR-007 | Qualification/training gate | Where configured, confirm required current training, equipment qualification, area qualification or task competency before allowing action. | Expired qualification blocks action. |
| MUT-FR-008 | State-transition validation | Validate requested command against authoritative current state and allowed transition table; UI state is never authoritative. | Illegal transitions fail deterministically. |
| MUT-FR-009 | Expected-version concurrency | Require expected aggregate/record version for mutations. Reject stale commands using optimistic concurrency. | Two simultaneous conflicting writes cannot silently overwrite. |
| MUT-FR-010 | Idempotency | Require idempotency key for commands capable of duplicate submission. Persist key, actor/source, command hash and resulting receipt. | Retries return same result without duplicate regulated event. |
| MUT-FR-011 | Reason-for-change enforcement | Rules identify commands requiring controlled reason/comment. Reason is structured, required before commit and preserved in audit. | Correction/override cannot proceed without required reason. |
| MUT-FR-012 | Signature requirement determination | Determine whether electronic signature is required, signature meaning, required signer class and whether one or multiple signatures are required. | Signature need cannot be bypassed by client. |
| MUT-FR-013 | Signature challenge integration | If signature is required, produce/consume a challenge bound to command, record ID, expected version/hash, meaning and expiry. Commit only after valid signature proof. | Expired/stale challenge prevents commit. |
| MUT-FR-014 | Domain-rule evaluation | Execute applicable released rule/calculation versions for materials, equipment, limits, eligibility, sequence, QMS and release controls. | Rule result and version are persisted. |
| MUT-FR-015 | Authoritative PostgreSQL transaction | Persist domain state, new version, audit event and outbox message in one PostgreSQL transaction. | No state can commit without its audit/outbox companion. |
| MUT-FR-016 | Audit event creation | Create audit record with actor, UTC time, source, action, old/new representation or references, reason, signature, correlation and rule/software versions. | Each committed mutation has auditable event. |
| MUT-FR-017 | Record hash | Canonicalize resulting regulated record/version and calculate cryptographic digest where the record class requires integrity binding. | Receipt exposes algorithm + digest. |
| MUT-FR-018 | Transactional outbox | Write integration/domain event into outbox in the same transaction; external bus publishing occurs only after commit. | Bus outage cannot lose committed event. |
| MUT-FR-019 | Mutation receipt | Return immutable identifiers: command ID, aggregate ID, resulting version, audit event ID, signature ID if applicable, correlation ID and record hash where applicable. | Caller can reconcile exact outcome. |
| MUT-FR-020 | Projection update isolation | Frappe projection/read model updates occur asynchronously after authoritative commit and may be retried without altering regulatory truth. | Projection failure does not roll back valid GxP commit. |
| MUT-FR-021 | Failure classification | Return stable machine-readable error codes for authentication, authorization, stale version, state violation, missing signature, rule failure, validation, dependency unavailable and system fault. | Clients do not depend on free-text errors. |
| MUT-FR-022 | Fail closed for compliance dependencies | If authoritative DB, Signature Service for required signings, Policy Service or integrity-critical component is unavailable, mutation does not succeed. | No degraded-mode bypass. |
| MUT-FR-023 | Integration identity | ERP/LIMS/Edge commands use non-human identities with narrowly scoped permissions and source-system IDs. | Integration cannot impersonate a human signer. |
| MUT-FR-024 | Device/input source validation | For machine-originated mutations/evidence, verify registered source/device identity and mapping before acceptance. | Unknown device source rejected/quarantined. |
| MUT-FR-025 | Late/replayed command control | Detect timestamp/sequence anomalies and duplicate/replayed integration/device commands using source event IDs, sequences and idempotency. | Replay cannot duplicate consumption/result. |
| MUT-FR-026 | Controlled administrative mutation | Exceptional admin/data-repair actions require dedicated privileged command types, incident/change/deviation reference, stronger authorization and independent review. | No generic DBA correction process. |
| MUT-FR-027 | Correlation/causation | Every command and generated event carries request, correlation and causation identifiers across services and adapters. | End-to-end trace reconstruction possible. |
| MUT-FR-028 | Command retention | Retain sufficient command/receipt metadata for investigation, duplicate detection and validation evidence according to record class. | Historic mutation can be reconstructed. |
| MUT-FR-029 | No arbitrary execution | Command handlers shall call validated domain services; customer-provided Python/JavaScript is prohibited in authoritative mutation execution. | Code injection path absent. |
| MUT-FR-030 | Schema/version compatibility | Command handlers explicitly support/deprecate schema versions; semantic changes require new version and migration/compatibility assessment. | Existing validated clients do not silently change behavior. |
| MUT-FR-031 | Security-event interface | Repeated denied, replayed, malformed, privilege-escalation or suspicious mutations generate security monitoring events separate from GxP audit where appropriate. | Security monitoring receives actionable events. |
| MUT-FR-032 | Inspection/reconciliation support | Provide query by command ID/correlation ID/record to trace command → decision → signature → version → audit → outbox. | QA/validation can prove transaction chain. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (5 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `CommandReceipt` | 12 | PostgreSQL (GxP Core, authoritative) |
| `IdempotencyRecord` | 7 | PostgreSQL (GxP Core, authoritative) |
| `OutboxEvent` | 8 | PostgreSQL (GxP Core, authoritative) |
| `gxp_command_receipt` | 23 | PostgreSQL (GxP Core, authoritative) |
| `gxp_outbox` | 18 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (4):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /gxp/v1/commands/{commandType}` | yes | — |
| `GET /gxp/v1/commands/{commandId}/receipt` | no | — |
| `GET /gxp/v1/records/{type}/{id}/mutation-history` | no | — |
| `POST /gxp/v1/commands/{command_type}` | yes | — |

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
| Failure | Required behavior |
|---|---|
| PostgreSQL unavailable | No regulated mutation succeeds |
| Policy unavailable | Fail closed |
| Signature unavailable and signature required | Command remains uncommitted |
| Event bus unavailable | Authoritative commit succeeds if outbox commit succeeds; publish later |
| Frappe projection failure | Retry projection; GxP record remains valid |
| ERP callback failure | Mark integration pending and reconcile |
| Duplicate request | Return existing receipt |
| Stale version | Reject with current version reference |
| Worker crash after DB commit | Receipt recoverable; outbox continues |

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- unauthorized user
- wrong site
- expired qualification
- invalid state transition
- stale version
- duplicate click/retry
- duplicate ERP/LIMS callback
- missing reason
- missing required signature
- record changed after signature challenge
- signature service outage
- DB rollback
- outbox publisher outage
- projection outage
- concurrency on same batch step
- concurrency on same material reservation
- replayed Edge event
- privileged repair command
- command schema backward compatibility
- restart recovery after commit
- happy path
- authorization denial
- validation failure
- stale/concurrent write
- duplicate/replay where applicable
- dependency outage
- restart/recovery
- data integrity
- audit verification
- signature verification where applicable
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-01/Document_03_SPEC-GXP-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-GXP-001/<test_case_id>/`.
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
- Document 04–08 interfaces are reconciled
- command families for initial V1 modules are catalogued
- DB transaction proof-of-concept passes failure injection
- direct Frappe CRUD bypass tests fail as expected
- threat-model review covers Gateway trust boundary
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
