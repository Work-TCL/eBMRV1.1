# WP-11 — Data Model

| Entity | Doc | Owner | Authoritative store | Fields defined |
|---|---|---|---|---|
| `data_ownership_registry` | 69 | infrastructure | PostgreSQL (GxP Core, authoritative) | 9 |
| `projection_checkpoint` | 69 | infrastructure | PostgreSQL (GxP Core, authoritative) | 5 |
| `migration_batch` | 69 | infrastructure | PostgreSQL (GxP Core, authoritative) | 6 |
| `evidence_object` | 72 | infrastructure | Object store (WORM evidence) + PostgreSQL metadata | 16 |
| `evidence_manifest` | 72 | infrastructure | Object store (WORM evidence) + PostgreSQL metadata | 5 |
| `gxp_outbox` | 73 | infrastructure | PostgreSQL transactional outbox (authoritative) / NATS JetStream (transport) | 11 |
| `consumer_inbox` | 73 | infrastructure | PostgreSQL transactional outbox (authoritative) / NATS JetStream (transport) | 5 |
| `projection_document_metadata` | 75 | infrastructure | Redis / search / read models (rebuildable, NON-AUTHORITATIVE) | 4 |
| `read_model_checkpoint` | 75 | infrastructure | Redis / search / read models (rebuildable, NON-AUTHORITATIVE) | 4 |
| `recovery_objective_profile` | 76 | infrastructure | PostgreSQL (GxP Core, authoritative) | 4 |
| `backup_inventory` | 76 | infrastructure | PostgreSQL (GxP Core, authoritative) | 8 |
| `restore_test` | 76 | infrastructure | PostgreSQL (GxP Core, authoritative) | 5 |
| `deployment_profile` | 77 | infrastructure | PostgreSQL (GxP Core, authoritative) | 8 |
| `slo_definition` | 78 | infrastructure | PostgreSQL (GxP Core, authoritative) | 5 |
| `capacity_forecast` | 78 | infrastructure | PostgreSQL (GxP Core, authoritative) | 7 |

## Rules
- one authoritative owner per entity
- universal aggregate columns + retention class
- append-only tables reject UPDATE/DELETE at privilege level
- migrations follow Document 112 §3 and register in `36_DATABASE_MIGRATION_CATALOGUE.md`
