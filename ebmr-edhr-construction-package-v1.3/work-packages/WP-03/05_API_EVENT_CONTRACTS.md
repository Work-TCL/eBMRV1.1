# WP-03 — API & Event Contracts

## Operations

| Operation | Doc | State-changing |
|---|---|---|
| `GET /genealogy/v1/nodes/lookup?...` | 13 | no |
| `GET /genealogy/v1/nodes/{id}/ancestors` | 13 | no |
| `GET /genealogy/v1/nodes/{id}/descendants` | 13 | no |
| `GET /genealogy/v1/serial/{serial}/full-trace` | 13 | no |
| `GET /genealogy/v1/material-lot/{lot}/affected-products` | 13 | no |
| `POST /genealogy/v1/impact-assessments` | 13 | yes |
| `GET /genealogy/v1/impact-assessments/{id}` | 13 | no |
| `POST /genealogy/v1/exports` | 13 | yes |
| `POST /qa-review/v1/batches/{batchId}/packages` | 14 | yes |
| `GET /qa-review/v1/packages/{id}` | 14 | no |
| `GET /qa-review/v1/packages/{id}/exceptions` | 14 | no |
| `POST /qa-review/v1/packages/{id}/comments` | 14 | yes |
| `POST /qa-review/v1/items/{id}/request-action` | 14 | yes |
| `POST /qa-review/v1/items/{id}/disposition` | 14 | yes |
| `POST /qa-review/v1/packages/{id}/complete` | 14 | yes |
| `POST /qa-review/v1/packages/{id}/reindex` | 14 | yes |
| `GET /qa-review/v1/dashboard` | 14 | no |
| `POST /release/v1/scopes/{type}/{id}/evaluate` | 15 | yes |
| `GET /release/v1/scopes/{id}/eligibility` | 15 | no |
| `POST /release/v1/scopes/{id}/release` | 15 | yes |
| `POST /release/v1/scopes/{id}/hold` | 15 | yes |
| `POST /release/v1/scopes/{id}/reject` | 15 | yes |
| `POST /release/v1/scopes/{id}/rework` | 15 | yes |
| `POST /release/v1/scopes/{id}/reprocess` | 15 | yes |
| `POST /release/v1/scopes/{id}/destroy` | 15 | yes |
| `GET /release/v1/scopes/{id}/package` | 15 | no |
| `POST /packaging/v1/runs` | 16 | yes |
| `POST /packaging/v1/runs/{id}/line-clearance` | 16 | yes |
| `POST /packaging/v1/runs/{id}/labels/issue` | 16 | yes |
| `POST /packaging/v1/print-jobs` | 16 | yes |
| `POST /packaging/v1/labels/{id}/reprint` | 16 | yes |
| `POST /packaging/v1/runs/{id}/label-application` | 16 | yes |
| `POST /packaging/v1/runs/{id}/inspection` | 16 | yes |
| `POST /packaging/v1/runs/{id}/reconcile-labels` | 16 | yes |
| `POST /packaging/v1/runs/{id}/reconcile-packaging` | 16 | yes |
| `POST /packaging/v1/runs/{id}/complete` | 16 | yes |
| `POST /manufacturing-calculations/v1/yield/evaluate` | 17 | yes |
| `POST /manufacturing-calculations/v1/potency/evaluate` | 17 | yes |
| `POST /reconciliation/v1/material/evaluate` | 17 | yes |
| `POST /reconciliation/v1/packaging/evaluate` | 17 | yes |
| `POST /reconciliation/v1/labels/evaluate` | 17 | yes |
| `POST /reconciliation/v1/components/evaluate` | 17 | yes |
| `POST /reconciliation/v1/{id}/verify` | 17 | yes |
| `GET /reconciliation/v1/batches/{batchId}/summary` | 17 | no |

## Events

| Event | Doc | Producer |
|---|---|---|
| `GenealogyNodeCreated` | 13 | SPEC-EBMR-004 |
| `GenealogyEdgeCreated` | 13 | SPEC-EBMR-004 |
| `GenealogyEdgeCorrected` | 13 | SPEC-EBMR-004 |
| `ImpactAssessmentCreated` | 13 | SPEC-EBMR-004 |
| `ImpactAssessmentApproved` | 13 | SPEC-EBMR-004 |
| `QAReviewPackageCreated` | 14 | SPEC-EBMR-005 |
| `QAExceptionIndexed` | 14 | SPEC-EBMR-005 |
| `QAReviewStarted` | 14 | SPEC-EBMR-005 |
| `QAActionRequested` | 14 | SPEC-EBMR-005 |
| `QAReviewReopened` | 14 | SPEC-EBMR-005 |
| `QAReviewCompleted` | 14 | SPEC-EBMR-005 |
| `ReleaseEvaluationCompleted` | 15 | SPEC-EBMR-006 |
| `ReleaseEligibilityChanged` | 15 | SPEC-EBMR-006 |
| `ReleaseHoldPlaced` | 15 | SPEC-EBMR-006 |
| `ProductReleased` | 15 | SPEC-EBMR-006 |
| `ProductRejected` | 15 | SPEC-EBMR-006 |
| `ReworkDispositionApproved` | 15 | SPEC-EBMR-006 |
| `ReprocessDispositionApproved` | 15 | SPEC-EBMR-006 |
| `DestructionDispositionApproved` | 15 | SPEC-EBMR-006 |
| `PostReleaseHoldPlaced` | 15 | SPEC-EBMR-006 |
| `PackagingRunStarted` | 16 | SPEC-EBMR-007 |
| `LineClearanceCompleted` | 16 | SPEC-EBMR-007 |
| `LabelIssued` | 16 | SPEC-EBMR-007 |
| `LabelPrinted` | 16 | SPEC-EBMR-007 |
| `LabelReprinted` | 16 | SPEC-EBMR-007 |
| `LabelApplied` | 16 | SPEC-EBMR-007 |
| `LabelMismatchDetected` | 16 | SPEC-EBMR-007 |
| `LabelReconciliationCompleted` | 16 | SPEC-EBMR-007 |
| `PackagingReconciliationCompleted` | 16 | SPEC-EBMR-007 |
| `PackageAggregated` | 16 | SPEC-EBMR-007 |
| `PackagingCompleted` | 16 | SPEC-EBMR-007 |
| `YieldCalculated` | 17 | SPEC-EBMR-008 |
| `YieldOutOfLimit` | 17 | SPEC-EBMR-008 |
| `YieldVerified` | 17 | SPEC-EBMR-008 |
| `MaterialReconciliationCalculated` | 17 | SPEC-EBMR-008 |
| `ReconciliationFailed` | 17 | SPEC-EBMR-008 |
| `ReconciliationVerified` | 17 | SPEC-EBMR-008 |
| `ReconciliationSuperseded` | 17 | SPEC-EBMR-008 |

## Contract rules
- schemas committed before implementation
- canonical command/receipt/error/event envelopes
- `additionalProperties: false` on commands
- decimal quantities as strings with UOM
- registry entry in `37_API_EVENT_COMPATIBILITY_REGISTRY.md`
