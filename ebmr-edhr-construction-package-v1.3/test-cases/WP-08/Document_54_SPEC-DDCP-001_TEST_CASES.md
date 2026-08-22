# Test Cases — Document 54: Prefilled Syringe & Injectable DDCP Manufacturing Profile (SPEC-DDCP-001)

**Work package:** WP-08  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** PFS-FR-001..030 (30)  
**Test cases:** 98  
**Code location:** `services/gxp-api/src/modules/ddcp`  
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

### TC-054-001-01 — Profile master — required behaviour

- **Requirement:** PFS-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Define injectable DDCP subtype, dosage form, presentation, fill volume, strength, device constituent and container-closure architecture. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Concrete product identity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-001-02 — Profile master — Offline buffering and reconnect preserve evidence

- **Requirement:** PFS-FR-001
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-054-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-002-01 — Constituent definition — required behaviour

- **Requirement:** PFS-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Model drug/biologic constituent, syringe/barrel, stopper/plunger, needle/needle shield, tip cap, safety device and packaging as versioned constituents | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Full genealogy. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-002-02 — Constituent definition — Offline buffering and reconnect preserve evidence

- **Requirement:** PFS-FR-002
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-054-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-002-03 — Constituent definition — Concurrent writers on one aggregate

- **Requirement:** PFS-FR-002
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-054-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-003-01 — Bulk drug handoff — required behaviour

- **Requirement:** PFS-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Receive released bulk drug/biologic batch reference with assay/potency, concentration, sterility/bioburden status and expiry/hold constraints. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Constituent handoff. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-003-02 — Bulk drug handoff — Action without the required signature is blocked

- **Requirement:** PFS-FR-003
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-054-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-003-03 — Bulk drug handoff — Signature bound to a superseded version is rejected

- **Requirement:** PFS-FR-003
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-054-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-003-04 — Bulk drug handoff — Illegal state transition is rejected

- **Requirement:** PFS-FR-003
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-054-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-004-01 — Primary components — required behaviour

- **Requirement:** PFS-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Require released lots for barrel/syringe, stopper/plunger, needle/closure and other product-contact components. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No unapproved component. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-004-02 — Primary components — Action without the required signature is blocked

- **Requirement:** PFS-FR-004
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-054-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-004-03 — Primary components — Signature bound to a superseded version is rejected

- **Requirement:** PFS-FR-004
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-054-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-005-01 — Component preparation — required behaviour

- **Requirement:** PFS-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Track washing/depyrogenation/sterilization/ready-to-use status according to configured component route. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Sterile readiness. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-005-02 — Component preparation — Illegal state transition is rejected

- **Requirement:** PFS-FR-005
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-054-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-006-01 — Line readiness — required behaviour

- **Requirement:** PFS-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Filling line, cleanroom, cleaning, SIP/sterilization, environmental state, personnel and filter status all verified before batch stage start. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Aseptic gate. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-006-02 — Line readiness — Illegal state transition is rejected

- **Requirement:** PFS-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-054-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-007-01 — Bulk hold time — required behaviour

- **Requirement:** PFS-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Track bulk compounding-to-filtration/filling hold time and block when released limits exceeded. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Validated timing. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-007-02 — Bulk hold time — Prohibited path is rejected

- **Requirement:** PFS-FR-007
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Track bulk compounding-to-filtration/filling hold time and block when released limits exceeded. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STERILE_FILTRATION_REQUIRED`
- **Depends on:** TC-054-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-007-03 — Bulk hold time — Action without the required signature is blocked

- **Requirement:** PFS-FR-007
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-054-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-007-04 — Bulk hold time — Signature bound to a superseded version is rejected

- **Requirement:** PFS-FR-007
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-054-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-008-01 — Sterile filtration — required behaviour

- **Requirement:** PFS-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: If process uses sterile filtration, bind filter lot/serial, pre/post integrity status, filtration parameters and evidence. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Filtration assurance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-008-02 — Sterile filtration — Illegal state transition is rejected

- **Requirement:** PFS-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-054-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-009-01 — Filling setup — required behaviour

- **Requirement:** PFS-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Record filler, product-contact path, fill program/version, needle/nozzle setup, target fill and line configuration. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Setup evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-009-02 — Filling setup — Concurrent writers on one aggregate

- **Requirement:** PFS-FR-009
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-054-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-010-01 — Fill execution — required behaviour

- **Requirement:** PFS-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Capture batch/cycle group, fill start/end, machine counts, actual/IPC weights or volumes, alarms/interventions and rejects. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Complete filling record. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-010-02 — Fill execution — Prohibited path is rejected

- **Requirement:** PFS-FR-010
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Capture batch/cycle group, fill start/end, machine counts, actual/IPC weights or volumes, alarms/interventions and rejects. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STERILE_FILTRATION_REQUIRED`
- **Depends on:** TC-054-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-011-01 — Fill-weight IPC — required behaviour

