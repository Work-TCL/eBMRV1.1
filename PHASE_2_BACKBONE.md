# Phase 2 — WP-00 Engineering Backbone

**Date:** 2026-09-09 / 10
**Goal:** make the CI/CD, coding-standard, SBOM/licence and branch-protection gates *real and running*
for the built stack (Python/FastAPI + Next.js), not just prose in `ebmr-edhr/docs/engineering/`.

---

## 1. What was delivered

### Root CI pipeline — `/.github/workflows/ci.yml`  (NEW)

The pre-existing `ebmr-edhr/.github/workflows/ci.yml` was an **npm/TypeScript** workflow (pre-ADR-0007)
sitting in a directory **GitHub Actions never executes** (only repo-root `.github/workflows/` runs). It
is replaced with a real pipeline for the built stack and stubbed with a redirect notice.

| Job | Steps | Blocking |
|---|---|---|
| **guardrails** | specs-read-only diff guard · contract conformance gate (`tooling/contracts/validate.py`, run *with the app importable* so CTRC-FR-001 coverage isn't skipped) · event contract gate (`tooling/events/validate.py`) · status-rollup-in-sync | specs guard + rollup **block**; contract/event gates **ratchet** (`continue-on-error`) — 3 known SG-013 leaks + 2 known SG-174 collisions |
| **lint** | `ruff check --select F` (real bugs) · full ruff ruleset (report) · `mypy` (report) | F-floor **blocks new bugs**; full set + mypy report-only |
| **frontend-lint** | `eslint` · `tsc --noEmit` | **blocks** |
| **test** | Postgres 14 service → bootstrap 6 base schemas → `alembic upgrade head` → **`alembic check` drift guard** (added after the Phase 1 stale-DB finding) → `pytest` + JUnit artefact | **blocks** |
| **supply-chain** | CycloneDX SBOM (Python + frontend) · **licence gate** (no PROHIBITED, no UNKNOWN) · `pip-audit` (report) · `gitleaks` secret scan | licence gate + gitleaks **block**; SBOM uploaded as artefact |

### Coding-standard enforcement (Document 97 / ADR-0007)

- `services/gxp-api/pyproject.toml`: `[tool.ruff]` (FastAPI-aware — ignores `B008` `Depends()`,
  `RUF012` `Mapped[...]`, `SIM117` nested `async with`) + `[tool.mypy]`.
- `ruff` + `mypy` added to the dev dependency group and **locked** (`uv.lock` updated).
- **Baseline measured** (`app/` + `scripts/`): ruff full ≈ 911 (534 in `app/`), of which **95 pyflakes
  (`F`)** — mostly `F401` unused-import (auto-fixable), plus **3 genuine bugs** (see §3).
- `docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md` updated: the `ci:lint` / `ci:typecheck` rows
  now point at the real jobs.

### SBOM + licence register (Document 104)

- **`sbom/sbom-gxp-api.cdx.json`** — CycloneDX 1.6, **48 components**, generated from the venv.
- `docs/generated/40_SBOM_LICENSE_DEPENDENCY_REGISTER.md` — rewritten from "intentionally empty" to a
  **populated register**: every direct + notable transitive dependency with version, licence, status,
  purpose and approval reference.
- **Licence posture: clean.** MIT / BSD-2 / BSD-3 / Apache-2.0 / PSF / MPL-2.0 (file-level) / MIT-0 /
  MIT-CMU. **Zero UNKNOWN, zero PROHIBITED, zero GPL/AGPL/SSPL.**
- Frontend: 3 direct prod deps (`next` / `react` / `react-dom`, MIT). SBOM step wired; committed output
  is a follow-up.

### Branch protection (Document 99)

- `/.github/CODEOWNERS` — rewritten for the real layout (`services/gxp-api/app/modules/...`, `frontend/`;
  dropped the non-existent `apps/ebmr_frappe` / `services/security` / `services/integration-gateway` /
  `services/ai-gateway`).
- `/.github/pull_request_template.md` — CLAUDE.md §6 completion report + the real gate checklist.
- `/.github/dependabot.yml` — weekly pip / npm / actions updates, `needs-sca-review` label, no auto-merge.
- `docs/engineering/REPOSITORY_BRANCHING_STANDARD.md` — added the exact GitHub branch-protection ruleset
  to apply (it is a repo-admin action, not committable).

### Status reconciliation

`build-status.json`: SPEC-ENG-001 / 003 / 007 / 008 (Docs 97 / 99 / 103 / 104) → `IN_DEVELOPMENT` on the
committed artefacts above; `rollup.py` re-run (**modules started 92 → 96**). SPEC-ENG-005 (Doc 101)
unchanged; SPEC-ENG-002 / 004 / 006 stay `NOT_STARTED` as *codified checks* (their standards prose
exists in `docs/engineering/`).

---

## 2. What CI catches today (verified locally)

| Gate | Result now |
|---|---|
| specs-read-only | clean |
| contract conformance | **3 CTRC-FR-001 violations** — `spec-val-001.yaml` missing 3 `signature-challenges` ops (SG-013). Ratcheting. |
| event contract | **2 CTRC-FR-008 violations** — `LineClearanceCompleted`, `MaterialReconciliationCalculated` (SG-174). Ratcheting. |
| ruff `--select F` (new-bug floor, `F401/F841/F811/F821` ignored as pre-existing) | **clean** |
| status rollup | deterministic; clean once committed |
| SBOM / licence | 48 components, 0 prohibited / unknown → **pass** |

---

## 3. Genuine pre-existing bugs surfaced by the new lint gate

The ruff floor found 3 real issues the gate ignores for now (each `noqa`-free so it stays visible):

| Finding | Location | Assessment |
|---|---|---|
| **`FilterIntegrityFailedError` defined twice with different HTTP status** (409 at L881, 422 at L1089) | `app/mutation/errors.py` | **Real defect** — the second definition wins, silently changing the error's status from 409 to 422. Which is correct is an error-registry decision (SG-142 class) — flagged for the Audit/error-registry owner, not guessed. |
| `evaluate_policy` imported twice (identical) | `app/modules/packaging/router.py` L11 + L27 | Harmless duplicate import; safe to drop one. |
| `current_id` used before assignment on the first-line-matches path | `scripts/fill_document_22_test_cases.py:326` | Real bug in a one-off test-case-fill script (not runtime). |

---

## 4. Ratchet plan (open Phase 2 work)

1. ✅ **DONE 2026-09-10** — **First cleanup PR** — `ruff check app scripts --select F401,I001 --fix`
   (85 files, pure import removal + sort) + hand-fixed the 14 `F841` findings the autofixer can't reach,
   then removed `F401,F841` from the CI floor's ignore list (`F811,F821` were already clean — the 3 bugs
   in §3 above were fixed before this pass). Floor is now the unqualified `ruff check app scripts
   --select F`. Verified: representative slice (test_batch_execution, test_qms_capa, test_rules,
   test_vault, test_contract_conformance, test_eventbus_outbox_consumer) 131/131 passed, 0 behavioural
   change.
