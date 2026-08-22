# WP-11 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| foreign service tries GxP write | 69 | HIGHER-PROCESS-RISK |
| Frappe projection lags one version | 69 | HIGHER-PROCESS-RISK |
| search rebuild | 69 | HIGHER-PROCESS-RISK |
| cache loss | 69 | HIGHER-PROCESS-RISK |
| external ID remap | 69 | HIGHER-PROCESS-RISK |
| migration count/hash mismatch | 69 | HIGHER-PROCESS-RISK |
| generic delete denied | 69 | HIGHER-PROCESS-RISK |
| two concurrent expected-version updates | 70 | HIGHER-PROCESS-RISK |
| deadlock retry | 70 | HIGHER-PROCESS-RISK |
| outbox atomic rollback | 70 | HIGHER-PROCESS-RISK |
| missing future partition | 70 | HIGHER-PROCESS-RISK |
| replica lag regulated action uses primary | 70 | HIGHER-PROCESS-RISK |
| large-table migration lock test | 70 | HIGHER-PROCESS-RISK |
| database checksum/index corruption drill | 70 | HIGHER-PROCESS-RISK |
| connection pool saturation | 70 | HIGHER-PROCESS-RISK |
| manual edit projected batch state denied | 71 | HIGHER-PROCESS-RISK |
| out-of-order event ignored | 71 | HIGHER-PROCESS-RISK |
| projection rebuild after DB loss | 71 | HIGHER-PROCESS-RISK |
| GxP API unavailable | 71 | HIGHER-PROCESS-RISK |
| MariaDB restored older than PostgreSQL | 71 | HIGHER-PROCESS-RISK |
| ERPNext absent deployment still functions | 71 | HIGHER-PROCESS-RISK |
| hash mismatch on upload | 72 | HIGHER-PROCESS-RISK |
| malware quarantine | 72 | HIGHER-PROCESS-RISK |
| overwritten provider object detected | 72 | HIGHER-PROCESS-RISK |
| legal hold blocks lifecycle deletion | 72 | HIGHER-PROCESS-RISK |
| cold archive restore | 72 | HIGHER-PROCESS-RISK |
| missing object | 72 | HIGHER-PROCESS-RISK |
| provider migration hash reconciliation | 72 | HIGHER-PROCESS-RISK |
| presigned URL expiry | 72 | HIGHER-PROCESS-RISK |
| DB commit while NATS down | 73 | HIGHER-PROCESS-RISK |
| publish ack lost then duplicate retry | 73 | HIGHER-PROCESS-RISK |
| consumer crash after side effect before ack | 73 | HIGHER-PROCESS-RISK |
| out-of-order aggregate version | 73 | HIGHER-PROCESS-RISK |
| poison event | 73 | HIGHER-PROCESS-RISK |
| schema additive change | 73 | HIGHER-PROCESS-RISK |
| breaking schema blocked | 73 | HIGHER-PROCESS-RISK |
| large evidence ref | 73 | HIGHER-PROCESS-RISK |
| activity retry after timeout | 74 | HIGHER-PROCESS-RISK |
| business validation not retried | 74 | HIGHER-PROCESS-RISK |
| workflow code replay after upgrade | 74 | HIGHER-PROCESS-RISK |
| duplicate start | 74 | HIGHER-PROCESS-RISK |
| signal duplicate/out-of-order | 74 | HIGHER-PROCESS-RISK |
| Temporal outage/recovery | 74 | HIGHER-PROCESS-RISK |
| GxP outage | 74 | HIGHER-PROCESS-RISK |
| continue-as-new | 74 | HIGHER-PROCESS-RISK |
| cross-tenant search | 75 | HIGHER-PROCESS-RISK |
| stale search result then authoritative fetch | 75 | HIGHER-PROCESS-RISK |
| Redis loss | 75 | HIGHER-PROCESS-RISK |
| search engine outage | 75 | HIGHER-PROCESS-RISK |
| rebuild with zero downtime alias switch | 75 | HIGHER-PROCESS-RISK |
| large export authorization | 75 | HIGHER-PROCESS-RISK |
| rule exact-version cache | 75 | HIGHER-PROCESS-RISK |
| backup set | 76 | HIGHER-PROCESS-RISK |
| target | 76 | HIGHER-PROCESS-RISK |
| PITR target | 76 | HIGHER-PROCESS-RISK |
| elapsed time | 76 | HIGHER-PROCESS-RISK |
| integrity checks | 76 | HIGHER-PROCESS-RISK |
| RPO/RTO achieved | 76 | HIGHER-PROCESS-RISK |
| evidence/report | 76 | HIGHER-PROCESS-RISK |
| backup success flag but corrupt restore | 76 | HIGHER-PROCESS-RISK |
| WAL gap | 76 | HIGHER-PROCESS-RISK |
| PITR to 10 minutes before incident | 76 | HIGHER-PROCESS-RISK |
| object evidence missing | 76 | HIGHER-PROCESS-RISK |
| MariaDB older than GxP then projection rebuild | 76 | HIGHER-PROCESS-RISK |
| standby promotion | 76 | HIGHER-PROCESS-RISK |
| split brain prevention | 76 | HIGHER-PROCESS-RISK |
| lost encryption key drill | 76 | HIGHER-PROCESS-RISK |
| RPO exceeded | 76 | HIGHER-PROCESS-RISK |
| fresh cloud install | 77 | HIGHER-PROCESS-RISK |
| air-gapped on-prem install | 77 | HIGHER-PROCESS-RISK |
| NTP missing preflight | 77 | HIGHER-PROCESS-RISK |
| PVC lost pod reschedule | 77 | HIGHER-PROCESS-RISK |
| rolling API upgrade | 77 | HIGHER-PROCESS-RISK |
| worker drains outbox | 77 | HIGHER-PROCESS-RISK |
| DB migration backward compatibility | 77 | HIGHER-PROCESS-RISK |
| failed smoke rollback | 77 | HIGHER-PROCESS-RISK |
| IaC drift | 77 | HIGHER-PROCESS-RISK |
| 250 concurrent synthetic users | 78 | HIGHER-PROCESS-RISK |
| 50 batches/day/plant | 78 | HIGHER-PROCESS-RISK |
| million audit/day load | 78 | HIGHER-PROCESS-RISK |
| DB failover under load | 78 | HIGHER-PROCESS-RISK |
| NATS outage catch-up | 78 | HIGHER-PROCESS-RISK |
| Temporal outage | 78 | HIGHER-PROCESS-RISK |
| search outage critical execution continues | 78 | HIGHER-PROCESS-RISK |
| object store slow upload | 78 | HIGHER-PROCESS-RISK |
| 72h Edge backlog catch-up | 78 | HIGHER-PROCESS-RISK |
| soak memory leak | 78 | HIGHER-PROCESS-RISK |
| performance regression gate | 78 | HIGHER-PROCESS-RISK |
