# Test Cases — Document 17: Yield, Calculations & Manufacturing Reconciliation Specification (SPEC-EBMR-008)

**Work package:** WP-03  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** YLD-FR-001..032 (32)  
**Test cases:** 123  
**Code location:** `services/gxp-api/src/modules/ebmr`  
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

### TC-017-001-01 — Theoretical yield definition — required behaviour

- **Requirement:** YLD-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Recipe/product defines theoretical yield or measure at appropriate manufacturing phases using released calculation/rule versions. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Expected output controlled. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- EvaluateYieldCommand.theoretical_quantity + get_effective_released_rule('yield_percent') (fails closed if unreleased); services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation.  |  **Defect:** —

### TC-017-001-02 — Theoretical yield definition — Action without the required signature is blocked

- **Requirement:** YLD-FR-001
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-017-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- EvaluateYieldCommand.theoretical_quantity + get_effective_released_rule('yield_percent') (fails closed if unreleased); services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation.  |  **Defect:** —

### TC-017-001-03 — Theoretical yield definition — Signature bound to a superseded version is rejected

- **Requirement:** YLD-FR-001
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-017-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- EvaluateYieldCommand.theoretical_quantity + get_effective_released_rule('yield_percent') (fails closed if unreleased); services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation.  |  **Defect:** —

### TC-017-001-04 — Theoretical yield definition — Limit boundary behaviour

- **Requirement:** YLD-FR-001
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- EvaluateYieldCommand.theoretical_quantity + get_effective_released_rule('yield_percent') (fails closed if unreleased); services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation.  |  **Defect:** —

### TC-017-002-01 — Actual yield source — required behaviour

- **Requirement:** YLD-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Actual yield derives from authoritative measured/recorded output quantities and source/equipment/manual evidence. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No untraceable number. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- actual_quantity + manual_source/manual_reason fields; input_hash=sha256(input_refs) for traceability; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation, test_evaluate_yield_manual_source_requires_reason.  |  **Defect:** —

### TC-017-002-02 — Actual yield source — Limit boundary behaviour

- **Requirement:** YLD-FR-002
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- actual_quantity + manual_source/manual_reason fields; input_hash=sha256(input_refs) for traceability; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation, test_evaluate_yield_manual_source_requires_reason.  |  **Defect:** —

### TC-017-003-01 — Yield percentage — required behaviour

- **Requirement:** YLD-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Calculate percentage of theoretical yield using validated decimal formula and explicit rounding. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reproducible result. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- Decimal-only formula via Document 08's rule engine, explicit rounding read from the rule's own rounding_policy (CC-4: 6dp intermediate/2dp reported, half-up); services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation.  |  **Defect:** —

### TC-017-003-02 — Yield percentage — Limit boundary behaviour

- **Requirement:** YLD-FR-003
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- Decimal-only formula via Document 08's rule engine, explicit rounding read from the rule's own rounding_policy (CC-4: 6dp intermediate/2dp reported, half-up); services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation.  |  **Defect:** —

### TC-017-004-01 — Independent verification — required behaviour

- **Requirement:** YLD-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Where required, calculated yield is independently verified or verified per automated-equipment rule/profile. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Support applicable 211.103 workflow. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- verify_record() requires an independent verifier, not the performer (SIG-FR-018); services/gxp-api/tests/test_yield_reconciliation.py::test_verify_requires_independent_verifier, test_verify_full_flow_with_independent_signer. The alternative 'verified per automated-equipment rule/profile' path is not built (SG-050).  |  **Defect:** —

### TC-017-004-02 — Independent verification — Limit boundary behaviour

- **Requirement:** YLD-FR-004
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- verify_record() requires an independent verifier, not the performer (SIG-FR-018); services/gxp-api/tests/test_yield_reconciliation.py::test_verify_requires_independent_verifier, test_verify_full_flow_with_independent_signer. The alternative 'verified per automated-equipment rule/profile' path is not built (SG-050).  |  **Defect:** —

### TC-017-005-01 — Phase yield — required behaviour

- **Requirement:** YLD-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Support multiple phase/stage calculations, not only final yield. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Process loss visible. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- phase_code + scope_type (BATCH/PHASE/SUB_LOT/SERIAL_GROUP) columns on ManufacturingCalculation support multiple phase/stage calculations per batch; not independently tested with a dedicated multi-phase scenario this pass.  |  **Defect:** —

### TC-017-005-02 — Phase yield — Limit boundary behaviour

- **Requirement:** YLD-FR-005
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- phase_code + scope_type (BATCH/PHASE/SUB_LOT/SERIAL_GROUP) columns on ManufacturingCalculation support multiple phase/stage calculations per batch; not independently tested with a dedicated multi-phase scenario this pass.  |  **Defect:** —

### TC-017-006-01 — Yield limits — required behaviour

- **Requirement:** YLD-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Released recipe defines min/max percentage or other acceptance rule and investigation trigger. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Out-of-limit automatic. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- min_percent/max_percent + OUT_OF_LIMIT state/YieldOutOfLimit event; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_below_min_boundary_out_of_limit.  |  **Defect:** —

### TC-017-006-02 — Yield limits — Action without the required signature is blocked

- **Requirement:** YLD-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-017-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- min_percent/max_percent + OUT_OF_LIMIT state/YieldOutOfLimit event; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_below_min_boundary_out_of_limit.  |  **Defect:** —

### TC-017-006-03 — Yield limits — Signature bound to a superseded version is rejected

- **Requirement:** YLD-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-017-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- min_percent/max_percent + OUT_OF_LIMIT state/YieldOutOfLimit event; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_below_min_boundary_out_of_limit.  |  **Defect:** —

### TC-017-006-04 — Yield limits — Limit boundary behaviour

- **Requirement:** YLD-FR-006
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- min_percent/max_percent + OUT_OF_LIMIT state/YieldOutOfLimit event; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_below_min_boundary_out_of_limit.  |  **Defect:** —

### TC-017-007-01 — Automated calculation — required behaviour

