# WP-04 — API & Event Contracts

## Operations

| Operation | Doc | State-changing |
|---|---|---|
| `POST /suppliers/v1` | 18 | yes |
| `POST /suppliers/{id}/qualifications` | 18 | yes |
| `POST /supplier-qualifications/{id}/approve` | 18 | yes |
| `POST /supplier-material-approvals` | 18 | yes |
| `POST /supplier-material-approvals/{id}/suspend` | 18 | yes |
| `GET /materials/{specId}/eligible-suppliers?site=...` | 18 | no |
| `POST /procurement/v1/requisitions` | 18 | yes |
| `POST /procurement/v1/purchase-orders` | 18 | yes |
| `POST /procurement/v1/purchase-orders/{id}/revise` | 18 | yes |
| `GET /procurement/v1/purchase-orders/{po}/receipt-expectation` | 18 | no |
| `POST /materials/v1/receipts` | 19 | yes |
| `POST /materials/v1/receipts/{id}/examine` | 19 | yes |
| `POST /materials/v1/lots/{id}/sampling-orders` | 19 | yes |
| `POST /sampling-orders/{id}/collect` | 19 | yes |
| `POST /materials/v1/lots/{id}/release` | 19 | yes |
| `POST /materials/v1/lots/{id}/reject` | 19 | yes |
| `POST /materials/v1/lots/{id}/retest` | 19 | yes |
| `GET /materials/v1/lots/{id}/quality-status` | 19 | no |
| `GET /materials/v1/lots/{id}/release-readiness` | 19 | no |
| `GET /inventory/v1/availability` | 20 | no |
| `POST /inventory/v1/reservations` | 20 | yes |
| `POST /inventory/v1/reservations/{id}/release` | 20 | yes |
| `POST /inventory/v1/transfers` | 20 | yes |
| `POST /inventory/v1/containers/{id}/split` | 20 | yes |
| `POST /inventory/v1/containers/merge` | 20 | yes |
| `POST /inventory/v1/cycle-counts` | 20 | yes |
| `GET /inventory/v1/lots/{id}/ledger` | 20 | no |
| `GET /inventory/v1/reconciliation/erp` | 20 | no |
| `POST /dispensing/v1/orders` | 21 | yes |
| `POST /dispensing/v1/orders/{id}/select-source` | 21 | yes |
| `POST /dispensing/v1/orders/{id}/start` | 21 | yes |
| `POST /dispensing/v1/orders/{id}/readings` | 21 | yes |
| `POST /dispensing/v1/orders/{id}/manual-reading` | 21 | yes |
| `POST /dispensing/v1/orders/{id}/verify` | 21 | yes |
| `POST /dispensing/v1/orders/{id}/complete` | 21 | yes |
| `POST /dispensing/v1/orders/{id}/cancel` | 21 | yes |
| `GET /dispensing/v1/queue` | 21 | no |
| `POST /materials/v1/consumptions` | 22 | yes |
| `POST /materials/v1/returns` | 22 | yes |
| `POST /inventory/v1/adjustments` | 22 | yes |
| `POST /inventory/v1/adjustments/{id}/approve` | 22 | yes |
| `POST /materials/v1/destructions` | 22 | yes |
| `POST /materials/v1/destructions/{id}/execute` | 22 | yes |
| `POST /reconciliation/v1/batches/{batchId}/materials/evaluate` | 22 | yes |
| `GET /reconciliation/v1/batches/{batchId}/materials` | 22 | no |
| `POST /qc/v1/specifications/drafts` | 23 | yes |
| `POST /qc/v1/specifications/{id}/release` | 23 | yes |
| `POST /qc/v1/samples` | 23 | yes |
| `POST /qc/v1/samples/{id}/receive` | 23 | yes |
| `POST /qc/v1/test-orders` | 23 | yes |
| `POST /qc/v1/test-orders/{id}/start` | 23 | yes |
| `POST /qc/v1/test-orders/{id}/raw-data` | 23 | yes |
| `POST /qc/v1/test-orders/{id}/results` | 23 | yes |
| `POST /qc/v1/test-orders/{id}/complete` | 23 | yes |
| `POST /qc/v1/test-orders/{id}/review` | 23 | yes |
| `POST /qc/v1/results/{id}/correct` | 23 | yes |
| `GET /qc/v1/samples/{id}/record` | 23 | no |
| `GET /qc/v1/release-readiness?...` | 23 | no |
| `POST /integrations/lims/{instance}/samples` | 24 | yes |
| `POST /integrations/lims/{instance}/samples/{id}/cancel` | 24 | yes |
| `POST /integrations/lims/{instance}/reconcile` | 24 | yes |
| `GET /integrations/lims/{instance}/health` | 24 | no |
| `POST /integrations/lims/{instance}/events/results` | 24 | yes |
| `POST /integrations/lims/{instance}/events/status` | 24 | yes |
| `POST /quality/oos/v1/from-result/{resultId}` | 25 | yes |
| `GET /quality/oos/v1/{id}` | 25 | no |
| `POST /quality/oos/v1/{id}/lab-investigation` | 25 | yes |
| `POST /quality/oos/v1/{id}/classify-lab-cause` | 25 | yes |
| `POST /quality/oos/v1/{id}/extended-investigation` | 25 | yes |
| `POST /quality/oos/v1/{id}/retest-plans` | 25 | yes |
| `POST /quality/oos/v1/{id}/resample-plans` | 25 | yes |
| `POST /quality/oos/v1/{id}/impact` | 25 | yes |
| `POST /quality/oos/v1/{id}/disposition` | 25 | yes |
| `POST /quality/oos/v1/{id}/close` | 25 | yes |
| `POST /quality/oot/v1/evaluate` | 25 | yes |
| `POST /quality/oot/v1/{id}/close` | 25 | yes |

