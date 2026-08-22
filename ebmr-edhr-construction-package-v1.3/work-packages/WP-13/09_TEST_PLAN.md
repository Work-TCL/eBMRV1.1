# WP-13 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| AI attempts QA release tool denied | 105 | HIGHER-PROCESS-RISK |
| prompt injection in retrieved SOP cannot change policy | 105 | HIGHER-PROCESS-RISK |
| cross-tenant RAG denied | 105 | HIGHER-PROCESS-RISK |
| model version change requires evaluation | 105 | HIGHER-PROCESS-RISK |
| invalid structured output | 105 | HIGHER-PROCESS-RISK |
| AI hallucinated lot rejected by groundedness test | 105 | HIGHER-PROCESS-RISK |
| provider outage core workflow remains | 105 | HIGHER-PROCESS-RISK |
| human rejects advisory but original retained | 105 | HIGHER-PROCESS-RISK |
| development agent cannot fabricate CI evidence | 105 | HIGHER-PROCESS-RISK |
