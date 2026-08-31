# WP-10 — Test Plan

Test depth follows the approved risk class (Document 111).

## Mandatory classes
unit; property/fuzz for calculations; repository; API; contract; integration; E2E; authorization; signature; concurrency; failure/recovery; security; performance where declared.

## Scenarios from the specifications

| Scenario | Doc | Risk |
|---|---|---|
| cross-tenant abuse case | 61 | HIGHER-PROCESS-RISK |
| signature fraud threat | 61 | HIGHER-PROCESS-RISK |
| audit tamper threat | 61 | HIGHER-PROCESS-RISK |
| Edge compromise | 61 | HIGHER-PROCESS-RISK |
| SSRF integration threat | 61 | HIGHER-PROCESS-RISK |
| critical residual risk approval | 61 | HIGHER-PROCESS-RISK |
| expired exception | 61 | HIGHER-PROCESS-RISK |
| change-triggered review | 61 | HIGHER-PROCESS-RISK |
| wrong issuer | 62 | HIGHER-PROCESS-RISK |
| wrong audience | 62 | HIGHER-PROCESS-RISK |
| expired token | 62 | HIGHER-PROCESS-RISK |
| clock skew | 62 | HIGHER-PROCESS-RISK |
| MFA missing for privileged role | 62 | HIGHER-PROCESS-RISK |
| disabled user existing session | 62 | HIGHER-PROCESS-RISK |
| cross-tenant claim injection | 62 | HIGHER-PROCESS-RISK |
| service token wrong audience | 62 | HIGHER-PROCESS-RISK |
| certificate revoked | 62 | HIGHER-PROCESS-RISK |
| self-approval denied | 63 | HIGHER-PROCESS-RISK |
| grant expiry during session | 63 | HIGHER-PROCESS-RISK |
| support cross-tenant access denied | 63 | HIGHER-PROCESS-RISK |
| DB UPDATE attempt absent from allowed tools | 63 | HIGHER-PROCESS-RISK |
| break-glass cannot sign QA release | 63 | HIGHER-PROCESS-RISK |
| admin command parameter validation | 63 | HIGHER-PROCESS-RISK |
| terminated support user access revoked | 63 | HIGHER-PROCESS-RISK |
| BOLA cross-tenant ID | 64 | HIGHER-PROCESS-RISK |
| mass assignment state/role field | 64 | HIGHER-PROCESS-RISK |
| SQL injection payload | 64 | HIGHER-PROCESS-RISK |
| stored XSS | 64 | HIGHER-PROCESS-RISK |
| CSRF mutation | 64 | HIGHER-PROCESS-RISK |
| SSRF metadata IP | 64 | HIGHER-PROCESS-RISK |
| oversized upload | 64 | HIGHER-PROCESS-RISK |
| malware file | 64 | HIGHER-PROCESS-RISK |
| CSV formula injection | 64 | HIGHER-PROCESS-RISK |
| third-party API malformed payload | 64 | HIGHER-PROCESS-RISK |
| bulk auth bypass | 64 | HIGHER-PROCESS-RISK |
| expired service cert | 65 | HIGHER-PROCESS-RISK |
| rotation with no outage | 65 | HIGHER-PROCESS-RISK |
| revoked Edge cert | 65 | HIGHER-PROCESS-RISK |
| secret leaked scanner test | 65 | HIGHER-PROCESS-RISK |
| field encryption wrong tenant key | 65 | HIGHER-PROCESS-RISK |
| backup restore with retired key | 65 | HIGHER-PROCESS-RISK |
| trust-all cert config blocked | 65 | HIGHER-PROCESS-RISK |
| hash algorithm migration | 65 | HIGHER-PROCESS-RISK |
| Frappe cannot connect to GxP DB directly | 66 | HIGHER-PROCESS-RISK |
| integration service cannot access QA tables | 66 | HIGHER-PROCESS-RISK |
| Edge cannot reach DB | 66 | HIGHER-PROCESS-RISK |
| cross-site job blocked | 66 | HIGHER-PROCESS-RISK |
| dev credential cannot reach prod | 66 | HIGHER-PROCESS-RISK |
| container root policy | 66 | HIGHER-PROCESS-RISK |
| public DB exposure detection | 66 | HIGHER-PROCESS-RISK |
| credential stuffing alert | 67 | HIGHER-PROCESS-RISK |
| cross-tenant denial burst | 67 | HIGHER-PROCESS-RISK |
| break-glass alert | 67 | HIGHER-PROCESS-RISK |
| audit hash failure | 67 | HIGHER-PROCESS-RISK |
| Edge buffer hash mismatch | 67 | HIGHER-PROCESS-RISK |
| log source silent | 67 | HIGHER-PROCESS-RISK |
| ransomware tabletop | 67 | HIGHER-PROCESS-RISK |
| session revocation containment | 67 | HIGHER-PROCESS-RISK |
| forensic chain-of-custody | 67 | HIGHER-PROCESS-RISK |
| secret in repo | 68 | HIGHER-PROCESS-RISK |
| critical dependency CVE | 68 | HIGHER-PROCESS-RISK |
| KEV critical library | 68 | HIGHER-PROCESS-RISK |
| unsigned image blocked | 68 | HIGHER-PROCESS-RISK |
| SBOM mismatch | 68 | HIGHER-PROCESS-RISK |
| vulnerable base image | 68 | HIGHER-PROCESS-RISK |
| untrusted PR secret access | 68 | HIGHER-PROCESS-RISK |
| pen-test BOLA finding | 68 | HIGHER-PROCESS-RISK |
| security exception expiry | 68 | HIGHER-PROCESS-RISK |
| regression test | 68 | HIGHER-PROCESS-RISK |
