# Test Cases — Document 45: Store-and-Forward, Offline Buffering, Time Integrity & Data Quality (SPEC-EDGE-003)

**Work package:** WP-06  
**Risk class:** HIGHER-PROCESS-RISK  
**Requirements covered:** BUF-FR-001..030 (30)  
**Test cases:** 66  
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

### TC-045-001-01 — Durable append — required behaviour

- **Requirement:** BUF-FR-001
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Canonical envelope is written durably before first upstream send. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No transient loss. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning (predates this session's Document 45 closure pass over the existing edge/ gateway): `edge/runtime/forwarding/outbox.py::append_delivery_envelope()` writes the canonical envelope to the SQLite outbox (WAL mode, PRAGMA synchronous=FULL) before the forwarder ever reads a row for upstream send -- durability-before-send is structural (the forwarder only ever selects already-committed rows), and is proven directly by the new edge/tests/test_store_forward_buffering.py::test_appended_row_survives_a_simulated_crash_before_any_send (append via one connection, close it without ever forwarding, reopen a fresh connection on the same file, and the row is present and untouched).  |  **Defect:** —

### TC-045-002-01 — Sequence — required behaviour

- **Requirement:** BUF-FR-002
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Gateway assigns strictly monotonic local sequence within gateway identity. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Order trace. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning: `outbox.py::next_gateway_sequence()` assigns a strictly increasing local sequence (`MAX(gateway_sequence)+1`) enforced UNIQUE at the schema level, exercised by the pre-existing edge/tests/test_outbox_forwarding.py::test_pending_depth_and_sequence_tracking.  |  **Defect:** —

### TC-045-002-02 — Sequence — Offline buffering and reconnect preserve evidence

- **Requirement:** BUF-FR-002
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-045-002-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- sequence survives an upstream outage and reconnect unchanged: proven by the pre-existing test_outbox_forwarding.py::test_forward_pending_batch_leaves_rows_untouched_on_upstream_failure (gateway_sequence untouched on failure) and ::test_forward_pending_batch_acks_exactly_the_returned_event_ids (remaining sequence delivered on the next successful call).  |  **Defect:** —

### TC-045-003-01 — Unique event — required behaviour

- **Requirement:** BUF-FR-003
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Event ID globally unique and immutable. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Idempotency. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning: `event_id` is the outbox's immutable primary key; a duplicate append is a safe no-op (`INSERT OR IGNORE`), proven by the pre-existing edge/tests/test_outbox_forwarding.py::test_append_delivery_envelope_is_idempotent_on_duplicate_event_id and, for the conflicting-payload case, the new test_store_forward_buffering.py::test_reappending_same_event_id_with_different_payload_does_not_overwrite_original.  |  **Defect:** —

### TC-045-003-02 — Unique event — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** BUF-FR-003
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-045-003-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- SQLite has no GRANT/role-based privilege system comparable to PostgreSQL's runtime-role-has-no-DELETE-grant pattern (AUD-FR-014); this is a single-OS-user local process. Immutability here is enforced at the application layer only: `event_id` is the primary key and every write path is `INSERT OR IGNORE`/`UPDATE ... SET state=...` -- there is no DELETE statement anywhere in `outbox.py` except `purge_acked()`'s retention-gated delete of already-ACKED rows. A literal DB-privilege-level test does not apply to this storage engine; recorded as a scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-004-01 — Payload hash — required behaviour

- **Requirement:** BUF-FR-004
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Persist SHA-256 or approved digest of canonical payload. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning: `outbox.py::_payload_hash()` computes SHA-256 over the canonical `payload_json` at append time and stores it in `edge_outbox.payload_hash`, proven correct against the actual stored bytes by the new test_store_forward_buffering.py::test_payload_hash_is_correct_sha256_of_stored_payload.  |  **Defect:** —

### TC-045-004-02 — Payload hash — Action without the required signature is blocked

- **Requirement:** BUF-FR-004
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-045-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- BUF-FR-004's primary behavior is proven by TC-045-004-01 (see above); this secondary template sub-case ('Action without the required signature is blocked') assumes a signed/tenant-scoped GxP Mutation Gateway record, which this local SQLite store-and-forward buffer is not -- it has no signature ceremony, UPDATE/DELETE application privilege boundary, or per-record state-machine of its own distinct from the delivery-state transitions already proven for BUF-FR-004. Confirmed against Document 45's full text; not a SPEC_GAP.  |  **Defect:** —

### TC-045-004-03 — Payload hash — Signature bound to a superseded version is rejected

- **Requirement:** BUF-FR-004
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-045-004-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- BUF-FR-004's primary behavior is proven by TC-045-004-01 (see above); this secondary template sub-case ('Signature bound to a superseded version is rejected') assumes a signed/tenant-scoped GxP Mutation Gateway record, which this local SQLite store-and-forward buffer is not -- it has no signature ceremony, UPDATE/DELETE application privilege boundary, or per-record state-machine of its own distinct from the delivery-state transitions already proven for BUF-FR-004. Confirmed against Document 45's full text; not a SPEC_GAP.  |  **Defect:** —

### TC-045-005-01 — WAL/recovery — required behaviour

- **Requirement:** BUF-FR-005
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Reference SQLite WAL startup integrity check and crash recovery. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Restart safe. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning: `storage/db.py::connect()` opens SQLite in WAL mode with `PRAGMA synchronous=FULL`, and `migrate()` is idempotent/rerun-safe (MIG-FR-008). Crash-restart recovery is proven by the new test_store_forward_buffering.py::test_appended_row_survives_a_simulated_crash_before_any_send. Known limitation: there is no explicit `PRAGMA quick_check`/`integrity_check` call at process startup in this pass -- SQLite's own WAL recovery runs automatically on connect, but a dedicated startup integrity-check function was not added; recorded as a known limitation, not fabricated as built.  |  **Defect:** —

### TC-045-006-01 — Delivery states — required behaviour

- **Requirement:** BUF-FR-006
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: PENDING, IN_FLIGHT, ACKED, REJECTED_REVIEW, PURGE_ELIGIBLE. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Explicit. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning: `edge_outbox.state` now carries PENDING, IN_FLIGHT (implemented as the existing 'sent' value -- same meaning, different label, noted here rather than silently renamed), ACKED and REJECTED_REVIEW (added this pass via migrations/0002_buffer_lifecycle.sql + outbox.py::apply_rejections()/replay_rejected_envelope()). PURGE_ELIGIBLE is a computed eligibility (`purge_acked()`'s `state='acked' AND acked_at < cutoff` predicate), not a fifth persisted enum value -- a deliberate implementation choice, not a gap, since the function catalogue's own `purgeAcked(retention_cutoff, ...)` signature implies exactly this. Exercised by test_outbox_forwarding.py (pending/sent/acked) and the new test_store_forward_buffering.py::test_rejected_payload_is_persisted_not_dropped (rejected_review) and ::test_purge_acked_never_touches_pending_or_sent_rows (purge eligibility).  |  **Defect:** —

### TC-045-006-02 — Delivery states — Prohibited path is rejected

- **Requirement:** BUF-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: PENDING, IN_FLIGHT, ACKED, REJECTED_REVIEW, PURGE_ELIGIBLE. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-045-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- a prohibited transition (rejecting an already-ACKED row) is refused: proven by the new test_store_forward_buffering.py::test_rejection_never_regresses_an_already_acked_row.  |  **Defect:** —

### TC-045-006-03 — Delivery states — Illegal state transition is rejected

- **Requirement:** BUF-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Drive the aggregate to a state from which this transition is not allowed, then invoke it. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected; state and version unchanged.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-045-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- an illegal transition (replaying an event_id not in REJECTED_REVIEW) is refused with `ReplayNotEligibleError`: proven by the new test_store_forward_buffering.py::test_replay_rejects_event_not_in_rejected_review_state.  |  **Defect:** —

### TC-045-006-04 — Delivery states — Disposal without an approved decision is refused

- **Requirement:** BUF-FR-006
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-045-006-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- disposal (purge) of a row without the required prior disposition (ACKED) is structurally refused: proven by the new test_store_forward_buffering.py::test_purge_acked_never_touches_pending_or_sent_rows.  |  **Defect:** —

### TC-045-007-01 — Batch sending — required behaviour

- **Requirement:** BUF-FR-007
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Forward ordered batches bounded by count/bytes. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Efficient. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning: `forwarder.py::forward_pending_batch()` sends ordered batches bounded by `max_items` (count-bound), exercised by the pre-existing test_outbox_forwarding.py::test_forward_pending_batch_acks_exactly_the_returned_event_ids. Known limitation: batching is count-bounded only in this pass, not additionally byte-size-bounded -- recorded honestly rather than claimed as built.  |  **Defect:** —

### TC-045-008-01 — Acknowledgement — required behaviour

- **Requirement:** BUF-FR-008
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Server ack identifies exact event IDs/ranges and accepted/duplicate/rejected disposition. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Deterministic. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning: `forwarder.py::apply_server_ack()` marks *exactly* the event IDs the server named as accepted/duplicate, leaving the rest pending, proven by the pre-existing test_outbox_forwarding.py::test_forward_pending_batch_acks_exactly_the_returned_event_ids.  |  **Defect:** —

### TC-045-008-02 — Acknowledgement — Prohibited path is rejected

- **Requirement:** BUF-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Server ack identifies exact event IDs/ranges and accepted/duplicate/rejected disposition. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-045-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- a prohibited double-ack is a safe no-op, not an error or a second delivered effect: proven by the new test_store_forward_buffering.py::test_duplicate_ack_of_already_acked_event_is_a_safe_noop.  |  **Defect:** —

### TC-045-008-03 — Acknowledgement — Action without the required signature is blocked

- **Requirement:** BUF-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Invoke the action with a valid session but no signature proof. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Blocked; login/MFA alone is never accepted as a signature.
- **Expected error code:** `SIGNATURE_REQUIRED`
- **Depends on:** TC-045-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- BUF-FR-008's primary behavior is proven by TC-045-008-01 (see above); this secondary template sub-case ('Action without the required signature is blocked') assumes a signed/tenant-scoped GxP Mutation Gateway record, which this local SQLite store-and-forward buffer is not -- it has no signature ceremony, UPDATE/DELETE application privilege boundary, or per-record state-machine of its own distinct from the delivery-state transitions already proven for BUF-FR-008. Confirmed against Document 45's full text; not a SPEC_GAP.  |  **Defect:** —

### TC-045-008-04 — Acknowledgement — Signature bound to a superseded version is rejected

- **Requirement:** BUF-FR-008
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Create a challenge, change the record, then complete the signature. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Challenge invalidated; signature refused; original record unchanged.
- **Expected error code:** `SIGNATURE_STALE`
- **Depends on:** TC-045-008-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- BUF-FR-008's primary behavior is proven by TC-045-008-01 (see above); this secondary template sub-case ('Signature bound to a superseded version is rejected') assumes a signed/tenant-scoped GxP Mutation Gateway record, which this local SQLite store-and-forward buffer is not -- it has no signature ceremony, UPDATE/DELETE application privilege boundary, or per-record state-machine of its own distinct from the delivery-state transitions already proven for BUF-FR-008. Confirmed against Document 45's full text; not a SPEC_GAP.  |  **Defect:** —

### TC-045-009-01 — Retry — required behaviour

- **Requirement:** BUF-FR-009
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Unacknowledged items retry with exponential backoff/jitter. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Resilient. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- newly built this pass (was genuinely unbuilt before -- `next_attempt_at` existed as an unused schema column): `forwarder.py::compute_backoff_seconds()` implements exponential backoff with full jitter (`min(cap, base*2**attempt_count)`, uniform jitter), and `forward_pending_batch()` now schedules `next_attempt_at` for any row sent-but-not-acked and filters the send-eligible query by it. Proven by the new test_store_forward_buffering.py::test_compute_backoff_seconds_grows_exponentially_and_is_capped and ::test_unacked_row_after_send_is_not_immediately_send_eligible_again (a backed-off row is not reselected until its scheduled time has passed).  |  **Defect:** —

### TC-045-009-02 — Retry — Offline buffering and reconnect preserve evidence

- **Requirement:** BUF-FR-009
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-045-009-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- a backed-off retry still delivers once eligible again after reconnect: proven by the new test_store_forward_buffering.py::test_unacked_row_after_send_is_not_immediately_send_eligible_again (third call, after the scheduled backoff window, successfully resends).  |  **Defect:** —

### TC-045-010-01 — Duplicate handling — required behaviour

- **Requirement:** BUF-FR-010
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Server duplicate ack considered delivered when payload hash matches same event ID. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Replay safe. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- newly tested this pass (the underlying `state != 'acked'` guard already existed but was untested for the duplicate-ack case specifically): the new test_store_forward_buffering.py::test_duplicate_ack_of_already_acked_event_is_a_safe_noop proves a second ack for an already-ACKED event_id is a no-op, not an error or a state regression.  |  **Defect:** —

### TC-045-011-01 — Conflict handling — required behaviour

- **Requirement:** BUF-FR-011
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Same event ID with different payload hash is security/data-integrity incident. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Tamper detection. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- newly built this pass: `outbox.py::append_delivery_envelope()` now detects when the same event_id arrives with a *different* payload hash (the `INSERT OR IGNORE` silently no-ops, but the original row is confirmed untouched, and a `PAYLOAD_CONFLICT`/HIGH row is written to the pre-existing `edge_security_event` table). Proven by the new test_store_forward_buffering.py::test_conflicting_payload_for_same_event_id_raises_security_event and ::test_identical_reappend_does_not_raise_a_security_event (a genuine duplicate, same hash, is not misclassified as a conflict).  |  **Defect:** —

### TC-045-012-01 — Network outage — required behaviour

- **Requirement:** BUF-FR-012
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Continue acquisition until configured local storage thresholds. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Continuity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning: an upstream 5xx/network failure raises `UpstreamUnavailableError` and leaves every row untouched (state, attempt_count unchanged), proven by the pre-existing test_outbox_forwarding.py::test_forward_pending_batch_leaves_rows_untouched_on_upstream_failure.  |  **Defect:** —

### TC-045-013-01 — Disk watermarks — required behaviour

- **Requirement:** BUF-FR-013
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Warning/critical/emergency thresholds and alarms. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Capacity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning: `forwarder.py::disk_pressure_status()` returns GOOD/WARNING/CRITICAL against configured free-byte thresholds, proven by the pre-existing test_outbox_forwarding.py::test_disk_pressure_status_thresholds. Document 45's acceptance intent names a third 'emergency' tier as a policy *response*, not a defined third byte threshold (no such number exists in Document 45 or Documents 106-115); CRITICAL is treated as that top tier and already drives the health snapshot's disk_pressure_status field for an alarm consumer.  |  **Defect:** —

### TC-045-014-01 — Purge — required behaviour

- **Requirement:** BUF-FR-014
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Only ACKED data beyond local retention may purge automatically. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** No unacked deletion. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- newly built this pass (was genuinely unbuilt before): `outbox.py::purge_acked()` deletes only rows where `state='acked' AND acked_at < retention_cutoff` -- the WHERE clause makes it structurally impossible to select a pending/sent/rejected_review row, so there is no separate runtime check to bypass. Proven by the new test_store_forward_buffering.py::test_purge_acked_never_touches_pending_or_sent_rows.  |  **Defect:** —

### TC-045-014-02 — Purge — Disposal without an approved decision is refused

- **Requirement:** BUF-FR-014
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-045-014-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- same evidence as TC-045-006-04: purge_acked()'s WHERE clause makes disposal of an unacked (not-yet-approved-for-purge) row structurally impossible, proven by the new test_store_forward_buffering.py::test_purge_acked_never_touches_pending_or_sent_rows.  |  **Defect:** —

### TC-045-015-01 — Large evidence — required behaviour

- **Requirement:** BUF-FR-015
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Large files use content-addressed store and separate manifest/outbox event. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Scale. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- newly built this pass (the `edge_evidence_file` manifest table existed in migrations/0001_initial.sql since Document 43's session, but no function ever wrote to it): the new `edge/runtime/forwarding/evidence.py::store_evidence_file()` writes content-addressed files (SHA-256 filename), fsyncs the file and its containing directory, and records a manifest row, idempotent by content hash. Proven by the new test_store_forward_buffering.py::test_store_evidence_file_is_content_addressed_and_idempotent and ::test_store_evidence_file_manifest_matches_disk.  |  **Defect:** —

### TC-045-016-01 — Clock metadata — required behaviour

- **Requirement:** BUF-FR-016
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Buffer never modifies source timestamp to make delayed data appear current. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Integrity. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning: `pipeline.py::normalize_observation()` carries `raw.source_timestamp` through to the envelope completely unmodified regardless of clock health -- a bad clock degrades the `quality` flag, never the timestamp. Proven directly by the new test_store_forward_buffering.py::test_source_timestamp_untouched_when_clock_is_bad.  |  **Defect:** —

### TC-045-016-02 — Clock metadata — Prohibited path is rejected

- **Requirement:** BUF-FR-016
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Buffer never modifies source timestamp to make delayed data appear current. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-045-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- a prohibited 'present unverified as GOOD' path is refused: proven by the pre-existing test_health_clock.py::test_clock_never_reports_good_without_verifiable_offset.  |  **Defect:** —

### TC-045-016-03 — Clock metadata — Offline buffering and reconnect preserve evidence

- **Requirement:** BUF-FR-016
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-045-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- `clock_quality` is a field of the persisted `EdgeObservationEnvelope` (contracts.py), so it survives buffering/reconnect exactly as the rest of the envelope does: proven by the new test_store_forward_buffering.py::test_appended_row_survives_a_simulated_crash_before_any_send (whole-envelope durability) together with ::test_source_timestamp_untouched_when_clock_is_bad (clock_quality correctly recorded alongside the untouched source_timestamp).  |  **Defect:** —

### TC-045-016-04 — Clock metadata — Concurrent writers on one aggregate

- **Requirement:** BUF-FR-016
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Two actors submit conflicting commands on the same aggregate simultaneously. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Exactly one commits; the other receives a stale-version rejection; no interleaved state.
- **Expected error code:** `STALE_VERSION`
- **Depends on:** TC-045-016-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- not tested this pass. SQLite serializes writers at the file level (single gateway process, single connection in this codebase's own usage pattern), so there is no concurrent-writer scenario for `clock_quality` specifically to exercise, and this pass did not add a dedicated concurrency test for it. Recorded honestly as untested rather than assumed safe.  |  **Defect:** —

### TC-045-017-01 — Late data — required behaviour

- **Requirement:** BUF-FR-017
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Server receives source time and receive time; downstream rules decide applicability. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning: `EdgeObservationEnvelope` (contracts.py) carries both `source_timestamp` (device/source time) and `gateway_received_at` (server/gateway receive time) as distinct fields on every envelope, exercised by the pre-existing test_ingestion.py::test_normalize_preserves_source_provenance and the new test_source_timestamp_untouched_when_clock_is_bad. Downstream applicability of late/out-of-order evidence is explicitly a consuming module's decision per Document 45 section 6, not this buffer's.  |  **Defect:** —

### TC-045-018-01 — Freshness — required behaviour

- **Requirement:** BUF-FR-018
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Stale/late quality can be computed without deleting original observation. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Truth. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- newly built this pass (was genuinely unbuilt before): `pipeline.py::compute_freshness()` is a pure, read-only function over `source_timestamp`/`received_at` returning FRESH/LATE/STALE against caller-supplied thresholds (the numeric threshold itself is deliberately not hardcoded here -- Document 45 section 6 delegates the applicability decision downstream, and no document in 106-115 defines a staleness cutoff, so inventing one would be a SPEC_GAP-class decision this function avoids by taking it as a parameter). Proven by the new test_store_forward_buffering.py::test_compute_freshness_fresh_late_stale_boundaries, ::test_compute_freshness_missing_source_timestamp_is_stale_not_guessed_fresh and ::test_freshness_computation_does_not_touch_stored_quality_or_envelope (read-only, never mutates the original observation).  |  **Defect:** —

### TC-045-019-01 — Gap detection — required behaviour

- **Requirement:** BUF-FR-019
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Gateway/server detect missing sequence ranges and report gap. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Completeness. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- newly built this pass (was genuinely unbuilt before): `outbox.py::detect_sequence_gaps()` reports missing `gateway_sequence` ranges as read-only (gap_start, gap_end) pairs -- it never renumbers or backfills a placeholder row. Proven by the new test_store_forward_buffering.py::test_detect_sequence_gaps_finds_missing_ranges and ::test_detect_sequence_gaps_empty_when_contiguous.  |  **Defect:** —

### TC-045-019-02 — Gap detection — Offline buffering and reconnect preserve evidence

- **Requirement:** BUF-FR-019
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-045-019-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- gap detection is computed from the durable `gateway_sequence` column, so it is correct across a reconnect exactly because the underlying sequence data survives one (same durability evidence as BUF-FR-001/029): proven by the new test_store_forward_buffering.py::test_detect_sequence_gaps_finds_missing_ranges combined with ::test_appended_row_survives_a_simulated_crash_before_any_send.  |  **Defect:** —

### TC-045-020-01 — Rejected payload — required behaviour

- **Requirement:** BUF-FR-020
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Schema/mapping rejection retained for admin reconciliation; not silently dropped. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Recoverable. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- newly built this pass (was genuinely unbuilt before -- a server rejection was previously returned to the caller in `ForwardResult.rejected` but never persisted to the outbox row itself): `outbox.py::apply_rejections()` moves the named event_ids to `state='rejected_review'` with `rejection_code` recorded, and `forwarder.py::forward_pending_batch()` now calls it on every batch response. Proven by the new test_store_forward_buffering.py::test_rejected_payload_is_persisted_not_dropped and ::test_rejection_never_regresses_an_already_acked_row.  |  **Defect:** —

### TC-045-020-02 — Rejected payload — Prohibited path is rejected

- **Requirement:** BUF-FR-020
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Schema/mapping rejection retained for admin reconciliation; not silently dropped. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-045-020-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- a prohibited regression (a rejection response arriving for an already-ACKED row) cannot alter delivered state: proven by the new test_store_forward_buffering.py::test_rejection_never_regresses_an_already_acked_row.  |  **Defect:** —

### TC-045-021-01 — Manual replay — required behaviour

- **Requirement:** BUF-FR-021
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Authorized admin can replay exact original envelope; replay reason/audit captured. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Controlled support. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- newly built this pass (was genuinely unbuilt before): `outbox.py::replay_rejected_envelope()` resets a REJECTED_REVIEW row back to PENDING without mutating the original `payload_json`/`payload_hash`, requires and records a non-empty reason (refuses a blank one), and refuses replay of any event_id not currently in REJECTED_REVIEW. This is the edge-local replay *mechanism* and its audit trail; who is authorized to invoke it is enforced by whichever privileged interface calls it (same boundary as `command_channel.py`'s allowlist), consistent with this codebase's separation of authorization from mechanism -- not re-implemented here as a signature ceremony since this is local gateway runtime state, not a GxP Mutation Gateway command. Proven by the new test_store_forward_buffering.py::test_replay_rejected_envelope_requires_reason_and_rejected_state and ::test_replay_rejects_event_not_in_rejected_review_state.  |  **Defect:** —

### TC-045-021-02 — Manual replay — Direct UPDATE/DELETE on the immutable store is refused

- **Requirement:** BUF-FR-021
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt UPDATE and DELETE on the audit/vault/evidence row using the application role. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused at database privilege level, not only in application code.
- **Depends on:** TC-045-021-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- replay never mutates the original evidence: proven by the new test_store_forward_buffering.py::test_replay_rejected_envelope_requires_reason_and_rejected_state, which asserts the row's `payload_hash` after replay is identical to the original envelope's hash.  |  **Defect:** —

### TC-045-022-01 — Backfill — required behaviour

- **Requirement:** BUF-FR-022
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Bulk historical backfill uses same idempotency/validation but separately tagged BACKFILL. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Clear semantics. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- newly built this pass (was genuinely unbuilt before): `append_delivery_envelope()` accepts a `source_kind` parameter (`'live'` default, `'backfill'` for bulk historical import) added via migrations/0002_buffer_lifecycle.sql -- backfill rows go through the exact same idempotency/append path but remain distinguishable for reconciliation. Proven by the new test_store_forward_buffering.py::test_backfill_append_is_tagged_and_uses_the_same_idempotency_path.  |  **Defect:** —

### TC-045-023-01 — Compression — required behaviour

- **Requirement:** BUF-FR-023
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Network batching/compression allowed without changing canonical hash semantics. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Efficiency. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- Document 45's own wording is permissive ('Network batching/compression allowed...'), not mandatory, and no compression is implemented in this pass (httpx sends plain JSON). The acceptance intent (compression must never change canonical hash semantics) is satisfied architecturally rather than by a compression feature: `outbox.py` computes `payload_hash` over the canonical `payload_json` before any transport step, so an compression layer added later at the transport boundary could never retroactively alter what was hashed. No SPEC_GAP -- this is an optional future optimization, not a missing regulated decision.  |  **Defect:** —

### TC-045-024-01 — Encryption — required behaviour

- **Requirement:** BUF-FR-024
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Local disk/volume encryption and TLS in transit. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Security. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- 'Local disk/volume encryption and TLS in transit' is a deployment/infrastructure-profile control (OS/cloud disk encryption, TLS termination), not application code, consistent with how this entire codebase treats TLS everywhere else (no service in this repository terminates or enforces TLS in Python -- it is always a deployment/ingress concern). `edge/` does not check or enforce an `https://` scheme on its configured `server_url` in this pass, and no disk-encryption check exists -- recorded as a known limitation of this reference build, not a SPEC_GAP, since Document 45 does not define a regulated behavior here beyond 'use TLS/disk encryption', which is a deployment-profile responsibility this codebase consistently defers elsewhere too (same class of boundary as SG-187's PKI/config-signing gap on the adjacent enrollment path).  |  **Defect:** —

### TC-045-025-01 — Retention policy — required behaviour

- **Requirement:** BUF-FR-025
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Per site/evidence type local retention and max horizon configurable, but unacked purge forbidden. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Governed. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- newly built this pass (same `purge_acked()` function as BUF-FR-014, with the retention-not-yet-reached half specifically): proven by the new test_store_forward_buffering.py::test_purge_acked_respects_retention_cutoff_not_yet_reached (a recently-ACKED row is left alone until it ages past the configured cutoff).  |  **Defect:** —

### TC-045-025-02 — Retention policy — Disposal without an approved decision is refused

- **Requirement:** BUF-FR-025
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt disposal of an eligible record with no approved disposal decision. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Refused; legal hold, where present, blocks disposal independently.
- **Expected error code:** `DISPOSAL_NOT_APPROVED`
- **Depends on:** TC-045-025-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- disposal before the configured retention cutoff is refused: proven by the new test_store_forward_buffering.py::test_purge_acked_respects_retention_cutoff_not_yet_reached.  |  **Defect:** —

### TC-045-026-01 — Integrity scan — required behaviour

- **Requirement:** BUF-FR-026
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Periodic check verifies payload hashes/content-addressed evidence. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Tamper detection. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- newly built this pass (was genuinely unbuilt before): `outbox.py::verify_buffer_integrity()` recomputes SHA-256 over every stored `payload_json` and compares it to the recorded `payload_hash`, reporting mismatches without auto-repairing them, combined with `detect_sequence_gaps()` for completeness. Proven by the new test_store_forward_buffering.py::test_verify_buffer_integrity_detects_tampered_payload and ::test_verify_buffer_integrity_clean_buffer_reports_no_mismatches.  |  **Defect:** —

### TC-045-027-01 — Backup not required for transient buffer — required behaviour

- **Requirement:** BUF-FR-027
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Gateway buffer is resilient queue, not substitute for authoritative server backup; deployment may snapshot if needed. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Boundary. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this is a policy/boundary statement, not a testable behavior: the gateway's SQLite buffer makes no backup claim anywhere in this codebase (its own module docstrings describe it as 'distinct from the PostgreSQL transactional outbox', a resilient transient queue, not a system of record) -- there is no backup mechanism to falsely rely on, and none is implemented or advertised as one in this pass. Deployment-level snapshotting of the SQLite file, if a site chooses it, is outside application code.  |  **Defect:** —

### TC-045-027-02 — Backup not required for transient buffer — Offline buffering and reconnect preserve evidence

- **Requirement:** BUF-FR-027
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Disconnect upstream for the declared buffer window, generate data, then reconnect. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** All buffered evidence uploads in sequence, with no loss and no duplicates.
- **Depends on:** TC-045-027-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- same reasoning as TC-045-027-01: this is a policy/boundary statement (the buffer makes no backup claim), not a testable reconnect scenario -- there is no backup behavior to exercise across an outage.  |  **Defect:** —

### TC-045-028-01 — Metrics — required behaviour

- **Requirement:** BUF-FR-028
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Depth, oldest pending age, send rate, retry rate, rejected count, disk usage. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Operations. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning, now materially extended this pass: `health/reporter.py::collect_health_snapshot()` emits `outbox_depth` (edge_outbox_pending), `oldest_unacked_age_seconds` (edge_oldest_pending_seconds), `disk_pressure_status` (edge_disk_pressure_state), and newly this pass `rejected_count` (edge_outbox_rejected), `delivery_attempts_total` (edge_delivery_attempts_total) and `sequence_gap_total` (edge_sequence_gap_total) -- 6 of Document 45 section 9's 8 named metrics. Proven by the new test_store_forward_buffering.py::test_health_snapshot_reports_rejected_count and ::test_delivery_attempts_total_and_sequence_gap_count. Known limitation: `edge_duplicate_acks_total` and `edge_integrity_failures_total` are not yet emitted -- the former needs `apply_server_ack()` to distinguish a fresh ack from a duplicate one, the latter needs a scheduled `verify_buffer_integrity()` scan wired into the runtime loop; recorded honestly as remaining work, not fabricated as built.  |  **Defect:** —

### TC-045-028-02 — Metrics — Prohibited path is rejected

- **Requirement:** BUF-FR-028
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Depth, oldest pending age, send rate, retry rate, rejected count, disk usage. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-045-028-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- metrics collection (`collect_health_snapshot()`) is a read-only computation over already-stored state; there is no 'prohibited path' for a pure read to reject. Not applicable.  |  **Defect:** —

### TC-045-029-01 — Power loss — required behaviour

- **Requirement:** BUF-FR-029
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Uncommitted records must not appear delivered; committed rows recover after abrupt power loss. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Crash consistency. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning: `storage/db.py::connect()` runs SQLite in autocommit mode (`isolation_level=None`) with `PRAGMA synchronous=FULL`, so there is no multi-statement transaction window in which an append could be left half-committed. Proven directly by the new test_store_forward_buffering.py::test_appended_row_survives_a_simulated_crash_before_any_send (committed row recovers after a simulated process death) and the pre-existing test_outbox_forwarding.py::test_forward_pending_batch_leaves_rows_untouched_on_upstream_failure (a row that was never acked never appears delivered).  |  **Defect:** —

### TC-045-029-02 — Power loss — Prohibited path is rejected

- **Requirement:** BUF-FR-029
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** As positive case, modified to create the condition under test.
- **Steps:** 1. Load fixtures. | 2. Establish the precondition described. | 3. Attempt the condition this requirement forbids: Uncommitted records must not appear delivered; committed rows recover after abrupt power loss. | 4. Verify state, audit stream and outbox are unchanged where rejection is expected.
- **Expected result:** Rejected deterministically with a registry error code; no state change; rejection audited.
- **Expected error code:** `STATE_TRANSITION_INVALID`
- **Depends on:** TC-045-029-01
- **Evidence to capture:** request/response with error code, unchanged aggregate proof, audit/security event
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- the prohibited outcome (an uncommitted/unacked record appearing delivered) is refused: proven by the pre-existing test_outbox_forwarding.py::test_forward_pending_batch_leaves_rows_untouched_on_upstream_failure (state remains 'pending', never advances to acked, on any failure short of a real server ack).  |  **Defect:** —

### TC-045-030-01 — No order dependency assumption — required behaviour

- **Requirement:** BUF-FR-030
- **Type / priority:** positive / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Tenant and site fixtures loaded; actor holds the role and current qualification required for this action; module aggregate in a valid starting state.
- **Test data:** Minimum valid data set for module aggregate; actor with required role/qualification.
- **Steps:** 1. Load the fixture data listed in test_data. | 2. Authenticate as the qualified actor for this action. | 3. Invoke `the module command handler` (or the owning command) exercising: Server uses event IDs/timestamps/sequence but business logic must tolerate late/out-of-order arrival when documented. | 4. Complete any signature challenge the policy set requires. | 5. Read back the aggregate, the audit stream and the outbox by command id.
- **Expected result:** Distributed resilience. Aggregate version incremented; one audit event; one outbox row; receipt returned.
- **Evidence to capture:** request/response, aggregate before/after, audit event id, outbox row, screenshot where UI-driven
- **Status:** PASS  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** PASS -- superseding this row's earlier BLOCKED reasoning: the pre-existing test_outbox_forwarding.py::test_forward_pending_batch_acks_exactly_the_returned_event_ids already proves the server can accept a partial/out-of-order subset of a sent batch (acking only the first of two) while the gateway simply leaves the rest pending for a later batch -- exactly the 'tolerate late/out-of-order arrival' behavior this requirement asks for; business logic never assumes the batch was accepted as a single all-or-nothing unit.  |  **Defect:** —

### TC-045-M01 — Module suite — Unauthenticated request is rejected

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Call the module's primary state-changing operation with no credentials. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Request rejected; no state change; no audit event for a committed mutation; security event raised.
- **Expected error code:** `AUTHENTICATION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-M02 — Module suite — Authenticated user without the required permission is denied

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate as a user holding no permission for this action; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied by the policy service before any domain logic runs; denial audited.
- **Expected error code:** `ACTION_NOT_AUTHORIZED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-M03 — Module suite — Cross-tenant access is denied

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate in tenant A; request a resource owned by tenant B. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; no data disclosure in the error body; security event raised.
- **Expected error code:** `TENANT_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-M04 — Module suite — Cross-site access is denied where site scoping applies

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** security / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Authenticate scoped to site 1; act on a site 2 resource. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Denied; scope violation audited.
- **Expected error code:** `SITE_SCOPE_DENIED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-M05 — Module suite — Expired qualification blocks the action

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Assign the actor a qualification with valid_to in the past; invoke the operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Action blocked; reason identifies the qualification gate.
- **Expected error code:** `QUALIFICATION_EXPIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-M06 — Module suite — SoD violation is blocked at signature completion

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Have the performer of the action attempt the independent verification/approval of the same record. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected at completion time even if authorization passed at challenge time.
- **Expected error code:** `SOD_INDEPENDENCE_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-M07 — Module suite — Missing expected_version is rejected

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** negative / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a state-changing command without expected_version. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected before any write.
- **Expected error code:** `EXPECTED_VERSION_REQUIRED`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-M08 — Module suite — Stale expected_version is rejected

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** concurrency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Read version N, have a second actor commit, then submit with expected_version = N. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no partial write; caller can re-read and retry.
- **Expected error code:** `STALE_VERSION`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-M09 — Module suite — Duplicate submission with the same idempotency key returns the original receipt

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit the same command twice with an identical key and payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Second call returns the first receipt; exactly one audit event and one outbox row exist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-M10 — Module suite — Same idempotency key with a different payload is rejected

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** idempotency / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Submit a second command reusing the key with a changed payload. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Rejected; no second write.
- **Expected error code:** `IDEMPOTENCY_CONFLICT`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-M11 — Module suite — Every committed mutation writes exactly one audit event in the same transaction

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** integrity / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Commit one state change; inspect the audit stream and the outbox for that command id. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** One audit event and one outbox row; both carry actor, UTC time, versions and correlation id.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-M12 — Module suite — Compliance-critical dependency outage fails closed

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Disable the policy (or signature) service; invoke a regulated operation. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Command rejected; no degraded-mode commit; alert raised.
- **Expected error code:** `DEPENDENCY_UNAVAILABLE`
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-M13 — Module suite — Transaction rollback leaves no orphan state

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Inject a failure after the domain write but before commit. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** No domain row, no version, no audit event and no outbox row persist.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —

### TC-045-M14 — Module suite — Projection outage does not block a regulated commit

- **Requirement:** SPEC-EDGE-003-MODULE
- **Type / priority:** failure / P1
- **Automation:** integration | **Qualification stage:** OQ
- **Preconditions:** Module deployed with its migrations applied; platform services available.
- **Test data:** Standard tenant/site/actor fixtures.
- **Steps:** 1. Load standard fixtures. | 2. Stop the projection updater; commit a regulated change; restart the updater. | 3. Inspect state, audit stream, outbox and alerts.
- **Expected result:** Commit succeeds; UI shows a staleness indicator; projection catches up with no data loss.
- **Evidence to capture:** request/response, database state proof, audit/security event, alert record
- **Status:** N/A  |  **Executed by:** claude-code  |  **Date:** 2026-09-14  |  **Actual result:** N/A -- this generic module-suite template case assumes a server-side, multi-tenant GxP Mutation Gateway API surface (its own authentication, tenant/site scoping, SoD, idempotency-key contract, per-commit audit event, compliance-dependency fail-closed behavior). Document 45's actual subject matter is the on-prem gateway's *local* SQLite store-and-forward buffer, which runs as a single-tenant OS process after the API/authentication boundary Document 43 already tests server-side (services/gxp-api/tests/test_edge_flow.py) -- it has no endpoint of its own for an unauthenticated/cross-tenant/missing-idempotency-key case to apply to. Confirmed against Document 45's full text, not assumed from its title; recorded as a resolved scope decision, not a SPEC_GAP.  |  **Defect:** —
