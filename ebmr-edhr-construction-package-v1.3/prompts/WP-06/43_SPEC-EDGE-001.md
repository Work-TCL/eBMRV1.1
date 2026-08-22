# Claude Code prompt — WP-06 / Document 43: Edge Gateway Runtime Architecture & Construction Specification

TASK:
Implement the Edge Gateway Runtime Architecture & Construction Specification module (SPEC-EDGE-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_43_Edge_Gateway_Runtime_Architecture_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: EDGE-FR-001..030 (30)
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
contracts/openapi/spec-edge-001.yaml
contracts/events/spec-edge-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-edge-001/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| EDGE-FR-001 | Gateway identity | Every gateway has immutable gateway ID, tenant/site assignment, host identity, certificate and lifecycle state. | No anonymous edge. |
| EDGE-FR-002 | Enrollment | New gateway enrollment requires one-time bootstrap token or administrator-approved enrollment and results in device certificate/workload identity. | Controlled onboarding. |
| EDGE-FR-003 | Site isolation | Gateway configuration and outbound data are bound to one authorized tenant/site deployment context unless an explicitly approved multi-site design exists. | No cross-tenant leakage. |
| EDGE-FR-004 | Configuration versions | Connector, mapping, certificate, buffering and forwarding configuration is immutable/versioned; gateway applies exact approved config version. | Reproducible runtime. |
| EDGE-FR-005 | Config validation | Gateway validates schema, signatures/checksum, supported plugin versions and contradictory settings before activation. | Bad config rejected. |
| EDGE-FR-006 | Atomic config activation | New configuration activates atomically; on failure gateway retains prior valid configuration and reports failure. | No half-configured runtime. |
| EDGE-FR-007 | Connector supervision | Gateway starts/stops/restarts drivers under supervisor and isolates crashing connector from other connectors. | Fault containment. |
| EDGE-FR-008 | Plugin sandbox boundary | Protocol plugins expose fixed adapter interfaces and cannot access GxP database credentials or unrestricted filesystem/secrets. | Security boundary. |
| EDGE-FR-009 | Observation envelope | All readings/events normalize into canonical EdgeObservationEnvelope before buffering/forwarding. | Common downstream contract. |
| EDGE-FR-010 | Source provenance | Envelope carries gateway, connector, device, source address/tag/node/register, mapping version and source event identity. | Traceable source. |
| EDGE-FR-011 | Timestamp model | Envelope carries source timestamp, gateway receive timestamp, UTC normalization and clock-quality metadata. | Chronology explicit. |
| EDGE-FR-012 | Data quality | Every observation includes quality/status such as GOOD, UNCERTAIN, BAD, STALE, COMM_ERROR, CLOCK_UNCERTAIN, MANUAL_FALLBACK. | No silent bad data. |
| EDGE-FR-013 | Canonical units | Mappings may convert source units to canonical units only through versioned conversion rule; raw source value/unit retained where required. | Reproducibility. |
| EDGE-FR-014 | Local buffering | Every forward-required observation/event is durably buffered before network transmission according to Document 45. | Loss resistance. |
| EDGE-FR-015 | Delivery acknowledgement | Gateway removes/archives delivery item only after authoritative server acknowledgement of exact event ID/range. | At-least-once safe. |
| EDGE-FR-016 | Idempotency | Globally unique event ID + gateway sequence prevents duplicate GxP effects during retries. | Replay safe. |
| EDGE-FR-017 | Health reporting | Gateway reports host, storage, buffer age/depth, connector status, clock health, certificate expiry, CPU/memory and version. | Operable. |
| EDGE-FR-018 | Local health UI/API | Authorized support can inspect status/config version without exposing secrets or modifying regulated mapping casually. | Supportable. |
| EDGE-FR-019 | Remote update | Software/plugin update is signed/versioned, change-controlled and supports rollback; no auto-update of validated production gateways by default. | Controlled SDLC. |
| EDGE-FR-020 | Certificate rotation | Rotate gateway/client certificates before expiry without changing gateway identity. | Secure lifecycle. |
| EDGE-FR-021 | Secrets | Secrets stored via OS/key store/secret file with restrictive permissions; never committed in config repo or logs. | Credential safety. |
| EDGE-FR-022 | Network segmentation | Gateway supports industrial-side and enterprise/cloud-side network interfaces with outbound-only preferred architecture. | Reduced attack surface. |
| EDGE-FR-023 | Command channel | Inbound machine command channel disabled by default; enabled only for explicit approved command profiles with allowlist and local safety interlocks. | Safe default. |
| EDGE-FR-024 | Local continuity | If upstream unavailable, acquisition and buffer continue while disk capacity policy permits. | Plant resilience. |
| EDGE-FR-025 | Disk pressure | Buffer thresholds trigger warning/critical alarms and documented degradation policy; silent data deletion prohibited. | Capacity safety. |
| EDGE-FR-026 | Clock health | Gateway monitors NTP/PTP/system clock offset; degraded clock marks data quality rather than rewriting source time silently. | Time integrity. |
| EDGE-FR-027 | Audit/config history | Gateway/server preserve enrollment, config activation, plugin update, certificate rotation and security-relevant runtime events. | Inspection/support trace. |
| EDGE-FR-028 | Observability | Structured logs, metrics and traces use correlation IDs and redact credentials/raw secrets. | Operations. |
| EDGE-FR-029 | Container deployment | Reference deployment supports signed container images/systemd/container runtime with restart policy and health probes. | Repeatable deployment. |
| EDGE-FR-030 | No local business truth | Gateway never independently marks batch step, QC result, equipment calibration or product release as complete. | Trust boundary. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| enrollGateway() | Installer / Site Admin | bootstrap_token:string; site_id:uuid; gateway_fingerprint:string; csr:PEM | GatewayEnrollmentResult{gateway_id,cert_chain,config_endpoint,expires_at} | GatewayEnrolled; ENROLLMENT_TOKEN_INVALID/DUPLICATE_GATEWAY; tests token replay/site misma |
| loadRuntimeConfig() | Gateway startup / config refresh | config_version?:string | ValidatedGatewayConfig | ConfigFetched/ConfigRejected; CONFIG_SIGNATURE_INVALID/PLUGIN_UNSUPPORTED |
| activateRuntimeConfig() | Config manager | validated_config | ActivationResult{active_version,restarted_connectors} | GatewayConfigActivated/ActivationFailed; test crash during activation |
| startConnector() | Supervisor | connector_id; connector_config_version | ConnectorHandle/status | ConnectorStarted; CONNECTOR_START_FAILED |
| stopConnector() | Supervisor/Admin | connector_id; reason | StopResult | ConnectorStopped |
| ingestSourceObservation() | Protocol plugin | RawSourceObservation | EdgeObservationEnvelope | ObservationBuffered; SOURCE_MAPPING_NOT_FOUND |
| normalizeObservation() | Ingestion pipeline | raw_value:any; source_type; mapping_version | NormalizedObservation | NORMALIZATION_FAILED/UOM_INCOMPATIBLE; golden mapping tests |
| appendDeliveryEnvelope() | Ingestion pipeline | EdgeObservationEnvelope | BufferedEnvelopeRef{event_id,seq} | BufferAppended; BUFFER_STORAGE_FAILURE |
| forwardPendingBatch() | Forwarder timer / connectivity restored | max_items:int; max_bytes:int | ForwardResult{sent_event_ids,server_ack} | EdgeBatchSent; UPSTREAM_UNAVAILABLE |
| applyServerAck() | Forwarder | ack ranges/event IDs | AckResult | EdgeDeliveryAcknowledged; ACK_UNKNOWN_EVENT |
| reportHealth() | Periodic timer | runtime metrics/connectors/storage/clock/certs | HealthAck | GatewayHealthReported; HEALTH_POST_FAILED |
| evaluateClockHealth() | Periodic timer | system_time; ntp_status; source | ClockHealth{offset_ms,status} | ClockHealthChanged; tests NTP loss/skew |
| rotateGatewayCertificate() | Scheduled/Admin | gateway_id; CSR | CertificateRotationResult | GatewayCertificateRotated; CERT_ROTATION_FAILED |
| installSignedUpdate() | Controlled deployment | artifact_ref; signature; expected_version; change_id | UpdateResult{old,new,status} | GatewaySoftwareUpdated/RolledBack; UPDATE_SIGNATURE_INVALID |
| quarantineConnector() | Security/health rule | connector_id; reason; evidence | QuarantineResult | ConnectorQuarantined |
| submitMachineCommand() | GxP Integration Gateway only | approved_command_profile; target; parameters; command_id | CommandExecutionReceipt | MachineCommandExecuted/Rejected; COMMAND_PROFILE_DISABLED/INTERLOCK_DENIED |

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
| `POST /edge/v1/enrollments` | yes | — |
| `GET /edge/v1/gateways/{gatewayId}/configuration` | no | — |
| `POST /edge/v1/gateways/{gatewayId}/observations:batch` | yes | — |
| `POST /edge/v1/gateways/{gatewayId}/health` | yes | — |
| `POST /edge/v1/gateways/{gatewayId}/certificate-rotation` | yes | — |
| `POST /edge/v1/gateways/{gatewayId}/security-events` | yes | — |

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
- enrollment token replay
- wrong tenant/site config
- invalid config signature
- connector crash while others continue
- gateway reboot with pending buffer
- duplicate server acknowledgements
- upstream outage 24h/72h synthetic
- disk full threshold
- corrupted SQLite/outbox recovery strategy
- clock offset > threshold
- expired certificate
- software update rollback
- protocol plugin attempts forbidden filesystem access
- command channel remains disabled without profile
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-06/Document_43_SPEC-EDGE-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EDGE-001/<test_case_id>/`.
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
