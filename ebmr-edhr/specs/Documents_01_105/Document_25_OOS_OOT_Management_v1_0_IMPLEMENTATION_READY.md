# US eBMR / eDHR Regulated Manufacturing Platform
## Document 25 — OOS / OOT Management Specification — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QC-003  
**Parent Documents:** Documents 01–22  
**Primary Dependencies:** Documents 03–24; QMS Deviation/CAPA/Change; Review/Release  
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

Define scientifically controlled investigation of Out-of-Specification results and configurable Out-of-Trend signals.

The system must prevent “testing into compliance,” suppression of original failing data, arbitrary retesting, and informal invalidation.

# 2. Critical Principle

```text
Original OOS Result
      │
      ├── always preserved
      ↓
Laboratory Investigation
      ├── proven assignable lab cause?
      │       └→ invalid test classification + evidence
      └── no proven cause
              ↓
      Broader Investigation
              ↓
      Retest/Resample only if authorized
              ↓
      Scientific conclusion + Impact + QA Disposition
```

A passing retest is **additional evidence**, not an automatic replacement for the OOS result.

# 3. Actors

- QC Analyst
- Laboratory Investigator
- QC Reviewer/Manager
- Manufacturing Investigator
- QA Investigator/Approver
- CAPA Owner
- LIMS Integration Service
- Auditor

