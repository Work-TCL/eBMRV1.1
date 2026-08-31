# SPEC-SEC-004 (Document 64) — OQ evidence pointer

Phase-1 build. Objective evidence for the executed test cases (see
`test-cases/TEST_CASE_LIBRARY.csv`, rows `TC-064-*`, status/executed_by/executed_at/actual_result):

- **Automated test source:** `services/gxp-api/tests/test_appsec_secure_runtime.py` (14 tests).
- **Real run:** 14/14 passed against `ebmr_new_gxp_test` on 2026-08-31 (see this session's transcript
  and `status/build-status.json` → module 64 `stage_history`).
- **Regression:** Documents 61/62/63 security suites 30/30 passed under the same changes; full
  `pytest -q` regression result recorded in the completion report / build-status note.
- **Contract validation:** `tooling/contracts/validate.py --strict-coverage` PASS,
  `tooling/events/validate.py` PASS.
- **Migration forward+rollback:** `0065_appsec_secure_runtime_schema` upgrade → downgrade → re-upgrade
  exercised on the restored test database.

Per-case evidence bundles are not materialised in this phase (same as Documents 61–63); the
authoritative record is the test library rows plus the automated test assertions they name.
