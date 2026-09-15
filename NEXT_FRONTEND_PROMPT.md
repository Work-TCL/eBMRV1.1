# Frontend build-out prompt — eBMR/eDHR platform

Paste this into a fresh Claude Code session at `/home/hepin/mydata/eBMR-new` to continue frontend work.
Read `CLAUDE.md` (repo root) and `frontend/AGENTS.md` first — both are binding.

## 0. What this is and how to work

This is a Part 11/GxP regulated manufacturing platform. The frontend (`frontend/`, Next.js + TypeScript)
is a thin client over `services/gxp-api` (FastAPI). **Never invent a field, endpoint, or behavior** — every
form field must come from reading the real Pydantic command class in the backend module's `commands.py`;
every action must call a real, already-existing endpoint in that module's `router.py`. If a page needs a
capability that doesn't exist on the backend, stop and say so — do not build a UI against an endpoint you
made up (this is a hard CLAUDE.md rule, not a style preference).

**Design instruction from the project owner: minimal and clean, simplest possible user experience.**
Concretely:
- Reuse the existing design system in `frontend/src/components/ui/` (`Card`, `Button`, `Field`, `Input`,
  `Select`, `Banner`, `Icon`, `JsonPanel`, `PageHead`, `Modal`) and shared form components in
  `frontend/src/components/shared/` (`FormConsole`, `SignedJsonForm`, `SignatureCeremony`,
  `RepeatableFields`, `OpsRecordPage`). Do not introduce a new UI kit, a new CSS approach, or a new form
  library.
- No new npm dependencies without writing the Document 104 justification (license, why nothing existing
  covers it) — the answer for almost everything here is "no new dependency needed."
- Prefer `FormConsole` for a page that's mostly a catalog of unsigned operations. Prefer `SignedJsonForm`
  for anything requiring a Part 11 signature (see §1 — several pages below are currently broken because
  they use plain `FormConsole` for actions that now require a real signature).
- Don't build a bespoke table/list component per page — check `frontend/src/components/shared/` and
  existing pages (`platform/page.tsx`, `genealogy/page.tsx`) for the table/detail patterns already in use
  before inventing a new one.
- A simple, working list + one clear action per row beats a dense dashboard. Every new page should answer
  "what do I do next" in one glance — don't make the user hunt through raw `JsonPanel` dumps to find an ID
  to paste into a text field below, if a table row with a button can do it directly.

Run the dev server and click through every page you touch before calling it done (`cd frontend && npm run
dev`, or whatever script `package.json` defines). Type-check and build must pass
(`npm run build` / `npx tsc --noEmit`, check `package.json` for the actual scripts). State plainly what you
tested vs. what you couldn't (no backend/test-DB available, etc.) — no fabricated test claims (CLAUDE.md §5
applies to frontend work too).

**Do not touch:** `specs/`, anything under `services/gxp-api/` (all backend work referenced below is
already done and tested — see §1), `edge/` (the standalone on-prem gateway has no HTTP surface for this
frontend to call — see the note in §1).

---

## 1. Backend context you need (already done — do not redo, just consume)

### 1a. Signature endpoints that exist now but have never been wired to any UI

This session resolved SG-156 (postmarket safety signals), SG-157 (reportability decide/approve) and
SG-161 (security exception request/approve split) — these actions now **really** require a Part 11
signature server-side. New HTTP challenge endpoints were added so a real client can obtain a
`challenge_id`. The existing frontend pages for these actions still use the old unsigned `FormConsole`,
so **those buttons are currently broken** (every submit gets HTTP 428 `MISSING_SIGNATURE`). This is the
single highest-priority fix in this prompt.

