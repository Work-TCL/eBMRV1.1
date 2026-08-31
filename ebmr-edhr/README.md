# eBMR / eDHR Claude Code Construction Package

**Version:** 1.0 — Proposed implementation-ready construction package / Ready for Review
**Specification baseline:** Documents 01–105 (2026-08-20) plus approved Documents 106–115 (2026-08-21)
**Purpose:** turn the controlled 105-document specification set into something Claude Code can execute
with minimal interpretation, without inventing regulated behaviour.

This repository is the **construction system**. It does not contain product code yet. Claude Code writes
the product code by executing the prompts in `prompts/` and the work packages in `work-packages/`.

---

## 1. What is in here

```text
ebmr-edhr/
├── START_HERE.md                  Phase 1 execution guide — read this first
├── CLAUDE.md                      project-wide contract for the coding agent
├── README.md                      this file
├── PACKAGE_MANIFEST.md / .json    every file with size and SHA-256
│
├── .claude/
│   ├── rules/                     11 modular rule files the agent must obey
│   └── settings.example.json      permissions: specs/ read-only, rules/ read-only
│
├── .github/                       CODEOWNERS, PR template with the mandatory completion report, CI gates
│
├── specs/                         ← YOU place the controlled baseline here (see §2)
│
├── docs/
│   ├── generated/                 43 Phase-0 artefacts compiled from the baseline
│   ├── adr/                       4 construction ADRs
│   ├── engineering/               9 working engineering standards (Docs 97–105)
│   ├── runbooks/                  (populated during implementation)
│   └── validation/                (populated during implementation)
│
├── gap-resolution/
│   ├── 18_SPEC_GAPS.md            the 20 gaps found in the baseline
│   ├── SPEC_GAP_RESOLUTION_INDEX.md
│   ├── addenda/                   Documents 106–115 (APPROVED) that close every gap
│   └── patches/                   7 exact patches to Documents 05, 69, 71, 73, 75, 91, 104
│
├── test-cases/                    9,150 executable test cases — one book per module
│   ├── TEST_CASE_LIBRARY.csv      master record: status, executor, result, evidence, defect
│   ├── TEST_CASE_STANDARD.md      execution rules the developer team follows
│   └── WP-XX/                     per-work-package index + per-document test case books
│
├── traceability/
│   ├── TRACEABILITY_MASTER.csv    capability → requirement → module → contract → test → evidence
│   ├── TRACEABILITY_MODEL.md      the chain, the gates, how to maintain it
│   ├── COVERAGE_REPORT.md         gaps in the chain
│   └── WP-XX_TRACEABILITY.md      per-work-package working view
│
├── status/
│   ├── STATUS_MODEL.md            12 build stages and the gate to enter each
│   ├── build-status.json          machine-readable state of every module and requirement
│   └── BUILD_STATUS.md            generated dashboard
│
├── tooling/status/rollup.py       regenerates the dashboard from real test results
│
├── prompts/                       122 dependency-ordered Claude Code prompts
├── work-packages/                 WP-00 … WP-14, 15 files each
└── (services/, apps/, contracts/, edge/, packages/, infrastructure/, validation/, tests/, tooling/)
                                   created by prompt 01
```

## 2. Set-up (once, before running anything)

1. **Place the controlled baseline.** Copy Documents 01–105, the Master Index, the Specification Authoring
   Standard and the Construction Instructions into `specs/` exactly as described in `specs/README.md`.
2. **Copy the approved gap resolutions.** Move `gap-resolution/addenda/Document_106…115_*_APPROVED.md`
   into `specs/Documents_106_115/`. These are now part of the controlled baseline.
3. **Apply the seven document patches** in `gap-resolution/patches/DOCUMENT_PATCH_LIST.md` through your
   normal document change control (two requirement re-namespaces, four event-ownership notes, one
   acceptance section added to Document 05).
