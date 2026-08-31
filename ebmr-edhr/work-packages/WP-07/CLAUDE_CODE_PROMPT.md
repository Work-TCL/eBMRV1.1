# Claude Code prompt — WP-07: Enterprise Integrations

TASK:
Implement WP-07 (ERP architecture and adapters, master-data sync, integration error/retry/reconciliation.) covering Documents 48, 49, 50, 51, 52, 53.

SOURCE OF TRUTH:
- `specs/Documents_01_105/` for each listed document
- Approved baselines: Documents 106–115 in `specs/Documents_106_115/`
- `work-packages/WP-07/01_SCOPE_AND_REQUIREMENTS.md` … `12_SPEC_GAPS.md`
- Requirements in scope: 161

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
- WP-01, WP-04 accepted.
- Contracts for in-scope modules committed before implementation.

ALLOWED SCOPE:
- `services/integration-gateway` (Document 48)
- `services/integration-gateway` (Document 49)
- `services/integration-gateway` (Document 50)
- `services/integration-gateway` (Document 51)
- `services/integration-gateway` (Document 52)
- `services/integration-gateway` (Document 53)
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
1. `prompts/WP-07/48_SPEC-ERP-001.md` — Enterprise ERP Integration Architecture & Provider Contract
2. `prompts/WP-07/49_SPEC-ERP-002.md` — ERPNext Adapter Detailed Contract
3. `prompts/WP-07/50_SPEC-ERP-003.md` — SAP S/4HANA Adapter Contract
4. `prompts/WP-07/51_SPEC-ERP-004.md` — Oracle Fusion, Dynamics 365 & Custom ERP Adapter Contracts
5. `prompts/WP-07/52_SPEC-ERP-005.md` — Master Data Synchronization, Mapping & Reconciliation
6. `prompts/WP-07/53_SPEC-ERP-006.md` — Integration Error Handling, Retry, Idempotency & Reconciliation

TEST CASES:
`test-cases/WP-07/README.md` indexes every case book in this package. All P1 cases must be PASS before the
package closes; every FAIL needs a defect reference and disposition; every BLOCKED case needs a recorded
blocker and owner.

TRACEABILITY & STATUS:
Update `traceability/TRACEABILITY_MASTER.csv`, `traceability/WP-07_TRACEABILITY.md` and
`status/build-status.json` as each module advances, then run `python tooling/status/rollup.py`.

ACCEPTANCE CRITERIA:
Every box in `work-packages/WP-07/11_ACCEPTANCE_CHECKLIST.md` is satisfied with real evidence.

SPEC_GAP RULE:
Do not guess regulated behaviour. Append to `docs/generated/18_SPEC_GAPS.md` and
`work-packages/WP-07/12_SPEC_GAPS.md`, then continue only on unaffected work.

BEFORE COMPLETION:
Run all checks and tests; report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; tests run and results; validation impact;
traceability updated; unresolved SPEC_GAPs; known limitations.
