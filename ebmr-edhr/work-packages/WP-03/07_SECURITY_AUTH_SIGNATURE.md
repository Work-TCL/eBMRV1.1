# WP-03 — Security, Authorization & Signature

## Signature points in this package

| Operation | Doc | Requirement |
|---|---|---|
| `POST /qa-review/v1/items/{id}/disposition` | 14 | policy lookup (Doc 106) |
| `POST /release/v1/scopes/{type}/{id}/evaluate` | 15 | policy lookup (Doc 106) |
| `POST /release/v1/scopes/{id}/release` | 15 | policy lookup (Doc 106) |
| `POST /release/v1/scopes/{id}/hold` | 15 | policy lookup (Doc 106) |
| `POST /release/v1/scopes/{id}/reject` | 15 | policy lookup (Doc 106) |
| `POST /release/v1/scopes/{id}/rework` | 15 | policy lookup (Doc 106) |
| `POST /release/v1/scopes/{id}/reprocess` | 15 | policy lookup (Doc 106) |
| `POST /release/v1/scopes/{id}/destroy` | 15 | policy lookup (Doc 106) |
| `POST /reconciliation/v1/{id}/verify` | 17 | policy lookup (Doc 106) |

## Authorization
- policy decision on every regulated action (Document 07)
- qualification gate where configured
- SoD standing rules and action independence (Document 107)

## Security controls
- see `docs/generated/22_SECURITY_CONTROL_MATRIX.md` and `.claude/rules/06-security-rules.md`
- mandatory tests from `24_SECURITY_TEST_PLAN.md`
