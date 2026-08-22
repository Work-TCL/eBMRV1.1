# Claude Code prompt — WP-04 / Document 21: Material Dispensing & Weighing Specification

TASK:
Implement the Material Dispensing & Weighing Specification module (SPEC-MAT-002C) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_21_Material_Dispensing_Weighing_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: DSP-FR-001..032 (32)
- Approved baselines: Document 106 (signature policy), 107 (SoD), 108 (retention), 109 (SLO/RPO),
  110 (precision/UOM), 111 (risk class), 112 (schemas/migrations), 113 (contracts), 114 (glossary)
- Phase-0 artefacts: `docs/generated/03_FUNCTION_CATALOGUE.csv`, `04_DATA_MODEL_CATALOGUE.md`,
  `05_DATABASE_OWNERSHIP_MATRIX.md`, `06_API_CATALOGUE.yaml`, `07_EVENT_CATALOGUE.yaml`,
  `14_ERROR_CODE_REGISTRY.md`, `28_INTENDED_USE_GXP_RISK_MATRIX.md`

RISK CLASS: **HIGHER-PROCESS-RISK** → scripted tests, independent review, mandatory negative and failure evidence

ARCHITECTURE CONSTRAINTS:
- Frappe is UI/configuration only; no core fork or edit.
- PostgreSQL is authoritative for regulated state; MariaDB holds read-only projections.
- Every regulated write goes through the Mutation Gateway → one PostgreSQL transaction carrying
  domain state + record version + audit event + outbox event.
- Signatures follow Document 04 + the approved Document 106 policy; login/MFA is never a signature.
- Audit, vault and evidence history is append-only and superseding.
- Outbox is the authoritative event source; NATS is transport; Temporal is orchestration only.
- Caches, projections, search and reports are rebuildable and never a regulated decision source.
- Adapters and edge never write GxP tables; they submit integration commands.
- AI is advisory; it cannot sign, release, disposition, approve, alter audit or submit reports.

PRECONDITIONS:
- WP-00 foundations exist (contracts tooling, guardrails, CI gates).
- WP-01 GxP Core is available (mutation, policy, signature, audit, vault, rules).
- Contracts for this module are committed before implementation (Document 113).

ALLOWED SCOPE:
- `services/gxp-api/src/modules/materials` and its tests
- `contracts/` entries owned by this module
- migrations for entities owned by this module
- Frappe UI surfaces for this module in `apps/ebmr_frappe/`

DO NOT:
- Do not modify anything under `specs/`.
- Do not implement a signature requirement not present in the approved Document 106 policy set
  (emit a policy row and reference the gap instead).
- Do not create a second authoritative store for an entity owned elsewhere.
- Do not add an endpoint to a module whose exposure boundary is "no independent API" (Document 113 §6).
- Do not write a migration for an entity absent from `docs/generated/04_DATA_MODEL_CATALOGUE.md`.
- Do not use binary floating point for a regulated quantity.
- Do not fabricate a test run, scan result or qualification record.
- Do not start work in another work package.

