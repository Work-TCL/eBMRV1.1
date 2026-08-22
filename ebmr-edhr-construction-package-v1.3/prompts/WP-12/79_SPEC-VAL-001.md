# Claude Code prompt — WP-12 / Document 79: Validation Master Plan & Computer Software Assurance Strategy

TASK:
Implement the Validation Master Plan & Computer Software Assurance Strategy module (SPEC-VAL-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_79_Validation_Master_Plan_CSA_Strategy_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: VAL-FR-001..028 (28)
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
- `validation` and its tests
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
validation/src/            # domain services, command handlers, repositories
validation/migrations/     # owned entities only
validation/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-val-001.yaml
contracts/events/spec-val-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-val-001/
```

REQUIREMENTS TO IMPLEMENT (28):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| VAL-FR-001 | Validation policy | Define product validation policy for DDCP/device/pharma deployment profiles. | Single strategy. |
| VAL-FR-002 | CSA applicability | Medical-device production/QMS functions use FDA 2026 CSA risk-based assurance principles. | Current FDA approach. |
| VAL-FR-003 | Drug validation basis | Drug constituent functions map Part 11/predicate rules/211.68 independently of device CSA guidance. | Correct scope. |
| VAL-FR-004 | Intended-use hierarchy | System → module → function → deployment intended use documented before assurance decision. | Risk context. |
| VAL-FR-005 | Validation plan version | Validation Master Plan versioned/released and linked to release family. | Controlled plan. |
| VAL-FR-006 | Deliverables | Define required artifacts by risk, deployment and customer responsibility. | Predictable evidence. |
| VAL-FR-007 | Responsibility matrix | Define vendor vs customer validation duties for platform, config, interfaces, SOPs, training and PQ/UAT. | Shared responsibility. |
| VAL-FR-008 | Risk-based rigor | Test method, independence and evidence depth increase with GxP/process risk. | Proportionate assurance. |
| VAL-FR-009 | Automated evidence | Controlled CI/unit/integration/system automation may provide objective validation evidence. | CSA efficiency. |
| VAL-FR-010 | Exploratory evidence | Exploratory testing permitted when risk allows and charter, actions, findings and conclusion are retained. | Flexible assurance. |
| VAL-FR-011 | Scripted evidence | Higher-risk or complex functions use detailed expected-results testing where needed. | Higher assurance. |
| VAL-FR-012 | Supplier evidence reuse | Code review, automated tests, SBOM, scans and design reviews can contribute when traceable. | Avoid duplication. |
| VAL-FR-013 | Representative environment | Qualification environment represents production configuration; differences documented/assessed. | Representative testing. |
| VAL-FR-014 | Configuration validation | Customer GxP configuration/rules/workflows/interfaces require validation beyond platform baseline. | Configured product. |
| VAL-FR-015 | Interface validation | ERP/LIMS/Edge/device interfaces separately scoped by intended use/risk. | Boundary assurance. |
| VAL-FR-016 | Migration validation | Data migration/conversion has dedicated plan/reconciliation/evidence. | Data integrity. |
| VAL-FR-017 | Part 11 validation | Electronic records/signatures/audit/copies/retention/access controls explicitly verified. | Part 11. |
| VAL-FR-018 | Infrastructure qualification | Cloud/on-prem infrastructure, backup, security and time prerequisites qualified. | Environment confidence. |
| VAL-FR-019 | Performance/security | Risk-relevant performance/security evidence required before regulated pilot. | Operational suitability. |
| VAL-FR-020 | Deviation handling | Validation deviations/defects/failures controlled; unresolved critical blockers prevent release. | No paper pass. |
| VAL-FR-021 | Traceability | Requirements ↔ risk ↔ functions ↔ tests ↔ evidence ↔ defects ↔ release. | Inspection-ready. |
| VAL-FR-022 | Approval roles | Validation author/reviewer/approver/QA release roles separated by policy. | SoD. |
| VAL-FR-023 | Customer package | Generate vendor baseline plus customer/site qualification package. | Commercial usability. |
| VAL-FR-024 | Release gate | Go-live requires approved VSR and exact validated artifact/configuration. | Controlled go-live. |
| VAL-FR-025 | Ongoing state | Periodic review/change impact/revalidation maintain validated state. | Lifecycle. |
| VAL-FR-026 | Evidence retention | Validation evidence retained according to applicable system/customer/regulatory policy. | Evidence. |
| VAL-FR-027 | Electronic validation records | Validation approvals/evidence use controlled electronic records/signatures when relied upon electronically. | Self-consistency. |
| VAL-FR-028 | No document-count metric | Assurance judged by risk coverage and evidence, not number of scripts/pages. | CSA intent. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createValidationMasterPlan() | Validation Lead | system_version; deployment_profile; regulatory_scopes; responsibility_model | ValidationMasterPlan | ValidationMasterPlanCreated |
| releaseValidationMasterPlan() | QA/Validation approver | vmp_id; version; signatures | ReleasedVMP | ValidationMasterPlanReleased |
| deriveValidationDeliverables() | Validation service | risk inventory; deployment profile; VMP version | ValidationDeliverablePlan | ValidationDeliverablesDerived |
| assignValidationResponsibility() | Validation Admin | artifact/control; vendor/customer/shared owner; rationale | ResponsibilityAssignment | ValidationResponsibilityAssigned |
| evaluateValidationReleaseGate() | Release workflow | release candidate; trace status; deviations; evidence | ValidationGateResult | ValidationReleaseGateEvaluated |
| generateValidationPackageIndex() | Validation service | release/customer/site scope | ValidationPackageIndex | ValidationPackageGenerated |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `validation_master_plan` | 6 | PostgreSQL (GxP Core, authoritative) |
| `validation_deliverable_requirement` | 6 | PostgreSQL (GxP Core, authoritative) |
| `validation_release_gate` | 4 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (4):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /validation/v1/master-plans` | yes | — |
| `POST /validation/v1/master-plans/{id}/release` | yes | policy lookup (Doc 106) |
| `GET /validation/v1/releases/{id}/gate` | no | policy lookup (Doc 106) |
| `GET /validation/v1/packages/{scope}` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (4):
| Event type | Producer | Dedupe key |
|---|---|---|
| `ValidationMasterPlanReleased` | SPEC-VAL-001 | event_id |
| `ValidationDeliverablesDerived` | SPEC-VAL-001 | event_id |
| `ValidationReleaseGateEvaluated` | SPEC-VAL-001 | event_id |
| `ValidationPackageGenerated` | SPEC-VAL-001 | event_id |

UI SURFACES:
- Validation Master Plan
- Responsibility Matrix
- Deliverables
- Release Gate
- Validation Package

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- Failed or interrupted validation execution remains recorded.
- Re-run creates a new execution linked to prior execution/deviation.
- Evidence-upload or DB failure must not produce PASS.
- Stale requirement/design/test versions cannot be approved.
- Signature failure blocks release rather than falling back to unsigned approval.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- high-risk scripted/automated evidence
- low-risk exploratory evidence
- missing customer config PQ
- open critical validation deviation
- Part 11 evidence missing
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-12/Document_79_SPEC-VAL-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-VAL-001/<test_case_id>/`.
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
