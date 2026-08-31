# US eBMR / eDHR Regulated Manufacturing Platform
## Document 66 — Network, Tenant, Deployment Isolation & Zero-Trust Architecture — v1.0 IMPLEMENTATION-READY

**Specification ID:** SPEC-SEC-006  
**Parent Documents:** Documents 01–60  
**Primary Dependencies:** Documents 02, 43–53, 61–65; Kubernetes/cloud/on-prem infrastructure  
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

Define trust zones, service/network flows, OT boundaries, tenant/site isolation and workload hardening so deployment security does not rely on a flat trusted network.

# 2. Actors / Components

- Cloud/Platform Architect
- Network Engineer
- DevOps/SRE
- Security Engineer
- Edge Administrator
- Integration Engineer
- Database Admin

# 3. Functional Requirements

| ID | Functionality | Detailed required behavior | Acceptance intent |
|---|---|---|---|
| NET-FR-001 | Deployment zones | Define ingress, app, GxP service, DB, integration, observability, admin and Edge/OT zones. | Layered architecture. |
| NET-FR-002 | Default deny | Network policies/firewalls default deny between zones and allow only required flows. | Least connectivity. |
| NET-FR-003 | No DB internet exposure | MariaDB/PostgreSQL/object stores/internal message bus not publicly exposed. | Attack surface. |
| NET-FR-004 | Service-to-service auth | Internal network location alone does not authorize service access; workload identity/auth required. | Zero trust. |
| NET-FR-005 | Ingress | Only approved reverse proxy/API gateway/load balancer exposed externally; admin routes separately protected. | Controlled entry. |
| NET-FR-006 | Egress | Application/integration services use outbound allowlists/proxy/network policy; GxP DB has no arbitrary internet egress. | SSRF containment. |
| NET-FR-007 | OT boundary | Edge Gateway mediates IT/OT data flow; cloud/app services do not directly initiate arbitrary PLC connections. | Industrial isolation. |
| NET-FR-008 | Edge outbound preferred | Plant Edge to server connections outbound initiated where feasible. | Reduced inbound exposure. |
| NET-FR-009 | Admin plane | Administrative access through protected VPN/ZTNA/bastion/PAM path rather than public service ports. | Privileged isolation. |
| NET-FR-010 | Tenant isolation | Dedicated customer deployment is baseline; within deployment tenant/site scopes still enforced in application/data/jobs. | Defense in depth. |
| NET-FR-011 | Cross-site isolation | Site-scoped integrations, Edge identities, service config and background jobs cannot cross site without explicit enterprise scope. | Scope. |
| NET-FR-012 | Database roles | Separate DB users/roles by service/schema/write need; Frappe DB credential cannot write GxP DB. | Data ownership. |
| NET-FR-013 | Schema ownership | GxP service repositories own tables; integrations/read models use restricted views/API, not shared superuser. | Least privilege. |
| NET-FR-014 | Message bus ACL | NATS/event subjects ACL by service identity; no universal publish/subscribe credential. | Event integrity. |
| NET-FR-015 | Object store policy | Evidence buckets/prefixes restricted by service identity; immutable/WORM policies protected from app deletion. | Evidence integrity. |
| NET-FR-016 | Kubernetes namespace | Reference K8s deployment separates workloads/namespaces/service accounts/network policies by trust/function. | Container isolation. |
| NET-FR-017 | Container privilege | Run non-root, read-only filesystem/capability drops/seccomp/AppArmor where compatible. | Workload hardening. |
| NET-FR-018 | Host hardening | Reference OS baseline disables unnecessary services, applies patch/config baseline and time sync. | Secure host. |
| NET-FR-019 | TLS termination | TLS termination points explicit; re-encrypt/internal TLS where trust boundary requires. | Transport clarity. |
| NET-FR-020 | Private endpoints | Cloud DB/object/KMS prefer private networking/endpoints where supported. | Reduced public exposure. |
| NET-FR-021 | DNS | Internal service discovery controlled; DNS changes/security monitored; avoid trusting hostname without TLS identity. | Name integrity. |
| NET-FR-022 | Remote sites | Site-to-central connectivity uses secure VPN/private link/TLS with explicit routing; no flat corporate network assumption. | Enterprise. |
| NET-FR-023 | Environment isolation | Dev/test/validation/prod separated accounts/projects/namespaces/secrets/data; production credentials absent from non-prod. | SDLC safety. |
| NET-FR-024 | Synthetic data | Non-prod uses synthetic/deidentified data by default; production data copy requires controlled approval/sanitization. | Privacy. |
| NET-FR-025 | Backup isolation | Backup repository/access logically isolated from normal application compromise path. | Ransomware resilience. |
| NET-FR-026 | Monitoring access | Security monitoring has read/ingest permissions, not business-write privileges. | Separation. |
| NET-FR-027 | Port inventory | All inbound/outbound ports/protocols documented by deployment profile. | Reviewable. |
| NET-FR-028 | Network change | GxP-impacting firewall/routing/service-exposure changes controlled and tested. | Validated state. |
| NET-FR-029 | Segmentation test | Automated/periodic tests verify forbidden network paths remain blocked. | Verification. |
| NET-FR-030 | No security by IP only | IP allowlist may supplement but never replace identity/auth for regulated APIs. | Zero trust. |


