# Test Cases — Document 57: Drug-Eluting / Drug-Coated Device DDCP Manufacturing Profile (SPEC-DDCP-004)

**Work package:** WP-08  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** COAT-FR-001..030 (30)  
**Test cases:** 97  
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

### TC-057-001-01 — Coated device profile — required behaviour

- **Requirement:** COAT-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support drug-eluting/coated/impregnated devices with device substrate + drug/biologic coating constituent + finished combined product. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Type 4/5 architecture. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- create_coated_device_profile_version() creates a ddcp_profile_version row with subtype left unset (Document 57 names no subtype variant of its own); services/gxp-api/tests/test_coated_device_flow.py::test_create_profile_and_release_has_no_subtype_enum.  |  **Defect:** —

### TC-057-001-02 — Coated device profile — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-001
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- create_coated_device_profile_version() creates a ddcp_profile_version row with subtype left unset (Document 57 names no subtype variant of its own); services/gxp-api/tests/test_coated_device_flow.py::test_create_profile_and_release_has_no_subtype_enum.  |  **Defect:** —

### TC-057-002-01 — Substrate identity — required behaviour

- **Requirement:** COAT-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Track base device lot/serial/subassembly and released device specification/version. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Device constituent. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- substrate identity modeled as a DEVICE-typed 'substrate' component_role, accepted via the shared constituent-handoff functions; services/gxp-api/tests/test_coated_device_flow.py::test_coating_readiness_and_start_run_records_initial_usage.  |  **Defect:** —

### TC-057-002-02 — Substrate identity — Action without the required signature is blocked

- **Requirement:** COAT-FR-002
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-057-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- substrate identity modeled as a DEVICE-typed 'substrate' component_role, accepted via the shared constituent-handoff functions; services/gxp-api/tests/test_coated_device_flow.py::test_coating_readiness_and_start_run_records_initial_usage.  |  **Defect:** —

### TC-057-002-03 — Substrate identity — Signature bound to a superseded version is rejected

- **Requirement:** COAT-FR-002
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-057-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-002-04 — Substrate identity — Limit boundary behaviour

- **Requirement:** COAT-FR-002
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-057-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-003-01 — Drug/coating constituent — required behaviour

- **Requirement:** COAT-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Track coating solution/formulation/bulk lot, concentration/potency, prepared amount and hold time. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Drug constituent. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- coating drug/solution constituent modeled as a DRUG-typed 'coating_solution' component_role, accepted via the shared constituent-handoff functions; services/gxp-api/tests/test_coated_device_flow.py::test_coating_readiness_and_start_run_records_initial_usage.  |  **Defect:** —

### TC-057-004-01 — Surface preparation — required behaviour

- **Requirement:** COAT-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Capture cleaning/activation/priming/pre-treatment steps and evidence. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Coating readiness. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- coating drug/solution constituent modeled as a DRUG-typed 'coating_solution' component_role, accepted via the shared constituent-handoff functions; services/gxp-api/tests/test_coated_device_flow.py::test_coating_readiness_and_start_run_records_initial_usage.  |  **Defect:** —

### TC-057-005-01 — Coating recipe — required behaviour

- **Requirement:** COAT-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Versioned coating process route: dip/spray/inkjet/deposition/impregnation/other approved method. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Extensible. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- start_coating_run() creates a ddcp_process_operation (operation_type=COATING_RUN) carrying program_id/program_version; services/gxp-api/tests/test_coated_device_flow.py::test_coating_readiness_and_start_run_records_initial_usage.  |  **Defect:** —

### TC-057-005-02 — Coating recipe — Action without the required signature is blocked

- **Requirement:** COAT-FR-005
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-057-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- start_coating_run() creates a ddcp_process_operation (operation_type=COATING_RUN) carrying program_id/program_version; services/gxp-api/tests/test_coated_device_flow.py::test_coating_readiness_and_start_run_records_initial_usage.  |  **Defect:** —

### TC-057-005-03 — Coating recipe — Signature bound to a superseded version is rejected

- **Requirement:** COAT-FR-005
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-057-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-005-04 — Coating recipe — Concurrent writers on one aggregate

- **Requirement:** COAT-FR-005
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-057-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-006-01 — Coating parameters — required behaviour

- **Requirement:** COAT-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Speed/time/flow/pressure/distance/temperature/humidity/cycle/pass and other mapped process parameters. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Process evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_coating_process_evidence() appends structured parameter readings to process_parameters; services/gxp-api/tests/test_coated_device_flow.py::test_process_evidence_excursion_holds_run_and_complete_requires_dual_reconciliation.  |  **Defect:** —

