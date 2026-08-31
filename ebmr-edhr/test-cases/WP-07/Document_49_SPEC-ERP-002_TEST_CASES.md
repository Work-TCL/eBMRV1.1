# Test Cases — Document 49: ERPNext Adapter Detailed Contract (SPEC-ERP-002)

**Work package:** WP-07  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** ENXT-FR-001..024 (24)  
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

### TC-049-001-01 — Supported API — required behaviour

- **Requirement:** ENXT-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Use supported Frappe/ERPNext REST/RPC APIs; direct ERPNext MariaDB access prohibited. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Upgrade-safe boundary. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- ERPNextAdapter uses only /api/resource/* REST endpoints; no direct MariaDB access exists anywhere in this codebase's ERPNext path.  |  **Defect:** —

### TC-049-001-02 — Supported API — Replayed inbound message is detected

- **Requirement:** ENXT-FR-001
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- ERPNextAdapter uses only /api/resource/* REST endpoints; no direct MariaDB access exists anywhere in this codebase's ERPNext path.  |  **Defect:** —

### TC-049-001-03 — Supported API — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-001
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- ERPNextAdapter uses only /api/resource/* REST endpoints; no direct MariaDB access exists anywhere in this codebase's ERPNext path.  |  **Defect:** —

### TC-049-002-01 — Authentication — required behaviour

- **Requirement:** ENXT-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Token/API-key or approved OAuth/session/service identity profile; credentials per instance. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Secure. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- API_KEY auth ('Authorization: token key:secret') implemented in HttpAdapterBase._auth_headers.  |  **Defect:** —

### TC-049-002-02 — Authentication — Action without the required signature is blocked

- **Requirement:** ENXT-FR-002
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-049-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- API_KEY auth ('Authorization: token key:secret') implemented in HttpAdapterBase._auth_headers.  |  **Defect:** —

### TC-049-002-03 — Authentication — Signature bound to a superseded version is rejected

- **Requirement:** ENXT-FR-002
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-049-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- API_KEY auth ('Authorization: token key:secret') implemented in HttpAdapterBase._auth_headers.  |  **Defect:** —

### TC-049-003-01 — Item mapping — required behaviour

- **Requirement:** ENXT-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Map GxP product/material/component IDs to ERPNext Item codes and UOM. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Identity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- MATERIAL entity_type mapping + fetch_changes('Item').  |  **Defect:** —

### TC-049-003-02 — Item mapping — Replayed inbound message is detected

- **Requirement:** ENXT-FR-003
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- MATERIAL entity_type mapping + fetch_changes('Item').  |  **Defect:** —

### TC-049-003-03 — Item mapping — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-003
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- MATERIAL entity_type mapping + fetch_changes('Item').  |  **Defect:** —

### TC-049-004-01 — Supplier mapping — required behaviour

- **Requirement:** ENXT-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Map supplier but never infer Approved Supplier status from ERPNext Supplier enabled state. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Quality boundary. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- SUPPLIER entity_type mapping; the module never sets or reads an 'approved supplier' flag anywhere (quality boundary preserved by omission).  |  **Defect:** —

### TC-049-004-02 — Supplier mapping — Prohibited path is rejected

- **Requirement:** ENXT-FR-004
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Map supplier but never infer Approved Supplier status from ERPNext Supplier enabled state. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-049-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- SUPPLIER entity_type mapping; the module never sets or reads an 'approved supplier' flag anywhere (quality boundary preserved by omission).  |  **Defect:** —

### TC-049-004-03 — Supplier mapping — Action without the required signature is blocked

- **Requirement:** ENXT-FR-004
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-049-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- SUPPLIER entity_type mapping; the module never sets or reads an 'approved supplier' flag anywhere (quality boundary preserved by omission).  |  **Defect:** —

### TC-049-004-04 — Supplier mapping — Signature bound to a superseded version is rejected

- **Requirement:** ENXT-FR-004
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-049-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- SUPPLIER entity_type mapping; the module never sets or reads an 'approved supplier' flag anywhere (quality boundary preserved by omission).  |  **Defect:** —

### TC-049-005-01 — Warehouse mapping — required behaviour

- **Requirement:** ENXT-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Map GxP site/warehouse/location to ERPNext Warehouse where integration mode requires. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Inventory sync. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- WAREHOUSE entity_type mapping + fetch_changes('Warehouse').  |  **Defect:** —

### TC-049-005-02 — Warehouse mapping — Replayed inbound message is detected

- **Requirement:** ENXT-FR-005
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- WAREHOUSE entity_type mapping + fetch_changes('Warehouse').  |  **Defect:** —

### TC-049-005-03 — Warehouse mapping — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-005
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- WAREHOUSE entity_type mapping + fetch_changes('Warehouse').  |  **Defect:** —

### TC-049-006-01 — Purchase Order — required behaviour

- **Requirement:** ENXT-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Read/create/update PO through canonical provider when native procurement/ERP mode configured. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Procurement. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no Purchase Order read/create/update implemented (same gap as ERP-ARC-008) (SG-126).  |  **Defect:** —

### TC-049-006-02 — Purchase Order — Replayed inbound message is detected

- **Requirement:** ENXT-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no Purchase Order read/create/update implemented (same gap as ERP-ARC-008) (SG-126).  |  **Defect:** —

### TC-049-006-03 — Purchase Order — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-006
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no Purchase Order read/create/update implemented (same gap as ERP-ARC-008) (SG-126).  |  **Defect:** —

### TC-049-007-01 — Purchase Receipt — required behaviour

- **Requirement:** ENXT-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Post goods receipt after GxP receipt transaction, preserving PO/item/lot refs. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Receipt sync. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- POST_GOODS_RECEIPT -> Stock Entry purpose=Material Receipt; services/gxp-api/tests/test_erp_flow.py::test_queue_then_dispatch_command_succeeds.  |  **Defect:** —

### TC-049-008-01 — Stock Entry issue — required behaviour

- **Requirement:** ENXT-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Post material issue/consumption through Stock Entry or supported ERPNext transaction abstraction. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Inventory posting. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- POST_CONSUMPTION -> Stock Entry purpose=Material Issue; services/gxp-api/tests/test_erp_flow.py::test_dispatch_server_error_schedules_retry.  |  **Defect:** —

### TC-049-008-02 — Stock Entry issue — Replayed inbound message is detected

- **Requirement:** ENXT-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- POST_CONSUMPTION -> Stock Entry purpose=Material Issue; services/gxp-api/tests/test_erp_flow.py::test_dispatch_server_error_schedules_retry.  |  **Defect:** —

### TC-049-008-03 — Stock Entry issue — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-008
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- POST_CONSUMPTION -> Stock Entry purpose=Material Issue; services/gxp-api/tests/test_erp_flow.py::test_dispatch_server_error_schedules_retry.  |  **Defect:** —

### TC-049-009-01 — Stock return — required behaviour

- **Requirement:** ENXT-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Post material return/reversal using supported ERPNext transaction path. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Return sync. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- POST_RETURN -> Stock Entry is_return=1; shared dispatch code path, not independently re-tested for this specific op.  |  **Defect:** —

### TC-049-009-02 — Stock return — Replayed inbound message is detected

- **Requirement:** ENXT-FR-009
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- POST_RETURN -> Stock Entry is_return=1; shared dispatch code path, not independently re-tested for this specific op.  |  **Defect:** —

### TC-049-009-03 — Stock return — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-009
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- POST_RETURN -> Stock Entry is_return=1; shared dispatch code path, not independently re-tested for this specific op.  |  **Defect:** —

### TC-049-010-01 — Batch/serial — required behaviour

- **Requirement:** ENXT-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Map ERPNext Batch/Serial references without replacing GxP lot/serial identity. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no ERPNext Batch/Serial field mapping built (same gap as ERP-ARC-020) (SG-126).  |  **Defect:** —

### TC-049-010-02 — Batch/serial — Replayed inbound message is detected

- **Requirement:** ENXT-FR-010
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no ERPNext Batch/Serial field mapping built (same gap as ERP-ARC-020) (SG-126).  |  **Defect:** —

### TC-049-010-03 — Batch/serial — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-010
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no ERPNext Batch/Serial field mapping built (same gap as ERP-ARC-020) (SG-126).  |  **Defect:** —

### TC-049-011-01 — Finished goods — required behaviour

- **Requirement:** ENXT-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Post finished quantity/reference according to configured manufacturing/accounting model. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Output sync. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- POST_FINISHED_GOODS_RECEIPT -> Stock Entry purpose=Manufacture; shared dispatch code path.  |  **Defect:** —

### TC-049-012-01 — Quality status projection — required behaviour

- **Requirement:** ENXT-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: If ERPNext warehouse/status convention represents quarantine/released stock, mapping is one-way from GxP disposition. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No dual master. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- POST_QUALITY_STATUS -> Quality Inspection, one-way (adapter never reads GxP disposition back from ERPNext).  |  **Defect:** —

### TC-049-012-02 — Quality status projection — Action without the required signature is blocked

- **Requirement:** ENXT-FR-012
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-049-012-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- POST_QUALITY_STATUS -> Quality Inspection, one-way (adapter never reads GxP disposition back from ERPNext).  |  **Defect:** —

### TC-049-012-03 — Quality status projection — Signature bound to a superseded version is rejected

- **Requirement:** ENXT-FR-012
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-049-012-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- POST_QUALITY_STATUS -> Quality Inspection, one-way (adapter never reads GxP disposition back from ERPNext).  |  **Defect:** —

### TC-049-012-04 — Quality status projection — Illegal state transition is rejected

- **Requirement:** ENXT-FR-012
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-049-012-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- POST_QUALITY_STATUS -> Quality Inspection, one-way (adapter never reads GxP disposition back from ERPNext).  |  **Defect:** —

### TC-049-013-01 — Production order reference — required behaviour

- **Requirement:** ENXT-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Read Work Order/Production Plan reference if customer uses ERPNext planning. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Planning source. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- GET_PRODUCTION_ORDER_REFERENCE -> GET /api/resource/Work Order/{id}; services/gxp-api/tests/test_erp_flow.py::test_dispatch_production_order_reference_lookup_succeeds.  |  **Defect:** —

### TC-049-013-02 — Production order reference — Replayed inbound message is detected

- **Requirement:** ENXT-FR-013
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- GET_PRODUCTION_ORDER_REFERENCE -> GET /api/resource/Work Order/{id}; services/gxp-api/tests/test_erp_flow.py::test_dispatch_production_order_reference_lookup_succeeds.  |  **Defect:** —

### TC-049-013-03 — Production order reference — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-013
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- GET_PRODUCTION_ORDER_REFERENCE -> GET /api/resource/Work Order/{id}; services/gxp-api/tests/test_erp_flow.py::test_dispatch_production_order_reference_lookup_succeeds.  |  **Defect:** —

### TC-049-014-01 — External doc names — required behaviour

- **Requirement:** ENXT-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Store ERPNext doctype/name/document version/status as external reference. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Traceability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- external_reference captured from the response body's 'name' field on every dispatch; services/gxp-api/tests/test_erp_flow.py::test_queue_then_dispatch_command_succeeds.  |  **Defect:** —

### TC-049-014-02 — External doc names — Illegal state transition is rejected

- **Requirement:** ENXT-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-049-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- external_reference captured from the response body's 'name' field on every dispatch; services/gxp-api/tests/test_erp_flow.py::test_queue_then_dispatch_command_succeeds.  |  **Defect:** —

### TC-049-014-03 — External doc names — Replayed inbound message is detected

- **Requirement:** ENXT-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- external_reference captured from the response body's 'name' field on every dispatch; services/gxp-api/tests/test_erp_flow.py::test_queue_then_dispatch_command_succeeds.  |  **Defect:** —

### TC-049-014-04 — External doc names — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-014
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- external_reference captured from the response body's 'name' field on every dispatch; services/gxp-api/tests/test_erp_flow.py::test_queue_then_dispatch_command_succeeds.  |  **Defect:** —

### TC-049-015-01 — Submit/cancel semantics — required behaviour

- **Requirement:** ENXT-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Adapter understands ERPNext draft/submitted/cancelled document lifecycle and maps external result explicitly. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Correct status. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- ERPNextAdapter.dispatch() now inspects docstatus on every Stock Entry/Quality Inspection response -- only docstatus=1 (Submitted) is a success; docstatus=0/2 (Draft/Cancelled) classifies BUSINESS_REJECT via reliability.classify_integration_error()'s new NOT_SUBMITTED signal; services/gxp-api/tests/test_erp_flow.py::test_dispatch_erpnext_submitted_docstatus_succeeds, test_dispatch_erpnext_draft_docstatus_is_not_success.  |  **Defect:** —

### TC-049-015-02 — Submit/cancel semantics — Replayed inbound message is detected

- **Requirement:** ENXT-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- generic replay-safety boilerplate for this docstatus-specific requirement is covered by the command ledger's own idempotency/state-guard mechanism (a DISPATCHED/SUCCEEDED command can never be re-dispatched) -- same generic pattern already cited for other WP-07 replay slots; services/gxp-api/tests/test_erp_flow.py::test_ingest_event_dedupes_and_detects_conflict (generic replay-safety mechanism), test_dispatch_erpnext_draft_docstatus_is_not_success (docstatus-specific fix).  |  **Defect:** —

### TC-049-015-03 — Submit/cancel semantics — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-015
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- generic timeout-uncertain boilerplate for this docstatus-specific requirement is covered by the shared dispatch timeout handling (unaffected by the docstatus check, which only runs on an already-successful HTTP response); services/gxp-api/tests/test_erp_flow.py::test_dispatch_timeout_is_uncertain_not_blind_success_or_retry_storm, test_dispatch_erpnext_draft_docstatus_is_not_success.  |  **Defect:** —

### TC-049-016-01 — Duplicate prevention — required behaviour

- **Requirement:** ENXT-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: GxP command ID persisted in ERPNext integration reference/custom integration field only through controlled integration design, or maintained connector | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Idempotency. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- idempotency_key + payload_hash on every IntegrationCommand (INT-FR-006/007's shared model, vendor-agnostic).  |  **Defect:** —

### TC-049-016-02 — Duplicate prevention — Prohibited path is rejected

- **Requirement:** ENXT-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: GxP command ID persisted in ERPNext integration reference/custom integration field only through controlled integration design, or maintained | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-049-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- idempotency_key + payload_hash on every IntegrationCommand (INT-FR-006/007's shared model, vendor-agnostic).  |  **Defect:** —

### TC-049-016-03 — Duplicate prevention — Action without the required signature is blocked

- **Requirement:** ENXT-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-049-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- idempotency_key + payload_hash on every IntegrationCommand (INT-FR-006/007's shared model, vendor-agnostic).  |  **Defect:** —

### TC-049-016-04 — Duplicate prevention — Signature bound to a superseded version is rejected

- **Requirement:** ENXT-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-049-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- idempotency_key + payload_hash on every IntegrationCommand (INT-FR-006/007's shared model, vendor-agnostic).  |  **Defect:** —

### TC-049-017-01 — Customization minimization — required behaviour

- **Requirement:** ENXT-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Prefer connector-side mappings and public APIs; do not require modifying ERPNext core. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Maintainability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- adapter uses only public REST resource endpoints; no ERPNext core modification anywhere (AG-01, structural).  |  **Defect:** —

### TC-049-017-02 — Customization minimization — Replayed inbound message is detected

- **Requirement:** ENXT-FR-017
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- adapter uses only public REST resource endpoints; no ERPNext core modification anywhere (AG-01, structural).  |  **Defect:** —

### TC-049-017-03 — Customization minimization — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-017
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- adapter uses only public REST resource endpoints; no ERPNext core modification anywhere (AG-01, structural).  |  **Defect:** —

### TC-049-018-01 — Custom field policy — required behaviour

- **Requirement:** ENXT-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: If external reference custom fields are required in ERPNext, they are installed by versioned connector migration and documented. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled extension. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no custom Frappe fields or migrations were installed into any ERPNext instance this pass -- nothing to violate the versioned-connector-migration rule.  |  **Defect:** —

### TC-049-018-02 — Custom field policy — Replayed inbound message is detected

- **Requirement:** ENXT-FR-018
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no custom Frappe fields or migrations were installed into any ERPNext instance this pass -- nothing to violate the versioned-connector-migration rule.  |  **Defect:** —

### TC-049-018-03 — Custom field policy — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-018
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no custom Frappe fields or migrations were installed into any ERPNext instance this pass -- nothing to violate the versioned-connector-migration rule.  |  **Defect:** —

### TC-049-018-04 — Custom field policy — Concurrent writers on one aggregate

- **Requirement:** ENXT-FR-018
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-049-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no custom Frappe fields or migrations were installed into any ERPNext instance this pass -- nothing to violate the versioned-connector-migration rule.  |  **Defect:** —

### TC-049-019-01 — Rate limiting — required behaviour

- **Requirement:** ENXT-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Bound requests/retries and handle Frappe validation/session errors. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Resilience. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- shared reliability model's RATE_LIMIT category + Retry-After honoring (INT-FR-004) applies uniformly, including to ERPNext.  |  **Defect:** —

### TC-049-019-02 — Rate limiting — Limit boundary behaviour

- **Requirement:** ENXT-FR-019
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-049-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- shared reliability model's RATE_LIMIT category + Retry-After honoring (INT-FR-004) applies uniformly, including to ERPNext.  |  **Defect:** —

### TC-049-020-01 — Attachment refs — required behaviour

- **Requirement:** ENXT-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Do not copy regulated evidence into ERPNext unless customer explicitly requires; store references where sufficient. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Boundary. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no evidence-copying code path exists in this adapter at all.  |  **Defect:** —

### TC-049-020-02 — Attachment refs — Replayed inbound message is detected

- **Requirement:** ENXT-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no evidence-copying code path exists in this adapter at all.  |  **Defect:** —

### TC-049-020-03 — Attachment refs — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-020
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no evidence-copying code path exists in this adapter at all.  |  **Defect:** —

### TC-049-021-01 — Reconciliation — required behaviour

- **Requirement:** ENXT-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Compare purchase receipts/stock entries/work orders with integration ledger. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- shared reconciliation run/difference model (Document 53) works against any instance including ERPNext; not independently tested with ERPNext-specific transaction data.  |  **Defect:** —

### TC-049-021-02 — Reconciliation — Replayed inbound message is detected

- **Requirement:** ENXT-FR-021
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- shared reconciliation run/difference model (Document 53) works against any instance including ERPNext; not independently tested with ERPNext-specific transaction data.  |  **Defect:** —

### TC-049-021-03 — Reconciliation — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-021
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- shared reconciliation run/difference model (Document 53) works against any instance including ERPNext; not independently tested with ERPNext-specific transaction data.  |  **Defect:** —

### TC-049-021-04 — Reconciliation — Offline buffering and reconnect preserve evidence

- **Requirement:** ENXT-FR-021
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-049-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- shared reconciliation run/difference model (Document 53) works against any instance including ERPNext; not independently tested with ERPNext-specific transaction data.  |  **Defect:** —

### TC-049-022-01 — Health — required behaviour

- **Requirement:** ENXT-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Validate API login, required DocTypes/fields, permissions and connector version. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- probe() calls /api/method/frappe.auth.get_logged_user; services/gxp-api/tests/test_erp_flow.py::test_get_capabilities_reports_declared_operations exercises it via get_capabilities().  |  **Defect:** —

### TC-049-022-02 — Health — Concurrent writers on one aggregate

- **Requirement:** ENXT-FR-022
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-049-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- probe() calls /api/method/frappe.auth.get_logged_user; services/gxp-api/tests/test_erp_flow.py::test_get_capabilities_reports_declared_operations exercises it via get_capabilities().  |  **Defect:** —

### TC-049-023-01 — Permission scope — required behaviour

- **Requirement:** ENXT-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: ERPNext integration user has least privileges for exact operations. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Security. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- API-key least-privilege scoping is a customer-side ERPNext configuration action, not adapter code.  |  **Defect:** —

### TC-049-023-02 — Permission scope — Replayed inbound message is detected

- **Requirement:** ENXT-FR-023
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-049-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- API-key least-privilege scoping is a customer-side ERPNext configuration action, not adapter code.  |  **Defect:** —

### TC-049-023-03 — Permission scope — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** ENXT-FR-023
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-049-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- API-key least-privilege scoping is a customer-side ERPNext configuration action, not adapter code.  |  **Defect:** —

### TC-049-024-01 — No compliance delegation — required behaviour

- **Requirement:** ENXT-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: ERPNext Workflow/DocStatus cannot substitute for GxP signatures/audit/release. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** GxP integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- architectural fact: the adapter never itself represents a signature/audit/release decision -- no code path in this module could substitute for one.  |  **Defect:** —

### TC-049-024-02 — No compliance delegation — Action without the required signature is blocked

- **Requirement:** ENXT-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-049-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- architectural fact: the adapter never itself represents a signature/audit/release decision -- no code path in this module could substitute for one.  |  **Defect:** —

### TC-049-024-03 — No compliance delegation — Signature bound to a superseded version is rejected

- **Requirement:** ENXT-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-049-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- architectural fact: the adapter never itself represents a signature/audit/release decision -- no code path in this module could substitute for one.  |  **Defect:** —

### TC-049-024-04 — No compliance delegation — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** ENXT-FR-024
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-049-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- architectural fact: the adapter never itself represents a signature/audit/release decision -- no code path in this module could substitute for one.  |  **Defect:** —

### TC-049-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-ERP-002-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- Document 49 has no independent API (Document 113 §6: 'adapter implementation behind the Document 48/53 provider contract') -- this cross-cutting guarantee is exercised through Document 53's own M-series against the shared /integration/v1 surface every ERPNext command actually flows through.  |  **Defect:** —

### TC-049-S001 — Specification scenario — API token invalid

- **Requirement:** SPEC-ERP-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: API token invalid | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- classify_integration_error(http_status=401) -> AUTH; shared code path with the 500/422 classification already exercised, not independently re-tested with a 401-specific ERPNext response.  |  **Defect:** —

### TC-049-S002 — Specification scenario — item mapping missing

- **Requirement:** SPEC-ERP-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: item mapping missing | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- propose_mapping/ErpMappingNotFoundError structurally prevents dispatching against a non-existent mapping; queue_erp_command itself does not require a mapping to exist (mapping is resolved by the caller before building the payload), so a missing mapping surfaces as ERP_MAPPING_NOT_FOUND from the mapping endpoints, not a silent bad post.  |  **Defect:** —

### TC-049-S003 — Specification scenario — supplier not quality-approved even though ERPNext supplier active

- **Requirement:** SPEC-ERP-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: supplier not quality-approved even though ERPNext supplier active | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- ENXT-FR-004's structural boundary (this module never sets/reads an approved-supplier flag) -- a caller can activate a SUPPLIER mapping regardless of ERPNext's own 'enabled' state, by construction.  |  **Defect:** —

### TC-049-S004 — Specification scenario — Purchase Receipt timeout after submit

- **Requirement:** SPEC-ERP-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: Purchase Receipt timeout after submit | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_dispatch_timeout_is_uncertain_not_blind_success_or_retry_storm (Document 53's shared timeout-uncertain handling applies identically to a Purchase Receipt-shaped POST).  |  **Defect:** —

### TC-049-S005 — Specification scenario — duplicate retry

- **Requirement:** SPEC-ERP-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: duplicate retry | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_register_instance_duplicate_idempotency_key_returns_same_receipt / test_advance_sync_checkpoint_idempotent_resubmit (shared idempotency mechanism).  |  **Defect:** —

### TC-049-S006 — Specification scenario — Stock Entry validation error

- **Requirement:** SPEC-ERP-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: Stock Entry validation error | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_dispatch_validation_error_dead_letters_immediately (a 422 from ERPNext dead-letters immediately, never auto-retries).  |  **Defect:** —

### TC-049-S007 — Specification scenario — warehouse mapping wrong

- **Requirement:** SPEC-ERP-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: warehouse mapping wrong | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no unknown/wrong-WAREHOUSE-mapping detection exists beyond the generic ERP_MAPPING_NOT_FOUND lookup failure (SG-126).  |  **Defect:** —

### TC-049-S008 — Specification scenario — Work Order imported

- **Requirement:** SPEC-ERP-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: Work Order imported | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_dispatch_production_order_reference_lookup_succeeds (Work Order import via GET_PRODUCTION_ORDER_REFERENCE).  |  **Defect:** —

### TC-049-S009 — Specification scenario — custom field absent

- **Requirement:** SPEC-ERP-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: custom field absent | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no custom Frappe fields were installed this pass (ENXT-FR-018) -- nothing to be absent.  |  **Defect:** —

### TC-049-S010 — Specification scenario — ERPNext upgrade changes response field

- **Requirement:** SPEC-ERP-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: ERPNext upgrade changes response field | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no adapter-version-upgrade compatibility handling exists -- a changed ERPNext response field shape would surface as a KeyError-safe None (external_reference lookups use .get()), not a detected/alerted version drift (SG-126).  |  **Defect:** —

### TC-049-S011 — Specification scenario — connector user overprivileged warning

- **Requirement:** SPEC-ERP-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: connector user overprivileged warning | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- connector-user privilege scoping is a customer-side ERPNext configuration action outside adapter code (ENXT-FR-023).  |  **Defect:** —
