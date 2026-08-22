# Claude Code prompt — WP-11: Data / Infrastructure / DR / SRE

TASK:
Implement WP-11 (Ownership/lineage, PostgreSQL, MariaDB projections, evidence/WORM, NATS/outbox, Temporal, read models, DR, deployment, SRE.) covering Documents 69, 70, 71, 72, 73, 74, 75, 76, 77, 78.

SOURCE OF TRUTH:
- `specs/Documents_01_105/` for each listed document
- Approved baselines: Documents 106–115 in `specs/Documents_106_115/`
- `work-packages/WP-11/01_SCOPE_AND_REQUIREMENTS.md` … `12_SPEC_GAPS.md`
- Requirements in scope: 315

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
- WP-00, WP-01 accepted.
- Contracts for in-scope modules committed before implementation.

ALLOWED SCOPE:
- `infrastructure` (Document 69)
- `infrastructure` (Document 70)
- `infrastructure` (Document 71)
- `infrastructure` (Document 72)
- `infrastructure` (Document 73)
- `infrastructure` (Document 74)
- `infrastructure` (Document 75)
- `infrastructure` (Document 76)
- `infrastructure` (Document 77)
- `infrastructure` (Document 78)
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
1. `prompts/WP-11/69_SPEC-DATA-001.md` — Enterprise Data Ownership, Persistence Topology & Data Lineage
2. `prompts/WP-11/70_SPEC-DATA-002.md` — PostgreSQL GxP Database Architecture, Schema, Partitioning & Concurrency
3. `prompts/WP-11/71_SPEC-DATA-003.md` — Frappe / MariaDB Operational Database, Projection & UI Data Architecture
4. `prompts/WP-11/72_SPEC-DATA-004.md` — Immutable Evidence, Object Storage, WORM, Archive & File Lifecycle
5. `prompts/WP-11/73_SPEC-DATA-005.md` — NATS / JetStream Event Bus, Transactional Outbox & Async Contracts
6. `prompts/WP-11/74_SPEC-DATA-006.md` — Temporal Durable Workflow Orchestration Architecture
7. `prompts/WP-11/75_SPEC-DATA-007.md` — Caching, Search, Read Models, Reporting Projections & Analytics Data Access
8. `prompts/WP-11/76_SPEC-DATA-008.md` — Backup, Restore, Point-in-Time Recovery & Disaster Recovery
9. `prompts/WP-11/77_SPEC-DATA-009.md` — Cloud-Neutral Deployment, Kubernetes, On-Prem Runtime & Upgrade Architecture
10. `prompts/WP-11/78_SPEC-DATA-010.md` — Performance, Capacity, Observability, SLOs & SRE Operations

TEST CASES:
`test-cases/WP-11/README.md` indexes every case book in this package. All P1 cases must be PASS before the
package closes; every FAIL needs a defect reference and disposition; every BLOCKED case needs a recorded
blocker and owner.

TRACEABILITY & STATUS:
Update `traceability/TRACEABILITY_MASTER.csv`, `traceability/WP-11_TRACEABILITY.md` and
`status/build-status.json` as each module advances, then run `python tooling/status/rollup.py`.

ACCEPTANCE CRITERIA:
Every box in `work-packages/WP-11/11_ACCEPTANCE_CHECKLIST.md` is satisfied with real evidence.

SPEC_GAP RULE:
Do not guess regulated behaviour. Append to `docs/generated/18_SPEC_GAPS.md` and
`work-packages/WP-11/12_SPEC_GAPS.md`, then continue only on unaffected work.

BEFORE COMPLETION:
Run all checks and tests; report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; tests run and results; validation impact;
traceability updated; unresolved SPEC_GAPs; known limitations.
