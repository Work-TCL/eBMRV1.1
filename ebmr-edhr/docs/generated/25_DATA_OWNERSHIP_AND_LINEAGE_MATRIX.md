# 25 — Data Ownership & Lineage Matrix

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Authoritative source → derived copy lineage, refresh mechanism and permitted use (Doc 69).

---

| Authoritative source | Derived artefact | Mechanism | Refresh / rebuild | Permitted use | Prohibited use |
|---|---|---|---|---|---|
| PostgreSQL GxP aggregate | Frappe projection DocType | outbox → NATS → projection updater | replay from outbox / full rebuild in maintenance mode (MDB-FR-015) | display, navigation, filtering | signing, release, disposition, any regulated decision |
| PostgreSQL GxP aggregate | Search index / read model | event consumer (Doc 75) | full rebuild from authoritative store | search, dashboards, trending | regulated calculation or acceptance decision |
| PostgreSQL audit stream | Audit review UI / export | read-only query (Doc 05) | n/a — immutable | review by exception, inspection export | edit, delete, re-order |
| Record Version Vault | Human-readable PDF/export | render from immutable version (Doc 06/72) | regenerate deterministically | inspection, customer distribution | editing a rendered record back into state |
| PostgreSQL outbox | NATS JetStream message | publisher after commit (Doc 73) | re-publish by event_id (dedupe) | integration, projections | treating bus delivery as commit evidence |
| GxP receipt/consumption | ERP goods movement | integration command (Doc 48/49/50/51) | reconciliation ledger + exception report | commercial posting | ERP status → QA release mapping |
| Edge buffered sample | GxP evidence record | integration command acceptance (Doc 45) | replay of buffered range with dedupe | process evidence after acceptance | authoritative before acceptance |
| LIMS result | GxP QC result record | adapter + GxP acceptance command (Doc 24) | re-fetch and re-accept by external result id | release decision input after acceptance | auto-release without GxP acceptance |

## Lineage stamping requirement

Every derived record carries `authoritative_source_id`, `authoritative_source_version`, `projected_at_utc` and `projection_status` (Doc 71 MDB-FR-003). A derived record without these fields is an architecture violation and must fail CI (guardrail AG-04).

---

## Implemented registry (`dataops.data_ownership_registry`) — WP-11 Document 69

The conceptual matrix above is now backed by a queryable PostgreSQL registry
(`services/gxp-api/app/modules/dataops/`), seeded from `05_DATABASE_OWNERSHIP_MATRIX.md`
(`scripts/seed.py` `DATA_OWNERSHIP_SEED` / `tests/conftest.py`). The live machine-readable form is
`GET /platform/v1/data-dictionary` (DATA-FR-027); ownership of a single entity is
`GET /platform/v1/data-ownership/{entityType}` (DATA-FR-001, fail-closed with `DATA_OWNER_UNKNOWN`).

### Storage tiers represented in the seeded baseline

| `authoritative_store` | Meaning | Example seeded entities |
|---|---|---|
| `POSTGRES` | GxP Core authoritative regulated state | `gxp_batch`, `audit_event`, `signature`, `vault_object`, `material_lot`, `qc_result`, `deviation_record`, `capa_record`, `release_decision`, `genealogy_node`, `security_incident`, … |
| `OBJECT` | WORM object storage (evidence); PostgreSQL holds metadata/hash (DATA-FR-009 / Doc 72) | `evidence_object` |
| `HISTORIAN` | High-frequency time-series / Edge storage; GxP holds intended-use evidence refs (DATA-FR-010) | `edge_observation` |
| `MARIADB` | Frappe UI/application metadata, DocTypes, non-authoritative workflow conveniences (DATA-FR-003) | `frappe_ui_configuration` |
| `EXTERNAL` | Authority stays in an integrated system (ERP/LIMS/IdP/SCADA); internal IDs are references (DATA-FR-015) | (external record referenced by `erp_external_mapping`, which is itself `POSTGRES`-owned) |

### Rules enforced by the module

- **No dual master (AG-05 / DATA-FR-001).** `data_ownership_registry` has a unique key on `entity_type`; `lint_ownership_seed()` (DATA-FR-030) rejects a duplicate or an invalid store/tier at CI time; `assert_authoritative_write_allowed()` (DATA-FR-025) raises `FORBIDDEN_DATA_OWNER_WRITE` for any non-owning service.
- **Projections are rebuildable and non-authoritative (DATA-FR-004/007/008/011/012).** `projection_checkpoint` records the cursor; `get_projection_freshness()` compares it to the authoritative audit-ledger version and reports `stale` / `degraded`; `POST /platform/v1/projections/{type}:rebuild` advances it through the Mutation Gateway (version++ + audit + `ProjectionRebuilt` + `ProjectionUpdateRequested` outbox). No signature (Document 106 # 10).
- **Migration provenance (DATA-FR-024).** `migration_batch` stores source system/artifact/hash, transform version and row-count/hash reconciliation; a count mismatch stays `PENDING`, never silently `RECONCILED`.
- **Retention (DATA-FR-022).** `retention_policy_id` is a *reference* to a Document 108 retention policy — numeric retention periods remain the open gap **SG-005**; this module never invents a duration.
- **No hard delete (DATA-FR-023).** The runtime app role holds `SELECT/INSERT/UPDATE/TRUNCATE` but **not `DELETE`** on the `dataops.*` tables — a generic delete is refused at the PostgreSQL privilege level.

### Known limitation

The seeded baseline is a representative, change-controlled set (~42 entities) covering every storage
tier and every bounded context, not yet an exhaustive transcription of all ~275
`05_DATABASE_OWNERSHIP_MATRIX.md` rows. Completing it is data entry against that same matrix through
`DATA_OWNERSHIP_SEED` / `registerDataClass()`, not a regulated-behaviour decision.
