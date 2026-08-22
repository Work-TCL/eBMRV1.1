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
