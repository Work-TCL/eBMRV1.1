# Security engineering rules

**Purpose:** Security engineering rules for the eBMR/eDHR platform.
**Applicable paths/modules:** see `docs/generated/17_REPOSITORY_STRUCTURE.md`; this rule applies to every
service, the Frappe app, edge and integration code unless a narrower scope is stated below.
**Source documents:** Document 61 (SPEC-SEC-001), Document 62 (SPEC-SEC-002), Document 63 (SPEC-SEC-003), Document 64 (SPEC-SEC-004), Document 65 (SPEC-SEC-005), Document 66 (SPEC-SEC-006), Document 67 (SPEC-SEC-007), Document 68 (SPEC-SEC-008)
**Source requirement IDs:** SEC-THR-001..028 (28); IAMSEC-FR-001..026 (26); PAM-FR-001..026 (26); APPSEC-FR-001..030 (30); KEY-FR-001..028 (28); NET-FR-001..030 (30); MON-FR-001..030 (30); SDLC-FR-001..034 (34)

---

## Required implementation pattern

Authenticate server-side; authorize every object and function access (BOLA/BFLA); enforce tenant and site
isolation at the query layer; keep signature separate from authentication; time-box and exclude
break-glass identities from approval paths; parameterise all SQL; validate and encode all input/output;
manage secrets and keys per Document 65; log structured and redacted security events per Document 67.

## Forbidden patterns

- secrets in code, logs, images, error responses or client bundles
- string-built SQL
- unauthenticated internal endpoints "because it is internal"
- privileged support path that can approve, sign or release
- outbound calls to destinations outside the allowlist
- disabling a security control to make a test pass

## Required tests

`docs/generated/24_SECURITY_TEST_PLAN.md` in full: authn, authz (BOLA/BFLA/cross-tenant), signature abuse,
injection, XSS/CSRF/SSRF, upload, secrets, crypto, privileged access, supply chain, edge/OT, logging.


## Source requirements (extract)

