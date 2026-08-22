# Claude Code prompt — WP-11 / Document 75: Caching, Search, Read Models, Reporting Projections & Analytics Data Access

TASK:
Implement the Caching, Search, Read Models, Reporting Projections & Analytics Data Access module (SPEC-DATA-007) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_75_Caching_Search_Read_Models_Reporting_Analytics_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: READ-FR-001..030 (30)
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
contracts/openapi/spec-data-007.yaml
contracts/events/spec-data-007/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-data-007/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| READ-FR-001 | Read-model purpose | Caches/search/read models improve UX/reporting but are non-authoritative projections. | Boundary. |
| READ-FR-002 | Redis usage | Redis may store sessions, rate limits, ephemeral locks, cache entries and queues only where architecture permits. | Controlled cache. |
| READ-FR-003 | No GxP truth in Redis | No regulated state/signature/audit/release result exists only in Redis. | Durability. |
| READ-FR-004 | Cache key scope | Tenant/site/user/entity/version included where necessary to prevent cross-scope leakage. | Isolation. |
| READ-FR-005 | TTL | Every cache class has TTL/invalidation strategy; infinite cache of mutable regulated data prohibited. | Freshness. |
| READ-FR-006 | Cache stampede | Use bounded locking/single-flight/jitter where high-cost queries need it. | Stability. |
| READ-FR-007 | Cache invalidation | Authoritative event/version invalidates/updates cache; regulated action can bypass cache. | Correctness. |
| READ-FR-008 | Search engine optional | OpenSearch/Elasticsearch-compatible or database search provider is pluggable; product not hard-dependent on one commercial engine. | Portability. |
| READ-FR-009 | Search index fields | Index only allowed searchable fields; sensitive/PII excluded or restricted. | Privacy. |
| READ-FR-010 | Search authorization | Search query applies tenant/site/role/resource filters; result ID then re-authorized on fetch. | No information leakage. |
| READ-FR-011 | No index authority | Search state/status never used as final release/signature target without authoritative fetch/version validation. | Consistency. |
| READ-FR-012 | Index version | Indexed document carries source entity ID/version/projected_at. | Trace. |
| READ-FR-013 | Stale results | UI can show stale/indexing status and authoritative detail refresh. | Transparency. |
| READ-FR-014 | Index rebuild | Full index can be dropped/recreated from authoritative source or projections. | Recoverability. |
| READ-FR-015 | Read model | Complex dashboards use dedicated read models/materialized views rather than deep cross-domain synchronous joins. | Performance. |
| READ-FR-016 | Materialized view refresh | Refresh mode/cadence/cutoff visible and not used for current regulated decision if stale. | Correctness. |
| READ-FR-017 | Report snapshots | Official reports/management packages freeze source cutoff/version independently of live dashboards. | Reproducibility. |
| READ-FR-018 | Analytics warehouse | Optional warehouse/lake export is one-way governed projection, not authoritative GxP write path. | Data architecture. |
| READ-FR-019 | ETL/ELT lineage | Exports include source IDs/versions/cutoff and transformation version. | Lineage. |
| READ-FR-020 | Read replica | PostgreSQL replicas can support bounded reporting where staleness accepted. | Scale. |
| READ-FR-021 | List pagination | Cursor/keyset pagination preferred for large operational lists; bounded page size. | Performance. |
| READ-FR-022 | Filter allowlist | Search/list filter/sort fields explicitly allowlisted/indexed to prevent abusive arbitrary queries. | Resource safety. |
| READ-FR-023 | Export limits | Large exports asynchronous with source snapshot/cutoff, authorization and expiration. | Scale/security. |
| READ-FR-024 | Session cache | Session revocation/authorization-critical state cannot be indefinitely cached past revocation policy. | Security. |
| READ-FR-025 | Rule/config cache | Released rule/master caches keyed by exact version and immutable content hash where possible. | Safe cache. |
| READ-FR-026 | Negative cache | Missing/denied resource caching scoped carefully and short-lived to avoid stale authorization/data visibility. | Correctness. |
| READ-FR-027 | Cache outage | Application degrades to authoritative reads or explicit unavailable; must not fabricate data. | Resilience. |
| READ-FR-028 | Search outage | Core regulated execution remains available where architecture allows; search/list UX may degrade. | Resilience. |
| READ-FR-029 | Observability | Hit ratio, latency, evictions, memory, index lag, rebuild progress and query performance monitored. | Operations. |
| READ-FR-030 | No sensitive logs | Search queries/cache keys/logs avoid leaking secrets/patient sensitive content. | Security. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| getVersionedCacheEntry() | Application service | cache class; tenant/site; entity id/version | CacheResult | CACHE_MISS |
| invalidateEntityCache() | Event consumer | entity type/id/new version | InvalidationReceipt | CacheInvalidated |
| indexAuthoritativeProjection() | Search projector | entity projection; source version; allowed fields | IndexReceipt | SearchDocumentIndexed |
| authorizeSearchQuery() | Search API | AuthContext; query/filter/sort | AuthorizedSearchPlan | SEARCH_FILTER_NOT_ALLOWED |
| fetchSearchResultDetail() | UI/API | result entity ID; source version | AuthoritativeDetail | SEARCH_RESULT_STALE |
| rebuildSearchIndex() | Admin/projector | index type; source cutoff | SearchRebuildResult | SearchIndexRebuilt |
| refreshReadModel() | Read-model worker | model; source cutoff/checkpoints | ReadModelSnapshot | ReadModelRefreshed |
| generateAsyncExport() | Authorized user/report worker | report definition; filters; source cutoff | ExportJobResult | ExportGenerated |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `projection_document_metadata` | 4 | Redis / search / read models (rebuildable, NON-AUTHORITATIVE) |
| `read_model_checkpoint` | 4 | Redis / search / read models (rebuildable, NON-AUTHORITATIVE) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (4):
| Operation | State-changing | Signature |
|---|---|---|
| `GET /search/v1/...` | no | — |
| `POST /search/v1/indexes/{type}:rebuild` | yes | — |
| `POST /reports/v1/exports` | yes | — |
| `GET /platform/v1/read-models/{name}/status` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `SearchDocumentIndexed` | SPEC-DATA-007 | event_id |
| `SearchIndexRebuilt` | SPEC-DATA-007 | event_id |
| `ReadModelRefreshed` | SPEC-DATA-007 | event_id |
| `CacheInvalidated` | SPEC-DATA-007 | event_id |
| `ProjectionLagExceeded` | SPEC-DATA-007 | event_id |
| `ExportGenerated` | SPEC-DATA-007 | event_id |

UI SURFACES:
- Search
- Index Health
- Cache Health
- Read Model Freshness
- Async Exports
- Analytics Cutoff

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
- cross-tenant search
- stale search result then authoritative fetch
- Redis loss
- search engine outage
- rebuild with zero downtime alias switch
- large export authorization
- rule exact-version cache
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-11/Document_75_SPEC-DATA-007_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DATA-007/<test_case_id>/`.
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
