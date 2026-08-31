# ADR-0008-FRAPPE-ROLE-AND-UI-LAYER — Frappe (`apps/ebmr_frappe`) is the operator UI of record

**Status:** Accepted  
**Date:** 2026-08-22  
**Deciders:** Platform Architect, Specification Owner

---

## Context

Three UI-adjacent directories exist in this repository: `apps/frappe` (the pinned Frappe framework
submodule, no custom app built on it yet), `frontend/` (a working Next.js application that already calls
`services/gxp-api` directly on port 8010 for batches, materials, recipes and products), and `eBMR-ui/`
(a static HTML style guide and screen set). Document 02 §5 names Frappe Framework as the "Primary
Application Framework"; guardrails AG-01/AG-02 and Document 71's projection/read-model rules assume the
operator UI is Frappe. None of Documents 01–105, `docs/generated/17_REPOSITORY_STRUCTURE.md`, or
`docs/generated/00_PROJECT_OUTLINE.md` mention Next.js, React or any UI framework other than Frappe
anywhere — `apps/ebmr_frappe` is the only UI surface the controlled specification baseline recognizes.
`frontend/` was built ahead of, and outside, that baseline; nothing in the specs anticipated it.

REMEDIATION_R1 FIX 4 requires this recorded plainly rather than left to drift: is the operator UI Frappe,
Next.js, or a split — and if Next.js is genuinely the operator UI, Document 71 needs reworking, not quiet
coexistence with two stories.

## Decision

1. **The operator UI is Frappe (`apps/ebmr_frappe`), not Next.js.** This affirms ADR-0005 and the spec
   baseline as written. Document 71's Frappe-projection/read-model assumptions stand unmodified — no
   SPEC_GAP is raised against Document 71, because the UI-framework question is answered, not open.
2. **`frontend/` (Next.js) is a pre-existing implementation deviation, not a second regulated UI.** It was
   built and is functioning ahead of `apps/ebmr_frappe` being scaffolded, calling `services/gxp-api`
   directly — the same GxP API `apps/ebmr_frappe` will call, so it does not violate AG-02 (no regulated
   write bypasses the Mutation Gateway) or AG-06. It is **not** the operator UI of record and must not be
   treated as validated regulated tooling. It is kept as an internal/engineering-demo surface for now.
   Retirement timing is a product scheduling decision, not an architecture one — see SPEC_GAP SG-021.
3. **`eBMR-ui/` is design assets, not a third live surface.** It is a static HTML style guide and screen
   reference with no application runtime; its tokens are already ported into `frontend/src/styles/ebmr-*.css`.
   It remains the design source of truth for both `frontend/` (while it exists) and `apps/ebmr_frappe`
   theming going forward. It is not deleted.
4. **`apps/ebmr_frappe` scaffolding begins with WP-01.** Each WP-01 sub-prompt (`prompts/WP-01/*.md`) already
   declares its own `apps/ebmr_frappe/ebmr/...` UI surface under "FILES TO CREATE/MODIFY" — starting with
   Document 04 (Part 11 Electronic Signature), the first WP-01 module with a real UI component (the
   signature ceremony screen). There is no separate WP-00 task to scaffold the app shell in bulk; it is
   built module by module as each work package's prompt specifies.

## Rationale

The controlled baseline is unambiguous and singular on this question — every reference to "the UI" across
Document 01/02, `17_REPOSITORY_STRUCTURE.md` and `00_PROJECT_OUTLINE.md` means Frappe, and AG-01/AG-02
already assume it mechanically (a custom Frappe app in `apps/ebmr_frappe`, regulated logic never embedded
in DocType controllers, Frappe calling GxP Core over the API). Reversing that would mean rewriting Document
71 and re-deriving every projection/read-model rule in the baseline — a change with far more blast radius
than accepting that `frontend/` is what it actually is: a working prototype that got ahead of the spec
process. Recording it as a deviation, not deleting it and not promoting it, matches Document 02 §13.1's
change-recording discipline and avoids two UI stories both quietly claiming to be authoritative.

## Consequences

- `apps/ebmr_frappe` is where regulated-UI validation evidence, test cases and traceability rows are
  recorded going forward — `frontend/`'s pages are out of scope for GxP UI validation.
- `frontend/` may keep running as an internal tool during the `apps/ebmr_frappe` build-out; no regulated
  claim is made about it, and it is called out as a known limitation in this task's completion report.
- SPEC_GAP SG-021 (`docs/generated/18_SPEC_GAPS.md`) tracks the open, non-blocking product decision of when
  `frontend/` is retired or repurposed — that decision does not block WP-01 or any GxP Core work.
- `eBMR-ui/` stays in the repository as the design-token source; it is not code and carries no regulated
  claim either way.
