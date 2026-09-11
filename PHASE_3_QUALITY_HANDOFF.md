# Phase 3 — Quality / Product-Owner Decision Hand-off

**Prepared by:** Engineering (Claude Code)
**Date:** 2026-09-10
**Branch:** `wp12-14-rbac-signature-fixes`
**Status of Phase 3:** engineering scope complete and committed. Phase 3 cannot be marked
*officially closed* until the decisions in this document are ratified.

---

## 0. How to read this document

Phase 3 left four items open. **None is a code defect.** Each is a regulated decision that
CLAUDE.md §4, SIG-FR-004 / SIGP-FR-004 and AG-15 reserve to the **Head of Quality** and
**Product Owner** (with **Regulatory Affairs** co-approval where a reportability action is
involved). Engineering has implemented every affected action so that it **fails closed** —
`SIGNATURE_POLICY_UNRESOLVED` (HTTP 409) or `PRECISION_POLICY_UNRESOLVED` (HTTP 409) — rather
than committing an unsigned or un-rounded regulated result. That behaviour is correct and
tested; it is also a hard stop for the affected workflows until these rows are approved.

**The four items are not all the same kind of decision:**

| Kind | Meaning | Items |
|---|---|---|
| **A — Ratify existing baseline content** | Document 106 §9 / Document 110 §2 already state the values. They are marked *PROPOSED* / carry an unsigned approval block. Quality confirms them (and the abstract-signer-class → platform-role mapping) with no new authoring. | SG-145; the SG-035 and SG-138 pairs that map to a Document 106 §9 row |
| **B — Author new policy** | Document 106 has **no row** for the action, or explicitly defers it ("per policy lookup"), or the row needs a mechanism the platform does not yet implement (2-signature chains). | SG-035 `product_version/reinstate` and `record_correction/complete`; SG-138 `training_assignment` ×3; **all of SG-167** |

Engineering has **not** seeded, guessed, or inferred any value. Section 6 of each item states
exactly what will be executed *after* ratification, and nothing will be executed before it.

### Reference: the platform signature-policy row

The runtime resolves every signature requirement from one row in `signature.signature_policies`.
The re-runnable seeding surface is the Python tuple `SIGNATURE_POLICY_FLOOR` in
`services/gxp-api/scripts/seed.py`:

```
(record_type, action, meaning, required_role_name, independent, signature_required, reason_required)
```

| Tuple field | Maps to DB column | Notes |
|---|---|---|
| `record_type` | `record_type` | platform record-class literal (e.g. `vault_object`) |
| `action` | `action` | canonical command action (e.g. `release`) |
| `meaning` | `meaning` | **must** be a SIG-FR-003 catalogue value: `Performed`, `Verified`, `Reviewed`, `Approved`, `Released`, `Rejected`, `Authored`, `Witnessed` |
| `required_role_name` | `required_role_id` (resolved) | concrete platform role, or `None` when the signer class is a role *pair* enforced by RBAC + a bespoke independence check |
| `independent` | `requires_independent_signer` | boolean |
| `signature_required` | `signature_required` | boolean |
| `reason_required` | `reason_required` | boolean |

**The platform row has no `signature_count` / `signature_order` column.** Document 106 §5's
`sig_policy` model defines `signature_count` (1–4) and `signature_order`; the implemented
`SignaturePolicy` model is **single-signature only**. Any Document 106 point with **Count = 2**
(the `correct / amend` and `destroy` families, and §9 rows 1 / 3) cannot be represented or
enforced by the current mechanism — see SG-035 item B2.

---

## 1. SG-035 — Vault / Rules / Product-version signature-policy rows

**Gap ID:** SG-035 &nbsp;·&nbsp; **Class:** E (engineering) in register, but the missing values are class R
**Owner:** Head of Quality + Product Owner
**Affected requirements:** SIG-FR-004, SIGP-FR-004, VLT-FR-001/010, RUL-FR-030, PRD-FR (product lifecycle)
**Affected endpoints / commands:**
`POST /vault/v1/masters/{type}/{businessId}/release` · `POST /vault/v1/corrections/{id}/complete` ·
`POST /rules/v1/{ruleId}/release` · `POST /products/v1/{id}/suspend` ·
`POST /products/v1/{id}/reinstate`

### 1.1 Current ambiguity

Five `(record_type, action)` pairs reach `resolve_signature_requirement()` with **no seeded
policy row**, so every call fails closed with `SIGNATURE_POLICY_UNRESOLVED` (409). Three of the
five have an explicit Document 106 §9 row; two do not. Two independent sub-questions:

1. **Is Document 106 §9 ratified?** The document is headed "v1.0 APPROVED / construction
   baseline", but §3 and §8 are marked "(proposed)"/"(PROPOSED)", §16 instructs implementers to
   treat any PROPOSED point as unapproved and reference **SG-004**, and the §17 approval block
   (Head of Quality / Regulatory Affairs / Product Owner) is **blank**. SG-004 is recorded
   `RESOLVED_APPROVED_2026-08-21` at the construction-baseline level; a formal Part 11 approval
   record against §9 has not been captured.
2. **How does an abstract signer *class* map to a concrete platform *role*?** Document 106 §4:
   "Customer role names are configuration; the signer **class** is the contract." Engineering has
   already applied a consistent mapping for ~40 seeded rows (§1.7 below); it has not been
   ratified.

### 1.2 Per-pair position against Document 106 §9

| # | Platform pair | Doc 106 §9 | Meaning | Signer class (verbatim) | Count | Independence (verbatim) | Reason | Kind |
|---|---|---|---|---|---|---|---|---|
| 1 | `vault_object` / `release` | **Row 2** | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes | **A** |
| 2 | `rule` / `release` | **Row 6** | `Released` | QA Approver / Batch Release | 1 | MUST be independent of every production performer on the record | yes | **A** |
| 3 | `product_version` / `suspend` | **Row 9** | `Performed` | Authorized holder (Production / QA) | 1 | None | yes | **A** |
| 4 | `record_correction` / `complete` | **Row 1** | `Approved` | Authorized corrector + independent approver | **2** | Corrector and approver MUST differ | yes (mandatory reason-for-change) | **B** — needs a 2-signature ceremony the platform does not implement |
| 5 | `product_version` / `reinstate` | **no row** | — | — | — | — | — | **B** — no signature point exists; §8 family "resume / unhold / release-hold" is the nearest PROPOSED default |

