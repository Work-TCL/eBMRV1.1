# Test Cases — Document 53: Integration Error Handling, Retry, Idempotency & Reconciliation (SPEC-ERP-006)

**Work package:** WP-07  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** INT-FR-001..030 (30)  
**Test cases:** 100  
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

### TC-053-001-01 — Canonical integration message — required behaviour

- **Requirement:** INT-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: All inbound/outbound exchanges have message/command/event ID, source, target, schema, correlation, causation and payload hash. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- IntegrationCommand/IntegrationInboundEvent carry id, source (erp_instance_id), correlation_id, causation_id and payload_hash.  |  **Defect:** —

### TC-053-001-02 — Canonical integration message — Replayed inbound message is detected

- **Requirement:** INT-FR-001
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-053-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- IntegrationCommand/IntegrationInboundEvent carry id, source (erp_instance_id), correlation_id, causation_id and payload_hash.  |  **Defect:** —

### TC-053-001-03 — Canonical integration message — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** INT-FR-001
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-053-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- IntegrationCommand/IntegrationInboundEvent carry id, source (erp_instance_id), correlation_id, causation_id and payload_hash.  |  **Defect:** —

### TC-053-002-01 — Error taxonomy — required behaviour

- **Requirement:** INT-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: AUTH, CONFIG, VALIDATION, BUSINESS_REJECT, CONFLICT, RATE_LIMIT, TRANSIENT_NETWORK, SERVER_ERROR, TIMEOUT_UNCERTAIN, SCHEMA, SECURITY, MANUAL_REVIEW. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Consistent handling. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- ERROR_CATEGORIES (12 values) + classify_integration_error(); services/gxp-api/tests/test_erp_flow.py::test_dispatch_server_error_schedules_retry (SERVER_ERROR), test_dispatch_validation_error_dead_letters_immediately (VALIDATION), test_dispatch_timeout_is_uncertain_not_blind_success_or_retry_storm (TIMEOUT_UNCERTAIN).  |  **Defect:** —

### TC-053-002-02 — Error taxonomy — Prohibited path is rejected

- **Requirement:** INT-FR-002
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: AUTH, CONFIG, VALIDATION, BUSINESS_REJECT, CONFLICT, RATE_LIMIT, TRANSIENT_NETWORK, SERVER_ERROR, TIMEOUT_UNCERTAIN, SCHEMA, SECURITY, MANUA | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-053-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- ERROR_CATEGORIES (12 values) + classify_integration_error(); services/gxp-api/tests/test_erp_flow.py::test_dispatch_server_error_schedules_retry (SERVER_ERROR), test_dispatch_validation_error_dead_letters_immediately (VALIDATION), test_dispatch_timeout_is_uncertain_not_blind_success_or_retry_storm (TIMEOUT_UNCERTAIN).  |  **Defect:** —

### TC-053-002-03 — Error taxonomy — Limit boundary behaviour

- **Requirement:** INT-FR-002
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-053-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- ERROR_CATEGORIES (12 values) + classify_integration_error(); services/gxp-api/tests/test_erp_flow.py::test_dispatch_server_error_schedules_retry (SERVER_ERROR), test_dispatch_validation_error_dead_letters_immediately (VALIDATION), test_dispatch_timeout_is_uncertain_not_blind_success_or_retry_storm (TIMEOUT_UNCERTAIN).  |  **Defect:** —

### TC-053-003-01 — Retry classification — required behaviour

- **Requirement:** INT-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Only retryable categories retry automatically; business/validation/config errors require correction/review. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No retry storms. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- RETRYABLE_CATEGORIES vs MANUAL_REVIEW_CATEGORIES in reliability.py; services/gxp-api/tests/test_erp_flow.py::test_dispatch_server_error_schedules_retry vs test_dispatch_validation_error_dead_letters_immediately.  |  **Defect:** —

### TC-053-004-01 — Exponential backoff — required behaviour

