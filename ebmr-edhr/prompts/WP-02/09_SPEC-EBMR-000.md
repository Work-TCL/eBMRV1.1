# Claude Code prompt — WP-02 / Document 09: Product, Constituent & Regulatory Profile Master

TASK:
Implement the Product, Constituent & Regulatory Profile Master module (SPEC-EBMR-000) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_09_Product_Constituent_Regulatory_Profile_Master_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: PRD-FR-001..032 (32)
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
contracts/openapi/spec-ebmr-000.yaml
contracts/events/spec-ebmr-000/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-ebmr-000/
```

REQUIREMENTS TO IMPLEMENT (32):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| PRD-FR-001 | Product master | Create controlled product identity with immutable internal ID, business code, marketed/internal names, lifecycle state, product family, dosage/device form, strength/configuration, manufacturing profile, and site applicability. | Product can be uniquely referenced across recipes, batches, QC, genealogy and release. |
| PRD-FR-002 | Product lifecycle | Support Draft, Under Review, Approved/Released, Effective, Suspended, Obsolete, Superseded. Released product versions are immutable. | Obsolete/suspended product cannot start new production unless controlled exception policy permits. |
| PRD-FR-003 | Product version | Product changes create a new version with effective dating and Vault release; historical batches remain linked to prior version. | No silent historical drift. |
| PRD-FR-004 | Constituent model | A DDCP product may contain Drug, Device, Biologic, HCT/P or Other constituent types; V1 actively supports Drug + Device and structurally supports later profiles. | Combination product is not represented as two unrelated masters. |
| PRD-FR-005 | Constituent role | Record primary/secondary constituent role, manufacturer/site source, business identity, exact version, lot/serial strategy and regulated handoff requirements. | Cross-constituent evidence can be validated. |
| PRD-FR-006 | Combination-product type | Support Single Entity, Co-Packaged and Cross-Labeled/Other relationship metadata as controlled product attributes; exact regulatory applicability remains customer/regulatory decision. | Workflow can distinguish product relationship type. |
| PRD-FR-007 | PMOA metadata | Store customer-approved PMOA/lead-center/regulatory-context reference without software deciding PMOA. | Product does not infer regulatory classification. |
| PRD-FR-008 | Part 4 operating-system profile | Store customer-approved compliance approach/profile reference and applicable supplementary control set. | Release/rules can select applicable profile. |
| PRD-FR-009 | Manufacturing profile | Assign one or more controlled manufacturing profiles: Injectable DDCP, Inhalation DDCP, Drug-Eluting/Coated Device, Device, Pharma, future extensions. | Recipe authoring can inherit valid process capabilities. |
| PRD-FR-010 | Sterile/aseptic applicability | Flag whether sterile/aseptic controls apply and reference released sterile-process profile rather than free-text setting. | Sterile-required product cannot use non-sterile recipe path. |
| PRD-FR-011 | Lot/serial strategy | Configure finished lot, device lot, unit serial, combination-product serial, or hybrid genealogy strategy. | Execution creates required identifiers. |
| PRD-FR-012 | UDI applicability | Configure UDI requirement, issuing-agency metadata, DI rules, production-identifier sources and packaging-level requirements where applicable. | Device/combination records support UDI capture. |
| PRD-FR-013 | Drug batch identity strategy | Configure drug batch/lot identification and whether final product shares or differs from drug-constituent batch identity. | Genealogy remains explicit. |
| PRD-FR-014 | Strength/concentration | Represent drug strength/concentration using structured quantity + UOM and product-specific calculation metadata. | No free-text-only strength. |
| PRD-FR-015 | Device configuration | Represent device model/configuration/version and compatible drug constituent constraints. | Wrong device configuration cannot be paired. |
| PRD-FR-016 | Constituent compatibility | Release controlled compatibility versions specifying allowed exact drug/device constituent combinations and critical interface constraints. | Final DDCP issue checks compatibility. |
| PRD-FR-017 | Packaging configuration | Reference released packaging hierarchy/configuration and label profile by product/version. | Packaging module uses exact approved configuration. |
| PRD-FR-018 | Shelf-life/expiration profile | Reference released expiration/stability policy; product master does not hard-code computed expiration logic. | Expiration is rule/profile driven. |
| PRD-FR-019 | Storage conditions | Reference structured storage/environment requirements and acceptable ranges. | Warehouse and batch rules can evaluate conditions. |
| PRD-FR-020 | Material/BOM relationship | Reference approved material/component structures; material specification versions remain separate controlled objects. | Product version does not duplicate mutable material specs. |
| PRD-FR-021 | Quality specification links | Reference released finished/in-process/device test specifications and sampling profiles. | QC receives correct requirements. |
| PRD-FR-022 | Equipment/process class requirements | Reference allowed equipment/process classes and special validation requirements. | Recipe validation checks compatibility. |
| PRD-FR-023 | Site admission | Product version has approved manufacturing/packaging/release sites and optional contract-manufacturing relationships. | Unauthorized site cannot issue batch. |
| PRD-FR-024 | Regulatory attribute provenance | Critical regulatory profile fields store source/decision reference, approver and effective version. | Audit can show basis of configuration. |
| PRD-FR-025 | Product change impact | Changing regulated product attributes triggers impact assessment for recipes, specs, labels, QC, validation, inventory, open batches and genealogy. | Downstream affected objects identified. |
| PRD-FR-026 | Clone/template creation | Allow draft clone from approved family/template, but cloned product receives new identity and requires full review/release. | No inherited approval. |
| PRD-FR-027 | Search/filter | Search by code, name, constituent type, manufacturing profile, site, lifecycle, UDI DI, device model, strength. | Operational usability. |
| PRD-FR-028 | API/integration mapping | Maintain external-system IDs for ERP/LIMS/label systems without using external ID as internal primary key. | ERP mappings do not contaminate domain identity. |
| PRD-FR-029 | Product suspension | Quality may suspend future issue with reason/signature while preserving active/in-process batch policy separately. | Suspension does not rewrite past batches. |
| PRD-FR-030 | Inspection export | Produce human-readable product/profile/version report with constituents, applicability, approved sites, labels/spec references and release signatures. | Controlled master can be reviewed externally. |
| PRD-FR-031 | Configuration completeness | Before product release, validate mandatory attributes based on active manufacturing/regulatory profile. | Incomplete DDCP cannot release. |
| PRD-FR-032 | Profile admission gate | Unsupported specialist context (e.g. biologic-specific or unsupported implantable/connected-device profile) fails closed unless corresponding profile package is approved. | Configuration cannot enable unsupported scope. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
_none declared in the source specifications_

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (6 entities owned by this module):
| Entity | Fields defined | Authoritative store |
|---|---|---|
| `product_family` | 6 | PostgreSQL (GxP Core, authoritative) |
| `product_version` | 25 | PostgreSQL (GxP Core, authoritative) |
| `product_constituent` | 9 | PostgreSQL (GxP Core, authoritative) |
| `constituent_compatibility_version` | 11 | PostgreSQL (GxP Core, authoritative) |
| `product_site_admission` | 6 | PostgreSQL (GxP Core, authoritative) |
| `product_external_mapping` | 5 | PostgreSQL (GxP Core, authoritative) |

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (11):
| Operation | State-changing | Signature |
|---|---|---|
| `POST /products/v1/drafts` | yes | — |
| `PUT /products/v1/drafts/{id}` | yes | — |
| `POST /products/v1/drafts/{id}/submit` | yes | — |
| `POST /products/v1/drafts/{id}/release` | yes | policy lookup (Doc 106) |
| `POST /products/v1/{id}/suspend` | yes | — |
| `POST /products/v1/{id}/reinstate` | yes | — |
| `GET /products/v1/{businessId}/versions` | no | — |
| `GET /products/v1/{id}` | no | — |
| `POST /products/v1/{id}/validate-completeness` | yes | — |
| `GET /products/v1/{id}/compatibility` | no | — |
| `GET /products/v1/{id}/issue-eligibility?site=...` | no | — |

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (8):
| Event type | Producer | Dedupe key |
|---|---|---|
| `ProductDraftSubmitted` | SPEC-EBMR-000 | event_id |
| `ProductVersionReleased` | SPEC-EBMR-000 | event_id |
| `ProductVersionEffective` | SPEC-EBMR-000 | event_id |
| `ProductVersionSuspended` | SPEC-EBMR-000 | event_id |
| `ProductVersionReinstated` | SPEC-EBMR-000 | event_id |
| `ProductVersionSuperseded` | SPEC-EBMR-000 | event_id |
| `ConstituentCompatibilityReleased` | SPEC-EBMR-000 | event_id |
| `ProductSiteAdmissionChanged` | SPEC-EBMR-000 | event_id |

UI SURFACES:
- Product Catalogue
- Product Version Editor
- Constituent Builder
- DDCP Compatibility Matrix
- Regulatory/Manufacturing Profile
- Site Admission
- Specifications & Packaging Links
- Release Readiness Checklist
- Version Comparison
- Product Audit / History

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
- basic drug+device product release
- missing constituent
- incompatible constituents
- future effective date
- suspended product
- wrong manufacturing site
- clone does not inherit approval
- product change creates version
- old batch resolves old product version
- UDI-required profile incomplete
- sterile-required profile missing
- concurrent product update
- external mapping duplicate
- unauthorized release
- release signature stale after draft change
- export/version comparison
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-02/Document_09_SPEC-EBMR-000_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-EBMR-000/<test_case_id>/`.
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
- product/constituent schemas are frozen
- DDCP compatibility model supports injectable reference profile
- site admission and product issue-eligibility are tested
- Vault integration is proven
- no batch can issue against mutable Frappe product draft
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
