# WP-06 — Implementation Sequence

1. **Document 38 — Equipment, Calibration, Qualification & Maintenance**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-06/38_*.md`)
2. **Document 39 — Cleaning, Sanitization & Line Clearance**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-06/39_*.md`)
3. **Document 40 — Sterile / Aseptic Manufacturing Operations**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-06/40_*.md`)
4. **Document 41 — Environmental Monitoring & Cleanroom State Control**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-06/41_*.md`)
5. **Document 42 — Sterilization, CIP/SIP & Sterile Filtration Management**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-06/42_*.md`)
6. **Document 43 — Edge Gateway Runtime Architecture & Construction Specification**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-06/43_*.md`)
7. **Document 44 — Industrial Device & Protocol Connectivity / Driver Specification**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-06/44_*.md`)
8. **Document 45 — Store-and-Forward, Offline Buffering, Time Integrity & Data Quality**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-06/45_*.md`)
9. **Document 46 — Barcode, Scanner, Balance, Printer, Tester & Peripheral Integration**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-06/46_*.md`)
10. **Document 47 — Machine / PLC / SCADA Data Acquisition, Evidence Mapping & Command Boundary**: contracts → schema/migrations → domain services and command handlers → events/projections → UI → tests (`prompts/WP-06/47_*.md`)

## Per-document notes from the specifications

### Document 38
```text
1. Core master/state model.
2. Schedule/eligibility engine.
3. Execution records and evidence.
4. GxP authorization/signature/audit.
5. Batch/Recipe/QA/Release integration.
6. Edge/device source integration.
7. Alerts/escalation.
8. UI/dashboard/export.
9. Failure/concurrency/negative tests.
10. Validation traceability.
```
### Document 39
```text
1. Core master/state model.
2. Schedule/eligibility engine.
3. Execution records and evidence.
4. GxP authorization/signature/audit.
5. Batch/Recipe/QA/Release integration.
6. Edge/device source integration.
7. Alerts/escalation.
8. UI/dashboard/export.
9. Failure/concurrency/negative tests.
10. Validation traceability.
```
### Document 40
```text
1. Core master/state model.
2. Schedule/eligibility engine.
3. Execution records and evidence.
4. GxP authorization/signature/audit.
5. Batch/Recipe/QA/Release integration.
6. Edge/device source integration.
7. Alerts/escalation.
8. UI/dashboard/export.
9. Failure/concurrency/negative tests.
10. Validation traceability.
```
### Document 41
```text
1. Core master/state model.
2. Schedule/eligibility engine.
3. Execution records and evidence.
4. GxP authorization/signature/audit.
5. Batch/Recipe/QA/Release integration.
6. Edge/device source integration.
7. Alerts/escalation.
8. UI/dashboard/export.
9. Failure/concurrency/negative tests.
10. Validation traceability.
```
### Document 42
```text
1. Core master/state model.
2. Schedule/eligibility engine.
3. Execution records and evidence.
4. GxP authorization/signature/audit.
5. Batch/Recipe/QA/Release integration.
6. Edge/device source integration.
7. Alerts/escalation.
8. UI/dashboard/export.
9. Failure/concurrency/negative tests.
10. Validation traceability.
```
### Document 43
```text
1. canonical contracts;
2. enrollment/identity;
3. config loader/activation;
4. connector supervisor;
5. observation ingestion/normalization;
6. SQLite outbox;
7. forwarding/ack/idempotency;
8. health/clock;
9. certificate rotation;
10. signed update/rollback;
11. command channel stub disabled by default;
12. soak/failure tests.
```
### Document 44
```text
see requirement order
```
### Document 45
```text
see requirement order
```
### Document 46
```text
see requirement order
```
### Document 47
```text
see requirement order
```
