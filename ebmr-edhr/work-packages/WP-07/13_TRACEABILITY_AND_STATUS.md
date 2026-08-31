# WP-07 — Traceability & Build Status

## Test cases in this package

Index: `test-cases/WP-07/README.md`

| Document | Module | Risk | Test case book |
|---|---|---|---|
| 48 | SPEC-ERP-001 | HIGHER-PROCESS-RISK | `test-cases/WP-07/Document_48_SPEC-ERP-001_TEST_CASES.md` |
| 49 | SPEC-ERP-002 | HIGHER-PROCESS-RISK | `test-cases/WP-07/Document_49_SPEC-ERP-002_TEST_CASES.md` |
| 50 | SPEC-ERP-003 | HIGHER-PROCESS-RISK | `test-cases/WP-07/Document_50_SPEC-ERP-003_TEST_CASES.md` |
| 51 | SPEC-ERP-004 | HIGHER-PROCESS-RISK | `test-cases/WP-07/Document_51_SPEC-ERP-004_TEST_CASES.md` |
| 52 | SPEC-ERP-005 | HIGHER-PROCESS-RISK | `test-cases/WP-07/Document_52_SPEC-ERP-005_TEST_CASES.md` |
| 53 | SPEC-ERP-006 | HIGHER-PROCESS-RISK | `test-cases/WP-07/Document_53_SPEC-ERP-006_TEST_CASES.md` |

## Traceability view

`traceability/WP-07_TRACEABILITY.md` — one row per requirement showing module, risk, signature relevance,
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
