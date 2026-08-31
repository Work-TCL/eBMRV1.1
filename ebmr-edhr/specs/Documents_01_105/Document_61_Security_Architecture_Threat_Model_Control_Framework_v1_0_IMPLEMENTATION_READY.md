# US eBMR / eDHR Regulated Manufacturing Platform
## Document 61 — Security Architecture, Threat Model & Control Framework — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-SEC-001  
**Parent Documents:** Documents 01–60  
**Primary Dependencies:** Documents 01–08, 29, 43–53; all deployment profiles  
**Status:** Proposed v1.0 — Implementation-Ready Baseline / Ready for Review & Freeze  
**Target Market:** United States  
**Primary Profiles:** DDCP V1; Medical Device V2; Pharmaceutical V3  
**Date:** 2026-08-20

---


# Implementation and Claude Code Construction Standard

This specification is intended for direct ingestion by Claude Code, Codex, and human engineering/security teams.

Before implementation, the coding agent shall extract:

1. requirement registry;
2. security-control catalogue;
3. module/service responsibility map;
4. function/service contract catalogue;
5. typed input/output schemas;
6. authorization/signature dependencies;
7. database reads/writes and transaction boundaries;
8. API/event contracts;
9. configuration and secret inventory;
10. threat/control/test mapping;
11. security logging requirements;
12. negative/abuse-case tests;
13. validation traceability.

For every public/domain/security function specified here, preserve:

- purpose;
- caller/trigger;
- typed inputs and source;
- authentication/authorization/qualification/SoD/signature prerequisites;
- business/security preconditions;
- database reads;
- database writes;
- transaction boundary;
- output;
- emitted/consumed events;
- stable error codes;
- idempotency/concurrency;
- audit evidence;
- security telemetry;
- positive, negative, abuse, failure and recovery tests.

If a missing decision materially changes security or regulated behavior, create a `SPEC_GAP` rather than inventing a rule.

# Security Framework Baseline

The security engineering baseline uses the following current references as implementation guidance:

- NIST Cybersecurity Framework (CSF) 2.0 for governance and cybersecurity outcomes.
- NIST SP 800-207 Zero Trust Architecture for resource/subject-centric access and no implicit network trust.
- NIST SP 800-218 SSDF v1.1 as the final secure-software-development baseline. NIST's v1.2 update is still draft as of this specification date and is treated only as a future design input.
- OWASP Application Security Verification Standard (ASVS) 5.0.0, released May 30, 2025, as a detailed application-security verification reference.
- OWASP API Security Top 10 2023 for API-specific abuse and authorization risks.
- CISA Secure by Design principles as voluntary product-security design guidance, especially secure defaults and shifting security burden away from customers.

Primary references:
- https://www.nist.gov/publications/nist-cybersecurity-framework-csf-20
- https://csrc.nist.gov/pubs/sp/800/207/final
- https://csrc.nist.gov/pubs/sp/800/218/final
- https://owasp.org/www-project-application-security-verification-standard/
- https://owasp.org/API-Security/editions/2023/en/0x11-t10/
- https://www.cisa.gov/securebydesign

# Security / GxP Boundary

Security controls support, but do not replace, GxP controls.

```text
Identity Provider / MFA
        ↓
Authentication Context
        ↓
Policy Service / Document 07
        ↓
Authorized GxP Action
        ↓
Part 11 Signature / Document 04 when required
        ↓
Mutation Gateway / Audit / Vault
```

Normal SSO login, MFA, or an administrator role is never automatically equivalent to a regulated electronic signature or Quality authority.

# 1. Objective

Define the platform-wide cybersecurity architecture, threat model, security risk/control catalogue and traceability framework so security decisions are explicit, testable and reviewable rather than scattered implementation choices.

# 2. Actors / Components

