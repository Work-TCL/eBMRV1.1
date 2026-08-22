# US eBMR / eDHR Regulated Manufacturing Platform
## Document 107 — Segregation of Duties & Incompatible Role Baseline — v1.0 APPROVED

**Specification ID:** SPEC-IAM-002
**Status:** APPROVED v1.0 (construction baseline) — approvers of record: Head of Quality and Security Officer
**Closes:** SG-009
**Approval:** Approved by the Project Owner during construction review on 2026-08-21. A formal Part 11 signature record must be captured in the QMS against this version before validated release; the approval block below is the record of the construction decision.

**Primary Dependencies:** Document 07 (IAM/RBAC/Qualification/SoD), Document 01 §6.1/§6.2, Document 04 (SIG-FR-018), Document 63 (privileged access), Document 106 (signature policy)

---

# 0. Why this document exists

Document 01 §6.2 lists the **classes** of segregation-of-duties rule the policy engine must support. Document 07 specifies the **engine**. Neither enumerates which concrete reference roles may not be held by the same person, nor the default performer/verifier independence rule per action. Without that data the policy engine ships with an empty rule set and every deployment silently re-derives a Part 11 control.

# 1. Objective and non-goals

**Objective.** Define the SoD data model, the platform-default incompatible-role matrix, the per-action independence rules, the evaluation points and the exception path.

**Non-goals.** This document does not define authentication (Document 62), privileged/break-glass access (Document 63) or the signature ceremony (Document 04).

# 2. Two distinct control types

| Control | Question it answers | Evaluated when |
|---|---|---|
| **Standing SoD** (role-pair) | May this person hold both of these roles at all? | Role assignment, access review, and at every authorization decision |
| **Dynamic SoD** (action independence) | May *this* person perform *this* action on *this* record, given who already acted on it? | At authorization and again at signature completion (SIG-FR-018) |

Both are required. A role-pair matrix alone misses "same qualified operator performed and verified"; action independence alone misses standing privilege concentration.

# 3. Data model

## `sod_rule`
```text
id uuid PK
tenant_id uuid NOT NULL
code varchar(80) NOT NULL          -- stable rule code referenced by sig_policy.independence_rule
rule_type varchar(20) NOT NULL     -- STANDING_ROLE_PAIR | ACTION_INDEPENDENCE
role_a varchar(120) NULL           -- STANDING_ROLE_PAIR
role_b varchar(120) NULL
record_class varchar(80) NULL      -- ACTION_INDEPENDENCE
action varchar(120) NULL
independent_of jsonb NULL          -- ['PERFORMER','AUTHOR','PRIOR_SIGNER','INVESTIGATOR','REQUESTER']
severity varchar(20) NOT NULL      -- PROHIBITED | REQUIRES_APPROVAL | REPORT_ONLY
rationale text NOT NULL
source_reference varchar(200) NOT NULL
effective_from timestamptz NOT NULL
effective_to timestamptz NULL
version bigint NOT NULL
policy_source varchar(30) NOT NULL -- PLATFORM_FLOOR | CUSTOMER_ADDITION
```
Constraints: `UNIQUE (tenant_id, code, effective_from)`; `CHECK (rule_type <> 'STANDING_ROLE_PAIR' OR (role_a IS NOT NULL AND role_b IS NOT NULL))`.

## `sod_exception`
```text
id uuid PK, tenant_id uuid, subject_id uuid, sod_rule_code varchar(80),
reason text NOT NULL, scope jsonb NOT NULL,           -- site/record/time bounded
requested_by uuid, approved_by uuid, approval_signature_id uuid,
valid_from timestamptz, valid_to timestamptz NOT NULL, -- open-ended exceptions prohibited
review_due timestamptz, state varchar(30), version bigint
```

# 4. Platform-default incompatible role pairs (PROPOSED)

Severity key: **P** = prohibited (never permitted together), **A** = requires documented approval and time-bounded exception, **R** = permitted but reported in access review.

