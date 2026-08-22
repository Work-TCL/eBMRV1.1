# Claude Code prompt — WP-11 / Document 73: NATS / JetStream Event Bus, Transactional Outbox & Async Contracts

TASK:
Implement the NATS / JetStream Event Bus, Transactional Outbox & Async Contracts module (SPEC-DATA-005) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_73_NATS_JetStream_Transactional_Outbox_Async_Contracts_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: EVT-FR-001..030 (30)
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
contracts/openapi/spec-data-005.yaml
contracts/events/spec-data-005/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-data-005/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| EVT-FR-001 | Canonical event envelope | Every event has event_id, type, schema version, aggregate id/version, tenant/site, correlation/causation, occurred_at and payload. | Stable contract. |
| EVT-FR-002 | Transactional outbox | Authoritative GxP event inserted in same PostgreSQL transaction as domain state/audit. | Atomic source. |
| EVT-FR-003 | Outbox publisher | Publisher reads committed pending events and publishes to NATS/JetStream idempotently. | Reliable delivery. |
| EVT-FR-004 | Publish acknowledgement | Outbox marked published only after broker acknowledgement according to configured durable stream semantics. | No lost publish. |
| EVT-FR-005 | At-least-once consumers | Consumers assume duplicate delivery and must be idempotent. | Correct distributed model. |
| EVT-FR-006 | Consumer inbox/dedupe | Critical consumer maintains processed event IDs/result/version to prevent duplicate business effect. | Replay safe. |
| EVT-FR-007 | Subject naming | Versioned subject namespace includes environment/domain/event but avoids leaking sensitive data in subject names. | Operable. |
| EVT-FR-008 | Stream configuration | Durable streams define retention, storage, replicas, max age/size and permissions per event class. | Controlled messaging. |
| EVT-FR-009 | Consumer durability | Durable named consumers with explicit ack/retry/backoff for critical projections/integrations. | Recovery. |
| EVT-FR-010 | Dead letter strategy | Poison events moved/recorded for manual review after bounded attempts without deleting original event. | No loss. |
| EVT-FR-011 | Schema registry | JSON Schema/AsyncAPI event definitions versioned and CI compatibility-tested. | Contract governance. |
| EVT-FR-012 | Backward compatibility | Compatible additive changes preferred; breaking change uses new schema/event version and migration plan. | Safe evolution. |
| EVT-FR-013 | No sensitive payload excess | Event payload minimizes PII/secrets; sensitive content uses reference when possible. | Security. |
| EVT-FR-014 | Ordering | Per aggregate version ordering validated; consumers handle late/out-of-order events and reject stale projections. | Consistency. |
| EVT-FR-015 | No global ordering assumption | Architecture never assumes total order across all aggregates/services. | Scale. |
| EVT-FR-016 | Replay | Authorized stream/outbox replay uses event identity/version and does not re-execute non-idempotent business effect incorrectly. | Recovery. |
| EVT-FR-017 | Backfill tag | Bulk/projector rebuild may use source snapshot/events with explicit replay/backfill context. | Semantics. |
| EVT-FR-018 | Broker outage | Domain transaction still commits with outbox; publisher catches up after broker recovery. | Resilience. |
| EVT-FR-019 | Database outage | Publisher/consumer does not fabricate state; broker retention alone cannot commit GxP truth. | Boundary. |
| EVT-FR-020 | NATS auth | Service identities have publish/subscribe ACLs limited to required subjects. | Security. |
| EVT-FR-021 | TLS | NATS connections TLS/mTLS according to deployment profile. | Transport security. |
| EVT-FR-022 | Multi-tenant subjects | Dedicated deployment baseline still carries tenant/site in envelope; ACL/subject design prevents accidental cross-scope. | Isolation. |
| EVT-FR-023 | Large payload | Large files stay object store; event contains evidence ref/hash, not multi-MB blobs. | Scale. |
| EVT-FR-024 | Event retention | Broker retention chosen for operational replay, not regulatory long-term archive; authoritative event/audit/evidence retention remains elsewhere. | Boundary. |
| EVT-FR-025 | Observability | Outbox age, publish lag, stream lag, consumer ack pending, redelivery and DLQ monitored. | Operations. |
| EVT-FR-026 | Consumer failure policy | Business validation failure differs from transient dependency failure; poison event does not retry forever. | Stability. |
| EVT-FR-027 | Projection consumers | Projection worker stores source aggregate/event version and ignores duplicate/stale event safely. | Correct projection. |
| EVT-FR-028 | Integration consumers | ERP/LIMS/Edge integration commands derive from source event and own idempotency/reconciliation. | Integration safety. |
| EVT-FR-029 | Schema ownership | Event producer owns schema; consumers cannot reinterpret fields inconsistently. | Governance. |
| EVT-FR-030 | No event-sourcing assumption | The platform uses events/outbox for integration; not every domain aggregate is rebuilt solely from broker events unless explicitly specified. | Architecture clarity. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| appendDomainOutboxEvent() | Domain transaction | canonical event envelope | OutboxRef | OUTBOX_EVENT_APPENDED |
| claimOutboxBatch() | Outbox publisher | batch size; lease duration; now | OutboxBatch | none |
| publishOutboxEvent() | Publisher | outbox event; subject mapping | PublishReceipt | EVENT_PUBLISHED/BROKER_UNAVAILABLE |
| markOutboxPublished() | Publisher | outbox_id; publish receipt | void | OUTBOX_PUBLISH_STATE_CONFLICT |
| consumeEventIdempotently() | Consumer wrapper | event envelope; handler ID | ConsumerReceipt | EVENT_ALREADY_PROCESSED/HANDLER_FAILED |
| handlePoisonEvent() | Consumer supervisor | event; failure history; policy | DeadLetterRef | EventDeadLettered |
| replayConsumerEvents() | Integration Admin | consumer; event range/filter; reason | ReplayJob | EventReplayStarted |
| verifyEventSchemaCompatibility() | CI | old/new JSON schema/AsyncAPI | CompatibilityReport | EVENT_SCHEMA_BREAKING_CHANGE |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `gxp_outbox` | 11 | PostgreSQL transactional outbox (authoritative) / NATS JetStream (transport) |
| `consumer_inbox` | 5 | PostgreSQL transactional outbox (authoritative) / NATS JetStream (transport) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (0):
_none declared in the source specifications_

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `EventPublished` | SPEC-DATA-005 | event_id |
| `EventDeadLettered` | SPEC-DATA-005 | event_id |
| `EventReplayStarted` | SPEC-DATA-005 | event_id |
| `EventSchemaBreakingChangeDetected` | SPEC-DATA-005 | event_id |
| `ConsumerLagExceeded` | SPEC-DATA-005 | event_id |
| `OutboxLagExceeded` | SPEC-DATA-005 | event_id |

UI SURFACES:
- Event Stream Health
- Outbox Lag
- Consumer Lag
- Dead Letters
- Schema Registry
- Replay Jobs

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
- DB commit while NATS down
- publish ack lost then duplicate retry
- consumer crash after side effect before ack
- out-of-order aggregate version
- poison event
- schema additive change
- breaking schema blocked
- large evidence ref
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-11/Document_73_SPEC-DATA-005_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-DATA-005/<test_case_id>/`.
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
