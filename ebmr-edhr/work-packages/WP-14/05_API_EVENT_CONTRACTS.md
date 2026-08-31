# WP-14 — API & Event Contracts

## Operations

| Operation | Doc | State-changing |
|---|---|---|
| `POST /validation/v1/pq/scenarios` | 85 | yes |
| `POST /validation/v1/pq/scenarios/{id}/participants` | 85 | yes |
| `POST /validation/v1/pq/executions` | 85 | yes |
| `POST /validation/v1/pq/{id}/approve` | 85 | yes |
| `POST /validation/v1/migrations/plans` | 87 | yes |
| `POST /validation/v1/migrations/runs` | 87 | yes |
| `POST /validation/v1/migrations/{id}/reconcile` | 87 | yes |
| `POST /validation/v1/migrations/{id}/approve` | 87 | yes |
| `POST /validation/v1/summary-reports` | 95 | yes |
| `GET /validation/v1/releases/{id}/go-live-readiness` | 95 | no |
| `POST /validation/v1/summary-reports/{id}/approve` | 95 | yes |
| `POST /validation/v1/releases/{id}/authorize` | 95 | yes |
| `POST /validation/v1/releases/{id}/deployment-check` | 95 | yes |

## Events

| Event | Doc | Producer |
|---|---|---|
| `PQScenarioCreated` | 85 | SPEC-VAL-007 |
| `PQScenarioCompleted` | 85 | SPEC-VAL-007 |
| `PQUsabilityObservationRecorded` | 85 | SPEC-VAL-007 |
| `PQApproved` | 85 | SPEC-VAL-007 |
| `MigrationSourceProfiled` | 87 | SPEC-VAL-009 |
| `MigrationDryRunCompleted` | 87 | SPEC-VAL-009 |
| `MigrationReconciled` | 87 | SPEC-VAL-009 |
| `MigrationAccepted` | 87 | SPEC-VAL-009 |
| `ValidationSummaryGenerated` | 95 | SPEC-VAL-017 |
| `GoLiveReadinessEvaluated` | 95 | SPEC-VAL-017 |
| `ValidationSummaryApproved` | 95 | SPEC-VAL-017 |
| `ValidatedReleaseAuthorized` | 95 | SPEC-VAL-017 |
| `DeploymentMatchesValidatedRelease` | 95 | SPEC-VAL-017 |
| `PostGoLiveVerificationCompleted` | 95 | SPEC-VAL-017 |

## Contract rules
- schemas committed before implementation
- canonical command/receipt/error/event envelopes
- `additionalProperties: false` on commands
- decimal quantities as strings with UOM
- registry entry in `37_API_EVENT_COMPATIBILITY_REGISTRY.md`
