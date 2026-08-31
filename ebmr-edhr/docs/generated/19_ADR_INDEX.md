# 19 — ADR Index

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Frozen architecture decisions from Document 02 §6.1 plus construction decisions recorded by this package.

---

## Frozen decisions (Document 02 §6.1 — do not re-litigate without controlled change)

| ADR | Decision | Frozen choice |
|---|---|---|
| ADR-001 | Application framework | Frappe |
| ADR-002 | Frappe operational DB | MariaDB initially |
| ADR-003 | GxP authoritative DB | PostgreSQL |
| ADR-004 | Identity abstraction | Keycloak-compatible; customer SSO supported |
| ADR-005 | Signature authentication | Mandatory step-up for regulated signatures |
| ADR-006 | Durable workflow | Temporal for long-running execution orchestration |
| ADR-007 | Policy engine | Proprietary Policy/Authorization Service; OPA-compatible boundary retained |
| ADR-008 | Asynchronous event bus | NATS-compatible; transactional outbox is the source |
| ADR-009 | Object/evidence storage | S3-compatible abstraction |
| ADR-010 | Service language | TypeScript/Node.js LTS for GxP services and Edge; Python for Frappe |
| ADR-011 | API definition | OpenAPI + JSON Schema; AsyncAPI/event schemas |
| ADR-012 | Deployment | Containers/Kubernetes-compatible; dedicated customer environments |
| ADR-013 | V1 offline | Edge buffering; no disconnected Part 11 browser execution |
| ADR-014 | Authorization | RBAC + qualification + contextual policy + SoD |
| ADR-015 | Audit tamper evidence | Immutable records + hash chain + signed checkpoint |
| ADR-016 | Generic CRUD | Prohibited for released/regulated records |
| ADR-017 | Integration pattern | Adapter interfaces, idempotent commands, reconciliation |
| ADR-018 | AI | Advisory only in V1 |

## Construction decisions recorded by this package

| ADR | Decision | Status |
|---|---|---|
| ADR-0001 | Repository layout reconciled to spec-declared paths | `docs/adr/ADR-0001-repository-layout.md` |
| ADR-0002 | GxP Core deployed as a modular monolith with mandatory logical boundaries | `docs/adr/ADR-0002-gxp-core-deployment-unit.md` |
| ADR-0003 | Contract-first generation of types from OpenAPI/JSON Schema | `docs/adr/ADR-0003-contract-first-codegen.md` |
| ADR-0004 | Requirement-ID namespace remediation for cross-document collisions | `docs/adr/ADR-0004-requirement-id-namespace.md` |
| ADR-0005 | Frappe Framework is the base layer (`apps/ebmr_frappe`); ERPNext is external-only, never installed into the platform runtime | `docs/adr/ADR-0005-frappe-base-layer-erpnext-external.md` |
| ADR-0006 | Tenancy is single-tenant-per-deployment (Option A), with a startup guard against a silent second organization | `docs/adr/ADR-0006-tenancy-model.md` |
| ADR-0007 | Python/FastAPI/async SQLAlchemy supersedes ADR-010's TypeScript/Node.js LTS decision for GxP services | `docs/adr/ADR-0007-python-fastapi-gxp-services.md` |
| ADR-0008 | Frappe (`apps/ebmr_frappe`) is the operator UI of record; `frontend/` (Next.js) is a recorded pre-existing deviation, not a second regulated UI | `docs/adr/ADR-0008-frappe-role-and-ui-layer.md` |
| ADR-0009 | WP-07 built as `services/gxp-api/app/modules/erp/` (not a separate `services/integration-gateway`); provisional entity schema authored under `erp.*` pending a human Document 112 amendment (SG-121) | `docs/adr/ADR-0009-integration-gateway-deployment-and-schema.md` |
