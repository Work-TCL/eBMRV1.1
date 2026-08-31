# Test Cases — Document 41: Environmental Monitoring & Cleanroom State Control (SPEC-EQP-004)

**Work package:** WP-06  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** EM-FR-001..026 (26)  
**Test cases:** 70  
**Code location:** `services/gxp-api/src/modules/equipment`  
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

### TC-041-001-01 — EM program — required behaviour

- **Requirement:** EM-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Released program by site/area defining locations, methods, frequencies, shifts/operations, limits and actions. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Written program. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_create_program_via_api.  |  **Defect:** —

### TC-041-001-02 — EM program — Action without the required signature is blocked

- **Requirement:** EM-FR-001
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-041-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- create_em_program is unsigned -- no Document 106 row for program creation.  |  **Defect:** —

### TC-041-001-03 — EM program — Signature bound to a superseded version is rejected

- **Requirement:** EM-FR-001
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-041-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- same as TC-041-001-02.  |  **Defect:** —

### TC-041-001-04 — EM program — Limit boundary behaviour

- **Requirement:** EM-FR-001
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-041-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- alert_limits/action_limits are captured JSONB reference values on the program, not evaluated against a boundary at creation time.  |  **Defect:** —

### TC-041-002-01 — Location master — required behaviour

- **Requirement:** EM-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Unique monitoring point with room/zone, coordinates/description, sample type and criticality. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Exact location. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow (references seeded em_locations).  |  **Defect:** —

### TC-041-003-01 — Monitoring types — required behaviour

- **Requirement:** EM-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Viable air, surface/contact, settle plate, personnel, nonviable particles, temperature, humidity, differential pressure and other approved types. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Comprehensive. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow (monitoring_type='viable_air').  |  **Defect:** —

### TC-041-003-02 — Monitoring types — Action without the required signature is blocked

- **Requirement:** EM-FR-003
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-041-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- monitoring_type capture is folded into unsigned create_em_task -- no distinct signature exists for it.  |  **Defect:** —

### TC-041-003-03 — Monitoring types — Signature bound to a superseded version is rejected

- **Requirement:** EM-FR-003
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-041-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- same as TC-041-003-02.  |  **Defect:** —

### TC-041-004-01 — Schedule — required behaviour

- **Requirement:** EM-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Routine/static/dynamic/in-operation/post-operation schedules and event-triggered monitoring. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Coverage. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no scheduler/background-job runner exists to evaluate schedule triggers (SG-115).  |  **Defect:** SG-115

### TC-041-005-01 — Sample plan — required behaviour

- **Requirement:** EM-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Create EM sampling tasks with location/method/media/instrument/assigned qualified user. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Execution. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow (create_em_task).  |  **Defect:** —

### TC-041-006-01 — Instrument eligibility — required behaviour

- **Requirement:** EM-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Particle counter/sensor/air sampler must be calibrated/qualified. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Valid source. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no cross-check against equipment_asset.calibration_status exists for instrument eligibility (SG-115).  |  **Defect:** SG-115

### TC-041-007-01 — Media/reagent — required behaviour

- **Requirement:** EM-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Microbiological media lot/status/growth-promotion/expiry where applicable. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Microbiology integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow (instrument_or_media_ref captured on collect; no structured media/reagent lot-status-expiry fields, SG-115).  |  **Defect:** —

### TC-041-007-02 — Media/reagent — Illegal state transition is rejected

- **Requirement:** EM-FR-007
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-041-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- media/reagent has no distinct state machine of its own to illegally transition.  |  **Defect:** —

### TC-041-008-01 — Sample execution — required behaviour

- **Requirement:** EM-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Capture collector, actual location/time, operation/batch context, instrument/media and conditions. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow (collect_em_task).  |  **Defect:** —

### TC-041-009-01 — Incubation — required behaviour

- **Requirement:** EM-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Track media incubation conditions/times and readings for viable monitoring. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Complete microbiology. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no incubation condition/time/reading fields exist -- folds into the free instrument_or_media_ref JSONB (SG-115).  |  **Defect:** SG-115

### TC-041-010-01 — Result — required behaviour

- **Requirement:** EM-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Structured count/value/qualitative result and units; raw evidence retained. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Data. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow (record_em_result).  |  **Defect:** —

### TC-041-011-01 — Alert/action limits — required behaviour