FILES TO CREATE/MODIFY:
```text
services/gxp-api/src/modules/materials/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/materials/migrations/     # owned entities only
services/gxp-api/src/modules/materials/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-mat-002c.yaml
contracts/events/spec-mat-002c/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-mat-002c/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| DSP-FR-001 | Dispensing order | Create dispensing requirement from issued batch recipe snapshot with material spec, target quantity/formula, tolerance, stage and batch. | Exact demand. |
| DSP-FR-002 | Candidate selection | Suggest eligible released lots/containers using Inventory selection rules; operator cannot select excluded lot. | Wrong material prevented. |
| DSP-FR-003 | Material scan | Require material/lot/container barcode scan where configured and verify against requirement. | Identity check. |
| DSP-FR-004 | Location scan | Optionally verify warehouse/dispensing booth/location before operation. | Context. |
| DSP-FR-005 | Operator qualification | Require active dispensing qualification/training and site access. | Qualified personnel. |
| DSP-FR-006 | Balance eligibility | Verify balance/device registration, calibration, qualification, location and status before use. | Valid equipment. |
| DSP-FR-007 | Tare | Capture tare method/value/container and device source where applicable. | Net weight reproducible. |
| DSP-FR-008 | Target quantity | Target from recipe calculation, including potency adjustment where configured; exact rule version retained. | No manual target change. |
| DSP-FR-009 | Live balance capture | Read stable weight from Edge/Balance adapter with device identity, timestamp and quality. | Automated evidence. |
| DSP-FR-010 | Stability rule | Balance adapter/config defines stable-reading criteria and unit/precision. | No transient reading. |
| DSP-FR-011 | Manual weight fallback | Allowed only when recipe/device fallback policy permits; requires reason, manual source, possibly independent verification/signature. | Controlled fallback. |
| DSP-FR-012 | Tolerance | Evaluate actual against released tolerance rule; outside tolerance blocks completion/creates exception. | Correct quantity. |
| DSP-FR-013 | Multiple additions | Support incremental weigh additions while preserving readings and final accepted net. | Full history. |
| DSP-FR-014 | Overweight correction | If allowed, controlled removal/reweigh records all readings and material disposition; original overweight reading retained. | No overwrite. |
| DSP-FR-015 | Underweight correction | Additional material can be added from same/allowed lot according to policy; each addition traceable. | Accurate genealogy. |
| DSP-FR-016 | Potency adjustment | Use released assay/potency result and rule to determine active material target; verifier sees source and calculation. | Drug support. |
| DSP-FR-017 | Multi-lot dispensing | Use multiple approved lots only when recipe/profile permits; genealogy records each exact quantity. | No hidden pooling. |
| DSP-FR-018 | Independent verification | Support verifier scan/check of material/lot/target/actual/device and e-signature where required. | Second-person check. |
| DSP-FR-019 | Dispensed container | Create dispensed-material container/package identity with label and exact source lot/container quantities. | Shop-floor trace. |
| DSP-FR-020 | Dispensing label | Print controlled label including material, batch, dispensed qty/UOM, source lot(s), date/time, status, expiry/use-by if configured. | Identity maintained. |
| DSP-FR-021 | Label reprint | Controlled reprint with reason and count/history. | No uncontrolled duplicates. |
| DSP-FR-022 | Material issue | On accepted dispense, post inventory transaction/reservation consumption for exact source quantity. | Stock consistent. |
| DSP-FR-023 | Genealogy | Create source lot/container → dispensed container → batch relationship. | Trace. |
| DSP-FR-024 | Partial source container | Update remaining source-container quantity and open/reseal status. | Inventory correct. |
| DSP-FR-025 | Expiry/retest recheck | Revalidate source lot at dispense completion, not only initial selection, for long operations. | No stale eligibility. |
| DSP-FR-026 | Environmental/booth condition | Where required verify dispensing area/environment status before operation. | Controlled environment. |
| DSP-FR-027 | Line/booth clearance | Require applicable booth/area clearance status before dispensing. | Cross-contamination prevention. |
| DSP-FR-028 | Exception | Wrong scan, ineligible lot, balance failure, tolerance failure, qualification lapse or environment issue creates/block according to rule. | Fail safe. |
| DSP-FR-029 | Pause/resume | Preserve in-progress readings; resume revalidates material/balance/operator/status according to policy. | Interrupted work safe. |
| DSP-FR-030 | Cancel | Cancel before completion returns reservation and retains attempted evidence/reason; no consumption posted unless physically handled per policy. | No lost trace. |
| DSP-FR-031 | Bulk dispensing | Support batch/staged dispensing queue but each requirement has independent identity, eligibility, weight and genealogy. | Efficiency without ambiguity. |
| DSP-FR-032 | Audit/export | Dispensing record includes target/calculation, source lots, all relevant readings, actual, equipment, operators/verifier, signatures, labels and exceptions. | eBMR evidence complete. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (4 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `dispensing_order` | 11 | PostgreSQL (GxP Core, authoritative) |
| `dispensing_source` | 6 | PostgreSQL (GxP Core, authoritative) |
| `weighing_session` | 10 | PostgreSQL (GxP Core, authoritative) |
| `dispensed_container` | 7 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (9):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /dispensing/v1/orders` | yes | — |
| `POST /dispensing/v1/orders/{id}/select-source` | yes | — |
| `POST /dispensing/v1/orders/{id}/start` | yes | — |
| `POST /dispensing/v1/orders/{id}/readings` | yes | — |
| `POST /dispensing/v1/orders/{id}/manual-reading` | yes | — |
| `POST /dispensing/v1/orders/{id}/verify` | yes | policy lookup (Doc 106) |
| `POST /dispensing/v1/orders/{id}/complete` | yes | — |
| `POST /dispensing/v1/orders/{id}/cancel` | yes | — |
| `GET /dispensing/v1/queue` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (7):
| Event type | Producer | Dedupe key |
|---|---|---|
| `DispensingStarted` | SPEC-MAT-002C | event_id |
| `DispensingSourceSelected` | SPEC-MAT-002C | event_id |
| `WeighingReadingAccepted` | SPEC-MAT-002C | event_id |
| `WeighingExceptionRaised` | SPEC-MAT-002C | event_id |
| `DispensingVerified` | SPEC-MAT-002C | event_id |
| `MaterialDispensed` | SPEC-MAT-002C | event_id |
| `DispensingCancelled` | SPEC-MAT-002C | event_id |