- **Requirement:** PFS-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Perform configurable in-process fill weight/volume sampling with method, sample frequency and acceptance rule. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Dose quantity control. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-012-01 — Stoppering/plunging — required behaviour

- **Requirement:** PFS-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Capture plunger/stopper insertion/position and relevant process settings/results. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Closure assembly. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-013-01 — Needle/closure assembly — required behaviour

- **Requirement:** PFS-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Track needle installation/shield/tip cap/closure configuration where applicable. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Device constituent. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-014-01 — Container closure integrity — required behaviour

- **Requirement:** PFS-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Link required CCI/leak/seal tests by lot/sample plan/method and release state. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** System integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-014-02 — Container closure integrity — Action without the required signature is blocked

- **Requirement:** PFS-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-054-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-014-03 — Container closure integrity — Signature bound to a superseded version is rejected

- **Requirement:** PFS-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-054-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-014-04 — Container closure integrity — Illegal state transition is rejected

- **Requirement:** PFS-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-054-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-015-01 — Visual inspection — required behaviour

- **Requirement:** PFS-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: 100% or configured inspection records machine/manual inspection version, defect codes, rejects and sampling verification. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Finished presentation quality. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-015-02 — Visual inspection — Prohibited path is rejected

- **Requirement:** PFS-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: 100% or configured inspection records machine/manual inspection version, defect codes, rejects and sampling verification. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STERILE_FILTRATION_REQUIRED`
- **Depends on:** TC-054-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-015-03 — Visual inspection — Concurrent writers on one aggregate

- **Requirement:** PFS-FR-015
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-054-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-016-01 — Silicone/tungsten/particulate profile — required behaviour

- **Requirement:** PFS-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support product-specific material/process attributes or QC references when defined in the product's released control strategy. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Product-specific extensibility. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-016-02 — Silicone/tungsten/particulate profile — Action without the required signature is blocked

- **Requirement:** PFS-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-054-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-016-03 — Silicone/tungsten/particulate profile — Signature bound to a superseded version is rejected

- **Requirement:** PFS-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-054-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-017-01 — Functional syringe tests — required behaviour

- **Requirement:** PFS-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support break-loose/glide force, needle shield/removal force, dose delivery, leakage or other device output tests when included in released specificat | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Device performance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-017-02 — Functional syringe tests — Action without the required signature is blocked

- **Requirement:** PFS-FR-017
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-054-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-017-03 — Functional syringe tests — Signature bound to a superseded version is rejected

- **Requirement:** PFS-FR-017
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-054-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-017-04 — Functional syringe tests — Limit boundary behaviour

- **Requirement:** PFS-FR-017
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-054-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-018-01 — Safety feature assembly — required behaviour

- **Requirement:** PFS-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: If needle-safety/guard device exists, track subassembly lot, assembly process and functional test. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Safety constituent. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-018-02 — Safety feature assembly — Offline buffering and reconnect preserve evidence

- **Requirement:** PFS-FR-018
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-054-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-019-01 — Serialization/UDI hooks — required behaviour

- **Requirement:** PFS-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support device/combination-product identifier/UDI configuration where applicable; actual applicability is regulatory-profile controlled. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Future compliance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-019-02 — Serialization/UDI hooks — Offline buffering and reconnect preserve evidence

- **Requirement:** PFS-FR-019
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-054-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-020-01 — Label/packaging — required behaviour

- **Requirement:** PFS-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Link label/artwork version, carton/IFU, lot/expiry and packaging reconciliation. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Finished unit trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-020-02 — Label/packaging — Concurrent writers on one aggregate

- **Requirement:** PFS-FR-020
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-054-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-021-01 — Unit/lot genealogy — required behaviour

- **Requirement:** PFS-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Drug bulk → component lots → filled syringe lot/unit/sample → packaged lot/device ID relationships preserved. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** End-to-end trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-021-02 — Unit/lot genealogy — Offline buffering and reconnect preserve evidence

- **Requirement:** PFS-FR-021
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-054-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-022-01 — Yield reconciliation — required behaviour

- **Requirement:** PFS-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Reconcile bulk issued, units filled, rejects, samples, line loss and finished packed quantity. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Mass/unit balance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-022-02 — Yield reconciliation — Prohibited path is rejected

- **Requirement:** PFS-FR-022
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Reconcile bulk issued, units filled, rejects, samples, line loss and finished packed quantity. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STERILE_FILTRATION_REQUIRED`
- **Depends on:** TC-054-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-022-03 — Yield reconciliation — Limit boundary behaviour

- **Requirement:** PFS-FR-022
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-054-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-023-01 — Constituent release — required behaviour

