# US eBMR / eDHR Regulated Manufacturing Platform
## Document 23 — Native Basic QC & Sampling Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QC-001  
**Parent Documents:** Documents 01–22  
**Primary Dependencies:** Documents 03–22; OOS/OOT; LIMS Adapter; Equipment; Rules Engine  
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

Provide a native QC capability sufficient for customers that do not operate a full external LIMS, while using the same data-integrity, signature, audit and release principles as the rest of the platform.

The module is intentionally **basic QC/LIMS-lite**, not an attempt to recreate every advanced feature of enterprise laboratory informatics.

# 2. Non-Goals

Not V1:
- full CDS/chromatography-data-system replacement;
- ELN replacement;
- laboratory inventory/chemical inventory at enterprise LIMS depth;
- complex stability study management beyond required hooks;
- instrument control;
- arbitrary laboratory scripting.

# 3. Actors

- Sampler
- QC Analyst
- QC Reviewer
- QC Manager
- QA Reviewer
- Instrument/Edge Service
- LIMS Integration Service
- Auditor

# 4. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| QC-FR-001 | Test specification master | Create versioned test specification by material/product/in-process/device scope with test list, methods, acceptance criteria, sampling plan and release dependency. | QC requirement controlled. |
| QC-FR-002 | Specification lifecycle | Draft, review, released/effective, superseded, obsolete, suspended; released spec immutable and Vault-backed. | No live edit. |
| QC-FR-003 | Test method reference | Each test references approved method/version, compendial/internal/validated method type and suitability/validation evidence reference. | Method exact. |
| QC-FR-004 | Method modification | Modified method requires controlled version, reason, validation/suitability evidence and approval; original method remains. | 211.194(b)-style record support. |
| QC-FR-005 | Sampling plan | Define sample source, quantity, number of units/containers, selection rule, frequency, sample type and reserve/retain behavior. | Written sampling plan. |
| QC-FR-006 | Sample identity | Assign immutable sample ID linked to source lot/batch/container/unit/location, amount, date sampled and date received in lab. | 211.194 sample identity. |
| QC-FR-007 | Sample type | Support incoming, in-process, finished product, device test, environmental, stability, reserve/retain and investigation samples. | Common QC core. |
| QC-FR-008 | Sampling execution | Record sampler, procedure/version, source location/container, amount, timestamp, container/label and chain-of-custody start. | Sample attributable. |
| QC-FR-009 | Chain of custody | Track sample transfers, lab location, storage condition, aliquots, destruction/retain status and custodians. | Sample integrity. |
| QC-FR-010 | Test order | Create one or more test orders from sample/spec with required tests, priority, due date and release/blocking flags. | Work queue controlled. |
| QC-FR-011 | Analyst assignment | Assign qualified analyst/team; qualification/training and method authorization checked at execution. | Qualified lab personnel. |
| QC-FR-012 | Instrument eligibility | Verify instrument/test equipment ID, calibration/status/method compatibility before accepting instrument-generated result. | Unqualified instrument blocked. |
| QC-FR-013 | Reference standard/reagent | Capture reference standard, reagent/solution IDs, lot, expiry/standardization status where test requires them. | Laboratory records complete. |
| QC-FR-014 | Sample amount | Record weight/measure used for each test where applicable. | 211.194(a)(3) support. |
| QC-FR-015 | Raw data | Retain all required raw data or immutable evidence references, including graphs/charts/spectra/files where produced by instrument. | Complete data. |
| QC-FR-016 | Manual raw data | Structured manual observations/entries capture analyst/time/unit/method step and audit history. | No untraceable worksheet. |
| QC-FR-017 | Instrument raw data | Instrument integration stores source ID, original file/reference, sequence/run ID, acquisition time, hash and metadata. | Original data preserved. |
| QC-FR-018 | Calculations | Use released calculation rules for calculations, units, conversion/equivalency factors and rounding; persist inputs/results/version. | 211.194(a)(5) support. |
| QC-FR-019 | Result | Store structured result, unit, method/spec version, acceptance criterion and Pass/Fail/OOS/OOT/Pending status. | Result meaning explicit. |
| QC-FR-020 | Multiple determinations | Model replicates/injections/readings individually where method requires; final reported result derives via released method/rule. | No hidden averaging. |
| QC-FR-021 | System suitability | Where applicable record system-suitability checks separately and determine whether test run is valid under method. | Invalid test distinguished. |
| QC-FR-022 | Analyst completion | Analyst signs/completes test record after all required data/results/evidence present. | Performer attribution. |
| QC-FR-023 | Second-person review | Reviewer verifies original records for accuracy, completeness and specification compliance; controlled e-sign where Part 11 applies. | 211.194(a)(8) support. |
| QC-FR-024 | Result correction | Correction creates superseding result/version with reason; original remains visible and may trigger impact review. | No overwrite. |
| QC-FR-025 | OOS trigger | Any applicable result outside specification/acceptance criteria automatically creates OOS candidate/record; user cannot suppress trigger. | Failed result preserved. |
| QC-FR-026 | OOT trigger | Released trend rule may flag result as OOT even if within specification; create OOT record without changing raw result. | Trend signal. |
| QC-FR-027 | Invalid test | Test may be invalidated only through controlled investigation with assignable cause/evidence; invalidation does not delete raw data. | Scientific invalidation. |
| QC-FR-028 | Retest | Retest cannot be started merely by editing/re-running failed result; it requires OOS/investigation authorization and new test instance. | No testing into compliance. |
| QC-FR-029 | Resample | New sample after OOS requires controlled authorization and scientific rationale; linked to original sample/OOS. | Controlled resampling. |
| QC-FR-030 | Material/batch disposition | QC test-set completion updates quality/release readiness but does not directly perform final batch/material release unless authorized module command executes. | Authority separated. |
| QC-FR-031 | Partial test completion | Test order shows incomplete required tests and blocks dependent release/step. | No false completion. |
| QC-FR-032 | Microbiology result support | Support qualitative/count results, incubation periods, organism/reference metadata and delayed completion without forcing all tests into numeric schema. | Future pharma/sterile ready. |
| QC-FR-033 | Device test support | Support force, torque, dimensional, dose-delivery, leak, electrical/functional, visual or other structured device test result types. | DDCP/device ready. |
| QC-FR-034 | Attachment/evidence | Attach method worksheets, chromatograms, spectra, reports, images and certificates with hash/version/source metadata. | Evidence complete. |
| QC-FR-035 | Stability linkage | Architecture can tag stability sample/timepoint/study and retain results, while full Stability Management may be separate later spec. | Expandable. |
| QC-FR-036 | QC dashboard | Show samples/tests by status, overdue, OOS/OOT, analyst, instrument, product/material and release blockers. | Operational. |
| QC-FR-037 | Search/export | Authorized users can retrieve complete sample/test record including raw data refs, calculations, analyst/reviewer signatures and audit. | Inspection-ready. |
| QC-FR-038 | No deletion | Sample/test/result/raw-data metadata cannot be physically deleted by normal application workflow. | Data integrity. |

