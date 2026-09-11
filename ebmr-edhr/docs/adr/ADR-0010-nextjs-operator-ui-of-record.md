# ADR-0010-NEXTJS-OPERATOR-UI-OF-RECORD — the Next.js `frontend/` is the operator UI of record; ADR-0008 superseded

**Status:** Accepted — supersedes ADR-0008
**Date:** 2026-09-09
**Deciders:** Project Owner (via Claude Code session), Platform Architect

---

## Context

ADR-0008 (2026-08-22) decided that the operator UI of record is a custom Frappe app
(`apps/ebmr_frappe`), that the Next.js `frontend/` is a throwaway prototype carrying no regulated
claim, and that `apps/ebmr_frappe` would be scaffolded module-by-module starting with WP-01.

That did not happen. As of 2026-09-09:

- `apps/ebmr_frappe` **does not exist** in the repository (`apps/` contains only the pinned `frappe`
  framework submodule).
- `frontend/` (Next.js App Router SPA) has grown into the **actual, and only, UI** — 72 pages covering
  WP-01 through WP-14, a ported design system (`frontend/src/styles/ebmr-*.css`), a shared component
  library, and an auth guard. It calls `services/gxp-api` directly on port 8010.
- Every UI-facing task since ADR-0008 (product master, aseptic profiles, equipment areas, DDCP demo
  flow, signature ceremonies, RBAC sync) was implemented against `frontend/`, not Frappe.

ADR-0008's decision and the built reality now contradict each other. Validation cannot trace any UI
requirement while the UI of record on paper is a codebase that was never written. This must be resolved
before WP-12 validation execution begins.

The Project Owner was presented with three options — (a) supersede ADR-0008 and name Next.js the UI of
record, (b) keep ADR-0008 and rebuild all 72 screens as a Frappe app, (c) a Frappe/Next.js split — and
selected (a).

## Decision

1. **The Next.js application in `frontend/` is the operator UI of record.** It is in scope for GxP UI
   validation: test cases, traceability rows and validation evidence for UI requirements
   (TEST-FR-011/012, SIG-FR-015/026, the "manifestation in UI" clauses of Document 04/05/06) are
   recorded against `frontend/` pages and components.

2. **ADR-0008 is superseded.** `apps/ebmr_frappe` is not built. `apps/frappe` (the framework submodule)
   remains only because Frappe is still a pinned dependency of any back-office tooling the project may
   later add; it hosts no regulated UI.

3. **The UI reads the GxP API directly; there is no Frappe/MariaDB projection tier.** `frontend/` fetches
   authoritative detail and version from `services/gxp-api` for every regulated action and signature
   (the read path Document 04/71 assigned to a projection is served directly by the owning service).
   The architecture non-negotiables that ADR-0008 restated still hold and are unaffected: no regulated
   write bypasses the Mutation Gateway (AG-06), no UI touches the database directly (AG-03), released
   record versions are immutable (AG-08).

4. **Document 71 (SPEC-DATA-003, Frappe/MariaDB Operational Projection & UI Data Architecture) no longer
   applies as written.** Its MDB-FR-001…028 projection-DocType model, staleness-metadata rules and
   read-model rebuild mechanism describe a tier this platform does not have. This is raised as a new
   SPEC_GAP (**SG-182**) for a human decision: rework Document 71 to describe the direct-read Next.js
   architecture, or formally descope it. SG-182 does not block the core build.

5. **`eBMR-ui/` is unchanged** — it stays as the design-token source of truth (already ported into
   `frontend/src/styles/`), not a live surface.

6. **AG-01 is formally deviated from.** Document 01/02's "Primary Application Framework: Frappe" is not
   the operator UI in this implementation. AG-02 (regulated logic never in UI controllers) and AG-03/06
   are honoured — regulated logic lives entirely in `services/gxp-api`; `frontend/` is a pure client.

## Rationale

The Frappe UI does not exist and the Next.js UI is complete and in daily use for the client demo. Option
(b) means re-implementing 72 validated-candidate screens in a second framework and reworking nothing else
of value; option (c) means validating two UI codebases. Option (a) records what was actually built,
scopes it for validation, and isolates the one genuine casualty — Document 71 — into a tracked SPEC_GAP
rather than leaving two UI stories both nominally authoritative.

## Consequences

- `frontend/` pages and components carry traceability rows and validation evidence going forward.
  `status/build-status.json` and `traceability/TRACEABILITY_MASTER.csv` UI rows are re-pointed from
  `apps/ebmr_frappe/...` to `frontend/src/app/...`.
- **SG-182** opens against Document 71. **SG-021** (frontend retirement timing) is resolved — `frontend/`
  is not retired; it is the UI. **SG-028 / SG-034 / SG-036** (Document 05/06/07/08 "Frappe UI surfaces
  cannot be built — `apps/ebmr_frappe` does not exist") are re-scoped: the equivalent Next.js surfaces
  exist; those gaps become "confirm the existing `frontend/` screen covers the requirement," owned by the
  UI module owner, not blocked on a non-existent app.
- `docs/generated/17_REPOSITORY_STRUCTURE.md` and `00_PROJECT_OUTLINE.md` add `frontend/` as a
  first-class regulated component.
- A UI test layer (component tests for high-risk controls per TEST-FR-012, an e2e layer per TEST-FR-013)
  is a WP-00 / WP-12 deliverable — `frontend/` currently has no automated test suite.
- AG-01's deviation is recorded here and referenced from
  `docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md`.
