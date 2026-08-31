# WP-11 — API & Event Contracts

## Operations

| Operation | Doc | State-changing |
|---|---|---|
| `GET /platform/v1/data-ownership/{entityType}` | 69 | no |
| `GET /platform/v1/projections/{type}/{id}/freshness` | 69 | no |
| `POST /platform/v1/projections/{type}:rebuild` | 69 | yes |
| `GET /platform/v1/data-dictionary` | 69 | no |
| `GET /api/method/... projection status/admin operations` | 71 | no |
| `POST /evidence/v1/uploads` | 72 | yes |
| `POST /evidence/v1/{id}:finalize` | 72 | yes |
| `GET /evidence/v1/{id}/download` | 72 | no |
| `POST /evidence/v1/manifests` | 72 | yes |
| `POST /evidence/v1/{id}/legal-holds` | 72 | yes |
| `POST /evidence/v1/integrity-checks` | 72 | yes |
| `GET /search/v1/...` | 75 | no |
| `POST /search/v1/indexes/{type}:rebuild` | 75 | yes |
| `POST /reports/v1/exports` | 75 | yes |
| `GET /platform/v1/read-models/{name}/status` | 75 | no |
| `POST /platform/v1/recovery-objectives` | 76 | yes |
| `GET /platform/v1/backups/health` | 76 | no |
| `POST /platform/v1/restore-tests` | 76 | yes |

## Events

| Event | Doc | Producer |
|---|---|---|
| `ProjectionUpdateRequested` | 69 | SPEC-DATA-001 |
| `ProjectionRebuilt` | 69 | SPEC-DATA-001 |
| `ProjectionStaleDetected` | 69 | SPEC-DATA-001 |
| `CrossStoreMismatchDetected` | 69 | SPEC-DATA-001 |
| `MigrationProvenanceRecorded` | 69 | SPEC-DATA-001 |
| `DatabaseIntegrityFailure` | 70 | SPEC-DATA-002 |
| `PartitionGapDetected` | 70 | SPEC-DATA-002 |
| `ReplicaLagExceeded` | 70 | SPEC-DATA-002 |
| `MigrationApplied` | 70 | SPEC-DATA-002 |
| `DeadlockDetected` | 70 | SPEC-DATA-002 |
| `ConnectionPoolExhausted` | 70 | SPEC-DATA-002 |
| `FrappeProjectionApplied` | 71 | SPEC-DATA-003 |
| `FrappeProjectionRebuilt` | 71 | SPEC-DATA-003 |
| `ProjectionStaleDetected` | 71 | SPEC-DATA-003 |
| `DirectProjectionMutationDenied` | 71 | SPEC-DATA-003 |
| `EvidenceUploadStaged` | 72 | SPEC-DATA-004 |
| `EvidenceFinalized` | 72 | SPEC-DATA-004 |
| `EvidenceHashMismatch` | 72 | SPEC-DATA-004 |
| `EvidenceMissing` | 72 | SPEC-DATA-004 |
| `EvidenceLegalHoldApplied` | 72 | SPEC-DATA-004 |
| `EvidencePurged` | 72 | SPEC-DATA-004 |
| `EvidenceProviderMigrated` | 72 | SPEC-DATA-004 |
| `EventPublished` | 73 | SPEC-DATA-005 |
| `EventDeadLettered` | 73 | SPEC-DATA-005 |
| `EventReplayStarted` | 73 | SPEC-DATA-005 |
| `EventSchemaBreakingChangeDetected` | 73 | SPEC-DATA-005 |
| `ConsumerLagExceeded` | 73 | SPEC-DATA-005 |
| `OutboxLagExceeded` | 73 | SPEC-DATA-005 |
| `WorkflowStarted` | 74 | SPEC-DATA-006 |
| `WorkflowStuckDetected` | 74 | SPEC-DATA-006 |
| `TemporalWorkerVersionChanged` | 74 | SPEC-DATA-006 |
| `WorkflowCompensationExecuted` | 74 | SPEC-DATA-006 |
| `TemporalNamespaceUnavailable` | 74 | SPEC-DATA-006 |
| `SearchDocumentIndexed` | 75 | SPEC-DATA-007 |
| `SearchIndexRebuilt` | 75 | SPEC-DATA-007 |
| `ReadModelRefreshed` | 75 | SPEC-DATA-007 |
| `CacheInvalidated` | 75 | SPEC-DATA-007 |
| `ProjectionLagExceeded` | 75 | SPEC-DATA-007 |
| `ExportGenerated` | 75 | SPEC-DATA-007 |
| `BackupRPOAtRisk` | 76 | SPEC-DATA-008 |
| `RestoreTestFailed` | 76 | SPEC-DATA-008 |
| `DatabaseFailoverCompleted` | 76 | SPEC-DATA-008 |
| `EvidenceRestoreMismatch` | 76 | SPEC-DATA-008 |
| `PlatformRecoveryValidated` | 76 | SPEC-DATA-008 |
| `RecoveryDataLossDetected` | 76 | SPEC-DATA-008 |
| `DeploymentPrerequisiteFailed` | 77 | SPEC-DATA-009 |
| `InfrastructureApplied` | 77 | SPEC-DATA-009 |
| `InstallationChecksCompleted` | 77 | SPEC-DATA-009 |
| `InfrastructureDriftDetected` | 77 | SPEC-DATA-009 |
| `PlatformUpgraded` | 77 | SPEC-DATA-009 |
| `RollbackInitiated` | 77 | SPEC-DATA-009 |
| `CertificateExpiryWarning` | 77 | SPEC-DATA-009 |
| `OperationalAlertRaised` | 78 | SPEC-DATA-010 |
| `PerformanceRegressionDetected` | 78 | SPEC-DATA-010 |
| `CapacityThresholdForecasted` | 78 | SPEC-DATA-010 |
| `ProjectionLagExceeded` | 78 | SPEC-DATA-010 |
| `OutboxLagExceeded` | 78 | SPEC-DATA-010 |
| `DatabaseSaturationDetected` | 78 | SPEC-DATA-010 |
| `GracefulDegradationVerified` | 78 | SPEC-DATA-010 |

## Contract rules
- schemas committed before implementation
- canonical command/receipt/error/event envelopes
- `additionalProperties: false` on commands
- decimal quantities as strings with UOM
- registry entry in `37_API_EVENT_COMPATIBILITY_REGISTRY.md`
