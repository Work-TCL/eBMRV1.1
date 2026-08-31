# US eBMR / eDHR Regulated Manufacturing Platform
## Document 37 — Quality Metrics, Trending & Effectiveness Checks — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-QMS-012  
**Parent Documents:** Documents 01–33  
**Primary Dependencies:** All QMS modules, Analytics, Management Review  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**V1 Vertical:** Drug–Device Combination Products (DDCP)  
**Future Profiles:** Medical Devices, Pharmaceuticals  
**Date:** 2026-08-20

---

# Implementation Standard

This document is implementation-grade. Codex/Claude Code shall not invent regulated behavior that is absent from this specification.

# Shared Quality Event Kernel

All QMS records share stable quality-event identity, tenant/site, source, severity, owner, due dates, product/batch/material/device/equipment/supplier links, evidence, relationships, audit and versioning.

# Regulatory Engineering Basis

Current verified anchors:
- 21 CFR §211.198 requires written procedures/records for drug-product complaints, Quality review, investigation determination, findings/follow-up where investigated, and documented reason/responsible person where no investigation is performed.
- Current QMSR is effective February 2, 2026 and incorporates ISO 13485:2016 by reference.
- 21 CFR Part 806 covers certain medical-device corrections/removals.
- 21 CFR Part 4 Subpart B and FDA's combination-product PMSR guidance address postmarketing safety reporting for combination products and distinct constituent/application reporting regimes.

The software supports controlled assessment, evidence, deadlines and submission references. It does not make unsupported autonomous legal/reportability decisions.

Official references:
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-C/part-211/subpart-J/section-211.198
- https://www.fda.gov/medical-devices/postmarket-requirements-devices/quality-management-system-regulation-qmsr
- https://www.ecfr.gov/current/title-21/chapter-I/subchapter-H/part-806
- https://www.fda.gov/combination-products/guidance-regulatory-information/postmarketing-safety-reporting-combination-products

# 1. Objective

Define versioned quality metrics, cross-module trending, alerting and a reusable effectiveness-check framework for CAPA, supplier actions and field actions.

# 2. Actors

- QA Management
- Process Owner
- QC Manager
- Supplier Quality
- Training Coordinator
- Management
- Auditor
- Analytics Service

# 3. Functional Requirements

| ID | Functionality | Detailed sub-functional behavior | Acceptance intent |
|---|---|---|---|
| MET-FR-001 | Metric catalogue | Controlled metric code, owner, numerator/denominator/data source, frequency/scope. | Stable semantics. |
| MET-FR-002 | Metric versioning | Formula/data mapping change creates version/effective date. | No trend distortion. |
| MET-FR-003 | Deviation metrics | Counts/rates/severity/recurrence/product/process/site/root cause/aging. | Quality. |
| MET-FR-004 | CAPA metrics | Open/overdue/cycle time/effectiveness failures/repeat issues. | CAPA health. |
| MET-FR-005 | OOS/OOT metrics | Rate by test/product/method/instrument/site and recurrence. | Lab signal. |
| MET-FR-006 | NCR metrics | Defect/nonconformance by product/supplier/process/device test. | Manufacturing. |
| MET-FR-007 | Complaint metrics | Rate/failure mode/product/lot/constituent/reportability/field-action signals. | Postmarket. |
| MET-FR-008 | Supplier metrics | Reject rate/SCAR aging/audit/performance. | Supplier. |
| MET-FR-009 | Audit metrics | Completion/overdue findings/repeat findings. | QMS. |
| MET-FR-010 | Training metrics | Overdue/expiry/failure/execution-block incidents. | Competency. |
| MET-FR-011 | Batch quality | Review/release cycle, exception count, right-first-time, yield/reconciliation failures. | Operations. |
| MET-FR-012 | Trend rules | Versioned thresholds/control rules/alerts separate from raw metric. | Signal. |
| MET-FR-013 | Normalization | Denominator/volume/time normalization explicit. | No misleading rates. |
| MET-FR-014 | Snapshot | Store source cutoff and formula version for period result. | Reproducible. |
| MET-FR-015 | Drilldown | Authorized drilldown to source records. | Evidence. |
| MET-FR-016 | Management review package | Freeze periodic quality summary/dashboard/export. | Review support. |
| MET-FR-017 | Alert/escalation | Threshold creates alert/assessment; CAPA only if configured/decided. | Controlled. |
| MET-FR-018 | Effectiveness framework | Shared criterion/period/data/result for CAPA/SCAR/field action. | Reuse. |
| MET-FR-019 | Failed effectiveness | Escalate/reopen/new action according to source policy. | No hidden fail. |
| MET-FR-020 | AI analytics | AI may summarize signals but cannot modify official metrics/actions. | Advisory. |
| MET-FR-021 | Access | Tenant/site/role restrictions. | Security. |
| MET-FR-022 | Export/API | Structured analytics export without direct write access. | BI integration. |
| MET-FR-023 | Late/corrected data | Recalculation creates new snapshot/version; prior approved package immutable. | History. |
| MET-FR-024 | Performance/freshness | Async/materialized calculations show source cutoff/freshness. | No stale ambiguity. |

