# WP-05 — Traceability & Build Status

## Test cases in this package

Index: `test-cases/WP-05/README.md`

| Document | Module | Risk | Test case book |
|---|---|---|---|
| 26 | SPEC-QMS-001 | HIGHER-PROCESS-RISK | `test-cases/WP-05/Document_26_SPEC-QMS-001_TEST_CASES.md` |
| 27 | SPEC-QMS-002 | HIGHER-PROCESS-RISK | `test-cases/WP-05/Document_27_SPEC-QMS-002_TEST_CASES.md` |
| 28 | SPEC-QMS-003 | HIGHER-PROCESS-RISK | `test-cases/WP-05/Document_28_SPEC-QMS-003_TEST_CASES.md` |
| 29 | SPEC-QMS-004 | HIGHER-PROCESS-RISK | `test-cases/WP-05/Document_29_SPEC-QMS-004_TEST_CASES.md` |
| 30 | SPEC-QMS-005 | HIGHER-PROCESS-RISK | `test-cases/WP-05/Document_30_SPEC-QMS-005_TEST_CASES.md` |
| 31 | SPEC-QMS-006 | HIGHER-PROCESS-RISK | `test-cases/WP-05/Document_31_SPEC-QMS-006_TEST_CASES.md` |
| 32 | SPEC-QMS-007 | HIGHER-PROCESS-RISK | `test-cases/WP-05/Document_32_SPEC-QMS-007_TEST_CASES.md` |
| 33 | SPEC-QMS-008 | HIGHER-PROCESS-RISK | `test-cases/WP-05/Document_33_SPEC-QMS-008_TEST_CASES.md` |
| 34 | SPEC-QMS-009 | HIGHER-PROCESS-RISK | `test-cases/WP-05/Document_34_SPEC-QMS-009_TEST_CASES.md` |
| 35 | SPEC-QMS-010 | HIGHER-PROCESS-RISK | `test-cases/WP-05/Document_35_SPEC-QMS-010_TEST_CASES.md` |
| 36 | SPEC-QMS-011 | STANDARD-RISK | `test-cases/WP-05/Document_36_SPEC-QMS-011_TEST_CASES.md` |
| 37 | SPEC-QMS-012 | HIGHER-PROCESS-RISK | `test-cases/WP-05/Document_37_SPEC-QMS-012_TEST_CASES.md` |

## Traceability view

`traceability/WP-05_TRACEABILITY.md` — one row per requirement showing module, risk, signature relevance,
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
