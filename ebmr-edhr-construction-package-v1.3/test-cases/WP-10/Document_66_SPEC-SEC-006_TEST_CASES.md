# Test Cases — Document 66: Network, Tenant, Deployment Isolation & Zero-Trust Architecture (SPEC-SEC-006)

**Work package:** WP-10  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** NET-FR-001..030 (30)  
**Test cases:** 75  
**Code location:** `platform/security`  
**Authoritative store:** PostgreSQL (GxP Core, authoritative)

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

### TC-066-001-01 — Deployment zones — required behaviour

- **Requirement:** NET-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Define ingress, app, GxP service, DB, integration, observability, admin and Edge/OT zones. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Layered architecture. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-001-02 — Deployment zones — Replayed inbound message is detected

- **Requirement:** NET-FR-001
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-066-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-001-03 — Deployment zones — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** NET-FR-001
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-066-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-001-04 — Deployment zones — Offline buffering and reconnect preserve evidence

- **Requirement:** NET-FR-001
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-066-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-002-01 — Default deny — required behaviour

- **Requirement:** NET-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Network policies/firewalls default deny between zones and allow only required flows. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Least connectivity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-002-02 — Default deny — Prohibited path is rejected

- **Requirement:** NET-FR-002
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Network policies/firewalls default deny between zones and allow only required flows. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-066-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-003-01 — No DB internet exposure — required behaviour

- **Requirement:** NET-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: MariaDB/PostgreSQL/object stores/internal message bus not publicly exposed. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Attack surface. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-004-01 — Service-to-service auth — required behaviour

- **Requirement:** NET-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Internal network location alone does not authorize service access; workload identity/auth required. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Zero trust. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-005-01 — Ingress — required behaviour

- **Requirement:** NET-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Only approved reverse proxy/API gateway/load balancer exposed externally; admin routes separately protected. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled entry. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-005-02 — Ingress — Action without the required signature is blocked

- **Requirement:** NET-FR-005
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-066-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-005-03 — Ingress — Signature bound to a superseded version is rejected

- **Requirement:** NET-FR-005
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-066-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-005-04 — Ingress — Replayed inbound message is detected

- **Requirement:** NET-FR-005
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-066-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-006-01 — Egress — required behaviour

- **Requirement:** NET-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Application/integration services use outbound allowlists/proxy/network policy; GxP DB has no arbitrary internet egress. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** SSRF containment. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-006-02 — Egress — Replayed inbound message is detected

- **Requirement:** NET-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-066-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-006-03 — Egress — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** NET-FR-006
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-066-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-007-01 — OT boundary — required behaviour

- **Requirement:** NET-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Edge Gateway mediates IT/OT data flow; cloud/app services do not directly initiate arbitrary PLC connections. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Industrial isolation. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-007-02 — OT boundary — Offline buffering and reconnect preserve evidence

- **Requirement:** NET-FR-007
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-066-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-008-01 — Edge outbound preferred — required behaviour

- **Requirement:** NET-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Plant Edge to server connections outbound initiated where feasible. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reduced inbound exposure. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-008-02 — Edge outbound preferred — Replayed inbound message is detected

- **Requirement:** NET-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-066-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-008-03 — Edge outbound preferred — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** NET-FR-008
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-066-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-008-04 — Edge outbound preferred — Offline buffering and reconnect preserve evidence

- **Requirement:** NET-FR-008
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-066-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-009-01 — Admin plane — required behaviour

- **Requirement:** NET-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Administrative access through protected VPN/ZTNA/bastion/PAM path rather than public service ports. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Privileged isolation. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-010-01 — Tenant isolation — required behaviour

- **Requirement:** NET-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Dedicated customer deployment is baseline; within deployment tenant/site scopes still enforced in application/data/jobs. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Defense in depth. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-011-01 — Cross-site isolation — required behaviour

- **Requirement:** NET-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Site-scoped integrations, Edge identities, service config and background jobs cannot cross site without explicit enterprise scope. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Scope. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-011-02 — Cross-site isolation — Limit boundary behaviour

- **Requirement:** NET-FR-011
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-066-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-011-03 — Cross-site isolation — Replayed inbound message is detected

- **Requirement:** NET-FR-011
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-066-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-011-04 — Cross-site isolation — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** NET-FR-011
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-066-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-012-01 — Database roles — required behaviour

- **Requirement:** NET-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Separate DB users/roles by service/schema/write need; Frappe DB credential cannot write GxP DB. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Data ownership. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-013-01 — Schema ownership — required behaviour

- **Requirement:** NET-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: GxP service repositories own tables; integrations/read models use restricted views/API, not shared superuser. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Least privilege. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-013-02 — Schema ownership — Replayed inbound message is detected

- **Requirement:** NET-FR-013
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-066-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-013-03 — Schema ownership — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** NET-FR-013
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-066-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-014-01 — Message bus ACL — required behaviour

