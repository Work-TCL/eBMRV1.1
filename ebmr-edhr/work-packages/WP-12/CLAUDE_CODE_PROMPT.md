# Claude Code prompt — WP-12: Validation Platform & Evidence

TASK:
Implement WP-12 (VMP/CSA, intended use & risk, traceability, test strategy, IQ/OQ, infrastructure/Part11/data-integrity/interface/DR/security/performance qualification, exceptions, periodic review.) covering Documents 79, 80, 81, 82, 83, 84, 86, 88, 89, 90, 91, 92, 93, 94, 96.

SOURCE OF TRUTH:
- `specs/Documents_01_105/` for each listed document
- Approved baselines: Documents 106–115 in `specs/Documents_106_115/`
- `work-packages/WP-12/01_SCOPE_AND_REQUIREMENTS.md` … `12_SPEC_GAPS.md`
- Requirements in scope: 350

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
- WP-01, WP-11 accepted.
- Contracts for in-scope modules committed before implementation.

ALLOWED SCOPE:
- `validation` (Document 79)
- `validation` (Document 80)
- `validation` (Document 81)
- `validation` (Document 82)
- `validation` (Document 83)
- `validation` (Document 84)
- `validation` (Document 86)
- `validation` (Document 88)
- `validation` (Document 89)
- `validation` (Document 90)
- `validation` (Document 91)
- `validation` (Document 92)
- `validation` (Document 93)
- `validation` (Document 94)
- `validation` (Document 96)
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
1. `prompts/WP-12/79_SPEC-VAL-001.md` — Validation Master Plan & Computer Software Assurance Strategy
2. `prompts/WP-12/80_SPEC-VAL-002.md` — Intended Use, GxP Criticality & Software Function Risk Classification
3. `prompts/WP-12/81_SPEC-VAL-003.md` — Requirements, Design Inputs & Validation Traceability Management
4. `prompts/WP-12/82_SPEC-VAL-004.md` — Validation Test Strategy, Test Methods & Objective Evidence Governance
5. `prompts/WP-12/83_SPEC-VAL-005.md` — Installation Qualification (IQ) & Installed Baseline Verification
6. `prompts/WP-12/84_SPEC-VAL-006.md` — Operational Qualification (OQ) & Functional Control Verification
7. `prompts/WP-12/86_SPEC-VAL-008.md` — Infrastructure, Cloud, Platform & Environment Qualification
8. `prompts/WP-12/88_SPEC-VAL-010.md` — 21 CFR Part 11 Electronic Records & Electronic Signature Validation
9. `prompts/WP-12/89_SPEC-VAL-011.md` — Audit Trail, Record Version Vault & Data Integrity Validation
10. `prompts/WP-12/90_SPEC-VAL-012.md` — Integration, Edge, Device, Peripheral & Interface Validation
11. `prompts/WP-12/91_SPEC-VAL-013.md` — Backup, Restore, PITR & Disaster Recovery Qualification
12. `prompts/WP-12/92_SPEC-VAL-014.md` — Security Qualification, Vulnerability Verification & Penetration Testing
13. `prompts/WP-12/93_SPEC-VAL-015.md` — Performance, Load, Capacity & Reliability Qualification
14. `prompts/WP-12/94_SPEC-VAL-016.md` — Validation Defect, Deviation, Test Exception & Remediation Management
15. `prompts/WP-12/96_SPEC-VAL-018.md` — Periodic Review, Change Impact, Revalidation & Validated-State Maintenance

TEST CASES:
`test-cases/WP-12/README.md` indexes every case book in this package. All P1 cases must be PASS before the
package closes; every FAIL needs a defect reference and disposition; every BLOCKED case needs a recorded
blocker and owner.

TRACEABILITY & STATUS:
Update `traceability/TRACEABILITY_MASTER.csv`, `traceability/WP-12_TRACEABILITY.md` and
`status/build-status.json` as each module advances, then run `python tooling/status/rollup.py`.

ACCEPTANCE CRITERIA:
Every box in `work-packages/WP-12/11_ACCEPTANCE_CHECKLIST.md` is satisfied with real evidence.

SPEC_GAP RULE:
Do not guess regulated behaviour. Append to `docs/generated/18_SPEC_GAPS.md` and
`work-packages/WP-12/12_SPEC_GAPS.md`, then continue only on unaffected work.

BEFORE COMPLETION:
Run all checks and tests; report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; tests run and results; validation impact;
traceability updated; unresolved SPEC_GAPs; known limitations.
