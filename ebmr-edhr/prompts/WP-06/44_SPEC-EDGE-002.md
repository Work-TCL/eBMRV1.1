# Claude Code prompt — WP-06 / Document 44: Industrial Device & Protocol Connectivity / Driver Specification

TASK:
Implement the Industrial Device & Protocol Connectivity / Driver Specification module (SPEC-EDGE-002) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_44_Industrial_Device_Protocol_Connectivity_Drivers_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: DRV-FR-001..025 (25)
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
contracts/openapi/spec-edge-002.yaml
contracts/events/spec-edge-002/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-edge-002/
```

REQUIREMENTS TO IMPLEMENT (25):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| DRV-FR-001 | Driver interface | All protocol plugins implement common lifecycle/connect/read/subscribe/write-capability/health contract. | Uniform runtime. |
| DRV-FR-002 | OPC UA endpoint | Support endpoint discovery/configured URL, security policy/mode, certificate trust and user/application authentication. | Secure OPC UA. |
| DRV-FR-003 | OPC UA certificates | Application instance certificate and trusted/rejected certificate stores managed explicitly. | Identity. |
| DRV-FR-004 | OPC UA browse | Authorized engineering mode may browse namespaces/nodes for mapping; production mapping references exact NodeIds. | Stable mapping. |
| DRV-FR-005 | OPC UA subscriptions | Support monitored items, sampling/publishing interval, queue size and reconnect/resubscribe. | Efficient acquisition. |
| DRV-FR-006 | OPC UA status | Map UA StatusCode/source/server timestamps into canonical quality/time fields. | Quality preserved. |
| DRV-FR-007 | Modbus TCP | Support host/unit ID/function/register/type/endianness/scaling with bounded polling. | Common industrial. |
| DRV-FR-008 | Modbus RTU | Support serial port/baud/parity/stop bits/slave ID/register mapping and bus serialization. | Serial support. |
| DRV-FR-009 | Modbus invalid value | Timeout/CRC/exception/out-of-range marks BAD/COMM_ERROR; never substitute last good as current without STALE quality. | Integrity. |
| DRV-FR-010 | MQTT 5 | Support broker TLS/auth, topic filters, QoS policy, retained flag handling, payload schema/version and client session policy. | Message source. |
| DRV-FR-011 | MQTT payload validation | JSON/binary/custom payload decoded only through versioned decoder plugin/schema. | No arbitrary parsing. |
| DRV-FR-012 | SNMP | Support v3 preferred with scoped credentials, OID mapping and polling/trap profile where appropriate. | Utilities/UPS. |
| DRV-FR-013 | Generic TCP/serial | Custom proprietary protocol lives in isolated adapter with framing/checksum/test vectors. | Extensibility. |
| DRV-FR-014 | REST/file adapter | Support authenticated REST polling/webhook or controlled file import for instruments producing reports. | Instrument integration. |
| DRV-FR-015 | Connection retry | Exponential backoff/jitter with configured max and health state; avoid network storms. | Resilience. |
| DRV-FR-016 | Source rate limits | Per-device poll/subscription limits prevent overloading PLC/instrument. | Operational safety. |
| DRV-FR-017 | Read/write separation | Driver advertises read/write capability separately; runtime blocks write unless explicit command profile. | Safe default. |
| DRV-FR-018 | Mapping test | Engineering test reads source and displays raw/normalized preview without committing regulated result. | Safe commissioning. |
| DRV-FR-019 | Simulation | Provide deterministic simulator/mock driver for CI/validation. | Testability. |
| DRV-FR-020 | Driver version | Every observation carries driver/plugin version. | Reproducibility. |
| DRV-FR-021 | Reconnect sequence | After reconnect, driver resubscribes/restarts polling and emits gap/reconnect event. | Data-gap awareness. |
| DRV-FR-022 | Credential rotation | Connector secrets/certs can rotate without rewriting mapping. | Security. |
| DRV-FR-023 | Driver health | Connection state, last success, error count, latency and source-specific diagnostics. | Observability. |
| DRV-FR-024 | Protocol errors | Native errors normalized to stable driver error taxonomy while raw diagnostic retained. | Support. |
| DRV-FR-025 | Production configuration | Protocol mapping config released/versioned; ad-hoc runtime node/register edits prohibited. | Validated state. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| connect() | Edge supervisor | ConnectorConfig | ConnectionResult{session_id,capabilities} | DriverConnected; AUTH_FAILED/ENDPOINT_UNREACHABLE |
| disconnect() | Supervisor / shutdown | session_id; reason | void/DisconnectResult | DriverDisconnected |
| readOnce() | Commissioning or polling scheduler | SourceAddress; read_options | RawSourceObservation | READ_TIMEOUT/PROTOCOL_EXCEPTION |
| subscribe() | Subscription scheduler | SourceAddress[]; sampling/publishing config | SubscriptionHandle | SubscriptionCreated/SUBSCRIBE_FAILED |
| unsubscribe() | Config change/shutdown | subscription_id | void | SubscriptionRemoved |
| browse() | Engineering mapping UI | root/node; filters; continuation | BrowseResult[] | BROWSE_DENIED/BROWSE_FAILED |
| write() | Approved machine command only | SourceAddress; typed value; command context | DriverWriteReceipt | WRITE_DISABLED/WRITE_FAILED/READBACK_MISMATCH |
| healthCheck() | Periodic supervisor | session_id | DriverHealth | DriverHealthChanged |
| decodePayload() | MQTT/custom message callback | bytes; decoder_version; content_type | DecodedFields | PAYLOAD_SCHEMA_INVALID |
| mapNativeQuality() | Driver read/subscription | native status/error | CanonicalQuality | QUALITY_MAPPING_UNKNOWN |
| reconnect() | Supervisor after disconnect | connector_id; previous state | ReconnectResult | DriverReconnected/RECONNECT_FAILED |
| testMapping() | Engineering UI | mapping draft; one-shot source request | MappingPreview | MAPPING_TEST_FAILED |

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
- connect/auth failure
- malformed configuration
- read timeout
- reconnect
- bad native quality
- mapping conversion
- duplicate/replayed source event where detectable
- graceful shutdown
- secret redaction
- driver crash isolation
- protocol simulator test
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-06/Document_44_SPEC-EDGE-002_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EDGE-002/<test_case_id>/`.
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
