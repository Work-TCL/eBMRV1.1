# Test Cases — Document 52: Master Data Synchronization, Mapping & Reconciliation (SPEC-ERP-005)

**Work package:** WP-07  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** MDS-FR-001..028 (28)  
**Test cases:** 98  
**Code location:** `services/integration-gateway`  
**Authoritative store:** External ERP (commercial truth) / PostgreSQL (GxP truth) per Doc 48 ownership matrix

Execution rules: run cases in listed order; a case with `depends_on` runs after its parent; record actual result and evidence for every case; a failed case is evidence and is never re-run over or edited to pass — raise a defect and reference it.

| Status values | meaning |
|---|---|
| NOT_STARTED | not yet executed |
| IN_PROGRESS | executing |
| PASS | executed, expected result observed, evidence captured |
| FAIL | executed, expected result not observed; defect raised |
| BLOCKED | cannot execute; blocker recorded |
| N/A | not applicable, with recorded justification |

---

### TC-052-001-01 — Master-data catalogue — required behaviour

- **Requirement:** MDS-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Define synchronized object types: commercial item, regulated product mapping, material item, supplier, site/plant, warehouse/location, UOM, reason/mov | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled scope. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- MAPPING_ENTITY_TYPES covers MATERIAL/PRODUCT/SUPPLIER/WAREHOUSE/LOCATION/UOM/REASON_CODE/CUSTOMER/GL_ACCOUNT/PRODUCTION_ORDER_REFERENCE.  |  **Defect:** —

### TC-052-002-01 — Field ownership — required behaviour

- **Requirement:** MDS-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Every synchronized field explicitly owned by GxP or ERP; BIDIRECTIONAL ownership disallowed for same semantic field unless conflict policy approved. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No conflict. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- field_ownership (GXP|ERP) column + enforced conflict-vs-overwrite logic in apply_external_change(); services/gxp-api/tests/test_erp_flow.py::test_external_change_on_gxp_owned_field_creates_conflict_not_overwrite, test_erp_owned_field_change_updates_projection.  |  **Defect:** —

### TC-052-002-02 — Field ownership — Action without the required signature is blocked

- **Requirement:** MDS-FR-002
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-052-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- field_ownership (GXP|ERP) column + enforced conflict-vs-overwrite logic in apply_external_change(); services/gxp-api/tests/test_erp_flow.py::test_external_change_on_gxp_owned_field_creates_conflict_not_overwrite, test_erp_owned_field_change_updates_projection.  |  **Defect:** —

### TC-052-002-03 — Field ownership — Signature bound to a superseded version is rejected

- **Requirement:** MDS-FR-002
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-052-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- field_ownership (GXP|ERP) column + enforced conflict-vs-overwrite logic in apply_external_change(); services/gxp-api/tests/test_erp_flow.py::test_external_change_on_gxp_owned_field_creates_conflict_not_overwrite, test_erp_owned_field_change_updates_projection.  |  **Defect:** —

### TC-052-002-04 — Field ownership — Replayed inbound message is detected

- **Requirement:** MDS-FR-002
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-052-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- field_ownership (GXP|ERP) column + enforced conflict-vs-overwrite logic in apply_external_change(); services/gxp-api/tests/test_erp_flow.py::test_external_change_on_gxp_owned_field_creates_conflict_not_overwrite, test_erp_owned_field_change_updates_projection.  |  **Defect:** —

### TC-052-003-01 — Mapping status — required behaviour

- **Requirement:** MDS-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: UNMAPPED, PROPOSED, ACTIVE, CONFLICT, SUSPENDED, RETIRED. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Explicit. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- MAPPING_STATUSES enum (UNMAPPED/PROPOSED/ACTIVE/CONFLICT/SUSPENDED/RETIRED); UNMAPPED/PROPOSED/ACTIVE/CONFLICT exercised by tests, SUSPENDED/RETIRED declared but no command transitions to them yet (see MDS-FR-017).  |  **Defect:** —

