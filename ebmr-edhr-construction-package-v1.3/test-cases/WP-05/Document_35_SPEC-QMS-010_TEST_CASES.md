# Test Cases — Document 35: Complaint Management (SPEC-QMS-010)

**Work package:** WP-05  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** CMP-FR-001..024 (24)  
**Test cases:** 64  
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

### TC-035-001-01 — Complaint intake — required behaviour

- **Requirement:** CMP-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Capture oral/written/electronic complaint from customer, patient/user, distributor, service, sales or regulator. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** All channels. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-002-01 — Known information — required behaviour

- **Requirement:** CMP-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Product name/strength/configuration, lot/batch/serial/UDI, complainant, date, nature, country/event details and reply where known. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Complaint file. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-003-01 — Acknowledgment — required behaviour

- **Requirement:** CMP-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Track complaint acknowledgment/communication. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Customer handling. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-004-01 — Product identification — required behaviour

- **Requirement:** CMP-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Resolve product/lot/serial; unknown IDs go to reconciliation queue. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-005-01 — Constituent classification — required behaviour

- **Requirement:** CMP-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Drug/device/interface/combination/packaging/label/usability/unknown. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** DDCP aware. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-005-02 — Constituent classification — Offline buffering and reconnect preserve evidence

- **Requirement:** CMP-FR-005
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-035-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-006-01 — Triage — required behaviour

- **Requirement:** CMP-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Quality/Regulatory seriousness/criticality assessment under approved procedure. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Safety. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-006-02 — Triage — Action without the required signature is blocked

- **Requirement:** CMP-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-035-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-006-03 — Triage — Signature bound to a superseded version is rejected

- **Requirement:** CMP-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-035-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-007-01 — Investigation decision — required behaviour

- **Requirement:** CMP-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Quality determines investigation required/not required. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** 211.198 support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-008-01 — No-investigation rationale — required behaviour

- **Requirement:** CMP-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: If not investigated, reason and responsible approver recorded. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** 211.198 support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-008-02 — No-investigation rationale — Action without the required signature is blocked

- **Requirement:** CMP-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-035-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-008-03 — No-investigation rationale — Signature bound to a superseded version is rejected

- **Requirement:** CMP-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-035-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-009-01 — Investigation — required behaviour

- **Requirement:** CMP-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Link batch/device history, QC, deviations, materials, equipment, complaints, service and returned product. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Complete. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-009-02 — Investigation — Offline buffering and reconnect preserve evidence

- **Requirement:** CMP-FR-009
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-035-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-010-01 — Returned product — required behaviour

- **Requirement:** CMP-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Track chain of custody, testing, preservation and disposition. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-010-02 — Returned product — Action without the required signature is blocked

- **Requirement:** CMP-FR-010
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-035-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-010-03 — Returned product — Signature bound to a superseded version is rejected

- **Requirement:** CMP-FR-010
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-035-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-010-04 — Returned product — Disposal without an approved decision is refused

- **Requirement:** CMP-FR-010
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-035-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-011-01 — Genealogy — required behaviour

- **Requirement:** CMP-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Serial/lot lookup identifies constituents/materials/related product. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** DDCP. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-012-01 — Reportability assessment — required behaviour

- **Requirement:** CMP-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Separate authorized assessment with rationale, regime, trigger/date and due date; software does not decide legal outcome alone. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-013-01 — Part 4 PMSR profile — required behaviour

- **Requirement:** CMP-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Support multiple constituent/application reporting regimes and information-sharing hooks. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Combination support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-014-01 — Device reporting hook — required behaviour

- **Requirement:** CMP-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: MDR/eMDR reference/workflow where applicable. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Postmarket. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-014-02 — Device reporting hook — Illegal state transition is rejected

- **Requirement:** CMP-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-035-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-014-03 — Device reporting hook — Offline buffering and reconnect preserve evidence

- **Requirement:** CMP-FR-014
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-035-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-015-01 — Drug safety hook — required behaviour

- **Requirement:** CMP-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: FAERS/safety-system reference/escalation where applicable. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Postmarket. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-016-01 — Trend — required behaviour

- **Requirement:** CMP-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Complaint codes/failure mode/product/lot/constituent trend. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Signal. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-016-02 — Trend — Prohibited path is rejected

- **Requirement:** CMP-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Complaint codes/failure mode/product/lot/constituent trend. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `INVESTIGATION_DECISION_REQUIRED`
- **Depends on:** TC-035-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-017-01 — CAPA — required behaviour

- **Requirement:** CMP-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Significant/repeat complaint can create CAPA. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Systemic. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-018-01 — Field action — required behaviour

- **Requirement:** CMP-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Complaint can trigger recall/field-action assessment. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Containment. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-019-01 — Response — required behaviour

- **Requirement:** CMP-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Track approved response to complainant. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Communication. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-019-02 — Response — Action without the required signature is blocked

- **Requirement:** CMP-FR-019
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-035-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-019-03 — Response — Signature bound to a superseded version is rejected

- **Requirement:** CMP-FR-019
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-035-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-020-01 — Closure — required behaviour

- **Requirement:** CMP-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Investigation decision, reportability, CAPA/field action and response complete per policy. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Complete. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-021-01 — Retention — required behaviour

- **Requirement:** CMP-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Apply product/profile/predicate retention policy. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Durable. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-021-02 — Retention — Disposal without an approved decision is refused

- **Requirement:** CMP-FR-021
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-035-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-022-01 — Privacy — required behaviour

- **Requirement:** CMP-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Restrict/minimize personal/health data. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Confidentiality. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-023-01 — Duplicate detection — required behaviour

- **Requirement:** CMP-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Link duplicate reports without deleting original intake. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-024-01 — Export — required behaviour

- **Requirement:** CMP-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `complaint_record`, `complaint_reportability_assessment`, `complaint_communication` in a valid starting state.
- **Test data:** Minimum valid data set for `complaint_record`, `complaint_reportability_assessment`, `complaint_communication`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /qms/v1/complaints` (or the owning command) exercising: Known data, investigation/follow-up or no-investigation rationale, reportability and response exportable. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Inspection-ready. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-QMS-010-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-S001 — Specification scenario — oral complaint

- **Requirement:** SPEC-QMS-010-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: oral complaint | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-S002 — Specification scenario — unknown serial

- **Requirement:** SPEC-QMS-010-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: unknown serial | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-S003 — Specification scenario — autoinjector constituent issue

- **Requirement:** SPEC-QMS-010-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: autoinjector constituent issue | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-S004 — Specification scenario — no-investigation rationale

- **Requirement:** SPEC-QMS-010-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: no-investigation rationale | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-S005 — Specification scenario — prior similar complaints

- **Requirement:** SPEC-QMS-010-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: prior similar complaints | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-S006 — Specification scenario — reportability due date

- **Requirement:** SPEC-QMS-010-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: reportability due date | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-S007 — Specification scenario — CAPA

- **Requirement:** SPEC-QMS-010-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: CAPA | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-S008 — Specification scenario — field action trigger

- **Requirement:** SPEC-QMS-010-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: field action trigger | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-S009 — Specification scenario — privacy restriction

- **Requirement:** SPEC-QMS-010-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: privacy restriction | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-S010 — Specification scenario — duplicate intake

- **Requirement:** SPEC-QMS-010-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: duplicate intake | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-035-S011 — Specification scenario — export

- **Requirement:** SPEC-QMS-010-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: export | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____
