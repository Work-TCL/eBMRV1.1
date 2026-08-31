# Claude Code prompt — WP-00 / Document 104: SBOM / Third-Party License Management

TASK:
Implement the SBOM / Third-Party License Management module (SPEC-ENG-008) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_104_SBOM_Third_Party_License_Management_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: DEP-FR-001..036 (36)
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
contracts/openapi/spec-eng-008.yaml
contracts/events/spec-eng-008/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-eng-008/
```

REQUIREMENTS TO IMPLEMENT (36):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| DEP-FR-001 | Dependency register | Inventory direct/transitive runtime/build/test dependencies with package/version/source/owner/purpose. | Complete inventory. |
| DEP-FR-002 | SBOM format | Generate machine-readable SPDX or CycloneDX-compatible SBOM per release/artifact. | Interoperability. |
| DEP-FR-003 | Artifact linkage | SBOM tied exact artifact digest/source commit/build provenance. | Accuracy. |
| DEP-FR-004 | Package source | Dependencies only from approved registries/sources; typosquat/private dependency-confusion controls. | Supply-chain. |
| DEP-FR-005 | Lock/pin | Production dependencies pinned via lockfile/digest; mutable floating versions prohibited. | Reproducibility. |
| DEP-FR-006 | License detection | Record declared/detected license(s), copyright notices and source reference. | IP. |
| DEP-FR-007 | License policy | Licenses classified APPROVED/REVIEW_REQUIRED/PROHIBITED by distribution/business model. | Governance. |
| DEP-FR-008 | Copyleft review | Strong/network copyleft or reciprocal obligations require legal/IP review before inclusion. | Acquisition readiness. |
| DEP-FR-009 | Unknown license | Unknown/no-license package blocked until legal decision. | IP protection. |
| DEP-FR-010 | Notice obligations | Attribution/NOTICE/source-offer or other obligations tracked and packaged when applicable. | Compliance. |
| DEP-FR-011 | Commercial dependency | Track license key/subscription/redistribution/support/EOL terms for commercial components. | Continuity. |
| DEP-FR-012 | Vulnerability mapping | SBOM components correlated with CVE/advisories and internal risk. | Security. |
| DEP-FR-013 | Known exploited status | Known-exploited/advisory status feeds remediation priority. | Risk. |
| DEP-FR-014 | Vulnerability exception | Risk acceptance time-bounded with compensating controls and affected releases. | Governance. |
| DEP-FR-015 | EOL status | Track package/runtime/base image support/EOL and planned replacement. | Lifecycle. |
| DEP-FR-016 | Maintainer health | High-risk dependencies assessed for maintenance/release/signing provenance/abandonment. | Supply-chain. |
| DEP-FR-017 | Dependency necessity | New dependency requires documented purpose and alternative/existing capability review. | Reduce attack surface. |
| DEP-FR-018 | Critical library approval | Crypto/auth/parser/native/runtime-critical libraries require Security/Architecture approval. | Higher scrutiny. |
| DEP-FR-019 | Development dependencies | Build/dev/test dependencies inventoried because compromise can affect artifact. | Supply-chain. |
| DEP-FR-020 | Container OS packages | Base image and OS packages appear in SBOM/scans. | Runtime visibility. |
| DEP-FR-021 | Frappe/ERPNext license | Framework/vendor component licenses and redistribution obligations tracked without modifying core ownership assumptions. | IP. |
| DEP-FR-022 | Generated/vendor code | Copied/generated snippets above trivial threshold require provenance/license record. | IP hygiene. |
| DEP-FR-023 | AI-generated code | AI output is treated as code authored for project and must pass provenance/license/duplication review tooling/policy where applicable. | AI development governance. |
| DEP-FR-024 | Model assets | AI models, embedding models, datasets/prompts with third-party license/terms tracked separately in AI asset register. | AI IP. |
| DEP-FR-025 | Dependency update | Update goes through PR/tests/scans/license review and validation impact as relevant. | Controlled change. |
| DEP-FR-026 | Automatic PRs | Dependabot/Renovate-style automation may propose updates but cannot auto-merge critical dependencies without gates. | Safe automation. |
| DEP-FR-027 | Transitive change | Lockfile diff reviewed for unexpected new package/license/native binary. | Visibility. |
| DEP-FR-028 | Binary provenance | Prebuilt native binaries/images/plugins require trusted source/checksum/signature where available. | Supply-chain. |
| DEP-FR-029 | Vendor SBOM | Third-party appliances/connectors may ingest vendor SBOM/support evidence where available. | Enterprise assurance. |
| DEP-FR-030 | Acquisition export | Generate complete dependency/license/IP/vulnerability register for due diligence. | Commercial value. |
| DEP-FR-031 | Removal | Unused dependency removed after confirming no required runtime/build/validation need. | Attack surface. |
| DEP-FR-032 | No hidden fetch | Build cannot download undeclared executable/model/tool artifact from arbitrary URL. | Reproducibility/security. |
| DEP-FR-033 | License files | Required third-party notices/licenses shipped with appropriate product distributions. | Compliance. |
| DEP-FR-034 | SBOM retention | SBOM and vulnerability snapshot retained for each supported/released version. | Historical evidence. |
| DEP-FR-035 | Customer disclosure | Provide appropriate SBOM/security component disclosure under customer contract without exposing proprietary code. | Enterprise. |
| DEP-FR-036 | No legal automation | Tool can classify/flag licenses but final ambiguous legal interpretation belongs authorized human/legal counsel. | Governance. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| registerDependency() | Developer/Dependency bot | ecosystem; package; version; purpose; source | DependencyRecord | DependencyRegistered |
| evaluateDependencyLicense() | License service/Legal | dependency; detected licenses; distribution context | LicenseDecision | DependencyLicenseEvaluated |
| evaluateDependencySecurity() | SCA/Security | dependency/SBOM; vulnerabilities; exploitability/exposure | DependencySecurityDecision | DependencySecurityEvaluated |
| approveDependency() | Architecture/Security/Legal as required | dependency candidate; purpose; alternatives; license/security decisions | ApprovedDependency | DependencyApproved |
| generateReleaseSBOM() | Release pipeline | artifact digest; lockfiles/images; provenance | SBOMArtifact | ReleaseSBOMGenerated |
| validateLockfileChange() | CI | old/new lockfile; manifest | LockfileDecision | UnexpectedDependencyChange |
| generateThirdPartyNotices() | Release tooling | release SBOM; license obligations | ThirdPartyNoticePackage | ThirdPartyNoticesGenerated |
| generateAcquisitionDependencyDossier() | Engineering/Legal | all supported releases; dependency registry | DependencyDossier | DependencyDossierGenerated |

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
- unknown license blocked
- copyleft review
- transitive package surprise
- critical CVE
- known-exploited package priority
- SBOM artifact digest match
- third-party notices
- AI model license appears in AI register
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-00/Document_104_SPEC-ENG-008_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-ENG-008/<test_case_id>/`.
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
