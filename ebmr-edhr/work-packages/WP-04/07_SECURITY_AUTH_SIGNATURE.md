# WP-04 — Security, Authorization & Signature

## Signature points in this package

| Operation | Doc | Requirement |
|---|---|---|
| `POST /supplier-qualifications/{id}/approve` | 18 | policy lookup (Doc 106) |
| `POST /materials/v1/lots/{id}/release` | 19 | policy lookup (Doc 106) |
| `POST /materials/v1/lots/{id}/reject` | 19 | policy lookup (Doc 106) |
| `POST /inventory/v1/reservations/{id}/release` | 20 | policy lookup (Doc 106) |
| `POST /dispensing/v1/orders/{id}/verify` | 21 | policy lookup (Doc 106) |
| `POST /inventory/v1/adjustments/{id}/approve` | 22 | policy lookup (Doc 106) |
| `POST /qc/v1/specifications/{id}/release` | 23 | policy lookup (Doc 106) |
| `POST /quality/oos/v1/{id}/disposition` | 25 | policy lookup (Doc 106) |
| `POST /quality/oos/v1/{id}/close` | 25 | policy lookup (Doc 106) |
| `POST /quality/oot/v1/{id}/close` | 25 | policy lookup (Doc 106) |

## Authorization
- policy decision on every regulated action (Document 07)
- qualification gate where configured
- SoD standing rules and action independence (Document 107)

## Security controls
- see `docs/generated/22_SECURITY_CONTROL_MATRIX.md` and `.claude/rules/06-security-rules.md`
- mandatory tests from `24_SECURITY_TEST_PLAN.md`
