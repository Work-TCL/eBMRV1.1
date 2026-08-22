# Test Cases — Document 60: Combination-Product Postmarket Regulatory Coordination, Information Sharing & Regulatory Calendar (SPEC-PM-003)

**Work package:** WP-09  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** PMO-FR-001..032 (32)  
**Test cases:** 87  
**Code location:** `services/gxp-api/src/modules/postmarket`  
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

### TC-060-001-01 — Applicant-role master — required behaviour

- **Requirement:** PMO-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Model combination-product applicant, constituent-part applicants, application numbers/types, addresses, contacts and effective relationship dates. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Part 4 context. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-002-01 — Product/applicant mapping — required behaviour

- **Requirement:** PMO-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Each marketed DDCP product version maps relevant applicant relationships and constituent/application roles. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Correct recipient/rules. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-002-02 — Product/applicant mapping — Concurrent writers on one aggregate

- **Requirement:** PMO-FR-002
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-060-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-003-01 — Part 4 sharing trigger — required behaviour

- **Requirement:** PMO-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Qualifying safety information can create information-sharing assessment/task when rule applies. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** §4.103 support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-004-01 — 5-calendar-day sharing clock — required behaviour

- **Requirement:** PMO-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Calculate no-later-than 5 calendar days from applicable applicant receipt date for §4.103 sharing. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Timeliness. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-004-02 — 5-calendar-day sharing clock — Limit boundary behaviour

- **Requirement:** PMO-FR-004
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-060-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-004-03 — 5-calendar-day sharing clock — Concurrent writers on one aggregate

- **Requirement:** PMO-FR-004
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-060-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-005-01 — Immutable sharing package — required behaviour

- **Requirement:** PMO-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Freeze exact information shared and provenance; later corrections/follow-up create new package/version. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Recordkeeping. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-005-02 — Immutable sharing package — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** PMO-FR-005
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-060-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-005-03 — Immutable sharing package — Concurrent writers on one aggregate

- **Requirement:** PMO-FR-005
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-060-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-006-01 — Recipient evidence — required behaviour

- **Requirement:** PMO-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Record recipient applicant name/address/contact/channel and relationship version. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** §4.103 record. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-006-02 — Recipient evidence — Concurrent writers on one aggregate

- **Requirement:** PMO-FR-006
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-060-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-007-01 — Sharing evidence — required behaviour

- **Requirement:** PMO-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Record company receipt date, sharing date/time, package hash, sender and delivery/ack evidence when available. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Proof. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-008-01 — Sharing escalation — required behaviour

- **Requirement:** PMO-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Due-soon/failed constituent sharing escalates to Regulatory management. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Compliance operations. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-008-02 — Sharing escalation — Prohibited path is rejected

- **Requirement:** PMO-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Due-soon/failed constituent sharing escalates to Regulatory management. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `FDA_REQUEST_DUE_DATE_REQUIRED`
- **Depends on:** TC-060-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-009-01 — Correction/removal assessment — required behaviour

- **Requirement:** PMO-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Document 36 Field Action creates linked Part 806 correction/removal assessment; do not duplicate action scope/communications. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Device postmarket. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-010-01 — 806 10-working-day clock — required behaviour

- **Requirement:** PMO-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: If reportable under configured §806.10 rule, calculate 10 working days from initiation. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Timely reporting. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-010-02 — 806 10-working-day clock — Limit boundary behaviour

- **Requirement:** PMO-FR-010
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-060-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-010-03 — 806 10-working-day clock — Concurrent writers on one aggregate

- **Requirement:** PMO-FR-010
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-060-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-011-01 — 806 nonreportable record — required behaviour

- **Requirement:** PMO-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: If not reportable, create controlled §806.20 record with required source/action facts and retention. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Recordkeeping. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-011-02 — 806 nonreportable record — Disposal without an approved decision is refused

- **Requirement:** PMO-FR-011
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-060-011-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-012-01 — Scope extension amendment — required behaviour

- **Requirement:** PMO-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Field-action expansion to additional lots/batches creates amendment assessment/task where required. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Dynamic action. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-013-01 — Field Alert candidate — required behaviour

