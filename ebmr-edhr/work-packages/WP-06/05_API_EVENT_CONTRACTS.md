# WP-06 — API & Event Contracts

## Operations

| Operation | Doc | State-changing |
|---|---|---|
| `POST /equipment/v1/assets` | 38 | yes |
| `POST /equipment/v1/{id}/qualifications` | 38 | yes |
| `POST /equipment/v1/{id}/calibrations` | 38 | yes |
| `POST /equipment/v1/{id}/maintenance` | 38 | yes |
| `POST /equipment/v1/{id}/hold` | 38 | yes |
| `POST /equipment/v1/{id}/return-to-service` | 38 | yes |
| `GET /equipment/v1/{id}/eligibility` | 38 | no |
| `GET /equipment/v1/{id}/history` | 38 | no |
| `GET /equipment/v1/dashboard` | 38 | no |
| `POST /cleaning/v1/executions` | 39 | yes |
| `POST /cleaning/v1/executions/{id}/steps` | 39 | yes |
| `POST /cleaning/v1/executions/{id}/complete` | 39 | yes |
| `POST /cleaning/v1/executions/{id}/verify` | 39 | yes |
| `POST /line-clearance/v1` | 39 | yes |
| `POST /line-clearance/v1/{id}/complete` | 39 | yes |
| `GET /cleaning/v1/equipment/{id}/status` | 39 | no |
| `POST /aseptic/v1/operations` | 40 | yes |
| `POST /aseptic/v1/operations/{id}/start` | 40 | yes |
| `POST /aseptic/v1/operations/{id}/interventions` | 40 | yes |
| `POST /aseptic/v1/operations/{id}/events` | 40 | yes |
| `POST /aseptic/v1/operations/{id}/complete` | 40 | yes |
| `GET /aseptic/v1/operations/{id}/readiness` | 40 | no |
| `GET /aseptic/v1/operations/{id}/review-summary` | 40 | no |
| `POST /em/v1/programs` | 41 | yes |
| `POST /em/v1/tasks` | 41 | yes |
| `POST /em/v1/tasks/{id}/collect` | 41 | yes |
| `POST /em/v1/results` | 41 | yes |
| `POST /em/v1/results/{id}/review` | 41 | yes |
| `POST /em/v1/excursions/{id}/impact` | 41 | yes |
| `GET /em/v1/areas/{id}/readiness` | 41 | no |
| `GET /em/v1/trends` | 41 | no |
| `POST /sterilization/v1/cycles` | 42 | yes |
| `POST /sterilization/v1/cycles/{id}/start` | 42 | yes |
| `POST /sterilization/v1/cycles/{id}/data` | 42 | yes |
| `POST /sterilization/v1/cycles/{id}/review` | 42 | yes |
| `POST /cip-sip/v1/cycles` | 42 | yes |
| `POST /filtration/v1/filters/install` | 42 | yes |
| `POST /filtration/v1/filters/{id}/integrity-tests` | 42 | yes |
| `POST /filtration/v1/uses/{id}/complete` | 42 | yes |
| `GET /sterilization/v1/items/{id}/status` | 42 | no |
| `POST /edge/v1/enrollments` | 43 | yes |
| `GET /edge/v1/gateways/{gatewayId}/configuration` | 43 | no |
| `POST /edge/v1/gateways/{gatewayId}/observations:batch` | 43 | yes |
| `POST /edge/v1/gateways/{gatewayId}/health` | 43 | yes |
| `POST /edge/v1/gateways/{gatewayId}/certificate-rotation` | 43 | yes |
| `POST /edge/v1/gateways/{gatewayId}/security-events` | 43 | yes |

## Events

| Event | Doc | Producer |
|---|---|---|
| `EquipmentInstalled` | 38 | SPEC-EQP-001 |
| `EquipmentQualified` | 38 | SPEC-EQP-001 |
| `CalibrationDue` | 38 | SPEC-EQP-001 |
| `EquipmentCalibrated` | 38 | SPEC-EQP-001 |
| `CalibrationOutOfTolerance` | 38 | SPEC-EQP-001 |
| `MaintenanceDue` | 38 | SPEC-EQP-001 |
| `EquipmentOutOfService` | 38 | SPEC-EQP-001 |
| `MaintenanceCompleted` | 38 | SPEC-EQP-001 |
| `EquipmentReturnedToService` | 38 | SPEC-EQP-001 |
| `EquipmentRetired` | 38 | SPEC-EQP-001 |
| `CleaningStarted` | 39 | SPEC-EQP-002 |
| `CleaningCompleted` | 39 | SPEC-EQP-002 |
| `CleaningVerificationFailed` | 39 | SPEC-EQP-002 |
| `EquipmentMarkedClean` | 39 | SPEC-EQP-002 |
| `CleanHoldExpired` | 39 | SPEC-EQP-002 |
| `LineClearanceStarted` | 39 | SPEC-EQP-002 |
| `LineClearanceCompleted` | 39 | SPEC-EQP-002 |
| `LineClearanceFailed` | 39 | SPEC-EQP-002 |
| `AsepticOperationStarted` | 40 | SPEC-EQP-003 |
| `AsepticInterventionRecorded` | 40 | SPEC-EQP-003 |
| `UnplannedInterventionDetected` | 40 | SPEC-EQP-003 |
| `AsepticHoldTimeExceeded` | 40 | SPEC-EQP-003 |
| `AsepticEnvironmentExcursionDetected` | 40 | SPEC-EQP-003 |
| `AsepticOperationHeld` | 40 | SPEC-EQP-003 |
| `AsepticOperationCompleted` | 40 | SPEC-EQP-003 |
| `EMTaskScheduled` | 41 | SPEC-EQP-004 |
| `EMSampleCollected` | 41 | SPEC-EQP-004 |
| `EMResultRecorded` | 41 | SPEC-EQP-004 |
| `EMAlertTriggered` | 41 | SPEC-EQP-004 |
| `EMActionLimitExceeded` | 41 | SPEC-EQP-004 |
| `EMDataGapDetected` | 41 | SPEC-EQP-004 |
| `EMAreaHeld` | 41 | SPEC-EQP-004 |
| `EMExcursionClosed` | 41 | SPEC-EQP-004 |
| `SterilizationCycleStarted` | 42 | SPEC-EQP-005 |
| `SterilizationCycleCompleted` | 42 | SPEC-EQP-005 |
| `SterilizationCycleFailed` | 42 | SPEC-EQP-005 |
| `SterilizationCycleAccepted` | 42 | SPEC-EQP-005 |
| `SIPStatusIssued` | 42 | SPEC-EQP-005 |
| `CIPCompleted` | 42 | SPEC-EQP-005 |
| `FilterInstalled` | 42 | SPEC-EQP-005 |
| `FilterIntegrityPassed` | 42 | SPEC-EQP-005 |
| `FilterIntegrityFailed` | 42 | SPEC-EQP-005 |
| `SterileStatusExpired` | 42 | SPEC-EQP-005 |

## Contract rules
- schemas committed before implementation
- canonical command/receipt/error/event envelopes
- `additionalProperties: false` on commands
- decimal quantities as strings with UOM
- registry entry in `37_API_EVENT_COMPATIBILITY_REGISTRY.md`
