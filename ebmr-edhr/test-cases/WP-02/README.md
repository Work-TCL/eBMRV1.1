# WP-02 — Test Case Index

**Scope:** Product & constituent master, master recipe/MMR, batch execution state machine, eDHR.  
**Total test cases:** 476  
**P1 (must pass before the work package can close):** 476

| Document | Module | Risk | Test cases | Test case book |
|---|---|---|---|---|
| 09 | SPEC-EBMR-000 | HIGHER-PROCESS-RISK | 121 | `test-cases/WP-02/Document_09_SPEC-EBMR-000_TEST_CASES.md` |
| 10 | SPEC-EBMR-001 | HIGHER-PROCESS-RISK | 115 | `test-cases/WP-02/Document_10_SPEC-EBMR-001_TEST_CASES.md` |
| 11 | SPEC-EBMR-002 | HIGHER-PROCESS-RISK | 131 | `test-cases/WP-02/Document_11_SPEC-EBMR-002_TEST_CASES.md` |
| 12 | SPEC-EBMR-003 | HIGHER-PROCESS-RISK | 109 | `test-cases/WP-02/Document_12_SPEC-EBMR-003_TEST_CASES.md` |

## Exit rule

The work package cannot close until every P1 case is PASS, every FAIL has a defect reference with a disposition, and every BLOCKED case has a recorded blocker and owner. Record results in `test-cases/TEST_CASE_LIBRARY.csv` (or your test management tool synced from it) and update `status/build-status.json`.
