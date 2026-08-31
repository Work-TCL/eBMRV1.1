# SPEC-SEC-006 — OQ evidence pointer

Phase-1 build. Objective evidence for the executed test cases (see `test-cases/TEST_CASE_LIBRARY.csv`,
rows for this module: status / executed_by / executed_at / actual_result):

- **Automated test source:** the module's new test file under `services/gxp-api/tests/`
  (test_crypto_secrets_pki.py / test_netzero_isolation.py / test_security_incident_response.py /
  test_supplychain_release_security.py).
- **Real run:** Docs 65-68 new suites 27/27 passed against `ebmr_new_gxp_test` on 2026-08-31.
- **Regression:** targeted regression (Documents 61-64 security suites + appsec + postmarket + iam_admin)
  65/65 passed under these changes; the full `pytest -q` sweep reached 54% with zero failures before it
  was stopped at the user's request in favour of the targeted path.
- **Contract validation:** tooling/contracts/validate.py --strict-coverage PASS,
  tooling/events/validate.py PASS.
- **Migration forward+rollback:** 0066-0069 upgrade -> downgrade -> re-upgrade exercised on the restored
  test database (single alembic head f6c4e0b1a8d5).

Per-case evidence bundles are not materialised in this phase (same as Documents 61-64); the authoritative
record is the test-library rows plus the automated test assertions they name.
