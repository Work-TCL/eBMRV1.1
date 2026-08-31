# WP-12 — Security, Authorization & Signature

## Signature points in this package

| Operation | Doc | Requirement |
|---|---|---|
| `POST /validation/v1/master-plans/{id}/release` | 79 | policy lookup (Doc 106) |
| `POST /validation/v1/function-risks/{id}/approve` | 80 | policy lookup (Doc 106) |
| `POST /validation/v1/tests/{id}/approve` | 82 | policy lookup (Doc 106) |
| `POST /validation/v1/iq/executions/{id}/approve` | 83 | policy lookup (Doc 106) |
| `POST /validation/v1/oq/{id}/approve` | 84 | policy lookup (Doc 106) |
| `POST /validation/v1/infrastructure/{id}/approve` | 86 | policy lookup (Doc 106) |
| `POST /validation/v1/part11/{id}/approve` | 88 | policy lookup (Doc 106) |
| `POST /validation/v1/data-integrity/{id}/approve` | 89 | policy lookup (Doc 106) |
| `POST /validation/v1/interfaces/{id}/approve` | 90 | policy lookup (Doc 106) |
| `POST /validation/v1/dr/{id}/approve` | 91 | policy lookup (Doc 106) |
| `POST /validation/v1/security/{id}/approve` | 92 | policy lookup (Doc 106) |
| `POST /validation/v1/exceptions/{id}/disposition` | 94 | policy lookup (Doc 106) |

## Authorization
- policy decision on every regulated action (Document 07)
- qualification gate where configured
- SoD standing rules and action independence (Document 107)

## Security controls
- see `docs/generated/22_SECURITY_CONTROL_MATRIX.md` and `.claude/rules/06-security-rules.md`
- mandatory tests from `24_SECURITY_TEST_PLAN.md`
