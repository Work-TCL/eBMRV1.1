# US eBMR / eDHR Regulated Manufacturing Platform
## Document 43 — Edge Gateway Runtime Architecture & Construction Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EDGE-001  
**Parent Documents:** Documents 01–42  
**Primary Dependencies:** Documents 02–08, 11, 38–42; Security/Infrastructure; Integration Gateway  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products (DDCP)  
**Future Profiles:** Medical Devices, Pharmaceuticals  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This specification is intended to be consumed directly by Claude Code, Codex, or a human engineering team.

The coding agent **must not start implementation by interpreting headings loosely**. It shall first convert this document into:

1. requirement registry;
2. module/submodule map;
3. service/class/function catalogue;
4. explicit input/output contract for every public/domain function;
5. database ownership and transaction map;
6. API and event contract list;
7. module dependency graph;
8. state machines;
9. UI-to-API action map;
10. test and validation traceability map.

For every function/service operation defined in this document, implementation must preserve:

- function/operation name and purpose;
- caller/trigger;
- input fields, types, requiredness and source;
- authorization, qualification and signature preconditions;
- business-rule validation;
- database reads;
- database writes;
- transaction boundary;
- output/result;
- emitted events;
- downstream consumers;
- stable error codes;
- idempotency/replay handling;
- concurrency behavior;
- GxP audit evidence;
- observability;
- positive/negative/failure tests.

If a requirement is ambiguous in a way that changes regulated behavior, the coding agent shall create a `SPEC_GAP` issue and stop that affected implementation path rather than inventing a rule.

# Architectural Principles

- Edge and protocol code is **not** the GxP system of record.
- PostgreSQL GxP Core remains authoritative for regulated state.
- Edge systems acquire, normalize, buffer and forward source evidence.
- Frappe is presentation/application workflow, not industrial protocol acquisition.
- Raw high-frequency telemetry remains at Edge/historian/time-series/object storage as appropriate.
- GxP stores the relevant result/evidence reference, source identity, timestamp, quality, mapping version and checksum needed for intended use.
- All inbound industrial data uses versioned mapping/configuration.
- Commands to machines are disabled by default in V1 unless a specifically validated command profile authorizes them.
- No protocol driver writes directly to business/GxP tables.
- Device clocks are never silently trusted without clock-health metadata.
- Offline buffering preserves original order, source timestamps, hashes and delivery status.

# Current Protocol Baseline

The architecture is protocol-neutral, but reference drivers may support:

- OPC UA client connectivity using current OPC UA 1.05.x services/security profiles;
- Modbus TCP and Modbus RTU;
- MQTT 5.0;
- SNMP where appropriate for equipment/UPS/utility devices;
- serial/TCP proprietary adapters through isolated plugins;
- file/SFTP/REST integration for instruments that export evidence rather than live values.

OPC UA application certificates, SecureChannels and endpoint security policy are handled by the driver/security layer. MQTT broker/client authentication, TLS and topic authorization are likewise configuration-controlled.

Primary public references:
- https://reference.opcfoundation.org/specs/OPC-10000-4
- https://docs.oasis-open.org/mqtt/mqtt/v5.0/mqtt-v5.0.pdf
- https://opcfoundation.org/markets-collaboration/isa-95/

# 1. Objective

Define the plant-side Edge Gateway runtime that securely acquires industrial evidence, normalizes it, buffers it through outages, and forwards it to the central/local GxP services without becoming the GxP system of record.

# 2. Actors / Components

- Site/Plant Administrator
- Integration Engineer
- GxP Integration Service
- Edge Runtime Supervisor
- Protocol Connector Plugin
- Security/PKI Service
- Observability Platform
- QA/Validation Reviewer

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
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

# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| enrollGateway() | Installer / Site Admin | bootstrap_token:string; site_id:uuid; gateway_fingerprint:string; csr:PEM | Token valid, unused, scoped to site; fingerprint not already active | Server creates gateway identity; binds site; issues certificate metadata; audits enrollment | GatewayEnrollmentResult{gateway_id,cert_chain,config_endpoint,expires_at} | GatewayEnrolled; ENROLLMENT_TOKEN_INVALID/DUPLICATE_GATEWAY; tests token replay/site mismatch |
| loadRuntimeConfig() | Gateway startup / config refresh | config_version?:string | Gateway identity valid; signed config available | Fetches config; verifies signature/schema/plugin compatibility; no DB business writes | ValidatedGatewayConfig | ConfigFetched/ConfigRejected; CONFIG_SIGNATURE_INVALID/PLUGIN_UNSUPPORTED |
| activateRuntimeConfig() | Config manager | validated_config | No running transaction using incompatible mapping; rollback point available | Writes local config snapshot atomically; restarts affected connectors only; updates active_version | ActivationResult{active_version,restarted_connectors} | GatewayConfigActivated/ActivationFailed; test crash during activation |
| startConnector() | Supervisor | connector_id; connector_config_version | Plugin installed; secrets resolved; endpoint config valid | Starts isolated driver process/task; registers health state | ConnectorHandle/status | ConnectorStarted; CONNECTOR_START_FAILED |
| stopConnector() | Supervisor/Admin | connector_id; reason | Authorized operational action | Graceful stop; flushes plugin-local queues; persists status | StopResult | ConnectorStopped |
| ingestSourceObservation() | Protocol plugin | RawSourceObservation | Connector active; source mapping exists or configured quarantine path | Builds raw provenance; calls normalizeObservation; persists to durable queue before forwarding | EdgeObservationEnvelope | ObservationBuffered; SOURCE_MAPPING_NOT_FOUND |
| normalizeObservation() | Ingestion pipeline | raw_value:any; source_type; mapping_version | Mapping version effective; type/UOM mapping valid | Converts type/UOM; retains raw representation/hash; assigns quality/timestamps | NormalizedObservation | NORMALIZATION_FAILED/UOM_INCOMPATIBLE; golden mapping tests |
| appendDeliveryEnvelope() | Ingestion pipeline | EdgeObservationEnvelope | Local buffer writable; event_id unique | Transactional append to local outbox with sequence and hash | BufferedEnvelopeRef{event_id,seq} | BufferAppended; BUFFER_STORAGE_FAILURE |
| forwardPendingBatch() | Forwarder timer / connectivity restored | max_items:int; max_bytes:int | Upstream authenticated; no active backoff | Reads ordered pending rows; sends canonical batch; does not delete | ForwardResult{sent_event_ids,server_ack} | EdgeBatchSent; UPSTREAM_UNAVAILABLE |
| applyServerAck() | Forwarder | ack ranges/event IDs | Ack signed/authenticated and scoped to gateway | Marks exact items ACKED; schedules purge per retention | AckResult | EdgeDeliveryAcknowledged; ACK_UNKNOWN_EVENT |
| reportHealth() | Periodic timer | runtime metrics/connectors/storage/clock/certs | Gateway identity valid | Posts health snapshot; locally persists last result | HealthAck | GatewayHealthReported; HEALTH_POST_FAILED |
| evaluateClockHealth() | Periodic timer | system_time; ntp_status; source | Clock policy loaded | Calculates offset/uncertainty class; updates runtime clock_quality | ClockHealth{offset_ms,status} | ClockHealthChanged; tests NTP loss/skew |
| rotateGatewayCertificate() | Scheduled/Admin | gateway_id; CSR | Current identity valid; rotation authorized; expiry window/policy | Issues new cert; overlap period; switches outbound identity; revokes old after success | CertificateRotationResult | GatewayCertificateRotated; CERT_ROTATION_FAILED |
| installSignedUpdate() | Controlled deployment | artifact_ref; signature; expected_version; change_id | Approved release/change; artifact signature valid | Pulls staged image/plugin; verifies; health-checks; activates or rolls back | UpdateResult{old,new,status} | GatewaySoftwareUpdated/RolledBack; UPDATE_SIGNATURE_INVALID |
| quarantineConnector() | Security/health rule | connector_id; reason; evidence | Authorized rule/admin | Stops connector; blocks restart until reviewed; health status CRITICAL | QuarantineResult | ConnectorQuarantined |
| submitMachineCommand() | GxP Integration Gateway only | approved_command_profile; target; parameters; command_id | Feature enabled; command allowlisted; actor/policy/signature/local interlock valid | Routes to connector command API; records local execution evidence; never bypasses PLC safety | CommandExecutionReceipt | MachineCommandExecuted/Rejected; COMMAND_PROFILE_DISABLED/INTERLOCK_DENIED |

# 5. Canonical Edge Observation Contract

```ts
type EdgeObservationEnvelope = {
  schemaVersion: "1.0";
  eventId: string;                 // UUIDv7
  gatewayId: string;
  tenantId: string;
  siteId: string;
  connectorId: string;
  connectorVersion: string;
  deviceId: string;
  mappingId: string;
  mappingVersion: string;
  source: {
    protocol: "OPCUA"|"MODBUS_TCP"|"MODBUS_RTU"|"MQTT"|"SNMP"|"SERIAL"|"REST"|"FILE";
    address: string;
    nativeDataType?: string;
  };
  sourceTimestamp?: string;        // ISO-8601 UTC if supplied
  gatewayReceivedAt: string;
  gatewaySequence: number;
  clockQuality: {
    status: "GOOD"|"UNCERTAIN"|"BAD";
    offsetMs?: number;
    source?: string;
  };
  quality: "GOOD"|"UNCERTAIN"|"BAD"|"STALE"|"COMM_ERROR"|"CLOCK_UNCERTAIN";
  raw: {
    value: unknown;
    unit?: string;
    hash?: string;
  };
  normalized?: {
    value: string|number|boolean|null;
    unit?: string;
  };
  correlationId?: string;
  batchContext?: {
    batchId?: string;
    stepId?: string;
    operationId?: string;
  };
};
```

