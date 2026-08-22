# WP-05 — Security, Authorization & Signature

## Signature points in this package

| Operation | Doc | Requirement |
|---|---|---|
| `POST /qms/v1/deviations/{id}/disposition` | 26 | policy lookup (Doc 106) |
| `POST /qms/v1/deviations/{id}/close` | 26 | policy lookup (Doc 106) |
| `POST /qms/v1/capas/{id}/close` | 27 | policy lookup (Doc 106) |
| `POST /qms/v1/nonconformances/{id}/disposition` | 28 | policy lookup (Doc 106) |
| `POST /qms/v1/nonconformances/{id}/verify` | 28 | policy lookup (Doc 106) |
| `POST /qms/v1/nonconformances/{id}/close` | 28 | policy lookup (Doc 106) |
| `POST /qms/v1/changes/{id}/approve` | 29 | policy lookup (Doc 106) |
| `POST /qms/v1/changes/{id}/verify` | 29 | policy lookup (Doc 106) |
| `POST /qms/v1/changes/{id}/close` | 29 | policy lookup (Doc 106) |
| `POST /documents/v1/drafts/{id}/release` | 30 | policy lookup (Doc 106) |
| `POST /training/v1/assignments` | 31 | policy lookup (Doc 106) |
| `POST /training/v1/assignments/{id}/complete` | 31 | policy lookup (Doc 106) |
| `POST /training/v1/assignments/{id}/assess` | 31 | policy lookup (Doc 106) |
| `POST /qms/v1/scars/{id}/close` | 32 | policy lookup (Doc 106) |
| `POST /qms/v1/findings/{id}/verify` | 34 | policy lookup (Doc 106) |
| `POST /qms/v1/audits/{id}/close` | 34 | policy lookup (Doc 106) |
| `POST /qms/v1/complaints/{id}/close` | 35 | policy lookup (Doc 106) |
| `POST /qms/v1/field-actions/{id}/approve` | 36 | policy lookup (Doc 106) |
| `POST /qms/v1/field-actions/{id}/close` | 36 | policy lookup (Doc 106) |
| `POST /quality-metrics/v1/definitions/{id}/release` | 37 | policy lookup (Doc 106) |

## Authorization
- policy decision on every regulated action (Document 07)
- qualification gate where configured
- SoD standing rules and action independence (Document 107)

## Security controls
- see `docs/generated/22_SECURITY_CONTROL_MATRIX.md` and `.claude/rules/06-security-rules.md`
- mandatory tests from `24_SECURITY_TEST_PLAN.md`