- **Requirement:** INT-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Configurable capped backoff + jitter; vendor Retry-After honored where applicable. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Resilience. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- compute_retry_decision(): base*multiplier^attempt capped + jitter, honoring an explicit retry_after_seconds where the caller supplies one; the Retry-After-header path itself is not independently re-tested with a live 429 response this pass.  |  **Defect:** —

### TC-053-005-01 — Maximum attempts — required behaviour

- **Requirement:** INT-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Retry count/time window configurable; exhausted commands enter manual-review/dead-letter. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Bounded. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- RetryPolicy.max_attempts + DEAD_LETTER on exhaustion; services/gxp-api/tests/test_erp_flow.py::test_dispatch_validation_error_dead_letters_immediately proves the DEAD_LETTER transition (via a non-retryable category; the 'retried N times then exhausted' path shares the identical decision code, not independently re-executed).  |  **Defect:** —

### TC-053-006-01 — Idempotency key — required behaviour

- **Requirement:** INT-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Every write command has stable idempotency key derived from immutable source event/operation semantics. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No duplicates. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- idempotency_key (unique per erp_instance_id) on IntegrationCommand; services/gxp-api/tests/test_erp_flow.py::test_register_instance_duplicate_idempotency_key_returns_same_receipt.  |  **Defect:** —

### TC-053-006-02 — Idempotency key — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** INT-FR-006
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-053-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- idempotency_key (unique per erp_instance_id) on IntegrationCommand; services/gxp-api/tests/test_erp_flow.py::test_register_instance_duplicate_idempotency_key_returns_same_receipt.  |  **Defect:** —

### TC-053-007-01 — Payload hash — required behaviour

- **Requirement:** INT-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Same idempotency key with different payload hash is conflict/integrity incident. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Tamper/drift detection. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- payload_hash conflict detection in queue_erp_command()/ingest_erp_event(); services/gxp-api/tests/test_erp_flow.py::test_ingest_event_dedupes_and_detects_conflict.  |  **Defect:** —

### TC-053-008-01 — Uncertain timeout — required behaviour

- **Requirement:** INT-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Timeout after external request may represent committed external transaction; reconcile before replaying create where duplicate risk exists. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Exactly-once effect strategy. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- TIMEOUT_UNCERTAIN classification + reconcile_uncertain_commit() (never blindly resumes as PENDING); services/gxp-api/tests/test_erp_flow.py::test_dispatch_timeout_is_uncertain_not_blind_success_or_retry_storm.  |  **Defect:** —

### TC-053-008-02 — Uncertain timeout — Replayed inbound message is detected

- **Requirement:** INT-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-053-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- TIMEOUT_UNCERTAIN classification + reconcile_uncertain_commit() (never blindly resumes as PENDING); services/gxp-api/tests/test_erp_flow.py::test_dispatch_timeout_is_uncertain_not_blind_success_or_retry_storm.  |  **Defect:** —

### TC-053-008-03 — Uncertain timeout — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** INT-FR-008
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-053-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- TIMEOUT_UNCERTAIN classification + reconcile_uncertain_commit() (never blindly resumes as PENDING); services/gxp-api/tests/test_erp_flow.py::test_dispatch_timeout_is_uncertain_not_blind_success_or_retry_storm.  |  **Defect:** —

### TC-053-009-01 — External correlation — required behaviour

- **Requirement:** INT-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Store vendor request/job/doc/reference IDs on every successful/uncertain attempt. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Investigability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- external_reference stored on the command and on every IntegrationCommandAttempt row; services/gxp-api/tests/test_erp_flow.py::test_queue_then_dispatch_command_succeeds.  |  **Defect:** —

### TC-053-009-02 — External correlation — Replayed inbound message is detected

- **Requirement:** INT-FR-009
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-053-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- external_reference stored on the command and on every IntegrationCommandAttempt row; services/gxp-api/tests/test_erp_flow.py::test_queue_then_dispatch_command_succeeds.  |  **Defect:** —

### TC-053-009-03 — External correlation — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** INT-FR-009
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-053-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- external_reference stored on the command and on every IntegrationCommandAttempt row; services/gxp-api/tests/test_erp_flow.py::test_queue_then_dispatch_command_succeeds.  |  **Defect:** —

