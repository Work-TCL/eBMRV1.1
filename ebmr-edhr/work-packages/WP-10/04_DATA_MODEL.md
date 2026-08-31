# WP-10 — Data Model

| Entity | Doc | Owner | Authoritative store | Fields defined |
|---|---|---|---|---|
| `security_threat_model_version` | 61 | platform/security | PostgreSQL (GxP Core, authoritative) | 7 |
| `security_threat` | 61 | platform/security | PostgreSQL (GxP Core, authoritative) | 6 |
| `security_control` | 61 | platform/security | PostgreSQL (GxP Core, authoritative) | 6 |
| `security_exception` | 61 | platform/security | PostgreSQL (GxP Core, authoritative) | 6 |
| `identity_provider_config` | 62 | platform/security | PostgreSQL (GxP Core, authoritative) | 6 |
| `application_session` | 62 | platform/security | PostgreSQL (GxP Core, authoritative) | 8 |
| `service_identity` | 62 | platform/security | PostgreSQL (GxP Core, authoritative) | 6 |
| `privileged_access_request` | 63 | platform/security | PostgreSQL (GxP Core, authoritative) | 9 |
| `privileged_grant` | 63 | platform/security | PostgreSQL (GxP Core, authoritative) | 5 |
| `privileged_session` | 63 | platform/security | PostgreSQL (GxP Core, authoritative) | 6 |
| `api_security_policy` | 64 | platform/security | PostgreSQL (GxP Core, authoritative) | 6 |
| `outbound_destination` | 64 | platform/security | PostgreSQL (GxP Core, authoritative) | 5 |
| `webhook_profile` | 64 | platform/security | PostgreSQL (GxP Core, authoritative) | 5 |
| `secret_metadata` | 65 | platform/security | PostgreSQL (GxP Core, authoritative) | 8 |
| `certificate_metadata` | 65 | platform/security | PostgreSQL (GxP Core, authoritative) | 8 |
| `crypto_profile` | 65 | platform/security | PostgreSQL (GxP Core, authoritative) | 5 |
| `network_flow_definition` | 66 | platform/security | PostgreSQL (GxP Core, authoritative) | 8 |
| `deployment_security_profile` | 66 | platform/security | PostgreSQL (GxP Core, authoritative) | 7 |
| `security_incident` | 67 | platform/security | PostgreSQL (GxP Core, authoritative) | 9 |
| `forensic_evidence` | 67 | platform/security | PostgreSQL (GxP Core, authoritative) | 4 |
| `software_component_inventory` | 68 | platform/security | PostgreSQL (GxP Core, authoritative) | 5 |
| `vulnerability_record` | 68 | platform/security | PostgreSQL (GxP Core, authoritative) | 11 |
| `release_security_evidence` | 68 | platform/security | PostgreSQL (GxP Core, authoritative) | 7 |

## Rules
- one authoritative owner per entity
- universal aggregate columns + retention class
- append-only tables reject UPDATE/DELETE at privilege level
- migrations follow Document 112 §3 and register in `36_DATABASE_MIGRATION_CATALOGUE.md`
