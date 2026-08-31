# Claude Code prompt — WP-06 / Document 45: Store-and-Forward, Offline Buffering, Time Integrity & Data Quality

TASK:
Implement the Store-and-Forward, Offline Buffering, Time Integrity & Data Quality module (SPEC-EDGE-003) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_45_Store_Forward_Offline_Buffering_Time_Data_Quality_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: BUF-FR-001..030 (30)
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
contracts/openapi/spec-edge-003.yaml
contracts/events/spec-edge-003/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-edge-003/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| BUF-FR-001 | Durable append | Canonical envelope is written durably before first upstream send. | No transient loss. |
| BUF-FR-002 | Sequence | Gateway assigns strictly monotonic local sequence within gateway identity. | Order trace. |
| BUF-FR-003 | Unique event | Event ID globally unique and immutable. | Idempotency. |
| BUF-FR-004 | Payload hash | Persist SHA-256 or approved digest of canonical payload. | Integrity. |
| BUF-FR-005 | WAL/recovery | Reference SQLite WAL startup integrity check and crash recovery. | Restart safe. |
| BUF-FR-006 | Delivery states | PENDING, IN_FLIGHT, ACKED, REJECTED_REVIEW, PURGE_ELIGIBLE. | Explicit. |
| BUF-FR-007 | Batch sending | Forward ordered batches bounded by count/bytes. | Efficient. |
| BUF-FR-008 | Acknowledgement | Server ack identifies exact event IDs/ranges and accepted/duplicate/rejected disposition. | Deterministic. |
| BUF-FR-009 | Retry | Unacknowledged items retry with exponential backoff/jitter. | Resilient. |
| BUF-FR-010 | Duplicate handling | Server duplicate ack considered delivered when payload hash matches same event ID. | Replay safe. |
| BUF-FR-011 | Conflict handling | Same event ID with different payload hash is security/data-integrity incident. | Tamper detection. |
| BUF-FR-012 | Network outage | Continue acquisition until configured local storage thresholds. | Continuity. |
| BUF-FR-013 | Disk watermarks | Warning/critical/emergency thresholds and alarms. | Capacity. |
| BUF-FR-014 | Purge | Only ACKED data beyond local retention may purge automatically. | No unacked deletion. |
| BUF-FR-015 | Large evidence | Large files use content-addressed store and separate manifest/outbox event. | Scale. |
| BUF-FR-016 | Clock metadata | Buffer never modifies source timestamp to make delayed data appear current. | Integrity. |
| BUF-FR-017 | Late data | Server receives source time and receive time; downstream rules decide applicability. | Controlled. |
| BUF-FR-018 | Freshness | Stale/late quality can be computed without deleting original observation. | Truth. |
| BUF-FR-019 | Gap detection | Gateway/server detect missing sequence ranges and report gap. | Completeness. |
| BUF-FR-020 | Rejected payload | Schema/mapping rejection retained for admin reconciliation; not silently dropped. | Recoverable. |
| BUF-FR-021 | Manual replay | Authorized admin can replay exact original envelope; replay reason/audit captured. | Controlled support. |
| BUF-FR-022 | Backfill | Bulk historical backfill uses same idempotency/validation but separately tagged BACKFILL. | Clear semantics. |
| BUF-FR-023 | Compression | Network batching/compression allowed without changing canonical hash semantics. | Efficiency. |
| BUF-FR-024 | Encryption | Local disk/volume encryption and TLS in transit. | Security. |
| BUF-FR-025 | Retention policy | Per site/evidence type local retention and max horizon configurable, but unacked purge forbidden. | Governed. |
| BUF-FR-026 | Integrity scan | Periodic check verifies payload hashes/content-addressed evidence. | Tamper detection. |
| BUF-FR-027 | Backup not required for transient buffer | Gateway buffer is resilient queue, not substitute for authoritative server backup; deployment may snapshot if needed. | Boundary. |
| BUF-FR-028 | Metrics | Depth, oldest pending age, send rate, retry rate, rejected count, disk usage. | Operations. |
| BUF-FR-029 | Power loss | Uncommitted records must not appear delivered; committed rows recover after abrupt power loss. | Crash consistency. |
| BUF-FR-030 | No order dependency assumption | Server uses event IDs/timestamps/sequence but business logic must tolerate late/out-of-order arrival when documented. | Distributed resilience. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| appendEnvelope() | Edge ingestion | envelope | BufferedEnvelopeRef | BUFFER_DUPLICATE/BUFFER_STORAGE_FAILURE |
| selectForwardBatch() | Forwarder | max_count; max_bytes; now | ForwardBatch | none |
| sendBatch() | Forwarder | ForwardBatch | ServerBatchAck | UPSTREAM_UNAVAILABLE/TIMEOUT |
| applyAck() | Forwarder | ServerBatchAck | AckApplyResult | DELIVERY_ACKED/PAYLOAD_CONFLICT |
| recoverInFlight() | Startup | recovery_cutoff | RecoveryResult | BufferRecovered |
| computeDiskPressure() | Health timer | filesystem stats; policy thresholds | DiskPressureStatus | DiskPressureChanged |
| purgeAcked() | Retention job | retention_cutoff; max_rows | PurgeResult | PURGE_BLOCKED_UNACKED |
| verifyBufferIntegrity() | Scheduled/support | range/time window | IntegrityReport | BUFFER_HASH_MISMATCH/SEQUENCE_GAP |
| replayRejected() | Integration Admin | event_id; reason; approved mapping/config context | ReplayReceipt | EdgeReplayRequested |
| storeEvidenceFile() | Instrument/file adapter | bytes/stream; metadata | EvidenceRef{sha256,path,size} | EVIDENCE_STORAGE_FAILURE |

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
- derive from the requirement table above
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-06/Document_45_SPEC-EDGE-003_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EDGE-003/<test_case_id>/`.
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
