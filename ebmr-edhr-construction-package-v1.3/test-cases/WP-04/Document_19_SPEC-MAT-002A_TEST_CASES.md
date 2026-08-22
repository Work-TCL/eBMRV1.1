# Test Cases — Document 19: Material Receipt, Quarantine & Quality Status Specification (SPEC-MAT-002A)

**Work package:** WP-04  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** RCV-FR-001..032 (32)  
**Test cases:** 99  
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

### TC-019-001-01 — Expected receipt — required behaviour

- **Requirement:** RCV-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Load PO/transfer expectation with exact material/spec/source/quantity/document requirements. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Receiver knows expected material. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-002-01 — Receipt transaction — required behaviour

- **Requirement:** RCV-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Create immutable receipt ID, site, date/time, receiver, carrier/reference, PO/source and received quantity. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Receipt attributable. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-002-02 — Receipt transaction — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** RCV-FR-002
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-019-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-003-01 — Visual examination — required behaviour

- **Requirement:** RCV-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Capture appropriate labeling, damage, broken seals, contamination and shipment-condition observations before acceptance into quarantine. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** 211.82-style receipt check. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-004-01 — Material identity — required behaviour

- **Requirement:** RCV-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Match received material code/name/spec to expected material; mismatch creates hold/deviation, not silent remapping. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Wrong material blocked. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-005-01 — Supplier/manufacturer identity — required behaviour

- **Requirement:** RCV-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Capture supplier and actual manufacturer and validate against approved source matrix. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Source eligibility checked. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-005-02 — Supplier/manufacturer identity — Action without the required signature is blocked

- **Requirement:** RCV-FR-005
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-019-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-005-03 — Supplier/manufacturer identity — Signature bound to a superseded version is rejected

- **Requirement:** RCV-FR-005
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-019-005-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-006-01 — Supplier lot — required behaviour

- **Requirement:** RCV-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Capture supplier lot/batch number exactly as received. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Traceability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-007-01 — Manufacturer lot — required behaviour

- **Requirement:** RCV-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Capture manufacturer lot where distinct. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Source traceability. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-008-01 — Internal lot — required behaviour

- **Requirement:** RCV-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Generate unique internal lot code for each received lot/shipment grouping according to site policy. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Distinctive status code. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-009-01 — Container identity — required behaviour

- **Requirement:** RCV-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Create individual/container-group IDs and optional barcodes/QR labels. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Sampling/dispensing exact. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-010-01 — Quantity — required behaviour

- **Requirement:** RCV-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Capture received gross/net/accepted quantity and UOM with conversion rules. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Inventory accurate. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-010-02 — Quantity — Concurrent writers on one aggregate

- **Requirement:** RCV-FR-010
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-019-010-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-011-01 — Manufacture/expiry/retest — required behaviour

- **Requirement:** RCV-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Capture available manufacture, expiry and retest dates with source/evidence and validation. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Eligibility later. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-012-01 — COA/CoC — required behaviour

- **Requirement:** RCV-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Capture required documents, file hash, source and document completeness. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Supplier evidence linked. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-013-01 — COA extraction — required behaviour

- **Requirement:** RCV-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: AI/OCR may assist data entry later, but extracted data is advisory until verified; original document remains evidence. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No autonomous release. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-014-01 — Shipment conditions — required behaviour

- **Requirement:** RCV-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Capture temperature logger/transport condition evidence where required and generate excursion if outside rule. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Cold-chain support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-015-01 — Automatic quarantine — required behaviour

- **Requirement:** RCV-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: All applicable incoming regulated materials/containers/closures enter QUARANTINE by default until required test/examination and QC disposition. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No direct released receipt. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-015-02 — Automatic quarantine — Action without the required signature is blocked

- **Requirement:** RCV-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-019-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-015-03 — Automatic quarantine — Signature bound to a superseded version is rejected

- **Requirement:** RCV-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-019-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-015-04 — Automatic quarantine — Disposal without an approved decision is refused

- **Requirement:** RCV-FR-015
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-019-015-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-016-01 — Physical/location quarantine — required behaviour

- **Requirement:** RCV-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Assign allowed quarantine location/zone; system prevents issue/dispense from quarantined stock. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Status enforced. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-016-02 — Physical/location quarantine — Prohibited path is rejected

- **Requirement:** RCV-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Assign allowed quarantine location/zone; system prevents issue/dispense from quarantined stock. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-019-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-016-03 — Physical/location quarantine — Action without the required signature is blocked

- **Requirement:** RCV-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-019-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-016-04 — Physical/location quarantine — Signature bound to a superseded version is rejected

- **Requirement:** RCV-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-019-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-017-01 — Status label — required behaviour

