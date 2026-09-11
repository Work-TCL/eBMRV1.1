# Phase 3 — Deferred Items Decision Request

**Prepared by:** Engineering (Claude Code)
**Date:** 2026-09-11
**Branch:** `wp15-phase3-deferred-decisions` (worktree `eBMR-new-p3remainder`, based on
`wp12-14-rbac-signature-fixes`)
**Status:** Phase 3 (`PHASE_3_QUALITY_HANDOFF.md`) applied every decision the project owner made
2026-09-10 and left **six items formally deferred**, documented in that file's §8 "Deferred —
documented, NOT applied" table and its per-item §1–§3 sections. This document is the follow-up
consolidated decision request for those six items. **Engineering has not seeded, guessed, or
inferred a value for any of them.**

All six currently fail closed with `SIGNATURE_POLICY_UNRESOLVED` (409) — verified against the code
in this worktree at commit `f730cae` (the shared `wp12-14-rbac-signature-fixes` HEAD at the time
this worktree was created). That is correct, tested behaviour per SIGP-FR-004 / AG-07, and it is a
hard stop for the affected actions until these decisions are ratified.

| Item | Gap ID | Record type / action | Kind | Blocks |
|---|---|---|---|---|
| **A** | SG-138 | `training_assignment` / `create`, `complete`, `assess` | B — Document defers the value | Training assignment lifecycle (Document 31) |
| **B** | SG-035 (pair 5) | `product_version` / `reinstate` | B — no Document 106 row exists | Product-version reinstate (Document 09, PRD-FR-029) |
| **C** | SG-167 | `ai_model_deployment/approve`, `ai_tool_call/authorize`, `ai_disposition/record`, `ai_release_gate/evaluate`, `ai_provider_switch/switch` | B — Document 105 outside Document 106 §2 scope | 5 AI-governance signed functions (no non-AI impact) |
| **D** | SG-035 (pair 4) | `record_correction` / `complete` | B — mechanism gap (needs a 2-signature ceremony the platform does not implement) | Record-correction completion (Document 06, VLT-FR-010/011) |
| **E** | SG-013 | 17 WP-06/07/08 API contracts | out of scope for this task | `contracts/openapi/.conformance-baseline` — mentioned only, not touched here |

Items A–D are examined below in the same format as `PHASE_3_QUALITY_HANDOFF.md`: current
ambiguity, options, recommendation *only* where Document 106 supports one, exact decision
required, behaviour after approval, how it is applied, and what must not change without approval.
Item E is out of scope; it is not re-analysed here.

---

## A. SG-138 — `training_assignment` / create, complete, assess

**Owner:** Head of Quality + QMS module owner
**Affected requirements:** SIGP-FR-004; Document 31 (SPEC-QMS-006) TRN-FR-003/006/007/008

### A.1 Where this lives in code

`services/gxp-api/app/modules/qms/training_commands.py`:

| Action | Literal `record_type`/`action` | Line | Record identity columns available |
|---|---|---|---|
| create | `"training_assignment"` / `"create"` | `training_commands.py:222` | `TrainingAssignment.subject_id` (the person being trained), `assigned_by_user_id` (who created the assignment) |
| complete | `"training_assignment"` / `"complete"` | `training_commands.py:280` | same, plus `trainer_user_id`, `equivalency_approved_by_user_id` |
| assess | `"training_assignment"` / `"assess"` | `training_commands.py:345` | same, plus `trainer_user_id` |

All three route through the shared `_resolve_and_consume_signature()` helper
(`training_commands.py:70-86`), which already calls
`signature_service.resolve_signature_requirement()` and fails closed identically to every other
signed command in the codebase. **No endpoint or command work is needed for any option below** —
only a `SIGNATURE_POLICY_FLOOR` row (or an explicit no-signature row, or nothing).

### A.2 Current ambiguity

Document 106 §9 rows 91–93 state, verbatim, meaning `per challenge`, signer class **"Per policy
lookup"**, independence **"Per policy lookup"**, reason **"per policy"**. This is not a value —
it is the document explicitly declining to state one and deferring it to a downstream policy
authority. §8's closest PROPOSED family ("complete / record / result / execute / perform /
confirm" → `Performed` / qualified performer / none / no) is for the generic completion family in
general, not authored with training-assignment SoD in mind, and it does not address `assess` at
all (`assess` is closer to "verify/review" territory — a second, independent check of the trainee's
competence — but no family says so).

