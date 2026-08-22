# WP-09 — API & Event Contracts

## Operations

| Operation | Doc | State-changing |
|---|---|---|
| `POST /postmarket/v1/sources` | 58 | yes |
| `POST /postmarket/v1/safety-cases` | 58 | yes |
| `POST /postmarket/v1/safety-cases/{id}/resolve-product` | 58 | yes |
| `POST /postmarket/v1/safety-cases/{id}/classifications` | 58 | yes |
| `POST /postmarket/v1/safety-cases/{id}/followups` | 58 | yes |
| `POST /postmarket/v1/safety-cases/{id}/duplicate-links` | 58 | yes |
| `POST /postmarket/v1/signals` | 58 | yes |
| `POST /postmarket/v1/signals/{id}/assessments` | 58 | yes |
| `POST /postmarket/v1/signals/{id}/escalations` | 58 | yes |
| `POST /postmarket/v1/periodic-datasets:freeze` | 58 | yes |
| `GET /postmarket/v1/dashboard` | 58 | no |
| `POST /regulatory/v1/cases/{caseId}/reportability-tracks` | 59 | yes |
| `POST /regulatory/v1/tracks/{id}/deadline:calculate` | 59 | yes |
| `POST /regulatory/v1/tracks/{id}/decisions` | 59 | yes |
| `POST /regulatory/v1/tracks/{id}/reports` | 59 | yes |
| `POST /regulatory/v1/reports/{id}/approve` | 59 | yes |
| `POST /regulatory/v1/reports/{id}/payloads:generate` | 59 | yes |
| `POST /regulatory/v1/reports/{id}/submissions` | 59 | yes |
| `POST /regulatory/v1/submissions/{id}/acknowledgements` | 59 | yes |
| `POST /regulatory/v1/reports/{id}/followups` | 59 | yes |
| `POST /regulatory/v1/cases/{id}/part4-deduplication:evaluate` | 59 | yes |
| `POST /postmarket/v1/applicant-relationships` | 60 | yes |
| `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate` | 60 | yes |
| `POST /postmarket/v1/sharing/{id}/package` | 60 | yes |
| `POST /postmarket/v1/sharing/{id}/record-sent` | 60 | yes |
| `POST /postmarket/v1/field-actions/{id}/correction-removal-assessment` | 60 | yes |
| `POST /postmarket/v1/correction-removal/{id}/decision` | 60 | yes |
| `POST /postmarket/v1/field-alerts` | 60 | yes |
| `POST /postmarket/v1/field-alerts/{id}/decision` | 60 | yes |
| `POST /postmarket/v1/bpdr-tracks` | 60 | yes |
| `POST /postmarket/v1/periodic-cycles:generate` | 60 | yes |
| `POST /postmarket/v1/periodic-cycles/{id}/dataset:freeze` | 60 | yes |
| `POST /postmarket/v1/fda-requests` | 60 | yes |
| `POST /postmarket/v1/obligations/{id}/deadline-overrides` | 60 | yes |
| `POST /postmarket/v1/retention:calculate` | 60 | yes |

## Events

| Event | Doc | Producer |
|---|---|---|
| `SafetyCaseCreated` | 58 | SPEC-PM-001 |
| `SafetyProductResolved` | 58 | SPEC-PM-001 |
| `SafetyCaseClassified` | 58 | SPEC-PM-001 |
| `SafetyCaseFollowupReceived` | 58 | SPEC-PM-001 |
| `SafetySignalRuleTriggered` | 58 | SPEC-PM-001 |
| `SafetySignalOpened` | 58 | SPEC-PM-001 |
| `SafetySignalAssessed` | 58 | SPEC-PM-001 |
| `SafetySignalEscalated` | 58 | SPEC-PM-001 |
| `PeriodicSafetyDatasetFrozen` | 58 | SPEC-PM-001 |
| `ApplicantRelationshipConfigured` | 60 | SPEC-PM-003 |
| `Part4SharingAssessmentCreated` | 60 | SPEC-PM-003 |
| `ConstituentSharingPackageCreated` | 60 | SPEC-PM-003 |
| `ConstituentInformationShared` | 60 | SPEC-PM-003 |
| `CorrectionRemovalAssessmentOpened` | 60 | SPEC-PM-003 |
| `CorrectionRemovalReportabilityDecided` | 60 | SPEC-PM-003 |
| `FieldAlertAssessmentOpened` | 60 | SPEC-PM-003 |
| `FieldAlertDecisionRecorded` | 60 | SPEC-PM-003 |
| `BPDRTrackCreated` | 60 | SPEC-PM-003 |
| `PeriodicSafetyScheduleGenerated` | 60 | SPEC-PM-003 |
| `PeriodicDatasetFrozen` | 60 | SPEC-PM-003 |
| `FDAInformationRequestOpened` | 60 | SPEC-PM-003 |
| `RegulatoryDeadlineOverridden` | 60 | SPEC-PM-003 |
| `PostmarketRetentionPolicyCalculated` | 60 | SPEC-PM-003 |
| `PostmarketLegalHoldPlaced` | 60 | SPEC-PM-003 |

## Contract rules
- schemas committed before implementation
- canonical command/receipt/error/event envelopes
- `additionalProperties: false` on commands
- decimal quantities as strings with UOM
- registry entry in `37_API_EVENT_COMPATIBILITY_REGISTRY.md`
