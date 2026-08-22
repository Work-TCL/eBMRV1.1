# WP-08 — Data Model

| Entity | Doc | Owner | Authoritative store | Fields defined |
|---|---|---|---|---|
| `ddcp_profile_version` | 54 | services/gxp-api/src/modules/ddcp | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `constituent_requirement` | 54 | services/gxp-api/src/modules/ddcp | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `constituent_handoff` | 54 | services/gxp-api/src/modules/ddcp | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `fill_operation` | 54 | services/gxp-api/src/modules/ddcp | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `production_count_ledger` | 54 | services/gxp-api/src/modules/ddcp | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `device_assembly_record` | 54 | services/gxp-api/src/modules/ddcp | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `device_functional_test_link` | 54 | services/gxp-api/src/modules/ddcp | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `ddcp_release_checkpoint` | 54 | services/gxp-api/src/modules/ddcp | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `batch_evidence_manifest` | 54 | services/gxp-api/src/modules/ddcp | PostgreSQL (GxP Core, authoritative) | Document 112 |

## Rules
- one authoritative owner per entity
- universal aggregate columns + retention class
- append-only tables reject UPDATE/DELETE at privilege level
- migrations follow Document 112 §3 and register in `36_DATABASE_MIGRATION_CATALOGUE.md`