### A.3 Available options

- **(A-i) Author values now.** Quality specifies, for each of create / complete / assess: meaning
  (a SIG-FR-003 catalogue value), signer class → platform role, independence rule, reason-required.
  A natural shape (for Quality to confirm or replace, not adopted by engineering):
  - `create`: who may assign training to a subject, and whether that needs a Part-11 signature at
    all (many QMS platforms treat assignment as an administrative act, not a quality decision).
  - `complete`: who attests the training happened — typically the trainee, the trainer, or both.
  - `assess`: who may record pass/fail — typically a qualified trainer/evaluator, independent of
    the trainee.
- **(A-ii) No signature required** for one, two, or all three (Document 106 §10 "explicitly NOT
  requiring a signature"). *Affirmative regulated decision — engineering cannot make it.*
- **(A-iii) Leave unresolved.** Training assignment lifecycle stays blocked at these points for
  every actor (current state).

### A.4 Engineering recommendation

**None.** Document 106 explicitly defers this value ("per policy lookup"); CLAUDE.md §4 and AG-15
forbid inferring it from the endpoint name or from the generic §8 family.

### A.5 Exact decision required

For **each** of `create` / `complete` / `assess`, one of:
- a full row (meaning · signer class + platform role · independence · reason-required), or
- an explicit "no signature" decision, or
- "leave unresolved."

### A.6 Behaviour after approval

| Action given a full row | Behaviour |
|---|---|
| Any of the three | issues a challenge with the approved meaning; the command commits only after a valid signature by the approved role, with the approved independence check; reason mandatory where the row says yes |
| "No signature" | commits after RBAC/qualification checks only; audit records the action as unsigned |
| Unresolved | unchanged — 409 `SIGNATURE_POLICY_UNRESOLVED` |

### A.7 How the approved decision is applied

One `SIGNATURE_POLICY_FLOOR` line per ratified action in `scripts/seed.py`, mirrored into
`tests/conftest.py`, applied to the live database only via `scripts/sync_signature_policies.py`
(never deletes a row) **after explicit confirmation it is safe to touch that database**, then
`tests/test_qms_training.py` (or the equivalent training test module) run and PASS evidence
captured, `docs/generated/18_SPEC_GAPS.md` / `traceability/TRACEABILITY_MASTER.csv` /
`status/build-status.json` updated, `rollup.py` run.

### A.8 What must NOT change without approval

- No row is seeded — including `signature_required=False` — until the decision above is recorded.
- The §8 PROPOSED generic family default is not silently adopted for any of the three actions.
- Fail-closed behaviour is not removed, bypassed, or downgraded to a warning.

---

## B. SG-035 (pair 5) — `product_version` / `reinstate`

**Owner:** Head of Quality + Product Owner
**Affected requirements:** SIGP-FR-004; Document 09 (SPEC-EBMR-000) PRD-FR-029

### B.1 Where this lives in code

`services/gxp-api/app/modules/product_master/commands.py:845` — `reinstate_product_version()`,
routed through the shared `_transition_with_signature()` (`commands.py:742`) with
`signature_action="reinstate"`. This is the exact same helper `suspend_product_version` uses —
`suspend` was resolved 2026-09-10 (Document 106 §9 row 9); `reinstate` was deliberately left open
because **no row names it**. No code change is needed for any option below; the endpoint
(`POST /products/v1/{product_version_id}/signature-challenges`) does not yet accept
`action="reinstate"` — that one-line addition happens only after ratification, same as it did for
`suspend`.

### B.2 Current ambiguity

Document 106 §9 has **no row** for `product_version/reinstate`. The nearest §8 PROPOSED family is
"resume / unhold / release-hold": meaning `Approved`, signer "QA authority that owns the hold
reason", independence "MUST be independent of the person who caused the condition where
configured", reason "yes". This family was written generically (it also covers e.g. `batches/{id}
/resume`, already an approved §9 row 17 using the identical text) — but §8 itself is headed
PROPOSED, and no §9 entry says it applies to product-version reinstatement specifically.

### B.3 Available options

- **(B-i) Author a new Document 106 §9 row for `product_version/reinstate`,** using the §8
  "resume/unhold" family text as the starting point (meaning `Approved`, signer "QA authority that
  owns the hold reason", independent of whoever suspended it, reason yes) — Quality confirms or
  amends.
- **(B-ii) Decide `reinstate` requires no signature** (Document 106 §10). *Affirmative regulated
  decision — engineering cannot make it.*
- **(B-iii) Leave unresolved.** `reinstate` stays blocked (current state).

### B.4 Engineering recommendation

**None on the value.** The §8 family is PROPOSED and was not authored with product-version
reinstatement specifically in mind — noting only, for reference, that Document 106 §9 row 17
(`batches/{id}/resume`) already uses that exact family verbatim for an analogous "undo a hold"
action, which is the closest existing precedent if Quality chooses (B-i).

### B.5 Exact decision required

B-i (with meaning/signer/independence/reason given or confirmed) / B-ii / B-iii.

### B.6 Behaviour after approval

| Option | Behaviour |
|---|---|
| B-i | `POST /products/v1/{id}/signature-challenges` accepts `action="reinstate"`; reinstate issues a challenge with the approved meaning, commits only after a valid signature meeting the approved role/independence |
| B-ii | reinstate proceeds with RBAC checks only; audit records it unsigned |
| B-iii | unchanged — 409 `SIGNATURE_POLICY_UNRESOLVED` |

### B.7 How the approved decision is applied

One `SIGNATURE_POLICY_FLOOR` line, mirrored into `tests/conftest.py`, the
`signature-challenges` endpoint's `action` allow-list extended by one value,
`scripts/sync_signature_policies.py` run against the live database only after explicit
confirmation, `test_product_master.py` updated (unsigned reinstate → `MISSING_SIGNATURE`/428,
challenge+password reinstate → success) and run for PASS evidence, tracking files updated.

### B.8 What must NOT change without approval

- No row seeded (including `signature_required=False`) until ratified.
- The §8 "resume/unhold" family is not applied by inference alone — Quality must affirm it applies
  to this specific action, or supply a different value.
- `product_version/suspend` (already resolved) is not touched.

---

## C. SG-167 — 5 AI-governance signature pairs

**Owner:** Head of Quality + Security Owner + AI-governance module owner
**Affected requirements:** SIGP-FR-004; Document 105 (SPEC-AI-001) AI-FR-005/007/009/010/021/034/054

### C.1 Where this lives in code

`services/gxp-api/app/modules/ai_governance/commands.py` — all five already call
`signature_service.resolve_signature_requirement()` and the 5
`POST /ai-governance/v1/{resource}/signature-challenges` endpoints already exist
(`app/modules/ai_governance/router.py`). No endpoint work needed for any option.

| Platform `(record_type, action)` | Function | Line |
|---|---|---|
| `ai_model_deployment` / `approve` | `approve_ai_model_deployment` | `commands.py:289` |
| `ai_tool_call` / `authorize` | `authorize_ai_tool_call` | `commands.py:579` |
| `ai_disposition` / `record` | `record_human_ai_disposition` | `commands.py:634` |
| `ai_release_gate` / `evaluate` | `evaluate_ai_release_gate` | `commands.py:748` |
| `ai_provider_switch` / `switch` | `switch_ai_provider_profile` | `commands.py:866` |

### C.2 Current ambiguity

Document 106 §2 scope is "every state-changing regulated operation exposed by **Documents
03–60**." Document 105 is outside that range — the Signature Point Register (§9) contains **zero**
SPEC-AI-001 rows, and no §8 family was written with AI-governance actions in mind. This is Kind B
for all five pairs: there is nothing in the existing baseline to ratify: Document 106 must be
**extended**.

### C.3 Available options

- **(C-i) Extend Document 106** with five new §9 rows (a v1.1 addendum, or a released
  `sig_policy_set` authoring action per §5). Quality + Security Owner specify, per pair: meaning ·
  signer class → platform role · independence · reason-required.
- **(C-ii) Decide one or more of the five need no signature**, recorded under §10. Note AG-14 /
  Document 105: AI is advisory only — a human still executes the underlying action through the
  normal (already-signed, where applicable) path, so Quality may reasonably conclude some of these
  are governance-configuration changes rather than Part 11 signature points, rather than a
  weakening of anything.
- **(C-iii) Leave unresolved.** All five stay blocked (current state; no non-AI workflow is
  affected either way).

### C.4 Engineering recommendation

**No recommendation on the values** — Document 106 has nothing to ratify for SPEC-AI-001 and
CLAUDE.md §4 / AG-15 forbid choosing a meaning, signer class or independence rule. The only
procedural recommendation is to resolve this as a controlled Document 106 v1.1 addendum, so these
five rows sit in the same governed register as every other signature point rather than as a
one-off carve-out.

### C.5 Exact decision required

For each of the five pairs: a full row, or an explicit §10 "no signature" decision, or
"leave unresolved."

### C.6 Behaviour after approval

Identical shape to items A/B: a full row makes the action's challenge endpoint issue a real
challenge and the command commit only after a valid, correctly-independent signature; "no
signature" commits after RBAC checks with an unsigned audit record; "unresolved" stays 409.

### C.7 How the approved decision is applied

One `SIGNATURE_POLICY_FLOOR` line per ratified pair, mirrored into `tests/conftest.py`,
`scripts/sync_signature_policies.py` run against the live database only after explicit
confirmation, `tests/test_ai_governance.py` run for PASS evidence, tracking files updated. AI /
service identity is never a signer regardless of the decision (SIGP-FR-008, AG-14) — this is not
open for negotiation and is unaffected by any of the three options.

### C.8 What must NOT change without approval

- No AI-governance row is seeded, with any value, until Document 106 is extended or a §10 decision
  is recorded.
- The §8 PROPOSED family text shown in `PHASE_3_QUALITY_HANDOFF.md` §3.1 for reference is not
  adopted as a substitute for an authored row.

---

## D. SG-035 (pair 4) — `record_correction` / `complete` — ENGINEERING BUILD

**Owner:** Head of Quality + Product Owner (decision to proceed); Engineering (build, once
greenlit)
**Affected requirements:** SIGP-FR-001/002/004/006/007; Document 06 (SPEC-GXP-004) VLT-FR-010/011;
Document 04 SIG-FR-004 (multi-signature ordering); Document 106 §9 row 1

This is the one item where Document 106 is unambiguous about the *value* — the blocker is that the
**platform has no mechanism** to enforce a 2-signature ordered chain. This section scopes the
build; it is not started until greenlit.

### D.1 What Document 106 §9 row 1 states (verbatim)

`POST /vault/v1/corrections/{id}/complete` → meaning `Approved` · signer class "Authorized
corrector + independent approver" · **count 2** · independence "Corrector and approver MUST
differ" · reason "yes (mandatory reason-for-change)". Document 106 §5's `sig_policy` data model
defines `signature_count` (1–4, checked) and `signature_order` (jsonb, ordered signer classes when
count > 1) for exactly this case; §7 SIGP-FR-007 "Ordered chains: where count > 1, order is
enforced server-side"; §13 test #5 "second signer signs before first → rejected."

### D.2 What already exists in code (narrower gap than `PHASE_3_QUALITY_HANDOFF.md` assumed)

- `SignaturePolicy` (`app/modules/signature/models.py:12-33`) **already has a `signature_count`
  column** (`SmallInteger`, default 1) — added in migration `b270544f6fb0` (0005), very early in
  the platform's history. It exists in the schema today but **nothing reads it**:
  `resolve_signature_requirement()` returns it unused, and no command or gateway code branches on
  it. There is **no `signature_order` column** — Document 106 §5 defines one; the platform does
  not.
- `RecordCorrection` (`app/modules/vault/models.py:66-88`) already has
  `approved_by_signatures: Mapped[dict | None] = mapped_column(JSONB)` — a list column, already
  shaped to hold more than one signature id (`complete_correction()` currently writes
  `[str(signature_id)]`, a single-element list).
- `complete_correction()` (`app/modules/vault/commands.py:228-320`) is a single-shot command: one
  `challenge_id` + `reauth_password`, one `resolve_signature_requirement()` call, one
  `vault_service.release_master()` call that both applies the correction and finalizes the
  correction record in the same transaction.

So the gap is narrower than the count column — it is: (1) no `signature_order`/chain-position
concept, (2) no way to issue a second challenge until the first is consumed, (3) no cross-signer
independence check ("this signer ≠ that earlier signer" rather than "this signer ≠ the record's
stored owner/investigator"), and (4) `complete_correction()` is structured to finalize on the
first (only) signature it gets — a two-signature version cannot finalize until *both* signers have
signed, so the record needs an intermediate state.

### D.3 Proposed build (for approval, not started)

1. **Schema — one new column, no new table.** Add `SignaturePolicy.signature_order: JSONB | None`
   (list of signer-class labels, matching Document 106 §5 verbatim) via a new Alembic migration.
   `signature_count` already exists — the migration just adds the missing column and a
   `CHECK (signature_count BETWEEN 1 AND 4)` constraint (Document 106 §5) if not already enforced.
2. **Chain position, not a new table.** A signature's position in the chain is derived, not
   stored separately: `position = 1 + count(valid Signature rows already recorded for this exact
   (record_type, record_id, record_version))`. Reusing the existing append-only `signatures` /
   `signature_challenges` tables (joined) avoids a parallel state machine and keeps AG-08
   (audit/vault/signature append-only) intact. A new helper in
   `app/modules/signature/service.py`, e.g. `create_chain_challenge()`:
   - resolves the policy, rejects if `position > signature_count` (chain already complete),
   - for `position > 1` with `requires_independent_signer` (or a dedicated "chain independence"
     flag), rejects if the requesting actor is any earlier signer in the same chain —
     `SOD_INDEPENDENCE_REQUIRED`, satisfying VLT-FR-011 / Document 106 §9 row 1's "MUST differ" and
     SIGP-FR-007's server-side ordering (a second signer literally cannot get a valid challenge for
     position 2 until position 1 exists, which is how "second signer signs before first" is
     rejected — §13 test #5).
3. **Command split.** `complete_correction()` changes from one call to a state machine on
   `RecordCorrection.status`: `requested → awaiting_second_signature → completed`. First signer's
   call consumes challenge #1, moves the correction to `awaiting_second_signature`, appends to
   `approved_by_signatures`, and does **not** yet call `vault_service.release_master()`. A second
   command call (same endpoint, or a new `/vault/v1/corrections/{id}/complete-second-signature`
   endpoint — naming is an engineering choice, not a regulated one) consumes challenge #2 from a
   *different* actor, appends the second signature id, and only then calls
   `vault_service.release_master()` and sets `status="completed"`. Both signature ids remain on the
   audit event / `approved_by_signatures` array either way — reason-for-change (mandatory,
   VLT-FR-011) is captured once at `request_correction()` time (already mandatory today) and
   carried through.
4. **Endpoint.** `POST /vault/v1/corrections/{id}/signature-challenges` (new — none exists today)
   issues challenge #1 or #2 depending on the correction's current chain position, refusing a
   third. `complete_correction` gains an explicit chain-position parameter or the two calls are
   distinguished by the correction's own status (engineering's choice, not regulated).
5. **Seed the row** once built: `("record_correction", "complete", "Approved", <corrector_role>,
   True, True, True)` plus the `signature_count=2` / `signature_order` values — **the platform-role
   mapping for "Authorized corrector" and "independent approver" is not stated as concrete roles
   anywhere in Document 106**, only as an abstract class, the same Kind-A ambiguity #2 every other
   item in this document and in `PHASE_3_QUALITY_HANDOFF.md` §1.1 point 2 raises. Engineering's
   candidate mapping, for confirmation only: "Authorized corrector" → RBAC-gated, no specific role
   (`required_role_name=None`, matching the "Authorized holder" precedent used for
   `equipment_asset/hold` and `product_version/suspend`); "independent approver" → `QA Releaser`
   (matching the "QA Approver for the record class" precedent used for `capa_record/close` etc.).
   **This mapping is offered for Quality to confirm or override, not adopted.**
6. **Tests** (Document 106 §13 test catalogue): positive 2-signature chain succeeds and produces a
   correction with two distinct `Signature` rows; second signer attempted before the first is
   rejected (fail: no valid position-1 signature exists yet, §13 test #5); same actor attempting
   both signatures is rejected (`SOD_INDEPENDENCE_REQUIRED`); a third signature attempt after the
   chain is already complete is rejected.

### D.4 Available options

- **(D-a) Approve the build above** (2-signature ordered chain, per §9 row 1) — engineering builds
  it, seeds the row, and reports PASS/FAIL evidence.
- **(D-b) Approve a single-signature interim floor** instead (one `Approved` challenge by an
  independent approver) — weaker than §9 row 1's count = 2; must be recorded as a deliberate,
  written deviation from the register (SIGP-FR-002 concerns floor-*weakening by customer
  configuration*, not by the platform itself choosing not to implement a documented floor value —
  either way this is a decision reserved to Quality, not an engineering shortcut).
- **(D-c) Leave unresolved.** Record-correction completion stays blocked (current state).

### D.5 Engineering recommendation

**(D-a)** — it matches Document 106 §9 row 1 exactly and the schema groundwork
(`signature_count`, `approved_by_signatures` as a list) already anticipates it; the remaining work
is bounded (one migration, one new service helper, a command-flow split, one new endpoint, seed
row + confirmation of the corrector/approver role mapping, and the four tests in D.3.6). **(D-b)**
is offered only because it unblocks sooner and is explicitly a documented weakening.

### D.6 Exact decision required

1. D-a / D-b / D-c.
2. If D-a: confirm or override the candidate corrector/approver role mapping in D.3.5.
3. Confirm it is safe to run `pytest` for this work before any test is executed (per the
   safe-concurrency rule — the other session may be running tests against the same
   `ebmr_new_gxp_test` database).

### D.7 Behaviour after approval

| Option | Behaviour |
|---|---|
| D-a | `POST /vault/v1/corrections/{id}/signature-challenges` issues challenge 1 (corrector), then challenge 2 (independent approver) only after challenge 1 is signed; `complete_correction` finalizes only once both are signed; out-of-order or same-actor attempts are rejected |
| D-b | one `Approved` signature by an independent approver required; recorded as a written deviation from §9 row 1 |
| D-c | unchanged — 409 `SIGNATURE_POLICY_UNRESOLVED` |

### D.8 What must NOT change without approval

- No migration, command, or endpoint change for this item happens before D-a/D-b is chosen.
- The corrector/approver role mapping is not adopted without confirmation.
- `signature_count` is not silently repurposed or read by any *other* action's resolution path as
  a side effect of this build — only `record_correction/complete` gains chain enforcement in this
  pass; every other already-seeded row keeps count = 1 behaviour unchanged.
- `RecordCorrection` remains the one vault entity that legitimately gets `UPDATE`d (its own
  status/completed_at/resulting_object_id) — the vault objects it references are still never
  edited, only superseded (existing docstring, unchanged).

---

## Global constraints (unchanged from `PHASE_3_QUALITY_HANDOFF.md` §6)

These hold for every item above and are not negotiable at the engineering level: no signature
requirement is hardcoded; no configuration weakens a floor; fail-closed stays fail-closed; no
signature is created outside the Signature Service; service/integration/device/AI identity can
never sign; `meaning` is always a SIG-FR-003 catalogue value; audit/signature/vault rows are
append-only; no value is guessed or inferred from an endpoint name.

## Mechanism reference

Application of any ratified item follows the exact same re-runnable mechanism
`PHASE_3_QUALITY_HANDOFF.md` §5 describes: `SIGNATURE_POLICY_FLOOR` in `scripts/seed.py` is the
single source of truth; `scripts/sync_signature_policies.py` applies it to an already-seeded
deployment idempotently and never deletes a row; test files are updated only where a local
per-test policy row would collide with the new floor row.
