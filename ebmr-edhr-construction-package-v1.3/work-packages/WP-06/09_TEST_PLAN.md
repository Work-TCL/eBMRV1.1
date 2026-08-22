# WP-06 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| valid equipment use | 38 | HIGHER-PROCESS-RISK |
| expired calibration blocks step | 38 | HIGHER-PROCESS-RISK |
| as-found OOT impact | 38 | HIGHER-PROCESS-RISK |
| maintenance then calibration required | 38 | HIGHER-PROCESS-RISK |
| breakdown during batch | 38 | HIGHER-PROCESS-RISK |
| wrong equipment class | 38 | HIGHER-PROCESS-RISK |
| relocation | 38 | HIGHER-PROCESS-RISK |
| firmware change | 38 | HIGHER-PROCESS-RISK |
| CMMS outage | 38 | HIGHER-PROCESS-RISK |
| concurrent reservation | 38 | HIGHER-PROCESS-RISK |
| retirement | 38 | HIGHER-PROCESS-RISK |
| normal clean | 39 | HIGHER-PROCESS-RISK |
| dirty hold exceeded | 39 | HIGHER-PROCESS-RISK |
| clean hold expires | 39 | HIGHER-PROCESS-RISK |
| swab failure | 39 | HIGHER-PROCESS-RISK |
| wrong cleaning procedure | 39 | HIGHER-PROCESS-RISK |
| previous label remains | 39 | HIGHER-PROCESS-RISK |
| wrong equipment installed | 39 | HIGHER-PROCESS-RISK |
| campaign cleaning | 39 | HIGHER-PROCESS-RISK |
| CIP integration | 39 | HIGHER-PROCESS-RISK |
| second-person verification | 39 | HIGHER-PROCESS-RISK |
| start with failed area readiness | 40 | HIGHER-PROCESS-RISK |
| unqualified operator | 40 | HIGHER-PROCESS-RISK |
| expired sterile component status | 40 | HIGHER-PROCESS-RISK |
| routine intervention | 40 | HIGHER-PROCESS-RISK |
| unplanned intervention | 40 | HIGHER-PROCESS-RISK |
| hold time exceeded | 40 | HIGHER-PROCESS-RISK |
| pressure excursion | 40 | HIGHER-PROCESS-RISK |
| filter integrity failure | 40 | HIGHER-PROCESS-RISK |
| RABS glove issue | 40 | HIGHER-PROCESS-RISK |
| completion with unresolved event denied | 40 | HIGHER-PROCESS-RISK |
| normal viable sample | 41 | HIGHER-PROCESS-RISK |
| action-limit excursion | 41 | HIGHER-PROCESS-RISK |
| resample cannot hide excursion | 41 | HIGHER-PROCESS-RISK |
| continuous pressure gap | 41 | HIGHER-PROCESS-RISK |
| sensor quality bad | 41 | HIGHER-PROCESS-RISK |
| unqualified instrument | 41 | HIGHER-PROCESS-RISK |
| organism ID | 41 | HIGHER-PROCESS-RISK |
| batch correlation | 41 | HIGHER-PROCESS-RISK |
| area readiness blocked | 41 | HIGHER-PROCESS-RISK |
| historian outage | 41 | HIGHER-PROCESS-RISK |
| valid autoclave cycle | 42 | HIGHER-PROCESS-RISK |
| wrong load pattern | 42 | HIGHER-PROCESS-RISK |
| controller alarm | 42 | HIGHER-PROCESS-RISK |
| cycle critical parameter fail | 42 | HIGHER-PROCESS-RISK |
| rerun without investigation denied | 42 | HIGHER-PROCESS-RISK |
| CIP rinse failure | 42 | HIGHER-PROCESS-RISK |
| pre-use filter fail | 42 | HIGHER-PROCESS-RISK |
| post-use filter fail | 42 | HIGHER-PROCESS-RISK |
| external sterilizer evidence | 42 | HIGHER-PROCESS-RISK |
| sterile status expiry | 42 | HIGHER-PROCESS-RISK |
| release blocker | 42 | HIGHER-PROCESS-RISK |
| enrollment token replay | 43 | HIGHER-PROCESS-RISK |
| wrong tenant/site config | 43 | HIGHER-PROCESS-RISK |
| invalid config signature | 43 | HIGHER-PROCESS-RISK |
| connector crash while others continue | 43 | HIGHER-PROCESS-RISK |
| gateway reboot with pending buffer | 43 | HIGHER-PROCESS-RISK |
| duplicate server acknowledgements | 43 | HIGHER-PROCESS-RISK |
| upstream outage 24h/72h synthetic | 43 | HIGHER-PROCESS-RISK |
| disk full threshold | 43 | HIGHER-PROCESS-RISK |
| corrupted SQLite/outbox recovery strategy | 43 | HIGHER-PROCESS-RISK |
| clock offset > threshold | 43 | HIGHER-PROCESS-RISK |
| expired certificate | 43 | HIGHER-PROCESS-RISK |
| software update rollback | 43 | HIGHER-PROCESS-RISK |
| protocol plugin attempts forbidden filesystem access | 43 | HIGHER-PROCESS-RISK |
| command channel remains disabled without profile | 43 | HIGHER-PROCESS-RISK |
| connect/auth failure | 44 | HIGHER-PROCESS-RISK |
| malformed configuration | 44 | HIGHER-PROCESS-RISK |
| read timeout | 44 | HIGHER-PROCESS-RISK |
| reconnect | 44 | HIGHER-PROCESS-RISK |
| bad native quality | 44 | HIGHER-PROCESS-RISK |
| mapping conversion | 44 | HIGHER-PROCESS-RISK |
| duplicate/replayed source event where detectable | 44 | HIGHER-PROCESS-RISK |
| graceful shutdown | 44 | HIGHER-PROCESS-RISK |
| secret redaction | 44 | HIGHER-PROCESS-RISK |
| driver crash isolation | 44 | HIGHER-PROCESS-RISK |
| protocol simulator test | 44 | HIGHER-PROCESS-RISK |
| same signal on OPC UA and Modbus maps identically | 47 | HIGHER-PROCESS-RISK |
| ambiguous batch context blocks step result | 47 | HIGHER-PROCESS-RISK |
| signal late after batch close | 47 | HIGHER-PROCESS-RISK |
| historian unavailable | 47 | HIGHER-PROCESS-RISK |
| mapping superseded during active batch | 47 | HIGHER-PROCESS-RISK |
| backfill does not look live | 47 | HIGHER-PROCESS-RISK |
| alarm creates deviation rule | 47 | HIGHER-PROCESS-RISK |
| generic write endpoint absent | 47 | HIGHER-PROCESS-RISK |
| command wrong role/signature/state | 47 | HIGHER-PROCESS-RISK |
| local PLC interlock denies command | 47 | HIGHER-PROCESS-RISK |
| successful write but readback mismatch | 47 | HIGHER-PROCESS-RISK |
| retry command does not duplicate effect when device supports idempotency/command correlation | 47 | HIGHER-PROCESS-RISK |