- **Requirement:** PMO-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Distributed drug-product quality issue from Complaint/Deviation/OOS/Field Action can create NDA Field Alert assessment. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** 314.81 linkage. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-014-01 — Field Alert 3-working-day clock — required behaviour

- **Requirement:** PMO-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: When applicable, calculate 3 working days from applicant receipt of qualifying information. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Timeliness. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-014-02 — Field Alert 3-working-day clock — Limit boundary behaviour

- **Requirement:** PMO-FR-014
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-060-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-014-03 — Field Alert 3-working-day clock — Concurrent writers on one aggregate

- **Requirement:** PMO-FR-014
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-060-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-015-01 — Field Alert evidence — required behaviour

- **Requirement:** PMO-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Link distributed batches, issue type, facility, specifications/contamination/mix-up facts and submission/rapid-communication evidence. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Traceability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-015-02 — Field Alert evidence — Limit boundary behaviour

- **Requirement:** PMO-FR-015
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-060-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-016-01 — BPDR candidate — required behaviour

- **Requirement:** PMO-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Biologic/product deviation can create BPDR assessment/report task where applicable. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Biologic postmarket. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-017-01 — Periodic schedule — required behaviour

- **Requirement:** PMO-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Maintain quarterly/annual or FDA-configured periodic safety reporting cycles by application/profile. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Calendar. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-018-01 — Periodic dataset freeze — required behaviour

- **Requirement:** PMO-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Use Document 58 immutable interval/cutoff dataset; preserve source versions and inclusion rules. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Reproducible report. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-018-02 — Periodic dataset freeze — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** PMO-FR-018
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-060-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-018-03 — Periodic dataset freeze — Concurrent writers on one aggregate

- **Requirement:** PMO-FR-018
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-060-018-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-019-01 — Part 4 periodic augmentation — required behaviour

- **Requirement:** PMO-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: For applicable NDA/ANDA/BLA combination products containing a device constituent, include required summary/analysis of applicable device reports for i | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Part 4. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-019-02 — Part 4 periodic augmentation — Offline buffering and reconnect preserve evidence

- **Requirement:** PMO-FR-019
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-060-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-020-01 — FDA information request — required behaviour

- **Requirement:** PMO-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Written FDA request creates task with request reference, reason/purpose, requested events/information and agency due date. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Agency response. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-021-01 — Regulatory correspondence — required behaviour

- **Requirement:** PMO-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Store incoming/outgoing correspondence, agency/center, submission/reference numbers, due dates and owner. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-022-01 — Unified regulatory calendar — required behaviour

- **Requirement:** PMO-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Show expedited reports, sharing, 806, Field Alerts, BPDR, periodic reports, agency requests and commitments. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Operations. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-023-01 — Deadline source/basis — required behaviour

- **Requirement:** PMO-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Every obligation stores rule/citation/agency-letter source, clock start, original/current due date and calendar profile. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Explainable. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-023-02 — Deadline source/basis — Concurrent writers on one aggregate

- **Requirement:** PMO-FR-023
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-060-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-024-01 — Deadline override — required behaviour

- **Requirement:** PMO-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Agency-granted alternate schedule/extension can change current due date only with evidence, authority and preserved original deadline. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled override. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-025-01 — Longest-applicable retention — required behaviour

- **Requirement:** PMO-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Combination-product postmarket records use configured longest applicable reporting recordkeeping period. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** §4.105 support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-025-02 — Longest-applicable retention — Disposal without an approved decision is refused

- **Requirement:** PMO-FR-025
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-060-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-026-01 — Retention basis — required behaviour

- **Requirement:** PMO-FR-026
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Store all applicable regimes, rule versions, calculated durations/triggers and selected longest rule. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Transparent retention. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-026-02 — Retention basis — Limit boundary behaviour

- **Requirement:** PMO-FR-026
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-060-026-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-026-03 — Retention basis — Disposal without an approved decision is refused

