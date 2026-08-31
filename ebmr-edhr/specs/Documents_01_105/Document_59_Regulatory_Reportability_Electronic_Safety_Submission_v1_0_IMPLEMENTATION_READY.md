# US eBMR / eDHR Regulated Manufacturing Platform
## Document 59 — Regulatory Reportability Assessment & Electronic Safety Submission Management — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-PM-002  
**Parent Documents:** Documents 01–58  
**Primary Dependencies:** Documents 35, 36, 58; Part 4; MDR/eMDR; AEMS; Evidence/Vault  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profile:** Drug–Device Combination Products (DDCP)  
**Date:** 2026-08-20

---

# Implementation / Claude Code Contract

Direct Claude Code/Codex specification. Before code, extract every reportability track, trigger, deadline rule, decision authority, function, input/output, DB effect, submission schema/transport, acknowledgement state, error, retry rule and validation test. Legal/reportability decisions are human Regulatory/Safety decisions; rules may only calculate candidate applicability and deadlines.

# Current Regulatory / Submission Baseline

- 21 CFR Part 803 generally requires device manufacturers to report reportable deaths, serious injuries and malfunctions within 30 calendar days; qualifying 5-day situations use 5 work days. Manufacturer/importer MDR reports are generally electronic.
- §314.80 and §600.80 include 15-calendar-day serious/unexpected postmarketing reporting and follow-up.
- Part 4 adds constituent-based requirements and can modify timing/routing; for certain device-authorized combination products, constituent drug/biologic 15-day reports use 30 calendar days.
- FDA eMDR currently uses ESG NextGen.
- FDA AEMS accepts E2B(R3); for postmarketing ICSRs submitted via ESG NextGen, FDA states E2B(R3) becomes required October 1, 2026, with E2B(R2) accepted through September 30, 2026 for firms not yet transitioned. Once a firm transitions to R3, it should not revert.

Official references:
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-A/part-4/subpart-B
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-803
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-D/part-314/subpart-B/section-314.80
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-F/part-600/subpart-D/section-600.80
- https://www.fda.gov/medical-devices/mandatory-reporting-requirements-manufacturers-importers-and-device-user-facilities/emdr-electronic-medical-device-reporting
- https://www.fda.gov/drugs/fda-adverse-event-monitoring-system-aems/fda-adverse-event-monitoring-system-aems-electronic-submissions

# 1. Objective

Define reportability assessment, regulatory clocks, report construction, approval, electronic/manual submission, acknowledgement, rejection recovery and follow-up for device, drug, biologic and combination-product postmarket safety reports.

# 2. Actors

