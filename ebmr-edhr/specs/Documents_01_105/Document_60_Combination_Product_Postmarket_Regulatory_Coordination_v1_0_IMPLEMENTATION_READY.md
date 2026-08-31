# US eBMR / eDHR Regulated Manufacturing Platform
## Document 60 — Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-PM-003  
**Parent Documents:** Documents 01–59  
**Primary Dependencies:** Documents 35–36, 58–59; Part 4; Part 806; Field Alert/BPDR; Records Management  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profile:** Drug–Device Combination Products (DDCP)  
**Date:** 2026-08-20

---

# Implementation / Claude Code Contract

Direct Claude Code/Codex specification. Before code, extract applicant relationships, obligations, trigger/clock/deadline rules, functions, inputs/outputs, DB changes, report/submission links, retention calculations, state machines, APIs/events, errors and tests. If a missing decision changes regulated behavior, create `SPEC_GAP`.

Document 36 owns operational field-action/recall execution. Document 60 owns regulatory coordination/reporting obligations around that field action; it must not create a second recall execution model. Document 59 remains the canonical report/submission engine.

# Current Regulatory Baseline

- 21 CFR §4.103 requires certain information associated with a combination-product death/serious injury or adverse experience to be provided to other constituent-part applicants no later than 5 calendar days after receipt, and records must include the information shared, receipt date, sharing date, and recipient name/address.
- §4.105 uses the longest applicable postmarketing-safety-reporting recordkeeping period.
- §806.10 reportable device corrections/removals are reported within 10 working days of initiation; scope extensions can require amendments. §806.20 requires records for nonreportable corrections/removals.
- §314.81 requires NDA Field Alert reporting within 3 working days of receipt of specified distributed-product quality information.
- Part 4 may also require field-alert and biological-product-deviation reporting based on constituent parts/application context and adds periodic-report obligations for certain combination products.

Official references:
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-4/subpart-B
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-806
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-D/part-314/subpart-B/section-314.81
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-F/part-600/subpart-B/section-600.14
- https://www.fda.gov/combination-products/guidance-regulatory-information/postmarketing-safety-reporting-combination-products

# 1. Objective

Define combination-product applicant coordination, constituent-part applicant information sharing, correction/removal regulatory records, Field Alert/BPDR workflow hooks, periodic safety reporting calendar, FDA information requests, deadline overrides and postmarket recordkeeping/retention.

# 2. Actors

