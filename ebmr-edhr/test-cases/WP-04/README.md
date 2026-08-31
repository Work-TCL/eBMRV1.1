# WP-04 — Test Case Index

**Scope:** Supplier/procurement, receipt/quarantine, inventory, dispensing, consumption, QC/sampling, LIMS, OOS/OOT.  
**Total test cases:** 960  
**P1 (must pass before the work package can close):** 960

| Document | Module | Risk | Test cases | Test case book |
|---|---|---|---|---|
| 18 | SPEC-MAT-001 | HIGHER-PROCESS-RISK | 104 | `test-cases/WP-04/Document_18_SPEC-MAT-001_TEST_CASES.md` |
| 19 | SPEC-MAT-002A | HIGHER-PROCESS-RISK | 99 | `test-cases/WP-04/Document_19_SPEC-MAT-002A_TEST_CASES.md` |
| 20 | SPEC-MAT-002B | HIGHER-PROCESS-RISK | 98 | `test-cases/WP-04/Document_20_SPEC-MAT-002B_TEST_CASES.md` |
| 21 | SPEC-MAT-002C | HIGHER-PROCESS-RISK | 102 | `test-cases/WP-04/Document_21_SPEC-MAT-002C_TEST_CASES.md` |
| 22 | SPEC-MAT-002D | HIGHER-PROCESS-RISK | 109 | `test-cases/WP-04/Document_22_SPEC-MAT-002D_TEST_CASES.md` |
| 23 | SPEC-QC-001 | HIGHER-PROCESS-RISK | 161 | `test-cases/WP-04/Document_23_SPEC-QC-001_TEST_CASES.md` |
| 24 | SPEC-QC-002 | HIGHER-PROCESS-RISK | 137 | `test-cases/WP-04/Document_24_SPEC-QC-002_TEST_CASES.md` |
| 25 | SPEC-QC-003 | HIGHER-PROCESS-RISK | 150 | `test-cases/WP-04/Document_25_SPEC-QC-003_TEST_CASES.md` |

## Exit rule

The work package cannot close until every P1 case is PASS, every FAIL has a defect reference with a disposition, and every BLOCKED case has a recorded blocker and owner. Record results in `test-cases/TEST_CASE_LIBRARY.csv` (or your test management tool synced from it) and update `status/build-status.json`.
