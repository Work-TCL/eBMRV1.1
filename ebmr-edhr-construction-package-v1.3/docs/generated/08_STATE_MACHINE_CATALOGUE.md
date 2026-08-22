# 08 — State Machine Catalogue

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Authoritative state models reproduced from the controlled specifications.

---


## Document 02 — System Architecture & GxP Core Technical Specification (DOC-002)

```text
Planned
  ↓
Created / Snapshot Locked
  ↓
Issued
  ↓
Ready
  ↓
In Execution
  ├── On Hold
  ├── Exception Pending
  └── In Execution
  ↓
Production Complete
  ↓
QA Review
  ├── Returned for Controlled Action
  └── QA Review
  ↓
Released / Rejected / Other Disposition
  ↓
Closed
```
```text
Not Ready
Ready
In Progress
Paused
Completed
Exception
Voided by controlled procedure
Superseded / Corrected
```
- **Owner:** `docs/architecture`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** ARC-001..018 (18); MUT-001..015 (15); SIG-001..016 (16)


## Document 09 — Product, Constituent & Regulatory Profile Master (SPEC-EBMR-000)

```text
DRAFT
  ↓ submit
UNDER_REVIEW
  ├─→ DRAFT (rework)
  ↓ approve + sign
RELEASED
  ↓ effective date reached
EFFECTIVE
  ├─→ SUSPENDED
  ├─→ SUPERSEDED
  └─→ OBSOLETE

SUSPENDED
  ├─→ EFFECTIVE (controlled reinstatement)
  └─→ OBSOLETE
```
- **Owner:** `services/gxp-api/src/modules/ebmr`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** PRD-FR-001..032 (32)


## Document 11 — Batch Execution Engine & State Machine Specification (SPEC-EBMR-002)

```text
PLANNED
  ↓ create
CREATED
  ↓ snapshot locked
ISSUED
  ↓ prerequisites ready
READY
  ↓ start
IN_EXECUTION
  ├─→ ON_HOLD
  ├─→ EXCEPTION_PENDING
  └─→ IN_EXECUTION
  ↓
PRODUCTION_COMPLETE
  ↓
QA_REVIEW
  ├─→ CONTROLLED_ACTION_REQUIRED
  └─→ RELEASE / REJECT / OTHER DISPOSITION
  ↓
CLOSED
```
```text
NOT_READY
  ↓ dependencies satisfied
READY
  ↓ claim/start
IN_PROGRESS
  ├─→ PAUSED
  ├─→ EXCEPTION
  └─→ COMPLETED
        ↓ correction
      SUPERSEDED_BY_CORRECTION
```
- **Owner:** `services/gxp-api/src/modules/ebmr`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** BAT-FR-001..036 (36)


## Document 17 — Yield, Calculations & Manufacturing Reconciliation Specification (SPEC-EBMR-008)

```text
Calculate
  ↓
Within tolerance → ACCEPTABLE
Outside tolerance
  ↓
Create/Link Deviation or Investigation
  ↓
Quality disposition
  ↓
Recalculate/Accept controlled resolution
  ↓
Release eligibility
```
- **Owner:** `services/gxp-api/src/modules/ebmr`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** YLD-FR-001..032 (32)


## Document 19 — Material Receipt, Quarantine & Quality Status Specification (SPEC-MAT-002A)

```text
EXPECTED
  ↓ receipt
RECEIVED
  ↓ initial examination
QUARANTINE
  ├─→ SAMPLING
  ├─→ TESTING
  ↓
QC_DISPOSITION_PENDING
  ├─→ RELEASED
  ├─→ REJECTED
  ├─→ RETEST_DUE
  └─→ CONDITIONAL (only configured controlled path)
```
- **Owner:** `services/gxp-api/src/modules/materials`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** RCV-FR-001..032 (32)


## Document 21 — Material Dispensing & Weighing Specification (SPEC-MAT-002C)

```text
Batch Material Requirement
  ↓
Reserve / Select Eligible Lot
  ↓
Scan Material + Lot + Container
  ↓
Verify Operator / Booth / Balance
  ↓
Calculate Target
  ↓
Tare
  ↓
Weigh / Stable Reading
  ↓
Tolerance Evaluation
  ↓
Verifier / E-Sign if required
  ↓
Create Dispensed Container + Label
  ↓
Inventory Transaction + Genealogy
  ↓
Complete
```
- **Owner:** `services/gxp-api/src/modules/materials`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** DSP-FR-001..032 (32)


