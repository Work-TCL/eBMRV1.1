# WP-05 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| automatic batch deviation | 26 | HIGHER-PROCESS-RISK |
| planned deviation expiry | 26 | HIGHER-PROCESS-RISK |
| cross-batch investigation | 26 | HIGHER-PROCESS-RISK |
| no assignable cause | 26 | HIGHER-PROCESS-RISK |
| CAPA required | 26 | HIGHER-PROCESS-RISK |
| change required | 26 | HIGHER-PROCESS-RISK |
| extension | 26 | HIGHER-PROCESS-RISK |
| close with missing impact denied | 26 | HIGHER-PROCESS-RISK |
| reopen | 26 | HIGHER-PROCESS-RISK |
| release blocker | 26 | HIGHER-PROCESS-RISK |
| export | 26 | HIGHER-PROCESS-RISK |
| CAPA from deviation | 27 | HIGHER-PROCESS-RISK |
| multi-action dependency | 27 | HIGHER-PROCESS-RISK |
| action without evidence denied | 27 | HIGHER-PROCESS-RISK |
| change dependency | 27 | HIGHER-PROCESS-RISK |
| failed effectiveness | 27 | HIGHER-PROCESS-RISK |
| extension | 27 | HIGHER-PROCESS-RISK |
| repeat deviation after CAPA | 27 | HIGHER-PROCESS-RISK |
| cancel | 27 | HIGHER-PROCESS-RISK |
| reopen | 27 | HIGHER-PROCESS-RISK |
| failed device test | 28 | HIGHER-PROCESS-RISK |
| material NCR | 28 | HIGHER-PROCESS-RISK |
| partial serial disposition | 28 | HIGHER-PROCESS-RISK |
| use-as-is denied/approved | 28 | HIGHER-PROCESS-RISK |
| rework/retest | 28 | HIGHER-PROCESS-RISK |
| scrap | 28 | HIGHER-PROCESS-RISK |
| supplier return | 28 | HIGHER-PROCESS-RISK |
| CAPA trigger | 28 | HIGHER-PROCESS-RISK |
| release block | 28 | HIGHER-PROCESS-RISK |
| recipe change | 29 | HIGHER-PROCESS-RISK |
| software schema change | 29 | HIGHER-PROCESS-RISK |
| supplier change | 29 | HIGHER-PROCESS-RISK |
| label change | 29 | HIGHER-PROCESS-RISK |
| open batch impact | 29 | HIGHER-PROCESS-RISK |
| training prerequisite | 29 | HIGHER-PROCESS-RISK |
| emergency change | 29 | HIGHER-PROCESS-RISK |
| rollback | 29 | HIGHER-PROCESS-RISK |
| cancel | 29 | HIGHER-PROCESS-RISK |
| post-implementation failure | 29 | HIGHER-PROCESS-RISK |
| new SOP release | 30 | HIGHER-PROCESS-RISK |
| future effective date | 30 | HIGHER-PROCESS-RISK |
| obsolete old version | 30 | HIGHER-PROCESS-RISK |
| historical batch opens old version | 30 | HIGHER-PROCESS-RISK |
| controlled copy | 30 | HIGHER-PROCESS-RISK |
| periodic review overdue | 30 | HIGHER-PROCESS-RISK |
| training assignment | 30 | HIGHER-PROCESS-RISK |
| unauthorized access | 30 | HIGHER-PROCESS-RISK |
| migration | 30 | HIGHER-PROCESS-RISK |
| document revision | 31 | HIGHER-PROCESS-RISK |
| failed exam | 31 | HIGHER-PROCESS-RISK |
| qualification expiry during batch | 31 | HIGHER-PROCESS-RISK |
| trainer unqualified | 31 | HIGHER-PROCESS-RISK |
| equivalency | 31 | HIGHER-PROCESS-RISK |
| waiver | 31 | HIGHER-PROCESS-RISK |
| temporary auth cannot bypass | 31 | HIGHER-PROCESS-RISK |
| role transfer | 31 | HIGHER-PROCESS-RISK |
| audit transcript | 31 | HIGHER-PROCESS-RISK |
| incoming reject | 32 | HIGHER-PROCESS-RISK |
| repeat supplier lot issue | 32 | HIGHER-PROCESS-RISK |
| SCAR overdue | 32 | HIGHER-PROCESS-RISK |
| supplier response rejected | 32 | HIGHER-PROCESS-RISK |
| source suspended | 32 | HIGHER-PROCESS-RISK |
| requalification | 32 | HIGHER-PROCESS-RISK |
| failed effectiveness | 32 | HIGHER-PROCESS-RISK |
| CAPA link | 32 | HIGHER-PROCESS-RISK |
| different methodologies | 33 | HIGHER-PROCESS-RISK |
| high risk higher approval | 33 | HIGHER-PROCESS-RISK |
| change triggers review | 33 | HIGHER-PROCESS-RISK |
| complaint signal | 33 | HIGHER-PROCESS-RISK |
| failed mitigation | 33 | HIGHER-PROCESS-RISK |
| version history | 33 | HIGHER-PROCESS-RISK |
| AI cannot accept | 33 | HIGHER-PROCESS-RISK |
| auditor independence | 34 | HIGHER-PROCESS-RISK |
| finding CAPA | 34 | HIGHER-PROCESS-RISK |
| late response | 34 | HIGHER-PROCESS-RISK |
| repeat finding | 34 | HIGHER-PROCESS-RISK |
| reschedule | 34 | HIGHER-PROCESS-RISK |
| report approval | 34 | HIGHER-PROCESS-RISK |
| restricted evidence | 34 | HIGHER-PROCESS-RISK |
| closure incomplete | 34 | HIGHER-PROCESS-RISK |
| oral complaint | 35 | HIGHER-PROCESS-RISK |
| unknown serial | 35 | HIGHER-PROCESS-RISK |
| autoinjector constituent issue | 35 | HIGHER-PROCESS-RISK |
| no-investigation rationale | 35 | HIGHER-PROCESS-RISK |
| prior similar complaints | 35 | HIGHER-PROCESS-RISK |
| reportability due date | 35 | HIGHER-PROCESS-RISK |
| CAPA | 35 | HIGHER-PROCESS-RISK |
| field action trigger | 35 | HIGHER-PROCESS-RISK |
| privacy restriction | 35 | HIGHER-PROCESS-RISK |
| duplicate intake | 35 | HIGHER-PROCESS-RISK |
| export | 35 | HIGHER-PROCESS-RISK |
| material-lot forward trace | 36 | STANDARD-RISK |
| single serial complaint | 36 | STANDARD-RISK |
| DDCP constituent issue | 36 | STANDARD-RISK |
| distribution hold | 36 | STANDARD-RISK |
| consignee snapshot | 36 | STANDARD-RISK |
| return reconciliation | 36 | STANDARD-RISK |
| device correction/removal record | 36 | STANDARD-RISK |
| scope expansion | 36 | STANDARD-RISK |
| CAPA dependency | 36 | STANDARD-RISK |
| closure | 36 | STANDARD-RISK |
| metric version change | 37 | HIGHER-PROCESS-RISK |
| late correction recalculation | 37 | HIGHER-PROCESS-RISK |
| CAPA effectiveness pass/fail | 37 | HIGHER-PROCESS-RISK |
| threshold alert | 37 | HIGHER-PROCESS-RISK |
| drilldown | 37 | HIGHER-PROCESS-RISK |
| site isolation | 37 | HIGHER-PROCESS-RISK |
| AI advisory only | 37 | HIGHER-PROCESS-RISK |
| frozen management snapshot | 37 | HIGHER-PROCESS-RISK |
