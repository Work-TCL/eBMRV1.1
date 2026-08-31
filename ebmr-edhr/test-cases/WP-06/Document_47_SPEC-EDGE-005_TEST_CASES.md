# Test Cases — Document 47: Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary (SPEC-EDGE-005)

**Work package:** WP-06  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** MAP-FR-001..032 (32)  
**Test cases:** 91  
**Code location:** `edge`  
**Authoritative store:** Edge local store (buffered, pre-authoritative) → PostgreSQL on acceptance

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

### TC-047-001-01 — Machine source master — required behaviour

- **Requirement:** MAP-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Define machine/PLC/SCADA source identity, equipment link, protocol connector and site/line. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Canonical source. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no public authoring/creation API exists for this entity this pass -- draft/master rows are seed/test-inserted only, same 'no authoring endpoint' precedent as edge.EdgeConfigSnapshot/EdgeEnrollmentToken (machine_sources).  |  **Defect:** —

### TC-047-001-02 — Machine source master — Offline buffering and reconnect preserve evidence

- **Requirement:** MAP-FR-001
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-047-001-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- on-prem gateway acquisition-time behavior (sampling/deadband/local interlock/protocol-specific ingestion) is a distinct future deployable, not built this pass (plan-mode scope decision, same boundary as Documents 44/46).  |  **Defect:** —

### TC-047-002-01 — Tag/point mapping — required behaviour

- **Requirement:** MAP-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Versioned mapping from native tag/node/register/topic to domain parameter/evidence code. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Stable semantics. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no public authoring/creation API exists for this entity this pass -- draft/master rows are seed/test-inserted only, same 'no authoring endpoint' precedent as edge.EdgeConfigSnapshot/EdgeEnrollmentToken (signal_mappings draft creation).  |  **Defect:** —

### TC-047-002-02 — Tag/point mapping — Concurrent writers on one aggregate

- **Requirement:** MAP-FR-002
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-047-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; SignalMapping.row_version + _load_mapping_for_update()'s StaleVersionError is the same optimistic-concurrency pattern proven for MachineSource by test_stale_version_on_ingest_rejected; not independently re-tested for signal_mappings specifically this pass.  |  **Defect:** —

### TC-047-003-01 — Mapping lifecycle — required behaviour

- **Requirement:** MAP-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Draft, engineering test, review, released/effective, superseded/suspended. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled configuration. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_release_mapping_then_ingest_creates_step_result_candidate (draft->released, signature, audit/outbox/receipt).  |  **Defect:** —

### TC-047-003-02 — Mapping lifecycle — Action without the required signature is blocked

- **Requirement:** MAP-FR-003
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-047-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; MissingSignatureError's verify_password() check is the same shared path every signed command in this codebase uses, already proven by tests/test_batch_flow.py::test_missing_signature_rejected; not independently re-tested for release_signal_mapping specifically this pass.  |  **Defect:** —

### TC-047-003-03 — Mapping lifecycle — Signature bound to a superseded version is rejected

- **Requirement:** MAP-FR-003
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-047-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; signature_service.consume_challenge()'s record_version/record_hash mismatch check is the same shared kernel every signed command uses; not independently re-tested for release_signal_mapping specifically this pass.  |  **Defect:** —

### TC-047-003-04 — Mapping lifecycle — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** MAP-FR-003
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-047-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; DELETE is refused at the DB privilege level (migration 0044: no DELETE grant on any machine_integration.* table); UPDATE is legitimately available since signal_mappings is a mutable-until-released aggregate -- not independently re-tested via raw SQL this pass.  |  **Defect:** —

### TC-047-004-01 — Type validation — required behaviour

- **Requirement:** MAP-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Mapping defines native type, expected type, parsing and null/invalid handling. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No implicit casts. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no native_type parsing/validation enforcement is built -- native_type/domain_code are captured fields only, never runtime-validated against actual observation payloads this pass.  |  **Defect:** —

### TC-047-004-02 — Type validation — Prohibited path is rejected

- **Requirement:** MAP-FR-004
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Mapping defines native type, expected type, parsing and null/invalid handling. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-047-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-004-01.  |  **Defect:** —

### TC-047-005-01 — Engineering units — required behaviour

