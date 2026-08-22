# Claude Code prompt — WP-05 / Document 32: Supplier Quality / SCAR

TASK:
Implement the Supplier Quality / SCAR module (SPEC-QMS-007) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_32_Supplier_Quality_SCAR_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: SCAR-FR-001..018 (18)
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
- `services/gxp-api/src/modules/qms` and its tests
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
services/gxp-api/src/modules/qms/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/qms/migrations/     # owned entities only
services/gxp-api/src/modules/qms/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-qms-007.yaml
contracts/events/spec-qms-007/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-qms-007/
```

REQUIREMENTS TO IMPLEMENT (18):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| SCAR-FR-001 | Supplier quality case | Create from incoming reject, deviation, complaint, audit, trend or manufacturing defect. | Source linked. |
| SCAR-FR-002 | Affected source | Identify supplier/manufacturer site, material/spec and affected lots/products. | Scope exact. |
| SCAR-FR-003 | Containment | Hold lot/source/new receipts/use if risk requires; link ASL status. | Immediate control. |
| SCAR-FR-004 | SCAR issue | Formal request with problem/evidence, required response and due dates. | Supplier action. |
| SCAR-FR-005 | Acknowledgment | Track supplier acknowledgment/contact. | Communication. |
| SCAR-FR-006 | Supplier root cause | Capture supplier-provided root cause/evidence as supplier statement, not automatically accepted fact. | Review. |
| SCAR-FR-007 | Supplier actions | Track supplier corrections/corrective actions and implementation evidence. | Action. |
| SCAR-FR-008 | Internal review | Supplier Quality/QA accepts/rejects response with rationale/signature. | Authority. |
| SCAR-FR-009 | Effectiveness | Verify incoming/performance data after implementation. | True closure. |
| SCAR-FR-010 | Requalification | Significant issue may trigger audit/requalification. | ASL. |
| SCAR-FR-011 | Source suspension | Supplier-material approval can be suspended pending resolution. | Procurement gate. |
| SCAR-FR-012 | Alternate source | Emergency alternative source links deviation/change. | Controlled. |
| SCAR-FR-013 | Internal CAPA | Internal CAPA may also be required. | Ownership. |
| SCAR-FR-014 | Repeat issue | Detect recurrence by supplier/material/defect. | Trend. |
| SCAR-FR-015 | Escalation | Overdue response escalates. | Timeliness. |
| SCAR-FR-016 | Closure | Close only after accepted response/effectiveness/source decision. | Complete. |
| SCAR-FR-017 | Performance impact | SCAR contributes to supplier scorecard/risk. | Data driven. |
| SCAR-FR-018 | Export | Correspondence/evidence/history exportable. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `supplier_quality_case` | 6 | PostgreSQL (GxP Core, authoritative) |
| `scar_record` | 7 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (6):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /qms/v1/supplier-cases` | yes | — |
| `POST /qms/v1/supplier-cases/{id}/scar` | yes | — |
| `POST /qms/v1/scars/{id}/response` | yes | — |
| `POST /qms/v1/scars/{id}/review` | yes | — |
| `POST /qms/v1/scars/{id}/effectiveness` | yes | — |
| `POST /qms/v1/scars/{id}/close` | yes | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (6):
| Event type | Producer | Dedupe key |
|---|---|---|
| `SupplierQualityCaseOpened` | SPEC-QMS-007 | event_id |
| `SCARIssued` | SPEC-QMS-007 | event_id |
| `SCARResponseReceived` | SPEC-QMS-007 | event_id |
| `SupplierSourceSuspended` | SPEC-QMS-007 | event_id |
| `SCAREffectivenessPassed` | SPEC-QMS-007 | event_id |
| `SCARClosed` | SPEC-QMS-007 | event_id |

UI SURFACES:
- Supplier Quality Dashboard
- Supplier Case
- Containment/ASL Impact
- SCAR
- Supplier Response
- Internal Review
- Effectiveness
- Supplier Status
- History

SECURITY:
- authorization on every object and function access; tenant/site isolation enforced in the query layer
- parameterised SQL; validated input; redacted structured logs
- security events for denied, replayed and malformed requests
- see `.claude/rules/06-security-rules.md`

FAILURE / RECOVERY:
- DB unavailable: no regulated state transition.
- Signature/Policy unavailable: fail closed where required.
- Notification/outbox failures retry.
- Stale version rejects.
- Scheduled due/expiry jobs resume from persisted records.

MIGRATIONS:
- expand → migrate → contract; resumable idempotent backfill; tested rollback
- add an entry to `docs/generated/36_DATABASE_MIGRATION_CATALOGUE.md`

TESTS (from the specification's test catalogue):
- incoming reject
- repeat supplier lot issue
- SCAR overdue
- supplier response rejected
- source suspended
- requalification
- failed effectiveness
- CAPA link
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-05/Document_32_SPEC-QMS-007_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-QMS-007/<test_case_id>/`.
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