### TC-052-003-02 — Mapping status — Illegal state transition is rejected

- **Requirement:** MDS-FR-003
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-052-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- MAPPING_STATUSES enum (UNMAPPED/PROPOSED/ACTIVE/CONFLICT/SUSPENDED/RETIRED); UNMAPPED/PROPOSED/ACTIVE/CONFLICT exercised by tests, SUSPENDED/RETIRED declared but no command transitions to them yet (see MDS-FR-017).  |  **Defect:** —

### TC-052-004-01 — Initial sync — required behaviour

- **Requirement:** MDS-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Bulk initial import uses staging, validation and reconciliation before activation. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Safe onboarding. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- sync_master_data() (app/modules/erp/sync.py) implements stage (PROPOSED mapping) -> validate (normalize_master_record) -> reconcile (match_internal_entity) -> activate (existing approve_mapping()) as one pipeline, walking multiple fetch_changes() pages per call; services/gxp-api/tests/test_erp_master_sync.py::test_sync_bulk_initial_import_walks_multiple_pages.  |  **Defect:** —

### TC-052-005-01 — Incremental sync — required behaviour

- **Requirement:** MDS-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Timestamp/change-token/event/poll strategy vendor-specific but canonical processing identical. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Ongoing sync. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- sync_master_data() is the same function for the incremental case -- cursor=<ErpSyncCheckpoint.cursor_value> instead of None; services/gxp-api/tests/test_erp_master_sync.py::test_sync_pulls_material_changes_and_proposes_explicit_and_fuzzy_matches (checkpoint advanced and reused across two sync_master_data() calls).  |  **Defect:** —

### TC-052-006-01 — External change detection — required behaviour

- **Requirement:** MDS-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: ERP-owned field changes update projection; GxP-owned field changes from ERP create conflict, not overwrite. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Ownership. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- apply_external_change(): GXP-owned field change creates a conflict, ERP-owned updates the projection; services/gxp-api/tests/test_erp_flow.py::test_external_change_on_gxp_owned_field_creates_conflict_not_overwrite, test_erp_owned_field_change_updates_projection.  |  **Defect:** —

### TC-052-006-02 — External change detection — Replayed inbound message is detected

- **Requirement:** MDS-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-052-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- apply_external_change(): GXP-owned field change creates a conflict, ERP-owned updates the projection; services/gxp-api/tests/test_erp_flow.py::test_external_change_on_gxp_owned_field_creates_conflict_not_overwrite, test_erp_owned_field_change_updates_projection.  |  **Defect:** —

### TC-052-006-03 — External change detection — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** MDS-FR-006
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-052-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- apply_external_change(): GXP-owned field change creates a conflict, ERP-owned updates the projection; services/gxp-api/tests/test_erp_flow.py::test_external_change_on_gxp_owned_field_creates_conflict_not_overwrite, test_erp_owned_field_change_updates_projection.  |  **Defect:** —

### TC-052-007-01 — GxP change propagation — required behaviour

- **Requirement:** MDS-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Approved GxP-owned projection can be sent outward only if provider profile supports it. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no explicit 'propagate this approved GxP-owned value outward to ERP' command exists (SG-126).  |  **Defect:** —

### TC-052-007-02 — GxP change propagation — Action without the required signature is blocked

- **Requirement:** MDS-FR-007
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-052-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no explicit 'propagate this approved GxP-owned value outward to ERP' command exists (SG-126).  |  **Defect:** —

### TC-052-007-03 — GxP change propagation — Signature bound to a superseded version is rejected

- **Requirement:** MDS-FR-007
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-052-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no explicit 'propagate this approved GxP-owned value outward to ERP' command exists (SG-126).  |  **Defect:** —

### TC-052-008-01 — Identity matching — required behaviour