- Security Architect
- Security Engineer
- System Architect
- Quality/Validation
- DevOps/SRE
- Product Owner
- Risk Approver
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| SEC-THR-001 | Security architecture register | Maintain system security architecture, trust zones, assets, actors, data classifications, entry points and security owners. | Visible security design. |
| SEC-THR-002 | Threat model lifecycle | Threat model created at architecture baseline and updated for new modules, integrations, deployment modes and material changes. | Continuous risk review. |
| SEC-THR-003 | Threat methodology | Use STRIDE or equivalent controlled methodology with asset/abuse-case mapping; methodology version retained. | Repeatable. |
| SEC-THR-004 | Asset catalogue | Classify GxP records, credentials, signatures, audit, source evidence, PII, configuration, code/artifacts and keys. | Protection based on value. |
| SEC-THR-005 | Trust boundaries | Explicit boundaries between browser, Frappe, GxP services, databases, Keycloak/IdP, Edge, OT network, integrations, object store and admin plane. | No implicit trust. |
| SEC-THR-006 | Abuse cases | Model account takeover, privilege escalation, signature fraud, audit tampering, data exfiltration, ransomware, API abuse, insider misuse, malicious integration, Edge compromise and supply-chain compromise. | Realistic adversary paths. |
| SEC-THR-007 | GxP integrity threats | Explicitly model unauthorized mutation, historical overwrite, duplicate/replayed command, stale version, failed-result deletion and audit-chain tampering. | Regulated integrity. |
| SEC-THR-008 | Availability threats | Model DoS, queue exhaustion, database outage, object-store outage, IdP outage, Edge outage and network segmentation. | Operational resilience. |
| SEC-THR-009 | Privacy threats | Model overexposure of complaint/patient/reporter/personnel data and export/search leakage. | Confidentiality. |
| SEC-THR-010 | OT threats | Model compromised PLC/SCADA/Edge source, forged telemetry, bad clock, protocol abuse and unauthorized machine command. | Factory boundary. |
| SEC-THR-011 | Integration threats | Model SSRF, unsafe third-party response consumption, compromised ERP/LIMS endpoint and replayed webhook. | External trust. |
| SEC-THR-012 | Tenant/site threats | Model cross-tenant and cross-site object access, cache leakage, search leakage and background-job scope errors. | Isolation. |
| SEC-THR-013 | Control mapping | Each identified threat maps preventive/detective/recovery controls and verification tests. | Actionable. |
| SEC-THR-014 | Risk rating | Use approved security-risk model with impact/likelihood/exposure and residual-risk decision. | Prioritized. |
| SEC-THR-015 | Security acceptance | High/critical residual risk requires Security owner plus Quality/Business acceptance where GxP impact exists. | Governed. |
| SEC-THR-016 | Security requirements | Threat mitigations generate stable security requirement IDs and tests. | Traceability. |
| SEC-THR-017 | Security ADR | Material security tradeoff documented in ADR with threat/risk/control impact. | Explainable design. |
| SEC-THR-018 | Secure defaults | Default deployment minimizes exposed services, uses TLS, denies generic admin access, disables machine write and requires strong auth. | Secure-by-default. |
| SEC-THR-019 | Attack surface inventory | Maintain deployed endpoints, ports, APIs, admin interfaces, integrations and versions. | Asset awareness. |
| SEC-THR-020 | Dependency boundary | Third-party library/service risk included in threat model where compromise affects regulated state. | Supply-chain aware. |
| SEC-THR-021 | Customer configuration threat review | Security-impacting tenant/customer configuration has safe defaults and validation. | No insecure customization. |
| SEC-THR-022 | Security control ownership | Every security control has implementation owner, evidence source and test owner. | Accountability. |
| SEC-THR-023 | Exception process | Security exception is time-bounded, risk-assessed, approved and tracked to remediation. | No permanent bypass. |
| SEC-THR-024 | Threat review trigger | Trigger on new external endpoint, auth mode, machine command, new data class, new deployment mode, major library/runtime or architectural change. | Change-sensitive. |
| SEC-THR-025 | Security profile | Cloud, private cloud and on-prem deployments receive profile-specific threat/control baselines. | Deployment-aware. |
| SEC-THR-026 | Control effectiveness | Security monitoring/pen test/incidents can update control effectiveness and reopen threats. | Feedback loop. |
| SEC-THR-027 | Inspection evidence | Threat/control/risk/exception history exportable for enterprise customer assessment. | Customer assurance. |
| SEC-THR-028 | No checklist-only security | Security framework mapping supplements—not replaces—system-specific threat modeling. | Meaningful design. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| createThreatModelVersion() | Security Architect | system_version; methodology_version; scope; assets; boundaries | Architect authorized; architecture version exists | Creates draft threat-model version and asset/boundary snapshots | ThreatModelDraft | ThreatModelDraftCreated; THREAT_SCOPE_INVALID |
| registerThreat() | Architect/Engineer | threat_model_id; asset/boundary; threat_type; abuse_case; evidence | Draft/open model | Creates threat with initial risk and affected modules | ThreatRecord | ThreatRegistered |
| mapSecurityControl() | Security Architect | threat_id; control_id; preventive/detective/recovery; implementation refs | Threat exists; control catalogue valid | Creates threat-control mapping and expected evidence/test refs | ThreatControlMapping | SecurityControlMapped |
| calculateSecurityRisk() | Security Risk Service | threat_id; impact inputs; likelihood inputs; methodology | Methodology effective | Calculates inherent/residual security risk deterministically | SecurityRiskAssessment | SecurityRiskCalculated |
| acceptResidualSecurityRisk() | Security/Quality/Business approver | risk_id; rationale; expiry/review date; signatures | Required authorities met; mitigations reviewed | Stores signed residual-risk decision/version | SecurityRiskAcceptance | ResidualSecurityRiskAccepted |
| openSecurityException() | Security owner | control/requirement; reason; compensating controls; expiry | Exception authority; risk assessment exists | Creates time-bounded exception and review/escalation schedule | SecurityException | SecurityExceptionOpened |
| triggerThreatModelReview() | Change/SDLC/event | change_id; affected modules; trigger type | Trigger recognized | Creates review task and identifies affected threats/controls | ThreatReviewTask | ThreatModelReviewRequired |
| generateSecurityControlMatrix() | Validation/Security | threat model/version; deployment profile | Mappings complete | Builds control→implementation→evidence→test matrix | SecurityControlMatrix | SecurityControlMatrixGenerated |