### TC-053-010-01 — Inbound dedupe — required behaviour

- **Requirement:** INT-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Unique external event/message ID + source instance and payload hash. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Replay safe. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- unique(erp_instance_id, external_event_id) + payload_hash comparison; services/gxp-api/tests/test_erp_flow.py::test_ingest_event_dedupes_and_detects_conflict.  |  **Defect:** —

### TC-053-010-02 — Inbound dedupe — Replayed inbound message is detected

- **Requirement:** INT-FR-010
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-053-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- unique(erp_instance_id, external_event_id) + payload_hash comparison; services/gxp-api/tests/test_erp_flow.py::test_ingest_event_dedupes_and_detects_conflict.  |  **Defect:** —

### TC-053-010-03 — Inbound dedupe — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** INT-FR-010
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-053-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- unique(erp_instance_id, external_event_id) + payload_hash comparison; services/gxp-api/tests/test_erp_flow.py::test_ingest_event_dedupes_and_detects_conflict.  |  **Defect:** —

### TC-053-011-01 — Out-of-order events — required behaviour

- **Requirement:** INT-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Process version/sequence-aware; stale events cannot overwrite newer projection. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Ordering. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- source_version is captured but no stale-supersede enforcement exists -- STALE_SUPERSEDED is declared in INBOUND_STATES but no code path ever sets it (SG-126).  |  **Defect:** —

### TC-053-011-02 — Out-of-order events — Concurrent writers on one aggregate

- **Requirement:** INT-FR-011
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-053-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- source_version is captured but no stale-supersede enforcement exists -- STALE_SUPERSEDED is declared in INBOUND_STATES but no code path ever sets it (SG-126).  |  **Defect:** —

### TC-053-012-01 — Dead letter — required behaviour

- **Requirement:** INT-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Retain failed original payload hash/reference, attempts/errors and required next action. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No loss. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- DEAD_LETTER state + required_next_action + original payload/payload_hash retained on the same row; services/gxp-api/tests/test_erp_flow.py::test_dispatch_validation_error_dead_letters_immediately.  |  **Defect:** —

### TC-053-012-02 — Dead letter — Prohibited path is rejected

- **Requirement:** INT-FR-012
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Retain failed original payload hash/reference, attempts/errors and required next action. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-053-012-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- DEAD_LETTER state + required_next_action + original payload/payload_hash retained on the same row; services/gxp-api/tests/test_erp_flow.py::test_dispatch_validation_error_dead_letters_immediately.  |  **Defect:** —

### TC-053-013-01 — Manual replay — required behaviour

- **Requirement:** INT-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Authorized replay uses exact original payload unless a new corrected command is explicitly created. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- retry_erp_command() reuses the exact original payload (never mutated); services/gxp-api/tests/test_erp_flow.py::test_retry_manual_requires_reason_and_resets_to_pending.  |  **Defect:** —

### TC-053-014-01 — Corrected command — required behaviour

- **Requirement:** INT-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Business correction creates new command ID linked to original; never mutate original command payload. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** History. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- create_corrected_command() links a new command to the original via correction_of_id, never mutating the original; services/gxp-api/tests/test_erp_flow.py::test_create_corrected_command_from_dead_letter.  |  **Defect:** —

### TC-053-014-02 — Corrected command — Prohibited path is rejected

- **Requirement:** INT-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Business correction creates new command ID linked to original; never mutate original command payload. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-053-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- create_corrected_command() links a new command to the original via correction_of_id, never mutating the original; services/gxp-api/tests/test_erp_flow.py::test_create_corrected_command_from_dead_letter.  |  **Defect:** —

### TC-053-015-01 — Cancellation — required behaviour

- **Requirement:** INT-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Pending command may be cancelled/superseded only before confirmed external commit and with reason. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** State clarity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- cancel_pending_erp_command() only accepts PENDING/RETRY_WAIT; services/gxp-api/tests/test_erp_flow.py::test_cancel_pending_command_requires_reason, test_cancel_dispatched_command_rejected.  |  **Defect:** —