- Safety Case Manager
- Medical Safety Reviewer
- Regulatory Affairs Specialist
- Regulatory Approver
- Pharmacovigilance
- Device Vigilance/MDR Specialist
- eMDR Submission Service
- AEMS/E2B Submission Service
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| REG-FR-001 | Independent reportability tracks | One safety case can have multiple independent tracks by report type/regime. | DDCP support. |
| REG-FR-002 | Application context | Track NDA/ANDA/BLA/device application plus combination-product applicant vs constituent-part applicant role. | Correct applicability. |
| REG-FR-003 | Versioned report catalogue | Report types/rules are effective-dated configuration: MDR 30-day, MDR 5-day, malfunction, drug/biologic expedited, follow-up/supplemental and future report types. | No hardcoded legal logic. |
| REG-FR-004 | Human decision authority | Rules calculate candidate applicability and deadlines; authorized reviewer makes final REPORTABLE/NOT_REPORTABLE/PENDING decision. | No autonomous legal decision. |
| REG-FR-005 | Clock-start basis | Each track stores source receipt/awareness basis, selected clock start, rationale, reviewer and rule version. | Explainable deadline. |
| REG-FR-006 | Calendar engine | Support CALENDAR_DAY, WORK_DAY, WORKING_DAY and explicit agency due dates with versioned calendars. | Correct time computation. |
| REG-FR-007 | MDR 30-day track | Support applicable manufacturer 30-calendar-day death/serious-injury/malfunction reporting. | Part 803. |
| REG-FR-008 | MDR 5-day track | Support qualifying 5-work-day remedial-action/FDA-request reporting. | Part 803. |
| REG-FR-009 | Malfunction assessment | Capture malfunction, recurrence-consequence rationale, device evaluation and evidence. | MDR basis. |
| REG-FR-010 | Drug expedited track | Support serious+unexpected drug adverse-experience 15-calendar-day candidate. | 314.80. |
| REG-FR-011 | Biologic expedited track | Support serious+unexpected biologic adverse-experience 15-calendar-day candidate. | 600.80. |
| REG-FR-012 | Part 4 modified timing | Support applicable 30-calendar-day constituent drug/biologic expedited timing for device-authorized combination products. | Combination timing. |
| REG-FR-013 | Follow-up/supplemental | New information can create follow-up report task with original report link and own rule/deadline. | Ongoing reporting. |
| REG-FR-014 | Report schema | Every report type uses versioned canonical data-element schema and versioned transport mapper. | Submission quality. |
| REG-FR-015 | Missing information | Required unavailable data is represented as unknown/not obtained with follow-up task where applicable; never fabricated. | Integrity. |
| REG-FR-016 | Field provenance | Each report field traces to safety case, complaint, product, genealogy, investigation or attributable reviewer entry. | Auditability. |
| REG-FR-017 | Narrative control | Medical/regulatory narrative is versioned, reviewed and approved/signed per policy. | Controlled content. |
| REG-FR-018 | eMDR payload | Generate validated eMDR payload through versioned implementation-package/profile mapper. | Electronic device reporting. |
| REG-FR-019 | eMDR acknowledgements | Track submission/processing acknowledgements and accepted/rejected state; send success alone is not FDA acceptance. | Submission proof. |
| REG-FR-020 | AEMS ICSR payload | Generate drug/biologic ICSR through configured E2B(R2/R3) profile and ESG NextGen, or controlled SRP/manual workflow if applicable. | Electronic safety reporting. |
| REG-FR-021 | E2B effective date | E2B standard is effective-dated config with R3 transition support; do not code one permanent format. | Future proof. |
| REG-FR-022 | Manual submission fallback | If automated connector unavailable, create approved submission package and require manual transmission evidence. | Business continuity. |
| REG-FR-023 | Attempt ledger | Every transmission attempt stores report/payload version/hash, sender/service identity, channel, endpoint/profile, timestamp, response and external correlation. | Evidence. |
| REG-FR-024 | Submitted payload immutability | Submitted payload cannot be edited; correction/follow-up creates new report/payload version. | History. |
| REG-FR-025 | Duplicate submission prevention | Prevent accidental second initial submission of same approved report version. | Idempotency. |
| REG-FR-026 | Rejected submission | Rejected payload creates correction/resubmission workflow preserving original payload/ack. | Recoverability. |
| REG-FR-027 | Deadline escalation | Due-soon/overdue tracks escalate to configured Regulatory management roles. | Timeliness. |
| REG-FR-028 | Exemption/alternate arrangement | Approved reporting exemption/alternate arrangement is versioned evidence/rule, not a code bypass. | Flexibility. |
| REG-FR-029 | Periodic linkage | Expedited/device reports feed applicable periodic-report datasets/summary rules. | Cross-report integration. |
| REG-FR-030 | Part 4 same-event dedupe | Evaluate whether one report can satisfy multiple requirements only when required content, manner and deadline conditions are met and reviewer approves. | Avoid duplicate reporting correctly. |
| REG-FR-031 | FDA information request | Agency request creates task with exact request reference, events/information requested and explicit agency due date. | Regulatory response. |
| REG-FR-032 | Audit/export | Export rule version, decisions, deadlines, report versions, payloads, acknowledgements, follow-ups and signatures. | Inspection-ready. |

