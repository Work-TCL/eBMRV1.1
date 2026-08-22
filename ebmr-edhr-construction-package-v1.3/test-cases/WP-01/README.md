# WP-01 — Test Case Index

**Scope:** The regulated kernel: every later module depends on these six services.  
**Total test cases:** 811  
**P1 (must pass before the work package can close):** 811

| Document | Module | Risk | Test cases | Test case book |
|---|---|---|---|---|
| 03 | SPEC-GXP-001 | HIGHER-PROCESS-RISK | 135 | `test-cases/WP-01/Document_03_SPEC-GXP-001_TEST_CASES.md` |
| 04 | SPEC-GXP-002 | HIGHER-PROCESS-RISK | 145 | `test-cases/WP-01/Document_04_SPEC-GXP-002_TEST_CASES.md` |
| 05 | SPEC-GXP-003 | HIGHER-PROCESS-RISK | 132 | `test-cases/WP-01/Document_05_SPEC-GXP-003_TEST_CASES.md` |
| 06 | SPEC-GXP-004 | HIGHER-PROCESS-RISK | 147 | `test-cases/WP-01/Document_06_SPEC-GXP-004_TEST_CASES.md` |
| 07 | SPEC-IAM-001 | HIGHER-PROCESS-RISK | 118 | `test-cases/WP-01/Document_07_SPEC-IAM-001_TEST_CASES.md` |
| 08 | SPEC-GXP-006 | HIGHER-PROCESS-RISK | 134 | `test-cases/WP-01/Document_08_SPEC-GXP-006_TEST_CASES.md` |

## Exit rule

The work package cannot close until every P1 case is PASS, every FAIL has a defect reference with a disposition, and every BLOCKED case has a recorded blocker and owner. Record results in `test-cases/TEST_CASE_LIBRARY.csv` (or your test management tool synced from it) and update `status/build-status.json`.