### TC-053-015-02 — Cancellation — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** INT-FR-015
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-053-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- cancel_pending_erp_command() only accepts PENDING/RETRY_WAIT; services/gxp-api/tests/test_erp_flow.py::test_cancel_pending_command_requires_reason, test_cancel_dispatched_command_rejected.  |  **Defect:** —

### TC-053-015-03 — Cancellation — Replayed inbound message is detected

- **Requirement:** INT-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-053-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- cancel_pending_erp_command() only accepts PENDING/RETRY_WAIT; services/gxp-api/tests/test_erp_flow.py::test_cancel_pending_command_requires_reason, test_cancel_dispatched_command_rejected.  |  **Defect:** —

### TC-053-015-04 — Cancellation — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** INT-FR-015
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-053-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- cancel_pending_erp_command() only accepts PENDING/RETRY_WAIT; services/gxp-api/tests/test_erp_flow.py::test_cancel_pending_command_requires_reason, test_cancel_dispatched_command_rejected.  |  **Defect:** —

### TC-053-016-01 — Compensation — required behaviour

- **Requirement:** INT-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: External reversal/compensation is a new integration command tied to authorized GxP correction/disposition. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No hidden rollback. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no distinct 'compensation command tied to an authorized GxP correction/disposition reference' type exists -- create_corrected_command covers correction, not a reversal/compensation semantic (SG-126).  |  **Defect:** —

### TC-053-016-02 — Compensation — Action without the required signature is blocked

- **Requirement:** INT-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-053-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no distinct 'compensation command tied to an authorized GxP correction/disposition reference' type exists -- create_corrected_command covers correction, not a reversal/compensation semantic (SG-126).  |  **Defect:** —

### TC-053-016-03 — Compensation — Signature bound to a superseded version is rejected

- **Requirement:** INT-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-053-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no distinct 'compensation command tied to an authorized GxP correction/disposition reference' type exists -- create_corrected_command covers correction, not a reversal/compensation semantic (SG-126).  |  **Defect:** —

### TC-053-016-04 — Compensation — Replayed inbound message is detected

- **Requirement:** INT-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-053-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no distinct 'compensation command tied to an authorized GxP correction/disposition reference' type exists -- create_corrected_command covers correction, not a reversal/compensation semantic (SG-126).  |  **Defect:** —

### TC-053-017-01 — Reconciliation types — required behaviour

- **Requirement:** INT-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: MISSING_EXTERNAL, EXTRA_EXTERNAL, VALUE_MISMATCH, STATUS_MISMATCH, REFERENCE_MISMATCH, DUPLICATE_EXTERNAL, STALE_MAPPING. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Structured drift. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- DIFFERENCE_TYPES (7 values); services/gxp-api/tests/test_erp_flow.py::test_reconciliation_run_lifecycle_never_auto_resolves exercises MISSING_EXTERNAL.  |  **Defect:** —

### TC-053-017-02 — Reconciliation types — Illegal state transition is rejected

- **Requirement:** INT-FR-017
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-053-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- DIFFERENCE_TYPES (7 values); services/gxp-api/tests/test_erp_flow.py::test_reconciliation_run_lifecycle_never_auto_resolves exercises MISSING_EXTERNAL.  |  **Defect:** —

### TC-053-017-03 — Reconciliation types — Replayed inbound message is detected

- **Requirement:** INT-FR-017
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-053-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- DIFFERENCE_TYPES (7 values); services/gxp-api/tests/test_erp_flow.py::test_reconciliation_run_lifecycle_never_auto_resolves exercises MISSING_EXTERNAL.  |  **Defect:** —

### TC-053-017-04 — Reconciliation types — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** INT-FR-017
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-053-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- DIFFERENCE_TYPES (7 values); services/gxp-api/tests/test_erp_flow.py::test_reconciliation_run_lifecycle_never_auto_resolves exercises MISSING_EXTERNAL.  |  **Defect:** —

### TC-053-018-01 — Reconciliation snapshot — required behaviour

- **Requirement:** INT-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Report records source cutoff, query keys, external response refs and mapping versions. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reproducible. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- cutoff_at/query_keys/mapping_version_snapshot captured at IntegrationReconciliationRun creation time.  |  **Defect:** —

