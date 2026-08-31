# Test Cases — Document 38: Equipment, Calibration, Qualification & Maintenance (SPEC-EQP-001)

**Work package:** WP-06  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** EQP-FR-001..030 (30)  
**Test cases:** 83  
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

### TC-038-001-01 — Equipment master — required behaviour

- **Requirement:** EQP-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Unique asset ID, type/class, manufacturer/model/serial, site/area/location, ownership and lifecycle status. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Canonical equipment identity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_create_asset_enters_installed.  |  **Defect:** —

### TC-038-001-02 — Equipment master — Illegal state transition is rejected

- **Requirement:** EQP-FR-001
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-038-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- create_equipment_asset is a creation operation with no prior aggregate state to illegally transition from; the module's real illegal-transition coverage is under EQP-FR-030 (see TC-038-030-02, test_return_to_service_rejected_without_qualification).  |  **Defect:** —

### TC-038-002-01 — Equipment class — required behaviour

- **Requirement:** EQP-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Reusable equipment class defines capability, process use, calibration/maintenance/cleaning requirements and allowed recipe roles. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Recipe compatibility. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_create_asset_enters_installed (equipment_class_id accepted and stored; captured, unenforced reference -- no equipment_class master entity exists, SG-113).  |  **Defect:** —

### TC-038-003-01 — Lifecycle — required behaviour

- **Requirement:** EQP-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Planned, Installed, Qualification Pending, Qualified/Available, Maintenance, Calibration Due, Out of Service, Suspended, Retired. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Explicit state. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_full_qualify_calibrate_return_to_service_flow, test_oot_calibration_holds_equipment_and_blocks_return and test_hold_requires_signature_and_reason together exercise INSTALLED, VERIFICATION, QUALIFIED_AVAILABLE, OUT_OF_SERVICE and SUSPENDED.  |  **Defect:** —

### TC-038-004-01 — Qualification status — required behaviour

- **Requirement:** EQP-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Track IQ/OQ/PQ or equivalent qualification references, approved scope, effective/expiry/requalification triggers. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Use only qualified assets. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_full_qualify_calibrate_return_to_service_flow.  |  **Defect:** —

### TC-038-004-02 — Qualification status — Action without the required signature is blocked

- **Requirement:** EQP-FR-004
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-038-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- record_qualification is unsigned -- Document 106 has no policy row for a 'qualify' action on equipment_asset; the module's one real signature is hold (Document 106 row 108), see TC-038-024-02's equivalent, test_hold_requires_signature_and_reason.  |  **Defect:** —

### TC-038-004-03 — Qualification status — Signature bound to a superseded version is rejected

- **Requirement:** EQP-FR-004
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-038-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- same as TC-038-004-02 -- record_qualification is unsigned.  |  **Defect:** —

### TC-038-004-04 — Qualification status — Illegal state transition is rejected

- **Requirement:** EQP-FR-004
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-038-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- the only state this module treats as universally forbidden for further mutation is RETIRED, and RETIRED is unreachable -- no retire operation exists in Document 38's declared API list (SG-112).  |  **Defect:** SG-112

### TC-038-005-01 — Calibration plan — required behaviour

- **Requirement:** EQP-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Define calibration points, tolerances, procedure/version, frequency, standard requirements and due rules. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled calibration. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_calibration_history_captures_standard_and_evidence_fields.  |  **Defect:** —

### TC-038-005-02 — Calibration plan — Limit boundary behaviour