- **Requirement:** PFS-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Drug and device-constituent evidence may have separate release checkpoints; final DDCP release remains independent. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Part 4 profile. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-023-02 — Constituent release — Action without the required signature is blocked

- **Requirement:** PFS-FR-023
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-054-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-023-03 — Constituent release — Signature bound to a superseded version is rejected

- **Requirement:** PFS-FR-023
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-054-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-023-04 — Constituent release — Offline buffering and reconnect preserve evidence

- **Requirement:** PFS-FR-023
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-054-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-024-01 — Final release blockers — required behaviour

- **Requirement:** PFS-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Open deviations/OOS, failed filter integrity, EM excursion, CCI/functional failure, unresolved reconciliation or missing constituent evidence block re | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No incomplete release. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-024-02 — Final release blockers — Prohibited path is rejected

- **Requirement:** PFS-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Open deviations/OOS, failed filter integrity, EM excursion, CCI/functional failure, unresolved reconciliation or missing constituent evidenc | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STERILE_FILTRATION_REQUIRED`
- **Depends on:** TC-054-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-024-03 — Final release blockers — Action without the required signature is blocked

- **Requirement:** PFS-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-054-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-024-04 — Final release blockers — Signature bound to a superseded version is rejected

- **Requirement:** PFS-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-054-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-025-01 — Batch review package — required behaviour

- **Requirement:** PFS-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Review shows critical aseptic timeline, filtration, fill IPC, interventions, defects, device tests, genealogy and deviations. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Review-by-exception. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-025-02 — Batch review package — Offline buffering and reconnect preserve evidence

- **Requirement:** PFS-FR-025
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-054-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-026-01 — Stability/retain refs — required behaviour

- **Requirement:** PFS-FR-026
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Create/reference stability/retain sample plans and finished lot samples where configured. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Lifecycle support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-027-01 — Rework restriction — required behaviour

- **Requirement:** PFS-FR-027
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Filled primary container rework/reprocessing routes are profile-specific and default disallowed unless released procedure explicitly permits. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Safe default. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-027-02 — Rework restriction — Action without the required signature is blocked

- **Requirement:** PFS-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-054-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-027-03 — Rework restriction — Signature bound to a superseded version is rejected

- **Requirement:** PFS-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-054-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-028-01 — Biologic subtype — required behaviour

- **Requirement:** PFS-FR-028
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Biologic constituent can reuse profile, but biologic-specific requirements remain separately enabled/baselined; no implicit equivalency. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Future profile. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-029-01 — Change sensitivity — required behaviour

- **Requirement:** PFS-FR-029
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Changes to syringe/barrel/stopper/needle/silicone/closure/fill program/filter/control strategy link Change Control and risk/validation impact. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Lifecycle. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-030-01 — Inspection export — required behaviour

- **Requirement:** PFS-FR-030
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** Minimum valid data set for `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Produce one reproducible PFS/DDCP batch package including drug + device constituent + combined-product evidence. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Inspection-ready. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-030-02 — Inspection export — Offline buffering and reconnect preserve evidence

- **Requirement:** PFS-FR-030
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `ddcp_profile_version`, `constituent_requirement`, `constituent_handoff` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-054-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-DDCP-001-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-S001 — Specification scenario — unreleased bulk blocked

- **Requirement:** SPEC-DDCP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: unreleased bulk blocked | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-S002 — Specification scenario — wrong stopper/syringe lot blocked

- **Requirement:** SPEC-DDCP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: wrong stopper/syringe lot blocked | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-S003 — Specification scenario — clean hold expired

- **Requirement:** SPEC-DDCP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: clean hold expired | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-S004 — Specification scenario — filter post-use integrity failed

- **Requirement:** SPEC-DDCP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: filter post-use integrity failed | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-S005 — Specification scenario — fill IPC OOS

- **Requirement:** SPEC-DDCP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: fill IPC OOS | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-S006 — Specification scenario — unplanned aseptic intervention

- **Requirement:** SPEC-DDCP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: unplanned aseptic intervention | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-S007 — Specification scenario — count source retry duplicate

- **Requirement:** SPEC-DDCP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: count source retry duplicate | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-S008 — Specification scenario — visual reject reconciliation

- **Requirement:** SPEC-DDCP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: visual reject reconciliation | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-S009 — Specification scenario — CCI sample failure

- **Requirement:** SPEC-DDCP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: CCI sample failure | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-S010 — Specification scenario — device functional test fail

- **Requirement:** SPEC-DDCP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: device functional test fail | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-S011 — Specification scenario — component change after batch issue does not alter snapshot

- **Requirement:** SPEC-DDCP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: component change after batch issue does not alter snapshot | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-054-S012 — Specification scenario — final release with device constituent incomplete denied

- **Requirement:** SPEC-DDCP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: final release with device constituent incomplete denied | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____