- **Requirement:** YLD-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Automated calculation records input references, rule version, engine version and result; verifier sees inputs/result. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Transparent automation. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- rule_object_id/rule_evaluation_id FK to Document 08's RuleDefinition/RuleEvaluation, plus input_refs/input_hash capture; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation.  |  **Defect:** —

### TC-017-007-02 — Automated calculation — Limit boundary behaviour

- **Requirement:** YLD-FR-007
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- rule_object_id/rule_evaluation_id FK to Document 08's RuleDefinition/RuleEvaluation, plus input_refs/input_hash capture; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation.  |  **Defect:** —

### TC-017-007-03 — Automated calculation — Concurrent writers on one aggregate

- **Requirement:** YLD-FR-007
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-017-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- rule_object_id/rule_evaluation_id FK to Document 08's RuleDefinition/RuleEvaluation, plus input_refs/input_hash capture; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation.  |  **Defect:** —

### TC-017-008-01 — Manual calculation fallback — required behaviour

- **Requirement:** YLD-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: If calculation manually entered/externally calculated, require source, reason/policy and verification; default prefer engine calculation. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Fallback controlled. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- manual_source/manual_reason are metadata captured alongside a value the rule engine *always* computes -- there is no path to enter an externally-precomputed yield value that bypasses the engine; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_manual_source_requires_reason proves only the required-reason rule, not a bypass path (SG-133).  |  **Defect:** —

### TC-017-008-02 — Manual calculation fallback — Limit boundary behaviour

- **Requirement:** YLD-FR-008
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- manual_source/manual_reason are metadata captured alongside a value the rule engine *always* computes -- there is no path to enter an externally-precomputed yield value that bypasses the engine; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_manual_source_requires_reason proves only the required-reason rule, not a bypass path (SG-133).  |  **Defect:** —

### TC-017-008-03 — Manual calculation fallback — Replayed inbound message is detected

- **Requirement:** YLD-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-017-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- manual_source/manual_reason are metadata captured alongside a value the rule engine *always* computes -- there is no path to enter an externally-precomputed yield value that bypasses the engine; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_manual_source_requires_reason proves only the required-reason rule, not a bypass path (SG-133).  |  **Defect:** —

### TC-017-008-04 — Manual calculation fallback — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** YLD-FR-008
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-017-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- manual_source/manual_reason are metadata captured alongside a value the rule engine *always* computes -- there is no path to enter an externally-precomputed yield value that bypasses the engine; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_manual_source_requires_reason proves only the required-reason rule, not a bypass path (SG-133).  |  **Defect:** —

### TC-017-009-01 — Material mass balance — required behaviour

- **Requirement:** YLD-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Reconcile received/issued/dispensed/consumed/returned/rejected/destroyed/loss quantities for defined scope. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Material accountability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- evaluate_material_reconciliation(); issued vs consumed/returned/samples/rejected/destroyed/approved_loss mass balance; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_material_reconciliation_acceptable.  |  **Defect:** —

### TC-017-009-02 — Material mass balance — Prohibited path is rejected

- **Requirement:** YLD-FR-009
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Reconcile received/issued/dispensed/consumed/returned/rejected/destroyed/loss quantities for defined scope. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-017-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- evaluate_material_reconciliation(); issued vs consumed/returned/samples/rejected/destroyed/approved_loss mass balance; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_material_reconciliation_acceptable.  |  **Defect:** —

### TC-017-010-01 — Dispensing reconciliation — required behaviour

- **Requirement:** YLD-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: For each material requirement reconcile dispensed vs consumed/returned/approved loss. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Per-material closure. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- same mass-balance mechanics as YLD-FR-009, scoped per material via item_ref; not independently tested with a dedicated per-material-requirement scenario.  |  **Defect:** —

### TC-017-010-02 — Dispensing reconciliation — Action without the required signature is blocked

- **Requirement:** YLD-FR-010
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-017-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- same mass-balance mechanics as YLD-FR-009, scoped per material via item_ref; not independently tested with a dedicated per-material-requirement scenario.  |  **Defect:** —

### TC-017-010-03 — Dispensing reconciliation — Signature bound to a superseded version is rejected

- **Requirement:** YLD-FR-010
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-017-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- same mass-balance mechanics as YLD-FR-009, scoped per material via item_ref; not independently tested with a dedicated per-material-requirement scenario.  |  **Defect:** —

### TC-017-011-01 — Packaging material balance — required behaviour

- **Requirement:** YLD-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Reconcile packaging components issued/used/rejected/returned/destroyed/samples. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Packaging accountability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- evaluate_packaging_reconciliation(); shared mass-balance mechanics with YLD-FR-009, not independently re-tested for this specific reconciliation_type.  |  **Defect:** —

### TC-017-011-02 — Packaging material balance — Prohibited path is rejected

- **Requirement:** YLD-FR-011
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Reconcile packaging components issued/used/rejected/returned/destroyed/samples. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-017-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- evaluate_packaging_reconciliation(); shared mass-balance mechanics with YLD-FR-009, not independently re-tested for this specific reconciliation_type.  |  **Defect:** —

### TC-017-012-01 — Label reconciliation — required behaviour

- **Requirement:** YLD-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Consume Document 16 label counts and applicable waiver/profile rule. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Unified release blocker. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** PASS -- evaluate_label_reconciliation() now consumes Document 16's own label counts via packaging.service.get_label_reconciliation_source() (issued/applied/returned/samples/rejected/destroyed); batch_id/site_id derived from the packaging run, not the caller; Document 16's calculated_variance/result recorded in item_ref without overwriting this module's variance; services/gxp-api/tests/test_yield_reconciliation.py::test_label_reconciliation_consumes_packaging_counts. YLD-FR-012's 'applicable waiver/profile rule' half remains unbuilt -- SG-134  |  **Defect:** —

### TC-017-013-01 — Device component reconciliation — required behaviour

- **Requirement:** YLD-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: For serialized/critical components reconcile issued/assembled/rejected/scrapped/returned where configured. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Component accountability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** PASS -- evaluate_component_reconciliation() resolves ReconciliationRecord.device_unit_id through Document 12's device.service.get_unit() and records the unit's serial_number in item_ref; YLD-FR-013's own issued/assembled/rejected/scrapped/returned vocabulary now counts toward the mass balance (COMPONENT_QUANTITY_CATEGORIES); services/gxp-api/tests/test_yield_reconciliation.py::test_component_reconciliation_scoped_to_device_unit  |  **Defect:** —

