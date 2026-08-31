# WP-03 — Data Model

| Entity | Doc | Owner | Authoritative store | Fields defined |
|---|---|---|---|---|
| `genealogy_node` | 13 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 10 |
| `genealogy_edge` | 13 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 12 |
| `qa_review_package` | 14 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 12 |
| `qa_review_item` | 14 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 10 |
| `qa_review_comment` | 14 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 5 |
| `release_scope` | 15 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 13 |
| `release_evaluation` | 15 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 7 |
| `release_decision` | 15 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 7 |
| `packaging_run` | 16 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 6 |
| `label_issue` | 16 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 10 |
| `label_reconciliation` | 16 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 10 |
| `package_node` | 16 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 4 |
| `manufacturing_calculation` | 17 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 16 |
| `reconciliation_record` | 17 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 9 |

## Rules
- one authoritative owner per entity
- universal aggregate columns + retention class
- append-only tables reject UPDATE/DELETE at privilege level
- migrations follow Document 112 §3 and register in `36_DATABASE_MIGRATION_CATALOGUE.md`
