# Claude Code prompt — WP-09 / Document 60: Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar

TASK:
Implement the Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar module (SPEC-PM-003) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_60_Combination_Product_Postmarket_Regulatory_Coordination_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: PMO-FR-001..032 (32)
- Approved baselines: Document 106 (signature policy), 107 (SoD), 108 (retention), 109 (SLO/RPO),
  110 (precision/UOM), 111 (risk class), 112 (schemas/migrations), 113 (contracts), 114 (glossary)
- Phase-0 artefacts: `docs/generated/03_FUNCTION_CATALOGUE.csv`, `04_DATA_MODEL_CATALOGUE.md`,
  `05_DATABASE_OWNERSHIP_MATRIX.md`, `06_API_CATALOGUE.yaml`, `07_EVENT_CATALOGUE.yaml`,
  `14_ERROR_CODE_REGISTRY.md`, `28_INTENDED_USE_GXP_RISK_MATRIX.md`

RISK CLASS: **HIGHER-PROCESS-RISK** → scripted tests, independent review, mandatory negative and failure evidence

ARCHITECTURE CONSTRAINTS:
- Frappe is UI/configuration only; no core fork or edit.
- PostgreSQL is authoritative for regulated state; MariaDB holds read-only projections.
- Every regulated write goes through the Mutation Gateway → one PostgreSQL transaction carrying
  domain state + record version + audit event + outbox event.
- Signatures follow Document 04 + the approved Document 106 policy; login/MFA is never a signature.
- Audit, vault and evidence history is append-only and superseding.
- Outbox is the authoritative event source; NATS is transport; Temporal is orchestration only.
- Caches, projections, search and reports are rebuildable and never a regulated decision source.
- Adapters and edge never write GxP tables; they submit integration commands.
- AI is advisory; it cannot sign, release, disposition, approve, alter audit or submit reports.

PRECONDITIONS:
- WP-00 foundations exist (contracts tooling, guardrails, CI gates).
- WP-01 GxP Core is available (mutation, policy, signature, audit, vault, rules).
- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `services/gxp-api/src/modules/postmarket` and its tests
- `contracts/` entries owned by this module
- migrations for entities owned by this module
- Frappe UI surfaces for this module in `apps/ebmr_frappe/`

DO NOT:
- Do not modify anything under `specs/`.
- Do not implement a signature requirement not present in the approved Document 106 policy set
  (emit a policy row and reference the gap instead).
- Do not create a second authoritative store for an entity owned elsewhere.
- Do not add an endpoint to a module whose exposure boundary is "no independent API" (Document 113 §6).
- Do not write a migration for an entity absent from `docs/generated/04_DATA_MODEL_CATALOGUE.md`.
- Do not use binary floating point for a regulated quantity.
- Do not fabricate a test run, scan result or qualification record.
- Do not start work in another work package.

