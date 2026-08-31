# WP-12 — Data Model

| Entity | Doc | Owner | Authoritative store | Fields defined |
|---|---|---|---|---|
| `validation_master_plan` | 79 | validation | PostgreSQL (GxP Core, authoritative) | 6 |
| `validation_deliverable_requirement` | 79 | validation | PostgreSQL (GxP Core, authoritative) | 6 |
| `validation_release_gate` | 79 | validation | PostgreSQL (GxP Core, authoritative) | 4 |
| `intended_use` | 80 | validation | PostgreSQL (GxP Core, authoritative) | 4 |
| `function_risk_assessment` | 80 | validation | PostgreSQL (GxP Core, authoritative) | 9 |
| `validation_requirement` | 81 | validation | PostgreSQL (GxP Core, authoritative) | 6 |
| `trace_link` | 81 | validation | PostgreSQL (GxP Core, authoritative) | 1 |
| `requirement_baseline` | 81 | validation | PostgreSQL (GxP Core, authoritative) | 4 |
| `validation_test_definition` | 82 | validation | PostgreSQL (GxP Core, authoritative) | 7 |
| `validation_test_execution` | 82 | validation | PostgreSQL (GxP Core, authoritative) | 6 |
| `iq_protocol` | 83 | validation | PostgreSQL (GxP Core, authoritative) | 2 |
| `iq_execution` | 83 | validation | PostgreSQL (GxP Core, authoritative) | 5 |
| `oq_suite` | 84 | validation | PostgreSQL (GxP Core, authoritative) | 4 |
| `oq_execution` | 84 | validation | PostgreSQL (GxP Core, authoritative) | 5 |
| `infrastructure_qualification_profile` | 86 | validation | PostgreSQL (GxP Core, authoritative) | 5 |
| `infrastructure_fingerprint` | 86 | validation | PostgreSQL (GxP Core, authoritative) | 4 |
| `part11_scope_assessment` | 88 | validation | PostgreSQL (GxP Core, authoritative) | 6 |
| `part11_control_evidence` | 88 | validation | PostgreSQL (GxP Core, authoritative) | 5 |
| `data_integrity_test_profile` | 89 | validation | PostgreSQL (GxP Core, authoritative) | 5 |
| `tamper_test_execution` | 89 | validation | PostgreSQL (GxP Core, authoritative) | 4 |
| `interface_validation_profile` | 90 | validation | PostgreSQL (GxP Core, authoritative) | 5 |
| `interface_test_execution` | 90 | validation | PostgreSQL (GxP Core, authoritative) | 4 |
| `dr_qualification_scenario` | 91 | validation | PostgreSQL (GxP Core, authoritative) | 6 |
| `dr_qualification_execution` | 91 | validation | PostgreSQL (GxP Core, authoritative) | 5 |
| `security_qualification_suite` | 92 | validation | PostgreSQL (GxP Core, authoritative) | 3 |
| `security_qualification_finding` | 92 | validation | PostgreSQL (GxP Core, authoritative) | 6 |
| `performance_qualification_scenario` | 93 | validation | PostgreSQL (GxP Core, authoritative) | 6 |
| `performance_run` | 93 | validation | PostgreSQL (GxP Core, authoritative) | 4 |
| `validation_exception` | 94 | validation | PostgreSQL (GxP Core, authoritative) | 9 |
| `validated_state_baseline` | 96 | validation | PostgreSQL (GxP Core, authoritative) | 1 |
| `validation_change_impact` | 96 | validation | PostgreSQL (GxP Core, authoritative) | 4 |
| `periodic_validation_review` | 96 | validation | PostgreSQL (GxP Core, authoritative) | 3 |

## Rules
- one authoritative owner per entity
- universal aggregate columns + retention class
- append-only tables reject UPDATE/DELETE at privilege level
- migrations follow Document 112 §3 and register in `36_DATABASE_MIGRATION_CATALOGUE.md`
