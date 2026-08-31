# US eBMR / eDHR Regulated Manufacturing Platform
## Document 58 — Postmarket Surveillance, Safety Case & Signal Management — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-PM-001  
**Parent Documents:** Documents 01–57  
**Primary Dependencies:** Documents 13, 26–37, 54–57; Analytics; Regulatory Reporting  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profile:** Drug–Device Combination Products (DDCP)  
**Date:** 2026-08-20

---

# Implementation / Claude Code Contract

This document is for direct Claude Code/Codex ingestion. Before code, extract requirement registry, module map, service/function catalogue, typed inputs/outputs, DB reads/writes and transaction boundaries, APIs/events, state machines, authorization/SoD/signatures, UI actions, errors, tests and traceability. If a missing decision changes regulated behavior, create `SPEC_GAP`; do not guess.

Documents 35 and 36 remain authoritative QMS records for complaints and field actions. This module references them and adds surveillance/signal behavior; it never duplicates or edits their regulated truth.

# Regulatory Engineering Basis

This module supports current Part 4 postmarketing-safety concepts and the surveillance/evaluation inputs used by applicable drug, biologic and device reporting regimes. Final seriousness, causality, expectedness and reportability decisions remain with authorized Safety/Regulatory personnel.

Official references:
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-4/subpart-B
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-803
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-D/part-314/subpart-B/section-314.80
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-F/part-600/subpart-D/section-600.80
- https://www.fda.gov/combination-products/guidance-regulatory-information/postmarketing-safety-reporting-combination-products

# 1. Objective

Define postmarket safety surveillance across complaints, service/repair, literature, manufacturing/QC events, field actions and external sources; normalize them into linked safety cases; detect/assess safety signals; and create controlled handoffs into QMS and formal regulatory reporting.

# 2. Actors