### 1.3 Available options

**For pairs 1–3 (Kind A):**
- **(A1)** Ratify Document 106 §9 rows 2 / 6 / 9 and the class→role mapping in §1.7; engineering
  seeds the three rows exactly as the register states them. *Supported by Document 106 §9.*
- **(A2)** Quality supplies a different meaning / signer class / independence / reason for any of
  the three (overrides the register).
- **(A3)** Leave one or more unresolved (the action stays blocked for all actors).

**For pair 4 `record_correction/complete` (Kind B):**
- **(B4a)** Approve a **two-signature** ceremony (corrector + independent approver, per §9 row 1
  and §8 "correct / amend" family) — requires an engineering change to add
  `signature_count` / ordered-chain support to `SignaturePolicy` and the Mutation Gateway,
  then seed the row.
- **(B4b)** Approve a **single** `Approved` signature by an independent approver as an interim
  platform floor (weaker than §9 row 1's Count = 2; would need to be recorded as a deliberate
  deviation from the register under SIGP-FR-002).
- **(B4c)** Leave unresolved — record correction completion stays blocked.

**For pair 5 `product_version/reinstate` (Kind B):**
- **(B5a)** Author a new Document 106 signature point for `product reinstate`. The §8 PROPOSED
  family default for "resume / unhold / release-hold" is: meaning `Approved`, signer "QA
  authority that owns the hold reason", independence "MUST be independent of the person who
  caused the condition where configured", reason "yes". Quality confirms or amends, then it is
  seeded.
