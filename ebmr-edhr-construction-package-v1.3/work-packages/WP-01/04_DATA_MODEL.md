# WP-01 — Data Model

| Entity | Doc | Owner | Authoritative store | Fields defined |
|---|---|---|---|---|
| `CommandReceipt` | 03 | services/gxp-api/src/modules/mutation | PostgreSQL (GxP Core, authoritative) | 12 |
| `IdempotencyRecord` | 03 | services/gxp-api/src/modules/mutation | PostgreSQL (GxP Core, authoritative) | 7 |
| `OutboxEvent` | 03 | services/gxp-api/src/modules/mutation | PostgreSQL (GxP Core, authoritative) | 8 |
| `gxp_command_receipt` | 03 | services/gxp-api/src/modules/mutation | PostgreSQL (GxP Core, authoritative) | 23 |
| `gxp_outbox` | 03 | services/gxp-api/src/modules/mutation | PostgreSQL (GxP Core, authoritative) | 18 |
| `gxp_signature_challenge` | 04 | services/gxp-api/src/modules/signature | PostgreSQL (GxP Core, authoritative) | 19 |
| `gxp_signature` | 04 | services/gxp-api/src/modules/signature | PostgreSQL (GxP Core, authoritative) | 21 |
| `vault_object` | 06 | services/gxp-api/src/modules/vault | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `vault_evidence_manifest` | 06 | services/gxp-api/src/modules/vault | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `gxp_vault_object` | 06 | services/gxp-api/src/modules/vault | PostgreSQL (GxP Core, authoritative) | 19 |
| `gxp_vault_evidence` | 06 | services/gxp-api/src/modules/vault | PostgreSQL (GxP Core, authoritative) | 7 |
| `gxp_record_correction` | 06 | services/gxp-api/src/modules/vault | PostgreSQL (GxP Core, authoritative) | 12 |
| `iam_subject` | 07 | services/gxp-api/src/modules/policy | PostgreSQL (GxP Core, authoritative) | 12 |
| `iam_role_assignment` | 07 | services/gxp-api/src/modules/policy | PostgreSQL (GxP Core, authoritative) | 10 |
| `iam_qualification` | 07 | services/gxp-api/src/modules/policy | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `iam_temporary_authorization` | 07 | services/gxp-api/src/modules/policy | PostgreSQL (GxP Core, authoritative) | 3 |
| `gxp_rule_definition` | 08 | services/gxp-api/src/modules/rules | PostgreSQL (GxP Core, authoritative) | 19 |
| `gxp_rule_evaluation` | 08 | services/gxp-api/src/modules/rules | PostgreSQL (GxP Core, authoritative) | 13 |

## Rules
- one authoritative owner per entity
- universal aggregate columns + retention class
- append-only tables reject UPDATE/DELETE at privilege level
- migrations follow Document 112 §3 and register in `36_DATABASE_MIGRATION_CATALOGUE.md`
