# CLAUDE.md — eBMR / eDHR Regulated Manufacturing Platform

You are implementing a **U.S.-market regulated eBMR/eDHR manufacturing platform** from a controlled
specification baseline. This file is the project-wide contract. Detailed rules are in `.claude/rules/`.

## 1. Source of truth

`specs/` holds the controlled baseline and is **read-only**. Precedence, highest first:

1. Document 01 (frozen Master Product / Compliance / Architecture Bible)
2. Documents 02–105 (numbered specifications)
3. Documents 106–115 (approved gap-resolution baselines: signature policy, SoD, retention, RPO/SLO, precision, risk class, schemas, contracts, glossary, remediation)
4. Specification Authoring Standard
5. Claude Code Master Project Construction Instructions v1.7
6. `docs/generated/` (Phase-0 compiled artefacts) and `docs/adr/`
7. The current task

Never edit `specs/`. If a specification is wrong, raise a SPEC_GAP.

## 2. Architecture non-negotiables

- **AG-01** — Frappe Framework is the UI/application/configuration framework. ERPNext is NOT a base layer — it is an optional external ERP integration target only (Doc 48/49).
- **AG-02** — Proprietary GxP Core is independent product IP.
- **AG-03** — PostgreSQL is authoritative for proprietary regulated GxP state.
- **AG-04** — Frappe/MariaDB holds framework/UI/configuration and controlled non-authoritative projections.
- **AG-05** — One authoritative owner/store per regulated entity.
- **AG-06** — Regulated mutations go through the Mutation Gateway / owning domain command.
- **AG-07** — Login/MFA is not an electronic signature.
- **AG-08** — Audit / Vault / evidence history is immutable and superseding.
- **AG-09** — PostgreSQL transactional outbox is the authoritative event source; NATS is transport.
- **AG-10** — Temporal orchestrates workflows but is never regulatory truth.
- **AG-11** — Cache/search/read models are rebuildable and non-authoritative.
- **AG-12** — Object evidence is hash-controlled and immutable/WORM-capable.
- **AG-13** — ERP/LIMS/Edge integrate through controlled APIs/events with reconciliation.
- **AG-14** — AI is advisory only.
- **AG-15** — No regulated behavior is guessed.

Full detail, forbidden patterns and negative tests: `.claude/rules/00-architecture-non-negotiables.md`
and `docs/generated/34_ARCHITECTURE_GUARDRAIL_MATRIX.md`.

## 3. The regulated mutation path (memorise this)

```text
Caller → authenticated context → policy (RBAC + qualification + SoD)
      → signature ceremony if the policy requires one
      → Mutation Gateway command (schema, expected_version, idempotency, reason)
      → owning domain service
      → ONE PostgreSQL transaction: domain state + record version + audit event + outbox event
      → receipt → outbox publisher → NATS → projections / integrations
```

Anything that writes regulated state outside this path is a defect, no matter how convenient.

## 4. SPEC_GAP rule

You may make ordinary engineering decisions. You may **not** invent anything that changes regulated
behaviour, record authority, signature requirements, authorization/SoD/qualification, audit or retention
semantics, quality/release decisions, calculation precision, contract compatibility, migration/data-loss
behaviour, security trust boundaries, validation acceptance or AI decision authority.

When such a decision is missing:

```text
DO NOT GUESS → append an entry to docs/generated/18_SPEC_GAPS.md
             → state affected requirements, risk, options, blocking yes/no
             → continue only on unaffected work
```

## 5. No fabricated evidence

Never invent a test run, a scan result, a coverage number, a qualification record or a signature.
Report what you actually executed and what actually happened. A failed test is evidence and stays.

## 6. Before you call any task complete

Run the checks and tests, then report:

1. requirement IDs implemented
2. functions created/changed
3. files changed
4. database migrations
5. API/event contract changes
6. dependency/licence changes
7. security impact
8. test cases executed — PASS / FAIL / BLOCKED counts plus the ids of every failure
9. validation/change impact
10. traceability and status files updated (include the `rollup.py` summary line)
11. unresolved SPEC_GAPs
12. known limitations

## 7. Work-package execution order