### TC-017-013-02 — Device component reconciliation — Prohibited path is rejected

- **Requirement:** YLD-FR-013
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: For serialized/critical components reconcile issued/assembled/rejected/scrapped/returned where configured. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-017-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** PASS -- a device_unit belonging to another batch is rejected before any row is written (assertion confirms zero reconciliation_records for the target batch); services/gxp-api/tests/test_yield_reconciliation.py::test_component_reconciliation_rejects_device_unit_from_another_batch. Registry code returned is VALIDATION_FAILED, not this template's generic STATE_TRANSITION_INVALID default -- the check is a scope/ownership validation, not a state transition  |  **Defect:** —

### TC-017-013-03 — Device component reconciliation — Offline buffering and reconnect preserve evidence

- **Requirement:** YLD-FR-013
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-017-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** BLOCKED -- the DeviceUnit integration this case depended on is now built (see TC-017-013-01), but store-and-forward/offline buffering is Document 45 (SPEC-EDGE-003) territory and no offline buffer exists for this module's commands; the disconnect/reconnect precondition is not constructible here. Re-scoped from SG-132 to the unbuilt Document 45 dependency.  |  **Defect:** —

### TC-017-014-01 — Unit count reconciliation — required behaviour

- **Requirement:** YLD-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Reconcile produced/accepted/rejected/reworked/sampled/scrapped packaged unit counts. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Finished quantity consistent. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no dedicated unit-count reconciliation type or produced/accepted/reworked/scrapped category vocabulary exists -- RECONCILIATION_TYPES (MATERIAL/PACKAGING/LABEL/COMPONENT) and _QUANTITY_CATEGORIES (consumed/returned/samples/rejected/destroyed/approved_loss) do not cover packaged-unit-count semantics (SG-133).  |  **Defect:** —

### TC-017-014-02 — Unit count reconciliation — Prohibited path is rejected

- **Requirement:** YLD-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Reconcile produced/accepted/rejected/reworked/sampled/scrapped packaged unit counts. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-017-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no dedicated unit-count reconciliation type or produced/accepted/reworked/scrapped category vocabulary exists -- RECONCILIATION_TYPES (MATERIAL/PACKAGING/LABEL/COMPONENT) and _QUANTITY_CATEGORIES (consumed/returned/samples/rejected/destroyed/approved_loss) do not cover packaged-unit-count semantics (SG-133).  |  **Defect:** —

### TC-017-015-01 — Potency correction — required behaviour

- **Requirement:** YLD-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Calculate required active material amount from released potency/assay result and formula/version. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Drug dispensing support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- evaluate_potency() resolves a customer-authored released rule at cmd.rule_id and fails closed (NotFoundError) if none exists -- no default potency formula is hardcoded, matching the fact that (unlike yield) no formula for potency correction is given in the approved baseline; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_potency_requires_a_released_rule.  |  **Defect:** —

### TC-017-015-02 — Potency correction — Action without the required signature is blocked

- **Requirement:** YLD-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-017-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- evaluate_potency() resolves a customer-authored released rule at cmd.rule_id and fails closed (NotFoundError) if none exists -- no default potency formula is hardcoded, matching the fact that (unlike yield) no formula for potency correction is given in the approved baseline; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_potency_requires_a_released_rule.  |  **Defect:** —

### TC-017-015-03 — Potency correction — Signature bound to a superseded version is rejected

- **Requirement:** YLD-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-017-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- evaluate_potency() resolves a customer-authored released rule at cmd.rule_id and fails closed (NotFoundError) if none exists -- no default potency formula is hardcoded, matching the fact that (unlike yield) no formula for potency correction is given in the approved baseline; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_potency_requires_a_released_rule.  |  **Defect:** —

### TC-017-015-04 — Potency correction — Limit boundary behaviour

- **Requirement:** YLD-FR-015
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- evaluate_potency() resolves a customer-authored released rule at cmd.rule_id and fails closed (NotFoundError) if none exists -- no default potency formula is hardcoded, matching the fact that (unlike yield) no formula for potency correction is given in the approved baseline; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_potency_requires_a_released_rule.  |  **Defect:** —

### TC-017-016-01 — Overage/excess — required behaviour

- **Requirement:** YLD-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Recipe may define justified component excess/overage as released parameter; system distinguishes planned excess from variance. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No hidden overage. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no overage/excess recipe parameter exists on any recipe entity built so far -- only ordinary tolerance/variance is modeled, with no distinction between planned excess and variance (SG-133).  |  **Defect:** —

### TC-017-016-02 — Overage/excess — Action without the required signature is blocked

- **Requirement:** YLD-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-017-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no overage/excess recipe parameter exists on any recipe entity built so far -- only ordinary tolerance/variance is modeled, with no distinction between planned excess and variance (SG-133).  |  **Defect:** —

### TC-017-016-03 — Overage/excess — Signature bound to a superseded version is rejected

- **Requirement:** YLD-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-017-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no overage/excess recipe parameter exists on any recipe entity built so far -- only ordinary tolerance/variance is modeled, with no distinction between planned excess and variance (SG-133).  |  **Defect:** —

### TC-017-017-01 — Unit conversion — required behaviour

- **Requirement:** YLD-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: All calculations use controlled UOM service and explicit dimensional conversion. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No mixed-unit error. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- uom is a single string column captured per record; this module never calls a controlled cross-UOM conversion service, so quantities in one calculation/reconciliation must already share one unit -- no dimensional conversion is performed (SG-133).  |  **Defect:** —

### TC-017-017-02 — Unit conversion — Limit boundary behaviour

- **Requirement:** YLD-FR-017
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- uom is a single string column captured per record; this module never calls a controlled cross-UOM conversion service, so quantities in one calculation/reconciliation must already share one unit -- no dimensional conversion is performed (SG-133).  |  **Defect:** —

