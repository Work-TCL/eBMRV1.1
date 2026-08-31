# US eBMR / eDHR Regulated Manufacturing Platform
## Document 47 — Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EDGE-005  
**Parent Documents:** Documents 01–42  
**Primary Dependencies:** Documents 11, 38–46; GxP Mutation Gateway; Review/Release; Historian  
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

Define how machine/PLC/SCADA signals are mapped into regulated manufacturing evidence, how high-frequency telemetry is separated from GxP records, how batch context is bound, and how any future machine command path is strictly allowlisted and validated.

# 2. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| MAP-FR-001 | Machine source master | Define machine/PLC/SCADA source identity, equipment link, protocol connector and site/line. | Canonical source. |
| MAP-FR-002 | Tag/point mapping | Versioned mapping from native tag/node/register/topic to domain parameter/evidence code. | Stable semantics. |
| MAP-FR-003 | Mapping lifecycle | Draft, engineering test, review, released/effective, superseded/suspended. | Controlled configuration. |
| MAP-FR-004 | Type validation | Mapping defines native type, expected type, parsing and null/invalid handling. | No implicit casts. |
| MAP-FR-005 | Engineering units | Raw unit, canonical unit and approved conversion reference. | Reproducible. |
| MAP-FR-006 | Scale/offset | Scaling defined explicitly; test vectors required. | No hidden conversion. |
| MAP-FR-007 | Quality mapping | Native quality/status to canonical quality mapping versioned. | Integrity. |
| MAP-FR-008 | Timestamp semantics | Choose source/server/gateway timestamp usage and freshness thresholds by point. | Time clarity. |
| MAP-FR-009 | Sampling strategy | Poll/subscription/event-only/deadband/aggregation semantics explicit. | Acquisition behavior. |
| MAP-FR-010 | Deadband | Engineering deadband may reduce telemetry but cannot suppress events required as regulated evidence. | Completeness. |
| MAP-FR-011 | Aggregation | High-frequency raw data may aggregate min/max/avg/end/event window only under approved rule, with raw evidence retention policy. | Scalable evidence. |
| MAP-FR-012 | Batch context binding | Mapping can bind observation to active batch/step/operation by server-issued context token or deterministic line state. | Correct association. |
| MAP-FR-013 | No heuristic batch assignment | Do not guess batch solely from time proximity when explicit context is required. | Trace. |
| MAP-FR-014 | Evidence rule | Define which observations become GxP step results, process evidence, alarms, EM events or historian-only telemetry. | Clear data ownership. |
| MAP-FR-015 | Alarm mapping | Machine alarms mapped to severity/event code and batch/equipment impact rule. | Exception handling. |
| MAP-FR-016 | State mapping | Machine state/run/idle/fault/changeover may feed execution timeline but does not independently transition GxP batch state unless approved orchestration rule does. | Authority boundary. |
| MAP-FR-017 | Setpoint vs actual | Store/map setpoint and measured actual separately. | Evidence clarity. |
| MAP-FR-018 | Command profile | Machine commands defined as allowlisted operation with typed parameters, target, preconditions, authorization, signature, timeout and read-back verification. | Safe commands. |
| MAP-FR-019 | Command disabled default | No generic tag/register write endpoint exposed to normal UI/API. | Security. |
| MAP-FR-020 | Local interlock | Command execution requires PLC/machine local safety/interlock; software never bypasses physical control logic. | Safety. |
| MAP-FR-021 | Command correlation | Command ID links request, approval, machine write, acknowledgement/read-back and resulting evidence. | Trace. |
| MAP-FR-022 | Command failure | Timeout/readback mismatch produces failure/hold/deviation according to profile, not optimistic success. | Fail safe. |
| MAP-FR-023 | SCADA integration | Existing SCADA may remain visualization/control system; eBMR consumes approved data/events through Edge. | Brownfield friendly. |
| MAP-FR-024 | Historian integration | Raw/high-frequency data can be persisted in historian/time-series and referenced by evidence manifest/checksum. | Scale. |
| MAP-FR-025 | Evidence window | For critical operation, capture pre/during/post time window or cycle dataset reference according to mapping. | Context. |
| MAP-FR-026 | Cycle/batch summary | Machine cycle produces summary with cycle ID, start/end, parameters, alarms and raw evidence reference. | Sterile/device/process. |
| MAP-FR-027 | Mapping change impact | Change mapping requires Change Control/validation impact when GxP-relevant; open batches keep issued mapping version. | Validated state. |
| MAP-FR-028 | Commissioning | Engineering test/simulation path clearly separated from production GxP data. | No test contamination. |
| MAP-FR-029 | Data replay | Historian/backfill replay tagged and idempotent; cannot silently appear as live data. | Semantics. |
| MAP-FR-030 | Review-by-exception | Out-of-limit machine data, alarms, gaps, manual fallback and mapping changes visible in QA review. | Quality awareness. |
| MAP-FR-031 | Export | Inspection export can include machine evidence summary plus source file/reference/hash. | Reproducible. |
| MAP-FR-032 | Performance | Millions of telemetry points/day do not require millions of Frappe rows; appropriate storage tiers enforced. | Scale. |