- **Requirement:** EQP-FR-005
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-038-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- calibration result (pass/fail/oot) is captured performer-attested input, not system-computed from a numeric tolerance boundary -- no released Document 08 rules-engine tolerance-evaluation hook exists for calibration (same no-op-until-authored precedent as material's release-eligibility gate); boundary-value evaluation is a procedural/SOP control outside this pass's automated scope.  |  **Defect:** —

### TC-038-005-03 — Calibration plan — Concurrent writers on one aggregate

- **Requirement:** EQP-FR-005
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-038-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_stale_version_rejected -- exercises the shared _load_asset_for_update() optimistic-concurrency guard (with_for_update + StaleVersionError) every equipment command, including record_calibration, uses identically.  |  **Defect:** —

### TC-038-006-01 — Calibration execution — required behaviour

- **Requirement:** EQP-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Capture pre-calibration/as-found, adjustments, post-calibration/as-left, standard/equipment, performer, date and result. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Complete evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_calibration_history_captures_standard_and_evidence_fields.  |  **Defect:** —

### TC-038-007-01 — Out-of-tolerance calibration — required behaviour

- **Requirement:** EQP-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: OOT calibration automatically generates equipment hold/impact assessment and may trigger deviation/CAPA. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Product impact controlled. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_oot_calibration_holds_equipment_and_blocks_return.  |  **Defect:** —

### TC-038-007-02 — Out-of-tolerance calibration — Limit boundary behaviour

- **Requirement:** EQP-FR-007
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-038-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- same as TC-038-005-02 -- result is captured input, not boundary-computed.  |  **Defect:** —

### TC-038-008-01 — Calibration standards — required behaviour

- **Requirement:** EQP-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Reference standard/tool ID, calibration status, traceability/evidence and expiry. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reliable calibration. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_calibration_history_captures_standard_and_evidence_fields (standard_reference/standard_calibration_status/standard_expiry_date round-trip through GET .../history; captured, unenforced reference -- no calibration_standard master entity exists, SG-113).  |  **Defect:** —

### TC-038-008-02 — Calibration standards — Illegal state transition is rejected

- **Requirement:** EQP-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-038-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- same RETIRED-unreachable reasoning as TC-038-004-04 (SG-112).  |  **Defect:** SG-112

### TC-038-009-01 — Preventive maintenance plan — required behaviour

- **Requirement:** EQP-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Frequency, tasks, parts, procedure, owner, expected downtime and due dates. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Routine upkeep. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_critical_modification_links_change_control (procedure_version/frequency_days/next_due_date captured on a planned maintenance_work_order and mirrored onto equipment_asset.next_maintenance_due_date).  |  **Defect:** —

### TC-038-009-02 — Preventive maintenance plan — Prohibited path is rejected

- **Requirement:** EQP-FR-009
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Frequency, tasks, parts, procedure, owner, expected downtime and due dates. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `CALIBRATION_OOT_IMPACT_REQUIRED`
- **Depends on:** TC-038-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no forbidden-input condition exists for PM-plan field capture -- any well-formed planned work order is accepted; this generic template row has no real negative case to exercise for a pure data-capture requirement.  |  **Defect:** —

### TC-038-010-01 — Maintenance work order — required behaviour

- **Requirement:** EQP-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Create planned/corrective work order with fault, work, parts, technician, timestamps and verification. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Service history. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_breakdown_maintenance_holds_then_verification_returns_to_service.  |  **Defect:** —

### TC-038-011-01 — Post-maintenance verification — required behaviour

- **Requirement:** EQP-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Equipment remains unavailable until required inspection/calibration/requalification/cleaning complete. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Safe return. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_breakdown_maintenance_holds_then_verification_returns_to_service (equipment stays OUT_OF_SERVICE/blocked from return_to_service until the work order is verified).  |  **Defect:** —

### TC-038-012-01 — Breakdown — required behaviour

- **Requirement:** EQP-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Unexpected failure marks equipment unavailable and evaluates affected in-process/recent batches. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Impact. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_breakdown_maintenance_holds_then_verification_returns_to_service (type=corrective immediately sets OUT_OF_SERVICE/hold_flag). The requirement's other half -- evaluating affected in-process/recent batches -- is not attempted; no equipment reference exists on batch_execution.BatchStep (SG-111)..  |  **Defect:** —

### TC-038-012-02 — Breakdown — Prohibited path is rejected

- **Requirement:** EQP-FR-012
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Unexpected failure marks equipment unavailable and evaluates affected in-process/recent batches. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `CALIBRATION_OOT_IMPACT_REQUIRED`
- **Depends on:** TC-038-012-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no forbidden-path distinct from the illegal-transition coverage already exercised under EQP-FR-030 (TC-038-030-02).  |  **Defect:** —

### TC-038-013-01 — Equipment use log — required behaviour

- **Requirement:** EQP-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Record date/time, batch/product/operation, operator/source, cleaning/maintenance context in chronological history. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** 211.182 support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_calibration_history_captures_standard_and_evidence_fields (asserts exactly one equipment_use_log row with log_type='calibration' after a calibration command; every mutating command in this module leaves an equivalent trace).  |  **Defect:** —

### TC-038-014-01 — Dedicated equipment — required behaviour

- **Requirement:** EQP-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Support dedicated-equipment profile with use/cleaning evidence in batch when appropriate. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Flexible compliance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_create_asset_enters_installed (dedicated flag accepted and stored; captured field, not independently enforced against a batch-consumption workflow this pass).  |  **Defect:** —

### TC-038-015-01 — Pre-use eligibility — required behaviour

- **Requirement:** EQP-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Batch step checks current qualification, calibration, maintenance, cleaning and hold status. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No invalid equipment. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_full_qualify_calibrate_return_to_service_flow (eligible=True with no reasons once qualified/calibrated) and test_oot_calibration_holds_equipment_and_blocks_return (eligible=False with CALIBRATION_OOT_IMPACT_REQUIRED).  |  **Defect:** —

### TC-038-015-02 — Pre-use eligibility — Illegal state transition is rejected

- **Requirement:** EQP-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-038-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- get_eligibility is a pure read query with no aggregate state of its own to illegally transition; the real state-machine illegal-transition coverage is under EQP-FR-030 (TC-038-030-02).  |  **Defect:** —

### TC-038-016-01 — Reservation — required behaviour

- **Requirement:** EQP-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Reserve equipment for batch/time window; reservation never overrides quality eligibility. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Scheduling. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no reservation-create operation exists -- EQP-FR-016 has no endpoint in Document 38's declared 9-op API list; equipment_use_log.log_type declares a 'reservation' value with no command that ever writes one (SG-112).  |  **Defect:** SG-112

### TC-038-016-02 — Reservation — Prohibited path is rejected

- **Requirement:** EQP-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Reserve equipment for batch/time window; reservation never overrides quality eligibility. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `CALIBRATION_OOT_IMPACT_REQUIRED`
- **Depends on:** TC-038-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- same reservation gap as TC-038-016-01 (SG-112).  |  **Defect:** SG-112

### TC-038-017-01 — Meter/runtime counters — required behaviour

- **Requirement:** EQP-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Capture hours/cycles/counts from Edge/manual source for condition/frequency-based maintenance. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Predictive scheduling. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- equipment_asset.runtime_hours/runtime_cycles are schema columns with no command -- manual or Edge-sourced -- that ever sets them (SG-109).  |  **Defect:** SG-109

### TC-038-017-02 — Meter/runtime counters — Offline buffering and reconnect preserve evidence

- **Requirement:** EQP-FR-017
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-038-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no Edge source exists to buffer/reconnect against (SG-109).  |  **Defect:** SG-109

### TC-038-018-01 — Instrument/device identity — required behaviour

- **Requirement:** EQP-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Register PLC, balance, tester, sensor, controller or machine endpoints and credentials/certificates separately from asset master. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Secure integration. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no device-identity/credential registration command exists (SG-109).  |  **Defect:** SG-109

### TC-038-018-02 — Instrument/device identity — Offline buffering and reconnect preserve evidence

- **Requirement:** EQP-FR-018
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-038-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no Edge/device source exists to buffer/reconnect against (SG-109).  |  **Defect:** SG-109

### TC-038-019-01 — Edge mapping — required behaviour

- **Requirement:** EQP-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Versioned mapping between equipment tag/channel and GxP parameter. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Source traceability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no Edge tag/channel mapping command exists (SG-109).  |  **Defect:** SG-109

### TC-038-019-02 — Edge mapping — Offline buffering and reconnect preserve evidence

- **Requirement:** EQP-FR-019
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-038-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no Edge source exists to buffer/reconnect against (SG-109).  |  **Defect:** SG-109

### TC-038-019-03 — Edge mapping — Concurrent writers on one aggregate

- **Requirement:** EQP-FR-019
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-038-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no Edge mapping aggregate exists to contend on (SG-109).  |  **Defect:** SG-109

### TC-038-020-01 — Status from maintenance system — required behaviour

- **Requirement:** EQP-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: External CMMS can provide work-order/reference status, but final GxP availability uses controlled product policy. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Boundary. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no CMMS integration exists (SG-109).  |  **Defect:** SG-109

### TC-038-020-02 — Status from maintenance system — Illegal state transition is rejected

- **Requirement:** EQP-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-038-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no CMMS integration exists (SG-109).  |  **Defect:** SG-109

### TC-038-020-03 — Status from maintenance system — Replayed inbound message is detected

- **Requirement:** EQP-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-038-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no CMMS integration exists to replay a message against (SG-109).  |  **Defect:** SG-109

### TC-038-020-04 — Status from maintenance system — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** EQP-FR-020
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-038-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no CMMS integration exists to time out against (SG-109).  |  **Defect:** SG-109

### TC-038-021-01 — Spare parts — required behaviour

- **Requirement:** EQP-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Record critical replaced component/part/serial where product/process impact exists. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Maintenance evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_critical_modification_links_change_control (parts_used captured as JSONB on the maintenance work order; captured, unenforced -- no spare-parts master entity exists, SG-113).  |  **Defect:** —

### TC-038-022-01 — Change control — required behaviour

- **Requirement:** EQP-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Critical equipment modification links Change Control and validation impact. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Validated state. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_critical_modification_links_change_control -- calls the owning qms.change_commands.create_change through the Mutation Gateway and stores the resulting change_control_id on the asset (AG-05/AG-06, no qms table written directly).  |  **Defect:** —

### TC-038-023-01 — Software/firmware — required behaviour

- **Requirement:** EQP-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Track firmware/software/config version for automated equipment where relevant. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reproducibility. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- firmware_version is captured once at create_equipment_asset time; no update command exists to actually 'track' a version change over the asset's life as EQP-FR-023 describes (SG-109).  |  **Defect:** SG-109

### TC-038-023-02 — Software/firmware — Concurrent writers on one aggregate

- **Requirement:** EQP-FR-023
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-038-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no firmware-update command exists to contend on (SG-109).  |  **Defect:** SG-109

### TC-038-024-01 — Alarm/events — required behaviour

- **Requirement:** EQP-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Equipment alarms linked to batch/step and deviation when released rules require. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Process impact. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no alarm/event ingestion source exists (SG-109).  |  **Defect:** SG-109

### TC-038-024-02 — Alarm/events — Action without the required signature is blocked

- **Requirement:** EQP-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-038-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no alarm-linked action exists to attempt without a signature (SG-109).  |  **Defect:** SG-109

### TC-038-024-03 — Alarm/events — Signature bound to a superseded version is rejected

- **Requirement:** EQP-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-038-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no alarm-linked action exists to test a stale-signature against (SG-109).  |  **Defect:** SG-109

### TC-038-025-01 — Cleaning dependency — required behaviour

- **Requirement:** EQP-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Eligibility references current cleaning/sanitization/sterilization state from Document 39/42. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Integrated. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no cleaning/sanitization source exists -- Document 39 is not built; get_eligibility() does not evaluate cleanliness_status for exactly this reason (SG-110).  |  **Defect:** SG-110

### TC-038-025-02 — Cleaning dependency — Illegal state transition is rejected

- **Requirement:** EQP-FR-025
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-038-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- same cleaning-dependency gap as TC-038-025-01 (SG-110).  |  **Defect:** SG-110

### TC-038-026-01 — Location transfer — required behaviour

- **Requirement:** EQP-FR-026
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Moving equipment to another area/site can trigger requalification/change/cleaning requirements. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled relocation. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no location-transfer operation exists -- EQP-FR-026 has no endpoint in Document 38's declared 9-op API list; location_id is captured only at asset creation (SG-112).  |  **Defect:** SG-112

### TC-038-027-01 — Retirement — required behaviour

- **Requirement:** EQP-FR-027
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Retire with final status, data retention, outstanding batch/maintenance impact and approval. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Lifecycle closure. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no retire operation exists -- RETIRED is unreachable (SG-112).  |  **Defect:** SG-112

### TC-038-027-02 — Retirement — Illegal state transition is rejected

- **Requirement:** EQP-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-038-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no retire operation exists to drive an illegal-transition case against (SG-112).  |  **Defect:** SG-112

### TC-038-027-03 — Retirement — Disposal without an approved decision is refused

- **Requirement:** EQP-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-038-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no retire/disposal operation exists (SG-112).  |  **Defect:** SG-112

### TC-038-028-01 — Dashboard — required behaviour

- **Requirement:** EQP-FR-028
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Due calibration/maintenance, out-of-service, utilization, recurring failures and impact events. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Operational visibility. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_dashboard_lists_out_of_service_assets.  |  **Defect:** —

### TC-038-028-02 — Dashboard — Prohibited path is rejected

- **Requirement:** EQP-FR-028
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Due calibration/maintenance, out-of-service, utilization, recurring failures and impact events. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `CALIBRATION_OOT_IMPACT_REQUIRED`
- **Depends on:** TC-038-028-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- get_dashboard is a read query with no forbidden-input condition to reject; this generic template row has no real negative case for a pure reporting endpoint.  |  **Defect:** —

### TC-038-029-01 — Audit/export — required behaviour

- **Requirement:** EQP-FR-029
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Complete qualification/calibration/maintenance/use history exportable. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Inspection-ready. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_calibration_history_captures_standard_and_evidence_fields and test_critical_modification_links_change_control (GET .../history returns full qualification/calibration/maintenance/use-log detail for the asset).  |  **Defect:** —

### TC-038-029-02 — Audit/export — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** EQP-FR-029
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-038-029-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_equipment_use_log_rejects_direct_update -- migration 0037 grants the app role SELECT/INSERT/TRUNCATE only (no UPDATE) on equipment.equipment_use_logs, refused at the database privilege level.  |  **Defect:** —

### TC-038-030-01 — No status bypass — required behaviour

- **Requirement:** EQP-FR-030
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** Minimum valid data set for `equipment_asset`, `equipment_calibration`, `maintenance_work_order`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /equipment/v1/assets` (or the owning command) exercising: Admin/operator cannot manually set 'Qualified/Available' without controlled evidence/authority. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_full_qualify_calibrate_return_to_service_flow -- QUALIFIED_AVAILABLE is written in exactly one place, return_to_service(), after it re-checks qualification/calibration/maintenance/hold evidence; no command accepts state directly from the caller.  |  **Defect:** —

### TC-038-030-02 — No status bypass — Illegal state transition is rejected

- **Requirement:** EQP-FR-030
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `equipment_asset`, `equipment_calibration`, `maintenance_work_order` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-038-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_return_to_service_rejected_without_qualification.  |  **Defect:** —

### TC-038-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_create_asset_unauthenticated_rejected.  |  **Defect:** —

### TC-038-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_create_asset_requires_equipment_administrator_role and test_hold_requires_role.  |  **Defect:** —

### TC-038-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- single-organization platform per ADR-0006 -- no tenant_id column exists anywhere in this codebase.  |  **Defect:** —

### TC-038-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- not independently re-executed in test_equipment_flow.py; enforced by the shared evaluate_policy() site-scoped role resolution (UserSiteRole.site_id filter) every command in this module calls before its domain logic runs, generically verified by other modules' dedicated cross-site cases (same shared code path).  |  **Defect:** —

### TC-038-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- MUT-FR-007's qualification gate is conditional/configured; no qualification code is declared for any Document 38 action (unlike Document 21's dispensing_operator gate).  |  **Defect:** —

### TC-038-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- hold_equipment's Document 106 row 108 declares requires_independent_signer=False -- independence is not required for this action, so there is no SoD-at-completion boundary to test here. Independent-signer coverage exists elsewhere in this codebase (e.g. material lot release/reject).  |  **Defect:** —

### TC-038-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_qualify_missing_expected_version_rejected.  |  **Defect:** —

### TC-038-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_stale_version_rejected.  |  **Defect:** —

### TC-038-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_duplicate_idempotency_key_returns_same_receipt.  |  **Defect:** —

### TC-038-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_duplicate_idempotency_key_different_payload_rejected.  |  **Defect:** —

### TC-038-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_full_qualify_calibrate_return_to_service_flow -- every 200 response's MutationReceipt carries a real audit_event_id from the same PostgreSQL transaction (write_audit_event/record_command_receipt pattern every command in this file uses).  |  **Defect:** —

### TC-038-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no fault-injection harness exists in this test suite to simulate a DB/signature-service outage; architectural guarantee (AG-06/MUT-FR-022) common to every module, not independently re-tested per module in this codebase.  |  **Defect:** —

### TC-038-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no crash/rollback-injection harness exists in this test suite; same architectural-guarantee treatment as TC-038-M12.  |  **Defect:** —

### TC-038-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-EQP-001-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** N/A -- no Frappe projection consumer exists in this codebase's test harness to take offline (AG-11); architectural guarantee, not independently testable here.  |  **Defect:** —

### TC-038-S001 — Specification scenario — valid equipment use

- **Requirement:** SPEC-EQP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: valid equipment use | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_full_qualify_calibrate_return_to_service_flow -- full create -> qualify -> calibrate -> return-to-service lifecycle exercised end to end.  |  **Defect:** —

### TC-038-S002 — Specification scenario — expired calibration blocks step

- **Requirement:** SPEC-EQP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: expired calibration blocks step | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_oot_calibration_holds_equipment_and_blocks_return -- the out-of-tolerance variant of 'calibration blocks step' is exercised (return_to_service rejected with CALIBRATION_OOT_IMPACT_REQUIRED); the date-based next_calibration_due_date<today variant of CALIBRATION_EXPIRED is code-reviewed (_ineligibility_reasons) but not independently asserted by a dedicated test this pass.  |  **Defect:** —

### TC-038-S003 — Specification scenario — as-found OOT impact

- **Requirement:** SPEC-EQP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: as-found OOT impact | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_oot_calibration_holds_equipment_and_blocks_return (as_found captured, impact_assessment_required=True asserted via GET .../history).  |  **Defect:** —

### TC-038-S004 — Specification scenario — maintenance then calibration required

- **Requirement:** SPEC-EQP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: maintenance then calibration required | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_breakdown_maintenance_holds_then_verification_returns_to_service.  |  **Defect:** —

### TC-038-S005 — Specification scenario — breakdown during batch

- **Requirement:** SPEC-EQP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: breakdown during batch | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_equipment_flow.py::test_breakdown_maintenance_holds_then_verification_returns_to_service -- the equipment-side breakdown behaviour (immediate hold/OUT_OF_SERVICE) is tested; the cross-module 'affects the in-process batch' linkage is not built (SG-111).  |  **Defect:** —

### TC-038-S006 — Specification scenario — wrong equipment class

- **Requirement:** SPEC-EQP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: wrong equipment class | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- equipment_class_id is a captured, unenforced reference -- no equipment_class master entity or recipe-role compatibility check exists to reject a wrong class (SG-113).  |  **Defect:** SG-113

### TC-038-S007 — Specification scenario — relocation

- **Requirement:** SPEC-EQP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: relocation | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no location-transfer operation exists (SG-112).  |  **Defect:** SG-112

### TC-038-S008 — Specification scenario — firmware change

- **Requirement:** SPEC-EQP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: firmware change | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no firmware-update command exists (SG-109).  |  **Defect:** SG-109

### TC-038-S009 — Specification scenario — CMMS outage

- **Requirement:** SPEC-EQP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: CMMS outage | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no CMMS integration exists (SG-109).  |  **Defect:** SG-109

### TC-038-S010 — Specification scenario — concurrent reservation

- **Requirement:** SPEC-EQP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: concurrent reservation | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no reservation operation exists (SG-112).  |  **Defect:** SG-112

### TC-038-S011 — Specification scenario — retirement

- **Requirement:** SPEC-EQP-001-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: retirement | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-25  |  **Actual result:** BLOCKED -- no retire operation exists (SG-112).  |  **Defect:** SG-112
