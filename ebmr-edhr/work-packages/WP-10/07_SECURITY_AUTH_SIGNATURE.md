# WP-10 — Security, Authorization & Signature

## Signature points in this package

| Operation | Doc | Requirement |
|---|---|---|
| `POST /security/v1/privileged-access/requests/{id}/approve` | 63 | policy lookup (Doc 106) |
| `POST /security/v1/privileged-sessions/{id}/close` | 63 | policy lookup (Doc 106) |
| `POST /security/v1/incidents/{id}/close` | 67 | policy lookup (Doc 106) |

## Authorization
- policy decision on every regulated action (Document 07)
- qualification gate where configured
- SoD standing rules and action independence (Document 107)

## Security controls
- see `docs/generated/22_SECURITY_CONTROL_MATRIX.md` and `.claude/rules/06-security-rules.md`
- mandatory tests from `24_SECURITY_TEST_PLAN.md`
