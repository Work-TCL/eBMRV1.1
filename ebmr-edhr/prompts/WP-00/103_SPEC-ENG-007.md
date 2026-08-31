# Claude Code prompt — WP-00 / Document 103: CI/CD & Release Process

TASK:
Implement the CI/CD & Release Process module (SPEC-ENG-007) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_103_CI_CD_Release_Process_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: CICD-FR-001..036 (36)
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

- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `tooling` and its tests
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
tooling/src/            # domain services, command handlers, repositories
tooling/migrations/     # owned entities only
tooling/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-eng-007.yaml
contracts/events/spec-eng-007/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-eng-007/
```

REQUIREMENTS TO IMPLEMENT (36):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| CICD-FR-001 | Pipeline as code | Build/test/release/deploy workflows version controlled and reviewed. | Reproducibility. |
| CICD-FR-002 | Trusted runners | Production signing/deploy jobs run on trusted hardened runners; untrusted PR code cannot access production secrets. | Supply-chain. |
| CICD-FR-003 | Lockfile builds | Dependencies installed from locked/pinned sources; unexpected lock change visible. | Reproducibility. |
| CICD-FR-004 | Build once | Release artifact built once, immutable, promoted across environments by digest rather than rebuilt. | Artifact identity. |
| CICD-FR-005 | Source provenance | Artifact links source commit, workflow version, builder, dependencies/SBOM and test evidence. | Traceability. |
| CICD-FR-006 | Lint/type gate | Coding/type/architecture checks mandatory. | Quality. |
| CICD-FR-007 | Test gate | Risk-derived required engineering test suites must pass/approved exception. | Quality. |
| CICD-FR-008 | Secret scan | Secret/private-key/token scanning before merge/release. | Security. |
| CICD-FR-009 | SAST | Static security analysis with policy thresholds and reviewed suppressions. | Security. |
| CICD-FR-010 | SCA | Dependency vulnerability/license scan linked Document104. | Supply chain. |
| CICD-FR-011 | IaC scan | Infrastructure/config manifests checked for security/misconfiguration. | Infrastructure. |
| CICD-FR-012 | Container scan | Image/base/package scan after build. | Runtime security. |
| CICD-FR-013 | SBOM | Release SBOM generated and stored with artifact. | Inventory. |
| CICD-FR-014 | Artifact signing | Approved artifact/images/attestations signed after release gates. | Provenance. |
| CICD-FR-015 | Contract gate | OpenAPI/AsyncAPI compatibility tests block unplanned breaking change. | Integration. |
| CICD-FR-016 | Migration gate | Migrations static-analyzed, dry-run/reconciled against supported previous versions. | Upgrade safety. |
| CICD-FR-017 | Validation impact gate | Changed higher-risk requirements/functions produce validation/change impact before production authorization. | Validated state. |
| CICD-FR-018 | Release candidate | Candidate freezes exact source/artifact/contracts/migrations/config baseline. | Controlled release. |
| CICD-FR-019 | Release notes | Generated/reviewed notes include features, fixes, migrations, compatibility, security/known limitations, validation impact. | Customer readiness. |
| CICD-FR-020 | Approval | Release approval roles distinct from author where policy requires. | SoD. |
| CICD-FR-021 | Validated release authorization | Regulated production deploy requires Document95 authorization matching artifact/config fingerprint. | Compliance gate. |
| CICD-FR-022 | Environment promotion | Same artifact digest promoted dev/test/validation/staging/prod; environment config externalized. | Consistency. |
| CICD-FR-023 | Predeploy check | Backup/PITR, migration readiness, capacity, secrets/certs, dependency health and change window checked. | Safe deployment. |
| CICD-FR-024 | Deployment strategy | Rolling/canary/blue-green selected by service risk; migrations remain compatible. | Availability. |
| CICD-FR-025 | Smoke checks | Postdeploy health/auth/db/object/NATS/Temporal/GxP smoke checks required. | Safe rollout. |
| CICD-FR-026 | Rollback | Rollback uses signed prior artifact and compatibility plan; DB state handled separately. | Recovery. |
| CICD-FR-027 | Automatic abort | Critical smoke/integrity/security/migration failure stops rollout. | Fail closed. |
| CICD-FR-028 | Hotfix process | Expedited path keeps security/test/validation/approval evidence appropriate to risk. | Emergency control. |
| CICD-FR-029 | Release manifest | One immutable manifest contains artifact digests, source, SBOM, contracts, migrations, tests, scans, validation authorization. | Due diligence. |
| CICD-FR-030 | Evidence retention | CI/release evidence retained according to product/validation policy, not ephemeral CI logs only. | Inspection. |
| CICD-FR-031 | Deploy identity | Deployment records actor/service identity, environment, versions, start/end and outcome. | Attribution. |
| CICD-FR-032 | No manual drift | Manual production config/manifest changes detected and reconciled through IaC/change control. | Validated state. |
| CICD-FR-033 | Feature flags | GxP flags promoted as validated configuration; ordinary safe flags still inventoried. | Configuration. |
| CICD-FR-034 | Artifact verification | Cluster/admission/deployer verifies digest/signature/approved release before start. | Supply-chain. |
| CICD-FR-035 | Environment protections | Production workflow requires protected environment approvals/secrets. | Access control. |
| CICD-FR-036 | Release reproducibility | Given source/lock/toolchain, organization can regenerate equivalent artifact or explain nondeterminism. | Assurance. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createReleaseCandidate() | Release pipeline | source commit; version; contract/migration/config refs | ReleaseCandidate | ReleaseCandidateCreated |
| buildReleaseArtifact() | Trusted CI | release candidate; toolchain image | ReleaseArtifactSet | ReleaseArtifactsBuilt |
| runReleaseSecurityGates() | Trusted CI | artifacts; SBOM; source | ReleaseSecurityReport | ReleaseSecurityGatesCompleted |
| runMigrationCompatibilityMatrix() | CI | candidate migrations; supported source versions; representative snapshots | MigrationMatrixReport | MigrationCompatibilityCompleted |
| assembleReleaseEvidenceManifest() | Release tooling | CI runs; SBOM; contracts; migrations; validation auth | ReleaseEvidenceManifest | ReleaseEvidenceManifestCreated |
| authorizeProductionPromotion() | Deployment gate | manifest; validated release authorization; target environment/config fingerprint | PromotionAuthorization | ProductionPromotionAuthorized |
| deployRelease() | Deployment system | authorization; artifact digests; strategy | DeploymentReceipt | ReleaseDeploymentStarted/Completed |
| executeControlledRollback() | Release/SRE | failed deployment; prior approved release; compatibility decision | RollbackReceipt | ReleaseRollbackExecuted |
| generateReleaseNotes() | Release tooling | requirements/issues/contracts/migrations/security/validation changes | ReleaseNotes | ReleaseNotesGenerated |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (0 entities owned by this module):
_none declared in the source specifications_

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (0):
_none declared in the source specifications_

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- none declared

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
- untrusted PR cannot read prod secret
- build artifact promoted without rebuild
- breaking contract blocks
- migration previous-version dry run
- validated authorization mismatch blocks prod
- smoke fail aborts
- rollback after compatible schema
- hotfix retains evidence
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-00/Document_103_SPEC-ENG-007_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-ENG-007/<test_case_id>/`.
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
