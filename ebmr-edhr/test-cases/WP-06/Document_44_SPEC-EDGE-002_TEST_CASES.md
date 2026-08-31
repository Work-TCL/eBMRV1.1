# Test Cases — Document 44: Industrial Device & Protocol Connectivity / Driver Specification (SPEC-EDGE-002)

**Work package:** WP-06  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** DRV-FR-001..025 (25)  
**Test cases:** 70  
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

### TC-044-001-01 — Driver interface — required behaviour

- **Requirement:** DRV-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: All protocol plugins implement common lifecycle/connect/read/subscribe/write-capability/health contract. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Uniform runtime. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-002-01 — OPC UA endpoint — required behaviour

- **Requirement:** DRV-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support endpoint discovery/configured URL, security policy/mode, certificate trust and user/application authentication. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Secure OPC UA. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-003-01 — OPC UA certificates — required behaviour

- **Requirement:** DRV-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Application instance certificate and trusted/rejected certificate stores managed explicitly. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Identity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-003-02 — OPC UA certificates — Prohibited path is rejected

- **Requirement:** DRV-FR-003
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Application instance certificate and trusted/rejected certificate stores managed explicitly. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `PAYLOAD_SCHEMA_INVALID`
- **Depends on:** TC-044-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-004-01 — OPC UA browse — required behaviour

- **Requirement:** DRV-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Authorized engineering mode may browse namespaces/nodes for mapping; production mapping references exact NodeIds. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Stable mapping. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-005-01 — OPC UA subscriptions — required behaviour

- **Requirement:** DRV-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support monitored items, sampling/publishing interval, queue size and reconnect/resubscribe. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Efficient acquisition. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-006-01 — OPC UA status — required behaviour

- **Requirement:** DRV-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Map UA StatusCode/source/server timestamps into canonical quality/time fields. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Quality preserved. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-006-02 — OPC UA status — Illegal state transition is rejected

- **Requirement:** DRV-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-044-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-007-01 — Modbus TCP — required behaviour

- **Requirement:** DRV-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support host/unit ID/function/register/type/endianness/scaling with bounded polling. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Common industrial. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-008-01 — Modbus RTU — required behaviour

- **Requirement:** DRV-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support serial port/baud/parity/stop bits/slave ID/register mapping and bus serialization. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Serial support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-009-01 — Modbus invalid value — required behaviour

- **Requirement:** DRV-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Timeout/CRC/exception/out-of-range marks BAD/COMM_ERROR; never substitute last good as current without STALE quality. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-009-02 — Modbus invalid value — Prohibited path is rejected

- **Requirement:** DRV-FR-009
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Timeout/CRC/exception/out-of-range marks BAD/COMM_ERROR; never substitute last good as current without STALE quality. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `PAYLOAD_SCHEMA_INVALID`
- **Depends on:** TC-044-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-010-01 — MQTT 5 — required behaviour

- **Requirement:** DRV-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support broker TLS/auth, topic filters, QoS policy, retained flag handling, payload schema/version and client session policy. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Message source. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-010-02 — MQTT 5 — Concurrent writers on one aggregate

- **Requirement:** DRV-FR-010
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-044-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-011-01 — MQTT payload validation — required behaviour

- **Requirement:** DRV-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: JSON/binary/custom payload decoded only through versioned decoder plugin/schema. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No arbitrary parsing. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-011-02 — MQTT payload validation — Concurrent writers on one aggregate

- **Requirement:** DRV-FR-011
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-044-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-012-01 — SNMP — required behaviour

- **Requirement:** DRV-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support v3 preferred with scoped credentials, OID mapping and polling/trap profile where appropriate. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Utilities/UPS. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-013-01 — Generic TCP/serial — required behaviour

- **Requirement:** DRV-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Custom proprietary protocol lives in isolated adapter with framing/checksum/test vectors. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Extensibility. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-013-02 — Generic TCP/serial — Replayed inbound message is detected

- **Requirement:** DRV-FR-013
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-044-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-013-03 — Generic TCP/serial — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** DRV-FR-013
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-044-013-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-014-01 — REST/file adapter — required behaviour

- **Requirement:** DRV-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Support authenticated REST polling/webhook or controlled file import for instruments producing reports. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Instrument integration. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-014-02 — REST/file adapter — Replayed inbound message is detected

- **Requirement:** DRV-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-044-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-014-03 — REST/file adapter — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** DRV-FR-014
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-044-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-015-01 — Connection retry — required behaviour

- **Requirement:** DRV-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Exponential backoff/jitter with configured max and health state; avoid network storms. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Resilience. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-015-02 — Connection retry — Illegal state transition is rejected

- **Requirement:** DRV-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-044-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-016-01 — Source rate limits — required behaviour

- **Requirement:** DRV-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Per-device poll/subscription limits prevent overloading PLC/instrument. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Operational safety. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-016-02 — Source rate limits — Prohibited path is rejected