```text
WP-00 Repository, tooling & contract foundations
WP-01 GxP Core (mutation, signature, audit, vault, IAM, rules)
WP-02 Product / recipe / batch execution / eDHR
WP-03 Genealogy / review / release / packaging / yield
WP-04 Procurement / materials / QC
WP-05 QMS
WP-06 Equipment / sterile / edge
WP-07 Enterprise integrations
WP-08 DDCP profiles
WP-09 Postmarket
WP-10 Security          (continuous from WP-00)
WP-11 Data / infrastructure / DR / SRE  (continuous from WP-00)
WP-12 Validation platform & evidence    (continuous from WP-01)
WP-13 AI advisory capabilities
WP-14 Customer deployment / PQ / go-live
```

Each package has a folder in `work-packages/` and a self-contained prompt in
`work-packages/WP-XX/CLAUDE_CODE_PROMPT.md`. Per-document sub-prompts are in `prompts/`.

## 7b. Test cases, traceability and build status

Three things are updated on **every** task, not at the end of the project.

**Test cases.** `test-cases/` holds 9,150 pre-written executable cases — one book per module, indexed per
work package, plus the master `TEST_CASE_LIBRARY.csv`. Execute the cases that exist; do not invent a
parallel set. Record `status`, `executed_by`, `executed_at`, `actual_result` and `defect_reference` for
every case, and capture the named evidence. P1 cases are blocking. A failed case is evidence: never
delete it, re-run over it, or edit the expected result to make it pass.

**Traceability.** `traceability/TRACEABILITY_MASTER.csv` links capability → requirement → module →
function → contract → entity → test cases → evidence → qualification stage. Update the row for every
requirement you touch. A requirement with no test, or a test with no requirement, fails the gate.

**Build status.** `status/build-status.json` is the machine-readable state of every module and every
requirement; `status/STATUS_MODEL.md` defines the twelve stages and the gate to enter each. Set the stage
at the end of every task and run `python tooling/status/rollup.py` to regenerate `status/BUILD_STATUS.md`.

You may set stages up to `CODE_COMPLETE` and the test states, from real results only.
`REVIEWED`, `OQ_EXECUTED`, `QUALIFIED` and `RELEASED` are set by humans.

## 8. Where to look

| Need | File |
|---|---|
| What exists and who owns it | `docs/generated/00_PROJECT_OUTLINE.md` |
| Every requirement | `docs/generated/01_REQUIREMENT_REGISTRY.csv` |
| Function contracts | `docs/generated/03_FUNCTION_CATALOGUE.csv` |
| Schemas and ownership | `docs/generated/04_DATA_MODEL_CATALOGUE.md`, `05_DATABASE_OWNERSHIP_MATRIX.md` |
| APIs / events | `docs/generated/06_API_CATALOGUE.yaml`, `07_EVENT_CATALOGUE.yaml` |
| Signature requirements | `specs/Documents_106_115/Document_106...` + `docs/generated/11_SIGNATURE_POLICY_MAP.md` |
| Risk class → test depth | `docs/generated/28_INTENDED_USE_GXP_RISK_MATRIX.md` |
| Open gaps | `docs/generated/18_SPEC_GAPS.md` |
| Test cases for a module | `test-cases/WP-XX/Document_NN_*_TEST_CASES.md` |
| Test execution rules | `test-cases/TEST_CASE_STANDARD.md` |
| Traceability chain | `traceability/TRACEABILITY_MASTER.csv`, `traceability/TRACEABILITY_MODEL.md` |
| What is built and how far | `status/BUILD_STATUS.md`, `status/STATUS_MODEL.md` |

## 9. Hard prohibitions

- No Frappe/ERPNext core fork or edit.
- No `frappe.db.set_value()` (or equivalent) on regulated data.
- No generic CRUD or `PATCH /regulated-record/{id}` style endpoint.
- No UPDATE/DELETE on audit, signature, vault or evidence rows.
- No publishing to the bus without a committed outbox row.
- No binary float for a regulated quantity.
- No regulated decision read from a cache, projection, search index or report.
- No AI authority to sign, release, disposition, approve, alter audit or submit a report.
- No dependency added without the Document 104 justification.
- No production database fix outside a controlled migration/repair mechanism.
