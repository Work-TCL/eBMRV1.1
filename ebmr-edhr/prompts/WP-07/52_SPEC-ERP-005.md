# Claude Code prompt — WP-07 / Document 52: Master Data Synchronization, Mapping & Reconciliation

TASK:
Implement the Master Data Synchronization, Mapping & Reconciliation module (SPEC-ERP-005) exactly as specified.

SOURCE OF TRUTH:
- `specs/Documents_01_105/Document_52_Master_Data_Synchronization_Mapping_Reconciliation_v1_0_IMPLEMENTATION_READY.md`
- Requirement IDs: MDS-FR-001..028 (28)
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
- `services/integration-gateway` and its tests
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
services/integration-gateway/src/            # domain services, command handlers, repositories
services/integration-gateway/migrations/     # owned entities only
services/integration-gateway/test/           # unit, integration, negative, concurrency
contracts/openapi/spec-erp-005.yaml
contracts/events/spec-erp-005/*.json
apps/ebmr_frappe/ebmr/…          # screens listed below (read-only projected GxP fields)
validation/requirements/spec-erp-005/
```

REQUIREMENTS TO IMPLEMENT (28):
| ID | Requirement | Required behaviour | Acceptance intent |
|---|---|---|---|
| MDS-FR-001 | Master-data catalogue | Define synchronized object types: commercial item, regulated product mapping, material item, supplier, site/plant, warehouse/location, UOM, reason/movement code, cost center/project refs as applicable. | Controlled scope. |
| MDS-FR-002 | Field ownership | Every synchronized field explicitly owned by GxP or ERP; BIDIRECTIONAL ownership disallowed for same semantic field unless conflict policy approved. | No conflict. |
| MDS-FR-003 | Mapping status | UNMAPPED, PROPOSED, ACTIVE, CONFLICT, SUSPENDED, RETIRED. | Explicit. |
| MDS-FR-004 | Initial sync | Bulk initial import uses staging, validation and reconciliation before activation. | Safe onboarding. |
| MDS-FR-005 | Incremental sync | Timestamp/change-token/event/poll strategy vendor-specific but canonical processing identical. | Ongoing sync. |
| MDS-FR-006 | External change detection | ERP-owned field changes update projection; GxP-owned field changes from ERP create conflict, not overwrite. | Ownership. |
| MDS-FR-007 | GxP change propagation | Approved GxP-owned projection can be sent outward only if provider profile supports it. | Controlled. |
| MDS-FR-008 | Identity matching | Prefer explicit external IDs; name/fuzzy match only proposes mapping for human review. | No wrong master link. |
| MDS-FR-009 | Duplicate detection | Detect duplicate external/internal mappings and block activation. | Integrity. |
| MDS-FR-010 | UOM mapping | UOM equivalency/conversion approved/versioned; unknown UOM quarantines record. | Quantity safety. |
| MDS-FR-011 | Plant/site mapping | ERP plant/org/company/location context maps exactly to tenant/site. | Isolation. |
| MDS-FR-012 | Warehouse mapping | Warehouse/bin/subinventory location mapping explicit and effective-dated. | Logistics. |
| MDS-FR-013 | Supplier mapping | Commercial supplier identity mapping distinct from GxP manufacturer/approved source status. | Quality. |
| MDS-FR-014 | Product/material mapping | External item maps to exact internal business identity/version policy, never “latest regulated version” dynamically during historical execution. | History. |
| MDS-FR-015 | Reference-data mapping | Movement type/reason code/status reference values versioned by ERP instance. | Adapter semantics. |
| MDS-FR-016 | Effective dates | Mappings can be future-effective and historical mappings remain for old transactions. | Reproducibility. |
| MDS-FR-017 | Suspension | Suspend mapping on discovered mismatch without deleting history. | Containment. |
| MDS-FR-018 | Conflict queue | Structured differences with owner/source/current/proposed values and resolution action. | Governance. |
| MDS-FR-019 | Approval | Critical identity/UOM/site mappings require integration/data-owner approval; quality-critical mappings may require QA/validation. | Controlled. |
| MDS-FR-020 | Bulk approval restriction | High-risk mappings cannot be blanket-approved without review profile. | Safety. |
| MDS-FR-021 | Mapping hash/version | Every integration transaction records mapping version/hash used. | Investigation. |
| MDS-FR-022 | Sync checkpoint | Persist external change cursor/watermark per entity/instance. | Restart safe. |
| MDS-FR-023 | Replay | Reprocess same inbound master event idempotently. | Replay safe. |
| MDS-FR-024 | Delete semantics | External deletion/deactivation maps to inactive/suspended projection; never physically deletes GxP-linked master history. | History. |
| MDS-FR-025 | Reconciliation | Scheduled object counts/key fields/active mapping differences. | Detect drift. |
| MDS-FR-026 | Data quality metrics | Unmapped, conflict, stale, failed sync and duplicate rates visible. | Operability. |
| MDS-FR-027 | Audit | Mapping create/change/approve/suspend/merge and conflict resolution audited. | Trace. |
| MDS-FR-028 | Migration | Customer onboarding mapping/import package retained with source checksum and approval. | Provenance. |

FUNCTIONS / SERVICES (from the specification's contract catalogue):
| Function | Caller/trigger | Inputs | Output | Events / errors / tests |
|---|---|---|---|---|
| stageInboundMasterRecords() | ERP poll/webhook/bulk import | entity_type; raw records; source cursor; instance | StagingBatchReceipt | MasterDataStaged; MASTER_SCHEMA_INVALID |
| normalizeMasterRecord() | Sync processor | staging_record; mapping_profile_version | NormalizedExternalMaster | MASTER_NORMALIZATION_FAILED |
| matchInternalEntity() | Sync processor/admin | normalized external master; entity type | MasterMatchResult | MASTER_MATCH_AMBIGUOUS |
| proposeMapping() | Sync processor/admin | external_ref; internal_ref; evidence; confidence | MappingProposal | MasterMappingProposed |
| approveMapping() | Data Owner/QA if required | mapping_id; expected_version; signature if policy | ActiveMapping | MasterMappingActivated |
| applyERPProjectionUpdate() | Sync processor | normalized record; active mapping | ProjectionUpdateResult | ERPProjectionUpdated/MasterConflictRaised |
| raiseMasterConflict() | Sync processor | entity/mapping; field diffs; source versions | MasterConflict | MasterDataConflictDetected |
| resolveMasterConflict() | Data Owner | conflict_id; resolution; reason; approvals | ConflictResolution | MasterConflictResolved |
| advanceSyncCheckpoint() | Sync worker | instance/entity; cursor/watermark; batch_id | SyncCheckpoint | SyncCheckpointAdvanced |
| reconcileMasterMappings() | Scheduled/admin | instance; entity_type; scope | MasterReconciliationReport | MasterReconciliationMismatchDetected |

For every function above and every function derived from the API list, specify and implement:
name/ID, purpose, caller, typed inputs, validation/preconditions, authorization + qualification + SoD,
signature requirement (from the Document 106 policy set), processing rules, DB reads, DB writes,
transaction boundary, output type, emitted events, errors, idempotency and concurrency behaviour.

DATA MODEL (0 entities owned by this module):
_none declared in the source specifications_

Every regulated table carries `id, tenant_id, site_id, state, version, created_at, updated_at`,
a retention class (Document 108) and row-level tenant scoping.

APIS (0):
_none declared in the source specifications_

State-changing operations require `expected_version` and `idempotency_key` and return a MutationReceipt.

EVENTS (0):
_none declared in the source specifications_

UI SURFACES:
- none declared

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
- initial 100k item import
- duplicate external item
- supplier same name different legal entity
- GxP-owned field changed in ERP
- unknown UOM
- wrong plant/site
- mapping future effective
- external item deactivated
- replay same import batch
- conflict resolution stale version
- sync cursor crash/restart
Plus mandatory: unauthorized user, wrong site, expired qualification, invalid transition, stale version,
duplicate submission, missing reason, missing signature, dependency outage, concurrency on the same aggregate.

TEST CASES TO EXECUTE (mandatory — do not invent your own instead):
- Test case book: `test-cases/WP-07/Document_52_SPEC-ERP-005_TEST_CASES.md`
- Every case in that book must be executed and its result recorded in
  `test-cases/TEST_CASE_LIBRARY.csv` (columns: status, executed_by, executed_at, actual_result,
  defect_reference).
- P1 cases are blocking: the module cannot advance past INTEGRATION_TESTED with any P1 case unexecuted.
- Negative, security, concurrency and failure cases are not optional. A control that has never been
  observed refusing has not been tested.
- Capture the evidence named in each case into `validation/evidence/<stage>/SPEC-ERP-005/<test_case_id>/`.
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