## Document 23 — Native Basic QC & Sampling Specification (SPEC-QC-001)

```text
PLANNED → COLLECTED → RECEIVED → IN_TESTING → TESTING_COMPLETE → DISPOSED/RETAINED
                       └→ HOLD
```
```text
CREATED → ASSIGNED → IN_PROGRESS → ANALYST_COMPLETE → REVIEW_PENDING
        → REVIEWED/ACCEPTED
```
- **Owner:** `services/gxp-api/src/modules/qc`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** QC-FR-001..038 (38)


## Document 25 — OOS / OOT Management Specification (SPEC-QC-003)

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
- **Owner:** `services/gxp-api/src/modules/qc`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** OOS-FR-001..030 (30); OOT-FR-001..010 (10)


## Document 26 — Deviation & Investigation Management (SPEC-QMS-001)

```text
OPEN → TRIAGE → CONTAINMENT → INVESTIGATION
     → IMPACT_ASSESSMENT → DISPOSITION → QA_REVIEW → CLOSED
CLOSED → REOPENED (controlled)
PLANNED: DRAFT → PREAPPROVED → ACTIVE → EXPIRED/CLOSED
```
- **Owner:** `services/gxp-api/src/modules/qms`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** DEV-FR-001..024 (24)


## Document 27 — CAPA Management (SPEC-QMS-002)

```text
OPEN → PROBLEM_CONFIRMED → PLAN → APPROVED
     → IMPLEMENTATION → IMPLEMENTATION_VERIFIED
     → EFFECTIVENESS_MONITORING → EFFECTIVENESS_REVIEW
     → QA_CLOSURE → CLOSED
EFFECTIVENESS_FAILED → REOPEN / NEW_ACTION
```
- **Owner:** `services/gxp-api/src/modules/qms`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** CAPA-FR-001..022 (22)


## Document 28 — Nonconformance Management (SPEC-QMS-003)

```text
OPEN → SEGREGATED → EVALUATION → DISPOSITION_PENDING
     → REWORK / RETURN / SCRAP / CONDITIONAL_DISPOSITION
     → VERIFICATION → QA_CLOSURE → CLOSED
```
- **Owner:** `services/gxp-api/src/modules/qms`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** NCR-FR-001..018 (18)


## Document 29 — Change Control (SPEC-QMS-004)

```text
DRAFT → IMPACT_ASSESSMENT → RISK_REVIEW → APPROVAL
     → IMPLEMENTATION → VERIFICATION/VALIDATION
     → EFFECTIVE → POST_IMPLEMENTATION_REVIEW → CLOSED
EMERGENCY → IMPLEMENT → RETROSPECTIVE_REVIEW
```
- **Owner:** `services/gxp-api/src/modules/qms`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** CHG-FR-001..024 (24)


## Document 30 — Document Control (SPEC-QMS-005)

```text
DRAFT → REVIEW → APPROVED/RELEASED → EFFECTIVE
     → SUPERSEDED → OBSOLETE/ARCHIVED
DRAFT/REVIEW → CANCELLED
```
- **Owner:** `services/gxp-api/src/modules/qms`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** DOC-FR-001..024 (24)


## Document 31 — Training & Personnel Qualification (SPEC-QMS-006)

```text
ASSIGNED → IN_PROGRESS → ASSESSMENT_PENDING → COMPLETED
      └→ FAILED → RETRAIN/REASSESS
COMPLETED → QUALIFIED (where applicable)
QUALIFIED → EXPIRING → EXPIRED / RENEWED
```
- **Owner:** `services/gxp-api/src/modules/qms`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** TRN-FR-001..024 (24)


## Document 32 — Supplier Quality / SCAR (SPEC-QMS-007)

```text
OPEN → CONTAINMENT → SCAR_ISSUED → SUPPLIER_RESPONSE
     → INTERNAL_REVIEW → IMPLEMENTATION → EFFECTIVENESS
     → SOURCE_STATUS_DECISION → CLOSED
```
- **Owner:** `services/gxp-api/src/modules/qms`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** SCAR-FR-001..018 (18)


## Document 33 — Risk Management (SPEC-QMS-008)

```text
DRAFT → INITIAL_ASSESSMENT → CONTROLS/MITIGATION
     → RESIDUAL_ASSESSMENT → ACCEPTANCE_REVIEW → ACCEPTED
ACCEPTED → PERIODIC_REVIEW / TRIGGERED_REVIEW → NEW_VERSION
```
- **Owner:** `services/gxp-api/src/modules/qms`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** RSK-FR-001..018 (18)


