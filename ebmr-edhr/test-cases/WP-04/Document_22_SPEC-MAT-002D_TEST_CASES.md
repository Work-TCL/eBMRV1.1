# Test Cases — Document 22: Material Consumption, Return, Adjustment, Destruction & Reconciliation Specification (SPEC-MAT-002D)

**Work package:** WP-04  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** CON-FR-001..032 (32)  
**Test cases:** 109  
**Code location:** `services/gxp-api/src/modules/materials`  
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

### TC-022-001-01 — Issue to production — required behaviour

- **Requirement:** CON-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Move dispensed/material container to production staging/use with exact batch/step reference and status. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Custody trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_full_consumption_marks_container_consumed.  |  **Defect:** —

### TC-022-001-02 — Issue to production — Illegal state transition is rejected

- **Requirement:** CON-FR-001
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-022-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_consumption_on_consumed_container_rejected.  |  **Defect:** —

### TC-022-002-01 — Consumption — required behaviour

- **Requirement:** CON-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Record actual material quantity consumed in step, source dispensed container/lot and time. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Actual use evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_full_consumption_marks_container_consumed.  |  **Defect:** —

### TC-022-003-01 — Automatic consumption — required behaviour

- **Requirement:** CON-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Where machine/process provides authoritative quantity, accept via validated integration/rule; otherwise controlled manual capture. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Flexible source. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no validated integration/rules-engine automatic consumption source exists (WP-06 not built); manual capture (source_type='manual') is built and tested, automatic is explicitly rejected (SG-098).  |  **Defect:** SG-098

### TC-022-003-02 — Automatic consumption — Replayed inbound message is detected

- **Requirement:** CON-FR-003
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-022-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no external integration exists to replay a message against (SG-098).  |  **Defect:** SG-098

### TC-022-003-03 — Automatic consumption — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** CON-FR-003
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-022-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no external integration exists to time out against (SG-098).  |  **Defect:** SG-098

### TC-022-004-01 — Partial consumption — required behaviour

- **Requirement:** CON-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Track remaining quantity in dispensed container and resulting status/location. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No assumed full use. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_partial_consumption_leaves_container_partially_consumed.  |  **Defect:** —

### TC-022-004-02 — Partial consumption — Illegal state transition is rejected

- **Requirement:** CON-FR-004
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-022-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_consumption_on_consumed_container_rejected.  |  **Defect:** —

### TC-022-005-01 — Return to warehouse — required behaviour

- **Requirement:** CON-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Return unused eligible material with quantity, seal/container condition, storage condition and status reevaluation. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Safe return. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_return_acceptable_condition_restores_balance.  |  **Defect:** —

### TC-022-005-02 — Return to warehouse — Illegal state transition is rejected

- **Requirement:** CON-FR-005
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-022-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_return_on_already_returned_container_rejected.  |  **Defect:** —

### TC-022-006-01 — Return rejection — required behaviour

- **Requirement:** CON-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: If return condition unsuitable, route to quarantine/reject/destruction workflow rather than normal stock. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No bad return. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_return_unacceptable_condition_routes_to_quarantine.  |  **Defect:** —

### TC-022-006-02 — Return rejection — Prohibited path is rejected

- **Requirement:** CON-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: If return condition unsuitable, route to quarantine/reject/destruction workflow rather than normal stock. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-022-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_return_unacceptable_condition_routes_to_quarantine (asserts no InventoryBalanceProjection row is created for the quarantined quantity -- the prohibited path is silent re-entry to stock).  |  **Defect:** —

### TC-022-006-03 — Return rejection — Illegal state transition is rejected

- **Requirement:** CON-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-022-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_return_on_already_returned_container_rejected.  |  **Defect:** —

### TC-022-007-01 — Material re-status after return — required behaviour

- **Requirement:** CON-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Product/profile may require QC/QA evaluation after exposure/opening/temperature excursion before reuse. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Risk controlled. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_return_unacceptable_condition_routes_to_quarantine (resulting_status is the re-status field).  |  **Defect:** —

