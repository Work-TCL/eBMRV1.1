# 23 — Threat Model Register

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Threats declared in Document 61 with affected assets, mitigating controls and residual risk owner.

---

| Threat ID | Threat | Description | Primary mitigation | Detection | Residual risk owner |
|---|---|---|---|---|---|
| SEC-THR-001 | Security architecture register | Maintain system security architecture, trust zones, assets, actors, data classifications, entry points and security owners. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-002 | Threat model lifecycle | Threat model created at architecture baseline and updated for new modules, integrations, deployment modes and material changes. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-003 | Threat methodology | Use STRIDE or equivalent controlled methodology with asset/abuse-case mapping; methodology version retained. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-004 | Asset catalogue | Classify GxP records, credentials, signatures, audit, source evidence, PII, configuration, code/artifacts and keys. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-005 | Trust boundaries | Explicit boundaries between browser, Frappe, GxP services, databases, Keycloak/IdP, Edge, OT network, integrations, object store and admin plane. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-006 | Abuse cases | Model account takeover, privilege escalation, signature fraud, audit tampering, data exfiltration, ransomware, API abuse, insider misuse, malicious integration, Edge compromise and supply-chain compro | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-007 | GxP integrity threats | Explicitly model unauthorized mutation, historical overwrite, duplicate/replayed command, stale version, failed-result deletion and audit-chain tampering. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-008 | Availability threats | Model DoS, queue exhaustion, database outage, object-store outage, IdP outage, Edge outage and network segmentation. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-009 | Privacy threats | Model overexposure of complaint/patient/reporter/personnel data and export/search leakage. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-010 | OT threats | Model compromised PLC/SCADA/Edge source, forged telemetry, bad clock, protocol abuse and unauthorized machine command. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-011 | Integration threats | Model SSRF, unsafe third-party response consumption, compromised ERP/LIMS endpoint and replayed webhook. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-012 | Tenant/site threats | Model cross-tenant and cross-site object access, cache leakage, search leakage and background-job scope errors. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-013 | Control mapping | Each identified threat maps preventive/detective/recovery controls and verification tests. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-014 | Risk rating | Use approved security-risk model with impact/likelihood/exposure and residual-risk decision. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-015 | Security acceptance | High/critical residual risk requires Security owner plus Quality/Business acceptance where GxP impact exists. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-016 | Security requirements | Threat mitigations generate stable security requirement IDs and tests. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-017 | Security ADR | Material security tradeoff documented in ADR with threat/risk/control impact. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-018 | Secure defaults | Default deployment minimizes exposed services, uses TLS, denies generic admin access, disables machine write and requires strong auth. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-019 | Attack surface inventory | Maintain deployed endpoints, ports, APIs, admin interfaces, integrations and versions. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-020 | Dependency boundary | Third-party library/service risk included in threat model where compromise affects regulated state. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-021 | Customer configuration threat review | Security-impacting tenant/customer configuration has safe defaults and validation. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-022 | Security control ownership | Every security control has implementation owner, evidence source and test owner. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-023 | Exception process | Security exception is time-bounded, risk-assessed, approved and tracked to remediation. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-024 | Threat review trigger | Trigger on new external endpoint, auth mode, machine command, new data class, new deployment mode, major library/runtime or architectural change. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-025 | Security profile | Cloud, private cloud and on-prem deployments receive profile-specific threat/control baselines. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-026 | Control effectiveness | Security monitoring/pen test/incidents can update control effectiveness and reopen threats. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-027 | Inspection evidence | Threat/control/risk/exception history exportable for enterprise customer assessment. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |
| SEC-THR-028 | No checklist-only security | Security framework mapping supplements—not replaces—system-specific threat modeling. | see 22_SECURITY_CONTROL_MATRIX.md | Doc 67 monitoring | Security Officer |

## Trust boundaries (Doc 02 §8, Doc 66)

- Browser/operator device → Frappe application
- Frappe application → GxP Core API (regulated write boundary)
- GxP Core → PostgreSQL authoritative store
- GxP Core → object/WORM evidence store
- Internal bus (NATS) between services
- OT/Edge network → IT integration boundary
- Platform → external ERP / LIMS / IdP / regulatory gateway
- Support/privileged access path (break-glass)
- AI gateway → authoritative retrieval sources (read-only)
