# Claude Code prompt — WP-03: Genealogy / Review / Release / Packaging / Yield

TASK:
Implement WP-03 (Traceability, review-by-exception, disposition, packaging/labeling reconciliation and yield.) covering Documents 13, 14, 15, 16, 17.

SOURCE OF TRUTH:
- `specs/Documents_01_105/` for each listed document
- Approved baselines: Documents 106–115 in `specs/Documents_106_115/`
- `work-packages/WP-03/01_SCOPE_AND_REQUIREMENTS.md` … `12_SPEC_GAPS.md`
- Requirements in scope: 156

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
- WP-02 accepted.
- Contracts for in-scope modules committed before implementation.

ALLOWED SCOPE:
- `services/gxp-api/src/modules/ebmr` (Document 13)
- `services/gxp-api/src/modules/ebmr` (Document 14)
- `services/gxp-api/src/modules/ebmr` (Document 15)
- `services/gxp-api/src/modules/ebmr` (Document 16)
- `services/gxp-api/src/modules/ebmr` (Document 17)
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
1. `prompts/WP-03/13_SPEC-EBMR-004.md` — Genealogy & Traceability Engine Specification
2. `prompts/WP-03/14_SPEC-EBMR-005.md` — Review-by-Exception & QA Review Specification
3. `prompts/WP-03/15_SPEC-EBMR-006.md` — Release / Disposition Engine Specification
4. `prompts/WP-03/16_SPEC-EBMR-007.md` — Packaging, Labeling & Reconciliation Specification
5. `prompts/WP-03/17_SPEC-EBMR-008.md` — Yield, Calculations & Manufacturing Reconciliation Specification

TEST CASES:
`test-cases/WP-03/README.md` indexes every case book in this package. All P1 cases must be PASS before the
package closes; every FAIL needs a defect reference and disposition; every BLOCKED case needs a recorded
blocker and owner.

TRACEABILITY & STATUS:
Update `traceability/TRACEABILITY_MASTER.csv`, `traceability/WP-03_TRACEABILITY.md` and
`status/build-status.json` as each module advances, then run `python tooling/status/rollup.py`.

ACCEPTANCE CRITERIA:
Every box in `work-packages/WP-03/11_ACCEPTANCE_CHECKLIST.md` is satisfied with real evidence.

SPEC_GAP RULE:
Do not guess regulated behaviour. Append to `docs/generated/18_SPEC_GAPS.md` and
`work-packages/WP-03/12_SPEC_GAPS.md`, then continue only on unaffected work.

BEFORE COMPLETION:
Run all checks and tests; report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; tests run and results; validation impact;
traceability updated; unresolved SPEC_GAPs; known limitations.
