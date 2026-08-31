# WP-08 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| unreleased bulk blocked | 54 | HIGHER-PROCESS-RISK |
| wrong stopper/syringe lot blocked | 54 | HIGHER-PROCESS-RISK |
| clean hold expired | 54 | HIGHER-PROCESS-RISK |
| filter post-use integrity failed | 54 | HIGHER-PROCESS-RISK |
| fill IPC OOS | 54 | HIGHER-PROCESS-RISK |
| unplanned aseptic intervention | 54 | HIGHER-PROCESS-RISK |
| count source retry duplicate | 54 | HIGHER-PROCESS-RISK |
| visual reject reconciliation | 54 | HIGHER-PROCESS-RISK |
| CCI sample failure | 54 | HIGHER-PROCESS-RISK |
| device functional test fail | 54 | HIGHER-PROCESS-RISK |
| component change after batch issue does not alter snapshot | 54 | HIGHER-PROCESS-RISK |
| final release with device constituent incomplete denied | 54 | HIGHER-PROCESS-RISK |
| PFS already bound to another serial | 55 | HIGHER-PROCESS-RISK |
| cartridge wrong family | 55 | HIGHER-PROCESS-RISK |
| device component lot on hold | 55 | HIGHER-PROCESS-RISK |
| tester calibration expired | 55 | HIGHER-PROCESS-RISK |
| tester program version wrong | 55 | HIGHER-PROCESS-RISK |
| activation force fail then passing retest preserves both | 55 | HIGHER-PROCESS-RISK |
| under-delivery | 55 | HIGHER-PROCESS-RISK |
| rejected unit disassembly/reuse attempt | 55 | HIGHER-PROCESS-RISK |
| reusable pen cross-label compatibility | 55 | HIGHER-PROCESS-RISK |
| complaint trace from serial to drug lot | 55 | HIGHER-PROCESS-RISK |
| MDI wrong valve lot | 56 | HIGHER-PROCESS-RISK |
| crimp result out of limit | 56 | HIGHER-PROCESS-RISK |
| DPI humidity excursion | 56 | HIGHER-PROCESS-RISK |
| blend hold time expired | 56 | HIGHER-PROCESS-RISK |
| delivered-dose OOS | 56 | HIGHER-PROCESS-RISK |
| later passing retest preserves initial OOS | 56 | HIGHER-PROCESS-RISK |
| aerodynamic data import missing raw evidence | 56 | HIGHER-PROCESS-RISK |
| device component changed after batch issue | 56 | HIGHER-PROCESS-RISK |
| final packaging wrong actuator/device family | 56 | HIGHER-PROCESS-RISK |
| wrong drug lot | 57 | HIGHER-PROCESS-RISK |
| substrate on hold | 57 | HIGHER-PROCESS-RISK |
| coating solution hold expired | 57 | HIGHER-PROCESS-RISK |
| humidity excursion | 57 | HIGHER-PROCESS-RISK |
| program version mismatch | 57 | HIGHER-PROCESS-RISK |
| drug loading OOS | 57 | HIGHER-PROCESS-RISK |
| coating integrity defect partial unit scope | 57 | HIGHER-PROCESS-RISK |
| failed sterilization | 57 | HIGHER-PROCESS-RISK |
| post-sterilization assay failure | 57 | HIGHER-PROCESS-RISK |
| unapproved recoating attempt | 57 | HIGHER-PROCESS-RISK |
| dual reconciliation mismatch | 57 | HIGHER-PROCESS-RISK |
| complaint trace to drug lot | 57 | HIGHER-PROCESS-RISK |
