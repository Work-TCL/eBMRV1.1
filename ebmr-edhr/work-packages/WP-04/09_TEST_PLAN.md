# WP-04 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| approved supplier PO | 18 | HIGHER-PROCESS-RISK |
| unapproved source blocked | 18 | HIGHER-PROCESS-RISK |
| supplier approval expires | 18 | HIGHER-PROCESS-RISK |
| conditional source | 18 | HIGHER-PROCESS-RISK |
| distributor vs manufacturer mismatch | 18 | HIGHER-PROCESS-RISK |
| PO revision changes source | 18 | HIGHER-PROCESS-RISK |
| expired certificate | 18 | HIGHER-PROCESS-RISK |
| duplicate external callback | 18 | HIGHER-PROCESS-RISK |
| supplier suspended with open PO | 18 | HIGHER-PROCESS-RISK |
| ERP unavailable | 18 | HIGHER-PROCESS-RISK |
| native procurement mode | 18 | HIGHER-PROCESS-RISK |
| audit/export | 18 | HIGHER-PROCESS-RISK |
| correct receipt | 19 | HIGHER-PROCESS-RISK |
| wrong supplier | 19 | HIGHER-PROCESS-RISK |
| wrong manufacturer | 19 | HIGHER-PROCESS-RISK |
| damaged seal | 19 | HIGHER-PROCESS-RISK |
| missing COA | 19 | HIGHER-PROCESS-RISK |
| quarantine issue attempt | 19 | HIGHER-PROCESS-RISK |
| sampling selected containers | 19 | HIGHER-PROCESS-RISK |
| identity test missing | 19 | HIGHER-PROCESS-RISK |
| supplier COA permitted/not permitted | 19 | HIGHER-PROCESS-RISK |
| release | 19 | HIGHER-PROCESS-RISK |
| reject | 19 | HIGHER-PROCESS-RISK |
| retest due | 19 | HIGHER-PROCESS-RISK |
| partial container disposition | 19 | HIGHER-PROCESS-RISK |
| ERP outage | 19 | HIGHER-PROCESS-RISK |
| stale QA signature | 19 | HIGHER-PROCESS-RISK |
| released lot availability | 20 | HIGHER-PROCESS-RISK |
| quarantine excluded | 20 | HIGHER-PROCESS-RISK |
| expired/retest excluded | 20 | HIGHER-PROCESS-RISK |
| simultaneous reservations | 20 | HIGHER-PROCESS-RISK |
| container split conservation | 20 | HIGHER-PROCESS-RISK |
| incompatible merge | 20 | HIGHER-PROCESS-RISK |
| transfer to wrong status zone | 20 | HIGHER-PROCESS-RISK |
| negative inventory attempt | 20 | HIGHER-PROCESS-RISK |
| FIFO/FEFO deviation | 20 | HIGHER-PROCESS-RISK |
| cycle-count discrepancy | 20 | HIGHER-PROCESS-RISK |
| ERP mismatch | 20 | HIGHER-PROCESS-RISK |
| intersite transfer | 20 | HIGHER-PROCESS-RISK |
| normal balance dispense | 21 | HIGHER-PROCESS-RISK |
| wrong material scan | 21 | HIGHER-PROCESS-RISK |
| quarantine/expired source | 21 | HIGHER-PROCESS-RISK |
| two batches same final stock | 21 | HIGHER-PROCESS-RISK |
| balance calibration expired | 21 | HIGHER-PROCESS-RISK |
| unstable reading | 21 | HIGHER-PROCESS-RISK |
| overweight correction | 21 | HIGHER-PROCESS-RISK |
| multi-lot allowed/disallowed | 21 | HIGHER-PROCESS-RISK |
| potency-adjusted target | 21 | HIGHER-PROCESS-RISK |
| manual fallback allowed/disallowed | 21 | HIGHER-PROCESS-RISK |
| verifier SoD | 21 | HIGHER-PROCESS-RISK |
| pause then retest date passes | 21 | HIGHER-PROCESS-RISK |
| label reprint | 21 | HIGHER-PROCESS-RISK |
| cancel | 21 | HIGHER-PROCESS-RISK |
| full consume | 22 | HIGHER-PROCESS-RISK |
| partial consume | 22 | HIGHER-PROCESS-RISK |
| cross-batch attempt | 22 | HIGHER-PROCESS-RISK |
| return acceptable | 22 | HIGHER-PROCESS-RISK |
| return needs quarantine | 22 | HIGHER-PROCESS-RISK |
| spill | 22 | HIGHER-PROCESS-RISK |
| sample withdrawal | 22 | HIGHER-PROCESS-RISK |
| high-risk adjustment | 22 | HIGHER-PROCESS-RISK |
| self-approval denied | 22 | HIGHER-PROCESS-RISK |
| destruction with witness | 22 | HIGHER-PROCESS-RISK |
| third-party destruction | 22 | HIGHER-PROCESS-RISK |
| failed reconciliation | 22 | HIGHER-PROCESS-RISK |
| correction/reversal | 22 | HIGHER-PROCESS-RISK |
| ERP retry duplicate | 22 | HIGHER-PROCESS-RISK |
| batch completion blocked | 22 | HIGHER-PROCESS-RISK |
| specification | 23 | HIGHER-PROCESS-RISK |
| test code/name | 23 | HIGHER-PROCESS-RISK |
| method version | 23 | HIGHER-PROCESS-RISK |
| result data type | 23 | HIGHER-PROCESS-RISK |
| acceptance rule | 23 | HIGHER-PROCESS-RISK |
| required flag | 23 | HIGHER-PROCESS-RISK |
| release-blocking flag | 23 | HIGHER-PROCESS-RISK |
| OOS/OOT policies | 23 | HIGHER-PROCESS-RISK |
| review policy | 23 | HIGHER-PROCESS-RISK |
| sample ID | 23 | HIGHER-PROCESS-RISK |
| test definition/version | 23 | HIGHER-PROCESS-RISK |
| assigned analyst | 23 | HIGHER-PROCESS-RISK |
| state/version | 23 | HIGHER-PROCESS-RISK |
| started/completed/reviewed times | 23 | HIGHER-PROCESS-RISK |
| blocking status | 23 | HIGHER-PROCESS-RISK |
| test order | 23 | HIGHER-PROCESS-RISK |
| instrument/equipment ID | 23 | HIGHER-PROCESS-RISK |
| analyst | 23 | HIGHER-PROCESS-RISK |
| sample amount | 23 | HIGHER-PROCESS-RISK |
| reference standards/reagents | 23 | HIGHER-PROCESS-RISK |
| system suitability | 23 | HIGHER-PROCESS-RISK |
| raw-data evidence IDs | 23 | HIGHER-PROCESS-RISK |
| calculation version | 23 | HIGHER-PROCESS-RISK |
| numeric single value | 23 | HIGHER-PROCESS-RISK |
| numeric replicate series | 23 | HIGHER-PROCESS-RISK |
| calculated numeric | 23 | HIGHER-PROCESS-RISK |
| qualitative enum | 23 | HIGHER-PROCESS-RISK |
| pass/fail | 23 | HIGHER-PROCESS-RISK |
| text/observation | 23 | HIGHER-PROCESS-RISK |
| count | 23 | HIGHER-PROCESS-RISK |
| range | 23 | HIGHER-PROCESS-RISK |
| multidimensional JSON schema for approved device tests | 23 | HIGHER-PROCESS-RISK |
| numeric pass | 23 | HIGHER-PROCESS-RISK |
| numeric OOS | 23 | HIGHER-PROCESS-RISK |
| qualitative fail | 23 | HIGHER-PROCESS-RISK |
| replicate calculation | 23 | HIGHER-PROCESS-RISK |
| missing raw data | 23 | HIGHER-PROCESS-RISK |
| wrong method version | 23 | HIGHER-PROCESS-RISK |
| analyst qualification expired | 23 | HIGHER-PROCESS-RISK |
| instrument calibration expired | 23 | HIGHER-PROCESS-RISK |
| system suitability failed | 23 | HIGHER-PROCESS-RISK |
| result correction | 23 | HIGHER-PROCESS-RISK |
| second-person reviewer edits attempt | 23 | HIGHER-PROCESS-RISK |
| OOS then retest | 23 | HIGHER-PROCESS-RISK |
| OOT within specification | 23 | HIGHER-PROCESS-RISK |
| late instrument file | 23 | HIGHER-PROCESS-RISK |
| sample chain of custody | 23 | HIGHER-PROCESS-RISK |
| duplicate test submission | 23 | HIGHER-PROCESS-RISK |
| backup/restore evidence | 23 | HIGHER-PROCESS-RISK |
| sample create | 24 | HIGHER-PROCESS-RISK |
| duplicate sample retry | 24 | HIGHER-PROCESS-RISK |
| pass result | 24 | HIGHER-PROCESS-RISK |
| OOS result | 24 | HIGHER-PROCESS-RISK |
| result revision | 24 | HIGHER-PROCESS-RISK |
| stale version | 24 | HIGHER-PROCESS-RISK |
| wrong method | 24 | HIGHER-PROCESS-RISK |
| wrong UOM | 24 | HIGHER-PROCESS-RISK |
| unknown sample | 24 | HIGHER-PROCESS-RISK |
| duplicate event | 24 | HIGHER-PROCESS-RISK |
| out-of-order events | 24 | HIGHER-PROCESS-RISK |
| attachment failure | 24 | HIGHER-PROCESS-RISK |
| source auth failure | 24 | HIGHER-PROCESS-RISK |
| LIMS outage | 24 | HIGHER-PROCESS-RISK |
| dead-letter replay | 24 | HIGHER-PROCESS-RISK |
| reconciliation missing result | 24 | HIGHER-PROCESS-RISK |
| administrator attempts result edit | 24 | HIGHER-PROCESS-RISK |
| justification | 25 | HIGHER-PROCESS-RISK |
| number of retests | 25 | HIGHER-PROCESS-RISK |
| method | 25 | HIGHER-PROCESS-RISK |
| analyst/instrument criteria | 25 | HIGHER-PROCESS-RISK |
| interpretation rule | 25 | HIGHER-PROCESS-RISK |
| approver signature | 25 | HIGHER-PROCESS-RISK |
| status | 25 | HIGHER-PROCESS-RISK |
| unlimited “try again” button | 25 | HIGHER-PROCESS-RISK |
| deleting failing injections/readings | 25 | HIGHER-PROCESS-RISK |
| replacing initial result field | 25 | HIGHER-PROCESS-RISK |
| selecting only favorable results without method/procedure basis | 25 | HIGHER-PROCESS-RISK |
| undocumented retesting | 25 | HIGHER-PROCESS-RISK |
| automatic OOS | 25 | HIGHER-PROCESS-RISK |
| attempt to suppress OOS | 25 | HIGHER-PROCESS-RISK |
| proven calculation error | 25 | HIGHER-PROCESS-RISK |
| unproven lab error | 25 | HIGHER-PROCESS-RISK |
| retest without authorization | 25 | HIGHER-PROCESS-RISK |
| configured retest count exceeded | 25 | HIGHER-PROCESS-RISK |
| passing retest does not replace original | 25 | HIGHER-PROCESS-RISK |
| resample without rationale | 25 | HIGHER-PROCESS-RISK |
| result correction vs retest distinction | 25 | HIGHER-PROCESS-RISK |
| OOS holds batch | 25 | HIGHER-PROCESS-RISK |
| CAPA link | 25 | HIGHER-PROCESS-RISK |
| confirmed OOS reject | 25 | HIGHER-PROCESS-RISK |
| OOT within spec | 25 | HIGHER-PROCESS-RISK |
| repeated OOT escalation | 25 | HIGHER-PROCESS-RISK |
| LIMS-managed OOS status sync | 25 | HIGHER-PROCESS-RISK |
| closed OOS reopened | 25 | HIGHER-PROCESS-RISK |
| reviewer/analyst SoD | 25 | HIGHER-PROCESS-RISK |
| audit/export | 25 | HIGHER-PROCESS-RISK |
