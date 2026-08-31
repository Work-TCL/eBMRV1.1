# US eBMR / eDHR Regulated Manufacturing Platform
## Document 106 — Electronic Signature Policy Baseline & Signature Point Register — v1.0 APPROVED

**Specification ID:** SPEC-GXP-007
**Status:** APPROVED v1.0 (construction baseline) — approvers of record: Head of Quality, Regulatory Affairs and Product Owner
**Closes:** SG-004
**Approval:** Approved by the Project Owner during construction review on 2026-08-21. A formal Part 11 signature record must be captured in the QMS against this version before validated release; the approval block below is the record of the construction decision.

**Primary Dependencies:** Document 04 (Part 11 Electronic Signature), Document 07 (Identity/RBAC/Qualification/SoD), Document 03 (Mutation Gateway), Document 88 (Part 11 validation), Document 01 §6
**Baseline:** Documents 01–105, 2026-08-20

---

# 0. Why this document exists

Document 04 specifies the **signature mechanism** completely: challenge creation, fresh step-up authentication, record/version/hash binding, meaning binding, nonce and expiry, invalidation on record change, manifestation, multi-signature ordering and independence. Document 04 SIG-FR-004 then states that a **record/action policy** defines *which* action requires a signature, *which meaning*, *which signer class*, *how many* signatures and *in what order*.

No document in the 01–105 baseline supplies those policy values. An implementation agent therefore cannot know whether `POST /qms/v1/deviations/{id}/close` requires a signature, and if so with what meaning and by whom. Inferring it from an endpoint name would be inventing regulated behaviour, which is prohibited.

This document supplies a **proposed platform signature policy baseline**: a floor that a customer may tighten but not weaken, plus the complete register of signature points compiled from the specifications.

# 1. Objective and non-goals

**Objective.** Define (a) the signature policy data model, (b) the platform-default policy for every signature point, (c) the resolution algorithm the Mutation Gateway uses at runtime, and (d) the validation evidence required for each.

**Non-goals.** This document does not change the signature ceremony (Document 04 owns it), does not define authentication factors (Document 62 owns them), and does not replace a customer's procedural decision to require more signatures than the platform floor.

# 2. Scope

In scope: every state-changing regulated operation exposed by Documents 03–60 and the postmarket submission actions in Documents 58–60.

Out of scope: read operations, configuration changes that are not regulated records, and internal service-to-service calls that do not change regulated state.

# 3. Policy principles (proposed)

| # | Principle | Rationale |
|---|---|---|
| P1 | A signature is required when the action **creates, approves, verifies, releases, rejects, corrects or closes** a predicate-rule record. | §11.10(e), §211.186/§211.188, §820.40/§820.181 record approval expectations. |
| P2 | A signature is **not** required merely because an action is audited. Audit is universal; signature is selective. | Prevents signature fatigue, which is itself a data-integrity risk. |
| P3 | The platform default is a **floor**. Customer configuration may add signatures, raise the signer class or add independence. It may never remove a floor signature. | Platform validation baseline must remain valid across deployments. |
| P4 | Every signature meaning comes from the controlled catalogue in SIG-FR-003. Free-text meanings are prohibited. | Manifestation and export must be deterministic. |
| P5 | Independence is evaluated **at signature completion time**, not at challenge creation time. | The signer set can change between challenge and completion. |
| P6 | Where an action both performs and verifies, the platform requires two distinct signatures, never one signature with two meanings. | §211.188(b)(11) style double-check semantics. |
| P7 | Service, integration and device identities can never satisfy a signature requirement. | SIG-FR-023. |
| P8 | If the policy cannot be resolved for an action, the Mutation Gateway **fails closed** with `SIGNATURE_POLICY_UNRESOLVED`. | No silent unsigned commit. |

# 4. Actors

Signer classes referenced below map to the Document 01 §6.1 reference role model. Customer role names are configuration; the signer **class** is the contract.

# 5. Data model

## `sig_policy`
```text
id                    uuid PK
tenant_id             uuid NOT NULL
site_id               uuid NULL                -- NULL = applies to all sites in tenant
record_class          varchar(80)  NOT NULL    -- e.g. Batch, BatchStep, Deviation, MaterialLot
action                varchar(120) NOT NULL    -- canonical command type, not URL
meaning               varchar(40)  NOT NULL    -- SIG-FR-003 catalogue value
signer_class          varchar(120) NOT NULL
signature_count       smallint     NOT NULL DEFAULT 1
signature_order       jsonb        NULL        -- ordered signer classes when count > 1
independence_rule     varchar(200) NOT NULL    -- reference to sod_rule.code or 'NONE'
qualification_rule    varchar(200) NULL
reason_required       boolean      NOT NULL DEFAULT false
policy_source         varchar(40)  NOT NULL    -- PLATFORM_FLOOR | CUSTOMER_ADDITION
effective_from        timestamptz  NOT NULL
effective_to          timestamptz  NULL
version               bigint       NOT NULL
released_version_id   uuid         NULL        -- vault version of the released policy set
created_at            timestamptz  NOT NULL
```
Constraints: `UNIQUE (tenant_id, site_id, record_class, action, meaning, effective_from)`;
`CHECK (signature_count BETWEEN 1 AND 4)`;
`CHECK (policy_source <> 'CUSTOMER_ADDITION' OR signature_count >= floor_count)` enforced by the policy release service.
Indexes: `(tenant_id, record_class, action, effective_from DESC)`.

