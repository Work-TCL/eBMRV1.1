# 40 — SBOM / Licence / Dependency Register

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Approved technology baseline and the register schema every dependency must populate (Document 104).

---

## Approved technology baseline (frozen ADRs, Document 02 §6.1)

| Component | Decision | ADR |
|---|---|---|
| Application framework | Frappe | ADR-001 |
| Frappe operational DB | MariaDB | ADR-002 |
| GxP authoritative DB | PostgreSQL | ADR-003 |
| Identity | Keycloak-compatible / customer SSO | ADR-004 |
| Durable workflow | Temporal | ADR-006 |
| Policy engine | proprietary, OPA-compatible boundary | ADR-007 |
| Event bus | NATS-compatible | ADR-008 |
| Object storage | S3-compatible | ADR-009 |
| Service language | TypeScript/Node.js LTS (Python for Frappe) | ADR-010 |
| Contracts | OpenAPI + JSON Schema + AsyncAPI | ADR-011 |
| Deployment | containers / Kubernetes-compatible | ADR-012 |

## Register schema (every dependency, model and binary)

```csv
ecosystem,name,version,source,hash,purpose,direct_or_transitive,scope,license,license_status,security_status,eol_date,owner,approval_reference,affected_artifacts,sbom_document
```

## Rules
- No package with unknown or prohibited licence enters a released build.
- Every dependency has a named owner and an approval reference.
- Version pinning and hash verification are mandatory; floating ranges are prohibited in release builds.
- Adding a dependency requires the Document 104 justification: why needed, whether an approved dependency already solves it, licence, security/EOL implications, SBOM effect, alternatives, approval.
- Dependencies are not added merely to reduce coding effort.

**Population:** this register is populated by CI at first build; it is intentionally empty of concrete versions here because inventing versions would create false provenance.
