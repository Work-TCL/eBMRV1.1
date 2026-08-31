# US eBMR / eDHR Regulated Manufacturing Platform
## Document 24 — LIMS Integration Architecture & Generic Adapter Contract — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QC-002  
**Parent Documents:** Documents 01–22  
**Primary Dependencies:** Documents 03–23; Integration/Event architecture; OOS/OOT  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products (DDCP)  
**Future Profiles:** Medical Devices, Pharmaceuticals  
**Date:** 2026-08-20

---


# Implementation Standard

This document is implementation-grade. Codex/Claude Code shall not invent regulated behavior that is absent from this specification.

Where applicable the specification defines:
- objective/scope/non-goals;
- actors and roles;
- all functionalities and sub-functionalities;
- workflows and state machines;
- business rules;
- authorization and segregation of duties;
- electronic-signature/audit behavior;
- entities, fields and relationships;
- PostgreSQL/Frappe ownership;
- tables, indexes and constraints;
- APIs, stable errors, idempotency and concurrency;
- events/outbox contracts;
- UI screens/actions;
- instrument/LIMS integrations;
- failure and recovery;
- security/configuration/observability;
- retention/migration/performance;
- repository structure;
- implementation sequence;
- positive, negative, concurrency and failure tests;
- acceptance criteria and coding-agent rules.

If a future decision changes regulated behavior and is not defined here, implementation must raise a specification gap rather than guess.

# Regulatory Engineering Basis

For applicable drug/DDCP profiles, the QC architecture is designed to support current requirements including:

- 21 CFR §211.160: laboratory control mechanisms, specifications, sampling plans and test procedures are controlled, Quality-reviewed/approved, followed and documented at the time of performance; deviations are recorded/justified; instruments must be calibrated and unsuitable instruments cannot be used.
- §211.165: each drug-product batch must have appropriate laboratory determination of conformance to final specifications before release, with appropriate written sampling/testing plans and acceptance criteria.
- §211.194: laboratory records include complete sample identification/source, methods, sample amount where appropriate, all data obtained during each test including relevant instrument output, calculations, results, analyst identity/date and second-person review; method modifications, reference standards/reagents and calibration records are also retained.
- FDA's May 2022 final guidance on investigating OOS test results: OOS includes results outside established specifications/acceptance criteria, including in-process laboratory tests; OOS results require scientifically sound investigation and controlled retesting/resampling rather than result substitution.
- FDA Data Integrity guidance: original data, metadata, audit trails and failed/suspect results must not be discarded merely because later data appear acceptable.

OOT is implemented as a configurable quality/trending concept. It is not treated as a universal standalone CFR-defined category; customer procedures and product/test context define OOT rules.

Current official sources:
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-I/section-211.160
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-I/section-211.165
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-J/section-211.194
- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/investigating-out-specification-oos-test-results-pharmaceutical-production-level-2-revision
- https://www.fda.gov/regulatory-information/search-fda-guidance-documents/data-integrity-and-compliance-drug-cgmp-questions-and-answers

# 1. Objective

Define a vendor-neutral LIMS integration contract so native QC and external laboratory systems can coexist without coupling the eBMR domain to one LIMS vendor.

# 2. Provider Interface

```text
interface LIMSProvider {
  createSample(...)
  cancelSample(...)
  getSampleStatus(...)
  getTestOrders(...)
  getResults(...)
  acknowledgeResult(...)
  getEvidence(...)
  healthCheck(...)
}
```

Adapters:
- LabWare
- STARLIMS
- openBIS/reference
- custom REST/SOAP/file/database interfaces
- future vendor-specific implementations

# 3. Functional Requirements

