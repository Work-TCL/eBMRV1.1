# WP-05 — API & Event Contracts

## Operations

| Operation | Doc | State-changing |
|---|---|---|
| `POST /qms/v1/deviations` | 26 | yes |
| `POST /qms/v1/deviations/{id}/triage` | 26 | yes |
| `POST /qms/v1/deviations/{id}/contain` | 26 | yes |
| `POST /qms/v1/deviations/{id}/investigation` | 26 | yes |
| `POST /qms/v1/deviations/{id}/impact` | 26 | yes |
| `POST /qms/v1/deviations/{id}/disposition` | 26 | yes |
| `POST /qms/v1/deviations/{id}/extend` | 26 | yes |
| `POST /qms/v1/deviations/{id}/close` | 26 | yes |
| `POST /qms/v1/deviations/{id}/reopen` | 26 | yes |
| `POST /qms/v1/capas` | 27 | yes |
| `POST /qms/v1/capas/{id}/plan` | 27 | yes |
| `POST /qms/v1/capas/{id}/actions` | 27 | yes |
| `POST /qms/v1/actions/{id}/complete` | 27 | yes |
| `POST /qms/v1/capas/{id}/effectiveness` | 27 | yes |
| `POST /qms/v1/capas/{id}/extend` | 27 | yes |
| `POST /qms/v1/capas/{id}/close` | 27 | yes |
| `POST /qms/v1/capas/{id}/reopen` | 27 | yes |
| `POST /qms/v1/nonconformances` | 28 | yes |
| `POST /qms/v1/nonconformances/{id}/segregate` | 28 | yes |
| `POST /qms/v1/nonconformances/{id}/evaluate` | 28 | yes |
| `POST /qms/v1/nonconformances/{id}/disposition` | 28 | yes |
| `POST /qms/v1/nonconformances/{id}/verify` | 28 | yes |
| `POST /qms/v1/nonconformances/{id}/close` | 28 | yes |
| `POST /qms/v1/changes` | 29 | yes |
| `POST /qms/v1/changes/{id}/impact` | 29 | yes |
| `POST /qms/v1/changes/{id}/approve` | 29 | yes |
| `POST /qms/v1/changes/{id}/tasks` | 29 | yes |
| `POST /qms/v1/changes/{id}/implement` | 29 | yes |
| `POST /qms/v1/changes/{id}/verify` | 29 | yes |
| `POST /qms/v1/changes/{id}/make-effective` | 29 | yes |
| `POST /qms/v1/changes/{id}/close` | 29 | yes |
| `POST /documents/v1/drafts` | 30 | yes |
| `POST /documents/v1/drafts/{id}/submit` | 30 | yes |
| `POST /documents/v1/drafts/{id}/release` | 30 | yes |
| `POST /documents/v1/versions/{id}/make-effective` | 30 | yes |
| `POST /documents/v1/versions/{id}/obsolete` | 30 | yes |
| `POST /documents/v1/versions/{id}/controlled-copies` | 30 | yes |
| `GET /documents/v1/{code}/versions` | 30 | no |
| `POST /training/v1/requirements` | 31 | yes |
| `POST /training/v1/assignments` | 31 | yes |
| `POST /training/v1/assignments/{id}/complete` | 31 | yes |
| `POST /training/v1/assignments/{id}/assess` | 31 | yes |
| `POST /training/v1/qualifications` | 31 | yes |
| `POST /training/v1/waivers` | 31 | yes |
| `GET /training/v1/subjects/{id}/status` | 31 | no |
| `GET /training/v1/matrix` | 31 | no |
| `POST /qms/v1/supplier-cases` | 32 | yes |
| `POST /qms/v1/supplier-cases/{id}/scar` | 32 | yes |
| `POST /qms/v1/scars/{id}/response` | 32 | yes |
| `POST /qms/v1/scars/{id}/review` | 32 | yes |
| `POST /qms/v1/scars/{id}/effectiveness` | 32 | yes |
| `POST /qms/v1/scars/{id}/close` | 32 | yes |
| `POST /qms/v1/risks` | 33 | yes |
| `POST /qms/v1/risks/{id}/assessments` | 33 | yes |
| `POST /qms/v1/risks/{id}/controls` | 33 | yes |
| `POST /qms/v1/risks/{id}/accept` | 33 | yes |
| `POST /qms/v1/risks/{id}/review` | 33 | yes |
| `GET /qms/v1/risks/dashboard` | 33 | no |
| `POST /qms/v1/audits` | 34 | yes |
| `POST /qms/v1/audits/{id}/start` | 34 | yes |
| `POST /qms/v1/audits/{id}/findings` | 34 | yes |
| `POST /qms/v1/findings/{id}/response` | 34 | yes |
| `POST /qms/v1/findings/{id}/verify` | 34 | yes |
| `POST /qms/v1/audits/{id}/close` | 34 | yes |
| `POST /qms/v1/complaints` | 35 | yes |
| `POST /qms/v1/complaints/{id}/triage` | 35 | yes |
| `POST /qms/v1/complaints/{id}/investigation-decision` | 35 | yes |
| `POST /qms/v1/complaints/{id}/investigation` | 35 | yes |
| `POST /qms/v1/complaints/{id}/reportability` | 35 | yes |
| `POST /qms/v1/complaints/{id}/response` | 35 | yes |
| `POST /qms/v1/complaints/{id}/close` | 35 | yes |
| `POST /qms/v1/field-actions` | 36 | yes |
| `POST /qms/v1/field-actions/{id}/scope` | 36 | yes |
| `POST /qms/v1/field-actions/{id}/reportability` | 36 | yes |
| `POST /qms/v1/field-actions/{id}/approve` | 36 | yes |
| `POST /qms/v1/field-actions/{id}/communications` | 36 | yes |
| `POST /qms/v1/field-actions/{id}/reconcile` | 36 | yes |
| `POST /qms/v1/field-actions/{id}/effectiveness` | 36 | yes |
| `POST /qms/v1/field-actions/{id}/close` | 36 | yes |
| `POST /quality-metrics/v1/definitions` | 37 | yes |
| `POST /quality-metrics/v1/definitions/{id}/release` | 37 | yes |
| `POST /quality-metrics/v1/calculate` | 37 | yes |
| `GET /quality-metrics/v1/dashboard` | 37 | no |
| `POST /quality-metrics/v1/management-review-packages` | 37 | yes |
| `POST /effectiveness/v1/checks` | 37 | yes |
| `POST /effectiveness/v1/checks/{id}/evaluate` | 37 | yes |

