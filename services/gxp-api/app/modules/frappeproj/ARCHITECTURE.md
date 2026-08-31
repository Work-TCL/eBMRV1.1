# `frappeproj` — Frappe / MariaDB Operational Database & Projection Architecture (Document 71 / SPEC-DATA-003)

Document 71 declares **0 owned entities, 1 read-only API, 4 events, no signatures**. Its substantive
requirements are DocType-level enforcement inside `apps/ebmr_frappe` — which does not exist yet.
`ADR-0008-frappe-role-and-ui-layer.md` (Accepted, 2026-08-22) already resolved the framework question
(the operator UI of record is Frappe, not the pre-existing `frontend/` Next.js deviation) and recorded
that `apps/ebmr_frappe` is scaffolded module-by-module starting with WP-01 Document 04, not in bulk —
so no SPEC_GAP is raised here either; this is a scope/sequencing fact, not a missing decision.

| MDB-FR | Requirement | Status / where enforced |
|---|---|---|
| MDB-FR-001 | Frappe DB boundary | Structural: `services/gxp-api` never connects to MariaDB (see boundary test below); MariaDB's actual contents are entirely Frappe's own concern, unscaffolded. |
| MDB-FR-002 | No GxP authority | AG-03/AG-04: PostgreSQL is authoritative for every regulated entity built so far; no regulated table exists in MariaDB because MariaDB isn't reachable from any regulated write path. |
| MDB-FR-003 | Projection DocTypes carry source id/version/projected_at/status | `contract.py::PROJECTION_BASELINE_FIELDS` / `build_projection_envelope()` — the shared shape; **not yet applied to a live DocType** (none exist). |
| MDB-FR-004 | Projection update via events/API worker, not manual edit | No projection worker exists yet (nothing to update). When built, it consumes the outbox (Document 73) the same way `dataops`/`readmodels` checkpoints already do. |
| MDB-FR-005 | Projection immutability in Frappe forms/hooks | Frappe-side (`apps/ebmr_frappe` server hooks) — not yet scaffolded. |
| MDB-FR-006 | Frappe configuration classification | Policy statement; applies once Frappe config DocTypes exist. |
| MDB-FR-007 | User identity mapping is projection, not authority | Already true by construction: `app/core/security.py::get_current_actor` resolves identity from the GxP-issued JWT, never from a Frappe session. |
| MDB-FR-008 | Frappe workflow is UX only | Applies once Frappe workflow exists; the GxP state machine (`app/mutation/*`, every module's `commands.py`) is already the sole authoritative state machine. |
| MDB-FR-009 | Evidence bytes routed to Evidence Store, Frappe stores a reference | Document 72 (`evidence`) already stores bytes in the object store + PostgreSQL metadata only; a future Frappe attachment field stores the `evidence_id` reference, never the bytes. |
| MDB-FR-010 | Frappe background jobs call GxP APIs, no direct PostgreSQL | Structural, same boundary test as MDB-FR-001/028 — `services/gxp-api`'s own credentials are the only path to PostgreSQL; nothing in this codebase issues them to a Frappe job. |
| MDB-FR-011 | Client/server scripts cannot bypass APIs | Frappe-side; not yet scaffolded. |
| MDB-FR-012 | ERPNext optionality | AG-01 / ADR-0005: ERPNext is an external integration target (`app/modules/erp/*`) reached over its own adapter; the GxP app has never required it to function. |
| MDB-FR-013 | Projection/list indexes | Frappe-side; not yet scaffolded. |
| MDB-FR-014 | No mirroring millions of audit rows into MariaDB | Structural: `audit.audit_events` has no MariaDB replica or export path in this codebase. |
| MDB-FR-015 | Projection rebuild in maintenance mode | Already implemented generically: `dataops.rebuild_projection()` / `readmodels.rebuild_search_index()` / `refresh_read_model()` — a future Frappe projection worker calls the same pattern. |
| MDB-FR-016 | No manual projection edit; repair source mapping and replay | Enforced at the DB privilege level everywhere a projection-shaped table exists (`dataops.*`, `readmodels.*` — app role has no `DELETE`, and there is no generic update-arbitrary-field endpoint). |
| MDB-FR-017 | MariaDB backup | Deployment/ops concern (Document 76); not application-code testable here. |
| MDB-FR-018 | Restore order / reconciliation | `verifyMariaDBAfterRestore()` is Frappe/ops tooling that doesn't exist yet; the reconciliation *mechanism* it would call is `dataops.verify_cross_store_consistency()` (already built, Document 69). |
| MDB-FR-019 | Frappe migrations versioned/controlled | Frappe-side (bench migrations); not yet scaffolded. |
| MDB-FR-020 | Site config secrets excluded from Frappe DB | Frappe-side; not yet scaffolded. Policy stands: no secret is ever written to a projection table in this codebase. |
| MDB-FR-021 | Tenant deployment topology | ADR-0006: single-tenant-per-deployment; applies identically once a Frappe site exists. |
| MDB-FR-022 | Frappe Version/activity is non-authoritative vs GxP Audit Ledger | Structural: `audit.audit_events` (Document 05) is the only ledger any command handler writes to. |
| MDB-FR-023 | Projection lag shown, not hidden | Already implemented generically: `dataops.get_projection_freshness()` / `readmodels.fetch_search_result_detail()` return `stale`/`degraded` flags a future Frappe UI would surface. |
| MDB-FR-024 | No false distributed atomicity from Frappe hooks; projector is replay/idempotent | `eventbus.consume_event_idempotently()` (Document 73) is exactly this mechanism, ready for a Frappe-side consumer to use once it exists. |
| MDB-FR-025 | Frappe permissions supplement UI visibility; Policy Service mandatory for regulated action | Already true: every `services/gxp-api` command handler calls `evaluate_policy()` regardless of what any caller's local permission model believes. |
| MDB-FR-026 | Read-only reporting MariaDB role | Frappe/ops-side; not yet scaffolded. |
| MDB-FR-027 | Database health monitoring | Ops concern; not application-code testable here. |
| MDB-FR-028 | No cross-engine SQL joins | Structural: `services/gxp-api` has zero MariaDB/MySQL driver dependency (proven, not just asserted — see `tests/test_frappeproj_boundary.py`), so a cross-engine join is not merely discouraged, it is impossible from this codebase. |

## Known limitation

`apps/ebmr_frappe` does not exist on disk as of this pass (verified: only the pinned `apps/frappe`
framework submodule is present). Every MDB-FR above that is genuinely Frappe-side (DocType hooks,
bench migrations, Frappe permissions, background jobs) cannot be implemented or tested until that
scaffolding begins, per `ADR-0008` point 4 — this is a sequencing fact carried forward from every prior
work package's own "Frappe UI surfaces" deferral, not a new gap introduced here.