# 5. State / Control Model

```text
ARCHITECTURE BASELINE
   ↓
THREAT_MODEL_DRAFT
   ↓
THREATS + CONTROLS + TESTS
   ↓
RISK_REVIEW
   ├→ MITIGATE
   ├→ ACCEPT (controlled)
   └→ EXCEPTION (time-bounded)
   ↓
APPROVED SECURITY BASELINE
   ↓
CHANGE/INCIDENT/PEN_TEST → REVIEW → NEW VERSION
```

# 6. Data Model

## `security_threat_model_version`
```text
id uuid PK
system_version varchar
methodology_version varchar
deployment_profile varchar
state varchar
vault_ref uuid
version bigint
```

## `security_threat`
- threat model version
- asset/boundary
- STRIDE/category
- abuse-case narrative
- attack preconditions
- impacted CIA/GxP attributes
- inherent/residual risk
- state

## `security_control`
- control code
- objective
- implementation owner
- evidence source
- test owner
- framework mappings

## `security_exception`
- control/requirement
- risk assessment
- compensating controls
- effective/expiry
- approvers
- remediation target


# 7. APIs / Internal Interfaces

- `POST /security/v1/threat-models`
- `POST /security/v1/threats`
- `POST /security/v1/threats/{id}/controls`
- `POST /security/v1/risks/{id}/accept`
- `POST /security/v1/exceptions`
- `GET /security/v1/control-matrix`

All security-sensitive mutations are server-side and auditable.

# 8. UI / Administrative Screens

1. Security Architecture
2. Threat Model
3. Assets/Trust Boundaries
4. Threat Register
5. Control Catalogue
6. Residual Risk
7. Exceptions
8. Control/Test Matrix

# 9. Security Events

- `ThreatModelDraftCreated`
- `ThreatRegistered`
- `SecurityControlMapped`
- `ResidualSecurityRiskAccepted`
- `SecurityExceptionOpened`
- `ThreatModelReviewRequired`

# 10. Failure / Recovery

- Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies.
- Security subsystem outage must not silently downgrade protection.
- Retryable infrastructure failures use bounded retry/backoff.
- Security-control bypass requires a separate controlled emergency path, not a hidden fallback.
- Recovery actions are themselves logged and reviewable.

# 11. Repository Structure

```text
services/security/security-architecture-threat-model-control-framework/
packages/security-contracts/
infrastructure/security/
apps/ebmr_frappe/ebmr/security/security-architecture-threat-model-control-framework/
validation/security/security-architecture-threat-model-control-framework/
tests/security/security-architecture-threat-model-control-framework/
```

# 12. Mandatory Test Catalogue

- cross-tenant abuse case
- signature fraud threat
- audit tamper threat
- Edge compromise
- SSRF integration threat
- critical residual risk approval
- expired exception
- change-triggered review

# 13. Acceptance Criteria

Every externally reachable or privileged trust boundary has documented threats, controls, evidence and tests, and no high/critical residual risk is silently accepted.

# 14. Claude Code / Codex Prohibitions

- Never use NIST/OWASP mapping as substitute for product threat model.
- Never close threat because a control is merely planned.
- Never make security exception indefinite.
- Never classify admin network as inherently trusted.


