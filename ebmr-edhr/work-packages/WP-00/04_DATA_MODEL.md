# WP-00 — Data Model

| Entity | Doc | Owner | Authoritative store | Fields defined |
|---|---|---|---|---|
| `Purpose` | 02 | docs/architecture | n/a (standard / governance document) | 7 |
| `Modules` | 02 | docs/architecture | n/a (standard / governance document) | 11 |
| `Storage` | 02 | docs/architecture | n/a (standard / governance document) | 3 |
| `Store` | 02 | docs/architecture | n/a (standard / governance document) | 5 |
| `Controls` | 02 | docs/architecture | n/a (standard / governance document) | 5 |
| `Inputs` | 02 | docs/architecture | n/a (standard / governance document) | 14 |
| `Outputs` | 02 | docs/architecture | n/a (standard / governance document) | 7 |
| `Rules` | 02 | docs/architecture | n/a (standard / governance document) | 6 |
| `Authentication` | 02 | docs/architecture | n/a (standard / governance document) | 6 |
| `Authorization` | 02 | docs/architecture | n/a (standard / governance document) | 6 |
| `Network` | 02 | docs/architecture | n/a (standard / governance document) | 6 |
| `Secrets` | 02 | docs/architecture | n/a (standard / governance document) | 5 |
| `Encryption` | 02 | docs/architecture | n/a (standard / governance document) | 6 |
| `Signals` | 02 | docs/architecture | n/a (standard / governance document) | 12 |
| `Accessibility` | 02 | docs/architecture | n/a (standard / governance document) | 5 |
| `Output` | 02 | docs/architecture | n/a (standard / governance document) | 8 |

## Rules
- one authoritative owner per entity
- universal aggregate columns + retention class
- append-only tables reject UPDATE/DELETE at privilege level
- migrations follow Document 112 §3 and register in `36_DATABASE_MIGRATION_CATALOGUE.md`