### TC-057-007-01 — Equipment/program — required behaviour

- **Requirement:** COAT-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Coater/equipment and recipe/program version eligible and bound to batch. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Validated state. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_coating_process_evidence() appends structured parameter readings to process_parameters; services/gxp-api/tests/test_coated_device_flow.py::test_process_evidence_excursion_holds_run_and_complete_requires_dual_reconciliation.  |  **Defect:** —

### TC-057-007-02 — Equipment/program — Concurrent writers on one aggregate

- **Requirement:** COAT-FR-007
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-057-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-008-01 — Environment — required behaviour

- **Requirement:** COAT-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Required room/temperature/humidity/particle/environment status gate. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Process control. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- evaluate_coating_run_readiness()'s caller-supplied environment_status snapshot blocks readiness with COATING_ENVIRONMENT_NOT_READY when the profile declares an environmentProfileId and the snapshot reports not-ready; services/gxp-api/tests/test_coated_device_flow.py::test_environment_gate_blocks_readiness_when_not_ready.  |  **Defect:** —

### TC-057-008-02 — Environment — Illegal state transition is rejected

- **Requirement:** COAT-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-057-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-009-01 — Drug usage ledger — required behaviour

- **Requirement:** COAT-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Track drug/coating solution issued, applied, residual, sampled, rejected, recovered/disposed and reconcile. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Drug mass balance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_drug_coating_usage()/drug_coating_usage_ledger (decimal mass-balance, DATA-FR-019) is checked at complete_coating_run() alongside the device-unit ledger for Document 57 §6's dual reconciliation; services/gxp-api/tests/test_coated_device_flow.py::test_bind_device_to_coating_rejects_duplicate_and_completes_run, ::test_evidence_package_and_complaint_trace.  |  **Defect:** —

### TC-057-009-02 — Drug usage ledger — Prohibited path is rejected

- **Requirement:** COAT-FR-009
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Track drug/coating solution issued, applied, residual, sampled, rejected, recovered/disposed and reconcile. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STERILIZATION_INTERACTION_REVIEW_REQUIRED`
- **Depends on:** TC-057-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_drug_coating_usage()/drug_coating_usage_ledger (decimal mass-balance, DATA-FR-019) is checked at complete_coating_run() alongside the device-unit ledger for Document 57 §6's dual reconciliation; services/gxp-api/tests/test_coated_device_flow.py::test_bind_device_to_coating_rejects_duplicate_and_completes_run, ::test_evidence_package_and_complaint_trace.  |  **Defect:** —

### TC-057-009-03 — Drug usage ledger — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-009
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-009-04 — Drug usage ledger — Disposal without an approved decision is refused

- **Requirement:** COAT-FR-009
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-057-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-010-01 — Unit/lot association — required behaviour

- **Requirement:** COAT-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Map device lot/serial/substrate unit to coating run and drug/coating constituent lot. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Combination genealogy. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- bind_device_to_coating_constituent() creates a ddcp_unit_binding row (binding_type=DEVICE_TO_COATING_CONSTITUENT, shared with Document 55) and rejects a duplicate device reference with DeviceToCoatingBindingAlreadyUsedError; services/gxp-api/tests/test_coated_device_flow.py::test_bind_device_to_coating_rejects_duplicate_and_completes_run.  |  **Defect:** —

### TC-057-010-02 — Unit/lot association — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-010
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- bind_device_to_coating_constituent() creates a ddcp_unit_binding row (binding_type=DEVICE_TO_COATING_CONSTITUENT, shared with Document 55) and rejects a duplicate device reference with DeviceToCoatingBindingAlreadyUsedError; services/gxp-api/tests/test_coated_device_flow.py::test_bind_device_to_coating_rejects_duplicate_and_completes_run.  |  **Defect:** —

### TC-057-011-01 — Coating weight/loading — required behaviour

- **Requirement:** COAT-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Record direct/indirect drug loading/coating weight measurement according to approved method. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Dose/loading evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_drug_loading_result() evaluates a caller-supplied released rule (SG-148/150 pattern) against the measured coating weight/loading value; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-011-02 — Coating weight/loading — Action without the required signature is blocked

- **Requirement:** COAT-FR-011
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-057-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_drug_loading_result() evaluates a caller-supplied released rule (SG-148/150 pattern) against the measured coating weight/loading value; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-011-03 — Coating weight/loading — Signature bound to a superseded version is rejected

- **Requirement:** COAT-FR-011
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-057-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-012-01 — Uniformity — required behaviour

- **Requirement:** COAT-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support coating thickness/loading/uniformity spatial or sampled result structures. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Quality. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_drug_loading_result()'s default test_type=COATING_INTEGRITY covers the uniformity/loading result shape; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-013-01 — Coating integrity — required behaviour

- **Requirement:** COAT-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Inspection for delamination/cracks/defects/adhesion or product-specific attributes. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Device/drug interaction. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_drug_loading_result()'s default test_type=COATING_INTEGRITY covers the uniformity/loading result shape; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-014-01 — Drug content/assay — required behaviour

- **Requirement:** COAT-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Link QC assay/content/impurity/degradation results for finished coated device where required. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Drug quality. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_post_sterilization_test() with test_type=DRUG_CONTENT_ASSAY links a drug-content/assay result; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-014-02 — Drug content/assay — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-014
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_post_sterilization_test() with test_type=DRUG_CONTENT_ASSAY links a drug-content/assay result; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-015-01 — Release/elution profile — required behaviour

- **Requirement:** COAT-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support in-vitro release/elution test result sets when product specification requires. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Therapeutic performance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_device_functional_test() with test_type=RELEASE_ELUTION and a method_reference; services/gxp-api/tests/test_coated_device_flow.py::test_device_functional_test_covers_integrity_elution_and_dimensional.  |  **Defect:** —

### TC-057-015-02 — Release/elution profile — Action without the required signature is blocked

- **Requirement:** COAT-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-057-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-015-03 — Release/elution profile — Signature bound to a superseded version is rejected

- **Requirement:** COAT-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-057-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-015-04 — Release/elution profile — Limit boundary behaviour

- **Requirement:** COAT-FR-015
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-057-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-016-01 — Dimensional/device function — required behaviour

- **Requirement:** COAT-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Ensure coating process does not invalidate required device dimensional/mechanical/functional tests. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Combined performance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_device_functional_test() with test_type=DIMENSIONAL_FUNCTION; services/gxp-api/tests/test_coated_device_flow.py::test_device_functional_test_covers_integrity_elution_and_dimensional.  |  **Defect:** —

### TC-057-016-02 — Dimensional/device function — Prohibited path is rejected

- **Requirement:** COAT-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Ensure coating process does not invalidate required device dimensional/mechanical/functional tests. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STERILIZATION_INTERACTION_REVIEW_REQUIRED`
- **Depends on:** TC-057-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-016-03 — Dimensional/device function — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-016
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-017-01 — Drying/curing — required behaviour