## Events

| Event | Doc | Producer |
|---|---|---|
| `DeviationOpened` | 26 | SPEC-QMS-001 |
| `DeviationContained` | 26 | SPEC-QMS-001 |
| `DeviationInvestigationStarted` | 26 | SPEC-QMS-001 |
| `DeviationImpactAssessed` | 26 | SPEC-QMS-001 |
| `DeviationCAPARequired` | 26 | SPEC-QMS-001 |
| `DeviationDispositionApproved` | 26 | SPEC-QMS-001 |
| `DeviationClosed` | 26 | SPEC-QMS-001 |
| `DeviationReopened` | 26 | SPEC-QMS-001 |
| `CAPAOpened` | 27 | SPEC-QMS-002 |
| `CAPAPlanApproved` | 27 | SPEC-QMS-002 |
| `CAPAActionAssigned` | 27 | SPEC-QMS-002 |
| `CAPAActionCompleted` | 27 | SPEC-QMS-002 |
| `CAPAEffectivenessStarted` | 27 | SPEC-QMS-002 |
| `CAPAEffectivenessFailed` | 27 | SPEC-QMS-002 |
| `CAPAClosed` | 27 | SPEC-QMS-002 |
| `CAPAReopened` | 27 | SPEC-QMS-002 |
| `NonconformanceOpened` | 28 | SPEC-QMS-003 |
| `NonconformingProductSegregated` | 28 | SPEC-QMS-003 |
| `NCRDispositionApproved` | 28 | SPEC-QMS-003 |
| `NCRReworkStarted` | 28 | SPEC-QMS-003 |
| `NCRReinspectionCompleted` | 28 | SPEC-QMS-003 |
| `NCRClosed` | 28 | SPEC-QMS-003 |
| `ChangeRequested` | 29 | SPEC-QMS-004 |
| `ChangeImpactAssessed` | 29 | SPEC-QMS-004 |
| `ChangeApproved` | 29 | SPEC-QMS-004 |
| `ChangeImplementationStarted` | 29 | SPEC-QMS-004 |
| `ChangeValidationCompleted` | 29 | SPEC-QMS-004 |
| `ChangeMadeEffective` | 29 | SPEC-QMS-004 |
| `ChangeClosed` | 29 | SPEC-QMS-004 |
| `EmergencyChangeOpened` | 29 | SPEC-QMS-004 |
| `DocumentVersionReleased` | 30 | SPEC-QMS-005 |
| `DocumentVersionEffective` | 30 | SPEC-QMS-005 |
| `DocumentVersionSuperseded` | 30 | SPEC-QMS-005 |
| `DocumentObsoleted` | 30 | SPEC-QMS-005 |
| `ControlledCopyIssued` | 30 | SPEC-QMS-005 |
| `DocumentPeriodicReviewDue` | 30 | SPEC-QMS-005 |
| `TrainingAssigned` | 31 | SPEC-QMS-006 |
| `TrainingCompleted` | 31 | SPEC-QMS-006 |
| `TrainingFailed` | 31 | SPEC-QMS-006 |
| `QualificationIssued` | 31 | SPEC-QMS-006 |
| `QualificationExpired` | 31 | SPEC-QMS-006 |
| `RetrainingRequired` | 31 | SPEC-QMS-006 |
| `TrainingWaiverApproved` | 31 | SPEC-QMS-006 |
| `SupplierQualityCaseOpened` | 32 | SPEC-QMS-007 |
| `SCARIssued` | 32 | SPEC-QMS-007 |
| `SCARResponseReceived` | 32 | SPEC-QMS-007 |
| `SupplierSourceSuspended` | 32 | SPEC-QMS-007 |
| `SCAREffectivenessPassed` | 32 | SPEC-QMS-007 |
| `SCARClosed` | 32 | SPEC-QMS-007 |
| `RiskCreated` | 33 | SPEC-QMS-008 |
| `RiskAssessmentCompleted` | 33 | SPEC-QMS-008 |
| `RiskMitigationRequired` | 33 | SPEC-QMS-008 |
| `RiskAccepted` | 33 | SPEC-QMS-008 |
| `RiskReviewTriggered` | 33 | SPEC-QMS-008 |
| `RiskReassessed` | 33 | SPEC-QMS-008 |
| `InternalAuditScheduled` | 34 | SPEC-QMS-009 |
| `InternalAuditStarted` | 34 | SPEC-QMS-009 |
| `AuditFindingOpened` | 34 | SPEC-QMS-009 |
| `AuditReportApproved` | 34 | SPEC-QMS-009 |
| `AuditFindingClosed` | 34 | SPEC-QMS-009 |
| `InternalAuditClosed` | 34 | SPEC-QMS-009 |
| `ComplaintReceived` | 35 | SPEC-QMS-010 |
| `ComplaintInvestigationRequired` | 35 | SPEC-QMS-010 |
| `ComplaintInvestigationWaivedWithRationale` | 35 | SPEC-QMS-010 |
| `ComplaintReportabilityAssessmentCompleted` | 35 | SPEC-QMS-010 |
| `ComplaintCAPAOpened` | 35 | SPEC-QMS-010 |
| `ComplaintFieldActionAssessmentOpened` | 35 | SPEC-QMS-010 |
| `ComplaintClosed` | 35 | SPEC-QMS-010 |
| `FieldActionAssessmentOpened` | 36 | SPEC-QMS-011 |
| `FieldActionScopeFrozen` | 36 | SPEC-QMS-011 |
| `FieldActionApproved` | 36 | SPEC-QMS-011 |
| `FieldActionNotificationSent` | 36 | SPEC-QMS-011 |
| `FieldActionUnitReturned` | 36 | SPEC-QMS-011 |
| `FieldActionCorrectionCompleted` | 36 | SPEC-QMS-011 |
| `FieldActionEffectivenessCompleted` | 36 | SPEC-QMS-011 |
| `FieldActionClosed` | 36 | SPEC-QMS-011 |
| `FieldActionScopeExpanded` | 36 | SPEC-QMS-011 |
| `QualityMetricCalculated` | 37 | SPEC-QMS-012 |
| `QualityTrendThresholdExceeded` | 37 | SPEC-QMS-012 |
| `QualitySignalAssessmentOpened` | 37 | SPEC-QMS-012 |
| `EffectivenessCheckDue` | 37 | SPEC-QMS-012 |
| `EffectivenessCheckPassed` | 37 | SPEC-QMS-012 |
| `EffectivenessCheckFailed` | 37 | SPEC-QMS-012 |
| `ManagementReviewPackageFrozen` | 37 | SPEC-QMS-012 |

## Contract rules
- schemas committed before implementation
- canonical command/receipt/error/event envelopes
- `additionalProperties: false` on commands
- decimal quantities as strings with UOM
- registry entry in `37_API_EVENT_COMPATIBILITY_REGISTRY.md`