## Document 34 — Internal Audit Management (SPEC-QMS-009)

```text
PLANNED → SCHEDULED → IN_PROGRESS → REPORT_DRAFT
     → REPORT_APPROVED → FINDINGS_OPEN
     → FOLLOW_UP → CLOSED
```
- **Owner:** `services/gxp-api/src/modules/qms`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** AUDIT-FR-001..017 (17)


## Document 35 — Complaint Management (SPEC-QMS-010)

```text
RECEIVED → TRIAGE → INVESTIGATION_DECISION
   ├→ NO_INVESTIGATION_JUSTIFIED
   └→ INVESTIGATION
       → REPORTABILITY_ASSESSMENT
       → CAPA/FIELD_ACTION if required
       → RESPONSE → QA_CLOSURE → CLOSED
```
- **Owner:** `services/gxp-api/src/modules/qms`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** CMP-FR-001..024 (24)


## Document 36 — Recall / Field Action Management (SPEC-QMS-011)

```text
ASSESSMENT → SCOPE_DEFINITION → REGULATORY_DECISION → APPROVAL
     → EXECUTION/NOTIFICATION → RECONCILIATION
     → EFFECTIVENESS → CLOSURE_REVIEW → CLOSED
CLOSED → EXPANDED/REOPENED (controlled)
```
- **Owner:** `services/gxp-api/src/modules/qms`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** FAR-FR-001..020 (20)


## Document 37 — Quality Metrics, Trending & Effectiveness Checks (SPEC-QMS-012)

```text
METRIC: DRAFT → RELEASED/EFFECTIVE → SUPERSEDED
SNAPSHOT: CALCULATING → COMPLETE → APPROVED/FROZEN
EFFECTIVENESS: PLANNED → OBSERVATION → EVALUATION → PASS/FAIL/INCONCLUSIVE
```
- **Owner:** `services/gxp-api/src/modules/qms`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** MET-FR-001..024 (24)


## Document 38 — Equipment, Calibration, Qualification & Maintenance (SPEC-EQP-001)

```text
PLANNED → INSTALLED → QUALIFICATION_PENDING → QUALIFIED_AVAILABLE
QUALIFIED_AVAILABLE → CALIBRATION_DUE / MAINTENANCE_DUE / OUT_OF_SERVICE / SUSPENDED
CALIBRATION/MAINTENANCE → VERIFICATION → QUALIFIED_AVAILABLE
ANY ACTIVE → RETIRED
```
- **Owner:** `services/gxp-api/src/modules/equipment`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** EQP-FR-001..030 (30)


## Document 39 — Cleaning, Sanitization & Line Clearance (SPEC-EQP-002)

```text
DIRTY → CLEANING → CLEANING_VERIFICATION → CLEAN
CLEAN → READY_FOR_USE
CLEAN → CLEAN_EXPIRED
ANY → HOLD

LINE CLEARANCE:
NOT_STARTED → IN_PROGRESS → VERIFICATION_PENDING → CLEARED
→ EXPIRED/USED
```
- **Owner:** `services/gxp-api/src/modules/equipment`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** CLN-FR-001..028 (28)


## Document 40 — Sterile / Aseptic Manufacturing Operations (SPEC-EQP-003)

```text
PREPARATION → AREA_READY → ASEPTIC_SETUP → EXECUTION
     → INTERVENTION/EXCURSION (as needed)
     → ASEPTIC_COMPLETE → QA_REVIEW

ANY CRITICAL FAILURE → HOLD / DEVIATION / IMPACT_ASSESSMENT
```
- **Owner:** `services/gxp-api/src/modules/equipment`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** ASP-FR-001..028 (28)


## Document 41 — Environmental Monitoring & Cleanroom State Control (SPEC-EQP-004)

```text
PROGRAM/SCHEDULE → SAMPLE_TASK → COLLECTED/ACQUIRED → RESULT_PENDING
     → REVIEWED
     ├→ NORMAL
     ├→ ALERT
     └→ ACTION_EXCURSION → INVESTIGATION → DISPOSITION

AREA STATUS: READY / WARNING / HOLD / NOT_READY
```
- **Owner:** `services/gxp-api/src/modules/equipment`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** EM-FR-001..026 (26)