| Code | Role A | Role B | Severity | Rationale |
|---|---|---|---|---|
| SOD-001 | Operator / Production Supervisor | QA Approver / Batch Release | **P** | Production cannot release its own product (Doc 01 §6.2). |
| SOD-002 | Security Administrator | QA Approver / Batch Release | **P** | Security admin can alter access; combining with release authority defeats the control. |
| SOD-003 | Application Administrator | QA Approver / Batch Release | **P** | Configuration authority plus release authority removes independent oversight. |
| SOD-004 | Enterprise / Site Administrator | Head of Quality | **P** | Administrative override capability must not sit with the ultimate quality authority. |
| SOD-005 | Document Controller | QA Approver of the same document | **A** | Controller may administer but should not approve content they authored. |
| SOD-006 | Deviation Investigator | QA Approver closing the same deviation | **P** | Investigator cannot approve their own investigation conclusion. |
| SOD-007 | CAPA Owner | CAPA effectiveness approver | **P** | Effectiveness must be judged independently of the owner. |
| SOD-008 | Supplier Quality Manager | Buyer / Procurement Manager | **A** | Supplier approval independent of commercial sourcing pressure. |
| SOD-009 | Calibration Technician | Equipment Administrator approving calibration status | **A** | Performer of calibration should not approve its acceptance. |
| SOD-010 | QC Analyst | QC Manager approving own OOS investigation | **P** | §211.192 style independence for OOS conclusions. |
| SOD-011 | Sampler | QC Analyst testing the same sample | **R** | Common in small labs; reported and risk-assessed. |
| SOD-012 | Material Issuer | Material Receiver for the same lot | **R** | Reported; may be prohibited by customer procedure. |
| SOD-013 | Integration Service Account | Any human role | **P** | Service identities are never human identities (MUT-FR-023). |
| SOD-014 | Read-only Auditor / Inspector | Any mutating role | **P** | Inspector accounts must remain non-mutating. |
| SOD-015 | Training Coordinator | Approver of own training record | **P** | Self-qualification prohibited. |
| SOD-016 | Internal Auditor | Owner of the audited area's records | **P** | Auditor independence. |
| SOD-017 | Packaging Operator | Label reconciliation approver | **A** | Reconciliation independence for §211.125-type controls. |
| SOD-018 | Dispensing Operator | Independent dispensing verifier | **P** (per action) | Enforced dynamically per dispense action, see §5. |
| SOD-019 | Regulatory Affairs submitter | Approver of the same report version | **A** | Submission independence where customer procedure requires. |
| SOD-020 | Break-glass / privileged support identity | Any regulated approval role | **P** | Document 63; privileged access is never an approval path. |

# 5. Platform-default action independence rules (PROPOSED)

| Code | Record class | Action | Signer must be independent of | Severity |
|---|---|---|---|---|
| IND-001 | BatchStep | verify | PERFORMER | P |
| IND-002 | Batch | release | every PERFORMER on the batch, and the QA Reviewer where two-stage review is configured | P |
| IND-003 | Batch | reject | every PERFORMER on the batch | P |
| IND-004 | MaterialDispense | verify | PERFORMER | P |
| IND-005 | Deviation | close | INVESTIGATOR, OWNER | P |
| IND-006 | CAPA | effectiveness-approve | OWNER | P |
| IND-007 | Nonconformance | disposition-approve | REQUESTER | P |
| IND-008 | ChangeControl | approve | AUTHOR | P |
| IND-009 | ControlledDocument | approve | AUTHOR | A (configurable per document class) |
| IND-010 | OOS | conclusion-approve | ANALYST who produced the result | P |
| IND-011 | MasterRecipe | release | AUTHOR | P |
| IND-012 | RecordCorrection | approve | CORRECTOR | P |
| IND-013 | Complaint | closure-approve | INVESTIGATOR | P |
| IND-014 | RegulatoryReport | approve | AUTHOR of the narrative | A |
| IND-015 | ValidationTestExecution | review | EXECUTOR | P |
| IND-016 | FieldAction | approve | REQUESTER | P |
| IND-017 | SterilizationCycle | release | OPERATOR of the cycle | P |
| IND-018 | LineClearance | verify | PERFORMER | P |
| IND-019 | EquipmentQualification | approve | TECHNICIAN who executed it | P |
| IND-020 | Any record | reopen | the approver who closed it (report-only where the same authority is the only one available) | R |