- Safety Intake Specialist
- Complaint Coordinator
- Medical Safety Reviewer
- Regulatory Affairs
- QA/Postmarket Quality
- Device Safety Engineer
- Pharmacovigilance Specialist
- Signal Management Committee
- Analytics Service
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| PMS-FR-001 | Source registry | Register complaint, service, repair, literature, regulator, distributor, field action, manufacturing, QC, study and external-safety sources with source owner and ingestion profile. | All safety information attributable. |
| PMS-FR-002 | Linked safety case | Create safety_case as a regulatory/surveillance layer referencing the source QMS/service record and version; do not copy source record into a second editable truth. | No duplicated QMS master. |
| PMS-FR-003 | Receipt/awareness chronology | Store source receipt, company initial receipt, regulatory-clock candidate, follow-up receipt and system ingestion timestamps separately. | Deadline reconstruction. |
| PMS-FR-004 | Product resolution | Resolve exact marketed product/application, lot/batch/serial, UDI/NDC and DDCP constituent architecture when known. | Correct regime and genealogy. |
| PMS-FR-005 | Unknown identity queue | Unknown product/lot/serial remains open data-quality task and is never discarded. | Completeness. |
| PMS-FR-006 | Controlled coding | Use versioned event, failure, complaint, device-problem and clinical coding dictionaries; retain code-system/version. | Consistent trending. |
| PMS-FR-007 | Seriousness attributes | Capture death, life-threatening, hospitalization, disability, congenital anomaly and medically-important inputs without automatically deciding reportability. | Safety assessment. |
| PMS-FR-008 | Device-event attributes | Capture death/serious-injury/malfunction candidates, caused/contributed evidence and remedial-action context. | MDR inputs. |
| PMS-FR-009 | Drug/biologic attributes | Capture adverse experience, seriousness, expectedness-reference, causality/reasonable-possibility inputs and reporter/source. | Drug/biologic inputs. |
| PMS-FR-010 | Manufacturing-event surveillance | Allow quality/manufacturing events to enter surveillance even without an injury when profile/rules make them relevant. | Combination-product breadth. |
| PMS-FR-011 | Field-action link | Document 36 field action creates a linked surveillance/regulatory source without duplicating execution data. | Postmarket/QMS connection. |
| PMS-FR-012 | Constituent attribution | Classify possible Drug, Biologic, Device, Interface, Packaging/Label, User Interaction or Unknown involvement. | DDCP analysis. |
| PMS-FR-013 | Multiple assessment tracks | One safety case can feed several independent reportability tracks while remaining one source case. | Combination-product support. |
| PMS-FR-014 | Duplicate detection | Detect probable duplicate reports using source/event/product/patient/device identifiers; original source records are retained. | No lost intake. |
| PMS-FR-015 | Duplicate linking | Link duplicates/related cases to a canonical case without destructive merge. | Integrity. |
| PMS-FR-016 | Follow-up versioning | Every material follow-up creates immutable follow-up version, receipt date, source/evidence and reassessment flags. | Dynamic case. |
| PMS-FR-017 | Expectedness reference | Expectedness assessment references exact labeling/reference-safety-information version used. | Reproducible decision. |
| PMS-FR-018 | Trend population | Define product/family/site/lot/device/constituent/event population and time window. | Meaningful metrics. |
| PMS-FR-019 | Exposure denominator | Use distribution/exposure data with source cutoff/version where available; explicitly mark denominator uncertainty. | Normalized rates. |
| PMS-FR-020 | Signal rules | Versioned statistical/business rules may flag severity/frequency shifts, clusters, recurrence or lot concentration. | Early detection. |
| PMS-FR-021 | Formal safety signal | Open signal from rule or authorized reviewer with frozen case/evidence snapshot. | Controlled signal. |
| PMS-FR-022 | Signal assessment | Assess clinical, device, drug, manufacturing, quality and genealogy evidence, plausibility, scope and action need. | Multidisciplinary review. |
| PMS-FR-023 | Signal state machine | DETECTED→TRIAGE→ASSESSMENT→REFUTED/MONITORING/CONFIRMED→ACTION→CLOSED. | Explicit lifecycle. |
| PMS-FR-024 | Escalation | Confirmed/critical signal may create CAPA, Change, Risk Review, Field Action or Document 59 reportability task. | Actionable. |
| PMS-FR-025 | Genealogy clustering | Use genealogy to identify affected component/material/device lots, equipment routes and process families. | Manufacturing intelligence. |
| PMS-FR-026 | Literature source | Literature event stores citation, source file/reference, reviewer and case/signal relationship. | Broad surveillance. |
| PMS-FR-027 | External authority source | FDA/other authority safety information can be referenced as external evidence without overwriting internal assessment. | Context. |
| PMS-FR-028 | AI advisory boundary | AI may summarize, suggest duplicates/codes/clusters; it cannot decide seriousness, causality, expectedness, reportability or closure. | Human authority. |
| PMS-FR-029 | Privacy | Patient/reporter identifiers use minimum-necessary access, encryption/pseudonymization and explicit retention. | Confidentiality. |
| PMS-FR-030 | Medical review | Where required, qualified medical reviewer records assessment, rationale, evidence and signature/time. | Qualified decision. |
| PMS-FR-031 | Regulatory handoff | Cases requiring formal legal/reporting assessment create one or more Document 59 tracks from a frozen case snapshot. | Deterministic handoff. |
| PMS-FR-032 | Periodic dataset | Qualifying cases/signals/actions are selected into immutable periodic safety dataset by application/reporting profile. | Periodic-report support. |
| PMS-FR-033 | Dashboard | Show serious cases, reportability pending, signal aging, rates, clusters, field actions and follow-up backlog. | Operational visibility. |
| PMS-FR-034 | Audit/export | Complete source→case→follow-up→signal→action history exportable with versions/signatures. | Inspection-ready. |