# 4. Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createReportabilityTracks() | Safety classification / field action / quality event | safety_case_id:uuid; application_profile_id:uuid; constituent_set[]; source_snapshot_id | Product/application resolved; rule catalogue effective | Insert candidate reportability_track rows; no final yes/no decision | ReportabilityTrack[] | ReportabilityTracksCreated; REPORTING_PROFILE_MISSING |
| calculateRegulatoryDeadline() | Reportability service | track_id; clock_start; rule_version; calendar_profile | Rule applicable; clock start available/reviewed | Calculate due_at and basis/calendar metadata; insert deadline version | DeadlineCalculation | RegulatoryDeadlineCalculated; CLOCK_START_REQUIRED |
| decideReportability() | Authorized Regulatory/Safety reviewer | track_id; decision enum; rationale; evidence_refs[]; signature | Reviewer authorized/qualified; case/version current | Insert signed decision version; if reportable create report task | ReportabilityDecision | ReportabilityDecided; REGULATORY_REVIEW_REQUIRED |
| buildRegulatoryReport() | Report author/service | report_task_id; report_schema_version; case_snapshot; reviewer entries | Track REPORTABLE; schema/profile effective | Assemble canonical dataset with field-level provenance; insert report draft/version | RegulatoryReportDraft | RegulatoryReportBuilt; REPORT_REQUIRED_DATA_MISSING |
| approveRegulatoryReport() | Regulatory approver | report_id; expected_version; signature | Validation checks pass; current source snapshot reviewed | Freeze report/narrative/payload-source dataset in Vault; status APPROVED | ApprovedRegulatoryReport | RegulatoryReportApproved |
| generateEMDRPayload() | eMDR adapter | approved MDR report; implementation_package_version | Report routes to eMDR; mapper/schema validated | Map canonical report to electronic MDR payload; hash/store generated payload | SubmissionPayload | EMDRPayloadGenerated; EMDR_SCHEMA_ERROR |
| generateAEMSPayload() | AEMS adapter | approved ICSR; e2b_profile_version | Report routes to AEMS; effective E2B profile | Map canonical report to configured E2B payload/attachments; hash/store | SubmissionPayload | AEMSPayloadGenerated; E2B_MAPPING_ERROR |
| submitRegulatoryReport() | Submission worker / authorized manual user | report_id; channel; payload_version; idempotency_key | Approved; channel active; report version not already accepted | Insert attempt; send or produce manual package; store external correlation | SubmissionAttempt | RegulatoryReportSubmitted; SUBMISSION_TRANSPORT_FAILED |
| ingestSubmissionAcknowledgement() | ESG/eMDR/AEMS callback/poller/manual evidence | attempt_id; ack_type; external_id; status; raw_ack_ref | Ack source authenticated/authorized; attempt exists | Append immutable ack; calculate submission state via profile | SubmissionStatus | SubmissionAcknowledgementReceived |
| handleSubmissionRejection() | Submission service | attempt_id; rejection_code/details | Ack says rejected | Create correction/resubmission task; preserve report/payload | ResubmissionTask | RegulatorySubmissionRejected |
| createFollowupReportTask() | Safety follow-up / FDA request | original_report_id; new_information_receipt; rule/context | Original submitted; follow-up condition met | Create linked followup task/deadline and source snapshot | FollowupReportTask | RegulatoryFollowupRequired |
| evaluateSameEventReportDeduplication() | Regulatory reviewer | candidate_track_ids[]; rule versions; report content comparison | Part 4 context active | Compare required content/manner/deadline and return eligibility analysis; no auto-close | DeduplicationAssessment | Part4CrossReportDeduplicationEvaluated |
| freezeReportabilityAuditPackage() | Inspection/export | case_id and/or report IDs | Records current/readable | Create evidence manifest of decisions/rules/payloads/acks/source refs | RegulatoryEvidencePackage | RegulatoryEvidencePackageGenerated |

# 5. Reportability Track Model

```text
Safety Case
 ├─ MDR 30-day
 ├─ MDR 5-day
 ├─ Malfunction
 ├─ Drug expedited / Part 4 modified
 ├─ Biologic expedited / Part 4 modified
 ├─ Correction/Removal assessment (Doc 60)
 ├─ Field Alert assessment (Doc 60)
 └─ BPDR assessment (Doc 60)
```

Each track has its own rule version, clock start, decision, due date, report task, submission channel and acknowledgements.

# 6. State Machine

```text
CANDIDATE → ASSESSMENT_PENDING
   ├→ NOT_REPORTABLE → CLOSED_WITH_RATIONALE
   ├→ PENDING_INFO
   └→ REPORTABLE → REPORT_DRAFT → APPROVED → SUBMISSION_PENDING
                                           ├→ ACCEPTED
                                           ├→ REJECTED → CORRECTION/RESUBMIT
                                           └→ FOLLOWUP_REQUIRED
```

# 7. Deadline Rule

```ts
type RegulatoryDeadlineRule = {
  id: string; reportType: string; applicabilityExpressionId: string;
  duration: number; unit: "CALENDAR_DAY"|"WORK_DAY"|"WORKING_DAY";
  clockStartDefinition: string; applicationTypeConditions: string[];
  constituentConditions: string[]; effectiveFrom: string; sourceCitation: string;
};
```

Deadline rules are versioned configuration in GxP PostgreSQL/Vault-backed regulatory configuration. UI never hardcodes deadlines.

# 8. Current Reference Rule Examples

- `MDR_30_DAY`: 30 calendar days where applicable.
- `MDR_5_DAY`: 5 work days where applicable.
- `DRUG_15_DAY`: 15 calendar days.
- `BIOLOGIC_15_DAY`: 15 calendar days.
- `PART4_DEVICE_LED_DRUG_OR_BIO_CONSTITUENT_EXPEDITED`: 30 calendar days only where §4.102 condition applies.

These examples do not bypass applicability review.

# 9. Electronic Submission Architecture

```text
Canonical Regulatory Report
        ↓
Report-Type Mapper
   ├─ eMDR mapper
   ├─ AEMS E2B mapper
   └─ Manual package mapper
        ↓
Transport: ESG NextGen / configured manual channel
        ↓
Acknowledgements / FDA accepted or rejected state
```