# 4. Claude Code Function / Service Contract Catalogue

| Function / Operation | Caller / Trigger | Inputs | Preconditions & validation | Processing / DB effects | Output | Events / Errors / Tests |
|---|---|---|---|---|---|---|
| generateNetworkPolicySet() | Infrastructure compiler | deployment_profile; service inventory; approved flow catalogue | Profile/version approved | Generates K8s/network/firewall policy manifests; no runtime DB writes | NetworkPolicyBundle | NetworkPolicyGenerated |
| validateServiceFlow() | CI/security test | source identity/zone; destination; protocol/port | Flow catalogue loaded | Compares intended connection against allowlist and policy | FlowDecision | NETWORK_FLOW_NOT_ALLOWED |
| issueSiteScopedEdgeNetworkProfile() | Deployment/Edge admin | site_id; gateway_id; required endpoints | Gateway/site identity valid | Generates minimum outbound endpoint/port profile | EdgeNetworkProfile | EdgeNetworkProfileIssued |
| verifyTenantScopePropagation() | Security test/runtime assertion | AuthContext/job/event; expected tenant/site | Context exists | Checks all downstream metadata carries compatible tenant/site scope | ScopeVerification | TENANT_SCOPE_MISMATCH |
| testForbiddenNetworkPath() | Continuous/periodic security test | source workload; destination target | Test environment/prod safe test profile | Attempts connection or policy simulation, records deny evidence | SegmentationTestResult | SegmentationControlFailed |
| validateDeploymentHardening() | CI/deploy admission | workload manifest/image/security context | Hardening policy effective | Checks root user, privileges, capabilities, host mounts, network exposure | HardeningResult | WORKLOAD_HARDENING_FAILED |


# 5. State / Control Model

```text
INTERNET / CUSTOMER USERS
          ↓
      INGRESS ZONE
          ↓
     APP / FRAPPE
          ↓ authenticated internal calls
      GXP SERVICES
          ↓
   GXP POSTGRES / VAULT

ERP/LIMS ↔ INTEGRATION ZONE
EDGE/OT → EDGE GATEWAY → INTEGRATION ZONE

ADMIN → ZTNA/VPN/BASTION/PAM → ADMIN PLANE

DEFAULT: NO OTHER FLOWS
```

# 6. Data Model

## `network_flow_definition`
- source zone/service
- destination zone/service
- protocol/port
- purpose
- auth mechanism
- deployment profile
- effective dates
- owner

## `deployment_security_profile`
- ingress/egress policy
- private endpoints
- namespaces
- service accounts
- container hardening
- admin access pattern
- backup/network isolation


# 7. APIs / Internal Interfaces

- `Infrastructure-as-code generated policies`
- `GET /security/v1/network-flows`
- `GET /security/v1/deployment-security-profile`

All security-sensitive mutations are server-side and auditable.

# 8. UI / Administrative Screens

1. Trust Zone Diagram
2. Network Flow Catalogue
3. Segmentation Test Results
4. Tenant/Site Isolation Test
5. Deployment Hardening

# 9. Security Events

- `ForbiddenNetworkPathDetected`
- `TenantScopeMismatchDetected`
- `WorkloadHardeningFailed`
- `UnexpectedPublicExposureDetected`

# 10. Failure / Recovery

- Fail closed for authentication, authorization, signature, secret/key, privileged-access and policy decisions unless an explicitly documented offline/emergency control applies.
- Security subsystem outage must not silently downgrade protection.
- Retryable infrastructure failures use bounded retry/backoff.
- Security-control bypass requires a separate controlled emergency path, not a hidden fallback.
- Recovery actions are themselves logged and reviewable.

# 11. Repository Structure

```text
services/security/network-tenant-deployment-isolation-zero-trust-architecture/
packages/security-contracts/
infrastructure/security/
apps/ebmr_frappe/ebmr/security/network-tenant-deployment-isolation-zero-trust-architecture/
validation/security/network-tenant-deployment-isolation-zero-trust-architecture/
tests/security/network-tenant-deployment-isolation-zero-trust-architecture/
```

# 12. Mandatory Test Catalogue

- Frappe cannot connect to GxP DB directly
- integration service cannot access QA tables
- Edge cannot reach DB
- cross-site job blocked
- dev credential cannot reach prod
- container root policy
- public DB exposure detection

# 13. Acceptance Criteria

No component obtains access because it shares a subnet; every allowed flow is documented, identity-authenticated where applicable, and unnecessary lateral paths are blocked.

# 14. Claude Code / Codex Prohibitions

- Never use flat VPC/VLAN as authorization.
- Never expose database/message bus publicly for convenience.
- Never let Edge gateway connect directly to GxP database.
- Never use production secrets in dev/test.


