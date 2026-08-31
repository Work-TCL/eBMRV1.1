# WP-01 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| unauthorized user | 03 | HIGHER-PROCESS-RISK |
| wrong site | 03 | HIGHER-PROCESS-RISK |
| expired qualification | 03 | HIGHER-PROCESS-RISK |
| invalid state transition | 03 | HIGHER-PROCESS-RISK |
| stale version | 03 | HIGHER-PROCESS-RISK |
| duplicate click/retry | 03 | HIGHER-PROCESS-RISK |
| duplicate ERP/LIMS callback | 03 | HIGHER-PROCESS-RISK |
| missing reason | 03 | HIGHER-PROCESS-RISK |
| missing required signature | 03 | HIGHER-PROCESS-RISK |
| record changed after signature challenge | 03 | HIGHER-PROCESS-RISK |
| signature service outage | 03 | HIGHER-PROCESS-RISK |
| DB rollback | 03 | HIGHER-PROCESS-RISK |
| outbox publisher outage | 03 | HIGHER-PROCESS-RISK |
| projection outage | 03 | HIGHER-PROCESS-RISK |
| concurrency on same batch step | 03 | HIGHER-PROCESS-RISK |
| concurrency on same material reservation | 03 | HIGHER-PROCESS-RISK |
| replayed Edge event | 03 | HIGHER-PROCESS-RISK |
| privileged repair command | 03 | HIGHER-PROCESS-RISK |
| command schema backward compatibility | 03 | HIGHER-PROCESS-RISK |
| restart recovery after commit | 03 | HIGHER-PROCESS-RISK |
| happy path | 03 | HIGHER-PROCESS-RISK |
| authorization denial | 03 | HIGHER-PROCESS-RISK |
| validation failure | 03 | HIGHER-PROCESS-RISK |
| stale/concurrent write | 03 | HIGHER-PROCESS-RISK |
| duplicate/replay where applicable | 03 | HIGHER-PROCESS-RISK |
| dependency outage | 03 | HIGHER-PROCESS-RISK |
| restart/recovery | 03 | HIGHER-PROCESS-RISK |
| data integrity | 03 | HIGHER-PROCESS-RISK |
| audit verification | 03 | HIGHER-PROCESS-RISK |
| signature verification where applicable | 03 | HIGHER-PROCESS-RISK |
| unique signer | 04 | HIGHER-PROCESS-RISK |
| renamed signer history | 04 | HIGHER-PROCESS-RISK |
| disabled signer | 04 | HIGHER-PROCESS-RISK |
| wrong signer challenge | 04 | HIGHER-PROCESS-RISK |
| fresh authentication required | 04 | HIGHER-PROCESS-RISK |
| record changes before completion | 04 | HIGHER-PROCESS-RISK |
| action/meaning mismatch | 04 | HIGHER-PROCESS-RISK |
| challenge expiry | 04 | HIGHER-PROCESS-RISK |
| replay | 04 | HIGHER-PROCESS-RISK |
| duplicate callback | 04 | HIGHER-PROCESS-RISK |
| performer/verifier SoD | 04 | HIGHER-PROCESS-RISK |
| service account attempts signing | 04 | HIGHER-PROCESS-RISK |
| manifestation in UI | 04 | HIGHER-PROCESS-RISK |
| manifestation in PDF/export | 04 | HIGHER-PROCESS-RISK |
| signature linked to exact old version after correction | 04 | HIGHER-PROCESS-RISK |
| customer IdP outage | 04 | HIGHER-PROCESS-RISK |
| auth method policy downgrade | 04 | HIGHER-PROCESS-RISK |
| timezone/display | 04 | HIGHER-PROCESS-RISK |
| history query | 04 | HIGHER-PROCESS-RISK |
| backup/restore retains signature linkage | 04 | HIGHER-PROCESS-RISK |
| happy path | 04 | HIGHER-PROCESS-RISK |
| authorization denial | 04 | HIGHER-PROCESS-RISK |
| validation failure | 04 | HIGHER-PROCESS-RISK |
| stale/concurrent write | 04 | HIGHER-PROCESS-RISK |
| duplicate/replay where applicable | 04 | HIGHER-PROCESS-RISK |
| dependency outage | 04 | HIGHER-PROCESS-RISK |
| restart/recovery | 04 | HIGHER-PROCESS-RISK |
| data integrity | 04 | HIGHER-PROCESS-RISK |
| audit verification | 04 | HIGHER-PROCESS-RISK |
| signature verification where applicable | 04 | HIGHER-PROCESS-RISK |
| create/change/delete-like correction events | 05 | HIGHER-PROCESS-RISK |
| previous value preservation | 05 | HIGHER-PROCESS-RISK |
| reason | 05 | HIGHER-PROCESS-RISK |
| signature link | 05 | HIGHER-PROCESS-RISK |
| human vs integration identity | 05 | HIGHER-PROCESS-RISK |
| event ordering | 05 | HIGHER-PROCESS-RISK |
| late source timestamp | 05 | HIGHER-PROCESS-RISK |
| attempted application UPDATE | 05 | HIGHER-PROCESS-RISK |
| attempted application DELETE | 05 | HIGHER-PROCESS-RISK |
| per-record hash tamper | 05 | HIGHER-PROCESS-RISK |
| missing event tamper | 05 | HIGHER-PROCESS-RISK |
| checkpoint verification | 05 | HIGHER-PROCESS-RISK |
| partition rollover | 05 | HIGHER-PROCESS-RISK |
| backup/restore | 05 | HIGHER-PROCESS-RISK |
| archive/retrieve | 05 | HIGHER-PROCESS-RISK |
| audit export | 05 | HIGHER-PROCESS-RISK |
| role-restricted review | 05 | HIGHER-PROCESS-RISK |
| privileged DB access monitoring | 05 | HIGHER-PROCESS-RISK |
| migration provenance | 05 | HIGHER-PROCESS-RISK |
| performance at target volume | 05 | HIGHER-PROCESS-RISK |
| happy path | 05 | HIGHER-PROCESS-RISK |
| authorization denial | 05 | HIGHER-PROCESS-RISK |
| validation failure | 05 | HIGHER-PROCESS-RISK |
| stale/concurrent write | 05 | HIGHER-PROCESS-RISK |
| duplicate/replay where applicable | 05 | HIGHER-PROCESS-RISK |
| dependency outage | 05 | HIGHER-PROCESS-RISK |
| restart/recovery | 05 | HIGHER-PROCESS-RISK |
| data integrity | 05 | HIGHER-PROCESS-RISK |
| audit verification | 05 | HIGHER-PROCESS-RISK |
| signature verification where applicable | 05 | HIGHER-PROCESS-RISK |
| single-record histories with thousands of events | 05 | HIGHER-PROCESS-RISK |
| tenant with millions/day | 05 | HIGHER-PROCESS-RISK |
| batch audit query | 05 | HIGHER-PROCESS-RISK |
| user/time-range query | 05 | HIGHER-PROCESS-RISK |
| changed-field query | 05 | HIGHER-PROCESS-RISK |
| archive export | 05 | HIGHER-PROCESS-RISK |
| checkpoint generation | 05 | HIGHER-PROCESS-RISK |
| released object write attempt | 06 | HIGHER-PROCESS-RISK |
| master version supersession | 06 | HIGHER-PROCESS-RISK |
| batch snapshot after master changes | 06 | HIGHER-PROCESS-RISK |
| attachment swap attempt | 06 | HIGHER-PROCESS-RISK |
| correction old/new | 06 | HIGHER-PROCESS-RISK |
| void/cancel | 06 | HIGHER-PROCESS-RISK |
| signature remains on old version | 06 | HIGHER-PROCESS-RISK |
| new signature on amendment | 06 | HIGHER-PROCESS-RISK |
| effective-date selection | 06 | HIGHER-PROCESS-RISK |
| obsolete-version issue attempt | 06 | HIGHER-PROCESS-RISK |
| schema upgrade readability | 06 | HIGHER-PROCESS-RISK |
| backup/restore hashes | 06 | HIGHER-PROCESS-RISK |
| archive/retrieve | 06 | HIGHER-PROCESS-RISK |
| DDCP constituent snapshot | 06 | HIGHER-PROCESS-RISK |
| migration provenance | 06 | HIGHER-PROCESS-RISK |
| happy path | 06 | HIGHER-PROCESS-RISK |
| authorization denial | 06 | HIGHER-PROCESS-RISK |
| validation failure | 06 | HIGHER-PROCESS-RISK |
| stale/concurrent write | 06 | HIGHER-PROCESS-RISK |
| duplicate/replay where applicable | 06 | HIGHER-PROCESS-RISK |
| dependency outage | 06 | HIGHER-PROCESS-RISK |
| restart/recovery | 06 | HIGHER-PROCESS-RISK |
| data integrity | 06 | HIGHER-PROCESS-RISK |
| audit verification | 06 | HIGHER-PROCESS-RISK |
| signature verification where applicable | 06 | HIGHER-PROCESS-RISK |
| field order changes produce same hash | 06 | HIGHER-PROCESS-RISK |
| semantic value change produces different hash | 06 | HIGHER-PROCESS-RISK |
| equivalent decimal formatting normalized | 06 | HIGHER-PROCESS-RISK |
| timestamps normalized | 06 | HIGHER-PROCESS-RISK |
| array order behavior defined by field semantics | 06 | HIGHER-PROCESS-RISK |
| null vs missing behavior defined | 06 | HIGHER-PROCESS-RISK |
| user wrong site | 07 | HIGHER-PROCESS-RISK |
| wrong role | 07 | HIGHER-PROCESS-RISK |
| expired qualification | 07 | HIGHER-PROCESS-RISK |
| missing training | 07 | HIGHER-PROCESS-RISK |
| performer=verifier | 07 | HIGHER-PROCESS-RISK |
| author=approver | 07 | HIGHER-PROCESS-RISK |
| temporary role expiry | 07 | HIGHER-PROCESS-RISK |
| break-glass | 07 | HIGHER-PROCESS-RISK |
| disabled user | 07 | HIGHER-PROCESS-RISK |
| role removed during active session | 07 | HIGHER-PROCESS-RISK |
| service account human-signature attempt | 07 | HIGHER-PROCESS-RISK |
| device identity acting as user | 07 | HIGHER-PROCESS-RISK |
| admin release attempt | 07 | HIGHER-PROCESS-RISK |
| support access expiry | 07 | HIGHER-PROCESS-RISK |
| access review output | 07 | HIGHER-PROCESS-RISK |
| customer SSO mapping | 07 | HIGHER-PROCESS-RISK |
| IdP outage behavior | 07 | HIGHER-PROCESS-RISK |
| happy path | 07 | HIGHER-PROCESS-RISK |
| authorization denial | 07 | HIGHER-PROCESS-RISK |
| validation failure | 07 | HIGHER-PROCESS-RISK |
| stale/concurrent write | 07 | HIGHER-PROCESS-RISK |
| duplicate/replay where applicable | 07 | HIGHER-PROCESS-RISK |
| dependency outage | 07 | HIGHER-PROCESS-RISK |
| restart/recovery | 07 | HIGHER-PROCESS-RISK |
| data integrity | 07 | HIGHER-PROCESS-RISK |
| audit verification | 07 | HIGHER-PROCESS-RISK |
| signature verification where applicable | 07 | HIGHER-PROCESS-RISK |
| deterministic repeat | 08 | HIGHER-PROCESS-RISK |
| decimal precision | 08 | HIGHER-PROCESS-RISK |
| every rounding mode used | 08 | HIGHER-PROCESS-RISK |
| min/max boundary | 08 | HIGHER-PROCESS-RISK |
| unit conversion | 08 | HIGHER-PROCESS-RISK |
| invalid unit | 08 | HIGHER-PROCESS-RISK |
| missing input | 08 | HIGHER-PROCESS-RISK |
| null behavior | 08 | HIGHER-PROCESS-RISK |
| effective dates | 08 | HIGHER-PROCESS-RISK |
| superseded rule snapshot | 08 | HIGHER-PROCESS-RISK |
| yield | 08 | HIGHER-PROCESS-RISK |
| potency | 08 | HIGHER-PROCESS-RISK |
| reconciliation | 08 | HIGHER-PROCESS-RISK |
| time-window | 08 | HIGHER-PROCESS-RISK |
| signature policy | 08 | HIGHER-PROCESS-RISK |
| release blocker aggregation | 08 | HIGHER-PROCESS-RISK |
| cache stale-rule test | 08 | HIGHER-PROCESS-RISK |
| engine upgrade replay/golden tests | 08 | HIGHER-PROCESS-RISK |
| happy path | 08 | HIGHER-PROCESS-RISK |
| authorization denial | 08 | HIGHER-PROCESS-RISK |
| validation failure | 08 | HIGHER-PROCESS-RISK |
| stale/concurrent write | 08 | HIGHER-PROCESS-RISK |
| duplicate/replay where applicable | 08 | HIGHER-PROCESS-RISK |
| dependency outage | 08 | HIGHER-PROCESS-RISK |
| restart/recovery | 08 | HIGHER-PROCESS-RISK |
| data integrity | 08 | HIGHER-PROCESS-RISK |
| audit verification | 08 | HIGHER-PROCESS-RISK |
| signature verification where applicable | 08 | HIGHER-PROCESS-RISK |
| nominal | 08 | HIGHER-PROCESS-RISK |
| lower boundary | 08 | HIGHER-PROCESS-RISK |
| upper boundary | 08 | HIGHER-PROCESS-RISK |
| just below/above boundary | 08 | HIGHER-PROCESS-RISK |
| invalid type | 08 | HIGHER-PROCESS-RISK |
| null/missing | 08 | HIGHER-PROCESS-RISK |
| arithmetic error where relevant | 08 | HIGHER-PROCESS-RISK |
