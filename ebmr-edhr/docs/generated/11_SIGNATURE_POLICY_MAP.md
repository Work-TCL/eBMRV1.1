# 11 — Signature Policy Map

**Package:** eBMR / eDHR Claude Code Construction Package  
**Status:** Proposed implementation-ready construction artifact / Ready for Review  
**Specification baseline:** Documents 01–105, baseline date 2026-08-20  
**Purpose:** Which actions require a Part 11 signature, with meaning, signer class and binding (Doc 04, Doc 88).

---

## Controlled signature meanings (Doc 04 SIG-FR-003)

`Performed`, `Verified`, `Reviewed`, `Approved`, `Released`, `Rejected`, `Authored`, `Witnessed`, `customer-approved extensions`

## Mandatory ceremony (Doc 04 SIG-FR-005..SIG-FR-014)

```text
server-side challenge (challenge_id, signer, tenant/site, record_id, version/hash, meaning, nonce, expiry)
  ↓ fresh step-up authentication (session alone is never sufficient — SIG-FR-006/008)
  ↓ capture issuer, subject, auth time, AMR/ACR, session ref
  ↓ bind record id + version + hash + action + meaning (SIG-FR-010/011)
  ↓ single-use nonce; expiry; invalidate on record change (SIG-FR-012/013/014)
  ↓ signature record → commit through Mutation Gateway
```

## Candidate signature points identified in the baseline

These are the actions whose specification text indicates approval/release/verification semantics. The **required meaning, signer role, signature count and order for each action is a configured, validated policy** (SIG-FR-004); the baseline does not fix the default values → **SG-004**.