UI SURFACES:
- Dispensing Queue
- Scan Batch/Requirement
- Scan Source
- Equipment/Booth Check
- Target Calculation
- Live Weight
- Tolerance
- Verification
- Label
- Completed Record

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
Fail closed on any compliance-critical dependency outage; no degraded-mode commit.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- normal balance dispense
- wrong material scan
- quarantine/expired source
- two batches same final stock
- balance calibration expired
- unstable reading
- overweight correction
- multi-lot allowed/disallowed
- potency-adjusted target
- manual fallback allowed/disallowed
- verifier SoD
- pause then retest date passes
- label reprint
- cancel
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-04/Document_21_SPEC-MAT-002C_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-MAT-002C/<test_case_id>/`.
- A failed case is evidence: never delete it, re-run over it, or edit the expected result to make it pass.
  Raise a defect, record the reference, re-execute as a new dated execution.

TRACEABILITY & STATUS (mandatory at the end of this prompt):
- Update `traceability/TRACEABILITY_MASTER.csv` for every requirement you touched: `build_stage`,
  `verification_state`, `test_case_ids`, `evidence_location`.
- Update `status/build-status.json`: set this module's `stage`, append to `stage_history`, set
  `requirements_state` per requirement, and set `test_pass` / `test_fail` / `test_blocked` from the
  actual recorded results.
- You may only set stages you can evidence, up to and including CODE_COMPLETE and the test states.
  `REVIEWED`, `OQ_EXECUTED`, `QUALIFIED` and `RELEASED` are set by humans, never by you.
- Run `python tooling/status/rollup.py` and include the printed summary in your completion report.

VALIDATION / TRACEABILITY:
- update `docs/generated/15_TEST_TRACEABILITY_MATRIX.csv` and `29_VALIDATION_TRACEABILITY_MASTER.csv`
- state IQ/OQ/PQ impact; HIGHER-PROCESS-RISK functions need retained objective evidence
- Part 11 impact where signatures are involved (Document 88)

ACCEPTANCE CRITERIA:
- every requirement above implemented, traced and tested
- all listed tests executed with real results
- no architecture guardrail violation
- contracts committed before implementation and compatible

SPEC_GAP RULE:
Do not guess regulated behaviour. Append unresolved decisions to `docs/generated/18_SPEC_GAPS.md`
with affected requirements, risk, options and blocking status, then continue only on unaffected work.

BEFORE COMPLETION:
Run lint, typecheck, unit, contract, integration and guardrail checks. Report actual results.

COMPLETION REPORT:
requirements implemented; functions created/changed; files changed; migrations; contract changes;
dependency/licence changes; security impact; **test cases executed with PASS/FAIL/BLOCKED counts and
the case ids of every failure**; validation impact; **traceability and status files updated (include the
rollup summary)**; unresolved SPEC_GAPs; known limitations.
