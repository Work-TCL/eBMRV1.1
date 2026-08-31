# WP-06 — Traceability & Build Status

## Test cases in this package

Index: `test-cases/WP-06/README.md`

| Document | Module | Risk | Test case book |
|---|---|---|---|
| 38 | SPEC-EQP-001 | HIGHER-PROCESS-RISK | `test-cases/WP-06/Document_38_SPEC-EQP-001_TEST_CASES.md` |
| 39 | SPEC-EQP-002 | HIGHER-PROCESS-RISK | `test-cases/WP-06/Document_39_SPEC-EQP-002_TEST_CASES.md` |
| 40 | SPEC-EQP-003 | HIGHER-PROCESS-RISK | `test-cases/WP-06/Document_40_SPEC-EQP-003_TEST_CASES.md` |
| 41 | SPEC-EQP-004 | HIGHER-PROCESS-RISK | `test-cases/WP-06/Document_41_SPEC-EQP-004_TEST_CASES.md` |
| 42 | SPEC-EQP-005 | HIGHER-PROCESS-RISK | `test-cases/WP-06/Document_42_SPEC-EQP-005_TEST_CASES.md` |
| 43 | SPEC-EDGE-001 | HIGHER-PROCESS-RISK | `test-cases/WP-06/Document_43_SPEC-EDGE-001_TEST_CASES.md` |
| 44 | SPEC-EDGE-002 | HIGHER-PROCESS-RISK | `test-cases/WP-06/Document_44_SPEC-EDGE-002_TEST_CASES.md` |
| 45 | SPEC-EDGE-003 | HIGHER-PROCESS-RISK | `test-cases/WP-06/Document_45_SPEC-EDGE-003_TEST_CASES.md` |
| 46 | SPEC-EDGE-004 | HIGHER-PROCESS-RISK | `test-cases/WP-06/Document_46_SPEC-EDGE-004_TEST_CASES.md` |
| 47 | SPEC-EDGE-005 | HIGHER-PROCESS-RISK | `test-cases/WP-06/Document_47_SPEC-EDGE-005_TEST_CASES.md` |

## Traceability view

`traceability/WP-06_TRACEABILITY.md` — one row per requirement showing module, risk, signature relevance,
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
