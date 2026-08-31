# US eBMR / eDHR Regulated Manufacturing Platform
## Document 46 — Barcode, Scanner, Balance, Printer, Tester & Peripheral Integration — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-EDGE-004  
**Parent Documents:** Documents 01–42  
**Primary Dependencies:** Documents 20–23, 38, 43–45; Packaging/Dispensing/eDHR  
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

Define operator-facing peripheral integration contracts for barcode scanning, weighing, controlled printing, testers, vision systems and file-producing instruments used by material, packaging, QC and device-production workflows.

# 2. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| PER-FR-001 | Peripheral registry | Barcode scanners, balances, printers, testers, cameras/vision and other peripherals have registered identity and site/station assignment. | Attributable source. |
| PER-FR-002 | Station profile | Define station/workcell allowed device types and intended operations. | Correct device use. |
| PER-FR-003 | Barcode scanner | Support keyboard wedge only for noncritical/simple cases; preferred explicit scanner SDK/serial/HID service with source identity. | Source clarity. |
| PER-FR-004 | Barcode parsing | Versioned barcode parser supports GS1/UDI/custom/internal labels; raw scan retained. | Deterministic parsing. |
| PER-FR-005 | Scan validation | Server/domain validates scanned business object against expected material/product/lot/serial/location/action. | No trust in text. |
| PER-FR-006 | Duplicate scan | Debounce/duplicate handling does not suppress legitimate repeated actions; operation context determines idempotency. | Safe UX. |
| PER-FR-007 | Balance integration | Registered balance delivers value, unit, stable flag, device time/status and calibration identity. | Weighing evidence. |
| PER-FR-008 | Stable reading | Device/adapter-specific stable criteria must be released/configured; UI cannot accept transient value as stable. | Accuracy. |
| PER-FR-009 | Balance tare | Tare operation/status captured when workflow requires; software distinguishes gross/tare/net. | Reproducibility. |
| PER-FR-010 | Manual fallback | Manual weight/result only if workflow policy permits and reason/verifier requirements met. | Controlled fallback. |
| PER-FR-011 | Label printer | Print request uses exact released template/artwork, variable data and printer identity. | Controlled labeling. |
| PER-FR-012 | Print acknowledgement | Where printer supports it, capture job/print status; lack of status does not fabricate successful physical application. | Boundary. |
| PER-FR-013 | Reprint | Reprint is a new controlled print action with reason/counter. | Trace. |
| PER-FR-014 | Tester integration | Functional/device testers return test ID, unit/serial, method/program version, values, result, raw evidence and tester identity. | eDHR evidence. |
| PER-FR-015 | Vision system | Capture inspected unit/lot, recipe/model version, defect classification, image/evidence ref and system confidence if used. | Inspection trace. |
| PER-FR-016 | AI/vision decision | Automated pass/fail only if validated approved model/rule; otherwise advisory result requiring operator/QA decision. | Controlled AI. |
| PER-FR-017 | File-producing instrument | Import original file/export with checksum and parse result through versioned adapter. | Data integrity. |
| PER-FR-018 | Peripheral eligibility | Calibration/qualification/maintenance status checked through Equipment module before regulated use. | Valid equipment. |
| PER-FR-019 | Station lock | Critical workflow binds expected station/peripheral so another nearby device cannot submit without authorization. | Context. |
| PER-FR-020 | Hot-plug/reconnect | Reconnect preserves device identity and generates session boundary. | Resilience. |
| PER-FR-021 | Device substitution | Replacement device requires eligibility and station policy; no hidden substitution. | Trace. |
| PER-FR-022 | Local UI | Operator sees device connected/eligible/stable/source status before action. | Transparency. |
| PER-FR-023 | Raw input preservation | Raw scan/weight/test payload retained or hashed/evidenced where required. | Auditability. |
| PER-FR-024 | Security | USB/serial/network device access restricted to gateway service; arbitrary removable-storage use prohibited by deployment hardening. | Security. |
| PER-FR-025 | Simulation | Peripheral simulators available for CI and validation. | Testability. |

