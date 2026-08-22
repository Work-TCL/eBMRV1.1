# WP-12 — API & Event Contracts

## Operations

| Operation | Doc | State-changing |
|---|---|---|
| `POST /validation/v1/master-plans` | 79 | yes |
| `POST /validation/v1/master-plans/{id}/release` | 79 | yes |
| `GET /validation/v1/releases/{id}/gate` | 79 | no |
| `GET /validation/v1/packages/{scope}` | 79 | no |
| `POST /validation/v1/intended-use` | 80 | yes |
| `POST /validation/v1/function-risks` | 80 | yes |
| `POST /validation/v1/function-risks/{id}/approve` | 80 | yes |
| `GET /validation/v1/functions/{id}/assurance` | 80 | no |
| `POST /validation/v1/requirements:ingest` | 81 | yes |
| `POST /validation/v1/trace-links` | 81 | yes |
| `POST /validation/v1/baselines` | 81 | yes |
| `GET /validation/v1/traceability` | 81 | no |
| `GET /validation/v1/traceability/gaps` | 81 | no |
| `POST /validation/v1/tests` | 82 | yes |
| `POST /validation/v1/tests/{id}/approve` | 82 | yes |
| `POST /validation/v1/executions` | 82 | yes |
| `POST /validation/v1/executions/{id}/complete` | 82 | yes |
| `POST /validation/v1/automated-evidence` | 82 | yes |
| `POST /validation/v1/iq/protocols` | 83 | yes |
| `POST /validation/v1/iq/executions` | 83 | yes |
| `POST /validation/v1/iq/executions/{id}/complete` | 83 | yes |
| `POST /validation/v1/iq/executions/{id}/approve` | 83 | yes |
| `POST /validation/v1/oq:suites` | 84 | yes |
| `POST /validation/v1/oq/executions` | 84 | yes |
| `GET /validation/v1/oq/{id}/coverage` | 84 | no |
| `POST /validation/v1/oq/{id}/approve` | 84 | yes |
| `POST /validation/v1/infrastructure/profiles` | 86 | yes |
| `POST /validation/v1/infrastructure/fingerprints` | 86 | yes |
| `POST /validation/v1/infrastructure/tests` | 86 | yes |
| `POST /validation/v1/infrastructure/{id}/approve` | 86 | yes |
| `POST /validation/v1/part11/assessments` | 88 | yes |
| `GET /validation/v1/part11/{id}/test-suite` | 88 | no |
| `POST /validation/v1/part11/{id}/approve` | 88 | yes |
| `POST /validation/v1/data-integrity/suites` | 89 | yes |
| `POST /validation/v1/data-integrity/tamper-tests` | 89 | yes |
| `POST /validation/v1/data-integrity/{id}/approve` | 89 | yes |
| `POST /validation/v1/interfaces/profiles` | 90 | yes |
| `POST /validation/v1/interfaces/tests` | 90 | yes |
| `POST /validation/v1/interfaces/edge-outage-tests` | 90 | yes |
| `POST /validation/v1/interfaces/{id}/approve` | 90 | yes |
| `POST /validation/v1/dr/scenarios` | 91 | yes |
| `POST /validation/v1/dr/executions` | 91 | yes |
| `POST /validation/v1/dr/{id}/measure` | 91 | yes |
| `POST /validation/v1/dr/{id}/approve` | 91 | yes |
| `POST /validation/v1/security/suites` | 92 | yes |
| `POST /validation/v1/security/tests` | 92 | yes |
| `POST /validation/v1/security/findings` | 92 | yes |
| `GET /validation/v1/security/{id}/gate` | 92 | no |
| `POST /validation/v1/security/{id}/approve` | 92 | yes |
| `POST /validation/v1/performance/scenarios` | 93 | yes |
| `POST /validation/v1/performance/runs` | 93 | yes |
| `POST /validation/v1/performance/{id}/evaluate` | 93 | yes |
| `GET /validation/v1/performance/sizing` | 93 | no |
| `POST /validation/v1/exceptions` | 94 | yes |
| `POST /validation/v1/exceptions/{id}/triage` | 94 | yes |
| `POST /validation/v1/exceptions/{id}/retest-plan` | 94 | yes |
| `POST /validation/v1/exceptions/{id}/disposition` | 94 | yes |
| `GET /validation/v1/releases/{id}/exception-gate` | 94 | no |
| `POST /validation/v1/change-impacts` | 96 | yes |
| `POST /validation/v1/revalidation-plans` | 96 | yes |
| `POST /validation/v1/revalidations` | 96 | yes |
| `POST /validation/v1/periodic-reviews` | 96 | yes |
| `POST /validation/v1/periodic-reviews/{id}/decision` | 96 | yes |
| `POST /validation/v1/decommission` | 96 | yes |

## Events

