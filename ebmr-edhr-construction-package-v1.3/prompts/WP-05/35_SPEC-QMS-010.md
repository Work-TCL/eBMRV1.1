# Claude Code prompt — WP-05 / Document 35: Complaint Management

TASK:
Implement the Complaint Management module (SPEC-QMS-010) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_35_Complaint_Management_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: CMP-FR-001..024 (24)
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
- `services/gxp-api/src/modules/qms` and its tests
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
services/gxp-api/src/modules/qms/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/qms/migrations/     # owned entities only
services/gxp-api/src/modules/qms/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-qms-010.yaml
contracts/events/spec-qms-010/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-qms-010/
```

REQUIREMENTS TO IMPLEMENT (24):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| CMP-FR-001 | Complaint intake | Capture oral/written/electronic complaint from customer, patient/user, distributor, service, sales or regulator. | All channels. |
| CMP-FR-002 | Known information | Product name/strength/configuration, lot/batch/serial/UDI, complainant, date, nature, country/event details and reply where known. | Complaint file. |
| CMP-FR-003 | Acknowledgment | Track complaint acknowledgment/communication. | Customer handling. |
| CMP-FR-004 | Product identification | Resolve product/lot/serial; unknown IDs go to reconciliation queue. | Trace. |
| CMP-FR-005 | Constituent classification | Drug/device/interface/combination/packaging/label/usability/unknown. | DDCP aware. |
| CMP-FR-006 | Triage | Quality/Regulatory seriousness/criticality assessment under approved procedure. | Safety. |
| CMP-FR-007 | Investigation decision | Quality determines investigation required/not required. | 211.198 support. |
| CMP-FR-008 | No-investigation rationale | If not investigated, reason and responsible approver recorded. | 211.198 support. |
| CMP-FR-009 | Investigation | Link batch/device history, QC, deviations, materials, equipment, complaints, service and returned product. | Complete. |
| CMP-FR-010 | Returned product | Track chain of custody, testing, preservation and disposition. | Evidence. |
| CMP-FR-011 | Genealogy | Serial/lot lookup identifies constituents/materials/related product. | DDCP. |
| CMP-FR-012 | Reportability assessment | Separate authorized assessment with rationale, regime, trigger/date and due date; software does not decide legal outcome alone. | Controlled. |
| CMP-FR-013 | Part 4 PMSR profile | Support multiple constituent/application reporting regimes and information-sharing hooks. | Combination support. |
| CMP-FR-014 | Device reporting hook | MDR/eMDR reference/workflow where applicable. | Postmarket. |
| CMP-FR-015 | Drug safety hook | FAERS/safety-system reference/escalation where applicable. | Postmarket. |
| CMP-FR-016 | Trend | Complaint codes/failure mode/product/lot/constituent trend. | Signal. |
| CMP-FR-017 | CAPA | Significant/repeat complaint can create CAPA. | Systemic. |
| CMP-FR-018 | Field action | Complaint can trigger recall/field-action assessment. | Containment. |
| CMP-FR-019 | Response | Track approved response to complainant. | Communication. |
| CMP-FR-020 | Closure | Investigation decision, reportability, CAPA/field action and response complete per policy. | Complete. |
| CMP-FR-021 | Retention | Apply product/profile/predicate retention policy. | Durable. |
| CMP-FR-022 | Privacy | Restrict/minimize personal/health data. | Confidentiality. |
| CMP-FR-023 | Duplicate detection | Link duplicate reports without deleting original intake. | Integrity. |
| CMP-FR-024 | Export | Known data, investigation/follow-up or no-investigation rationale, reportability and response exportable. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `complaint_record` | 15 | PostgreSQL (GxP Core, authoritative) |
| `complaint_reportability_assessment` | 5 | PostgreSQL (GxP Core, authoritative) |
| `complaint_communication` | 4 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (7):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /qms/v1/complaints` | yes | — |
| `POST /qms/v1/complaints/{id}/triage` | yes | — |
| `POST /qms/v1/complaints/{id}/investigation-decision` | yes | — |
| `POST /qms/v1/complaints/{id}/investigation` | yes | — |
| `POST /qms/v1/complaints/{id}/reportability` | yes | — |
| `POST /qms/v1/complaints/{id}/response` | yes | — |
| `POST /qms/v1/complaints/{id}/close` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (7):
| Event type | Producer | Dedupe key |
|---|---|---|
| `ComplaintReceived` | SPEC-QMS-010 | event_id |
| `ComplaintInvestigationRequired` | SPEC-QMS-010 | event_id |
| `ComplaintInvestigationWaivedWithRationale` | SPEC-QMS-010 | event_id |
| `ComplaintReportabilityAssessmentCompleted` | SPEC-QMS-010 | event_id |
| `ComplaintCAPAOpened` | SPEC-QMS-010 | event_id |
| `ComplaintFieldActionAssessmentOpened` | SPEC-QMS-010 | event_id |
| `ComplaintClosed` | SPEC-QMS-010 | event_id |

UI SURFACES:
- Complaint Intake
- Product/Serial Lookup
- Triage
- Investigation Decision
- Manufacturing/Genealogy Evidence
- Returned Product
- Reportability Assessment
- CAPA/Field Action
- Communications
- Closure
- Trend

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- DB unavailable: no regulated transition.
- Signature/Policy unavailable: required action fails closed.
- Notification/integration failure: outbox retries; authoritative state remains.
- Stale version: reject.
- Scheduled due-date/metric jobs recover from persisted state.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- oral complaint
- unknown serial
- autoinjector constituent issue
- no-investigation rationale
- prior similar complaints
- reportability due date
- CAPA
- field action trigger
- privacy restriction
- duplicate intake
- export
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-05/Document_35_SPEC-QMS-010_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-QMS-010/<test_case_id>/`.
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