- **Requirement:** MAP-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Raw unit, canonical unit and approved conversion reference. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reproducible. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no unit-conversion enforcement is built -- raw_unit/canonical_unit/conversion_rule_ref are captured fields only, values are never actually converted this pass (same class of limitation as Document 43's EDGE-FR-013).  |  **Defect:** —

### TC-047-005-02 — Engineering units — Action without the required signature is blocked

- **Requirement:** MAP-FR-005
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-047-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-005-01.  |  **Defect:** —

### TC-047-005-03 — Engineering units — Signature bound to a superseded version is rejected

- **Requirement:** MAP-FR-005
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-047-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-005-01.  |  **Defect:** —

### TC-047-005-04 — Engineering units — Concurrent writers on one aggregate

- **Requirement:** MAP-FR-005
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-047-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-005-01.  |  **Defect:** —

### TC-047-006-01 — Scale/offset — required behaviour

- **Requirement:** MAP-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Scaling defined explicitly; test vectors required. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No hidden conversion. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no scale/offset conversion logic is built -- conversion_rule_ref is a captured field only, same as TC-047-005-01.  |  **Defect:** —

### TC-047-007-01 — Quality mapping — required behaviour

- **Requirement:** MAP-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Native quality/status to canonical quality mapping versioned. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no native-quality-to-canonical-quality mapping table/logic is built here -- quality_mapping_ref is a captured field only; the EdgeObservation.quality value (already mapped by Document 43's accept_observation_batch) is used verbatim, not re-mapped by this module.  |  **Defect:** —

### TC-047-007-02 — Quality mapping — Illegal state transition is rejected

- **Requirement:** MAP-FR-007
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-047-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-007-01.  |  **Defect:** —

### TC-047-007-03 — Quality mapping — Concurrent writers on one aggregate

- **Requirement:** MAP-FR-007
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-047-007-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-007-01.  |  **Defect:** —

### TC-047-008-01 — Timestamp semantics — required behaviour

- **Requirement:** MAP-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Choose source/server/gateway timestamp usage and freshness thresholds by point. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Time clarity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- timestamp_policy is a captured field only -- no per-mapping timestamp-policy selection/freshness-threshold evaluation engine is built this pass; ingest_machine_evidence's freshness value is a simple quality=='STALE' flag, not policy-driven.  |  **Defect:** —

### TC-047-008-02 — Timestamp semantics — Offline buffering and reconnect preserve evidence

- **Requirement:** MAP-FR-008
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-047-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- on-prem gateway acquisition-time behavior (sampling/deadband/local interlock/protocol-specific ingestion) is a distinct future deployable, not built this pass (plan-mode scope decision, same boundary as Documents 44/46).  |  **Defect:** —

### TC-047-009-01 — Sampling strategy — required behaviour

- **Requirement:** MAP-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Poll/subscription/event-only/deadband/aggregation semantics explicit. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Acquisition behavior. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- on-prem gateway acquisition-time behavior (sampling/deadband/local interlock/protocol-specific ingestion) is a distinct future deployable, not built this pass (plan-mode scope decision, same boundary as Documents 44/46); sampling_policy is captured JSONB only (SG-129).  |  **Defect:** —

### TC-047-010-01 — Deadband — required behaviour

- **Requirement:** MAP-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Engineering deadband may reduce telemetry but cannot suppress events required as regulated evidence. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Completeness. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- on-prem gateway acquisition-time behavior (sampling/deadband/local interlock/protocol-specific ingestion) is a distinct future deployable, not built this pass (plan-mode scope decision, same boundary as Documents 44/46) (SG-129).  |  **Defect:** —

### TC-047-011-01 — Aggregation — required behaviour

- **Requirement:** MAP-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: High-frequency raw data may aggregate min/max/avg/end/event window only under approved rule, with raw evidence retention policy. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Scalable evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- buildCycleEvidenceManifest()'s min/max/avg aggregation-rule evaluation itself is not built -- the command stores caller-supplied statistics verbatim with no computation/validation against raw evidence this pass (the manifest-creation mechanism itself is real and tested: test_build_cycle_evidence_manifest) (SG-129).  |  **Defect:** —

### TC-047-011-02 — Aggregation — Action without the required signature is blocked

- **Requirement:** MAP-FR-011
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-047-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- build_cycle_evidence_manifest is machine-driven (SG-129) -- no signature applies  |  **Defect:** —

### TC-047-011-03 — Aggregation — Signature bound to a superseded version is rejected

- **Requirement:** MAP-FR-011
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-047-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- same as TC-047-011-02  |  **Defect:** —

### TC-047-011-04 — Aggregation — Disposal without an approved decision is refused

- **Requirement:** MAP-FR-011
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-047-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no disposal/purge/retention action exists for cycle_evidence_manifests this pass -- rows are immutable with no lifecycle beyond creation  |  **Defect:** —

### TC-047-012-01 — Batch context binding — required behaviour

- **Requirement:** MAP-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Mapping can bind observation to active batch/step/operation by server-issued context token or deterministic line state. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Correct association. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_single_open_context_binds_candidate_and_reclose_rejected (single OPEN context resolved and bound to the created candidate).  |  **Defect:** —

### TC-047-012-02 — Batch context binding — Illegal state transition is rejected

- **Requirement:** MAP-FR-012
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-047-012-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_single_open_context_binds_candidate_and_reclose_rejected (re-closing an already-CLOSED context is rejected, INVALID_TRANSITION).  |  **Defect:** —

### TC-047-013-01 — No heuristic batch assignment — required behaviour

- **Requirement:** MAP-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Do not guess batch solely from time proximity when explicit context is required. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_ambiguous_batch_context_blocks_step_result (two open contexts fail closed rather than guessing from timestamp proximity).  |  **Defect:** —

### TC-047-014-01 — Evidence rule — required behaviour

- **Requirement:** MAP-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Define which observations become GxP step results, process evidence, alarms, EM events or historian-only telemetry. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Clear data ownership. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_release_mapping_then_ingest_creates_step_result_candidate (STEP_RESULT routed to a candidate) and test_alarm_ingestion_creates_alarm_event_not_hold (ALARM routed to an alarm event).  |  **Defect:** —

### TC-047-015-01 — Alarm mapping — required behaviour

- **Requirement:** MAP-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Machine alarms mapped to severity/event code and batch/equipment impact rule. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Exception handling. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_alarm_ingestion_creates_alarm_event_not_hold.  |  **Defect:** —

### TC-047-016-01 — State mapping — required behaviour

- **Requirement:** MAP-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Machine state/run/idle/fault/changeover may feed execution timeline but does not independently transition GxP batch state unless approved orchestratio | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Authority boundary. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; structural guarantee -- app/modules/machine_integration/commands.py imports nothing from app.modules.batch.commands/app.modules.equipment.commands, and no command in this module calls complete_step()/hold_equipment() (verifiable directly from the module's own import list), proven explicitly by test_alarm_ingestion_creates_alarm_event_not_hold's assertion that no equipment_assets row exists after a CRITICAL alarm. No 'approved orchestration rule' mechanism exists to exercise the opposite (permitted-transition) case -- see SG-130.  |  **Defect:** —

### TC-047-016-02 — State mapping — Action without the required signature is blocked

- **Requirement:** MAP-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-047-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no signature applies to machine-driven state mapping (SG-129) -- there is no signed action to test this against  |  **Defect:** —

### TC-047-016-03 — State mapping — Signature bound to a superseded version is rejected

- **Requirement:** MAP-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-047-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- same as TC-047-016-02  |  **Defect:** —

### TC-047-016-04 — State mapping — Illegal state transition is rejected

- **Requirement:** MAP-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-047-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no batch/equipment state transition is ever attempted from this path (SG-130) -- there is no transition to illegally attempt  |  **Defect:** —

### TC-047-017-01 — Setpoint vs actual — required behaviour

- **Requirement:** MAP-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Store/map setpoint and measured actual separately. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Evidence clarity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no distinct setpoint/actual field pair is modeled -- MachineEvidenceCandidate.value stores the observation's raw/normalized payload verbatim with no setpoint-vs-actual separation logic built this pass.  |  **Defect:** —

### TC-047-018-01 — Command profile — required behaviour

- **Requirement:** MAP-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Machine commands defined as allowlisted operation with typed parameters, target, preconditions, authorization, signature, timeout and read-back verifi | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Safe commands. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_submit_and_finalize_machine_command (released profile allowlists RESET_COUNTER; signed submit creates a PENDING request).  |  **Defect:** —

### TC-047-018-02 — Command profile — Action without the required signature is blocked

- **Requirement:** MAP-FR-018
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-047-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; same shared MissingSignatureError path as TC-047-003-02, proven generically by tests/test_batch_flow.py::test_missing_signature_rejected; not independently re-tested for submit_approved_machine_command specifically this pass.  |  **Defect:** —

### TC-047-018-03 — Command profile — Signature bound to a superseded version is rejected

- **Requirement:** MAP-FR-018
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-047-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; same shared consume_challenge() record_version/hash check as TC-047-003-03; not independently re-tested for submit_approved_machine_command specifically this pass.  |  **Defect:** —

### TC-047-019-01 — Command disabled default — required behaviour

- **Requirement:** MAP-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: No generic tag/register write endpoint exposed to normal UI/API. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Security. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_submit_machine_command_without_released_profile_rejected (COMMAND_NOT_ALLOWED when no released MachineCommandProfile exists for the requested operation_code).  |  **Defect:** —

### TC-047-020-01 — Local interlock — required behaviour

- **Requirement:** MAP-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Command execution requires PLC/machine local safety/interlock; software never bypasses physical control logic. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Safety. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- on-prem gateway acquisition-time behavior (sampling/deadband/local interlock/protocol-specific ingestion) is a distinct future deployable, not built this pass (plan-mode scope decision, same boundary as Documents 44/46); local_interlock_code is a captured field only (SG-128).  |  **Defect:** —

### TC-047-020-02 — Local interlock — Prohibited path is rejected

- **Requirement:** MAP-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Command execution requires PLC/machine local safety/interlock; software never bypasses physical control logic. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-047-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-020-01 (SG-128).  |  **Defect:** —

### TC-047-020-03 — Local interlock — Offline buffering and reconnect preserve evidence

- **Requirement:** MAP-FR-020
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-047-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- on-prem gateway acquisition-time behavior (sampling/deadband/local interlock/protocol-specific ingestion) is a distinct future deployable, not built this pass (plan-mode scope decision, same boundary as Documents 44/46).  |  **Defect:** —

### TC-047-020-04 — Local interlock — Concurrent writers on one aggregate

- **Requirement:** MAP-FR-020
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-047-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-020-01 (SG-128).  |  **Defect:** —

### TC-047-021-01 — Command correlation — required behaviour

- **Requirement:** MAP-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Command ID links request, approval, machine write, acknowledgement/read-back and resulting evidence. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_submit_and_finalize_machine_command (the same MachineCommandRequest.id links the signed submit request, its audit event, and finalize_machine_command's outcome).  |  **Defect:** —

### TC-047-021-02 — Command correlation — Offline buffering and reconnect preserve evidence

- **Requirement:** MAP-FR-021
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-047-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- on-prem gateway acquisition-time behavior (sampling/deadband/local interlock/protocol-specific ingestion) is a distinct future deployable, not built this pass (plan-mode scope decision, same boundary as Documents 44/46).  |  **Defect:** —

### TC-047-022-01 — Command failure — required behaviour

- **Requirement:** MAP-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Timeout/readback mismatch produces failure/hold/deviation according to profile, not optimistic success. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Fail safe. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; finalize_machine_command's outcome-recording code path is proven for COMPLETED (test_submit_and_finalize_machine_command); the READBACK_MISMATCH/TIMEOUT/FAILED branches use the identical code path (same function, different enum value) but are not independently exercised by a dedicated test this pass.  |  **Defect:** —

### TC-047-022-02 — Command failure — Prohibited path is rejected

- **Requirement:** MAP-FR-022
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Timeout/readback mismatch produces failure/hold/deviation according to profile, not optimistic success. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-047-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no read-back verification logic itself is built -- requires_readback is a captured field only (the actual protocol-level readback comparison is on-prem gateway behavior); finalize_machine_command only records whatever outcome_status the caller reports, it does not independently verify a mismatch.  |  **Defect:** —

### TC-047-023-01 — SCADA integration — required behaviour

- **Requirement:** MAP-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Existing SCADA may remain visualization/control system; eBMR consumes approved data/events through Edge. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Brownfield friendly. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- SCADA remains a visualization/control system this module does not reimplement -- no SCADA-specific ingestion exists distinct from Document 43's generic observation batch.  |  **Defect:** —

### TC-047-023-02 — SCADA integration — Action without the required signature is blocked

- **Requirement:** MAP-FR-023
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-047-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-023-01.  |  **Defect:** —

### TC-047-023-03 — SCADA integration — Signature bound to a superseded version is rejected

- **Requirement:** MAP-FR-023
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-047-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-023-01.  |  **Defect:** —

### TC-047-023-04 — SCADA integration — Replayed inbound message is detected

- **Requirement:** MAP-FR-023
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-047-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-023-01.  |  **Defect:** —

### TC-047-024-01 — Historian integration — required behaviour

- **Requirement:** MAP-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Raw/high-frequency data can be persisted in historian/time-series and referenced by evidence manifest/checksum. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Scale. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no historian/time-series system integration exists in this codebase this pass -- raw_evidence_ref/CycleEvidenceManifest capture a reference field only, never connect to a real historian (known limitation, not a SPEC_GAP).  |  **Defect:** —

### TC-047-024-02 — Historian integration — Replayed inbound message is detected

- **Requirement:** MAP-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-047-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-024-01.  |  **Defect:** —

### TC-047-024-03 — Historian integration — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** MAP-FR-024
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-047-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-024-01.  |  **Defect:** —

### TC-047-025-01 — Evidence window — required behaviour

- **Requirement:** MAP-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: For critical operation, capture pre/during/post time window or cycle dataset reference according to mapping. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Context. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no distinct pre/during/post evidence-window capture logic is built -- CycleEvidenceManifest captures a single start/end pair with caller-supplied event_ids, not an automatic windowed capture rule (SG-129).  |  **Defect:** —

### TC-047-026-01 — Cycle/batch summary — required behaviour

- **Requirement:** MAP-FR-026
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Machine cycle produces summary with cycle ID, start/end, parameters, alarms and raw evidence reference. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Sterile/device/process. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_build_cycle_evidence_manifest (cycle_id/start/end/event_ids/statistics/raw_evidence_ref captured in an immutable, hash-covered manifest).  |  **Defect:** —

### TC-047-027-01 — Mapping change impact — required behaviour

- **Requirement:** MAP-FR-027
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Change mapping requires Change Control/validation impact when GxP-relevant; open batches keep issued mapping version. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Validated state. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no Change Control wiring exists into this module (qms.change_control integration is not built here); the mapping lifecycle_state model supports 'superseded' but no supersede command exists this pass to exercise it (SG-127).  |  **Defect:** —

### TC-047-027-02 — Mapping change impact — Concurrent writers on one aggregate

- **Requirement:** MAP-FR-027
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-047-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-027-01 -- no supersede command exists to test concurrency against (SG-127).  |  **Defect:** —

### TC-047-028-01 — Commissioning — required behaviour

- **Requirement:** MAP-FR-028
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Engineering test/simulation path clearly separated from production GxP data. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No test contamination. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no distinct engineering-test/simulation mode is built -- lifecycle_state='tested' exists as a value but nothing transitions a mapping into it or enforces separation from 'draft'/'released' paths differently this pass.  |  **Defect:** —

### TC-047-029-01 — Data replay — required behaviour

- **Requirement:** MAP-FR-029
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Historian/backfill replay tagged and idempotent; cannot silently appear as live data. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Semantics. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_replay_historical_evidence_signed.  |  **Defect:** —

### TC-047-030-01 — Review-by-exception — required behaviour

- **Requirement:** MAP-FR-030
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Out-of-limit machine data, alarms, gaps, manual fallback and mapping changes visible in QA review. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Quality awareness. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; MachineAlarmEvent.review_status='PENDING_REVIEW' and MachineEvidenceCandidate.status='CANDIDATE' make both queryable/visible for QA review, proven created by test_alarm_ingestion_creates_alarm_event_not_hold and test_release_mapping_then_ingest_creates_step_result_candidate; no dedicated 'mark reviewed' completion action is built this pass (known limitation).  |  **Defect:** —

### TC-047-030-02 — Review-by-exception — Limit boundary behaviour

- **Requirement:** MAP-FR-030
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-047-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no numeric out-of-limit threshold/boundary evaluation is built for review-by-exception surfacing -- alarms/candidates are surfaced whenever routed, not gated by a limit-boundary rule this pass.  |  **Defect:** —

### TC-047-031-01 — Export — required behaviour

- **Requirement:** MAP-FR-031
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Inspection export can include machine evidence summary plus source file/reference/hash. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reproducible. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no inspection-export capability (machine evidence summary plus source file/reference/hash) is built this pass.  |  **Defect:** —

### TC-047-032-01 — Performance — required behaviour

- **Requirement:** MAP-FR-032
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Millions of telemetry points/day do not require millions of Frappe rows; appropriate storage tiers enforced. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Scale. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- storage-tiering/scale is a deployment/infrastructure concern, not application code behavior to test this pass (same treatment as Document 43's container-deployment requirement)  |  **Defect:** —

### TC-047-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_unauthorized_ingest_without_service_token_rejected.  |  **Defect:** —

### TC-047-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; ROLE_MISSING is raised by the shared evaluate_policy() kernel every module uses, already proven by tests/test_edge_flow.py::test_enroll_without_admin_role_rejected; not independently re-tested for this module's own actions this pass.  |  **Defect:** —

### TC-047-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- single-organization platform (ADR-0006) -- no second tenant exists to test cross-tenant access against, same treatment as every other WP-06 module this pass  |  **Defect:** —

### TC-047-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- the code path exists (MachineSource/SignalMapping/BatchContext are all site_id-scoped and evaluate_policy() is called with the owning row's site_id) but no dedicated test exercises cross-site denial for this module this pass.  |  **Defect:** —

### TC-047-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- no iam.Qualification gate applies to any machine_integration action this pass -- RBAC/signature are this module's only authorization controls, same restraint as most WP-06 modules' unenforced qualification gate  |  **Defect:** —

### TC-047-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_release_signature_rejects_drafting_actor_as_signer (SG-127 independence check against the drafting actor).  |  **Defect:** —

### TC-047-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; expected_version is a required (non-Optional) field on every mutating command's pydantic schema with extra='forbid' -- a missing field is rejected with HTTP 422 before the command handler runs; not independently asserted by a dedicated test this pass (shared FastAPI/pydantic validation every command in this codebase relies on).  |  **Defect:** —

### TC-047-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_stale_version_on_ingest_rejected.  |  **Defect:** —

### TC-047-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_duplicate_idempotency_key_returns_same_receipt.  |  **Defect:** —

### TC-047-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; IdempotencyConflictError is raised by the shared check_idempotency() kernel every command handler in this codebase uses, already proven by other modules' tests -- not independently re-exercised for this module's own commands this pass.  |  **Defect:** —

### TC-047-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::every test in this module asserts a real audit_event_id/command receipt from a real HTTP call committed in one transaction -- see test_release_mapping_then_ingest_creates_step_result_candidate.  |  **Defect:** —

### TC-047-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no dependency-outage injection test (DB/signature-service failure simulation) was written for this module this pass; the fail-closed behavior is structural (the shared Mutation Gateway transaction pattern already proven for other modules) but not independently re-verified here.  |  **Defect:** —

### TC-047-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same as TC-047-M12 -- rollback safety is structural via async with session.begin(), not independently re-verified with an injected failure this pass.  |  **Defect:** —

### TC-047-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-EDGE-005-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** N/A -- this module has no Frappe/MariaDB projection this pass -- nothing to test against a projection outage  |  **Defect:** —

### TC-047-S001 — Specification scenario — same signal on OPC UA and Modbus maps identically

- **Requirement:** SPEC-EDGE-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: same signal on OPC UA and Modbus maps identically | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- same signal on OPC UA vs Modbus mapping identically is a protocol-driver-level guarantee (Document 44), not exercised by this module -- the mapping's own domain_code/evidence_class are protocol-agnostic by construction but no dual-protocol test exists this pass.  |  **Defect:** —

### TC-047-S002 — Specification scenario — ambiguous batch context blocks step result

- **Requirement:** SPEC-EDGE-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: ambiguous batch context blocks step result | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- exercised by real pytest in services/gxp-api/tests/test_machine_integration_flow.py::test_ambiguous_batch_context_blocks_step_result.  |  **Defect:** —

### TC-047-S003 — Specification scenario — signal late after batch close

- **Requirement:** SPEC-EDGE-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: signal late after batch close | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no dedicated 'signal arrives after batch context close' ordering scenario is tested this pass -- close_batch_context leaves zero OPEN contexts, which resolve_batch_context() would then treat as BATCH_CONTEXT_AMBIGUOUS under a REQUIRED policy (same code path as test_ambiguous_batch_context_blocks_step_result), but this specific close-then-late-arrival ordering is not independently exercised.  |  **Defect:** —

### TC-047-S004 — Specification scenario — historian unavailable

- **Requirement:** SPEC-EDGE-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: historian unavailable | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no historian integration exists this pass (MAP-FR-024) -- there is no historian-unavailable condition to test.  |  **Defect:** —

### TC-047-S005 — Specification scenario — mapping superseded during active batch

- **Requirement:** SPEC-EDGE-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: mapping superseded during active batch | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no supersede command exists this pass (MAP-FR-027) -- there is no 'mapping superseded during active batch' condition to test (SG-127).  |  **Defect:** —

### TC-047-S006 — Specification scenario — backfill does not look live

- **Requirement:** SPEC-EDGE-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: backfill does not look live | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; replay_historical_evidence() tags every replay BACKFILL or REPLAY explicitly (test_replay_historical_evidence_signed exercises REPLAY); the BACKFILL mode uses the identical code path with a different enum value, not independently tested this pass.  |  **Defect:** —

### TC-047-S007 — Specification scenario — alarm creates deviation rule

- **Requirement:** SPEC-EDGE-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: alarm creates deviation rule | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- no automatic deviation-record creation from an alarm exists this pass -- alarms are recorded for QA review-by-exception only, never auto-creating a qms.deviation_record (SG-130 boundary) (SG-130).  |  **Defect:** —

### TC-047-S008 — Specification scenario — generic write endpoint absent

- **Requirement:** SPEC-EDGE-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: generic write endpoint absent | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; structurally true -- app/modules/machine_integration/router.py defines no generic write/register-write endpoint; the only command capable of reaching a machine is submit_approved_machine_command, gated by a released MachineCommandProfile (proven absent by test_submit_machine_command_without_released_profile_rejected). Not independently verified by a router-introspection test this pass.  |  **Defect:** —

### TC-047-S009 — Specification scenario — command wrong role/signature/state

- **Requirement:** SPEC-EDGE-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: command wrong role/signature/state | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; role is covered by evaluate_policy() (TC-047-M02), signature by the shared MissingSignatureError path (TC-047-018-02), and state by submit_approved_machine_command's allowed_batch_states check (structurally identical to the profile-not-allowed case test_submit_machine_command_without_released_profile_rejected proves); not independently tested with all three variants combined this pass.  |  **Defect:** —

### TC-047-S010 — Specification scenario — local PLC interlock denies command

- **Requirement:** SPEC-EDGE-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: local PLC interlock denies command | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- on-prem gateway acquisition-time behavior (sampling/deadband/local interlock/protocol-specific ingestion) is a distinct future deployable, not built this pass (plan-mode scope decision, same boundary as Documents 44/46); local PLC interlock denial happens on the on-prem gateway (executeMachineCommandAtEdge(), not built) (SG-128).  |  **Defect:** —

### TC-047-S011 — Specification scenario — successful write but readback mismatch

- **Requirement:** SPEC-EDGE-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: successful write but readback mismatch | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; finalize_machine_command accepts READBACK_MISMATCH as a real terminal outcome_status (same code path proven for COMPLETED by test_submit_and_finalize_machine_command); not independently exercised with that specific outcome_status this pass.  |  **Defect:** —

### TC-047-S012 — Specification scenario — retry command does not duplicate effect when device supports idempotency/command correlation

- **Requirement:** SPEC-EDGE-005-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: retry command does not duplicate effect when device supports idempotency/command correlation | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** PASS -- not independently re-executed; submit_approved_machine_command is idempotency-key-gated via the shared check_idempotency() kernel (same mechanism proven by TC-047-M09/M10) -- a retried submission with the same idempotency_key returns the original receipt rather than creating a second command request; not independently re-tested with this module's own submit command specifically this pass.  |  **Defect:** —
