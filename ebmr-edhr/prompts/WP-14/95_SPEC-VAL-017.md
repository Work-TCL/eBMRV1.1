# Claude Code prompt — WP-14 / Document 95: Validation Summary Report, Release-to-Production & Go-Live Authorization

TASK:
Implement the Validation Summary Report, Release-to-Production & Go-Live Authorization module (SPEC-VAL-017) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_95_Validation_Summary_Release_GoLive_Authorization_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: VSR-FR-001..024 (24)
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
contracts/openapi/spec-val-017.yaml
contracts/events/spec-val-017/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-val-017/
```

REQUIREMENTS TO IMPLEMENT (24):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| VSR-FR-001 | VSR generation | Generate VSR from authoritative validation artifacts. | Final evidence. |
| VSR-FR-002 | Scope | State system/release/customer/environment/config/intended use. | Boundary. |
| VSR-FR-003 | Baselines | List requirement/risk/design/test/config/IQ/OQ/PQ/security/performance/DR baselines. | Reproducible. |
| VSR-FR-004 | Execution summary | Summarize evidence by method/risk/module/status. | Coverage. |
| VSR-FR-005 | Traceability | Include critical gap/orphan status. | Completeness. |
| VSR-FR-006 | Deviations | Include open/closed/accepted exceptions and release impact. | Transparency. |
| VSR-FR-007 | Security | Include qualification/findings/exceptions. | Risk. |
| VSR-FR-008 | Performance | Include operating envelope/limitations. | Operations. |
| VSR-FR-009 | DR | Include restore/DR qualification and achieved objectives. | Recovery. |
| VSR-FR-010 | Migration | Include migration validation if applicable. | Cutover. |
| VSR-FR-011 | Part 11 | Include Part 11 package/customer responsibilities. | Compliance. |
| VSR-FR-012 | Customer responsibilities | Outstanding SOP/training/certification/config duties explicit. | Shared validation. |
| VSR-FR-013 | Known limitations | Approved limitations/workarounds/monitoring listed. | Transparency. |
| VSR-FR-014 | Recommendation/approval | Validation recommendation separate from QA/System Owner authorization. | SoD. |
| VSR-FR-015 | Go-live prerequisites | Training, prod config, backups, interfaces, support, monitoring/cutover tasks checked. | Readiness. |
| VSR-FR-016 | Configuration fingerprint | Record approved production configuration hash. | Validated state. |
| VSR-FR-017 | Release identity | Exact image/code/SBOM/schema/migration/config versions. | Software identity. |
| VSR-FR-018 | Approval | VSR electronically approved/signed by required roles. | Controlled. |
| VSR-FR-019 | Decision | APPROVED/CONDITIONAL/REJECTED; condition cannot bypass critical GxP control. | Explicit. |
| VSR-FR-020 | Evidence manifest | VSR references immutable validation package. | Inspection. |
| VSR-FR-021 | Customer package | Generate vendor/customer subset based on responsibility/access. | Commercial. |
| VSR-FR-022 | Pipeline gate | Production promotion checks validated release authorization. | Technical gate. |
| VSR-FR-023 | Post-go-live | Defined smoke/monitoring verification. | Safe deployment. |
| VSR-FR-024 | Rollback | Failed post-go-live verification follows controlled rollback/incident/change. | Recovery. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| generateValidationSummaryReport() | Validation service | release/customer/site | ValidationSummaryReport | ValidationSummaryGenerated |
| evaluateGoLiveReadiness() | Release gate | VSR scope; training/config/DR/security/interface gates | GoLiveReadiness | GoLiveReadinessEvaluated |
| approveValidationSummary() | Validation Lead/QA/System Owner | VSR; recommendation; signatures | ApprovedVSR | ValidationSummaryApproved |
| issueValidatedReleaseAuthorization() | QA/System Owner | approved VSR; release/config fingerprint | ValidatedReleaseAuthorization | ValidatedReleaseAuthorized |
| verifyDeploymentAgainstValidationRelease() | Deploy pipeline | authorization; artifact/config fingerprint | DeploymentValidationCheck | DeploymentMatchesValidatedRelease |
| recordPostGoLiveVerification() | Release/Validation | production release; smoke/monitor results | PostGoLiveResult | PostGoLiveVerificationCompleted |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `validation_summary_report` | 7 | PostgreSQL (GxP Core, authoritative) |
| `validated_release_authorization` | 6 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (5):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /validation/v1/summary-reports` | yes | — |
| `GET /validation/v1/releases/{id}/go-live-readiness` | no | policy lookup (Doc 106) |
| `POST /validation/v1/summary-reports/{id}/approve` | yes | policy lookup (Doc 106) |
| `POST /validation/v1/releases/{id}/authorize` | yes | policy lookup (Doc 106) |
| `POST /validation/v1/releases/{id}/deployment-check` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `ValidationSummaryGenerated` | SPEC-VAL-017 | event_id |
| `GoLiveReadinessEvaluated` | SPEC-VAL-017 | event_id |
| `ValidationSummaryApproved` | SPEC-VAL-017 | event_id |
| `ValidatedReleaseAuthorized` | SPEC-VAL-017 | event_id |
| `DeploymentMatchesValidatedRelease` | SPEC-VAL-017 | event_id |
| `PostGoLiveVerificationCompleted` | SPEC-VAL-017 | event_id |

UI SURFACES:
- Validation Summary
- Go-Live Checklist
- Known Limitations
- Release Authorization
- Post-Go-Live

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
- config mismatch
- open critical exception
- expired training
- DR missing
- security critical finding
- post-go-live smoke fail
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-14/Document_95_SPEC-VAL-017_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-VAL-017/<test_case_id>/`.
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
