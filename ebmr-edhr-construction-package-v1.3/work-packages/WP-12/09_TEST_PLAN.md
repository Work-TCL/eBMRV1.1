# WP-12 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| high-risk scripted/automated evidence | 79 | HIGHER-PROCESS-RISK |
| low-risk exploratory evidence | 79 | HIGHER-PROCESS-RISK |
| missing customer config PQ | 79 | HIGHER-PROCESS-RISK |
| open critical validation deviation | 79 | HIGHER-PROCESS-RISK |
| Part 11 evidence missing | 79 | HIGHER-PROCESS-RISK |
| calculation high impact | 80 | HIGHER-PROCESS-RISK |
| display-only low risk | 80 | HIGHER-PROCESS-RISK |
| audit-disable high risk | 80 | HIGHER-PROCESS-RISK |
| customer release-rule config | 80 | HIGHER-PROCESS-RISK |
| external bad mapping | 80 | HIGHER-PROCESS-RISK |
| AI advisory | 80 | HIGHER-PROCESS-RISK |
| orphan critical requirement | 81 | HIGHER-PROCESS-RISK |
| test to superseded requirement | 81 | HIGHER-PROCESS-RISK |
| API change impact | 81 | HIGHER-PROCESS-RISK |
| customer URS layer | 81 | HIGHER-PROCESS-RISK |
| critical SPEC_GAP | 81 | HIGHER-PROCESS-RISK |
| automated pass import | 82 | HIGHER-PROCESS-RISK |
| flaky automation | 82 | HIGHER-PROCESS-RISK |
| failed manual step | 82 | HIGHER-PROCESS-RISK |
| exploratory session | 82 | HIGHER-PROCESS-RISK |
| retest preserves old fail | 82 | HIGHER-PROCESS-RISK |
| stale environment fingerprint | 82 | HIGHER-PROCESS-RISK |
| wrong image digest | 83 | HIGHER-PROCESS-RISK |
| unsupported DB version | 83 | HIGHER-PROCESS-RISK |
| NTP missing | 83 | HIGHER-PROCESS-RISK |
| backup absent | 83 | HIGHER-PROCESS-RISK |
| cert expired | 83 | HIGHER-PROCESS-RISK |
| forbidden path open | 83 | HIGHER-PROCESS-RISK |
| validation endpoint points to prod ERP | 83 | HIGHER-PROCESS-RISK |
| stale mutation denied | 84 | HIGHER-PROCESS-RISK |
| signature wrong meaning | 84 | HIGHER-PROCESS-RISK |
| audit old/new | 84 | HIGHER-PROCESS-RISK |
| rounding vectors | 84 | HIGHER-PROCESS-RISK |
| duplicate command | 84 | HIGHER-PROCESS-RISK |
| worker restart | 84 | HIGHER-PROCESS-RISK |
| unauthorized release | 84 | HIGHER-PROCESS-RISK |
| prod/validation difference | 86 | HIGHER-PROCESS-RISK |
| network deny | 86 | HIGHER-PROCESS-RISK |
| managed DB failover | 86 | HIGHER-PROCESS-RISK |
| NATS persistence | 86 | HIGHER-PROCESS-RISK |
| Temporal reconnect | 86 | HIGHER-PROCESS-RISK |
| clock alert | 86 | HIGHER-PROCESS-RISK |
| object immutability | 86 | HIGHER-PROCESS-RISK |
| unauthorized record access | 88 | HIGHER-PROCESS-RISK |
| audit old/new | 88 | HIGHER-PROCESS-RISK |
| wrong workflow order | 88 | HIGHER-PROCESS-RISK |
| invalid scanner source | 88 | HIGHER-PROCESS-RISK |
| signature manifestation | 88 | HIGHER-PROCESS-RISK |
| signature reassociation denied | 88 | HIGHER-PROCESS-RISK |
| expired challenge | 88 | HIGHER-PROCESS-RISK |
| archive retrieval | 88 | HIGHER-PROCESS-RISK |
| audit row modified/deleted | 89 | HIGHER-PROCESS-RISK |
| hash chain break | 89 | HIGHER-PROCESS-RISK |
| evidence replaced | 89 | HIGHER-PROCESS-RISK |
| failed result retained | 89 | HIGHER-PROCESS-RISK |
| correction history | 89 | HIGHER-PROCESS-RISK |
| cold archive | 89 | HIGHER-PROCESS-RISK |
| late Edge chronology | 89 | HIGHER-PROCESS-RISK |
| duplicate ERP receipt | 90 | HIGHER-PROCESS-RISK |
| wrong LIMS sample | 90 | HIGHER-PROCESS-RISK |
| 72h Edge outage synthetic | 90 | HIGHER-PROCESS-RISK |
| bad OPC quality | 90 | HIGHER-PROCESS-RISK |
| unstable balance | 90 | HIGHER-PROCESS-RISK |
| wrong barcode | 90 | HIGHER-PROCESS-RISK |
| spoofed webhook | 90 | HIGHER-PROCESS-RISK |
| command disabled | 90 | HIGHER-PROCESS-RISK |
| PITR | 91 | HIGHER-PROCESS-RISK |
| standby failover | 91 | HIGHER-PROCESS-RISK |
| object mismatch | 91 | HIGHER-PROCESS-RISK |
| outbox recovery | 91 | HIGHER-PROCESS-RISK |
| Temporal resume | 91 | HIGHER-PROCESS-RISK |
| MariaDB rebuild | 91 | HIGHER-PROCESS-RISK |
| key unavailable | 91 | HIGHER-PROCESS-RISK |
| RPO exceeded | 91 | HIGHER-PROCESS-RISK |
| cross-tenant BOLA | 92 | HIGHER-PROCESS-RISK |
| MFA bypass | 92 | HIGHER-PROCESS-RISK |
| SSRF | 92 | HIGHER-PROCESS-RISK |
| malicious upload | 92 | HIGHER-PROCESS-RISK |
| break-glass no signature | 92 | HIGHER-PROCESS-RISK |
| expired cert | 92 | HIGHER-PROCESS-RISK |
| unsigned image | 92 | HIGHER-PROCESS-RISK |
| SIEM rule | 92 | HIGHER-PROCESS-RISK |
| 250 concurrent | 93 | HIGHER-PROCESS-RISK |
| several-thousand-step batch | 93 | HIGHER-PROCESS-RISK |
| millions audit/day | 93 | HIGHER-PROCESS-RISK |
| long Edge catch-up | 93 | HIGHER-PROCESS-RISK |
| DB failover | 93 | HIGHER-PROCESS-RISK |
| NATS outage | 93 | HIGHER-PROCESS-RISK |
| soak | 93 | HIGHER-PROCESS-RISK |
| heavy report | 93 | HIGHER-PROCESS-RISK |
| fail then fixed/retest | 94 | HIGHER-PROCESS-RISK |
| wrong environment invalidates pass | 94 | HIGHER-PROCESS-RISK |
| missing critical evidence | 94 | HIGHER-PROCESS-RISK |
| accepted cosmetic issue | 94 | HIGHER-PROCESS-RISK |
| critical defect blocks release | 94 | HIGHER-PROCESS-RISK |
| security patch targeted regression | 96 | HIGHER-PROCESS-RISK |
| DB major upgrade | 96 | HIGHER-PROCESS-RISK |
| release rule change | 96 | HIGHER-PROCESS-RISK |
| IdP change Part11 retest | 96 | HIGHER-PROCESS-RISK |
| expired DR qualification | 96 | HIGHER-PROCESS-RISK |
| critical incident suspension | 96 | HIGHER-PROCESS-RISK |
| decommission archive | 96 | HIGHER-PROCESS-RISK |