# 5. State Models

Sample:
```text
PLANNED → COLLECTED → RECEIVED → IN_TESTING → TESTING_COMPLETE → DISPOSED/RETAINED
                       └→ HOLD
```

Test Order:
```text
CREATED → ASSIGNED → IN_PROGRESS → ANALYST_COMPLETE → REVIEW_PENDING
        → REVIEWED/ACCEPTED
```

Alternate:
`OOS_PENDING`, `OOT_PENDING`, `INVALID_UNDER_INVESTIGATION`, `SUPERSEDED`.

# 6. Data Model

## `qc_test_specification`
```text
id uuid PK
tenant_id uuid
spec_code varchar(120)
version_no bigint
scope_type varchar(40)
scope_version_id uuid
status varchar(40)
effective_from/to
sampling_plan_id uuid
released_vault_object_id uuid
```

## `qc_test_definition`
- specification
- test code/name
- method version
- result data type
- UOM
- acceptance rule
- required flag
- release-blocking flag
- OOS/OOT policies
- review policy

## `qc_sample`
```text
id uuid PK
tenant_id uuid
sample_number varchar(160)
sample_type varchar(50)
source_type varchar(50)
source_id uuid
source_location_ref varchar(200)
lot_batch_serial_ref varchar(200)
sample_quantity numeric(24,8)
sample_uom varchar(40)
sampled_at timestamptz
received_at timestamptz
sampler_subject_id uuid
state varchar(40)
version bigint
```

## `qc_test_order`
- sample ID
- test definition/version
- assigned analyst
- state/version
- started/completed/reviewed times
- blocking status

## `qc_test_run`
- test order
- method version
- instrument/equipment ID
- analyst
- sample amount
- reference standards/reagents
- system suitability
- raw-data evidence IDs
- calculation version

## `qc_result`
```text
id uuid PK
test_order_id uuid
test_run_id uuid
result_version bigint
result_type varchar(40)
value_decimal numeric(30,12)
value_text text
value_json jsonb
uom varchar(40)
acceptance_rule_id uuid
outcome varchar(40)
oos_record_id uuid
oot_record_id uuid
supersedes_result_id uuid
created_at timestamptz
```

# 7. Test Result Types

Supported:
- numeric single value;
- numeric replicate series;
- calculated numeric;
- qualitative enum;
- pass/fail;
- text/observation;
- count;
- range;
- multidimensional JSON schema for approved device tests.

