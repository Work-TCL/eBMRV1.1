# WP-14 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| untrained user blocked | 85 | HIGHER-PROCESS-RISK |
| PFS batch scenario | 85 | HIGHER-PROCESS-RISK |
| ERP unavailable | 85 | HIGHER-PROCESS-RISK |
| signature flow | 85 | HIGHER-PROCESS-RISK |
| batch deviation | 85 | HIGHER-PROCESS-RISK |
| procedure/UI mismatch | 85 | HIGHER-PROCESS-RISK |
| controlled UAT reuse | 85 | HIGHER-PROCESS-RISK |
| duplicate legacy ID | 87 | HIGHER-PROCESS-RISK |
| timezone conversion | 87 | HIGHER-PROCESS-RISK |
| historic signature | 87 | HIGHER-PROCESS-RISK |
| missing attachment | 87 | HIGHER-PROCESS-RISK |
| quantity mismatch | 87 | HIGHER-PROCESS-RISK |
| rejected record | 87 | HIGHER-PROCESS-RISK |
| final delta | 87 | HIGHER-PROCESS-RISK |
| config mismatch | 95 | HIGHER-PROCESS-RISK |
| open critical exception | 95 | HIGHER-PROCESS-RISK |
| expired training | 95 | HIGHER-PROCESS-RISK |
| DR missing | 95 | HIGHER-PROCESS-RISK |
| security critical finding | 95 | HIGHER-PROCESS-RISK |
| post-go-live smoke fail | 95 | HIGHER-PROCESS-RISK |