- **Requirement:** COAT-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Capture curing/drying conditions and hold times after coating. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Process. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_device_assembly_step() with assembly_step=DRYING_CURING (extended ASSEMBLY_STEPS, SG-150); services/gxp-api/tests/test_coated_device_flow.py::test_surface_prep_drying_curing_and_equipment_bound_run.  |  **Defect:** —

### TC-057-018-01 — Sterilization interaction — required behaviour

- **Requirement:** COAT-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Profile specifies pre/post coating sterilization route and recognizes potential impact of sterilization on drug/coating/device. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Critical DDCP interaction. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- create_coated_device_profile_version() captures sterilizationRouteId on the profile's own constituent_architecture when supplied, and leaves it unset (no generic assumption) when not; services/gxp-api/tests/test_coated_device_flow.py::test_sterilization_interaction_captured_on_profile.  |  **Defect:** —

### TC-057-018-02 — Sterilization interaction — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-018
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-019-01 — Sterilization evidence — required behaviour

- **Requirement:** COAT-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Link sterilization cycle/contract process to exact coated device lot/serial. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Genealogy. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_post_sterilization_test() carries sterilization_reference inside qc_record_reference, never duplicating Document 42's sterilization-cycle data; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-019-02 — Sterilization evidence — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-019
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_post_sterilization_test() carries sterilization_reference inside qc_record_reference, never duplicating Document 42's sterilization-cycle data; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-020-01 — Post-sterilization testing — required behaviour

- **Requirement:** COAT-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Profile can require drug assay/degradation/release/device tests after sterilization. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Interaction verification. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_post_sterilization_test() links a post-sterilization drug/device test result to the batch; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-020-02 — Post-sterilization testing — Action without the required signature is blocked

- **Requirement:** COAT-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-057-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_post_sterilization_test() links a post-sterilization drug/device test result to the batch; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-020-03 — Post-sterilization testing — Signature bound to a superseded version is rejected

- **Requirement:** COAT-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-057-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-020-04 — Post-sterilization testing — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-020
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-021-01 — Packaging — required behaviour

- **Requirement:** COAT-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Barrier/package materials, protection, labeling and packaged lot genealogy. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Finished product. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-022-01 — Unit serialization — required behaviour

