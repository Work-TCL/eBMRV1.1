# Claude Code prompt — WP-02 / Document 10: Master Recipe / Master Manufacturing Record Specification

TASK:
Implement the Master Recipe / Master Manufacturing Record Specification module (SPEC-EBMR-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_10_Master_Recipe_Master_Manufacturing_Record_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: RCP-FR-001..036 (36)
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
- `services/gxp-api/src/modules/ebmr` and its tests
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
services/gxp-api/src/modules/ebmr/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/ebmr/migrations/     # owned entities only
services/gxp-api/src/modules/ebmr/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-ebmr-001.yaml
contracts/events/spec-ebmr-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-ebmr-001/
```

REQUIREMENTS TO IMPLEMENT (36):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| RCP-FR-001 | Recipe family | Create recipe/MMR family under exact product version/profile and manufacturing site scope. | Recipe has clear governing product. |
| RCP-FR-002 | Recipe version lifecycle | Draft, review, approved/released, effective, superseded, obsolete, suspended. Released version immutable. | Production only uses eligible release. |
| RCP-FR-003 | Batch-size variants | Support controlled batch-size variants and scaling policy; drug profile may require distinct master records by batch size as applicable. | Scaling is never an uncontrolled multiplier. |
| RCP-FR-004 | Structured sections | Recipe contains ordered sections/stages with purpose, area, expected duration and dependencies. | No single free-text blob. |
| RCP-FR-005 | Step definition | Each step has stable step ID, instruction, type, sequence/dependencies, performer role, inputs, outputs, validations and completion criteria. | Executable semantics explicit. |
| RCP-FR-006 | Step types | Support Instruction, Data Entry, Scan, Weigh, Equipment Check, Calculation, IPC/QC, Signature, Verification, Timer, Hold Point, Material Consume, Assembly, Test, Packaging, Custom Approved Type. | Common engine reusable. |
| RCP-FR-007 | Dependencies | Directed dependency graph supports sequential, parallel and join behavior without cycles unless an explicitly modelled repeat/rework structure is used. | Graph validates before release. |
| RCP-FR-008 | Conditional branches | Released rule determines branch based on structured result; operator cannot choose hidden uncontrolled path. | Branch reason auditable. |
| RCP-FR-009 | Material requirements | Each requirement references material/component specification, target quantity/formula, tolerance, stage and alternative-policy reference. | Wrong material blocked. |
| RCP-FR-010 | Equipment requirements | Step references equipment class/asset eligibility, qualification/calibration/cleaning status and optional redundancy. | Equipment checks enforceable. |
| RCP-FR-011 | Personnel requirements | Step references roles, training and qualifications including independent verifier where required. | Execution gating possible. |
| RCP-FR-012 | Area/environment requirement | Step references permitted site/area/room/line and environmental/sterile profile. | Execution location constrained. |
| RCP-FR-013 | Parameter definition | Structured parameter includes code, label, type, UOM, source, target/limits, precision, mandatory flag and rule references. | Data capture validated. |
| RCP-FR-014 | Source type | Parameter source can be Manual, Device/Edge, Calculated, LIMS, ERP, Imported Evidence or System; allowed fallback explicitly configured. | Manual substitution cannot occur silently. |
| RCP-FR-015 | Manual fallback policy | If automated source unavailable, rule defines whether manual entry is prohibited or allowed with reason, qualification and verification/signature. | Fallback controlled. |
| RCP-FR-016 | Calculation reference | Recipe references released calculation/rule version from Document 08. | No embedded arbitrary formula. |
| RCP-FR-017 | IPC/QC point | Step can create required sample/test orders, acceptance criteria and continuation/release hold. | QC integrated. |
| RCP-FR-018 | Timer/hold time | Step may start, pause or stop controlled timer with max/min duration and exception behavior. | Time limits enforced. |
| RCP-FR-019 | Electronic-signature requirement | Recipe specifies signature policy by step/action without embedding authentication mechanics. | Document 04 reused. |
| RCP-FR-020 | Independent verification | Step supports performer/verifier and history-aware SoD. | Independent check enforced. |
| RCP-FR-021 | Attachment/evidence requirement | Step can require photo, instrument file, document, certificate or machine evidence with type constraints. | Evidence completeness testable. |
| RCP-FR-022 | Instruction version integrity | Instruction shown at execution comes from exact issued recipe snapshot. | Later edits cannot change open batch. |
| RCP-FR-023 | Line clearance/cleaning | Recipe may require prerequisite line-clearance/cleaning evidence before stage start. | Packaging/sterile controls integrated. |
| RCP-FR-024 | Sterile-specific step metadata | For applicable profile, support intervention classification, sterile component status, filter/cycle references, hold times and environmental dependencies. | Aseptic profile extensible. |
| RCP-FR-025 | Device assembly metadata | Support component lot/serial inputs, assembly relationship, device test result and unit/lot scope. | eDHR reuse. |
| RCP-FR-026 | Packaging/label step | Reference packaging/label configuration and issuance/reconciliation requirements. | Document 16 integration. |
| RCP-FR-027 | Expected yield points | Declare manufacturing phases at which yield/reconciliation calculation is required. | Document 17 integration. |
| RCP-FR-028 | Exception policy | Each step defines what happens on out-of-limit, missing evidence, timeout, failed device read or ineligible resource: block, hold, deviation, retry under rule. | No ad hoc operator decision. |
| RCP-FR-029 | Rework/reprocess route | Approved alternative route is modelled as separate released route/profile; cannot be improvised during batch execution. | Controlled rework. |
| RCP-FR-030 | Recipe completeness validator | Before release, validate graph, dependencies, missing specs, rules, signature policies, unsupported step types, unused references and profile-specific requirements. | Invalid recipe cannot release. |
| RCP-FR-031 | Independent master review | Release policy supports author + independent checker/approver; signatures bind exact canonical recipe version. | 211.186-style master control support. |
| RCP-FR-032 | Effective date and site | Recipe validity depends on product/site/effective date and released dependencies. | Issue eligibility deterministic. |
| RCP-FR-033 | Change impact | Changing released recipe creates new version and evaluates open batches, materials, labels, validation and training impact. | Existing batch unaffected unless controlled change path. |
| RCP-FR-034 | Recipe compare | Provide semantic version comparison: instructions, steps, limits, materials, equipment, rules, signatures, branches. | Reviewer can see critical change. |
| RCP-FR-035 | Simulation | Non-production simulation validates graph/rules/inputs without creating regulated batch. | Authoring quality improved. |
| RCP-FR-036 | Template reuse | Reusable step/section templates may be inserted into draft recipe; final recipe stores resolved exact template version/content. | No live mutable template at execution. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (9 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `recipe_family` | 7 | PostgreSQL (GxP Core, authoritative) |
| `recipe_version` | 12 | PostgreSQL (GxP Core, authoritative) |
| `recipe_section` | 8 | PostgreSQL (GxP Core, authoritative) |
| `recipe_step` | 12 | PostgreSQL (GxP Core, authoritative) |
| `recipe_step_dependency` | 3 | PostgreSQL (GxP Core, authoritative) |
| `recipe_parameter` | 10 | PostgreSQL (GxP Core, authoritative) |
| `recipe_material_requirement` | 7 | PostgreSQL (GxP Core, authoritative) |
| `recipe_equipment_requirement` | 4 | PostgreSQL (GxP Core, authoritative) |
| `recipe_evidence_requirement` | 5 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (10):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /recipes/v1/drafts` | yes | — |
| `PUT /recipes/v1/drafts/{id}` | yes | — |
| `POST /recipes/v1/drafts/{id}/validate` | yes | — |
| `POST /recipes/v1/drafts/{id}/simulate` | yes | — |
| `POST /recipes/v1/drafts/{id}/submit` | yes | — |
| `POST /recipes/v1/drafts/{id}/release` | yes | policy lookup (Doc 106) |
| `GET /recipes/v1/{familyId}/versions` | no | — |
| `GET /recipes/v1/versions/{id}` | no | — |
| `GET /recipes/v1/versions/{id}/compare/{otherId}` | no | — |
| `GET /recipes/v1/versions/{id}/issue-eligibility?site=...&date=...` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `RecipeDraftSubmitted` | SPEC-EBMR-001 | event_id |
| `RecipeValidationFailed` | SPEC-EBMR-001 | event_id |
| `RecipeVersionReleased` | SPEC-EBMR-001 | event_id |
| `RecipeVersionEffective` | SPEC-EBMR-001 | event_id |
| `RecipeVersionSuspended` | SPEC-EBMR-001 | event_id |
| `RecipeVersionSuperseded` | SPEC-EBMR-001 | event_id |

UI SURFACES:
- Recipe Catalogue
- Recipe Header/Product/Batch Size
- Section & Step Builder
- Dependency Graph View
- Materials
- Equipment
- Parameters/Calculations
- QC/Sampling
- Signatures/Verification
- Exceptions/Timers
- Packaging/Label
- Release Readiness
- Version Compare
- Simulation

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
- normal sequential recipe
- parallel/join
- conditional branch
- cycle rejection
- unreachable step
- missing material spec
- missing rule
- obsolete equipment policy
- wrong product version
- independent approval
- recipe changed after signature challenge
- issue snapshot immutable
- master superseded while batch active
- manual fallback rule
- rework route
- sterile profile requirement
- batch size variant
- recipe compare
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-02/Document_10_SPEC-EBMR-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EBMR-001/<test_case_id>/`.
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
- step type contract
- graph semantics
- snapshot schema
- recipe release state model
- rule/signature references
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