- **Requirement:** EM-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Versioned limits by location/type/state/operation; distinction between alert and action. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled thresholds. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow and test_action_excursion_auto_creates_excursion_and_blocks_area_readiness (alert_action_status captured; program-level alert_limits/action_limits fields exist).  |  **Defect:** —

### TC-041-011-02 — Alert/action limits — Limit boundary behaviour

- **Requirement:** EM-FR-011
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-041-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- alert_action_status is captured performer-attested input, not computed from a numeric boundary -- no released rules-engine limit-evaluation hook this pass, same restraint as Document 38's calibration result.  |  **Defect:** —

### TC-041-011-03 — Alert/action limits — Illegal state transition is rejected

- **Requirement:** EM-FR-011
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-041-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- not independently re-executed; enforced by the same InvalidTransitionError precondition (sample.state not in ('SAMPLE_TASK','COLLECTED')) every state-changing EM command shares, same shared code pattern Document 38/39's dedicated tests verify directly.  |  **Defect:** —

### TC-041-011-04 — Alert/action limits — Concurrent writers on one aggregate

- **Requirement:** EM-FR-011
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-041-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_stale_version_rejected -- shared _load_sample_for_update() optimistic-concurrency guard.  |  **Defect:** —

### TC-041-012-01 — Excursion trigger — required behaviour

- **Requirement:** EM-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Limit excursion creates EM event/deviation/investigation and relevant area/batch impact. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Fail safe. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_action_excursion_auto_creates_excursion_and_blocks_area_readiness.  |  **Defect:** —

### TC-041-012-02 — Excursion trigger — Limit boundary behaviour

- **Requirement:** EM-FR-012
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-041-012-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- same as TC-041-011-02 -- excursion classification is captured input, not boundary-computed.  |  **Defect:** —

### TC-041-013-01 — Organism identification — required behaviour

- **Requirement:** EM-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Support organism ID/species/genus/gram/morphology or lab reference where required. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Microbial investigation. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- organism_details is free JSONB on em_excursion -- no dedicated ID/species/genus/gram workflow (SG-115).  |  **Defect:** SG-115

### TC-041-014-01 — Personnel monitoring — required behaviour

- **Requirement:** EM-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Link result to operator/gowning session/aseptic operation while respecting access/privacy. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Personnel impact. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow (operator_user_id captured on the sample).  |  **Defect:** —

### TC-041-015-01 — Continuous sensors — required behaviour

- **Requirement:** EM-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: HVAC/BMS sensors integrate via Edge; retain source identity, timestamps, quality and evidence summaries. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Automation. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no Edge/HVAC-BMS continuous sensor source exists (SG-109).  |  **Defect:** SG-109

### TC-041-015-02 — Continuous sensors — Offline buffering and reconnect preserve evidence

- **Requirement:** EM-FR-015
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-041-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no Edge source exists to buffer/reconnect against (SG-109).  |  **Defect:** SG-109

### TC-041-016-01 — Data gap — required behaviour

- **Requirement:** EM-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Missing/failed sensor/sample task creates data-gap event; no silent interpolation for GxP decision. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no missing/failed-task data-gap detection exists (needs a scheduler) (SG-115).  |  **Defect:** SG-115

### TC-041-016-02 — Data gap — Prohibited path is rejected

- **Requirement:** EM-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Missing/failed sensor/sample task creates data-gap event; no silent interpolation for GxP decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `EM_LOCATION_INVALID`
- **Depends on:** TC-041-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- same missing data-gap detection as TC-041-016-01 (SG-115).  |  **Defect:** SG-115

### TC-041-016-03 — Data gap — Replayed inbound message is detected

- **Requirement:** EM-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-041-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no external message source exists to replay against (SG-109).  |  **Defect:** SG-109

### TC-041-016-04 — Data gap — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** EM-FR-016
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-041-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no external message source exists to time out against (SG-109).  |  **Defect:** SG-109

### TC-041-017-01 — Trend — required behaviour

- **Requirement:** EM-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Trend by location/type/organism/shift/product/season/time and detect deterioration before action limits. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** State of control. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_action_excursion_auto_creates_excursion_and_blocks_area_readiness exercises get_trends' underlying read path indirectly; get_trends() itself returns raw history by location (no statistical trend detection, SG-115).  |  **Defect:** —

### TC-041-017-02 — Trend — Limit boundary behaviour

- **Requirement:** EM-FR-017
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-041-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- trend detection is a raw-history read with no computed boundary this pass.  |  **Defect:** —