4. **Regenerate traceability** after the patches: requirement registry, test traceability and validation
   traceability all reference the changed identifiers.
5. **Capture the QMS signature records** against Documents 106–115. They are approved as the construction
   baseline; formal Part 11 signature records belong in your QMS before validated release.
6. **Copy `.claude/settings.example.json` to `.claude/settings.json`** and adjust for your environment.
   The default denies edits to `specs/`, `CLAUDE.md` and `.claude/rules/`.

## 3. How to run it with Claude Code

Open the repository in Claude Code and run the prompts **in order**. Each prompt is self-contained: it
names its source documents, requirement IDs, target files, functions, contracts, tests, acceptance
criteria and the completion report it must produce.

```text
1.  prompts/00_BOOTSTRAP_PHASE0.md         verify the baseline and the Phase-0 artefacts (no coding)
2.  prompts/01_REPOSITORY_FOUNDATION.md    skeleton, guardrails, contract tooling, CI gates
3.  work-packages/WP-00/CLAUDE_CODE_PROMPT.md   repository, tooling & contract foundations
4.  work-packages/WP-01/CLAUDE_CODE_PROMPT.md   GxP Core (mutation, signature, audit, vault, IAM, rules)
5.  work-packages/WP-02/…                       product / recipe / batch / eDHR
6.  work-packages/WP-03/…                       genealogy / review / release / packaging / yield
7.  work-packages/WP-04/…                       procurement / materials / QC
8.  work-packages/WP-05/…                       QMS
9.  work-packages/WP-06/…                       equipment / sterile / edge
10. work-packages/WP-07/…                       enterprise integrations
11. work-packages/WP-08/…                       DDCP profiles
12. work-packages/WP-09/…                       postmarket
13. work-packages/WP-10/…                       security          (start early, run continuously)
14. work-packages/WP-11/…                       data / infrastructure / DR / SRE  (continuous)
15. work-packages/WP-12/…                       validation platform & evidence    (continuous)
16. work-packages/WP-13/…                       AI advisory capabilities
17. work-packages/WP-14/…                       customer deployment / PQ / go-live
```

Each work-package prompt delegates to its per-document sub-prompts in `prompts/WP-XX/`. If a work-package
prompt is too large for one reliable session, run the sub-prompts individually — they are designed to be
executed and reviewed one document at a time.

**Start WP-10, WP-11 and WP-12 alongside WP-01, not after WP-09.** Security, data architecture and
validation are continuous concerns; they are numbered as packages so their deliverables have owners, not
so they can be deferred.

## 4. Working rhythm per prompt

```text
read the prompt → read its source documents in specs/ → plan → write contracts → write code
→ execute the module's test case book → record every result and its evidence
→ update traceability/TRACEABILITY_MASTER.csv and status/build-status.json
→ run tooling/status/rollup.py → deliver the 12-point completion report
```

Review each completion report before starting the next prompt. The report is where you catch a fabricated
test claim, a missed requirement or an architecture drift while it is still cheap to fix.

### Test cases

The developer team does not write test cases from scratch. `test-cases/` already contains **9,150
executable cases** derived from the specifications:

| Type | Cases | Why they exist |
|---|---|---|
| positive | 2,965 | one per requirement — the required behaviour |
| negative | 2,674 | the control observed refusing |
| scenario | 1,208 | every scenario the specifications themselves declare |
| failure | 783 | dependency outage, rollback, timeout, offline |
| security | 568 | authn, authz, cross-tenant, immutability, AI authority |
| concurrency | 477 | stale version, simultaneous writers |
| idempotency | 206 | duplicate click, retried callback |
| boundary | 166 | limit and rounding-stage behaviour |
| integrity | 103 | audit and outbox companion proof |

Each case carries preconditions, test data, numbered steps, expected result, expected error code, evidence
to capture, automation level and qualification stage. Results go back into
`test-cases/TEST_CASE_LIBRARY.csv`, which feeds traceability and the status dashboard automatically.

