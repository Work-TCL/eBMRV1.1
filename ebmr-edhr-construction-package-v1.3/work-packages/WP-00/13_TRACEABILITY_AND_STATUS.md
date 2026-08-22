# WP-00 — Traceability & Build Status

## Test cases in this package

Index: `test-cases/WP-00/README.md`

| Document | Module | Risk | Test case book |
|---|---|---|---|
| 01 | DOC-001 | N/A | `test-cases/WP-00/Document_01_DOC-001_TEST_CASES.md` |
| 02 | DOC-002 | N/A | `test-cases/WP-00/Document_02_DOC-002_TEST_CASES.md` |
| 97 | SPEC-ENG-001 | HIGHER-PROCESS-RISK | `test-cases/WP-00/Document_97_SPEC-ENG-001_TEST_CASES.md` |
| 98 | SPEC-ENG-002 | HIGHER-PROCESS-RISK | `test-cases/WP-00/Document_98_SPEC-ENG-002_TEST_CASES.md` |
| 99 | SPEC-ENG-003 | HIGHER-PROCESS-RISK | `test-cases/WP-00/Document_99_SPEC-ENG-003_TEST_CASES.md` |
| 100 | SPEC-ENG-004 | HIGHER-PROCESS-RISK | `test-cases/WP-00/Document_100_SPEC-ENG-004_TEST_CASES.md` |
| 101 | SPEC-ENG-005 | HIGHER-PROCESS-RISK | `test-cases/WP-00/Document_101_SPEC-ENG-005_TEST_CASES.md` |
| 102 | SPEC-ENG-006 | HIGHER-PROCESS-RISK | `test-cases/WP-00/Document_102_SPEC-ENG-006_TEST_CASES.md` |
| 103 | SPEC-ENG-007 | HIGHER-PROCESS-RISK | `test-cases/WP-00/Document_103_SPEC-ENG-007_TEST_CASES.md` |
| 104 | SPEC-ENG-008 | HIGHER-PROCESS-RISK | `test-cases/WP-00/Document_104_SPEC-ENG-008_TEST_CASES.md` |

## Traceability view

`traceability/WP-00_TRACEABILITY.md` — one row per requirement showing module, risk, signature relevance,
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
