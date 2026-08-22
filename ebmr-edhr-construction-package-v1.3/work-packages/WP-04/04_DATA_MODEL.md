# WP-04 — Data Model

| Entity | Doc | Owner | Authoritative store | Fields defined |
|---|---|---|---|---|
| `supplier` | 18 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 9 |
| `supplier_site` | 18 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 5 |
| `supplier_qualification` | 18 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 10 |
| `approved_supplier_material` | 18 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 8 |
| `purchase_requisition` | 18 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 5 |
| `purchase_order_ref` | 18 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 6 |
| `material_receipt` | 19 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 12 |
| `material_lot` | 19 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 13 |
| `material_container` | 19 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 7 |
| `sampling_order` | 19 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 6 |
| `material_quality_disposition` | 19 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 6 |
| `warehouse_location` | 20 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 8 |
| `inventory_transaction` | 20 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 16 |
| `inventory_balance_projection` | 20 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 6 |
| `inventory_reservation` | 20 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 7 |
| `dispensing_order` | 21 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 11 |
| `dispensing_source` | 21 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 6 |
| `weighing_session` | 21 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 10 |
| `dispensed_container` | 21 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 7 |
| `material_consumption` | 22 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 11 |
| `material_return` | 22 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 7 |
| `inventory_adjustment_request` | 22 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 8 |
| `destruction_record` | 22 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 9 |
| `material_reconciliation` | 22 | services/gxp-api/src/modules/materials | PostgreSQL (GxP Core, authoritative) | 7 |
| `qc_test_specification` | 23 | services/gxp-api/src/modules/qc | PostgreSQL (GxP Core, authoritative) | 10 |
| `qc_test_definition` | 23 | services/gxp-api/src/modules/qc | PostgreSQL (GxP Core, authoritative) | 7 |
| `qc_sample` | 23 | services/gxp-api/src/modules/qc | PostgreSQL (GxP Core, authoritative) | 15 |
| `qc_test_order` | 23 | services/gxp-api/src/modules/qc | PostgreSQL (GxP Core, authoritative) | 6 |
| `qc_test_run` | 23 | services/gxp-api/src/modules/qc | PostgreSQL (GxP Core, authoritative) | 8 |
| `qc_result` | 23 | services/gxp-api/src/modules/qc | PostgreSQL (GxP Core, authoritative) | 15 |
| `oos_record` | 25 | services/gxp-api/src/modules/qc | PostgreSQL (GxP Core, authoritative) | 17 |
| `oos_investigation_activity` | 25 | services/gxp-api/src/modules/qc | PostgreSQL (GxP Core, authoritative) | 7 |
| `oos_retest_plan` | 25 | services/gxp-api/src/modules/qc | PostgreSQL (GxP Core, authoritative) | 7 |
| `oos_resample_plan` | 25 | services/gxp-api/src/modules/qc | PostgreSQL (GxP Core, authoritative) | 5 |
| `oot_record` | 25 | services/gxp-api/src/modules/qc | PostgreSQL (GxP Core, authoritative) | 7 |

## Rules
- one authoritative owner per entity
- universal aggregate columns + retention class
- append-only tables reject UPDATE/DELETE at privilege level
- migrations follow Document 112 §3 and register in `36_DATABASE_MIGRATION_CATALOGUE.md`