# 4. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| OOS-FR-001 | Automatic OOS creation | Applicable result outside released specification/acceptance criterion creates OOS record automatically and links original result/sample/test/batch/material. | OOS cannot be suppressed. |
| OOS-FR-002 | Original result preservation | Original result, raw data, calculations, method, analyst, instrument, timestamps and audit remain immutable/retrievable regardless of later investigation/retest. | No result substitution. |
| OOS-FR-003 | Immediate notification | Notify QC/QA and affected batch/material workflow according to severity/profile; place release/continuation hold where configured. | Risk contained. |
| OOS-FR-004 | OOS state model | Open → Laboratory Investigation → Extended/Manufacturing Investigation if required → Impact/Disposition → QA Approval → Closed. | Controlled progression. |
| OOS-FR-005 | Phase I laboratory review | Capture analyst interview/check, method/procedure adherence, calculations, instrument status, standards/reagents, sample preparation, system suitability, raw data and obvious assignable cause evidence. | Scientific initial investigation. |
| OOS-FR-006 | Assignable cause | Only invalidate original test as analytically invalid when documented evidence supports specific assignable laboratory cause under procedure. | No speculative invalidation. |
| OOS-FR-007 | No assignable cause | If no conclusive laboratory error, proceed to broader investigation rather than declaring test invalid. | Comprehensive investigation. |
| OOS-FR-008 | Manufacturing investigation | Link batch records, process parameters, materials, equipment, environment, deviations, other batches/lots and historical trends as required. | Root cause beyond lab. |
| OOS-FR-009 | Batch/material hold | OOS can place affected batch/material/related lots on controlled hold pending investigation. | No release. |
| OOS-FR-010 | Retest plan | Retesting requires predefined/procedurally justified number of retests, method, analyst/instrument strategy and interpretation rule approved before executing retest. | No testing into compliance. |
| OOS-FR-011 | Retest authorization | Authorized QC/QA approval required before retest; original test remains. | Controlled action. |
| OOS-FR-012 | Retest result | Each retest is independent test instance linked to OOS, with complete raw data/result/review. | Full evidence. |
| OOS-FR-013 | Retest interpretation | System does not automatically average away/replace initial OOS; outcome follows released OOS procedure/rule and QA disposition. | No cherry-picking. |
| OOS-FR-014 | Resample plan | Resampling requires scientific rationale that original sample may not represent batch/material, authorization and defined sampling plan. | Controlled resampling. |
| OOS-FR-015 | Resample lineage | New sample explicitly links to original sample/OOS and captures source/location/container/quantity/time. | Trace. |
| OOS-FR-016 | Invalid test classification | Invalid result/test remains visible with reason/evidence and state; does not become deleted/hidden. | Data integrity. |
| OOS-FR-017 | Root cause | Capture root cause category/method/evidence; “unknown/no assignable cause” allowed when justified, not forced fake cause. | Scientific integrity. |
| OOS-FR-018 | Impact assessment | Assess affected batch/material/product, related lots, prior/subsequent batches, stability/complaints/other results as procedure requires. | Scope determined. |
| OOS-FR-019 | Disposition | Possible outcomes include Confirmed OOS/Reject, Laboratory Error/Invalid Test, Manufacturing Cause, No Assignable Cause with QA decision, Reprocess/Rework path where allowed. | Explicit conclusion. |
| OOS-FR-020 | CAPA link | Create/link CAPA when investigation identifies systemic/corrective/preventive action need. | QMS integration. |
| OOS-FR-021 | Change control link | Method/process/spec/system changes resulting from OOS require controlled Change Control. | No informal fix. |
| OOS-FR-022 | Closure | OOS closes only after required investigation, impact, retest/resample dispositions, linked actions and QA approval/signature complete. | No premature closure. |
| OOS-FR-023 | Reopen | New material information/evidence can reopen closed OOS through controlled workflow preserving prior closure decision. | History. |
| OOT-FR-001 | OOT rule | Define versioned trend rule by test/product/material/site using statistical/historical/business methodology approved by customer Quality. | Configurable. |
| OOT-FR-002 | OOT trigger | Result can trigger OOT while still within specification; raw result remains PASS against specification plus separate OOT flag/investigation status. | Do not mislabel as OOS. |
| OOT-FR-003 | OOT baseline | Trend rule references approved historical window/population, expected range/control logic and exclusions. | Method reproducible. |
| OOT-FR-004 | OOT state model | Open → Trend Review → Investigation/Impact → Action/Disposition → QA Approval → Closed. | Controlled. |
| OOT-FR-005 | Historical comparison | Display current result versus prior lots/batches/timepoints and relevant statistics/limits without changing official result. | Context. |
| OOT-FR-006 | OOT impact | Determine potential effect on batch/material/stability/process and whether release hold is required by profile. | Risk based. |
| OOT-FR-007 | Repeat OOT escalation | Repeated OOT signals can escalate severity/CAPA/change review according to trend rules. | Systemic detection. |
| OOT-FR-008 | Spec vs trend separation | Specification acceptance and OOT trending are separate dimensions; one does not silently modify the other. | Semantics clear. |
| OOT-FR-009 | External trend source | External LIMS/statistical tool OOT flag may be imported with source/method/version; GxP retains accepted flag/investigation linkage. | Integration. |
| OOT-FR-010 | Trend recalculation | When baseline/rule changes, historical official results remain; new trend analyses are versioned rather than rewriting past OOT decisions. | History. |
| OOS-FR-024 | Role/SoD | Analyst, investigator, QC reviewer and QA approver permissions configurable; analyst cannot unilaterally invalidate own failing result. | Independent authority. |
| OOS-FR-025 | E-signature | Key investigation/authorization/closure/disposition actions use regulated signatures per policy. | Attributable decisions. |
| OOS-FR-026 | Audit | Every investigation statement, classification, retest/resample authorization, result, conclusion, impact and closure is auditable/versioned. | Inspection-ready. |
| OOS-FR-027 | Review-by-exception | Open/closed OOS/OOT, retests, invalidated tests and impact status appear in QA Review package. | Release aware. |
| OOS-FR-028 | Release engine | Open/unresolved/confirmed OOS/OOT impacts feed explicit release blockers/warnings based on profile. | No bypass. |
| OOS-FR-029 | Metrics/trending | Dashboard OOS rate, recurring test/method/instrument/product/analyst patterns and closure aging; metrics never substitute investigation. | Quality intelligence. |
| OOS-FR-030 | Export | Generate complete investigation package with original and all subsequent data/results, approvals, impacts, audit and linked CAPA/change. | Inspection-ready. |

# 5. OOS State Machine

