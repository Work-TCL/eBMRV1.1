# US eBMR / eDHR Regulated Manufacturing Platform
## Document 45 — Store-and-Forward, Offline Buffering, Time Integrity & Data Quality — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EDGE-003  
**Parent Documents:** Documents 01–42  
**Primary Dependencies:** Documents 43–44; Integration Gateway; Infrastructure/DR  
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

Define durable Edge buffering, outage recovery, acknowledgement, replay, time/freshness semantics and data-quality propagation so plant evidence is not lost or silently altered during network interruptions.

# 2. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
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

# 3. Claude Code Function Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| appendEnvelope() | Edge ingestion | envelope | event_id unique; storage healthy | BEGIN IMMEDIATE; insert outbox+hash+sequence; COMMIT | BufferedEnvelopeRef | BUFFER_DUPLICATE/BUFFER_STORAGE_FAILURE |
| selectForwardBatch() | Forwarder | max_count; max_bytes; now | No current send lock or safe concurrent selector | Selects earliest retry-eligible PENDING items ordered by sequence; marks IN_FLIGHT with attempt | ForwardBatch | none |
| sendBatch() | Forwarder | ForwardBatch | Upstream auth and network available | Serializes/compresses transport; sends; stores attempt metadata | ServerBatchAck | UPSTREAM_UNAVAILABLE/TIMEOUT |
| applyAck() | Forwarder | ServerBatchAck | Ack gateway ID valid; event IDs exist | Updates accepted/duplicate to ACKED; rejects to REJECTED_REVIEW; detects hash conflict | AckApplyResult | DELIVERY_ACKED/PAYLOAD_CONFLICT |
| recoverInFlight() | Startup | recovery_cutoff | DB integrity valid | Moves stale IN_FLIGHT without ack back to PENDING preserving attempt count | RecoveryResult | BufferRecovered |
| computeDiskPressure() | Health timer | filesystem stats; policy thresholds | Policy loaded | Computes NORMAL/WARN/CRITICAL/EMERGENCY | DiskPressureStatus | DiskPressureChanged |
| purgeAcked() | Retention job | retention_cutoff; max_rows | Only ACKED/PURGE_ELIGIBLE | Deletes eligible rows/files after evidence reference checks | PurgeResult | PURGE_BLOCKED_UNACKED |
| verifyBufferIntegrity() | Scheduled/support | range/time window | Storage readable | Recomputes hashes and sequence continuity | IntegrityReport | BUFFER_HASH_MISMATCH/SEQUENCE_GAP |
| replayRejected() | Integration Admin | event_id; reason; approved mapping/config context | Authorized; exact payload retained | Creates replay attempt of same event or controlled corrected mapping path without mutating original | ReplayReceipt | EdgeReplayRequested |
| storeEvidenceFile() | Instrument/file adapter | bytes/stream; metadata | Disk capacity; MIME/size policy | Writes content-addressed file; fsync; hashes; creates evidence manifest | EvidenceRef{sha256,path,size} | EVIDENCE_STORAGE_FAILURE |

# 4. Reference SQLite Schema

```sql
CREATE TABLE edge_outbox (
  event_id TEXT PRIMARY KEY,
  gateway_sequence INTEGER NOT NULL UNIQUE,
  schema_version TEXT NOT NULL,
  payload_json BLOB NOT NULL,
  payload_hash TEXT NOT NULL,
  state TEXT NOT NULL,
  created_at TEXT NOT NULL,
  first_sent_at TEXT,
  last_sent_at TEXT,
  acked_at TEXT,
  attempt_count INTEGER NOT NULL DEFAULT 0,
  next_attempt_at TEXT,
  rejection_code TEXT
);

CREATE INDEX idx_edge_outbox_send
ON edge_outbox(state, next_attempt_at, gateway_sequence);
```

Use WAL mode and synchronous setting selected through validated deployment profile.

# 5. Server Acknowledgement Contract

```json
{
  "gateway_id":"...",
  "batch_id":"...",
  "accepted":[{"event_id":"...","server_ref":"..."}],
  "duplicates":[{"event_id":"...","server_ref":"..."}],
  "rejected":[{"event_id":"...","code":"MAPPING_VERSION_UNKNOWN"}],
  "highest_contiguous_sequence":123456
}
```

The server shall not acknowledge an event before its durable intended server-side acceptance transaction is complete.

# 6. Data Freshness / Quality

Quality and freshness are different dimensions.

Example:
- source native GOOD + received 20 minutes late → quality may remain GOOD, freshness=LATE/STALE for process use.
- communication timeout → quality=COMM_ERROR.
- uncertain clock → clockQuality=UNCERTAIN even if numeric value is valid.

Downstream module decides whether late/stale evidence can satisfy a specific recipe/EM/QC requirement.

# 7. Outage Scenarios

## Cloud outage
Acquisition continues; local buffer grows; dashboard displays offline state.

## Gateway restart
SQLite recovers; `recoverInFlight()` returns uncertain sends to retry.

## Long outage / disk critical
Gateway raises critical alarm. It shall follow configured emergency policy, but must never silently discard unacknowledged regulated evidence. Site operating procedure may require process hold.

## Server rejects unknown mapping version
Item enters `REJECTED_REVIEW`; integration admin resolves config/mapping and replays exact evidence.

# 8. Server Idempotency Requirement

Server maintains unique `(gateway_id,event_id)` or equivalent constraint and payload hash.

Same event + same hash → duplicate accepted safely.  
Same event + different hash → integrity incident, not last-write-wins.

# 9. Observability

- edge_outbox_pending
- edge_outbox_rejected
- edge_oldest_pending_seconds
- edge_delivery_attempts_total
- edge_duplicate_acks_total
- edge_sequence_gap_total
- edge_disk_pressure_state
- edge_integrity_failures_total

# 10. Tests

Include abrupt power loss simulation, repeated resend, response timeout after server commit, duplicate ack, server reboot, sequence gaps, 72h synthetic outage, disk pressure and evidence-file corruption.

# 11. Acceptance

A server commit followed by lost network response must produce a duplicate retry that is idempotently acknowledged, with exactly one downstream GxP effect.

# 12. Claude Code Prohibitions

- Never delete PENDING/IN_FLIGHT evidence to free disk automatically.
- Never use at-most-once transport as evidence of no duplicates.
- Never overwrite source timestamp with receive timestamp.
- Never “fix” sequence gaps by renumbering records.
