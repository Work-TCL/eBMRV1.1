# Claude Code prompt — WP-01: GxP Core — Mutation / Signature / Audit / Vault / IAM / Rules

TASK:
Implement WP-01 (The regulated kernel: every later module depends on these six services.) covering Documents 03, 04, 05, 06, 07, 08.

SOURCE OF TRUTH:
- `specs/Documents_01_105/` for each listed document
- Approved baselines: Documents 106–115 in `specs/Documents_106_115/`
- `work-packages/WP-01/01_SCOPE_AND_REQUIREMENTS.md` … `12_SPEC_GAPS.md`
- Requirements in scope: 186

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
- WP-00 accepted.
- Contracts for in-scope modules committed before implementation.

ALLOWED SCOPE:
- `services/gxp-api/src/modules/mutation` (Document 03)
- `services/gxp-api/src/modules/signature` (Document 04)
- `services/gxp-api/src/modules/audit` (Document 05)
- `services/gxp-api/src/modules/vault` (Document 06)
- `services/gxp-api/src/modules/policy` (Document 07)
- `services/gxp-api/src/modules/rules` (Document 08)
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
1. `prompts/WP-01/03_SPEC-GXP-001.md` — GxP Mutation Gateway
2. `prompts/WP-01/04_SPEC-GXP-002.md` — 21 CFR Part 11 Electronic Signature
3. `prompts/WP-01/05_SPEC-GXP-003.md` — Immutable Audit Ledger & Audit Review
4. `prompts/WP-01/06_SPEC-GXP-004.md` — Record Version Vault, Locking, Amendment & Controlled Correction
5. `prompts/WP-01/07_SPEC-IAM-001.md` — Identity, Authorization, RBAC, Qualification & Segregation-of-Duties
6. `prompts/WP-01/08_SPEC-GXP-006.md` — Regulatory Rules & Calculation Engine

TEST CASES:
`test-cases/WP-01/README.md` indexes every case book in this package. All P1 cases must be PASS before the
package closes; every FAIL needs a defect reference and disposition; every BLOCKED case needs a recorded
blocker and owner.

TRACEABILITY & STATUS:
Update `traceability/TRACEABILITY_MASTER.csv`, `traceability/WP-01_TRACEABILITY.md` and
`status/build-status.json` as each module advances, then run `python tooling/status/rollup.py`.

ACCEPTANCE CRITERIA:
Every box in `work-packages/WP-01/11_ACCEPTANCE_CHECKLIST.md` is satisfied with real evidence.

SPEC_GAP RULE:
Do not guess regulated behaviour. Append to `docs/generated/18_SPEC_GAPS.md` and
`work-packages/WP-01/12_SPEC_GAPS.md`, then continue only on unaffected work.

BEFORE COMPLETION:
Run all checks and tests; report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; tests run and results; validation impact;
traceability updated; unresolved SPEC_GAPs; known limitations.
