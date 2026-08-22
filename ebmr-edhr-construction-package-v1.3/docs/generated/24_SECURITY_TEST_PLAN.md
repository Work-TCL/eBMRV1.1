# 24 — Security Test Plan

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Security verification derived from Documents 61–68 and qualified under Document 92.

---

## Mandatory test classes

- Authentication: brute force, session fixation, token replay, MFA bypass attempts.
- Authorization: BOLA (object-level), BFLA (function-level), cross-tenant and cross-site access.
- Signature: replay, cross-action reuse, service-identity signing, expired challenge, changed record.
- Injection: SQL, command, template, LDAP, header, log injection.
- Web: XSS, CSRF, SSRF, open redirect, clickjacking, CORS misconfiguration.
- File upload: type confusion, oversized, malicious content, path traversal.
- Secrets: no secret in code, logs, images, error responses or client bundles.
- Crypto: TLS configuration, key lifecycle, digest verification, WORM lock behaviour.
- Privileged access: break-glass time-bounding, approval-path exclusion, session recording.
- Supply chain: SBOM completeness, dependency provenance, unsigned artefact rejection.
- Edge/OT: device identity spoofing, replayed telemetry, command boundary enforcement.
- Logging: redaction of PII/secrets, tamper resistance, completeness of security events.

## Per-module security scenarios extracted from the specifications

| Document | Scenario |
|---|---|
| 61 | cross-tenant abuse case |
| 61 | signature fraud threat |
| 61 | audit tamper threat |
| 61 | Edge compromise |
| 61 | SSRF integration threat |
| 61 | critical residual risk approval |
| 61 | expired exception |
| 61 | change-triggered review |
| 62 | wrong issuer |
| 62 | wrong audience |
| 62 | expired token |
| 62 | clock skew |
| 62 | MFA missing for privileged role |
| 62 | disabled user existing session |
| 62 | cross-tenant claim injection |
| 62 | service token wrong audience |
| 62 | certificate revoked |
| 63 | self-approval denied |
| 63 | grant expiry during session |
| 63 | support cross-tenant access denied |
| 63 | DB UPDATE attempt absent from allowed tools |
| 63 | break-glass cannot sign QA release |
| 63 | admin command parameter validation |
| 63 | terminated support user access revoked |
| 64 | BOLA cross-tenant ID |
| 64 | mass assignment state/role field |
| 64 | SQL injection payload |
| 64 | stored XSS |
| 64 | CSRF mutation |
| 64 | SSRF metadata IP |
| 64 | oversized upload |
| 64 | malware file |
| 64 | CSV formula injection |
| 64 | third-party API malformed payload |
| 64 | bulk auth bypass |
| 65 | expired service cert |
| 65 | rotation with no outage |
| 65 | revoked Edge cert |
| 65 | secret leaked scanner test |
| 65 | field encryption wrong tenant key |
| 65 | backup restore with retired key |
| 65 | trust-all cert config blocked |
| 65 | hash algorithm migration |
| 66 | Frappe cannot connect to GxP DB directly |
| 66 | integration service cannot access QA tables |
| 66 | Edge cannot reach DB |
| 66 | cross-site job blocked |
| 66 | dev credential cannot reach prod |
| 66 | container root policy |
| 66 | public DB exposure detection |
| 67 | credential stuffing alert |
| 67 | cross-tenant denial burst |
| 67 | break-glass alert |
| 67 | audit hash failure |
| 67 | Edge buffer hash mismatch |
| 67 | log source silent |
| 67 | ransomware tabletop |
| 67 | session revocation containment |
| 67 | forensic chain-of-custody |
| 68 | secret in repo |
| 68 | critical dependency CVE |
| 68 | KEV critical library |
| 68 | unsigned image blocked |
| 68 | SBOM mismatch |
| 68 | vulnerable base image |
| 68 | untrusted PR secret access |
| 68 | pen-test BOLA finding |
| 68 | security exception expiry |
| 68 | regression test |
| 92 | cross-tenant BOLA |
| 92 | MFA bypass |
| 92 | SSRF |
| 92 | malicious upload |
| 92 | break-glass no signature |
| 92 | expired cert |
| 92 | unsigned image |
| 92 | SIEM rule |

## Gates
- SAST/SCA/secret/IaC/container scanning on every PR (Doc 68/103).
- Penetration test before each validated production release (Doc 92).
- Any critical finding blocks the release candidate.