| Action / API | Module | Indicated semantics | Meaning (to be approved) | Signer class | Binding |
|---|---|---|---|---|---|
| `POST /signature/v1/challenges` | SPEC-GXP-002 | sign | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /signature/v1/challenges/{id}/verify` | SPEC-GXP-002 | sign, verify | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /signature/v1/signatures/{id}/consume` | SPEC-GXP-002 | sign | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /vault/v1/masters/{type}/{businessId}/release` | SPEC-GXP-004 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /iam/v1/temporary-authorizations` | SPEC-IAM-001 |  | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /rules/v1/{ruleId}/release` | SPEC-GXP-006 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /products/v1/drafts/{id}/release` | SPEC-EBMR-000 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /recipes/v1/drafts/{id}/release` | SPEC-EBMR-001 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /batches/{id}/steps/{stepId}/verify` | SPEC-EBMR-002 | verify | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qa-review/v1/items/{id}/disposition` | SPEC-EBMR-005 | disposition | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /release/v1/scopes/{type}/{id}/evaluate` | SPEC-EBMR-006 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /release/v1/scopes/{id}/release` | SPEC-EBMR-006 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /release/v1/scopes/{id}/hold` | SPEC-EBMR-006 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /release/v1/scopes/{id}/reject` | SPEC-EBMR-006 | reject, release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /release/v1/scopes/{id}/rework` | SPEC-EBMR-006 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /release/v1/scopes/{id}/reprocess` | SPEC-EBMR-006 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /release/v1/scopes/{id}/destroy` | SPEC-EBMR-006 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /reconciliation/v1/{id}/verify` | SPEC-EBMR-008 | verify | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /supplier-qualifications/{id}/approve` | SPEC-MAT-001 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /materials/v1/lots/{id}/release` | SPEC-MAT-002A | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /materials/v1/lots/{id}/reject` | SPEC-MAT-002A | reject | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /inventory/v1/reservations/{id}/release` | SPEC-MAT-002B | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /dispensing/v1/orders/{id}/verify` | SPEC-MAT-002C | verify | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /inventory/v1/adjustments/{id}/approve` | SPEC-MAT-002D | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qc/v1/specifications/{id}/release` | SPEC-QC-001 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /quality/oos/v1/{id}/disposition` | SPEC-QC-003 | disposition | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /quality/oos/v1/{id}/close` | SPEC-QC-003 | close | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /quality/oot/v1/{id}/close` | SPEC-QC-003 | close | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/deviations/{id}/disposition` | SPEC-QMS-001 | disposition | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/deviations/{id}/close` | SPEC-QMS-001 | close | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/capas/{id}/close` | SPEC-QMS-002 | close | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/nonconformances/{id}/disposition` | SPEC-QMS-003 | disposition | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/nonconformances/{id}/verify` | SPEC-QMS-003 | verify | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/nonconformances/{id}/close` | SPEC-QMS-003 | close | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/changes/{id}/approve` | SPEC-QMS-004 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/changes/{id}/verify` | SPEC-QMS-004 | verify | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/changes/{id}/close` | SPEC-QMS-004 | close | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /documents/v1/drafts/{id}/release` | SPEC-QMS-005 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /training/v1/assignments` | SPEC-QMS-006 | sign | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /training/v1/assignments/{id}/complete` | SPEC-QMS-006 | sign | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /training/v1/assignments/{id}/assess` | SPEC-QMS-006 | sign | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/scars/{id}/close` | SPEC-QMS-007 | close | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/findings/{id}/verify` | SPEC-QMS-009 | verify | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/audits/{id}/close` | SPEC-QMS-009 | close | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/complaints/{id}/close` | SPEC-QMS-010 | close | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/field-actions/{id}/approve` | SPEC-QMS-011 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /qms/v1/field-actions/{id}/close` | SPEC-QMS-011 | close | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /quality-metrics/v1/definitions/{id}/release` | SPEC-QMS-012 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /cleaning/v1/executions/{id}/verify` | SPEC-EQP-002 | verify | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /postmarket/v1/signals` | SPEC-PM-001 | sign | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /postmarket/v1/signals/{id}/assessments` | SPEC-PM-001 | sign | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /postmarket/v1/signals/{id}/escalations` | SPEC-PM-001 | sign | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /regulatory/v1/reports/{id}/approve` | SPEC-PM-002 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /security/v1/privileged-access/requests/{id}/approve` | SPEC-SEC-003 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /security/v1/privileged-sessions/{id}/close` | SPEC-SEC-003 | close | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /security/v1/incidents/{id}/close` | SPEC-SEC-007 | close | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/master-plans/{id}/release` | SPEC-VAL-001 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/function-risks/{id}/approve` | SPEC-VAL-002 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/tests/{id}/approve` | SPEC-VAL-004 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/iq/executions/{id}/approve` | SPEC-VAL-005 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/oq/{id}/approve` | SPEC-VAL-006 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/pq/{id}/approve` | SPEC-VAL-007 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/infrastructure/{id}/approve` | SPEC-VAL-008 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/migrations/{id}/approve` | SPEC-VAL-009 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/part11/{id}/approve` | SPEC-VAL-010 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/data-integrity/{id}/approve` | SPEC-VAL-011 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/interfaces/{id}/approve` | SPEC-VAL-012 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/dr/{id}/approve` | SPEC-VAL-013 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/security/{id}/approve` | SPEC-VAL-014 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/exceptions/{id}/disposition` | SPEC-VAL-016 | disposition | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/summary-reports/{id}/approve` | SPEC-VAL-017 | approve | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/releases/{id}/authorize` | SPEC-VAL-017 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |
| `POST /validation/v1/releases/{id}/deployment-check` | SPEC-VAL-017 | release | **UNRESOLVED (SG-004)** | **UNRESOLVED (SG-004)** | record_id + version + hash + meaning |

**Candidate signature points identified:** 73

## Prohibitions

- Service, integration or device identity may never create a human signature (SIG-FR-023).
- Signatures are never delegated (SIG-FR-022).
- Historical signatures are never deleted; superseded versions keep their signatures (SIG-FR-028).
- Signature time is server-assigned UTC (SIG-FR-025).
- Login/MFA alone is not a signature (AG-07).
