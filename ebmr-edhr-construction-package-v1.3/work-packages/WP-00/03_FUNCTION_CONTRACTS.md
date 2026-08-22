# WP-00 — Function Contracts

Every function must specify typed inputs, validations, authorization/qualification/SoD, signature requirement, processing rules, DB reads/writes, transaction boundary, outputs, events, errors, idempotency and concurrency. Full rows: `docs/generated/03_FUNCTION_CATALOGUE.csv` filtered by module.

| Function | Doc | Caller | Inputs | Preconditions | Output |
|---|---|---|---|---|---|
| lintSourceFile() | 97 | Pre-commit/CI | file_path; language; coding_profile_version | File belongs to supported source tree | LintResult |
| typeCheckPackage() | 97 | CI | package_path; tsconfig/python typing profile | Dependencies installed from lockfile | TypeCheckReport |
| validateRegulatedNumericUsage() | 97 | CI semantic rule | AST/source files; regulated module catalogue | Catalogue current | NumericSafetyReport |
| validateFrappeBoundary() | 97 | CI architecture rule | Python/JS import/call graph | Architecture registry exists | BoundaryReport |
| validateLoggingStatement() | 97 | Static/runtime test | logging call; redaction policy | Logging framework registered | LoggingCheck |
| validateDomainErrorRegistry() | 97 | CI | source error codes; registry | Registry current | ErrorRegistryReport |
| scanForbiddenConstructs() | 97 | CI | repo; policy version | None | ForbiddenConstructReport |
| generateCodingComplianceReport() | 97 | Release CI | all lint/type/security/architecture results | Checks completed | CodingComplianceReport |
| buildAgentTaskPlan() | 98 | Claude Code/Codex before code | task; applicable specs; repo state | Specs accessible | AgentTaskPlan |
| validateArchitectureInvariant() | 98 | Agent/CI | proposed change graph; invariant registry | Registry current | ArchitectureDecision |
| detectSpecificationGap() | 98 | Agent | required behavior; searched spec refs | Behavior material and unresolved | SpecGap |
| validateDependencyAddition() | 98 | Agent/CI | package; version; purpose; alternatives | Document104 registry available | DependencyDecision |
| validateAgentMigrationPlan() | 98 | Agent before migration | schema diff; ownership; compatibility; rollback/restore plan | Document100 rules loaded | MigrationPlanCheck |
| validateAgentContractChange() | 98 | Agent before API/event edit | old/new contract; consumers; version plan | Contract registry current | ContractChangeDecision |
| produceAgentCompletionReport() | 98 | Agent task close | diff; tests; scans; requirements; gaps | Work performed | AgentCompletionReport |
| verifyNoFakeEvidence() | 98 | CI/review | claimed test/evidence refs; CI run IDs | Evidence sources reachable | EvidenceVerification |
| createPullRequestChecklist() | 99 | PR bot/Developer | changed files; requirement IDs; task metadata | Branch based on protected baseline | PRChecklist |
| resolveRequiredReviewers() | 99 | PR bot | changed paths; CODEOWNERS; risk classification | Ownership files valid | ReviewerRequirement |
| evaluateMergeGate() | 99 | Git hosting integration | PR; approvals; CI; unresolved threads; policy | PR open/current | MergeGateDecision |
| createReleaseTag() | 99 | Release automation | approved source commit; version; release authorization | Commit merged; release gates pass | ReleaseTag |
| openHotfixBranch() | 99 | Release/Security | production release tag; incident/change; scope | Authorized emergency change | HotfixBranch |
| reconcileHotfixForward() | 99 | Release automation | hotfix commit; main branch | Hotfix released | ForwardMergeStatus |
| auditRepositoryAccess() | 99 | Security/Engineering Ops | repo/org memberships; role policy | Read access available | RepoAccessReview |
| generateRepoDueDiligenceIndex() | 99 | Engineering Ops | repo inventory; release/tag/license/ownership data | Metadata available | RepoDueDiligenceIndex |
| createMigrationPlan() | 100 | Developer/Claude Code | schema diff; data transform; owner; affected release | Ownership registry current | MigrationPlan |
| analyzeMigrationRisk() | 100 | CI/DB tooling | migration SQL/ORM patch; representative schema stats | Staging stats available | MigrationRiskReport |
| executeMigrationDryRun() | 100 | CI/Staging | migration package; restored representative DB | Backup copy ready | MigrationDryRunResult |
| runChunkedBackfill() | 100 | Migration worker | migration ID; query scope; chunk size; transform version | Schema expanded; checkpoint table ready | BackfillResult |
| verifyMigrationReconciliation() | 100 | Migration/Validation | before metrics; after state; reconciliation rules | Migration finished | MigrationReconciliation |
| markMigrationApplied() | 100 | Migration runner | migration ID; checksum; commit; result | Exact migration succeeded/reconciled | AppliedMigration |
| detectMigrationDrift() | 100 | Startup/CI | expected migration manifest; DB applied list/checksums | DB reachable | MigrationDriftReport |
| generateUpgradePath() | 100 | Release tooling | from version; to version; migration graph | Supported versions known | UpgradePath |
| validateOpenAPIContract() | 101 | CI | OpenAPI document; style/security rules | Contract parses | OpenAPIValidationReport |
| validateAsyncAPIContract() | 101 | CI | AsyncAPI/events; schema registry | Contract parses | AsyncAPIValidationReport |
| classifyContractChange() | 101 | CI/Release | old contract; new contract | Both versions available | ContractChangeClassification |
| resolveContractConsumers() | 101 | Contract registry | operation/event ID | Registry current | ConsumerInventory |
| runConsumerContractTests() | 101 | CI | provider candidate; consumer test packs | Test packs registered | ConsumerContractResult |
| validateIdempotencyContract() | 101 | CI/design check | mutation operation schema/docs | Operation mutating/retryable | IdempotencyContractCheck |
| registerDeprecation() | 101 | API Governance | contract/version; replacement; end date; consumers | Owner approved | DeprecationRecord |
| generateContractCatalogue() | 101 | Release tooling | all OpenAPI/AsyncAPI/schema sources | Contracts valid | ContractCatalogue |
| deriveRequiredTestSet() | 102 | CI/Change impact | changed requirements/functions/files; risk matrix | Trace graph current | RequiredTestSet |
| runUnitTestSuite() | 102 | CI | package; commit; test profile | Build successful | TestRun |
| runIntegrationTestEnvironment() | 102 | CI | suite; container/service versions; config | Ephemeral dependencies provisioned | IntegrationTestRun |
| runConcurrencyScenario() | 102 | CI/Performance | scenario; worker count; seed; target function | Test data isolated | ConcurrencyResult |
| runFailureInjectionScenario() | 102 | Resilience test | dependency; failure mode; duration; expected behavior | Safe test environment | FailureInjectionResult |
| importTestRunAsValidationEvidence() | 102 | Validation integration | CI run ID; test IDs; build/environment fingerprint | Run trusted and tests mapped to validation | ValidationEvidenceImport |
| detectFlakyTest() | 102 | CI analytics | test history; threshold/policy | Sufficient run history | FlakyTestFinding |
| evaluateTestReleaseGate() | 102 | Release CI | required test set; runs; exceptions | Current commit/release | TestGateDecision |
| createReleaseCandidate() | 103 | Release pipeline | source commit; version; contract/migration/config refs | Main protected and required CI checks current | ReleaseCandidate |
| buildReleaseArtifact() | 103 | Trusted CI | release candidate; toolchain image | Dependencies locked; source clean | ReleaseArtifactSet |
| runReleaseSecurityGates() | 103 | Trusted CI | artifacts; SBOM; source | Artifact immutable | ReleaseSecurityReport |
| runMigrationCompatibilityMatrix() | 103 | CI | candidate migrations; supported source versions; representative snapshots | Migration plans present | MigrationMatrixReport |
| assembleReleaseEvidenceManifest() | 103 | Release tooling | CI runs; SBOM; contracts; migrations; validation auth | Required evidence available | ReleaseEvidenceManifest |
| authorizeProductionPromotion() | 103 | Deployment gate | manifest; validated release authorization; target environment/config fingerprint | Approvals current | PromotionAuthorization |
| deployRelease() | 103 | Deployment system | authorization; artifact digests; strategy | Target prechecks pass | DeploymentReceipt |
| executeControlledRollback() | 103 | Release/SRE | failed deployment; prior approved release; compatibility decision | Rollback authorized and DB compatibility understood | RollbackReceipt |
| generateReleaseNotes() | 103 | Release tooling | requirements/issues/contracts/migrations/security/validation changes | Candidate frozen | ReleaseNotes |
| registerDependency() | 104 | Developer/Dependency bot | ecosystem; package; version; purpose; source | Package resolved from approved source | DependencyRecord |
| evaluateDependencyLicense() | 104 | License service/Legal | dependency; detected licenses; distribution context | License metadata available | LicenseDecision |
| evaluateDependencySecurity() | 104 | SCA/Security | dependency/SBOM; vulnerabilities; exploitability/exposure | Scan/advisory data current | DependencySecurityDecision |
| approveDependency() | 104 | Architecture/Security/Legal as required | dependency candidate; purpose; alternatives; license/security decisions | Required reviews complete | ApprovedDependency |
| generateReleaseSBOM() | 104 | Release pipeline | artifact digest; lockfiles/images; provenance | Artifact built | SBOMArtifact |
| validateLockfileChange() | 104 | CI | old/new lockfile; manifest | Diff parsable | LockfileDecision |
| generateThirdPartyNotices() | 104 | Release tooling | release SBOM; license obligations | All licenses classified | ThirdPartyNoticePackage |
| generateAcquisitionDependencyDossier() | 104 | Engineering/Legal | all supported releases; dependency registry | Data available | DependencyDossier |
