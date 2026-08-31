# WP-11 — Function Contracts

Every function must specify typed inputs, validations, authorization/qualification/SoD, signature requirement, processing rules, DB reads/writes, transaction boundary, outputs, events, errors, idempotency and concurrency. Full rows: `docs/generated/03_FUNCTION_CATALOGUE.csv` filtered by module.

| Function | Doc | Caller | Inputs | Preconditions | Output |
|---|---|---|---|---|---|
| resolveDataOwner() | 69 | Any service/design tooling | entity_type; field/path? | Data ownership registry loaded | DataOwnerDecision |
| assertAuthoritativeWriteAllowed() | 69 | Repository/mutation layer | service_identity; entity_type; operation | Owner registry effective | WriteOwnershipDecision |
| publishProjectionChange() | 69 | Authoritative service after commit | source_event_id; entity_type/id/version; projection payload/ref | Authoritative tx committed | ProjectionEvent |
| getProjectionFreshness() | 69 | UI/read service | projection_type; entity_id | Projection exists | ProjectionFreshness |
| rebuildProjection() | 69 | Projection worker/admin | projection_type; scope; source cutoff | Authorized/rebuildable projection | ProjectionRebuildResult |
| registerDataClass() | 69 | Data governance | entity/field; classification; retention; encryption profile | Governance authority | DataClassEntry |
| recordMigrationProvenance() | 69 | Migration service | migration_batch; source; checksums; transformation version; destination refs | Migration approved | MigrationProvenance |
| verifyCrossStoreConsistency() | 69 | Scheduled/admin | projection/integration scope; source cutoff | Authoritative source available | ConsistencyReport |
| executeGxPTransaction() | 70 | Mutation Gateway/domain service | aggregate id/version; command payload; actor/context | Expected version valid; auth/rules/signature complete | MutationReceipt |
| applyOptimisticUpdate() | 70 | Repository | table/key; expected_version; changes | Expected version supplied | UpdatedVersion |
| appendOutboxEvent() | 70 | Domain transaction | event envelope | Inside active authoritative transaction | OutboxRef |
| createTimePartition() | 70 | Partition maintenance job | table; start/end; storage/index profile | Partition template approved; bounds non-overlap | PartitionRef |
| verifyPartitionCoverage() | 70 | Preflight/monitor | table; future horizon | Partitioned table exists | CoverageReport |
| runDatabaseIntegrityCheck() | 70 | DBA automation | database/schema/table scope; check profile | Read-safe maintenance window/policy | IntegrityCheckReport |
| getPrimaryConsistencyRead() | 70 | Regulated action service | entity/id; expected version | Primary available | AuthoritativeRecord |
| runReadReplicaQuery() | 70 | Reporting | report/query definition; max_staleness | Replica healthy and lag <= allowed threshold | ReportDataset |
| applyGxPProjection() | 71 | Projection worker | source event/entity/version; projection DTO | Event authenticated/idempotent; version >= current | ProjectionApplyResult |
| rejectDirectProjectionMutation() | 71 | Frappe server hook/API | doctype/document changes; user context | DocType/source field marked projection | Denied |
| rebuildFrappeProjection() | 71 | Admin/projector | projection type; scope; source cutoff | Maintenance authorization; authoritative APIs available | ProjectionRebuildResult |
| getProjectionStatus() | 71 | Frappe UI | entity/source ID | Projection exists | ProjectionStatus |
| invokeGxPAction() | 71 | Frappe controller | operationId; DTO; AuthContext; idempotency/expected version | User authenticated; route allowed | GxPActionReceipt |
| verifyMariaDBAfterRestore() | 71 | Recovery runbook | restore timestamp; projection checkpoints | MariaDB restored and isolated from writes | MariaDBRecoveryReport |
| stageEvidenceUpload() | 72 | UI/Edge/Integration | owner context; filename; MIME; size; expected hash? | Uploader authorized; policy/quotas | EvidenceUploadSession |
| finalizeEvidenceUpload() | 72 | Upload callback/service | evidence_id; provider object/version; calculated hash; size | Upload complete; malware/type checks passed | EvidenceRef |
| createEvidenceManifest() | 72 | Vault/Release/Export | owner record/version; evidence refs; manifest type | All refs available/current | EvidenceManifestRef |
| authorizeEvidenceDownload() | 72 | Download API | AuthContext; evidence_id; purpose | Resource authorization/retention state valid | EvidenceDownloadGrant |
| verifyEvidenceIntegrity() | 72 | Scheduled/restore/inspection | evidence scope; sampling/full mode | Objects readable | EvidenceIntegrityReport |
| applyEvidenceLegalHold() | 72 | Records/Legal | evidence scope; hold_id; reason | Authorized hold | HoldReceipt |
| purgeExpiredEvidence() | 72 | Retention worker | eligibility set; policy version | Retention elapsed; no hold; no blocking reference | PurgeReport |
| migrateEvidenceProvider() | 72 | Migration tool | source provider; target provider; manifest scope | Migration approved; target configured | ProviderMigrationReport |
| appendDomainOutboxEvent() | 73 | Domain transaction | canonical event envelope | Active authoritative DB tx; event ID unique | OutboxRef |
| claimOutboxBatch() | 73 | Outbox publisher | batch size; lease duration; now | Publisher DB role; pending records | OutboxBatch |
| publishOutboxEvent() | 73 | Publisher | outbox event; subject mapping | NATS connection/auth; schema valid | PublishReceipt |
| markOutboxPublished() | 73 | Publisher | outbox_id; publish receipt | Receipt matches event | void |
| consumeEventIdempotently() | 73 | Consumer wrapper | event envelope; handler ID | Schema/auth scope valid | ConsumerReceipt |
| handlePoisonEvent() | 73 | Consumer supervisor | event; failure history; policy | Retry threshold reached/nonretryable | DeadLetterRef |
| replayConsumerEvents() | 73 | Integration Admin | consumer; event range/filter; reason | Authorized; handler idempotent/replay tested | ReplayJob |
| verifyEventSchemaCompatibility() | 73 | CI | old/new JSON schema/AsyncAPI | Schema registry available | CompatibilityReport |
| startBusinessWorkflow() | 74 | Domain service after authoritative creation | workflow_type; business_id; initial refs; correlation | Domain record exists; workflow profile effective | WorkflowRef |
| executeGxPActivity() | 74 | Temporal Activity | operationId; command DTO; idempotency key; expected version | Worker authorized; domain dependency available | GxPActionReceipt |
| scheduleRegulatoryTimer() | 74 | Workflow logic | domain obligation ID; due_at; escalation offsets | Due date already authoritative | TimerPlan |
| receiveDomainSignal() | 74 | Domain event bridge | workflow ID; signal type; authoritative record/version | Source event authenticated/current | SignalReceipt |
| compensateBusinessStep() | 74 | Workflow Activity | source action ref; authorized compensation command | Compensation allowed by domain rules | CompensationReceipt |
| continueLongWorkflow() | 74 | Workflow | carry-forward state refs/version | History threshold/profile met | NewRunRef |
| queryWorkflowOperations() | 74 | Ops UI | workflow ID | Ops authorization | WorkflowOperationalView |
| replayWorkflowTest() | 74 | CI | historical workflow history fixture; new worker code | Fixture/version known | ReplayTestResult |
| getVersionedCacheEntry() | 75 | Application service | cache class; tenant/site; entity id/version | Cache configured; auth already resolved as required | CacheResult |
| invalidateEntityCache() | 75 | Event consumer | entity type/id/new version | Event valid/current | InvalidationReceipt |
| indexAuthoritativeProjection() | 75 | Search projector | entity projection; source version; allowed fields | Event/projection authorized; schema effective | IndexReceipt |
| authorizeSearchQuery() | 75 | Search API | AuthContext; query/filter/sort | User authenticated; fields allowlisted | AuthorizedSearchPlan |
| fetchSearchResultDetail() | 75 | UI/API | result entity ID; source version | Result visible | AuthoritativeDetail |
| rebuildSearchIndex() | 75 | Admin/projector | index type; source cutoff | Authorized; source accessible | SearchRebuildResult |
| refreshReadModel() | 75 | Read-model worker | model; source cutoff/checkpoints | Sources available | ReadModelSnapshot |
| generateAsyncExport() | 75 | Authorized user/report worker | report definition; filters; source cutoff | Export permission/limits | ExportJobResult |
| createRecoveryObjectiveProfile() | 76 | Platform/Customer Admin | component/capability; RPO; RTO; durability/region profile | Authorized and architecture compatible | RecoveryObjectiveProfile |
| verifyBackupFreshness() | 76 | Scheduled monitor | component; objective profile; backup/WAL metadata | Backup provider reachable | BackupHealth |
| executePostgresRestoreTest() | 76 | DR automation | backup set; PITR target; isolated target profile | Backup/key/WAL available | RestoreTestReport |
| reconcileEvidenceAfterRestore() | 76 | DR validation | restored GxP metadata; object provider/snapshot | Metadata/object restore available | EvidenceRecoveryReport |
| rebuildDerivedStoresAfterRestore() | 76 | Recovery orchestration | projection/search/cache scopes; authoritative cutoff | Authoritative services healthy | DerivedRecoveryResult |
| promoteStandby() | 76 | DR operator/automation | cluster; target replica; incident/change ID | Quorum/split-brain checks; authority valid | FailoverReceipt |
| validateRecoveredPlatform() | 76 | DR validation gate | recovery environment; component reports; smoke/test profile | Required stores restored | RecoveryValidationDecision |
| recordDataLossAssessment() | 76 | Security/QA/DR | restore point; expected latest; missing interval/events | Recovery complete enough to compare | DataLossAssessment |
| validateDeploymentPrerequisites() | 77 | Installer/CI | deployment profile; discovered infrastructure | Profile version approved | PrerequisiteReport |
| renderInfrastructurePlan() | 77 | IaC pipeline | customer/environment profile; versions; sizing | Inputs approved; modules pinned | InfrastructurePlan |
| applyInfrastructurePlan() | 77 | Authorized deploy pipeline | signed plan/artifacts; environment | Change/release approved; credentials scoped | DeploymentResult |
| runPostInstallQualificationChecks() | 77 | Installer/Validation | environment; check profile | Core services deployed | InstallationCheckReport |
| performRollingUpgrade() | 77 | Release pipeline | current/new release; migration plan; rollout strategy | Backup/preflight/security gate passed | UpgradeResult |
| detectInfrastructureDrift() | 77 | Scheduled/CI | declared IaC state; observed resources | Read permission | DriftReport |
| scaleService() | 77 | Autoscaler/operator | service; target replicas/capacity trigger | Bounds/DB pool capacity policy | ScaleResult |
| drainWorkerSafely() | 77 | Deployment lifecycle | worker instance; grace deadline | Worker healthy enough to drain | DrainResult |
| recordServiceLevelObjective() | 78 | SRE/Product | capability; SLI; target; window; deployment profile | Owner/measurement defined | SLODefinition |
| calculateCapacityForecast() | 78 | Capacity job | current metrics; growth assumptions; retention; horizon | Metrics sufficient; model version approved | CapacityForecast |
| runSyntheticLoadScenario() | 78 | Performance environment | scenario version; target scale; duration | Environment isolated/representative; synthetic data | LoadTestReport |
| evaluateReleasePerformanceGate() | 78 | CI/release | baseline report; candidate report; allowed regressions | Comparable test scenario | PerformanceGateDecision |
| emitPlatformMetric() | 78 | Any component | metric name/value/labels | Metric registered; labels bounded | MetricReceipt |
| startTraceSpan() | 78 | Request/service middleware | trace context; operation; safe attributes | Tracing enabled/sample policy | TraceSpan |
| evaluateOperationalAlert() | 78 | Monitoring | metrics/logs/events; alert rule version | Rule effective | OperationalAlert |
| executeCapacityScalingPlan() | 78 | SRE/automation | service/component; approved scaling action | Forecast/alert and permissions | ScalingReceipt |
| verifyGracefulDegradation() | 78 | Resilience test | failed dependency; expected capability matrix | Test environment/safe injection | DegradationTestReport |