# 6. Edge Runtime State Model

```text
UNENROLLED
   ↓ enroll
ENROLLED
   ↓ config valid
CONFIGURED
   ↓ services started
RUNNING
   ├─→ DEGRADED
   ├─→ OFFLINE_UPSTREAM
   ├─→ DISK_PRESSURE
   ├─→ SECURITY_HOLD
   └─→ UPDATE_PENDING
RUNNING/DEGRADED → STOPPED
```

# 7. Local Persistence

Reference V1:
- SQLite in WAL mode for delivery/outbox metadata and configuration snapshots.
- Encrypted host/filesystem volume.
- Raw large instrument files stored as content-addressed files with SHA-256 and metadata rows.
- Database schema migrations version-controlled.
- No credentials in SQLite rows.

Suggested tables:
- `edge_gateway_state`
- `edge_config_snapshot`
- `edge_connector_state`
- `edge_outbox`
- `edge_delivery_attempt`
- `edge_health_snapshot`
- `edge_security_event`
- `edge_evidence_file`

`edge_outbox` fields:
```text
event_id text PK
gateway_sequence integer UNIQUE
schema_version text
payload_json blob/text
payload_hash text
state text
created_at text
first_sent_at text
acked_at text
attempt_count integer
next_attempt_at text
```

# 8. Server APIs

- `POST /edge/v1/enrollments`
- `GET /edge/v1/gateways/{gatewayId}/configuration`
- `POST /edge/v1/gateways/{gatewayId}/observations:batch`
- `POST /edge/v1/gateways/{gatewayId}/health`
- `POST /edge/v1/gateways/{gatewayId}/certificate-rotation`
- `POST /edge/v1/gateways/{gatewayId}/security-events`

Observation batch response includes accepted/duplicate/rejected event IDs and stable rejection codes.

# 9. Module Connections

```text
Protocol Driver (Doc 44)
        ↓ RawSourceObservation
Edge Runtime (Doc 43)
        ↓ canonical envelope
Store & Forward (Doc 45)
        ↓ authenticated batch
Integration Gateway
        ↓ mapping / validation
GxP Mutation Gateway
        ↓
Batch / Equipment / EM / Sterile / QC modules

Peripherals (Doc 46) ──→ Edge Runtime
PLC/SCADA Evidence Mapping (Doc 47) ──→ Integration Gateway
```

# 10. Security

- outbound-only preferred;
- TLS 1.2+ / approved enterprise profile;
- gateway workload certificate;
- protocol credentials scoped per connector;
- least-privilege OS account;
- rootless container where practical;
- no inbound SSH required for normal operation;
- signed images and SBOM;
- firewall rules documented;
- audit of privileged local support sessions where customer requires.

# 11. Observability

Metrics:
- connector_up;
- observations_received_total;
- observations_bad_quality_total;
- outbox_depth;
- oldest_unacked_age_seconds;
- disk_free_bytes;
- forwarding_latency;
- upstream_errors;
- clock_offset_ms;
- cert_expiry_days;
- restart_count.

# 12. Repository Structure

```text
edge/
├── runtime/
│   ├── supervisor/
│   ├── ingestion/
│   ├── normalization/
│   ├── forwarding/
│   ├── health/
│   ├── security/
│   └── config/
├── plugins/
├── storage/
├── contracts/
├── migrations/
├── cli/
└── tests/
```

# 13. Implementation Sequence

1. canonical contracts;
2. enrollment/identity;
3. config loader/activation;
4. connector supervisor;
5. observation ingestion/normalization;
6. SQLite outbox;
7. forwarding/ack/idempotency;
8. health/clock;
9. certificate rotation;
10. signed update/rollback;
11. command channel stub disabled by default;
12. soak/failure tests.

# 14. Mandatory Tests

- enrollment token replay;
- wrong tenant/site config;
- invalid config signature;
- connector crash while others continue;
- gateway reboot with pending buffer;
- duplicate server acknowledgements;
- upstream outage 24h/72h synthetic;
- disk full threshold;
- corrupted SQLite/outbox recovery strategy;
- clock offset > threshold;
- expired certificate;
- software update rollback;
- protocol plugin attempts forbidden filesystem access;
- command channel remains disabled without profile.

# 15. Acceptance Criteria

A disconnected plant gateway can acquire configured observations for the defined buffer horizon, survive restart, restore connectivity, resend in original sequence with no lost event IDs, and cause no duplicate GxP mutation.

# 16. Claude Code Prohibitions

- Do not put protocol-specific logic in GxP domain services.
- Do not delete unacknowledged buffer rows.
- Do not infer GOOD quality from missing quality metadata.
- Do not use client/browser time as authoritative.
- Do not make gateway database a customer master database.
- Do not enable machine write commands as a convenience feature.