**`frontend/src/app/security/page.tsx`** — inside the `FormConsole` titled "Threat model & risk operations
(Doc 61)": remove the `risks/{id}/accept` op from that `FormConsole`'s `ops` array and the `exceptions`
op's sibling approve-flow doesn't exist yet either. Replace both with a new `SignedJsonForm` block (same
place in the page, same pattern as `frontend/src/app/validation/page.tsx`'s use of `SignedJsonForm`):

- **Accept a residual risk** — `postPath: "risks/{risk_id}/accept"`, `challengePath: "risks/{risk_id}/accept-signature-challenges"`, `action: "accept_risk"`. Body fields: `risk_id` (path param, also read `app/modules/security/commands.py::AcceptResidualSecurityRiskCommand` for the rest — `expected_version`, `rationale`, `expiry_review_date`).
- **Approve a security exception** — `postPath: "exceptions/{exception_id}/approve"`, `challengePath: "exceptions/{exception_id}/approval-signature-challenges"`, `action: "approve"`. Body fields per `app/modules/security/commands.py::ApproveSecurityExceptionCommand` (just `expected_version` beyond the path id).
- Leave the existing unsigned **"Raise a security exception"** `FormConsole` op alone — `POST /security/v1/exceptions` (`RequestSecurityExceptionCommand`) is intentionally unsigned (the *request* half of SG-161's split); only *approval* needs a signature.
- Both challenge endpoints already exist in `app/modules/security/router.py` (`post_accept_risk_signature_challenge`, `post_approve_exception_signature_challenge`) — nothing to add server-side.

**`frontend/src/app/postmarket/page.tsx`** — inside the `FormConsole` titled "Safety case & signal
operations (Doc 58)": remove the `signals` (open), `signals/{signal_id}/assessments` (assess) and
`signals/{signal_id}/escalations` (escalate) ops from that `FormConsole` and rebuild them as a
`SignedJsonForm` (new endpoints, added this session, in `app/modules/postmarket/router.py`):

- **Open a safety signal** — `postPath: "signals"`, `challengePath: "signals/signature-challenges"` (no path param — this challenge signs a not-yet-created record), `action: "open"`, **`mirrorBodyInChallenge: true`** (the challenge endpoint only reads `signal_code` out of the body but the rest of the fields — `site_id`, `detection_source`, `trigger_refs`, `population_definition`, `case_ids_for_snapshot`, `rationale`, `rule_version`, `exposure_denominator`, `denominator_uncertain` — must still be sent to the actual mutation; read `OpenSafetySignalCommand` in `commands.py` for exact fields/types).
- **Assess a signal** — `postPath: "signals/{signal_id}/assessments"`, `challengePath: "signals/{signal_id}/assessment-signature-challenges"`, `action: "assess"`. Fields per `AssessSafetySignalCommand`: `signal_id`, `expected_version`, `assessment` (kv), `next_state`, `recommended_actions`, `reason`.
- **Escalate a signal** — `postPath: "signals/{signal_id}/escalations"`, `challengePath: "signals/{signal_id}/escalation-signature-challenges"`, `action: "escalate"`. Fields per `EscalateSignalCommand`.

Inside the `FormConsole` titled "Regulatory reporting operations (Doc 59)": remove `tracks/{track_id}/decisions` (decide) and `reports/{report_id}/approve` (approve) and rebuild as `SignedJsonForm` (new endpoints in `app/modules/postmarket/reportability_router.py`):

- **Decide reportability** — `postPath: "tracks/{track_id}/decisions"`, `challengePath: "tracks/{track_id}/decision-signature-challenges"`, `action: "decide"`. Fields per `DecideReportabilityCommand`.
- **Approve a report** — `postPath: "reports/{report_id}/approve"`, `challengePath: "reports/{report_id}/approval-signature-challenges"`, `action: "approve"`. Fields per `ApproveRegulatoryReportCommand` (just `expected_version`).

Everything else in both pages' existing `FormConsole`s is unaffected — leave it alone.

**Before you build these**, know that `SignedJsonForm` currently renders a *separate* input row for every
`{name}` path placeholder in `postPath`/`challengePath`, on top of whatever `fields` you declare — so if
`signal_id` (or `risk_id`/`exception_id`/`track_id`/`report_id`) is both a path placeholder and a body
field (required here, because this backend's routers check `path_id == body.id` and reject a mismatch),
the user would see the same ID asked for twice. **Fix `frontend/src/components/shared/SignedJsonForm.tsx`
first**: when a path-param name also appears in `op.fields`, don't render the separate auto-generated path
row for it — take that value from the body fields state for both the path fill and the body. This is a
small, contained change (look at `pathParamNames`/the `params.map(...)` render block and `fillPath` calls)
and it directly serves the "simplest user experience" instruction — do this once, and it benefits every op
above.

### 1b. What's real vs. intentionally still unresolved — don't wire these

A handful of other postmarket/reportability actions (`reportability_track.create`,
`regulatory_report.create`, `regulatory_report.generate_payload`, `regulatory_report.submit`, and several
others) still have **no Document 106 signature policy row** and correctly fail closed with
`SIGNATURE_POLICY_UNRESOLVED` if you try to sign them. Only the actions named in §1a
(`safety_signal.open/assess/escalate`, `reportability_track.decide`, `regulatory_report.approve`,
`security_threat.accept_risk`, `security_exception.approve`) are real, resolved policies today. Leave
every other reportability/postmarket `FormConsole` op exactly as it is (unsigned `FormConsole` is correct
for them, because the backend command itself doesn't call `_resolve_signature` for them, or resolves it as
"not required" — check `commands.py`/`reportability_commands.py` if you're unsure which is which).

### 1c. EDGE-FR-022 has no frontend surface — do not build anything for it

The on-prem edge gateway (`edge/`, a separate standalone Python process, not part of `services/gxp-api`)
validates its own local config file against `edge/runtime/config/schema.py::ConnectorConfig.network_zone`.
This has no HTTP endpoint at all — it's not something `services/gxp-api` exposes, so there is nothing this
frontend can call for it. Don't invent one. The real, buildable Edge Gateway frontend gap is a *different*
thing — the server-side `app/modules/edge/` module (§3) — see below.

---

## 2. Priority 0 — a live bug (5 minutes)

`frontend/src/app/qc/page.tsx` has a stale, duplicate `OpenOosModal` (around line 954) that POSTs to
`/oos/v1/from-result/${resultId}` — **missing the `/quality` prefix** the real route requires
(`POST /quality/oos/v1/from-result/{result_id}`, `app/modules/qc/router.py`'s `oos_router`). This 404s
today. The real, complete OOS flow already lives in `frontend/src/app/quality/oos/page.tsx`. Delete the
stale modal and its trigger button from `qc/page.tsx`, and if useful, link to `/quality/oos` instead (check
how other pages cross-link, e.g. via Next's `Link`).

---

## 3. Priority 1 — new page: Edge Gateway management (currently zero UI, full backend exists)

Backend: `app/modules/edge/router.py`, prefix `/edge/v1`. Endpoints:

| Method & path | Purpose |
|---|---|
| `POST /enrollments` | Enroll a new gateway (signed) |
| `POST /enrollments/signature-challenges` | Challenge for enrollment |
| `GET /gateways/{gateway_id}` | Gateway detail |
| `GET /gateways/{gateway_id}/configuration` | Current distributed config |
| `POST /gateways/{gateway_id}/health` | Record a health heartbeat |
| `POST /gateways/{gateway_id}/security-events` | Record a security event |
| `POST /gateways/{gateway_id}/signature-challenges` | Generic gateway-action challenge |
| `POST /gateways/{gateway_id}/certificate-rotation` | Rotate the gateway's cert (signed) |
| `POST /gateways/{gateway_id}/observations:batch` | Ingest an observation batch |

Read `app/modules/edge/commands.py` and `models.py` for exact field shapes and what `Gateway` state/fields
exist, and check whether there's a "list gateways" capability anywhere (if not, note it as a gap rather
than guessing one into existence — a detail-by-id page is still useful and correct even without a list
endpoint; consider whether an existing generic entity-search/read endpoint elsewhere covers listing, but
don't invent a new backend endpoint yourself).

New page: `frontend/src/app/edge/page.tsx`. Follow the `platform/page.tsx` pattern (mix of `FormConsole`
for the straightforward ops, a `SignedJsonForm` or `SignatureCeremony` for enrollment/cert-rotation, and a
`GetCard`-style read panel for gateway detail/configuration by ID). Add it to the nav
(`frontend/src/components/layout/` — find where other top-level pages register themselves).

---

## 4. Priority 2 — other fully-missing pages (real backend, zero frontend)

For each: read the module's `commands.py` for exact fields, follow the closest existing analogous page's
pattern, keep it to one focused page (don't split into sub-pages unless the operation count genuinely
warrants it, matching how `qc/page.tsx` or `postmarket/page.tsx` already group many ops under one page with
multiple `FormConsole`/`SignedJsonForm` blocks).

- **Machine integration / PLC-SCADA evidence** — `app/modules/machine_integration/router.py`, prefix
  `/machine-integration/v1`, 14 endpoints (signal-mapping release with signature, batch-context open/close,
  evidence ingest, cycle-evidence-manifest build + export, machine-command submit/finalize with signature,
  evidence review, evidence replay with signature). New page: `frontend/src/app/machine-integration/page.tsx`.
  This module has several signed actions (signal-mapping release, machine-command, evidence-replay) —
  use `SignedJsonForm` for those, `FormConsole`/plain forms for the rest.

- **QC method master** — `app/modules/qc/router.py`, already-mounted under `/qc/v1`: `POST
  /methods/drafts`, `GET /methods/{method_code}/versions`, `GET /methods/{method_version_id}`, `POST
  /methods/{method_version_id}/signature-challenges`, `POST /methods/drafts/{method_version_id}/release`.
  This can live as a new section inside the existing `frontend/src/app/qc/page.tsx` (it already covers
  specifications/samples/test-orders for the same module) rather than a new top-level page — follow the
  existing "Specification" draft/release pattern already in that file for QC specs, which is structurally
  identical to method-master's draft/release.

- **OOT (out-of-trend) lifecycle** — `app/modules/qc/router.py`'s `oos_router`, prefix `/quality`: `POST
  /oot/v1/evaluate`, `POST /oot/v1/{oot_id}/signature-challenges`, `POST /oot/v1/{oot_id}/close`. This is
  small and belongs next to the existing OOS lifecycle in `frontend/src/app/quality/oos/page.tsx` (rename
  considerations aside, just add an "OOT" section to that same page using the same signed-action pattern
  already built there for OOS).

- **QC result correction/approval** — same `qc/router.py`: `POST /results/{result_id}/signature-challenges`,
  `POST /results/{result_id}/correct`, `POST /corrections/{correction_id}/approve`. Two-signature-chain
  shape (requester signs the correction request, an independent approver signs the approval) similar to
  the correction-removal pattern in `postmarket/page.tsx` — check
  `app/modules/qc/commands.py::RequestResultCorrectionCommand`/`ApproveResultCorrectionCommand` for the
  independence rule (is the approver checked against the requester?). Add to `frontend/src/app/qc/page.tsx`
  near the existing results table/`GET /results` usage.

- **Material specification master** — `app/modules/material_specification/router.py`, prefix
  `/material-specifications/v1`: draft create, version list/detail, signature-challenge, release. Same
  draft/release shape as QC specs and QC methods above — this is genuinely a new page,
  `frontend/src/app/material-specifications/page.tsx` (distinct from the existing
  `frontend/src/app/materials/page.tsx`, which is raw-material-lot/inventory, not the specification
  master).

- **Workflow ops (Temporal step-stuck detection)** — `app/modules/workflowops/router.py`, prefix
  `/workflowops/v1`, only 2 endpoints (`POST /step-stuck-detection`, `GET
  /step-stuck-detection/{step_id}`). Small enough to add as one card on `frontend/src/app/platform/page.tsx`
  (which already aggregates several small ops-y modules — DR/backup, dataops, read-models) rather than a
  whole new page.

**Explicitly out of scope — do not build UI for these** (verified: no backend router exists at all, so
there is nothing to call): SRE/SLO/observability dashboards (Doc 78), a contract/event registry browser,
`dbops` consistency tooling. If you want these built, that's backend work first, a separate task.

---

## 5. Priority 3 — fill the yield reconciliation gap

`frontend/src/app/yield/page.tsx` only has a data-entry form for one of six "evaluate" operations
(`manufacturing-calculations/v1/yield/evaluate`). The other five have no create form at all — they can
only be viewed/verified once a record exists via some other path:

- `manufacturing-calculations/v1/potency/evaluate`
- `reconciliation/v1/material/evaluate`
- `reconciliation/v1/packaging/evaluate`
- `reconciliation/v1/labels/evaluate`
- `reconciliation/v1/components/evaluate`

Read `app/modules/yield_reconciliation/commands.py` for each command's exact fields and add one form per
op, following the existing `EvaluateYieldCard` component in the same file as the template — five small,
near-identical cards/forms, not five different UI patterns. Don't over-abstract this into a single generic
"evaluate anything" component unless the five commands are trivially close to identical in shape; a little
repetition across five small, near-identical cards is fine and clearer than a premature abstraction (see
CLAUDE.md's own guidance: don't design for hypothetical future requirements).

---

## 6. Priority 4 — cross-cutting cleanup

### `userSelect` retrofit (small, mechanical)

The `userSelect` field type (`FormConsole.tsx`, `OpsRecordPage.tsx`) already exists and is used in 2 pages.
Convert these plain-text fields that are clearly user-id fields to `userSelect`:
- `frontend/src/app/platform/page.tsx` — `approved_by` (recovery-objectives form)
- `frontend/src/app/validation/go-live/page.tsx` — `user_id`
- `frontend/src/app/postmarket/page.tsx` — `owner_subject_id` (4 occurrences — sources, field-alerts, bpdr-tracks, fda-requests)
- `frontend/src/app/security/page.tsx` — `subject_id` (this file already uses `userSelect` for a different field; make it consistent)

### Inline signing dedup

These pages hand-roll their own challenge/reauth-password logic instead of using the shared
`SignedJsonForm`/`SignatureCeremony` components — find each `reauth_password` reference and replace the
bespoke fetch-challenge-then-submit logic with the shared component, matching how e.g.
`frontend/src/app/deviations/[id]/page.tsx` or `frontend/src/app/em/page.tsx` already use
`SignatureCeremony`:
- `frontend/src/app/dispensing/page.tsx`
- `frontend/src/app/equipment/[id]/page.tsx`
- `frontend/src/app/material-lots/page.tsx`
- `frontend/src/app/qc/page.tsx` (two separate inline instances)
- `frontend/src/app/suppliers/page.tsx`

Do this refactor carefully and one file at a time — verify each page's signed action still works
end-to-end after the swap before moving to the next file. This is behavior-preserving cleanup, not a
redesign; don't change what each action does, only how it gets its signature.

---

## 7. Report back

For each item you complete, state: which files changed/added, which backend endpoints they call (so it's
traceable), what you tested (dev server click-through, build, type-check) and what you could not test and
why. Flag anything you found that looks like a backend gap (missing endpoint, missing field, ambiguous
independence rule) rather than guessing — that becomes a SPEC_GAP or a follow-up, not a frontend
workaround.
