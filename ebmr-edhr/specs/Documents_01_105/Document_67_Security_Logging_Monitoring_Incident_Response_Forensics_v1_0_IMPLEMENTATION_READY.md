# US eBMR / eDHR Regulated Manufacturing Platform
## Document 67 — Security Logging, Monitoring, Incident Response & Forensic Evidence — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-SEC-007  
**Parent Documents:** Documents 01–60  
**Primary Dependencies:** Documents 05, 26–29, 43–53, 61–66; SIEM/observability  
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

Define security telemetry, detection, incident response, forensic evidence and GxP-impact assessment while keeping the regulatory audit ledger distinct from security logs.

# 2. Actors / Components

- SOC/Security Analyst
- Incident Commander
- Security Engineer
- QA/Validation
- SRE
- Privacy/Legal
- Customer Security Contact
- Auditor

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| MON-FR-001 | Security event taxonomy | Define authentication, authorization, privileged, admin, config, secret/key, API abuse, integration, malware, integrity, network and data-access security events. | Consistent detection. |
| MON-FR-002 | Separate audit vs security logs | GxP audit ledger remains regulatory mutation history; security telemetry is separate but cross-correlated. | Correct evidence. |
| MON-FR-003 | Structured logging | Security logs include event code, UTC time, subject/service, tenant/site, source, target, result, correlation and severity. | Machine usable. |
| MON-FR-004 | Sensitive redaction | Logs exclude secrets/tokens/passwords/private keys and minimize PII/regulated content. | Safe telemetry. |
| MON-FR-005 | Central collection | App/services/Edge/IdP/infrastructure forward security telemetry to central SIEM/log platform where deployment supports. | Visibility. |
| MON-FR-006 | Tamper resistance | Security logs centrally retained with restricted delete/admin roles; critical log source loss alerts. | Evidence. |
| MON-FR-007 | Clock | All sources use synchronized UTC and carry clock-health metadata for Edge/OT. | Timeline. |
| MON-FR-008 | Detection rules | Versioned alerts for brute force, impossible/abnormal access, privilege elevation, break-glass, denied cross-tenant, hash conflict, unusual export, cert/secret issues and service anomalies. | Detection. |
| MON-FR-009 | Rate anomaly | Detect repeated BOLA/authorization denials, scan patterns, resource abuse and API enumeration. | API security. |
| MON-FR-010 | Data-integrity alert | Audit hash/checkpoint, event-id payload conflict, unexpected DB mutation or evidence hash mismatch becomes critical security/quality event. | GxP integrity. |
| MON-FR-011 | Edge security | Gateway cert misuse, config-signature failure, clock anomaly, buffer integrity failure and command denial visible centrally. | OT visibility. |
| MON-FR-012 | Incident register | Formal security incident with severity, scope, owner, affected tenants/sites, data/GxP impact and timeline. | Managed response. |
| MON-FR-013 | Incident states | Detected → Triage → Contain → Investigate → Eradicate/Recover → GxP/Data Impact → Close/Postmortem. | Explicit. |
| MON-FR-014 | Evidence preservation | Forensic snapshot/log/evidence collection uses immutable refs/hashes and chain-of-custody metadata. | Investigation. |
| MON-FR-015 | Containment actions | Revoke sessions/certs/secrets, isolate service/gateway, block integration, freeze account or disable feature through controlled commands. | Rapid response. |
| MON-FR-016 | GxP impact assessment | Incident affecting regulated data/system may create deviation/change/CAPA/validation impact through QMS. | Quality integration. |
| MON-FR-017 | Data breach assessment hook | Privacy/security incident can create legal/privacy assessment task without software autonomously making notification determination. | Governance. |
| MON-FR-018 | Ransomware | Incident playbook supports isolation, credential rotation, immutable backup assessment and restoration decision. | Resilience. |
| MON-FR-019 | Customer notification | Enterprise/customer security notification tasks tracked under contractual/regulatory policy. | Accountability. |
| MON-FR-020 | Incident communications | Internal/external communications versioned and approved where material. | Controlled. |
| MON-FR-021 | Postmortem | Root cause, control failure, corrective actions and lessons linked CAPA/Change/security backlog. | Improvement. |
| MON-FR-022 | Detection validation | Security rules tested with synthetic events and periodic control checks. | No dead alerts. |
| MON-FR-023 | Retention | Security telemetry retention configurable; incident evidence/regulated-impact evidence retained per applicable investigation policy. | Evidence. |
| MON-FR-024 | Access | Security logs restricted; support/customer views scoped to tenant/site and role. | Confidentiality. |
| MON-FR-025 | Export | Incident timeline/evidence package exportable without exposing unrelated tenant data. | Forensics. |
| MON-FR-026 | Alert fatigue | Detection rules have severity, dedup/suppression windows and tuning history; suppression cannot hide critical integrity alerts silently. | Operable. |
| MON-FR-027 | Health | Monitor log-ingestion lag/source silence/SIEM forwarding failure. | Telemetry assurance. |
| MON-FR-028 | Metrics | MTTD/MTTR, alert volume, false positives, privileged events, integrity events and unresolved security findings. | Management. |
| MON-FR-029 | No auto-delete | Incident closure never deletes security events/source evidence. | History. |
| MON-FR-030 | Security/QMS linkage | Security incident IDs can be referenced by deviation/CAPA/change and vice versa without duplicating evidence. | Integrated. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| emitSecurityEvent() | Any service/Edge/security control | event_code; subject; tenant/site; target; result; correlation; metadata | Event schema registered; metadata redaction policy | Writes to security event pipeline/outbox; not GxP business tables | SecurityEventReceipt | SecurityEventEmitted |
| evaluateDetectionRules() | SIEM/detection worker | security events; rule versions; window | Rules effective | Evaluates patterns/thresholds, deduplicates alerts | SecurityAlert[] | SecurityAlertRaised |
| openSecurityIncident() | Security analyst/critical rule | alert/evidence refs; severity; affected scope | Not duplicate or reviewer chooses separate incident | Creates incident and timeline | SecurityIncident | SecurityIncidentOpened |
| executeIncidentContainment() | Incident commander | incident_id; containment command; target; approval if required | Command allowlisted; authority valid | Calls session/cert/secret/network/connector isolation operations; records outcome | ContainmentReceipt | IncidentContainmentExecuted |
| preserveForensicEvidence() | Incident responder | source/path/object/log range; acquisition metadata | Authorized; source available | Copies/snapshots evidence to protected store; hashes and records chain-of-custody | ForensicEvidenceRef | ForensicEvidencePreserved |
| assessGxPIncidentImpact() | Security + QA | incident_id; affected systems/time/data; evidence | Incident scoped | Creates signed/approved impact assessment and linked QMS actions if needed | GxPIncidentImpact | SecurityGxPImpactAssessed |
| closeSecurityIncident() | Incident owner/approver | incident_id; root cause; actions; residual risk | Containment/recovery/impact/actions complete per policy | Closes incident, freezes postmortem/evidence manifest | IncidentClosure | SecurityIncidentClosed |
| testDetectionRule() | Security engineering/CI | rule_id; synthetic event set | Rule draft/effective test environment | Executes rule and compares expected alerts/suppressions | DetectionTestResult | DetectionRuleTested |