## `sig_policy_set`
```text
id uuid PK, tenant_id uuid, version bigint, state varchar(30),  -- DRAFT | RELEASED | SUPERSEDED
released_by uuid, released_at timestamptz, vault_object_id uuid, digest varchar(128)
```
A policy set is a **released, versioned, vaulted artefact** (Document 06). Batch execution binds the policy-set version in force at issue, so a mid-batch policy change cannot retroactively alter what a record required.

# 6. Runtime resolution algorithm

```text
resolveSignatureRequirement(command_type, record_class, record_id, actor_context)
  1. load policy set version bound to the aggregate (batch/record snapshot) — never "latest"
  2. select rows matching (record_class, action) effective at command time
  3. if none and command is state-changing and record_class is regulated → SIGNATURE_POLICY_UNRESOLVED (fail closed)
  4. for each required signature: resolve signer_class → allowed subjects (Doc 07)
  5. apply independence_rule against the record's existing actor set (performer, prior signers, author)
  6. apply qualification_rule (training/equipment/area currency)
  7. return ordered SignatureRequirement[] to the Mutation Gateway (MUT-FR-012)
```

The Gateway then creates one challenge per required signature (SIG-FR-005) and commits only after all proofs are valid (MUT-FR-013).

# 7. Functional requirements

| ID | Requirement | Detailed behaviour | Acceptance intent |
|---|---|---|---|
| SIGP-FR-001 | Policy is data, not code | Signature requirements are resolved from released policy data, never from hardcoded conditionals in a domain service. | Grep of domain code finds no literal signature branching. |
| SIGP-FR-002 | Floor enforcement | Customer configuration cannot reduce count, weaken signer class or remove independence below the platform floor. | Negative test: weakening attempt rejected with `SIGNATURE_POLICY_BELOW_FLOOR`. |
| SIGP-FR-003 | Policy versioning | Policy sets are released, versioned and vaulted; records bind the version in force. | Historic record replays its original requirement. |
| SIGP-FR-004 | Fail closed | Unresolved policy for a regulated state change blocks the commit. | Negative test passes. |
| SIGP-FR-005 | Meaning catalogue | Only SIG-FR-003 meanings are accepted. | Invalid meaning rejected at policy authoring time. |
| SIGP-FR-006 | Independence evaluation time | Independence and qualification are re-evaluated at signature completion. | Test: signer becomes non-independent between challenge and completion → rejected. |
| SIGP-FR-007 | Ordered chains | Where count > 1, order is enforced server-side. | Out-of-order signature rejected. |
| SIGP-FR-008 | Human-only | Service/integration/device identity cannot satisfy any signature requirement. | Service token rejected. |
| SIGP-FR-009 | Policy audit | Every policy authoring, release and supersession is audited and signed as `Approved`. | Policy change history reproducible. |
| SIGP-FR-010 | Inspection export | Export shows, for any record, the policy version applied, requirements resolved and signatures obtained. | Inspection query reproducible. |
| SIGP-FR-011 | Gap marking | Any signature point whose baseline is still `PROPOSED` is exported with its open gap reference. | No silent adoption of unapproved policy. |
| SIGP-FR-012 | Configuration validation impact | A customer policy addition is a configured-state change requiring PQ/UAT evidence (Document 85/96). | Change impact recorded. |

# 8. Platform floor — action family defaults (PROPOSED)

These defaults were derived by action family, not by guessing per endpoint. Each family states the meaning, signer class, count, independence and reason requirement.

| Action family | Meaning | Signer class | Count | Independence | Qualification | Reason |
|---|---|---|---|---|---|---|
| release / disposition / certif | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | Release qualification current | yes |
| reject | `Rejected` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | Release qualification current | yes |
| approve / approval / authoriz | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | Role qualification current | yes |
| verify / verification / witness / second-check / double-check | `Verified` | Qualified independent verifier | 1 | MUST NOT be the performer of the same action (SIG-FR-018) | Task qualification current | no |
| review | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | Review qualification current | no |
| close / closure | `Approved` | QA Approver for the record class | 1 | MUST be independent of the investigator/owner | Role qualification current | yes |
| correct / amend / amendment | `Approved` | Authorized corrector + independent approver | 2 | Corrector and approver MUST differ | Role qualification current | yes (mandatory reason-for-change) |
| override / exception / waive / deviat | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | Elevated authorization | yes |
| sign / signature | `per challenge` | Per policy lookup | 1 | Per policy lookup | Per policy lookup | per policy |
| complete / record / result / execute / perform / confirm | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | Task qualification current | no |
| issue / start / begin | `Performed` | Production Supervisor or qualified issuer | 1 | None | Task qualification current | no |
| hold / quarantine / block / suspend | `Performed` | Authorized holder (Production / QA) | 1 | None | Role qualification | yes |
| resume / unhold / release-hold | `Approved` | QA authority that owns the hold reason | 1 | MUST be independent of the person who caused the condition where configured | Role qualification | yes |
| destroy / discard / scrap / dispose | `Approved` | Warehouse Manager + QA per policy | 2 | Requester and approver MUST differ | Role qualification | yes |
| cancel / abort / void | `Approved` | Authorized canceller for the record class | 1 | MUST be independent of the author | Role qualification | yes |
| reopen | `Approved` | QA authority that closed the record class | 1 | Independent of the requester | Role qualification | yes |
| extend / extension | `Approved` | Owner's management + QA per policy | 1 | Independent of the owner | Role qualification | yes |
| submit / transmit / report | `Approved` | Regulatory Affairs authorized submitter | 1 | MUST be a human; service identity prohibited (SIG-FR-023) | Regulatory role qualification | yes |
| dispens / weigh | `Performed` | Dispensing Operator (qualified) | 1 | Independent verification required where the material or step is flagged critical | Dispensing qualification | no |