- **Requirement:** RCV-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Generate container/lot status label containing internal lot/container ID, material, status and other configured fields. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Physical/digital alignment. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-017-02 — Status label — Illegal state transition is rejected

- **Requirement:** RCV-FR-017
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-019-017-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-018-01 — Sampling request — required behaviour

- **Requirement:** RCV-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Create sampling order based on material/spec/supplier risk/lot/shipment and sampling plan. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** QC workflow initiated. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-019-01 — Container selection — required behaviour

- **Requirement:** RCV-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Sampling plan identifies container(s) selected and quantity; actual selected containers recorded. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Representative sample trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-020-01 — Sampling execution — required behaviour

- **Requirement:** RCV-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Capture sampler, date/time, method/procedure reference, container, sample ID and reseal/marking evidence. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** 211.84-style evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-021-01 — Aseptic sampling — required behaviour

- **Requirement:** RCV-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Where required enforce sterile equipment/aseptic sampling qualification/profile and environment evidence. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Sterile materials supported. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-022-01 — Sample chain of custody — required behaviour

- **Requirement:** RCV-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Track sample container/location/transfer to QC/LIMS and status. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Sample integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-022-02 — Sample chain of custody — Illegal state transition is rejected

- **Requirement:** RCV-FR-022
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-019-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-022-03 — Sample chain of custody — Replayed inbound message is detected

- **Requirement:** RCV-FR-022
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-019-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-022-04 — Sample chain of custody — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** RCV-FR-022
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-019-022-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-023-01 — Identity test — required behaviour

- **Requirement:** RCV-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: For applicable drug components require identity testing rule and result before release; supplier COA alone cannot bypass required identity testing. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** 211.84 support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-023-02 — Identity test — Action without the required signature is blocked

- **Requirement:** RCV-FR-023
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-019-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-023-03 — Identity test — Signature bound to a superseded version is rejected

- **Requirement:** RCV-FR-023
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-019-023-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-024-01 — Supplier COA reliance — required behaviour

- **Requirement:** RCV-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Where permitted by profile, accept supplier analysis only with approved supplier-reliability status and required manufacturer testing/identity control | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Conditional reliance. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-024-02 — Supplier COA reliance — Action without the required signature is blocked

- **Requirement:** RCV-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-019-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-024-03 — Supplier COA reliance — Signature bound to a superseded version is rejected

- **Requirement:** RCV-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-019-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-024-04 — Supplier COA reliance — Illegal state transition is rejected

- **Requirement:** RCV-FR-024
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-019-024-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-025-01 — Incoming QC — required behaviour

- **Requirement:** RCV-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Link required tests/specification, native QC or LIMS results and result versions. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Disposition evidence. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-025-02 — Incoming QC — Limit boundary behaviour

- **Requirement:** RCV-FR-025
- **Type / priority:** boundary / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Execute with a value just inside, exactly at, and just outside the declared limit. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Inside passes, boundary follows the declared inclusivity, outside fails; rounding occurs only at declared stages.
- **Depends on:** TC-019-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-025-03 — Incoming QC — Replayed inbound message is detected

- **Requirement:** RCV-FR-025
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-019-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-025-04 — Incoming QC — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** RCV-FR-025
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-019-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-026-01 — Release disposition — required behaviour

- **Requirement:** RCV-FR-026
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Authorized Quality transitions lot/container group to RELEASED only after required evidence/rules complete. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** QC authority. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-026-02 — Release disposition — Action without the required signature is blocked

- **Requirement:** RCV-FR-026
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-019-026-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-026-03 — Release disposition — Signature bound to a superseded version is rejected

- **Requirement:** RCV-FR-026
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-019-026-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-026-04 — Release disposition — Illegal state transition is rejected

- **Requirement:** RCV-FR-026
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-019-026-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-027-01 — Reject disposition — required behaviour

- **Requirement:** RCV-FR-027
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Failed lot becomes REJECTED and is controlled under segregated status/location to prevent use. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** 211.89 support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-027-02 — Reject disposition — Prohibited path is rejected

- **Requirement:** RCV-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Failed lot becomes REJECTED and is controlled under segregated status/location to prevent use. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-019-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-027-03 — Reject disposition — Action without the required signature is blocked

- **Requirement:** RCV-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-019-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-027-04 — Reject disposition — Signature bound to a superseded version is rejected

- **Requirement:** RCV-FR-027
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-019-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-028-01 — Conditional/under-deviation use — required behaviour

- **Requirement:** RCV-FR-028
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Default disabled; if customer procedure permits exceptional use, require deviation, quality approval, bounded scope and explicit material eligibility  | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Exception controlled. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-029-01 — Retest status — required behaviour

