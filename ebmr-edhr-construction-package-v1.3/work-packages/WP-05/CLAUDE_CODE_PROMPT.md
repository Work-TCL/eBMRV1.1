# Claude Code prompt — WP-05: Quality Management System

TASK:
Implement WP-05 (Deviation, CAPA, NC, change, document, training, SCAR, risk, audit, complaint, recall, metrics.) covering Documents 26, 27, 28, 29, 30, 31, 32, 33, 34, 35, 36, 37.

SOURCE OF TRUTH:
- `specs/Documents_01_105/` for each listed document
- Approved baselines: Documents 106–115 in `specs/Documents_106_115/`
- `work-packages/WP-05/01_SCOPE_AND_REQUIREMENTS.md` … `12_SPEC_GAPS.md`
- Requirements in scope: 257

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
- WP-01, WP-02 accepted.
- Contracts for in-scope modules committed before implementation.

ALLOWED SCOPE:
- `services/gxp-api/src/modules/qms` (Document 26)
- `services/gxp-api/src/modules/qms` (Document 27)
- `services/gxp-api/src/modules/qms` (Document 28)
- `services/gxp-api/src/modules/qms` (Document 29)
- `services/gxp-api/src/modules/qms` (Document 30)
- `services/gxp-api/src/modules/qms` (Document 31)
- `services/gxp-api/src/modules/qms` (Document 32)
- `services/gxp-api/src/modules/qms` (Document 33)
- `services/gxp-api/src/modules/qms` (Document 34)
- `services/gxp-api/src/modules/qms` (Document 35)
- `services/gxp-api/src/modules/qms` (Document 36)
- `services/gxp-api/src/modules/qms` (Document 37)
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
1. `prompts/WP-05/26_SPEC-QMS-001.md` — Deviation & Investigation Management
2. `prompts/WP-05/27_SPEC-QMS-002.md` — CAPA Management
3. `prompts/WP-05/28_SPEC-QMS-003.md` — Nonconformance Management
4. `prompts/WP-05/29_SPEC-QMS-004.md` — Change Control
5. `prompts/WP-05/30_SPEC-QMS-005.md` — Document Control
6. `prompts/WP-05/31_SPEC-QMS-006.md` — Training & Personnel Qualification
7. `prompts/WP-05/32_SPEC-QMS-007.md` — Supplier Quality / SCAR
8. `prompts/WP-05/33_SPEC-QMS-008.md` — Risk Management
9. `prompts/WP-05/34_SPEC-QMS-009.md` — Internal Audit Management
10. `prompts/WP-05/35_SPEC-QMS-010.md` — Complaint Management
11. `prompts/WP-05/36_SPEC-QMS-011.md` — Recall / Field Action Management
12. `prompts/WP-05/37_SPEC-QMS-012.md` — Quality Metrics, Trending & Effectiveness Checks

TEST CASES:
`test-cases/WP-05/README.md` indexes every case book in this package. All P1 cases must be PASS before the
package closes; every FAIL needs a defect reference and disposition; every BLOCKED case needs a recorded
blocker and owner.

TRACEABILITY & STATUS:
Update `traceability/TRACEABILITY_MASTER.csv`, `traceability/WP-05_TRACEABILITY.md` and
`status/build-status.json` as each module advances, then run `python tooling/status/rollup.py`.

ACCEPTANCE CRITERIA:
Every box in `work-packages/WP-05/11_ACCEPTANCE_CHECKLIST.md` is satisfied with real evidence.

SPEC_GAP RULE:
Do not guess regulated behaviour. Append to `docs/generated/18_SPEC_GAPS.md` and
`work-packages/WP-05/12_SPEC_GAPS.md`, then continue only on unaffected work.

BEFORE COMPLETION:
Run all checks and tests; report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; tests run and results; validation impact;
traceability updated; unresolved SPEC_GAPs; known limitations.