# 4. Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| registerPostmarketSource() | Regulatory Admin | source_type:string; organization:string; channel:string; owner_id:uuid; ingestion_profile_id:uuid | Authorized; source type/config valid | Insert versioned postmarket_source; audit | PostmarketSource | PostmarketSourceRegistered; PMS_SOURCE_INVALID; tests duplicate/unauthorized |
| createSafetyCaseLink() | Complaint/Service/Literature ingestion | source_record_type:string; source_record_id:uuid; source_record_version:int; receipt timestamps; product hints | Source exists; source/version not already linked | Insert safety_case reference and safety-only metadata; no source mutation | SafetyCase | SafetyCaseCreated; PMS_CASE_DUPLICATE_SOURCE |
| resolveMarketedProduct() | Safety intake processor | case_id:uuid; product identifiers; lot/serial/NDC/UDI | Catalogue/mappings available | Resolve marketed product/application/constituents; create resolution version | ProductResolution | SafetyProductResolved; PRODUCT_UNRESOLVED |
| classifySafetyCase() | Safety/Regulatory reviewer | case_id; classification DTO; expectedness_ref?; rationale; signature? | Reviewer authorized/qualified; latest follow-up reviewed | Insert immutable classification version; update current pointer | SafetyClassification | SafetyCaseClassified; SAFETY_CLASSIFICATION_INCOMPLETE |
| addSafetyCaseFollowup() | Intake/Safety | case_id; new_information; receipt_at; evidence_refs[] | Case active; source attributable | Insert followup; flag classification/reportability/deadline reassessment | SafetyFollowup | SafetyCaseFollowupReceived |
| findProbableDuplicates() | Processor/AI advisory | case_id; matching_policy_version | Policy released | Read candidate index; calculate match features; no merge write | DuplicateCandidate[] | SafetyDuplicateCandidatesFound |
| linkDuplicateCases() | Safety reviewer | canonical_case_id; duplicate_case_ids[]; rationale | Authorized; cases exist and versions current | Insert case_relationship rows; preserve all cases | DuplicateLinkResult | SafetyCasesLinked |
| calculateSurveillanceMetric() | Scheduled analytics | metric_definition_version; scope; period; source_cutoff | Metric definition released; source availability recorded | Read cases/exposure; calculate immutable metric snapshot | SurveillanceMetricSnapshot | PMSMetricCalculated; tests missing denominator/late data |
| evaluateSignalRules() | Scheduled/manual | metric snapshots; case set; signal_rule_versions | Rules effective | Evaluate rules and return triggers/evidence only | SignalRuleResult[] | SafetySignalRuleTriggered |
| openSafetySignal() | Safety reviewer/rule | trigger_refs[]; product/constituent scope; rationale | No duplicate open signal unless separately justified | Insert signal + frozen case/evidence snapshot | SafetySignal | SafetySignalOpened |
| assessSafetySignal() | Safety/Medical/Quality team | signal_id; assessment; scope; recommended actions; signatures | Role/SoD policy met | Insert assessment version; update state/action links | SafetySignalAssessment | SafetySignalAssessed |
| escalateSignalToQMSOrRegulatory() | Safety/Regulatory | signal_id; action_type; target_module; rationale | Signal assessed; action authorized | Call target module API; store returned cross-link | EscalationReceipt | SafetySignalEscalated |
| buildPeriodicSafetyDataset() | Periodic report service | application_id; interval_start; interval_end; report_type; cutoff | Reporting profile configured | Create immutable manifest of qualifying cases/reports/signals/actions and source versions | PeriodicSafetyDataset | PeriodicSafetyDatasetFrozen |

# 5. State Models

```text
SAFETY CASE:
RECEIVED → IDENTITY_RESOLUTION → INITIAL_CLASSIFICATION
   ├→ FOLLOWUP_PENDING → NEW_VERSION → REASSESSMENT
   ├→ REPORTABILITY_ASSESSMENT_REQUIRED
   ├→ SIGNAL_MONITORING
   └→ CLOSED_FOR_SURVEILLANCE

SIGNAL:
DETECTED → TRIAGE → ASSESSMENT
   ├→ REFUTED → CLOSED
   ├→ MONITORING → REASSESSMENT
   └→ CONFIRMED → ACTION → CLOSED
```

# 6. Data Model

## `postmarket_source`
`id, tenant_id, source_type, organization_or_system, channel, ingestion_profile_id, state, version`

## `safety_case`
```text
id uuid PK
safety_case_number varchar UNIQUE
source_record_type/id/version
source_receipt_at timestamptz
company_initial_receipt_at timestamptz
regulatory_clock_candidate_at timestamptz
system_ingested_at timestamptz
marketed_product_id uuid
application_profile_id uuid
constituent_classification jsonb
state varchar
current_classification_version bigint
version bigint
```

## `safety_case_followup`
`case_id, followup_no, receipt_at, source/evidence, changes, reassessment_flags, version`

## `safety_signal`
`signal_no, product/constituent scope, trigger refs, frozen case-set snapshot, metric/rule versions, severity, state, assessments, actions, version`

# 7. Classification Contract

Classification is not reportability. Store structured inputs for drug/biologic/device assessment plus the exact reference labeling/version used for expectedness. All reviewer-entered judgments are attributable/versioned.

