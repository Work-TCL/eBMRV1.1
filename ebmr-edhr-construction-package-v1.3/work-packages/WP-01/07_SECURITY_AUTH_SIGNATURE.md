# WP-01 — Security, Authorization & Signature

## Signature points in this package

| Operation | Doc | Requirement |
|---|---|---|
| `POST /signature/v1/challenges` | 04 | policy lookup (Doc 106) |
| `POST /signature/v1/challenges/{id}/verify` | 04 | policy lookup (Doc 106) |
| `POST /signature/v1/signatures/{id}/consume` | 04 | policy lookup (Doc 106) |
| `POST /vault/v1/masters/{type}/{businessId}/release` | 06 | policy lookup (Doc 106) |
| `POST /rules/v1/{ruleId}/release` | 08 | policy lookup (Doc 106) |

## Authorization
- policy decision on every regulated action (Document 07)
- qualification gate where configured
- SoD standing rules and action independence (Document 107)

## Security controls
- see `docs/generated/22_SECURITY_CONTROL_MATRIX.md` and `.claude/rules/06-security-rules.md`
- mandatory tests from `24_SECURITY_TEST_PLAN.md`
