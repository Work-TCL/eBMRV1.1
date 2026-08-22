# Build Status Model

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** The stages every module and functionality moves through, and the gate to advance.

---

A module never skips a stage. A module can be sent backwards (a failed review returns it to
IN_DEVELOPMENT); that is recorded, not overwritten.

| # | Stage | Meaning | Gate to enter |
|---|---|---|---|
| 1 | `NOT_STARTED` | No work begun. | — |
| 2 | `CONTRACTS_DRAFTED` | OpenAPI/AsyncAPI/JSON Schema committed for the module. | Contract lint and compatibility check pass. |
| 3 | `SCHEMA_READY` | Entities defined and migrations written with rollback. | Migration safety check passes; catalogue entry exists. |
| 4 | `IN_DEVELOPMENT` | Command handlers, domain services and repositories being written. | Compiles; unit tests exist. |
| 5 | `CODE_COMPLETE` | All requirements implemented; nothing stubbed. | Every requirement has code and a test case mapped. |
| 6 | `UNIT_TESTED` | Unit and property tests pass. | Automated suite green in CI. |
| 7 | `INTEGRATION_TESTED` | Integration, contract and concurrency cases pass. | All P1 integration cases PASS. |
| 8 | `NEGATIVE_TESTED` | All negative, security and failure cases pass. | Every control observed refusing at least once. |
| 9 | `REVIEWED` | Independent code and test review complete. | Reviewer recorded; findings closed. |
| 10 | `OQ_EXECUTED` | Qualification protocol executed with retained evidence. | Evidence in validation/evidence; failures dispositioned. |
| 11 | `QUALIFIED` | Qualification approved. | Validation Lead sign-off recorded. |
| 12 | `RELEASED` | Included in an authorized validated release. | VSR reference recorded (Document 95). |

## Functionality-level status

Each requirement (functionality) carries its own state, so progress is visible below module level:

| State | Meaning |
|---|---|
| `NOT_STARTED` | no code, no tests executed |
| `IN_PROGRESS` | code exists, tests not all executed |
| `IMPLEMENTED` | code complete, positive case PASS |
| `VERIFIED` | all mapped test cases PASS including negatives |
| `VALIDATED` | covered by executed, reviewed qualification evidence |
| `BLOCKED` | blocked; blocker and owner recorded |
| `DEFERRED` | out of the current release scope, with a recorded decision |

## Who updates what

- **Claude Code** updates `status/build-status.json` at the end of every prompt, as part of the mandatory
  completion report. It may only set stages it can evidence (through CODE_COMPLETE / test states).
- **The QA test executor** sets test case results in `test-cases/TEST_CASE_LIBRARY.csv`.
- **The reviewer** sets `REVIEWED`.
- **The Validation Lead** sets `OQ_EXECUTED`, `QUALIFIED` and `RELEASED`. No agent may set these.

## Roll-up

`tooling/status/rollup.py` regenerates `status/BUILD_STATUS.md` and the per-work-package dashboards from
`build-status.json` plus the test library, so the human-readable view is never hand-maintained.
