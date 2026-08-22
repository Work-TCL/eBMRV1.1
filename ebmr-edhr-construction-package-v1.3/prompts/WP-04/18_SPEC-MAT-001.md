# Claude Code prompt — WP-04 / Document 18: Procurement & Supplier Quality Specification

TASK:
Implement the Procurement & Supplier Quality Specification module (SPEC-MAT-001) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_18_Procurement_Supplier_Quality_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: SUP-FR-001..032 (32)
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
contracts/openapi/spec-mat-001.yaml
contracts/events/spec-mat-001/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-mat-001/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| SUP-FR-001 | Supplier master | Maintain supplier legal identity, business name, addresses, sites, contacts, manufacturer-vs-distributor role, external IDs and lifecycle status. | One controlled supplier identity. |
| SUP-FR-002 | Manufacturer master | Separate actual manufacturer identity from commercial supplier/distributor where different. | Manufacturer genealogy exact. |
| SUP-FR-003 | Supplier qualification request | Initiate qualification for supplier/site/material category with scope, risk, requested evidence and owner. | Qualification controlled. |
| SUP-FR-004 | Supplier risk classification | Classify supplier/material criticality using released risk methodology and product/profile applicability. | Controls proportional. |
| SUP-FR-005 | Qualification evidence | Store questionnaire, certifications, licenses, audits, capability evidence, quality agreements, test history and attachments as versioned evidence. | Review basis retained. |
| SUP-FR-006 | Supplier audit | Plan/record audit scope, date, auditors, findings, response, CAPA/SCAR links and approval. | Supplier audit inspectable. |
| SUP-FR-007 | Supplier approval | Approve supplier for specific manufacturer site/material/specification/category/site/customer scope, not blanket global approval by default. | ASL granular. |
| SUP-FR-008 | Approved Supplier List | Maintain effective-dated supplier-material/site approval matrix with status Approved, Conditional, Suspended, Disqualified, Expired. | Procurement eligibility deterministic. |
| SUP-FR-009 | Requalification | Define expiry/review frequency/risk trigger; generate due alerts and block new procurement if policy requires. | Approval current. |
| SUP-FR-010 | Suspension | Quality can suspend supplier/material relationship with reason/signature; open PO/receipt impact assessed separately. | No silent continued use. |
| SUP-FR-011 | Disqualification | Permanent/controlled disqualification retains history and affected material/product impact. | Historical evidence preserved. |
| SUP-FR-012 | Conditional approval | Support temporary/conditional supplier use under defined scope, expiry, justification, enhanced inspection/testing and approval. | Exception bounded. |
| SUP-FR-013 | Quality agreement | Reference controlled quality agreement version, effective dates and obligations; renewal/expiry alerts. | Contract expectations linked. |
| SUP-FR-014 | Supplier change notification | Record supplier/manufacturer/process/material/site change notices and link to Change Control/impact assessment. | Supplier changes assessed. |
| SUP-FR-015 | Supplier performance | Track incoming acceptance, rejects, SCARs, complaints, deviations, delivery performance and quality metrics. | Requalification data driven. |
| SUP-FR-016 | SCAR initiation | Create supplier corrective-action request from incoming defect, deviation, audit or trend and track response/effectiveness. | QMS integration. |
| SUP-FR-017 | Material-source approval | Specific material/specification can have allowed supplier + manufacturer combinations and alternates. | Wrong source blocked. |
| SUP-FR-018 | Procurement item mapping | Map regulated material/spec version to purchasing description/code and ERP/native item without losing regulated identity. | Commercial/GxP identities separated. |
| SUP-FR-019 | Purchase requisition | Create PR with requesting site, material/spec version, quantity/UOM, need date, approved source requirements and project/batch reference if applicable. | Requirements exact. |
| SUP-FR-020 | PR approval | Configurable approval by amount/site/category plus quality gate for critical/unapproved source. | No buyer override. |
| SUP-FR-021 | RFQ | Optional RFQ to approved candidate suppliers, capturing commercial quote separately from qualification status. | Commercial comparison. |
| SUP-FR-022 | Supplier selection | Buyer may select only eligible supplier/manufacturer relationship unless controlled exception is approved. | ASL enforced. |
| SUP-FR-023 | Purchase order | PO includes exact regulated material/spec reference, supplier/manufacturer, quantity/UOM, delivery site and quality/document requirements. | Receipt expectations exact. |
| SUP-FR-024 | PO revision | Commercial changes versioned; regulated source/spec changes require revalidation/quality approval and may require new PO revision. | No silent source substitution. |
| SUP-FR-025 | COA/document requirement | PO may define required COA/CoC/test certificate/sterility certificate/document set. | Receipt completeness known. |
| SUP-FR-026 | Lot/document terms | PO can require supplier lot, manufacturer lot, manufacture/expiry/retest data and container identity information. | Traceability prepared. |
| SUP-FR-027 | ERP mode | If external ERP owns PR/RFQ/PO, eBMR receives validated references and enforces ASL/spec/source eligibility; ERP remains financial/commercial SoR. | Adapter boundary. |
| SUP-FR-028 | Native mode | If no ERP, native procurement supports PR/RFQ/PO and status without implementing GL/AP/tax settlement. | SME-ready. |
| SUP-FR-029 | Duplicate supplier detection | Detect likely duplicate legal/manufacturer identities before creation; merge prohibited without controlled data-management procedure. | Master quality. |
| SUP-FR-030 | Supplier document expiry | Alert certificates/agreements/audits nearing expiry and evaluate whether they affect eligibility. | No stale qualification. |
| SUP-FR-031 | Procurement audit | Audit source selection, approval, PO regulated-field changes, exceptions and external synchronization. | Traceable purchasing. |
| SUP-FR-032 | Inspection export | Provide supplier qualification/ASL/SCAR/audit/performance history for authorized review. | Inspection-ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (6 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `supplier` | 9 | PostgreSQL (GxP Core, authoritative) |
| `supplier_site` | 5 | PostgreSQL (GxP Core, authoritative) |
| `supplier_qualification` | 10 | PostgreSQL (GxP Core, authoritative) |
| `approved_supplier_material` | 8 | PostgreSQL (GxP Core, authoritative) |
| `purchase_requisition` | 5 | PostgreSQL (GxP Core, authoritative) |
| `purchase_order_ref` | 6 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (10):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /suppliers/v1` | yes | — |
| `POST /suppliers/{id}/qualifications` | yes | — |
| `POST /supplier-qualifications/{id}/approve` | yes | policy lookup (Doc 106) |
| `POST /supplier-material-approvals` | yes | — |
| `POST /supplier-material-approvals/{id}/suspend` | yes | — |
| `GET /materials/{specId}/eligible-suppliers?site=...` | no | — |
| `POST /procurement/v1/requisitions` | yes | — |
| `POST /procurement/v1/purchase-orders` | yes | — |
| `POST /procurement/v1/purchase-orders/{id}/revise` | yes | — |
| `GET /procurement/v1/purchase-orders/{po}/receipt-expectation` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (7):
| Event type | Producer | Dedupe key |
|---|---|---|
| `SupplierQualificationApproved` | SPEC-MAT-001 | event_id |
| `SupplierMaterialApproved` | SPEC-MAT-001 | event_id |
| `SupplierSuspended` | SPEC-MAT-001 | event_id |
| `SupplierDisqualified` | SPEC-MAT-001 | event_id |
| `PurchaseRequisitionApproved` | SPEC-MAT-001 | event_id |
| `PurchaseOrderIssued` | SPEC-MAT-001 | event_id |
| `PurchaseOrderRegulatedFieldsChanged` | SPEC-MAT-001 | event_id |

UI SURFACES:
- Supplier Catalogue
- Supplier Qualification
- Supplier Audit
- Approved Supplier List
- Material/Source Matrix
- Supplier Performance
- SCAR Links
- RFQ/Quote Comparison
- PO Regulated Requirements
- Supplier Quality Dashboard

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
- approved supplier PO
- unapproved source blocked
- supplier approval expires
- conditional source
- distributor vs manufacturer mismatch
- PO revision changes source
- expired certificate
- duplicate external callback
- supplier suspended with open PO
- ERP unavailable
- native procurement mode
- audit/export
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-04/Document_18_SPEC-MAT-001_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-MAT-001/<test_case_id>/`.
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
