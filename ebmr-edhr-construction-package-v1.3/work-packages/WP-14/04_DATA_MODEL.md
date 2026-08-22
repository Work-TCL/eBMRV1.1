# WP-14 — Data Model

| Entity | Doc | Owner | Authoritative store | Fields defined |
|---|---|---|---|---|
| `pq_scenario` | 85 | validation | PostgreSQL (GxP Core, authoritative) | 6 |
| `pq_execution` | 85 | validation | PostgreSQL (GxP Core, authoritative) | 3 |
| `migration_validation_plan` | 87 | validation | PostgreSQL (GxP Core, authoritative) | 7 |
| `migration_run` | 87 | validation | PostgreSQL (GxP Core, authoritative) | 5 |
| `migration_reconciliation` | 87 | validation | PostgreSQL (GxP Core, authoritative) | 1 |
| `validation_summary_report` | 95 | validation | PostgreSQL (GxP Core, authoritative) | 7 |
| `validated_release_authorization` | 95 | validation | PostgreSQL (GxP Core, authoritative) | 6 |

## Rules
- one authoritative owner per entity
- universal aggregate columns + retention class
- append-only tables reject UPDATE/DELETE at privilege level
- migrations follow Document 112 §3 and register in `36_DATABASE_MIGRATION_CATALOGUE.md`