- **Requirement:** DRV-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Per-device poll/subscription limits prevent overloading PLC/instrument. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `PAYLOAD_SCHEMA_INVALID`
- **Depends on:** TC-044-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-016-03 — Source rate limits — Limit boundary behaviour

- **Requirement:** DRV-FR-016
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-044-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-016-04 — Source rate limits — Offline buffering and reconnect preserve evidence

- **Requirement:** DRV-FR-016
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-044-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-017-01 — Read/write separation — required behaviour

- **Requirement:** DRV-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Driver advertises read/write capability separately; runtime blocks write unless explicit command profile. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Safe default. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-017-02 — Read/write separation — Prohibited path is rejected

- **Requirement:** DRV-FR-017
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Driver advertises read/write capability separately; runtime blocks write unless explicit command profile. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `PAYLOAD_SCHEMA_INVALID`
- **Depends on:** TC-044-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-017-03 — Read/write separation — Concurrent writers on one aggregate

- **Requirement:** DRV-FR-017
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-044-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-018-01 — Mapping test — required behaviour

- **Requirement:** DRV-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Engineering test reads source and displays raw/normalized preview without committing regulated result. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Safe commissioning. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-019-01 — Simulation — required behaviour

- **Requirement:** DRV-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Provide deterministic simulator/mock driver for CI/validation. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Testability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-020-01 — Driver version — required behaviour

- **Requirement:** DRV-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Every observation carries driver/plugin version. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reproducibility. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-020-02 — Driver version — Concurrent writers on one aggregate

- **Requirement:** DRV-FR-020
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-044-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-021-01 — Reconnect sequence — required behaviour

- **Requirement:** DRV-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: After reconnect, driver resubscribes/restarts polling and emits gap/reconnect event. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Data-gap awareness. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-022-01 — Credential rotation — required behaviour

- **Requirement:** DRV-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Connector secrets/certs can rotate without rewriting mapping. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Security. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-023-01 — Driver health — required behaviour

- **Requirement:** DRV-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Connection state, last success, error count, latency and source-specific diagnostics. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Observability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-023-02 — Driver health — Illegal state transition is rejected

- **Requirement:** DRV-FR-023
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-044-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-024-01 — Protocol errors — required behaviour

- **Requirement:** DRV-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Native errors normalized to stable driver error taxonomy while raw diagnostic retained. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-025-01 — Production configuration — required behaviour

- **Requirement:** DRV-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Protocol mapping config released/versioned; ad-hoc runtime node/register edits prohibited. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Validated state. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-025-02 — Production configuration — Action without the required signature is blocked

- **Requirement:** DRV-FR-025
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-044-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-025-03 — Production configuration — Signature bound to a superseded version is rejected

- **Requirement:** DRV-FR-025
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-044-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-025-04 — Production configuration — Concurrent writers on one aggregate

- **Requirement:** DRV-FR-025
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-044-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-EDGE-002-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-S001 — Specification scenario — connect/auth failure

- **Requirement:** SPEC-EDGE-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: connect/auth failure | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-S002 — Specification scenario — malformed configuration

- **Requirement:** SPEC-EDGE-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: malformed configuration | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-S003 — Specification scenario — read timeout

- **Requirement:** SPEC-EDGE-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: read timeout | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-S004 — Specification scenario — reconnect

- **Requirement:** SPEC-EDGE-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: reconnect | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-S005 — Specification scenario — bad native quality

- **Requirement:** SPEC-EDGE-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: bad native quality | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-S006 — Specification scenario — mapping conversion

- **Requirement:** SPEC-EDGE-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: mapping conversion | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-S007 — Specification scenario — duplicate/replayed source event where detectable

- **Requirement:** SPEC-EDGE-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: duplicate/replayed source event where detectable | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-S008 — Specification scenario — graceful shutdown

- **Requirement:** SPEC-EDGE-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: graceful shutdown | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-S009 — Specification scenario — secret redaction

- **Requirement:** SPEC-EDGE-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: secret redaction | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-S010 — Specification scenario — driver crash isolation

- **Requirement:** SPEC-EDGE-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: driver crash isolation | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —

### TC-044-S011 — Specification scenario — protocol simulator test

- **Requirement:** SPEC-EDGE-002-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: protocol simulator test | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** BLOCKED  |  **Executed by:** claude-code  |  **Date:** 2026-08-26  |  **Actual result:** BLOCKED -- Document 44 (SPEC-EDGE-002) is the on-prem gateway runtime's protocol driver layer (OPC UA/Modbus/MQTT/SNMP/serial/REST-file client drivers and the EdgeDriver plugin interface) -- entirely on the gateway side of the Document 43 server/on-prem boundary. Per that session's plan-mode sign-off (app/modules/edge/models.py module docstring), the on-prem gateway runtime is a distinct future deployable, not built this pass; confirmed against Document 44's full text, not assumed from its title. No server-side code exists to execute this case against; recorded as a resolved scope decision in status/build-status.json, not a SPEC_GAP.  |  **Defect:** —
