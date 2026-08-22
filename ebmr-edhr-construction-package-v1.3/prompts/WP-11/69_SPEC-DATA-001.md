# Claude Code prompt — WP-11 / Document 69: Enterprise Data Ownership, Persistence Topology & Data Lineage

TASK:
Implement the Enterprise Data Ownership, Persistence Topology & Data Lineage module (SPEC-DATA-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_69_Data_Ownership_Persistence_Topology_Lineage_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: DATA-FR-001..030 (30)
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
contracts/openapi/spec-data-001.yaml
contracts/events/spec-data-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-data-001/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| DATA-FR-001 | Authoritative-store registry | Every entity/data class has declared authoritative store/service owner and permitted projections. | No dual master. |
| DATA-FR-002 | PostgreSQL authority | Regulated GxP commands, record versions, signatures, audit, release/disposition, genealogy and other proprietary GxP state use PostgreSQL ownership. | Clear GxP truth. |
| DATA-FR-003 | MariaDB scope | Frappe/MariaDB owns UI/application metadata, Frappe users/config as applicable, DocTypes/projections and non-authoritative workflow conveniences. | Framework boundary. |
| DATA-FR-004 | Projection marking | Every Frappe/read/search projection declares source entity/version and rebuild mechanism. | No mistaken authority. |
| DATA-FR-005 | No cross-DB transaction assumption | No business invariant depends on atomic commit across PostgreSQL and MariaDB. | Distributed safety. |
| DATA-FR-006 | Postgres-first regulated mutation | Authoritative GxP state commits in PostgreSQL with audit/outbox; Frappe projection follows asynchronously or through explicit read-through. | Correct order. |
| DATA-FR-007 | Read path | UI may query Frappe projection for lists but must fetch authoritative detail/version for regulated action/signature where needed. | Freshness. |
| DATA-FR-008 | Staleness metadata | Projection exposes source version, projected_at and stale/degraded status. | Transparency. |
| DATA-FR-009 | Object-store ownership | Binary/raw evidence uses object storage; relational DB stores metadata/hash/links, not arbitrary large blobs by default. | Scale. |
| DATA-FR-010 | Historian ownership | High-frequency telemetry belongs in historian/time-series/Edge storage; GxP stores relevant evidence/result refs. | Tiering. |
| DATA-FR-011 | Search ownership | Search index is rebuildable projection and cannot determine official regulated value/state. | Search boundary. |
| DATA-FR-012 | Cache ownership | Cache is disposable and never sole source of permissions, signature target, release decision or regulated state. | Safe cache. |
| DATA-FR-013 | Temporal ownership | Temporal owns workflow execution history/coordination only; domain state belongs to GxP services. | Orchestration boundary. |
| DATA-FR-014 | NATS ownership | NATS/JetStream owns transport state only; business event source is PostgreSQL outbox/event record. | Messaging boundary. |
| DATA-FR-015 | External systems | ERP/LIMS/IdP/SCADA authority follows integration ownership matrix; external IDs remain references. | Integration clarity. |
| DATA-FR-016 | Entity identity | Internal immutable UUID/ID persists independently of external IDs/names. | Stable identity. |
| DATA-FR-017 | Version semantics | Regulated mutable records use optimistic aggregate version; released versions immutable. | Concurrency. |
| DATA-FR-018 | Timestamps | Server UTC authoritative receipt/transaction times; source times retained separately. | Chronology. |
| DATA-FR-019 | Decimal values | Regulated numeric values/calculations use exact decimal representation and explicit UOM/rounding. | No float drift. |
| DATA-FR-020 | Tenant/site key | Authoritative records carry tenant and site scope where applicable and are indexed/authorized consistently. | Isolation. |
| DATA-FR-021 | Sensitive classification | PII/security/GxP/config data classes map to encryption/access/retention policies. | Data protection. |
| DATA-FR-022 | Retention metadata | Every data class has retention trigger, duration/profile, legal-hold behavior and archive/delete owner. | Lifecycle. |
| DATA-FR-023 | Deletion | Regulated/history records are not hard-deleted through generic CRUD; purge uses controlled retention service. | Integrity. |
| DATA-FR-024 | Migration provenance | Imported/migrated data stores source system/file, transformation version, checksum and migration batch. | Traceability. |
| DATA-FR-025 | Schema ownership | Only owning service migration package may alter its authoritative tables. | Service boundary. |
| DATA-FR-026 | Reporting | Analytics/reporting uses read replicas/read models/warehouse exports where possible; operational database is not unrestricted BI endpoint. | Performance/security. |
| DATA-FR-027 | Data dictionary | Machine-readable entity/field/owner/classification/retention dictionary generated and maintained. | Claude Code clarity. |
| DATA-FR-028 | Cross-store consistency | Projection/integration consistency is monitored and repairable from authoritative source. | Recoverability. |
| DATA-FR-029 | Data lineage | Critical result can identify source record/version, transformation/rule and destination evidence. | Traceability. |
| DATA-FR-030 | Architecture enforcement | CI/lint/tests prevent forbidden repository/service direct access to another service's authoritative schema where feasible. | Guardrails. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| resolveDataOwner() | Any service/design tooling | entity_type; field/path? | DataOwnerDecision | DATA_OWNER_UNKNOWN |
| assertAuthoritativeWriteAllowed() | Repository/mutation layer | service_identity; entity_type; operation | WriteOwnershipDecision | FORBIDDEN_DATA_OWNER_WRITE |
| publishProjectionChange() | Authoritative service after commit | source_event_id; entity_type/id/version; projection payload/ref | ProjectionEvent | ProjectionUpdateRequested |
| getProjectionFreshness() | UI/read service | projection_type; entity_id | ProjectionFreshness | PROJECTION_STALE |
| rebuildProjection() | Projection worker/admin | projection_type; scope; source cutoff | ProjectionRebuildResult | ProjectionRebuilt |
| registerDataClass() | Data governance | entity/field; classification; retention; encryption profile | DataClassEntry | DataClassRegistered |
| recordMigrationProvenance() | Migration service | migration_batch; source; checksums; transformation version; destination refs | MigrationProvenance | MigrationProvenanceRecorded |
| verifyCrossStoreConsistency() | Scheduled/admin | projection/integration scope; source cutoff | ConsistencyReport | CrossStoreMismatchDetected |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `data_ownership_registry` | 9 | PostgreSQL (GxP Core, authoritative) |
| `projection_checkpoint` | 5 | PostgreSQL (GxP Core, authoritative) |
| `migration_batch` | 6 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (4):
| Operation | State-changing | Signature |
|---|---|---|
| `GET /platform/v1/data-ownership/{entityType}` | no | — |
| `GET /platform/v1/projections/{type}/{id}/freshness` | no | — |
| `POST /platform/v1/projections/{type}:rebuild` | yes | — |
| `GET /platform/v1/data-dictionary` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (5):
| Event type | Producer | Dedupe key |
|---|---|---|
| `ProjectionUpdateRequested` | SPEC-DATA-001 | event_id |
| `ProjectionRebuilt` | SPEC-DATA-001 | event_id |
| `ProjectionStaleDetected` | SPEC-DATA-001 | event_id |
| `CrossStoreMismatchDetected` | SPEC-DATA-001 | event_id |
| `MigrationProvenanceRecorded` | SPEC-DATA-001 | event_id |

UI SURFACES:
- Data Ownership Matrix
- Projection Health
- Data Dictionary
- Migration Provenance
- Cross-Store Consistency

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
- foreign service tries GxP write
- Frappe projection lags one version
- search rebuild
- cache loss
- external ID remap
- migration count/hash mismatch
- generic delete denied
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-11/Document_69_SPEC-DATA-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DATA-001/<test_case_id>/`.
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
