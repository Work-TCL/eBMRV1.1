# WP-04 — Traceability & Build Status

## Test cases in this package

Index: `test-cases/WP-04/README.md`

| Document | Module | Risk | Test case book |
|---|---|---|---|
| 18 | SPEC-MAT-001 | HIGHER-PROCESS-RISK | `test-cases/WP-04/Document_18_SPEC-MAT-001_TEST_CASES.md` |
| 19 | SPEC-MAT-002A | HIGHER-PROCESS-RISK | `test-cases/WP-04/Document_19_SPEC-MAT-002A_TEST_CASES.md` |
| 20 | SPEC-MAT-002B | HIGHER-PROCESS-RISK | `test-cases/WP-04/Document_20_SPEC-MAT-002B_TEST_CASES.md` |
| 21 | SPEC-MAT-002C | HIGHER-PROCESS-RISK | `test-cases/WP-04/Document_21_SPEC-MAT-002C_TEST_CASES.md` |
| 22 | SPEC-MAT-002D | HIGHER-PROCESS-RISK | `test-cases/WP-04/Document_22_SPEC-MAT-002D_TEST_CASES.md` |
| 23 | SPEC-QC-001 | HIGHER-PROCESS-RISK | `test-cases/WP-04/Document_23_SPEC-QC-001_TEST_CASES.md` |
| 24 | SPEC-QC-002 | HIGHER-PROCESS-RISK | `test-cases/WP-04/Document_24_SPEC-QC-002_TEST_CASES.md` |
| 25 | SPEC-QC-003 | HIGHER-PROCESS-RISK | `test-cases/WP-04/Document_25_SPEC-QC-003_TEST_CASES.md` |

## Traceability view

`traceability/WP-04_TRACEABILITY.md` — one row per requirement showing module, risk, signature relevance,
mapped test cases and current build/verification/validation state. The authoritative record is
`traceability/TRACEABILITY_MASTER.csv`.

## Status tracking

- Stage model and gates: `status/STATUS_MODEL.md`
- Machine-readable state: `status/build-status.json`
- Dashboard: `status/BUILD_STATUS.md` (generated — run `python tooling/status/rollup.py`)

## Update rhythm

| When | Who | Update |
|---|---|---|
| Contracts committed | Claude Code | module stage → `CONTRACTS_DRAFTED` |
| Migrations written | Claude Code | stage → `SCHEMA_READY` |
| Requirement implemented | Claude Code | `requirements_state[req] = IMPLEMENTED` |
| Test case executed | QA executor | test library `status`, `executed_by`, `actual_result`, evidence |
| All mapped cases PASS | rollup | `requirements_state[req] = VERIFIED` |
| Independent review done | Reviewer | stage → `REVIEWED` |
| OQ executed / approved | Validation Lead | stage → `OQ_EXECUTED` → `QUALIFIED` |
| Included in a validated release | Validation Lead | stage → `RELEASED` with VSR reference |

Claude Code may set stages only up to `CODE_COMPLETE` and the test states, and only from real results.