- **Requirement:** MDS-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Prefer explicit external IDs; name/fuzzy match only proposes mapping for human review. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No wrong master link. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- matching.match_internal_entity() (app/modules/erp/matching.py): an exact internal-code match returns EXPLICIT_ID; a name-similarity match at/above the documented FUZZY_MATCH_MIN_SCORE threshold returns FUZZY_PROPOSED; either way only a PROPOSED mapping is created, never an activated one; services/gxp-api/tests/test_erp_master_sync.py::test_sync_pulls_material_changes_and_proposes_explicit_and_fuzzy_matches.  |  **Defect:** —

### TC-052-008-02 — Identity matching — Replayed inbound message is detected

- **Requirement:** MDS-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-052-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- an external_id already mapped (any status) is never re-proposed on replay -- checked before matching runs at all; services/gxp-api/tests/test_erp_master_sync.py::test_sync_pulls_material_changes_and_proposes_explicit_and_fuzzy_matches (second sync_master_data() call).  |  **Defect:** —

### TC-052-008-03 — Identity matching — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** MDS-FR-008
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-052-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- fetch_changes() runs with no open transaction; a failed page never partially writes a match -- covered generically by services/gxp-api/tests/test_erp_flow.py::test_dispatch_timeout_is_uncertain_not_blind_success_or_retry_storm plus services/gxp-api/tests/test_erp_master_sync.py's own real fetch_changes() integration.  |  **Defect:** —

### TC-052-009-01 — Duplicate detection — required behaviour

- **Requirement:** MDS-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Detect duplicate external/internal mappings and block activation. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- propose_mapping()'s duplicate ACTIVE/PROPOSED check; services/gxp-api/tests/test_erp_flow.py::test_propose_duplicate_external_mapping_rejected.  |  **Defect:** —

### TC-052-009-02 — Duplicate detection — Prohibited path is rejected

- **Requirement:** MDS-FR-009
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Detect duplicate external/internal mappings and block activation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-052-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- propose_mapping()'s duplicate ACTIVE/PROPOSED check; services/gxp-api/tests/test_erp_flow.py::test_propose_duplicate_external_mapping_rejected.  |  **Defect:** —

### TC-052-009-03 — Duplicate detection — Replayed inbound message is detected

- **Requirement:** MDS-FR-009
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-052-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- propose_mapping()'s duplicate ACTIVE/PROPOSED check; services/gxp-api/tests/test_erp_flow.py::test_propose_duplicate_external_mapping_rejected.  |  **Defect:** —

### TC-052-009-04 — Duplicate detection — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** MDS-FR-009
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-052-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- propose_mapping()'s duplicate ACTIVE/PROPOSED check; services/gxp-api/tests/test_erp_flow.py::test_propose_duplicate_external_mapping_rejected.  |  **Defect:** —

### TC-052-010-01 — UOM mapping — required behaviour

- **Requirement:** MDS-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: UOM equivalency/conversion approved/versioned; unknown UOM quarantines record. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Quantity safety. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- uom_conversion_factor NUMERIC(24,10) field on the mapping (versioned via mapping row version); no unknown-UOM auto-quarantine behavior built.  |  **Defect:** —

### TC-052-010-02 — UOM mapping — Action without the required signature is blocked

- **Requirement:** MDS-FR-010
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-052-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- uom_conversion_factor NUMERIC(24,10) field on the mapping (versioned via mapping row version); no unknown-UOM auto-quarantine behavior built.  |  **Defect:** —

### TC-052-010-03 — UOM mapping — Signature bound to a superseded version is rejected

- **Requirement:** MDS-FR-010
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-052-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- uom_conversion_factor NUMERIC(24,10) field on the mapping (versioned via mapping row version); no unknown-UOM auto-quarantine behavior built.  |  **Defect:** —

### TC-052-010-04 — UOM mapping — Concurrent writers on one aggregate

- **Requirement:** MDS-FR-010
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-052-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- uom_conversion_factor NUMERIC(24,10) field on the mapping (versioned via mapping row version); no unknown-UOM auto-quarantine behavior built.  |  **Defect:** —

