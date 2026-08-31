# WP-10 — Traceability & Build Status

## Test cases in this package

Index: `test-cases/WP-10/README.md`

| Document | Module | Risk | Test case book |
|---|---|---|---|
| 61 | SPEC-SEC-001 | HIGHER-PROCESS-RISK | `test-cases/WP-10/Document_61_SPEC-SEC-001_TEST_CASES.md` |
| 62 | SPEC-SEC-002 | HIGHER-PROCESS-RISK | `test-cases/WP-10/Document_62_SPEC-SEC-002_TEST_CASES.md` |
| 63 | SPEC-SEC-003 | HIGHER-PROCESS-RISK | `test-cases/WP-10/Document_63_SPEC-SEC-003_TEST_CASES.md` |
| 64 | SPEC-SEC-004 | HIGHER-PROCESS-RISK | `test-cases/WP-10/Document_64_SPEC-SEC-004_TEST_CASES.md` |
| 65 | SPEC-SEC-005 | HIGHER-PROCESS-RISK | `test-cases/WP-10/Document_65_SPEC-SEC-005_TEST_CASES.md` |
| 66 | SPEC-SEC-006 | HIGHER-PROCESS-RISK | `test-cases/WP-10/Document_66_SPEC-SEC-006_TEST_CASES.md` |
| 67 | SPEC-SEC-007 | HIGHER-PROCESS-RISK | `test-cases/WP-10/Document_67_SPEC-SEC-007_TEST_CASES.md` |
| 68 | SPEC-SEC-008 | HIGHER-PROCESS-RISK | `test-cases/WP-10/Document_68_SPEC-SEC-008_TEST_CASES.md` |

## Traceability view

`traceability/WP-10_TRACEABILITY.md` — one row per requirement showing module, risk, signature relevance,
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
