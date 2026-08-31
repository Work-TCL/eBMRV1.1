# WP-02 — Security, Authorization & Signature

## Signature points in this package

| Operation | Doc | Requirement |
|---|---|---|
| `POST /products/v1/drafts/{id}/release` | 09 | policy lookup (Doc 106) |
| `POST /recipes/v1/drafts/{id}/release` | 10 | policy lookup (Doc 106) |
| `POST /batches/{id}/steps/{stepId}/verify` | 11 | policy lookup (Doc 106) |

## Authorization
- policy decision on every regulated action (Document 07)
- qualification gate where configured
- SoD standing rules and action independence (Document 107)

## Security controls
- see `docs/generated/22_SECURITY_CONTROL_MATRIX.md` and `.claude/rules/06-security-rules.md`
- mandatory tests from `24_SECURITY_TEST_PLAN.md`