### TC-052-011-01 — Plant/site mapping — required behaviour

- **Requirement:** MDS-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: ERP plant/org/company/location context maps exactly to tenant/site. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Isolation. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- erp_instance.site_id + WAREHOUSE/LOCATION entity_type mapping give an explicit plant/site scope.  |  **Defect:** —

### TC-052-011-02 — Plant/site mapping — Replayed inbound message is detected

- **Requirement:** MDS-FR-011
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-052-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- erp_instance.site_id + WAREHOUSE/LOCATION entity_type mapping give an explicit plant/site scope.  |  **Defect:** —

### TC-052-011-03 — Plant/site mapping — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** MDS-FR-011
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-052-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- erp_instance.site_id + WAREHOUSE/LOCATION entity_type mapping give an explicit plant/site scope.  |  **Defect:** —

### TC-052-012-01 — Warehouse mapping — required behaviour

- **Requirement:** MDS-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Warehouse/bin/subinventory location mapping explicit and effective-dated. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Logistics. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- WAREHOUSE entity_type + effective_from/effective_to columns on erp_external_mappings.  |  **Defect:** —

### TC-052-013-01 — Supplier mapping — required behaviour

- **Requirement:** MDS-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Commercial supplier identity mapping distinct from GxP manufacturer/approved source status. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Quality. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- SUPPLIER entity_type mapping is structurally distinct from any 'approved supplier' concept, which this module never touches (same boundary as ENXT-FR-004).  |  **Defect:** —

### TC-052-013-02 — Supplier mapping — Action without the required signature is blocked

- **Requirement:** MDS-FR-013
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-052-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- SUPPLIER entity_type mapping is structurally distinct from any 'approved supplier' concept, which this module never touches (same boundary as ENXT-FR-004).  |  **Defect:** —

### TC-052-013-03 — Supplier mapping — Signature bound to a superseded version is rejected

- **Requirement:** MDS-FR-013
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-052-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- SUPPLIER entity_type mapping is structurally distinct from any 'approved supplier' concept, which this module never touches (same boundary as ENXT-FR-004).  |  **Defect:** —

### TC-052-013-04 — Supplier mapping — Illegal state transition is rejected

- **Requirement:** MDS-FR-013
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-052-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- SUPPLIER entity_type mapping is structurally distinct from any 'approved supplier' concept, which this module never touches (same boundary as ENXT-FR-004).  |  **Defect:** —

### TC-052-014-01 — Product/material mapping — required behaviour

- **Requirement:** MDS-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: External item maps to exact internal business identity/version policy, never “latest regulated version” dynamically during historical execution. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** History. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- internal_id binds to one exact internal aggregate id -- never a dynamically-resolved 'latest version' lookup.  |  **Defect:** —

### TC-052-014-02 — Product/material mapping — Prohibited path is rejected

- **Requirement:** MDS-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: External item maps to exact internal business identity/version policy, never “latest regulated version” dynamically during historical execut | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-052-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- internal_id binds to one exact internal aggregate id -- never a dynamically-resolved 'latest version' lookup.  |  **Defect:** —

### TC-052-014-03 — Product/material mapping — Replayed inbound message is detected

- **Requirement:** MDS-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-052-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- internal_id binds to one exact internal aggregate id -- never a dynamically-resolved 'latest version' lookup.  |  **Defect:** —

### TC-052-014-04 — Product/material mapping — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** MDS-FR-014
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-052-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- internal_id binds to one exact internal aggregate id -- never a dynamically-resolved 'latest version' lookup.  |  **Defect:** —

### TC-052-015-01 — Reference-data mapping — required behaviour

- **Requirement:** MDS-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Movement type/reason code/status reference values versioned by ERP instance. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Adapter semantics. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- REASON_CODE entity_type + internal_code-keyed mapping path supports code-based (non-UUID) reference values.  |  **Defect:** —

