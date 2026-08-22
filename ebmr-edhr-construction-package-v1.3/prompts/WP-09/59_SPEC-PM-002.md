# Claude Code prompt — WP-09 / Document 59: Regulatory Reportability Assessment & Electronic Safety Submission Management

TASK:
Implement the Regulatory Reportability Assessment & Electronic Safety Submission Management module (SPEC-PM-002) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_59_Regulatory_Reportability_Electronic_Safety_Submission_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: REG-FR-001..032 (32)
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
contracts/openapi/spec-pm-002.yaml
contracts/events/spec-pm-002/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-pm-002/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
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

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createReportabilityTracks() | Safety classification / field action / quality event | safety_case_id:uuid; application_profile_id:uuid; constituent_set[]; source_snapshot_id | ReportabilityTrack[] | ReportabilityTracksCreated; REPORTING_PROFILE_MISSING |
| calculateRegulatoryDeadline() | Reportability service | track_id; clock_start; rule_version; calendar_profile | DeadlineCalculation | RegulatoryDeadlineCalculated; CLOCK_START_REQUIRED |
| decideReportability() | Authorized Regulatory/Safety reviewer | track_id; decision enum; rationale; evidence_refs[]; signature | ReportabilityDecision | ReportabilityDecided; REGULATORY_REVIEW_REQUIRED |
| buildRegulatoryReport() | Report author/service | report_task_id; report_schema_version; case_snapshot; reviewer entries | RegulatoryReportDraft | RegulatoryReportBuilt; REPORT_REQUIRED_DATA_MISSING |
| approveRegulatoryReport() | Regulatory approver | report_id; expected_version; signature | ApprovedRegulatoryReport | RegulatoryReportApproved |
| generateEMDRPayload() | eMDR adapter | approved MDR report; implementation_package_version | SubmissionPayload | EMDRPayloadGenerated; EMDR_SCHEMA_ERROR |
| generateAEMSPayload() | AEMS adapter | approved ICSR; e2b_profile_version | SubmissionPayload | AEMSPayloadGenerated; E2B_MAPPING_ERROR |
| submitRegulatoryReport() | Submission worker / authorized manual user | report_id; channel; payload_version; idempotency_key | SubmissionAttempt | RegulatoryReportSubmitted; SUBMISSION_TRANSPORT_FAILED |
| ingestSubmissionAcknowledgement() | ESG/eMDR/AEMS callback/poller/manual evidence | attempt_id; ack_type; external_id; status; raw_ack_ref | SubmissionStatus | SubmissionAcknowledgementReceived |
| handleSubmissionRejection() | Submission service | attempt_id; rejection_code/details | ResubmissionTask | RegulatorySubmissionRejected |
| createFollowupReportTask() | Safety follow-up / FDA request | original_report_id; new_information_receipt; rule/context | FollowupReportTask | RegulatoryFollowupRequired |
| evaluateSameEventReportDeduplication() | Regulatory reviewer | candidate_track_ids[]; rule versions; report content comparison | DeduplicationAssessment | Part4CrossReportDeduplicationEvaluated |
| freezeReportabilityAuditPackage() | Inspection/export | case_id and/or report IDs | RegulatoryEvidencePackage | RegulatoryEvidencePackageGenerated |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (4 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `reportability_track` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `regulatory_report` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `regulatory_submission_attempt` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |
| `regulatory_submission_ack` | schema in Document 112 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (10):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /regulatory/v1/cases/{caseId}/reportability-tracks` | yes | — |
| `POST /regulatory/v1/tracks/{id}/deadline:calculate` | yes | — |
| `POST /regulatory/v1/tracks/{id}/decisions` | yes | — |
| `POST /regulatory/v1/tracks/{id}/reports` | yes | — |
| `POST /regulatory/v1/reports/{id}/approve` | yes | policy lookup (Doc 106) |
| `POST /regulatory/v1/reports/{id}/payloads:generate` | yes | — |
| `POST /regulatory/v1/reports/{id}/submissions` | yes | — |
| `POST /regulatory/v1/submissions/{id}/acknowledgements` | yes | — |
| `POST /regulatory/v1/reports/{id}/followups` | yes | — |
| `POST /regulatory/v1/cases/{id}/part4-deduplication:evaluate` | yes | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- Reportability Workbench
- Regulatory Clock Panel
- MDR Assessment
- Drug/Biologic Expedited Assessment
- Part 4 Combination Assessment
- Report Builder
- Field Provenance
- Approval
- Submission Queue
- Acknowledgement/Rejection
- Follow-up Reports
- Inspection Package

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
- device death candidate and 30-day calculation
- qualifying 5-day device track
- drug serious+unexpected 15-day candidate
- device-authorized DDCP drug constituent uses configured Part 4 30-day rule
- missing clock start blocks due date
- one case has multiple independent tracks
- Part 4 same-event dedupe false because deadline differs
- eMDR schema failure
- transport success + FDA rejection
- timeout after ESG transmission
- E2B R2 before effective transition
- E2B R3 after effective transition
- follow-up creates new report
- signed not-reportable decision
- duplicate initial submission blocked
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-09/Document_59_SPEC-PM-002_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-PM-002/<test_case_id>/`.
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
