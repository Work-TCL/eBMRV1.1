# Claude Code prompt — WP-03 / Document 13: Genealogy & Traceability Engine Specification

TASK:
Implement the Genealogy & Traceability Engine Specification module (SPEC-EBMR-004) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_13_Genealogy_Traceability_Engine_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: GEN-FR-001..030 (30)
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
- `services/gxp-api/src/modules/ebmr` and its tests
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
services/gxp-api/src/modules/ebmr/src/            # domain services, command handlers, repositories
services/gxp-api/src/modules/ebmr/migrations/     # owned entities only
services/gxp-api/src/modules/ebmr/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-ebmr-004.yaml
contracts/events/spec-ebmr-004/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-ebmr-004/
```

REQUIREMENTS TO IMPLEMENT (30):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| GEN-FR-001 | Canonical genealogy entity | Represent supplier/material lot/container, drug batch, intermediate, device component lot/serial, device unit, combination lot/serial, package and distribution reference as typed genealogy nodes. | Common trace model. |
| GEN-FR-002 | Typed relationships | Use controlled edge types such as CONTAINS, DERIVED_FROM, CONSUMED_IN, ASSEMBLED_INTO, PACKAGED_AS, FILLED_INTO, TESTED_BY, STERILIZED_IN, DISTRIBUTED_AS. | Meaning explicit. |
| GEN-FR-003 | Forward trace | Given source material/component/drug batch, return all directly/indirectly affected intermediates/final lots/serials/packages. | Recall impact. |
| GEN-FR-004 | Backward trace | Given final lot/serial, return all source materials/components/drug/device lots, operations and equipment evidence. | Investigation. |
| GEN-FR-005 | Container-level trace | Track internal material container identity where dispensing/partial use matters. | Exact source. |
| GEN-FR-006 | Quantity on edge | Store consumed/produced quantity + UOM for material transformation relationships where applicable. | Mass/quantity genealogy. |
| GEN-FR-007 | Step provenance | Edge can reference batch step/operation that created relationship. | Process context. |
| GEN-FR-008 | Version/hash provenance | Node/edge references exact authoritative record/version and source event. | No mutable pointer. |
| GEN-FR-009 | Drug-device compatibility | Final DDCP genealogy records exact constituent compatibility version used. | Pairing evidence. |
| GEN-FR-010 | Serial relationship | Support component serial → device serial → combination-product serial. | Unit trace. |
| GEN-FR-011 | Lot-to-serial scale | Efficiently represent many serials consuming same lot without unbounded duplicated metadata. | Scale. |
| GEN-FR-012 | Package hierarchy | Represent unit → carton → shipper/pallet/package aggregation where required. | Distribution/recall. |
| GEN-FR-013 | Distribution reference | Link released product lot/serial/package to ERP/WMS shipment/distribution reference without making ERP record genealogy truth. | Downstream trace. |
| GEN-FR-014 | Rework relationship | Record REWORKED_FROM/SUPERSEDES relationships preserving original identity. | History. |
| GEN-FR-015 | Split/merge | Support one lot split into many, many materials into one batch, subassemblies merged into final unit. | Manufacturing transformations. |
| GEN-FR-016 | No arbitrary deletion | Genealogy nodes/edges from regulated execution are immutable facts; corrections append superseding/voiding relationship metadata. | Trace cannot disappear. |
| GEN-FR-017 | Correction | If erroneous link was recorded, correction marks original as invalid/superseded through controlled event and adds correct edge; original remains. | Audit. |
| GEN-FR-018 | Recall query | Query affected final products, inventory, released/distributed references and quality events from any source node. | Field action support. |
| GEN-FR-019 | Complaint query | Serial/lot complaint query retrieves full manufacturing/constituent history and related prior complaints/events. | Investigation. |
| GEN-FR-020 | Supplier impact | Supplier/manufacturer lot can identify internal lots and finished product impact. | Supplier quality. |
| GEN-FR-021 | Equipment correlation | Optionally associate operations with actual equipment, but do not model equipment as material ancestry unless semantically appropriate. | Process evidence. |
| GEN-FR-022 | Evidence links | Node/edge can reference COA, test report, assembly/test evidence, sterilization evidence. | Complete context. |
| GEN-FR-023 | Graph consistency | Prevent invalid edge classes, self-relationships, impossible product type transitions and duplicate exact edges. | Semantic integrity. |
| GEN-FR-024 | Cycle handling | Material/product ancestry should normally be acyclic; rework/correction relationships are separately typed to avoid misleading ancestry cycles. | Trace algorithm safe. |
| GEN-FR-025 | Traversal depth | Support bounded/unbounded authorized traversals with protection against runaway queries. | Performance/security. |
| GEN-FR-026 | Affected scope snapshot | Recall/impact assessment can save a versioned result set with query criteria, graph version/cutoff and reviewer signature. | Investigation reproducible. |
| GEN-FR-027 | External mapping | ERP/LIMS source IDs linked to nodes as provenance but internal genealogy IDs remain authoritative. | Vendor independence. |
| GEN-FR-028 | Import/migration | Migrated genealogy identifies source system/migration batch and preserves source checksum. | Historical provenance. |
| GEN-FR-029 | Performance | Target common single-serial backward trace under interactive latency and large-lot forward impact through indexed traversal/materialized helper tables. | Usable at scale. |
| GEN-FR-030 | Export | Generate structured genealogy JSON/CSV and human-readable trace report with node/edge evidence. | Inspection/recall ready. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (2 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `genealogy_node` | 10 | PostgreSQL (GxP Core, authoritative) |
| `genealogy_edge` | 12 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (8):
| Operation | State-changing | Signature |
|---|---|---|
| `GET /genealogy/v1/nodes/lookup?...` | no | — |
| `GET /genealogy/v1/nodes/{id}/ancestors` | no | — |
| `GET /genealogy/v1/nodes/{id}/descendants` | no | — |
| `GET /genealogy/v1/serial/{serial}/full-trace` | no | — |
| `GET /genealogy/v1/material-lot/{lot}/affected-products` | no | — |
| `POST /genealogy/v1/impact-assessments` | yes | — |
| `GET /genealogy/v1/impact-assessments/{id}` | no | — |
| `POST /genealogy/v1/exports` | yes | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (5):
| Event type | Producer | Dedupe key |
|---|---|---|
| `GenealogyNodeCreated` | SPEC-EBMR-004 | event_id |
| `GenealogyEdgeCreated` | SPEC-EBMR-004 | event_id |
| `GenealogyEdgeCorrected` | SPEC-EBMR-004 | event_id |
| `ImpactAssessmentCreated` | SPEC-EBMR-004 | event_id |
| `ImpactAssessmentApproved` | SPEC-EBMR-004 | event_id |

UI SURFACES:
- Genealogy Search
- Interactive Trace Tree/Graph
- Material Lot Impact
- Serial History
- DDCP Constituent View
- Recall Impact Assessment
- Saved/Approved Impact Snapshot
- Export

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
- simple material→batch
- drug batch→device serial
- many component lots
- split/merge
- partial container
- rework
- wrong edge correction
- cycle protection
- tenant isolation
- 100k serial affected query
- saved recall impact
- migration provenance
- package hierarchy
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-03/Document_13_SPEC-EBMR-004_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EBMR-004/<test_case_id>/`.
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