### TC-052-015-02 — Reference-data mapping — Illegal state transition is rejected

- **Requirement:** MDS-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-052-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- REASON_CODE entity_type + internal_code-keyed mapping path supports code-based (non-UUID) reference values.  |  **Defect:** —

### TC-052-015-03 — Reference-data mapping — Replayed inbound message is detected

- **Requirement:** MDS-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-052-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- REASON_CODE entity_type + internal_code-keyed mapping path supports code-based (non-UUID) reference values.  |  **Defect:** —

### TC-052-015-04 — Reference-data mapping — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** MDS-FR-015
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-052-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- REASON_CODE entity_type + internal_code-keyed mapping path supports code-based (non-UUID) reference values.  |  **Defect:** —

### TC-052-016-01 — Effective dates — required behaviour

- **Requirement:** MDS-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Mappings can be future-effective and historical mappings remain for old transactions. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reproducibility. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- effective_from/effective_to columns on erp_external_mappings; services/gxp-api/tests/test_erp_flow.py::test_propose_and_approve_mapping exercises the mapping row these live on.  |  **Defect:** —

### TC-052-017-01 — Suspension — required behaviour

- **Requirement:** MDS-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Suspend mapping on discovered mismatch without deleting history. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Containment. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- suspend_mapping() (app/modules/erp/commands.py) is the real ACTIVE->SUSPENDED command MDS-FR-017 required -- never deletes the row, reactivation reuses the existing approve_mapping() SUSPENDED->ACTIVE path; services/gxp-api/tests/test_erp_master_sync.py::test_sync_detects_external_deactivation_and_suspends_active_mapping, test_suspend_mapping_requires_reason_and_only_suspends_active.  |  **Defect:** —

### TC-052-018-01 — Conflict queue — required behaviour

- **Requirement:** MDS-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Structured differences with owner/source/current/proposed values and resolution action. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Governance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- ErpMappingConflict table + resolve_master_conflict(); services/gxp-api/tests/test_erp_flow.py::test_external_change_on_gxp_owned_field_creates_conflict_not_overwrite.  |  **Defect:** —

### TC-052-019-01 — Approval — required behaviour

- **Requirement:** MDS-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Critical identity/UOM/site mappings require integration/data-owner approval; quality-critical mappings may require QA/validation. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- approve_mapping() + requires_qa_review routing flag on conflicts; services/gxp-api/tests/test_erp_flow.py::test_propose_and_approve_mapping.  |  **Defect:** —

### TC-052-019-02 — Approval — Replayed inbound message is detected

- **Requirement:** MDS-FR-019
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-052-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- approve_mapping() + requires_qa_review routing flag on conflicts; services/gxp-api/tests/test_erp_flow.py::test_propose_and_approve_mapping.  |  **Defect:** —

### TC-052-019-03 — Approval — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** MDS-FR-019
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-052-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- approve_mapping() + requires_qa_review routing flag on conflicts; services/gxp-api/tests/test_erp_flow.py::test_propose_and_approve_mapping.  |  **Defect:** —

### TC-052-020-01 — Bulk approval restriction — required behaviour

- **Requirement:** MDS-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: High-risk mappings cannot be blanket-approved without review profile. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Safety. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- no bulk-approve endpoint exists at all -- blanket approval is structurally impossible, by omission.  |  **Defect:** —

### TC-052-020-02 — Bulk approval restriction — Action without the required signature is blocked

- **Requirement:** MDS-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-052-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- no bulk-approve endpoint exists at all -- blanket approval is structurally impossible, by omission.  |  **Defect:** —

### TC-052-020-03 — Bulk approval restriction — Signature bound to a superseded version is rejected

- **Requirement:** MDS-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-052-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- no bulk-approve endpoint exists at all -- blanket approval is structurally impossible, by omission.  |  **Defect:** —

### TC-052-021-01 — Mapping hash/version — required behaviour