- **Requirement:** RCV-FR-029
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Material may transition to RETEST_DUE/QUARANTINE and requires reexamination/retest before continued use where required. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** 211.87 support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-029-02 — Retest status — Illegal state transition is rejected

- **Requirement:** RCV-FR-029
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-019-029-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-030-01 — Partial lot disposition — required behaviour

- **Requirement:** RCV-FR-030
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Allow container-level partial release/reject only when sampling/spec/profile explicitly permits and genealogy remains exact. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No ambiguous status. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-030-02 — Partial lot disposition — Prohibited path is rejected

- **Requirement:** RCV-FR-030
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Allow container-level partial release/reject only when sampling/spec/profile explicitly permits and genealogy remains exact. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-019-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-030-03 — Partial lot disposition — Action without the required signature is blocked

- **Requirement:** RCV-FR-030
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-019-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-030-04 — Partial lot disposition — Signature bound to a superseded version is rejected

- **Requirement:** RCV-FR-030
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-019-030-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-031-01 — Receipt discrepancy — required behaviour

- **Requirement:** RCV-FR-031
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Over/short/damaged/wrong lot/document mismatch generates discrepancy workflow and ERP reconciliation. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Commercial/GxP synchronized. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-031-02 — Receipt discrepancy — Illegal state transition is rejected

- **Requirement:** RCV-FR-031
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-019-031-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-031-03 — Receipt discrepancy — Replayed inbound message is detected

- **Requirement:** RCV-FR-031
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Re-deliver a previously accepted external message with the same source id. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Replay detected and rejected; no duplicate regulated record; reconciliation entry created.
- **Expected error code:** `REPLAY_DETECTED`
- **Depends on:** TC-019-031-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-031-04 — Receipt discrepancy — Timeout-uncertain outcome is resolved by lookup

- **Requirement:** RCV-FR-031
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Force a timeout on the external call, then re-run the operation. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** System looks up the external state and never blindly re-creates the object.
- **Depends on:** TC-019-031-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-032-01 — Audit/export — required behaviour

- **Requirement:** RCV-FR-032
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** Minimum valid data set for `material_receipt`, `material_lot`, `material_container`; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `POST /materials/v1/receipts` (or the owning command) exercising: Full receipt→quarantine→sample→QC→release/reject history is exportable. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Inspection-ready. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-032-02 — Audit/export — Prohibited path is rejected

- **Requirement:** RCV-FR-032
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Full receipt→quarantine→sample→QC→release/reject history is exportable. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-019-032-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-032-03 — Audit/export — Action without the required signature is blocked

- **Requirement:** RCV-FR-032
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-019-032-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-032-04 — Audit/export — Signature bound to a superseded version is rejected

- **Requirement:** RCV-FR-032
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; `material_receipt`, `material_lot`, `material_container` in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-019-032-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-MAT-002A-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S001 — Specification scenario — correct receipt

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: correct receipt | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S002 — Specification scenario — wrong supplier

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: wrong supplier | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S003 — Specification scenario — wrong manufacturer

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: wrong manufacturer | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S004 — Specification scenario — damaged seal

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: damaged seal | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S005 — Specification scenario — missing COA

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: missing COA | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S006 — Specification scenario — quarantine issue attempt

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: quarantine issue attempt | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S007 — Specification scenario — sampling selected containers

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: sampling selected containers | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S008 — Specification scenario — identity test missing

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: identity test missing | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S009 — Specification scenario — supplier COA permitted/not permitted

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: supplier COA permitted/not permitted | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S010 — Specification scenario — release

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: release | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S011 — Specification scenario — reject

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: reject | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S012 — Specification scenario — retest due

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: retest due | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S013 — Specification scenario — partial container disposition

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: partial container disposition | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S014 — Specification scenario — ERP outage

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** e2e | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: ERP outage | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____

### TC-019-S015 — Specification scenario — stale QA signature

- **Requirement:** SPEC-MAT-002A-SPEC-SCENARIO
- **Type / priority:** scenario / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module functionally complete; upstream dependencies available.
- **Test data:** Scenario-specific data set defined by the executor and recorded before execution.
- **Steps:** 1. Prepare the scenario data and record it. | 2. Execute the scenario exactly as declared in the specification: stale QA signature | 3. Capture the evidence listed in evidence_to_capture.
- **Expected result:** Behaviour matches the specification's declared acceptance criteria for this scenario.
- **Evidence to capture:** execution record, inputs, outputs, screenshots, audit references
- **Status:** NOT_STARTED  |  **Executed by:** ____  |  **Date:** ____  |  **Actual result:** ____  |  **Defect:** ____