- **Requirement:** NET-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: NATS/event subjects ACL by service identity; no universal publish/subscribe credential. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Event integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-015-01 — Object store policy — required behaviour

- **Requirement:** NET-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Evidence buckets/prefixes restricted by service identity; immutable/WORM policies protected from app deletion. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Evidence integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-015-02 — Object store policy — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** NET-FR-015
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-066-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-016-01 — Kubernetes namespace — required behaviour

- **Requirement:** NET-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Reference K8s deployment separates workloads/namespaces/service accounts/network policies by trust/function. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Container isolation. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-017-01 — Container privilege — required behaviour

- **Requirement:** NET-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Run non-root, read-only filesystem/capability drops/seccomp/AppArmor where compatible. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Workload hardening. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-018-01 — Host hardening — required behaviour

- **Requirement:** NET-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Reference OS baseline disables unnecessary services, applies patch/config baseline and time sync. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Secure host. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-019-01 — TLS termination — required behaviour

- **Requirement:** NET-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: TLS termination points explicit; re-encrypt/internal TLS where trust boundary requires. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Transport clarity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-020-01 — Private endpoints — required behaviour

- **Requirement:** NET-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Cloud DB/object/KMS prefer private networking/endpoints where supported. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reduced public exposure. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-021-01 — DNS — required behaviour

- **Requirement:** NET-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Internal service discovery controlled; DNS changes/security monitored; avoid trusting hostname without TLS identity. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Name integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-022-01 — Remote sites — required behaviour

- **Requirement:** NET-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Site-to-central connectivity uses secure VPN/private link/TLS with explicit routing; no flat corporate network assumption. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Enterprise. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-023-01 — Environment isolation — required behaviour

- **Requirement:** NET-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Dev/test/validation/prod separated accounts/projects/namespaces/secrets/data; production credentials absent from non-prod. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** SDLC safety. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-024-01 — Synthetic data — required behaviour

- **Requirement:** NET-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Non-prod uses synthetic/deidentified data by default; production data copy requires controlled approval/sanitization. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Privacy. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-025-01 — Backup isolation — required behaviour

- **Requirement:** NET-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Backup repository/access logically isolated from normal application compromise path. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Ransomware resilience. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-026-01 — Monitoring access — required behaviour

- **Requirement:** NET-FR-026
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Security monitoring has read/ingest permissions, not business-write privileges. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Separation. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-027-01 — Port inventory — required behaviour

- **Requirement:** NET-FR-027
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: All inbound/outbound ports/protocols documented by deployment profile. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reviewable. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-027-02 — Port inventory — Replayed inbound message is detected

- **Requirement:** NET-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-066-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-027-03 — Port inventory — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** NET-FR-027
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-066-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-028-01 — Network change — required behaviour

- **Requirement:** NET-FR-028
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: GxP-impacting firewall/routing/service-exposure changes controlled and tested. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Validated state. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-029-01 — Segmentation test — required behaviour

- **Requirement:** NET-FR-029
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: Automated/periodic tests verify forbidden network paths remain blocked. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Verification. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-029-02 — Segmentation test — Prohibited path is rejected

- **Requirement:** NET-FR-029
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Automated/periodic tests verify forbidden network paths remain blocked. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-066-029-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-029-03 — Segmentation test — Concurrent writers on one aggregate

- **Requirement:** NET-FR-029
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-066-029-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-030-01 — No security by IP only — required behaviour

- **Requirement:** NET-FR-030
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** Minimum valid data set for `network_flow_definition`, `deployment_security_profile`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `GET /security/v1/network-flows` (or the owning command) exercising: IP allowlist may supplement but never replace identity/auth for regulated APIs. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Zero trust. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-030-02 — No security by IP only — Prohibited path is rejected

- **Requirement:** NET-FR-030
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `network_flow_definition`, `deployment_security_profile` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: IP allowlist may supplement but never replace identity/auth for regulated APIs. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-066-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-SEC-006-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-S001 — Specification scenario — Frappe cannot connect to GxP DB directly

- **Requirement:** SPEC-SEC-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: Frappe cannot connect to GxP DB directly | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-S002 — Specification scenario — integration service cannot access QA tables

- **Requirement:** SPEC-SEC-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: integration service cannot access QA tables | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-S003 — Specification scenario — Edge cannot reach DB

- **Requirement:** SPEC-SEC-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: Edge cannot reach DB | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-S004 — Specification scenario — cross-site job blocked

- **Requirement:** SPEC-SEC-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: cross-site job blocked | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-S005 — Specification scenario — dev credential cannot reach prod

- **Requirement:** SPEC-SEC-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: dev credential cannot reach prod | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-S006 — Specification scenario — container root policy

- **Requirement:** SPEC-SEC-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: container root policy | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-066-S007 — Specification scenario — public DB exposure detection

- **Requirement:** SPEC-SEC-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: public DB exposure detection | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____
