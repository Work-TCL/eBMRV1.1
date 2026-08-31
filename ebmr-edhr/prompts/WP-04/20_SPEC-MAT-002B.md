# Claude Code prompt — WP-04 / Document 20: Inventory, Lot/Container & Warehouse Specification

TASK:
Implement the Inventory, Lot/Container & Warehouse Specification module (SPEC-MAT-002B) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_20_Inventory_Lot_Container_Warehouse_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: INV-FR-001..032 (32)
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
contracts/openapi/spec-mat-002b.yaml
contracts/events/spec-mat-002b/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-mat-002b/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| INV-FR-001 | Warehouse master | Define site warehouse, zones, rooms, bins/locations, environmental class and permitted status/material categories. | Location controlled. |
| INV-FR-002 | Status segregation | Locations can be designated quarantine, released, rejected, return, destruction, controlled-temperature, sterile/component or other configured zones. | Physical/digital status aligned. |
| INV-FR-003 | Lot inventory | Maintain on-hand/reserved/available quantity by material lot and container. | Exact stock. |
| INV-FR-004 | Container inventory | Track individual container quantity/status/location where material handling requires it. | Dispensing source exact. |
| INV-FR-005 | Unit-of-measure | Canonical UOM and validated conversion used for stock transactions. | No unit ambiguity. |
| INV-FR-006 | Inventory transaction ledger | Every receipt, transfer, reserve, issue, dispense, consume, return, adjust, reject/destruct creates immutable transaction. | No editable balance. |
| INV-FR-007 | Derived balance | Current quantity derives from transaction ledger/projection and is reconciliation-tested. | History authoritative. |
| INV-FR-008 | Location transfer | Move lot/container between permitted locations with scanner/manual verification and status compatibility. | Wrong zone blocked. |
| INV-FR-009 | Inter-site transfer | Controlled shipment/receipt relationship preserving lot/container identity and quality state rules. | Multi-plant trace. |
| INV-FR-010 | Reservation | Reserve quantity/containers for batch/order without consuming; prevent over-reservation. | Planning safe. |
| INV-FR-011 | Reservation expiry/release | Reservation has status/expiry/cancel rules and can be released when batch changes. | No stranded stock. |
| INV-FR-012 | FEFO/FIFO policy | Selection engine prioritizes approved stock by product/profile rule; drug-side baseline supports oldest-approved stock rotation and deviation path. | Stock rotation compliant. |
| INV-FR-013 | Expiry | Expired material automatically becomes ineligible and may trigger status/hold workflow. | No expired use. |
| INV-FR-014 | Retest due | Retest-due material becomes ineligible/quarantine according to profile until reapproved. | 211.87 support. |
| INV-FR-015 | Quality hold | Quality can place lot/container hold independent of warehouse location. | Immediate block. |
| INV-FR-016 | Recall/blocked source | Supplier/material/quality event can block affected lots/containers through impact command. | Quality integrated. |
| INV-FR-017 | Product eligibility | Material lot may be released generally but only eligible for products/sites/spec versions defined by rules. | Correct product use. |
| INV-FR-018 | Alternative material | Selection of approved alternative material requires recipe/rule compatibility and possibly change/deviation approval. | No ad hoc substitution. |
| INV-FR-019 | Barcode | Generate/accept controlled barcode for material/lot/container/location; scan verifies expected identity. | Shop-floor reliability. |
| INV-FR-020 | Cycle count | Perform controlled inventory counts, discrepancies and adjustment approval without altering GxP transaction history. | Inventory accuracy. |
| INV-FR-021 | Physical count freeze | Optional location/item count lock prevents conflicting warehouse movements during count. | Concurrency safe. |
| INV-FR-022 | Negative inventory | GxP inventory cannot go negative through normal transaction. | Constraint. |
| INV-FR-023 | Container split | Split container creates child container identities with quantity conservation and parent relationship. | Traceability. |
| INV-FR-024 | Container merge | Merge only when material/spec/lot/status compatibility rules permit; preserve source relationships. | No identity loss. |
| INV-FR-025 | Partial container | Track remaining quantity after sampling/dispensing/return and reseal/open status where relevant. | Usability. |
| INV-FR-026 | Storage condition | Associate material/location storage requirements and environmental evidence/reference; excursion creates hold/impact when configured. | Quality protection. |
| INV-FR-027 | Label status | Container status labels reprinted only through controlled reprint with current quality status/version. | Physical status current. |
| INV-FR-028 | Inventory reconciliation with ERP | Compare GxP quantity to ERP/WMS quantity/reference; mismatches flagged, never auto-resolved by overwriting GxP ledger. | Boundary. |
| INV-FR-029 | Search | Search stock by material/spec/lot/container/status/location/expiry/retest/supplier/manufacturer. | Operational. |
| INV-FR-030 | Genealogy | Inventory transactions create/maintain lot/container provenance used by Document 13. | Traceable. |
| INV-FR-031 | Retention | Transaction history retained according to associated regulated record/material policy. | Evidence enduring. |
| INV-FR-032 | Performance | Support thousands/millions of inventory transactions with indexed ledger and balance projection. | Enterprise scale. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (4 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `warehouse_location` | 8 | PostgreSQL (GxP Core, authoritative) |
| `inventory_transaction` | 16 | PostgreSQL (GxP Core, authoritative) |
| `inventory_balance_projection` | 6 | PostgreSQL (GxP Core, authoritative) |
| `inventory_reservation` | 7 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (9):
| Operation | State-changing | Signature |
|---|---|---|
| `GET /inventory/v1/availability` | no | — |
| `POST /inventory/v1/reservations` | yes | — |
| `POST /inventory/v1/reservations/{id}/release` | yes | policy lookup (Doc 106) |
| `POST /inventory/v1/transfers` | yes | — |
| `POST /inventory/v1/containers/{id}/split` | yes | — |
| `POST /inventory/v1/containers/merge` | yes | — |
| `POST /inventory/v1/cycle-counts` | yes | — |
| `GET /inventory/v1/lots/{id}/ledger` | no | — |
| `GET /inventory/v1/reconciliation/erp` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (9):
| Event type | Producer | Dedupe key |
|---|---|---|
| `InventoryReceived` | SPEC-MAT-002B | event_id |
| `InventoryTransferred` | SPEC-MAT-002B | event_id |
| `InventoryReserved` | SPEC-MAT-002B | event_id |
| `InventoryReservationReleased` | SPEC-MAT-002B | event_id |
| `ContainerSplit` | SPEC-MAT-002B | event_id |
| `ContainerMerged` | SPEC-MAT-002B | event_id |
| `MaterialQualityHoldPlaced` | SPEC-MAT-002B | event_id |
| `InventoryAdjusted` | SPEC-MAT-002B | event_id |
| `InventoryERPDiscrepancyDetected` | SPEC-MAT-002B | event_id |

UI SURFACES:
- Warehouse Overview
- Material Availability
- Lot/Container Search
- Transfer
- Reservation
- Expiry/Retest
- Quality Hold
- Cycle Count
- Container Split/Merge
- Inventory Ledger
- ERP Reconciliation

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
- released lot availability
- quarantine excluded
- expired/retest excluded
- simultaneous reservations
- container split conservation
- incompatible merge
- transfer to wrong status zone
- negative inventory attempt
- FIFO/FEFO deviation
- cycle-count discrepancy
- ERP mismatch
- intersite transfer
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-04/Document_20_SPEC-MAT-002B_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-MAT-002B/<test_case_id>/`.
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
