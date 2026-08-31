# WP-00 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| signatures | 02 | N/A |
| audit | 02 | N/A |
| record locking | 02 | N/A |
| recipe release | 02 | N/A |
| batch execution | 02 | N/A |
| calculations | 02 | N/A |
| genealogy | 02 | N/A |
| material eligibility | 02 | N/A |
| QA release | 02 | N/A |
| data migration | 02 | N/A |
| backup/restore | 02 | N/A |
| integration result acceptance | 02 | N/A |
| unit | 02 | N/A |
| property/rule tests | 02 | N/A |
| contract | 02 | N/A |
| workflow replay | 02 | N/A |
| integration | 02 | N/A |
| database migration | 02 | N/A |
| security | 02 | N/A |
| concurrency | 02 | N/A |
| idempotency | 02 | N/A |
| failure/recovery | 02 | N/A |
| audit-integrity | 02 | N/A |
| signature | 02 | N/A |
| negative | 02 | N/A |
| performance | 02 | N/A |
| validation scenario | 02 | N/A |
| TypeScript strict compilation | 97 | HIGHER-PROCESS-RISK |
| Python typing/static checks | 97 | HIGHER-PROCESS-RISK |
| float arithmetic rejection in regulated calculation module | 97 | HIGHER-PROCESS-RISK |
| direct GxP DB access from Frappe blocked | 97 | HIGHER-PROCESS-RISK |
| secret-in-log negative test | 97 | HIGHER-PROCESS-RISK |
| dynamic SQL/eval forbidden scan | 97 | HIGHER-PROCESS-RISK |
| transaction/external-call code review rule | 97 | HIGHER-PROCESS-RISK |
| generated client drift test | 97 | HIGHER-PROCESS-RISK |
| agent tries direct Postgres access from Frappe | 98 | HIGHER-PROCESS-RISK |
| agent tries audit DELETE | 98 | HIGHER-PROCESS-RISK |
| missing regulated behavior creates SPEC_GAP | 98 | HIGHER-PROCESS-RISK |
| new npm dependency blocked before approval | 98 | HIGHER-PROCESS-RISK |
| breaking event change blocked | 98 | HIGHER-PROCESS-RISK |
| claimed test run ID absent | 98 | HIGHER-PROCESS-RISK |
| prompt injection in issue/comment ignored | 98 | HIGHER-PROCESS-RISK |
| core Frappe patch rejected | 98 | HIGHER-PROCESS-RISK |
| direct push protected branch rejected | 99 | HIGHER-PROCESS-RISK |
| missing CODEOWNER approval | 99 | HIGHER-PROCESS-RISK |
| failed CI merge blocked | 99 | HIGHER-PROCESS-RISK |
| hotfix forward-merge check | 99 | HIGHER-PROCESS-RISK |
| secret committed blocks PR | 99 | HIGHER-PROCESS-RISK |
| release tag source mismatch | 99 | HIGHER-PROCESS-RISK |
| bot personal PAT prohibited | 99 | HIGHER-PROCESS-RISK |
| branch from stale release conflict | 99 | HIGHER-PROCESS-RISK |
| drop regulated column blocked | 100 | HIGHER-PROCESS-RISK |
| large NOT NULL migration expand-contract | 100 | HIGHER-PROCESS-RISK |
| chunked backfill resume | 100 | HIGHER-PROCESS-RISK |
| migration checksum drift | 100 | HIGHER-PROCESS-RISK |
| rolling old/new app compatibility | 100 | HIGHER-PROCESS-RISK |
| MariaDB projection rebuild | 100 | HIGHER-PROCESS-RISK |
| failed concurrent index | 100 | HIGHER-PROCESS-RISK |
| PITR readiness check | 100 | HIGHER-PROCESS-RISK |
| required request field breaking change | 101 | HIGHER-PROCESS-RISK |
| optional response field compatible | 101 | HIGHER-PROCESS-RISK |
| duplicate idempotency key same payload | 101 | HIGHER-PROCESS-RISK |
| same key different payload conflict | 101 | HIGHER-PROCESS-RISK |
| event replay duplicate | 101 | HIGHER-PROCESS-RISK |
| enum evolution | 101 | HIGHER-PROCESS-RISK |
| consumer test failure | 101 | HIGHER-PROCESS-RISK |
| deprecated endpoint telemetry | 101 | HIGHER-PROCESS-RISK |
| unit/property rule vectors | 102 | HIGHER-PROCESS-RISK |
| real PostgreSQL repository constraints | 102 | HIGHER-PROCESS-RISK |
| API BOLA negative tests | 102 | HIGHER-PROCESS-RISK |
| outbox duplicate consumer crash scenario | 102 | HIGHER-PROCESS-RISK |
| Temporal replay compatibility | 102 | HIGHER-PROCESS-RISK |
| migration previous-version matrix | 102 | HIGHER-PROCESS-RISK |
| flaky critical test | 102 | HIGHER-PROCESS-RISK |
| CI evidence imported into validation | 102 | HIGHER-PROCESS-RISK |
| untrusted PR cannot read prod secret | 103 | HIGHER-PROCESS-RISK |
| build artifact promoted without rebuild | 103 | HIGHER-PROCESS-RISK |
| breaking contract blocks | 103 | HIGHER-PROCESS-RISK |
| migration previous-version dry run | 103 | HIGHER-PROCESS-RISK |
| validated authorization mismatch blocks prod | 103 | HIGHER-PROCESS-RISK |
| smoke fail aborts | 103 | HIGHER-PROCESS-RISK |
| rollback after compatible schema | 103 | HIGHER-PROCESS-RISK |
| hotfix retains evidence | 103 | HIGHER-PROCESS-RISK |
| unknown license blocked | 104 | HIGHER-PROCESS-RISK |
| copyleft review | 104 | HIGHER-PROCESS-RISK |
| transitive package surprise | 104 | HIGHER-PROCESS-RISK |
| critical CVE | 104 | HIGHER-PROCESS-RISK |
| known-exploited package priority | 104 | HIGHER-PROCESS-RISK |
| SBOM artifact digest match | 104 | HIGHER-PROCESS-RISK |
| third-party notices | 104 | HIGHER-PROCESS-RISK |
| AI model license appears in AI register | 104 | HIGHER-PROCESS-RISK |