# 3. Claude Code Function Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| releaseSignalMapping() | Integration Engineer + QA/Validation | mapping_draft_id; signatures | Mapping tested; test vectors pass; change/validation approvals complete | Vault-releases mapping; marks effective date; publishes config event | ReleasedSignalMapping | SignalMappingReleased; MAPPING_VALIDATION_INCOMPLETE |
| resolveBatchContext() | Integration Gateway | gateway/device/line; context token or active-operation reference; observation | Context binding policy configured | Validates server-issued context token or deterministic operation relation; no loose guess | BatchContext\|null | BATCH_CONTEXT_AMBIGUOUS |
| evaluateEvidenceRouting() | Integration Gateway | observation; released mapping | Mapping effective; quality/time known | Routes to historian-only, step result candidate, equipment event, EM event, alarm, cycle evidence | EvidenceRouteDecision | EvidenceRouted; MAPPING_NOT_EFFECTIVE |
| createStepResultCandidate() | Integration Gateway | observation; batch/step context; parameter mapping | Batch step expects parameter; source allowed; freshness/quality acceptable | Builds command for Mutation Gateway; does not write batch DB directly | GxPCommandEnvelope | StepResultCandidateCreated; SOURCE_NOT_ALLOWED/FRESHNESS_FAILED |
| createMachineAlarmEvent() | Integration Gateway | alarm observation; mapping | Alarm code mapping exists | Builds equipment/batch quality event with severity and source evidence | AlarmEventCommand | MachineAlarmDetected |
| buildCycleEvidenceManifest() | Cycle aggregator | cycle_id; observation/event refs; start/end; profile | Cycle complete or checkpoint; evidence refs available | Creates immutable manifest with hashes/statistics/raw refs/mapping version | CycleEvidenceManifest | CycleEvidenceCreated |
| submitApprovedMachineCommand() | GxP service | command_profile_id; target; typed params; actor/signature/context | Command profile effective; policy+SoD+signature; batch/equipment state valid | Creates command request and sends to Edge with command_id | CommandRequestReceipt | MachineCommandRequested; COMMAND_NOT_ALLOWED |
| executeMachineCommandAtEdge() | Edge command handler | command_id; signed request; target; params | Gateway/site/expiry/signature valid; local allowlist/interlock; connector writable | Executes driver write/method; optional readback; logs raw native response | EdgeCommandReceipt | MachineCommandExecuted/COMMAND_INTERLOCK_DENIED |
| finalizeMachineCommand() | GxP Integration service | EdgeCommandReceipt | Matches pending command; not expired; readback rules satisfied | Stores authoritative command outcome/audit; triggers batch/equipment event | MachineCommandOutcome | MachineCommandCompleted/READBACK_MISMATCH |
| replayHistoricalEvidence() | Integration Admin | evidence IDs/time range; reason; target mapping mode | Authorized; historical source retained | Tags BACKFILL/REPLAY; routes through idempotency; does not masquerade as live | ReplayJobReceipt | HistoricalReplayStarted |

# 4. Signal Mapping Object