## Document 42 — Sterilization, CIP/SIP & Sterile Filtration Management (SPEC-EQP-005)

```text
PROFILE/LOAD READY → CYCLE_STARTED → CYCLE_RUNNING
     → CYCLE_COMPLETE → REVIEW_PENDING
     ├→ ACCEPTED → STERILE/CLEAN STATUS ISSUED
     └→ FAILED/HOLD → INVESTIGATION

FILTER:
RECEIVED/ELIGIBLE → INSTALLED → PRE_USE_TEST (if required)
→ IN_USE → POST_USE_TEST → ACCEPTED / FAILED
```
- **Owner:** `services/gxp-api/src/modules/equipment`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** STR-FR-001..030 (30)


## Document 43 — Edge Gateway Runtime Architecture & Construction Specification (SPEC-EDGE-001)

```text
UNENROLLED
   ↓ enroll
ENROLLED
   ↓ config valid
CONFIGURED
   ↓ services started
RUNNING
   ├─→ DEGRADED
   ├─→ OFFLINE_UPSTREAM
   ├─→ DISK_PRESSURE
   ├─→ SECURITY_HOLD
   └─→ UPDATE_PENDING
RUNNING/DEGRADED → STOPPED
```
- **Owner:** `edge`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** EDGE-FR-001..030 (30)


## Document 53 — Integration Error Handling, Retry, Idempotency & Reconciliation (SPEC-ERP-006)

```text
PENDING
  ↓ dispatch
IN_PROGRESS
  ├→ SUCCEEDED
  ├→ RETRY_WAIT → IN_PROGRESS
  ├→ TIMEOUT_UNCERTAIN → RECONCILING
  │                         ├→ SUCCEEDED
  │                         └→ RETRY_WAIT / MANUAL_REVIEW
  ├→ BUSINESS_REJECTED → MANUAL_REVIEW
  └→ DEAD_LETTER

PENDING/RETRY_WAIT → CANCELLED (controlled, only when safe)
```
- **Owner:** `services/integration-gateway`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** INT-FR-001..030 (30)


## Document 58 — Postmarket Surveillance, Safety Case & Signal Management (SPEC-PM-001)

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
- **Owner:** `services/gxp-api/src/modules/postmarket`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** PMS-FR-001..034 (34)


## Document 59 — Regulatory Reportability Assessment & Electronic Safety Submission Management (SPEC-PM-002)

```text
CANDIDATE → ASSESSMENT_PENDING
   ├→ NOT_REPORTABLE → CLOSED_WITH_RATIONALE
   ├→ PENDING_INFO
   └→ REPORTABLE → REPORT_DRAFT → APPROVED → SUBMISSION_PENDING
                                           ├→ ACCEPTED
                                           ├→ REJECTED → CORRECTION/RESUBMIT
                                           └→ FOLLOWUP_REQUIRED
```
- **Owner:** `services/gxp-api/src/modules/postmarket`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** REG-FR-001..032 (32)


## Document 60 — Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar (SPEC-PM-003)

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
- **Owner:** `services/gxp-api/src/modules/postmarket`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** PMO-FR-001..032 (32)


## Document 61 — Security Architecture, Threat Model & Control Framework (SPEC-SEC-001)

```text
ARCHITECTURE BASELINE
   ↓
THREAT_MODEL_DRAFT
   ↓
THREATS + CONTROLS + TESTS
   ↓
RISK_REVIEW
   ├→ MITIGATE
   ├→ ACCEPT (controlled)
   └→ EXCEPTION (time-bounded)
   ↓
APPROVED SECURITY BASELINE
   ↓
CHANGE/INCIDENT/PEN_TEST → REVIEW → NEW VERSION
```
- **Owner:** `platform/security`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** SEC-THR-001..028 (28)


## Document 62 — Identity Federation, SSO, MFA, Sessions & Service Identities (SPEC-SEC-002)

```text
UNAUTHENTICATED
   ↓ federation/MFA
AUTHENTICATED
   ↓ app session
ACTIVE_SESSION
   ├→ STEP_UP_REQUIRED
   ├→ EXPIRED
   ├→ REVOKED
   └→ LOGOUT

SERVICE IDENTITY:
PROVISIONED → ACTIVE → ROTATING → REVOKED
```
- **Owner:** `platform/security`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** IAMSEC-FR-001..026 (26)


## Document 63 — Privileged Access, Support Access, Break-Glass & Administrative Security (SPEC-SEC-003)