| Event | Doc | Producer |
|---|---|---|
| `ValidationMasterPlanReleased` | 79 | SPEC-VAL-001 |
| `ValidationDeliverablesDerived` | 79 | SPEC-VAL-001 |
| `ValidationReleaseGateEvaluated` | 79 | SPEC-VAL-001 |
| `ValidationPackageGenerated` | 79 | SPEC-VAL-001 |
| `IntendedUseCreated` | 80 | SPEC-VAL-002 |
| `FunctionRiskAssessed` | 80 | SPEC-VAL-002 |
| `RiskAssessmentApproved` | 80 | SPEC-VAL-002 |
| `AssuranceLevelDerived` | 80 | SPEC-VAL-002 |
| `ValidationRiskReassessmentRequired` | 80 | SPEC-VAL-002 |
| `RequirementIngested` | 81 | SPEC-VAL-003 |
| `RequirementBaselineFrozen` | 81 | SPEC-VAL-003 |
| `TraceabilityGapDetected` | 81 | SPEC-VAL-003 |
| `TraceabilityMatrixGenerated` | 81 | SPEC-VAL-003 |
| `ValidationTestApproved` | 82 | SPEC-VAL-004 |
| `ValidationTestExecutionStarted` | 82 | SPEC-VAL-004 |
| `ValidationTestCompleted` | 82 | SPEC-VAL-004 |
| `AutomatedEvidenceImported` | 82 | SPEC-VAL-004 |
| `ValidationTestReviewed` | 82 | SPEC-VAL-004 |
| `InstalledInventoryCaptured` | 83 | SPEC-VAL-005 |
| `IQPrerequisitesVerified` | 83 | SPEC-VAL-005 |
| `IQCompleted` | 83 | SPEC-VAL-005 |
| `IQApproved` | 83 | SPEC-VAL-005 |
| `OQSuiteDerived` | 84 | SPEC-VAL-006 |
| `OQExecutionCompleted` | 84 | SPEC-VAL-006 |
| `OQCoverageEvaluated` | 84 | SPEC-VAL-006 |
| `OQApproved` | 84 | SPEC-VAL-006 |
| `InfrastructureFingerprintCaptured` | 86 | SPEC-VAL-008 |
| `InfrastructureQualificationDifferenceDetected` | 86 | SPEC-VAL-008 |
| `InfrastructureQualified` | 86 | SPEC-VAL-008 |
| `Part11AssessmentCreated` | 88 | SPEC-VAL-010 |
| `Part11TestSuiteDerived` | 88 | SPEC-VAL-010 |
| `Part11QualificationApproved` | 88 | SPEC-VAL-010 |
| `AuditTamperTestCompleted` | 89 | SPEC-VAL-011 |
| `VaultCanonicalizationVerified` | 89 | SPEC-VAL-011 |
| `ArchiveRetrievalVerified` | 89 | SPEC-VAL-011 |
| `DataIntegrityQualificationApproved` | 89 | SPEC-VAL-011 |
| `InterfaceContractTestsCompleted` | 90 | SPEC-VAL-012 |
| `EdgeOutageQualificationCompleted` | 90 | SPEC-VAL-012 |
| `InterfaceReconciliationVerified` | 90 | SPEC-VAL-012 |
| `InterfaceQualificationApproved` | 90 | SPEC-VAL-012 |
| `DRRestoreExecuted` | 91 | SPEC-VAL-013 |
| `RecoveryObjectivesMeasured` | 91 | SPEC-VAL-013 |
| `RecoveredGxPSmokeCompleted` | 91 | SPEC-VAL-013 |
| `DRQualificationApproved` | 91 | SPEC-VAL-013 |
| `SecurityControlTestCompleted` | 92 | SPEC-VAL-014 |
| `PenTestFindingImported` | 92 | SPEC-VAL-014 |
| `SecurityQualificationGateEvaluated` | 92 | SPEC-VAL-014 |
| `SecurityQualificationApproved` | 92 | SPEC-VAL-014 |
| `PerformanceQualificationExecuted` | 93 | SPEC-VAL-015 |
| `PerformanceAcceptanceEvaluated` | 93 | SPEC-VAL-015 |
| `DeploymentSizingDerived` | 93 | SPEC-VAL-015 |
| `PerformanceQualificationApproved` | 93 | SPEC-VAL-015 |
| `ValidationExceptionCreated` | 94 | SPEC-VAL-016 |
| `ValidationExceptionTriaged` | 94 | SPEC-VAL-016 |
| `ValidationRetestScopeDefined` | 94 | SPEC-VAL-016 |
| `ValidationExceptionDispositioned` | 94 | SPEC-VAL-016 |
| `ValidationChangeImpactAssessed` | 96 | SPEC-VAL-018 |
| `RevalidationPlanApproved` | 96 | SPEC-VAL-018 |
| `RevalidationCompleted` | 96 | SPEC-VAL-018 |
| `PeriodicReviewCreated` | 96 | SPEC-VAL-018 |
| `ValidatedStateEvaluated` | 96 | SPEC-VAL-018 |
| `ValidatedSystemDecommissioned` | 96 | SPEC-VAL-018 |

## Contract rules
- schemas committed before implementation
- canonical command/receipt/error/event envelopes
- `additionalProperties: false` on commands
- decimal quantities as strings with UOM
- registry entry in `37_API_EVENT_COMPATIBILITY_REGISTRY.md`
