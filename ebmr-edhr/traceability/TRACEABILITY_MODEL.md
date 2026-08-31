# Traceability Model

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** How every level of the platform is linked, from frozen capability to executed test evidence.

---

## Chain

```text
Document 01 capability (C-nnn, MAT-nnn, PH-nnn, ST-nnn, CP-nnn, QMS-nnn, MD-nnn, PM-nnn)
  → requirement (Documents 03–115, e.g. MUT-FR-009)
    → module (SPEC-GXP-001) → code location (services/gxp-api/src/modules/mutation)
      → function / service contract (docs/generated/03_FUNCTION_CATALOGUE.csv)
        → API operation and event contract (contracts/)
          → data entity and migration (docs/generated/04, 36)
            → test cases (test-cases/TEST_CASE_LIBRARY.csv)
              → executed evidence (validation/evidence/<stage>/<module>/<test_case_id>/)
                → qualification stage (IQ/OQ/PQ) → VSR (Document 95)
```

Every link is a column in `TRACEABILITY_MASTER.csv`, so the chain is queryable in both directions:
*"which tests prove MUT-FR-009?"* and *"which requirement does TC-003-009-02 prove?"*

## Files

| File | Purpose |
|---|---|
| `traceability/TRACEABILITY_MASTER.csv` | the full chain, one row per requirement |
| `traceability/WP-XX_TRACEABILITY.md` | per-work-package view for daily use |
| `traceability/COVERAGE_REPORT.md` | gaps in the chain (requirement without tests, test without requirement) |
| `docs/generated/42_CAPABILITY_COVERAGE_MATRIX.csv` | Document 01 capability coverage |
| `docs/generated/29_VALIDATION_TRACEABILITY_MASTER.csv` | validation-facing view |
| `status/build-status.json` | machine-readable build state, updated by every completed prompt |

## Gates

1. **No requirement without a test case.** Fails the traceability CI job.
2. **No test case without a requirement.** Orphan tests are deleted or given a requirement.
3. **No code without a requirement reference.** Every command handler names its requirement IDs in a
   header comment and in its contract's `x-requirement-ids`.
4. **No requirement marked VERIFIED without executed evidence.** Verification state is set from real test
   results, never by hand.
5. **No module marked QUALIFIED without its OQ evidence** and its open defects dispositioned.

## Maintaining it

The matrices are generated from `specs/` plus the test library. When a specification changes, regenerate
and review the diff. When a test executes, the result flows from the test library into the master matrix
and the status roll-up. Never hand-edit a generated matrix to make a gate pass — that breaks the only
audit trail that shows what was actually proven.