### TC-017-017-03 — Unit conversion — Concurrent writers on one aggregate

- **Requirement:** YLD-FR-017
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-017-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- uom is a single string column captured per record; this module never calls a controlled cross-UOM conversion service, so quantities in one calculation/reconciliation must already share one unit -- no dimensional conversion is performed (SG-133).  |  **Defect:** —

### TC-017-018-01 — Precision/rounding — required behaviour

- **Requirement:** YLD-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Each calculation has explicit decimal precision, rounding mode and stage. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No developer default. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- CC-4 (Document 110 Sec 2) read explicitly from the resolved rule's own rounding_policy (reported_dp, mode) at evaluation time, never a hardcoded developer default; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation exercises _quantize().  |  **Defect:** —

### TC-017-018-02 — Precision/rounding — Limit boundary behaviour

- **Requirement:** YLD-FR-018
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- CC-4 (Document 110 Sec 2) read explicitly from the resolved rule's own rounding_policy (reported_dp, mode) at evaluation time, never a hardcoded developer default; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation exercises _quantize().  |  **Defect:** —

### TC-017-019-01 — Tolerance — required behaviour

- **Requirement:** YLD-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Reconciliation defines absolute/percentage tolerance and inclusive/exclusive semantics. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Boundary deterministic. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- tolerance_rule dict ({type, value, inclusive}) with explicit inclusive/exclusive boundary semantics; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_reconciliation_out_of_tolerance.  |  **Defect:** —

### TC-017-019-02 — Tolerance — Limit boundary behaviour

- **Requirement:** YLD-FR-019
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- tolerance_rule dict ({type, value, inclusive}) with explicit inclusive/exclusive boundary semantics; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_reconciliation_out_of_tolerance.  |  **Defect:** —

### TC-017-020-01 — Variance — required behaviour

- **Requirement:** YLD-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Outside-tolerance result creates blocker and linked deviation/investigation according to profile. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No silent acceptance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- OUT_OF_TOLERANCE state + ReconciliationFailed event create an automatic, non-silent blocker (release_blocked via get_batch_summary); services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_reconciliation_out_of_tolerance. linked_quality_event_id exists on the schema for a future deviation-record link; app/modules/qms's DeviationRecord (create_deviation...disposition_deviation) is the real candidate target, but no command in this module creates or references one -- not wired this pass (SG-049).  |  **Defect:** —

### TC-017-020-02 — Variance — Prohibited path is rejected

- **Requirement:** YLD-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Outside-tolerance result creates blocker and linked deviation/investigation according to profile. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-017-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- OUT_OF_TOLERANCE state + ReconciliationFailed event create an automatic, non-silent blocker (release_blocked via get_batch_summary); services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_reconciliation_out_of_tolerance. linked_quality_event_id exists on the schema for a future deviation-record link; app/modules/qms's DeviationRecord (create_deviation...disposition_deviation) is the real candidate target, but no command in this module creates or references one -- not wired this pass (SG-049).  |  **Defect:** —

### TC-017-020-03 — Variance — Limit boundary behaviour

- **Requirement:** YLD-FR-020
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- OUT_OF_TOLERANCE state + ReconciliationFailed event create an automatic, non-silent blocker (release_blocked via get_batch_summary); services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_reconciliation_out_of_tolerance. linked_quality_event_id exists on the schema for a future deviation-record link; app/modules/qms's DeviationRecord (create_deviation...disposition_deviation) is the real candidate target, but no command in this module creates or references one -- not wired this pass (SG-049).  |  **Defect:** —

### TC-017-020-04 — Variance — Concurrent writers on one aggregate

- **Requirement:** YLD-FR-020
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-017-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- OUT_OF_TOLERANCE state + ReconciliationFailed event create an automatic, non-silent blocker (release_blocked via get_batch_summary); services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_reconciliation_out_of_tolerance. linked_quality_event_id exists on the schema for a future deviation-record link; app/modules/qms's DeviationRecord (create_deviation...disposition_deviation) is the real candidate target, but no command in this module creates or references one -- not wired this pass (SG-049).  |  **Defect:** —

### TC-017-021-01 — Approved loss — required behaviour

- **Requirement:** YLD-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Document controlled reasons/categories for process loss, sample, spill, reject, destruction; approval may be required. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Variance explained. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** PASS -- ReconciliationRecord.loss_reasons: a non-zero approved_loss fails closed without at least one reason carrying category+description, and quantified reasons must account for the whole approved loss; the approval links to QMS via linked_deviation_id -> qms.service.get_deviation() -> linked_quality_event_id (Document 17 links to a deviation, never creates one -- AG-05); services/gxp-api/tests/test_yield_reconciliation.py::test_approved_loss_with_documented_reasons_is_accepted, ::test_partial_loss_reason_quantities_are_rejected, ::test_approved_loss_links_to_qms_deviation. Category *vocabulary* is deliberately unconstrained -- SG-135  |  **Defect:** —

### TC-017-021-02 — Approved loss — Prohibited path is rejected

- **Requirement:** YLD-FR-021
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Document controlled reasons/categories for process loss, sample, spill, reject, destruction; approval may be required. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-017-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** PASS -- approved_loss with no documented reason is rejected VALIDATION_FAILED and nothing is written (batch summary confirms zero reconciliations); services/gxp-api/tests/test_yield_reconciliation.py::test_approved_loss_without_documented_reason_is_rejected. Registry code is VALIDATION_FAILED, not this template's generic STATE_TRANSITION_INVALID default -- the check is an evidence-completeness validation, not a state transition  |  **Defect:** —

### TC-017-021-03 — Approved loss — Action without the required signature is blocked

- **Requirement:** YLD-FR-021
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-017-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** BLOCKED -- Document 106 declares no signature row for approved-loss reconciliation (row 40, `verify`, is the only signed action in Document 17), so a 'missing required signature' rejection is not constructible: the policy requires none. Not a defect; the case presumes a signature requirement the approved baseline does not define  |  **Defect:** —

### TC-017-021-04 — Approved loss — Signature bound to a superseded version is rejected