# 4. State / Workflow Model

```text
METRIC: DRAFT → RELEASED/EFFECTIVE → SUPERSEDED
SNAPSHOT: CALCULATING → COMPLETE → APPROVED/FROZEN
EFFECTIVENESS: PLANNED → OBSERVATION → EVALUATION → PASS/FAIL/INCONCLUSIVE
```

# 5. Data Model

## `quality_metric_definition`
```text
id uuid PK
metric_code varchar(120)
version_no bigint
source_model_id varchar(120)
numerator_definition jsonb
denominator_definition jsonb
formula_rule_id uuid
scope_dimensions jsonb
frequency varchar(40)
threshold_rule_ids jsonb
effective_from/to
state varchar(40)
```

## `quality_metric_snapshot`
```text
id uuid PK
metric_definition_id uuid
period_start timestamptz
period_end timestamptz
scope jsonb
source_cutoff timestamptz
result jsonb
formula_version varchar(40)
state varchar(40)
created_at timestamptz
```

## `effectiveness_check`
- source module/record
- criterion
- metric/data source
- observation period
- due date
- result/evidence
- reviewer/signature


# 6. APIs

- `POST /quality-metrics/v1/definitions`
- `POST /quality-metrics/v1/definitions/{id}/release`
- `POST /quality-metrics/v1/calculate`
- `GET /quality-metrics/v1/dashboard`
- `POST /quality-metrics/v1/management-review-packages`
- `POST /effectiveness/v1/checks`
- `POST /effectiveness/v1/checks/{id}/evaluate`

All regulated mutations pass through the GxP Mutation Gateway.

# 7. UI Screens

1. Quality Dashboard
2. Metric Catalogue
3. Deviation/CAPA/OOS/NCR Trends
4. Complaint/Supplier Trends
5. Training/Audit Trends
6. Batch Quality
7. Alert Queue
8. Effectiveness Checks
9. Management Review Package

# 8. Events

- `QualityMetricCalculated`
- `QualityTrendThresholdExceeded`
- `QualitySignalAssessmentOpened`
- `EffectivenessCheckDue`
- `EffectivenessCheckPassed`
- `EffectivenessCheckFailed`
- `ManagementReviewPackageFrozen`

# 9. Authorization / Signature / Audit

- Server-side authorization controls every state transition.
- High-risk decisions/closures use regulated signatures when applicable.
- Corrections preserve original values/evidence.
- Regulatory/reportability decisions require authorized human review.
- Admin/service identities cannot impersonate Quality/Regulatory signers.

# 10. Failure / Recovery

- DB unavailable: no regulated transition.
- Signature/Policy unavailable: required action fails closed.
- Notification/integration failure: outbox retries; authoritative state remains.
- Stale version: reject.
- Scheduled due-date/metric jobs recover from persisted state.

# 11. Repository Structure

```text
services/gxp-api/src/modules/qms/quality-metrics,-trending-and-effectiveness-checks/
apps/ebmr_frappe/ebmr/qms/quality-metrics,-trending-and-effectiveness-checks/
contracts/events/qms/quality-metrics,-trending-and-effectiveness-checks/
validation/requirements/qms/quality-metrics,-trending-and-effectiveness-checks/
```

# 12. Implementation Sequence

1. Core record/state.
2. Evidence/relationship model.
3. Authorization/signature/audit.
4. Cross-module integrations.
5. UI and dashboards.
6. Events/outbox/notifications.
7. Reports/exports.
8. Negative/failure tests.
9. Validation traceability.

# 13. Test Catalogue

- metric version change
- late correction recalculation
- CAPA effectiveness pass/fail
- threshold alert
- drilldown
- site isolation
- AI advisory only
- frozen management snapshot

# 14. Acceptance Criteria

Historical metric values and management-review packages are reproducible from exact formula version, source cutoff and source records.

# 15. Codex / Claude Code Rules

- Never recompute old approved snapshot in place.
- Never let AI modify official metric.
- Never auto-create/close CAPA solely from analytics without configured Quality assessment.

# 16. Stable Error Codes
`METRIC_DEFINITION_NOT_RELEASED`, `METRIC_SOURCE_INCOMPLETE`, `SNAPSHOT_STALE`, `EFFECTIVENESS_CRITERION_REQUIRED`, `EFFECTIVENESS_INCONCLUSIVE`, `MANAGEMENT_PACKAGE_FROZEN`.