```ts
type SignalMappingVersion = {
  mappingId: string;
  version: string;
  deviceId: string;
  sourceAddress: string;
  nativeType: string;
  domainCode: string;
  evidenceClass: "HISTORIAN_ONLY"|"STEP_RESULT"|"PROCESS_EVIDENCE"|"ALARM"|"EQUIPMENT_STATE"|"EM_RESULT"|"CYCLE_DATA";
  rawUnit?: string;
  canonicalUnit?: string;
  conversionRuleId?: string;
  qualityMappingId: string;
  timestampPolicy: string;
  freshnessPolicyId?: string;
  samplingPolicy: {
    mode: "POLL"|"SUBSCRIBE"|"EVENT";
    intervalMs?: number;
    deadband?: number;
  };
  batchContextPolicy: string;
  effectiveFrom: string;
  vaultObjectId: string;
};
```

# 5. Data Tiering

```text
PLC / Machine
     ↓
Edge
     ├── High-frequency raw → Historian / Time Series
     └── Relevant events/results → Integration Gateway
                                     ↓
                              GxP Mutation Gateway
                                     ↓
                            Batch/Equipment/EM/QC
```

GxP evidence can reference:
- historian query window;
- cycle file;
- content hash;
- mapping version;
- summarized min/max/avg;
- alarm list;
- exact critical result.

# 6. Batch Context

Preferred context binding:
1. batch/step issues an `operation_context_id`;
2. Integration Gateway registers active context for equipment/line;
3. observations arriving for mapping that requires context carry/resolve exact active context;
4. context start/end is audited;
5. ambiguity fails closed for step-result creation.

# 7. Command Profile

```ts
type MachineCommandProfile = {
  id: string;
  version: string;
  operationCode: string;
  allowedEquipmentClasses: string[];
  parameterSchema: object;
  requiredRoles: string[];
  signaturePolicyId?: string;
  allowedBatchStates: string[];
  timeoutMs: number;
  requiresReadback: boolean;
  localInterlockCode?: string;
  mappingVersion: string;
};
```

There is **no generic `/write-tag` production endpoint**.

# 8. Command Sequence

```text
Authorized UI / Domain Action
    ↓
Mutation Gateway authorization/rules/signature
    ↓
Command Request persisted
    ↓
Integration Gateway
    ↓
Edge authenticated command channel
    ↓
Local allowlist + interlock
    ↓
Protocol driver write/method
    ↓
Readback/native response
    ↓
Edge receipt
    ↓
GxP command outcome/audit
```

# 9. Historian / Time-Series Contract

Historian is evidence storage, not batch-state authority.

Evidence reference stores:
- historian instance;
- device/signal IDs;
- UTC start/end;
- mapping version;
- query/filter/aggregation rule;
- optional exported immutable file hash.

# 10. SCADA Boundary

Existing SCADA may continue:
- visualization;
- alarms;
- operator control;
- local automation.

eBMR receives approved evidence. It should not replace safety PLC/DCS interlocks.

# 11. Review-by-Exception Inputs

- alarm during critical step;
- source communication gap;
- bad/uncertain quality;
- manual fallback;
- out-of-limit signal;
- command failure/readback mismatch;
- mapping change affecting batch;
- clock uncertainty;
- missing cycle evidence.

# 12. Tests

- same signal on OPC UA and Modbus maps identically;
- ambiguous batch context blocks step result;
- signal late after batch close;
- historian unavailable;
- mapping superseded during active batch;
- backfill does not look live;
- alarm creates deviation rule;
- generic write endpoint absent;
- command wrong role/signature/state;
- local PLC interlock denies command;
- successful write but readback mismatch;
- retry command does not duplicate effect when device supports idempotency/command correlation.

# 13. Acceptance

A critical machine parameter for an active batch can be traced from native source address and raw evidence through mapping/version/context into the exact eBMR step result, while unrelated high-frequency telemetry remains outside Frappe/GxP transactional tables.

# 14. Claude Code Prohibitions

- Never infer batch context from nearest timestamp if policy requires explicit context.
- Never expose arbitrary PLC/register write API.
- Never let SCADA/PLC “batch complete” directly release GxP batch.
- Never copy millions of telemetry rows into Frappe.
- Never discard source mapping/version from stored regulated evidence.