```text
NO_ELEVATION
   ↓ request
PENDING_APPROVAL
   ├→ DENIED
   └→ ACTIVE_JIT_GRANT
           ↓
      PRIVILEGED_SESSION
           ↓
        EXPIRED/CLOSED
           ↓
        REVIEW (if required)

EMERGENCY → BREAK_GLASS_ACTIVE → CLOSED → MANDATORY_REVIEW
```
- **Owner:** `platform/security`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** PAM-FR-001..026 (26)


## Document 64 — Application, API, UI & Secure Runtime Engineering (SPEC-SEC-004)

```text
REQUEST
  ↓ authenticate
AUTH_CONTEXT
  ↓ schema/resource bounds
VALIDATED_REQUEST
  ↓ authorization/object/property checks
AUTHORIZED_REQUEST
  ↓ business/domain validation
DOMAIN_COMMAND
  ↓
RESPONSE MINIMIZATION + SECURITY HEADERS

FAILURE AT ANY SECURITY GATE → REJECT + SECURITY/AUDIT TELEMETRY AS APPLICABLE
```
- **Owner:** `platform/security`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** APPSEC-FR-001..030 (30)


## Document 65 — Secrets Management, PKI, Cryptography & Key Lifecycle (SPEC-SEC-005)

```text
SECRET/CERT:
REQUESTED → ACTIVE → ROTATING → RETIRED/REVOKED → DESTROYED (when permitted)

KEY:
GENERATED/IMPORTED → ACTIVE → DECRYPT_ONLY/RETIRING → ARCHIVED → DESTROYED
```
- **Owner:** `platform/security`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** KEY-FR-001..028 (28)


## Document 66 — Network, Tenant, Deployment Isolation & Zero-Trust Architecture (SPEC-SEC-006)

```text
INTERNET / CUSTOMER USERS
          ↓
      INGRESS ZONE
          ↓
     APP / FRAPPE
          ↓ authenticated internal calls
      GXP SERVICES
          ↓
   GXP POSTGRES / VAULT

ERP/LIMS ↔ INTEGRATION ZONE
EDGE/OT → EDGE GATEWAY → INTEGRATION ZONE

ADMIN → ZTNA/VPN/BASTION/PAM → ADMIN PLANE

DEFAULT: NO OTHER FLOWS
```
- **Owner:** `platform/security`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** NET-FR-001..030 (30)


## Document 67 — Security Logging, Monitoring, Incident Response & Forensic Evidence (SPEC-SEC-007)

```text
SECURITY EVENT
    ↓
DETECTION / ALERT
    ↓
TRIAGE
    ├→ FALSE/EXPECTED → CLOSED ALERT
    └→ INCIDENT
          ↓
       CONTAIN
          ↓
      INVESTIGATE
          ↓
ERADICATE / RECOVER
          ↓
GxP/DATA IMPACT
          ↓
POSTMORTEM / ACTIONS
          ↓
CLOSED
```
- **Owner:** `platform/security`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** MON-FR-001..030 (30)


## Document 68 — Secure SDLC, Software Supply Chain, SBOM, Vulnerability & Release Security (SPEC-SEC-008)

```text
REQUIREMENTS/THREAT MODEL
      ↓
DESIGN SECURITY REVIEW
      ↓
IMPLEMENT + CODE REVIEW
      ↓
SAST/SCA/SECRET/IAC/TEST
      ↓
BUILD + SBOM + PROVENANCE
      ↓
SECURITY RELEASE GATE
  ├→ BLOCK
  └→ PASS
       ↓
SIGN ARTIFACT
       ↓
CONTROLLED DEPLOYMENT
       ↓
MONITOR / VULNERABILITY INTAKE / PATCH
```
- **Owner:** `platform/security`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** SDLC-FR-001..034 (34)


## Document 69 — Enterprise Data Ownership, Persistence Topology & Data Lineage (SPEC-DATA-001)

```text
AUTHORITATIVE GxP WRITE
      ↓
PostgreSQL transaction
  ├ domain state
  ├ audit/version
  └ outbox
      ↓
Async projections
  ├ Frappe/MariaDB
  ├ Search
  ├ Cache
  ├ Analytics
  └ Integrations

Object evidence ← metadata/hash in GxP
Historian/Edge ← raw telemetry; GxP holds intended-use evidence refs
```
- **Owner:** `infrastructure`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** DATA-FR-001..030 (30)


## Document 70 — PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency (SPEC-DATA-002)

