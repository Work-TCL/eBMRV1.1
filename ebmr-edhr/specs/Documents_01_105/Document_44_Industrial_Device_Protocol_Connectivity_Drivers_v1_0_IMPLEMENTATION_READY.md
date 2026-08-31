# US eBMR / eDHR Regulated Manufacturing Platform
## Document 44 — Industrial Device & Protocol Connectivity / Driver Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EDGE-002  
**Parent Documents:** Documents 01–42  
**Primary Dependencies:** Document 43; Equipment/EM/Sterile/QC modules; Security  
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

Define protocol-neutral driver contracts and reference behavior for OPC UA, Modbus TCP/RTU, MQTT, SNMP and controlled custom/instrument adapters.

# 2. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
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

# 3. Claude Code Function / Driver Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| connect() | Edge supervisor | ConnectorConfig | Config valid; credentials available | Creates protocol session/socket/client; sets connection health | ConnectionResult{session_id,capabilities} | DriverConnected; AUTH_FAILED/ENDPOINT_UNREACHABLE |
| disconnect() | Supervisor / shutdown | session_id; reason | Session exists | Graceful unsubscribe/close | void/DisconnectResult | DriverDisconnected |
| readOnce() | Commissioning or polling scheduler | SourceAddress; read_options | Connected; read rate allowed | Executes one protocol read; preserves native status/timestamps | RawSourceObservation | READ_TIMEOUT/PROTOCOL_EXCEPTION |
| subscribe() | Subscription scheduler | SourceAddress[]; sampling/publishing config | Protocol supports subscription; connected | Creates monitored subscription and callback | SubscriptionHandle | SubscriptionCreated/SUBSCRIBE_FAILED |
| unsubscribe() | Config change/shutdown | subscription_id | Subscription exists | Deletes monitored items/subscription | void | SubscriptionRemoved |
| browse() | Engineering mapping UI | root/node; filters; continuation | Engineering permission; non-production or approved commissioning mode | Browses metadata only | BrowseResult[] | BROWSE_DENIED/BROWSE_FAILED |
| write() | Approved machine command only | SourceAddress; typed value; command context | Driver writable + runtime command policy + interlock authorized | Executes protocol-specific write; read-back verification if profile requires | DriverWriteReceipt | WRITE_DISABLED/WRITE_FAILED/READBACK_MISMATCH |
| healthCheck() | Periodic supervisor | session_id | Driver instantiated | Checks connection/session latency/native status | DriverHealth | DriverHealthChanged |
| decodePayload() | MQTT/custom message callback | bytes; decoder_version; content_type | Decoder released for source | Validates and decodes deterministic payload | DecodedFields | PAYLOAD_SCHEMA_INVALID |
| mapNativeQuality() | Driver read/subscription | native status/error | Mapping table released | Maps native quality to canonical quality, retaining raw native code | CanonicalQuality | QUALITY_MAPPING_UNKNOWN |
| reconnect() | Supervisor after disconnect | connector_id; previous state | Backoff elapsed | Creates new session; re-establishes subscriptions; emits gap boundary | ReconnectResult | DriverReconnected/RECONNECT_FAILED |
| testMapping() | Engineering UI | mapping draft; one-shot source request | Authorized engineer; no production commit | Reads source, runs decoder/conversion, returns preview only | MappingPreview | MAPPING_TEST_FAILED |

# 4. Common Driver Interface

```ts
interface EdgeDriver {
  connect(config: ConnectorConfig): Promise<ConnectionResult>;
  disconnect(reason: string): Promise<void>;
  readOnce(address: SourceAddress, opts?: ReadOptions): Promise<RawSourceObservation>;
  subscribe?(addresses: SourceAddress[], opts: SubscriptionOptions, cb: ObservationCallback): Promise<SubscriptionHandle>;
  unsubscribe?(id: string): Promise<void>;
  browse?(request: BrowseRequest): Promise<BrowseResult>;
  write?(request: DriverWriteRequest): Promise<DriverWriteReceipt>;
  healthCheck(): Promise<DriverHealth>;
}
```

No driver receives database repository objects from the GxP application.

# 5. OPC UA Reference Configuration

```yaml
protocol: OPCUA
endpoint_url: opc.tcp://10.0.0.10:4840
security_mode: SignAndEncrypt
security_policy: <approved policy>
client_certificate_ref: secret://...
trust_store: /var/lib/edge/opcua/trusted
auth:
  type: username_password | x509 | anonymous_if_explicitly_approved
subscription:
  publishing_interval_ms: 1000
  keepalive_count: 10
```

Mapping:
```yaml
source:
  node_id: "ns=4;s=Line1.Filler.Pressure"
  expected_data_type: Double
canonical:
  parameter_code: FILL_PRESSURE
  uom: bar
```

# 6. Modbus Mapping Contract

```yaml
protocol: MODBUS_TCP
host: 10.0.0.20
port: 502
unit_id: 1
register:
  function: HOLDING
  address: 40010
  length: 2
  data_type: FLOAT32
  byte_order: ABCD
scale: 1.0
```

Each mapping has test vectors with raw registers → expected engineering value.

# 7. MQTT Mapping Contract

```yaml
protocol: MQTT
broker: mqtts://broker.local:8883
client_id: edge-site-a
topic: plant/line1/filler/telemetry
qos: 1
decoder: filler-v2
schema_version: "2.1"
```

Retained messages must be identified and handled according to mapping policy; a retained historical value cannot silently masquerade as a new live observation.

# 8. SNMP

- Prefer SNMPv3 auth/privacy.
- Polling interval bounded.
- Trap ingestion optional and separately authenticated.
- OID mapping versioned.
- Network-management status is converted to equipment evidence only through approved mapping/rules.

# 9. Stable Error Taxonomy

```text
ENDPOINT_UNREACHABLE
AUTH_FAILED
CERT_UNTRUSTED
SESSION_EXPIRED
READ_TIMEOUT
WRITE_DISABLED
PROTOCOL_EXCEPTION
CRC_ERROR
BAD_NATIVE_QUALITY
PAYLOAD_SCHEMA_INVALID
SOURCE_MAPPING_NOT_FOUND
RATE_LIMITED
RECONNECT_FAILED
```

# 10. Security

- OPC UA trust store explicit;
- no “accept any certificate” in production;
- MQTT TLS and topic ACL;
- SNMPv3 preferred;
- Modbus isolated on industrial network/VLAN because protocol lacks native security;
- custom TCP/serial parser fuzz-tested;
- no driver logs secret values.

# 11. Repository Structure

```text
edge/plugins/
├── base/
├── opcua/
├── modbus/
├── mqtt/
├── snmp/
├── serial/
├── rest/
├── file/
└── simulators/
```

# 12. Mandatory Contract Tests

Every plugin must pass:
- connect/auth failure;
- malformed configuration;
- read timeout;
- reconnect;
- bad native quality;
- mapping conversion;
- duplicate/replayed source event where detectable;
- graceful shutdown;
- secret redaction;
- driver crash isolation;
- protocol simulator test.

# 13. Acceptance

The same downstream EdgeObservationEnvelope is produced for equivalent logical parameters regardless of whether the source is OPC UA, Modbus, MQTT or another approved driver.

# 14. Claude Code Prohibitions

- Do not import OPC UA/Modbus/MQTT libraries into GxP Core packages.
- Do not use “accept all certs” in production OPC UA.
- Do not write to PLC/register by default.
- Do not map communication timeout to numeric zero.
- Do not treat retained MQTT payload as current without timestamp/freshness policy.
