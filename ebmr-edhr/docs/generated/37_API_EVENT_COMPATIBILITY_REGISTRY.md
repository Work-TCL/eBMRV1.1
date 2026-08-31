# 37 — API / Event Compatibility Registry

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Contract inventory with owner, version, consumers and compatibility policy (Document 101/113).

---

## Compatibility policy
- Additive optional field → minor, no version bump.
- Required field, type, semantic or enum-removal change → new `schema_version`.
- Two versions supported concurrently for at least one release.
- Every change updates this registry and runs consumer contract tests.


## API operations

| Operation | Owner module | WP | Version | Idempotency | expected_version | Consumers | Compatibility state |
|---|---|---|---|---|---|---|---|
| `POST /gxp/v1/commands/{commandType}` | SPEC-GXP-001 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /gxp/v1/commands/{commandId}/receipt` | SPEC-GXP-001 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /gxp/v1/records/{type}/{id}/mutation-history` | SPEC-GXP-001 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /gxp/v1/commands/{command_type}` | SPEC-GXP-001 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /signature/v1/challenges` | SPEC-GXP-002 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /signature/v1/challenges/{id}/verify` | SPEC-GXP-002 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /signature/v1/signatures/{id}/consume` | SPEC-GXP-002 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /audit/v1/records/{type}/{id}` | SPEC-GXP-003 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /audit/v1/batches/{id}` | SPEC-GXP-003 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /audit/v1/users/{subjectId}` | SPEC-GXP-003 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /audit/v1/search?...` | SPEC-GXP-003 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /audit/v1/exports` | SPEC-GXP-003 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /vault/v1/masters/{type}/{businessId}/release` | SPEC-GXP-004 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /vault/v1/objects/{objectId}` | SPEC-GXP-004 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /vault/v1/objects/{objectId}/integrity` | SPEC-GXP-004 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /vault/v1/objects/{objectId}/corrections` | SPEC-GXP-004 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /vault/v1/corrections/{id}/complete` | SPEC-GXP-004 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /vault/v1/business/{type}/{businessId}/versions` | SPEC-GXP-004 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /policy/v1/decisions` | SPEC-IAM-001 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /iam/v1/subjects/{id}/effective-authority` | SPEC-IAM-001 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /iam/v1/subjects/{id}/qualifications` | SPEC-IAM-001 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /iam/v1/temporary-authorizations` | SPEC-IAM-001 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /iam/v1/break-glass` | SPEC-IAM-001 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /iam/v1/access-reviews` | SPEC-IAM-001 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /iam/v1/access-reviews/{id}/report` | SPEC-IAM-001 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /rules/v1/drafts` | SPEC-GXP-006 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /rules/v1/{ruleId}/validate` | SPEC-GXP-006 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /rules/v1/{ruleId}/simulate` | SPEC-GXP-006 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /rules/v1/{ruleId}/release` | SPEC-GXP-006 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /rules/v1/{ruleId}/versions` | SPEC-GXP-006 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /rules/v1/evaluate` | SPEC-GXP-006 | WP-01 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /rules/v1/uom/drafts` | SPEC-GXP-006 | WP-01 | v1 | required | required | Frappe UI, integrations | additive (CR-003) |
| `POST /rules/v1/uom/{uomId}/release` | SPEC-GXP-006 | WP-01 | v1 | required | required | Frappe UI, integrations | additive (CR-003) |
| `GET /rules/v1/uom/{code}/versions` | SPEC-GXP-006 | WP-01 | v1 | n/a | n/a | Frappe UI, integrations | additive (CR-003) |
| `POST /rules/v1/uom-conversions/drafts` | SPEC-GXP-006 | WP-01 | v1 | required | required | Frappe UI, integrations | additive (CR-003) |
| `POST /rules/v1/uom-conversions/{conversionId}/release` | SPEC-GXP-006 | WP-01 | v1 | required | required | Frappe UI, integrations | additive (CR-003) |
| `POST /products/v1/drafts` | SPEC-EBMR-000 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `PUT /products/v1/drafts/{id}` | SPEC-EBMR-000 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /products/v1/drafts/{id}/submit` | SPEC-EBMR-000 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /products/v1/drafts/{id}/release` | SPEC-EBMR-000 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /products/v1/{id}/suspend` | SPEC-EBMR-000 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /products/v1/{id}/reinstate` | SPEC-EBMR-000 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /products/v1/{businessId}/versions` | SPEC-EBMR-000 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /products/v1/{id}` | SPEC-EBMR-000 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /products/v1/{id}/validate-completeness` | SPEC-EBMR-000 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /products/v1/{id}/compatibility` | SPEC-EBMR-000 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /products/v1/{id}/issue-eligibility?site=...` | SPEC-EBMR-000 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /recipes/v1/drafts` | SPEC-EBMR-001 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `PUT /recipes/v1/drafts/{id}` | SPEC-EBMR-001 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /recipes/v1/drafts/{id}/validate` | SPEC-EBMR-001 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /recipes/v1/drafts/{id}/simulate` | SPEC-EBMR-001 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /recipes/v1/drafts/{id}/submit` | SPEC-EBMR-001 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /recipes/v1/drafts/{id}/release` | SPEC-EBMR-001 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /recipes/v1/{familyId}/versions` | SPEC-EBMR-001 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /recipes/v1/versions/{id}` | SPEC-EBMR-001 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /recipes/v1/versions/{id}/compare/{otherId}` | SPEC-EBMR-001 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /recipes/v1/versions/{id}/issue-eligibility?site=...&date=...` | SPEC-EBMR-001 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /batches/v1` | SPEC-EBMR-002 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /batches/{id}/issue` | SPEC-EBMR-002 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /batches/{id}/start` | SPEC-EBMR-002 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /batches/{id}/hold` | SPEC-EBMR-002 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /batches/{id}/resume` | SPEC-EBMR-002 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /batches/{id}/steps/{stepId}/start` | SPEC-EBMR-002 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /batches/{id}/steps/{stepId}/results` | SPEC-EBMR-002 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /batches/{id}/steps/{stepId}/complete` | SPEC-EBMR-002 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /batches/{id}/steps/{stepId}/verify` | SPEC-EBMR-002 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /batches/{id}/steps/{stepId}/correct` | SPEC-EBMR-002 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /batches/{id}/production-complete` | SPEC-EBMR-002 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /batches/{id}/abort` | SPEC-EBMR-002 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /batches/{id}` | SPEC-EBMR-002 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /batches/{id}/execution-view` | SPEC-EBMR-002 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /batches/{id}/blockers` | SPEC-EBMR-002 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /devices/v1/lots` | SPEC-EBMR-003 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /devices/v1/units/bulk-create` | SPEC-EBMR-003 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /devices/v1/units/{id}/components` | SPEC-EBMR-003 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /devices/v1/units/{id}/tests` | SPEC-EBMR-003 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /devices/v1/units/{id}/inspection` | SPEC-EBMR-003 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /devices/v1/units/{id}/hold` | SPEC-EBMR-003 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /devices/v1/units/{id}/rework` | SPEC-EBMR-003 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /devices/v1/units/{id}/accept` | SPEC-EBMR-003 | WP-02 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /devices/v1/units/by-serial/{serial}` | SPEC-EBMR-003 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /devices/v1/units/{id}/history` | SPEC-EBMR-003 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /devices/v1/lots/{id}/release-readiness` | SPEC-EBMR-003 | WP-02 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /genealogy/v1/nodes/lookup?...` | SPEC-EBMR-004 | WP-03 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /genealogy/v1/nodes/{id}/ancestors` | SPEC-EBMR-004 | WP-03 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /genealogy/v1/nodes/{id}/descendants` | SPEC-EBMR-004 | WP-03 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /genealogy/v1/serial/{serial}/full-trace` | SPEC-EBMR-004 | WP-03 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /genealogy/v1/material-lot/{lot}/affected-products` | SPEC-EBMR-004 | WP-03 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /genealogy/v1/impact-assessments` | SPEC-EBMR-004 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /genealogy/v1/impact-assessments/{id}` | SPEC-EBMR-004 | WP-03 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /genealogy/v1/exports` | SPEC-EBMR-004 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qa-review/v1/batches/{batchId}/packages` | SPEC-EBMR-005 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /qa-review/v1/packages/{id}` | SPEC-EBMR-005 | WP-03 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /qa-review/v1/packages/{id}/exceptions` | SPEC-EBMR-005 | WP-03 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /qa-review/v1/packages/{id}/comments` | SPEC-EBMR-005 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qa-review/v1/items/{id}/request-action` | SPEC-EBMR-005 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qa-review/v1/items/{id}/disposition` | SPEC-EBMR-005 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qa-review/v1/packages/{id}/complete` | SPEC-EBMR-005 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qa-review/v1/packages/{id}/reindex` | SPEC-EBMR-005 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /qa-review/v1/dashboard` | SPEC-EBMR-005 | WP-03 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /release/v1/scopes/{type}/{id}/evaluate` | SPEC-EBMR-006 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /release/v1/scopes/{id}/eligibility` | SPEC-EBMR-006 | WP-03 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /release/v1/scopes/{id}/release` | SPEC-EBMR-006 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /release/v1/scopes/{id}/hold` | SPEC-EBMR-006 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /release/v1/scopes/{id}/reject` | SPEC-EBMR-006 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /release/v1/scopes/{id}/rework` | SPEC-EBMR-006 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /release/v1/scopes/{id}/reprocess` | SPEC-EBMR-006 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /release/v1/scopes/{id}/destroy` | SPEC-EBMR-006 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /release/v1/scopes/{id}/package` | SPEC-EBMR-006 | WP-03 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /packaging/v1/runs` | SPEC-EBMR-007 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /packaging/v1/runs/{id}/line-clearance` | SPEC-EBMR-007 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /packaging/v1/runs/{id}/labels/issue` | SPEC-EBMR-007 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /packaging/v1/print-jobs` | SPEC-EBMR-007 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /packaging/v1/labels/{id}/reprint` | SPEC-EBMR-007 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /packaging/v1/runs/{id}/label-application` | SPEC-EBMR-007 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /packaging/v1/runs/{id}/inspection` | SPEC-EBMR-007 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /packaging/v1/runs/{id}/reconcile-labels` | SPEC-EBMR-007 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /packaging/v1/runs/{id}/reconcile-packaging` | SPEC-EBMR-007 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /packaging/v1/runs/{id}/complete` | SPEC-EBMR-007 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /manufacturing-calculations/v1/yield/evaluate` | SPEC-EBMR-008 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /manufacturing-calculations/v1/potency/evaluate` | SPEC-EBMR-008 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /reconciliation/v1/material/evaluate` | SPEC-EBMR-008 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /reconciliation/v1/packaging/evaluate` | SPEC-EBMR-008 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /reconciliation/v1/labels/evaluate` | SPEC-EBMR-008 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /reconciliation/v1/components/evaluate` | SPEC-EBMR-008 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /reconciliation/v1/{id}/verify` | SPEC-EBMR-008 | WP-03 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /reconciliation/v1/batches/{batchId}/summary` | SPEC-EBMR-008 | WP-03 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /suppliers/v1` | SPEC-MAT-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /suppliers/{id}/qualifications` | SPEC-MAT-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /supplier-qualifications/{id}/approve` | SPEC-MAT-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /supplier-material-approvals` | SPEC-MAT-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /supplier-material-approvals/{id}/suspend` | SPEC-MAT-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /materials/{specId}/eligible-suppliers?site=...` | SPEC-MAT-001 | WP-04 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /procurement/v1/requisitions` | SPEC-MAT-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /procurement/v1/purchase-orders` | SPEC-MAT-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /procurement/v1/purchase-orders/{id}/revise` | SPEC-MAT-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /procurement/v1/purchase-orders/{po}/receipt-expectation` | SPEC-MAT-001 | WP-04 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /materials/v1/receipts` | SPEC-MAT-002A | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /materials/v1/receipts/{id}/examine` | SPEC-MAT-002A | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /materials/v1/lots/{id}/sampling-orders` | SPEC-MAT-002A | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /sampling-orders/{id}/collect` | SPEC-MAT-002A | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /materials/v1/lots/{id}/release` | SPEC-MAT-002A | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /materials/v1/lots/{id}/reject` | SPEC-MAT-002A | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /materials/v1/lots/{id}/retest` | SPEC-MAT-002A | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /materials/v1/lots/{id}/quality-status` | SPEC-MAT-002A | WP-04 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /materials/v1/lots/{id}/release-readiness` | SPEC-MAT-002A | WP-04 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /inventory/v1/availability` | SPEC-MAT-002B | WP-04 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /inventory/v1/reservations` | SPEC-MAT-002B | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /inventory/v1/reservations/{id}/release` | SPEC-MAT-002B | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /inventory/v1/transfers` | SPEC-MAT-002B | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /inventory/v1/containers/{id}/split` | SPEC-MAT-002B | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /inventory/v1/containers/merge` | SPEC-MAT-002B | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /inventory/v1/cycle-counts` | SPEC-MAT-002B | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /inventory/v1/lots/{id}/ledger` | SPEC-MAT-002B | WP-04 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /inventory/v1/reconciliation/erp` | SPEC-MAT-002B | WP-04 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /dispensing/v1/orders` | SPEC-MAT-002C | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /dispensing/v1/orders/{id}/select-source` | SPEC-MAT-002C | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /dispensing/v1/orders/{id}/start` | SPEC-MAT-002C | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /dispensing/v1/orders/{id}/readings` | SPEC-MAT-002C | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /dispensing/v1/orders/{id}/manual-reading` | SPEC-MAT-002C | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /dispensing/v1/orders/{id}/verify` | SPEC-MAT-002C | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /dispensing/v1/orders/{id}/complete` | SPEC-MAT-002C | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /dispensing/v1/orders/{id}/cancel` | SPEC-MAT-002C | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /dispensing/v1/queue` | SPEC-MAT-002C | WP-04 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /materials/v1/consumptions` | SPEC-MAT-002D | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /materials/v1/returns` | SPEC-MAT-002D | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /inventory/v1/adjustments` | SPEC-MAT-002D | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /inventory/v1/adjustments/{id}/approve` | SPEC-MAT-002D | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /materials/v1/destructions` | SPEC-MAT-002D | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /materials/v1/destructions/{id}/execute` | SPEC-MAT-002D | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /reconciliation/v1/batches/{batchId}/materials/evaluate` | SPEC-MAT-002D | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /reconciliation/v1/batches/{batchId}/materials` | SPEC-MAT-002D | WP-04 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /qc/v1/specifications/drafts` | SPEC-QC-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qc/v1/specifications/{id}/release` | SPEC-QC-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qc/v1/samples` | SPEC-QC-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qc/v1/samples/{id}/receive` | SPEC-QC-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qc/v1/test-orders` | SPEC-QC-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qc/v1/test-orders/{id}/start` | SPEC-QC-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qc/v1/test-orders/{id}/raw-data` | SPEC-QC-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qc/v1/test-orders/{id}/results` | SPEC-QC-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qc/v1/test-orders/{id}/complete` | SPEC-QC-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qc/v1/test-orders/{id}/review` | SPEC-QC-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qc/v1/results/{id}/correct` | SPEC-QC-001 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /qc/v1/samples/{id}/record` | SPEC-QC-001 | WP-04 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /qc/v1/release-readiness?...` | SPEC-QC-001 | WP-04 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /integrations/lims/{instance}/samples` | SPEC-QC-002 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /integrations/lims/{instance}/samples/{id}/cancel` | SPEC-QC-002 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /integrations/lims/{instance}/reconcile` | SPEC-QC-002 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /integrations/lims/{instance}/health` | SPEC-QC-002 | WP-04 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /integrations/lims/{instance}/events/results` | SPEC-QC-002 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /integrations/lims/{instance}/events/status` | SPEC-QC-002 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /quality/oos/v1/from-result/{resultId}` | SPEC-QC-003 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /quality/oos/v1/{id}` | SPEC-QC-003 | WP-04 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /quality/oos/v1/{id}/lab-investigation` | SPEC-QC-003 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /quality/oos/v1/{id}/classify-lab-cause` | SPEC-QC-003 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /quality/oos/v1/{id}/extended-investigation` | SPEC-QC-003 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /quality/oos/v1/{id}/retest-plans` | SPEC-QC-003 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /quality/oos/v1/{id}/resample-plans` | SPEC-QC-003 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /quality/oos/v1/{id}/impact` | SPEC-QC-003 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /quality/oos/v1/{id}/disposition` | SPEC-QC-003 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /quality/oos/v1/{id}/close` | SPEC-QC-003 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /quality/oot/v1/evaluate` | SPEC-QC-003 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /quality/oot/v1/{id}/close` | SPEC-QC-003 | WP-04 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/deviations` | SPEC-QMS-001 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/deviations/{id}/triage` | SPEC-QMS-001 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/deviations/{id}/contain` | SPEC-QMS-001 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/deviations/{id}/investigation` | SPEC-QMS-001 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/deviations/{id}/impact` | SPEC-QMS-001 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/deviations/{id}/disposition` | SPEC-QMS-001 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/deviations/{id}/extend` | SPEC-QMS-001 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/deviations/{id}/close` | SPEC-QMS-001 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/deviations/{id}/reopen` | SPEC-QMS-001 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/capas` | SPEC-QMS-002 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/capas/{id}/plan` | SPEC-QMS-002 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/capas/{id}/actions` | SPEC-QMS-002 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/actions/{id}/complete` | SPEC-QMS-002 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/capas/{id}/effectiveness` | SPEC-QMS-002 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/capas/{id}/extend` | SPEC-QMS-002 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/capas/{id}/close` | SPEC-QMS-002 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/capas/{id}/reopen` | SPEC-QMS-002 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/nonconformances` | SPEC-QMS-003 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/nonconformances/{id}/segregate` | SPEC-QMS-003 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/nonconformances/{id}/evaluate` | SPEC-QMS-003 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/nonconformances/{id}/disposition` | SPEC-QMS-003 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/nonconformances/{id}/verify` | SPEC-QMS-003 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/nonconformances/{id}/close` | SPEC-QMS-003 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/changes` | SPEC-QMS-004 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/changes/{id}/impact` | SPEC-QMS-004 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/changes/{id}/approve` | SPEC-QMS-004 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/changes/{id}/tasks` | SPEC-QMS-004 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/changes/{id}/implement` | SPEC-QMS-004 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/changes/{id}/verify` | SPEC-QMS-004 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/changes/{id}/make-effective` | SPEC-QMS-004 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/changes/{id}/close` | SPEC-QMS-004 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /documents/v1/drafts` | SPEC-QMS-005 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /documents/v1/drafts/{id}/submit` | SPEC-QMS-005 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /documents/v1/drafts/{id}/release` | SPEC-QMS-005 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /documents/v1/versions/{id}/make-effective` | SPEC-QMS-005 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /documents/v1/versions/{id}/obsolete` | SPEC-QMS-005 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /documents/v1/versions/{id}/controlled-copies` | SPEC-QMS-005 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /documents/v1/{code}/versions` | SPEC-QMS-005 | WP-05 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /training/v1/requirements` | SPEC-QMS-006 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /training/v1/assignments` | SPEC-QMS-006 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /training/v1/assignments/{id}/complete` | SPEC-QMS-006 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /training/v1/assignments/{id}/assess` | SPEC-QMS-006 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /training/v1/qualifications` | SPEC-QMS-006 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /training/v1/waivers` | SPEC-QMS-006 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /training/v1/subjects/{id}/status` | SPEC-QMS-006 | WP-05 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /training/v1/matrix` | SPEC-QMS-006 | WP-05 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /qms/v1/supplier-cases` | SPEC-QMS-007 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/supplier-cases/{id}/scar` | SPEC-QMS-007 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/scars/{id}/response` | SPEC-QMS-007 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/scars/{id}/review` | SPEC-QMS-007 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/scars/{id}/effectiveness` | SPEC-QMS-007 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/scars/{id}/close` | SPEC-QMS-007 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/risks` | SPEC-QMS-008 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/risks/{id}/assessments` | SPEC-QMS-008 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/risks/{id}/controls` | SPEC-QMS-008 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/risks/{id}/accept` | SPEC-QMS-008 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/risks/{id}/review` | SPEC-QMS-008 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /qms/v1/risks/dashboard` | SPEC-QMS-008 | WP-05 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /qms/v1/audits` | SPEC-QMS-009 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/audits/{id}/start` | SPEC-QMS-009 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/audits/{id}/findings` | SPEC-QMS-009 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/findings/{id}/response` | SPEC-QMS-009 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/findings/{id}/verify` | SPEC-QMS-009 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/audits/{id}/close` | SPEC-QMS-009 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/complaints` | SPEC-QMS-010 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/complaints/{id}/triage` | SPEC-QMS-010 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/complaints/{id}/investigation-decision` | SPEC-QMS-010 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/complaints/{id}/investigation` | SPEC-QMS-010 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/complaints/{id}/reportability` | SPEC-QMS-010 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/complaints/{id}/response` | SPEC-QMS-010 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/complaints/{id}/close` | SPEC-QMS-010 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/field-actions` | SPEC-QMS-011 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/field-actions/{id}/scope` | SPEC-QMS-011 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/field-actions/{id}/reportability` | SPEC-QMS-011 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/field-actions/{id}/approve` | SPEC-QMS-011 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/field-actions/{id}/communications` | SPEC-QMS-011 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/field-actions/{id}/reconcile` | SPEC-QMS-011 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/field-actions/{id}/effectiveness` | SPEC-QMS-011 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /qms/v1/field-actions/{id}/close` | SPEC-QMS-011 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /quality-metrics/v1/definitions` | SPEC-QMS-012 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /quality-metrics/v1/definitions/{id}/release` | SPEC-QMS-012 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /quality-metrics/v1/calculate` | SPEC-QMS-012 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /quality-metrics/v1/dashboard` | SPEC-QMS-012 | WP-05 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /quality-metrics/v1/management-review-packages` | SPEC-QMS-012 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /effectiveness/v1/checks` | SPEC-QMS-012 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /effectiveness/v1/checks/{id}/evaluate` | SPEC-QMS-012 | WP-05 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /equipment/v1/assets` | SPEC-EQP-001 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /equipment/v1/{id}/qualifications` | SPEC-EQP-001 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /equipment/v1/{id}/calibrations` | SPEC-EQP-001 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /equipment/v1/{id}/maintenance` | SPEC-EQP-001 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /equipment/v1/{id}/hold` | SPEC-EQP-001 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /equipment/v1/{id}/return-to-service` | SPEC-EQP-001 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /equipment/v1/{id}/eligibility` | SPEC-EQP-001 | WP-06 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /equipment/v1/{id}/history` | SPEC-EQP-001 | WP-06 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /equipment/v1/dashboard` | SPEC-EQP-001 | WP-06 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /cleaning/v1/executions` | SPEC-EQP-002 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /cleaning/v1/executions/{id}/steps` | SPEC-EQP-002 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /cleaning/v1/executions/{id}/complete` | SPEC-EQP-002 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /cleaning/v1/executions/{id}/verify` | SPEC-EQP-002 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /line-clearance/v1` | SPEC-EQP-002 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /line-clearance/v1/{id}/complete` | SPEC-EQP-002 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /cleaning/v1/equipment/{id}/status` | SPEC-EQP-002 | WP-06 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /aseptic/v1/operations` | SPEC-EQP-003 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /aseptic/v1/operations/{id}/start` | SPEC-EQP-003 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /aseptic/v1/operations/{id}/interventions` | SPEC-EQP-003 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /aseptic/v1/operations/{id}/events` | SPEC-EQP-003 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /aseptic/v1/operations/{id}/complete` | SPEC-EQP-003 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /aseptic/v1/operations/{id}/readiness` | SPEC-EQP-003 | WP-06 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /aseptic/v1/operations/{id}/review-summary` | SPEC-EQP-003 | WP-06 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /em/v1/programs` | SPEC-EQP-004 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /em/v1/tasks` | SPEC-EQP-004 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /em/v1/tasks/{id}/collect` | SPEC-EQP-004 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /em/v1/results` | SPEC-EQP-004 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /em/v1/results/{id}/review` | SPEC-EQP-004 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /em/v1/excursions/{id}/impact` | SPEC-EQP-004 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /em/v1/areas/{id}/readiness` | SPEC-EQP-004 | WP-06 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /em/v1/trends` | SPEC-EQP-004 | WP-06 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /sterilization/v1/cycles` | SPEC-EQP-005 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /sterilization/v1/cycles/{id}/start` | SPEC-EQP-005 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /sterilization/v1/cycles/{id}/data` | SPEC-EQP-005 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /sterilization/v1/cycles/{id}/review` | SPEC-EQP-005 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /cip-sip/v1/cycles` | SPEC-EQP-005 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /filtration/v1/filters/install` | SPEC-EQP-005 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /filtration/v1/filters/{id}/integrity-tests` | SPEC-EQP-005 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /filtration/v1/uses/{id}/complete` | SPEC-EQP-005 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /sterilization/v1/items/{id}/status` | SPEC-EQP-005 | WP-06 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /edge/v1/enrollments` | SPEC-EDGE-001 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /edge/v1/gateways/{gatewayId}/configuration` | SPEC-EDGE-001 | WP-06 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /edge/v1/gateways/{gatewayId}/observations:batch` | SPEC-EDGE-001 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /edge/v1/gateways/{gatewayId}/health` | SPEC-EDGE-001 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /edge/v1/gateways/{gatewayId}/certificate-rotation` | SPEC-EDGE-001 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /edge/v1/gateways/{gatewayId}/security-events` | SPEC-EDGE-001 | WP-06 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/sources` | SPEC-PM-001 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/safety-cases` | SPEC-PM-001 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/safety-cases/{id}/resolve-product` | SPEC-PM-001 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/safety-cases/{id}/classifications` | SPEC-PM-001 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/safety-cases/{id}/followups` | SPEC-PM-001 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/safety-cases/{id}/duplicate-links` | SPEC-PM-001 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/signals` | SPEC-PM-001 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/signals/{id}/assessments` | SPEC-PM-001 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/signals/{id}/escalations` | SPEC-PM-001 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/periodic-datasets:freeze` | SPEC-PM-001 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /postmarket/v1/dashboard` | SPEC-PM-001 | WP-09 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /regulatory/v1/cases/{caseId}/reportability-tracks` | SPEC-PM-002 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /regulatory/v1/tracks/{id}/deadline:calculate` | SPEC-PM-002 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /regulatory/v1/tracks/{id}/decisions` | SPEC-PM-002 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /regulatory/v1/tracks/{id}/reports` | SPEC-PM-002 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /regulatory/v1/reports/{id}/approve` | SPEC-PM-002 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /regulatory/v1/reports/{id}/payloads:generate` | SPEC-PM-002 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /regulatory/v1/reports/{id}/submissions` | SPEC-PM-002 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /regulatory/v1/submissions/{id}/acknowledgements` | SPEC-PM-002 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /regulatory/v1/reports/{id}/followups` | SPEC-PM-002 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /regulatory/v1/cases/{id}/part4-deduplication:evaluate` | SPEC-PM-002 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/applicant-relationships` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/cases/{id}/part4-sharing:evaluate` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/sharing/{id}/package` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/sharing/{id}/record-sent` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/field-actions/{id}/correction-removal-assessment` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/correction-removal/{id}/decision` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/field-alerts` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/field-alerts/{id}/decision` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/bpdr-tracks` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/periodic-cycles:generate` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/periodic-cycles/{id}/dataset:freeze` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/fda-requests` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/obligations/{id}/deadline-overrides` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /postmarket/v1/retention:calculate` | SPEC-PM-003 | WP-09 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/threat-models` | SPEC-SEC-001 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/threats` | SPEC-SEC-001 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/threats/{id}/controls` | SPEC-SEC-001 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/risks/{id}/accept` | SPEC-SEC-001 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/exceptions` | SPEC-SEC-001 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /security/v1/control-matrix` | SPEC-SEC-001 | WP-10 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /auth/login` | SPEC-SEC-002 | WP-10 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /auth/callback` | SPEC-SEC-002 | WP-10 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /auth/logout` | SPEC-SEC-002 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/sessions/{id}/revoke` | SPEC-SEC-002 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/service-identities` | SPEC-SEC-002 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/identity-providers` | SPEC-SEC-002 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/privileged-access/requests` | SPEC-SEC-003 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/privileged-access/requests/{id}/approve` | SPEC-SEC-003 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/support-sessions` | SPEC-SEC-003 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/admin-commands/{code}:execute` | SPEC-SEC-003 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/break-glass` | SPEC-SEC-003 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/privileged-sessions/{id}/close` | SPEC-SEC-003 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/outbound-destinations` | SPEC-SEC-004 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/webhook-profiles` | SPEC-SEC-004 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /security/v1/api-inventory` | SPEC-SEC-004 | WP-10 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /security/v1/secrets/{id}/rotate` | SPEC-SEC-005 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/certificates:issue` | SPEC-SEC-005 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/certificates/{id}/rotate` | SPEC-SEC-005 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/certificates/{id}/revoke` | SPEC-SEC-005 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /security/v1/crypto-health` | SPEC-SEC-005 | WP-10 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /security/v1/network-flows` | SPEC-SEC-006 | WP-10 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /security/v1/deployment-security-profile` | SPEC-SEC-006 | WP-10 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /security/v1/incidents` | SPEC-SEC-007 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/incidents/{id}/containment` | SPEC-SEC-007 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/incidents/{id}/evidence` | SPEC-SEC-007 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/incidents/{id}/gxp-impact` | SPEC-SEC-007 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/incidents/{id}/close` | SPEC-SEC-007 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/vulnerabilities` | SPEC-SEC-008 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/vulnerabilities/{id}/assess` | SPEC-SEC-008 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /security/v1/vulnerabilities/{id}/exceptions` | SPEC-SEC-008 | WP-10 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /security/v1/releases/{id}/security-evidence` | SPEC-SEC-008 | WP-10 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /platform/v1/data-ownership/{entityType}` | SPEC-DATA-001 | WP-11 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /platform/v1/projections/{type}/{id}/freshness` | SPEC-DATA-001 | WP-11 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /platform/v1/projections/{type}:rebuild` | SPEC-DATA-001 | WP-11 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /platform/v1/data-dictionary` | SPEC-DATA-001 | WP-11 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /api/method/... projection status/admin operations` | SPEC-DATA-003 | WP-11 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /evidence/v1/uploads` | SPEC-DATA-004 | WP-11 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /evidence/v1/{id}:finalize` | SPEC-DATA-004 | WP-11 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /evidence/v1/{id}/download` | SPEC-DATA-004 | WP-11 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /evidence/v1/manifests` | SPEC-DATA-004 | WP-11 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /evidence/v1/{id}/legal-holds` | SPEC-DATA-004 | WP-11 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /evidence/v1/integrity-checks` | SPEC-DATA-004 | WP-11 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /search/v1/...` | SPEC-DATA-007 | WP-11 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /search/v1/indexes/{type}:rebuild` | SPEC-DATA-007 | WP-11 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /reports/v1/exports` | SPEC-DATA-007 | WP-11 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /platform/v1/read-models/{name}/status` | SPEC-DATA-007 | WP-11 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /platform/v1/recovery-objectives` | SPEC-DATA-008 | WP-11 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /platform/v1/backups/health` | SPEC-DATA-008 | WP-11 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /platform/v1/restore-tests` | SPEC-DATA-008 | WP-11 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/master-plans` | SPEC-VAL-001 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/master-plans/{id}/release` | SPEC-VAL-001 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /validation/v1/releases/{id}/gate` | SPEC-VAL-001 | WP-12 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /validation/v1/packages/{scope}` | SPEC-VAL-001 | WP-12 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /validation/v1/intended-use` | SPEC-VAL-002 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/function-risks` | SPEC-VAL-002 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/function-risks/{id}/approve` | SPEC-VAL-002 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /validation/v1/functions/{id}/assurance` | SPEC-VAL-002 | WP-12 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /validation/v1/requirements:ingest` | SPEC-VAL-003 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/trace-links` | SPEC-VAL-003 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/baselines` | SPEC-VAL-003 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /validation/v1/traceability` | SPEC-VAL-003 | WP-12 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `GET /validation/v1/traceability/gaps` | SPEC-VAL-003 | WP-12 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /validation/v1/tests` | SPEC-VAL-004 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/tests/{id}/approve` | SPEC-VAL-004 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/executions` | SPEC-VAL-004 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/executions/{id}/complete` | SPEC-VAL-004 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/automated-evidence` | SPEC-VAL-004 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/iq/protocols` | SPEC-VAL-005 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/iq/executions` | SPEC-VAL-005 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/iq/executions/{id}/complete` | SPEC-VAL-005 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/iq/executions/{id}/approve` | SPEC-VAL-005 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/oq:suites` | SPEC-VAL-006 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/oq/executions` | SPEC-VAL-006 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /validation/v1/oq/{id}/coverage` | SPEC-VAL-006 | WP-12 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /validation/v1/oq/{id}/approve` | SPEC-VAL-006 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/pq/scenarios` | SPEC-VAL-007 | WP-14 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/pq/scenarios/{id}/participants` | SPEC-VAL-007 | WP-14 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/pq/executions` | SPEC-VAL-007 | WP-14 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/pq/{id}/approve` | SPEC-VAL-007 | WP-14 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/infrastructure/profiles` | SPEC-VAL-008 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/infrastructure/fingerprints` | SPEC-VAL-008 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/infrastructure/tests` | SPEC-VAL-008 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/infrastructure/{id}/approve` | SPEC-VAL-008 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/migrations/plans` | SPEC-VAL-009 | WP-14 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/migrations/runs` | SPEC-VAL-009 | WP-14 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/migrations/{id}/reconcile` | SPEC-VAL-009 | WP-14 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/migrations/{id}/approve` | SPEC-VAL-009 | WP-14 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/part11/assessments` | SPEC-VAL-010 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /validation/v1/part11/{id}/test-suite` | SPEC-VAL-010 | WP-12 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /validation/v1/part11/{id}/approve` | SPEC-VAL-010 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/data-integrity/suites` | SPEC-VAL-011 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/data-integrity/tamper-tests` | SPEC-VAL-011 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/data-integrity/{id}/approve` | SPEC-VAL-011 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/interfaces/profiles` | SPEC-VAL-012 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/interfaces/tests` | SPEC-VAL-012 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/interfaces/edge-outage-tests` | SPEC-VAL-012 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/interfaces/{id}/approve` | SPEC-VAL-012 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/dr/scenarios` | SPEC-VAL-013 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/dr/executions` | SPEC-VAL-013 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/dr/{id}/measure` | SPEC-VAL-013 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/dr/{id}/approve` | SPEC-VAL-013 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/security/suites` | SPEC-VAL-014 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/security/tests` | SPEC-VAL-014 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/security/findings` | SPEC-VAL-014 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /validation/v1/security/{id}/gate` | SPEC-VAL-014 | WP-12 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /validation/v1/security/{id}/approve` | SPEC-VAL-014 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/performance/scenarios` | SPEC-VAL-015 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/performance/runs` | SPEC-VAL-015 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/performance/{id}/evaluate` | SPEC-VAL-015 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /validation/v1/performance/sizing` | SPEC-VAL-015 | WP-12 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /validation/v1/exceptions` | SPEC-VAL-016 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/exceptions/{id}/triage` | SPEC-VAL-016 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/exceptions/{id}/retest-plan` | SPEC-VAL-016 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/exceptions/{id}/disposition` | SPEC-VAL-016 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /validation/v1/releases/{id}/exception-gate` | SPEC-VAL-016 | WP-12 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /validation/v1/summary-reports` | SPEC-VAL-017 | WP-14 | v1 | required | required | Frappe UI, integrations | initial |
| `GET /validation/v1/releases/{id}/go-live-readiness` | SPEC-VAL-017 | WP-14 | v1 | n/a | n/a | Frappe UI, integrations | initial |
| `POST /validation/v1/summary-reports/{id}/approve` | SPEC-VAL-017 | WP-14 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/releases/{id}/authorize` | SPEC-VAL-017 | WP-14 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/releases/{id}/deployment-check` | SPEC-VAL-017 | WP-14 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/change-impacts` | SPEC-VAL-018 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/revalidation-plans` | SPEC-VAL-018 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/revalidations` | SPEC-VAL-018 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/periodic-reviews` | SPEC-VAL-018 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/periodic-reviews/{id}/decision` | SPEC-VAL-018 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |
| `POST /validation/v1/decommission` | SPEC-VAL-018 | WP-12 | v1 | required | required | Frappe UI, integrations | initial |

