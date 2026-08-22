# WP-09 — Security, Authorization & Signature

## Signature points in this package

| Operation | Doc | Requirement |
|---|---|---|
| `POST /postmarket/v1/signals` | 58 | policy lookup (Doc 106) |
| `POST /postmarket/v1/signals/{id}/assessments` | 58 | policy lookup (Doc 106) |
| `POST /postmarket/v1/signals/{id}/escalations` | 58 | policy lookup (Doc 106) |
| `POST /regulatory/v1/reports/{id}/approve` | 59 | policy lookup (Doc 106) |

## Authorization
- policy decision on every regulated action (Document 07)
- qualification gate where configured
- SoD standing rules and action independence (Document 107)

## Security controls
- see `docs/generated/22_SECURITY_CONTROL_MATRIX.md` and `.claude/rules/06-security-rules.md`
- mandatory tests from `24_SECURITY_TEST_PLAN.md`