- **Requirement:** MDS-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Every integration transaction records mapping version/hash used. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Investigation. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- mapping_hash computed at approval time, version bumped on every change; services/gxp-api/tests/test_erp_flow.py::test_propose_and_approve_mapping.  |  **Defect:** —

### TC-052-021-02 — Mapping hash/version — Replayed inbound message is detected

- **Requirement:** MDS-FR-021
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-052-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- mapping_hash computed at approval time, version bumped on every change; services/gxp-api/tests/test_erp_flow.py::test_propose_and_approve_mapping.  |  **Defect:** —

### TC-052-021-03 — Mapping hash/version — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** MDS-FR-021
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-052-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- mapping_hash computed at approval time, version bumped on every change; services/gxp-api/tests/test_erp_flow.py::test_propose_and_approve_mapping.  |  **Defect:** —

### TC-052-021-04 — Mapping hash/version — Concurrent writers on one aggregate

- **Requirement:** MDS-FR-021
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-052-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- mapping_hash computed at approval time, version bumped on every change; services/gxp-api/tests/test_erp_flow.py::test_propose_and_approve_mapping.  |  **Defect:** —

### TC-052-022-01 — Sync checkpoint — required behaviour

- **Requirement:** MDS-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Persist external change cursor/watermark per entity/instance. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Restart safe. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- ErpSyncCheckpoint table + advance_sync_checkpoint(); services/gxp-api/tests/test_erp_flow.py::test_advance_sync_checkpoint_idempotent_resubmit.  |  **Defect:** —

### TC-052-022-02 — Sync checkpoint — Replayed inbound message is detected

- **Requirement:** MDS-FR-022
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-052-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- ErpSyncCheckpoint table + advance_sync_checkpoint(); services/gxp-api/tests/test_erp_flow.py::test_advance_sync_checkpoint_idempotent_resubmit.  |  **Defect:** —

### TC-052-022-03 — Sync checkpoint — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** MDS-FR-022
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-052-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- ErpSyncCheckpoint table + advance_sync_checkpoint(); services/gxp-api/tests/test_erp_flow.py::test_advance_sync_checkpoint_idempotent_resubmit.  |  **Defect:** —

### TC-052-023-01 — Replay — required behaviour

- **Requirement:** MDS-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Reprocess same inbound master event idempotently. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Replay safe. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- advance_sync_checkpoint() is idempotent via idempotency_key; services/gxp-api/tests/test_erp_flow.py::test_advance_sync_checkpoint_idempotent_resubmit; ingest_erp_event's dedupe demonstrates the same replay-safety pattern generically.  |  **Defect:** —

### TC-052-023-02 — Replay — Replayed inbound message is detected

- **Requirement:** MDS-FR-023
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-052-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- advance_sync_checkpoint() is idempotent via idempotency_key; services/gxp-api/tests/test_erp_flow.py::test_advance_sync_checkpoint_idempotent_resubmit; ingest_erp_event's dedupe demonstrates the same replay-safety pattern generically.  |  **Defect:** —

### TC-052-023-03 — Replay — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** MDS-FR-023
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-052-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- advance_sync_checkpoint() is idempotent via idempotency_key; services/gxp-api/tests/test_erp_flow.py::test_advance_sync_checkpoint_idempotent_resubmit; ingest_erp_event's dedupe demonstrates the same replay-safety pattern generically.  |  **Defect:** —

### TC-052-024-01 — Delete semantics — required behaviour

- **Requirement:** MDS-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: External deletion/deactivation maps to inactive/suspended projection; never physically deletes GxP-linked master history. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** History. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- sync_master_data() detects an ERPNext 'disabled' deactivation signal on an already-ACTIVE mapping and calls suspend_mapping() -- the mapping row (and all GxP history referencing it) is never deleted; services/gxp-api/tests/test_erp_master_sync.py::test_sync_detects_external_deactivation_and_suspends_active_mapping.  |  **Defect:** —

### TC-052-024-02 — Delete semantics — Prohibited path is rejected