## Events

| Event | Doc | Producer |
|---|---|---|
| `SupplierQualificationApproved` | 18 | SPEC-MAT-001 |
| `SupplierMaterialApproved` | 18 | SPEC-MAT-001 |
| `SupplierSuspended` | 18 | SPEC-MAT-001 |
| `SupplierDisqualified` | 18 | SPEC-MAT-001 |
| `PurchaseRequisitionApproved` | 18 | SPEC-MAT-001 |
| `PurchaseOrderIssued` | 18 | SPEC-MAT-001 |
| `PurchaseOrderRegulatedFieldsChanged` | 18 | SPEC-MAT-001 |
| `MaterialReceived` | 19 | SPEC-MAT-002A |
| `MaterialQuarantined` | 19 | SPEC-MAT-002A |
| `SamplingOrdered` | 19 | SPEC-MAT-002A |
| `SampleCollected` | 19 | SPEC-MAT-002A |
| `MaterialQCCompleted` | 19 | SPEC-MAT-002A |
| `MaterialReleased` | 19 | SPEC-MAT-002A |
| `MaterialRejected` | 19 | SPEC-MAT-002A |
| `MaterialRetestRequired` | 19 | SPEC-MAT-002A |
| `ReceiptDiscrepancyRaised` | 19 | SPEC-MAT-002A |
| `InventoryReceived` | 20 | SPEC-MAT-002B |
| `InventoryTransferred` | 20 | SPEC-MAT-002B |
| `InventoryReserved` | 20 | SPEC-MAT-002B |
| `InventoryReservationReleased` | 20 | SPEC-MAT-002B |
| `ContainerSplit` | 20 | SPEC-MAT-002B |
| `ContainerMerged` | 20 | SPEC-MAT-002B |
| `MaterialQualityHoldPlaced` | 20 | SPEC-MAT-002B |
| `InventoryAdjusted` | 20 | SPEC-MAT-002B |
| `InventoryERPDiscrepancyDetected` | 20 | SPEC-MAT-002B |
| `DispensingStarted` | 21 | SPEC-MAT-002C |
| `DispensingSourceSelected` | 21 | SPEC-MAT-002C |
| `WeighingReadingAccepted` | 21 | SPEC-MAT-002C |
| `WeighingExceptionRaised` | 21 | SPEC-MAT-002C |
| `DispensingVerified` | 21 | SPEC-MAT-002C |
| `MaterialDispensed` | 21 | SPEC-MAT-002C |
| `DispensingCancelled` | 21 | SPEC-MAT-002C |
| `MaterialConsumed` | 22 | SPEC-MAT-002D |
| `MaterialReturned` | 22 | SPEC-MAT-002D |
| `MaterialSampled` | 22 | SPEC-MAT-002D |
| `MaterialLossRecorded` | 22 | SPEC-MAT-002D |
| `InventoryAdjustmentApproved` | 22 | SPEC-MAT-002D |
| `MaterialDestroyed` | 22 | SPEC-MAT-002D |
| `MaterialReconciliationCalculated` | 22 | SPEC-MAT-002D |
| `MaterialReconciliationFailed` | 22 | SPEC-MAT-002D |
| `ERPInventoryPostingFailed` | 22 | SPEC-MAT-002D |
| `QCSampleCreated` | 23 | SPEC-QC-001 |
| `QCSampleReceived` | 23 | SPEC-QC-001 |
| `QCTestStarted` | 23 | SPEC-QC-001 |
| `QCResultRecorded` | 23 | SPEC-QC-001 |
| `QCResultOOSDetected` | 23 | SPEC-QC-001 |
| `QCResultOOTDetected` | 23 | SPEC-QC-001 |
| `QCTestAnalystCompleted` | 23 | SPEC-QC-001 |
| `QCTestReviewed` | 23 | SPEC-QC-001 |
| `QCResultCorrected` | 23 | SPEC-QC-001 |
| `QCTestInvalidated` | 23 | SPEC-QC-001 |
| `LIMSSampleRequested` | 24 | SPEC-QC-002 |
| `LIMSStatusReceived` | 24 | SPEC-QC-002 |
| `LIMSResultReceived` | 24 | SPEC-QC-002 |
| `LIMSResultAccepted` | 24 | SPEC-QC-002 |
| `LIMSResultRejected` | 24 | SPEC-QC-002 |
| `LIMSResultRevised` | 24 | SPEC-QC-002 |
| `LIMSIntegrationDeadLettered` | 24 | SPEC-QC-002 |
| `LIMSReconciliationMismatchDetected` | 24 | SPEC-QC-002 |
| `OOSOpened` | 25 | SPEC-QC-003 |
| `OOSLabInvestigationStarted` | 25 | SPEC-QC-003 |
| `OOSAssignableCauseDetermined` | 25 | SPEC-QC-003 |
| `OOSExtendedInvestigationStarted` | 25 | SPEC-QC-003 |
| `OOSRetestAuthorized` | 25 | SPEC-QC-003 |
| `OOSRetestCompleted` | 25 | SPEC-QC-003 |
| `OOSResampleAuthorized` | 25 | SPEC-QC-003 |
| `OOSImpactAssessed` | 25 | SPEC-QC-003 |
| `OOSDispositionApproved` | 25 | SPEC-QC-003 |
| `OOSClosed` | 25 | SPEC-QC-003 |
| `OOTDetected` | 25 | SPEC-QC-003 |
| `OOTInvestigationStarted` | 25 | SPEC-QC-003 |
| `OOTClosed` | 25 | SPEC-QC-003 |

## Contract rules
- schemas committed before implementation
- canonical command/receipt/error/event envelopes
- `additionalProperties: false` on commands
- decimal quantities as strings with UOM
- registry entry in `37_API_EVENT_COMPATIBILITY_REGISTRY.md`
