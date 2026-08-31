# WP-12 — Function Contracts

Every function must specify typed inputs, validations, authorization/qualification/SoD, signature requirement, processing rules, DB reads/writes, transaction boundary, outputs, events, errors, idempotency and concurrency. Full rows: `docs/generated/03_FUNCTION_CATALOGUE.csv` filtered by module.

| Function | Doc | Caller | Inputs | Preconditions | Output |
|---|---|---|---|---|---|
| createValidationMasterPlan() | 79 | Validation Lead | system_version; deployment_profile; regulatory_scopes; responsibility_model | Architecture baseline exists | ValidationMasterPlan |
| releaseValidationMasterPlan() | 79 | QA/Validation approver | vmp_id; version; signatures | Mandatory sections/reviews complete | ReleasedVMP |
| deriveValidationDeliverables() | 79 | Validation service | risk inventory; deployment profile; VMP version | Risk assessments available | ValidationDeliverablePlan |
| assignValidationResponsibility() | 79 | Validation Admin | artifact/control; vendor/customer/shared owner; rationale | VMP effective | ResponsibilityAssignment |
| evaluateValidationReleaseGate() | 79 | Release workflow | release candidate; trace status; deviations; evidence | VMP effective | ValidationGateResult |
| generateValidationPackageIndex() | 79 | Validation service | release/customer/site scope | Approved artifacts available | ValidationPackageIndex |
| createIntendedUseStatement() | 80 | System/Process Owner | scope_type; scope_id; intended_use; process; users | Scope exists | IntendedUse |
| assessFunctionRisk() | 80 | Validation/Process Owner | function_id; failure_modes; impacts; detectability; automation/record role | Function/spec version exists | FunctionRiskAssessment |
| approveRiskAssessment() | 80 | QA/Validation | assessment_id; decision; signature | Assessment complete/current | ApprovedRiskAssessment |
| deriveAssuranceLevel() | 80 | Validation service | approved risk; function type; VMP rules | VMP effective | AssuranceRequirement |
| reassessRiskForChange() | 80 | Change Control | change_id; affected function/config IDs | Impact identified | RiskReassessment |
| ingestRequirement() | 81 | Spec ingestion/Validation | source_doc; req_id; version; text; classification | Stable source ID | RequirementVersion |
| linkRequirementToDesign() | 81 | Engineering/Extractor | requirement; function/API/schema/artifact ref | Artifacts exist | TraceLink |
| linkRequirementToTest() | 81 | Validation | requirement; test/version; coverage type | Both exist/current | TraceLink |
| freezeRequirementBaseline() | 81 | Validation Lead | release/scope; versions; exclusions | Approvals/risk current | RequirementBaseline |
| detectTraceabilityGaps() | 81 | Release gate | baseline; risk rules | Baseline exists | TraceabilityGapReport |
| generateTraceabilityMatrix() | 81 | Validation/Inspection | baseline/release; format | Trace graph available | TraceabilityMatrix |
| createValidationTestDefinition() | 82 | Validation/Engineer | test_type; requirements; risk; procedure/charter; expected results | Trace/risk exists | TestDefinition |
| approveTestDefinition() | 82 | Reviewer | test/version; signature | Definition complete/current | ApprovedTest |
| startTestExecution() | 82 | Tester/CI | test version; environment fingerprint; data/config refs | Eligible environment | TestExecution |
| recordTestObservation() | 82 | Tester/Automation | execution; step/check; actual; evidence; status | Execution active | ObservationReceipt |
| completeTestExecution() | 82 | Tester/CI | execution; conclusion; summary | Mandatory evidence present | TestResult |
| reviewTestExecution() | 82 | Reviewer | execution; conclusion; signature | Execution closed | TestReview |
| importAutomatedTestEvidence() | 82 | CI | run ID; commit; report; artifact refs; fingerprint | Trusted CI source | ImportedTestEvidence |
| createIQProtocol() | 83 | Validation/Installer | environment; release; deployment profile; component inventory | Approved release/profile | IQProtocol |
| captureInstalledInventory() | 83 | Qualification agent | environment | Authorized read-only | InstalledInventory |
| verifyInstalledArtifact() | 83 | IQ executor | component; expected digest/signature/version | Release manifest available | IQCheckResult |
| verifyEnvironmentPrerequisites() | 83 | IQ executor | environment/profile | Profile effective | IQCheckSet |
| completeIQExecution() | 83 | Validation executor | IQ run; results; deviations | Mandatory checks complete | IQResult |
| approveIQ() | 83 | Validation/QA | IQ result; signature | PASS or approved deviations | ApprovedIQ |
| deriveOQSuite() | 84 | Validation service | requirement baseline; risks; IQ | IQ approved | OQSuite |
| executeOQSuite() | 84 | Validation/CI | OQ suite; environment/config fingerprint | IQ valid | OQExecution |
| evaluateOQCoverage() | 84 | Validation | OQ execution; risk/requirements | Execution closed | OQCoverageReport |
| approveOQ() | 84 | Validation/QA | execution; coverage; deviations; signature | Critical blockers resolved | ApprovedOQ |
| createInfrastructureQualificationProfile() | 86 | Platform/Validation | deployment profile; inventory; control requirements | Architecture/release approved | InfraQualificationProfile |
| captureInfrastructureFingerprint() | 86 | Qualification agent | environment | Read access | InfrastructureFingerprint |
| compareEnvironmentToQualifiedBaseline() | 86 | Validation | fingerprint; profile | Both current | InfrastructureComparison |
| executeInfrastructureControlTest() | 86 | Validation/SRE | control/test code; environment | Safe test approved | InfrastructureTestResult |
| approveInfrastructureQualification() | 86 | Validation/QA | profile; tests; deviations; signature | Critical controls accepted | QualifiedInfrastructure |
| createPart11Assessment() | 88 | Validation/Regulatory | record types; predicate rules; deployment/use | Intended use approved | Part11Assessment |
| derivePart11TestSuite() | 88 | Validation | assessment; platform/customer config | Assessment approved | Part11TestSuite |
| verifySignatureManifestation() | 88 | Automated/manual test | signed record/export | Signed record exists | ControlTestResult |
| verifySignatureRecordLink() | 88 | Validation | signature ID; record versions | Evidence available | ControlTestResult |
| verifyRecordCopyCompleteness() | 88 | Validation | record/version; export types | Record retained | CopyVerification |
| approvePart11Qualification() | 88 | QA/Validation | assessment/tests/deviations; signature | Required controls passed | Part11Qualification |
| deriveDataIntegrityTestSuite() | 89 | Validation | data classes; risk; audit/Vault architecture | Baselines current | DataIntegritySuite |
| runAuditTamperDetectionTest() | 89 | Validation isolated env | audit scope; tamper scenario | Non-production copy | TamperTestResult |
| verifyVaultCanonicalization() | 89 | Automated validation | test vectors; engine version | Vectors approved | CanonicalizationResult |
| verifyRecordCorrectionHistory() | 89 | Validation | record; correction scenario | Record released | IntegrityTestResult |
| verifyArchiveRetrievalIntegrity() | 89 | Validation/DR | archived record/evidence set | Archive available | ArchiveIntegrityResult |
| approveDataIntegrityQualification() | 89 | QA/Validation | suite/results/deviations | Critical tests complete | DataIntegrityQualification |
| createInterfaceValidationProfile() | 90 | Integration/Validation | interface; version; intended use; mappings; failure modes | Contract approved | InterfaceValidationProfile |
| executeInterfaceContractTests() | 90 | CI/Validation | profile; simulator/sandbox; environment | Endpoint available | InterfaceTestRun |
| executeEdgeOutageQualification() | 90 | Validation/Edge | gateway/profile; outage duration/load | Gateway qualified | EdgeOutageTest |
| verifyExternalReconciliation() | 90 | Validation | interface transactions; external records | Readback available | InterfaceReconciliation |
| approveInterfaceQualification() | 90 | Validation/QA | profile/results/deviations | Critical tests passed | InterfaceQualification |
| createDRQualificationScenario() | 91 | SRE/Validation | failure scenario; scope; target RPO/RTO; restore point | DR profile approved | DRScenario |
| executeRestoreQualification() | 91 | DR operator | scenario; backup set; isolated target | Backup/key available | DRExecution |
| measureRecoveryObjectives() | 91 | Validation | execution; source marker; ready time | Execution complete enough | RecoveryObjectiveResult |
| runRecoveredGxPSmoke() | 91 | Validation | recovered environment; smoke profile | Core stores restored | RecoverySmokeResult |
| approveDRQualification() | 91 | QA/Validation | results/deviations | Objectives accepted | DRQualification |
| deriveSecurityQualificationSuite() | 92 | Security/Validation | threat/control matrix; release/profile | Security baseline released | SecurityQualificationSuite |
| executeSecurityControlTest() | 92 | Security runner | test ID; environment; safe payload/config | Environment approved | SecurityControlTestResult |
| importPenetrationTestFinding() | 92 | Security | external finding/report; severity; evidence | Trusted source | SecurityFinding |
| evaluateSecurityQualificationGate() | 92 | Security/QA | results; open findings; exceptions | Current release/profile | SecurityQualificationGate |
| approveSecurityQualification() | 92 | Security+QA | suite/results/findings/exceptions; signatures | Gate ready | SecurityQualification |
| createPerformanceQualificationScenario() | 93 | Performance/Validation | workload; NFRs/SLOs; environment; duration | Environment qualified | PerformanceScenario |
| executePerformanceQualification() | 93 | Load harness | scenario; synthetic data; release/config fingerprint | Environment stable | PerformanceRun |
| evaluatePerformanceAcceptance() | 93 | Performance/Validation | run; thresholds | Run complete | PerformanceQualificationResult |
| deriveDeploymentSizing() | 93 | Capacity service | qualified results; customer load | Comparable model | DeploymentSizingProfile |
| approvePerformanceQualification() | 93 | Validation/SRE/System Owner | results; limitations; deviations | Criteria met | PerformanceQualification |
| createValidationException() | 94 | Test system/Validator | source execution; type; description; evidence; requirements | Source exists | ValidationException |
| triageValidationException() | 94 | Validation/QA/Engineering | exception; severity; GxP/release impact; rationale | Authorized | ExceptionTriage |
| linkEngineeringDefect() | 94 | Engineering integration | exception; issue/commit/PR | Refs valid | DefectLink |
| defineRetestScope() | 94 | Validation | exception; fix/change; affected trace graph | Cause/fix known | RetestPlan |
| dispositionValidationException() | 94 | QA/Validation | exception; disposition; rationale; signature | Required actions complete | ExceptionDisposition |
| evaluateExceptionReleaseBlockers() | 94 | Release gate | release; open exceptions | Policy effective | ExceptionGateResult |
| assessValidationChangeImpact() | 96 | Change Control | change; changed artifacts/config; target env | Validated baseline exists | ValidationChangeImpact |
| approveRevalidationPlan() | 96 | Validation/QA | impact; selected tests/level; rationale | Impact complete | RevalidationPlan |
| executeRevalidation() | 96 | Validation/CI | plan; target release/environment | Plan approved | RevalidationExecution |
| createPeriodicReview() | 96 | Scheduled/System Owner | deployment/baseline; period | Review due | PeriodicReview |
| evaluateValidatedState() | 96 | QA/System Owner | periodic review inputs/actions | Evidence complete | ValidatedStateDecision |
| decommissionValidatedSystem() | 96 | System Owner/Records/QA | deployment; archive/retention/shutdown plan | Retention/legal requirements resolved | DecommissionRecord |