- Regulatory Affairs
- Pharmacovigilance/Safety
- Device Vigilance
- QA
- Field Action/Recall Coordinator
- Records Manager
- Legal/Compliance
- Regulatory Submission Service
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| PMO-FR-001 | Applicant-role master | Model combination-product applicant, constituent-part applicants, application numbers/types, addresses, contacts and effective relationship dates. | Part 4 context. |
| PMO-FR-002 | Product/applicant mapping | Each marketed DDCP product version maps relevant applicant relationships and constituent/application roles. | Correct recipient/rules. |
| PMO-FR-003 | Part 4 sharing trigger | Qualifying safety information can create information-sharing assessment/task when rule applies. | §4.103 support. |
| PMO-FR-004 | 5-calendar-day sharing clock | Calculate no-later-than 5 calendar days from applicable applicant receipt date for §4.103 sharing. | Timeliness. |
| PMO-FR-005 | Immutable sharing package | Freeze exact information shared and provenance; later corrections/follow-up create new package/version. | Recordkeeping. |
| PMO-FR-006 | Recipient evidence | Record recipient applicant name/address/contact/channel and relationship version. | §4.103 record. |
| PMO-FR-007 | Sharing evidence | Record company receipt date, sharing date/time, package hash, sender and delivery/ack evidence when available. | Proof. |
| PMO-FR-008 | Sharing escalation | Due-soon/failed constituent sharing escalates to Regulatory management. | Compliance operations. |
| PMO-FR-009 | Correction/removal assessment | Document 36 Field Action creates linked Part 806 correction/removal assessment; do not duplicate action scope/communications. | Device postmarket. |
| PMO-FR-010 | 806 10-working-day clock | If reportable under configured §806.10 rule, calculate 10 working days from initiation. | Timely reporting. |
| PMO-FR-011 | 806 nonreportable record | If not reportable, create controlled §806.20 record with required source/action facts and retention. | Recordkeeping. |
| PMO-FR-012 | Scope extension amendment | Field-action expansion to additional lots/batches creates amendment assessment/task where required. | Dynamic action. |
| PMO-FR-013 | Field Alert candidate | Distributed drug-product quality issue from Complaint/Deviation/OOS/Field Action can create NDA Field Alert assessment. | 314.81 linkage. |
| PMO-FR-014 | Field Alert 3-working-day clock | When applicable, calculate 3 working days from applicant receipt of qualifying information. | Timeliness. |
| PMO-FR-015 | Field Alert evidence | Link distributed batches, issue type, facility, specifications/contamination/mix-up facts and submission/rapid-communication evidence. | Traceability. |
| PMO-FR-016 | BPDR candidate | Biologic/product deviation can create BPDR assessment/report task where applicable. | Biologic postmarket. |
| PMO-FR-017 | Periodic schedule | Maintain quarterly/annual or FDA-configured periodic safety reporting cycles by application/profile. | Calendar. |
| PMO-FR-018 | Periodic dataset freeze | Use Document 58 immutable interval/cutoff dataset; preserve source versions and inclusion rules. | Reproducible report. |
| PMO-FR-019 | Part 4 periodic augmentation | For applicable NDA/ANDA/BLA combination products containing a device constituent, include required summary/analysis of applicable device reports for interval. | Part 4. |
| PMO-FR-020 | FDA information request | Written FDA request creates task with request reference, reason/purpose, requested events/information and agency due date. | Agency response. |
| PMO-FR-021 | Regulatory correspondence | Store incoming/outgoing correspondence, agency/center, submission/reference numbers, due dates and owner. | Trace. |
| PMO-FR-022 | Unified regulatory calendar | Show expedited reports, sharing, 806, Field Alerts, BPDR, periodic reports, agency requests and commitments. | Operations. |
| PMO-FR-023 | Deadline source/basis | Every obligation stores rule/citation/agency-letter source, clock start, original/current due date and calendar profile. | Explainable. |
| PMO-FR-024 | Deadline override | Agency-granted alternate schedule/extension can change current due date only with evidence, authority and preserved original deadline. | Controlled override. |
| PMO-FR-025 | Longest-applicable retention | Combination-product postmarket records use configured longest applicable reporting recordkeeping period. | §4.105 support. |
| PMO-FR-026 | Retention basis | Store all applicable regimes, rule versions, calculated durations/triggers and selected longest rule. | Transparent retention. |
| PMO-FR-027 | No retrospective shortening | Later profile/rule change cannot silently shorten retention of existing records. | Durability. |
| PMO-FR-028 | Legal/regulatory hold | Authorized hold suspends normal purge/destruction and preserves reason/scope. | Governance. |
| PMO-FR-029 | Submission linkage | Obligations reference Document 59 regulatory report/submission or controlled manual evidence; no duplicate submitted-payload store. | Single submission truth. |
| PMO-FR-030 | Field-action linkage | Part 806 record references exact Document 36 field-action/scope snapshot. | No duplication. |
| PMO-FR-031 | Periodic report state | SCHEDULED→DATA_COLLECTION→FROZEN→ANALYSIS→APPROVED→SUBMITTED→ACK/ARCHIVE. | Controlled lifecycle. |
| PMO-FR-032 | Inspection dashboard/export | Show due/overdue obligations and export applicant-sharing, 806, Field Alert/BPDR, periodic, agency-request and retention evidence. | Inspection-ready. |

