# WP-07 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| ERP unavailable after GxP commit | 48 | HIGHER-PROCESS-RISK |
| timeout after ERP committed but before response | 48 | HIGHER-PROCESS-RISK |
| duplicate command retry | 48 | HIGHER-PROCESS-RISK |
| stale item mapping | 48 | HIGHER-PROCESS-RISK |
| wrong UOM | 48 | HIGHER-PROCESS-RISK |
| external transaction manually reversed | 48 | HIGHER-PROCESS-RISK |
| adapter version upgrade | 48 | HIGHER-PROCESS-RISK |
| wrong tenant/site mapping | 48 | HIGHER-PROCESS-RISK |
| reconciliation catches missing posting | 48 | HIGHER-PROCESS-RISK |
| integration admin cannot edit GxP transaction | 48 | HIGHER-PROCESS-RISK |
| API token invalid | 49 | HIGHER-PROCESS-RISK |
| item mapping missing | 49 | HIGHER-PROCESS-RISK |
| supplier not quality-approved even though ERPNext supplier active | 49 | HIGHER-PROCESS-RISK |
| Purchase Receipt timeout after submit | 49 | HIGHER-PROCESS-RISK |
| duplicate retry | 49 | HIGHER-PROCESS-RISK |
| Stock Entry validation error | 49 | HIGHER-PROCESS-RISK |
| warehouse mapping wrong | 49 | HIGHER-PROCESS-RISK |
| Work Order imported | 49 | HIGHER-PROCESS-RISK |
| custom field absent | 49 | HIGHER-PROCESS-RISK |
| ERPNext upgrade changes response field | 49 | HIGHER-PROCESS-RISK |
| connector user overprivileged warning | 49 | HIGHER-PROCESS-RISK |
| wrong SAP plant mapping | 50 | HIGHER-PROCESS-RISK |
| wrong movement code configuration | 50 | HIGHER-PROCESS-RISK |
| CSRF failure | 50 | HIGHER-PROCESS-RISK |
| OAuth expiry | 50 | HIGHER-PROCESS-RISK |
| material document POST succeeds then client timeout | 50 | HIGHER-PROCESS-RISK |
| duplicate retry | 50 | HIGHER-PROCESS-RISK |
| business validation error | 50 | HIGHER-PROCESS-RISK |
| reversal after GxP correction | 50 | HIGHER-PROCESS-RISK |
| stock differs from GxP projection | 50 | HIGHER-PROCESS-RISK |
| API service version upgrade | 50 | HIGHER-PROCESS-RISK |
| Oracle privilege missing | 51 | HIGHER-PROCESS-RISK |
| Oracle transaction accepted with partial failed records | 51 | HIGHER-PROCESS-RISK |
| Dynamics wrong company context | 51 | HIGHER-PROCESS-RISK |
| Dynamics OData throttling | 51 | HIGHER-PROCESS-RISK |
| Dynamics data-management job fails after upload | 51 | HIGHER-PROCESS-RISK |
| custom REST timeout after external commit | 51 | HIGHER-PROCESS-RISK |
| custom file duplicate pickup | 51 | HIGHER-PROCESS-RISK |
| custom adapter lacks reconciliation path | 51 | HIGHER-PROCESS-RISK |
| external schema changes | 51 | HIGHER-PROCESS-RISK |
| initial 100k item import | 52 | HIGHER-PROCESS-RISK |
| duplicate external item | 52 | HIGHER-PROCESS-RISK |
| supplier same name different legal entity | 52 | HIGHER-PROCESS-RISK |
| GxP-owned field changed in ERP | 52 | HIGHER-PROCESS-RISK |
| unknown UOM | 52 | HIGHER-PROCESS-RISK |
| wrong plant/site | 52 | HIGHER-PROCESS-RISK |
| mapping future effective | 52 | HIGHER-PROCESS-RISK |
| external item deactivated | 52 | HIGHER-PROCESS-RISK |
| replay same import batch | 52 | HIGHER-PROCESS-RISK |
| conflict resolution stale version | 52 | HIGHER-PROCESS-RISK |
| sync cursor crash/restart | 52 | HIGHER-PROCESS-RISK |
| 500 error retry | 53 | HIGHER-PROCESS-RISK |
| 400 validation no retry | 53 | HIGHER-PROCESS-RISK |
| 429 Retry-After | 53 | HIGHER-PROCESS-RISK |
| timeout after vendor commit | 53 | HIGHER-PROCESS-RISK |
| duplicate idempotency same hash | 53 | HIGHER-PROCESS-RISK |
| duplicate idempotency different hash | 53 | HIGHER-PROCESS-RISK |
| inbound duplicate event | 53 | HIGHER-PROCESS-RISK |
| out-of-order inbound version | 53 | HIGHER-PROCESS-RISK |
| dead-letter replay | 53 | HIGHER-PROCESS-RISK |
| corrected new command | 53 | HIGHER-PROCESS-RISK |
| circuit breaker | 53 | HIGHER-PROCESS-RISK |
| bulk partial failure | 53 | HIGHER-PROCESS-RISK |
| reconciliation missing external posting | 53 | HIGHER-PROCESS-RISK |
| extra external transaction | 53 | HIGHER-PROCESS-RISK |