### Knowing what is built

`status/BUILD_STATUS.md` answers *"what is built and how far"* at three levels: work package, module and
individual requirement. Twelve stages, no skipping:

```text
NOT_STARTED → CONTRACTS_DRAFTED → SCHEMA_READY → IN_DEVELOPMENT → CODE_COMPLETE
→ UNIT_TESTED → INTEGRATION_TESTED → NEGATIVE_TESTED → REVIEWED
→ OQ_EXECUTED → QUALIFIED → RELEASED
```

Claude Code may advance a module only to `CODE_COMPLETE` and the test states, and only from real recorded
results. `REVIEWED`, `OQ_EXECUTED`, `QUALIFIED` and `RELEASED` are human decisions — an agent can never
mark its own work qualified.

## 5. The rules that matter most

The agent has these in `CLAUDE.md` and `.claude/rules/`, but you should know them too, because they are
what you are checking for in review:

- Regulated writes only through the Mutation Gateway, in one PostgreSQL transaction with the audit event
  and outbox row.
- PostgreSQL is authoritative; Frappe/MariaDB holds read-only projections; one owner per entity.
- Login/MFA is never a signature; signature requirements come from the approved Document 106 policy data,
  never from code conditionals.
- Audit, vault and evidence are append-only. Corrections supersede; nothing is edited in place.
- No binary floating point for a regulated quantity.
- AI advises; a qualified human decides and signs.
- **Never guess regulated behaviour** — raise a SPEC_GAP in `docs/generated/18_SPEC_GAPS.md`.
- **Never fabricate evidence** — no invented test runs, scan results or qualification records.

## 6. What was found in the baseline, and what was done about it

Twenty gaps were found across Documents 01–105. Nine were blocking. None was resolved by guessing; each
became a numbered gap with analysis, options and a resolution document.

| Gap class | Count | Resolution |
|---|---|---|
| Editorial / engineering (E) | 12 | Documents 112–115 and seven document patches |
| Design decision (D) | 2 | Documents 109, 113 (recorded as decisions with rationale) |
| Regulated decision (R) | 6 | Documents 106, 107, 108, 109, 110, 111 — approved baselines with approval blocks |

Highlights worth your attention:

- **SG-004** — no document defined *which* action requires a signature, with what meaning, by whom.
  Document 106 now registers **171 signature points** (109 Part 11 critical) with a platform floor a
  customer may tighten but never weaken.
- **SG-009** — the SoD engine was specified but shipped with no rules. Document 107 defines 20 prohibited
  role pairs and 20 action-independence rules.
- **SG-010** — no module had a GxP risk classification, so the validation programme had no basis.
  Document 111 classifies all 105 modules by a mechanical, re-runnable rule; 102 are higher-process-risk.
- **SG-001/002** — `DRV-FR` was used by two documents and `DEP-FR` by two others. Requirement IDs must
  resolve to exactly one requirement or traceability is unprovable. Patches P-01 and P-02 fix this.
- **SG-013** — 497 operations and 484 events were declared by name with almost no field-level schemas.
  Document 113 makes contract-first mandatory per work package, with canonical envelopes.

## 7. Regeneration

Everything in `docs/generated/` is compiled from `specs/`. If a specification changes, regenerate rather
than hand-editing, then review the diff. Hand-edited artefacts drift from the baseline and quietly break
traceability.

## 8. Status

This package is **Ready for Review**, not frozen. Freeze it only after you have reviewed the Phase-0
artefacts and the approved Documents 106–115, and after the seven patches are applied through change
control.

**First file to put in the Claude Code repository root:** `CLAUDE.md`.
**First prompt to run:** `prompts/00_BOOTSTRAP_PHASE0.md`.
**First thing to check every morning:** `status/BUILD_STATUS.md`.
**Step-by-step Phase 1 instructions, with checks and remediation:** `START_HERE.md`.