```text
GxP SERVICE
   ↓ pooled authenticated connection
POSTGRES PRIMARY
   ├ bounded-context schemas
   ├ domain tables
   ├ immutable versions/audit
   ├ outbox
   └ partitioned high-volume tables
      ↓ WAL/replication
READ REPLICA(S) / PITR ARCHIVE
```
- **Owner:** `infrastructure`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** PG-FR-001..034 (34)


## Document 71 — Frappe / MariaDB Operational Database, Projection & UI Data Architecture (SPEC-DATA-003)

```text
GxP PostgreSQL
    ↓ events/APIs
Projection Worker
    ↓
Frappe MariaDB
  ├ UI projections
  ├ Frappe config/meta
  ├ non-authoritative workflow UX
  └ optional ERPNext data
       ↓
Frappe UI

Regulated action: Frappe UI → GxP API → PostgreSQL → projection update
```
- **Owner:** `infrastructure`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** MDB-FR-001..028 (28)


## Document 72 — Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle (SPEC-DATA-004)

```text
UPLOAD REQUEST
   ↓
STAGED / QUARANTINED
   ↓ validate scan/type/hash
IMMUTABLE_AVAILABLE
   ↓
REFERENCED BY RECORD/VERSION/MANIFEST
   ↓
ACTIVE / ARCHIVED / COLD
   ├→ LEGAL_HOLD
   └→ PURGE_ELIGIBLE → CONTROLLED_DESTROYED
```
- **Owner:** `infrastructure`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** OBJ-FR-001..030 (30)


## Document 73 — NATS / JetStream Event Bus, Transactional Outbox & Async Contracts (SPEC-DATA-005)

```text
GxP TRANSACTION
    ├ domain state
    ├ audit/version
    └ OUTBOX(PENDING)
          ↓ publisher
      NATS/JETSTREAM
          ↓ durable consumers
   ┌──────┼──────────┐
Projection Integration Notifications
   ↓          ↓
INBOX/DEDUPE + idempotent handler

Broker down → outbox grows → catch up after recovery
```
- **Owner:** `infrastructure`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** EVT-FR-001..030 (30)


## Document 74 — Temporal Durable Workflow Orchestration Architecture (SPEC-DATA-006)

```text
DOMAIN RECORD CREATED IN GxP
         ↓ event
START TEMPORAL WORKFLOW
         ↓
DETERMINISTIC WORKFLOW LOGIC
   ├ timer/wait
   ├ signal
   └ Activity → GxP/Integration API
                    ↓
             authoritative mutation
                    ↓
              domain event/signal
                    ↓
              workflow continues

Temporal lost → orchestration pauses
GxP truth remains authoritative
```
```text
business_process_type
business_record_id
temporal_workflow_id
current_run_id (operational)
correlation_id
```
- **Owner:** `infrastructure`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** TMP-FR-001..030 (30)


## Document 75 — Caching, Search, Read Models, Reporting Projections & Analytics Data Access (SPEC-DATA-007)

```text
AUTHORITATIVE SOURCES
     ↓ events/checkpoints
READ LAYERS
  ├ Redis cache
  ├ Frappe projections
  ├ Search index
  ├ Read models/materialized views
  └ Analytics warehouse export

REGULATED ACTION → authoritative fetch/version check
```
- **Owner:** `infrastructure`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** READ-FR-001..030 (30)


## Document 76 — Backup, Restore, Point-in-Time Recovery & Disaster Recovery (SPEC-DATA-008)

```text
NORMAL
  ↓ backup/WAL/replication
PROTECTED RECOVERY SETS
  ↓ scheduled restore tests

DISASTER
  ↓ declare
CONTAIN / SELECT RECOVERY POINT
  ↓
RESTORE/PROMOTE AUTHORITATIVE STORES
  ↓
RECONCILE OBJECT EVIDENCE
  ↓
RESTORE/REBUILD DERIVED STORES
  ↓
SECURITY/GxP RECOVERY VALIDATION
  ├→ FAIL → REMEDIATE
  └→ PASS → SERVICE REOPEN
```
- **Owner:** `infrastructure`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** DR-FR-001..032 (32)


## Document 77 — Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture (SPEC-DATA-009)