| ID | Functionality | Detailed behavior | Acceptance intent |
|---|---|---|---|
| LIMS-FR-001 | Provider abstraction | Expose generic LIMSProvider contract independent of LabWare/STARLIMS/openBIS/custom vendor. | Vendor-neutral domain. |
| LIMS-FR-002 | System registry | Register LIMS instances, site scope, auth method, endpoint/version, supported operations and health. | Multiple LIMS supported. |
| LIMS-FR-003 | Master mapping | Map product/material/test method/spec/sample types and external IDs with version/status. | Semantic mapping controlled. |
| LIMS-FR-004 | Sample creation | Send sample/test request with exact source record/version, required tests, priority and correlation ID. | Request attributable. |
| LIMS-FR-005 | External sample ID | Persist LIMS sample/order IDs without replacing internal GxP IDs. | Identity separation. |
| LIMS-FR-006 | Status sync | Receive/poll sample/test statuses using idempotent versioned callbacks. | Workflow current. |
| LIMS-FR-007 | Result ingestion | Receive structured result including test code, value/UOM, method, analyst/system source, completion/review state and external result version. | Complete result contract. |
| LIMS-FR-008 | Raw evidence reference | Receive secure evidence/file/export/reference metadata where integration design supports it. | Original evidence linked. |
| LIMS-FR-009 | Result versioning | Each LIMS result/revision maps to immutable accepted GxP result version; original prior versions retained. | No overwrite. |
| LIMS-FR-010 | Duplicate protection | Use external event/result IDs plus idempotency hash to avoid duplicate accepted results. | Replay safe. |
| LIMS-FR-011 | Ordering | Handle late/out-of-order callbacks by external version/sequence and current GxP state rules. | No stale overwrite. |
| LIMS-FR-012 | Schema validation | Validate required fields, data types, UOM, test mapping, method version and source identity before acceptance. | Bad payload rejected/quarantined. |
| LIMS-FR-013 | Source authentication | Use mTLS/OAuth/workload identity/API signing as supported; anonymous callbacks prohibited. | Trusted source. |
| LIMS-FR-014 | Tenant/site scope | LIMS instance and mapping restricted to authorized customer/site. | Isolation. |
| LIMS-FR-015 | Result acceptance policy | External LIMS 'approved' status is evidence, not automatic final batch release; GxP Release Engine evaluates overall eligibility. | Authority separated. |
| LIMS-FR-016 | OOS trigger | External OOS result creates/links GxP OOS record even if LIMS manages its own investigation; source-of-truth responsibility is configured. | No missed OOS. |
| LIMS-FR-017 | OOS ownership mode | Support GXP_MANAGED, LIMS_MANAGED_WITH_SYNC, or HYBRID integration profile with explicit field/state ownership. | No dual-master conflict. |
| LIMS-FR-018 | OOT sync | Receive OOT/trend flag where external LIMS provides it; GxP may independently evaluate configured OOT rules. | Trend visible. |
| LIMS-FR-019 | Result correction | LIMS revision creates new accepted version; never update prior GxP result row. | Data integrity. |
| LIMS-FR-020 | Retest/resample linkage | External new test/sample must carry relation to originating OOS/investigation when applicable. | Scientific history preserved. |
| LIMS-FR-021 | Cancellation | Sample/test cancellation requires reason/source and may be blocked if required for batch/material release. | No silent missing test. |
| LIMS-FR-022 | Acknowledgement | GxP sends accepted/rejected callback acknowledgement with internal event/result ID. | Reconciliation. |
| LIMS-FR-023 | Retry | Outbound and inbound processing idempotent with exponential backoff and dead-letter/manual reconciliation. | Resilient. |
| LIMS-FR-024 | Dead letter | Unprocessable messages retained with payload hash/reference, error code, retry history and operator action. | No lost result. |
| LIMS-FR-025 | Reconciliation job | Periodically compare expected samples/tests/results between systems and surface missing/duplicate/version mismatch. | Integration integrity. |
| LIMS-FR-026 | Manual reconciliation | Authorized integration admin can map/replay/correct integration metadata, but cannot fabricate/change laboratory result. | Admin boundary. |
| LIMS-FR-027 | Time semantics | Store LIMS source timestamps and GxP received/accepted timestamps separately. | Chronology clear. |
| LIMS-FR-028 | Unit conversion | Only controlled UOM mapping/conversion; incompatible unit rejects result. | No semantic drift. |
| LIMS-FR-029 | Method mapping | Unknown/mismatched method/version is rejected/held for review rather than accepted as equivalent. | Method integrity. |
| LIMS-FR-030 | Attachment security | Files scanned, hashed and content-type validated; external URLs not treated as permanent evidence unless approved architecture preserves accessibility/integrity. | Evidence durable. |
| LIMS-FR-031 | Audit | Audit outbound request, inbound event, validation decision, accepted result version, mapping change and manual reconciliation. | Traceable. |
| LIMS-FR-032 | Monitoring | Health, queue age, error rate, last successful sync, result latency and reconciliation differences exposed. | Operational. |
| LIMS-FR-033 | Adapter versioning | Adapter and contract version recorded with each accepted result/event where needed for investigation. | Historical reproducibility. |
| LIMS-FR-034 | Test environment | Provide sandbox/simulator and contract test suite so vendor adapters can be validated before production. | Implementation safe. |

# 4. Integration Architecture

```text
GxP QC / Sampling
      ↓ Outbox
Integration Gateway
      ↓
LIMS Adapter
      ↓
External LIMS

External LIMS
      ↓ webhook/poll
Adapter Validation
      ↓
Integration Command Service
      ↓
Mutation Gateway
      ↓
GxP QC Result / OOS / Audit
```

No adapter writes PostgreSQL directly.

# 5. Ownership Modes

## Mode A — GXP_MANAGED
eBMR owns:
- sample lifecycle;
- QC result authoritative accepted version;
- OOS/OOT;
- review.

LIMS acts primarily as execution/source.

