# WP-02 — Data Model

| Entity | Doc | Owner | Authoritative store | Fields defined |
|---|---|---|---|---|
| `product_family` | 09 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 6 |
| `product_version` | 09 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 25 |
| `product_constituent` | 09 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 9 |
| `constituent_compatibility_version` | 09 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 11 |
| `product_site_admission` | 09 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 6 |
| `product_external_mapping` | 09 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 5 |
| `recipe_family` | 10 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 7 |
| `recipe_version` | 10 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 12 |
| `recipe_section` | 10 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 8 |
| `recipe_step` | 10 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 12 |
| `recipe_step_dependency` | 10 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 3 |
| `recipe_parameter` | 10 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 10 |
| `recipe_material_requirement` | 10 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 7 |
| `recipe_equipment_requirement` | 10 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 4 |
| `recipe_evidence_requirement` | 10 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 5 |
| `gxp_batch` | 11 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 18 |
| `gxp_batch_step` | 11 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 13 |
| `gxp_step_result` | 11 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 13 |
| `gxp_step_evidence_link` | 11 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 3 |
| `gxp_batch_hold` | 11 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 5 |
| `device_unit` | 12 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 13 |
| `device_component_usage` | 12 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 7 |
| `device_test_result` | 12 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 9 |
| `device_defect` | 12 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 4 |
| `device_evidence_inheritance` | 12 | services/gxp-api/src/modules/ebmr | PostgreSQL (GxP Core, authoritative) | 4 |

## Rules
- one authoritative owner per entity
- universal aggregate columns + retention class
- append-only tables reject UPDATE/DELETE at privilege level
- migrations follow Document 112 §3 and register in `36_DATABASE_MIGRATION_CATALOGUE.md`
