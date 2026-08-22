# Claude Code prompt — WP-01 / Document 05: Immutable Audit Ledger & Audit Review

TASK:
Implement the Immutable Audit Ledger & Audit Review module (SPEC-GXP-003) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_05_Immutable_Audit_Ledger_and_Audit_Review_Specification_v1_1_IMPLEMENTATION_READY.md`
- Requirement IDs: AUD-FR-001..030 (30)
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
- `services/gxp-api/src/modules/audit` and its tests
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
services/gxp-api/src/modules/audit/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/audit/migrations/     # owned entities only
services/gxp-api/src/modules/audit/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-gxp-003.yaml
contracts/events/spec-gxp-003/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-gxp-003/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| AUD-FR-001 | Independent audit ledger | GxP audit is a dedicated authoritative ledger separate from Frappe Version, application logs, Temporal history and SIEM logs. | Removing Frappe history does not remove GxP audit. |
| AUD-FR-002 | Automatic generation | Committed regulated mutations automatically generate audit events; users cannot choose whether an applicable event is audited. | No optional audit checkbox. |
| AUD-FR-003 | UTC timestamp | Each event receives authoritative server UTC time plus source/device timestamp metadata where relevant. | Browser clock irrelevant. |
| AUD-FR-004 | Actor attribution | Record human/service/device actor type, immutable subject/source ID and display/context metadata. | API/service actions distinguishable from humans. |
| AUD-FR-005 | Action semantics | Use stable event types: Created, Changed, Corrected, Signed, Approved, Released, StatusChanged, Consumed, Returned, IntegrationAccepted, etc. | Audit is understandable, not generic 'update'. |
| AUD-FR-006 | Old/new preservation | For changed regulated data preserve old and new values or immutable version references sufficient to reconstruct the change. | Previous information never obscured. |
| AUD-FR-007 | Changed field set | Record normalized changed fields for review/search without relying only on full JSON diff. | QA can filter changed critical parameters. |
| AUD-FR-008 | Reason linkage | Store mandatory reason/comment for controlled correction, override, manual replacement, admin repair and other policy-defined changes. | Reason retrievable with event. |
| AUD-FR-009 | Signature linkage | Audit event references signature ID(s) and meaning where action is signed. | Audit and signature reconcile. |
| AUD-FR-010 | Record/version linkage | Every event references aggregate/record and resulting version; where applicable record digest. | History order deterministic. |
| AUD-FR-011 | Correlation/causation | Persist request/correlation/causation IDs to connect UI command, background activity and integration side effects. | Investigation trace end-to-end. |
| AUD-FR-012 | Source attribution | Identify Frappe UI, REST API, ERP, LIMS, Edge, background system, migration or privileged repair source. | Source reports possible. |
| AUD-FR-013 | Software/rule version | Record product release and critical rule/calculation version used for action where relevant. | Historical decision reproducible. |
| AUD-FR-014 | Append-only application permissions | Application DB role may INSERT audit events and SELECT authorized records; no UPDATE/DELETE privilege for audit tables. | Privilege test enforced. |
| AUD-FR-015 | Partitioning without semantic loss | Time/tenant partitioning permitted for scale, but event IDs/order, retention and search remain consistent. | Partition maintenance cannot erase retained events. |
| AUD-FR-016 | Per-record hash chain | Regulated aggregate event streams include previous event hash/current event hash using canonical event representation. | Tampering detectable. |
| AUD-FR-017 | Integrity checkpoints | Periodically create signed integrity manifest/Merkle-style root or equivalent over audit ranges and store in immutable-capable storage. | Independent verification possible. |
| AUD-FR-018 | Integrity verification job | Scheduled process verifies chain/checkpoint consistency and alarms on mismatch/missing ranges. | Tamper issue not silent. |
| AUD-FR-019 | Privileged DB monitoring | DBA/cloud-admin access and extraordinary actions are monitored through independent infrastructure/security logs and controlled procedures. | DBA is not invisible. |
| AUD-FR-020 | Audit review UI | Authorized QA/auditor can filter by record, batch, user, event type, field, time, site, signature, source and reason. | Review does not require SQL. |
| AUD-FR-021 | Audit review annotations | If customer procedure requires documented audit-trail review, create separate review record/signature without changing the underlying audit events. | Audit event remains immutable. |
| AUD-FR-022 | Export | Generate human-readable and structured audit export tied to exact record/export manifest and integrity checks. | Inspection-ready. |
| AUD-FR-023 | Retention | Audit retained at least as long as associated regulated record policy; archival retains search/retrieval and integrity evidence. | No premature purge. |
| AUD-FR-024 | Legal/quality hold | Retention engine can suspend disposal/archive transitions for held records/events. | Held audit preserved. |
| AUD-FR-025 | Sensitive-data handling | Operational logs may redact sensitive values, but authorized GxP audit/evidence must preserve required content/meaning. Secrets must never be captured. | No credential leakage. |
| AUD-FR-026 | Migration audit | Migrated records include provenance/migration events and source checksums without pretending migrated events occurred natively. | Migration distinguishable. |
| AUD-FR-027 | Failed-action security trail | Policy-denied/replay/attack events may be sent to security ledger/SIEM; only failed actions with GxP significance need GxP audit according to risk/policy. | Avoid misleading committed-record audit. |
| AUD-FR-028 | Time ordering | Persist per-aggregate monotonic version/sequence and database commit order metadata where needed; source timestamp does not control authoritative order. | Late device data handled explicitly. |
| AUD-FR-029 | Backup/restore integrity | Restore procedure verifies audit record counts, hash checkpoints, references and signature linkage. | Restore qualification includes integrity. |
| AUD-FR-030 | No ordinary purge UI | Application users and admins cannot delete audit events via normal UI/API. Retention disposal, if ever permitted, is a separately controlled archival process based on applicable policy. | Deletion path controlled and testable. |

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

APIS (5):
| Operation | State-changing | Signature |
|---|---|---|
| `GET /audit/v1/records/{type}/{id}` | no | — |
| `GET /audit/v1/batches/{id}` | no | — |
| `GET /audit/v1/users/{subjectId}` | no | — |
| `GET /audit/v1/search?...` | no | — |
| `POST /audit/v1/exports` | yes | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- Record Audit Timeline
- Changed Values
- Signature Timeline
- Manual Overrides/Corrections
- Integration/Device Events
- Integrity Health
- Audit Review Record
- actor/source;
- authoritative time;
- action;
- old/new;
- reason;
- linked signature;
- linked record version;
- correlation chain.

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
If audit insert in the authoritative transaction fails, regulated mutation fails.
If integrity-checkpoint generation fails after prior audit events were committed, events remain valid but health alert is raised and checkpoint retried.
If audit read projection fails, authoritative ledger remains available through controlled fallback query.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- create/change/delete-like correction events
- previous value preservation
- reason
- signature link
- human vs integration identity
- event ordering
- late source timestamp
- attempted application UPDATE
- attempted application DELETE
- per-record hash tamper
- missing event tamper
- checkpoint verification
- partition rollover
- backup/restore
- archive/retrieve
- audit export
- role-restricted review
- privileged DB access monitoring
- migration provenance
- performance at target volume
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
- single-record histories with thousands of events
- tenant with millions/day
- batch audit query
- user/time-range query
- changed-field query
- archive export
- checkpoint generation
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-01/Document_05_SPEC-GXP-003_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-GXP-003/<test_case_id>/`.
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