Every type has explicit schema and review rendering.

# 8. API Surface

- `POST /qc/v1/specifications/drafts`
- `POST /qc/v1/specifications/{id}/release`
- `POST /qc/v1/samples`
- `POST /qc/v1/samples/{id}/receive`
- `POST /qc/v1/test-orders`
- `POST /qc/v1/test-orders/{id}/start`
- `POST /qc/v1/test-orders/{id}/raw-data`
- `POST /qc/v1/test-orders/{id}/results`
- `POST /qc/v1/test-orders/{id}/complete`
- `POST /qc/v1/test-orders/{id}/review`
- `POST /qc/v1/results/{id}/correct`
- `GET /qc/v1/samples/{id}/record`
- `GET /qc/v1/release-readiness?...`

Stable errors:
`TEST_SPEC_NOT_EFFECTIVE`, `ANALYST_NOT_QUALIFIED`, `INSTRUMENT_INELIGIBLE`, `METHOD_VERSION_INVALID`, `RAW_DATA_REQUIRED`, `SYSTEM_SUITABILITY_FAILED`, `RESULT_OUT_OF_SPEC`, `RESULT_OUT_OF_TREND`, `SECOND_PERSON_REVIEW_REQUIRED`, `RESULT_VERSION_STALE`.

# 9. Result Evaluation

Pipeline:

```text
Raw/Observed Data
    ↓
Method-defined calculation
    ↓
Reported Result
    ↓
Specification comparison
    ├→ PASS
    ├→ OOS
    └→ OOT flag (if trend rule)
```

A later result never removes the prior result from history.

# 10. Raw Data / Evidence

Evidence service stores:
- original file;
- hash;
- source instrument;
- acquisition/run ID;
- acquired timestamp;
- uploaded/received timestamp;
- MIME/type;
- storage retention.

If instrument system remains authoritative for dynamic data, eBMR stores immutable reference/export/evidence sufficient for intended validated design; exact instrument integration is assessed per adapter.

# 11. Review UI

QC Reviewer sees:
- sample/source;
- method;
- sample amount;
- raw data/evidence;
- calculations;
- result/criterion;
- prior/superseded results;
- system suitability;
- OOS/OOT;
- analyst;
- audit;
- review signature.

# 12. Second-Person Review

Review action verifies:
- correct sample/source;
- method;
- complete data;
- calculations;
- acceptance comparison;
- OOS/OOT handling;
- instrument status;
- original data availability.

Reviewer cannot edit analyst result.

# 13. Events

- QCSampleCreated
- QCSampleReceived
- QCTestStarted
- QCResultRecorded
- QCResultOOSDetected
- QCResultOOTDetected
- QCTestAnalystCompleted
- QCTestReviewed
- QCResultCorrected
- QCTestInvalidated

# 14. Audit / Signature

Audit:
- sample creation/collection/receipt;
- test start;
- raw evidence ingestion;
- all result versions;
- calculations;
- invalidation;
- correction;
- analyst/reviewer signatures;
- OOS/OOT linkage.

# 15. Repository Structure

```text
services/gxp-api/src/modules/qc/
services/gxp-api/src/modules/sampling/
apps/ebmr_frappe/ebmr/qc/
apps/ebmr_frappe/ebmr/sampling/
contracts/events/qc/
validation/requirements/qc/
```

# 16. Observability

Metrics:
- samples pending;
- tests overdue;
- instrument integration failures;
- OOS rate;
- OOT rate;
- review backlog;
- raw-data ingestion errors;
- LIMS handoff status.

# 17. Implementation Sequence

1. test specification/method references;
2. sample;
3. test order;
4. result schemas;
5. calculation/acceptance;
6. raw evidence;
7. analyst completion;
8. second-person review;
9. OOS/OOT hooks;
10. release readiness;
11. instrument/Edge adapters.

# 18. Test Catalogue

- numeric pass;
- numeric OOS;
- qualitative fail;
- replicate calculation;
- missing raw data;
- wrong method version;
- analyst qualification expired;
- instrument calibration expired;
- system suitability failed;
- result correction;
- second-person reviewer edits attempt;
- OOS then retest;
- OOT within specification;
- late instrument file;
- sample chain of custody;
- duplicate test submission;
- backup/restore evidence.

# 19. Acceptance

Native QC is sufficient for a representative DDCP flow:
incoming material sample → identity/assay tests → material release; in-process sample → IPC result; finished/DDCP test → reviewed result → release engine.

# 20. Codex / Claude Rules

Never overwrite an OOS/failing result with a passing retest.
Never let analyst self-review when independent review policy applies.
Never store only the interpreted result when required raw data/evidence exists.
Never treat “invalid test” as a user-selected status without investigation.