# 6. Functional requirements

| ID | Requirement | Detailed behaviour | Acceptance intent |
|---|---|---|---|
| SODB-FR-001 | Rules are data | SoD rules are released, versioned configuration, not code branches. | No SoD conditional in domain code. |
| SODB-FR-002 | Two evaluation points | Standing rules evaluate at role assignment and at authorization; action independence evaluates at authorization and again at signature completion. | Both negative tests pass. |
| SODB-FR-003 | Floor enforcement | Customers may raise severity or add rules; they may not lower a PROHIBITED platform rule. | Weakening attempt rejected. |
| SODB-FR-004 | Exceptions are bounded | Every exception has reason, scope, approver signature, and a mandatory end date. | Open-ended exception rejected. |
| SODB-FR-005 | Exception review | Active exceptions appear in periodic access review (IAM-FR-026). | Review report includes them. |
| SODB-FR-006 | Conflict reporting | Access review reports every held role pair with severity R or above. | Report reproducible. |
| SODB-FR-007 | Emergency access | Break-glass identities are excluded from all approval paths and time-boxed (Document 63). | Negative test passes. |
| SODB-FR-008 | Audit | Rule authoring, release, exception grant and every SoD denial are audited. | History reproducible. |
| SODB-FR-009 | Fail closed | If SoD evaluation cannot complete, the action is denied. | `DEPENDENCY_UNAVAILABLE`. |
| SODB-FR-010 | Small-site mode | Where a customer genuinely lacks two qualified people, only severity A/R rules may be exempted, never P, and the exemption is a documented quality decision. | P rules cannot be exempted. |

# 7. Stable error codes

`SOD_CONFLICT`, `SOD_INDEPENDENCE_REQUIRED`, `SOD_EXCEPTION_EXPIRED`, `SOD_EXCEPTION_SCOPE_EXCEEDED`,
`SOD_RULE_BELOW_FLOOR`, `SOD_ROLE_PAIR_PROHIBITED`, `SOD_EVALUATION_UNAVAILABLE`.

# 8. Test catalogue

1. Each prohibited role pair: assignment attempt rejected.
2. Each action-independence rule: same-person attempt rejected at authorization.
3. Same-person attempt that passes authorization but violates independence at signature completion → rejected.
4. Time-bounded exception: grant, use, expiry, post-expiry denial.
5. Open-ended exception rejected.
6. Access review report lists all active conflicts and exceptions.
7. Break-glass identity attempts approval → denied and alerted.
8. Customer attempts to downgrade a P rule → rejected.
9. SoD service unavailable → action denied, no bypass.
10. Concurrency: two users attempt the second signature simultaneously → only an independent signer succeeds.

# 9. Validation impact

Independence controls are Part 11 and data-integrity critical: OQ evidence per Document 84 and Part 11 validation per Document 88. Customer additions and small-site exemptions are configured-state changes requiring PQ evidence (Document 85).

# 10. Acceptance criteria

1. Rule engine implemented with both rule types and both evaluation points.
2. Platform floor loaded as released, versioned configuration with `policy_source = PLATFORM_FLOOR`.
3. All §8 tests pass.
4. Access review report demonstrates conflict and exception visibility.

# 11. Claude Code / Codex prohibitions

- Do not implement `if user == performer` checks inside domain services; call the policy engine.
- Do not grant a service account a human role to make a test pass.
- Do not create an exception without an end date.
- Do not lower a PROHIBITED rule to make a workflow succeed; raise a SPEC_GAP instead.

# 12. Approval block

| Role | Name | Decision | Date | Signature reference |
|---|---|---|---|---|
| Head of Quality |  |  |  |  |
| Security Officer |  |  |  |  |