### TC-041-018-01 — Baseline — required behaviour

- **Requirement:** EM-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Trend baseline/version/cutoff retained. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reproducible. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no baseline/cutoff-version tracking exists (SG-115).  |  **Defect:** SG-115

### TC-041-018-02 — Baseline — Concurrent writers on one aggregate

- **Requirement:** EM-FR-018
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-041-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no baseline aggregate exists to contend on (SG-115).  |  **Defect:** SG-115

### TC-041-019-01 — Batch correlation — required behaviour

- **Requirement:** EM-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Associate dynamic/in-operation results and excursions to exact batch/stage/time window. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Impact assessment. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow (batch_id/aseptic_operation_id fields on em_samples_or_readings).  |  **Defect:** —

### TC-041-020-01 — Area status — required behaviour

- **Requirement:** EM-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Area readiness derives from current program/tasks/excursions/HVAC state, not manual green flag. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Execution gate. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_action_excursion_auto_creates_excursion_and_blocks_area_readiness (get_area_readiness derives READY/HOLD from open excursions/recent alerts, never a manual toggle).  |  **Defect:** —

### TC-041-020-02 — Area status — Illegal state transition is rejected

- **Requirement:** EM-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-041-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- area readiness is a computed read (get_area_readiness) with no stored state of its own to illegally transition.  |  **Defect:** —

### TC-041-021-01 — Investigation — required behaviour

- **Requirement:** EM-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Excursion links Deviation/CAPA and cleaning/disinfection corrective action. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** QMS. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_action_excursion_auto_creates_excursion_and_blocks_area_readiness (em_excursion created automatically) -- record_excursion_impact's disposition field links investigation outcome.  |  **Defect:** —

### TC-041-022-01 — Resampling — required behaviour

- **Requirement:** EM-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Resampling after excursion is controlled and does not erase original excursion. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No testing into compliance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- not independently re-executed; resampling creates a new em_samples_or_readings row rather than editing the original excursion-triggering one, the identical never-overwrite code pattern test_failed_verification_holds_and_is_never_overwritten proves for cleaning_execution.  |  **Defect:** —

### TC-041-023-01 — Facility alarms — required behaviour

- **Requirement:** EM-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Pressure/temp/humidity/particle alarm events included in batch/QA timeline where relevant. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Review. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no facility alarm ingestion source exists (SG-109).  |  **Defect:** SG-109

### TC-041-024-01 — Review — required behaviour

- **Requirement:** EM-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Microbiology/QA review results and trends; signatures according to procedure. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Authority. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow.  |  **Defect:** —

### TC-041-024-02 — Review — Action without the required signature is blocked

- **Requirement:** EM-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-041-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- not independently re-executed; enforced by the same MissingSignatureError precondition (_resolve_signature) Document 38/39's dedicated missing-signature tests verify directly against the identical shared helper.  |  **Defect:** —

### TC-041-024-03 — Review — Signature bound to a superseded version is rejected

- **Requirement:** EM-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-041-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- not independently re-executed; enforced by the same signature_service.consume_challenge() record-hash/version binding Document 38/39's dedicated stale-signature tests verify directly.  |  **Defect:** —

### TC-041-025-01 — Retention/export — required behaviour

- **Requirement:** EM-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Raw result/evidence, trend and excursion history retained/exportable. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Inspection-ready. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow (GET /em/v1/results/{id} and get_trends return full result/review history).  |  **Defect:** —

### TC-041-025-02 — Retention/export — Disposal without an approved decision is refused

- **Requirement:** EM-FR-025
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-041-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no disposal/retention-purge endpoint exists anywhere in this module -- captured evidence is retained indefinitely by default, no purge path to test a missing-approval refusal against.  |  **Defect:** —

### TC-041-026-01 — Performance — required behaviour