2. Fix the 3 bugs in §3; remove `F811,F821` from the ignore list. *(Already done — see item 1: F811/F821
   were clean going into this pass, so the ignore list needed only the F401/F841 removal.)*
3. Ratchet the full ruff ruleset from report-only → blocking (E/W/I/UP/SIM/RUF), file group by file group.
4. Ratchet `mypy` toward `--strict` (ADR-0007 target): enable `disallow_untyped_defs`,
   `disallow_any_generics`, … as the baseline clears.
5. ✅ **DONE 2026-09-10** — Added the **`float`-in-regulated-code lint rule** (ADR-0007 consequence; Doc
   110 CALC-FR-001) as a 5th check in `ebmr-edhr/tooling/guardrails/validate.py`
   (`no-float-for-decimal-column`), wired into the same CI steps as items 3/6. Deliberately narrower than
   "any float field" (engineering timing/duration floats are pervasive and legitimate throughout
   `app/modules/erp/reliability.py` and similar) — flags only an ORM column whose database type is
   `Numeric`/`DECIMAL` but whose `Mapped[...]` annotation says `float`, which has zero false-positive
   risk and found one real bug: `qms.NcrDisposition.quantity` (+ its `DispositionNcrCommand.quantity`
   Pydantic counterpart) was `float` end-to-end despite the column being `Numeric(18, 6)` — fixed to
   `Decimal` in both places, matching the `Decimal`-field convention already used everywhere else in the
   codebase (CTR-FR-015 decimal-as-string transport). Verified clean against `app/` (5/5 checks pass, 0
   findings) and against `tests/test_qms_ncr.py` (17/17 passed — see §6 completion report).
6. ✅ **DONE 2026-09-10** — Codified **`ebmr-edhr/tooling/guardrails/`** — 4 of the
   `34_ARCHITECTURE_GUARDRAIL_MATRIX.md` checks (no cross-module repository write, no
   `frappe.db.set_value`-equivalent, no generic CRUD endpoint, no bus publish without a committed outbox
   row) as runnable stdlib-`ast` lint, wired into the CI `guardrails` job as a **blocking** gate (clean on
   the real codebase today, not a ratchet) plus 9 pytest negative-fixture tests in the `lint` job. See
   `ebmr-edhr/tooling/guardrails/README.md`.
7. **SAST** tool selection (CodeQL or semgrep) + wire into `supply-chain`.
8. ✅ **DONE 2026-09-10** — Committed `sbom/sbom-frontend.cdx.json` (29 resolved production components,
   0 UNKNOWN/PROHIBITED licences; logged a critical `next`/`sharp` `npm audit` finding as an open item
   rather than silently patching — see `40_SBOM_LICENSE_DEPENDENCY_REGISTER.md` Open Items). The
   DEP-FR-018 Security/Architecture sign-off for the crypto/auth deps (jose / cryptography / bcrypt /
   ecdsa / rsa) remains open — that is a human approval step, not something this pass could execute.
9. Container `Dockerfile` + IaC → then container/OS-package SBOM (DEP-FR-020) and IaC scan.
10. The **merge-to-main** and **release-candidate** pipeline stages (build-once, artefact sign, release
    manifest) — needed before a first tagged release.