# 4. Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| configureApplicantRelationship() | Regulatory Admin | product/application IDs; applicant roles; counterpart name/address/contact; effective dates | Authorized; product/application valid; overlap rules satisfied | Insert versioned applicant_relationship and audit | ApplicantRelationship | ApplicantRelationshipConfigured; APPLICANT_RELATIONSHIP_INVALID |
| evaluatePart4InformationSharing() | Safety case/follow-up | safety_case_id; company_receipt_at; application/profile; applicant relationships | Marketed combination product; current relationship/rule exists | Evaluate sharing candidate; create obligation/task only after configured reviewer confirmation | InformationSharingAssessment | Part4SharingAssessmentCreated |
| createConstituentSharingPackage() | Regulatory reviewer | sharing_task_id; safety information snapshot; recipient relationship version | Task open; recipient resolved; package complete | Freeze package in Vault with hash/provenance | SharingPackage | ConstituentSharingPackageCreated |
| recordConstituentInformationShared() | Regulatory user/integration | sharing_task_id; sent_at; channel; recipient; delivery_evidence | Approved package; deadline active | Append transmission evidence; mark obligation satisfied; no source-case mutation | SharingReceipt | ConstituentInformationShared |
| createCorrectionRemovalAssessment() | Document 36 event | field_action_id; initiation_at; device/application profile | Field-action scope snapshot exists | Create linked Part806 assessment and regulatory obligation candidate | CorrectionRemovalAssessment | CorrectionRemovalAssessmentOpened |
| decideCorrectionRemovalReportability() | Regulatory reviewer | assessment_id; reportable:boolean; rationale; signature | Reviewer authorized; field-action facts current | Insert decision; if reportable create Doc59 report/manual task; if no create 806.20 regulatory record | CorrectionRemovalDecision | CorrectionRemovalReportabilityDecided |
| createFieldAlertAssessment() | Complaint/Deviation/OOS/Field Action | application/product; distributed batches; issue facts; applicant_receipt_at | NDA context configured; distributed-product candidate | Create Field Alert assessment and 3-working-day deadline candidate | FieldAlertAssessment | FieldAlertAssessmentOpened |
| decideFieldAlertReportability() | Regulatory/Quality reviewer | assessment_id; decision; rationale; signature | Reviewer authorized; source evidence reviewed | Insert decision; create report/submission/rapid communication task if reportable | FieldAlertDecision | FieldAlertDecisionRecorded |
| createBPDRTrack() | Biologic quality/deviation event | product/application; deviation facts; discovery/receipt dates | Biologic/BLA profile configured | Create BPDR assessment/report task according to effective rule/profile | BPDRTrack | BPDRTrackCreated |
| generatePeriodicReportingSchedule() | Regulatory calendar job | application_id; approval/license date; reporting profile; FDA overrides | Profile effective | Generate nonduplicate cycles/due dates and persist rule basis | PeriodicSchedule | PeriodicSafetyScheduleGenerated |
| freezePeriodicReportDataset() | Periodic report owner | cycle_id; source_cutoff | Cycle in data collection; source surveillance complete enough per procedure | Call Doc58 dataset builder; persist immutable dataset ref | PeriodicDatasetRef | PeriodicDatasetFrozen |
| createFDAInformationRequestTask() | Regulatory user/inbound correspondence | agency letter/ref; requested info/events; due_at; received_at | Request verified/authenticated operationally | Insert correspondence + regulatory obligation/task | FDARequestTask | FDAInformationRequestOpened |
| applyRegulatoryDeadlineOverride() | Regulatory manager | obligation_id; new_due_at; agency evidence; reason; signature | Authorized; source evidence valid | Insert deadline version preserving original/current history | DeadlineOverride | RegulatoryDeadlineOverridden |
| calculatePostmarketRetentionPolicy() | Records Management | product/application profile; applicable regimes; record type | Applicability matrix approved | Evaluate retention rules; choose longest; insert decision/basis | RetentionPolicyDecision | PostmarketRetentionPolicyCalculated |
| placePostmarketLegalHold() | Legal/Regulatory | record scope; reason; authority; effective_at | Authorized | Insert hold; purge service must check active holds | LegalHold | PostmarketLegalHoldPlaced |

# 5. Applicant Relationship Model

```text
Combination Product
   ├ Application(s)
   ├ Combination Product Applicant
   └ Constituent Part Applicants
        ├ Device applicant
        ├ Drug applicant
        └ Biologic applicant
```

Relationships are effective-dated/versioned and include legal organization name, address, regulatory contacts, agreement/reference and constituent/application role.

# 6. Part 4 Information-Sharing Workflow

```text
Qualifying safety information received
       ↓
Applicability assessment
       ↓
Recipient relationship resolution
       ↓
5-calendar-day regulatory obligation
       ↓
Approved immutable sharing package
       ↓
Transmit / record recipient + sent date
       ↓
Delivery evidence / escalation
       ↓
Retention under longest applicable policy
```

# 7. Corrections / Removals Boundary

Document 36 owns affected-product scope, consignee communications, returns/corrections, effectiveness and operational closure. This document owns only Part 806 regulatory assessment, deadline, report/submission link, nonreportable record and amendments.

# 8. Field Alert / BPDR Boundary

Field Alert and BPDR assessments consume source Quality/Deviation/Complaint/Field Action facts. Report generation/submission uses Document 59. No second regulatory payload implementation is created here.

# 9. Periodic Reporting Cycle

```text
SCHEDULED → DATA_COLLECTION → DATASET_FROZEN
          → MEDICAL/REGULATORY_ANALYSIS → APPROVAL
          → SUBMISSION → ACK/ARCHIVE
```

Part 4 augmentation rules are versioned and application/constituent-specific.

# 10. Data Model

## `regulatory_obligation`
```text
id uuid PK
obligation_type varchar
source_type/id/version
application_id uuid
rule_version_id uuid
clock_start_at timestamptz
original_due_at timestamptz
current_due_at timestamptz
calendar_profile_id uuid
state varchar
owner_subject_id uuid
version bigint
```

## `applicant_relationship`
`product/application, applicant_type, counterpart organization/address/contact, constituent role, effective dates, evidence refs, version`

## `constituent_information_share`
`case_id, recipient relationship version, package Vault ref/hash, company receipt date, due date, sent date, delivery evidence, state, version`