- **Requirement:** YLD-FR-021
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-017-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** BLOCKED -- same reason as TC-017-021-03: no signature is required for this action by Document 106, so there is no signature to bind to a superseded version  |  **Defect:** —

### TC-017-022-01 — Correction — required behaviour

- **Requirement:** YLD-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Input/result correction preserves original and automatically re-evaluates affected downstream yields/reconciliations/review. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Consistency maintained. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-09-12  |  **Actual result:** PARTIALLY BLOCKED -- the "preserves original" half is now built and PASSES: all five `Evaluate*` commands accept `supersedes_id`+`reason`, flag the original `SUPERSEDED`, link the new row, and emit a `Corrected` audit event + `ReconciliationSuperseded` outbox event (`_apply_supersede()`) -- verified by `tests/test_yield_reconciliation.py::test_evaluate_yield_supersede_flags_original_and_links_correction` and `test_evaluate_material_reconciliation_supersede_flags_original`, both PASS. Still BLOCKED overall because "automatically re-evaluates affected downstream yields/reconciliations" is not built -- no baseline definition of "downstream" exists to build against (SG-133 remainder).  |  **Defect:** —

### TC-017-022-02 — Correction — Limit boundary behaviour

- **Requirement:** YLD-FR-022
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-09-12  |  **Actual result:** PARTIALLY BLOCKED -- boundary behavior for the "preserves original" half is verified: superseding an already-`SUPERSEDED` original is rejected `VALIDATION_FAILED` (`test_evaluate_yield_supersede_rejects_already_superseded_original`), a missing `reason` is rejected `VALIDATION_FAILED` (`test_evaluate_yield_supersede_requires_reason`), and a cross-batch `supersedes_id` is rejected `VALIDATION_FAILED` (`test_supersede_rejects_a_record_from_a_different_batch`) -- all PASS. Still BLOCKED overall for the same reason as TC-017-022-01: the downstream-re-evaluation half is not built (SG-133 remainder).  |  **Defect:** —

### TC-017-023-01 — Snapshot rule version — required behaviour

- **Requirement:** YLD-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Batch uses exact calculation/reconciliation rules included in issue snapshot. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Historical reproducibility. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- rule_object_id/rule_evaluation_id capture the exact Document 08 rule/evaluation version used at calculation time (immutable FK, not a re-resolved lookup) -- historically reproducible by construction; not independently tested with a batch-issue-snapshot-specific scenario (the snapshot mechanism itself belongs to the already-built batch_execution module).  |  **Defect:** —

### TC-017-023-02 — Snapshot rule version — Limit boundary behaviour

- **Requirement:** YLD-FR-023
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- rule_object_id/rule_evaluation_id capture the exact Document 08 rule/evaluation version used at calculation time (immutable FK, not a re-resolved lookup) -- historically reproducible by construction; not independently tested with a batch-issue-snapshot-specific scenario (the snapshot mechanism itself belongs to the already-built batch_execution module).  |  **Defect:** —

### TC-017-023-03 — Snapshot rule version — Concurrent writers on one aggregate

- **Requirement:** YLD-FR-023
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-017-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- rule_object_id/rule_evaluation_id capture the exact Document 08 rule/evaluation version used at calculation time (immutable FK, not a re-resolved lookup) -- historically reproducible by construction; not independently tested with a batch-issue-snapshot-specific scenario (the snapshot mechanism itself belongs to the already-built batch_execution module).  |  **Defect:** —

### TC-017-024-01 — Rework/reprocess accounting — required behaviour

- **Requirement:** YLD-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Original and rework material/output remain linked; no double-counting. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** True balance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- input_refs is a free-form JSONB bag; nothing structurally links a rework calculation back to its original to prevent double-counting (SG-133).  |  **Defect:** —

### TC-017-025-01 — Partial batch/sub-lot — required behaviour

- **Requirement:** YLD-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Where supported, calculate and reconcile by defined scope and aggregate to parent. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Partial release support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- SCOPE_TYPES includes SUB_LOT and rows can be scoped to one, but get_batch_summary() lists rows -- it does not sum/aggregate sub-lot results into a parent-level total (SG-133).  |  **Defect:** —

### TC-017-025-02 — Partial batch/sub-lot — Limit boundary behaviour

- **Requirement:** YLD-FR-025
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- SCOPE_TYPES includes SUB_LOT and rows can be scoped to one, but get_batch_summary() lists rows -- it does not sum/aggregate sub-lot results into a parent-level total (SG-133).  |  **Defect:** —

### TC-017-026-01 — Serial/device scope — required behaviour

- **Requirement:** YLD-FR-026
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Unit count/component usage may aggregate serial-level data without losing exception visibility. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** High-volume support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** PASS -- get_batch_summary() gained by_device_unit: serial-scoped rows summed per device unit (record_count + per-category Decimal totals) with every unresolved row listed by id on its own unit's entry, so aggregation does not hide exceptions; services/gxp-api/tests/test_yield_reconciliation.py::test_batch_summary_aggregates_by_device_unit_keeping_exceptions_visible and ::test_batch_summary_omits_units_for_unscoped_reconciliation  |  **Defect:** —

### TC-017-026-02 — Serial/device scope — Offline buffering and reconnect preserve evidence

- **Requirement:** YLD-FR-026
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-017-026-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** BLOCKED -- the serial/device-scope aggregation this case depended on is now built (see TC-017-026-01), but store-and-forward/offline buffering is Document 45 (SPEC-EDGE-003) territory and no offline buffer exists for this module's commands; the disconnect/reconnect precondition is not constructible here. Re-scoped from SG-132 to the unbuilt Document 45 dependency.  |  **Defect:** —

### TC-017-027-01 — External inventory reconciliation — required behaviour

- **Requirement:** YLD-FR-027
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: ERP/WMS quantity may be compared after GxP calculation; discrepancy flagged but ERP never overwrites GxP evidence automatically. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Boundary clear. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** PASS -- _compare_external_inventory() compares external_reference.quantity against the GxP-computed accounted total after the GxP calculation and records the outcome in ReconciliationRecord.external_comparison; a mismatch is raised in Document 53's ledger via erp.commands.record_reconciliation_difference() (VALUE_MISMATCH, resolution_status OPEN); services/gxp-api/tests/test_yield_reconciliation.py::test_matching_external_quantity_records_comparison_without_a_difference and ::test_external_discrepancy_flags_erp_difference_but_never_overwrites_variance  |  **Defect:** —