FILES TO CREATE/MODIFY:
```text
services/gxp-api/src/modules/postmarket/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/postmarket/migrations/     # owned entities only
services/gxp-api/src/modules/postmarket/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-pm-003.yaml
contracts/events/spec-pm-003/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-pm-003/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
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

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| configureApplicantRelationship() | Regulatory Admin | product/application IDs; applicant roles; counterpart name/address/contact; effective dates | ApplicantRelationship | ApplicantRelationshipConfigured; APPLICANT_RELATIONSHIP_INVALID |
| evaluatePart4InformationSharing() | Safety case/follow-up | safety_case_id; company_receipt_at; application/profile; applicant relationships | InformationSharingAssessment | Part4SharingAssessmentCreated |
| createConstituentSharingPackage() | Regulatory reviewer | sharing_task_id; safety information snapshot; recipient relationship version | SharingPackage | ConstituentSharingPackageCreated |
| recordConstituentInformationShared() | Regulatory user/integration | sharing_task_id; sent_at; channel; recipient; delivery_evidence | SharingReceipt | ConstituentInformationShared |
| createCorrectionRemovalAssessment() | Document 36 event | field_action_id; initiation_at; device/application profile | CorrectionRemovalAssessment | CorrectionRemovalAssessmentOpened |
| decideCorrectionRemovalReportability() | Regulatory reviewer | assessment_id; reportable:boolean; rationale; signature | CorrectionRemovalDecision | CorrectionRemovalReportabilityDecided |
| createFieldAlertAssessment() | Complaint/Deviation/OOS/Field Action | application/product; distributed batches; issue facts; applicant_receipt_at | FieldAlertAssessment | FieldAlertAssessmentOpened |
| decideFieldAlertReportability() | Regulatory/Quality reviewer | assessment_id; decision; rationale; signature | FieldAlertDecision | FieldAlertDecisionRecorded |
| createBPDRTrack() | Biologic quality/deviation event | product/application; deviation facts; discovery/receipt dates | BPDRTrack | BPDRTrackCreated |
| generatePeriodicReportingSchedule() | Regulatory calendar job | application_id; approval/license date; reporting profile; FDA overrides | PeriodicSchedule | PeriodicSafetyScheduleGenerated |
| freezePeriodicReportDataset() | Periodic report owner | cycle_id; source_cutoff | PeriodicDatasetRef | PeriodicDatasetFrozen |
| createFDAInformationRequestTask() | Regulatory user/inbound correspondence | agency letter/ref; requested info/events; due_at; received_at | FDARequestTask | FDAInformationRequestOpened |
| applyRegulatoryDeadlineOverride() | Regulatory manager | obligation_id; new_due_at; agency evidence; reason; signature | DeadlineOverride | RegulatoryDeadlineOverridden |
| calculatePostmarketRetentionPolicy() | Records Management | product/application profile; applicable regimes; record type | RetentionPolicyDecision | PostmarketRetentionPolicyCalculated |
| placePostmarketLegalHold() | Legal/Regulatory | record scope; reason; authority; effective_at | LegalHold | PostmarketLegalHoldPlaced |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (5 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `regulatory_obligation` | 12 | PostgreSQL (GxP Core, authoritative) |
| `applicant_relationship` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `constituent_information_share` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `correction_removal_regulatory_record` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `periodic_reporting_cycle` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (14):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /postmarket/v1/applicant-relationships` | yes | — |
| `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate` | yes | — |
| `POST /postmarket/v1/sharing/{id}/package` | yes | — |
| `POST /postmarket/v1/sharing/{id}/record-sent` | yes | — |
| `POST /postmarket/v1/field-actions/{id}/correction-removal-assessment` | yes | — |
| `POST /postmarket/v1/correction-removal/{id}/decision` | yes | — |
| `POST /postmarket/v1/field-alerts` | yes | — |
| `POST /postmarket/v1/field-alerts/{id}/decision` | yes | — |
| `POST /postmarket/v1/bpdr-tracks` | yes | — |
| `POST /postmarket/v1/periodic-cycles:generate` | yes | — |
| `POST /postmarket/v1/periodic-cycles/{id}/dataset:freeze` | yes | — |
| `POST /postmarket/v1/fda-requests` | yes | — |
| `POST /postmarket/v1/obligations/{id}/deadline-overrides` | yes | — |
| `POST /postmarket/v1/retention:calculate` | yes | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (15):
| Event type | Producer | Dedupe key |
|---|---|---|
| `ApplicantRelationshipConfigured` | SPEC-PM-003 | event_id |
| `Part4SharingAssessmentCreated` | SPEC-PM-003 | event_id |
| `ConstituentSharingPackageCreated` | SPEC-PM-003 | event_id |
| `ConstituentInformationShared` | SPEC-PM-003 | event_id |
| `CorrectionRemovalAssessmentOpened` | SPEC-PM-003 | event_id |
| `CorrectionRemovalReportabilityDecided` | SPEC-PM-003 | event_id |
| `FieldAlertAssessmentOpened` | SPEC-PM-003 | event_id |
| `FieldAlertDecisionRecorded` | SPEC-PM-003 | event_id |
| `BPDRTrackCreated` | SPEC-PM-003 | event_id |
| `PeriodicSafetyScheduleGenerated` | SPEC-PM-003 | event_id |
| `PeriodicDatasetFrozen` | SPEC-PM-003 | event_id |
| `FDAInformationRequestOpened` | SPEC-PM-003 | event_id |
| `RegulatoryDeadlineOverridden` | SPEC-PM-003 | event_id |
| `PostmarketRetentionPolicyCalculated` | SPEC-PM-003 | event_id |
| `PostmarketLegalHoldPlaced` | SPEC-PM-003 | event_id |