# 9. Signature Point Register

Compiled from every state-changing operation declared in Documents 03–60.
**Total signature points identified: 171** (of which 109 carry a `Released`, `Rejected`, `Approved` or `Verified` meaning and are therefore Part 11 critical).

| # | Doc | Module | Operation | Meaning | Signer class | Count | Independence | Reason |
|---|---|---|---|---|---|---|---|---|
| 1 | 06 | SPEC-GXP-004 | `POST /vault/v1/corrections/{id}/complete` | `Approved` | Authorized corrector + independent approver | 2 | Corrector and approver MUST differ | yes (mandatory reason-for-change) |
| 2 | 06 | SPEC-GXP-004 | `POST /vault/v1/masters/{type}/{businessId}/release` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 3 | 06 | SPEC-GXP-004 | `POST /vault/v1/objects/{objectId}/corrections` | `Approved` | Authorized corrector + independent approver | 2 | Corrector and approver MUST differ | yes (mandatory reason-for-change) |
| 4 | 07 | SPEC-IAM-001 | `POST /iam/v1/access-reviews` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |
| 5 | 07 | SPEC-IAM-001 | `POST /iam/v1/temporary-authorizations` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 6 | 08 | SPEC-GXP-006 | `POST /rules/v1/{ruleId}/release` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 7 | 09 | SPEC-EBMR-000 | `POST /products/v1/drafts/{id}/release` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 8 | 09 | SPEC-EBMR-000 | `POST /products/v1/drafts/{id}/submit` | `Approved` | Regulatory Affairs authorized submitter | 1 | MUST be a human; service identity prohibited (SIG-FR-023) | yes |
| 9 | 09 | SPEC-EBMR-000 | `POST /products/v1/{id}/suspend` | `Performed` | Authorized holder (Production / QA) | 1 | None | yes |
| 10 | 09 | SPEC-EBMR-000 | `POST /products/v1/{id}/validate-completeness` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 11 | 10 | SPEC-EBMR-001 | `POST /recipes/v1/drafts/{id}/release` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 12 | 10 | SPEC-EBMR-001 | `POST /recipes/v1/drafts/{id}/submit` | `Approved` | Regulatory Affairs authorized submitter | 1 | MUST be a human; service identity prohibited (SIG-FR-023) | yes |
| 13 | 11 | SPEC-EBMR-002 | `POST /batches/{id}/abort` | `Approved` | Authorized canceller for the record class | 1 | MUST be independent of the author | yes |
| 14 | 11 | SPEC-EBMR-002 | `POST /batches/{id}/hold` | `Performed` | Authorized holder (Production / QA) | 1 | None | yes |
| 15 | 11 | SPEC-EBMR-002 | `POST /batches/{id}/issue` | `Performed` | Production Supervisor or qualified issuer | 1 | None | no |
| 16 | 11 | SPEC-EBMR-002 | `POST /batches/{id}/production-complete` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 17 | 11 | SPEC-EBMR-002 | `POST /batches/{id}/resume` | `Approved` | QA authority that owns the hold reason | 1 | MUST be independent of the person who caused the condition where configured | yes |
| 18 | 11 | SPEC-EBMR-002 | `POST /batches/{id}/start` | `Performed` | Production Supervisor or qualified issuer | 1 | None | no |
| 19 | 11 | SPEC-EBMR-002 | `POST /batches/{id}/steps/{stepId}/complete` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 20 | 11 | SPEC-EBMR-002 | `POST /batches/{id}/steps/{stepId}/correct` | `Approved` | Authorized corrector + independent approver | 2 | Corrector and approver MUST differ | yes (mandatory reason-for-change) |
| 21 | 11 | SPEC-EBMR-002 | `POST /batches/{id}/steps/{stepId}/results` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 22 | 11 | SPEC-EBMR-002 | `POST /batches/{id}/steps/{stepId}/start` | `Performed` | Production Supervisor or qualified issuer | 1 | None | no |
| 23 | 11 | SPEC-EBMR-002 | `POST /batches/{id}/steps/{stepId}/verify` | `Verified` | Qualified independent verifier | 1 | MUST NOT be the performer of the same action (SIG-FR-018) | no |
| 24 | 12 | SPEC-EBMR-003 | `POST /devices/v1/units/{id}/hold` | `Performed` | Authorized holder (Production / QA) | 1 | None | yes |
| 25 | 14 | SPEC-EBMR-005 | `POST /qa-review/v1/batches/{batchId}/packages` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |
| 26 | 14 | SPEC-EBMR-005 | `POST /qa-review/v1/items/{id}/disposition` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 27 | 14 | SPEC-EBMR-005 | `POST /qa-review/v1/items/{id}/request-action` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |
| 28 | 14 | SPEC-EBMR-005 | `POST /qa-review/v1/packages/{id}/comments` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |
| 29 | 14 | SPEC-EBMR-005 | `POST /qa-review/v1/packages/{id}/complete` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |
| 30 | 14 | SPEC-EBMR-005 | `POST /qa-review/v1/packages/{id}/reindex` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |
| 31 | 15 | SPEC-EBMR-006 | `POST /release/v1/scopes/{id}/destroy` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 32 | 15 | SPEC-EBMR-006 | `POST /release/v1/scopes/{id}/hold` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 33 | 15 | SPEC-EBMR-006 | `POST /release/v1/scopes/{id}/reject` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 34 | 15 | SPEC-EBMR-006 | `POST /release/v1/scopes/{id}/release` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 35 | 15 | SPEC-EBMR-006 | `POST /release/v1/scopes/{id}/reprocess` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 36 | 15 | SPEC-EBMR-006 | `POST /release/v1/scopes/{id}/rework` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 37 | 15 | SPEC-EBMR-006 | `POST /release/v1/scopes/{type}/{id}/evaluate` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 38 | 16 | SPEC-EBMR-007 | `POST /packaging/v1/runs/{id}/complete` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 39 | 16 | SPEC-EBMR-007 | `POST /packaging/v1/runs/{id}/labels/issue` | `Performed` | Production Supervisor or qualified issuer | 1 | None | no |
| 40 | 17 | SPEC-EBMR-008 | `POST /reconciliation/v1/{id}/verify` | `Verified` | Qualified independent verifier | 1 | MUST NOT be the performer of the same action (SIG-FR-018) | no |
| 41 | 18 | SPEC-MAT-001 | `POST /supplier-material-approvals` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 42 | 18 | SPEC-MAT-001 | `POST /supplier-material-approvals/{id}/suspend` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 43 | 18 | SPEC-MAT-001 | `POST /supplier-qualifications/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 44 | 19 | SPEC-MAT-002A | `POST /materials/v1/lots/{id}/reject` | `Rejected` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 45 | 19 | SPEC-MAT-002A | `POST /materials/v1/lots/{id}/release` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 46 | 20 | SPEC-MAT-002B | `POST /inventory/v1/reservations/{id}/release` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 47 | 21 | SPEC-MAT-002C | `POST /dispensing/v1/orders` | `Performed` | Dispensing Operator (qualified) | 1 | Independent verification required where the material or step is flagged critical | no |
| 48 | 21 | SPEC-MAT-002C | `POST /dispensing/v1/orders/{id}/cancel` | `Approved` | Authorized canceller for the record class | 1 | MUST be independent of the author | yes |
| 49 | 21 | SPEC-MAT-002C | `POST /dispensing/v1/orders/{id}/complete` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 50 | 21 | SPEC-MAT-002C | `POST /dispensing/v1/orders/{id}/manual-reading` | `Performed` | Dispensing Operator (qualified) | 1 | Independent verification required where the material or step is flagged critical | no |
| 51 | 21 | SPEC-MAT-002C | `POST /dispensing/v1/orders/{id}/readings` | `Performed` | Dispensing Operator (qualified) | 1 | Independent verification required where the material or step is flagged critical | no |
| 52 | 21 | SPEC-MAT-002C | `POST /dispensing/v1/orders/{id}/select-source` | `Performed` | Dispensing Operator (qualified) | 1 | Independent verification required where the material or step is flagged critical | no |
| 53 | 21 | SPEC-MAT-002C | `POST /dispensing/v1/orders/{id}/start` | `Performed` | Production Supervisor or qualified issuer | 1 | None | no |
| 54 | 21 | SPEC-MAT-002C | `POST /dispensing/v1/orders/{id}/verify` | `Verified` | Qualified independent verifier | 1 | MUST NOT be the performer of the same action (SIG-FR-018) | no |
| 55 | 22 | SPEC-MAT-002D | `POST /inventory/v1/adjustments/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 56 | 22 | SPEC-MAT-002D | `POST /materials/v1/destructions/{id}/execute` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 57 | 23 | SPEC-QC-001 | `POST /qc/v1/results/{id}/correct` | `Approved` | Authorized corrector + independent approver | 2 | Corrector and approver MUST differ | yes (mandatory reason-for-change) |
| 58 | 23 | SPEC-QC-001 | `POST /qc/v1/specifications/{id}/release` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 59 | 23 | SPEC-QC-001 | `POST /qc/v1/test-orders/{id}/complete` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 60 | 23 | SPEC-QC-001 | `POST /qc/v1/test-orders/{id}/results` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 61 | 23 | SPEC-QC-001 | `POST /qc/v1/test-orders/{id}/review` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |
| 62 | 23 | SPEC-QC-001 | `POST /qc/v1/test-orders/{id}/start` | `Performed` | Production Supervisor or qualified issuer | 1 | None | no |
| 63 | 24 | SPEC-QC-002 | `POST /integrations/lims/{instance}/events/results` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 64 | 24 | SPEC-QC-002 | `POST /integrations/lims/{instance}/samples/{id}/cancel` | `Approved` | Authorized canceller for the record class | 1 | MUST be independent of the author | yes |
| 65 | 25 | SPEC-QC-003 | `POST /quality/oos/v1/from-result/{resultId}` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 66 | 25 | SPEC-QC-003 | `POST /quality/oos/v1/{id}/close` | `Approved` | QA Approver for the record class | 1 | MUST be independent of the investigator/owner | yes |
| 67 | 25 | SPEC-QC-003 | `POST /quality/oos/v1/{id}/disposition` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 68 | 25 | SPEC-QC-003 | `POST /quality/oos/v1/{id}/extended-investigation` | `Approved` | Owner's management + QA per policy | 1 | Independent of the owner | yes |
| 69 | 25 | SPEC-QC-003 | `POST /quality/oot/v1/{id}/close` | `Approved` | QA Approver for the record class | 1 | MUST be independent of the investigator/owner | yes |
| 70 | 26 | SPEC-QMS-001 | `POST /qms/v1/deviations` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 71 | 26 | SPEC-QMS-001 | `POST /qms/v1/deviations/{id}/close` | `Approved` | QA Approver for the record class | 1 | MUST be independent of the investigator/owner | yes |
| 72 | 26 | SPEC-QMS-001 | `POST /qms/v1/deviations/{id}/contain` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 73 | 26 | SPEC-QMS-001 | `POST /qms/v1/deviations/{id}/disposition` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 74 | 26 | SPEC-QMS-001 | `POST /qms/v1/deviations/{id}/extend` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 75 | 26 | SPEC-QMS-001 | `POST /qms/v1/deviations/{id}/impact` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 76 | 26 | SPEC-QMS-001 | `POST /qms/v1/deviations/{id}/investigation` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 77 | 26 | SPEC-QMS-001 | `POST /qms/v1/deviations/{id}/reopen` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 78 | 26 | SPEC-QMS-001 | `POST /qms/v1/deviations/{id}/triage` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 79 | 27 | SPEC-QMS-002 | `POST /qms/v1/actions/{id}/complete` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 80 | 27 | SPEC-QMS-002 | `POST /qms/v1/capas/{id}/close` | `Approved` | QA Approver for the record class | 1 | MUST be independent of the investigator/owner | yes |
| 81 | 27 | SPEC-QMS-002 | `POST /qms/v1/capas/{id}/extend` | `Approved` | Owner's management + QA per policy | 1 | Independent of the owner | yes |
| 82 | 27 | SPEC-QMS-002 | `POST /qms/v1/capas/{id}/reopen` | `Approved` | QA authority that closed the record class | 1 | Independent of the requester | yes |
| 83 | 28 | SPEC-QMS-003 | `POST /qms/v1/nonconformances/{id}/close` | `Approved` | QA Approver for the record class | 1 | MUST be independent of the investigator/owner | yes |
| 84 | 28 | SPEC-QMS-003 | `POST /qms/v1/nonconformances/{id}/disposition` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 85 | 28 | SPEC-QMS-003 | `POST /qms/v1/nonconformances/{id}/verify` | `Verified` | Qualified independent verifier | 1 | MUST NOT be the performer of the same action (SIG-FR-018) | no |
| 86 | 29 | SPEC-QMS-004 | `POST /qms/v1/changes/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 87 | 29 | SPEC-QMS-004 | `POST /qms/v1/changes/{id}/close` | `Approved` | QA Approver for the record class | 1 | MUST be independent of the investigator/owner | yes |
| 88 | 29 | SPEC-QMS-004 | `POST /qms/v1/changes/{id}/verify` | `Verified` | Qualified independent verifier | 1 | MUST NOT be the performer of the same action (SIG-FR-018) | no |
| 89 | 30 | SPEC-QMS-005 | `POST /documents/v1/drafts/{id}/release` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 90 | 30 | SPEC-QMS-005 | `POST /documents/v1/drafts/{id}/submit` | `Approved` | Regulatory Affairs authorized submitter | 1 | MUST be a human; service identity prohibited (SIG-FR-023) | yes |
| 91 | 31 | SPEC-QMS-006 | `POST /training/v1/assignments` | `per challenge` | Per policy lookup | 1 | Per policy lookup | per policy |
| 92 | 31 | SPEC-QMS-006 | `POST /training/v1/assignments/{id}/assess` | `per challenge` | Per policy lookup | 1 | Per policy lookup | per policy |
| 93 | 31 | SPEC-QMS-006 | `POST /training/v1/assignments/{id}/complete` | `per challenge` | Per policy lookup | 1 | Per policy lookup | per policy |
| 94 | 31 | SPEC-QMS-006 | `POST /training/v1/waivers` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 95 | 32 | SPEC-QMS-007 | `POST /qms/v1/scars/{id}/close` | `Approved` | QA Approver for the record class | 1 | MUST be independent of the investigator/owner | yes |
| 96 | 32 | SPEC-QMS-007 | `POST /qms/v1/scars/{id}/review` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |
| 97 | 33 | SPEC-QMS-008 | `POST /qms/v1/risks/{id}/review` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |
| 98 | 34 | SPEC-QMS-009 | `POST /qms/v1/audits/{id}/close` | `Approved` | QA Approver for the record class | 1 | MUST be independent of the investigator/owner | yes |
| 99 | 34 | SPEC-QMS-009 | `POST /qms/v1/audits/{id}/start` | `Performed` | Production Supervisor or qualified issuer | 1 | None | no |
| 100 | 34 | SPEC-QMS-009 | `POST /qms/v1/findings/{id}/verify` | `Verified` | Qualified independent verifier | 1 | MUST NOT be the performer of the same action (SIG-FR-018) | no |
| 101 | 35 | SPEC-QMS-010 | `POST /qms/v1/complaints/{id}/close` | `Approved` | QA Approver for the record class | 1 | MUST be independent of the investigator/owner | yes |
| 102 | 35 | SPEC-QMS-010 | `POST /qms/v1/complaints/{id}/reportability` | `Approved` | Regulatory Affairs authorized submitter | 1 | MUST be a human; service identity prohibited (SIG-FR-023) | yes |
| 103 | 36 | SPEC-QMS-011 | `POST /qms/v1/field-actions/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 104 | 36 | SPEC-QMS-011 | `POST /qms/v1/field-actions/{id}/close` | `Approved` | QA Approver for the record class | 1 | MUST be independent of the investigator/owner | yes |
| 105 | 36 | SPEC-QMS-011 | `POST /qms/v1/field-actions/{id}/reportability` | `Approved` | Regulatory Affairs authorized submitter | 1 | MUST be a human; service identity prohibited (SIG-FR-023) | yes |
| 106 | 37 | SPEC-QMS-012 | `POST /quality-metrics/v1/definitions/{id}/release` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 107 | 37 | SPEC-QMS-012 | `POST /quality-metrics/v1/management-review-packages` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |
| 108 | 38 | SPEC-EQP-001 | `POST /equipment/v1/{id}/hold` | `Performed` | Authorized holder (Production / QA) | 1 | None | yes |
| 109 | 39 | SPEC-EQP-002 | `POST /cleaning/v1/executions/{id}/complete` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 110 | 39 | SPEC-EQP-002 | `POST /cleaning/v1/executions/{id}/verify` | `Verified` | Qualified independent verifier | 1 | MUST NOT be the performer of the same action (SIG-FR-018) | no |
| 111 | 39 | SPEC-EQP-002 | `POST /line-clearance/v1/{id}/complete` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 112 | 40 | SPEC-EQP-003 | `POST /aseptic/v1/operations/{id}/complete` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 113 | 40 | SPEC-EQP-003 | `POST /aseptic/v1/operations/{id}/start` | `Performed` | Production Supervisor or qualified issuer | 1 | None | no |
| 114 | 41 | SPEC-EQP-004 | `POST /em/v1/results` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 115 | 41 | SPEC-EQP-004 | `POST /em/v1/results/{id}/review` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |
| 116 | 42 | SPEC-EQP-005 | `POST /filtration/v1/uses/{id}/complete` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 117 | 42 | SPEC-EQP-005 | `POST /sterilization/v1/cycles/{id}/review` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |
| 118 | 42 | SPEC-EQP-005 | `POST /sterilization/v1/cycles/{id}/start` | `Performed` | Production Supervisor or qualified issuer | 1 | None | no |
| 119 | 43 | SPEC-EDGE-001 | `POST /edge/v1/gateways/{gatewayId}/certificate-rotation` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 120 | 58 | SPEC-PM-001 | `POST /postmarket/v1/signals` | `per challenge` | Per policy lookup | 1 | Per policy lookup | per policy |
| 121 | 58 | SPEC-PM-001 | `POST /postmarket/v1/signals/{id}/assessments` | `per challenge` | Per policy lookup | 1 | Per policy lookup | per policy |
| 122 | 58 | SPEC-PM-001 | `POST /postmarket/v1/signals/{id}/escalations` | `per challenge` | Per policy lookup | 1 | Per policy lookup | per policy |
| 123 | 59 | SPEC-PM-002 | `POST /regulatory/v1/cases/{caseId}/reportability-tracks` | `Approved` | Regulatory Affairs authorized submitter | 1 | MUST be a human; service identity prohibited (SIG-FR-023) | yes |
| 124 | 59 | SPEC-PM-002 | `POST /regulatory/v1/reports/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 125 | 59 | SPEC-PM-002 | `POST /regulatory/v1/reports/{id}/followups` | `Approved` | Regulatory Affairs authorized submitter | 1 | MUST be a human; service identity prohibited (SIG-FR-023) | yes |
| 126 | 59 | SPEC-PM-002 | `POST /regulatory/v1/reports/{id}/payloads:generate` | `Approved` | Regulatory Affairs authorized submitter | 1 | MUST be a human; service identity prohibited (SIG-FR-023) | yes |
| 127 | 59 | SPEC-PM-002 | `POST /regulatory/v1/reports/{id}/submissions` | `Approved` | Regulatory Affairs authorized submitter | 1 | MUST be a human; service identity prohibited (SIG-FR-023) | yes |
| 128 | 59 | SPEC-PM-002 | `POST /regulatory/v1/tracks/{id}/reports` | `Approved` | Regulatory Affairs authorized submitter | 1 | MUST be a human; service identity prohibited (SIG-FR-023) | yes |
| 129 | 60 | SPEC-PM-003 | `POST /postmarket/v1/correction-removal/{id}/decision` | `Approved` | Authorized corrector + independent approver | 2 | Corrector and approver MUST differ | yes (mandatory reason-for-change) |
| 130 | 60 | SPEC-PM-003 | `POST /postmarket/v1/field-actions/{id}/correction-removal-assessment` | `Approved` | Authorized corrector + independent approver | 2 | Corrector and approver MUST differ | yes (mandatory reason-for-change) |
| 131 | 60 | SPEC-PM-003 | `POST /postmarket/v1/obligations/{id}/deadline-overrides` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 132 | 60 | SPEC-PM-003 | `POST /postmarket/v1/sharing/{id}/record-sent` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 133 | 61 | SPEC-SEC-001 | `POST /security/v1/exceptions` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 134 | 63 | SPEC-SEC-003 | `POST /security/v1/admin-commands/{code}:execute` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 135 | 63 | SPEC-SEC-003 | `POST /security/v1/privileged-access/requests/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 136 | 63 | SPEC-SEC-003 | `POST /security/v1/privileged-sessions/{id}/close` | `Approved` | QA Approver for the record class | 1 | MUST be independent of the investigator/owner | yes |
| 137 | 65 | SPEC-SEC-005 | `POST /security/v1/certificates/{id}/revoke` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 138 | 65 | SPEC-SEC-005 | `POST /security/v1/certificates/{id}/rotate` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 139 | 65 | SPEC-SEC-005 | `POST /security/v1/certificates:issue` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 140 | 67 | SPEC-SEC-007 | `POST /security/v1/incidents/{id}/close` | `Approved` | QA Approver for the record class | 1 | MUST be independent of the investigator/owner | yes |
| 141 | 68 | SPEC-SEC-008 | `POST /security/v1/vulnerabilities/{id}/exceptions` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 142 | 72 | SPEC-DATA-004 | `POST /evidence/v1/{id}/legal-holds` | `Performed` | Authorized holder (Production / QA) | 1 | None | yes |
| 143 | 75 | SPEC-DATA-007 | `POST /reports/v1/exports` | `Approved` | Regulatory Affairs authorized submitter | 1 | MUST be a human; service identity prohibited (SIG-FR-023) | yes |
| 144 | 79 | SPEC-VAL-001 | `POST /validation/v1/master-plans/{id}/release` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 145 | 80 | SPEC-VAL-002 | `POST /validation/v1/function-risks/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 146 | 82 | SPEC-VAL-004 | `POST /validation/v1/executions/{id}/complete` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 147 | 82 | SPEC-VAL-004 | `POST /validation/v1/tests/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 148 | 83 | SPEC-VAL-005 | `POST /validation/v1/iq/executions/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 149 | 83 | SPEC-VAL-005 | `POST /validation/v1/iq/executions/{id}/complete` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 150 | 84 | SPEC-VAL-006 | `POST /validation/v1/oq/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 151 | 85 | SPEC-VAL-007 | `POST /validation/v1/pq/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 152 | 86 | SPEC-VAL-008 | `POST /validation/v1/infrastructure/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 153 | 87 | SPEC-VAL-009 | `POST /validation/v1/migrations/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 154 | 88 | SPEC-VAL-010 | `POST /validation/v1/part11/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 155 | 89 | SPEC-VAL-011 | `POST /validation/v1/data-integrity/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 156 | 90 | SPEC-VAL-012 | `POST /validation/v1/interfaces/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 157 | 91 | SPEC-VAL-013 | `POST /validation/v1/dr/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 158 | 92 | SPEC-VAL-014 | `POST /validation/v1/security/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 159 | 93 | SPEC-VAL-015 | `POST /validation/v1/performance/runs` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 160 | 93 | SPEC-VAL-015 | `POST /validation/v1/performance/scenarios` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 161 | 93 | SPEC-VAL-015 | `POST /validation/v1/performance/{id}/evaluate` | `Performed` | Qualified performer for the task | 1 | None required unless the step is flagged critical | no |
| 162 | 94 | SPEC-VAL-016 | `POST /validation/v1/exceptions` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 163 | 94 | SPEC-VAL-016 | `POST /validation/v1/exceptions/{id}/disposition` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 164 | 94 | SPEC-VAL-016 | `POST /validation/v1/exceptions/{id}/retest-plan` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 165 | 94 | SPEC-VAL-016 | `POST /validation/v1/exceptions/{id}/triage` | `Approved` | Elevated authority defined by the record class | 1 | MUST be independent of the requester | yes |
| 166 | 95 | SPEC-VAL-017 | `POST /validation/v1/releases/{id}/authorize` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 167 | 95 | SPEC-VAL-017 | `POST /validation/v1/releases/{id}/deployment-check` | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes |
| 168 | 95 | SPEC-VAL-017 | `POST /validation/v1/summary-reports` | `Approved` | Regulatory Affairs authorized submitter | 1 | MUST be a human; service identity prohibited (SIG-FR-023) | yes |
| 169 | 95 | SPEC-VAL-017 | `POST /validation/v1/summary-reports/{id}/approve` | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | 1 | MUST be independent of the author | yes |
| 170 | 96 | SPEC-VAL-018 | `POST /validation/v1/periodic-reviews` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |
| 171 | 96 | SPEC-VAL-018 | `POST /validation/v1/periodic-reviews/{id}/decision` | `Reviewed` | QA Reviewer | 1 | MUST be independent of the performer | no |

