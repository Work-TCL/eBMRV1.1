# WP-02 — API & Event Contracts

## Operations

| Operation | Doc | State-changing |
|---|---|---|
| `POST /products/v1/drafts` | 09 | yes |
| `PUT /products/v1/drafts/{id}` | 09 | yes |
| `POST /products/v1/drafts/{id}/submit` | 09 | yes |
| `POST /products/v1/drafts/{id}/release` | 09 | yes |
| `POST /products/v1/{id}/suspend` | 09 | yes |
| `POST /products/v1/{id}/reinstate` | 09 | yes |
| `GET /products/v1/{businessId}/versions` | 09 | no |
| `GET /products/v1/{id}` | 09 | no |
| `POST /products/v1/{id}/validate-completeness` | 09 | yes |
| `GET /products/v1/{id}/compatibility` | 09 | no |
| `GET /products/v1/{id}/issue-eligibility?site=...` | 09 | no |
| `POST /recipes/v1/drafts` | 10 | yes |
| `PUT /recipes/v1/drafts/{id}` | 10 | yes |
| `POST /recipes/v1/drafts/{id}/validate` | 10 | yes |
| `POST /recipes/v1/drafts/{id}/simulate` | 10 | yes |
| `POST /recipes/v1/drafts/{id}/submit` | 10 | yes |
| `POST /recipes/v1/drafts/{id}/release` | 10 | yes |
| `GET /recipes/v1/{familyId}/versions` | 10 | no |
| `GET /recipes/v1/versions/{id}` | 10 | no |
| `GET /recipes/v1/versions/{id}/compare/{otherId}` | 10 | no |
| `GET /recipes/v1/versions/{id}/issue-eligibility?site=...&date=...` | 10 | no |
| `POST /batches/v1` | 11 | yes |
| `POST /batches/{id}/issue` | 11 | yes |
| `POST /batches/{id}/start` | 11 | yes |
| `POST /batches/{id}/hold` | 11 | yes |
| `POST /batches/{id}/resume` | 11 | yes |
| `POST /batches/{id}/steps/{stepId}/start` | 11 | yes |
| `POST /batches/{id}/steps/{stepId}/results` | 11 | yes |
| `POST /batches/{id}/steps/{stepId}/complete` | 11 | yes |
| `POST /batches/{id}/steps/{stepId}/verify` | 11 | yes |
| `POST /batches/{id}/steps/{stepId}/correct` | 11 | yes |
| `POST /batches/{id}/production-complete` | 11 | yes |
| `POST /batches/{id}/abort` | 11 | yes |
| `GET /batches/{id}` | 11 | no |
| `GET /batches/{id}/execution-view` | 11 | no |
| `GET /batches/{id}/blockers` | 11 | no |
| `POST /devices/v1/lots` | 12 | yes |
| `POST /devices/v1/units/bulk-create` | 12 | yes |
| `POST /devices/v1/units/{id}/components` | 12 | yes |
| `POST /devices/v1/units/{id}/tests` | 12 | yes |
| `POST /devices/v1/units/{id}/inspection` | 12 | yes |
| `POST /devices/v1/units/{id}/hold` | 12 | yes |
| `POST /devices/v1/units/{id}/rework` | 12 | yes |
| `POST /devices/v1/units/{id}/accept` | 12 | yes |
| `GET /devices/v1/units/by-serial/{serial}` | 12 | no |
| `GET /devices/v1/units/{id}/history` | 12 | no |
| `GET /devices/v1/lots/{id}/release-readiness` | 12 | no |

## Events

| Event | Doc | Producer |
|---|---|---|
| `ProductDraftSubmitted` | 09 | SPEC-EBMR-000 |
| `ProductVersionReleased` | 09 | SPEC-EBMR-000 |
| `ProductVersionEffective` | 09 | SPEC-EBMR-000 |
| `ProductVersionSuspended` | 09 | SPEC-EBMR-000 |
| `ProductVersionReinstated` | 09 | SPEC-EBMR-000 |
| `ProductVersionSuperseded` | 09 | SPEC-EBMR-000 |
| `ConstituentCompatibilityReleased` | 09 | SPEC-EBMR-000 |
| `ProductSiteAdmissionChanged` | 09 | SPEC-EBMR-000 |
| `RecipeDraftSubmitted` | 10 | SPEC-EBMR-001 |
| `RecipeValidationFailed` | 10 | SPEC-EBMR-001 |
| `RecipeVersionReleased` | 10 | SPEC-EBMR-001 |
| `RecipeVersionEffective` | 10 | SPEC-EBMR-001 |
| `RecipeVersionSuspended` | 10 | SPEC-EBMR-001 |
| `RecipeVersionSuperseded` | 10 | SPEC-EBMR-001 |
| `BatchCreated` | 11 | SPEC-EBMR-002 |
| `BatchIssued` | 11 | SPEC-EBMR-002 |
| `BatchStarted` | 11 | SPEC-EBMR-002 |
| `BatchHeld` | 11 | SPEC-EBMR-002 |
| `BatchResumed` | 11 | SPEC-EBMR-002 |
| `StepReady` | 11 | SPEC-EBMR-002 |
| `StepStarted` | 11 | SPEC-EBMR-002 |
| `StepResultRecorded` | 11 | SPEC-EBMR-002 |
| `StepCompleted` | 11 | SPEC-EBMR-002 |
| `StepVerified` | 11 | SPEC-EBMR-002 |
| `StepExceptionRaised` | 11 | SPEC-EBMR-002 |
| `StepCorrected` | 11 | SPEC-EBMR-002 |
| `BranchSelected` | 11 | SPEC-EBMR-002 |
| `ProductionCompleted` | 11 | SPEC-EBMR-002 |
| `BatchAborted` | 11 | SPEC-EBMR-002 |
| `QAReviewRequested` | 11 | SPEC-EBMR-002 |
| `DeviceUnitCreated` | 12 | SPEC-EBMR-003 |
| `ComponentAssembled` | 12 | SPEC-EBMR-003 |
| `DeviceTestRecorded` | 12 | SPEC-EBMR-003 |
| `DeviceInspectionRecorded` | 12 | SPEC-EBMR-003 |
| `DeviceNonconformanceRaised` | 12 | SPEC-EBMR-003 |
| `DeviceReworkStarted` | 12 | SPEC-EBMR-003 |
| `DeviceAccepted` | 12 | SPEC-EBMR-003 |
| `DeviceScrapped` | 12 | SPEC-EBMR-003 |
| `DeviceReleased` | 12 | SPEC-EBMR-003 |

## Contract rules
- schemas committed before implementation
- canonical command/receipt/error/event envelopes
- `additionalProperties: false` on commands
- decimal quantities as strings with UOM
- registry entry in `37_API_EVENT_COMPATIBILITY_REGISTRY.md`