# 3. Claude Code Function Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| captureBarcodeScan() | Scanner adapter | raw_scan; scanner_id; station_id; timestamp | Scanner registered/eligible; station active | Preserves raw scan; parses using parser version; builds ScanObservation | ScanObservation{raw,parsed,parser_version} | BarcodeScanned; BARCODE_PARSE_FAILED |
| validateScanForAction() | UI/domain action | ScanObservation; expected_entity_type; action_context | User/action authorized; expected requirement exists | Resolves entity and checks material/lot/serial/location/status compatibility | ScanValidationResult | WRONG_MATERIAL/WRONG_LOT/WRONG_SERIAL/LOCATION_MISMATCH |
| readStableWeight() | Dispensing UI | balance_id; timeout_ms; expected_uom | Balance eligible; driver connected | Collects readings until device stable flag/approved stability algorithm; converts controlled UOM | StableWeightReading | READING_UNSTABLE/BALANCE_INELIGIBLE |
| recordTare() | Dispensing workflow | balance_id; tare_context | Tare allowed; container context known | Invokes/reads tare; records value/status/source | TareReceipt | TARE_FAILED |
| submitManualWeight() | Operator UI | value; uom; reason; verifier/signature if required | Fallback policy allows; actor qualified | Creates manual-source evidence; no device attribution | ManualWeightResult | MANUAL_FALLBACK_NOT_ALLOWED |
| createPrintJob() | Packaging/dispensing module | template_version; variable_data; printer_id; copies | Template released; printer eligible; action authorized | Canonicalizes variables; hashes request; stores print job; sends adapter request | PrintJobReceipt | LABEL_TEMPLATE_INVALID/PRINTER_INELIGIBLE |
| reprintLabel() | Authorized UI | original_print_job_id; reason | Reprint policy/role valid | Creates child print job, increments counter, audits reason | PrintJobReceipt | REPRINT_REASON_REQUIRED |
| ingestTesterResult() | Tester adapter | tester payload; tester_id; program_version; unit/serial | Tester eligible; mapping released | Validates program/unit; stores raw evidence ref; emits canonical test result event | CanonicalTesterResult | TESTER_PROGRAM_MISMATCH/UNIT_ID_MISMATCH |
| ingestVisionResult() | Vision adapter | inspection payload; model/recipe version; image refs | System eligible; model/version approved for intended use | Maps defects/result; stores evidence refs/confidence; labels AI/advisory status | VisionInspectionResult | VISION_MODEL_UNAPPROVED |
| registerPeripheralSession() | Gateway runtime | device_id; station_id; connection metadata | Device registered; station mapping valid | Creates ephemeral connection/session and health state | PeripheralSession | DEVICE_NOT_REGISTERED/STATION_NOT_ALLOWED |

# 4. Canonical Contracts

## ScanObservation

```ts
type ScanObservation = {
  scanId: string;
  scannerId: string;
  stationId: string;
  raw: string;
  parserId: string;
  parserVersion: string;
  parsed: {
    entityType?: string;
    productCode?: string;
    lot?: string;
    serial?: string;
    udi?: string;
    expiry?: string;
    custom?: Record<string,string>;
  };
  acquiredAt: string;
};
```

## StableWeightReading

```ts
type StableWeightReading = {
  readingId: string;
  balanceId: string;
  value: string;     // decimal string
  uom: string;
  gross?: string;
  tare?: string;
  net?: string;
  stable: boolean;
  sourceTimestamp?: string;
  receivedAt: string;
  deviceStatus: string;
  calibrationRef?: string;
};
```

# 5. Station Model

`station_profile`:
- site/area/line;
- station code;
- allowed operations;
- allowed peripheral classes;
- expected device IDs optional;
- fallback policy;
- network/gateway assignment.

# 6. Barcode Strategy

Parsing is separate from business validation.

```text
raw scan
  ↓ parser
parsed identity
  ↓ server lookup
authoritative material/product/serial record
  ↓ action-specific eligibility
accepted/rejected scan
```

Never assume a syntactically valid barcode is authorized for the current batch.

# 7. Balance Strategy

- use decimal strings;
- stable reading only;
- preserve device UOM and canonical UOM;
- check equipment eligibility;
- fallback is explicit;
- readings associated with weighing session/order.

# 8. Printing Boundary

The print service does not decide product correctness. Packaging/Dispensing domains create the approved print request. Adapter only renders/sends exact approved payload.

# 9. Tester/Vision Boundary

Tester/vision system output is external evidence. eDHR/QC module determines whether the result fulfills an acceptance requirement.

# 10. UI Components

Reusable:
- `<ScannerStatus />`
- `<ScanInputAction />`
- `<BalanceStatus />`
- `<LiveStableWeight />`
- `<ControlledPrintAction />`
- `<TesterResultPanel />`
- `<VisionEvidencePanel />`

# 11. Tests

Include wrong material scan, duplicate scan, balance disconnect during weighing, calibration expiry, unstable reading, printer retry causing duplicate physical labels, tester program mismatch, serial mismatch, vision model version mismatch, file checksum mismatch.

# 12. Acceptance

A complete dispensing and device-test workflow can identify exact devices, acquire attributable values/results, reject mismatches, preserve raw evidence and produce GxP events without peripheral code directly mutating batch/release state.

# 13. Claude Code Prohibitions

- Never treat keyboard-wedge text as authenticated scanner identity in critical workflows unless deployment profile explicitly accepts it.
- Never round balance value in UI before regulated rule evaluation.
- Never allow printer adapter to choose label template.
- Never accept tester “PASS” without expected unit/program/method validation.