# 10. Explicitly NOT requiring a signature (proposed)

- Creating a draft or initiating a record (audit only).
- Attaching evidence to an open record (audit only; the approving signature covers the evidence set).
- Triage, assignment and reassignment (audited, escalation-controlled).
- Search, export and read operations.
- Projection rebuilds and cache invalidation.
- Integration inbound acceptance of data that does not itself constitute an approval (the subsequent GxP acceptance decision may require one).

If a customer's procedure requires a signature on any of these, it is added as a `CUSTOMER_ADDITION`, never by code change.

# 11. Failure and recovery

| Condition | Behaviour |
|---|---|
| Policy service unavailable | Fail closed; `DEPENDENCY_UNAVAILABLE`; no degraded-mode commit (MUT-FR-022). |
| Policy unresolved for a regulated action | `SIGNATURE_POLICY_UNRESOLVED`; command rejected; security event raised. |
| Record changed after challenge | Challenge invalidated (SIG-FR-014); new challenge required. |
| Signer loses qualification between challenge and completion | Completion rejected; audit records the attempt. |
| Second signer unavailable in an ordered chain | Record remains in its pre-commit state; no partial commit. |

# 12. Stable error codes

`SIGNATURE_POLICY_UNRESOLVED`, `SIGNATURE_POLICY_BELOW_FLOOR`, `SIGNATURE_ORDER_VIOLATION`,
`SIGNATURE_INDEPENDENCE_VIOLATION`, `SIGNATURE_QUALIFICATION_EXPIRED`, `SIGNATURE_CLASS_NOT_PERMITTED`,
`SIGNATURE_SERVICE_IDENTITY_PROHIBITED`, `SIGNATURE_POLICY_VERSION_MISMATCH`.

