# Evidence — SPEC-ENG-005 (Document 101), WP-01 GxP Core contract slice, 2026-08-27

| File | What it is |
|---|---|
| `contract_validate_20260827.txt` | Real output of `tooling/contracts/validate.py` across all 12 parseable contracts. Exit code 1: 107 violations, all in the 8 contracts predating the gate. |
| `contract_conformance_pytest_20260827.txt` | `pytest tests/test_contract_conformance.py -v` — 48 passed. |
| `full_suite_20260827.log` | Full regression suite, 642 tests: **630 passed, 12 failed**. |

## Note on the 12 failures in `full_suite_20260827.log`

All 12 are in `tests/test_aseptic_flow.py` (9) and `tests/test_audit_review.py` (3) — the two
alphabetically-first files, which executed while a second pytest session was concurrently truncating
`ebmr_new_gxp_test` through the `clean_database` fixture. The failure signatures are fixture-teardown
symptoms, not assertion failures: `ForeignKeyViolationError` on `user_site_roles_role_id_fkey` (the
role row was deleted under the running test) and `KeyError` on a seeded role.

Both files were re-run immediately afterwards with sole access to the database:

```
$ pytest tests/test_aseptic_flow.py tests/test_audit_review.py -q
19 passed in 108.64s (0:01:48)
```

The failed run is retained here as evidence and is not deleted (TEST-FR-032). It is recorded as an
environment defect in the execution, not a product defect: no code path in either module was changed
by this work package, and the re-run under a clean environment passed every case.