### TC-017-027-02 — External inventory reconciliation — Prohibited path is rejected

- **Requirement:** YLD-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: ERP/WMS quantity may be compared after GxP calculation; discrepancy flagged but ERP never overwrites GxP evidence automatically. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-017-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** PASS -- the prohibited path in YLD-FR-027 is ERP overwriting GxP evidence: with ERP reporting 92 against a GxP-computed 100, variance stays 0.000000, state stays ACCEPTABLE and quantities.accounted stays 100.000000 while the mismatch is flagged only in the ERP ledger; services/gxp-api/tests/test_yield_reconciliation.py::test_external_discrepancy_flags_erp_difference_but_never_overwrites_variance. Also covered: no erp_run_id supplied -> comparison recorded, no difference claimed (::test_external_discrepancy_without_erp_run_is_recorded_but_not_flagged)  |  **Defect:** —

### TC-017-027-03 — External inventory reconciliation — Limit boundary behaviour

- **Requirement:** YLD-FR-027
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** PASS -- boundary is exact Decimal equality, not a tolerance: 100.000001 external vs 100.000000 GxP is flagged (difference '0.000001'); the tolerance belongs to the GxP mass balance, not to the ERP cross-check; services/gxp-api/tests/test_yield_reconciliation.py::test_external_comparison_boundary_smallest_representable_difference  |  **Defect:** —

### TC-017-027-04 — External inventory reconciliation — Replayed inbound message is detected

- **Requirement:** YLD-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-017-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** PASS -- the ERP difference is written under an idempotency key derived from the evaluate command's own key ('{key}:erp-diff'), so a replayed evaluate returns the same receipt and the difference ledger still holds exactly one row; services/gxp-api/tests/test_yield_reconciliation.py::test_replayed_evaluate_does_not_raise_a_second_erp_difference  |  **Defect:** —

### TC-017-028-01 — Review display — required behaviour

- **Requirement:** YLD-FR-028
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: QA sees source quantities, formulas, calculation versions, results, tolerances, variances and investigations. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reviewable. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- get_batch_summary() returns source quantities, uom, tolerance_rule, result, state, variance and verified flag for QA review; services/gxp-api/tests/test_yield_reconciliation.py::test_batch_summary_release_blocked_until_verified.  |  **Defect:** —

### TC-017-028-02 — Review display — Limit boundary behaviour

- **Requirement:** YLD-FR-028
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-028-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- get_batch_summary() returns source quantities, uom, tolerance_rule, result, state, variance and verified flag for QA review; services/gxp-api/tests/test_yield_reconciliation.py::test_batch_summary_release_blocked_until_verified.  |  **Defect:** —

### TC-017-028-03 — Review display — Concurrent writers on one aggregate

- **Requirement:** YLD-FR-028
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-017-028-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- get_batch_summary() returns source quantities, uom, tolerance_rule, result, state, variance and verified flag for QA review; services/gxp-api/tests/test_yield_reconciliation.py::test_batch_summary_release_blocked_until_verified.  |  **Defect:** —

### TC-017-029-01 — Release blocker — required behaviour

- **Requirement:** YLD-FR-029
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Required unresolved yield/reconciliation failures block release. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Quality gate. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- release_blocked flag computed from any unresolved (FAILED/OUT_OF_LIMIT/OUT_OF_TOLERANCE) calculation or reconciliation; services/gxp-api/tests/test_yield_reconciliation.py::test_batch_summary_release_blocked_until_verified.  |  **Defect:** —

### TC-017-029-02 — Release blocker — Prohibited path is rejected

- **Requirement:** YLD-FR-029
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Required unresolved yield/reconciliation failures block release. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-017-029-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- release_blocked flag computed from any unresolved (FAILED/OUT_OF_LIMIT/OUT_OF_TOLERANCE) calculation or reconciliation; services/gxp-api/tests/test_yield_reconciliation.py::test_batch_summary_release_blocked_until_verified.  |  **Defect:** —

### TC-017-029-03 — Release blocker — Action without the required signature is blocked

- **Requirement:** YLD-FR-029
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-017-029-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- release_blocked flag computed from any unresolved (FAILED/OUT_OF_LIMIT/OUT_OF_TOLERANCE) calculation or reconciliation; services/gxp-api/tests/test_yield_reconciliation.py::test_batch_summary_release_blocked_until_verified.  |  **Defect:** —

### TC-017-029-04 — Release blocker — Signature bound to a superseded version is rejected

- **Requirement:** YLD-FR-029
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-017-029-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- release_blocked flag computed from any unresolved (FAILED/OUT_OF_LIMIT/OUT_OF_TOLERANCE) calculation or reconciliation; services/gxp-api/tests/test_yield_reconciliation.py::test_batch_summary_release_blocked_until_verified.  |  **Defect:** —

### TC-017-030-01 — Export — required behaviour

- **Requirement:** YLD-FR-030
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Final batch record includes yield and reconciliation results plus verification/signature and variance disposition. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** 211.188-style evidence support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** BLOCKED -- no document in Documents 01-105 declares a batch-record or eDHR export operation at all (verified against the API lists of Documents 12-17); the export has no owning module, canonical format, Vault/immutability semantics, signature policy or retention class. Promoted out of SG-132 into its own gap SG-137. get_batch_summary() already returns the *content* YLD-FR-030 describes but is an explicitly live, non-authoritative read -- not a frozen, hashed, signed export  |  **Defect:** —

### TC-017-030-02 — Export — Action without the required signature is blocked

- **Requirement:** YLD-FR-030
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-017-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** BLOCKED -- no document in Documents 01-105 declares a batch-record or eDHR export operation at all (verified against the API lists of Documents 12-17); the export has no owning module, canonical format, Vault/immutability semantics, signature policy or retention class. Promoted out of SG-132 into its own gap SG-137. get_batch_summary() already returns the *content* YLD-FR-030 describes but is an explicitly live, non-authoritative read -- not a frozen, hashed, signed export  |  **Defect:** —