# 13. Test catalogue

1. Each floor family: positive signature path produces a valid, bound, manifested signature.
2. Each floor family: missing signature blocks the commit.
3. Independence: performer attempts to verify own action → rejected.
4. Independence: production performer attempts QA release → rejected.
5. Ordered chain: second signer signs before first → rejected.
6. Policy weakening attempt by customer configuration → rejected.
7. Policy version binding: policy changed mid-batch → record still requires the bound version's set.
8. Service identity attempts any signature → rejected.
9. Qualification expiry between challenge and completion → rejected.
10. Unresolved policy for a new command type → fail closed, security event raised.
11. Export shows policy version, requirements and obtained signatures for a historic record.
12. Concurrency: two signers complete simultaneously on a 2-signature chain → exactly one valid ordering persists.

# 14. Validation impact

- Part 11 validation (Document 88) must execute the floor matrix as OQ evidence.
- Any customer addition is configured-state change requiring PQ evidence (Document 85).
- Changing a floor value after approval is a revalidation trigger (Document 96).

# 15. Acceptance criteria

1. Policy data model implemented with floor enforcement and versioned release.
2. Every signature point in §9 has an approved policy row or an open gap reference.
3. Mutation Gateway resolves requirements exclusively from policy data.
4. All §13 tests pass, including every negative case.
5. Inspection export reproduces requirement resolution for a historic record.

# 16. Claude Code / Codex prohibitions

- Do not hardcode a signature requirement in a domain service or a Frappe controller.
- Do not create a signature record outside the Signature Service.
- Do not treat an authenticated session, an API key or an approval flag in a payload as a signature.
- Do not implement a signature point marked `PROPOSED` as if it were approved: emit the policy row with `policy_status = PROPOSED` and reference SG-004 in the generated artefacts.

# 17. Approval block

| Role | Name | Decision | Date | Signature reference |
|---|---|---|---|---|
| Head of Quality |  |  |  |  |
| Regulatory Affairs |  |  |  |  |
| Product Owner |  |  |  |  |

Approved as the construction baseline. Formal QMS signature records are captured against this version.
