# Prompt 01 — Repository foundation (WP-00 entry)

TASK:
Create the monorepo skeleton, contract tooling, architecture guardrails and CI gates.

SOURCE OF TRUTH:
- `docs/generated/17_REPOSITORY_STRUCTURE.md` (authoritative layout)
- `docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md`
- `docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md`
- `docs/generated/39_CI_CD_RELEASE_EVIDENCE_MODEL.md`
- Documents 97–104 and 113; `docs/adr/ADR-0001`, `ADR-0002`, `ADR-0003`

ALLOWED SCOPE:
- directory skeleton, workspace/build configuration, linting, typing, test harness
- `tooling/guardrails/*` static checks
- `contracts/` structure and schema linting
- `.github/workflows/ci.yml` wiring
- no domain logic

DO NOT:
- implement any regulated module (that is WP-01 onward)
- modify `specs/`
- add dependencies without the Document 104 justification

DELIVERABLES:
1. Directory skeleton exactly as `17_REPOSITORY_STRUCTURE.md`.
2. TypeScript strict configuration; Python typing for the Frappe app.
3. Guardrail checks that fail the build on: `specs/` edits, Frappe core edits, `frappe.db.set_value` on
   regulated data, cross-module repository imports, bus publish outside the outbox publisher, binary float
   in a regulated numeric path, raw SQL string building.
4. Contract lint + compatibility check + codegen into `packages/data-contracts`.
5. Conformance checks: requirement-ID uniqueness, single event producer, entity ownership, risk-class coverage.
6. Traceability check job.
7. Migration safety check.
8. CI pipeline wired to all gates with real, non-fabricated output.

ACCEPTANCE CRITERIA:
- a deliberately violating branch fails CI for each guardrail (prove it with a negative test)
- `npm run guardrails`, `contracts:check`, `specs:conformance`, `traceability:check`, `migrations:check` all exist and run
- no domain code added

COMPLETION REPORT: per CLAUDE.md §6.
