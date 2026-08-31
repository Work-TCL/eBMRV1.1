# Claude Code prompt — WP-00: Repository, Tooling & Contract Foundations

TASK:
Implement WP-00 (Monorepo skeleton, contract tooling, CI gates, architecture guardrails, migration/test/release standards.) covering Documents 01, 02, 97, 98, 99, 100, 101, 102, 103, 104.

SOURCE OF TRUTH:
- `specs/Documents_01_105/` for each listed document
- Approved baselines: Documents 106–115 in `specs/Documents_106_115/`
- `work-packages/WP-00/01_SCOPE_AND_REQUIREMENTS.md` … `12_SPEC_GAPS.md`
- Requirements in scope: 542

ARCHITECTURE CONSTRAINTS:
- Frappe is UI/configuration only; no core fork or edit.
- PostgreSQL is authoritative for regulated state; MariaDB holds read-only projections.
- Every regulated write goes through the Mutation Gateway → one PostgreSQL transaction carrying
  domain state + record version + audit event + outbox event.
- Signatures follow Document 04 + the approved Document 106 policy; login/MFA is never a signature.
- Audit, vault and evidence history is append-only and superseding.
- Outbox is the authoritative event source; NATS is transport; Temporal is orchestration only.
- Caches, projections, search and reports are rebuildable and never a regulated decision source.
- Adapters and edge never write GxP tables; they submit integration commands.
- AI is advisory; it cannot sign, release, disposition, approve, alter audit or submit reports.

PRECONDITIONS:
- Phase-0 review approved accepted.
- Contracts for in-scope modules committed before implementation.

ALLOWED SCOPE:
- `docs/architecture` (Document 01)
- `docs/architecture` (Document 02)
- `tooling` (Document 97)
- `tooling` (Document 98)
- `tooling` (Document 99)
- `tooling` (Document 100)
- `tooling` (Document 101)
- `tooling` (Document 102)
- `tooling` (Document 103)
- `tooling` (Document 104)
- contracts, migrations, tests and Frappe UI for these modules only

DO NOT:
- Do not modify anything under `specs/`.
- Do not implement a signature requirement not present in the approved Document 106 policy set
  (emit a policy row and reference the gap instead).
- Do not create a second authoritative store for an entity owned elsewhere.
- Do not add an endpoint to a module whose exposure boundary is "no independent API" (Document 113 §6).
- Do not write a migration for an entity absent from `docs/generated/04_DATA_MODEL_CATALOGUE.md`.
- Do not use binary floating point for a regulated quantity.
- Do not fabricate a test run, scan result or qualification record.
- Do not start work in another work package.

EXECUTION ORDER — run these sub-prompts in sequence:
1. `prompts/WP-00/01_DOC-001.md` — Master Product, Compliance & Architecture Bible
2. `prompts/WP-00/02_DOC-002.md` — System Architecture & GxP Core Technical Specification
3. `prompts/WP-00/97_SPEC-ENG-001.md` — Coding Standards
4. `prompts/WP-00/98_SPEC-ENG-002.md` — Architecture Rules for Claude Code / Codex
5. `prompts/WP-00/99_SPEC-ENG-003.md` — Repository & Branching Standard
6. `prompts/WP-00/100_SPEC-ENG-004.md` — Database Migration Standard
7. `prompts/WP-00/101_SPEC-ENG-005.md` — API & Event Contract Standard
8. `prompts/WP-00/102_SPEC-ENG-006.md` — Testing Strategy
9. `prompts/WP-00/103_SPEC-ENG-007.md` — CI/CD & Release Process
10. `prompts/WP-00/104_SPEC-ENG-008.md` — SBOM / Third-Party License Management

TEST CASES:
`test-cases/WP-00/README.md` indexes every case book in this package. All P1 cases must be PASS before the
package closes; every FAIL needs a defect reference and disposition; every BLOCKED case needs a recorded
blocker and owner.

TRACEABILITY & STATUS:
Update `traceability/TRACEABILITY_MASTER.csv`, `traceability/WP-00_TRACEABILITY.md` and
`status/build-status.json` as each module advances, then run `python tooling/status/rollup.py`.

ACCEPTANCE CRITERIA:
Every box in `work-packages/WP-00/11_ACCEPTANCE_CHECKLIST.md` is satisfied with real evidence.

SPEC_GAP RULE:
Do not guess regulated behaviour. Append to `docs/generated/18_SPEC_GAPS.md` and
`work-packages/WP-00/12_SPEC_GAPS.md`, then continue only on unaffected work.

BEFORE COMPLETION:
Run all checks and tests; report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; tests run and results; validation impact;
traceability updated; unresolved SPEC_GAPs; known limitations.
