# WP-05 — Data Model

| Entity | Doc | Owner | Authoritative store | Fields defined |
|---|---|---|---|---|
| `deviation_record` | 26 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 19 |
| `deviation_impact_link` | 26 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 3 |
| `capa_record` | 27 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 11 |
| `capa_action` | 27 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 6 |
| `capa_effectiveness_check` | 27 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 5 |
| `nonconformance_record` | 28 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 10 |
| `ncr_disposition` | 28 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 6 |
| `change_control` | 29 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 14 |
| `change_affected_object` | 29 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 3 |
| `change_task` | 29 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 4 |
| `controlled_document` | 30 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 8 |
| `controlled_document_version` | 30 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 11 |
| `controlled_copy` | 30 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 4 |
| `training_requirement` | 31 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 5 |
| `training_assignment` | 31 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 10 |
| `qualification_record` | 31 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 6 |
| `supplier_quality_case` | 32 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 6 |
| `scar_record` | 32 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 7 |
| `risk_record` | 33 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 11 |
| `risk_assessment_version` | 33 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 6 |
| `internal_audit` | 34 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 13 |
| `audit_finding` | 34 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 8 |
| `complaint_record` | 35 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 15 |
| `complaint_reportability_assessment` | 35 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 5 |
| `complaint_communication` | 35 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 4 |
| `field_action` | 36 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 10 |
| `field_action_scope_item` | 36 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 3 |
| `field_action_communication` | 36 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 3 |
| `field_action_reconciliation` | 36 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 1 |
| `quality_metric_definition` | 37 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 12 |
| `quality_metric_snapshot` | 37 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 10 |
| `effectiveness_check` | 37 | services/gxp-api/src/modules/qms | PostgreSQL (GxP Core, authoritative) | 7 |

## Rules
- one authoritative owner per entity
- universal aggregate columns + retention class
- append-only tables reject UPDATE/DELETE at privilege level
- migrations follow Document 112 §3 and register in `36_DATABASE_MIGRATION_CATALOGUE.md`
