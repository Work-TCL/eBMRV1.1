# WP-12 — Traceability & Build Status

## Test cases in this package

Index: `test-cases/WP-12/README.md`

| Document | Module | Risk | Test case book |
|---|---|---|---|
| 79 | SPEC-VAL-001 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_79_SPEC-VAL-001_TEST_CASES.md` |
| 80 | SPEC-VAL-002 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_80_SPEC-VAL-002_TEST_CASES.md` |
| 81 | SPEC-VAL-003 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_81_SPEC-VAL-003_TEST_CASES.md` |
| 82 | SPEC-VAL-004 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_82_SPEC-VAL-004_TEST_CASES.md` |
| 83 | SPEC-VAL-005 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_83_SPEC-VAL-005_TEST_CASES.md` |
| 84 | SPEC-VAL-006 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_84_SPEC-VAL-006_TEST_CASES.md` |
| 86 | SPEC-VAL-008 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_86_SPEC-VAL-008_TEST_CASES.md` |
| 88 | SPEC-VAL-010 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_88_SPEC-VAL-010_TEST_CASES.md` |
| 89 | SPEC-VAL-011 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_89_SPEC-VAL-011_TEST_CASES.md` |
| 90 | SPEC-VAL-012 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_90_SPEC-VAL-012_TEST_CASES.md` |
| 91 | SPEC-VAL-013 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_91_SPEC-VAL-013_TEST_CASES.md` |
| 92 | SPEC-VAL-014 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_92_SPEC-VAL-014_TEST_CASES.md` |
| 93 | SPEC-VAL-015 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_93_SPEC-VAL-015_TEST_CASES.md` |
| 94 | SPEC-VAL-016 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_94_SPEC-VAL-016_TEST_CASES.md` |
| 96 | SPEC-VAL-018 | HIGHER-PROCESS-RISK | `test-cases/WP-12/Document_96_SPEC-VAL-018_TEST_CASES.md` |

## Traceability view

`traceability/WP-12_TRACEABILITY.md` — one row per requirement showing module, risk, signature relevance,
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
