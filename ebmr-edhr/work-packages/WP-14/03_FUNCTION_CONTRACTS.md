# WP-14 — Function Contracts

Every function must specify typed inputs, validations, authorization/qualification/SoD, signature requirement, processing rules, DB reads/writes, transaction boundary, outputs, events, errors, idempotency and concurrency. Full rows: `docs/generated/03_FUNCTION_CATALOGUE.csv` filtered by module.

| Function | Doc | Caller | Inputs | Preconditions | Output |
|---|---|---|---|---|---|
| createPQScenario() | 85 | Validation/Process SME | site/product/process; actors; prerequisites; steps; acceptance | OQ approved; config known | PQScenario |
| assignPQParticipants() | 85 | Validation Admin | scenario; users/roles; training refs | Users eligible | PQParticipantSet |
| executePQScenario() | 85 | Representative users | scenario; site/environment; dataset | Participants trained; procedures effective | PQExecution |
| recordPQUsabilityObservation() | 85 | Tester/Observer | execution; observation; severity; impact | Execution active/review | PQObservation |
| approvePQ() | 85 | Process Owner/QA | scenario/executions; deviations; signatures | Required scenarios accepted | ApprovedPQ |
| createMigrationValidationPlan() | 87 | Data/Validation | source; target; scope; cutoff; mappings; reconciliation rules | Migration approved | MigrationValidationPlan |
| profileMigrationSource() | 87 | Migration tool | source snapshot/ref | Authorized read-only | SourceProfile |
| executeMigrationDryRun() | 87 | Migration service | plan/version; snapshot; sandbox | Plan approved; target isolated | MigrationRun |
| reconcileMigrationRun() | 87 | Validation/Data | migration run; reconciliation profile | Run complete | MigrationReconciliation |
| approveMigrationCutover() | 87 | System Owner/QA | final run; reconciliation; deviations; signature | Thresholds met | MigrationAcceptance |
| verifyLegacyRecordTrace() | 87 | Inspection test | legacy_id | Mapping/archive available | LegacyTraceResult |
| generateValidationSummaryReport() | 95 | Validation service | release/customer/site | Required artifacts current | ValidationSummaryReport |
| evaluateGoLiveReadiness() | 95 | Release gate | VSR scope; training/config/DR/security/interface gates | Current evidence | GoLiveReadiness |
| approveValidationSummary() | 95 | Validation Lead/QA/System Owner | VSR; recommendation; signatures | Blockers resolved | ApprovedVSR |
| issueValidatedReleaseAuthorization() | 95 | QA/System Owner | approved VSR; release/config fingerprint | Approval current | ValidatedReleaseAuthorization |
| verifyDeploymentAgainstValidationRelease() | 95 | Deploy pipeline | authorization; artifact/config fingerprint | Authorization active | DeploymentValidationCheck |
| recordPostGoLiveVerification() | 95 | Release/Validation | production release; smoke/monitor results | Deployment complete | PostGoLiveResult |