## Mode B — LIMS_MANAGED_WITH_SYNC
LIMS owns lab workflow/investigation; eBMR stores immutable accepted result/evidence/status and required regulatory links.

## Mode C — HYBRID
Explicit per-field/state ownership matrix required before activation.

Default recommendation for enterprise LIMS customers: LIMS-managed lab workflow with strict GxP result/evidence synchronization and eBMR release dependency.

# 6. Mapping Tables

`lims_instance`
- instance ID
- site
- provider type/version
- endpoints
- auth secret reference
- status

`lims_mapping`
- internal object type/ID/version
- external entity type/ID
- mapping version
- effective dates
- status

`lims_message`
- direction
- external event ID
- internal correlation ID
- payload hash
- schema version
- received/sent time
- status/error
- retry metadata

# 7. Result Contract

```json
{
  "external_event_id":"evt-123",
  "external_sample_id":"S-100",
  "external_test_id":"ASSAY",
  "external_result_version":"3",
  "internal_sample_ref":"uuid",
  "test_code":"ASSAY",
  "method_code":"HPLC-001",
  "method_version":"5",
  "result":{"value":"99.4","uom":"%"},
  "outcome":"PASS",
  "performed_at":"...",
  "reviewed_at":"...",
  "source_system":"LIMS-A",
  "evidence":[]
}
```

# 8. API / Webhook

Internal:
- `POST /integrations/lims/{instance}/samples`
- `POST /integrations/lims/{instance}/samples/{id}/cancel`
- `POST /integrations/lims/{instance}/reconcile`
- `GET /integrations/lims/{instance}/health`

Inbound:
- `POST /integrations/lims/{instance}/events/results`
- `POST /integrations/lims/{instance}/events/status`

All inbound operations authenticate instance identity and require unique external event ID.

# 9. Stable Errors

`LIMS_MAPPING_NOT_FOUND`, `LIMS_METHOD_MISMATCH`, `LIMS_UOM_INVALID`, `LIMS_DUPLICATE_EVENT`, `LIMS_RESULT_VERSION_STALE`, `LIMS_RESULT_SCHEMA_INVALID`, `LIMS_SAMPLE_UNKNOWN`, `LIMS_SOURCE_NOT_AUTHORIZED`, `LIMS_EVIDENCE_INVALID`, `LIMS_RECONCILIATION_MISMATCH`.

# 10. Dead-Letter / Reconciliation UI

Screens:
1. LIMS Instances
2. Mapping
3. Message Monitor
4. Dead Letter Queue
5. Reconciliation Differences
6. Manual Mapping Resolution
7. Result History
8. Health Dashboard

Admin actions may:
- correct mapping;
- retry/replay exact stored message;
- acknowledge known duplicate;
- link external/internal IDs.

Admin may not edit result content.

# 11. Security

- private network path where practical;
- mTLS/OAuth/service identity;
- scoped credentials;
- IP/network controls as supplemental;
- secret manager;
- TLS;
- payload size limits;
- malware scanning for files;
- no database credentials shared with LIMS.

# 12. Events

- LIMSSampleRequested
- LIMSStatusReceived
- LIMSResultReceived
- LIMSResultAccepted
- LIMSResultRejected
- LIMSResultRevised
- LIMSIntegrationDeadLettered
- LIMSReconciliationMismatchDetected

# 13. Observability

Metrics:
- requests/sec;
- callback latency;
- pending outbound;
- dead letters;
- mapping failures;
- result acceptance/rejection;
- oldest pending message;
- reconciliation mismatch count.

# 14. Repository Structure

```text
services/integration-gateway/src/lims/
connectors/lims/base/
connectors/lims/labware/
connectors/lims/starlims/
contracts/openapi/lims/
contracts/events/lims/
test/contract/lims-simulator/
```

# 15. Implementation Sequence

1. provider interface;
2. instance registry;
3. mapping;
4. sample outbound;
5. result inbound;
6. idempotency/versioning;
7. result acceptance through Mutation Gateway;
8. dead letter;
9. reconciliation;
10. OOS/OOT ownership modes;
11. first real vendor adapter.

# 16. Test Catalogue

- sample create;
- duplicate sample retry;
- pass result;
- OOS result;
- result revision;
- stale version;
- wrong method;
- wrong UOM;
- unknown sample;
- duplicate event;
- out-of-order events;
- attachment failure;
- source auth failure;
- LIMS outage;
- dead-letter replay;
- reconciliation missing result;
- administrator attempts result edit.

# 17. Acceptance

The generic contract is complete when a simulator can prove:
sample request → external test execution → result callback → QC accepted result → OOS trigger if required → QA/release dependency, with retries and duplicate protection.

# 18. Codex / Claude Rules

Never let adapter write GxP tables directly.
Never let LIMS “released” status equal final product release.
Never overwrite a prior result when external version increases.
Never allow integration admin to change laboratory result content.