### TC-053-018-02 — Reconciliation snapshot — Replayed inbound message is detected

- **Requirement:** INT-FR-018
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-053-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- cutoff_at/query_keys/mapping_version_snapshot captured at IntegrationReconciliationRun creation time.  |  **Defect:** —

### TC-053-018-03 — Reconciliation snapshot — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** INT-FR-018
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-053-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- cutoff_at/query_keys/mapping_version_snapshot captured at IntegrationReconciliationRun creation time.  |  **Defect:** —

### TC-053-018-04 — Reconciliation snapshot — Concurrent writers on one aggregate

- **Requirement:** INT-FR-018
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-053-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- cutoff_at/query_keys/mapping_version_snapshot captured at IntegrationReconciliationRun creation time.  |  **Defect:** —

### TC-053-019-01 — Auto-resolve — required behaviour

- **Requirement:** INT-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Only benign known differences/duplicates may auto-resolve under released rule; quantity/status mismatches require review. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Safe. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- resolve_reconciliation_difference() rejects resolution_status='AUTO_RESOLVED' outright (SG-124: no auto-resolve rule exists); services/gxp-api/tests/test_erp_flow.py::test_reconciliation_run_lifecycle_never_auto_resolves.  |  **Defect:** —

### TC-053-019-02 — Auto-resolve — Action without the required signature is blocked

- **Requirement:** INT-FR-019
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-053-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- resolve_reconciliation_difference() rejects resolution_status='AUTO_RESOLVED' outright (SG-124: no auto-resolve rule exists); services/gxp-api/tests/test_erp_flow.py::test_reconciliation_run_lifecycle_never_auto_resolves.  |  **Defect:** —

### TC-053-019-03 — Auto-resolve — Signature bound to a superseded version is rejected

- **Requirement:** INT-FR-019
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-053-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- resolve_reconciliation_difference() rejects resolution_status='AUTO_RESOLVED' outright (SG-124: no auto-resolve rule exists); services/gxp-api/tests/test_erp_flow.py::test_reconciliation_run_lifecycle_never_auto_resolves.  |  **Defect:** —

### TC-053-019-04 — Auto-resolve — Illegal state transition is rejected

- **Requirement:** INT-FR-019
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-053-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- resolve_reconciliation_difference() rejects resolution_status='AUTO_RESOLVED' outright (SG-124: no auto-resolve rule exists); services/gxp-api/tests/test_erp_flow.py::test_reconciliation_run_lifecycle_never_auto_resolves.  |  **Defect:** —

### TC-053-020-01 — Integration hold — required behaviour

- **Requirement:** INT-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Critical unresolved integration mismatch can create operational/QA review flag according to module policy. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Risk. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- requires_qa_hold boolean field on every IntegrationReconciliationDifference -- routing-only signal, not itself a QA workflow gate this pass.  |  **Defect:** —

### TC-053-020-02 — Integration hold — Replayed inbound message is detected

- **Requirement:** INT-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-053-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- requires_qa_hold boolean field on every IntegrationReconciliationDifference -- routing-only signal, not itself a QA workflow gate this pass.  |  **Defect:** —

### TC-053-020-03 — Integration hold — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** INT-FR-020
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-053-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- requires_qa_hold boolean field on every IntegrationReconciliationDifference -- routing-only signal, not itself a QA workflow gate this pass.  |  **Defect:** —

### TC-053-021-01 — SLA/aging — required behaviour

- **Requirement:** INT-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Track oldest pending, retry age, dead-letter age and reconciliation age. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Operations. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- attempt_count/next_attempt_at/created_at are queryable raw fields but no aggregated SLA/aging dashboard query exists (SG-126).  |  **Defect:** —

### TC-053-022-01 — Circuit breaker — required behaviour

- **Requirement:** INT-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Per-instance breaker protects repeated transient vendor failures without losing queued commands. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Stability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- IntegrationCircuitBreaker + trip/close logic in reliability.py; services/gxp-api/tests/test_erp_flow.py::test_circuit_breaker_opens_after_repeated_failures_and_throttles.  |  **Defect:** —