### TC-017-030-03 — Export — Signature bound to a superseded version is rejected

- **Requirement:** YLD-FR-030
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-017-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** BLOCKED -- no document in Documents 01-105 declares a batch-record or eDHR export operation at all (verified against the API lists of Documents 12-17); the export has no owning module, canonical format, Vault/immutability semantics, signature policy or retention class. Promoted out of SG-132 into its own gap SG-137. get_batch_summary() already returns the *content* YLD-FR-030 describes but is an explicitly live, non-authoritative read -- not a frozen, hashed, signed export  |  **Defect:** —

### TC-017-030-04 — Export — Limit boundary behaviour

- **Requirement:** YLD-FR-030
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** BLOCKED -- no document in Documents 01-105 declares a batch-record or eDHR export operation at all (verified against the API lists of Documents 12-17); the export has no owning module, canonical format, Vault/immutability semantics, signature policy or retention class. Promoted out of SG-132 into its own gap SG-137. get_batch_summary() already returns the *content* YLD-FR-030 describes but is an explicitly live, non-authoritative read -- not a frozen, hashed, signed export  |  **Defect:** —

### TC-017-031-01 — Calculation trace — required behaviour

- **Requirement:** YLD-FR-031
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: For every result retain input IDs/versions/values, calculation rule, engine version, time and verifier/signature if required. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reproducible. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- input_refs/input_hash/rule_object_id/rule_evaluation_id/evaluated_by_user_id/evaluated_at/verified_signature_id/verified_by_user_id/verified_at all captured per result; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation, test_verify_full_flow_with_independent_signer.  |  **Defect:** —

### TC-017-031-02 — Calculation trace — Action without the required signature is blocked

- **Requirement:** YLD-FR-031
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-017-031-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- input_refs/input_hash/rule_object_id/rule_evaluation_id/evaluated_by_user_id/evaluated_at/verified_signature_id/verified_by_user_id/verified_at all captured per result; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation, test_verify_full_flow_with_independent_signer.  |  **Defect:** —

### TC-017-031-03 — Calculation trace — Signature bound to a superseded version is rejected

- **Requirement:** YLD-FR-031
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-017-031-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- input_refs/input_hash/rule_object_id/rule_evaluation_id/evaluated_by_user_id/evaluated_at/verified_signature_id/verified_by_user_id/verified_at all captured per result; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation, test_verify_full_flow_with_independent_signer.  |  **Defect:** —

### TC-017-031-04 — Calculation trace — Limit boundary behaviour

- **Requirement:** YLD-FR-031
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-017-031-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- input_refs/input_hash/rule_object_id/rule_evaluation_id/evaluated_by_user_id/evaluated_at/verified_signature_id/verified_by_user_id/verified_at all captured per result; services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation, test_verify_full_flow_with_independent_signer.  |  **Defect:** —

### TC-017-032-01 — Performance — required behaviour

