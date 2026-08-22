# WP-01 — API & Event Contracts

## Operations

| Operation | Doc | State-changing |
|---|---|---|
| `POST /gxp/v1/commands/{commandType}` | 03 | yes |
| `GET /gxp/v1/commands/{commandId}/receipt` | 03 | no |
| `GET /gxp/v1/records/{type}/{id}/mutation-history` | 03 | no |
| `POST /gxp/v1/commands/{command_type}` | 03 | yes |
| `POST /signature/v1/challenges` | 04 | yes |
| `POST /signature/v1/challenges/{id}/verify` | 04 | yes |
| `POST /signature/v1/signatures/{id}/consume` | 04 | yes |
| `GET /audit/v1/records/{type}/{id}` | 05 | no |
| `GET /audit/v1/batches/{id}` | 05 | no |
| `GET /audit/v1/users/{subjectId}` | 05 | no |
| `GET /audit/v1/search?...` | 05 | no |
| `POST /audit/v1/exports` | 05 | yes |
| `POST /vault/v1/masters/{type}/{businessId}/release` | 06 | yes |
| `GET /vault/v1/objects/{objectId}` | 06 | no |
| `GET /vault/v1/objects/{objectId}/integrity` | 06 | no |
| `POST /vault/v1/objects/{objectId}/corrections` | 06 | yes |
| `POST /vault/v1/corrections/{id}/complete` | 06 | yes |
| `GET /vault/v1/business/{type}/{businessId}/versions` | 06 | no |
| `POST /policy/v1/decisions` | 07 | yes |
| `GET /iam/v1/subjects/{id}/effective-authority` | 07 | no |
| `GET /iam/v1/subjects/{id}/qualifications` | 07 | no |
| `POST /iam/v1/temporary-authorizations` | 07 | yes |
| `POST /iam/v1/break-glass` | 07 | yes |
| `POST /iam/v1/access-reviews` | 07 | yes |
| `GET /iam/v1/access-reviews/{id}/report` | 07 | no |
| `POST /rules/v1/drafts` | 08 | yes |
| `POST /rules/v1/{ruleId}/validate` | 08 | yes |
| `POST /rules/v1/{ruleId}/simulate` | 08 | yes |
| `POST /rules/v1/{ruleId}/release` | 08 | yes |
| `GET /rules/v1/{ruleId}/versions` | 08 | no |
| `POST /rules/v1/evaluate` | 08 | yes |

## Events

_none declared in the source specifications_

## Contract rules
- schemas committed before implementation
- canonical command/receipt/error/event envelopes
- `additionalProperties: false` on commands
- decimal quantities as strings with UOM
- registry entry in `37_API_EVENT_COMPATIBILITY_REGISTRY.md`