- **(B5b)** Decide `reinstate` requires **no** signature (record as a §10 "explicitly NOT
  requiring a signature" addition). *This is an affirmative regulated decision; engineering
  cannot make it.*
- **(B5c)** Leave unresolved — reinstate stays blocked.

### 1.4 Engineering recommendation (only where the specification supports one)

- **Pairs 1–3:** recommend **(A1)** — the values are stated verbatim in Document 106 §9 and the
  class→role mapping is the one already in force for ~40 rows.
- **Pair 4:** recommend **(B4a)** — it matches Document 106 §9 row 1 and §8 exactly. **(B4b)** is
  offered only because it unblocks sooner; it is a documented weakening and needs explicit
  Quality acceptance.
- **Pair 5:** **no recommendation.** Document 106 has no signature point for `reinstate`; the §8
  family default is *PROPOSED* and not clearly on point. This is an authoring decision for
  Quality.

### 1.5 Exact decision required from Quality / PO

1. **Ratify (or amend) Document 106 §9 rows 1, 2, 6, 9** and record the Part 11 approval against
   §9 (closes the SG-004 residual for these points).
2. **Ratify the abstract-class → platform-role mapping** in §1.7 (or supply corrections).
3. For **pair 4**: choose **B4a / B4b / B4c**.
4. For **pair 5**: choose **B5a** (and give the meaning / signer / independence / reason) **/
   B5b / B5c**.

### 1.6 System behaviour after approval

| Pair | Before | After |
|---|---|---|
| `vault_object/release` | 409 `SIGNATURE_POLICY_UNRESOLVED` on every call | issues a `Released` challenge; commit requires a valid signature by the mapped role, independent of every production performer; reason mandatory |
| `rule/release` | 409 | same shape as `vault_object/release` |
| `product_version/suspend` | 409 | issues a `Performed` challenge; signature by an authorised holder (RBAC-gated); reason mandatory; no independence check |
| `record_correction/complete` | 409 | **B4a**: two ordered challenges (corrector, then independent approver); **B4b**: one `Approved` challenge, independent approver; **B4c**: unchanged |
| `product_version/reinstate` | 409 | **B5a**: challenge per the approved meaning; **B5b**: proceeds with no signature (audit only); **B5c**: unchanged |

No other action changes. Batch release, material-lot disposition, recipe release,
product-version release and the ~40 already-seeded rows are unaffected.

### 1.7 How the approved decision is applied

For every ratified Kind-A pair, engineering adds **one line** to `SIGNATURE_POLICY_FLOOR` in
`services/gxp-api/scripts/seed.py`, using the class→role mapping below:

| Doc 106 signer class (verbatim) | Platform `required_role_name` | `independent` | Precedent already seeded |
|---|---|---|---|
| QA Approver / Batch Release | `QA Releaser` | `True` | `batch/release` (§9 33/34), `oos_record/disposition` (§9 67), `material_lot/release` (§9 45) |
| QA Approver for the record class | `QA Releaser` | `True` | `oos_record/close` (§9 66), `security_incident/close` (§9 140) |
| QA Reviewer | `QA Reviewer` | `True` | `batch/review` (§9 25), `qc_test_order/review` (§9 61) |
| Qualified independent verifier | `None` (perf ≠ verifier checked in code) | `True` | `reconciliation_record/verify` (§9 40), `cleaning_execution/verify` (§9 110) |
| Authorized holder (Production / QA) | `None` (RBAC `*.hold`/`*.suspend`) | `False` | `equipment_asset/hold` (§9 108), `batch_step/hold` |
| Module approver role (QA Manager / Head of Quality) | `QA Releaser` | `True` | `supplier_qualification/approve` (§9 43) |

Concrete lines that **would** be added for pairs 1–3 under option (A1) — shown for review, **not
yet committed**:

```python
("vault_object",     "release", "Released",  "QA Releaser", True,  True, True),   # Doc 106 §9 row 2
("rule",             "release", "Released",  "QA Releaser", True,  True, True),   # Doc 106 §9 row 6
("product_version",  "suspend", "Performed", None,          False, True, True),   # Doc 106 §9 row 9
```

(The `independent=True` flag on the two `Released` rows is enforced in the owning command
against the record's `Created` audit event — the same bespoke pattern already used for
`product_version/release` and `recipe_version/release`, because `resolve_signature_requirement()`
does not itself read `required_role_id` / `requires_independent_signer`.)

Then engineering runs the sync script (§5) against each deployment and re-runs the affected
test suites (`test_vault.py`, `test_rules.py`, `test_product_master.py`) to confirm the gate
now issues and accepts a valid challenge, and captures the PASS evidence.

### 1.8 What must NOT be changed without approval

- **No row is seeded** for any of the five pairs until the corresponding decision above is
  ratified in writing.
- **No `signature_required=False` row** is added for any pair (that is the affirmative
  "no signature needed" decision, reserved to Quality — SIGP-FR-002 / principle P3).
- The **fail-closed behaviour** (`SIGNATURE_POLICY_UNRESOLVED`) is not removed, bypassed, or
  downgraded to a warning (principle P8, SIGP-FR-004).
- The class→role mapping is **not** silently changed for the ~40 already-seeded rows.
- `record_correction/complete` is **not** given a single-signature row without an explicit
  **B4b** acceptance recorded as a deviation from Document 106 §9 row 1.

---

## 2. SG-138 — WP-05 QMS signature-policy rows (24 pairs)

**Gap ID:** SG-138 &nbsp;·&nbsp; **Class:** R
**Owner:** Head of Quality (approver) + Regulatory Affairs + QMS module owner
**Affected requirements:** SIGP-FR-004; Documents 26–37 (SPEC-QMS-001…012) disposition/close/verify/approve actions
**Engineering half:** already complete — all 14 `signature-challenges` endpoints exist
(`app/modules/qms/signature_support.py`); the `training_assignment/create` ordering bug is fixed.
**Policy-data half:** open — the 24 pairs below have no seeded row.

> `deviation_record/disposition` and `deviation_record/close` were resolved 2026-09-09 by
> project-owner direction against Document 106 §9 rows 73 / 71. The 24 pairs here are everything
> else in SG-138.

### 2.1 Current ambiguity

Identical in shape to SG-035: (1) is Document 106 §9 (rows 70–107) ratified, and (2) how does
each abstract signer class map to a platform role. Every QMS command already calls
`resolve_signature_requirement()`; with no row, all 24 transitions fail closed with
`SIGNATURE_POLICY_UNRESOLVED` and **cannot be completed by any actor**.

### 2.2 Per-pair position against Document 106 §9

**Kind A — an explicit §9 row exists (21 pairs):**

| Platform `(record_type, action)` | Doc 106 §9 | Meaning | Signer class (verbatim) | Indep. | Reason |
|---|---|---|---|---|---|
| `capa_record` / `close` | Row 80 | `Approved` | QA Approver for the record class | independent of investigator/owner | yes |
| `nonconformance_record` / `disposition` | Row 84 | `Released` | QA Approver / Batch Release | indep. of every production performer | yes |
| `nonconformance_record` / `verify` | Row 85 | `Verified` | Qualified independent verifier | MUST NOT be the performer | no |
| `nonconformance_record` / `close` | Row 83 | `Approved` | QA Approver for the record class | independent of investigator/owner | yes |
| `change_control` / `approve` | Row 86 | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | independent of the author | yes |
| `change_control` / `verify` | Row 88 | `Verified` | Qualified independent verifier | MUST NOT be the performer | no |
| `change_control` / `close` | Row 87 | `Approved` | QA Approver for the record class | independent of investigator/owner | yes |
| `complaint_record` / `reportability` | Row 102 | `Approved` | Regulatory Affairs authorized submitter | human only (SIG-FR-023) | yes |
| `complaint_record` / `close` | Row 101 | `Approved` | QA Approver for the record class | independent of investigator/owner | yes |
| `scar_record` / `review` | Row 96 | `Reviewed` | QA Reviewer | independent of the performer | no |
| `scar_record` / `close` | Row 95 | `Approved` | QA Approver for the record class | independent of investigator/owner | yes |
| `field_action` / `reportability` | Row 105 | `Approved` | Regulatory Affairs authorized submitter | human only (SIG-FR-023) | yes |
| `field_action` / `approve` | Row 103 | `Approved` | Module approver role (QA Manager / Head of Quality per record class) | independent of the author | yes |
| `field_action` / `close` | Row 104 | `Approved` | QA Approver for the record class | independent of investigator/owner | yes |
| `internal_audit` / `start` | Row 99 | `Performed` | Production Supervisor or qualified issuer | None | no |
| `internal_audit` / `close` | Row 98 | `Approved` | QA Approver for the record class | independent of investigator/owner | yes |
| `audit_finding` / `verify` | Row 100 | `Verified` | Qualified independent verifier | MUST NOT be the performer | no |
| `controlled_document_version` / `release` | Row 89 | `Released` | QA Approver / Batch Release | indep. of every production performer | yes |
| `risk_record` / `review` | Row 97 | `Reviewed` | QA Reviewer | independent of the performer | no |
| `quality_metric_definition` / `release` | Row 106 | `Released` | QA Approver / Batch Release | indep. of every production performer | yes |
| `quality_metric_snapshot` / `management_review` | Row 107 | `Reviewed` | QA Reviewer | independent of the performer | no |

**Kind B — Document 106 explicitly defers (3 pairs):**

| Platform `(record_type, action)` | Doc 106 §9 | Meaning | Signer class | Indep. | Reason |
|---|---|---|---|---|---|
| `training_assignment` / `create` | Row 91 | `per challenge` | **Per policy lookup** | Per policy lookup | per policy |
| `training_assignment` / `complete` | Row 93 | `per challenge` | **Per policy lookup** | Per policy lookup | per policy |
| `training_assignment` / `assess` | Row 92 | `per challenge` | **Per policy lookup** | Per policy lookup | per policy |

### 2.3 Available options

**Kind A (21 pairs):**
- **(A)** Ratify Document 106 §9 rows 80–107 (the subset above) + the class→role mapping in §1.7;
  engineering seeds all 21 rows as the register states them. *Supported by Document 106 §9.*
- **(B)** Quality amends any specific row.
- **(C)** Leave any pair unresolved (that QMS transition stays blocked).
- **(D)** Seed `signature_required=False` for any pair — **rejected by SG-138's own analysis**:
  it is an affirmative decision that a QMS disposition / close needs no signature, which no
  approver has made, and it would commit product dispositions and recall approvals unsigned.

**Kind B — `training_assignment` (3 pairs):** Document 106 does not supply a value. Options:
- **(B-i)** Quality specifies the meaning / signer class / independence / reason for each of
  create / complete / assess (a Document 106 addendum or a `sig_policy_set` authoring action).
- **(B-ii)** Decide training assignment/complete/assess require no signature (record under §10).
- **(B-iii)** Leave unresolved — training assignment lifecycle stays blocked at these points.

### 2.4 Engineering recommendation

- **Kind A (21 pairs):** recommend **(A)** — verbatim from Document 106 §9, mapping already in
  force. Two mapping notes for Quality to confirm explicitly:
  - "Module approver role (QA Manager / Head of Quality per record class)" (`change_control/approve`,
    `field_action/approve`) → `QA Releaser`, matching the seeded precedent
    `supplier_qualification/approve` (§9 row 43). Confirm or supply a distinct QA-Manager role.
  - "Regulatory Affairs authorized submitter" (`complaint_record/reportability`,
    `field_action/reportability`) → the platform role `Postmarket Regulatory Affairs`
    (seeded for the WP-09 regulatory rows). Confirm. **Regulatory Affairs co-approval required
    for these two.**
- **Kind B (`training_assignment` ×3):** **no recommendation** — Document 106 defers the value;
  it is Quality's to author.

### 2.5 Exact decision required from Quality / PO

1. **Ratify (or amend) the 21 Document 106 §9 rows enumerated in the §2.2 Kind-A table**
   (rows 80, 83, 84, 85, 86, 87, 88, 89, 95, 96, 97, 98, 99, 100, 101, 102, 103, 104, 105,
   106, 107) and record the Part 11 approval.
2. **Confirm the two mapping calls** in §2.4 (QA-Manager class, Regulatory-Affairs class).
   Regulatory Affairs co-signs for the two reportability pairs.
3. For **`training_assignment` create / complete / assess**: choose **B-i** (and give the four
   values for each) **/ B-ii / B-iii**.
4. Confirm whether the `Verified` pairs (`nonconformance_record/verify`, `change_control/verify`,
   `audit_finding/verify`) enforce independence in code against the performer identity
   (engineering will implement the check against each record's own performer column, matching
   the seeded `reconciliation_record/verify` pattern) — or whether Quality wants a named role.

### 2.6 System behaviour after approval

Each ratified pair moves from "409 `SIGNATURE_POLICY_UNRESOLVED`, transition impossible" to
"issues a challenge with the approved meaning; commit requires a valid signature by the mapped
role, with the approved independence check; reason mandatory where the row says yes". The 14
`signature-challenges` endpoints already exist, so no new endpoint work is needed for Kind A.
`training_assignment` behaviour changes only per the option chosen in §2.5.3.

### 2.7 How the approved decision is applied

One `SIGNATURE_POLICY_FLOOR` line per ratified pair in `scripts/seed.py`, e.g. (shown for
review, **not committed**):

```python
("capa_record",                 "close",             "Approved", "QA Releaser", True,  True, True),   # Doc 106 §9 row 80
("nonconformance_record",        "disposition",       "Released", "QA Releaser", True,  True, True),   # §9 row 84
("nonconformance_record",        "verify",            "Verified", None,          True,  True, False),  # §9 row 85
("change_control",               "approve",           "Approved", "QA Releaser", True,  True, True),   # §9 row 86
("controlled_document_version",  "release",           "Released", "QA Releaser", True,  True, True),   # §9 row 89
("risk_record",                  "review",            "Reviewed", "QA Reviewer", True,  True, False),  # §9 row 97
("internal_audit",               "start",             "Performed", None,         False, True, False),  # §9 row 99
("complaint_record",             "reportability",     "Approved", "Postmarket Regulatory Affairs", False, True, True),  # §9 row 102
# ... 13 more, one per ratified pair ...
```

Independence for pairs whose `resolve_signature_requirement()` does not read the role/independence
columns is enforced in `app/modules/qms/commands.py` against each record's own
investigator/owner/performer identity column — the pattern already used for
`deviation_record/disposition+close`. Then: run `sync_signature_policies.py` (§5), execute the
per-module QMS test suites, capture PASS evidence, and update SG-138 to `RESOLVED` (or
`PARTIALLY_RESOLVED` if `training_assignment` is left open).

### 2.8 What must NOT be changed without approval

- No QMS row is seeded until §9 rows 80–107 are ratified.
- No `signature_required=False` row for any QMS disposition, close, verify, approve or
  reportability action (SG-138 option D — reserved to Quality).
- The `training_assignment` pairs are **not** seeded from the §8 platform-floor family or any
  analogous row — Document 106 says "per policy lookup", which means Quality authors it.
- Fail-closed behaviour is not removed or downgraded.
- The abstract-class → role mapping is not applied to `training_assignment` or to any pair
  Quality amends.

---

## 3. SG-167 — SPEC-AI-001 signature-policy rows (5 pairs)

**Gap ID:** SG-167 (canonical; code comments citing "SG-168" describe the same gap)
**Class:** R &nbsp;·&nbsp; **Owner:** Head of Quality (approver) + Security Owner + AI-governance module owner
**Affected requirements:** SIGP-FR-004; Document 105 AI-FR-006/007/009/010/034/054
**Engineering half:** complete — `content_challenge_hash()` fix landed; the 5
`POST /ai-governance/v1/{resource}/signature-challenges` endpoints exist.
**Policy-data half:** open — **Document 106 has zero SPEC-AI-001 rows.**

### 3.1 Current ambiguity

Document 106 §2 scope is "every state-changing regulated operation exposed by **Documents
03–60**". **Document 105 (SPEC-AI-001) is outside that range.** The Signature Point Register
(§9) therefore contains **no** `ai_model_deployment` / `ai_tool_call` / `ai_disposition` /
`ai_release_gate` / `ai_provider_switch` entry, and no §8 family was written with AI-governance
actions in mind. All 5 signed AI-governance functions fail closed with
`SIGNATURE_POLICY_UNRESOLVED` on every invocation.

This is **Kind B for all five pairs** — there is no existing baseline content to ratify.
Document 106 must be **extended**.

| Platform `(record_type, action)` | Function | Nearest §8 PROPOSED family (for reference only) |
|---|---|---|
| `ai_model_deployment` / `approve` | `approveAIModelDeployment` | "approve / approval / authoriz" → `Approved` / Module approver / indep. of author / reason yes |
| `ai_tool_call` / `authorize` | `authorizeAIToolCall` | "approve / approval / authoriz" → as above |
| `ai_disposition` / `record` | `recordHumanAIDisposition` | "complete / record / result …" → `Performed` / qualified performer / none / reason no |
| `ai_release_gate` / `evaluate` | `evaluateAIReleaseGate` | "release / disposition / certif" → `Released` / QA Approver / indep. of every production performer / reason yes |
| `ai_provider_switch` / `switch` | `switchAIProviderProfile` | (no clear family) |

The §8 mappings above are **illustrative context only** — §8 is PROPOSED, was not authored for
AI governance, and engineering is **not** proposing to adopt them.

### 3.2 Available options

- **(A)** **Extend Document 106** with five new Signature Point Register rows (a Document 106
  v1.1 addendum, or a released `sig_policy_set` authoring action per §5). Quality + Security
  Owner specify, for each of the five: meaning (SIG-FR-003 value), signer class → platform role,
  independence rule, reason-required. Engineering then seeds them.
- **(B)** Decide that one or more of the five require **no** signature and record each under
  Document 106 §10 ("explicitly NOT requiring a signature"). *Affirmative regulated decision —
  Quality's to make.* Note AG-14 / Document 105: AI is advisory; a human still executes the
  underlying action through the normal path, so Quality may reasonably conclude some of these
  are governance-config changes rather than Part 11 signature points.
- **(C)** Leave unresolved — the 5 AI-governance signed functions stay blocked (current state;
  does not block any non-AI workflow).

### 3.3 Engineering recommendation

**No recommendation on the values.** Document 106 contains nothing to ratify for SPEC-AI-001,
and CLAUDE.md §4 + AG-15 forbid engineering from choosing a meaning, signer class or
independence rule. Engineering's only recommendation is **procedural**: resolve this as a
Document 106 v1.1 addendum so the AI rows sit in the same controlled register as every other
signature point, with the same SG-004-style approval record.

### 3.4 Exact decision required from Quality / PO (+ Security Owner)

For **each** of the five pairs, one of:
- a full row: `meaning` (from SIG-FR-003) · signer class + platform role · independence rule ·
  reason-required (yes/no); **or**
- an explicit "no signature required" decision recorded under Document 106 §10.

### 3.5 System behaviour after approval

| Option chosen for a pair | Behaviour |
|---|---|
| Full row (A) | the `signature-challenges` endpoint issues a challenge with the approved meaning; the command commits only after a valid signature by the approved role with the approved independence check |
| No signature (B) | the command commits after RBAC + qualification checks only; no challenge; audit records the action as unsigned |
| Unresolved (C) | unchanged — 409 `SIGNATURE_POLICY_UNRESOLVED` |

### 3.6 How the approved decision is applied

For each pair given a full row, engineering adds one `SIGNATURE_POLICY_FLOOR` line in
`scripts/seed.py` with the approved values, runs `sync_signature_policies.py` (§5), and
executes `tests/test_ai_governance.py` to confirm the challenge path now works end-to-end.
For each "no signature" pair, engineering sets `signature_required=False` **only against the
written §10 decision** and records it in the row comment. SG-167 then moves to `RESOLVED`.

### 3.7 What must NOT be changed without approval

- **No AI-governance row is seeded** — with any value, including `signature_required=False` —
  until Document 106 is extended or a §10 decision is recorded.
- The §8 PROPOSED family defaults are **not** adopted as a substitute for an authored AI row.
- AI identity / service identity is never a signer (SIGP-FR-008, AG-14, Document 105 AI-FR-006)
  — this constraint stands regardless of the decision.
- Fail-closed behaviour is retained until a row or a §10 decision exists.

---

## 4. SG-145 — Document 110 §2 "(PROPOSED)" calculation-class table

**Gap ID:** SG-145 &nbsp;·&nbsp; **Class:** R &nbsp;·&nbsp; **Owner:** Head of Quality + Product Owner (Document 110's named approvers)
**Affected requirements:** CALC-FR-004, CALC-FR-012
**`blocking`:** false — blocks **VALIDATED release** of the calculation-class code paths, **not**
`CODE_COMPLETE`.

### 4.1 Current ambiguity

Document 110 is headed "APPROVED v1.0 (construction baseline) — approvers of record: Head of
Quality and Product Owner". Every section reads as approved **except §2**, headed "Calculation
classes and default policy **(PROPOSED)**" — the ten-row table that fixes storage precision,
rounding mode, rounding stage and comparison rule for calculation classes CC-1…CC-10. No other
section carries a status qualifier, and the §10 approval block (Head of Quality / Product Owner)
is **blank**. §2 is the **only** numeric precision policy anywhere in the approved baseline.

Engineering has implemented §2 **verbatim** in `app/modules/rules/precision.py`
(`CLASS_POLICY` / `resolve_class_policy`) as the construction baseline — SG-143 is
`RESOLVED` on that basis. `precision_policy.calculation_class` is required at rule-draft time
and unresolved/unknown classes fail closed with `PRECISION_POLICY_UNRESOLVED` (409).

### 4.2 The content awaiting ratification (Document 110 §2, verbatim)

| Class | Storage precision | Rounding mode | Rounding stage | Comparison rule |
|---|---|---|---|---|
| CC-1 Mass/weight capture | instrument resolution, as captured (min 4 dp) | none at capture | capture only | compare at instrument resolution |
| CC-2 Volume capture | as captured (min 4 dp) | none at capture | capture only | as captured |
| CC-3 Tolerance evaluation | 6 dp intermediate | half-up | at comparison only | policy states inclusive/exclusive bounds |
| CC-4 Yield / reconciliation | 6 dp intermediate, 2 dp reported | half-up | at each declared checkpoint and at presentation | limit inclusive unless stated |
| CC-5 Concentration / potency | 6 dp intermediate, source-specified reported dp | half-up | at reported precision | per specification method |
| CC-6 Count / units | integer | n/a | n/a | exact equality |
| CC-7 Time / duration | seconds (UTC-based) | none | n/a | inclusive of declared boundary |
| CC-8 Environmental | source resolution | none at capture | comparison only | per method/limit definition |
| CC-9 Statistical / trending | 6 dp internal, 4 dp reported | half-even (banker's) | at report generation | advisory only; never a release decision alone |
| CC-10 Financial/commercial | per ERP contract | per ERP contract | at integration boundary | not a GxP decision path |

### 4.3 Available options

- **(A)** Head of Quality + Product Owner issue a **Part 11 approval record against §2
  specifically**, using the table as implemented in `precision.py` as the reviewed artefact.
  Change to §2 thereafter is a controlled Document 110 revision (CALC-FR-012). *Recommended in
  SG-145.*
- **(B)** Treat the "(PROPOSED)" heading as a **documentation defect** (the document was approved
  as a whole) and formally strike it in a **Document 110 v1.1 erratum**.
- **(C)** Leave §2 unresolved and gate VALIDATED release of every CC-1…CC-10-governed code path
  (yield, potency, tolerance, reconciliation variance, release eligibility) on manual QA
  sign-off per deployment until a formal record exists.

### 4.4 Engineering recommendation

**(A) or (B)** — both produce a ratified §2 with no code change (the implementation already
matches §2 verbatim). **(A)** is the cleaner audit trail (an explicit Part 11 record against the
table). Engineering has no basis to prefer one over the other beyond that; the choice is
Quality's.

### 4.5 Exact decision required from Quality / PO

Either **(A)** sign a Part 11 approval record against Document 110 §2 as implemented, **or**
**(B)** issue a Document 110 v1.1 erratum striking "(PROPOSED)" from the §2 heading, **or**
**(C)** direct that CC-governed code paths remain gated on per-deployment manual sign-off.

### 4.6 System behaviour after approval

**No runtime behaviour changes.** `precision.py` already enforces §2. What changes is
validation status: the CC-1…CC-10 code paths become eligible for `OQ_EXECUTED` / `QUALIFIED` /
`RELEASED` (human-set stages) against an approved numeric policy instead of a proposed one.
Under **(C)**, those stages stay blocked pending per-deployment sign-off.

### 4.7 How the approved decision is applied

- **(A)/(B):** engineering updates the SG-145 entry to `RESOLVED`, references the approval
  record or erratum in `precision.py`'s module docstring and in
  `docs/generated/18_SPEC_GAPS.md`, and removes the "(PROPOSED)" caveat from the SG-143
  resolution note. **No functional code change.** `sync_signature_policies.py` is **not**
  involved (this is a precision policy, not a signature policy).
- **(C):** engineering records the per-deployment manual-sign-off gate as a release checklist
  item; no code change.

### 4.8 What must NOT be changed without approval

- The §2 values in `precision.py` (`CLASS_POLICY`) are **not** altered — not the rounding mode
  (half-up for regulated pass/fail; half-even only for CC-9 statistical aggregation), not the
  decimal places, not the rounding stage. Any change to a §2 value is a Document 110 revision
  and a revalidation trigger (Document 110 §7, Document 96).
- The `PRECISION_POLICY_UNRESOLVED` fail-closed path is retained.
- SG-143 is **not** reopened — it is resolved on the construction-baseline implementation;
  SG-145 governs only the approval *status* of §2.

---

## 5. `scripts/sync_signature_policies.py` — exact mechanism

This is the **only** approved way to apply a ratified signature-policy row to an already-seeded
deployment (`scripts/seed.py` upserts the same rows, but only inside a destructive fresh
org/site/user reseed, which cannot be run against a live database).

### 5.1 What it does

```
.venv/bin/python -m scripts.sync_signature_policies
```

1. Imports `SIGNATURE_POLICY_FLOOR` from `scripts/seed.py` (the single source of truth for the
   platform floor).
2. For each tuple `(record_type, action, meaning, role_name, independent, sig_required,
   reason_required)`:
   - resolves `role_name` → `iam.roles.id` in **this** deployment. If the role does not exist
     here, the row is **skipped** (counted, not an error) — same behaviour as
     `sync_permissions.py`.
   - looks up an existing `signature.signature_policies` row by `(record_type, action)`:
     - **absent** → inserts it with `policy_source = "PLATFORM_FLOOR"` → `created += 1`
     - **present and identical** → no-op
     - **present and different** → updates `meaning`, `required_role_id`,
       `requires_independent_signer`, `signature_required`, `reason_required` in place →
       `updated += 1`
3. Commits once, prints `signature policies: N created, M updated, K skipped (role not in this
   deployment), T total in floor`.

### 5.2 What it does NOT do

- **Never deletes a row.** Removing a signature-policy row flips a resolved action back to
  fail-closed (`SIGNATURE_POLICY_UNRESOLVED`) for every actor — the exact failure mode AG-07 /
  SIG-FR-004 exist to prevent by accident. A row that must be retired is a separate, reviewed
  action, not a sync.
- Does not touch `signature.signatures`, `audit.*`, or `vault.*` (append-only, AG-08).
- Does not create roles, permissions, or challenges.
- Does not read or modify `precision_policy` / calculation-class data (SG-145 is out of its
  scope entirely).

### 5.3 Execution order for a ratified batch

1. Engineering adds the approved tuple(s) to `SIGNATURE_POLICY_FLOOR` in `scripts/seed.py`,
   one line per ratified `(record_type, action)`, with a comment citing the Document 106 §9
   row number (or the addendum reference for SG-167).
2. Mirror the same tuple(s) into `services/gxp-api/tests/conftest.py`'s signature-policy seed
   list **only where no test already adds a conflicting local row** (several tests add their
   own per-test `signature_required=False` rows for unrelated setup and would collide on
   `UNIQUE (record_type, action)` — those tests are updated to use the real ceremony instead).
3. Run `sync_signature_policies.py` against each target database (`ebmr_new_gxp` demo, then any
   customer deployment) during a controlled change window.
4. Run the affected test suites, capture PASS/FAIL evidence, update
   `docs/generated/18_SPEC_GAPS.md` (SG-035 / SG-138 / SG-167 → `RESOLVED` or
   `PARTIALLY_RESOLVED`), update `traceability/TRACEABILITY_MASTER.csv` rows for the affected
   requirements, set module stages in `status/build-status.json`, and run
   `tooling/status/rollup.py`.

---

## 6. Global constraints — what engineering will NOT do regardless of ratification

These hold for every item above and are not negotiable at the engineering level:

1. **No signature requirement is hardcoded** in a domain service or resolved from a code
   conditional (SIGP-FR-001 / Document 106 §16). Every row lives in policy data.
2. **No customer or platform configuration weakens a floor** — cannot reduce signature count,
   weaken the signer class, or remove independence below the ratified floor (SIGP-FR-002,
   principle P3). `SIGNATURE_POLICY_BELOW_FLOOR` enforcement stays.
3. **Fail-closed stays fail-closed** — an unresolved policy for a regulated state change blocks
   the commit (`SIGNATURE_POLICY_UNRESOLVED`, principle P8, SIGP-FR-004). It is never downgraded
   to a warning or a default-allow.
4. **No signature record is created outside the Signature Service**; no authenticated session,
   API key, or payload flag is treated as a signature (Document 106 §16, AG-07).
5. **Service / integration / device / AI identity can never sign** (SIGP-FR-008, SIG-FR-023,
   AG-14).
6. **`meaning` is always a SIG-FR-003 catalogue value** — never free text (principle P4).
7. **Audit, signature and vault rows are append-only** — no `UPDATE` / `DELETE` (AG-08).
8. **No value is guessed or inferred from an endpoint name** (CLAUDE.md §4, AG-15). Where
   Document 106 / Document 110 supplies a value, engineering applies it verbatim after
   ratification; where it does not, engineering waits for Quality to author it.

---

## 7. Summary — what Quality / PO must return

| Item | Decision needed | Kind | Blocks |
|---|---|---|---|
| **SG-035 pairs 1–3** (`vault_object/release`, `rule/release`, `product_version/suspend`) | Ratify Doc 106 §9 rows 2/6/9 + class→role mapping | A | Vault master release, rule release, product suspend |
| **SG-035 pair 4** (`record_correction/complete`) | B4a (2-sig ceremony) / B4b (1-sig interim, recorded deviation) / B4c | B | Record-correction completion |
| **SG-035 pair 5** (`product_version/reinstate`) | B5a (author a row) / B5b (no signature, §10) / B5c | B | Product-version reinstate |
| **SG-138 Kind A** (21 QMS pairs) | Ratify the 21 Doc 106 §9 rows in the §2.2 Kind-A table + confirm 2 mapping calls (+ Reg. Affairs co-sign for the 2 reportability pairs) | A | 21 QMS disposition/close/verify/approve/review transitions |
| **SG-138 Kind B** (`training_assignment` create/complete/assess) | B-i (author 3 rows) / B-ii (no signature, §10) / B-iii | B | Training assignment lifecycle |
| **SG-167** (5 AI-governance pairs) | Extend Doc 106 with 5 rows (Quality + Security Owner) — or §10 "no signature" per pair | B | 5 signed AI-governance functions (no non-AI impact) |
| **SG-145** (Doc 110 §2) | A (Part 11 record against §2) / B (v1.1 erratum) / C (per-deployment manual gate) | A | VALIDATED release of CC-1…CC-10 code paths (not CODE_COMPLETE) |

Engineering will execute the ratified decisions **only** after they are recorded in writing,
following §5.3, and will report the PASS/FAIL evidence per CLAUDE.md §6.

---

## 8. Application log — decisions recorded and applied

**Decision of record — 2026-09-10, project owner:** *"ebmr-edhr … follow this docs and based on this
docs if you have not answer then ask me."* Plus the three answers captured via the decision prompt:
(1) do the full implementation now for the ~21 pairs Document 106 §9 specifies; (2) for the 3
class/RBAC-mismatch pairs, map to the Document 106 class and grant the missing RBAC permission;
(3) mark SG-145 approved (editorial), and defer `training_assignment` ×3, `record_correction/complete`,
`product_version/reinstate`, and SG-167 ×5. This is a project-owner **construction-baseline** decision;
the customer's formal QMS Part 11 signatures are still captured at PQ.

Execution is staged; each stage commits only when its own tests are green.

### Stage 1 — DONE (commit pending in this session)

| Item | Applied | Evidence |
|---|---|---|
| **SG-145** | Doc 110 §2 "(PROPOSED)" treated as an editorial artefact inside Document 110 v1.0 APPROVED. `18_SPEC_GAPS.md` SG-145 → `RESOLVED`; `app/modules/rules/precision.py` docstring updated. No functional code change. Customer Part 11 record against §2 still captured at PQ (Doc 110 §7). | `test_rules.py` green (part of the 57-pass run) |
| **SG-035 `product_version/suspend`** | Seeded verbatim from **Document 106 §9 row 9**: `("product_version","suspend","Performed",None,False,True,True)` — `Performed`, signer class "Authorized holder (Production / QA)" → role pair → `required_role_name=None` (RBAC `product.suspend` gates it), no independence, reason required. Added to `scripts/seed.py` `SIGNATURE_POLICY_FLOOR` + `tests/conftest.py`; `product_master/router.py` `signature-challenges` now accepts `action="suspend"`. No command change (`_transition_with_signature` already runs the ceremony). `sync_signature_policies.py` run against `ebmr_new_gxp`: **1 created, 84 total**. | `test_product_master.py` updated + green: unsigned suspend → `MISSING_SIGNATURE`/428; challenge+password suspend → 200, `lifecycle_state="suspended"`; `reinstate` still → `SIGNATURE_POLICY_UNRESOLVED`/409. Full run `test_product_master.py test_rules.py test_recipe_master.py test_release.py` = **57 passed / 0 failed** (6:39). |

**Still fail-closed after Stage 1** (verified in `ebmr_new_gxp`): `vault_object/release`,
`record_correction/complete`, `rule/release`, `product_version/reinstate`.

### Stages 2–5 — DONE (all committed 2026-09-10)

Shared mechanism: **`signature_service.enforce_signer_policy()`** (added to
`app/modules/signature/service.py`; re-exported from `app/modules/qms/signature_support.py` so the
12 QMS command modules' imports are unchanged) — the role + independence check that
`resolve_signature_requirement()` does not do, generalising the bespoke block already in
`close_deviation()` / `release_recipe_version()`. Where a record has no stored owner/performer identity
for the independence clause (`complaint_record`, `field_action`, `scar_record`,
`quality_metric_snapshot`, the generic `vault_object` release, `rule` release), **only the required
role is enforced and the independence gap is documented** — the same honest limitation already recorded
for `qa_review_package/complete`.

| Stage | Commit | Pairs applied (Doc 106 §9 row) | Live DB |
|---|---|---|---|
| **2a** | `6992774` | `capa_record/close` (80) | `sync_signature_policies.py` → 85 rows |
| **2b/2c** | `40e77a7` | `nonconformance_record/{disposition,verify,close}` (84/85/83), `change_control/{approve,verify,close}` (86/88/87) | → 91 rows |
| **3** | `8ef320b` | `scar_record/{review,close}` (96/95), `internal_audit/{start,close}` (99/98), `audit_finding/verify` (100), `complaint_record/{reportability,close}` (102/101), `field_action/{reportability,approve,close}` (105/103/104) | → 101 rows |
| **4** | `61f1dbb` | `controlled_document_version/release` (89), `risk_record/review` (97), `quality_metric_definition/release` (106), `quality_metric_snapshot/management_review` (107) | → 105 rows |
| **5** | `bf01d16` | **SG-035** `vault_object/release` (2), `rule/release` (6) | → 107 rows |

RBAC grants added (project-owner-directed "map to the Doc 106 class and grant the missing permission"):
`Postmarket Regulatory Affairs` role given `complaint.reportability` + `field_action.reportability`;
`QA Reviewer` given `quality_metric.management_review`; `QA Releaser` given `rules.release` (was
Admin-only). All mirrored in `scripts/seed.py` + `tests/conftest.py`; `sync_permissions.py` applied
them to `ebmr_new_gxp`.

New signature-challenge endpoints (routers that had none): `POST /rules/v1/{id}/signature-challenges`,
`POST /vault/v1/masters/{type}/{id}/signature-challenges`.

**SG-138 result: all 21 Document 106 §9 pairs it left open are applied.** Only the 3
`training_assignment` "per policy lookup" pairs remain (deferred below).
**SG-035 result: `product_version/{release,suspend}`, `recipe_version/release`, `vault_object/release`,
`rule/release` all resolved.** Only `record_correction/complete` and `product_version/reinstate` remain
(deferred below).

Per-stage tests (independent runs, each with an untouched-module control): 2a 45✓ · 2b/2c 61✓ · 3 91✓
(after a conftest `QA Reviewer` grant alignment + a `ScarRecord` identity-column fix) · 4 61✓ · 5 45✓
+ 1 pre-existing order-dependent isolation failure
(`test_vault.py::test_concurrent_release_same_business_id_raises_clean_conflict`, `assert 2 == 1` —
proven pre-existing on a clean tree in STEP 2; no signature path; passes in full-suite ordering).

### Deferred — documented, NOT applied (project-owner-directed 2026-09-10)

| Item | Reason | Register status |
|---|---|---|
| SG-035 `record_correction/complete` | Document 106 §9 row 1 requires **2 signatures** (corrector + independent approver); the platform has no 2-signature ceremony. | SG-035 OPEN for this pair |
| SG-035 `product_version/reinstate` | **No Document 106 row exists.** | SG-035 OPEN for this pair |
| SG-138 `training_assignment` create / complete / assess | Document 106 §9 rows 91–93 state **"per policy lookup"** — the document defers the value. | SG-138 OPEN for these 3 pairs |
| SG-167 — all 5 AI-governance pairs | Document 105 is outside Document 106 §2's "Documents 03–60" scope — **zero SPEC-AI-001 rows**. No non-AI impact. | SG-167 OPEN |
