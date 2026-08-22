# WP-14 — Traceability & Build Status

## Test cases in this package

Index: `test-cases/WP-14/README.md`

| Document | Module | Risk | Test case book |
|---|---|---|---|
| 85 | SPEC-VAL-007 | HIGHER-PROCESS-RISK | `test-cases/WP-14/Document_85_SPEC-VAL-007_TEST_CASES.md` |
| 87 | SPEC-VAL-009 | HIGHER-PROCESS-RISK | `test-cases/WP-14/Document_87_SPEC-VAL-009_TEST_CASES.md` |
| 95 | SPEC-VAL-017 | HIGHER-PROCESS-RISK | `test-cases/WP-14/Document_95_SPEC-VAL-017_TEST_CASES.md` |

## Traceability view

`traceability/WP-14_TRACEABILITY.md` — one row per requirement showing module, risk, signature relevance,
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
