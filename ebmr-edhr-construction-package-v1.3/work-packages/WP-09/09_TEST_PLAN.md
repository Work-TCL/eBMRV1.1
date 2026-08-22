# WP-09 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| complaint already linked | 58 | HIGHER-PROCESS-RISK |
| unknown serial later resolved | 58 | HIGHER-PROCESS-RISK |
| follow-up changes classification | 58 | HIGHER-PROCESS-RISK |
| duplicate source reports linked without deletion | 58 | HIGHER-PROCESS-RISK |
| same-lot cluster | 58 | HIGHER-PROCESS-RISK |
| denominator unavailable | 58 | HIGHER-PROCESS-RISK |
| historical metric formula version remains reproducible | 58 | HIGHER-PROCESS-RISK |
| AI suggestion rejected by reviewer | 58 | HIGHER-PROCESS-RISK |
| signal creates CAPA | 58 | HIGHER-PROCESS-RISK |
| signal creates Field Action | 58 | HIGHER-PROCESS-RISK |
| DDCP case creates multiple reportability tracks | 58 | HIGHER-PROCESS-RISK |
| concurrent follow-up during medical review forces refresh | 58 | HIGHER-PROCESS-RISK |
| privacy role denial | 58 | HIGHER-PROCESS-RISK |
| device death candidate and 30-day calculation | 59 | HIGHER-PROCESS-RISK |
| qualifying 5-day device track | 59 | HIGHER-PROCESS-RISK |
| drug serious+unexpected 15-day candidate | 59 | HIGHER-PROCESS-RISK |
| device-authorized DDCP drug constituent uses configured Part 4 30-day rule | 59 | HIGHER-PROCESS-RISK |
| missing clock start blocks due date | 59 | HIGHER-PROCESS-RISK |
| one case has multiple independent tracks | 59 | HIGHER-PROCESS-RISK |
| Part 4 same-event dedupe false because deadline differs | 59 | HIGHER-PROCESS-RISK |
| eMDR schema failure | 59 | HIGHER-PROCESS-RISK |
| transport success + FDA rejection | 59 | HIGHER-PROCESS-RISK |
| timeout after ESG transmission | 59 | HIGHER-PROCESS-RISK |
| E2B R2 before effective transition | 59 | HIGHER-PROCESS-RISK |
| E2B R3 after effective transition | 59 | HIGHER-PROCESS-RISK |
| follow-up creates new report | 59 | HIGHER-PROCESS-RISK |
| signed not-reportable decision | 59 | HIGHER-PROCESS-RISK |
| duplicate initial submission blocked | 59 | HIGHER-PROCESS-RISK |
| two constituent applicants create correct sharing recipients | 60 | HIGHER-PROCESS-RISK |
| missing recipient blocks completion | 60 | HIGHER-PROCESS-RISK |
| 5-calendar-day sharing deadline | 60 | HIGHER-PROCESS-RISK |
| reportable field action creates 10-working-day 806 obligation | 60 | HIGHER-PROCESS-RISK |
| nonreportable correction/removal creates controlled 806.20 record | 60 | HIGHER-PROCESS-RISK |
| scope expansion creates amendment task | 60 | HIGHER-PROCESS-RISK |
| NDA Field Alert 3-working-day calculation | 60 | HIGHER-PROCESS-RISK |
| biologic profile creates BPDR task | 60 | HIGHER-PROCESS-RISK |
| quarterly/annual periodic cycle generation without duplicates | 60 | HIGHER-PROCESS-RISK |
| Part 4 periodic augmentation | 60 | HIGHER-PROCESS-RISK |
| FDA letter explicit due date | 60 | HIGHER-PROCESS-RISK |
| agency extension preserves original deadline | 60 | HIGHER-PROCESS-RISK |
| retention selects longest configured applicable period | 60 | HIGHER-PROCESS-RISK |
| legal hold blocks purge | 60 | HIGHER-PROCESS-RISK |