```text
OPEN
  ↓
LAB_INVESTIGATION
  ├─→ ASSIGNABLE_LAB_CAUSE
  │       ↓
  │   INVALID_TEST_DISPOSITION
  │       ↓
  │   QA_REVIEW
  │
  └─→ NO_ASSIGNABLE_LAB_CAUSE
          ↓
     EXTENDED_INVESTIGATION
          ↓
   RETEST / RESAMPLE (if authorized)
          ↓
      IMPACT_ASSESSMENT
          ↓
      FINAL_DISPOSITION
          ↓
       QA_APPROVAL
          ↓
         CLOSED
```

States are not exactly FDA terminology requirements; they implement a controlled product workflow aligned to current OOS guidance.

# 6. OOT State Machine

```text
OPEN
  ↓
TREND_REVIEW
  ↓
INVESTIGATION
  ↓
IMPACT / ACTION
  ↓
QA_APPROVAL
  ↓
CLOSED
```

OOT remains distinct from OOS.

# 7. Data Model

## `oos_record`

```text
id uuid PK
tenant_id uuid
site_id uuid
oos_number varchar(120)
source_result_id uuid NOT NULL
sample_id uuid
test_order_id uuid
batch_id uuid
material_lot_id uuid
state varchar(50)
severity varchar(40)
version bigint
hold_status varchar(40)
final_classification varchar(60)
root_cause_code varchar(100)
opened_at timestamptz
closed_at timestamptz
```

## `oos_investigation_activity`
- OOS ID
- phase/type
- checklist/question
- response
- evidence refs
- investigator
- timestamp
- version

## `oos_retest_plan`
- OOS
- justification
- number of retests
- method
- analyst/instrument criteria
- interpretation rule
- approver signature
- status

## `oos_resample_plan`
- scientific rationale
- sampling plan/version
- source
- approver
- resulting sample IDs

## `oot_record`
- source result
- trend rule/version
- baseline/reference
- trigger details
- state
- investigation/impact
- closure

# 8. Phase I Laboratory Investigation Checklist

Configurable template should cover:
- sample identity/handling;
- method/version/procedure adherence;
- analyst actions;
- calculations/transcriptions;
- instrument calibration/qualification/status;
- system suitability;
- standards/reagents/solutions;
- sample preparation;
- dilution;
- integration/data-processing where applicable;
- raw data completeness;
- obvious event/deviation;
- environmental/lab conditions;
- contemporaneous analyst explanation.

Checklist completion alone does not prove laboratory error.

# 9. Retest Control

Retest plan is released/approved before retest execution.

The system must prohibit:
- unlimited “try again” button;
- deleting failing injections/readings;
- replacing initial result field;
- selecting only favorable results without method/procedure basis;
- undocumented retesting.

# 10. APIs

- `POST /quality/oos/v1/from-result/{resultId}`
- `GET /quality/oos/v1/{id}`
- `POST /quality/oos/v1/{id}/lab-investigation`
- `POST /quality/oos/v1/{id}/classify-lab-cause`
- `POST /quality/oos/v1/{id}/extended-investigation`
- `POST /quality/oos/v1/{id}/retest-plans`
- `POST /quality/oos/v1/{id}/resample-plans`
- `POST /quality/oos/v1/{id}/impact`
- `POST /quality/oos/v1/{id}/disposition`
- `POST /quality/oos/v1/{id}/close`
- `POST /quality/oot/v1/evaluate`
- `POST /quality/oot/v1/{id}/close`

# 11. Error Codes

`OOS_ALREADY_EXISTS`, `ORIGINAL_RESULT_REQUIRED`, `LAB_CAUSE_EVIDENCE_REQUIRED`, `RETEST_NOT_AUTHORIZED`, `RETEST_LIMIT_REACHED`, `RESAMPLE_NOT_AUTHORIZED`, `INVESTIGATION_INCOMPLETE`, `IMPACT_ASSESSMENT_REQUIRED`, `QA_APPROVAL_REQUIRED`, `OOT_RULE_NOT_RELEASED`, `OOS_RELEASE_BLOCK_ACTIVE`.

# 12. UI

OOS:
1. OOS Header / Original Result
2. Raw Data / Method
3. Laboratory Investigation
4. Assignable Cause Decision
5. Manufacturing/Extended Investigation
6. Retest Plan/Results
7. Resample Plan/Results
8. Impact Assessment
9. CAPA/Change Links
10. Final Disposition
11. QA Closure
12. Full Audit

