# WP-00 — Test Case Index

**Scope:** Monorepo skeleton, contract tooling, CI gates, architecture guardrails, migration/test/release standards.  
**Total test cases:** 726  
**P1 (must pass before the work package can close):** 726

| Document | Module | Risk | Test cases | Test case book |
|---|---|---|---|---|
| 97 | SPEC-ENG-001 | HIGHER-PROCESS-RISK | 87 | `test-cases/WP-00/Document_97_SPEC-ENG-001_TEST_CASES.md` |
| 98 | SPEC-ENG-002 | HIGHER-PROCESS-RISK | 96 | `test-cases/WP-00/Document_98_SPEC-ENG-002_TEST_CASES.md` |
| 99 | SPEC-ENG-003 | HIGHER-PROCESS-RISK | 91 | `test-cases/WP-00/Document_99_SPEC-ENG-003_TEST_CASES.md` |
| 100 | SPEC-ENG-004 | HIGHER-PROCESS-RISK | 78 | `test-cases/WP-00/Document_100_SPEC-ENG-004_TEST_CASES.md` |
| 101 | SPEC-ENG-005 | HIGHER-PROCESS-RISK | 87 | `test-cases/WP-00/Document_101_SPEC-ENG-005_TEST_CASES.md` |
| 102 | SPEC-ENG-006 | HIGHER-PROCESS-RISK | 98 | `test-cases/WP-00/Document_102_SPEC-ENG-006_TEST_CASES.md` |
| 103 | SPEC-ENG-007 | HIGHER-PROCESS-RISK | 105 | `test-cases/WP-00/Document_103_SPEC-ENG-007_TEST_CASES.md` |
| 104 | SPEC-ENG-008 | HIGHER-PROCESS-RISK | 84 | `test-cases/WP-00/Document_104_SPEC-ENG-008_TEST_CASES.md` |

## Exit rule

The work package cannot close until every P1 case is PASS, every FAIL has a defect reference with a disposition, and every BLOCKED case has a recorded blocker and owner. Record results in `test-cases/TEST_CASE_LIBRARY.csv` (or your test management tool synced from it) and update `status/build-status.json`.
