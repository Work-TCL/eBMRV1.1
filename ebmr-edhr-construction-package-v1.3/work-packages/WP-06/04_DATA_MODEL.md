# WP-06 — Data Model

| Entity | Doc | Owner | Authoritative store | Fields defined |
|---|---|---|---|---|
| `equipment_asset` | 38 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 16 |
| `equipment_calibration` | 38 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 8 |
| `maintenance_work_order` | 38 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 6 |
| `equipment_use_log` | 38 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 6 |
| `cleaning_procedure_version` | 39 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 9 |
| `cleaning_execution` | 39 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 11 |
| `line_clearance` | 39 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 7 |
| `aseptic_profile_version` | 40 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 7 |
| `aseptic_operation` | 40 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 9 |
| `aseptic_intervention` | 40 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 9 |
| `aseptic_event_timeline` | 40 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 5 |
| `em_program_version` | 41 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 9 |
| `em_location` | 41 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 5 |
| `em_sample_or_reading` | 41 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 11 |
| `em_excursion` | 41 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 4 |
| `process_cycle_profile_version` | 42 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 9 |
| `process_cycle` | 42 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 14 |
| `sterilization_load_item` | 42 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 4 |
| `sterile_filter_use` | 42 | services/gxp-api/src/modules/equipment | PostgreSQL (GxP Core, authoritative) | 6 |

## Rules
- one authoritative owner per entity
- universal aggregate columns + retention class
- append-only tables reject UPDATE/DELETE at privilege level
- migrations follow Document 112 §3 and register in `36_DATABASE_MIGRATION_CATALOGUE.md`