- **Requirement:** PMO-FR-026
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-060-026-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-026-04 — Retention basis — Concurrent writers on one aggregate

- **Requirement:** PMO-FR-026
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-060-026-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-027-01 — No retrospective shortening — required behaviour

- **Requirement:** PMO-FR-027
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Later profile/rule change cannot silently shorten retention of existing records. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Durability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-027-02 — No retrospective shortening — Disposal without an approved decision is refused

- **Requirement:** PMO-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-060-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-028-01 — Legal/regulatory hold — required behaviour

- **Requirement:** PMO-FR-028
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Authorized hold suspends normal purge/destruction and preserves reason/scope. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Governance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-028-02 — Legal/regulatory hold — Disposal without an approved decision is refused

- **Requirement:** PMO-FR-028
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-060-028-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-029-01 — Submission linkage — required behaviour

- **Requirement:** PMO-FR-029
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Obligations reference Document 59 regulatory report/submission or controlled manual evidence; no duplicate submitted-payload store. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Single submission truth. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-030-01 — Field-action linkage — required behaviour

- **Requirement:** PMO-FR-030
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Part 806 record references exact Document 36 field-action/scope snapshot. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No duplication. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-031-01 — Periodic report state — required behaviour

- **Requirement:** PMO-FR-031
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: SCHEDULED→DATA_COLLECTION→FROZEN→ANALYSIS→APPROVED→SUBMITTED→ACK/ARCHIVE. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled lifecycle. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-031-02 — Periodic report state — Action without the required signature is blocked

- **Requirement:** PMO-FR-031
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-060-031-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-031-03 — Periodic report state — Signature bound to a superseded version is rejected

- **Requirement:** PMO-FR-031
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-060-031-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-031-04 — Periodic report state — Illegal state transition is rejected

- **Requirement:** PMO-FR-031
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-060-031-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-032-01 — Inspection dashboard/export — required behaviour

- **Requirement:** PMO-FR-032
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** Minimum valid data set for `regulatory_obligation`, `applicant_relationship`, `constituent_information_share`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /postmarket/v1/applicant-relationships` (or the owning command) exercising: Show due/overdue obligations and export applicant-sharing, 806, Field Alert/BPDR, periodic, agency-request and retention evidence. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Inspection-ready. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-032-02 — Inspection dashboard/export — Disposal without an approved decision is refused

- **Requirement:** PMO-FR-032
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `regulatory_obligation`, `applicant_relationship`, `constituent_information_share` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-060-032-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-PM-003-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S001 — Specification scenario — two constituent applicants create correct sharing recipients

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: two constituent applicants create correct sharing recipients | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S002 — Specification scenario — missing recipient blocks completion

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: missing recipient blocks completion | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S003 — Specification scenario — 5-calendar-day sharing deadline

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: 5-calendar-day sharing deadline | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S004 — Specification scenario — reportable field action creates 10-working-day 806 obligation

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: reportable field action creates 10-working-day 806 obligation | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S005 — Specification scenario — nonreportable correction/removal creates controlled 806.20 record

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: nonreportable correction/removal creates controlled 806.20 record | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S006 — Specification scenario — scope expansion creates amendment task

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: scope expansion creates amendment task | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S007 — Specification scenario — NDA Field Alert 3-working-day calculation

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: NDA Field Alert 3-working-day calculation | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S008 — Specification scenario — biologic profile creates BPDR task

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: biologic profile creates BPDR task | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S009 — Specification scenario — quarterly/annual periodic cycle generation without duplicates

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: quarterly/annual periodic cycle generation without duplicates | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S010 — Specification scenario — Part 4 periodic augmentation

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: Part 4 periodic augmentation | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S011 — Specification scenario — FDA letter explicit due date

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: FDA letter explicit due date | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S012 — Specification scenario — agency extension preserves original deadline

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: agency extension preserves original deadline | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S013 — Specification scenario — retention selects longest configured applicable period

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: retention selects longest configured applicable period | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-060-S014 — Specification scenario — legal hold blocks purge

- **Requirement:** SPEC-PM-003-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: legal hold blocks purge | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____
