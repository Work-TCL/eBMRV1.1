# 39 — CI/CD & Release Evidence Model

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Pipeline stages, gates and evidence produced at each step (Document 103/68/104/95).

---

```text
PR
 ├ lint / typecheck / unit
 ├ contract schema lint + compatibility check
 ├ architecture guardrail checks (34_ARCHITECTURE_GUARDRAIL_MATRIX.md)
 ├ migration safety check
 ├ SAST / secret scan / dependency (SCA) / licence check
 ├ requirement-ID uniqueness + single-producer checks (Doc 115)
 └ traceability update check (requirement ↔ test)
merge to main
 ├ integration + E2E
 ├ container build (build once)
 ├ SBOM generation
 ├ IaC + container scan
 └ artefact signing
release candidate
 ├ full engineering test suite
 ├ performance smoke against SLO classes
 ├ migration matrix execution on a restored copy
 ├ validation impact assessment
 └ release manifest (artefact hashes, SBOM, contracts, migrations, requirements)
validated release authorization (Doc 95)
 ├ qualification evidence complete (IQ/OQ/PQ as applicable)
 ├ open validation exceptions assessed (Doc 94)
 └ signed authorization
deployment
 ├ environment fingerprint verification
 ├ post-deployment checks
 └ rollback plan verified
```

| Gate | Blocking condition | Evidence produced |
|---|---|---|
| PR gate | any lint/type/unit/guardrail/contract failure | CI run record + logs |
| Security gate | critical SAST/SCA/secret/IaC finding | scan reports |
| Licence gate | unknown or prohibited licence (Doc 104) | SBOM + licence report |
| Migration gate | unsafe lock or missing rollback | migration plan + dry-run result |
| Contract gate | breaking change without version bump | compatibility diff |
| Traceability gate | requirement without a test or test without a requirement | traceability delta |
| Release gate | missing qualification evidence or unresolved blocking exception | release manifest |
| Deployment gate | fingerprint mismatch with the authorized release | deployment record |

**Rule:** production cannot deploy an unvalidated or fingerprint-mismatched regulated configuration. Never fabricate a test run, scan result or validation record.

---

## Implementation status — Phase 2 (2026-09-09)

The pre-ADR-0007 workflow (`ebmr-edhr/.github/workflows/ci.yml`, npm-only, wrong directory to ever run)
is superseded by **`/.github/workflows/ci.yml`** at the repository root, wired to the built stack
(Python/FastAPI GxP Core + Next.js UI).

| Model gate | CI job / step | Blocking? | Notes |
|---|---|---|---|
| Specs read-only | `guardrails` → *Specs are read-only* | **yes** | diff-based; fails on any `specs/` change |
| Contract lint + compatibility | `guardrails` → *Contract conformance gate* | **yes (blocking, 2026-09-10)** | `tooling/contracts/validate.py --baseline contracts/openapi/.conformance-baseline`, run with the app importable so CTRC-FR-001 coverage is not skipped. M1 (WP-01..04) + WP-12 fully contracted; 17 non-M1 residuals (WP-06/07/08) are an agreed baseline — a NEW uncontracted operation fails, a baselined one doesn't, a stale baseline line fails |
| Single event producer / closed payloads | `guardrails` → *Event contract gate* | **yes** | `tooling/events/validate.py` — currently reports 2 known violations (**SG-174** name collisions) |
| Traceability / status in sync | `guardrails` → *Status rollup is in sync* | **yes** | `rollup.py` then `git diff --exit-code BUILD_STATUS.md` |
| lint / typecheck | `lint` (`ruff --select F` **blocking**; full ruff + `mypy` report-only) · `frontend-lint` (`eslint` + `tsc --noEmit`) | partial | ratchet plan in `PHASE_2_BACKBONE.md` — F-codes block now, the rest blocks after the baseline is cleared |
| unit / integration tests | `test` — Postgres 14 service, `alembic upgrade head`, `alembic check` drift guard, `pytest` + JUnit artefact | **yes** | drift guard added after the Phase 1 stale-test-DB finding |
| SCA / licence | `supply-chain` → *Licence gate* (**blocking**: no PROHIBITED, no UNKNOWN) + `pip-audit` (report-only until a triage owner is named) | partial | |
| SBOM generation | `supply-chain` → *SBOM Python / frontend* (CycloneDX) → uploaded artefact; Python SBOM also committed at `sbom/sbom-gxp-api.cdx.json` | **yes** | |
| Secret scan | `supply-chain` → `gitleaks` | **yes** | repo-level push protection also on |
| SAST | — | **not yet** | tool selection (CodeQL / semgrep) is an open Phase 2 item |
| IaC / container scan | — | **not yet** | no Dockerfile / IaC in the tree yet |
| Architecture guardrails (`34_`) | — | **not yet** | `tooling/guardrails/` does not exist; the checks are described in `34_` but not codified |
| Build once / artefact signing / release manifest | — | **not yet** | belongs to the release-candidate stage; no tagged release yet |

**Not yet implemented (tracked in `PHASE_2_BACKBONE.md`):** SAST tool, architecture-guardrail codification,
container/IaC scan, artefact build+sign+manifest, the merge-to-main and release-candidate stages, and the
GitHub branch-protection ruleset itself (a repo-admin action — spec'd in
`docs/engineering/REPOSITORY_BRANCHING_STANDARD.md`).