# 8. Trend / Signal Architecture

```text
Complaints + Service + QMS + Manufacturing + Field Actions + Literature
                         ↓
                 Versioned metrics
                         ↓
                  Signal rules
                         ↓
                Human assessment
                         ↓
 QMS action / Field Action / Risk / Reportability
```

Metric snapshots persist formula/rule version, source cutoff, numerator, denominator/exposure source, scope and data-quality flags.

# 9. APIs

- `POST /postmarket/v1/sources`
- `POST /postmarket/v1/safety-cases`
- `POST /postmarket/v1/safety-cases/{id}/resolve-product`
- `POST /postmarket/v1/safety-cases/{id}/classifications`
- `POST /postmarket/v1/safety-cases/{id}/followups`
- `POST /postmarket/v1/safety-cases/{id}/duplicate-links`
- `POST /postmarket/v1/signals`
- `POST /postmarket/v1/signals/{id}/assessments`
- `POST /postmarket/v1/signals/{id}/escalations`
- `POST /postmarket/v1/periodic-datasets:freeze`
- `GET /postmarket/v1/dashboard`

# 10. Events

- `SafetyCaseCreated`
- `SafetyProductResolved`
- `SafetyCaseClassified`
- `SafetyCaseFollowupReceived`
- `SafetySignalRuleTriggered`
- `SafetySignalOpened`
- `SafetySignalAssessed`
- `SafetySignalEscalated`
- `PeriodicSafetyDatasetFrozen`

# 11. Authorization / Audit / Privacy

Safety classification, medical review and signal disposition are server-authorized. Patient/reporter identity is field/role restricted and may be pseudonymized. Every classification/follow-up/signal action preserves actor, time, rationale, source versions and signature when policy requires. Generic administrators cannot sign medical/regulatory assessments.

# 12. Failure / Concurrency

Use optimistic concurrency for case/signal versions. Follow-up received during review creates a new version and forces reviewer refresh. Analytics failure cannot close a signal. Missing product identity or denominator is explicit, not inferred.

# 13. UI

1. Postmarket Intake Queue
2. Safety Case
3. Product/Serial/Genealogy Lookup
4. Clinical/Device Classification
5. Follow-up
6. Duplicate Review
7. Signal Dashboard
8. Signal Assessment
9. Trend Explorer
10. Action/Handoff
11. Periodic Dataset Preview
12. Audit/Export

# 14. Stable Errors

`PMS_SOURCE_INVALID`, `PMS_CASE_DUPLICATE_SOURCE`, `PRODUCT_UNRESOLVED`, `SAFETY_CLASSIFICATION_INCOMPLETE`, `EXPECTEDNESS_REFERENCE_REQUIRED`, `MEDICAL_REVIEW_REQUIRED`, `SIGNAL_SCOPE_INVALID`, `PERIODIC_DATASET_NOT_REPRODUCIBLE`, `STALE_SAFETY_CASE_VERSION`.

# 15. Mandatory Tests

- complaint already linked;
- unknown serial later resolved;
- follow-up changes classification;
- duplicate source reports linked without deletion;
- same-lot cluster;
- denominator unavailable;
- historical metric formula version remains reproducible;
- AI suggestion rejected by reviewer;
- signal creates CAPA;
- signal creates Field Action;
- DDCP case creates multiple reportability tracks;
- concurrent follow-up during medical review forces refresh;
- privacy role denial.

# 16. Repository Structure

```text
services/gxp-api/src/modules/postmarket/surveillance/
services/gxp-api/src/modules/postmarket/signals/
apps/ebmr_frappe/ebmr/postmarket/surveillance/
contracts/events/postmarket/
validation/requirements/postmarket/
```

# 17. Acceptance Criteria

A complaint involving one autoinjector serial can be linked to exact manufacturing genealogy, classified for surveillance, compared with related trends, opened as a signal when warranted, escalated to QMS/regulatory action, and preserved without duplicating the complaint or making an autonomous legal decision.

# 18. Claude Code Prohibitions

- Never use complaint state as reportability state.
- Never derive deadlines solely from system ingestion time.
- Never destructively merge duplicate source records.
- Never allow AI to make final safety/reportability classification.
- Never create a second editable complaint/field-action truth.
