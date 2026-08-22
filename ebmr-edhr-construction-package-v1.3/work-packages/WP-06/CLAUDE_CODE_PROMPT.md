# Claude Code prompt — WP-06: Equipment / Sterile / Edge

TASK:
Implement WP-06 (Equipment/calibration, cleaning/line clearance, aseptic, EM, sterilization plus the Edge/OT stack.) covering Documents 38, 39, 40, 41, 42, 43, 44, 45, 46, 47.

SOURCE OF TRUTH:
- `specs/Documents_01_105/` for each listed document
- Approved baselines: Documents 106–115 in `specs/Documents_106_115/`
- `work-packages/WP-06/01_SCOPE_AND_REQUIREMENTS.md` … `12_SPEC_GAPS.md`
- Requirements in scope: 284

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
- WP-02, WP-04 accepted.
- Contracts for in-scope modules committed before implementation.

ALLOWED SCOPE:
- `services/gxp-api/src/modules/equipment` (Document 38)
- `services/gxp-api/src/modules/equipment` (Document 39)
- `services/gxp-api/src/modules/equipment` (Document 40)
- `services/gxp-api/src/modules/equipment` (Document 41)
- `services/gxp-api/src/modules/equipment` (Document 42)
- `edge` (Document 43)
- `edge` (Document 44)
- `edge` (Document 45)
- `edge` (Document 46)
- `edge` (Document 47)
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
1. `prompts/WP-06/38_SPEC-EQP-001.md` — Equipment, Calibration, Qualification & Maintenance
2. `prompts/WP-06/39_SPEC-EQP-002.md` — Cleaning, Sanitization & Line Clearance
3. `prompts/WP-06/40_SPEC-EQP-003.md` — Sterile / Aseptic Manufacturing Operations
4. `prompts/WP-06/41_SPEC-EQP-004.md` — Environmental Monitoring & Cleanroom State Control
5. `prompts/WP-06/42_SPEC-EQP-005.md` — Sterilization, CIP/SIP & Sterile Filtration Management
6. `prompts/WP-06/43_SPEC-EDGE-001.md` — Edge Gateway Runtime Architecture & Construction Specification
7. `prompts/WP-06/44_SPEC-EDGE-002.md` — Industrial Device & Protocol Connectivity / Driver Specification
8. `prompts/WP-06/45_SPEC-EDGE-003.md` — Store-and-Forward, Offline Buffering, Time Integrity & Data Quality
9. `prompts/WP-06/46_SPEC-EDGE-004.md` — Barcode, Scanner, Balance, Printer, Tester & Peripheral Integration
10. `prompts/WP-06/47_SPEC-EDGE-005.md` — Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary

TEST CASES:
`test-cases/WP-06/README.md` indexes every case book in this package. All P1 cases must be PASS before the
package closes; every FAIL needs a defect reference and disposition; every BLOCKED case needs a recorded
blocker and owner.

TRACEABILITY & STATUS:
Update `traceability/TRACEABILITY_MASTER.csv`, `traceability/WP-06_TRACEABILITY.md` and
`status/build-status.json` as each module advances, then run `python tooling/status/rollup.py`.

ACCEPTANCE CRITERIA:
Every box in `work-packages/WP-06/11_ACCEPTANCE_CHECKLIST.md` is satisfied with real evidence.

SPEC_GAP RULE:
Do not guess regulated behaviour. Append to `docs/generated/18_SPEC_GAPS.md` and
`work-packages/WP-06/12_SPEC_GAPS.md`, then continue only on unaffected work.

BEFORE COMPLETION:
Run all checks and tests; report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; tests run and results; validation impact;
traceability updated; unresolved SPEC_GAPs; known limitations.