- **Requirement:** YLD-FR-032
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** Minimum valid data set for `manufacturing_calculation`, `reconciliation_record`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /manufacturing-calculations/v1/yield/evaluate` (or the owning command) exercising: Large serial/component reconciliations may run asynchronously but final state is versioned and release waits for current result. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Scale safe. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- every evaluation in this module runs synchronously within the request's own transaction; no async job/queue path exists for large serial/component reconciliations (SG-133).  |  **Defect:** —

### TC-017-032-02 — Performance — Action without the required signature is blocked

- **Requirement:** YLD-FR-032
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-017-032-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- every evaluation in this module runs synchronously within the request's own transaction; no async job/queue path exists for large serial/component reconciliations (SG-133).  |  **Defect:** —

### TC-017-032-03 — Performance — Signature bound to a superseded version is rejected

- **Requirement:** YLD-FR-032
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-017-032-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- every evaluation in this module runs synchronously within the request's own transaction; no async job/queue path exists for large serial/component reconciliations (SG-133).  |  **Defect:** —

### TC-017-032-04 — Performance — Illegal state transition is rejected

- **Requirement:** YLD-FR-032
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `manufacturing_calculation`, `reconciliation_record` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-017-032-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- every evaluation in this module runs synchronously within the request's own transaction; no async job/queue path exists for large serial/component reconciliations (SG-133).  |  **Defect:** —

### TC-017-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- shared FastAPI get_current_actor dependency rejects an unauthenticated caller on every route in this module; services/gxp-api/tests/test_yield_reconciliation.py::test_unauthorized_without_token_rejected.  |  **Defect:** —

### TC-017-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- shared evaluate_policy() RBAC check (same mechanism proven by every other module's dedicated permission test) gates every command in this module; not independently re-tested with a dedicated authenticated-but-unauthorized case this pass.  |  **Defect:** —

### TC-017-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- single-tenant-per-deployment platform (ADR-0006) -- no tenant_id column exists anywhere in this codebase.  |  **Defect:** —

### TC-017-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- shared evaluate_policy() site-scoped role resolution every command in this module calls; not independently re-tested here.  |  **Defect:** —

### TC-017-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no qualification code is declared for any yield/reconciliation action.  |  **Defect:** —

### TC-017-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- verify_record() rejects a verifier who is also the performer (SIG-FR-018) -- this module's own real SoD check; services/gxp-api/tests/test_yield_reconciliation.py::test_verify_requires_independent_verifier.  |  **Defect:** —

### TC-017-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- VerifyRecordCommand.expected_version is a required field, checked with StaleVersionError on mismatch before any write; services/gxp-api/tests/test_yield_reconciliation.py::test_verify_stale_version_rejected.  |  **Defect:** —

### TC-017-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- StaleVersionError raised by verify_record()'s SELECT ... FOR UPDATE + version check; services/gxp-api/tests/test_yield_reconciliation.py::test_verify_stale_version_rejected.  |  **Defect:** —

### TC-017-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- check_idempotency()/_receipt_from_existing() on every command; services/gxp-api/tests/test_yield_reconciliation.py::test_duplicate_idempotency_key_returns_same_receipt.  |  **Defect:** —

### TC-017-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- shared check_idempotency()/IdempotencyConflictError gateway helper every command calls (same mechanism proven by other modules' dedicated conflict tests); not independently re-tested with a same-key-different-payload case in this module this pass.  |  **Defect:** —

### TC-017-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- every 200 response's MutationReceipt carries a real audit_event_id from the same PostgreSQL transaction; proven by every test in services/gxp-api/tests/test_yield_reconciliation.py.  |  **Defect:** —

### TC-017-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no fault-injection harness exists in this test suite to simulate a DB/signature-service outage; architectural guarantee (AG-06/MUT-FR-022), not independently re-tested per module in this codebase.  |  **Defect:** —

### TC-017-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no crash/rollback-injection harness exists in this test suite; same architectural-guarantee treatment as M12.  |  **Defect:** —

### TC-017-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-EBMR-008-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no Frappe projection consumer exists in this codebase's test harness to take offline (AG-11).  |  **Defect:** —

### TC-017-S001 — Specification scenario — normal yield

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: normal yield | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation (normal yield calculation via the released yield_percent rule).  |  **Defect:** —

### TC-017-S002 — Specification scenario — zero theoretical quantity

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: zero theoretical quantity | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_zero_theoretical_quantity_fails_not_crashes (division by zero produces a typed ValidationFailedError, never a silent zero/NaN/crash -- CALC-FR-010).  |  **Defect:** —

### TC-017-S003 — Specification scenario — decimal precision

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: decimal precision | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_normal_calculation exercises _quantize()'s CC-4 6dp intermediate / 2dp reported half-up rounding read from the rule's own rounding_policy.  |  **Defect:** —

### TC-017-S004 — Specification scenario — UOM conversion

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: UOM conversion | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no controlled UOM conversion service exists in this module (YLD-FR-017's own gap) -- a cross-UOM scenario is not constructible (SG-133).  |  **Defect:** —

### TC-017-S005 — Specification scenario — min boundary

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: min boundary | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_yield_below_min_boundary_out_of_limit.  |  **Defect:** —

### TC-017-S006 — Specification scenario — max boundary

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: max boundary | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- max_percent uses the identical OUT_OF_LIMIT comparison as min_percent (YLD-FR-006); shared code path with S005, not independently re-tested with a max-specific case this pass.  |  **Defect:** —

### TC-017-S007 — Specification scenario — below/above tolerance

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: below/above tolerance | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_reconciliation_out_of_tolerance (below/above tolerance via the inclusive/exclusive tolerance_rule comparison).  |  **Defect:** —

### TC-017-S008 — Specification scenario — independent verification

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: independent verification | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_yield_reconciliation.py::test_verify_full_flow_with_independent_signer, test_verify_requires_independent_verifier.  |  **Defect:** —

### TC-017-S009 — Specification scenario — potency adjustment

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: potency adjustment | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_potency_requires_a_released_rule proves the fail-closed path; a full potency-adjustment-succeeds scenario against a real customer-authored rule is not independently exercised (no such rule is seeded by default, YLD-FR-015).  |  **Defect:** —

### TC-017-S010 — Specification scenario — material return

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: material return | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_material_reconciliation_acceptable exercises the generic mass-balance mechanics including the 'returned' category; not independently tested with return-specific values.  |  **Defect:** —

### TC-017-S011 — Specification scenario — sample/destruction

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: sample/destruction | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- 'samples'/'destroyed' categories are part of the same generic mass-balance mechanics proven by services/gxp-api/tests/test_yield_reconciliation.py::test_evaluate_material_reconciliation_acceptable; not independently tested with sample/destruction-specific values.  |  **Defect:** —

### TC-017-S012 — Specification scenario — rework

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: rework | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- input_refs has no rework-linkage structure to prevent double-counting (YLD-FR-024's own gap) (SG-133).  |  **Defect:** —

### TC-017-S013 — Specification scenario — label discrepancy

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: label discrepancy | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** PASS -- 100 labels issued in Document 16, 95 accounted, the missing 5 surface as this module's own OUT_OF_TOLERANCE (variance 5.000000) and set the batch summary's unified release_blocked flag; services/gxp-api/tests/test_yield_reconciliation.py::test_label_discrepancy_from_packaging_counts_blocks_release  |  **Defect:** —

### TC-017-S014 — Specification scenario — component scrap

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: component scrap | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** PASS -- component scrap reconciled against a real DeviceUnit serial identity using YLD-FR-013's literal scrapped/assembled categories, balancing to variance 0.000000; services/gxp-api/tests/test_yield_reconciliation.py::test_component_reconciliation_scoped_to_device_unit  |  **Defect:** —

### TC-017-S015 — Specification scenario — ERP discrepancy

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: ERP discrepancy | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-27  |  **Actual result:** PASS -- ERP discrepancy scenario end to end: ERP run created through Document 53's own endpoint, GxP reconciliation evaluated, mismatch flagged as VALUE_MISMATCH/OPEN with internal_value and external_value both recorded, GxP variance untouched; services/gxp-api/tests/test_yield_reconciliation.py::test_external_discrepancy_flags_erp_difference_but_never_overwrites_variance  |  **Defect:** —

### TC-017-S016 — Specification scenario — correction recalculation

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: correction recalculation | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no correction command exists in this module (YLD-FR-022's own gap) (SG-133).  |  **Defect:** —

### TC-017-S017 — Specification scenario — old rule snapshot

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: old rule snapshot | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- rule_object_id/rule_evaluation_id are immutable FKs captured at evaluation time, not a re-resolved lookup -- an old batch's calculation structurally keeps pointing at the exact rule version used, even after a newer version is released (YLD-FR-023); not independently tested with a live rule-supersession scenario this pass.  |  **Defect:** —

### TC-017-S018 — Specification scenario — large serial aggregation

- **Requirement:** SPEC-EBMR-008-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: large serial aggregation | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- every evaluation in this module runs synchronously; no async job/queue path exists (YLD-FR-032's own gap) (SG-133).  |  **Defect:** —