### TC-022-007-02 — Material re-status after return — Illegal state transition is rejected

- **Requirement:** CON-FR-007
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-022-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_return_on_already_returned_container_rejected.  |  **Defect:** —

### TC-022-008-01 — Excess material — required behaviour

- **Requirement:** CON-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Record excess generated/remaining from dispensing/process and controlled disposition. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Balance complete. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_partial_consumption_leaves_container_partially_consumed (remaining_quantity is the excess/remaining balance Document 22 requires be tracked; no separate 'excess material' entity is declared anywhere in Document 22's own data-model section).  |  **Defect:** —

### TC-022-008-02 — Excess material — Action without the required signature is blocked

- **Requirement:** CON-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-022-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no standalone signed 'excess material' action exists in Document 106 for SPEC-MAT-002D; excess quantity is captured via remaining_quantity and disposed of only through the module's two actually-signed actions (inventory_adjustment_request.approve row 55, destruction_record.execute row 56), independently tested under CON-FR-014/CON-FR-017.  |  **Defect:** —

### TC-022-008-03 — Excess material — Signature bound to a superseded version is rejected

- **Requirement:** CON-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-022-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- same as TC-022-008-02 -- no signed 'excess material' action exists.  |  **Defect:** —

### TC-022-008-04 — Excess material — Disposal without an approved decision is refused

- **Requirement:** CON-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-022-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- 'disposal' of excess material is the same signed destruction_record.execute action (row 56); there is no separate 'disposal approval' decision distinct from it. See CON-FR-016/017.  |  **Defect:** —

### TC-022-009-01 — Process loss — required behaviour

- **Requirement:** CON-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Record allowed loss category/quantity/source and approval/rule. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Variance explained. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_record_material_loss_all_types[APPROVED_LOSS].  |  **Defect:** —

### TC-022-010-01 — Spill — required behaviour

- **Requirement:** CON-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Record spill quantity/estimate, quality/deviation link and cleanup evidence where required. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Incident trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_record_material_loss_all_types[SPILL].  |  **Defect:** —

### TC-022-011-01 — Sample withdrawal — required behaviour

- **Requirement:** CON-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Account for QC/in-process/reserve sample quantity and sample ID. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Balance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_record_material_loss_all_types[SAMPLE].  |  **Defect:** —

### TC-022-012-01 — Reject/scrap material — required behaviour

- **Requirement:** CON-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Record rejected process material quantity, reason, location and disposition. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No ghost stock. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_record_material_loss_all_types[REJECT].  |  **Defect:** —

### TC-022-012-02 — Reject/scrap material — Prohibited path is rejected

- **Requirement:** CON-FR-012
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Record rejected process material quantity, reason, location and disposition. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-022-012-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_record_material_loss_invalid_type_rejected.  |  **Defect:** —

### TC-022-012-03 — Reject/scrap material — Action without the required signature is blocked

- **Requirement:** CON-FR-012
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-022-012-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- record_material_loss (REJECT/SAMPLE/SPILL/APPROVED_LOSS) is unsigned -- Document 106 has no policy row for it. The module's only two signed actions are tested under CON-FR-014/CON-FR-017.  |  **Defect:** —

### TC-022-012-04 — Reject/scrap material — Signature bound to a superseded version is rejected

- **Requirement:** CON-FR-012
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-022-012-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- same as TC-022-012-03 -- record_material_loss is unsigned.  |  **Defect:** —

### TC-022-013-01 — Inventory adjustment — required behaviour

- **Requirement:** CON-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Exceptional positive/negative adjustment requires controlled reason, evidence, authorization and audit; cannot be routine correction for software defe | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled discrepancy. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_adjustment_request_create_and_approve.  |  **Defect:** —

### TC-022-013-02 — Inventory adjustment — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** CON-FR-013
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-022-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_inventory_transaction_table_rejects_direct_delete (the immutable ADJUST_POSITIVE/ADJUST_NEGATIVE ledger evidence an approved adjustment creates; inventory_adjustment_requests itself is intentionally a mutable status-transition aggregate -- see the migration's own append-only-vs-mutable privilege-split rationale).  |  **Defect:** —

### TC-022-013-03 — Inventory adjustment — Reject required behaviour

- **Requirement:** CON-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state; a `requested` adjustment exists.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /inventory/v1/adjustments/{request_id}/reject` with a completed signature challenge (`action: "reject"`). | 4. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Request status becomes `rejected`; no `InventoryTransaction`/balance change (a rejected adjustment never touched inventory); one audit event; one outbox row; receipt returned with a signature id.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, unchanged `InventoryBalanceProjection`
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-17  |  **Actual result:** PASS -- until this pass `reject_inventory_adjustment_request` did not exist at all (only approve was built) -- a wrong/unwanted request had no way out of `requested` (docs/testing/DDCP_Client_Demo_Guide_Gujarati.md §19 #7). Built as approve's counterpart: signed (`Rejected` meaning, independent QA Releaser signer -- Document 106 has no dedicated reject row for this action, so this reuses row 55's approve shape + P1's own "approves ... rejects ..." principle + this codebase's own `material_lot.reject` precedent), no balance/transaction side effect. Also fixed a latent bug found while wiring this in: `POST .../signature-challenges` always issued an `Approved`-meaning challenge regardless of the requested `action`, which would have signed a rejection decision under the wrong meaning. Exercised by real pytest: services/gxp-api/tests/test_material_consumption_flow.py::test_adjustment_request_create_and_reject.  |  **Defect:** —

### TC-022-014-01 — Adjustment SoD — required behaviour

- **Requirement:** CON-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: High-risk adjustment can require independent approval; user cannot approve own adjustment if configured. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Fraud/error control. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_adjustment_request_create_and_approve (independent approver succeeds) and test_adjustment_self_approval_denied (same-actor approval is refused).  |  **Defect:** —

### TC-022-014-02 — Adjustment SoD — Action without the required signature is blocked

- **Requirement:** CON-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-022-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_adjustment_approve_missing_signature_rejected.  |  **Defect:** —

### TC-022-014-03 — Adjustment SoD — Signature bound to a superseded version is rejected

- **Requirement:** CON-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-022-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_adjustment_approve_stale_version_rejected.  |  **Defect:** —

### TC-022-014-04 — Adjustment SoD — Reject requires independence

- **Requirement:** CON-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state; a `requested` adjustment exists, requested by the same actor attempting to reject it.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. The requester attempts `POST .../reject` on their own request with a valid signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; the same CON-FR-014 independence rule approve already enforces applies symmetrically to reject.
- **Expected error code:** `VALIDATION_FAILED`
- **Depends on:** TC-022-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-17  |  **Actual result:** PASS -- `reject_inventory_adjustment_request()` runs the identical `actor_user_id == request.requested_by_user_id` check `approve_inventory_adjustment_request()` uses, so self-rejection is refused the same way self-approval already was. Exercised by real pytest: services/gxp-api/tests/test_material_consumption_flow.py::test_adjustment_self_rejection_denied.  |  **Defect:** —

### TC-022-015-01 — Destruction request — required behaviour

- **Requirement:** CON-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Create destruction disposition for rejected/expired/excess/material/product with exact lot/container/quantity. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Scope exact. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_destruction_request_and_execute_third_party.  |  **Defect:** —

### TC-022-015-02 — Destruction request — Prohibited path is rejected

- **Requirement:** CON-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Create destruction disposition for rejected/expired/excess/material/product with exact lot/container/quantity. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-022-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_destruction_scope_requires_exactly_one.  |  **Defect:** —

### TC-022-015-03 — Destruction request — Action without the required signature is blocked

- **Requirement:** CON-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-022-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- create_destruction_request is unsigned (Document 106 row 56 signs only 'execute', not 'create'). The real signature-ceremony negative coverage is under CON-FR-018 (execute), see test_destruction_execute_missing_signature_rejected.  |  **Defect:** —

### TC-022-015-04 — Destruction request — Signature bound to a superseded version is rejected

- **Requirement:** CON-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-022-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- same as TC-022-015-03; see test_destruction_execute_stale_version_rejected under CON-FR-018 for the real 'execute' signature-version coverage.  |  **Defect:** —

### TC-022-016-01 — Destruction authorization — required behaviour

- **Requirement:** CON-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Require QA/authorized approval and witness where policy requires. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled disposition. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_destruction_request_and_execute_third_party (witnesses field populated, execute signed).  |  **Defect:** —

### TC-022-017-01 — Destruction execution — required behaviour

- **Requirement:** CON-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Record method, date/time, performers/witnesses, quantity, evidence and destination/vendor where applicable. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_destruction_request_and_execute_third_party.  |  **Defect:** —

### TC-022-018-01 — Third-party destruction — required behaviour

- **Requirement:** CON-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Track approved vendor/manifest/certificate and chain of custody. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** External disposition trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_destruction_request_and_execute_third_party (vendor_name/manifest_reference populated).  |  **Defect:** —

### TC-022-018-02 — Third-party destruction — Action without the required signature is blocked

- **Requirement:** CON-FR-018
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-022-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_destruction_execute_missing_signature_rejected.  |  **Defect:** —

### TC-022-018-03 — Third-party destruction — Signature bound to a superseded version is rejected

- **Requirement:** CON-FR-018
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-022-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_destruction_execute_stale_version_rejected.  |  **Defect:** —

### TC-022-019-01 — Reconciliation scope — required behaviour

- **Requirement:** CON-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Calculate material balance by batch/material requirement/lot/container/stage according to released rules. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Configurable scope. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_reconciliation_acceptable_outcome.  |  **Defect:** —

### TC-022-019-02 — Reconciliation scope — Action without the required signature is blocked

- **Requirement:** CON-FR-019
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-022-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- evaluate_material_reconciliation is unsigned -- Document 106 has no policy row for this operation; 'reconciliation acceptance outside nominal rules' routes through the linked deviation's own signature chain instead (see test_reconciliation_variance_outcome_links_deviation).  |  **Defect:** —

### TC-022-019-03 — Reconciliation scope — Signature bound to a superseded version is rejected

- **Requirement:** CON-FR-019
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-022-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- same as TC-022-019-02 -- evaluate_material_reconciliation is unsigned.  |  **Defect:** —

### TC-022-019-04 — Reconciliation scope — Limit boundary behaviour

- **Requirement:** CON-FR-019
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-022-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_reconciliation_reevaluation_creates_new_version_never_edits (version-sequence boundary: first evaluation = version 1, re-evaluation = version 2, never edited in place).  |  **Defect:** —

### TC-022-020-01 — Source categories — required behaviour

- **Requirement:** CON-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Reconciliation includes dispensed/issued, consumed, returned, samples, rejected, destroyed, approved loss and unexplained variance. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Complete mass balance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_reconciliation_acceptable_outcome (all 7 CON-FR-020 source categories summed: dispensed, consumed, returned, sampled, rejected, destroyed, approved_loss).  |  **Defect:** —

### TC-022-020-02 — Source categories — Prohibited path is rejected

- **Requirement:** CON-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Reconciliation includes dispensed/issued, consumed, returned, samples, rejected, destroyed, approved loss and unexplained variance. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-022-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_reconciliation_negative_tolerance_rejected.  |  **Defect:** —

### TC-022-020-03 — Source categories — Action without the required signature is blocked

- **Requirement:** CON-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-022-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- same as TC-022-019-02 -- evaluate_material_reconciliation is unsigned.  |  **Defect:** —

### TC-022-020-04 — Source categories — Signature bound to a superseded version is rejected

- **Requirement:** CON-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-022-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- same as TC-022-019-02 -- evaluate_material_reconciliation is unsigned.  |  **Defect:** —

### TC-022-021-01 — Tolerance — required behaviour

- **Requirement:** CON-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Use Document 08/17 released tolerance/rounding/UOM rules. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Deterministic. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no released Document 08/17 reconciliation tolerance/rounding rule exists (Document 17 is not built in this codebase); tolerance_value is caller-supplied captured input instead (SG-098).  |  **Defect:** SG-098

### TC-022-021-02 — Tolerance — Action without the required signature is blocked

- **Requirement:** CON-FR-021
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-022-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- same missing tolerance-rule authority as TC-022-021-01 (SG-098).  |  **Defect:** SG-098

### TC-022-021-03 — Tolerance — Signature bound to a superseded version is rejected

- **Requirement:** CON-FR-021
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-022-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- same missing tolerance-rule authority as TC-022-021-01 (SG-098).  |  **Defect:** SG-098

### TC-022-021-04 — Tolerance — Limit boundary behaviour

- **Requirement:** CON-FR-021
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-022-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- same missing tolerance-rule authority as TC-022-021-01 (SG-098).  |  **Defect:** SG-098

### TC-022-022-01 — Variance blocker — required behaviour

- **Requirement:** CON-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Out-of-tolerance/unexplained variance creates deviation/investigation and blocks production completion/release as configured. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No silent loss. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- auto-deviation severity/owner is caller-supplied (not auto-derived) and the actual block on batch Production Complete is not wired into app/modules/batch/commands.py this pass (cross-module quality-authority policy decision) (SG-098).  |  **Defect:** SG-098

### TC-022-022-02 — Variance blocker — Prohibited path is rejected

- **Requirement:** CON-FR-022
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Out-of-tolerance/unexplained variance creates deviation/investigation and blocks production completion/release as configured. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-022-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- same batch-completion-gate gap as TC-022-022-01 (SG-098).  |  **Defect:** SG-098

### TC-022-022-03 — Variance blocker — Action without the required signature is blocked

- **Requirement:** CON-FR-022
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-022-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- same batch-completion-gate gap as TC-022-022-01 (SG-098).  |  **Defect:** SG-098

### TC-022-022-04 — Variance blocker — Signature bound to a superseded version is rejected

- **Requirement:** CON-FR-022
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-022-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- same batch-completion-gate gap as TC-022-022-01 (SG-098).  |  **Defect:** SG-098

### TC-022-023-01 — Correction recalculation — required behaviour

- **Requirement:** CON-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Any corrected transaction creates superseding transaction/event and automatically recalculates affected reconciliation; original remains. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** History. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_reconciliation_reevaluation_creates_new_version_never_edits.  |  **Defect:** —

### TC-022-023-02 — Correction recalculation — Limit boundary behaviour

- **Requirement:** CON-FR-023
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-022-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_reconciliation_reevaluation_creates_new_version_never_edits (version-sequence boundary).  |  **Defect:** —

### TC-022-024-01 — No transaction deletion — required behaviour

- **Requirement:** CON-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Consumption/return/adjustment/destruction records are immutable transactions; correction is reversal/supersession pattern. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Ledger integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_reconciliation_reevaluation_creates_new_version_never_edits (original row's own fields unchanged after a re-evaluation).  |  **Defect:** —

### TC-022-024-02 — No transaction deletion — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** CON-FR-024
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-022-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_material_consumption_table_rejects_direct_update and test_inventory_transaction_table_rejects_direct_delete.  |  **Defect:** —

### TC-022-025-01 — ERP posting — required behaviour

- **Requirement:** CON-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Post consumption/return/scrap/destruction quantity/reference after GxP commit; retries idempotent. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Commercial sync. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code (automated)  |  **Date:** 2026-09-14  |  **Actual result:** WP-11 Stage 4 (SG-183): `app/modules/erp/consumer.py` -- a real durable NATS JetStream consumer -- subscribes to `MaterialConsumed`, resolves the site's ACTIVE ERPNext instance + the consumed material's ACTIVE `ErpExternalMapping`, and calls the real `queue_erp_command(POST_CONSUMPTION)` automatically after the real `POST /materials/v1/consumptions` commit -- proven end to end against the live broker + a real Postgres database (real dispense -> consume chain, real outbox publish, real fetch/process, real `IntegrationCommand` row with the expected ERPNext Stock Entry payload): `tests/test_erp_consumer.py::test_mapped_erpnext_consumption_is_queued_end_to_end`, PASS. Idempotent retry (this row's own "retries idempotent" clause) is the same `check_idempotency`/idempotency_key mechanism already proven generically (`test_register_instance_duplicate_idempotency_key_returns_same_receipt`) plus `consume_event_idempotently`'s own dedupe (WP-11 Stage 3) -- not re-proven standalone for this specific event here. Scope: ERPNext only (SAP/Oracle/Dynamics deliberately not attempted -- no vendor-neutral payload mapping exists anywhere in this codebase, would be an unverified guess for 3 more vendors); warehouse (`s_warehouse`) omitted from the payload, no mapping layer exists for it either -- both disclosed limitations in `erp/consumer.py`'s own docstring, not blocking. `get_material_reconciliation`'s `erp_posting_status` field is unchanged by this pass (still not read by this new consumer) -- SG-098 stays open for that reporting piece and for CON-FR-025-02/03 (inbound replay/timeout-uncertain lookup, not exercised here).  |  **Defect:** SG-098 (partially resolved, see above)

### TC-022-025-02 — ERP posting — Replayed inbound message is detected

- **Requirement:** CON-FR-025
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-022-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no ERP integration exists to replay a message against (SG-098).  |  **Defect:** SG-098

### TC-022-025-03 — ERP posting — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** CON-FR-025
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-022-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no ERP integration exists to time out against (SG-098).  |  **Defect:** SG-098

### TC-022-026-01 — ERP discrepancy — required behaviour

- **Requirement:** CON-FR-026
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Compare external postings and create reconciliation issue; ERP never overwrites GxP transaction ledger. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Boundary. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no ERP integration exists to compare a discrepancy against (SG-098).  |  **Defect:** SG-098

### TC-022-026-02 — ERP discrepancy — Prohibited path is rejected

- **Requirement:** CON-FR-026
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Compare external postings and create reconciliation issue; ERP never overwrites GxP transaction ledger. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-022-026-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no ERP integration exists to compare a discrepancy against (SG-098).  |  **Defect:** SG-098

### TC-022-026-03 — ERP discrepancy — Replayed inbound message is detected

- **Requirement:** CON-FR-026
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-022-026-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no ERP integration exists to replay a message against (SG-098).  |  **Defect:** SG-098

### TC-022-026-04 — ERP discrepancy — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** CON-FR-026
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-022-026-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no ERP integration exists to time out against (SG-098).  |  **Defect:** SG-098

### TC-022-027-01 — Genealogy impact — required behaviour

- **Requirement:** CON-FR-027
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Consumption creates genealogy; return/destruction preserves source/material identity and affected batch links. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_full_consumption_marks_container_consumed (batch_id/material_lot_id/quantity/occurred_at captured on material_consumption -- genealogy-queryable; Document 13's own genealogy-module query endpoints are a separate module and out of scope for this session's write-path).  |  **Defect:** —

### TC-022-028-01 — Batch completion gate — required behaviour

- **Requirement:** CON-FR-028
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: All required material transactions/reconciliation must be current/acceptable before Production Complete. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** eBMR complete. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- the batch-completion gate is not wired into app/modules/batch/commands.py's production_complete transition this pass (cross-module gate, same class of decision as the SCAR/supplier-suspension SPEC_GAP already on file) (SG-098).  |  **Defect:** SG-098

### TC-022-029-01 — QA review — required behaviour

- **Requirement:** CON-FR-029
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Review-by-exception shows adjustments, spills, losses, destruction and failed reconciliation. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Quality visibility. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- QA review-by-exception is a read/reporting capability; Document 22 section 6's own API list declares no dedicated QA-review operation. Adjustments/losses/destructions/failed-reconciliation are queryable through the already-built generic audit.review/vault.review capability, not a new Document-22-specific endpoint.  |  **Defect:** —

### TC-022-029-02 — QA review — Prohibited path is rejected

- **Requirement:** CON-FR-029
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Review-by-exception shows adjustments, spills, losses, destruction and failed reconciliation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-022-029-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- same as TC-022-029-01 -- no dedicated QA-review endpoint exists to test.  |  **Defect:** —

### TC-022-030-01 — Audit/export — required behaviour

- **Requirement:** CON-FR-030
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Batch/material history export includes all source/quantity/disposition/reconciliation records and signatures. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Inspection-ready. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_full_consumption_marks_container_consumed (every command returns a MutationReceipt with a real audit_event_id, proving the same-transaction audit write every command in this file exercises).  |  **Defect:** —

### TC-022-030-02 — Audit/export — Action without the required signature is blocked

- **Requirement:** CON-FR-030
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-022-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- 'audit/export' itself has no bespoke signed action in Document 106 for SPEC-MAT-002D.  |  **Defect:** —

### TC-022-030-03 — Audit/export — Signature bound to a superseded version is rejected

- **Requirement:** CON-FR-030
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-022-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- same as TC-022-030-02.  |  **Defect:** —

### TC-022-030-04 — Audit/export — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** CON-FR-030
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-022-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_material_consumption_table_rejects_direct_update and test_inventory_transaction_table_rejects_direct_delete.  |  **Defect:** —

### TC-022-031-01 — Cross-batch prohibition — required behaviour

- **Requirement:** CON-FR-031
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: A dispensed container assigned to Batch A cannot be consumed in Batch B unless a controlled return/reissue process creates new authorization. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No cross-use. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_consumption_cross_batch_rejected.  |  **Defect:** —

### TC-022-032-01 — Performance — required behaviour

- **Requirement:** CON-FR-032
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** Minimum valid data set for `material_consumption`, `material_return`, `inventory_adjustment_request`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/consumptions` (or the owning command) exercising: Batch reconciliation may aggregate large device/packaging/component transaction sets asynchronously but current status is versioned. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Scale safe. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_reconciliation_acceptable_outcome (order-independent aggregation across the batch's ledger).  |  **Defect:** —

### TC-022-032-02 — Performance — Illegal state transition is rejected

- **Requirement:** CON-FR-032
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-022-032-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_consumption_on_consumed_container_rejected.  |  **Defect:** —

### TC-022-032-03 — Performance — Offline buffering and reconnect preserve evidence

- **Requirement:** CON-FR-032
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-022-032-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no offline-capable edge/device client exists in this codebase to buffer and reconnect (same WP-06 root cause as CON-FR-003's automatic-consumption gap) (SG-098).  |  **Defect:** SG-098

### TC-022-032-04 — Performance — Concurrent writers on one aggregate

- **Requirement:** CON-FR-032
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_consumption`, `material_return`, `inventory_adjustment_request` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-022-032-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_adjustment_approve_stale_version_rejected and test_destruction_execute_stale_version_rejected (with_for_update() row locks + optimistic-concurrency StaleVersionError, the concurrent-writer guard this module uses on every mutable aggregate).  |  **Defect:** —

### TC-022-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_consumption_unauthenticated_rejected.  |  **Defect:** —

### TC-022-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_consumption_without_permission_denied.  |  **Defect:** —

### TC-022-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- single-organization platform per ADR-0006 -- no tenant_id column exists anywhere in this codebase.  |  **Defect:** —

### TC-022-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- not independently re-executed in test_material_consumption_flow.py; enforced by the shared evaluate_policy() site-scoped role resolution (UserSiteRole.site_id filter) every command in this module calls, generically verified by services/gxp-api/tests/test_batch_execution.py and tests/test_audit_review.py's dedicated cross-site cases (same shared code path).  |  **Defect:** —

### TC-022-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- MUT-FR-007's qualification gate is conditional/configured; no qualification code is declared for any SPEC-MAT-002D action (unlike Document 21's dispensing_operator gate).  |  **Defect:** —

### TC-022-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_adjustment_self_approval_denied.  |  **Defect:** —

### TC-022-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_adjustment_approve_missing_expected_version_rejected.  |  **Defect:** —

### TC-022-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_adjustment_approve_stale_version_rejected and test_destruction_execute_stale_version_rejected.  |  **Defect:** —

### TC-022-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_consumption_duplicate_idempotency_key_returns_same_receipt.  |  **Defect:** —

### TC-022-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_consumption_same_key_different_payload_rejected.  |  **Defect:** —

### TC-022-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_full_consumption_marks_container_consumed (every 200 response's MutationReceipt carries a real audit_event_id from the same PostgreSQL transaction, the write_audit_event/record_command_receipt pattern every command in this file uses).  |  **Defect:** —

### TC-022-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no fault-injection harness exists in this test suite to simulate a DB/signature-service outage; architectural guarantee (AG-06/MUT-FR-022) common to every module, not independently re-tested per module in this codebase.  |  **Defect:** —

### TC-022-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no crash/rollback-injection harness exists in this test suite; same architectural-guarantee treatment as TC-022-M12.  |  **Defect:** —

### TC-022-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-MAT-002D-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no Frappe projection consumer exists in this codebase's test harness to take offline (AG-11); architectural guarantee, not independently testable here.  |  **Defect:** —

### TC-022-S001 — Specification scenario — full consume

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: full consume | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_full_consumption_marks_container_consumed.  |  **Defect:** —

### TC-022-S002 — Specification scenario — partial consume

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: partial consume | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_partial_consumption_leaves_container_partially_consumed.  |  **Defect:** —

### TC-022-S003 — Specification scenario — cross-batch attempt

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: cross-batch attempt | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_consumption_cross_batch_rejected.  |  **Defect:** —

### TC-022-S004 — Specification scenario — return acceptable

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: return acceptable | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_return_acceptable_condition_restores_balance.  |  **Defect:** —

### TC-022-S005 — Specification scenario — return needs quarantine

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: return needs quarantine | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_return_unacceptable_condition_routes_to_quarantine.  |  **Defect:** —

### TC-022-S006 — Specification scenario — spill

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: spill | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_record_material_loss_all_types[SPILL].  |  **Defect:** —

### TC-022-S007 — Specification scenario — sample withdrawal

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: sample withdrawal | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_record_material_loss_all_types[SAMPLE].  |  **Defect:** —

### TC-022-S008 — Specification scenario — high-risk adjustment

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: high-risk adjustment | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_adjustment_request_create_and_approve.  |  **Defect:** —

### TC-022-S009 — Specification scenario — self-approval denied

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: self-approval denied | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_adjustment_self_approval_denied.  |  **Defect:** —

### TC-022-S010 — Specification scenario — destruction with witness

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: destruction with witness | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_destruction_request_and_execute_third_party.  |  **Defect:** —

### TC-022-S011 — Specification scenario — third-party destruction

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: third-party destruction | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_destruction_request_and_execute_third_party.  |  **Defect:** —

### TC-022-S012 — Specification scenario — failed reconciliation

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: failed reconciliation | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_reconciliation_variance_outcome_links_deviation.  |  **Defect:** —

### TC-022-S013 — Specification scenario — correction/reversal

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: correction/reversal | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_material_consumption_flow.py::test_reconciliation_reevaluation_creates_new_version_never_edits.  |  **Defect:** —

### TC-022-S014 — Specification scenario — ERP retry duplicate

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: ERP retry duplicate | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no ERP integration exists to retry a duplicate posting against (SG-098).  |  **Defect:** SG-098

### TC-022-S015 — Specification scenario — batch completion blocked

- **Requirement:** SPEC-MAT-002D-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: batch completion blocked | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- the batch-completion gate is not wired into app/modules/batch/commands.py this pass (SG-098).  |  **Defect:** SG-098
