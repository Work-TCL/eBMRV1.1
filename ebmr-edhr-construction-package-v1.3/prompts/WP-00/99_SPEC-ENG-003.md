# Claude Code prompt — WP-00 / Document 99: Repository & Branching Standard

TASK:
Implement the Repository & Branching Standard module (SPEC-ENG-003) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_99_Repository_Branching_Standard_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: GIT-FR-001..030 (30)
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
contracts/openapi/spec-eng-003.yaml
contracts/events/spec-eng-003/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-eng-003/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| GIT-FR-001 | Repository model | Use documented monorepo or approved multi-repo topology with explicit ownership; topology versioned in architecture. | Due diligence. |
| GIT-FR-002 | Main branch | main/equivalent is protected and always represents releasable integrated state subject to release gates. | Stability. |
| GIT-FR-003 | No direct push | Direct pushes/force pushes to protected production branches prohibited. | Control. |
| GIT-FR-004 | Feature branches | Short-lived branches from current protected baseline; naming includes issue/change/task ID. | Traceability. |
| GIT-FR-005 | PR required | All production code/config/migration/contract changes merge through pull request. | Review. |
| GIT-FR-006 | PR metadata | PR includes purpose, requirement IDs, risk, migrations, APIs/events, dependencies, tests, validation impact. | Review context. |
| GIT-FR-007 | CODEOWNERS | GxP core, IAM/signature, audit/Vault, migrations, security, CI/release and validation paths have mandatory owners. | Independent review. |
| GIT-FR-008 | Required approvals | Approval count/roles based on path/risk; author cannot satisfy all required approvals. | SoD. |
| GIT-FR-009 | Status checks | Required CI checks cannot be bypassed by normal developers. | Automated gate. |
| GIT-FR-010 | Conversation resolution | Required review threads resolved before merge; dismissals recorded. | Review integrity. |
| GIT-FR-011 | Signed commits/tags | Release tags/artifacts use organization-approved signing/attestation; developer commit signing policy configurable. | Provenance. |
| GIT-FR-012 | Commit content | Commits avoid secrets/binaries/generated build output unless designated; messages reference issue/change where practical. | Clean history. |
| GIT-FR-013 | History rewrite | Published protected history not rewritten except exceptional repository security procedure. | Evidence. |
| GIT-FR-014 | Release tags | Immutable annotated/signed release tags identify exact source baseline. | Reproducibility. |
| GIT-FR-015 | Versioning | Product/service/schema/contract versions follow documented semantic/calendar strategy; one release manifest is authoritative. | Consistency. |
| GIT-FR-016 | Hotfix | Hotfix starts from production release baseline, receives expedited but mandatory controls, then merges forward. | Emergency control. |
| GIT-FR-017 | Security fix | Embargoed private workflow supported for sensitive vulnerability patches. | Disclosure safety. |
| GIT-FR-018 | Rollback branch | Rollback uses known prior release/artifact; no ad-hoc revert of database history. | Safe recovery. |
| GIT-FR-019 | Generated files | Generated contracts/clients checked or rebuilt according to policy; source generator remains authoritative. | Consistency. |
| GIT-FR-020 | Large files | Evidence/test binaries stored artifact/evidence system or Git LFS only if approved; normal Git history not used as regulated archive. | Repo health. |
| GIT-FR-021 | Submodules | Git submodules discouraged/controlled; third-party source pinned and license/provenance tracked. | Supply chain. |
| GIT-FR-022 | Secrets | Secret scanning blocks pushes/PR; leaked credential treated as incident and rotated. | Security. |
| GIT-FR-023 | Branch retention | Merged feature branches may delete; protected release tags/history remain. | Hygiene. |
| GIT-FR-024 | Forks | External forks for proprietary regulated code disabled/restricted according to organization policy. | IP. |
| GIT-FR-025 | Access review | Repository roles/team access periodically reviewed and offboarding immediate. | Security. |
| GIT-FR-026 | Bot accounts | CI/AI bots use named apps/service identities and least privilege, not personal PATs. | Attribution. |
| GIT-FR-027 | PR provenance | Automation identifies AI-assisted changes if organization policy requires, but human accountability remains with reviewers/authorizers. | Governance. |
| GIT-FR-028 | Release evidence | PR/commit/tag/build/validation authorization connected in release manifest. | Acquisition readiness. |
| GIT-FR-029 | Archive | Repository backup/export and ownership records support acquisition/business continuity. | Due diligence. |
| GIT-FR-030 | No orphan code | Every production repo has owner, purpose, license/IP status, CI and release lifecycle. | Portfolio hygiene. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| createPullRequestChecklist() | PR bot/Developer | changed files; requirement IDs; task metadata | PRChecklist | PullRequestChecklistCreated |
| resolveRequiredReviewers() | PR bot | changed paths; CODEOWNERS; risk classification | ReviewerRequirement | RequiredReviewersResolved |
| evaluateMergeGate() | Git hosting integration | PR; approvals; CI; unresolved threads; policy | MergeGateDecision | MergeGateEvaluated |
| createReleaseTag() | Release automation | approved source commit; version; release authorization | ReleaseTag | ReleaseTagCreated |
| openHotfixBranch() | Release/Security | production release tag; incident/change; scope | HotfixBranch | HotfixBranchOpened |
| reconcileHotfixForward() | Release automation | hotfix commit; main branch | ForwardMergeStatus | HotfixForwardMergeRequired |
| auditRepositoryAccess() | Security/Engineering Ops | repo/org memberships; role policy | RepoAccessReview | RepositoryAccessReviewCompleted |
| generateRepoDueDiligenceIndex() | Engineering Ops | repo inventory; release/tag/license/ownership data | RepoDueDiligenceIndex | RepoDueDiligenceGenerated |

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
- direct push protected branch rejected
- missing CODEOWNER approval
- failed CI merge blocked
- hotfix forward-merge check
- secret committed blocks PR
- release tag source mismatch
- bot personal PAT prohibited
- branch from stale release conflict
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-00/Document_99_SPEC-ENG-003_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-ENG-003/<test_case_id>/`.
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