Transport adapters never decide reportability.

# 10. E2B Transition Configuration

Reference deployment configuration:
```yaml
aems:
  transport: ESG_NEXTGEN
  profiles:
    - standard: E2B_R2
      effective_to: 2026-09-30
    - standard: E2B_R3
      effective_from: 2026-10-01
```
Actual deployment must validate against then-current FDA implementation guides. Once a customer has transitioned to R3, connector policy must prohibit reverting unless FDA instructions then permit it.

# 11. Data Model

## `reportability_track`
`id, safety_case_id, report_type, application_profile_id, rule_version_id, state, clock_start_at, deadline_at, decision, rationale, decision_signature_id, version`

## `regulatory_report`
`track_id, report_version, canonical_dataset jsonb, narrative, source_snapshot_id, approval_signature_id, vault_object_id, payload_hash, state`

## `regulatory_submission_attempt`
`report_id/version, channel, transport/profile version, payload_hash, idempotency_key, sent_at, external_correlation, status, error, version`

## `regulatory_submission_ack`
`attempt_id, ack_type, external_id, received_at, status, raw_evidence_ref`

# 12. Field Provenance

Every report field records value, source record/version, mapping rule, manual-entry actor if applicable and correction history. Submitted payloads reference the frozen canonical report version.

# 13. APIs

- `POST /regulatory/v1/cases/{caseId}/reportability-tracks`
- `POST /regulatory/v1/tracks/{id}/deadline:calculate`
- `POST /regulatory/v1/tracks/{id}/decisions`
- `POST /regulatory/v1/tracks/{id}/reports`
- `POST /regulatory/v1/reports/{id}/approve`
- `POST /regulatory/v1/reports/{id}/payloads:generate`
- `POST /regulatory/v1/reports/{id}/submissions`
- `POST /regulatory/v1/submissions/{id}/acknowledgements`
- `POST /regulatory/v1/reports/{id}/followups`
- `POST /regulatory/v1/cases/{id}/part4-deduplication:evaluate`

# 14. UI

1. Reportability Workbench
2. Regulatory Clock Panel
3. MDR Assessment
4. Drug/Biologic Expedited Assessment
5. Part 4 Combination Assessment
6. Report Builder
7. Field Provenance
8. Approval
9. Submission Queue
10. Acknowledgement/Rejection
11. Follow-up Reports
12. Inspection Package

# 15. Stable Errors

`REPORTING_PROFILE_MISSING`, `CLOCK_START_REQUIRED`, `REGULATORY_REVIEW_REQUIRED`, `REPORT_REQUIRED_DATA_MISSING`, `REPORT_SCHEMA_NOT_EFFECTIVE`, `EMDR_SCHEMA_ERROR`, `E2B_MAPPING_ERROR`, `SUBMISSION_CHANNEL_UNAVAILABLE`, `SUBMISSION_DUPLICATE_BLOCKED`, `SUBMISSION_REJECTED`, `FOLLOWUP_DEADLINE_MISSING`, `STALE_REPORT_VERSION`.

# 16. Mandatory Tests

- device death candidate and 30-day calculation;
- qualifying 5-day device track;
- drug serious+unexpected 15-day candidate;
- device-authorized DDCP drug constituent uses configured Part 4 30-day rule;
- missing clock start blocks due date;
- one case has multiple independent tracks;
- Part 4 same-event dedupe false because deadline differs;
- eMDR schema failure;
- transport success + FDA rejection;
- timeout after ESG transmission;
- E2B R2 before effective transition;
- E2B R3 after effective transition;
- follow-up creates new report;
- signed not-reportable decision;
- duplicate initial submission blocked.

# 17. Repository Structure

```text
services/gxp-api/src/modules/postmarket/reportability/
services/integration-gateway/src/regulatory/emdr/
services/integration-gateway/src/regulatory/aems/
apps/ebmr_frappe/ebmr/postmarket/reportability/
contracts/regulatory/
validation/requirements/postmarket-reporting/
```

# 18. Acceptance Criteria

A DDCP safety case can be evaluated under all applicable report types, produce independent explainable deadlines, create an approved report with field-level provenance, transmit through configured FDA channel, preserve acknowledgements/rejections, and manage follow-up without altering the source safety case.

# 19. Claude Code Prohibitions

- Never let rule output become final legal reportability without authorized review.
- Never treat HTTP/transport success as FDA acceptance.
- Never overwrite a submitted payload.
- Never permanently hardcode E2B(R2) or E2B(R3).
- Never calculate all deadlines as calendar days.
