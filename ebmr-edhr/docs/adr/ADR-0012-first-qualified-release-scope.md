# ADR-0012-FIRST-QUALIFIED-RELEASE-SCOPE — the first QUALIFIED/RELEASED milestone is narrow core-eBMR

**Status:** Accepted
**Date:** 2026-09-09
**Deciders:** Project Owner (via Claude Code session), Platform Architect, Validation Lead

---

## Context

103 tracked modules across 15 work packages, ~2 965 requirements, 9 150 test cases. Full-scope
qualification (every module to `QUALIFIED`/`RELEASED`) is on the order of a year of team effort, and
`REVIEWED`/`OQ_EXECUTED`/`QUALIFIED`/`RELEASED` are human-set gates that cannot be reached until the WP-12
validation platform is executed against a stable scope.

Holding the first release until everything is qualified maximises the time to any releasable artifact and
the exposure to scope creep. The Project Owner chose to define a **narrow first milestone** and extend in
validated increments after.

## Decision

1. **The first qualified/released scope is core-eBMR:**
   - **WP-01** — GxP Core (mutation gateway, Part 11 signature, immutable audit ledger, record
     vault/versioning, IAM/RBAC/SoD/qualification, regulatory rules & calculation engine)
   - **WP-02** — Product / Recipe / Batch execution / eDHR (on the single authoritative store per
     ADR-0013)
   - **WP-03** — Genealogy / Review-by-exception / Release-disposition / Packaging / Yield
   - **WP-04** — Procurement / Materials / QC
   - **WP-10** — Security **baseline only**: the controls the above four packages exercise
     (authn/authz/BOLA/BFLA, tenant/site isolation, signature-abuse, injection, secrets, audit-tamper).
     Full Document 61–68 coverage is a later increment.

2. **Out of the first milestone** (built, extended and validated in later increments): WP-05 QMS,
   WP-06 Equipment/Sterile/Edge, WP-07 Enterprise Integrations, WP-08 DDCP profiles, WP-09 Postmarket,
   WP-13 AI advisory. WP-11 and WP-12 are **continuous** — the infrastructure and validation platform
   the first milestone depends on — not deferred.

3. **Entry criteria for starting first-milestone validation execution (WP-12 IQ/OQ):**
   - ADR-0013 store cutover complete (SG-173 executed)
   - SG-013 API + event contracts committed for WP-01/02/03/04; conformance gate in CI
   - Document 106 signature-policy rows complete for every WP-01/02/03/04 signed action
     (SG-035 remainder, SG-181 remainder; SG-091 `reason_required` enforced)
   - SG-143 resolved (rules evaluator applies frozen precision/rounding/UOM)
   - WP-00 engineering backbone in place (CI, SBOM, coding-standard enforcement, branch protection)
   - `frontend/` has a UI component + e2e test layer for the in-scope screens (per ADR-0010)

4. **Exit criteria:** every requirement in the five in-scope packages `VERIFIED` with executed OQ
   evidence; traceability complete; validation summary + go-live authorization signed (Document 95).

## Rationale

WP-01–04 plus a security baseline is the smallest set that delivers a usable, inspectable eBMR/eDHR
(make a product, run a batch, consume materials, QC-disposition, review by exception, release with
genealogy) and it contains the fewest open regulated SPEC_GAPs. The excluded packages each carry large
blocked-gap clusters (SG-059…108, SG-109…131, SG-121…126, SG-150/179, SG-154…160, SG-167) that would
gate a wider first milestone on decisions and build-out not yet done.

## Consequences

- `status/STATUS_MODEL.md` / `build-status.json` tag each module with `release_milestone: M1` or
  `later`; the rollup reports M1 progress separately.
- WP-05–09 and WP-13 continue in development but their `CODE_COMPLETE` claims are not on the M1 critical
  path.
- The remediation roadmap (`DOCS_VS_IMPLEMENTATION_GAP_ANALYSIS.md` §8/§10) is re-ordered so Phases 1–3
  and 6 target the M1 scope first.
- A later ADR defines M2 scope once M1 reaches `OQ_EXECUTED`.
