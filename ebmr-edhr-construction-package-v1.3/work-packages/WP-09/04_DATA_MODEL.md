# WP-09 — Data Model

| Entity | Doc | Owner | Authoritative store | Fields defined |
|---|---|---|---|---|
| `postmarket_source` | 58 | services/gxp-api/src/modules/postmarket | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `safety_case` | 58 | services/gxp-api/src/modules/postmarket | PostgreSQL (GxP Core, authoritative) | 13 |
| `safety_case_followup` | 58 | services/gxp-api/src/modules/postmarket | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `safety_signal` | 58 | services/gxp-api/src/modules/postmarket | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `reportability_track` | 59 | services/gxp-api/src/modules/postmarket | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `regulatory_report` | 59 | services/gxp-api/src/modules/postmarket | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `regulatory_submission_attempt` | 59 | services/gxp-api/src/modules/postmarket | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `regulatory_submission_ack` | 59 | services/gxp-api/src/modules/postmarket | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `regulatory_obligation` | 60 | services/gxp-api/src/modules/postmarket | PostgreSQL (GxP Core, authoritative) | 12 |
| `applicant_relationship` | 60 | services/gxp-api/src/modules/postmarket | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `constituent_information_share` | 60 | services/gxp-api/src/modules/postmarket | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `correction_removal_regulatory_record` | 60 | services/gxp-api/src/modules/postmarket | PostgreSQL (GxP Core, authoritative) | Document 112 |
| `periodic_reporting_cycle` | 60 | services/gxp-api/src/modules/postmarket | PostgreSQL (GxP Core, authoritative) | Document 112 |

## Rules
- one authoritative owner per entity
- universal aggregate columns + retention class
- append-only tables reject UPDATE/DELETE at privilege level
- migrations follow Document 112 §3 and register in `36_DATABASE_MIGRATION_CATALOGUE.md`