# 5. State / Control Model

```text
SECURITY EVENT
    ↓
DETECTION / ALERT
    ↓
TRIAGE
    ├→ FALSE/EXPECTED → CLOSED ALERT
    └→ INCIDENT
          ↓
       CONTAIN
          ↓
      INVESTIGATE
          ↓
ERADICATE / RECOVER
          ↓
GxP/DATA IMPACT
          ↓
POSTMORTEM / ACTIONS
          ↓
CLOSED
```

# 6. Data Model

## `security_event` (central telemetry schema)
- event ID/code
- occurred/received time
- subject/service
- tenant/site
- source/target
- outcome/severity
- correlation
- redacted metadata

## `security_incident`
```text
id uuid PK
incident_number varchar UNIQUE
severity varchar
state varchar
owner_subject_id uuid
affected_scope jsonb
detected_at/contained_at/recovered_at/closed_at
gxp_impact_state varchar
version bigint
```

## `forensic_evidence`
- incident
- source
- acquisition timestamp/actor
- hash/algorithm
- object/Vault ref
- chain-of-custody events


# 7. APIs / Internal Interfaces

- `POST /security/v1/incidents`
- `POST /security/v1/incidents/{id}/containment`
- `POST /security/v1/incidents/{id}/evidence`
- `POST /security/v1/incidents/{id}/gxp-impact`
- `POST /security/v1/incidents/{id}/close`

All security-sensitive mutations are server-side and auditable.

# 8. UI / Administrative Screens

1. Security Alerts
2. Incident Queue
3. Incident Timeline
4. Containment Actions
5. Forensic Evidence
6. GxP Impact
7. Detection Rules
8. Telemetry Health
9. Metrics

# 9. Security Events

- `SecurityAlertRaised`
- `SecurityIncidentOpened`
- `IncidentContainmentExecuted`
- `ForensicEvidencePreserved`
- `SecurityGxPImpactAssessed`
- `SecurityIncidentClosed`

# 10. Failure / Recovery

- Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies.
- Security subsystem outage must not silently downgrade protection.
- Retryable infrastructure failures use bounded retry/backoff.
- Security-control bypass requires a separate controlled emergency path, not a hidden fallback.
- Recovery actions are themselves logged and reviewable.

# 11. Repository Structure

```text
services/security/security-logging-monitoring-incident-response-forensic-evidence/
packages/security-contracts/
infrastructure/security/
apps/ebmr_frappe/ebmr/security/security-logging-monitoring-incident-response-forensic-evidence/
validation/security/security-logging-monitoring-incident-response-forensic-evidence/
tests/security/security-logging-monitoring-incident-response-forensic-evidence/
```

# 12. Mandatory Test Catalogue

- credential stuffing alert
- cross-tenant denial burst
- break-glass alert
- audit hash failure
- Edge buffer hash mismatch
- log source silent
- ransomware tabletop
- session revocation containment
- forensic chain-of-custody

# 13. Acceptance Criteria

A critical security incident affecting regulated data can be reconstructed from detection through containment, evidence, GxP impact, recovery and corrective action without relying solely on mutable application logs.

# 14. Claude Code / Codex Prohibitions

- Never replace GxP audit ledger with SIEM logs.
- Never log secrets to improve troubleshooting.
- Never close incident before required GxP impact assessment.
- Never auto-delete incident evidence on closure.