## Events

| Event type | Producer | WP | schema_version | Consumers | Ordering | Dedupe | Compatibility state |
|---|---|---|---|---|---|---|---|
| `ProductDraftSubmitted` | SPEC-EBMR-000 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ProductVersionReleased` | SPEC-EBMR-000 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ProductVersionEffective` | SPEC-EBMR-000 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ProductVersionSuspended` | SPEC-EBMR-000 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ProductVersionReinstated` | SPEC-EBMR-000 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ProductVersionSuperseded` | SPEC-EBMR-000 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ConstituentCompatibilityReleased` | SPEC-EBMR-000 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ProductSiteAdmissionChanged` | SPEC-EBMR-000 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RecipeDraftSubmitted` | SPEC-EBMR-001 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RecipeValidationFailed` | SPEC-EBMR-001 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RecipeVersionReleased` | SPEC-EBMR-001 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RecipeVersionEffective` | SPEC-EBMR-001 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RecipeVersionSuspended` | SPEC-EBMR-001 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RecipeVersionSuperseded` | SPEC-EBMR-001 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `BatchCreated` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `BatchIssued` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `BatchStarted` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `BatchHeld` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `BatchResumed` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `StepReady` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `StepStarted` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `StepResultRecorded` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `StepCompleted` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `StepVerified` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `StepExceptionRaised` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `StepCorrected` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `BranchSelected` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ProductionCompleted` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `BatchAborted` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QAReviewRequested` | SPEC-EBMR-002 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviceUnitCreated` | SPEC-EBMR-003 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ComponentAssembled` | SPEC-EBMR-003 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviceTestRecorded` | SPEC-EBMR-003 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviceInspectionRecorded` | SPEC-EBMR-003 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviceNonconformanceRaised` | SPEC-EBMR-003 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviceReworkStarted` | SPEC-EBMR-003 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviceAccepted` | SPEC-EBMR-003 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviceScrapped` | SPEC-EBMR-003 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviceReleased` | SPEC-EBMR-003 | WP-02 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `GenealogyNodeCreated` | SPEC-EBMR-004 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `GenealogyEdgeCreated` | SPEC-EBMR-004 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `GenealogyEdgeCorrected` | SPEC-EBMR-004 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ImpactAssessmentCreated` | SPEC-EBMR-004 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ImpactAssessmentApproved` | SPEC-EBMR-004 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QAReviewPackageCreated` | SPEC-EBMR-005 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QAExceptionIndexed` | SPEC-EBMR-005 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QAReviewStarted` | SPEC-EBMR-005 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QAActionRequested` | SPEC-EBMR-005 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QAReviewReopened` | SPEC-EBMR-005 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QAReviewCompleted` | SPEC-EBMR-005 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ReleaseEvaluationCompleted` | SPEC-EBMR-006 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ReleaseEligibilityChanged` | SPEC-EBMR-006 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ReleaseHoldPlaced` | SPEC-EBMR-006 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ProductReleased` | SPEC-EBMR-006 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ProductRejected` | SPEC-EBMR-006 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ReworkDispositionApproved` | SPEC-EBMR-006 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ReprocessDispositionApproved` | SPEC-EBMR-006 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DestructionDispositionApproved` | SPEC-EBMR-006 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PostReleaseHoldPlaced` | SPEC-EBMR-006 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PackagingRunStarted` | SPEC-EBMR-007 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LineClearanceCompleted` | SPEC-EBMR-007 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LabelIssued` | SPEC-EBMR-007 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LabelPrinted` | SPEC-EBMR-007 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LabelReprinted` | SPEC-EBMR-007 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LabelApplied` | SPEC-EBMR-007 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LabelMismatchDetected` | SPEC-EBMR-007 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LabelReconciliationCompleted` | SPEC-EBMR-007 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PackagingReconciliationCompleted` | SPEC-EBMR-007 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PackageAggregated` | SPEC-EBMR-007 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PackagingCompleted` | SPEC-EBMR-007 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `YieldCalculated` | SPEC-EBMR-008 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `YieldOutOfLimit` | SPEC-EBMR-008 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `YieldVerified` | SPEC-EBMR-008 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialReconciliationCalculated` | SPEC-EBMR-008 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ReconciliationFailed` | SPEC-EBMR-008 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ReconciliationVerified` | SPEC-EBMR-008 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ReconciliationSuperseded` | SPEC-EBMR-008 | WP-03 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SupplierQualificationApproved` | SPEC-MAT-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SupplierMaterialApproved` | SPEC-MAT-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SupplierSuspended` | SPEC-MAT-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SupplierDisqualified` | SPEC-MAT-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PurchaseRequisitionApproved` | SPEC-MAT-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PurchaseOrderIssued` | SPEC-MAT-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PurchaseOrderRegulatedFieldsChanged` | SPEC-MAT-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialReceived` | SPEC-MAT-002A | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialQuarantined` | SPEC-MAT-002A | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SamplingOrdered` | SPEC-MAT-002A | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SampleCollected` | SPEC-MAT-002A | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialQCCompleted` | SPEC-MAT-002A | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialReleased` | SPEC-MAT-002A | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialRejected` | SPEC-MAT-002A | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialRetestRequired` | SPEC-MAT-002A | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ReceiptDiscrepancyRaised` | SPEC-MAT-002A | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InventoryReceived` | SPEC-MAT-002B | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InventoryTransferred` | SPEC-MAT-002B | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InventoryReserved` | SPEC-MAT-002B | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InventoryReservationReleased` | SPEC-MAT-002B | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ContainerSplit` | SPEC-MAT-002B | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ContainerMerged` | SPEC-MAT-002B | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialQualityHoldPlaced` | SPEC-MAT-002B | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InventoryAdjusted` | SPEC-MAT-002B | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InventoryERPDiscrepancyDetected` | SPEC-MAT-002B | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DispensingStarted` | SPEC-MAT-002C | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DispensingSourceSelected` | SPEC-MAT-002C | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `WeighingReadingAccepted` | SPEC-MAT-002C | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `WeighingExceptionRaised` | SPEC-MAT-002C | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DispensingVerified` | SPEC-MAT-002C | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialDispensed` | SPEC-MAT-002C | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DispensingCancelled` | SPEC-MAT-002C | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialConsumed` | SPEC-MAT-002D | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialReturned` | SPEC-MAT-002D | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialSampled` | SPEC-MAT-002D | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialLossRecorded` | SPEC-MAT-002D | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InventoryAdjustmentApproved` | SPEC-MAT-002D | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialDestroyed` | SPEC-MAT-002D | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaterialReconciliationFailed` | SPEC-MAT-002D | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ERPInventoryPostingFailed` | SPEC-MAT-002D | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QCSampleCreated` | SPEC-QC-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QCSampleReceived` | SPEC-QC-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QCTestStarted` | SPEC-QC-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QCResultRecorded` | SPEC-QC-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QCResultOOSDetected` | SPEC-QC-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QCResultOOTDetected` | SPEC-QC-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QCTestAnalystCompleted` | SPEC-QC-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QCTestReviewed` | SPEC-QC-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QCResultCorrected` | SPEC-QC-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QCTestInvalidated` | SPEC-QC-001 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LIMSSampleRequested` | SPEC-QC-002 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LIMSStatusReceived` | SPEC-QC-002 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LIMSResultReceived` | SPEC-QC-002 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LIMSResultAccepted` | SPEC-QC-002 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LIMSResultRejected` | SPEC-QC-002 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LIMSResultRevised` | SPEC-QC-002 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LIMSIntegrationDeadLettered` | SPEC-QC-002 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LIMSReconciliationMismatchDetected` | SPEC-QC-002 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OOSOpened` | SPEC-QC-003 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OOSLabInvestigationStarted` | SPEC-QC-003 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OOSAssignableCauseDetermined` | SPEC-QC-003 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OOSExtendedInvestigationStarted` | SPEC-QC-003 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OOSRetestAuthorized` | SPEC-QC-003 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OOSRetestCompleted` | SPEC-QC-003 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OOSResampleAuthorized` | SPEC-QC-003 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OOSImpactAssessed` | SPEC-QC-003 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OOSDispositionApproved` | SPEC-QC-003 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OOSClosed` | SPEC-QC-003 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OOTDetected` | SPEC-QC-003 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OOTInvestigationStarted` | SPEC-QC-003 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OOTClosed` | SPEC-QC-003 | WP-04 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviationOpened` | SPEC-QMS-001 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviationContained` | SPEC-QMS-001 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviationInvestigationStarted` | SPEC-QMS-001 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviationImpactAssessed` | SPEC-QMS-001 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviationCAPARequired` | SPEC-QMS-001 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviationDispositionApproved` | SPEC-QMS-001 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviationClosed` | SPEC-QMS-001 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeviationReopened` | SPEC-QMS-001 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CAPAOpened` | SPEC-QMS-002 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CAPAPlanApproved` | SPEC-QMS-002 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CAPAActionAssigned` | SPEC-QMS-002 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CAPAActionCompleted` | SPEC-QMS-002 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CAPAEffectivenessStarted` | SPEC-QMS-002 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CAPAEffectivenessFailed` | SPEC-QMS-002 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CAPAClosed` | SPEC-QMS-002 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CAPAReopened` | SPEC-QMS-002 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `NonconformanceOpened` | SPEC-QMS-003 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `NonconformingProductSegregated` | SPEC-QMS-003 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `NCRDispositionApproved` | SPEC-QMS-003 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `NCRReworkStarted` | SPEC-QMS-003 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `NCRReinspectionCompleted` | SPEC-QMS-003 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `NCRClosed` | SPEC-QMS-003 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ChangeRequested` | SPEC-QMS-004 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ChangeImpactAssessed` | SPEC-QMS-004 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ChangeApproved` | SPEC-QMS-004 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ChangeImplementationStarted` | SPEC-QMS-004 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ChangeValidationCompleted` | SPEC-QMS-004 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ChangeMadeEffective` | SPEC-QMS-004 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ChangeClosed` | SPEC-QMS-004 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EmergencyChangeOpened` | SPEC-QMS-004 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DocumentVersionReleased` | SPEC-QMS-005 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DocumentVersionEffective` | SPEC-QMS-005 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DocumentVersionSuperseded` | SPEC-QMS-005 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DocumentObsoleted` | SPEC-QMS-005 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ControlledCopyIssued` | SPEC-QMS-005 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DocumentPeriodicReviewDue` | SPEC-QMS-005 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `TrainingAssigned` | SPEC-QMS-006 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `TrainingCompleted` | SPEC-QMS-006 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `TrainingFailed` | SPEC-QMS-006 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QualificationIssued` | SPEC-QMS-006 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QualificationExpired` | SPEC-QMS-006 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RetrainingRequired` | SPEC-QMS-006 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `TrainingWaiverApproved` | SPEC-QMS-006 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SupplierQualityCaseOpened` | SPEC-QMS-007 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SCARIssued` | SPEC-QMS-007 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SCARResponseReceived` | SPEC-QMS-007 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SupplierSourceSuspended` | SPEC-QMS-007 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SCAREffectivenessPassed` | SPEC-QMS-007 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SCARClosed` | SPEC-QMS-007 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RiskCreated` | SPEC-QMS-008 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RiskAssessmentCompleted` | SPEC-QMS-008 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RiskMitigationRequired` | SPEC-QMS-008 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RiskAccepted` | SPEC-QMS-008 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RiskReviewTriggered` | SPEC-QMS-008 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RiskReassessed` | SPEC-QMS-008 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InternalAuditScheduled` | SPEC-QMS-009 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InternalAuditStarted` | SPEC-QMS-009 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AuditFindingOpened` | SPEC-QMS-009 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AuditReportApproved` | SPEC-QMS-009 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AuditFindingClosed` | SPEC-QMS-009 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InternalAuditClosed` | SPEC-QMS-009 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ComplaintReceived` | SPEC-QMS-010 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ComplaintInvestigationRequired` | SPEC-QMS-010 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ComplaintInvestigationWaivedWithRationale` | SPEC-QMS-010 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ComplaintReportabilityAssessmentCompleted` | SPEC-QMS-010 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ComplaintCAPAOpened` | SPEC-QMS-010 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ComplaintFieldActionAssessmentOpened` | SPEC-QMS-010 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ComplaintClosed` | SPEC-QMS-010 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FieldActionAssessmentOpened` | SPEC-QMS-011 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FieldActionScopeFrozen` | SPEC-QMS-011 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FieldActionApproved` | SPEC-QMS-011 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FieldActionNotificationSent` | SPEC-QMS-011 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FieldActionUnitReturned` | SPEC-QMS-011 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FieldActionCorrectionCompleted` | SPEC-QMS-011 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FieldActionEffectivenessCompleted` | SPEC-QMS-011 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FieldActionClosed` | SPEC-QMS-011 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FieldActionScopeExpanded` | SPEC-QMS-011 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QualityMetricCalculated` | SPEC-QMS-012 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QualityTrendThresholdExceeded` | SPEC-QMS-012 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `QualitySignalAssessmentOpened` | SPEC-QMS-012 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EffectivenessCheckDue` | SPEC-QMS-012 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EffectivenessCheckPassed` | SPEC-QMS-012 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EffectivenessCheckFailed` | SPEC-QMS-012 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ManagementReviewPackageFrozen` | SPEC-QMS-012 | WP-05 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EquipmentInstalled` | SPEC-EQP-001 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EquipmentQualified` | SPEC-EQP-001 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CalibrationDue` | SPEC-EQP-001 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EquipmentCalibrated` | SPEC-EQP-001 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CalibrationOutOfTolerance` | SPEC-EQP-001 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaintenanceDue` | SPEC-EQP-001 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EquipmentOutOfService` | SPEC-EQP-001 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaintenanceCompleted` | SPEC-EQP-001 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EquipmentReturnedToService` | SPEC-EQP-001 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EquipmentRetired` | SPEC-EQP-001 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CleaningStarted` | SPEC-EQP-002 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CleaningCompleted` | SPEC-EQP-002 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CleaningVerificationFailed` | SPEC-EQP-002 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EquipmentMarkedClean` | SPEC-EQP-002 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CleanHoldExpired` | SPEC-EQP-002 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LineClearanceStarted` | SPEC-EQP-002 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `LineClearanceFailed` | SPEC-EQP-002 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AsepticOperationStarted` | SPEC-EQP-003 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AsepticInterventionRecorded` | SPEC-EQP-003 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `UnplannedInterventionDetected` | SPEC-EQP-003 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AsepticHoldTimeExceeded` | SPEC-EQP-003 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AsepticEnvironmentExcursionDetected` | SPEC-EQP-003 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AsepticOperationHeld` | SPEC-EQP-003 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AsepticOperationCompleted` | SPEC-EQP-003 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EMTaskScheduled` | SPEC-EQP-004 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EMSampleCollected` | SPEC-EQP-004 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EMResultRecorded` | SPEC-EQP-004 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EMAlertTriggered` | SPEC-EQP-004 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EMActionLimitExceeded` | SPEC-EQP-004 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EMDataGapDetected` | SPEC-EQP-004 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EMAreaHeld` | SPEC-EQP-004 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EMExcursionClosed` | SPEC-EQP-004 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SterilizationCycleStarted` | SPEC-EQP-005 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SterilizationCycleCompleted` | SPEC-EQP-005 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SterilizationCycleFailed` | SPEC-EQP-005 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SterilizationCycleAccepted` | SPEC-EQP-005 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SIPStatusIssued` | SPEC-EQP-005 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CIPCompleted` | SPEC-EQP-005 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FilterInstalled` | SPEC-EQP-005 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FilterIntegrityPassed` | SPEC-EQP-005 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FilterIntegrityFailed` | SPEC-EQP-005 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SterileStatusExpired` | SPEC-EQP-005 | WP-06 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SafetyCaseCreated` | SPEC-PM-001 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SafetyProductResolved` | SPEC-PM-001 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SafetyCaseClassified` | SPEC-PM-001 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SafetyCaseFollowupReceived` | SPEC-PM-001 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SafetySignalRuleTriggered` | SPEC-PM-001 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SafetySignalOpened` | SPEC-PM-001 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SafetySignalAssessed` | SPEC-PM-001 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SafetySignalEscalated` | SPEC-PM-001 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PeriodicSafetyDatasetFrozen` | SPEC-PM-001 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ApplicantRelationshipConfigured` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `Part4SharingAssessmentCreated` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ConstituentSharingPackageCreated` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ConstituentInformationShared` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CorrectionRemovalAssessmentOpened` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CorrectionRemovalReportabilityDecided` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FieldAlertAssessmentOpened` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FieldAlertDecisionRecorded` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `BPDRTrackCreated` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PeriodicSafetyScheduleGenerated` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PeriodicDatasetFrozen` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FDAInformationRequestOpened` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RegulatoryDeadlineOverridden` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PostmarketRetentionPolicyCalculated` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PostmarketLegalHoldPlaced` | SPEC-PM-003 | WP-09 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ThreatModelDraftCreated` | SPEC-SEC-001 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ThreatRegistered` | SPEC-SEC-001 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SecurityControlMapped` | SPEC-SEC-001 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ResidualSecurityRiskAccepted` | SPEC-SEC-001 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SecurityExceptionOpened` | SPEC-SEC-001 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ThreatModelReviewRequired` | SPEC-SEC-001 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AuthenticationSucceeded` | SPEC-SEC-002 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AuthenticationFailed` | SPEC-SEC-002 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MFARequired` | SPEC-SEC-002 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SessionCreated` | SPEC-SEC-002 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SessionRevoked` | SPEC-SEC-002 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ExternalIdentityMapped` | SPEC-SEC-002 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ServiceIdentityProvisioned` | SPEC-SEC-002 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PrivilegedAccessRequested` | SPEC-SEC-003 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PrivilegedAccessGranted` | SPEC-SEC-003 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SupportSessionOpened` | SPEC-SEC-003 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AdminCommandExecuted` | SPEC-SEC-003 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `BreakGlassActivated` | SPEC-SEC-003 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PrivilegedSessionClosed` | SPEC-SEC-003 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PrivilegedSessionReviewed` | SPEC-SEC-003 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `APIAccessDenied` | SPEC-SEC-004 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RateLimitTriggered` | SPEC-SEC-004 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SSRFBlocked` | SPEC-SEC-004 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MaliciousUploadDetected` | SPEC-SEC-004 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `WebhookReplayDetected` | SPEC-SEC-004 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeprecatedAPIUsed` | SPEC-SEC-004 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SecretAccessDenied` | SPEC-SEC-005 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SecretRotated` | SPEC-SEC-005 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CertificateIssued` | SPEC-SEC-005 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CertificateRotated` | SPEC-SEC-005 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CertificateRevoked` | SPEC-SEC-005 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CryptoHealthFailed` | SPEC-SEC-005 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `KeyAccessAnomaly` | SPEC-SEC-005 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ForbiddenNetworkPathDetected` | SPEC-SEC-006 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `TenantScopeMismatchDetected` | SPEC-SEC-006 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `WorkloadHardeningFailed` | SPEC-SEC-006 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `UnexpectedPublicExposureDetected` | SPEC-SEC-006 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SecurityAlertRaised` | SPEC-SEC-007 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SecurityIncidentOpened` | SPEC-SEC-007 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `IncidentContainmentExecuted` | SPEC-SEC-007 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ForensicEvidencePreserved` | SPEC-SEC-007 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SecurityGxPImpactAssessed` | SPEC-SEC-007 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SecurityIncidentClosed` | SPEC-SEC-007 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ReleaseSBOMGenerated` | SPEC-SEC-008 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `VulnerabilityRegistered` | SPEC-SEC-008 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `VulnerabilityAssessed` | SPEC-SEC-008 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SecurityReleaseBlocked` | SPEC-SEC-008 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ReleaseArtifactSigned` | SPEC-SEC-008 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SecurityAdvisoryPublished` | SPEC-SEC-008 | WP-10 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ProjectionUpdateRequested` | SPEC-DATA-001 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ProjectionRebuilt` | SPEC-DATA-001 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ProjectionStaleDetected` | SPEC-DATA-010 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CrossStoreMismatchDetected` | SPEC-DATA-001 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MigrationProvenanceRecorded` | SPEC-DATA-001 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DatabaseIntegrityFailure` | SPEC-DATA-002 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PartitionGapDetected` | SPEC-DATA-002 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ReplicaLagExceeded` | SPEC-DATA-002 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MigrationApplied` | SPEC-DATA-002 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeadlockDetected` | SPEC-DATA-002 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ConnectionPoolExhausted` | SPEC-DATA-002 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FrappeProjectionApplied` | SPEC-DATA-003 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FrappeProjectionRebuilt` | SPEC-DATA-003 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DirectProjectionMutationDenied` | SPEC-DATA-003 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EvidenceUploadStaged` | SPEC-DATA-004 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EvidenceFinalized` | SPEC-DATA-004 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EvidenceHashMismatch` | SPEC-DATA-004 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EvidenceMissing` | SPEC-DATA-004 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EvidenceLegalHoldApplied` | SPEC-DATA-004 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EvidencePurged` | SPEC-DATA-004 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EvidenceProviderMigrated` | SPEC-DATA-004 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EventPublished` | SPEC-DATA-005 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EventDeadLettered` | SPEC-DATA-005 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EventReplayStarted` | SPEC-DATA-005 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EventSchemaBreakingChangeDetected` | SPEC-DATA-005 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ConsumerLagExceeded` | SPEC-DATA-005 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OutboxLagExceeded` | SPEC-DATA-010 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `WorkflowStarted` | SPEC-DATA-006 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `WorkflowStuckDetected` | SPEC-DATA-006 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `TemporalWorkerVersionChanged` | SPEC-DATA-006 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `WorkflowCompensationExecuted` | SPEC-DATA-006 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `TemporalNamespaceUnavailable` | SPEC-DATA-006 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SearchDocumentIndexed` | SPEC-DATA-007 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SearchIndexRebuilt` | SPEC-DATA-007 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ReadModelRefreshed` | SPEC-DATA-007 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CacheInvalidated` | SPEC-DATA-007 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ProjectionLagExceeded` | SPEC-DATA-010 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ExportGenerated` | SPEC-DATA-007 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `BackupRPOAtRisk` | SPEC-DATA-008 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RestoreTestFailed` | SPEC-DATA-008 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DatabaseFailoverCompleted` | SPEC-DATA-008 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EvidenceRestoreMismatch` | SPEC-DATA-008 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PlatformRecoveryValidated` | SPEC-DATA-008 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RecoveryDataLossDetected` | SPEC-DATA-008 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeploymentPrerequisiteFailed` | SPEC-DATA-009 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InfrastructureApplied` | SPEC-DATA-009 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InstallationChecksCompleted` | SPEC-DATA-009 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InfrastructureDriftDetected` | SPEC-DATA-009 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PlatformUpgraded` | SPEC-DATA-009 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RollbackInitiated` | SPEC-DATA-009 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CertificateExpiryWarning` | SPEC-DATA-009 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OperationalAlertRaised` | SPEC-DATA-010 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PerformanceRegressionDetected` | SPEC-DATA-010 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `CapacityThresholdForecasted` | SPEC-DATA-010 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DatabaseSaturationDetected` | SPEC-DATA-010 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `GracefulDegradationVerified` | SPEC-DATA-010 | WP-11 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationMasterPlanReleased` | SPEC-VAL-001 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationDeliverablesDerived` | SPEC-VAL-001 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationReleaseGateEvaluated` | SPEC-VAL-001 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationPackageGenerated` | SPEC-VAL-001 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `IntendedUseCreated` | SPEC-VAL-002 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `FunctionRiskAssessed` | SPEC-VAL-002 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RiskAssessmentApproved` | SPEC-VAL-002 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AssuranceLevelDerived` | SPEC-VAL-002 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationRiskReassessmentRequired` | SPEC-VAL-002 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RequirementIngested` | SPEC-VAL-003 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RequirementBaselineFrozen` | SPEC-VAL-003 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `TraceabilityGapDetected` | SPEC-VAL-003 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `TraceabilityMatrixGenerated` | SPEC-VAL-003 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationTestApproved` | SPEC-VAL-004 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationTestExecutionStarted` | SPEC-VAL-004 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationTestCompleted` | SPEC-VAL-004 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AutomatedEvidenceImported` | SPEC-VAL-004 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationTestReviewed` | SPEC-VAL-004 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InstalledInventoryCaptured` | SPEC-VAL-005 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `IQPrerequisitesVerified` | SPEC-VAL-005 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `IQCompleted` | SPEC-VAL-005 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `IQApproved` | SPEC-VAL-005 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OQSuiteDerived` | SPEC-VAL-006 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OQExecutionCompleted` | SPEC-VAL-006 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OQCoverageEvaluated` | SPEC-VAL-006 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `OQApproved` | SPEC-VAL-006 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PQScenarioCreated` | SPEC-VAL-007 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PQScenarioCompleted` | SPEC-VAL-007 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PQUsabilityObservationRecorded` | SPEC-VAL-007 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PQApproved` | SPEC-VAL-007 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InfrastructureFingerprintCaptured` | SPEC-VAL-008 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InfrastructureQualificationDifferenceDetected` | SPEC-VAL-008 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InfrastructureQualified` | SPEC-VAL-008 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MigrationSourceProfiled` | SPEC-VAL-009 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MigrationDryRunCompleted` | SPEC-VAL-009 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MigrationReconciled` | SPEC-VAL-009 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `MigrationAccepted` | SPEC-VAL-009 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `Part11AssessmentCreated` | SPEC-VAL-010 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `Part11TestSuiteDerived` | SPEC-VAL-010 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `Part11QualificationApproved` | SPEC-VAL-010 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `AuditTamperTestCompleted` | SPEC-VAL-011 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `VaultCanonicalizationVerified` | SPEC-VAL-011 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ArchiveRetrievalVerified` | SPEC-VAL-011 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DataIntegrityQualificationApproved` | SPEC-VAL-011 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InterfaceContractTestsCompleted` | SPEC-VAL-012 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `EdgeOutageQualificationCompleted` | SPEC-VAL-012 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InterfaceReconciliationVerified` | SPEC-VAL-012 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `InterfaceQualificationApproved` | SPEC-VAL-012 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DRRestoreExecuted` | SPEC-VAL-013 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RecoveryObjectivesMeasured` | SPEC-VAL-013 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RecoveredGxPSmokeCompleted` | SPEC-VAL-013 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DRQualificationApproved` | SPEC-VAL-013 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SecurityControlTestCompleted` | SPEC-VAL-014 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PenTestFindingImported` | SPEC-VAL-014 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SecurityQualificationGateEvaluated` | SPEC-VAL-014 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `SecurityQualificationApproved` | SPEC-VAL-014 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PerformanceQualificationExecuted` | SPEC-VAL-015 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PerformanceAcceptanceEvaluated` | SPEC-VAL-015 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeploymentSizingDerived` | SPEC-VAL-015 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PerformanceQualificationApproved` | SPEC-VAL-015 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationExceptionCreated` | SPEC-VAL-016 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationExceptionTriaged` | SPEC-VAL-016 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationRetestScopeDefined` | SPEC-VAL-016 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationExceptionDispositioned` | SPEC-VAL-016 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationSummaryGenerated` | SPEC-VAL-017 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `GoLiveReadinessEvaluated` | SPEC-VAL-017 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationSummaryApproved` | SPEC-VAL-017 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidatedReleaseAuthorized` | SPEC-VAL-017 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `DeploymentMatchesValidatedRelease` | SPEC-VAL-017 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PostGoLiveVerificationCompleted` | SPEC-VAL-017 | WP-14 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidationChangeImpactAssessed` | SPEC-VAL-018 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RevalidationPlanApproved` | SPEC-VAL-018 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `RevalidationCompleted` | SPEC-VAL-018 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `PeriodicReviewCreated` | SPEC-VAL-018 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidatedStateEvaluated` | SPEC-VAL-018 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |
| `ValidatedSystemDecommissioned` | SPEC-VAL-018 | WP-12 | 1.0 | projections, read models, integrations | per aggregate_id | event_id | initial |

---

## Change records

Every schema change appends a record here with its impact and consumer list (CTRC-FR-007).
The tables above are the Phase-0 baseline inventory, generated from Documents 01–105 before any code
existed. Where a change record below contradicts a baseline row, the change record is current.

### CR-001 — 2026-08-27 — WP-01 GxP Core contract slice (Documents 03, 04, 05, 06, 08)

**Change:** first committed field-level contracts for SPEC-GXP-001/002/003/004/006, closing part of
SG-013. Five files added under `contracts/openapi/`. No implementation code was changed, so no
runtime behaviour changed for any consumer.

| Contract | Module | Doc | Operations | Kind |
|---|---|---|---|---|
| `spec-gxp-001.yaml` | SPEC-GXP-001 | 03 | 0 (components-only) | new |
| `spec-gxp-002.yaml` | SPEC-GXP-002 | 04 | 0 (components-only) | new |
| `spec-gxp-003.yaml` | SPEC-GXP-003 | 05 | 5 | new |
| `spec-gxp-004.yaml` | SPEC-GXP-004 | 06 | 6 | new |
| `spec-gxp-006.yaml` | SPEC-GXP-006 | 08 | 6 | new |

**Compatibility classification: INITIAL.** These contracts describe operations that already exist and
already behave this way; nothing is added, removed, renamed or narrowed. There is no breaking change
and no `schema_version` bump. Consumers: the eBMR SPA frontend (`frontend/`) and any internal caller of
`services/gxp-api`. No external customer integration consumes these five surfaces today.

**Shared-envelope decision.** `spec-gxp-001.yaml` is the single definition of `CommandEnvelope`,
`MutationReceipt`, `ErrorResponse`, `PlatformErrorCode` and `PageEnvelope`; the other four `$ref` it by
relative file path. A neutral `_common.yaml` was rejected because CTR-FR-031 requires every contract to
have an owning service and Document 03 is the declared owner of command/idempotency/receipt semantics.
Consequence for every later work package: the WP-02..WP-14 contracts should `$ref` these rather than
redefine them, and the eight contracts written before this slice still define their own local copies.

**Declared deviations from Document 113 §2's canonical envelopes.** Each is a narrowing of the
specified shape to what is built. None is a change to a shipped interface; all are recorded so the
compatibility tool has a single truth to check against.

| Envelope | Document 113 §2 field | Built | Impact if later added |
|---|---|---|---|
| Command | `command_id`, `requested_at` | assigned server-side, not transported | additive optional → minor |
| Command | `command_type`, `aggregate_type` | fixed by the route | n/a — would be redundant |
| Command | `aggregate_id` | path parameter | n/a |
| Command | `tenant_id`, `site_id` | derived from the authenticated actor | **must not** be added — CTR-FR-011 forbids a caller field overriding authenticated scope |
| Command | `expected_version` | declared per command, absent on all 17 WP-01 operations | **required-field addition → breaking**, needs `schema_version` bump (SG-014) |
| Command | `reason` | declared per command where the domain requires it | additive optional → minor |
| Command | nested `payload` | flattened into the command body | restructuring → breaking |
| Receipt | `previous_version`, `decision`, `record_hash`, `committed_at_utc`, `projection_status` | omitted | additive optional → minor |
| Receipt | `signature_ids` (array) | singular nullable `signature_id` | type change → breaking; needed only when a single command carries two signatures, which none does |
| Error | `error_code` / nested `error` object / `retryable` / `correlation_id` | flat `{code, message, details}` | three-way source conflict — see SG-140; adding `correlation_id` would be additive optional → minor |
| Event | whole envelope | `outbox_events` carries `id` (the event id, under a different name), `event_type`, `aggregate_type`, `aggregate_id`, `aggregate_version`, `payload`, `correlation_id`, `causation_id`, `occurred_at` — but **no `schema_version` and no `tenant_id`/`site_id`** | not yet contract-published (see below) |

**Pagination deviation.** `PageEnvelope` is offset/limit with `page_size` bounded to 100 and a declared
sortable-column set. CTR-FR-012 prefers bounded cursor/keyset paging with stable ordering for large
lists. Offset paging is not stable under concurrent insert. Recorded as a known deviation rather than
changed, because switching would be a breaking change to every list endpoint in the platform.
Two operations return a bare array rather than the page envelope —
`getVaultVersionsForBusinessId` and `getRuleVersions` — because a single business object's version
history is bounded by construction.

**Events: no change.** This slice covered the API half of SG-013 only. All 484 event types remain
name-and-path entries with no committed AsyncAPI or JSON Schema, and no event contract is published
here. The outbox envelope's missing `schema_version` and tenant/site scope are noted
above and must be resolved before any event contract can claim Document 113 §2 conformance or
CTR-FR-026/EVT-FR-001 compliance. Note also that the publisher in `app/main.py` is a Phase-1 log-only
stand-in with no real bus, so no consumer exists to be broken and no delivery semantics are testable.

**Enforcement added.** `tooling/contracts/validate.py` now gates CTRC-FR-001/002/003/009 and
CTR-FR-002 across every file in `contracts/openapi/`. Its first run found 107 violations, all of them
in the eight contracts written before the gate existed; the five contracts added by this change record
are clean. Those 107 are recorded under SG-013 and were deliberately not fixed as part of this change.

**New gaps raised by this change:** SG-139 (Doc 03/04 declare 7 unimplemented operations; Document 113
§6 records no exposure boundary for either module), SG-140 (three-way error-envelope conflict),
SG-141 (`Disposition` signature meaning outside the SIG-FR-003 catalogue), SG-142 (unconstrained audit
action vocabulary), SG-143 (rules evaluator ignores its own precision/rounding/UOM policies),
SG-144 (`SimulateRuleRequest` not a closed payload).

### CR-002 — 2026-08-27 — Document 110 precision/rounding/UOM enforcement closes SG-143

**Change:** `spec-gxp-006.yaml` updated in place (no operation added, removed or renamed — same six
operations as CR-001). `precision_policy.calculation_class`, `unit_policy` entries and division-by-zero
handling are now enforced at runtime where the contract previously stated they were not (SG-143).

| Operation | Kind | Detail |
|---|---|---|
| `postCreateRuleDraft` | narrowed | `precision_policy.calculation_class` must resolve to one of Document 110 §2's ten calculation classes (`PRECISION_POLICY_UNRESOLVED`, 409) — a new required-content constraint inside the existing free-form `precision_policy: object`, not a schema shape change (the property was already `required`). |
| `postSimulateRule` | narrowed | Comparisons round to the resolved class's declared comparison precision (N4) before evaluating; a `unit_policy` entry is validated against the new UOM master and may now fail `UOM_UNKNOWN` (422) or `UOM_CONVERSION_UNAVAILABLE` (404); a division by zero now fails `DIVISION_UNDEFINED` (409) instead of the generic `VALIDATION_FAILED` (422) it fell under before. |
| `postEvaluateRule` | additive | Same runtime behaviour as simulate, but every Document 110 condition is caught and recorded as a persisted `ERROR`-outcome evaluation row (with the stable code in `result.code`) rather than raised — consistent with the operation's existing "a failed evaluation is a recorded outcome, not a dropped request" contract. New nullable `RuleEvaluation.raw_result`/`.applied_policy_version` columns (migration `f3a8c1e5b7d2`) are not exposed on the `MutationReceipt` this operation returns — no consumer-visible shape change. |

**Compatibility classification: MOSTLY ADDITIVE, ONE NARROWING.** `postSimulateRule`'s division-by-zero
status code changes from `422 VALIDATION_FAILED` to `409 DIVISION_UNDEFINED` for the one input shape
that triggers it (previously not distinguishable from any other malformed expression). No consumer of
this surface exists outside the eBMR SPA and this pass's own tests (same consumer set as CR-001), so
this is recorded as a compatibility fact for the registry rather than treated as requiring a
`schema_version` bump — reconsider if `postSimulateRule` gains an external consumer.

**Two module-scoped error codes added**, per Document 110 §5, declared in `spec-gxp-006.yaml`'s
operation-level response prose (the established lightweight pattern this file's other pre-gate
contracts use — e.g. `spec-erp-006.yaml`) rather than a new formal enum schema: `DIVISION_UNDEFINED`
(409), `UOM_UNKNOWN` (422), `UOM_CONVERSION_UNAVAILABLE` (404), `NUMERIC_OVERFLOW` (422),
`PRECISION_POLICY_UNRESOLVED` (409, `postCreateRuleDraft` only). None was added to `spec-gxp-001.yaml`'s
`PlatformErrorCode` — Document 113 §4 reserves that registry for platform-wide classes, and these five
are scoped to the rules/calculation domain.

**New gaps raised by this change:** SG-145 (Document 110 §2's calculation-class table is marked
"(PROPOSED)" inside an otherwise APPROVED v1.0 document — implemented as the construction baseline per
the task decision, pending a Part 11 approval record against §2 specifically), SG-146 (the new
`rules.gxp_uom`/`gxp_uom_conversion` master has no author/release command surface yet, and the
pre-existing free-text UOM columns across batch/qc/genealogy/yield/material/recipe_master/
product_master/batch_execution are unmigrated).

### CR-003 — 2026-08-27 — UOM/conversion authoring command surface (SG-146, authoring half)

**Change:** `spec-gxp-006.yaml` grows from 6 to 11 operations. Five new operations author and release
the `rules.gxp_uom`/`rules.gxp_uom_conversion` master rows Document 110 §3 requires and the rules
evaluator's `unit_policy` resolution has enforced since CR-002 — until now, only a controlled
migration/seed or a test fixture could write one.

| Operation | Method + path | Kind |
|---|---|---|
| `postCreateUomDraft` | `POST /rules/v1/uom/drafts` | new |
| `postReleaseUom` | `POST /rules/v1/uom/{uomId}/release` | new |
| `getUomVersions` | `GET /rules/v1/uom/{code}/versions` | new |
| `postCreateUomConversionDraft` | `POST /rules/v1/uom-conversions/drafts` | new |
| `postReleaseUomConversion` | `POST /rules/v1/uom-conversions/{conversionId}/release` | new |

**Compatibility classification: ADDITIVE.** Five wholly new operations under wholly new paths; nothing
existing is renamed, removed or narrowed. No `schema_version` bump. Same consumer set as CR-001/CR-002
(the eBMR SPA frontend and internal callers of `services/gxp-api`; no external customer integration
consumes `/rules/v1` today).

**Design reuse, not new machinery.** Same draft→released lifecycle (two states, no `validated` — a UOM
row has no expression to statically check), same fail-closed signature resolution
(`SIGNATURE_POLICY_UNRESOLVED` pending a Document 106 `(uom, release)`/`(uom_conversion, release)`
policy row) and same Vault-snapshot-on-release discipline (`object_type="uom"`/`"uom_conversion"`)
`postCreateRuleDraft`/`postReleaseRule` already established. Reuses the existing `rules.author`/
`rules.release` policy actions rather than declaring new ones — no permission-catalogue change.

**Downstream reconciliation in the same pass:** `app/modules/yield_reconciliation/commands.py`'s
`evaluate_yield()` previously read `rule.rounding_policy.get("reported_dp"/"mode")` directly and
re-quantized with its own `_quantize()` helper — a second rounding pathway alongside
`app/modules/rules/precision.py`, flagged in CR-002/SG-143's resolution note. It now reads
`RuleEvaluation.result`/`.raw_result` directly (already rounded by the engine per the rule's own
`precision_policy.calculation_class`), and the seeded `yield_percent` floor rule
(`scripts/seed.py`, `tests/conftest.py`) was updated from the legacy `{"class": "CC-4", ...}` shape to
`{"calculation_class": "CC-4"}`. No API/event contract change — `EvaluateYieldCommand`'s request/response
shape and `/manufacturing-calculations/v1/yield/evaluate`'s behaviour are unchanged for a caller;
`calc.result["yield_percent"]` still reports the same 2dp half-up value as before, computed by one path
instead of two.

**New gaps:** none. SG-146's authoring-surface half is closed by this change (see the SG-146 entry in
`18_SPEC_GAPS.md`, downgraded to `PARTIALLY_RESOLVED`); the free-text-UOM-columns half remains open.

### CR-004 — 2026-08-27 — WP-02 contract slice, module 1 of 4: Document 09 (SPEC-EBMR-000, Product Master)

**Change:** `spec-ebmr-000.yaml` committed — first field-level contract for `/products/v1`, 11 operations
(`postCreateProductDraft`, `putUpdateProductDraft`, `postSubmitProductDraft`, `postReleaseProductVersion`,
`postSuspendProductVersion`, `postReinstateProductVersion`, `getProductVersions`,
`getProductVersionDetail`, `postValidateProductCompleteness`, `getProductConstituentCompatibility`,
`getProductIssueEligibility`), closing 11 of SG-013's uncontracted-operations backlog.

**Compatibility classification: INITIAL.** Describes operations that already exist and already behave
this way; nothing added, removed, renamed or narrowed. No `schema_version` bump. Same consumer set as
CR-001 (the eBMR SPA frontend and internal callers; no external customer integration consumes
`/products/v1` today).

**Verification, not just authorship:** validated clean against `tooling/contracts/validate.py`
(0 findings: parseable, OpenAPI 3.1, every `$ref` resolves, every `*Command` schema closed, every
schema/operation carries `x-requirement-ids`, canonical `MutationReceipt`/`ErrorResponse` envelopes used
throughout) and against the live route table (`implemented − committed = ∅` and
`committed − implemented = ∅` for `/products/v1` — exact 1:1 coverage, not a partial/best-effort
contract). `tooling/contracts/validate.py`'s baseline violation count is unchanged at 107 — this
contract adds zero new debt.

**$ref reuse, same shared-envelope decision as CR-001.** `CommandEnvelope`/`MutationReceipt`/
`ErrorResponse`/the standard error responses are `$ref`'d from `spec-gxp-001.yaml` by relative path, not
redefined.

**SG-146 cross-reference:** `ProductVersion.strength_uom_id` (the SG-146 expand-step column added to
`ebmr.gxp_product_version` in migration `e7b3f9a2c6d4`) is documented on the `ProductVersion` schema —
the first contract in this registry to describe a SG-146 dual-write column.

**New gaps:** none. `app/modules/product` (an older, differently-scoped stub) is confirmed out of scope
for this contract — see the file's own description block for the general "two live modules with a
similar name" caution this codebase has now surfaced three times (`batch`/`batch_execution` per
migration `e7b3f9a2c6d4`'s note being the other two).

### CR-005 — 2026-08-27 — WP-02 contract slice, module 2 of 4: Document 10 (SPEC-EBMR-001, Master Recipe / MMR)

**Change:** `spec-ebmr-001.yaml` committed — first field-level contract for `/recipes/v2`, 10 operations
(`postCreateRecipeDraft`, `putUpdateRecipeDraft`, `postValidateRecipeDraft`, `postSimulateRecipeDraft`,
`postSubmitRecipeDraft`, `postReleaseRecipeVersion`, `getRecipeVersions`, `getRecipeVersionDetail`,
`getRecipeVersionCompare`, `getRecipeIssueEligibility`), closing 10 more of SG-013's uncontracted-
operations backlog.

**Compatibility classification: INITIAL.** Describes operations that already exist and already behave
this way; nothing added, removed, renamed or narrowed. No `schema_version` bump. Same consumer set as
CR-001/CR-004 (the eBMR SPA frontend and internal callers; no external customer integration consumes
`/recipes/v2` today).

**Verification, not just authorship:** validated clean against `tooling/contracts/validate.py`
(0 findings referencing this file, both with and without `--strict-coverage`: parseable, OpenAPI 3.1,
every `$ref` resolves, every `*Command` schema closed, every schema/operation carries
`x-requirement-ids`, canonical `MutationReceipt`/`ErrorResponse` envelopes used throughout) and against
the live route table (`implemented − committed = ∅` and `committed − implemented = ∅` for `/recipes/v2`
— exact 10:10 coverage, not a partial/best-effort contract). `tooling/contracts/validate.py`'s baseline
violation count (without `--strict-coverage`, the mode the documented "107" baseline was measured in) is
unchanged at 107 — this contract adds zero new debt. Regression check: `tests/test_recipe_master.py`,
`tests/test_batch4to8_uom.py` and `tests/test_contract_conformance.py` re-run against this contract file
present with real results captured in the task completion report (no code under `app/modules/recipe_master`
changed by this contract addition).

**$ref reuse, same shared-envelope decision as CR-001/CR-004.** `CommandEnvelope`/`MutationReceipt`/
`ErrorResponse`/the standard error responses are `$ref`'d from `spec-gxp-001.yaml` by relative path, not
redefined.

**SG-146 cross-reference:** `RecipeVersion.batch_size_uom_id` is documented on the `RecipeVersion` schema.
`RecipeParameter.uom_id` exists on the model (migration `e7b3f9a2c6d4`) but the router's response dict
(`_parameter_dict`) does not return it — documented as a known read-side gap on the `RecipeParameter`
schema rather than silently "corrected" by inventing a field the API does not actually return.

**New gaps:** none newly raised. `app/modules/recipe` (an older, differently-scoped Batch-facing stub) is
confirmed out of scope — the fourth occurrence of the "two live modules with a similar name" pattern in
this codebase (`product`/`product_master`, `batch`/`batch_execution`, `recipe`/`recipe_master`, and the
general note in `e7b3f9a2c6d4`). Pre-existing SG-013/SG-046 backlog items already cover what this
contract deliberately excludes (conditional branches, material/equipment/personnel/area requirements,
sterile/device-assembly/packaging step metadata, rework routing, template reuse) — see the contract
file's own description block for the full list; no new SPEC_GAP entry was needed.

### CR-006 — 2026-08-27 — WP-02 contract slice, module 3 of 4: Document 11 (SPEC-EBMR-002, Batch Execution Engine)

**Change:** `spec-ebmr-002.yaml` committed — first field-level contract for `/batches/v1`, 10 operations
(`postCreateBatch`, `getBatchList`, `getBatchDetail`, `postIssueBatch`, `getBatchExecutionView`,
`postStartBatch`, `postHoldBatch`, `postResumeBatch`, `postAbortBatch`, `postStartStep`), closing 10 more
of SG-013's uncontracted-operations backlog.

**Compatibility classification: INITIAL.** Describes operations that already exist and already behave
this way; nothing added, removed, renamed or narrowed. No `schema_version` bump. Same consumer set as
CR-001/CR-004/CR-005 (the eBMR SPA frontend and internal callers; no external customer integration
consumes `/batches/v1` today).

**Verification, not just authorship:** validated clean against `tooling/contracts/validate.py`
(0 findings referencing this file, run without `--strict-coverage` — the mode the documented "107"
baseline was measured in — parseable, OpenAPI 3.1, every `$ref` resolves, every `*Command` schema
closed, every schema/operation carries `x-requirement-ids`, canonical `MutationReceipt`/`ErrorResponse`
envelopes used throughout) and against the live route table (`implemented − committed = ∅` and
`committed − implemented = ∅` for `/batches/v1` — exact 10:10 coverage). Baseline violation count is
unchanged at 107 — this contract adds zero new debt. Regression check:
`tests/test_recipe_master.py` + `tests/test_batch4to8_uom.py` + `tests/test_contract_conformance.py`
(64 passed) re-run clean with this contract file present (no code under `app/modules/batch_execution`
changed by this contract addition).

**$ref reuse, same shared-envelope decision as CR-001/CR-004/CR-005.** `CommandEnvelope`/
`MutationReceipt`/`ErrorResponse`/the standard error responses are `$ref`'d from `spec-gxp-001.yaml` by
relative path, not redefined.

**SG-146 cross-reference:** `Batch.target_uom_id` is documented on the `Batch` schema.

**New gaps:** none newly raised. `app/modules/batch` (an older module still referencing the legacy
`ebmr.products`/`ebmr.recipes` schema) is confirmed out of scope — the third documented occurrence of the
"two live modules with a similar name" pattern. This contract's own description block documents, rather
than silently omits, the scope this pass does not reach: only 2 of Document 11's 5 owned entities are
DDL-ready (`gxp_step_result`/`gxp_step_evidence_link`/`gxp_batch_hold` are SG-047), the batch lifecycle
implemented is a narrow buildable subset of BAT-FR-004's full state list (SG-048), and step readiness is
predecessor-only (BAT-FR-006) — pre-existing SG-047/SG-048 backlog already covers all of it; no new
SPEC_GAP entry was needed.

### CR-007 — 2026-08-27 — WP-02 contract slice, module 4 of 4: Document 12 (SPEC-EBMR-003, eDHR)

**Change:** `spec-ebmr-003.yaml` committed — first field-level contract for `/devices/v1`, 6 operations
(`postCreateDeviceLot`, `postBulkCreateDeviceUnits`, `postHoldDeviceUnit`, `getDeviceUnitBySerial`,
`getDeviceUnitHistory`, `getDeviceLotReleaseReadiness`), closing 6 more of SG-013's uncontracted-
operations backlog and completing this WP-02 contract slice (product_master → recipe_master →
batch_execution → device, CR-004 through CR-007, 37 operations total across 4 files).

**Compatibility classification: INITIAL.** Describes operations that already exist and already behave
this way; nothing added, removed, renamed or narrowed. No `schema_version` bump. Same consumer set as
CR-001/CR-004/CR-005/CR-006 (the eBMR SPA frontend and internal callers; no external customer integration
consumes `/devices/v1` today).

**Verification, not just authorship:** validated clean against `tooling/contracts/validate.py`
(0 findings referencing this file, run without `--strict-coverage` — the mode the documented "107"
baseline was measured in — parseable, OpenAPI 3.1, every `$ref` resolves, every `*Command` schema
closed, every schema/operation carries `x-requirement-ids`, canonical `MutationReceipt`/`ErrorResponse`
envelopes used throughout) and against the live route table (`implemented − committed = ∅` and
`committed − implemented = ∅` for `/devices/v1` — exact 6:6 coverage). Baseline violation count is
unchanged at 107 across all four files added this pass — cumulative zero new debt. Regression check:
`tests/test_device.py` + `tests/test_batch_execution.py` + `tests/test_contract_conformance.py` re-run
with this contract file present (result captured in the task completion report; no code under
`app/modules/device` changed by this contract addition).

**$ref reuse, same shared-envelope decision as CR-001/CR-004/CR-005/CR-006.** `CommandEnvelope`/
`MutationReceipt`/`ErrorResponse`/the standard error responses are `$ref`'d from `spec-gxp-001.yaml` by
relative path, not redefined.

**No SG-146 cross-reference.** Unlike CR-004/CR-005/CR-006, Document 12's owned entity (`DeviceUnit`) has
no free-text UOM column — device production history in this baseline carries no quantity/UOM field, so
SG-146's expand step never touched this module.

**New gaps:** none newly raised. Unlike `product`/`recipe`/`batch`, no legacy `device` stub exists — this
is Document 12's only module, so there is no "two live implementations" caution to record here. This
contract's description block documents the scope this pass does not reach: only 1 of Document 12's 5
owned entities is DDL-ready (`device_component_usage`/`device_test_result`/`device_defect`/
`device_evidence_inheritance` are SG-049), the state model reaches only `created`/`hold` of Document 12
§4's full model (SG-050), `getDeviceUnitHistory` returns only the current row despite its name, and
`getDeviceLotReleaseReadiness` is explicitly non-authoritative (state-only, not a release decision) —
pre-existing SG-049/SG-050 backlog already covers all of it; no new SPEC_GAP entry was needed.

### CR-013 — 2026-08-29 — Contract-hygiene sweep: every pre-existing `tooling/contracts/validate.py` violation resolved

**Change:** not new contract authoring — a cleanup pass over the 8 contract files that predated this
session's own WP-02/WP-03 work and carried real, pre-existing violations: `spec-mat-001.yaml`,
`spec-qc-001.yaml`, `spec-qc-002.yaml`, `spec-qc-003.yaml`, `spec-iam-001.yaml`, `spec-erp-006.yaml`,
`spec-edge-001.yaml`, `spec-edge-005.yaml`. `tooling/contracts/validate.py` now reports
**`PASS  no contract conformance violations found`** — the documented "107" baseline this registry has
tracked since CR-001 is fully resolved, not just held flat.

**What was actually wrong, by category:**
- **A real YAML parse bug** in `spec-qc-001.yaml`: an unquoted `summary:` string containing `(Doc 106:
  only if flagged critical)` — the bare `106:` mid-string was parsed as a nested mapping key. Fixed by
  quoting the string. Same known trap this session's `18_SPEC_GAPS.md` edits hit twice earlier
  (unquoted colon inside a flow-style YAML value).
- **A genuine path-parameter naming bug**, not a missing operation, in two files: `spec-qc-003.yaml` and
  `spec-edge-005.yaml` declared path parameters in camelCase (`{oosId}`, `{ootId}`, `{resultId}`,
  `{mappingId}`, `{contextId}`, `{sourceId}`, `{requestId}`, `{siteId}`) while the actual FastAPI routes
  use snake_case (`{oos_id}`, `{oot_id}`, `{result_id}`, `{mapping_id}`, `{context_id}`, `{source_id}`,
  `{request_id}`, `{site_id}`) — Python/this-codebase's own convention, matching every other module.
  `tooling/contracts/validate.py` treats a path with a differently-named parameter as a different
  operation entirely, so this surfaced as 12 (`spec-qc-003.yaml`) + a further count
  (`spec-edge-005.yaml`) "implemented operation missing from contract" findings that were never really
  missing operations — corrected with a mechanical find-and-replace once traced to the router source.
- **`x-requirement-ids` genuinely absent** on ~84 schemas and a handful of operations across all 8
  files — the largest category by count. Every addition traced to a real, existing requirement ID
  confirmed present in `01_REQUIREMENT_REGISTRY.csv` before use (never invented) — the same discipline
  this session's WP-02/WP-03 contracts followed throughout.
- **Two genuinely missing operations** in `spec-mat-001.yaml`: `GET /suppliers/v1` and
  `GET /suppliers/v1/{supplier_id}` were implemented in `app/modules/supplier_quality/router.py` but had
  never been contracted. Added with real response schemas (`Supplier`, `SupplierPage`, `SupplierDetail`,
  `SupplierSite`, `SupplierQualificationSummary`) traced to the router's own `_supplier_dict`/
  `_qualification_dict` field lists.
- **Self-inflicted duplicate-YAML-key bug caught and fixed in the same pass**: adding the two new
  `/suppliers/v1` GET operations as a *second* `/suppliers/v1:` path-item block silently shadowed the
  file's pre-existing `POST /suppliers/v1` block (YAML last-key-wins on a duplicate mapping key) — caught
  because it flipped a fixed `POST /suppliers/v1` finding into a newly-broken one on the very next
  `validate.py` run, not assumed fixed from a first pass. Corrected by merging the `get:` into the
  existing path item and deleting the duplicate key. Recorded here as a caution for merging into any
  contract file with the flow-mapping/multi-line-key style this repo's earlier (pre-CR-001) contracts
  use — always re-run `validate.py` after every edit, not just after the last one.

**Not touched:** `spec-qc-003.yaml`'s implemented-but-uncontracted `GET /supplier-qualifications/
{qualification_id}` (a distinct `--strict-coverage`-only surface, out of this cleanup's scope — noted in
`spec-mat-001.yaml`'s own description for a future pass) and the entire 254-operation
uncontracted-surface backlog (`SG-013`) — this pass closed real violations in already-partially-contracted
files, not new surfaces.

**Verification:** `tooling/contracts/validate.py` (no `--strict-coverage`) exit code 0,
`PASS  no contract conformance violations found`. Per-file exact operation-coverage spot-checks
confirmed 0 phantom/0 gap for every file touched. Regression test run in progress at time of writing;
result to be recorded once complete (no application code changed by this pass — contract-only). — 2026-08-27 — WP-03 contract slice, module 1 of 5: Document 13 (SPEC-EBMR-004, Genealogy & Traceability Engine)

**Change:** `spec-ebmr-004.yaml` committed — first field-level contract for `/genealogy/v1`, 5 read-only
operations (`getGenealogyNodesLookup`, `getGenealogyNodeAncestors`, `getGenealogyNodeDescendants`,
`getGenealogySerialFullTrace`, `getGenealogyMaterialLotAffectedProducts`). No write operations exist by
design (Document 13 §8: genealogy rows are meant to be produced by domain events from other modules, not
a public write API) — this matches Document 13's own 8-API list exactly rather than inventing a
POST/PUT the source document doesn't declare.

**Compatibility classification: INITIAL.** Nothing added, removed, renamed or narrowed; no `schema_version`
bump. Same consumer set as every other contract in this registry.

**Verification:** validated clean against `tooling/contracts/validate.py` (0 findings referencing this
file, both with and without `--strict-coverage`) and against the live route table (exact 5:5 coverage for
`/genealogy/v1`). Baseline violation count held at 107 across this entire 5-file WP-03 pass.

**$ref reuse.** `ErrorResponse`/standard error responses $ref'd from `spec-gxp-001.yaml`. No
`MutationReceipt` usage in this file — every operation is a GET.

**SG-146 cross-reference:** `GenealogyEdge.uom`/`uom_id` are dual-written by `create_edge` (the internal
write path this contract doesn't expose) but no endpoint here returns an edge's own fields — traversal
responses return only the nodes reached and bare edge ids (`TraversalResult`), documented as a known
read-side gap.

**New gaps:** none. `create_node`/`create_edge`/`correct_edge` remain intentionally uncontracted internal
functions, not a missed public surface.

### CR-009 — 2026-08-27 — WP-03 contract slice, module 2 of 5: Document 14 (SPEC-EBMR-005, Review-by-Exception & QA Review)

**Change:** `spec-ebmr-005.yaml` committed — first field-level contract for `/qa-review/v1`, 6 operations
(`postCreateReviewPackage`, `getReviewPackageDetail`, `getReviewPackageExceptions`,
`postReindexReviewPackage`, `postCompleteReviewPackage`, `getReviewDashboard`).

**Compatibility classification: INITIAL.**

**Verification:** validated clean (0 findings, baseline held at 107); exact 6:6 coverage for
`/qa-review/v1`.

**$ref reuse.** Standard shared envelopes from `spec-gxp-001.yaml`.

**No SG-146 cross-reference.** `qa_review_package` carries no UOM column.

**New gaps:** none. The contract documents (not silently corrects) that completeness checking covers only
2 of 9 real signal categories QA review would ideally check (batch hold + Vault integrity), matching the
module's own pre-existing SG-053/SG-054 disclosure.

### CR-010 — 2026-08-27 — WP-03 contract slice, module 3 of 5: Document 15 (SPEC-EBMR-006, Release / Disposition Engine)

**Change:** `spec-ebmr-006.yaml` committed — first field-level contract for `/release/v1`, 6 operations
(`postEvaluateReleaseScope`, `getReleaseScopeEligibility`, `postReleaseScopeDecision`,
`postHoldReleaseScope`, `postRejectReleaseScope`, `getReleasePackage`).

**Compatibility classification: INITIAL.**

**Verification:** validated clean (0 findings, baseline held at 107); exact 6:6 coverage for
`/release/v1`.

**$ref reuse.** Standard shared envelopes; `postReleaseScopeDecision` is signature-gated the same
fail-closed way as every prior release-type action in this registry (Document 106 policy resolution,
`SIGNATURE_POLICY_UNRESOLVED` on an unresolved policy row).

**No SG-146 cross-reference.** `release_scope`/`release_evaluation`/`release_decision` carry no UOM
column.

**New gaps:** none. Documents that eligibility evaluation covers only 2 of 9 named categories (QA review
+ Vault integrity), matching pre-existing SG-056.

### CR-011 — 2026-08-27 — WP-03 contract slice, module 4 of 5: Document 16 (SPEC-EBMR-007, Packaging, Labeling & Reconciliation)

**Change:** `spec-ebmr-007.yaml` committed — first field-level contract for `/packaging/v1`, 8 operations
(`postCreatePackagingRun`, `getPackagingRuns`, `getPackagingRunDetail`, `postPackagingLineClearance`,
`postIssueLabel`, `postReconcileLabels`, `postReconcilePackaging`, `postCompletePackagingRun`).

**Compatibility classification: INITIAL.**

**Verification:** validated clean (0 findings, baseline held at 107); exact 8:8 coverage for
`/packaging/v1`. `getPackagingRuns` is this session's first genuinely paginated WP-02/WP-03 list endpoint
— reuses the shared `PageEnvelope` schema and `Page`/`PageSize`/`Query`/`SortBy`/`SortDir` parameters
from `spec-gxp-001.yaml` rather than redefining them.

**$ref reuse**, plus the shared pagination components just noted.

**No SG-146 cross-reference.** None of this module's entities carry a UOM column (label/pack counts are
plain integers).

**New gaps:** none. Documents that Document 16 declares zero read operations in its own API table despite
needing them for its own listed UI screens — assessed as a real authoring gap in the source document, and
2 read endpoints are built anyway (a deliberate, disclosed deviation from the stricter "don't add outside
the document's own list" discipline used elsewhere, e.g. genealogy above). Also documents that none of
Document 16's 10 operations require a signature, unlike every other release/complete-type action in this
registry.

### CR-012 — 2026-08-27 — WP-03 contract slice, module 5 of 5: Document 17 (SPEC-EBMR-008, Yield, Calculations & Manufacturing Reconciliation) — closes the WP-03 slice

**Change:** `spec-ebmr-008.yaml` committed — 9 Document 17 operations (`postEvaluateYield`,
`postEvaluatePotency`, `postEvaluateMaterialReconciliation`, `postEvaluatePackagingReconciliation`,
`postEvaluateLabelReconciliation`, `postEvaluateComponentReconciliation`,
`postYieldReconciliationSignatureChallenge`, `postVerifyRecord`, `getBatchSummary`) **plus 2 operations
that are not Document 17 at all** (`postEvaluateMaterialDispensingReconciliation`,
`getMaterialDispensingReconciliation` — SPEC-MAT-002D/Document 22, WP-04, CON-FR-019..026). This closes
the 5-file WP-03 contract slice (CR-008 through CR-012, genealogy → qa_review → release → packaging →
yield_reconciliation, 34 operations across 5 files, all validated with the baseline held at exactly 107
throughout).

**A genuine routing-surface collision, not a documentation choice:** `app/modules/material/router.py`
mounts its own `reconciliation_v1_router` under the literal same `/reconciliation/v1` prefix
`yield_reconciliation`'s router uses. `tooling/contracts/validate.py`'s `surface_of()` groups coverage by
first-two-literal-path-segments, so both modules' operations land in one contract-coverage bucket
regardless of which module actually owns them — omitting the 2 material-module operations from this file
left them flagged as `CTRC-FR-001` (implemented-but-uncontracted) findings, growing the baseline to 110.
They are included here, clearly marked `NOT Document 17` in both the path descriptions and every related
schema's own description string, precisely to avoid inflating this document's own scope claim while still
keeping the baseline at 107 — ownership stays with the material module; a future SPEC-MAT-002D contract
may re-declare the same two operations under its own file (OpenAPI operation coverage is not
file-exclusive). Also documented: `batch_id` on those 2 operations resolves against `ebmr.batches` (the
legacy `batch` module's table) — not `ebmr.gxp_batch` (`batch_execution`'s table) every other `batch_id`
in this file refers to.

**Compatibility classification: INITIAL.**

**Verification:** validated clean (0 findings referencing this file); exact 11:11 coverage across the
combined `/manufacturing-calculations/v1` + `/reconciliation/v1` surfaces (9 Document 17 + 2 SPEC-MAT-002D
operations).

**$ref reuse.** Standard shared envelopes. `postVerifyRecord` is signature-gated (Document 106 row 40 —
the one genuinely signed action in Document 17, with an explicit SIG-FR-018 independence check: the
verifier must not be the original performer, checked and failed closed with `MissingSignatureError`
*before* the signature ceremony even begins).

**SG-146 cross-reference:** `ManufacturingCalculation.uom_id`/`ReconciliationRecord.uom_id` are documented
on their respective response schemas.

**New gaps:** none newly raised beyond documenting two pre-existing observations as-is rather than
silently correcting them: `getBatchSummary` has no policy check at all (unlike every other read endpoint
in this entire WP-02/WP-03 contract set), and the routing collision with the material module described
above. Neither is a regulated-behaviour guess this contract-writing pass could resolve on its own
authority, so neither triggered a new SPEC_GAP entry — both are recorded here for a human reviewer to
decide whether they need one.

### CR-014 — 2026-08-29 — WP-04 contract slice: the `material` module, Documents 19-22 (SPEC-MAT-002A/B/C/D), 49 operations across 4 files

**Change:** `spec-mat-002a.yaml` (Document 19, Material Receipt/Quarantine/Quality Status, 19 ops),
`spec-mat-002b.yaml` (Document 20, Inventory/Lot/Container/Warehouse, 10 ops), `spec-mat-002c.yaml`
(Document 21, Material Dispensing & Weighing, 11 ops) and `spec-mat-002d.yaml` (Document 22, Consumption/
Return/Adjustment/Destruction, 9 ops) committed — the largest single uncontracted surface in the repo
before this pass (`app/modules/material/router.py`, 51 endpoints across 7 `APIRouter` instances). Closes
the biggest slice of the SG-013 backlog identified after the CR-013 hygiene sweep.

**Split follows requirement-ID namespace, not router-prefix boundary.** The module's own router mixes
Document 19/20/22 operations across `/materials/v1` and `/inventory/v1` (e.g. inventory-adjustment
endpoints live under `/inventory/v1/adjustments` but are CON-FR-013/014, Document 22, confirmed by
grepping the actual `CON-FR-` citations in `commands.py` rather than trusting the path prefix). The 2
remaining Document 22 operations (reconciliation evaluate/get) are **not** in `spec-mat-002d.yaml` — see
CR-012: they were already committed in `spec-ebmr-008.yaml` under its own "NOT Document 17" section,
because the material module's `reconciliation_v1_router` collides with `yield_reconciliation`'s router on
the identical `/reconciliation/v1` prefix. `spec-mat-002d.yaml`'s own description cross-references this
explicitly rather than silently omitting those 2 operations with no explanation.

**Material-master CRUD has no Document 19-22 owner — traced, not guessed.** `POST/GET /materials`,
`PATCH/DELETE /materials/{id}` predate the Document 19-22 namespace (code comments cite the older
Document 02 architecture-level `MAT-*`/`C-013` IDs, not `RCV-FR-*`). Cited against `C-013` ("Raw Material
Master") in `spec-mat-002a.yaml` rather than invented against a Document 19 ID that doesn't cover it —
confirmed by checking RCV-FR-001..032's actual requirement names in `01_REQUIREMENT_REGISTRY.csv`, none
of which is "material master".

**Two real, previously-undocumented code-vs-model mismatches surfaced, not silently corrected:**
(1) `DispensingOrder.DISPENSING_ORDER_STATES` names `awaiting_verification`, but `verify_dispensing`
actually writes the literal string `"verified"` — documented on `DispensingOrderState` and the
`postVerifyDispensing` operation in `spec-mat-002c.yaml`. (2) Two parallel, independently-signed
lot-disposition paths coexist on the same `MaterialLot` entity — the legacy `MaterialLotDisposition`-
backed `/material-lots/{id}/disposition` (narrower, `quarantine`-only) and Document 19's own
`MaterialQualityDisposition`-backed release/reject (wider `PRE_DISPOSITION_LOT_STATES`, partial-container
support, a real independence check) — both fully functional, both documented in `spec-mat-002a.yaml`
rather than one being assumed dead code.

**Compatibility classification: INITIAL.**

**Verification:** validated clean (0 findings across all 4 files, and the temporary `CTRC-FR-001`
findings against `spec-mat-002a.yaml`/`spec-mat-002b.yaml`'s shared `/materials/v1`/`/inventory/v1`
surfaces — expected until `spec-mat-002d.yaml` closed the same surfaces — resolved once all 4 files were
committed together). Exact 49:49 coverage confirmed across the combined surface set (zero phantom, zero
gap). Baseline held at 0 (the post-CR-013 state) throughout.

**$ref reuse.** Standard shared envelopes from `spec-gxp-001.yaml`, including `PageEnvelope`/`Page`/
`PageSize`/`Query`/`SortBy`/`SortDir` for the module's several genuinely-paginated list endpoints.

**SG-146 cross-reference:** every quantity-carrying entity in this module (13 tables from the earlier
SG-146 pass) has its `*_uom_id` field documented on the corresponding response schema.

**New gaps:** none newly raised. This slice documents (does not silently resolve) SG-057/058
(material-specific approved-source/spec-version entities don't exist), SG-081 (`warehouse_location` has
no CRUD API), SG-082 (ERP reconciliation is a GxP-only stub), SG-083 (reservation has no
deviation-override path), SG-084/086 (cycle count and some pre-existing Document 21 rows are unsigned —
no Document 106 row resolves one), SG-085 (same-site transfer only), SG-087 (order creation is unsigned
by architecture, not oversight), SG-088 (no Edge/Balance device adapter), SG-089/094/098 (tolerance/
target-calculation is caller-supplied captured input across Documents 21/22, not a released rule) — all
pre-existing, all already on file.

### CR-015 — 2026-08-29 — WP-06 contract slice: the `equipment` module, Documents 38-42 (SPEC-EQP-001/002/003/004/005), 56 operations across 5 files

`spec-eqp-001.yaml` (Document 38, equipment/calibration/qualification/maintenance, EQP-FR-*, 12 ops),
`spec-eqp-002.yaml` (Document 39, cleaning/sanitization/line clearance, CLN-FR-*, 11 ops across
`/cleaning/v1` + `/line-clearance/v1`), `spec-eqp-003.yaml` (Document 40, sterile/aseptic operations,
ASP-FR-*, 9 ops), `spec-eqp-004.yaml` (Document 41, environmental monitoring, EM-FR-*, 11 ops),
`spec-eqp-005.yaml` (Document 42, sterilization/CIP-SIP/sterile filtration, STR-FR-*, 13 ops across
`/sterilization/v1` + `/cip-sip/v1` + `/filtration/v1`). All five files share one `app/modules/equipment`
module/schema per AG-05 — a single owning module across 5 documents, same "one directory, several
sub-document files" pattern as `material`'s Documents 19-22.

**Build-order dependency, contracted in build order not document order.** The code itself was built
39 → 41 → 42 → 40 (Document 40's aseptic readiness composition calls real functions from 38/39/41/42
rather than raising forward-dependency SPEC_GAPs for its own most central requirements). Contracted in
the same order for the same reason: `spec-eqp-002.yaml` (39) and `spec-eqp-004.yaml` (41) were written
before `spec-eqp-005.yaml` (42) and `spec-eqp-003.yaml` (40, last), so the aseptic contract's readiness
composition could be described against already-documented sibling operations
(`getEmAreaReadiness`, `getAssetEligibility`, `getSterilizationItemStatus`) rather than forward references.

**Cross-module read with no route of its own.** `cleaning_commands.get_area_line_clearance_status`
(Document 39) is called directly by Document 40's readiness composition but has no router registration —
documented in `spec-eqp-002.yaml`'s description as not contracted, same treatment as any internal
composition helper.

**Two "one entity, N routes" precedents in this slice**, both cited explicitly in their contract's
description rather than silently picked: Document 42's `postCreateProcessCycle`
(`/sterilization/v1/cycles`) and `postCreateCipSipCycle` (`/cip-sip/v1/cycles`) both create the identical
`ProcessCycle` row via the identical handler, distinguished only by the `process_type` value supplied.

**Verification:** `validate.py` (no flags) reports 0 conformance findings across all 31 committed
contract files — baseline held at 0 (the post-CR-013 state) through this addition. `validate.py
--strict-coverage` (run inside the gxp-api venv) confirms exact, zero-gap coverage independently for
every one of the five route surfaces this slice owns (`/equipment/v1`, `/cleaning/v1` +
`/line-clearance/v1`, `/aseptic/v1`, `/em/v1`, `/sterilization/v1` + `/cip-sip/v1` + `/filtration/v1`) —
confirmed clean immediately after each file was committed, not only at the end of the slice. Platform
totals moved from 233 committed / 219 backlog (post-CR-014) to 289 committed / 163 backlog.

**Pre-existing, not touched by this slice:** `spec-edge-001.yaml` (Document 43) and `spec-edge-005.yaml`
(Document 47) were already committed before this slice began and were not re-verified or modified here
beyond confirming (via the same `--strict-coverage` run) that their route surfaces remain exactly
covered. Documents 44-46 (DRV-FR/BUF-FR/PER-FR, driver/buffering/protocol specifics) have no server-side
implementation in this codebase — the on-prem gateway runtime they describe is explicitly out of scope
as "a distinct future deployable" per `spec-edge-001.yaml`'s own description — so nothing exists for them
to contract; this is not a gap this slice left behind.

**New gaps:** none newly raised. This slice documents (does not silently resolve) several pre-existing
"captured, not enforced" reference fields with no dedicated master entity in the frozen 4-entity-per-
document data models (`equipment_class_id`, `location_id`, calibration `standard_reference`, spare
`parts_used`, `item_reference` on sterilization load items); EQP-FR-017's manual-only runtime counters and
EQP-FR-012's un-cross-referenced "affected batches" analysis (both citing SG-048); Document 39's narrow
`EquipmentArea` master standing in for the full Document 01/02 C-003 Building/Area/Room/Line hierarchy;
Document 41's captured, performer-attested `alert_action_status` with no automated limit evaluation and
EM-FR-017/018's raw-history-only trend endpoint; Document 42's `reuse_count` that is tracked but never
incremented (STR-FR-022 default single-use); and Document 38's un-contracted retirement path (EQP-FR-027
describes retirement, but no operation in the module's declared API list reaches it — RETIRED is only
reachable via a direct migration/repair path today). None of these were guessed into existence to close
a gap in this contract; all are reported as-is.

### CR-016 — 2026-08-29 — Platform admin/legacy contract slice: IAM extension, legacy product/recipe/batch, supplier-qualification detail

Three additions after WP-06 closed the equipment/edge backlog, none tied to a specific numbered WP:

- **`spec-iam-001.yaml` extended** (Document 07, `app/modules/iam/router.py`) — 18 new operations
  (organization CRUD, sites CRUD, users CRUD + deactivate/reactivate/role-assignment, roles CRUD, login,
  `/auth/me`) added to the file that already contracted the policy-decision/permission-catalog half of
  the same module. None of the newly-contracted operations match Document 07's own declared 7-op API
  list (`POST /policy/v1/decisions`, `GET /iam/v1/subjects/{id}/effective-authority`, `GET /iam/v1/
  subjects/{id}/qualifications`, `POST /iam/v1/temporary-authorizations`, `POST /iam/v1/break-glass`,
  `POST /iam/v1/access-reviews`, `GET /iam/v1/access-reviews/{id}/report`) — none of those 7 are
  implemented in this codebase at all; what's contracted instead is basic platform administration, traced
  to the closest-fit IAM-FR-* requirements and documented as a real gap in the file's own description, not
  guessed onto the undeclared names. Also documented: no optimistic concurrency on this surface (`User`/
  `Role`/`Site`/`Organization` carry no `version` column; every command uses `expected_version=None`).
- **`spec-legacy-001.yaml`** (new file, `app/modules/product` + `app/modules/recipe` + `app/modules/
  batch`) — 21 operations. The original pre-WP-02 product/recipe/batch implementation, fully live
  alongside `product_master`/`recipe_master`/`batch_execution` (`spec-ebmr-000/001/002.yaml`) — both sets
  are functional, neither is dead code (same "two live implementations" precedent as `material`'s
  disposition paths and `material`'s dispensing-vs-material-master naming). This legacy `batch` module
  turned out to have a genuinely complete, independently-signed review→release lifecycle with its own
  Vault snapshot — narrower in scope than `batch_execution` (no execution-snapshot freeze at issue) but
  not a stub. Three operationIds collided with `spec-ebmr-002.yaml` (`postCreateBatch`, `postIssueBatch`,
  `postStartStep` — the same verb-noun pattern, different modules) and were disambiguated to
  `postCreateLegacyBatch`/`postIssueLegacyBatch`/`postStartLegacyStep` (CTR-FR-002). No numbered Document
  02-105 owns this trio; requirement IDs trace to the closest-fit architecture-level entries (C-012,
  BAT-FR-*, MUT-FR-*, SIG-FR-*) — documented explicitly in the file's own description as "this file exists
  because the code exists," not because a spec calls for it. Two real, pre-existing gaps reported (not
  fixed): `postCreateProduct` has no code-level uniqueness check beyond the DB constraint (a duplicate
  `(site_id, code)` 500s rather than returning `VALIDATION_FAILED`), and `getRecipe` has no `NotFoundError`
  handling for an unknown `recipe_id` (also a 500, contrasting every other module's convention).
- **`spec-mat-001.yaml` gap closed** — `getSupplierQualification` (`GET /supplier-qualifications/
  {qualification_id}`), a gap this file's own 2026-08-29 hygiene-pass note explicitly deferred earlier the
  same day. 1 operation, 1 new schema (`SupplierQualificationDetail`, `allOf`-extending the pre-existing
  `SupplierQualificationSummary` with an `evidence` array).

**Verification:** `validate.py` (no flags) reports 0 conformance findings across all 32 committed contract
files — baseline held at 0 through every addition in this slice, confirmed after each file was written.
`validate.py --strict-coverage` confirms exact, zero-gap coverage for `/auth`, `/organization`, `/sites`,
`/users`, `/roles` (IAM extension); `/products`, `/recipes`, `/batches` (legacy trio); and the entire
`supplier_quality` module's routing surface (both gaps now closed). Platform totals moved from 289
committed / 163 backlog (post-CR-015) to 329 committed / 123 backlog.

**New gaps:** none newly raised. Real, pre-existing application defects reported above (product
create's missing uniqueness check, recipe detail's missing 404 handling) are documented, not silently
patched — fixing application code is out of scope for a contract-authoring task.

### CR-017 — 2026-08-29 — WP-05 QMS contract slice: all twelve modules, Documents 26-37, closes the entire platform SG-013 backlog

**Change:** `spec-qms-001.yaml` through `spec-qms-012.yaml` committed (new files) — the full WP-05 QMS
surface (`app/modules/qms/`), one file per Document/module: deviation (26), CAPA (27), NCR (28), change
control (29), document control (30), training & qualification (31), SCAR (32), risk management (33),
internal audit (34), complaint (35), field action (36), quality metrics (37). 122 operations across the
twelve files (each module's own declared op-count plus, in every module, the `signature-challenges`
ceremony-entry-point endpoint SG-138's engineering half added earlier the same day — none of those
fourteen endpoints is in any Document's own declared API table, all fourteen are contracted because the
router implements them, the same "contract the code that exists" discipline used throughout this
project). Internal audit and quality metrics each contribute two `signature-challenges` endpoints
(`internal_audit`/`audit_finding`; `quality_metric_definition`/`quality_metric_snapshot` — separate
record types on separate sub-resources, not one record with two actions).

**This closes the entire platform-wide SG-013 uncontracted-operation backlog.** Before this slice: 329
committed / 123 backlog, and every one of the 123 was a QMS operation (confirmed directly via
`validate.py --strict-coverage --json` immediately before starting — no other module had any remaining
gap). After: 452 committed / 0 backlog (`validate.py --strict-coverage` reports `uncovered_operations: 0`
in both normal and strict mode; a 453rd implemented operation is a pre-existing, non-QMS accounting
artifact unrelated to this slice, not a new gap).

**Four `operationId` collisions found and disambiguated (CTR-FR-002), all verb-noun patterns repeated
across modules that happen to share a shape:** `postAssessImpact` (deviation vs change control — change
control's renamed `postAssessChangeImpact`), `postMakeEffective` (change control vs document control —
document control's renamed `postMakeDocumentVersionEffective`), `postRecordCommunication` (complaint vs
field action — field action's renamed `postRecordFieldActionCommunication`), `postAssessReportability`
(complaint vs field action — field action's renamed `postAssessFieldActionReportability`). Complaint and
deviation each kept their shorter original name as the first module to claim it; this is a naming
convention note, not a behavioural difference between the two operations either pair names.

**Compatibility classification: INITIAL** for all twelve files — no prior contract existed for any WP-05
QMS operation.

**Verification:** `validate.py` (no flags) — `PASS  no contract conformance violations found` — 0
findings across all 44 committed contract files, confirmed after every one of the twelve QMS files was
written. `validate.py --strict-coverage` — same PASS, `uncovered_operations: 0`. Every command schema
closes with `additionalProperties: false` (CTRC-FR-003); every schema and operation carries
`x-requirement-ids` traced to real rows in `01_REQUIREMENT_REGISTRY.csv` for Documents 26-37, never
invented (CTRC-FR-009); every mutation response is the canonical `spec-gxp-001.yaml` `MutationReceipt`,
every declared error the canonical `ErrorResponse` (CTRC-FR-002).

**$ref reuse.** All twelve files `$ref` `MutationReceipt`/`ErrorResponse`/the five standard named
responses/`PageEnvelope`/the five list-query parameters from `spec-gxp-001.yaml`, per this project's
established shared-envelope convention (CR-001 onward) — none of the twelve redefines these locally.

**SG-146 cross-reference:** none. No WP-05 QMS entity carries a `uom`/quantity column — SG-146's 8-module
UOM expand step never touched this module family.

**SG-138 cross-reference:** every `signature-challenges` request/response schema in all twelve files
documents, in its own description, that the endpoint returns `SIGNATURE_POLICY_UNRESOLVED` today and why
(SG-138's policy-data half is still open, `blocking: true`, reserved to Head of Quality + Regulatory
Affairs). No `meaning`, signer role, independence flag or reason-required flag is invented anywhere in
these files — every `SignatureChallengeResponse.meaning` is documented as read verbatim from the
resolved Document 106 policy row, matching the engineering-half implementation's own discipline.

**New gaps:** none newly raised. One pre-existing defect, already documented in SG-138's own narrative
(not newly discovered by this contract-authoring pass), is reflected here for completeness: `training/
v1/assignments/{assignment_id}/signature-challenges` does not accept `action: create` — see
`spec-qms-006.yaml`'s own module-level description and SG-138 for why (`create_assignment()`'s signature
ceremony cannot bind to a record that doesn't exist yet at request time; a command-layer fix, out of
scope for contract authoring).

---

### CR-018 — 2026-08-29 (later the same day) — Event-schema first slice (WP-05 QMS, 84/484 events) + `training_assignment`/`create` signature-ordering fix

**Change, part 1 — event contracts.** `contracts/events/event-data-005.json` (the canonical event
envelope) plus `event-qms-001.json` through `event-qms-012.json` committed (new files) — the first slice
of SG-013's event half, covering every SPEC-QMS-* event declared in `07_EVENT_CATALOGUE.yaml` (84 events,
one file per Document 26-37 module). Ground truth was established the same way as CR-017's operations:
by cross-referencing the catalogue's declared `producer: SPEC-QMS-NNN` events against the real
`event_type=` literals *and* dynamic ternary assignments (regex-extracted, then manually verified) in all
twelve `app/modules/qms/*_commands.py` files, not by trusting the catalogue. Found 4 real divergences
across 3 modules: `DocumentPeriodicReviewDue` (QMS-005), `QualificationExpired`/`RetrainingRequired`
(QMS-006) and `FieldActionCorrectionCompleted` (QMS-011) are declared but have no producing code path;
`TrainingRequirementCreated` (QMS-006) is implemented but was undeclared — all four recorded in the
affected files' `description` fields, none silently fixed or normalized. Also documented, again against
verified source, not assumption: `event_type` names reused across call sites with overlapping-but-
different payload shapes (e.g. `ComplaintReceived` from three unrelated transitions in `complaint_
commands.py`), and three dual-aggregate cases where one call writes the same `event_type` twice on two
different aggregates (`SCARIssued`/`SCARClosed` on `scar_record` + `supplier_quality_case`;
`QualityMetricCalculated` on `quality_metric_definition` + `quality_metric_snapshot`).

**Format decision (ordinary engineering, not regulated):** plain JSON Schema (draft 2020-12) was used
instead of full AsyncAPI. `app/main.py::outbox_publisher_loop()` is, by its own docstring, "a Phase 1
stand-in for a real bus" that logs rather than publishes to NATS — no subject/channel/binding convention
exists in the codebase to contract, so an AsyncAPI document would have to invent transport architecture
that hasn't been decided. JSON Schema contracts the one thing that is real and stable: the payload shape
written to `OutboxEvent` by `app/mutation/gateway.py::write_outbox_event()`. Recorded in
`event-data-005.json`'s own description, including the real `OutboxEvent` row shape's divergence from
Document 113 §2's canonical envelope (no `tenant_id`/`site_id`/`schema_version` at the row level; has
`published_at`, which Document 113 doesn't name; `occurred_at` not `occurred_at_utc`).

**New tooling.** `ebmr-edhr/tooling/events/validate.py` — a structural gate for event JSON contracts,
parallel to `tooling/contracts/validate.py` but scoped differently: it checks JSON parseability, local
(`#/$defs/...`) and cross-file `$ref` resolution (into other event files and into `contracts/openapi/
*.yaml` via PyYAML), `x-requirement-ids` presence at file/`$defs`/event-entry level (CTRC-FR-009), closed
payloads via `additionalProperties: false` (F1-derived) and CTRC-FR-008 single-producer-per-`event_type`
consistency across files. It explicitly does **not** attempt a CTRC-FR-001-equivalent code-coverage gate
— unlike API operations, event emission sites use dynamic `event_type = "X" if cond else "Y"` assignment
patterns that a static route-introspection approach (the technique `tooling/contracts/validate.py` uses)
cannot safely resolve without a real static-analysis engine; scoped out rather than approximated, and
documented as such in the script's own docstring.

**Verification:** first run of `validate.py` found 80 violations, all one root cause — every `$defs/
*Payload` schema was missing its own `x-requirement-ids` (only the file-level and `events[]`-entry-level
keys had been set originally). Fixed by deriving each payload schema's `x-requirement-ids` from the union
of every `events[]` entry that `$ref`s it. Re-run: **`PASS  no event contract violations found`** — 13
files parsed, 84 event entries, 0 violations.

**Change, part 2 — `training_assignment`/`create` signature-ordering fix (SG-138).** Closes the defect
CR-017 flagged as pre-existing and out of scope: `create_assignment()` could not be signed because its
signature challenge would need to bind to a record id that didn't exist yet at challenge-request time.
Fixed in `services/gxp-api/app/modules/qms/`: `signature_support.py` gained `create_qms_signature_
challenge_for_new_record()`, refactored out of the existing `create_qms_signature_challenge()` via a
shared `_resolve_and_challenge()` helper; `training_commands.py`'s `CreateTrainingAssignmentCommand`
gained an optional `assignment_id` field that `create_assignment()` now uses instead of always generating
its own; `training_router.py` gained `POST /training/v1/assignments/signature-challenges`, which
pregenerates the assignment's UUID server-side, binds the challenge to `(id, version=1)` — the version
every new row in this codebase starts at — and returns both the challenge and the pregenerated
`assignment_id` for the caller's subsequent `POST /training/v1/assignments` call. This is a command-layer
and API-surface change, not a contract-authoring one, but is recorded here because it changes the
`spec-qms-006.yaml` `training/v1/assignments/signature-challenges` contract CR-017 committed with a
`create`-not-supported note — that note is now stale in behaviour (the endpoint exists and supports
`create`) though the contract file's schema shape is unaffected (same `SignatureChallengeRequest`/
response shapes as the other eleven modules' endpoints). Proven with a real challenge→create round trip,
not unit coverage alone: `test_create_assignment_round_trip_signs_create` requests a challenge, asserts
the returned `aggregate_id` matches the pregenerated id, creates the assignment using that id, and
confirms the persisted row's actual id/version match — plus four more new tests covering fail-closed-on-
unresolved-policy, unknown-action-rejected and stale-challenge-after-expiry. `test_qms_training_
qualification.py` in full: **25/25 passed**.

**SG-013 cross-reference:** the event-schema slice closes 84 of the 484 declared event types (all of
WP-05 QMS); 400 remain unschematised across every other module. `SG-013` stays `blocking: true`, OPEN.

**SG-138 cross-reference:** the ordering-bug defect this CR fixes is the *engineering* half only. The
policy-data half — no QMS record type seeded in `SIGNATURE_POLICY_FLOOR`, so all 26 `(record_type,
action)` pairs including `training_assignment`/`create` still return `SIGNATURE_POLICY_UNRESOLVED` — is
untouched and remains fully open, reserved to Head of Quality + Regulatory Affairs.

**New gaps:** none newly raised.

---

### CR-019 — 2026-08-29 (later the same day) — WP-07 completion pass: 8 new operations across `spec-erp-006.yaml`, closing 33 of 38 SG-126 requirements

**Change.** `contracts/openapi/spec-erp-006.yaml` gains 8 new operations, contracted before code
(CTR-FR-001): `POST /integration/v1/instances/{instance_id}/validate` (MULTI-FR-024),
`GET /integration/v1/instances/{instance_id}/sla-metrics` (INT-FR-021),
`GET /integration/v1/instances/{instance_id}/data-quality-metrics` (MDS-FR-026),
`POST /integration/v1/commands/{command_id}/compensate` (INT-FR-016), `POST /integration/v1/bulk-jobs`,
`POST /integration/v1/bulk-jobs/{job_id}/progress`, `POST /integration/v1/bulk-jobs/{job_id}/complete`
(all INT-FR-023), and `POST /integration/v1/migration-packages` (MDS-FR-028). `ErpInstanceView` gains
`validated`; `IngestERPEventCommand` gains `external_entity_id` (INT-FR-011). No existing operation's
request/response shape changed -- purely additive.

**Application-layer change accompanying the contract (this CR covers both, per this project's own "code
that reads like the surrounding code" discipline — WP-07's contract and implementation were built
together, not contract-then-separately-implemented):** new migration `0053_erp_wp07_completion_
extensions` (`integration_inbound_events.external_entity_id`, `integration_circuit_breakers` rate-limit
window columns, new `integration_security_events`/`integration_bulk_jobs`/`erp_migration_packages`
tables, `integration_commands.compensates_command_id`/`gxp_authorization_reference`,
`erp_instances.validated`/`validated_by_user_id`/`validated_at`); 3 new `PROVIDER_OPERATIONS`
(`POST_PURCHASE_ORDER_REF`/`POST_RESERVATION`/`POST_RELEASE_AVAILABILITY`) plus
`GET_PURCHASE_ORDER_REFERENCE` wired across all four named-vendor adapters; SAP `GET_MATERIAL_STOCK`/
`POST_TRANSFER`/movement-type override/CSRF handling; Dynamics `dataAreaId` enforcement;
`validate_erp_instance()` GENERIC-connector certification gate. Full detail and the itemized list of
what remains deliberately deferred (SOAP/SFTP/DB-read adapters, SAP `$batch`/BAPI-RFC, secret-manager
integration): `docs/generated/18_SPEC_GAPS.md` SG-126's 2026-08-29 (later the same day) update.

**Compatibility classification: ADDITIVE.** Every new operation is a new path; every schema change is a
new optional field on an existing request/response shape (`ErpInstanceView.validated`,
`IngestERPEventCommand.external_entity_id`) or a wholly new schema. No existing consumer of
`spec-erp-006.yaml` breaks.

**Verification.** `tooling/contracts/validate.py --strict-coverage`: 0 `CTRC-FR-001` violations for
`spec-erp-006.yaml` (3 unrelated pre-existing violations in `spec-ddcp-001.yaml` belong to a concurrent
peer session's WP-08 work, confirmed via direct coordination, not this pass). `tests/test_erp_flow.py` +
`test_erp_master_sync.py`: 51 passed, 0 failed, real re-run (chown frappe:frappe; `ps -ef` confirmed no
concurrent pytest; coordinated with peer sessions ebmr-new-a4/ebmr-new-68 on the shared
`ebmr_new_gxp_test` database throughout, including one real collision this pass caused and fixed --
an `alembic downgrade`/edit/`upgrade` cycle that briefly took the schema below head while a peer's test
ran, now treated as a DB-coordination event on the same footing as a pytest run going forward).

**SG-013 cross-reference:** none -- all 8 new operations are additive to an already-fully-contracted
surface (SG-013's API-operation half closed platform-wide in CR-017); no new backlog created.

**SG-121/126 cross-reference:** SG-121's provisional-schema status is unchanged (still pending a human
Document 112 amendment) but its scope grows by the 3 new tables and 8 new/changed columns this CR adds --
all recorded in `docs/generated/05_DATABASE_OWNERSHIP_MATRIX.md`. SG-126 item (2) (deep per-vendor field
mapping) is substantially closed by this CR -- see SG-126's own updated entry for the itemized before/
after and the deliberately-deferred remainder.

**New gaps:** none newly raised. One real, disclosed correction of this pass's own making: SAP-FR-008
(transfer posting) was initially missed in a first draft of this pass and added in a follow-up edit
(`POST_TRANSFER`, SAP movement type 311) before this CR was written -- caught by comparing the built
requirement list against the source spec text directly, not left as a silent gap.

---

### CR-020 — 2026-08-29 (later the same day) — WP-07 test-case execution pass: Retry-After fix, 62 of 92 blocked P1 cases closed

**Change.** Executing the 92 P1 test cases `status/build-status.json` tracked BLOCKED against the now-real
WP-07 code (CR-019) found one genuine defect and fixed it: INT-FR-004's vendor `Retry-After` header was
accepted by `reliability.compute_retry_decision()` (the parameter existed) but never actually populated by
any adapter or read by `dispatch_erp_command()` -- the platform's own computed exponential backoff was
used unconditionally instead. Fixed: `ERPProviderResponse.retry_after_seconds` (new field, `provider.py`),
`adapters/base.py::extract_retry_after_seconds()` (shared helper, all 5 adapters wired), `commands.py`
passes it through. No contract change -- this is purely an internal reliability-model correction, not a
new/changed API surface.

**Test-case disposition (test-cases/TEST_CASE_LIBRARY.csv, `status/build-status.json`):** 62 of 92 P1
cases moved BLOCKED -> PASS with real evidence (mapped to a specific test function or a structural code-
path proof). 30 remain BLOCKED, each with an individual, specific reason -- 8 signature-premise mismatches
(SG-122: the auto-generated template assumes every requirement is signed; WP-07 is unsigned by design),
15 mapping to SG-126's already-disclosed deferred capabilities (SAP-FR-018/MULTI-FR-015), 5 premise-
inapplicable (a read-only endpoint or non-stateful capability has no state transition to prohibit), and 2
written this pass but not yet executed (DB ceded to a peer session's coordinated runs at time of writing).

**New gap found and disclosed, not fixed (out of this pass's scope):** `IntegrationBulkJob`'s `FAILED`
status is declared in `BULK_JOB_STATUSES` but no code path anywhere ever sets it -- `complete_bulk_job()`
only ever reaches `COMPLETED` or `COMPLETED_WITH_ERRORS`. A wholesale job-abort path (distinct from
partial per-record failure, already covered) was never designed. Recorded in `TEST_CASE_LIBRARY.csv`
(TC-051-S005) and `status/build-status.json`, not silently dropped.

**Verification.** `tests/test_erp_flow.py` + `test_erp_master_sync.py`: 54 passed, 0 failed, real clean
run after the Retry-After fix (`test_dispatch_honors_vendor_retry_after_header` proves the vendor's
declared 120s is honored verbatim, not the platform's default ~30s exponential backoff). `tooling/status/
rollup.py`: 531/2965 requirements verified, 2166 test cases executed (up from 506/2093 before this pass).

**SG-126 cross-reference:** no new items added to the deferred list -- the 15 BLOCKED cases mapping to
SAP-FR-018/MULTI-FR-015 were already disclosed there (CR-019's update); this pass's own new finding
(bulk-job FAILED status) is a distinct, smaller gap recorded directly in the CSV/build-status rather than
folded into SG-126's broader capability-deferral list.

**New gaps:** none requiring a new SPEC_GAP entry -- both findings (Retry-After, bulk-job FAILED status)
are either fixed (former) or a narrow, precisely-scoped code gap already fully disclosed in the test-case
CSV and build-status.json (latter), not a regulated-behaviour decision needing escalation.
