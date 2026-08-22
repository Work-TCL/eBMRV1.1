# WP-02 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| basic drug+device product release | 09 | HIGHER-PROCESS-RISK |
| missing constituent | 09 | HIGHER-PROCESS-RISK |
| incompatible constituents | 09 | HIGHER-PROCESS-RISK |
| future effective date | 09 | HIGHER-PROCESS-RISK |
| suspended product | 09 | HIGHER-PROCESS-RISK |
| wrong manufacturing site | 09 | HIGHER-PROCESS-RISK |
| clone does not inherit approval | 09 | HIGHER-PROCESS-RISK |
| product change creates version | 09 | HIGHER-PROCESS-RISK |
| old batch resolves old product version | 09 | HIGHER-PROCESS-RISK |
| UDI-required profile incomplete | 09 | HIGHER-PROCESS-RISK |
| sterile-required profile missing | 09 | HIGHER-PROCESS-RISK |
| concurrent product update | 09 | HIGHER-PROCESS-RISK |
| external mapping duplicate | 09 | HIGHER-PROCESS-RISK |
| unauthorized release | 09 | HIGHER-PROCESS-RISK |
| release signature stale after draft change | 09 | HIGHER-PROCESS-RISK |
| export/version comparison | 09 | HIGHER-PROCESS-RISK |
| normal sequential recipe | 10 | HIGHER-PROCESS-RISK |
| parallel/join | 10 | HIGHER-PROCESS-RISK |
| conditional branch | 10 | HIGHER-PROCESS-RISK |
| cycle rejection | 10 | HIGHER-PROCESS-RISK |
| unreachable step | 10 | HIGHER-PROCESS-RISK |
| missing material spec | 10 | HIGHER-PROCESS-RISK |
| missing rule | 10 | HIGHER-PROCESS-RISK |
| obsolete equipment policy | 10 | HIGHER-PROCESS-RISK |
| wrong product version | 10 | HIGHER-PROCESS-RISK |
| independent approval | 10 | HIGHER-PROCESS-RISK |
| recipe changed after signature challenge | 10 | HIGHER-PROCESS-RISK |
| issue snapshot immutable | 10 | HIGHER-PROCESS-RISK |
| master superseded while batch active | 10 | HIGHER-PROCESS-RISK |
| manual fallback rule | 10 | HIGHER-PROCESS-RISK |
| rework route | 10 | HIGHER-PROCESS-RISK |
| sterile profile requirement | 10 | HIGHER-PROCESS-RISK |
| batch size variant | 10 | HIGHER-PROCESS-RISK |
| recipe compare | 10 | HIGHER-PROCESS-RISK |
| sequential normal batch | 11 | HIGHER-PROCESS-RISK |
| parallel steps | 11 | HIGHER-PROCESS-RISK |
| conditional branch | 11 | HIGHER-PROCESS-RISK |
| duplicate step start | 11 | HIGHER-PROCESS-RISK |
| simultaneous result edits | 11 | HIGHER-PROCESS-RISK |
| stale version | 11 | HIGHER-PROCESS-RISK |
| browser refresh | 11 | HIGHER-PROCESS-RISK |
| worker crash | 11 | HIGHER-PROCESS-RISK |
| event-bus outage | 11 | HIGHER-PROCESS-RISK |
| material failure | 11 | HIGHER-PROCESS-RISK |
| calibration expiration mid-batch | 11 | HIGHER-PROCESS-RISK |
| qualification expiration before next step | 11 | HIGHER-PROCESS-RISK |
| manual fallback | 11 | HIGHER-PROCESS-RISK |
| device duplicate/replay | 11 | HIGHER-PROCESS-RISK |
| hold/resume | 11 | HIGHER-PROCESS-RISK |
| timer breach | 11 | HIGHER-PROCESS-RISK |
| correction | 11 | HIGHER-PROCESS-RISK |
| rework route | 11 | HIGHER-PROCESS-RISK |
| abort | 11 | HIGHER-PROCESS-RISK |
| production completion blocker | 11 | HIGHER-PROCESS-RISK |
| unit/serial scope | 11 | HIGHER-PROCESS-RISK |
| unit/lot scope | 12 | HIGHER-PROCESS-RISK |
| test specification version | 12 | HIGHER-PROCESS-RISK |
| test code | 12 | HIGHER-PROCESS-RISK |
| tester equipment ID | 12 | HIGHER-PROCESS-RISK |
| result values | 12 | HIGHER-PROCESS-RISK |
| pass/fail | 12 | HIGHER-PROCESS-RISK |
| raw evidence reference | 12 | HIGHER-PROCESS-RISK |
| rule evaluation | 12 | HIGHER-PROCESS-RISK |
| result version/supersession | 12 | HIGHER-PROCESS-RISK |
| unit creation | 12 | HIGHER-PROCESS-RISK |
| duplicate serial | 12 | HIGHER-PROCESS-RISK |
| component lot trace | 12 | HIGHER-PROCESS-RISK |
| wrong component | 12 | HIGHER-PROCESS-RISK |
| tester calibration invalid | 12 | HIGHER-PROCESS-RISK |
| failed test → NCR | 12 | HIGHER-PROCESS-RISK |
| retest retains original | 12 | HIGHER-PROCESS-RISK |
| rework | 12 | HIGHER-PROCESS-RISK |
| scrap | 12 | HIGHER-PROCESS-RISK |
| shared evidence inheritance | 12 | HIGHER-PROCESS-RISK |
| UDI recording | 12 | HIGHER-PROCESS-RISK |
| batch-to-unit drug linkage | 12 | HIGHER-PROCESS-RISK |
| high-volume bulk results | 12 | HIGHER-PROCESS-RISK |
| unit correction | 12 | HIGHER-PROCESS-RISK |
| device export | 12 | HIGHER-PROCESS-RISK |