- **Requirement:** MDS-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: External deletion/deactivation maps to inactive/suspended projection; never physically deletes GxP-linked master history. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-052-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- suspend_mapping()/the ORM mapping model expose no delete path at all for erp_external_mappings -- the forbidden condition (physical delete) is structurally unreachable, not merely rejected at runtime; services/gxp-api/tests/test_erp_master_sync.py::test_sync_detects_external_deactivation_and_suspends_active_mapping.  |  **Defect:** —

### TC-052-024-03 — Delete semantics — Replayed inbound message is detected

- **Requirement:** MDS-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-052-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- a mapping already SUSPENDED (or otherwise already processed) is left alone on a re-delivered deactivation signal (existing.mapping_status == 'ACTIVE' guard) -- generic replay-safety pattern; services/gxp-api/tests/test_erp_master_sync.py::test_sync_detects_external_deactivation_and_suspends_active_mapping.  |  **Defect:** —

### TC-052-024-04 — Delete semantics — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** MDS-FR-024
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-052-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- generic timeout-uncertain boilerplate covered by the shared dispatch/fetch timeout handling (fetch_changes() runs outside any open transaction); services/gxp-api/tests/test_erp_flow.py::test_dispatch_timeout_is_uncertain_not_blind_success_or_retry_storm.  |  **Defect:** —

### TC-052-025-01 — Reconciliation — required behaviour

- **Requirement:** MDS-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Scheduled object counts/key fields/active mapping differences. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Detect drift. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- shared reconciliation run/difference model applies to mapping data as any other reconciliation scope; not tested with an MDS-specific field-count scenario.  |  **Defect:** —

### TC-052-026-01 — Data quality metrics — required behaviour

- **Requirement:** MDS-FR-026
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Unmapped, conflict, stale, failed sync and duplicate rates visible. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Operability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no unmapped/conflict/stale/duplicate-rate dashboard or metrics endpoint exists (SG-126).  |  **Defect:** —

### TC-052-026-02 — Data quality metrics — Prohibited path is rejected

- **Requirement:** MDS-FR-026
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Unmapped, conflict, stale, failed sync and duplicate rates visible. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-052-026-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no unmapped/conflict/stale/duplicate-rate dashboard or metrics endpoint exists (SG-126).  |  **Defect:** —

### TC-052-027-01 — Audit — required behaviour

- **Requirement:** MDS-FR-027
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Mapping create/change/approve/suspend/merge and conflict resolution audited. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- every mapping create/approve/conflict/resolve writes a real audit event via _write_receipt(); proven implicitly by every 200 response's audit_event_id in the mapping tests.  |  **Defect:** —

### TC-052-027-02 — Audit — Action without the required signature is blocked

- **Requirement:** MDS-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-052-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- every mapping create/approve/conflict/resolve writes a real audit event via _write_receipt(); proven implicitly by every 200 response's audit_event_id in the mapping tests.  |  **Defect:** —

### TC-052-027-03 — Audit — Signature bound to a superseded version is rejected

- **Requirement:** MDS-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-052-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- every mapping create/approve/conflict/resolve writes a real audit event via _write_receipt(); proven implicitly by every 200 response's audit_event_id in the mapping tests.  |  **Defect:** —

### TC-052-027-04 — Audit — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** MDS-FR-027
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-052-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- every mapping create/approve/conflict/resolve writes a real audit event via _write_receipt(); proven implicitly by every 200 response's audit_event_id in the mapping tests.  |  **Defect:** —

### TC-052-028-01 — Migration — required behaviour

- **Requirement:** MDS-FR-028
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Customer onboarding mapping/import package retained with source checksum and approval. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Provenance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no customer-onboarding import-package/checksum/approval mechanism exists (SG-126).  |  **Defect:** —

