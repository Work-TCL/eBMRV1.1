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