UI SURFACES:
- Applicant/Constituent Relationship
- Information Sharing Queue
- Sharing Package
- Correction/Removal Regulatory Assessment
- Field Alert Assessment
- BPDR Queue
- Periodic Safety Calendar
- Periodic Report Workspace
- FDA Requests/Correspondence
- Unified Regulatory Calendar
- Retention Basis / Legal Hold
- Inspection Dashboard

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
Fail closed on any compliance-critical dependency outage; no degraded-mode commit.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- two constituent applicants create correct sharing recipients
- missing recipient blocks completion
- 5-calendar-day sharing deadline
- reportable field action creates 10-working-day 806 obligation
- nonreportable correction/removal creates controlled 806.20 record
- scope expansion creates amendment task
- NDA Field Alert 3-working-day calculation
- biologic profile creates BPDR task
- quarterly/annual periodic cycle generation without duplicates
- Part 4 periodic augmentation
- FDA letter explicit due date
- agency extension preserves original deadline
- retention selects longest configured applicable period
- legal hold blocks purge
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-09/Document_60_SPEC-PM-003_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-PM-003/<test_case_id>/`.
- A failed case is evidence: never delete it, re-run over it, or edit the expected result to make it pass.
  Raise a defect, record the reference, re-execute as a new dated execution.

TRACEABILITY & STATUS (mandatory at the end of this prompt):
- Update `traceability/TRACEABILITY_MASTER.csv` for every requirement you touched: `build_stage`,
  `verification_state`, `test_case_ids`, `evidence_location`.
- Update `status/build-status.json`: set this module's `stage`, append to `stage_history`, set
  `requirements_state` per requirement, and set `test_pass` / `test_fail` / `test_blocked` from the
  actual recorded results.
- You may only set stages you can evidence, up to and including CODE_COMPLETE and the test states.
  `REVIEWED`, `OQ_EXECUTED`, `QUALIFIED` and `RELEASED` are set by humans, never by you.
- Run `python tooling/status/rollup.py` and include the printed summary in your completion report.

VALIDATION / TRACEABILITY:
- update `docs/generated/15_TEST_TRACEABILITY_MATRIX.csv` and `29_VALIDATION_TRACEABILITY_MASTER.csv`
- state IQ/OQ/PQ impact; HIGHER-PROCESS-RISK functions need retained objective evidence
- Part 11 impact where signatures are involved (Document 88)

ACCEPTANCE CRITERIA:
- every requirement above implemented, traced and tested
- all listed tests executed with real results
- no architecture guardrail violation
- contracts committed before implementation and compatible

SPEC_GAP RULE:
Do not guess regulated behaviour. Append unresolved decisions to `docs/generated/18_SPEC_GAPS.md`
with affected requirements, risk, options and blocking status, then continue only on unaffected work.

BEFORE COMPLETION:
Run lint, typecheck, unit, contract, integration and guardrail checks. Report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; **test cases executed with PASS/FAIL/BLOCKED counts and
the case ids of every failure**; validation impact; **traceability and status files updated (include the
rollup summary)**; unresolved SPEC_GAPs; known limitations.
