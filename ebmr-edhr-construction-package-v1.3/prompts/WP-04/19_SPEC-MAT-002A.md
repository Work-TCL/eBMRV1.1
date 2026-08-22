# Claude Code prompt — WP-04 / Document 19: Material Receipt, Quarantine & Quality Status Specification

TASK:
Implement the Material Receipt, Quarantine & Quality Status Specification module (SPEC-MAT-002A) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_19_Material_Receipt_Quarantine_Quality_Status_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: RCV-FR-001..032 (32)
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
contracts/openapi/spec-mat-002a.yaml
contracts/events/spec-mat-002a/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-mat-002a/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| RCV-FR-001 | Expected receipt | Load PO/transfer expectation with exact material/spec/source/quantity/document requirements. | Receiver knows expected material. |
| RCV-FR-002 | Receipt transaction | Create immutable receipt ID, site, date/time, receiver, carrier/reference, PO/source and received quantity. | Receipt attributable. |
| RCV-FR-003 | Visual examination | Capture appropriate labeling, damage, broken seals, contamination and shipment-condition observations before acceptance into quarantine. | 211.82-style receipt check. |
| RCV-FR-004 | Material identity | Match received material code/name/spec to expected material; mismatch creates hold/deviation, not silent remapping. | Wrong material blocked. |
| RCV-FR-005 | Supplier/manufacturer identity | Capture supplier and actual manufacturer and validate against approved source matrix. | Source eligibility checked. |
| RCV-FR-006 | Supplier lot | Capture supplier lot/batch number exactly as received. | Traceability. |
| RCV-FR-007 | Manufacturer lot | Capture manufacturer lot where distinct. | Source traceability. |
| RCV-FR-008 | Internal lot | Generate unique internal lot code for each received lot/shipment grouping according to site policy. | Distinctive status code. |
| RCV-FR-009 | Container identity | Create individual/container-group IDs and optional barcodes/QR labels. | Sampling/dispensing exact. |
| RCV-FR-010 | Quantity | Capture received gross/net/accepted quantity and UOM with conversion rules. | Inventory accurate. |
| RCV-FR-011 | Manufacture/expiry/retest | Capture available manufacture, expiry and retest dates with source/evidence and validation. | Eligibility later. |
| RCV-FR-012 | COA/CoC | Capture required documents, file hash, source and document completeness. | Supplier evidence linked. |
| RCV-FR-013 | COA extraction | AI/OCR may assist data entry later, but extracted data is advisory until verified; original document remains evidence. | No autonomous release. |
| RCV-FR-014 | Shipment conditions | Capture temperature logger/transport condition evidence where required and generate excursion if outside rule. | Cold-chain support. |
| RCV-FR-015 | Automatic quarantine | All applicable incoming regulated materials/containers/closures enter QUARANTINE by default until required test/examination and QC disposition. | No direct released receipt. |
| RCV-FR-016 | Physical/location quarantine | Assign allowed quarantine location/zone; system prevents issue/dispense from quarantined stock. | Status enforced. |
| RCV-FR-017 | Status label | Generate container/lot status label containing internal lot/container ID, material, status and other configured fields. | Physical/digital alignment. |
| RCV-FR-018 | Sampling request | Create sampling order based on material/spec/supplier risk/lot/shipment and sampling plan. | QC workflow initiated. |
| RCV-FR-019 | Container selection | Sampling plan identifies container(s) selected and quantity; actual selected containers recorded. | Representative sample trace. |
| RCV-FR-020 | Sampling execution | Capture sampler, date/time, method/procedure reference, container, sample ID and reseal/marking evidence. | 211.84-style evidence. |
| RCV-FR-021 | Aseptic sampling | Where required enforce sterile equipment/aseptic sampling qualification/profile and environment evidence. | Sterile materials supported. |
| RCV-FR-022 | Sample chain of custody | Track sample container/location/transfer to QC/LIMS and status. | Sample integrity. |
| RCV-FR-023 | Identity test | For applicable drug components require identity testing rule and result before release; supplier COA alone cannot bypass required identity testing. | 211.84 support. |
| RCV-FR-024 | Supplier COA reliance | Where permitted by profile, accept supplier analysis only with approved supplier-reliability status and required manufacturer testing/identity controls. | Conditional reliance. |
| RCV-FR-025 | Incoming QC | Link required tests/specification, native QC or LIMS results and result versions. | Disposition evidence. |
| RCV-FR-026 | Release disposition | Authorized Quality transitions lot/container group to RELEASED only after required evidence/rules complete. | QC authority. |
| RCV-FR-027 | Reject disposition | Failed lot becomes REJECTED and is controlled under segregated status/location to prevent use. | 211.89 support. |
| RCV-FR-028 | Conditional/under-deviation use | Default disabled; if customer procedure permits exceptional use, require deviation, quality approval, bounded scope and explicit material eligibility rule. | Exception controlled. |
| RCV-FR-029 | Retest status | Material may transition to RETEST_DUE/QUARANTINE and requires reexamination/retest before continued use where required. | 211.87 support. |
| RCV-FR-030 | Partial lot disposition | Allow container-level partial release/reject only when sampling/spec/profile explicitly permits and genealogy remains exact. | No ambiguous status. |
| RCV-FR-031 | Receipt discrepancy | Over/short/damaged/wrong lot/document mismatch generates discrepancy workflow and ERP reconciliation. | Commercial/GxP synchronized. |
| RCV-FR-032 | Audit/export | Full receipt→quarantine→sample→QC→release/reject history is exportable. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (5 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `material_receipt` | 12 | PostgreSQL (GxP Core, authoritative) |
| `material_lot` | 13 | PostgreSQL (GxP Core, authoritative) |
| `material_container` | 7 | PostgreSQL (GxP Core, authoritative) |
| `sampling_order` | 6 | PostgreSQL (GxP Core, authoritative) |
| `material_quality_disposition` | 6 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (9):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /materials/v1/receipts` | yes | — |
| `POST /materials/v1/receipts/{id}/examine` | yes | — |
| `POST /materials/v1/lots/{id}/sampling-orders` | yes | — |
| `POST /sampling-orders/{id}/collect` | yes | — |
| `POST /materials/v1/lots/{id}/release` | yes | policy lookup (Doc 106) |
| `POST /materials/v1/lots/{id}/reject` | yes | policy lookup (Doc 106) |
| `POST /materials/v1/lots/{id}/retest` | yes | — |
| `GET /materials/v1/lots/{id}/quality-status` | no | — |
| `GET /materials/v1/lots/{id}/release-readiness` | no | policy lookup (Doc 106) |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (9):
| Event type | Producer | Dedupe key |
|---|---|---|
| `MaterialReceived` | SPEC-MAT-002A | event_id |
| `MaterialQuarantined` | SPEC-MAT-002A | event_id |
| `SamplingOrdered` | SPEC-MAT-002A | event_id |
| `SampleCollected` | SPEC-MAT-002A | event_id |
| `MaterialQCCompleted` | SPEC-MAT-002A | event_id |
| `MaterialReleased` | SPEC-MAT-002A | event_id |
| `MaterialRejected` | SPEC-MAT-002A | event_id |
| `MaterialRetestRequired` | SPEC-MAT-002A | event_id |
| `ReceiptDiscrepancyRaised` | SPEC-MAT-002A | event_id |

UI SURFACES:
- Expected Receipts
- Receiving
- Visual Examination
- Lot/Container Labeling
- Quarantine Dashboard
- Sampling
- QC/LIMS Status
- Quality Disposition
- Retest/Expiry Dashboard
- Receipt History

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
- correct receipt
- wrong supplier
- wrong manufacturer
- damaged seal
- missing COA
- quarantine issue attempt
- sampling selected containers
- identity test missing
- supplier COA permitted/not permitted
- release
- reject
- retest due
- partial container disposition
- ERP outage
- stale QA signature
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-04/Document_19_SPEC-MAT-002A_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-MAT-002A/<test_case_id>/`.
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