```text
SOURCE + SIGNED ARTIFACTS + IaC
          ↓
DEPLOYMENT PROFILE
  ├ AWS
  ├ Azure
  └ On-Prem/Private Cloud
          ↓
PRECHECK
          ↓
INFRA APPLY / INSTALL
          ↓
DB/OBJECT/NATS/TEMPORAL
          ↓
APP/API/WORKERS/FRAPPE
          ↓
POST-INSTALL SECURITY/GxP CHECKS
          ↓
READY

UPGRADE: PRECHECK → BACKUP → MIGRATE → ROLL → SMOKE → ACCEPT/ROLLBACK
```
- **Owner:** `infrastructure`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** DEP-FR-001..035 (35)


## Document 78 — Performance, Capacity, Observability, SLOs & SRE Operations (SPEC-DATA-010)

```text
WORKLOAD / CUSTOMER GROWTH
       ↓
SLIs + CAPACITY METRICS
       ↓
SLO / FORECAST
   ├→ NORMAL
   ├→ SCALE
   ├→ TUNE
   └→ ARCHITECTURAL CAPACITY REVIEW

REQUEST → TRACE → SERVICE → DB/OUTBOX → EVENT/CONSUMER
          ↓ metrics/logs
      DASHBOARD/ALERT
          ↓
        RUNBOOK
```
- **Owner:** `infrastructure`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** SRE-FR-001..036 (36)


## Document 79 — Validation Master Plan & Computer Software Assurance Strategy (SPEC-VAL-001)

```text
DRAFT VMP → REVIEW → RELEASED → INTENDED USE/RISK → VALIDATION EXECUTION → VSR → GO-LIVE → PERIODIC REVIEW
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** VAL-FR-001..028 (28)


## Document 80 — Intended Use, GxP Criticality & Software Function Risk Classification (SPEC-VAL-002)

```text
FUNCTION → INTENDED USE → FAILURE MODE/IMPACT → RISK CATEGORY → ASSURANCE METHOD → RESIDUAL RISK APPROVAL → CHANGE REASSESSMENT
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** RISK-FR-001..022 (22)


## Document 81 — Requirements, Design Inputs & Validation Traceability Management (SPEC-VAL-003)

```text
SOURCE REQUIREMENT → VERSION → RISK + DESIGN/FUNCTION/API/SCHEMA + TEST/EVIDENCE + DEFECT → RELEASE BASELINE
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** REQ-FR-001..023 (23)


## Document 82 — Validation Test Strategy, Test Methods & Objective Evidence Governance (SPEC-VAL-004)

```text
TEST DRAFT → APPROVED → EXECUTION (AUTOMATED/SCRIPTED/EXPLORATORY) → PASS/FAIL/BLOCKED → REVIEW → TRACE/RELEASE
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** TST-FR-001..024 (24)


## Document 83 — Installation Qualification (IQ) & Installed Baseline Verification (SPEC-VAL-005)

```text
APPROVED RELEASE/PROFILE → IQ PROTOCOL → INVENTORY/CONFIG/PREREQUISITE CHECKS → DEVIATIONS → IQ APPROVAL → OQ ELIGIBLE
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** IQ-FR-001..021 (21)


## Document 84 — Operational Qualification (OQ) & Functional Control Verification (SPEC-VAL-006)

```text
IQ APPROVED → RISK-BASED OQ SUITE → FUNCTIONAL/NEGATIVE/CONCURRENCY/RECOVERY TEST → DEFECT/RETEST → OQ APPROVAL
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** OQ-FR-001..018 (18)


## Document 85 — Performance Qualification (PQ), UAT & Business Process Verification (SPEC-VAL-007)

```text
OQ APPROVED + SOP/TRAINING READY → PQ SCENARIOS → TRAINED USERS EXECUTE → OBSERVATIONS/EXCEPTIONS → CUSTOMER/QA APPROVAL
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** PQ-FR-001..020 (20)


## Document 86 — Infrastructure, Cloud, Platform & Environment Qualification (SPEC-VAL-008)

```text
DEPLOYMENT PROFILE → INFRA BASELINE → ENVIRONMENT FINGERPRINT → CONTROL/FAILOVER/SECURITY TESTS → DIFFERENCES → QUALIFIED ENVIRONMENT → DRIFT/CHANGE
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** INFQ-FR-001..020 (20)


## Document 87 — Data Migration, Conversion, Cutover & Reconciliation Validation (SPEC-VAL-009)

