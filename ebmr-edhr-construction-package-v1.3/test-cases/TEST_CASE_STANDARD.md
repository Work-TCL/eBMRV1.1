# Test Case Standard & Execution Rules

**Total test cases:** 9150
**Coverage:** every requirement in Documents 03–105 has at least one positive case; higher-risk and
rejection-bearing requirements carry targeted negative, boundary, concurrency and failure cases; every
module carries the 14-case mandatory platform suite; every scenario declared in a specification's own
test catalogue is included as a scenario case.

## Distribution

| Test type | Cases |
|---|---|
| positive | 2965 |
| negative | 2674 |
| scenario | 1208 |
| failure | 783 |
| security | 568 |
| concurrency | 477 |
| idempotency | 206 |
| boundary | 166 |
| integrity | 103 |

| Work package | Cases |
|---|---|
| WP-00 | 726 |
| WP-01 | 811 |
| WP-02 | 476 |
| WP-03 | 563 |
| WP-04 | 960 |
| WP-05 | 739 |
| WP-06 | 811 |
| WP-07 | 576 |
| WP-08 | 375 |
| WP-09 | 277 |
| WP-10 | 620 |
| WP-11 | 863 |
| WP-12 | 980 |
| WP-13 | 181 |
| WP-14 | 192 |

## Test case fields

`test_case_id, requirement_id, document, module, work_package, title, test_type, priority, risk_class,
preconditions, test_data, steps, expected_result, error_code_expected, evidence_to_capture,
automation_level, qualification_stage, depends_on, owner_role, status, executed_by, executed_at,
actual_result, defect_reference, source_section`

## Rules the developer team follows

1. **Every case is executed and recorded.** No case is closed by inspection or assumption.
2. **A failed execution is evidence.** Never delete it, re-run over it, or edit an assertion to make it
   pass. Raise a defect, reference it, and re-execute as a new dated execution.
3. **Evidence is captured for every case**, not only failures — request/response, state before and after,
   audit event id, outbox row, screenshots for UI-driven cases.
4. **P1 cases gate the work package.** All must be PASS before the package can close.
5. **Negative cases are not optional.** For HIGHER-PROCESS-RISK modules they are the primary evidence that
   the control works; a control that has never been observed refusing has not been tested.
6. **Test data is recorded before execution**, including tenant, site, actor, roles and qualifications.
7. **Automated cases still need evidence**: the CI run id, the assertion output and the commit sha.
8. **Traceability is updated in the same change** — a test that does not map to a requirement, or a
   requirement with no test, fails the traceability gate.
9. **Qualification stage matters.** Cases marked OQ produce validation evidence and follow Document 84
   execution rules (scripted, independently reviewed, retained). Engineering cases feed regression.
10. **Test cases are controlled.** Changing an expected result is a change to the acceptance criteria and
    needs the same review as changing the requirement.

## Where results live

- Working record: `test-cases/TEST_CASE_LIBRARY.csv` (or your test management tool, synced from it)
- Evidence: `validation/evidence/<stage>/<release>/<test_case_id>/`
- Roll-up: `status/build-status.json` → `status/BUILD_STATUS.md`
- Traceability: `traceability/TRACEABILITY_MASTER.csv`