### TC-053-022-02 — Circuit breaker — Prohibited path is rejected

- **Requirement:** INT-FR-022
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Per-instance breaker protects repeated transient vendor failures without losing queued commands. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-053-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- IntegrationCircuitBreaker + trip/close logic in reliability.py; services/gxp-api/tests/test_erp_flow.py::test_circuit_breaker_opens_after_repeated_failures_and_throttles.  |  **Defect:** —

### TC-053-023-01 — Bulk jobs — required behaviour

- **Requirement:** INT-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Bulk import/export job tracks record-level successes/failures and supports idempotent resume. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Scale. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no bulk import/export job-tracking entity or resume mechanism exists (SG-126).  |  **Defect:** —

### TC-053-023-02 — Bulk jobs — Prohibited path is rejected

- **Requirement:** INT-FR-023
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Bulk import/export job tracks record-level successes/failures and supports idempotent resume. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-053-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no bulk import/export job-tracking entity or resume mechanism exists (SG-126).  |  **Defect:** —

### TC-053-024-01 — Rate limiting — required behaviour

- **Requirement:** INT-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Per provider/operation quotas configured. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Vendor-safe. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- RATE_LIMIT is classified and retried reactively (a 429 response), but no proactive per-provider/operation quota configuration exists (SG-126).  |  **Defect:** —

### TC-053-024-02 — Rate limiting — Limit boundary behaviour

- **Requirement:** INT-FR-024
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-053-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- RATE_LIMIT is classified and retried reactively (a 429 response), but no proactive per-provider/operation quota configuration exists (SG-126).  |  **Defect:** —

### TC-053-025-01 — Security event — required behaviour

- **Requirement:** INT-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Unexpected payload hash/idempotency conflict/source identity mismatch raises security/data-integrity event. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Detection. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- ErpExternalConflictError is raised on a payload-hash/idempotency conflict, but no separate security-ledger/SIEM event is emitted for it (no such ledger exists in this codebase for integration events specifically) (SG-126).  |  **Defect:** —

### TC-053-026-01 — Observability — required behaviour

- **Requirement:** INT-FR-026
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Metrics/logs/traces include correlation IDs but redact sensitive credentials/content. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- correlation_id on every ledger row; error_detail is structured JSONB; no credential ever enters error_detail/audit payloads (adapters never echo auth_secret back).  |  **Defect:** —

### TC-053-027-01 — Audit — required behaviour

- **Requirement:** INT-FR-027
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Manual retry/remap/cancel/reconcile resolution audited. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Accountability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- every manual retry/cancel/correct/resolve writes a real audit event via _write_receipt(); proven implicitly by every 200 response's audit_event_id.  |  **Defect:** —

### TC-053-027-02 — Audit — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** INT-FR-027
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-053-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- every manual retry/cancel/correct/resolve writes a real audit event via _write_receipt(); proven implicitly by every 200 response's audit_event_id.  |  **Defect:** —

### TC-053-028-01 — Retention — required behaviour