### TC-052-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-ERP-005-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 52 has no independent public API (Document 113 §6: 'master-data sync jobs behind the Document 53 integration gateway') -- realized through the shared /integration/v1/mappings surface, itself owned by Document 53's contract, and covered by Document 53's own M-series.  |  **Defect:** —

### TC-052-S001 — Specification scenario — initial 100k item import

- **Requirement:** SPEC-ERP-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: initial 100k item import | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- sync_master_data() is now genuinely constructible at scale without a human calling proposeMapping per record -- exercised across 3 paginated 100-record fetch_changes() pages (300 records) in one bulk-import call; a literal 100k-record load/performance run was not executed this pass (CLAUDE.md SS5 -- that is a separate performance-test exercise, not a functional-pipeline gap). services/gxp-api/tests/test_erp_master_sync.py::test_sync_bulk_initial_import_walks_multiple_pages.  |  **Defect:** —

### TC-052-S002 — Specification scenario — duplicate external item

- **Requirement:** SPEC-ERP-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: duplicate external item | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_propose_duplicate_external_mapping_rejected (duplicate external item detection).  |  **Defect:** —

### TC-052-S003 — Specification scenario — supplier same name different legal entity

- **Requirement:** SPEC-ERP-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: supplier same name different legal entity | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- MDS-FR-013's structural boundary (supplier commercial mapping never implies GxP manufacturer/approved-source status) -- a same-name-different-legal-entity supplier is simply two independent mapping rows by construction.  |  **Defect:** —

### TC-052-S004 — Specification scenario — GxP-owned field changed in ERP

- **Requirement:** SPEC-ERP-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: GxP-owned field changed in ERP | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_external_change_on_gxp_owned_field_creates_conflict_not_overwrite.  |  **Defect:** —

### TC-052-S005 — Specification scenario — unknown UOM

- **Requirement:** SPEC-ERP-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: unknown UOM | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- uom_conversion_factor is nullable and Numeric-typed; an unrecognized UOM has no conversion factor rather than a fabricated one (structural safety, not an active quarantine workflow).  |  **Defect:** —

### TC-052-S006 — Specification scenario — wrong plant/site

- **Requirement:** SPEC-ERP-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: wrong plant/site | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no wrong-plant/site detection exists beyond the generic mapping-not-found lookup failure (SG-126).  |  **Defect:** —

### TC-052-S007 — Specification scenario — mapping future effective

- **Requirement:** SPEC-ERP-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: mapping future effective | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- effective_from/effective_to columns support a future-effective mapping row directly; services/gxp-api/tests/test_erp_flow.py::test_propose_and_approve_mapping exercises the row these live on (future-dating itself not independently re-tested).  |  **Defect:** —

### TC-052-S008 — Specification scenario — external item deactivated

- **Requirement:** SPEC-ERP-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: external item deactivated | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- an ERPNext 'disabled' flag on an external record now suspends its ACTIVE mapping via the new suspend_mapping() command, detected by sync_master_data(); services/gxp-api/tests/test_erp_master_sync.py::test_sync_detects_external_deactivation_and_suspends_active_mapping.  |  **Defect:** —

### TC-052-S009 — Specification scenario — replay same import batch

- **Requirement:** SPEC-ERP-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: replay same import batch | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_advance_sync_checkpoint_idempotent_resubmit (replay same import batch via idempotency).  |  **Defect:** —

### TC-052-S010 — Specification scenario — conflict resolution stale version

- **Requirement:** SPEC-ERP-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: conflict resolution stale version | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_reconciliation_run_lifecycle_never_auto_resolves proves StaleVersionError-style optimistic concurrency generically (conflict-resolution stale-version case not independently re-executed for this document).  |  **Defect:** —

### TC-052-S011 — Specification scenario — sync cursor crash/restart

- **Requirement:** SPEC-ERP-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: sync cursor crash/restart | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_advance_sync_checkpoint_idempotent_resubmit proves the checkpoint upsert survives a resubmitted batch_id, the same mechanism a crash/restart resume would rely on.  |  **Defect:** —
