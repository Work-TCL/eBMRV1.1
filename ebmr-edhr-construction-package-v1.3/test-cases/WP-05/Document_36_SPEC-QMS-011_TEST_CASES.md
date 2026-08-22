# Test Cases — Document 36: Recall / Field Action Management (SPEC-QMS-011)

**Work package:** WP-05  
**Risk class:** STANDARD-RISK  
**Requirements covered:** FAR-FR-001..020 (20)  
**Test cases:** 56  
**Code location:** `services/gxp-api/src/modules/qms`  
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

### TC-036-001-01 — Assessment initiation — required behaviour

- **Requirement:** FAR-FR-001
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Create from complaint, deviation, CAPA, trend, regulatory request or management decision. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Trigger linked. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-002-01 — Action classification — required behaviour

- **Requirement:** FAR-FR-002
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Recall/correction/removal/field action/customer advisory/stock recovery or configured terminology. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Explicit. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-003-01 — Affected scope — required behaviour

- **Requirement:** FAR-FR-003
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Use Genealogy to identify products/lots/serials/packages/distribution references. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Accurate. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-004-01 — Constituent scope — required behaviour

- **Requirement:** FAR-FR-004
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: DDCP action can target whole product or constituent/interface with final-product impact. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Combination aware. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-005-01 — Risk assessment — required behaviour

- **Requirement:** FAR-FR-005
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Link health/product risk assessment and rationale. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-006-01 — Reportability assessment — required behaviour

- **Requirement:** FAR-FR-006
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Authorized Regulatory determines applicable Part 806/drug/biologic/Part4 obligations/deadlines. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Human authority. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-007-01 — Distribution hold — required behaviour

- **Requirement:** FAR-FR-007
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Block undistributed inventory when required. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Containment. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-007-02 — Distribution hold — Prohibited path is rejected

- **Requirement:** FAR-FR-007
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Block undistributed inventory when required. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `EFFECTIVENESS_REQUIRED`
- **Depends on:** TC-036-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-007-03 — Distribution hold — Concurrent writers on one aggregate

- **Requirement:** FAR-FR-007
- **Type / priority:** concurrency / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-036-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-008-01 — Consignee snapshot — required behaviour

- **Requirement:** FAR-FR-008
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Resolve and freeze distribution/consignee scope from ERP/WMS/CRM. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Communication scope. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-008-02 — Consignee snapshot — Replayed inbound message is detected

- **Requirement:** FAR-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-036-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-008-03 — Consignee snapshot — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** FAR-FR-008
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-036-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-009-01 — Communication package — required behaviour

- **Requirement:** FAR-FR-009
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Version/approve notification text/instructions/attachments. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-009-02 — Communication package — Action without the required signature is blocked

- **Requirement:** FAR-FR-009
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-036-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-009-03 — Communication package — Signature bound to a superseded version is rejected

- **Requirement:** FAR-FR-009
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-036-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-009-04 — Communication package — Concurrent writers on one aggregate

- **Requirement:** FAR-FR-009
- **Type / priority:** concurrency / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-036-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-010-01 — Notification tracking — required behaviour

- **Requirement:** FAR-FR-010
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Recipient/date/channel/delivery/acknowledgment/follow-up. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Execution. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-011-01 — Return/correction plan — required behaviour

- **Requirement:** FAR-FR-011
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Return/inspect/correct/update/replace/destroy plan. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Disposition. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-012-01 — Unit reconciliation — required behaviour

- **Requirement:** FAR-FR-012
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Affected/contacted/returned/corrected/destroyed/unavailable/outstanding. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Effectiveness. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-013-01 — Effectiveness checks — required behaviour

- **Requirement:** FAR-FR-013
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Verify communication/action effectiveness under approved plan. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Control. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-013-02 — Effectiveness checks — Action without the required signature is blocked

- **Requirement:** FAR-FR-013
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-036-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-013-03 — Effectiveness checks — Signature bound to a superseded version is rejected