| ID | Requirement | Required behaviour |
|---|---|---|
| SEC-THR-001 | Security architecture register | Maintain system security architecture, trust zones, assets, actors, data classifications, entry points and security owners. |
| SEC-THR-002 | Threat model lifecycle | Threat model created at architecture baseline and updated for new modules, integrations, deployment modes and material changes. |
| SEC-THR-003 | Threat methodology | Use STRIDE or equivalent controlled methodology with asset/abuse-case mapping; methodology version retained. |
| SEC-THR-004 | Asset catalogue | Classify GxP records, credentials, signatures, audit, source evidence, PII, configuration, code/artifacts and keys. |
| SEC-THR-005 | Trust boundaries | Explicit boundaries between browser, Frappe, GxP services, databases, Keycloak/IdP, Edge, OT network, integrations, object store and admin plane. |
| SEC-THR-006 | Abuse cases | Model account takeover, privilege escalation, signature fraud, audit tampering, data exfiltration, ransomware, API abuse, insider misuse, malicious integration, Edge compromise and supply-chain compro |
| SEC-THR-007 | GxP integrity threats | Explicitly model unauthorized mutation, historical overwrite, duplicate/replayed command, stale version, failed-result deletion and audit-chain tampering. |
| SEC-THR-008 | Availability threats | Model DoS, queue exhaustion, database outage, object-store outage, IdP outage, Edge outage and network segmentation. |
| SEC-THR-009 | Privacy threats | Model overexposure of complaint/patient/reporter/personnel data and export/search leakage. |
| SEC-THR-010 | OT threats | Model compromised PLC/SCADA/Edge source, forged telemetry, bad clock, protocol abuse and unauthorized machine command. |
| SEC-THR-011 | Integration threats | Model SSRF, unsafe third-party response consumption, compromised ERP/LIMS endpoint and replayed webhook. |
| SEC-THR-012 | Tenant/site threats | Model cross-tenant and cross-site object access, cache leakage, search leakage and background-job scope errors. |
| SEC-THR-013 | Control mapping | Each identified threat maps preventive/detective/recovery controls and verification tests. |
| SEC-THR-014 | Risk rating | Use approved security-risk model with impact/likelihood/exposure and residual-risk decision. |
| SEC-THR-015 | Security acceptance | High/critical residual risk requires Security owner plus Quality/Business acceptance where GxP impact exists. |
| SEC-THR-016 | Security requirements | Threat mitigations generate stable security requirement IDs and tests. |
| SEC-THR-017 | Security ADR | Material security tradeoff documented in ADR with threat/risk/control impact. |
| SEC-THR-018 | Secure defaults | Default deployment minimizes exposed services, uses TLS, denies generic admin access, disables machine write and requires strong auth. |
| SEC-THR-019 | Attack surface inventory | Maintain deployed endpoints, ports, APIs, admin interfaces, integrations and versions. |
| SEC-THR-020 | Dependency boundary | Third-party library/service risk included in threat model where compromise affects regulated state. |
| SEC-THR-021 | Customer configuration threat review | Security-impacting tenant/customer configuration has safe defaults and validation. |
| SEC-THR-022 | Security control ownership | Every security control has implementation owner, evidence source and test owner. |
| SEC-THR-023 | Exception process | Security exception is time-bounded, risk-assessed, approved and tracked to remediation. |
| SEC-THR-024 | Threat review trigger | Trigger on new external endpoint, auth mode, machine command, new data class, new deployment mode, major library/runtime or architectural change. |
| SEC-THR-025 | Security profile | Cloud, private cloud and on-prem deployments receive profile-specific threat/control baselines. |
| SEC-THR-026 | Control effectiveness | Security monitoring/pen test/incidents can update control effectiveness and reopen threats. |
| SEC-THR-027 | Inspection evidence | Threat/control/risk/exception history exportable for enterprise customer assessment. |
| SEC-THR-028 | No checklist-only security | Security framework mapping supplements—not replaces—system-specific threat modeling. |
| IAMSEC-FR-001 | Federated identity | Support OIDC and SAML federation through Keycloak-compatible identity boundary; direct app password store is fallback only for approved isolated deployments. |
| IAMSEC-FR-002 | Local fallback IdP | On-prem/private deployments can use locally managed Keycloak-compatible realm when customer IdP unavailable. |
| IAMSEC-FR-003 | MFA policy | MFA requirements configurable by user risk/role/context; privileged users require MFA. |
| IAMSEC-FR-004 | MFA methods | Support WebAuthn/passkeys/security keys and approved TOTP/IdP MFA methods; weak factors configurable as disallowed. |
| IAMSEC-FR-005 | SSO session | Application accepts short-lived identity tokens/session assertions and validates issuer/audience/signature/expiry/nonce/state. |
| IAMSEC-FR-006 | Session binding | Session binds tenant/user/authentication context and cannot change tenant/site silently. |
| IAMSEC-FR-007 | Session timeout | Idle and absolute session lifetimes configurable by deployment/profile; sensitive contexts shorter. |
| IAMSEC-FR-008 | Reauthentication | Sensitive security/admin operations may require fresh authentication independently of Part 11 signing. |
| IAMSEC-FR-009 | Part 11 separation | Regulated signature ceremony always uses Document 04; normal MFA/session is never reused automatically as signature proof. |
| IAMSEC-FR-010 | Token revocation | Disabled user/critical risk/session logout/revocation invalidates or rapidly expires app access. |
| IAMSEC-FR-011 | Group/claim mapping | External groups/claims map through controlled identity mapping; external IdP does not directly assign unrestricted GxP permission. |
| IAMSEC-FR-012 | Provisioning | SCIM or controlled directory sync may provision identity metadata; authorization remains controlled in platform. |

## SPEC_GAP triggers

Raise a SPEC_GAP rather than deciding, if you encounter: a missing signature/authorization/retention/
precision value, a conflict between two source documents, an entity without an owner, an event without a
producer, or any requirement that would need a regulated behaviour you cannot trace to
Document 61, Document 62, Document 63, Document 64, Document 65, Document 66, Document 67, Document 68 or Documents 106–115.