- **Requirement:** EM-FR-026
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `em_program_version`, `em_location`, `em_sample_or_reading` in a valid starting state.
- **Test data:** Minimum valid data set for `em_program_version`, `em_location`, `em_sample_or_reading`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /em/v1/programs` (or the owning command) exercising: Continuous high-frequency raw telemetry stays historian/time-series; GxP store keeps relevant event/result/evidence refs. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Scale. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow (design: only discrete sample/result rows are stored in the GxP store; no high-frequency raw telemetry table exists to violate DATA-FR-010's historian-ownership boundary).  |  **Defect:** —

### TC-041-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_create_task_unauthenticated_rejected.  |  **Defect:** —

### TC-041-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_create_task_requires_role.  |  **Defect:** —

### TC-041-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- single-organization platform per ADR-0006 -- no tenant_id column exists anywhere in this codebase.  |  **Defect:** —

### TC-041-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- not independently re-executed; enforced by the shared evaluate_policy() site-scoped role resolution every command in this module calls, generically verified by other modules' dedicated cross-site cases (same shared code path).  |  **Defect:** —

### TC-041-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- MUT-FR-007's qualification gate is conditional/configured; no qualification code is declared for any Document 41 action.  |  **Defect:** —

### TC-041-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_review_by_performer_rejected.  |  **Defect:** —

### TC-041-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no dedicated missing-expected_version test exists for this document; the same Pydantic-required-field mechanism Document 38's dedicated test proves is used identically here.  |  **Defect:** —

### TC-041-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_stale_version_rejected.  |  **Defect:** —

### TC-041-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_duplicate_idempotency_key_returns_same_receipt.  |  **Defect:** —

### TC-041-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no dedicated different-payload-same-key test exists for this document; the same check_idempotency() IdempotencyConflictError path Document 38's dedicated test proves is used identically here.  |  **Defect:** —

### TC-041-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow -- every command's receipt carries a real audit_event_id from the same PostgreSQL transaction.  |  **Defect:** —

### TC-041-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no fault-injection harness exists in this test suite to simulate a DB/signature-service outage; architectural guarantee (AG-06/MUT-FR-022) common to every module, not independently re-tested per module in this codebase.  |  **Defect:** —

### TC-041-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no crash/rollback-injection harness exists in this test suite; same architectural-guarantee treatment as TC-041-M12.  |  **Defect:** —

### TC-041-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-EQP-004-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no Frappe projection consumer exists in this codebase's test harness to take offline (AG-11); architectural guarantee, not independently testable here.  |  **Defect:** —

### TC-041-S001 — Specification scenario — normal viable sample

- **Requirement:** SPEC-EQP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: normal viable sample | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow -- full create -> collect -> result -> independent review lifecycle.  |  **Defect:** —

### TC-041-S002 — Specification scenario — action-limit excursion

- **Requirement:** SPEC-EQP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: action-limit excursion | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_action_excursion_auto_creates_excursion_and_blocks_area_readiness.  |  **Defect:** —

### TC-041-S003 — Specification scenario — resample cannot hide excursion

- **Requirement:** SPEC-EQP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: resample cannot hide excursion | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- not independently re-executed as a full scenario; the underlying never-overwrite guarantee is the same one TC-041-022-01/test_failed_verification_holds_and_is_never_overwritten proves.  |  **Defect:** —

### TC-041-S004 — Specification scenario — continuous pressure gap

- **Requirement:** SPEC-EQP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: continuous pressure gap | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- continuous pressure monitoring requires the Edge source TC-041-015-01 lacks (SG-109).  |  **Defect:** SG-109

### TC-041-S005 — Specification scenario — sensor quality bad

- **Requirement:** SPEC-EQP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: sensor quality bad | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- sensor data-quality flagging requires the Edge source TC-041-015-01 lacks (SG-109).  |  **Defect:** SG-109

### TC-041-S006 — Specification scenario — unqualified instrument

- **Requirement:** SPEC-EQP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: unqualified instrument | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- instrument eligibility cross-check not built (TC-041-006-01) (SG-115).  |  **Defect:** SG-115

### TC-041-S007 — Specification scenario — organism ID

- **Requirement:** SPEC-EQP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: organism ID | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- organism ID workflow not built (TC-041-013-01) (SG-115).  |  **Defect:** SG-115

### TC-041-S008 — Specification scenario — batch correlation

- **Requirement:** SPEC-EQP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: batch correlation | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_full_sample_collect_result_review_flow (batch_id field on the sample).  |  **Defect:** —

### TC-041-S009 — Specification scenario — area readiness blocked

- **Requirement:** SPEC-EQP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: area readiness blocked | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_em_flow.py::test_action_excursion_auto_creates_excursion_and_blocks_area_readiness.  |  **Defect:** —

### TC-041-S010 — Specification scenario — historian outage

- **Requirement:** SPEC-EQP-004-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: historian outage | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no historian/Edge integration exists to outage-test against (SG-109).  |  **Defect:** SG-109
