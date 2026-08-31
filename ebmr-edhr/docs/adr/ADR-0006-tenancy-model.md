# ADR-0006-TENANCY-MODEL — Single-tenant-per-deployment; row-level tenancy deferred

**Status:** Accepted  
**Date:** 2026-08-22  
**Deciders:** Platform Architect, Specification Owner

---

## Context

`iam.Organization` is modelled in `services/gxp-api` (REMEDIATION_R1 gate review, Phase 1 kernel), so
tenancy exists as a concept — but every regulated table carries only `site_id`, not a tenant/organization
column. Tenant isolation is therefore transitive (`row -> site -> organization`), enforced by whichever
query happens to join through `site` correctly, rather than by a column a forgotten join cannot bypass.
Guardrail AG-05 (one authoritative owner/store per regulated entity) and Documents 66/70's tenant-isolation
expectations are satisfied today only as long as every query and RBAC check honours that transitive chain.

Both a single-tenant deployment model and a row-level multi-tenant model are legitimate architectures for
this platform. What is not legitimate is leaving the choice undecided while the schema grows — retrofitting
a `tenant_id` column across the full entity catalogue later is materially more expensive than deciding now,
and the decision has direct consequences for row-level security, query authorization and future migrations.

## Decision

1. **This platform is single-tenant per deployment.** One `iam.Organization` row exists per running
   instance of `services/gxp-api`. `Organization` is retained for identity, display and reporting, but
   tenant isolation is achieved by deployment boundary (separate database/instance per customer), not by
   row-level filtering within a shared database.
2. **A startup guard enforces the assumption mechanically.** `assert_single_organization()`
   (`app/core/db.py`) counts `iam.organizations` and raises at process startup if more than one row exists,
   so a violation of the single-tenant assumption is a boot-time failure, not a silent isolation gap.
3. **Row-level tenancy (Option B — `tenant_id` on every regulated table, PostgreSQL RLS) is deferred**, not
   rejected. If a future shared-SaaS deployment model requires it, it is a new ADR and a migration
   (`tenant_id UUID NOT NULL` backfilled from `site -> organization`, composite index, RLS policy), not a
   silent retrofit.

## Rationale

The current deployment model is per-customer (one database per customer), which is exactly the case Option
A is designed for — the isolation guarantee comes from the deployment boundary itself, and row-level
security would add real engineering cost (schema migration across every regulated table, RLS policy
authoring and testing, `app.tenant_id` session-variable plumbing on every request) for a guarantee the
deployment model doesn't currently need. Recording the decision now, with a mechanical guard rather than
just a document, means the assumption cannot rot silently the way an undocumented convention would.

## Consequences

- `docs/adr/ADR-0006-tenancy-model.md` is authoritative for the tenancy model until superseded.
- `assert_single_organization()` runs at every `services/gxp-api` process startup (`app/main.py` `lifespan`)
  and fails the boot if a second organization exists.
- `test_cross_organization_access_denied` and `test_assert_single_organization_raises_on_second_organization`
  (`tests/test_tenancy.py`) are the executable evidence for this ADR.
- Adopting Option B later is a new ADR plus a `tenant_id` migration across every regulated table — not a
  transparent change; it changes the authorization query shape everywhere.