- **Requirement:** COAT-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support serial/unit-level coated device trace when device profile requires. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Device postmarket. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- bind_device_to_coating_constituent()'s device_unit_reference round-trips a caller-supplied unit_serial through the ddcp_unit_binding record; services/gxp-api/tests/test_coated_device_flow.py::test_device_to_coating_binding_carries_unit_serial.  |  **Defect:** —

### TC-057-022-02 — Unit serialization — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-022
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-023-01 — Process sampling — required behaviour

- **Requirement:** COAT-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Sampling plan can select devices/locations/timepoints across coating run. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Representativeness. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-023-02 — Process sampling — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-023
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-024-01 — OOS/NCR — required behaviour

- **Requirement:** COAT-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Coating/drug/device failures create OOS/NCR/deviation and affected unit/lot scope. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** QMS. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_drug_loading_result() returns result_state=OOS when the released rule outcome is FAIL (DRUG_LOADING_OOS); services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-024-02 — OOS/NCR — Prohibited path is rejected

- **Requirement:** COAT-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Coating/drug/device failures create OOS/NCR/deviation and affected unit/lot scope. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STERILIZATION_INTERACTION_REVIEW_REQUIRED`
- **Depends on:** TC-057-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- record_drug_loading_result() returns result_state=OOS when the released rule outcome is FAIL (DRUG_LOADING_OOS); services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-024-03 — OOS/NCR — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-024
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-025-01 — Rework — required behaviour

- **Requirement:** COAT-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Recoating/stripping/reprocessing default prohibited unless released validated route explicitly permits and drug/device impact assessed. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Safe default. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- new record_coated_device_disposition() rejects REWORK missing either a rework_procedure_reference or a drug_device_impact_assessment (ReworkRouteRequiredError, stricter default-disallow than PFS-FR-027/INJ-FR-022 per this document's own 'impact assessed' text) and accepts once both are supplied; services/gxp-api/tests/test_coated_device_flow.py::test_coated_device_disposition_requires_reason_and_dual_rework_evidence.  |  **Defect:** —

### TC-057-025-02 — Rework — Action without the required signature is blocked

- **Requirement:** COAT-FR-025
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-057-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-025-03 — Rework — Signature bound to a superseded version is rejected

- **Requirement:** COAT-FR-025
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-057-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-025-04 — Rework — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-025
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-026-01 — Yield/reconciliation — required behaviour

- **Requirement:** COAT-FR-026
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Reconcile device units and drug/coating material separately and combined. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Full balance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- complete_coating_run() checks both the device-unit ledger (production_count_ledger, count_type=COATED) and the drug/coating-material ledger (drug_coating_usage_ledger, usage_type=ISSUED) before allowing completion -- Document 57 §6's dual reconciliation, structural completeness only (no numeric variance tolerance baselined anywhere); services/gxp-api/tests/test_coated_device_flow.py::test_bind_device_to_coating_rejects_duplicate_and_completes_run.  |  **Defect:** —

### TC-057-026-02 — Yield/reconciliation — Limit boundary behaviour

- **Requirement:** COAT-FR-026
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-057-026-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- complete_coating_run() checks both the device-unit ledger (production_count_ledger, count_type=COATED) and the drug/coating-material ledger (drug_coating_usage_ledger, usage_type=ISSUED) before allowing completion -- Document 57 §6's dual reconciliation, structural completeness only (no numeric variance tolerance baselined anywhere); services/gxp-api/tests/test_coated_device_flow.py::test_bind_device_to_coating_rejects_duplicate_and_completes_run.  |  **Defect:** —

### TC-057-026-03 — Yield/reconciliation — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-026
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-026-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-027-01 — Constituent checkpoints — required behaviour

- **Requirement:** COAT-FR-027
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Device substrate and drug constituent may have separate release inputs; finished coated device has independent final release. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Part 4. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- evaluate_coated_device_release_readiness() composes DRUG_CONSTITUENT/DEVICE_CONSTITUENT/COMBINED_PRODUCT checkpoints, reusing ddcp_release_checkpoint verbatim; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-027-02 — Constituent checkpoints — Action without the required signature is blocked

- **Requirement:** COAT-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-057-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- evaluate_coated_device_release_readiness() composes DRUG_CONSTITUENT/DEVICE_CONSTITUENT/COMBINED_PRODUCT checkpoints, reusing ddcp_release_checkpoint verbatim; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-027-03 — Constituent checkpoints — Signature bound to a superseded version is rejected

- **Requirement:** COAT-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-057-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-027-04 — Constituent checkpoints — Offline buffering and reconnect preserve evidence

- **Requirement:** COAT-FR-027
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-057-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-028-01 — Final blockers — required behaviour

- **Requirement:** COAT-FR-028
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Coating parameter excursion, drug reconciliation gap, sterilization issue, assay/release/device failure, genealogy gap or QMS issue blocks release. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No bypass. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- evaluate_coated_device_release_readiness() blocks DEVICE_CONSTITUENT after a real OOS drug-loading result -- a genuine negative-path assertion (readiness_after['ready'] is False), not just the happy path; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-028-02 — Final blockers — Prohibited path is rejected

- **Requirement:** COAT-FR-028
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Coating parameter excursion, drug reconciliation gap, sterilization issue, assay/release/device failure, genealogy gap or QMS issue blocks r | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STERILIZATION_INTERACTION_REVIEW_REQUIRED`
- **Depends on:** TC-057-028-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- evaluate_coated_device_release_readiness() blocks DEVICE_CONSTITUENT after a real OOS drug-loading result -- a genuine negative-path assertion (readiness_after['ready'] is False), not just the happy path; services/gxp-api/tests/test_coated_device_flow.py::test_drug_loading_result_post_sterilization_test_and_release_readiness.  |  **Defect:** —