- **Requirement:** FAR-FR-013
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-036-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-014-01 — Submission evidence — required behaviour

- **Requirement:** FAR-FR-014
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Store regulatory report/submission IDs/dates/acknowledgments. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-015-01 — Corrections/removals record — required behaviour

- **Requirement:** FAR-FR-015
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Maintain applicable device correction/removal records even if reporting decision is no. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Part 806 support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-015-02 — Corrections/removals record — Offline buffering and reconnect preserve evidence

- **Requirement:** FAR-FR-015
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-036-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-016-01 — CAPA link — required behaviour

- **Requirement:** FAR-FR-016
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Underlying systemic action links CAPA. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Systemic. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-017-01 — Status updates — required behaviour

- **Requirement:** FAR-FR-017
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Track management/regulatory updates and milestones. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Governance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-017-02 — Status updates — Illegal state transition is rejected

- **Requirement:** FAR-FR-017
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-036-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-018-01 — Closure — required behaviour

- **Requirement:** FAR-FR-018
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Scope reconciliation, action, submissions, effectiveness and dependencies complete. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Complete. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-019-01 — Scope expansion — required behaviour

- **Requirement:** FAR-FR-019
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: New affected product reopens/expands controlled version. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Dynamic. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-019-02 — Scope expansion — Concurrent writers on one aggregate

- **Requirement:** FAR-FR-019
- **Type / priority:** concurrency / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-036-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-020-01 — Export — required behaviour

- **Requirement:** FAR-FR-020
- **Type / priority:** positive / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `field_action`, `field_action_scope_item`, `field_action_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `field_action`, `field_action_scope_item`, `field_action_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/field-actions` (or the owning command) exercising: Decision/scope/communication/reconciliation/submission/closure package exportable. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Inspection-ready. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-QMS-011-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-S001 — Specification scenario — material-lot forward trace

- **Requirement:** SPEC-QMS-011-SPEC-SCENARIO
- **Type / priority:** scenario / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: material-lot forward trace | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-S002 — Specification scenario — single serial complaint

- **Requirement:** SPEC-QMS-011-SPEC-SCENARIO
- **Type / priority:** scenario / P2
- **Automation:** e2e | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: single serial complaint | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-S003 — Specification scenario — DDCP constituent issue

- **Requirement:** SPEC-QMS-011-SPEC-SCENARIO
- **Type / priority:** scenario / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: DDCP constituent issue | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-S004 — Specification scenario — distribution hold

- **Requirement:** SPEC-QMS-011-SPEC-SCENARIO
- **Type / priority:** scenario / P2
- **Automation:** e2e | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: distribution hold | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-S005 — Specification scenario — consignee snapshot

- **Requirement:** SPEC-QMS-011-SPEC-SCENARIO
- **Type / priority:** scenario / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: consignee snapshot | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-S006 — Specification scenario — return reconciliation

- **Requirement:** SPEC-QMS-011-SPEC-SCENARIO
- **Type / priority:** scenario / P2
- **Automation:** e2e | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: return reconciliation | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-S007 — Specification scenario — device correction/removal record

- **Requirement:** SPEC-QMS-011-SPEC-SCENARIO
- **Type / priority:** scenario / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: device correction/removal record | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-S008 — Specification scenario — scope expansion

- **Requirement:** SPEC-QMS-011-SPEC-SCENARIO
- **Type / priority:** scenario / P2
- **Automation:** e2e | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: scope expansion | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-S009 — Specification scenario — CAPA dependency

- **Requirement:** SPEC-QMS-011-SPEC-SCENARIO
- **Type / priority:** scenario / P2
- **Automation:** integration | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: CAPA dependency | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-036-S010 — Specification scenario — closure

- **Requirement:** SPEC-QMS-011-SPEC-SCENARIO
- **Type / priority:** scenario / P2
- **Automation:** e2e | **Qualification stage:** OQ (sampled)
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: closure | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____
