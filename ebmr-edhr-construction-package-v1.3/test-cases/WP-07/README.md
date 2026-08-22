# WP-07 — Test Case Index

**Scope:** ERP architecture and adapters, master-data sync, integration error/retry/reconciliation.  
**Total test cases:** 576  
**P1 (must pass before the work package can close):** 576

| Document | Module | Risk | Test cases | Test case book |
|---|---|---|---|---|
| 48 | SPEC-ERP-001 | HIGHER-PROCESS-RISK | 120 | `test-cases/WP-07/Document_48_SPEC-ERP-001_TEST_CASES.md` |
| 49 | SPEC-ERP-002 | HIGHER-PROCESS-RISK | 98 | `test-cases/WP-07/Document_49_SPEC-ERP-002_TEST_CASES.md` |
| 50 | SPEC-ERP-003 | HIGHER-PROCESS-RISK | 76 | `test-cases/WP-07/Document_50_SPEC-ERP-003_TEST_CASES.md` |
| 51 | SPEC-ERP-004 | HIGHER-PROCESS-RISK | 84 | `test-cases/WP-07/Document_51_SPEC-ERP-004_TEST_CASES.md` |
| 52 | SPEC-ERP-005 | HIGHER-PROCESS-RISK | 98 | `test-cases/WP-07/Document_52_SPEC-ERP-005_TEST_CASES.md` |
| 53 | SPEC-ERP-006 | HIGHER-PROCESS-RISK | 100 | `test-cases/WP-07/Document_53_SPEC-ERP-006_TEST_CASES.md` |

## Exit rule

The work package cannot close until every P1 case is PASS, every FAIL has a defect reference with a disposition, and every BLOCKED case has a recorded blocker and owner. Record results in `test-cases/TEST_CASE_LIBRARY.csv` (or your test management tool synced from it) and update `status/build-status.json`.