```text
SOURCE SNAPSHOT/PROFILE → MAPPING/TRANSFORM → DRY RUN → RECONCILE → FINAL CUTOVER/DELTA → RECONCILE → ACCEPT/ROLLBACK
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** MIGV-FR-001..022 (22)


## Document 88 — 21 CFR Part 11 Electronic Records & Electronic Signature Validation (SPEC-VAL-010)

```text
PART 11 SCOPE → CONTROL MATRIX → RECORD/SIGNATURE TESTS → CUSTOMER RESPONSIBILITY EVIDENCE → DEVIATIONS → QUALIFICATION
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** P11-FR-001..026 (26)


## Document 89 — Audit Trail, Record Version Vault & Data Integrity Validation (SPEC-VAL-011)

```text
CREATE → MODIFY/CORRECT → SIGN/RELEASE → ARCHIVE → RETRIEVE; AT EACH STAGE AUDIT/VERSION/HASH/LINEAGE → TAMPER TEST → QUALIFICATION
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** DIV-FR-001..024 (24)


## Document 90 — Integration, Edge, Device, Peripheral & Interface Validation (SPEC-VAL-012)

```text
INTERFACE CONTRACT → AUTH/SCHEMA/MAPPING → HAPPY/NEGATIVE/DUPLICATE/OUTAGE/RECOVERY → READBACK/RECONCILIATION → QUALIFIED INTERFACE
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** IFV-FR-001..024 (24)


## Document 91 — Backup, Restore, PITR & Disaster Recovery Qualification (SPEC-VAL-013)

```text
BACKUPS → FAILURE/SCENARIO → RESTORE/PITR/FAILOVER → MEASURE RPO/RTO → AUDIT/EVIDENCE/SECURITY RECONCILE → GxP SMOKE → APPROVE
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** DRV-FR-001..022 (22)


## Document 92 — Security Qualification, Vulnerability Verification & Penetration Testing (SPEC-VAL-014)

```text
THREATS/CONTROLS → AUTOMATED SCANS/TESTS → MANUAL/PEN TEST → FINDINGS → FIX/RETEST OR CONTROLLED EXCEPTION → SECURITY QUALIFICATION
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** SECQ-FR-001..024 (24)


## Document 93 — Performance, Load, Capacity & Reliability Qualification (SPEC-VAL-015)

```text
QUALIFIED ENV + WORKLOAD MODEL → LOAD/STRESS/SOAK/FAILURE → METRICS → NFR/SLO EVALUATION → HEADROOM/SIZING → APPROVE
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** PERFQ-FR-001..024 (24)


## Document 94 — Validation Defect, Deviation, Test Exception & Remediation Management (SPEC-VAL-016)

```text
FAILED/DEVIATED EVIDENCE → EXCEPTION → TRIAGE → FIX/RETEST OR RISK DISPOSITION/RELEASE BLOCK → CLOSE/REOPEN
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** VEX-FR-001..022 (22)


## Document 95 — Validation Summary Report, Release-to-Production & Go-Live Authorization (SPEC-VAL-017)

```text
VALIDATION ARTIFACTS → VSR → TRACE/DEVIATION/SECURITY/DR/PERFORMANCE/CUSTOMER READINESS → APPROVAL → VALIDATED RELEASE AUTH → DEPLOY → POST-GO-LIVE
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** VSR-FR-001..024 (24)


## Document 96 — Periodic Review, Change Impact, Revalidation & Validated-State Maintenance (SPEC-VAL-018)

```text
VALIDATED BASELINE → CHANGE/INCIDENT/PERIODIC REVIEW → IMPACT → NONE/TARGETED/PARTIAL/FULL/SUSPEND → EVIDENCE/APPROVAL → NEW BASELINE
```
- **Owner:** `validation`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** VSM-FR-001..028 (28)


## Document 98 — Architecture Rules for Claude Code / Codex (SPEC-ENG-002)

```text
1. READ applicable specs
2. IDENTIFY requirements / functions / owners
3. CHECK architecture invariants
4. CREATE implementation plan
5. IDENTIFY migrations/contracts/dependencies
6. IMPLEMENT smallest compliant change
7. RUN required tests/scans
8. UPDATE traceability/docs
9. REVIEW diff for forbidden patterns
10. REPORT actual evidence and SPEC_GAPs
```
- **Owner:** `tooling`  
- **Transition authority:** server-side domain service only (UI state is never authoritative — MUT-FR-008)  
- **Illegal transition behaviour:** deterministic rejection with `STATE_TRANSITION_INVALID`  
- **Requirements:** AGT-FR-001..036 (36)