## `correction_removal_regulatory_record`
`field_action_id, initiation date, reportability decision/rationale/signature, 806 report ref or 806.20 record, amendments, version`

## `periodic_reporting_cycle`
`application, period start/end, dataset cutoff, due date, profile/rule, dataset ref, report/submission ref, state, version`

# 11. Retention Model

Do not store one arbitrary universal retention value. Store:
- applicable regimes;
- retention rule versions;
- each calculated duration/trigger;
- selected longest requirement;
- legal/regulatory holds.

A future rule/profile change must not silently reduce already-assigned retention.

# 12. APIs

- `POST /postmarket/v1/applicant-relationships`
- `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate`
- `POST /postmarket/v1/sharing/{id}/package`
- `POST /postmarket/v1/sharing/{id}/record-sent`
- `POST /postmarket/v1/field-actions/{id}/correction-removal-assessment`
- `POST /postmarket/v1/correction-removal/{id}/decision`
- `POST /postmarket/v1/field-alerts`
- `POST /postmarket/v1/field-alerts/{id}/decision`
- `POST /postmarket/v1/bpdr-tracks`
- `POST /postmarket/v1/periodic-cycles:generate`
- `POST /postmarket/v1/periodic-cycles/{id}/dataset:freeze`
- `POST /postmarket/v1/fda-requests`
- `POST /postmarket/v1/obligations/{id}/deadline-overrides`
- `POST /postmarket/v1/retention:calculate`

# 13. Events

- `ApplicantRelationshipConfigured`
- `Part4SharingAssessmentCreated`
- `ConstituentSharingPackageCreated`
- `ConstituentInformationShared`
- `CorrectionRemovalAssessmentOpened`
- `CorrectionRemovalReportabilityDecided`
- `FieldAlertAssessmentOpened`
- `FieldAlertDecisionRecorded`
- `BPDRTrackCreated`
- `PeriodicSafetyScheduleGenerated`
- `PeriodicDatasetFrozen`
- `FDAInformationRequestOpened`
- `RegulatoryDeadlineOverridden`
- `PostmarketRetentionPolicyCalculated`
- `PostmarketLegalHoldPlaced`

# 14. UI

1. Applicant/Constituent Relationship
2. Information Sharing Queue
3. Sharing Package
4. Correction/Removal Regulatory Assessment
5. Field Alert Assessment
6. BPDR Queue
7. Periodic Safety Calendar
8. Periodic Report Workspace
9. FDA Requests/Correspondence
10. Unified Regulatory Calendar
11. Retention Basis / Legal Hold
12. Inspection Dashboard

# 15. Stable Errors

`APPLICANT_RELATIONSHIP_MISSING`, `PART4_SHARING_DEADLINE_MISSING`, `PART4_SHARING_RECIPIENT_MISSING`, `CORRECTION_REMOVAL_SCOPE_MISSING`, `FIELD_ALERT_APPLICATION_MISMATCH`, `PERIODIC_REPORT_PROFILE_MISSING`, `FDA_REQUEST_DUE_DATE_REQUIRED`, `RETENTION_RULE_MISSING`, `LEGAL_HOLD_ACTIVE`, `STALE_REGULATORY_OBLIGATION_VERSION`.

# 16. Mandatory Tests

- two constituent applicants create correct sharing recipients;
- missing recipient blocks completion;
- 5-calendar-day sharing deadline;
- reportable field action creates 10-working-day 806 obligation;
- nonreportable correction/removal creates controlled 806.20 record;
- scope expansion creates amendment task;
- NDA Field Alert 3-working-day calculation;
- biologic profile creates BPDR task;
- quarterly/annual periodic cycle generation without duplicates;
- Part 4 periodic augmentation;
- FDA letter explicit due date;
- agency extension preserves original deadline;
- retention selects longest configured applicable period;
- legal hold blocks purge.

# 17. Repository Structure

```text
services/gxp-api/src/modules/postmarket/regulatory-operations/
apps/ebmr_frappe/ebmr/postmarket/regulatory_operations/
contracts/events/postmarket/
services/workers/src/regulatory-calendar/
validation/requirements/postmarket-operations/
```

# 18. Acceptance Criteria

A marketed DDCP can maintain its applicant relationships, share qualifying safety information with other constituent applicants on a controlled deadline, manage Part 806/Field Alert/BPDR/periodic obligations without duplicating QMS execution, respond to FDA requests, and retain postmarket records under a transparent longest-applicable-retention policy.

# 19. Claude Code Prohibitions

- Never duplicate Document 36 recall/field-action execution.
- Never mark information shared without package/recipient/sent-date evidence.
- Never assume all clocks start from complaint creation time.
- Never shorten retention because a later rule/profile is shorter.
- Never allow generic admin to override regulatory due date without source evidence.