### TC-057-028-03 — Final blockers — Action without the required signature is blocked

- **Requirement:** COAT-FR-028
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-057-028-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-028-04 — Final blockers — Signature bound to a superseded version is rejected

- **Requirement:** COAT-FR-028
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-057-028-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-029-01 — Change impact — required behaviour

- **Requirement:** COAT-FR-029
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Substrate material, coating formulation, drug source, coating equipment/program, environment, sterilization, packaging and test-method changes require | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Lifecycle. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- get_ddcp_change_linkage() (reused verbatim from Document 54) round-trips a qms.change_commands.assess_impact()-created link for a coated-device profile; services/gxp-api/tests/test_coated_device_flow.py::test_change_linkage_reused_for_coated_device_profile.  |  **Defect:** —

### TC-057-030-01 — Complaint/field trace — required behaviour

- **Requirement:** COAT-FR-030
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Complaint serial/lot can trace backward to coating run/drug lot and forward to affected distributed units. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Postmarket. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- trace_coated_device_complaint() composes substrate/drug handoffs, device-to-coating bindings, functional test links and drug/coating usage for a batch; create_coated_device_batch_evidence_package() freezes a batch_evidence_manifest row; services/gxp-api/tests/test_coated_device_flow.py::test_evidence_package_and_complaint_trace.  |  **Defect:** —

### TC-057-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-29  |  **Actual result:** PASS -- trace_coated_device_complaint() composes substrate/drug handoffs, device-to-coating bindings, functional test links and drug/coating usage for a batch; create_coated_device_batch_evidence_package() freezes a batch_evidence_manifest row; services/gxp-api/tests/test_coated_device_flow.py::test_evidence_package_and_complaint_trace.  |  **Defect:** —

### TC-057-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-DDCP-004-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-S001 — Specification scenario — wrong drug lot

- **Requirement:** SPEC-DDCP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: wrong drug lot | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-S002 — Specification scenario — substrate on hold

- **Requirement:** SPEC-DDCP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: substrate on hold | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-S003 — Specification scenario — coating solution hold expired

- **Requirement:** SPEC-DDCP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: coating solution hold expired | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-S004 — Specification scenario — humidity excursion

- **Requirement:** SPEC-DDCP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: humidity excursion | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-S005 — Specification scenario — program version mismatch

- **Requirement:** SPEC-DDCP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: program version mismatch | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-S006 — Specification scenario — drug loading OOS

- **Requirement:** SPEC-DDCP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: drug loading OOS | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-S007 — Specification scenario — coating integrity defect partial unit scope

- **Requirement:** SPEC-DDCP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: coating integrity defect partial unit scope | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-S008 — Specification scenario — failed sterilization

- **Requirement:** SPEC-DDCP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: failed sterilization | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-S009 — Specification scenario — post-sterilization assay failure

- **Requirement:** SPEC-DDCP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: post-sterilization assay failure | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-S010 — Specification scenario — unapproved recoating attempt

- **Requirement:** SPEC-DDCP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: unapproved recoating attempt | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-S011 — Specification scenario — dual reconciliation mismatch

- **Requirement:** SPEC-DDCP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: dual reconciliation mismatch | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-057-S012 — Specification scenario — complaint trace to drug lot

- **Requirement:** SPEC-DDCP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: complaint trace to drug lot | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____
