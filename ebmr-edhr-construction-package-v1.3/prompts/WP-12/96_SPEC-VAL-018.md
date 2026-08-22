# Claude Code prompt — WP-12 / Document 96: Periodic Review, Change Impact, Revalidation & Validated-State Maintenance

TASK:
Implement the Periodic Review, Change Impact, Revalidation & Validated-State Maintenance module (SPEC-VAL-018) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_96_Periodic_Review_Change_Impact_Revalidation_Validated_State_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: VSM-FR-001..028 (28)
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
contracts/openapi/spec-val-018.yaml
contracts/events/spec-val-018/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-val-018/
```

REQUIREMENTS TO IMPLEMENT (28):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| VSM-FR-001 | Validated baseline | Inventory software/services/config/rules/interfaces/infrastructure/procedures in validated state. | Known state. |
| VSM-FR-002 | Change trigger | Every controlled change evaluates validation impact before production. | Lifecycle. |
| VSM-FR-003 | Impact scope | Identify affected requirements/risk/functions/tests/interfaces/data/security/performance/SOP/training. | Complete impact. |
| VSM-FR-004 | Revalidation level | NONE_WITH_RATIONALE/DOC_REVIEW/TARGETED_TEST/PARTIAL/FULL_REQUALIFICATION. | Proportionate. |
| VSM-FR-005 | Emergency change | Expedited route allowed with risk/evidence and retrospective completion. | Continuity. |
| VSM-FR-006 | Patches | OS/runtime/library/security patches use risk-based impact, not blanket full regression. | CSA. |
| VSM-FR-007 | GxP config | Rule/workflow/form/signature/role/interface config change assessed. | Configured state. |
| VSM-FR-008 | Infrastructure change | DB/cloud/K8s/storage/network changes map requalification scope. | Environment. |
| VSM-FR-009 | Interface change | ERP/LIMS/device schema/version change maps requalification. | Integration. |
| VSM-FR-010 | Data change | Migration/bulk repair/master conversion receives validation scope. | Integrity. |
| VSM-FR-011 | Periodic schedule | Validated deployments reviewed at risk/contract interval. | Ongoing assurance. |
| VSM-FR-012 | Review inputs | Changes, incidents, CAPA, defects, vulnerabilities, DR, performance, access, vendor/EOL and audit trends. | Holistic. |
| VSM-FR-013 | Version support | Unsupported/EOL dependencies flagged/remediated. | Lifecycle. |
| VSM-FR-014 | Drift review | Production config/infrastructure compared to validated baseline. | State control. |
| VSM-FR-015 | Training/SOP | Procedure/training currentness/effectiveness reviewed after process change. | Human system. |
| VSM-FR-016 | Part 11 review | Identity/signature/audit/archive control changes/incidents assessed. | Compliance. |
| VSM-FR-017 | DR review | Latest restore/DR evidence and RPO/RTO issues reviewed. | Recovery. |
| VSM-FR-018 | Security review | Pen/scans/open findings/incidents/exceptions reviewed. | Cybersecurity. |
| VSM-FR-019 | Capacity review | Growth/headroom/SLO issues reviewed. | Reliability. |
| VSM-FR-020 | Customer review | Enabled modules/config/interfaces/site deviations included. | Deployment. |
| VSM-FR-021 | Decision | VALIDATED_CONFIRMED/ACTION_REQUIRED/REVALIDATION_REQUIRED/SUSPENDED. | Explicit. |
| VSM-FR-022 | Actions | Findings create Change/CAPA/validation action with owner/due date. | Improvement. |
| VSM-FR-023 | Suspension | Critical integrity/security/validation issue can suspend affected use. | Risk control. |
| VSM-FR-024 | Release continuity | Each release references prior baseline/change impact/delta or VSR. | Continuity. |
| VSM-FR-025 | Evidence | Periodic review/revalidation retained with system history. | Inspection. |
| VSM-FR-026 | Decommission | Retirement includes record archive/retrieval/access/integration shutdown. | Lifecycle end. |
| VSM-FR-027 | Supplier change | Major cloud/identity/vendor dependency change triggers impact. | External dependency. |
| VSM-FR-028 | No perpetual validation | Initial validation never means permanent assurance without controlled lifecycle. | Principle. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| assessValidationChangeImpact() | Change Control | change; changed artifacts/config; target env | ValidationChangeImpact | ValidationChangeImpactAssessed |
| approveRevalidationPlan() | Validation/QA | impact; selected tests/level; rationale | RevalidationPlan | RevalidationPlanApproved |
| executeRevalidation() | Validation/CI | plan; target release/environment | RevalidationExecution | RevalidationCompleted |
| createPeriodicReview() | Scheduled/System Owner | deployment/baseline; period | PeriodicReview | PeriodicReviewCreated |
| evaluateValidatedState() | QA/System Owner | periodic review inputs/actions | ValidatedStateDecision | ValidatedStateEvaluated |
| decommissionValidatedSystem() | System Owner/Records/QA | deployment; archive/retention/shutdown plan | DecommissionRecord | ValidatedSystemDecommissioned |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (3 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `validated_state_baseline` | 1 | PostgreSQL (GxP Core, authoritative) |
| `validation_change_impact` | 4 | PostgreSQL (GxP Core, authoritative) |
| `periodic_validation_review` | 3 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (6):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /validation/v1/change-impacts` | yes | — |
| `POST /validation/v1/revalidation-plans` | yes | — |
| `POST /validation/v1/revalidations` | yes | — |
| `POST /validation/v1/periodic-reviews` | yes | — |
| `POST /validation/v1/periodic-reviews/{id}/decision` | yes | — |
| `POST /validation/v1/decommission` | yes | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `ValidationChangeImpactAssessed` | SPEC-VAL-018 | event_id |
| `RevalidationPlanApproved` | SPEC-VAL-018 | event_id |
| `RevalidationCompleted` | SPEC-VAL-018 | event_id |
| `PeriodicReviewCreated` | SPEC-VAL-018 | event_id |
| `ValidatedStateEvaluated` | SPEC-VAL-018 | event_id |
| `ValidatedSystemDecommissioned` | SPEC-VAL-018 | event_id |

UI SURFACES:
- Validated Baseline
- Change Impact
- Revalidation Plans
- Periodic Review
- Drift/Issues
- Validated-State Decision
- Decommission

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
- security patch targeted regression
- DB major upgrade
- release rule change
- IdP change Part11 retest
- expired DR qualification
- critical incident suspension
- decommission archive
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-12/Document_96_SPEC-VAL-018_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-VAL-018/<test_case_id>/`.
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