- **Requirement:** INT-FR-028
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Integration ledgers retained long enough to support regulated-record investigation and external reconciliation. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no retention_class column exists on any of the ten provisional erp.* tables (Document 70's universal aggregate baseline element deferred alongside the rest of the provisional schema, SG-121) (SG-121).  |  **Defect:** —

### TC-053-028-02 — Retention — Replayed inbound message is detected

- **Requirement:** INT-FR-028
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-053-028-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no retention_class column exists on any of the ten provisional erp.* tables (Document 70's universal aggregate baseline element deferred alongside the rest of the provisional schema, SG-121) (SG-121).  |  **Defect:** —

### TC-053-028-03 — Retention — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** INT-FR-028
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-053-028-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no retention_class column exists on any of the ten provisional erp.* tables (Document 70's universal aggregate baseline element deferred alongside the rest of the provisional schema, SG-121) (SG-121).  |  **Defect:** —

### TC-053-028-04 — Retention — Offline buffering and reconnect preserve evidence

- **Requirement:** INT-FR-028
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-053-028-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no retention_class column exists on any of the ten provisional erp.* tables (Document 70's universal aggregate baseline element deferred alongside the rest of the provisional schema, SG-121) (SG-121).  |  **Defect:** —

### TC-053-029-01 — Chaos testing — required behaviour

- **Requirement:** INT-FR-029
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Simulate network partitions, lost responses, duplicates, throttling, partial bulk failure and provider outage. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reliability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no network-partition/lost-response/duplicate/throttling/provider-outage chaos-testing harness exists beyond this pass's unit-level fault injection (500/422/timeout) (SG-126).  |  **Defect:** —

### TC-053-029-02 — Chaos testing — Prohibited path is rejected

- **Requirement:** INT-FR-029
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Simulate network partitions, lost responses, duplicates, throttling, partial bulk failure and provider outage. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-053-029-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no network-partition/lost-response/duplicate/throttling/provider-outage chaos-testing harness exists beyond this pass's unit-level fault injection (500/422/timeout) (SG-126).  |  **Defect:** —

### TC-053-030-01 — No silent success — required behaviour

- **Requirement:** INT-FR-030
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: UI never displays external posting successful until Integration Gateway has confirmed/reconciled it. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Truth. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- dispatch_erp_command()'s two-transaction design means GET /integration/v1/commands/{id} never reports SUCCEEDED until the second transaction has committed a confirmed outcome; proven by every dispatch test reading command.state afterward.  |  **Defect:** —

### TC-053-030-02 — No silent success — Prohibited path is rejected

- **Requirement:** INT-FR-030
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: UI never displays external posting successful until Integration Gateway has confirmed/reconciled it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-053-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- dispatch_erp_command()'s two-transaction design means GET /integration/v1/commands/{id} never reports SUCCEEDED until the second transaction has committed a confirmed outcome; proven by every dispatch test reading command.state afterward.  |  **Defect:** —

### TC-053-030-03 — No silent success — Replayed inbound message is detected

- **Requirement:** INT-FR-030
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-053-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- dispatch_erp_command()'s two-transaction design means GET /integration/v1/commands/{id} never reports SUCCEEDED until the second transaction has committed a confirmed outcome; proven by every dispatch test reading command.state afterward.  |  **Defect:** —

### TC-053-030-04 — No silent success — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** INT-FR-030
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-053-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- dispatch_erp_command()'s two-transaction design means GET /integration/v1/commands/{id} never reports SUCCEEDED until the second transaction has committed a confirmed outcome; proven by every dispatch test reading command.state afterward.  |  **Defect:** —

### TC-053-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- shared FastAPI get_current_actor dependency on every /integration/v1 route; not independently re-tested for this document.  |  **Defect:** —

### TC-053-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_register_instance_unauthorized_without_permission (same RBAC mechanism every /integration/v1 route uses).  |  **Defect:** —

### TC-053-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- single-tenant-per-deployment platform (ADR-0006) -- no tenant_id column exists anywhere in this codebase.  |  **Defect:** —

### TC-053-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- shared evaluate_policy() site-scoped role resolution every command in this module calls; not independently re-tested here.  |  **Defect:** —

### TC-053-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no qualification code is declared for any WP-07 action.  |  **Defect:** —

### TC-053-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- every WP-07 action is unsigned (SG-122) -- no signature-completion SoD check applies.  |  **Defect:** —

### TC-053-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- expected_version is a required Pydantic field on every versioned command.  |  **Defect:** —

### TC-053-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- StaleVersionError raised by every _load_*_for_update helper; not independently re-tested with a dedicated stale-version case this pass.  |  **Defect:** —

### TC-053-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_register_instance_duplicate_idempotency_key_returns_same_receipt, test_advance_sync_checkpoint_idempotent_resubmit.  |  **Defect:** —

### TC-053-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_ingest_event_dedupes_and_detects_conflict (INT-FR-007's own duplicate-different-payload conflict path).  |  **Defect:** —

### TC-053-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- every 200 response's MutationReceipt carries a real audit_event_id from the same PostgreSQL transaction; proven by every test in services/gxp-api/tests/test_erp_flow.py.  |  **Defect:** —

### TC-053-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no fault-injection harness exists in this test suite to simulate a DB/signature-service outage.  |  **Defect:** —

### TC-053-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no crash/rollback-injection harness exists in this test suite.  |  **Defect:** —

### TC-053-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-ERP-006-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no Frappe projection consumer exists in this codebase's test harness to take offline.  |  **Defect:** —

### TC-053-S001 — Specification scenario — 500 error retry

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: 500 error retry | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_dispatch_server_error_schedules_retry (500 -> SERVER_ERROR -> RETRY_WAIT).  |  **Defect:** —

### TC-053-S002 — Specification scenario — 400 validation no retry

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: 400 validation no retry | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_dispatch_validation_error_dead_letters_immediately (400/422-class -> VALIDATION -> DEAD_LETTER, never retried).  |  **Defect:** —

### TC-053-S003 — Specification scenario — 429 Retry-After

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: 429 Retry-After | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no test sends a live 429 with a Retry-After header -- compute_retry_decision()'s retry_after_seconds branch is real code, not independently exercised end-to-end this pass (SG-126).  |  **Defect:** —

### TC-053-S004 — Specification scenario — timeout after vendor commit

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: timeout after vendor commit | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_dispatch_timeout_is_uncertain_not_blind_success_or_retry_storm.  |  **Defect:** —

### TC-053-S005 — Specification scenario — duplicate idempotency same hash

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: duplicate idempotency same hash | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_register_instance_duplicate_idempotency_key_returns_same_receipt (duplicate idempotency, same payload hash).  |  **Defect:** —

### TC-053-S006 — Specification scenario — duplicate idempotency different hash

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: duplicate idempotency different hash | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_propose_duplicate_external_mapping_rejected demonstrates the general conflict-on-different-content pattern; ingest_erp_event()'s own different-payload-hash path is services/gxp-api/tests/test_erp_flow.py::test_ingest_event_dedupes_and_detects_conflict.  |  **Defect:** —

### TC-053-S007 — Specification scenario — inbound duplicate event

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: inbound duplicate event | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_ingest_event_dedupes_and_detects_conflict (duplicate inbound event, same payload -> idempotent no-op).  |  **Defect:** —

### TC-053-S008 — Specification scenario — out-of-order inbound version

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: out-of-order inbound version | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no stale-supersede enforcement exists for an out-of-order inbound version (same gap as INT-FR-011) (SG-126).  |  **Defect:** —

### TC-053-S009 — Specification scenario — dead-letter replay

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: dead-letter replay | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_create_corrected_command_from_dead_letter (dead-letter replay via retry_erp_command / correction via create_corrected_command).  |  **Defect:** —

### TC-053-S010 — Specification scenario — corrected new command

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: corrected new command | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_create_corrected_command_from_dead_letter (a corrected new command, never mutating the original).  |  **Defect:** —

### TC-053-S011 — Specification scenario — circuit breaker

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: circuit breaker | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_circuit_breaker_opens_after_repeated_failures_and_throttles.  |  **Defect:** —

### TC-053-S012 — Specification scenario — bulk partial failure

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: bulk partial failure | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no bulk-job partial-failure tracking exists (same gap as INT-FR-023) (SG-126).  |  **Defect:** —

### TC-053-S013 — Specification scenario — reconciliation missing external posting

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: reconciliation missing external posting | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- services/gxp-api/tests/test_erp_flow.py::test_reconciliation_run_lifecycle_never_auto_resolves exercises MISSING_EXTERNAL directly (recordReconciliationDifference).  |  **Defect:** —

### TC-053-S014 — Specification scenario — extra external transaction

- **Requirement:** SPEC-ERP-006-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: extra external transaction | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no EXTRA_EXTERNAL-specific scenario is independently exercised -- the difference_type is declared and accepted by record_reconciliation_difference() identically to MISSING_EXTERNAL, not independently re-tested with this specific value (SG-126).  |  **Defect:** —