OOT:
1. OOT Signal
2. Trend Chart / Historical Context
3. Investigation
4. Impact/Action
5. QA Closure

# 13. Trend Engine Interface

Document 08 Rules Engine evaluates OOT rule.

Example output:
```json
{
  "rule_id":"OOT-ASSAY-001",
  "rule_version":"2.0",
  "triggered":true,
  "reason_codes":["SHIFT_FROM_10_BATCH_MEAN"],
  "baseline_ref":"...",
  "statistics":{"current":"99.1","mean":"100.2"}
}
```

Statistical methodology is customer/procedure-specific and must be validated before use.

# 14. Integration Ownership

If LIMS manages OOS investigation:
- eBMR stores original accepted result;
- creates linked OOS mirror/status;
- imports investigation status/conclusion/version/evidence;
- release engine remains aware of unresolved OOS;
- ownership matrix defines which system can transition which state.

No dual editable master.

# 15. Events

- OOSOpened
- OOSLabInvestigationStarted
- OOSAssignableCauseDetermined
- OOSExtendedInvestigationStarted
- OOSRetestAuthorized
- OOSRetestCompleted
- OOSResampleAuthorized
- OOSImpactAssessed
- OOSDispositionApproved
- OOSClosed
- OOTDetected
- OOTInvestigationStarted
- OOTClosed

# 16. Audit / Signature

Mandatory audit:
- original trigger;
- investigation entries/corrections;
- invalidation decision;
- retest/resample authorization;
- every result;
- impact;
- root cause;
- disposition;
- closure.

Signature policies may require:
- retest authorization;
- resample authorization;
- final disposition;
- closure.

# 17. Review / Release Integration

Release blocker examples:
- `OOS_OPEN`
- `OOS_CONFIRMED_REJECT`
- `OOS_IMPACT_NOT_ASSESSED`
- `OOT_REVIEW_REQUIRED`
- `RETEST_RESULT_PENDING`

A closed OOS can still result in reject/hold disposition depending on conclusion.

# 18. Repository Structure

```text
services/gxp-api/src/modules/oos/
services/gxp-api/src/modules/oot/
apps/ebmr_frappe/ebmr/oos/
apps/ebmr_frappe/ebmr/oot/
contracts/events/oos/
validation/requirements/oos/
```

# 19. Observability

Metrics:
- OOS opened/closed;
- OOS aging;
- retest frequency;
- invalid-test rate;
- OOS by product/test/method/instrument;
- OOT signals;
- repeat OOT;
- investigations overdue;
- confirmed OOS rate.

High invalid-test or retest patterns are quality signals, not performance targets to optimize away.

# 20. Implementation Sequence

1. OOS trigger/original result link;
2. laboratory investigation;
3. lab cause classification;
4. broader investigation;
5. retest plan;
6. resample plan;
7. impact/disposition;
8. closure/signature;
9. release blockers;
10. OOT rule/investigation;
11. LIMS ownership modes;
12. metrics/trending.

# 21. Test Catalogue

- automatic OOS;
- attempt to suppress OOS;
- proven calculation error;
- unproven lab error;
- retest without authorization;
- configured retest count exceeded;
- passing retest does not replace original;
- resample without rationale;
- result correction vs retest distinction;
- OOS holds batch;
- CAPA link;
- confirmed OOS reject;
- OOT within spec;
- repeated OOT escalation;
- LIMS-managed OOS status sync;
- closed OOS reopened;
- reviewer/analyst SoD;
- audit/export.

# 22. Acceptance

A representative assay OOS must be traceable from:
original sample/result/raw evidence → laboratory investigation → retest/resample authorization if applicable → all subsequent results → manufacturing impact → CAPA/change links → QA disposition/closure → batch/material release decision.

# 23. Codex / Claude Rules

Never implement “invalidate result” as delete/hide.
Never let a passing retest automatically convert initial OOS into PASS.
Never permit unlimited retesting.
Never classify OOT as OOS unless the actual result violates specification.
Never auto-generate a root cause when evidence does not support one.
