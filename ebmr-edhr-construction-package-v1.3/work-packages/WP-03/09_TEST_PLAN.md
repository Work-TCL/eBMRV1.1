# WP-03 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| simple material→batch | 13 | HIGHER-PROCESS-RISK |
| drug batch→device serial | 13 | HIGHER-PROCESS-RISK |
| many component lots | 13 | HIGHER-PROCESS-RISK |
| split/merge | 13 | HIGHER-PROCESS-RISK |
| partial container | 13 | HIGHER-PROCESS-RISK |
| rework | 13 | HIGHER-PROCESS-RISK |
| wrong edge correction | 13 | HIGHER-PROCESS-RISK |
| cycle protection | 13 | HIGHER-PROCESS-RISK |
| tenant isolation | 13 | HIGHER-PROCESS-RISK |
| 100k serial affected query | 13 | HIGHER-PROCESS-RISK |
| saved recall impact | 13 | HIGHER-PROCESS-RISK |
| migration provenance | 13 | HIGHER-PROCESS-RISK |
| package hierarchy | 13 | HIGHER-PROCESS-RISK |
| no exceptions normal batch | 14 | HIGHER-PROCESS-RISK |
| hidden missing field caught by completeness | 14 | HIGHER-PROCESS-RISK |
| correction visible | 14 | HIGHER-PROCESS-RISK |
| manual override visible | 14 | HIGHER-PROCESS-RISK |
| unresolved deviation | 14 | HIGHER-PROCESS-RISK |
| calibration exception | 14 | HIGHER-PROCESS-RISK |
| environmental excursion | 14 | HIGHER-PROCESS-RISK |
| label mismatch | 14 | HIGHER-PROCESS-RISK |
| failed reconciliation | 14 | HIGHER-PROCESS-RISK |
| invalid signature | 14 | HIGHER-PROCESS-RISK |
| source changes after review signature | 14 | HIGHER-PROCESS-RISK |
| multi-reviewer | 14 | HIGHER-PROCESS-RISK |
| integrity checkpoint failure | 14 | HIGHER-PROCESS-RISK |
| fully eligible release | 15 | HIGHER-PROCESS-RISK |
| open deviation | 15 | HIGHER-PROCESS-RISK |
| missing QC | 15 | HIGHER-PROCESS-RISK |
| stale QA review | 15 | HIGHER-PROCESS-RISK |
| missing material genealogy | 15 | HIGHER-PROCESS-RISK |
| equipment exception | 15 | HIGHER-PROCESS-RISK |
| sterile excursion | 15 | HIGHER-PROCESS-RISK |
| failed label reconciliation | 15 | HIGHER-PROCESS-RISK |
| yield failure | 15 | HIGHER-PROCESS-RISK |
| same user SoD conflict | 15 | HIGHER-PROCESS-RISK |
| record changes during signature | 15 | HIGHER-PROCESS-RISK |
| ERP outage after release | 15 | HIGHER-PROCESS-RISK |
| reject | 15 | HIGHER-PROCESS-RISK |
| rework | 15 | HIGHER-PROCESS-RISK |
| partial release disabled | 15 | HIGHER-PROCESS-RISK |
| DDCP constituent released but final not released | 15 | HIGHER-PROCESS-RISK |
| correct label | 16 | HIGHER-PROCESS-RISK |
| wrong label scan | 16 | HIGHER-PROCESS-RISK |
| obsolete label | 16 | HIGHER-PROCESS-RISK |
| duplicate serial | 16 | HIGHER-PROCESS-RISK |
| controlled reprint | 16 | HIGHER-PROCESS-RISK |
| excessive labels | 16 | HIGHER-PROCESS-RISK |
| discrepancy outside limit | 16 | HIGHER-PROCESS-RISK |
| line clearance incomplete | 16 | HIGHER-PROCESS-RISK |
| label return | 16 | HIGHER-PROCESS-RISK |
| destruction | 16 | HIGHER-PROCESS-RISK |
| package aggregation | 16 | HIGHER-PROCESS-RISK |
| wrong aggregation correction | 16 | HIGHER-PROCESS-RISK |
| packaging material rejected | 16 | HIGHER-PROCESS-RISK |
| printer retry/idempotency | 16 | HIGHER-PROCESS-RISK |
| completion blocker | 16 | HIGHER-PROCESS-RISK |
| normal yield | 17 | HIGHER-PROCESS-RISK |
| zero theoretical quantity | 17 | HIGHER-PROCESS-RISK |
| decimal precision | 17 | HIGHER-PROCESS-RISK |
| UOM conversion | 17 | HIGHER-PROCESS-RISK |
| min boundary | 17 | HIGHER-PROCESS-RISK |
| max boundary | 17 | HIGHER-PROCESS-RISK |
| below/above tolerance | 17 | HIGHER-PROCESS-RISK |
| independent verification | 17 | HIGHER-PROCESS-RISK |
| potency adjustment | 17 | HIGHER-PROCESS-RISK |
| material return | 17 | HIGHER-PROCESS-RISK |
| sample/destruction | 17 | HIGHER-PROCESS-RISK |
| rework | 17 | HIGHER-PROCESS-RISK |
| label discrepancy | 17 | HIGHER-PROCESS-RISK |
| component scrap | 17 | HIGHER-PROCESS-RISK |
| ERP discrepancy | 17 | HIGHER-PROCESS-RISK |
| correction recalculation | 17 | HIGHER-PROCESS-RISK |
| old rule snapshot | 17 | HIGHER-PROCESS-RISK |
| large serial aggregation | 17 | HIGHER-PROCESS-RISK |
