# WP-14 — Test Case Index

**Scope:** PQ/UAT, data migration/cutover/reconciliation validation, VSR and validated release authorization.  
**Total test cases:** 192  
**P1 (must pass before the work package can close):** 192

| Document | Module | Risk | Test cases | Test case book |
|---|---|---|---|---|
| 85 | SPEC-VAL-007 | HIGHER-PROCESS-RISK | 57 | `test-cases/WP-14/Document_85_SPEC-VAL-007_TEST_CASES.md` |
| 87 | SPEC-VAL-009 | HIGHER-PROCESS-RISK | 63 | `test-cases/WP-14/Document_87_SPEC-VAL-009_TEST_CASES.md` |
| 95 | SPEC-VAL-017 | HIGHER-PROCESS-RISK | 72 | `test-cases/WP-14/Document_95_SPEC-VAL-017_TEST_CASES.md` |

## Exit rule

The work package cannot close until every P1 case is PASS, every FAIL has a defect reference with a disposition, and every BLOCKED case has a recorded blocker and owner. Record results in `test-cases/TEST_CASE_LIBRARY.csv` (or your test management tool synced from it) and update `status/build-status.json`.