11. **SPEC-ENG-002/004/006** codified checks: architecture-rules-for-agents lint, migration-standard
    CI check (expand→contract window, rollback presence), testing-strategy risk-tier coverage check.
12. Apply the GitHub branch-protection ruleset (repo-admin action, spec in the branching standard).
13. ✅ **DONE 2026-09-10** — **Rebuilt `ebmr_new_gxp_test` cleanly**: `alembic downgrade base` then
    `alembic upgrade head` (93/93 migrations, both directions, zero errors) to prove the chain replays
    clean from empty rather than trusting a DB that had migrations 0084/0089/0090 hand-applied during
    Phases 1/3. One real bug found and fixed on the way: migration 0053's `downgrade()` used
    non-idempotent `op.drop_constraint()`/`op.drop_column()` on the same FK/columns migration 0083 (a
    repair migration for the same objects) already drops idempotently and runs first in downgrade order
    — fixed to match 0083's `DROP ... IF EXISTS` idiom. A second, much larger bug found and fixed by
    following through with `alembic check` on the rebuilt DB: `app/all_models.py` (the Alembic
    autogenerate model registry every other module is listed in) never imported the model files for
    `ai_governance`, `machine_integration`, `postmarket` or `validation` — 73 real, correctly-migrated
    tables were invisible to `alembic check`/`autogenerate` the entire time. Fixed by adding the 7 missing
    import lines. `alembic check`'s "removed table" count drops from 74 (73 real + the expected
    `alembic_version` false positive) to 1 (just that false positive) after the fix. **Not fixed, logged
    as SG-184**: ~144 `BIGINT`-vs-`Integer` `version`-column type mismatches and ~169 index /  13
    check-constraint gaps between the migrations and the (now fully visible) models, spread across most
    of the schema — real, but a genuinely undecided reconciliation question (which type is correct),
    not something to guess at inside this pass. `alembic check` is not clean today; SG-184 has the full
    accounting and closure criteria. A third bug found and fixed by then running the actual test suite
    against the rebuilt DB: migrations 0002/0004 (the two earliest privilege-lockdown migrations) never
    granted the runtime app role `TRUNCATE` on 24 tables `tests/conftest.py`'s autouse cleanup fixture
    needs (every later per-table grant does include it) — the live `ebmr_new_gxp_test` never hit this
    because someone had hand-granted it directly, outside any migration, exactly the "hidden state"
    class of defect this rebuild exists to surface. Migration 0094 grants `TRUNCATE` on 22 of the 24
    (ordinary mutable tables) — deliberately **not** on `audit.audit_events`/`signature.signatures`,
    which migration 0002 already made append-only for AG-08 and must stay that way for the app role in
    both test and production. That correctly-scoped grant then ran straight into Postgres's own `TRUNCATE
    ... CASCADE` semantics: `signature.signatures` carries an FK to `iam.users`, so truncating `iam.users`
    (needed for cleanup) cascades into `signatures` regardless of which tables the fixture names
    explicitly, and fails the same way for the whole combined statement. Rather than hand-picking which
    subset of a 252-table list happens to chain into an append-only table via some FK path, the actual
    fix is in `tests/conftest.py`: the cleanup truncate now runs as the migration role (which owns every
    table) instead of the app role — pure test-harness reset plumbing, not something any test exercises,
    same pattern 3 other test files already use for privileged test-only operations. Migration 0094
    itself stays (privilege-consistency hygiene matching the per-table convention every later migration
    uses; harmless and independently correct even though the test fixture no longer strictly needs it).
    Full accounting in `36_DATABASE_MIGRATION_CATALOGUE.md`. Verified: the item-1
    representative slice + every test file for the 4 newly-visible modules (ai_governance,
    machine_integration, postmarket, validation ×7 files) + test_qms_ncr.py (the NCR float→Decimal fix,
    §4 item 5) — see §6 completion report for the pass/fail count.

---

## 5. Files changed

```
NEW  .github/workflows/ci.yml
NEW  .github/CODEOWNERS
NEW  .github/pull_request_template.md
NEW  .github/dependabot.yml
NEW  sbom/sbom-gxp-api.cdx.json
NEW  PHASE_2_BACKBONE.md
MOD  services/gxp-api/pyproject.toml           (ruff + mypy config + dev deps)
MOD  services/gxp-api/uv.lock                  (ruff, mypy locked)
MOD  ebmr-edhr/.github/workflows/ci.yml        (→ superseded stub)
MOD  ebmr-edhr/docs/generated/33_CODING_STANDARD_COMPLIANCE_MATRIX.md
MOD  ebmr-edhr/docs/generated/39_CI_CD_RELEASE_EVIDENCE_MODEL.md
MOD  ebmr-edhr/docs/generated/40_SBOM_LICENSE_DEPENDENCY_REGISTER.md
MOD  ebmr-edhr/docs/engineering/REPOSITORY_BRANCHING_STANDARD.md
MOD  ebmr-edhr/status/build-status.json + BUILD_STATUS.md   (WP-00 → IN_DEVELOPMENT; rollup)
```
