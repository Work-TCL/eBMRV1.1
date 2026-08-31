# 09 — UI → Action → API Map

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Every UI surface declared in the specifications, the regulated action it triggers and the API it must call.

---

Frappe screens never write regulated state directly. Each action maps to a GxP API call (AG-06). Projected GxP fields are read-only (Doc 71).

| UI surface | Module | Work package | Primary API surface | Signature | Source |
|---|---|---|---|---|---|
| product/batch/document identity; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| exact action; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| signature meaning; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | policy lookup (Doc 04) | Doc 04 |
| relevant version; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| warning if data changed; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| required comment/reason; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| signer name. | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | policy lookup (Doc 04) | Doc 04 |
| signed status; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | policy lookup (Doc 04) | Doc 04 |
| signer printed name; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | policy lookup (Doc 04) | Doc 04 |
| UTC/local display time; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| meaning; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| signature ID; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | policy lookup (Doc 04) | Doc 04 |
| resulting record version. | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| action; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| record identity/version; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| summary fields; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| required reason/comment; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| signature policy. | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | policy lookup (Doc 04) | Doc 04 |
| exact record target; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| exact action/meaning; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| signer identity; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | policy lookup (Doc 04) | Doc 04 |
| warning that signature is attributable; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | policy lookup (Doc 04) | Doc 04 |
| current record version; | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| reason/comment if required. | SPEC-GXP-002 | WP-01 | `POST /signature/v1/challenges`, `POST /signature/v1/challenges/{id}/verify`, `POST /signature/v1/signatures/{id}/consume` | — | Doc 04 |
| Record Audit Timeline | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | — | Doc 05 |
| Changed Values | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | — | Doc 05 |
| Signature Timeline | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | policy lookup (Doc 04) | Doc 05 |
| Manual Overrides/Corrections | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | — | Doc 05 |
| Integration/Device Events | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | — | Doc 05 |
| Integrity Health | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | — | Doc 05 |
| Audit Review Record | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | — | Doc 05 |
| actor/source; | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | — | Doc 05 |
| authoritative time; | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | — | Doc 05 |
| action; | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | — | Doc 05 |
| old/new; | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | — | Doc 05 |
| reason; | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | — | Doc 05 |
| linked signature; | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | policy lookup (Doc 04) | Doc 05 |
| linked record version; | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | — | Doc 05 |
| correlation chain. | SPEC-GXP-003 | WP-01 | `GET /audit/v1/records/{type}/{id}`, `GET /audit/v1/batches/{id}`, `GET /audit/v1/users/{subjectId}` | — | Doc 05 |
| View Historical Version | SPEC-GXP-004 | WP-01 | `POST /vault/v1/masters/{type}/{businessId}/release`, `GET /vault/v1/objects/{objectId}`, `GET /vault/v1/objects/{objectId}/integrity` | — | Doc 06 |
| Request Correction | SPEC-GXP-004 | WP-01 | `POST /vault/v1/masters/{type}/{businessId}/release`, `GET /vault/v1/objects/{objectId}`, `GET /vault/v1/objects/{objectId}/integrity` | — | Doc 06 |
| Impact Assessment | SPEC-GXP-004 | WP-01 | `POST /vault/v1/masters/{type}/{businessId}/release`, `GET /vault/v1/objects/{objectId}`, `GET /vault/v1/objects/{objectId}/integrity` | — | Doc 06 |
| Compare Old vs Proposed | SPEC-GXP-004 | WP-01 | `POST /vault/v1/masters/{type}/{businessId}/release`, `GET /vault/v1/objects/{objectId}`, `GET /vault/v1/objects/{objectId}/integrity` | — | Doc 06 |
| Signature/Approval | SPEC-GXP-004 | WP-01 | `POST /vault/v1/masters/{type}/{businessId}/release`, `GET /vault/v1/objects/{objectId}`, `GET /vault/v1/objects/{objectId}/integrity` | policy lookup (Doc 04) | Doc 06 |
| Corrected Version History | SPEC-GXP-004 | WP-01 | `POST /vault/v1/masters/{type}/{businessId}/release`, `GET /vault/v1/objects/{objectId}`, `GET /vault/v1/objects/{objectId}/integrity` | — | Doc 06 |
| User Directory Mapping | SPEC-IAM-001 | WP-01 | `POST /policy/v1/decisions`, `GET /iam/v1/subjects/{id}/effective-authority`, `GET /iam/v1/subjects/{id}/qualifications` | — | Doc 07 |
| Role Assignment | SPEC-IAM-001 | WP-01 | `POST /policy/v1/decisions`, `GET /iam/v1/subjects/{id}/effective-authority`, `GET /iam/v1/subjects/{id}/qualifications` | policy lookup (Doc 04) | Doc 07 |
| Qualification Assignment | SPEC-IAM-001 | WP-01 | `POST /policy/v1/decisions`, `GET /iam/v1/subjects/{id}/effective-authority`, `GET /iam/v1/subjects/{id}/qualifications` | policy lookup (Doc 04) | Doc 07 |
| Temporary Authorization | SPEC-IAM-001 | WP-01 | `POST /policy/v1/decisions`, `GET /iam/v1/subjects/{id}/effective-authority`, `GET /iam/v1/subjects/{id}/qualifications` | policy lookup (Doc 04) | Doc 07 |
| Break-Glass Review | SPEC-IAM-001 | WP-01 | `POST /policy/v1/decisions`, `GET /iam/v1/subjects/{id}/effective-authority`, `GET /iam/v1/subjects/{id}/qualifications` | — | Doc 07 |
| Service Account Registry | SPEC-IAM-001 | WP-01 | `POST /policy/v1/decisions`, `GET /iam/v1/subjects/{id}/effective-authority`, `GET /iam/v1/subjects/{id}/qualifications` | — | Doc 07 |
| Device Identity Registry | SPEC-IAM-001 | WP-01 | `POST /policy/v1/decisions`, `GET /iam/v1/subjects/{id}/effective-authority`, `GET /iam/v1/subjects/{id}/qualifications` | — | Doc 07 |
| Access Review Dashboard | SPEC-IAM-001 | WP-01 | `POST /policy/v1/decisions`, `GET /iam/v1/subjects/{id}/effective-authority`, `GET /iam/v1/subjects/{id}/qualifications` | — | Doc 07 |
| Rule Catalogue | SPEC-GXP-006 | WP-01 | `POST /rules/v1/drafts`, `POST /rules/v1/{ruleId}/validate`, `POST /rules/v1/{ruleId}/simulate` | — | Doc 08 |
| Rule Draft Editor | SPEC-GXP-006 | WP-01 | `POST /rules/v1/drafts`, `POST /rules/v1/{ruleId}/validate`, `POST /rules/v1/{ruleId}/simulate` | — | Doc 08 |
| Input/Output Contract | SPEC-GXP-006 | WP-01 | `POST /rules/v1/drafts`, `POST /rules/v1/{ruleId}/validate`, `POST /rules/v1/{ruleId}/simulate` | — | Doc 08 |
| Units/Precision/Rounding | SPEC-GXP-006 | WP-01 | `POST /rules/v1/drafts`, `POST /rules/v1/{ruleId}/validate`, `POST /rules/v1/{ruleId}/simulate` | — | Doc 08 |
| Test Vectors | SPEC-GXP-006 | WP-01 | `POST /rules/v1/drafts`, `POST /rules/v1/{ruleId}/validate`, `POST /rules/v1/{ruleId}/simulate` | — | Doc 08 |
| Simulation | SPEC-GXP-006 | WP-01 | `POST /rules/v1/drafts`, `POST /rules/v1/{ruleId}/validate`, `POST /rules/v1/{ruleId}/simulate` | — | Doc 08 |
| Review/Approval | SPEC-GXP-006 | WP-01 | `POST /rules/v1/drafts`, `POST /rules/v1/{ruleId}/validate`, `POST /rules/v1/{ruleId}/simulate` | — | Doc 08 |
| Released Versions | SPEC-GXP-006 | WP-01 | `POST /rules/v1/drafts`, `POST /rules/v1/{ruleId}/validate`, `POST /rules/v1/{ruleId}/simulate` | policy lookup (Doc 04) | Doc 08 |
| Impact Analysis | SPEC-GXP-006 | WP-01 | `POST /rules/v1/drafts`, `POST /rules/v1/{ruleId}/validate`, `POST /rules/v1/{ruleId}/simulate` | — | Doc 08 |
| Product Catalogue | SPEC-EBMR-000 | WP-02 | `POST /products/v1/drafts`, `PUT /products/v1/drafts/{id}`, `POST /products/v1/drafts/{id}/submit` | — | Doc 09 |
| Product Version Editor | SPEC-EBMR-000 | WP-02 | `POST /products/v1/drafts`, `PUT /products/v1/drafts/{id}`, `POST /products/v1/drafts/{id}/submit` | — | Doc 09 |
| Constituent Builder | SPEC-EBMR-000 | WP-02 | `POST /products/v1/drafts`, `PUT /products/v1/drafts/{id}`, `POST /products/v1/drafts/{id}/submit` | — | Doc 09 |
| DDCP Compatibility Matrix | SPEC-EBMR-000 | WP-02 | `POST /products/v1/drafts`, `PUT /products/v1/drafts/{id}`, `POST /products/v1/drafts/{id}/submit` | — | Doc 09 |
| Regulatory/Manufacturing Profile | SPEC-EBMR-000 | WP-02 | `POST /products/v1/drafts`, `PUT /products/v1/drafts/{id}`, `POST /products/v1/drafts/{id}/submit` | — | Doc 09 |
| Site Admission | SPEC-EBMR-000 | WP-02 | `POST /products/v1/drafts`, `PUT /products/v1/drafts/{id}`, `POST /products/v1/drafts/{id}/submit` | — | Doc 09 |
| Specifications & Packaging Links | SPEC-EBMR-000 | WP-02 | `POST /products/v1/drafts`, `PUT /products/v1/drafts/{id}`, `POST /products/v1/drafts/{id}/submit` | — | Doc 09 |
| Release Readiness Checklist | SPEC-EBMR-000 | WP-02 | `POST /products/v1/drafts`, `PUT /products/v1/drafts/{id}`, `POST /products/v1/drafts/{id}/submit` | policy lookup (Doc 04) | Doc 09 |
| Version Comparison | SPEC-EBMR-000 | WP-02 | `POST /products/v1/drafts`, `PUT /products/v1/drafts/{id}`, `POST /products/v1/drafts/{id}/submit` | — | Doc 09 |
| Product Audit / History | SPEC-EBMR-000 | WP-02 | `POST /products/v1/drafts`, `PUT /products/v1/drafts/{id}`, `POST /products/v1/drafts/{id}/submit` | — | Doc 09 |
| Recipe Catalogue | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | — | Doc 10 |
| Recipe Header/Product/Batch Size | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | — | Doc 10 |
| Section & Step Builder | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | — | Doc 10 |
| Dependency Graph View | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | — | Doc 10 |
| Materials | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | — | Doc 10 |
| Equipment | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | — | Doc 10 |
| Parameters/Calculations | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | — | Doc 10 |
| QC/Sampling | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | — | Doc 10 |
| Signatures/Verification | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | policy lookup (Doc 04) | Doc 10 |
| Exceptions/Timers | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | — | Doc 10 |
| Packaging/Label | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | — | Doc 10 |
| Release Readiness | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | policy lookup (Doc 04) | Doc 10 |
| Version Compare | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | — | Doc 10 |
| Simulation | SPEC-EBMR-001 | WP-02 | `POST /recipes/v1/drafts`, `PUT /recipes/v1/drafts/{id}`, `POST /recipes/v1/drafts/{id}/validate` | — | Doc 10 |
| batch header; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| current section/step; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| instruction; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| required materials/equipment; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| input controls; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| scanner/balance/device status; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| target/limits; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| evidence; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| timer; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| verifier/signature; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | policy lookup (Doc 04) | Doc 11 |
| hold/exception; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| next permitted action. | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| all active batches; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| bottlenecks; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| holds; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| exceptions; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| overdue timers; | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | — | Doc 11 |
| operator assignments. | SPEC-EBMR-002 | WP-02 | `POST /batches/v1`, `POST /batches/{id}/issue`, `POST /batches/{id}/start` | policy lookup (Doc 04) | Doc 11 |
| Device Lot Dashboard | SPEC-EBMR-003 | WP-02 | `POST /devices/v1/lots`, `POST /devices/v1/units/bulk-create`, `POST /devices/v1/units/{id}/components` | — | Doc 12 |
| Serial/Unit Search | SPEC-EBMR-003 | WP-02 | `POST /devices/v1/lots`, `POST /devices/v1/units/bulk-create`, `POST /devices/v1/units/{id}/components` | — | Doc 12 |
| Assembly Execution | SPEC-EBMR-003 | WP-02 | `POST /devices/v1/lots`, `POST /devices/v1/units/bulk-create`, `POST /devices/v1/units/{id}/components` | — | Doc 12 |
| Test Station View | SPEC-EBMR-003 | WP-02 | `POST /devices/v1/lots`, `POST /devices/v1/units/bulk-create`, `POST /devices/v1/units/{id}/components` | — | Doc 12 |
| Inspection View | SPEC-EBMR-003 | WP-02 | `POST /devices/v1/lots`, `POST /devices/v1/units/bulk-create`, `POST /devices/v1/units/{id}/components` | — | Doc 12 |
| NCR/Rework | SPEC-EBMR-003 | WP-02 | `POST /devices/v1/lots`, `POST /devices/v1/units/bulk-create`, `POST /devices/v1/units/{id}/components` | — | Doc 12 |
| Unit History | SPEC-EBMR-003 | WP-02 | `POST /devices/v1/lots`, `POST /devices/v1/units/bulk-create`, `POST /devices/v1/units/{id}/components` | — | Doc 12 |
| UDI/Label | SPEC-EBMR-003 | WP-02 | `POST /devices/v1/lots`, `POST /devices/v1/units/bulk-create`, `POST /devices/v1/units/{id}/components` | — | Doc 12 |
| Release Readiness | SPEC-EBMR-003 | WP-02 | `POST /devices/v1/lots`, `POST /devices/v1/units/bulk-create`, `POST /devices/v1/units/{id}/components` | policy lookup (Doc 04) | Doc 12 |
| Device History Export | SPEC-EBMR-003 | WP-02 | `POST /devices/v1/lots`, `POST /devices/v1/units/bulk-create`, `POST /devices/v1/units/{id}/components` | — | Doc 12 |
| Genealogy Search | SPEC-EBMR-004 | WP-03 | `GET /genealogy/v1/nodes/lookup?...`, `GET /genealogy/v1/nodes/{id}/ancestors`, `GET /genealogy/v1/nodes/{id}/descendants` | — | Doc 13 |
| Interactive Trace Tree/Graph | SPEC-EBMR-004 | WP-03 | `GET /genealogy/v1/nodes/lookup?...`, `GET /genealogy/v1/nodes/{id}/ancestors`, `GET /genealogy/v1/nodes/{id}/descendants` | — | Doc 13 |
| Material Lot Impact | SPEC-EBMR-004 | WP-03 | `GET /genealogy/v1/nodes/lookup?...`, `GET /genealogy/v1/nodes/{id}/ancestors`, `GET /genealogy/v1/nodes/{id}/descendants` | — | Doc 13 |
| Serial History | SPEC-EBMR-004 | WP-03 | `GET /genealogy/v1/nodes/lookup?...`, `GET /genealogy/v1/nodes/{id}/ancestors`, `GET /genealogy/v1/nodes/{id}/descendants` | — | Doc 13 |
| DDCP Constituent View | SPEC-EBMR-004 | WP-03 | `GET /genealogy/v1/nodes/lookup?...`, `GET /genealogy/v1/nodes/{id}/ancestors`, `GET /genealogy/v1/nodes/{id}/descendants` | — | Doc 13 |
| Recall Impact Assessment | SPEC-EBMR-004 | WP-03 | `GET /genealogy/v1/nodes/lookup?...`, `GET /genealogy/v1/nodes/{id}/ancestors`, `GET /genealogy/v1/nodes/{id}/descendants` | — | Doc 13 |
| Saved/Approved Impact Snapshot | SPEC-EBMR-004 | WP-03 | `GET /genealogy/v1/nodes/lookup?...`, `GET /genealogy/v1/nodes/{id}/ancestors`, `GET /genealogy/v1/nodes/{id}/descendants` | policy lookup (Doc 04) | Doc 13 |
| Export | SPEC-EBMR-004 | WP-03 | `GET /genealogy/v1/nodes/lookup?...`, `GET /genealogy/v1/nodes/{id}/ancestors`, `GET /genealogy/v1/nodes/{id}/descendants` | — | Doc 13 |
| Batch Header / Product / Recipe | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | — | Doc 14 |
| Release Blockers | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | policy lookup (Doc 04) | Doc 14 |
| Exception Summary by severity/category | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | — | Doc 14 |
| Corrections & Overrides | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | — | Doc 14 |
| QC/OOS/OOT | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | — | Doc 14 |
| Materials | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | — | Doc 14 |
| Equipment/Environment | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | — | Doc 14 |
| Packaging/Labels | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | — | Doc 14 |
| Genealogy | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | — | Doc 14 |
| Yield/Reconciliation | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | — | Doc 14 |
| Signatures | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | policy lookup (Doc 04) | Doc 14 |
| Audit Trail | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | — | Doc 14 |
| Full Record | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | — | Doc 14 |
| Review Checklist | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | — | Doc 14 |
| Reviewer Comments / Actions | SPEC-EBMR-005 | WP-03 | `POST /qa-review/v1/batches/{batchId}/packages`, `GET /qa-review/v1/packages/{id}`, `GET /qa-review/v1/packages/{id}/exceptions` | — | Doc 14 |
| Release Dashboard | SPEC-EBMR-006 | WP-03 | `POST /release/v1/scopes/{type}/{id}/evaluate`, `GET /release/v1/scopes/{id}/eligibility`, `POST /release/v1/scopes/{id}/release` | policy lookup (Doc 04) | Doc 15 |
| Scope Header | SPEC-EBMR-006 | WP-03 | `POST /release/v1/scopes/{type}/{id}/evaluate`, `GET /release/v1/scopes/{id}/eligibility`, `POST /release/v1/scopes/{id}/release` | — | Doc 15 |
| Eligibility Summary | SPEC-EBMR-006 | WP-03 | `POST /release/v1/scopes/{type}/{id}/evaluate`, `GET /release/v1/scopes/{id}/eligibility`, `POST /release/v1/scopes/{id}/release` | — | Doc 15 |
| Blockers/Warnings | SPEC-EBMR-006 | WP-03 | `POST /release/v1/scopes/{type}/{id}/evaluate`, `GET /release/v1/scopes/{id}/eligibility`, `POST /release/v1/scopes/{id}/release` | — | Doc 15 |
| QA Review Status | SPEC-EBMR-006 | WP-03 | `POST /release/v1/scopes/{type}/{id}/evaluate`, `GET /release/v1/scopes/{id}/eligibility`, `POST /release/v1/scopes/{id}/release` | — | Doc 15 |
| QC/QMS | SPEC-EBMR-006 | WP-03 | `POST /release/v1/scopes/{type}/{id}/evaluate`, `GET /release/v1/scopes/{id}/eligibility`, `POST /release/v1/scopes/{id}/release` | — | Doc 15 |
| Materials/Genealogy | SPEC-EBMR-006 | WP-03 | `POST /release/v1/scopes/{type}/{id}/evaluate`, `GET /release/v1/scopes/{id}/eligibility`, `POST /release/v1/scopes/{id}/release` | — | Doc 15 |
| Packaging/Label | SPEC-EBMR-006 | WP-03 | `POST /release/v1/scopes/{type}/{id}/evaluate`, `GET /release/v1/scopes/{id}/eligibility`, `POST /release/v1/scopes/{id}/release` | — | Doc 15 |
| Yield/Reconciliation | SPEC-EBMR-006 | WP-03 | `POST /release/v1/scopes/{type}/{id}/evaluate`, `GET /release/v1/scopes/{id}/eligibility`, `POST /release/v1/scopes/{id}/release` | — | Doc 15 |
| Release Decision | SPEC-EBMR-006 | WP-03 | `POST /release/v1/scopes/{type}/{id}/evaluate`, `GET /release/v1/scopes/{id}/eligibility`, `POST /release/v1/scopes/{id}/release` | policy lookup (Doc 04) | Doc 15 |
| Signature Dialog | SPEC-EBMR-006 | WP-03 | `POST /release/v1/scopes/{type}/{id}/evaluate`, `GET /release/v1/scopes/{id}/eligibility`, `POST /release/v1/scopes/{id}/release` | policy lookup (Doc 04) | Doc 15 |
| Release Package | SPEC-EBMR-006 | WP-03 | `POST /release/v1/scopes/{type}/{id}/evaluate`, `GET /release/v1/scopes/{id}/eligibility`, `POST /release/v1/scopes/{id}/release` | policy lookup (Doc 04) | Doc 15 |
| Packaging Run | SPEC-EBMR-007 | WP-03 | `POST /packaging/v1/runs`, `POST /packaging/v1/runs/{id}/line-clearance`, `POST /packaging/v1/runs/{id}/labels/issue` | — | Doc 16 |
| Line Clearance | SPEC-EBMR-007 | WP-03 | `POST /packaging/v1/runs`, `POST /packaging/v1/runs/{id}/line-clearance`, `POST /packaging/v1/runs/{id}/labels/issue` | — | Doc 16 |
| Packaging Materials | SPEC-EBMR-007 | WP-03 | `POST /packaging/v1/runs`, `POST /packaging/v1/runs/{id}/line-clearance`, `POST /packaging/v1/runs/{id}/labels/issue` | — | Doc 16 |
| Label Issuance | SPEC-EBMR-007 | WP-03 | `POST /packaging/v1/runs`, `POST /packaging/v1/runs/{id}/line-clearance`, `POST /packaging/v1/runs/{id}/labels/issue` | — | Doc 16 |
| Print/Reprint | SPEC-EBMR-007 | WP-03 | `POST /packaging/v1/runs`, `POST /packaging/v1/runs/{id}/line-clearance`, `POST /packaging/v1/runs/{id}/labels/issue` | — | Doc 16 |
| Application Verification | SPEC-EBMR-007 | WP-03 | `POST /packaging/v1/runs`, `POST /packaging/v1/runs/{id}/line-clearance`, `POST /packaging/v1/runs/{id}/labels/issue` | policy lookup (Doc 04) | Doc 16 |
| Inspection | SPEC-EBMR-007 | WP-03 | `POST /packaging/v1/runs`, `POST /packaging/v1/runs/{id}/line-clearance`, `POST /packaging/v1/runs/{id}/labels/issue` | — | Doc 16 |
| Label Reconciliation | SPEC-EBMR-007 | WP-03 | `POST /packaging/v1/runs`, `POST /packaging/v1/runs/{id}/line-clearance`, `POST /packaging/v1/runs/{id}/labels/issue` | — | Doc 16 |
| Packaging Reconciliation | SPEC-EBMR-007 | WP-03 | `POST /packaging/v1/runs`, `POST /packaging/v1/runs/{id}/line-clearance`, `POST /packaging/v1/runs/{id}/labels/issue` | — | Doc 16 |
| Serialization/Aggregation | SPEC-EBMR-007 | WP-03 | `POST /packaging/v1/runs`, `POST /packaging/v1/runs/{id}/line-clearance`, `POST /packaging/v1/runs/{id}/labels/issue` | — | Doc 16 |
| Completion | SPEC-EBMR-007 | WP-03 | `POST /packaging/v1/runs`, `POST /packaging/v1/runs/{id}/line-clearance`, `POST /packaging/v1/runs/{id}/labels/issue` | — | Doc 16 |
| phase; | SPEC-EBMR-008 | WP-03 | `POST /manufacturing-calculations/v1/yield/evaluate`, `POST /manufacturing-calculations/v1/potency/evaluate`, `POST /reconciliation/v1/material/evaluate` | — | Doc 17 |
| theoretical quantity; | SPEC-EBMR-008 | WP-03 | `POST /manufacturing-calculations/v1/yield/evaluate`, `POST /manufacturing-calculations/v1/potency/evaluate`, `POST /reconciliation/v1/material/evaluate` | — | Doc 17 |
| actual quantity; | SPEC-EBMR-008 | WP-03 | `POST /manufacturing-calculations/v1/yield/evaluate`, `POST /manufacturing-calculations/v1/potency/evaluate`, `POST /reconciliation/v1/material/evaluate` | — | Doc 17 |
| UOM; | SPEC-EBMR-008 | WP-03 | `POST /manufacturing-calculations/v1/yield/evaluate`, `POST /manufacturing-calculations/v1/potency/evaluate`, `POST /reconciliation/v1/material/evaluate` | — | Doc 17 |
| formula/version; | SPEC-EBMR-008 | WP-03 | `POST /manufacturing-calculations/v1/yield/evaluate`, `POST /manufacturing-calculations/v1/potency/evaluate`, `POST /reconciliation/v1/material/evaluate` | — | Doc 17 |
| calculated percentage; | SPEC-EBMR-008 | WP-03 | `POST /manufacturing-calculations/v1/yield/evaluate`, `POST /manufacturing-calculations/v1/potency/evaluate`, `POST /reconciliation/v1/material/evaluate` | — | Doc 17 |
| limits; | SPEC-EBMR-008 | WP-03 | `POST /manufacturing-calculations/v1/yield/evaluate`, `POST /manufacturing-calculations/v1/potency/evaluate`, `POST /reconciliation/v1/material/evaluate` | — | Doc 17 |
| outcome; | SPEC-EBMR-008 | WP-03 | `POST /manufacturing-calculations/v1/yield/evaluate`, `POST /manufacturing-calculations/v1/potency/evaluate`, `POST /reconciliation/v1/material/evaluate` | — | Doc 17 |
| input source drilldown; | SPEC-EBMR-008 | WP-03 | `POST /manufacturing-calculations/v1/yield/evaluate`, `POST /manufacturing-calculations/v1/potency/evaluate`, `POST /reconciliation/v1/material/evaluate` | — | Doc 17 |
| verifier/signature. | SPEC-EBMR-008 | WP-03 | `POST /manufacturing-calculations/v1/yield/evaluate`, `POST /manufacturing-calculations/v1/potency/evaluate`, `POST /reconciliation/v1/material/evaluate` | policy lookup (Doc 04) | Doc 17 |
| Supplier Catalogue | SPEC-MAT-001 | WP-04 | `POST /suppliers/v1`, `POST /suppliers/{id}/qualifications`, `POST /supplier-qualifications/{id}/approve` | — | Doc 18 |
| Supplier Qualification | SPEC-MAT-001 | WP-04 | `POST /suppliers/v1`, `POST /suppliers/{id}/qualifications`, `POST /supplier-qualifications/{id}/approve` | — | Doc 18 |
| Supplier Audit | SPEC-MAT-001 | WP-04 | `POST /suppliers/v1`, `POST /suppliers/{id}/qualifications`, `POST /supplier-qualifications/{id}/approve` | — | Doc 18 |
| Approved Supplier List | SPEC-MAT-001 | WP-04 | `POST /suppliers/v1`, `POST /suppliers/{id}/qualifications`, `POST /supplier-qualifications/{id}/approve` | policy lookup (Doc 04) | Doc 18 |
| Material/Source Matrix | SPEC-MAT-001 | WP-04 | `POST /suppliers/v1`, `POST /suppliers/{id}/qualifications`, `POST /supplier-qualifications/{id}/approve` | — | Doc 18 |
| Supplier Performance | SPEC-MAT-001 | WP-04 | `POST /suppliers/v1`, `POST /suppliers/{id}/qualifications`, `POST /supplier-qualifications/{id}/approve` | — | Doc 18 |
| SCAR Links | SPEC-MAT-001 | WP-04 | `POST /suppliers/v1`, `POST /suppliers/{id}/qualifications`, `POST /supplier-qualifications/{id}/approve` | — | Doc 18 |
| RFQ/Quote Comparison | SPEC-MAT-001 | WP-04 | `POST /suppliers/v1`, `POST /suppliers/{id}/qualifications`, `POST /supplier-qualifications/{id}/approve` | — | Doc 18 |
| PO Regulated Requirements | SPEC-MAT-001 | WP-04 | `POST /suppliers/v1`, `POST /suppliers/{id}/qualifications`, `POST /supplier-qualifications/{id}/approve` | — | Doc 18 |
| Supplier Quality Dashboard | SPEC-MAT-001 | WP-04 | `POST /suppliers/v1`, `POST /suppliers/{id}/qualifications`, `POST /supplier-qualifications/{id}/approve` | — | Doc 18 |
| Expected Receipts | SPEC-MAT-002A | WP-04 | `POST /materials/v1/receipts`, `POST /materials/v1/receipts/{id}/examine`, `POST /materials/v1/lots/{id}/sampling-orders` | — | Doc 19 |
| Receiving | SPEC-MAT-002A | WP-04 | `POST /materials/v1/receipts`, `POST /materials/v1/receipts/{id}/examine`, `POST /materials/v1/lots/{id}/sampling-orders` | — | Doc 19 |
| Visual Examination | SPEC-MAT-002A | WP-04 | `POST /materials/v1/receipts`, `POST /materials/v1/receipts/{id}/examine`, `POST /materials/v1/lots/{id}/sampling-orders` | — | Doc 19 |
| Lot/Container Labeling | SPEC-MAT-002A | WP-04 | `POST /materials/v1/receipts`, `POST /materials/v1/receipts/{id}/examine`, `POST /materials/v1/lots/{id}/sampling-orders` | — | Doc 19 |
| Quarantine Dashboard | SPEC-MAT-002A | WP-04 | `POST /materials/v1/receipts`, `POST /materials/v1/receipts/{id}/examine`, `POST /materials/v1/lots/{id}/sampling-orders` | — | Doc 19 |
| Sampling | SPEC-MAT-002A | WP-04 | `POST /materials/v1/receipts`, `POST /materials/v1/receipts/{id}/examine`, `POST /materials/v1/lots/{id}/sampling-orders` | — | Doc 19 |
| QC/LIMS Status | SPEC-MAT-002A | WP-04 | `POST /materials/v1/receipts`, `POST /materials/v1/receipts/{id}/examine`, `POST /materials/v1/lots/{id}/sampling-orders` | — | Doc 19 |
| Quality Disposition | SPEC-MAT-002A | WP-04 | `POST /materials/v1/receipts`, `POST /materials/v1/receipts/{id}/examine`, `POST /materials/v1/lots/{id}/sampling-orders` | policy lookup (Doc 04) | Doc 19 |
| Retest/Expiry Dashboard | SPEC-MAT-002A | WP-04 | `POST /materials/v1/receipts`, `POST /materials/v1/receipts/{id}/examine`, `POST /materials/v1/lots/{id}/sampling-orders` | — | Doc 19 |
| Receipt History | SPEC-MAT-002A | WP-04 | `POST /materials/v1/receipts`, `POST /materials/v1/receipts/{id}/examine`, `POST /materials/v1/lots/{id}/sampling-orders` | — | Doc 19 |
| Warehouse Overview | SPEC-MAT-002B | WP-04 | `GET /inventory/v1/availability`, `POST /inventory/v1/reservations`, `POST /inventory/v1/reservations/{id}/release` | — | Doc 20 |
| Material Availability | SPEC-MAT-002B | WP-04 | `GET /inventory/v1/availability`, `POST /inventory/v1/reservations`, `POST /inventory/v1/reservations/{id}/release` | — | Doc 20 |
| Lot/Container Search | SPEC-MAT-002B | WP-04 | `GET /inventory/v1/availability`, `POST /inventory/v1/reservations`, `POST /inventory/v1/reservations/{id}/release` | — | Doc 20 |
| Transfer | SPEC-MAT-002B | WP-04 | `GET /inventory/v1/availability`, `POST /inventory/v1/reservations`, `POST /inventory/v1/reservations/{id}/release` | — | Doc 20 |
| Reservation | SPEC-MAT-002B | WP-04 | `GET /inventory/v1/availability`, `POST /inventory/v1/reservations`, `POST /inventory/v1/reservations/{id}/release` | — | Doc 20 |
| Expiry/Retest | SPEC-MAT-002B | WP-04 | `GET /inventory/v1/availability`, `POST /inventory/v1/reservations`, `POST /inventory/v1/reservations/{id}/release` | — | Doc 20 |
| Quality Hold | SPEC-MAT-002B | WP-04 | `GET /inventory/v1/availability`, `POST /inventory/v1/reservations`, `POST /inventory/v1/reservations/{id}/release` | — | Doc 20 |
| Cycle Count | SPEC-MAT-002B | WP-04 | `GET /inventory/v1/availability`, `POST /inventory/v1/reservations`, `POST /inventory/v1/reservations/{id}/release` | — | Doc 20 |
| Container Split/Merge | SPEC-MAT-002B | WP-04 | `GET /inventory/v1/availability`, `POST /inventory/v1/reservations`, `POST /inventory/v1/reservations/{id}/release` | — | Doc 20 |
| Inventory Ledger | SPEC-MAT-002B | WP-04 | `GET /inventory/v1/availability`, `POST /inventory/v1/reservations`, `POST /inventory/v1/reservations/{id}/release` | — | Doc 20 |
| ERP Reconciliation | SPEC-MAT-002B | WP-04 | `GET /inventory/v1/availability`, `POST /inventory/v1/reservations`, `POST /inventory/v1/reservations/{id}/release` | — | Doc 20 |
| Dispensing Queue | SPEC-MAT-002C | WP-04 | `POST /dispensing/v1/orders`, `POST /dispensing/v1/orders/{id}/select-source`, `POST /dispensing/v1/orders/{id}/start` | — | Doc 21 |
| Scan Batch/Requirement | SPEC-MAT-002C | WP-04 | `POST /dispensing/v1/orders`, `POST /dispensing/v1/orders/{id}/select-source`, `POST /dispensing/v1/orders/{id}/start` | — | Doc 21 |
| Scan Source | SPEC-MAT-002C | WP-04 | `POST /dispensing/v1/orders`, `POST /dispensing/v1/orders/{id}/select-source`, `POST /dispensing/v1/orders/{id}/start` | — | Doc 21 |
| Equipment/Booth Check | SPEC-MAT-002C | WP-04 | `POST /dispensing/v1/orders`, `POST /dispensing/v1/orders/{id}/select-source`, `POST /dispensing/v1/orders/{id}/start` | — | Doc 21 |
| Target Calculation | SPEC-MAT-002C | WP-04 | `POST /dispensing/v1/orders`, `POST /dispensing/v1/orders/{id}/select-source`, `POST /dispensing/v1/orders/{id}/start` | — | Doc 21 |
| Live Weight | SPEC-MAT-002C | WP-04 | `POST /dispensing/v1/orders`, `POST /dispensing/v1/orders/{id}/select-source`, `POST /dispensing/v1/orders/{id}/start` | — | Doc 21 |
| Tolerance | SPEC-MAT-002C | WP-04 | `POST /dispensing/v1/orders`, `POST /dispensing/v1/orders/{id}/select-source`, `POST /dispensing/v1/orders/{id}/start` | — | Doc 21 |
| Verification | SPEC-MAT-002C | WP-04 | `POST /dispensing/v1/orders`, `POST /dispensing/v1/orders/{id}/select-source`, `POST /dispensing/v1/orders/{id}/start` | policy lookup (Doc 04) | Doc 21 |
| Label | SPEC-MAT-002C | WP-04 | `POST /dispensing/v1/orders`, `POST /dispensing/v1/orders/{id}/select-source`, `POST /dispensing/v1/orders/{id}/start` | — | Doc 21 |
| Completed Record | SPEC-MAT-002C | WP-04 | `POST /dispensing/v1/orders`, `POST /dispensing/v1/orders/{id}/select-source`, `POST /dispensing/v1/orders/{id}/start` | — | Doc 21 |
| Batch Material Usage | SPEC-MAT-002D | WP-04 | `POST /materials/v1/consumptions`, `POST /materials/v1/returns`, `POST /inventory/v1/adjustments` | — | Doc 22 |
| Consume | SPEC-MAT-002D | WP-04 | `POST /materials/v1/consumptions`, `POST /materials/v1/returns`, `POST /inventory/v1/adjustments` | — | Doc 22 |
| Return | SPEC-MAT-002D | WP-04 | `POST /materials/v1/consumptions`, `POST /materials/v1/returns`, `POST /inventory/v1/adjustments` | — | Doc 22 |
| Loss/Spill/Sample | SPEC-MAT-002D | WP-04 | `POST /materials/v1/consumptions`, `POST /materials/v1/returns`, `POST /inventory/v1/adjustments` | — | Doc 22 |
| Adjustment Request | SPEC-MAT-002D | WP-04 | `POST /materials/v1/consumptions`, `POST /materials/v1/returns`, `POST /inventory/v1/adjustments` | — | Doc 22 |
| Destruction | SPEC-MAT-002D | WP-04 | `POST /materials/v1/consumptions`, `POST /materials/v1/returns`, `POST /inventory/v1/adjustments` | — | Doc 22 |
| Reconciliation | SPEC-MAT-002D | WP-04 | `POST /materials/v1/consumptions`, `POST /materials/v1/returns`, `POST /inventory/v1/adjustments` | — | Doc 22 |
| ERP Posting/Reconciliation | SPEC-MAT-002D | WP-04 | `POST /materials/v1/consumptions`, `POST /materials/v1/returns`, `POST /inventory/v1/adjustments` | — | Doc 22 |
| Material History | SPEC-MAT-002D | WP-04 | `POST /materials/v1/consumptions`, `POST /materials/v1/returns`, `POST /inventory/v1/adjustments` | — | Doc 22 |
| sample/source; | SPEC-QC-001 | WP-04 | `POST /qc/v1/specifications/drafts`, `POST /qc/v1/specifications/{id}/release`, `POST /qc/v1/samples` | — | Doc 23 |
| method; | SPEC-QC-001 | WP-04 | `POST /qc/v1/specifications/drafts`, `POST /qc/v1/specifications/{id}/release`, `POST /qc/v1/samples` | — | Doc 23 |
| sample amount; | SPEC-QC-001 | WP-04 | `POST /qc/v1/specifications/drafts`, `POST /qc/v1/specifications/{id}/release`, `POST /qc/v1/samples` | — | Doc 23 |
| raw data/evidence; | SPEC-QC-001 | WP-04 | `POST /qc/v1/specifications/drafts`, `POST /qc/v1/specifications/{id}/release`, `POST /qc/v1/samples` | — | Doc 23 |
| calculations; | SPEC-QC-001 | WP-04 | `POST /qc/v1/specifications/drafts`, `POST /qc/v1/specifications/{id}/release`, `POST /qc/v1/samples` | — | Doc 23 |
| result/criterion; | SPEC-QC-001 | WP-04 | `POST /qc/v1/specifications/drafts`, `POST /qc/v1/specifications/{id}/release`, `POST /qc/v1/samples` | — | Doc 23 |
| prior/superseded results; | SPEC-QC-001 | WP-04 | `POST /qc/v1/specifications/drafts`, `POST /qc/v1/specifications/{id}/release`, `POST /qc/v1/samples` | — | Doc 23 |
| system suitability; | SPEC-QC-001 | WP-04 | `POST /qc/v1/specifications/drafts`, `POST /qc/v1/specifications/{id}/release`, `POST /qc/v1/samples` | — | Doc 23 |
| OOS/OOT; | SPEC-QC-001 | WP-04 | `POST /qc/v1/specifications/drafts`, `POST /qc/v1/specifications/{id}/release`, `POST /qc/v1/samples` | — | Doc 23 |
| analyst; | SPEC-QC-001 | WP-04 | `POST /qc/v1/specifications/drafts`, `POST /qc/v1/specifications/{id}/release`, `POST /qc/v1/samples` | — | Doc 23 |
| audit; | SPEC-QC-001 | WP-04 | `POST /qc/v1/specifications/drafts`, `POST /qc/v1/specifications/{id}/release`, `POST /qc/v1/samples` | — | Doc 23 |
| review signature. | SPEC-QC-001 | WP-04 | `POST /qc/v1/specifications/drafts`, `POST /qc/v1/specifications/{id}/release`, `POST /qc/v1/samples` | policy lookup (Doc 04) | Doc 23 |
| LIMS Instances | SPEC-QC-002 | WP-04 | `POST /integrations/lims/{instance}/samples`, `POST /integrations/lims/{instance}/samples/{id}/cancel`, `POST /integrations/lims/{instance}/reconcile` | — | Doc 24 |
| Mapping | SPEC-QC-002 | WP-04 | `POST /integrations/lims/{instance}/samples`, `POST /integrations/lims/{instance}/samples/{id}/cancel`, `POST /integrations/lims/{instance}/reconcile` | — | Doc 24 |
| Message Monitor | SPEC-QC-002 | WP-04 | `POST /integrations/lims/{instance}/samples`, `POST /integrations/lims/{instance}/samples/{id}/cancel`, `POST /integrations/lims/{instance}/reconcile` | — | Doc 24 |
| Dead Letter Queue | SPEC-QC-002 | WP-04 | `POST /integrations/lims/{instance}/samples`, `POST /integrations/lims/{instance}/samples/{id}/cancel`, `POST /integrations/lims/{instance}/reconcile` | — | Doc 24 |
| Reconciliation Differences | SPEC-QC-002 | WP-04 | `POST /integrations/lims/{instance}/samples`, `POST /integrations/lims/{instance}/samples/{id}/cancel`, `POST /integrations/lims/{instance}/reconcile` | — | Doc 24 |
| Manual Mapping Resolution | SPEC-QC-002 | WP-04 | `POST /integrations/lims/{instance}/samples`, `POST /integrations/lims/{instance}/samples/{id}/cancel`, `POST /integrations/lims/{instance}/reconcile` | — | Doc 24 |
| Result History | SPEC-QC-002 | WP-04 | `POST /integrations/lims/{instance}/samples`, `POST /integrations/lims/{instance}/samples/{id}/cancel`, `POST /integrations/lims/{instance}/reconcile` | — | Doc 24 |
| Health Dashboard | SPEC-QC-002 | WP-04 | `POST /integrations/lims/{instance}/samples`, `POST /integrations/lims/{instance}/samples/{id}/cancel`, `POST /integrations/lims/{instance}/reconcile` | — | Doc 24 |
| correct mapping; | SPEC-QC-002 | WP-04 | `POST /integrations/lims/{instance}/samples`, `POST /integrations/lims/{instance}/samples/{id}/cancel`, `POST /integrations/lims/{instance}/reconcile` | — | Doc 24 |
| retry/replay exact stored message; | SPEC-QC-002 | WP-04 | `POST /integrations/lims/{instance}/samples`, `POST /integrations/lims/{instance}/samples/{id}/cancel`, `POST /integrations/lims/{instance}/reconcile` | — | Doc 24 |
| acknowledge known duplicate; | SPEC-QC-002 | WP-04 | `POST /integrations/lims/{instance}/samples`, `POST /integrations/lims/{instance}/samples/{id}/cancel`, `POST /integrations/lims/{instance}/reconcile` | — | Doc 24 |
| link external/internal IDs. | SPEC-QC-002 | WP-04 | `POST /integrations/lims/{instance}/samples`, `POST /integrations/lims/{instance}/samples/{id}/cancel`, `POST /integrations/lims/{instance}/reconcile` | — | Doc 24 |
| OOS Header / Original Result | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | — | Doc 25 |
| Raw Data / Method | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | — | Doc 25 |
| Laboratory Investigation | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | — | Doc 25 |
| Assignable Cause Decision | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | policy lookup (Doc 04) | Doc 25 |
| Manufacturing/Extended Investigation | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | — | Doc 25 |
| Retest Plan/Results | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | — | Doc 25 |
| Resample Plan/Results | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | — | Doc 25 |
| Impact Assessment | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | — | Doc 25 |
| CAPA/Change Links | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | — | Doc 25 |
| Final Disposition | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | policy lookup (Doc 04) | Doc 25 |
| QA Closure | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | — | Doc 25 |
| Full Audit | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | — | Doc 25 |
| OOT Signal | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | policy lookup (Doc 04) | Doc 25 |
| Trend Chart / Historical Context | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | — | Doc 25 |
| Investigation | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | — | Doc 25 |
| Impact/Action | SPEC-QC-003 | WP-04 | `POST /quality/oos/v1/from-result/{resultId}`, `GET /quality/oos/v1/{id}`, `POST /quality/oos/v1/{id}/lab-investigation` | — | Doc 25 |
| Deviation Dashboard | SPEC-QMS-001 | WP-05 | `POST /qms/v1/deviations`, `POST /qms/v1/deviations/{id}/triage`, `POST /qms/v1/deviations/{id}/contain` | — | Doc 26 |
| Initiation/Triage | SPEC-QMS-001 | WP-05 | `POST /qms/v1/deviations`, `POST /qms/v1/deviations/{id}/triage`, `POST /qms/v1/deviations/{id}/contain` | — | Doc 26 |
| Containment | SPEC-QMS-001 | WP-05 | `POST /qms/v1/deviations`, `POST /qms/v1/deviations/{id}/triage`, `POST /qms/v1/deviations/{id}/contain` | — | Doc 26 |
| Investigation & Evidence | SPEC-QMS-001 | WP-05 | `POST /qms/v1/deviations`, `POST /qms/v1/deviations/{id}/triage`, `POST /qms/v1/deviations/{id}/contain` | — | Doc 26 |
| Root Cause | SPEC-QMS-001 | WP-05 | `POST /qms/v1/deviations`, `POST /qms/v1/deviations/{id}/triage`, `POST /qms/v1/deviations/{id}/contain` | — | Doc 26 |
| Impact Assessment | SPEC-QMS-001 | WP-05 | `POST /qms/v1/deviations`, `POST /qms/v1/deviations/{id}/triage`, `POST /qms/v1/deviations/{id}/contain` | — | Doc 26 |
| Disposition | SPEC-QMS-001 | WP-05 | `POST /qms/v1/deviations`, `POST /qms/v1/deviations/{id}/triage`, `POST /qms/v1/deviations/{id}/contain` | policy lookup (Doc 04) | Doc 26 |
| Linked CAPA/Change | SPEC-QMS-001 | WP-05 | `POST /qms/v1/deviations`, `POST /qms/v1/deviations/{id}/triage`, `POST /qms/v1/deviations/{id}/contain` | — | Doc 26 |
| QA Closure | SPEC-QMS-001 | WP-05 | `POST /qms/v1/deviations`, `POST /qms/v1/deviations/{id}/triage`, `POST /qms/v1/deviations/{id}/contain` | — | Doc 26 |
| Audit/History | SPEC-QMS-001 | WP-05 | `POST /qms/v1/deviations`, `POST /qms/v1/deviations/{id}/triage`, `POST /qms/v1/deviations/{id}/contain` | — | Doc 26 |
| CAPA Dashboard | SPEC-QMS-002 | WP-05 | `POST /qms/v1/capas`, `POST /qms/v1/capas/{id}/plan`, `POST /qms/v1/capas/{id}/actions` | — | Doc 27 |
| Problem/Scope | SPEC-QMS-002 | WP-05 | `POST /qms/v1/capas`, `POST /qms/v1/capas/{id}/plan`, `POST /qms/v1/capas/{id}/actions` | — | Doc 27 |
| Root Cause | SPEC-QMS-002 | WP-05 | `POST /qms/v1/capas`, `POST /qms/v1/capas/{id}/plan`, `POST /qms/v1/capas/{id}/actions` | — | Doc 27 |
| Action Plan | SPEC-QMS-002 | WP-05 | `POST /qms/v1/capas`, `POST /qms/v1/capas/{id}/plan`, `POST /qms/v1/capas/{id}/actions` | — | Doc 27 |
| Dependencies | SPEC-QMS-002 | WP-05 | `POST /qms/v1/capas`, `POST /qms/v1/capas/{id}/plan`, `POST /qms/v1/capas/{id}/actions` | — | Doc 27 |
| Implementation Evidence | SPEC-QMS-002 | WP-05 | `POST /qms/v1/capas`, `POST /qms/v1/capas/{id}/plan`, `POST /qms/v1/capas/{id}/actions` | — | Doc 27 |
| Effectiveness Plan | SPEC-QMS-002 | WP-05 | `POST /qms/v1/capas`, `POST /qms/v1/capas/{id}/plan`, `POST /qms/v1/capas/{id}/actions` | — | Doc 27 |
| Effectiveness Review | SPEC-QMS-002 | WP-05 | `POST /qms/v1/capas`, `POST /qms/v1/capas/{id}/plan`, `POST /qms/v1/capas/{id}/actions` | — | Doc 27 |
| QA Closure | SPEC-QMS-002 | WP-05 | `POST /qms/v1/capas`, `POST /qms/v1/capas/{id}/plan`, `POST /qms/v1/capas/{id}/actions` | — | Doc 27 |
| Audit | SPEC-QMS-002 | WP-05 | `POST /qms/v1/capas`, `POST /qms/v1/capas/{id}/plan`, `POST /qms/v1/capas/{id}/actions` | — | Doc 27 |
| NCR Dashboard | SPEC-QMS-003 | WP-05 | `POST /qms/v1/nonconformances`, `POST /qms/v1/nonconformances/{id}/segregate`, `POST /qms/v1/nonconformances/{id}/evaluate` | — | Doc 28 |
| Initiation | SPEC-QMS-003 | WP-05 | `POST /qms/v1/nonconformances`, `POST /qms/v1/nonconformances/{id}/segregate`, `POST /qms/v1/nonconformances/{id}/evaluate` | — | Doc 28 |
| Affected Scope | SPEC-QMS-003 | WP-05 | `POST /qms/v1/nonconformances`, `POST /qms/v1/nonconformances/{id}/segregate`, `POST /qms/v1/nonconformances/{id}/evaluate` | — | Doc 28 |
| Segregation | SPEC-QMS-003 | WP-05 | `POST /qms/v1/nonconformances`, `POST /qms/v1/nonconformances/{id}/segregate`, `POST /qms/v1/nonconformances/{id}/evaluate` | — | Doc 28 |
| Evaluation | SPEC-QMS-003 | WP-05 | `POST /qms/v1/nonconformances`, `POST /qms/v1/nonconformances/{id}/segregate`, `POST /qms/v1/nonconformances/{id}/evaluate` | — | Doc 28 |
| Disposition | SPEC-QMS-003 | WP-05 | `POST /qms/v1/nonconformances`, `POST /qms/v1/nonconformances/{id}/segregate`, `POST /qms/v1/nonconformances/{id}/evaluate` | policy lookup (Doc 04) | Doc 28 |
| Rework/Retest | SPEC-QMS-003 | WP-05 | `POST /qms/v1/nonconformances`, `POST /qms/v1/nonconformances/{id}/segregate`, `POST /qms/v1/nonconformances/{id}/evaluate` | — | Doc 28 |
| Supplier/CAPA Links | SPEC-QMS-003 | WP-05 | `POST /qms/v1/nonconformances`, `POST /qms/v1/nonconformances/{id}/segregate`, `POST /qms/v1/nonconformances/{id}/evaluate` | — | Doc 28 |
| Closure | SPEC-QMS-003 | WP-05 | `POST /qms/v1/nonconformances`, `POST /qms/v1/nonconformances/{id}/segregate`, `POST /qms/v1/nonconformances/{id}/evaluate` | — | Doc 28 |
| Audit | SPEC-QMS-003 | WP-05 | `POST /qms/v1/nonconformances`, `POST /qms/v1/nonconformances/{id}/segregate`, `POST /qms/v1/nonconformances/{id}/evaluate` | — | Doc 28 |
| Change Dashboard | SPEC-QMS-004 | WP-05 | `POST /qms/v1/changes`, `POST /qms/v1/changes/{id}/impact`, `POST /qms/v1/changes/{id}/approve` | — | Doc 29 |
| Request | SPEC-QMS-004 | WP-05 | `POST /qms/v1/changes`, `POST /qms/v1/changes/{id}/impact`, `POST /qms/v1/changes/{id}/approve` | — | Doc 29 |
| Affected Objects | SPEC-QMS-004 | WP-05 | `POST /qms/v1/changes`, `POST /qms/v1/changes/{id}/impact`, `POST /qms/v1/changes/{id}/approve` | — | Doc 29 |
| Impact Assessments | SPEC-QMS-004 | WP-05 | `POST /qms/v1/changes`, `POST /qms/v1/changes/{id}/impact`, `POST /qms/v1/changes/{id}/approve` | — | Doc 29 |
| Risk | SPEC-QMS-004 | WP-05 | `POST /qms/v1/changes`, `POST /qms/v1/changes/{id}/impact`, `POST /qms/v1/changes/{id}/approve` | — | Doc 29 |
| Implementation Plan | SPEC-QMS-004 | WP-05 | `POST /qms/v1/changes`, `POST /qms/v1/changes/{id}/impact`, `POST /qms/v1/changes/{id}/approve` | — | Doc 29 |
| Validation/Training | SPEC-QMS-004 | WP-05 | `POST /qms/v1/changes`, `POST /qms/v1/changes/{id}/impact`, `POST /qms/v1/changes/{id}/approve` | — | Doc 29 |
| Approvals | SPEC-QMS-004 | WP-05 | `POST /qms/v1/changes`, `POST /qms/v1/changes/{id}/impact`, `POST /qms/v1/changes/{id}/approve` | — | Doc 29 |
| Execution Evidence | SPEC-QMS-004 | WP-05 | `POST /qms/v1/changes`, `POST /qms/v1/changes/{id}/impact`, `POST /qms/v1/changes/{id}/approve` | — | Doc 29 |
| Post-Implementation Review | SPEC-QMS-004 | WP-05 | `POST /qms/v1/changes`, `POST /qms/v1/changes/{id}/impact`, `POST /qms/v1/changes/{id}/approve` | — | Doc 29 |
| Closure | SPEC-QMS-004 | WP-05 | `POST /qms/v1/changes`, `POST /qms/v1/changes/{id}/impact`, `POST /qms/v1/changes/{id}/approve` | — | Doc 29 |
| Document Library | SPEC-QMS-005 | WP-05 | `POST /documents/v1/drafts`, `POST /documents/v1/drafts/{id}/submit`, `POST /documents/v1/drafts/{id}/release` | — | Doc 30 |
| Document Editor/Upload | SPEC-QMS-005 | WP-05 | `POST /documents/v1/drafts`, `POST /documents/v1/drafts/{id}/submit`, `POST /documents/v1/drafts/{id}/release` | — | Doc 30 |
| Review/Approval | SPEC-QMS-005 | WP-05 | `POST /documents/v1/drafts`, `POST /documents/v1/drafts/{id}/submit`, `POST /documents/v1/drafts/{id}/release` | — | Doc 30 |
| Version Compare | SPEC-QMS-005 | WP-05 | `POST /documents/v1/drafts`, `POST /documents/v1/drafts/{id}/submit`, `POST /documents/v1/drafts/{id}/release` | — | Doc 30 |
| Effective/Obsolete | SPEC-QMS-005 | WP-05 | `POST /documents/v1/drafts`, `POST /documents/v1/drafts/{id}/submit`, `POST /documents/v1/drafts/{id}/release` | — | Doc 30 |
| Controlled Copies | SPEC-QMS-005 | WP-05 | `POST /documents/v1/drafts`, `POST /documents/v1/drafts/{id}/submit`, `POST /documents/v1/drafts/{id}/release` | — | Doc 30 |
| Periodic Review | SPEC-QMS-005 | WP-05 | `POST /documents/v1/drafts`, `POST /documents/v1/drafts/{id}/submit`, `POST /documents/v1/drafts/{id}/release` | — | Doc 30 |
| Training Impact | SPEC-QMS-005 | WP-05 | `POST /documents/v1/drafts`, `POST /documents/v1/drafts/{id}/submit`, `POST /documents/v1/drafts/{id}/release` | — | Doc 30 |
| Audit | SPEC-QMS-005 | WP-05 | `POST /documents/v1/drafts`, `POST /documents/v1/drafts/{id}/submit`, `POST /documents/v1/drafts/{id}/release` | — | Doc 30 |
| Training Dashboard | SPEC-QMS-006 | WP-05 | `POST /training/v1/requirements`, `POST /training/v1/assignments`, `POST /training/v1/assignments/{id}/complete` | — | Doc 31 |
| Curriculum/Requirement | SPEC-QMS-006 | WP-05 | `POST /training/v1/requirements`, `POST /training/v1/assignments`, `POST /training/v1/assignments/{id}/complete` | — | Doc 31 |
| Assignments | SPEC-QMS-006 | WP-05 | `POST /training/v1/requirements`, `POST /training/v1/assignments`, `POST /training/v1/assignments/{id}/complete` | policy lookup (Doc 04) | Doc 31 |
| Learning/Acknowledgment | SPEC-QMS-006 | WP-05 | `POST /training/v1/requirements`, `POST /training/v1/assignments`, `POST /training/v1/assignments/{id}/complete` | — | Doc 31 |
| Assessment | SPEC-QMS-006 | WP-05 | `POST /training/v1/requirements`, `POST /training/v1/assignments`, `POST /training/v1/assignments/{id}/complete` | — | Doc 31 |
| Practical Evaluation | SPEC-QMS-006 | WP-05 | `POST /training/v1/requirements`, `POST /training/v1/assignments`, `POST /training/v1/assignments/{id}/complete` | — | Doc 31 |
| Qualifications | SPEC-QMS-006 | WP-05 | `POST /training/v1/requirements`, `POST /training/v1/assignments`, `POST /training/v1/assignments/{id}/complete` | — | Doc 31 |
| Expiry/Renewal | SPEC-QMS-006 | WP-05 | `POST /training/v1/requirements`, `POST /training/v1/assignments`, `POST /training/v1/assignments/{id}/complete` | — | Doc 31 |
| Training Matrix | SPEC-QMS-006 | WP-05 | `POST /training/v1/requirements`, `POST /training/v1/assignments`, `POST /training/v1/assignments/{id}/complete` | — | Doc 31 |
| Transcript | SPEC-QMS-006 | WP-05 | `POST /training/v1/requirements`, `POST /training/v1/assignments`, `POST /training/v1/assignments/{id}/complete` | — | Doc 31 |
| Supplier Quality Dashboard | SPEC-QMS-007 | WP-05 | `POST /qms/v1/supplier-cases`, `POST /qms/v1/supplier-cases/{id}/scar`, `POST /qms/v1/scars/{id}/response` | — | Doc 32 |
| Supplier Case | SPEC-QMS-007 | WP-05 | `POST /qms/v1/supplier-cases`, `POST /qms/v1/supplier-cases/{id}/scar`, `POST /qms/v1/scars/{id}/response` | — | Doc 32 |
| Containment/ASL Impact | SPEC-QMS-007 | WP-05 | `POST /qms/v1/supplier-cases`, `POST /qms/v1/supplier-cases/{id}/scar`, `POST /qms/v1/scars/{id}/response` | — | Doc 32 |
| SCAR | SPEC-QMS-007 | WP-05 | `POST /qms/v1/supplier-cases`, `POST /qms/v1/supplier-cases/{id}/scar`, `POST /qms/v1/scars/{id}/response` | — | Doc 32 |
| Supplier Response | SPEC-QMS-007 | WP-05 | `POST /qms/v1/supplier-cases`, `POST /qms/v1/supplier-cases/{id}/scar`, `POST /qms/v1/scars/{id}/response` | — | Doc 32 |
| Internal Review | SPEC-QMS-007 | WP-05 | `POST /qms/v1/supplier-cases`, `POST /qms/v1/supplier-cases/{id}/scar`, `POST /qms/v1/scars/{id}/response` | — | Doc 32 |
| Effectiveness | SPEC-QMS-007 | WP-05 | `POST /qms/v1/supplier-cases`, `POST /qms/v1/supplier-cases/{id}/scar`, `POST /qms/v1/scars/{id}/response` | — | Doc 32 |
| Supplier Status | SPEC-QMS-007 | WP-05 | `POST /qms/v1/supplier-cases`, `POST /qms/v1/supplier-cases/{id}/scar`, `POST /qms/v1/scars/{id}/response` | — | Doc 32 |
| History | SPEC-QMS-007 | WP-05 | `POST /qms/v1/supplier-cases`, `POST /qms/v1/supplier-cases/{id}/scar`, `POST /qms/v1/scars/{id}/response` | — | Doc 32 |
| Risk Register | SPEC-QMS-008 | WP-05 | `POST /qms/v1/risks`, `POST /qms/v1/risks/{id}/assessments`, `POST /qms/v1/risks/{id}/controls` | — | Doc 33 |
| Risk Assessment | SPEC-QMS-008 | WP-05 | `POST /qms/v1/risks`, `POST /qms/v1/risks/{id}/assessments`, `POST /qms/v1/risks/{id}/controls` | — | Doc 33 |
| Controls/Mitigations | SPEC-QMS-008 | WP-05 | `POST /qms/v1/risks`, `POST /qms/v1/risks/{id}/assessments`, `POST /qms/v1/risks/{id}/controls` | — | Doc 33 |
| Residual Risk | SPEC-QMS-008 | WP-05 | `POST /qms/v1/risks`, `POST /qms/v1/risks/{id}/assessments`, `POST /qms/v1/risks/{id}/controls` | — | Doc 33 |
| Acceptance | SPEC-QMS-008 | WP-05 | `POST /qms/v1/risks`, `POST /qms/v1/risks/{id}/assessments`, `POST /qms/v1/risks/{id}/controls` | — | Doc 33 |
| Related Events/Changes | SPEC-QMS-008 | WP-05 | `POST /qms/v1/risks`, `POST /qms/v1/risks/{id}/assessments`, `POST /qms/v1/risks/{id}/controls` | — | Doc 33 |
| Review Calendar | SPEC-QMS-008 | WP-05 | `POST /qms/v1/risks`, `POST /qms/v1/risks/{id}/assessments`, `POST /qms/v1/risks/{id}/controls` | — | Doc 33 |
| Dashboard | SPEC-QMS-008 | WP-05 | `POST /qms/v1/risks`, `POST /qms/v1/risks/{id}/assessments`, `POST /qms/v1/risks/{id}/controls` | — | Doc 33 |
| Audit Program | SPEC-QMS-009 | WP-05 | `POST /qms/v1/audits`, `POST /qms/v1/audits/{id}/start`, `POST /qms/v1/audits/{id}/findings` | — | Doc 34 |
| Audit Plan | SPEC-QMS-009 | WP-05 | `POST /qms/v1/audits`, `POST /qms/v1/audits/{id}/start`, `POST /qms/v1/audits/{id}/findings` | — | Doc 34 |
| Checklist | SPEC-QMS-009 | WP-05 | `POST /qms/v1/audits`, `POST /qms/v1/audits/{id}/start`, `POST /qms/v1/audits/{id}/findings` | — | Doc 34 |
| Evidence/Notes | SPEC-QMS-009 | WP-05 | `POST /qms/v1/audits`, `POST /qms/v1/audits/{id}/start`, `POST /qms/v1/audits/{id}/findings` | — | Doc 34 |
| Findings | SPEC-QMS-009 | WP-05 | `POST /qms/v1/audits`, `POST /qms/v1/audits/{id}/start`, `POST /qms/v1/audits/{id}/findings` | — | Doc 34 |
| Report | SPEC-QMS-009 | WP-05 | `POST /qms/v1/audits`, `POST /qms/v1/audits/{id}/start`, `POST /qms/v1/audits/{id}/findings` | — | Doc 34 |
| Responses/CAPA | SPEC-QMS-009 | WP-05 | `POST /qms/v1/audits`, `POST /qms/v1/audits/{id}/start`, `POST /qms/v1/audits/{id}/findings` | — | Doc 34 |
| Follow-Up | SPEC-QMS-009 | WP-05 | `POST /qms/v1/audits`, `POST /qms/v1/audits/{id}/start`, `POST /qms/v1/audits/{id}/findings` | — | Doc 34 |
| Metrics | SPEC-QMS-009 | WP-05 | `POST /qms/v1/audits`, `POST /qms/v1/audits/{id}/start`, `POST /qms/v1/audits/{id}/findings` | — | Doc 34 |
| Complaint Intake | SPEC-QMS-010 | WP-05 | `POST /qms/v1/complaints`, `POST /qms/v1/complaints/{id}/triage`, `POST /qms/v1/complaints/{id}/investigation-decision` | — | Doc 35 |
| Product/Serial Lookup | SPEC-QMS-010 | WP-05 | `POST /qms/v1/complaints`, `POST /qms/v1/complaints/{id}/triage`, `POST /qms/v1/complaints/{id}/investigation-decision` | — | Doc 35 |
| Triage | SPEC-QMS-010 | WP-05 | `POST /qms/v1/complaints`, `POST /qms/v1/complaints/{id}/triage`, `POST /qms/v1/complaints/{id}/investigation-decision` | — | Doc 35 |
| Investigation Decision | SPEC-QMS-010 | WP-05 | `POST /qms/v1/complaints`, `POST /qms/v1/complaints/{id}/triage`, `POST /qms/v1/complaints/{id}/investigation-decision` | — | Doc 35 |
| Manufacturing/Genealogy Evidence | SPEC-QMS-010 | WP-05 | `POST /qms/v1/complaints`, `POST /qms/v1/complaints/{id}/triage`, `POST /qms/v1/complaints/{id}/investigation-decision` | — | Doc 35 |
| Returned Product | SPEC-QMS-010 | WP-05 | `POST /qms/v1/complaints`, `POST /qms/v1/complaints/{id}/triage`, `POST /qms/v1/complaints/{id}/investigation-decision` | — | Doc 35 |
| Reportability Assessment | SPEC-QMS-010 | WP-05 | `POST /qms/v1/complaints`, `POST /qms/v1/complaints/{id}/triage`, `POST /qms/v1/complaints/{id}/investigation-decision` | — | Doc 35 |
| CAPA/Field Action | SPEC-QMS-010 | WP-05 | `POST /qms/v1/complaints`, `POST /qms/v1/complaints/{id}/triage`, `POST /qms/v1/complaints/{id}/investigation-decision` | — | Doc 35 |
| Communications | SPEC-QMS-010 | WP-05 | `POST /qms/v1/complaints`, `POST /qms/v1/complaints/{id}/triage`, `POST /qms/v1/complaints/{id}/investigation-decision` | — | Doc 35 |
| Closure | SPEC-QMS-010 | WP-05 | `POST /qms/v1/complaints`, `POST /qms/v1/complaints/{id}/triage`, `POST /qms/v1/complaints/{id}/investigation-decision` | — | Doc 35 |
| Trend | SPEC-QMS-010 | WP-05 | `POST /qms/v1/complaints`, `POST /qms/v1/complaints/{id}/triage`, `POST /qms/v1/complaints/{id}/investigation-decision` | — | Doc 35 |
| Field Action Dashboard | SPEC-QMS-011 | WP-05 | `POST /qms/v1/field-actions`, `POST /qms/v1/field-actions/{id}/scope`, `POST /qms/v1/field-actions/{id}/reportability` | — | Doc 36 |
| Assessment/Risk | SPEC-QMS-011 | WP-05 | `POST /qms/v1/field-actions`, `POST /qms/v1/field-actions/{id}/scope`, `POST /qms/v1/field-actions/{id}/reportability` | — | Doc 36 |
| Affected Product Scope | SPEC-QMS-011 | WP-05 | `POST /qms/v1/field-actions`, `POST /qms/v1/field-actions/{id}/scope`, `POST /qms/v1/field-actions/{id}/reportability` | — | Doc 36 |
| Distribution/Consignees | SPEC-QMS-011 | WP-05 | `POST /qms/v1/field-actions`, `POST /qms/v1/field-actions/{id}/scope`, `POST /qms/v1/field-actions/{id}/reportability` | policy lookup (Doc 04) | Doc 36 |
| Reportability | SPEC-QMS-011 | WP-05 | `POST /qms/v1/field-actions`, `POST /qms/v1/field-actions/{id}/scope`, `POST /qms/v1/field-actions/{id}/reportability` | — | Doc 36 |
| Communication Package | SPEC-QMS-011 | WP-05 | `POST /qms/v1/field-actions`, `POST /qms/v1/field-actions/{id}/scope`, `POST /qms/v1/field-actions/{id}/reportability` | — | Doc 36 |
| Execution | SPEC-QMS-011 | WP-05 | `POST /qms/v1/field-actions`, `POST /qms/v1/field-actions/{id}/scope`, `POST /qms/v1/field-actions/{id}/reportability` | — | Doc 36 |
| Returns/Corrections | SPEC-QMS-011 | WP-05 | `POST /qms/v1/field-actions`, `POST /qms/v1/field-actions/{id}/scope`, `POST /qms/v1/field-actions/{id}/reportability` | — | Doc 36 |
| Reconciliation | SPEC-QMS-011 | WP-05 | `POST /qms/v1/field-actions`, `POST /qms/v1/field-actions/{id}/scope`, `POST /qms/v1/field-actions/{id}/reportability` | — | Doc 36 |
| Effectiveness | SPEC-QMS-011 | WP-05 | `POST /qms/v1/field-actions`, `POST /qms/v1/field-actions/{id}/scope`, `POST /qms/v1/field-actions/{id}/reportability` | — | Doc 36 |
| Closure | SPEC-QMS-011 | WP-05 | `POST /qms/v1/field-actions`, `POST /qms/v1/field-actions/{id}/scope`, `POST /qms/v1/field-actions/{id}/reportability` | — | Doc 36 |
| Quality Dashboard | SPEC-QMS-012 | WP-05 | `POST /quality-metrics/v1/definitions`, `POST /quality-metrics/v1/definitions/{id}/release`, `POST /quality-metrics/v1/calculate` | — | Doc 37 |
| Metric Catalogue | SPEC-QMS-012 | WP-05 | `POST /quality-metrics/v1/definitions`, `POST /quality-metrics/v1/definitions/{id}/release`, `POST /quality-metrics/v1/calculate` | — | Doc 37 |
| Deviation/CAPA/OOS/NCR Trends | SPEC-QMS-012 | WP-05 | `POST /quality-metrics/v1/definitions`, `POST /quality-metrics/v1/definitions/{id}/release`, `POST /quality-metrics/v1/calculate` | — | Doc 37 |
| Complaint/Supplier Trends | SPEC-QMS-012 | WP-05 | `POST /quality-metrics/v1/definitions`, `POST /quality-metrics/v1/definitions/{id}/release`, `POST /quality-metrics/v1/calculate` | — | Doc 37 |
| Training/Audit Trends | SPEC-QMS-012 | WP-05 | `POST /quality-metrics/v1/definitions`, `POST /quality-metrics/v1/definitions/{id}/release`, `POST /quality-metrics/v1/calculate` | — | Doc 37 |
| Batch Quality | SPEC-QMS-012 | WP-05 | `POST /quality-metrics/v1/definitions`, `POST /quality-metrics/v1/definitions/{id}/release`, `POST /quality-metrics/v1/calculate` | — | Doc 37 |
| Alert Queue | SPEC-QMS-012 | WP-05 | `POST /quality-metrics/v1/definitions`, `POST /quality-metrics/v1/definitions/{id}/release`, `POST /quality-metrics/v1/calculate` | — | Doc 37 |
| Effectiveness Checks | SPEC-QMS-012 | WP-05 | `POST /quality-metrics/v1/definitions`, `POST /quality-metrics/v1/definitions/{id}/release`, `POST /quality-metrics/v1/calculate` | — | Doc 37 |
| Management Review Package | SPEC-QMS-012 | WP-05 | `POST /quality-metrics/v1/definitions`, `POST /quality-metrics/v1/definitions/{id}/release`, `POST /quality-metrics/v1/calculate` | — | Doc 37 |
| Equipment Catalogue | SPEC-EQP-001 | WP-06 | `POST /equipment/v1/assets`, `POST /equipment/v1/{id}/qualifications`, `POST /equipment/v1/{id}/calibrations` | — | Doc 38 |
| Asset Detail | SPEC-EQP-001 | WP-06 | `POST /equipment/v1/assets`, `POST /equipment/v1/{id}/qualifications`, `POST /equipment/v1/{id}/calibrations` | — | Doc 38 |
| Qualification | SPEC-EQP-001 | WP-06 | `POST /equipment/v1/assets`, `POST /equipment/v1/{id}/qualifications`, `POST /equipment/v1/{id}/calibrations` | — | Doc 38 |
| Calibration Plan/Execution | SPEC-EQP-001 | WP-06 | `POST /equipment/v1/assets`, `POST /equipment/v1/{id}/qualifications`, `POST /equipment/v1/{id}/calibrations` | — | Doc 38 |
| Maintenance Work Orders | SPEC-EQP-001 | WP-06 | `POST /equipment/v1/assets`, `POST /equipment/v1/{id}/qualifications`, `POST /equipment/v1/{id}/calibrations` | — | Doc 38 |
| Use Log | SPEC-EQP-001 | WP-06 | `POST /equipment/v1/assets`, `POST /equipment/v1/{id}/qualifications`, `POST /equipment/v1/{id}/calibrations` | — | Doc 38 |
| Firmware/Configuration | SPEC-EQP-001 | WP-06 | `POST /equipment/v1/assets`, `POST /equipment/v1/{id}/qualifications`, `POST /equipment/v1/{id}/calibrations` | — | Doc 38 |
| Eligibility | SPEC-EQP-001 | WP-06 | `POST /equipment/v1/assets`, `POST /equipment/v1/{id}/qualifications`, `POST /equipment/v1/{id}/calibrations` | — | Doc 38 |
| Due Dashboard | SPEC-EQP-001 | WP-06 | `POST /equipment/v1/assets`, `POST /equipment/v1/{id}/qualifications`, `POST /equipment/v1/{id}/calibrations` | — | Doc 38 |
| History/Export | SPEC-EQP-001 | WP-06 | `POST /equipment/v1/assets`, `POST /equipment/v1/{id}/qualifications`, `POST /equipment/v1/{id}/calibrations` | — | Doc 38 |
| Cleaning Queue | SPEC-EQP-002 | WP-06 | `POST /cleaning/v1/executions`, `POST /cleaning/v1/executions/{id}/steps`, `POST /cleaning/v1/executions/{id}/complete` | — | Doc 39 |
| Cleaning Execution | SPEC-EQP-002 | WP-06 | `POST /cleaning/v1/executions`, `POST /cleaning/v1/executions/{id}/steps`, `POST /cleaning/v1/executions/{id}/complete` | — | Doc 39 |
| Agents/Materials | SPEC-EQP-002 | WP-06 | `POST /cleaning/v1/executions`, `POST /cleaning/v1/executions/{id}/steps`, `POST /cleaning/v1/executions/{id}/complete` | — | Doc 39 |
| Inspection/Sampling | SPEC-EQP-002 | WP-06 | `POST /cleaning/v1/executions`, `POST /cleaning/v1/executions/{id}/steps`, `POST /cleaning/v1/executions/{id}/complete` | — | Doc 39 |
| Clean Hold Status | SPEC-EQP-002 | WP-06 | `POST /cleaning/v1/executions`, `POST /cleaning/v1/executions/{id}/steps`, `POST /cleaning/v1/executions/{id}/complete` | — | Doc 39 |
| Line Clearance | SPEC-EQP-002 | WP-06 | `POST /cleaning/v1/executions`, `POST /cleaning/v1/executions/{id}/steps`, `POST /cleaning/v1/executions/{id}/complete` | — | Doc 39 |
| Changeover | SPEC-EQP-002 | WP-06 | `POST /cleaning/v1/executions`, `POST /cleaning/v1/executions/{id}/steps`, `POST /cleaning/v1/executions/{id}/complete` | — | Doc 39 |
| Cleaning History | SPEC-EQP-002 | WP-06 | `POST /cleaning/v1/executions`, `POST /cleaning/v1/executions/{id}/steps`, `POST /cleaning/v1/executions/{id}/complete` | — | Doc 39 |
| Aseptic Readiness | SPEC-EQP-003 | WP-06 | `POST /aseptic/v1/operations`, `POST /aseptic/v1/operations/{id}/start`, `POST /aseptic/v1/operations/{id}/interventions` | — | Doc 40 |
| Area/Personnel Status | SPEC-EQP-003 | WP-06 | `POST /aseptic/v1/operations`, `POST /aseptic/v1/operations/{id}/start`, `POST /aseptic/v1/operations/{id}/interventions` | — | Doc 40 |
| Sterile Inputs | SPEC-EQP-003 | WP-06 | `POST /aseptic/v1/operations`, `POST /aseptic/v1/operations/{id}/start`, `POST /aseptic/v1/operations/{id}/interventions` | — | Doc 40 |
| Aseptic Setup | SPEC-EQP-003 | WP-06 | `POST /aseptic/v1/operations`, `POST /aseptic/v1/operations/{id}/start`, `POST /aseptic/v1/operations/{id}/interventions` | — | Doc 40 |
| Live Operation | SPEC-EQP-003 | WP-06 | `POST /aseptic/v1/operations`, `POST /aseptic/v1/operations/{id}/start`, `POST /aseptic/v1/operations/{id}/interventions` | — | Doc 40 |
| Interventions | SPEC-EQP-003 | WP-06 | `POST /aseptic/v1/operations`, `POST /aseptic/v1/operations/{id}/start`, `POST /aseptic/v1/operations/{id}/interventions` | — | Doc 40 |
| Hold-Time Timeline | SPEC-EQP-003 | WP-06 | `POST /aseptic/v1/operations`, `POST /aseptic/v1/operations/{id}/start`, `POST /aseptic/v1/operations/{id}/interventions` | — | Doc 40 |
| Environment/Alarms | SPEC-EQP-003 | WP-06 | `POST /aseptic/v1/operations`, `POST /aseptic/v1/operations/{id}/start`, `POST /aseptic/v1/operations/{id}/interventions` | — | Doc 40 |
| Completion | SPEC-EQP-003 | WP-06 | `POST /aseptic/v1/operations`, `POST /aseptic/v1/operations/{id}/start`, `POST /aseptic/v1/operations/{id}/interventions` | — | Doc 40 |
| QA Summary | SPEC-EQP-003 | WP-06 | `POST /aseptic/v1/operations`, `POST /aseptic/v1/operations/{id}/start`, `POST /aseptic/v1/operations/{id}/interventions` | — | Doc 40 |
| EM Program | SPEC-EQP-004 | WP-06 | `POST /em/v1/programs`, `POST /em/v1/tasks`, `POST /em/v1/tasks/{id}/collect` | — | Doc 41 |
| Monitoring Locations | SPEC-EQP-004 | WP-06 | `POST /em/v1/programs`, `POST /em/v1/tasks`, `POST /em/v1/tasks/{id}/collect` | — | Doc 41 |
| Sampling Schedule | SPEC-EQP-004 | WP-06 | `POST /em/v1/programs`, `POST /em/v1/tasks`, `POST /em/v1/tasks/{id}/collect` | — | Doc 41 |
| EM Collection | SPEC-EQP-004 | WP-06 | `POST /em/v1/programs`, `POST /em/v1/tasks`, `POST /em/v1/tasks/{id}/collect` | — | Doc 41 |
| Continuous Monitoring | SPEC-EQP-004 | WP-06 | `POST /em/v1/programs`, `POST /em/v1/tasks`, `POST /em/v1/tasks/{id}/collect` | — | Doc 41 |
| Result Review | SPEC-EQP-004 | WP-06 | `POST /em/v1/programs`, `POST /em/v1/tasks`, `POST /em/v1/tasks/{id}/collect` | — | Doc 41 |
| Excursions | SPEC-EQP-004 | WP-06 | `POST /em/v1/programs`, `POST /em/v1/tasks`, `POST /em/v1/tasks/{id}/collect` | — | Doc 41 |
| Organism Identification | SPEC-EQP-004 | WP-06 | `POST /em/v1/programs`, `POST /em/v1/tasks`, `POST /em/v1/tasks/{id}/collect` | — | Doc 41 |
| Area Readiness | SPEC-EQP-004 | WP-06 | `POST /em/v1/programs`, `POST /em/v1/tasks`, `POST /em/v1/tasks/{id}/collect` | — | Doc 41 |
| Trend Dashboard | SPEC-EQP-004 | WP-06 | `POST /em/v1/programs`, `POST /em/v1/tasks`, `POST /em/v1/tasks/{id}/collect` | — | Doc 41 |
| Batch Correlation | SPEC-EQP-004 | WP-06 | `POST /em/v1/programs`, `POST /em/v1/tasks`, `POST /em/v1/tasks/{id}/collect` | — | Doc 41 |
| Cycle Profiles | SPEC-EQP-005 | WP-06 | `POST /sterilization/v1/cycles`, `POST /sterilization/v1/cycles/{id}/start`, `POST /sterilization/v1/cycles/{id}/data` | — | Doc 42 |
| Load Builder | SPEC-EQP-005 | WP-06 | `POST /sterilization/v1/cycles`, `POST /sterilization/v1/cycles/{id}/start`, `POST /sterilization/v1/cycles/{id}/data` | — | Doc 42 |
| Cycle Execution/Monitor | SPEC-EQP-005 | WP-06 | `POST /sterilization/v1/cycles`, `POST /sterilization/v1/cycles/{id}/start`, `POST /sterilization/v1/cycles/{id}/data` | — | Doc 42 |
| Cycle Review | SPEC-EQP-005 | WP-06 | `POST /sterilization/v1/cycles`, `POST /sterilization/v1/cycles/{id}/start`, `POST /sterilization/v1/cycles/{id}/data` | — | Doc 42 |
| Indicators | SPEC-EQP-005 | WP-06 | `POST /sterilization/v1/cycles`, `POST /sterilization/v1/cycles/{id}/start`, `POST /sterilization/v1/cycles/{id}/data` | — | Doc 42 |
| CIP/SIP | SPEC-EQP-005 | WP-06 | `POST /sterilization/v1/cycles`, `POST /sterilization/v1/cycles/{id}/start`, `POST /sterilization/v1/cycles/{id}/data` | — | Doc 42 |
| Filter Inventory/Installation | SPEC-EQP-005 | WP-06 | `POST /sterilization/v1/cycles`, `POST /sterilization/v1/cycles/{id}/start`, `POST /sterilization/v1/cycles/{id}/data` | — | Doc 42 |
| Integrity Testing | SPEC-EQP-005 | WP-06 | `POST /sterilization/v1/cycles`, `POST /sterilization/v1/cycles/{id}/start`, `POST /sterilization/v1/cycles/{id}/data` | — | Doc 42 |
| Sterile Status | SPEC-EQP-005 | WP-06 | `POST /sterilization/v1/cycles`, `POST /sterilization/v1/cycles/{id}/start`, `POST /sterilization/v1/cycles/{id}/data` | — | Doc 42 |
| Batch/Genealogy Summary | SPEC-EQP-005 | WP-06 | `POST /sterilization/v1/cycles`, `POST /sterilization/v1/cycles/{id}/start`, `POST /sterilization/v1/cycles/{id}/data` | — | Doc 42 |
| <ScannerStatus /> | SPEC-EDGE-004 | WP-06 | see 06_API_CATALOGUE.yaml | — | Doc 46 |
| <ScanInputAction /> | SPEC-EDGE-004 | WP-06 | see 06_API_CATALOGUE.yaml | — | Doc 46 |
| <BalanceStatus /> | SPEC-EDGE-004 | WP-06 | see 06_API_CATALOGUE.yaml | — | Doc 46 |
| <LiveStableWeight /> | SPEC-EDGE-004 | WP-06 | see 06_API_CATALOGUE.yaml | — | Doc 46 |
| <ControlledPrintAction /> | SPEC-EDGE-004 | WP-06 | see 06_API_CATALOGUE.yaml | — | Doc 46 |
| <TesterResultPanel /> | SPEC-EDGE-004 | WP-06 | see 06_API_CATALOGUE.yaml | — | Doc 46 |
| <VisionEvidencePanel /> | SPEC-EDGE-004 | WP-06 | see 06_API_CATALOGUE.yaml | — | Doc 46 |
| ERP Instance Registry | SPEC-ERP-001 | WP-07 | see 06_API_CATALOGUE.yaml | — | Doc 48 |
| Capability/Health | SPEC-ERP-001 | WP-07 | see 06_API_CATALOGUE.yaml | — | Doc 48 |
| Mapping Dashboard | SPEC-ERP-001 | WP-07 | see 06_API_CATALOGUE.yaml | — | Doc 48 |
| Command Queue | SPEC-ERP-001 | WP-07 | see 06_API_CATALOGUE.yaml | — | Doc 48 |
| Failed/Retry Queue | SPEC-ERP-001 | WP-07 | see 06_API_CATALOGUE.yaml | — | Doc 48 |
| Inbound Event Monitor | SPEC-ERP-001 | WP-07 | see 06_API_CATALOGUE.yaml | — | Doc 48 |
| Reconciliation Dashboard | SPEC-ERP-001 | WP-07 | see 06_API_CATALOGUE.yaml | — | Doc 48 |
| External Reference Drilldown | SPEC-ERP-001 | WP-07 | see 06_API_CATALOGUE.yaml | — | Doc 48 |
| Integration Audit | SPEC-ERP-001 | WP-07 | see 06_API_CATALOGUE.yaml | — | Doc 48 |
| Injectable Profile Designer | SPEC-DDCP-001 | WP-08 | see 06_API_CATALOGUE.yaml | policy lookup (Doc 04) | Doc 54 |
| Constituent Requirements | SPEC-DDCP-001 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 54 |
| Batch Readiness | SPEC-DDCP-001 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 54 |
| Filling Setup | SPEC-DDCP-001 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 54 |
| Aseptic Fill Execution | SPEC-DDCP-001 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 54 |
| Fill IPC | SPEC-DDCP-001 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 54 |
| Closure/Assembly | SPEC-DDCP-001 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 54 |
| Inspection | SPEC-DDCP-001 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 54 |
| Device Functional Results | SPEC-DDCP-001 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 54 |
| Reconciliation | SPEC-DDCP-001 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 54 |
| DDCP Review | SPEC-DDCP-001 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 54 |
| Final Release Summary | SPEC-DDCP-001 | WP-08 | see 06_API_CATALOGUE.yaml | policy lookup (Doc 04) | Doc 54 |
| Injector Profile | SPEC-DDCP-002 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 55 |
| Assembly BOM/Route | SPEC-DDCP-002 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 55 |
| Assembly Readiness | SPEC-DDCP-002 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 55 |
| Unit Scan/Binding | SPEC-DDCP-002 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 55 |
| Assembly Execution | SPEC-DDCP-002 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 55 |
| Functional Test | SPEC-DDCP-002 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 55 |
| Reject/Rework | SPEC-DDCP-002 | WP-08 | see 06_API_CATALOGUE.yaml | policy lookup (Doc 04) | Doc 55 |
| Unit Genealogy | SPEC-DDCP-002 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 55 |
| Packaging | SPEC-DDCP-002 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 55 |
| Review/Release | SPEC-DDCP-002 | WP-08 | see 06_API_CATALOGUE.yaml | policy lookup (Doc 04) | Doc 55 |
| Complaint Serial Trace | SPEC-DDCP-002 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 55 |
| Inhalation Profile | SPEC-DDCP-003 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 56 |
| Formulation/Blend Handoff | SPEC-DDCP-003 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 56 |
| Device Components | SPEC-DDCP-003 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 56 |
| Readiness | SPEC-DDCP-003 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 56 |
| Filling/Assembly | SPEC-DDCP-003 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 56 |
| Closure/Leak | SPEC-DDCP-003 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 56 |
| Dose/Performance Tests | SPEC-DDCP-003 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 56 |
| Packaging | SPEC-DDCP-003 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 56 |
| Genealogy | SPEC-DDCP-003 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 56 |
| Review/Release | SPEC-DDCP-003 | WP-08 | see 06_API_CATALOGUE.yaml | policy lookup (Doc 04) | Doc 56 |
| Coated Device Profile | SPEC-DDCP-004 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 57 |
| Constituent Handoff | SPEC-DDCP-004 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 57 |
| Coating Readiness | SPEC-DDCP-004 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 57 |
| Coating Run | SPEC-DDCP-004 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 57 |
| Process Parameter Timeline | SPEC-DDCP-004 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 57 |
| Drug Loading / QC | SPEC-DDCP-004 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 57 |
| Coating Inspection | SPEC-DDCP-004 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 57 |
| Sterilization Link | SPEC-DDCP-004 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 57 |
| Post-Sterilization Test | SPEC-DDCP-004 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 57 |
| Dual Reconciliation | SPEC-DDCP-004 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 57 |
| Genealogy | SPEC-DDCP-004 | WP-08 | see 06_API_CATALOGUE.yaml | — | Doc 57 |
| QA Release | SPEC-DDCP-004 | WP-08 | see 06_API_CATALOGUE.yaml | policy lookup (Doc 04) | Doc 57 |
| Postmarket Intake Queue | SPEC-PM-001 | WP-09 | `POST /postmarket/v1/sources`, `POST /postmarket/v1/safety-cases`, `POST /postmarket/v1/safety-cases/{id}/resolve-product` | — | Doc 58 |
| Safety Case | SPEC-PM-001 | WP-09 | `POST /postmarket/v1/sources`, `POST /postmarket/v1/safety-cases`, `POST /postmarket/v1/safety-cases/{id}/resolve-product` | — | Doc 58 |
| Product/Serial/Genealogy Lookup | SPEC-PM-001 | WP-09 | `POST /postmarket/v1/sources`, `POST /postmarket/v1/safety-cases`, `POST /postmarket/v1/safety-cases/{id}/resolve-product` | — | Doc 58 |
| Clinical/Device Classification | SPEC-PM-001 | WP-09 | `POST /postmarket/v1/sources`, `POST /postmarket/v1/safety-cases`, `POST /postmarket/v1/safety-cases/{id}/resolve-product` | — | Doc 58 |
| Follow-up | SPEC-PM-001 | WP-09 | `POST /postmarket/v1/sources`, `POST /postmarket/v1/safety-cases`, `POST /postmarket/v1/safety-cases/{id}/resolve-product` | — | Doc 58 |
| Duplicate Review | SPEC-PM-001 | WP-09 | `POST /postmarket/v1/sources`, `POST /postmarket/v1/safety-cases`, `POST /postmarket/v1/safety-cases/{id}/resolve-product` | — | Doc 58 |
| Signal Dashboard | SPEC-PM-001 | WP-09 | `POST /postmarket/v1/sources`, `POST /postmarket/v1/safety-cases`, `POST /postmarket/v1/safety-cases/{id}/resolve-product` | policy lookup (Doc 04) | Doc 58 |
| Signal Assessment | SPEC-PM-001 | WP-09 | `POST /postmarket/v1/sources`, `POST /postmarket/v1/safety-cases`, `POST /postmarket/v1/safety-cases/{id}/resolve-product` | policy lookup (Doc 04) | Doc 58 |
| Trend Explorer | SPEC-PM-001 | WP-09 | `POST /postmarket/v1/sources`, `POST /postmarket/v1/safety-cases`, `POST /postmarket/v1/safety-cases/{id}/resolve-product` | — | Doc 58 |
| Action/Handoff | SPEC-PM-001 | WP-09 | `POST /postmarket/v1/sources`, `POST /postmarket/v1/safety-cases`, `POST /postmarket/v1/safety-cases/{id}/resolve-product` | — | Doc 58 |
| Periodic Dataset Preview | SPEC-PM-001 | WP-09 | `POST /postmarket/v1/sources`, `POST /postmarket/v1/safety-cases`, `POST /postmarket/v1/safety-cases/{id}/resolve-product` | — | Doc 58 |
| Audit/Export | SPEC-PM-001 | WP-09 | `POST /postmarket/v1/sources`, `POST /postmarket/v1/safety-cases`, `POST /postmarket/v1/safety-cases/{id}/resolve-product` | — | Doc 58 |
| Reportability Workbench | SPEC-PM-002 | WP-09 | `POST /regulatory/v1/cases/{caseId}/reportability-tracks`, `POST /regulatory/v1/tracks/{id}/deadline:calculate`, `POST /regulatory/v1/tracks/{id}/decisions` | — | Doc 59 |
| Regulatory Clock Panel | SPEC-PM-002 | WP-09 | `POST /regulatory/v1/cases/{caseId}/reportability-tracks`, `POST /regulatory/v1/tracks/{id}/deadline:calculate`, `POST /regulatory/v1/tracks/{id}/decisions` | — | Doc 59 |
| MDR Assessment | SPEC-PM-002 | WP-09 | `POST /regulatory/v1/cases/{caseId}/reportability-tracks`, `POST /regulatory/v1/tracks/{id}/deadline:calculate`, `POST /regulatory/v1/tracks/{id}/decisions` | — | Doc 59 |
| Drug/Biologic Expedited Assessment | SPEC-PM-002 | WP-09 | `POST /regulatory/v1/cases/{caseId}/reportability-tracks`, `POST /regulatory/v1/tracks/{id}/deadline:calculate`, `POST /regulatory/v1/tracks/{id}/decisions` | — | Doc 59 |
| Part 4 Combination Assessment | SPEC-PM-002 | WP-09 | `POST /regulatory/v1/cases/{caseId}/reportability-tracks`, `POST /regulatory/v1/tracks/{id}/deadline:calculate`, `POST /regulatory/v1/tracks/{id}/decisions` | — | Doc 59 |
| Report Builder | SPEC-PM-002 | WP-09 | `POST /regulatory/v1/cases/{caseId}/reportability-tracks`, `POST /regulatory/v1/tracks/{id}/deadline:calculate`, `POST /regulatory/v1/tracks/{id}/decisions` | — | Doc 59 |
| Field Provenance | SPEC-PM-002 | WP-09 | `POST /regulatory/v1/cases/{caseId}/reportability-tracks`, `POST /regulatory/v1/tracks/{id}/deadline:calculate`, `POST /regulatory/v1/tracks/{id}/decisions` | — | Doc 59 |
| Approval | SPEC-PM-002 | WP-09 | `POST /regulatory/v1/cases/{caseId}/reportability-tracks`, `POST /regulatory/v1/tracks/{id}/deadline:calculate`, `POST /regulatory/v1/tracks/{id}/decisions` | — | Doc 59 |
| Submission Queue | SPEC-PM-002 | WP-09 | `POST /regulatory/v1/cases/{caseId}/reportability-tracks`, `POST /regulatory/v1/tracks/{id}/deadline:calculate`, `POST /regulatory/v1/tracks/{id}/decisions` | — | Doc 59 |
| Acknowledgement/Rejection | SPEC-PM-002 | WP-09 | `POST /regulatory/v1/cases/{caseId}/reportability-tracks`, `POST /regulatory/v1/tracks/{id}/deadline:calculate`, `POST /regulatory/v1/tracks/{id}/decisions` | policy lookup (Doc 04) | Doc 59 |
| Follow-up Reports | SPEC-PM-002 | WP-09 | `POST /regulatory/v1/cases/{caseId}/reportability-tracks`, `POST /regulatory/v1/tracks/{id}/deadline:calculate`, `POST /regulatory/v1/tracks/{id}/decisions` | — | Doc 59 |
| Inspection Package | SPEC-PM-002 | WP-09 | `POST /regulatory/v1/cases/{caseId}/reportability-tracks`, `POST /regulatory/v1/tracks/{id}/deadline:calculate`, `POST /regulatory/v1/tracks/{id}/decisions` | — | Doc 59 |
| Applicant/Constituent Relationship | SPEC-PM-003 | WP-09 | `POST /postmarket/v1/applicant-relationships`, `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate`, `POST /postmarket/v1/sharing/{id}/package` | — | Doc 60 |
| Information Sharing Queue | SPEC-PM-003 | WP-09 | `POST /postmarket/v1/applicant-relationships`, `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate`, `POST /postmarket/v1/sharing/{id}/package` | — | Doc 60 |
| Sharing Package | SPEC-PM-003 | WP-09 | `POST /postmarket/v1/applicant-relationships`, `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate`, `POST /postmarket/v1/sharing/{id}/package` | — | Doc 60 |
| Correction/Removal Regulatory Assessment | SPEC-PM-003 | WP-09 | `POST /postmarket/v1/applicant-relationships`, `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate`, `POST /postmarket/v1/sharing/{id}/package` | — | Doc 60 |
| Field Alert Assessment | SPEC-PM-003 | WP-09 | `POST /postmarket/v1/applicant-relationships`, `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate`, `POST /postmarket/v1/sharing/{id}/package` | — | Doc 60 |
| BPDR Queue | SPEC-PM-003 | WP-09 | `POST /postmarket/v1/applicant-relationships`, `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate`, `POST /postmarket/v1/sharing/{id}/package` | — | Doc 60 |
| Periodic Safety Calendar | SPEC-PM-003 | WP-09 | `POST /postmarket/v1/applicant-relationships`, `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate`, `POST /postmarket/v1/sharing/{id}/package` | — | Doc 60 |
| Periodic Report Workspace | SPEC-PM-003 | WP-09 | `POST /postmarket/v1/applicant-relationships`, `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate`, `POST /postmarket/v1/sharing/{id}/package` | — | Doc 60 |
| FDA Requests/Correspondence | SPEC-PM-003 | WP-09 | `POST /postmarket/v1/applicant-relationships`, `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate`, `POST /postmarket/v1/sharing/{id}/package` | — | Doc 60 |
| Unified Regulatory Calendar | SPEC-PM-003 | WP-09 | `POST /postmarket/v1/applicant-relationships`, `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate`, `POST /postmarket/v1/sharing/{id}/package` | — | Doc 60 |
| Retention Basis / Legal Hold | SPEC-PM-003 | WP-09 | `POST /postmarket/v1/applicant-relationships`, `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate`, `POST /postmarket/v1/sharing/{id}/package` | — | Doc 60 |
| Inspection Dashboard | SPEC-PM-003 | WP-09 | `POST /postmarket/v1/applicant-relationships`, `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate`, `POST /postmarket/v1/sharing/{id}/package` | — | Doc 60 |
| Security Architecture | SPEC-SEC-001 | WP-10 | `POST /security/v1/threat-models`, `POST /security/v1/threats`, `POST /security/v1/threats/{id}/controls` | — | Doc 61 |
| Threat Model | SPEC-SEC-001 | WP-10 | `POST /security/v1/threat-models`, `POST /security/v1/threats`, `POST /security/v1/threats/{id}/controls` | — | Doc 61 |
| Assets/Trust Boundaries | SPEC-SEC-001 | WP-10 | `POST /security/v1/threat-models`, `POST /security/v1/threats`, `POST /security/v1/threats/{id}/controls` | — | Doc 61 |
| Threat Register | SPEC-SEC-001 | WP-10 | `POST /security/v1/threat-models`, `POST /security/v1/threats`, `POST /security/v1/threats/{id}/controls` | — | Doc 61 |
| Control Catalogue | SPEC-SEC-001 | WP-10 | `POST /security/v1/threat-models`, `POST /security/v1/threats`, `POST /security/v1/threats/{id}/controls` | — | Doc 61 |
| Residual Risk | SPEC-SEC-001 | WP-10 | `POST /security/v1/threat-models`, `POST /security/v1/threats`, `POST /security/v1/threats/{id}/controls` | — | Doc 61 |
| Exceptions | SPEC-SEC-001 | WP-10 | `POST /security/v1/threat-models`, `POST /security/v1/threats`, `POST /security/v1/threats/{id}/controls` | — | Doc 61 |
| Control/Test Matrix | SPEC-SEC-001 | WP-10 | `POST /security/v1/threat-models`, `POST /security/v1/threats`, `POST /security/v1/threats/{id}/controls` | — | Doc 61 |
| Identity Provider Config | SPEC-SEC-002 | WP-10 | `GET /auth/login`, `GET /auth/callback`, `POST /auth/logout` | — | Doc 62 |
| Active Sessions | SPEC-SEC-002 | WP-10 | `GET /auth/login`, `GET /auth/callback`, `POST /auth/logout` | — | Doc 62 |
| Service Identities | SPEC-SEC-002 | WP-10 | `GET /auth/login`, `GET /auth/callback`, `POST /auth/logout` | — | Doc 62 |
| Federation Mapping | SPEC-SEC-002 | WP-10 | `GET /auth/login`, `GET /auth/callback`, `POST /auth/logout` | — | Doc 62 |
| Authentication Policy | SPEC-SEC-002 | WP-10 | `GET /auth/login`, `GET /auth/callback`, `POST /auth/logout` | — | Doc 62 |
| Session Revocation | SPEC-SEC-002 | WP-10 | `GET /auth/login`, `GET /auth/callback`, `POST /auth/logout` | — | Doc 62 |
| Privileged Access Requests | SPEC-SEC-003 | WP-10 | `POST /security/v1/privileged-access/requests`, `POST /security/v1/privileged-access/requests/{id}/approve`, `POST /security/v1/support-sessions` | — | Doc 63 |
| Active Grants | SPEC-SEC-003 | WP-10 | `POST /security/v1/privileged-access/requests`, `POST /security/v1/privileged-access/requests/{id}/approve`, `POST /security/v1/support-sessions` | — | Doc 63 |
| Support Sessions | SPEC-SEC-003 | WP-10 | `POST /security/v1/privileged-access/requests`, `POST /security/v1/privileged-access/requests/{id}/approve`, `POST /security/v1/support-sessions` | — | Doc 63 |
| Controlled Admin Commands | SPEC-SEC-003 | WP-10 | `POST /security/v1/privileged-access/requests`, `POST /security/v1/privileged-access/requests/{id}/approve`, `POST /security/v1/support-sessions` | — | Doc 63 |
| Break-Glass | SPEC-SEC-003 | WP-10 | `POST /security/v1/privileged-access/requests`, `POST /security/v1/privileged-access/requests/{id}/approve`, `POST /security/v1/support-sessions` | — | Doc 63 |
| Privileged Session Review | SPEC-SEC-003 | WP-10 | `POST /security/v1/privileged-access/requests`, `POST /security/v1/privileged-access/requests/{id}/approve`, `POST /security/v1/support-sessions` | — | Doc 63 |
| Privileged Role Review | SPEC-SEC-003 | WP-10 | `POST /security/v1/privileged-access/requests`, `POST /security/v1/privileged-access/requests/{id}/approve`, `POST /security/v1/support-sessions` | — | Doc 63 |
| API Security Inventory | SPEC-SEC-004 | WP-10 | `POST /security/v1/outbound-destinations`, `POST /security/v1/webhook-profiles`, `GET /security/v1/api-inventory` | — | Doc 64 |
| Rate-Limit Policies | SPEC-SEC-004 | WP-10 | `POST /security/v1/outbound-destinations`, `POST /security/v1/webhook-profiles`, `GET /security/v1/api-inventory` | — | Doc 64 |
| Outbound Destination Registry | SPEC-SEC-004 | WP-10 | `POST /security/v1/outbound-destinations`, `POST /security/v1/webhook-profiles`, `GET /security/v1/api-inventory` | — | Doc 64 |
| Webhook Profiles | SPEC-SEC-004 | WP-10 | `POST /security/v1/outbound-destinations`, `POST /security/v1/webhook-profiles`, `GET /security/v1/api-inventory` | — | Doc 64 |
| File Quarantine | SPEC-SEC-004 | WP-10 | `POST /security/v1/outbound-destinations`, `POST /security/v1/webhook-profiles`, `GET /security/v1/api-inventory` | — | Doc 64 |
| Security Test Coverage | SPEC-SEC-004 | WP-10 | `POST /security/v1/outbound-destinations`, `POST /security/v1/webhook-profiles`, `GET /security/v1/api-inventory` | — | Doc 64 |
| Secret Inventory (metadata only) | SPEC-SEC-005 | WP-10 | `POST /security/v1/secrets/{id}/rotate`, `POST /security/v1/certificates:issue`, `POST /security/v1/certificates/{id}/rotate` | — | Doc 65 |
| Certificate Inventory | SPEC-SEC-005 | WP-10 | `POST /security/v1/secrets/{id}/rotate`, `POST /security/v1/certificates:issue`, `POST /security/v1/certificates/{id}/rotate` | — | Doc 65 |
| Rotation Dashboard | SPEC-SEC-005 | WP-10 | `POST /security/v1/secrets/{id}/rotate`, `POST /security/v1/certificates:issue`, `POST /security/v1/certificates/{id}/rotate` | — | Doc 65 |
| Crypto Profiles | SPEC-SEC-005 | WP-10 | `POST /security/v1/secrets/{id}/rotate`, `POST /security/v1/certificates:issue`, `POST /security/v1/certificates/{id}/rotate` | — | Doc 65 |
| Trust Stores | SPEC-SEC-005 | WP-10 | `POST /security/v1/secrets/{id}/rotate`, `POST /security/v1/certificates:issue`, `POST /security/v1/certificates/{id}/rotate` | — | Doc 65 |
| Key Access Audit | SPEC-SEC-005 | WP-10 | `POST /security/v1/secrets/{id}/rotate`, `POST /security/v1/certificates:issue`, `POST /security/v1/certificates/{id}/rotate` | — | Doc 65 |
| Trust Zone Diagram | SPEC-SEC-006 | WP-10 | `GET /security/v1/network-flows`, `GET /security/v1/deployment-security-profile` | — | Doc 66 |
| Network Flow Catalogue | SPEC-SEC-006 | WP-10 | `GET /security/v1/network-flows`, `GET /security/v1/deployment-security-profile` | — | Doc 66 |
| Segmentation Test Results | SPEC-SEC-006 | WP-10 | `GET /security/v1/network-flows`, `GET /security/v1/deployment-security-profile` | — | Doc 66 |
| Tenant/Site Isolation Test | SPEC-SEC-006 | WP-10 | `GET /security/v1/network-flows`, `GET /security/v1/deployment-security-profile` | — | Doc 66 |
| Deployment Hardening | SPEC-SEC-006 | WP-10 | `GET /security/v1/network-flows`, `GET /security/v1/deployment-security-profile` | — | Doc 66 |
| Security Alerts | SPEC-SEC-007 | WP-10 | `POST /security/v1/incidents`, `POST /security/v1/incidents/{id}/containment`, `POST /security/v1/incidents/{id}/evidence` | — | Doc 67 |
| Incident Queue | SPEC-SEC-007 | WP-10 | `POST /security/v1/incidents`, `POST /security/v1/incidents/{id}/containment`, `POST /security/v1/incidents/{id}/evidence` | — | Doc 67 |
| Incident Timeline | SPEC-SEC-007 | WP-10 | `POST /security/v1/incidents`, `POST /security/v1/incidents/{id}/containment`, `POST /security/v1/incidents/{id}/evidence` | — | Doc 67 |
| Containment Actions | SPEC-SEC-007 | WP-10 | `POST /security/v1/incidents`, `POST /security/v1/incidents/{id}/containment`, `POST /security/v1/incidents/{id}/evidence` | — | Doc 67 |
| Forensic Evidence | SPEC-SEC-007 | WP-10 | `POST /security/v1/incidents`, `POST /security/v1/incidents/{id}/containment`, `POST /security/v1/incidents/{id}/evidence` | — | Doc 67 |
| GxP Impact | SPEC-SEC-007 | WP-10 | `POST /security/v1/incidents`, `POST /security/v1/incidents/{id}/containment`, `POST /security/v1/incidents/{id}/evidence` | — | Doc 67 |
| Detection Rules | SPEC-SEC-007 | WP-10 | `POST /security/v1/incidents`, `POST /security/v1/incidents/{id}/containment`, `POST /security/v1/incidents/{id}/evidence` | — | Doc 67 |
| Telemetry Health | SPEC-SEC-007 | WP-10 | `POST /security/v1/incidents`, `POST /security/v1/incidents/{id}/containment`, `POST /security/v1/incidents/{id}/evidence` | — | Doc 67 |
| Metrics | SPEC-SEC-007 | WP-10 | `POST /security/v1/incidents`, `POST /security/v1/incidents/{id}/containment`, `POST /security/v1/incidents/{id}/evidence` | — | Doc 67 |
| Vulnerability Register | SPEC-SEC-008 | WP-10 | `POST /security/v1/vulnerabilities`, `POST /security/v1/vulnerabilities/{id}/assess`, `POST /security/v1/vulnerabilities/{id}/exceptions` | — | Doc 68 |
| Component/SBOM Inventory | SPEC-SEC-008 | WP-10 | `POST /security/v1/vulnerabilities`, `POST /security/v1/vulnerabilities/{id}/assess`, `POST /security/v1/vulnerabilities/{id}/exceptions` | — | Doc 68 |
| Security Release Gate | SPEC-SEC-008 | WP-10 | `POST /security/v1/vulnerabilities`, `POST /security/v1/vulnerabilities/{id}/assess`, `POST /security/v1/vulnerabilities/{id}/exceptions` | policy lookup (Doc 04) | Doc 68 |
| Exceptions | SPEC-SEC-008 | WP-10 | `POST /security/v1/vulnerabilities`, `POST /security/v1/vulnerabilities/{id}/assess`, `POST /security/v1/vulnerabilities/{id}/exceptions` | — | Doc 68 |
| Pen Test Findings | SPEC-SEC-008 | WP-10 | `POST /security/v1/vulnerabilities`, `POST /security/v1/vulnerabilities/{id}/assess`, `POST /security/v1/vulnerabilities/{id}/exceptions` | — | Doc 68 |
| Security Advisories | SPEC-SEC-008 | WP-10 | `POST /security/v1/vulnerabilities`, `POST /security/v1/vulnerabilities/{id}/assess`, `POST /security/v1/vulnerabilities/{id}/exceptions` | — | Doc 68 |
| Supported Releases | SPEC-SEC-008 | WP-10 | `POST /security/v1/vulnerabilities`, `POST /security/v1/vulnerabilities/{id}/assess`, `POST /security/v1/vulnerabilities/{id}/exceptions` | policy lookup (Doc 04) | Doc 68 |
| Data Ownership Matrix | SPEC-DATA-001 | WP-11 | `GET /platform/v1/data-ownership/{entityType}`, `GET /platform/v1/projections/{type}/{id}/freshness`, `POST /platform/v1/projections/{type}:rebuild` | — | Doc 69 |
| Projection Health | SPEC-DATA-001 | WP-11 | `GET /platform/v1/data-ownership/{entityType}`, `GET /platform/v1/projections/{type}/{id}/freshness`, `POST /platform/v1/projections/{type}:rebuild` | — | Doc 69 |
| Data Dictionary | SPEC-DATA-001 | WP-11 | `GET /platform/v1/data-ownership/{entityType}`, `GET /platform/v1/projections/{type}/{id}/freshness`, `POST /platform/v1/projections/{type}:rebuild` | — | Doc 69 |
| Migration Provenance | SPEC-DATA-001 | WP-11 | `GET /platform/v1/data-ownership/{entityType}`, `GET /platform/v1/projections/{type}/{id}/freshness`, `POST /platform/v1/projections/{type}:rebuild` | — | Doc 69 |
| Cross-Store Consistency | SPEC-DATA-001 | WP-11 | `GET /platform/v1/data-ownership/{entityType}`, `GET /platform/v1/projections/{type}/{id}/freshness`, `POST /platform/v1/projections/{type}:rebuild` | — | Doc 69 |
| Database/Schema Inventory | SPEC-DATA-002 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 70 |
| Partition Health | SPEC-DATA-002 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 70 |
| Connection/Lock Dashboard | SPEC-DATA-002 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 70 |
| Slow Query Dashboard | SPEC-DATA-002 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 70 |
| Integrity Checks | SPEC-DATA-002 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 70 |
| Migration History | SPEC-DATA-002 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 70 |
| Projection Sync Status | SPEC-DATA-003 | WP-11 | `GET /api/method/... projection status/admin operations` | — | Doc 71 |
| Frappe DB Health | SPEC-DATA-003 | WP-11 | `GET /api/method/... projection status/admin operations` | — | Doc 71 |
| Projection Rebuild | SPEC-DATA-003 | WP-11 | `GET /api/method/... projection status/admin operations` | — | Doc 71 |
| Stale Projection Indicators | SPEC-DATA-003 | WP-11 | `GET /api/method/... projection status/admin operations` | — | Doc 71 |
| Frappe Migration History | SPEC-DATA-003 | WP-11 | `GET /api/method/... projection status/admin operations` | — | Doc 71 |
| Evidence Browser (authorized metadata) | SPEC-DATA-004 | WP-11 | `POST /evidence/v1/uploads`, `POST /evidence/v1/{id}:finalize`, `GET /evidence/v1/{id}/download` | policy lookup (Doc 04) | Doc 72 |
| Upload/Quarantine | SPEC-DATA-004 | WP-11 | `POST /evidence/v1/uploads`, `POST /evidence/v1/{id}:finalize`, `GET /evidence/v1/{id}/download` | — | Doc 72 |
| Integrity Status | SPEC-DATA-004 | WP-11 | `POST /evidence/v1/uploads`, `POST /evidence/v1/{id}:finalize`, `GET /evidence/v1/{id}/download` | — | Doc 72 |
| Retention/Hold | SPEC-DATA-004 | WP-11 | `POST /evidence/v1/uploads`, `POST /evidence/v1/{id}:finalize`, `GET /evidence/v1/{id}/download` | — | Doc 72 |
| Archive Tier | SPEC-DATA-004 | WP-11 | `POST /evidence/v1/uploads`, `POST /evidence/v1/{id}:finalize`, `GET /evidence/v1/{id}/download` | — | Doc 72 |
| Evidence Manifest | SPEC-DATA-004 | WP-11 | `POST /evidence/v1/uploads`, `POST /evidence/v1/{id}:finalize`, `GET /evidence/v1/{id}/download` | — | Doc 72 |
| Provider Migration | SPEC-DATA-004 | WP-11 | `POST /evidence/v1/uploads`, `POST /evidence/v1/{id}:finalize`, `GET /evidence/v1/{id}/download` | — | Doc 72 |
| Event Stream Health | SPEC-DATA-005 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 73 |
| Outbox Lag | SPEC-DATA-005 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 73 |
| Consumer Lag | SPEC-DATA-005 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 73 |
| Dead Letters | SPEC-DATA-005 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 73 |
| Schema Registry | SPEC-DATA-005 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 73 |
| Replay Jobs | SPEC-DATA-005 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 73 |
| Workflow Operations | SPEC-DATA-006 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 74 |
| Stuck/Failed Activities | SPEC-DATA-006 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 74 |
| Timer/Deadline Operations | SPEC-DATA-006 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 74 |
| Worker Version/Task Queues | SPEC-DATA-006 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 74 |
| Replay Compatibility | SPEC-DATA-006 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 74 |
| Search | SPEC-DATA-007 | WP-11 | `GET /search/v1/...`, `POST /search/v1/indexes/{type}:rebuild`, `POST /reports/v1/exports` | — | Doc 75 |
| Index Health | SPEC-DATA-007 | WP-11 | `GET /search/v1/...`, `POST /search/v1/indexes/{type}:rebuild`, `POST /reports/v1/exports` | — | Doc 75 |
| Cache Health | SPEC-DATA-007 | WP-11 | `GET /search/v1/...`, `POST /search/v1/indexes/{type}:rebuild`, `POST /reports/v1/exports` | — | Doc 75 |
| Read Model Freshness | SPEC-DATA-007 | WP-11 | `GET /search/v1/...`, `POST /search/v1/indexes/{type}:rebuild`, `POST /reports/v1/exports` | — | Doc 75 |
| Async Exports | SPEC-DATA-007 | WP-11 | `GET /search/v1/...`, `POST /search/v1/indexes/{type}:rebuild`, `POST /reports/v1/exports` | — | Doc 75 |
| Analytics Cutoff | SPEC-DATA-007 | WP-11 | `GET /search/v1/...`, `POST /search/v1/indexes/{type}:rebuild`, `POST /reports/v1/exports` | — | Doc 75 |
| Backup Health | SPEC-DATA-008 | WP-11 | `POST /platform/v1/recovery-objectives`, `GET /platform/v1/backups/health`, `POST /platform/v1/restore-tests` | — | Doc 76 |
| WAL/PITR Coverage | SPEC-DATA-008 | WP-11 | `POST /platform/v1/recovery-objectives`, `GET /platform/v1/backups/health`, `POST /platform/v1/restore-tests` | — | Doc 76 |
| Restore Tests | SPEC-DATA-008 | WP-11 | `POST /platform/v1/recovery-objectives`, `GET /platform/v1/backups/health`, `POST /platform/v1/restore-tests` | — | Doc 76 |
| DR Objectives | SPEC-DATA-008 | WP-11 | `POST /platform/v1/recovery-objectives`, `GET /platform/v1/backups/health`, `POST /platform/v1/restore-tests` | — | Doc 76 |
| Failover/Incident | SPEC-DATA-008 | WP-11 | `POST /platform/v1/recovery-objectives`, `GET /platform/v1/backups/health`, `POST /platform/v1/restore-tests` | — | Doc 76 |
| Recovery Validation | SPEC-DATA-008 | WP-11 | `POST /platform/v1/recovery-objectives`, `GET /platform/v1/backups/health`, `POST /platform/v1/restore-tests` | — | Doc 76 |
| Deployment Inventory | SPEC-DATA-009 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 77 |
| Version Matrix | SPEC-DATA-009 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 77 |
| Install Preflight | SPEC-DATA-009 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 77 |
| Upgrade Dashboard | SPEC-DATA-009 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 77 |
| Drift | SPEC-DATA-009 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 77 |
| Capacity/Autoscaling | SPEC-DATA-009 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 77 |
| Post-Install Qualification | SPEC-DATA-009 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 77 |
| Executive Reliability | SPEC-DATA-010 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 78 |
| GxP API | SPEC-DATA-010 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 78 |
| Database | SPEC-DATA-010 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 78 |
| NATS/Outbox | SPEC-DATA-010 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 78 |
| Temporal | SPEC-DATA-010 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 78 |
| Edge Fleet | SPEC-DATA-010 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 78 |
| Object Evidence | SPEC-DATA-010 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 78 |
| Projection Freshness | SPEC-DATA-010 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 78 |
| Capacity Forecast | SPEC-DATA-010 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 78 |
| Backup/DR | SPEC-DATA-010 | WP-11 | see 06_API_CATALOGUE.yaml | — | Doc 78 |
| Validation Master Plan | SPEC-VAL-001 | WP-12 | `POST /validation/v1/master-plans`, `POST /validation/v1/master-plans/{id}/release`, `GET /validation/v1/releases/{id}/gate` | — | Doc 79 |
| Responsibility Matrix | SPEC-VAL-001 | WP-12 | `POST /validation/v1/master-plans`, `POST /validation/v1/master-plans/{id}/release`, `GET /validation/v1/releases/{id}/gate` | — | Doc 79 |
| Deliverables | SPEC-VAL-001 | WP-12 | `POST /validation/v1/master-plans`, `POST /validation/v1/master-plans/{id}/release`, `GET /validation/v1/releases/{id}/gate` | — | Doc 79 |
| Release Gate | SPEC-VAL-001 | WP-12 | `POST /validation/v1/master-plans`, `POST /validation/v1/master-plans/{id}/release`, `GET /validation/v1/releases/{id}/gate` | policy lookup (Doc 04) | Doc 79 |
| Validation Package | SPEC-VAL-001 | WP-12 | `POST /validation/v1/master-plans`, `POST /validation/v1/master-plans/{id}/release`, `GET /validation/v1/releases/{id}/gate` | — | Doc 79 |
| Intended Use | SPEC-VAL-002 | WP-12 | `POST /validation/v1/intended-use`, `POST /validation/v1/function-risks`, `POST /validation/v1/function-risks/{id}/approve` | — | Doc 80 |
| Function Risk Matrix | SPEC-VAL-002 | WP-12 | `POST /validation/v1/intended-use`, `POST /validation/v1/function-risks`, `POST /validation/v1/function-risks/{id}/approve` | — | Doc 80 |
| Failure Modes | SPEC-VAL-002 | WP-12 | `POST /validation/v1/intended-use`, `POST /validation/v1/function-risks`, `POST /validation/v1/function-risks/{id}/approve` | — | Doc 80 |
| Assurance Level | SPEC-VAL-002 | WP-12 | `POST /validation/v1/intended-use`, `POST /validation/v1/function-risks`, `POST /validation/v1/function-risks/{id}/approve` | — | Doc 80 |
| Risk Change Impact | SPEC-VAL-002 | WP-12 | `POST /validation/v1/intended-use`, `POST /validation/v1/function-risks`, `POST /validation/v1/function-risks/{id}/approve` | — | Doc 80 |
| Requirement Registry | SPEC-VAL-003 | WP-12 | `POST /validation/v1/requirements:ingest`, `POST /validation/v1/trace-links`, `POST /validation/v1/baselines` | — | Doc 81 |
| Design Trace | SPEC-VAL-003 | WP-12 | `POST /validation/v1/requirements:ingest`, `POST /validation/v1/trace-links`, `POST /validation/v1/baselines` | policy lookup (Doc 04) | Doc 81 |
| Test Trace | SPEC-VAL-003 | WP-12 | `POST /validation/v1/requirements:ingest`, `POST /validation/v1/trace-links`, `POST /validation/v1/baselines` | — | Doc 81 |
| Gaps | SPEC-VAL-003 | WP-12 | `POST /validation/v1/requirements:ingest`, `POST /validation/v1/trace-links`, `POST /validation/v1/baselines` | — | Doc 81 |
| Baseline Freeze | SPEC-VAL-003 | WP-12 | `POST /validation/v1/requirements:ingest`, `POST /validation/v1/trace-links`, `POST /validation/v1/baselines` | — | Doc 81 |
| Traceability Export | SPEC-VAL-003 | WP-12 | `POST /validation/v1/requirements:ingest`, `POST /validation/v1/trace-links`, `POST /validation/v1/baselines` | — | Doc 81 |
| Test Library | SPEC-VAL-004 | WP-12 | `POST /validation/v1/tests`, `POST /validation/v1/tests/{id}/approve`, `POST /validation/v1/executions` | — | Doc 82 |
| Execution Workspace | SPEC-VAL-004 | WP-12 | `POST /validation/v1/tests`, `POST /validation/v1/tests/{id}/approve`, `POST /validation/v1/executions` | — | Doc 82 |
| Automated Evidence | SPEC-VAL-004 | WP-12 | `POST /validation/v1/tests`, `POST /validation/v1/tests/{id}/approve`, `POST /validation/v1/executions` | — | Doc 82 |
| Exploratory Charters | SPEC-VAL-004 | WP-12 | `POST /validation/v1/tests`, `POST /validation/v1/tests/{id}/approve`, `POST /validation/v1/executions` | — | Doc 82 |
| Failed/Blocked Tests | SPEC-VAL-004 | WP-12 | `POST /validation/v1/tests`, `POST /validation/v1/tests/{id}/approve`, `POST /validation/v1/executions` | — | Doc 82 |
| Evidence Review | SPEC-VAL-004 | WP-12 | `POST /validation/v1/tests`, `POST /validation/v1/tests/{id}/approve`, `POST /validation/v1/executions` | — | Doc 82 |
| IQ Protocol | SPEC-VAL-005 | WP-12 | `POST /validation/v1/iq/protocols`, `POST /validation/v1/iq/executions`, `POST /validation/v1/iq/executions/{id}/complete` | — | Doc 83 |
| Installed Inventory | SPEC-VAL-005 | WP-12 | `POST /validation/v1/iq/protocols`, `POST /validation/v1/iq/executions`, `POST /validation/v1/iq/executions/{id}/complete` | — | Doc 83 |
| Prerequisite Checks | SPEC-VAL-005 | WP-12 | `POST /validation/v1/iq/protocols`, `POST /validation/v1/iq/executions`, `POST /validation/v1/iq/executions/{id}/complete` | — | Doc 83 |
| IQ Deviations | SPEC-VAL-005 | WP-12 | `POST /validation/v1/iq/protocols`, `POST /validation/v1/iq/executions`, `POST /validation/v1/iq/executions/{id}/complete` | — | Doc 83 |
| IQ Approval | SPEC-VAL-005 | WP-12 | `POST /validation/v1/iq/protocols`, `POST /validation/v1/iq/executions`, `POST /validation/v1/iq/executions/{id}/complete` | — | Doc 83 |
| OQ Scope | SPEC-VAL-006 | WP-12 | `POST /validation/v1/oq:suites`, `POST /validation/v1/oq/executions`, `GET /validation/v1/oq/{id}/coverage` | — | Doc 84 |
| OQ Execution | SPEC-VAL-006 | WP-12 | `POST /validation/v1/oq:suites`, `POST /validation/v1/oq/executions`, `GET /validation/v1/oq/{id}/coverage` | — | Doc 84 |
| Critical Coverage | SPEC-VAL-006 | WP-12 | `POST /validation/v1/oq:suites`, `POST /validation/v1/oq/executions`, `GET /validation/v1/oq/{id}/coverage` | — | Doc 84 |
| Failures | SPEC-VAL-006 | WP-12 | `POST /validation/v1/oq:suites`, `POST /validation/v1/oq/executions`, `GET /validation/v1/oq/{id}/coverage` | — | Doc 84 |
| OQ Approval | SPEC-VAL-006 | WP-12 | `POST /validation/v1/oq:suites`, `POST /validation/v1/oq/executions`, `GET /validation/v1/oq/{id}/coverage` | — | Doc 84 |
| PQ Scenarios | SPEC-VAL-007 | WP-14 | `POST /validation/v1/pq/scenarios`, `POST /validation/v1/pq/scenarios/{id}/participants`, `POST /validation/v1/pq/executions` | — | Doc 85 |
| Participants/Training | SPEC-VAL-007 | WP-14 | `POST /validation/v1/pq/scenarios`, `POST /validation/v1/pq/scenarios/{id}/participants`, `POST /validation/v1/pq/executions` | — | Doc 85 |
| PQ Execution | SPEC-VAL-007 | WP-14 | `POST /validation/v1/pq/scenarios`, `POST /validation/v1/pq/scenarios/{id}/participants`, `POST /validation/v1/pq/executions` | — | Doc 85 |
| Usability Observations | SPEC-VAL-007 | WP-14 | `POST /validation/v1/pq/scenarios`, `POST /validation/v1/pq/scenarios/{id}/participants`, `POST /validation/v1/pq/executions` | — | Doc 85 |
| Site Acceptance | SPEC-VAL-007 | WP-14 | `POST /validation/v1/pq/scenarios`, `POST /validation/v1/pq/scenarios/{id}/participants`, `POST /validation/v1/pq/executions` | — | Doc 85 |
| Infrastructure Baseline | SPEC-VAL-008 | WP-12 | `POST /validation/v1/infrastructure/profiles`, `POST /validation/v1/infrastructure/fingerprints`, `POST /validation/v1/infrastructure/tests` | — | Doc 86 |
| Environment Fingerprint | SPEC-VAL-008 | WP-12 | `POST /validation/v1/infrastructure/profiles`, `POST /validation/v1/infrastructure/fingerprints`, `POST /validation/v1/infrastructure/tests` | — | Doc 86 |
| Control Tests | SPEC-VAL-008 | WP-12 | `POST /validation/v1/infrastructure/profiles`, `POST /validation/v1/infrastructure/fingerprints`, `POST /validation/v1/infrastructure/tests` | — | Doc 86 |
| Supplier Evidence | SPEC-VAL-008 | WP-12 | `POST /validation/v1/infrastructure/profiles`, `POST /validation/v1/infrastructure/fingerprints`, `POST /validation/v1/infrastructure/tests` | — | Doc 86 |
| Drift/Requalification | SPEC-VAL-008 | WP-12 | `POST /validation/v1/infrastructure/profiles`, `POST /validation/v1/infrastructure/fingerprints`, `POST /validation/v1/infrastructure/tests` | — | Doc 86 |
| Migration Plan | SPEC-VAL-009 | WP-14 | `POST /validation/v1/migrations/plans`, `POST /validation/v1/migrations/runs`, `POST /validation/v1/migrations/{id}/reconcile` | — | Doc 87 |
| Source Profile | SPEC-VAL-009 | WP-14 | `POST /validation/v1/migrations/plans`, `POST /validation/v1/migrations/runs`, `POST /validation/v1/migrations/{id}/reconcile` | — | Doc 87 |
| Dry Runs | SPEC-VAL-009 | WP-14 | `POST /validation/v1/migrations/plans`, `POST /validation/v1/migrations/runs`, `POST /validation/v1/migrations/{id}/reconcile` | — | Doc 87 |
| Reconciliation | SPEC-VAL-009 | WP-14 | `POST /validation/v1/migrations/plans`, `POST /validation/v1/migrations/runs`, `POST /validation/v1/migrations/{id}/reconcile` | — | Doc 87 |
| Cutover | SPEC-VAL-009 | WP-14 | `POST /validation/v1/migrations/plans`, `POST /validation/v1/migrations/runs`, `POST /validation/v1/migrations/{id}/reconcile` | — | Doc 87 |
| Legacy Trace | SPEC-VAL-009 | WP-14 | `POST /validation/v1/migrations/plans`, `POST /validation/v1/migrations/runs`, `POST /validation/v1/migrations/{id}/reconcile` | — | Doc 87 |
| Part 11 Scope | SPEC-VAL-010 | WP-12 | `POST /validation/v1/part11/assessments`, `GET /validation/v1/part11/{id}/test-suite`, `POST /validation/v1/part11/{id}/approve` | — | Doc 88 |
| Control Matrix | SPEC-VAL-010 | WP-12 | `POST /validation/v1/part11/assessments`, `GET /validation/v1/part11/{id}/test-suite`, `POST /validation/v1/part11/{id}/approve` | — | Doc 88 |
| Record Copy Test | SPEC-VAL-010 | WP-12 | `POST /validation/v1/part11/assessments`, `GET /validation/v1/part11/{id}/test-suite`, `POST /validation/v1/part11/{id}/approve` | — | Doc 88 |
| Signature Validation | SPEC-VAL-010 | WP-12 | `POST /validation/v1/part11/assessments`, `GET /validation/v1/part11/{id}/test-suite`, `POST /validation/v1/part11/{id}/approve` | policy lookup (Doc 04) | Doc 88 |
| Customer Responsibility | SPEC-VAL-010 | WP-12 | `POST /validation/v1/part11/assessments`, `GET /validation/v1/part11/{id}/test-suite`, `POST /validation/v1/part11/{id}/approve` | — | Doc 88 |
| Part 11 Package | SPEC-VAL-010 | WP-12 | `POST /validation/v1/part11/assessments`, `GET /validation/v1/part11/{id}/test-suite`, `POST /validation/v1/part11/{id}/approve` | — | Doc 88 |
| Data Integrity Matrix | SPEC-VAL-011 | WP-12 | `POST /validation/v1/data-integrity/suites`, `POST /validation/v1/data-integrity/tamper-tests`, `POST /validation/v1/data-integrity/{id}/approve` | — | Doc 89 |
| Audit Tamper | SPEC-VAL-011 | WP-12 | `POST /validation/v1/data-integrity/suites`, `POST /validation/v1/data-integrity/tamper-tests`, `POST /validation/v1/data-integrity/{id}/approve` | — | Doc 89 |
| Vault Canonicalization | SPEC-VAL-011 | WP-12 | `POST /validation/v1/data-integrity/suites`, `POST /validation/v1/data-integrity/tamper-tests`, `POST /validation/v1/data-integrity/{id}/approve` | — | Doc 89 |
| Corrections | SPEC-VAL-011 | WP-12 | `POST /validation/v1/data-integrity/suites`, `POST /validation/v1/data-integrity/tamper-tests`, `POST /validation/v1/data-integrity/{id}/approve` | — | Doc 89 |
| Archive Retrieval | SPEC-VAL-011 | WP-12 | `POST /validation/v1/data-integrity/suites`, `POST /validation/v1/data-integrity/tamper-tests`, `POST /validation/v1/data-integrity/{id}/approve` | — | Doc 89 |
| Qualification | SPEC-VAL-011 | WP-12 | `POST /validation/v1/data-integrity/suites`, `POST /validation/v1/data-integrity/tamper-tests`, `POST /validation/v1/data-integrity/{id}/approve` | — | Doc 89 |
| Interface Inventory | SPEC-VAL-012 | WP-12 | `POST /validation/v1/interfaces/profiles`, `POST /validation/v1/interfaces/tests`, `POST /validation/v1/interfaces/edge-outage-tests` | — | Doc 90 |
| Contract Tests | SPEC-VAL-012 | WP-12 | `POST /validation/v1/interfaces/profiles`, `POST /validation/v1/interfaces/tests`, `POST /validation/v1/interfaces/edge-outage-tests` | — | Doc 90 |
| Edge Offline | SPEC-VAL-012 | WP-12 | `POST /validation/v1/interfaces/profiles`, `POST /validation/v1/interfaces/tests`, `POST /validation/v1/interfaces/edge-outage-tests` | — | Doc 90 |
| Device Tests | SPEC-VAL-012 | WP-12 | `POST /validation/v1/interfaces/profiles`, `POST /validation/v1/interfaces/tests`, `POST /validation/v1/interfaces/edge-outage-tests` | — | Doc 90 |
| Reconciliation | SPEC-VAL-012 | WP-12 | `POST /validation/v1/interfaces/profiles`, `POST /validation/v1/interfaces/tests`, `POST /validation/v1/interfaces/edge-outage-tests` | — | Doc 90 |
| Qualification | SPEC-VAL-012 | WP-12 | `POST /validation/v1/interfaces/profiles`, `POST /validation/v1/interfaces/tests`, `POST /validation/v1/interfaces/edge-outage-tests` | — | Doc 90 |
| DR Scenarios | SPEC-VAL-013 | WP-12 | `POST /validation/v1/dr/scenarios`, `POST /validation/v1/dr/executions`, `POST /validation/v1/dr/{id}/measure` | — | Doc 91 |
| Restore Timeline | SPEC-VAL-013 | WP-12 | `POST /validation/v1/dr/scenarios`, `POST /validation/v1/dr/executions`, `POST /validation/v1/dr/{id}/measure` | — | Doc 91 |
| RPO/RTO | SPEC-VAL-013 | WP-12 | `POST /validation/v1/dr/scenarios`, `POST /validation/v1/dr/executions`, `POST /validation/v1/dr/{id}/measure` | — | Doc 91 |
| Integrity/Smoke | SPEC-VAL-013 | WP-12 | `POST /validation/v1/dr/scenarios`, `POST /validation/v1/dr/executions`, `POST /validation/v1/dr/{id}/measure` | — | Doc 91 |
| DR Qualification | SPEC-VAL-013 | WP-12 | `POST /validation/v1/dr/scenarios`, `POST /validation/v1/dr/executions`, `POST /validation/v1/dr/{id}/measure` | — | Doc 91 |
| Security Qualification | SPEC-VAL-014 | WP-12 | `POST /validation/v1/security/suites`, `POST /validation/v1/security/tests`, `POST /validation/v1/security/findings` | — | Doc 92 |
| Pen Findings | SPEC-VAL-014 | WP-12 | `POST /validation/v1/security/suites`, `POST /validation/v1/security/tests`, `POST /validation/v1/security/findings` | — | Doc 92 |
| Control Coverage | SPEC-VAL-014 | WP-12 | `POST /validation/v1/security/suites`, `POST /validation/v1/security/tests`, `POST /validation/v1/security/findings` | — | Doc 92 |
| Exceptions | SPEC-VAL-014 | WP-12 | `POST /validation/v1/security/suites`, `POST /validation/v1/security/tests`, `POST /validation/v1/security/findings` | — | Doc 92 |
| Security Gate | SPEC-VAL-014 | WP-12 | `POST /validation/v1/security/suites`, `POST /validation/v1/security/tests`, `POST /validation/v1/security/findings` | — | Doc 92 |
| Performance Scenarios | SPEC-VAL-015 | WP-12 | `POST /validation/v1/performance/scenarios`, `POST /validation/v1/performance/runs`, `POST /validation/v1/performance/{id}/evaluate` | — | Doc 93 |
| Load Results | SPEC-VAL-015 | WP-12 | `POST /validation/v1/performance/scenarios`, `POST /validation/v1/performance/runs`, `POST /validation/v1/performance/{id}/evaluate` | — | Doc 93 |
| SLO Acceptance | SPEC-VAL-015 | WP-12 | `POST /validation/v1/performance/scenarios`, `POST /validation/v1/performance/runs`, `POST /validation/v1/performance/{id}/evaluate` | — | Doc 93 |
| Bottlenecks | SPEC-VAL-015 | WP-12 | `POST /validation/v1/performance/scenarios`, `POST /validation/v1/performance/runs`, `POST /validation/v1/performance/{id}/evaluate` | — | Doc 93 |
| Sizing | SPEC-VAL-015 | WP-12 | `POST /validation/v1/performance/scenarios`, `POST /validation/v1/performance/runs`, `POST /validation/v1/performance/{id}/evaluate` | — | Doc 93 |
| Regression | SPEC-VAL-015 | WP-12 | `POST /validation/v1/performance/scenarios`, `POST /validation/v1/performance/runs`, `POST /validation/v1/performance/{id}/evaluate` | — | Doc 93 |
| Validation Exceptions | SPEC-VAL-016 | WP-12 | `POST /validation/v1/exceptions`, `POST /validation/v1/exceptions/{id}/triage`, `POST /validation/v1/exceptions/{id}/retest-plan` | — | Doc 94 |
| Triage | SPEC-VAL-016 | WP-12 | `POST /validation/v1/exceptions`, `POST /validation/v1/exceptions/{id}/triage`, `POST /validation/v1/exceptions/{id}/retest-plan` | — | Doc 94 |
| Defect Links | SPEC-VAL-016 | WP-12 | `POST /validation/v1/exceptions`, `POST /validation/v1/exceptions/{id}/triage`, `POST /validation/v1/exceptions/{id}/retest-plan` | — | Doc 94 |
| Retest Scope | SPEC-VAL-016 | WP-12 | `POST /validation/v1/exceptions`, `POST /validation/v1/exceptions/{id}/triage`, `POST /validation/v1/exceptions/{id}/retest-plan` | — | Doc 94 |
| Risk Acceptance | SPEC-VAL-016 | WP-12 | `POST /validation/v1/exceptions`, `POST /validation/v1/exceptions/{id}/triage`, `POST /validation/v1/exceptions/{id}/retest-plan` | — | Doc 94 |
| Release Blockers | SPEC-VAL-016 | WP-12 | `POST /validation/v1/exceptions`, `POST /validation/v1/exceptions/{id}/triage`, `POST /validation/v1/exceptions/{id}/retest-plan` | policy lookup (Doc 04) | Doc 94 |
| Trend | SPEC-VAL-016 | WP-12 | `POST /validation/v1/exceptions`, `POST /validation/v1/exceptions/{id}/triage`, `POST /validation/v1/exceptions/{id}/retest-plan` | — | Doc 94 |
| Validation Summary | SPEC-VAL-017 | WP-14 | `POST /validation/v1/summary-reports`, `GET /validation/v1/releases/{id}/go-live-readiness`, `POST /validation/v1/summary-reports/{id}/approve` | — | Doc 95 |
| Go-Live Checklist | SPEC-VAL-017 | WP-14 | `POST /validation/v1/summary-reports`, `GET /validation/v1/releases/{id}/go-live-readiness`, `POST /validation/v1/summary-reports/{id}/approve` | — | Doc 95 |
| Known Limitations | SPEC-VAL-017 | WP-14 | `POST /validation/v1/summary-reports`, `GET /validation/v1/releases/{id}/go-live-readiness`, `POST /validation/v1/summary-reports/{id}/approve` | — | Doc 95 |
| Release Authorization | SPEC-VAL-017 | WP-14 | `POST /validation/v1/summary-reports`, `GET /validation/v1/releases/{id}/go-live-readiness`, `POST /validation/v1/summary-reports/{id}/approve` | policy lookup (Doc 04) | Doc 95 |
| Post-Go-Live | SPEC-VAL-017 | WP-14 | `POST /validation/v1/summary-reports`, `GET /validation/v1/releases/{id}/go-live-readiness`, `POST /validation/v1/summary-reports/{id}/approve` | — | Doc 95 |
| Validated Baseline | SPEC-VAL-018 | WP-12 | `POST /validation/v1/change-impacts`, `POST /validation/v1/revalidation-plans`, `POST /validation/v1/revalidations` | — | Doc 96 |
| Change Impact | SPEC-VAL-018 | WP-12 | `POST /validation/v1/change-impacts`, `POST /validation/v1/revalidation-plans`, `POST /validation/v1/revalidations` | — | Doc 96 |
| Revalidation Plans | SPEC-VAL-018 | WP-12 | `POST /validation/v1/change-impacts`, `POST /validation/v1/revalidation-plans`, `POST /validation/v1/revalidations` | — | Doc 96 |
| Periodic Review | SPEC-VAL-018 | WP-12 | `POST /validation/v1/change-impacts`, `POST /validation/v1/revalidation-plans`, `POST /validation/v1/revalidations` | — | Doc 96 |
| Drift/Issues | SPEC-VAL-018 | WP-12 | `POST /validation/v1/change-impacts`, `POST /validation/v1/revalidation-plans`, `POST /validation/v1/revalidations` | — | Doc 96 |
| Validated-State Decision | SPEC-VAL-018 | WP-12 | `POST /validation/v1/change-impacts`, `POST /validation/v1/revalidation-plans`, `POST /validation/v1/revalidations` | — | Doc 96 |
| Decommission | SPEC-VAL-018 | WP-12 | `POST /validation/v1/change-impacts`, `POST /validation/v1/revalidation-plans`, `POST /validation/v1/revalidations` | — | Doc 96 |
