# NZ-eBMR — System Walkthrough

A step-by-step guide to what this HTML presentation shows: how a new
customer gets set up, and how each day-to-day workflow runs, screen by
screen, click by click.

## Before you read this: what this presentation is and isn't

`eBMR-ui/` is a **design preview**, not a working application. Every
screen renders real layout, real copy, and (as of this pass) real
navigation between screens and real-looking confirmation dialogs — but
there is no server, no database, and no DocType behind any of it. Clicking
"Approve" opens a signature-style dialog and closes it; it does not create
a record. This matches the disclaimer already on the [developer catalogue](dev-catalogue.html)
and the product's own build rule (`UI-CLAUDE.md`): the UI is never allowed
to fake a saved/committed state, and this doc doesn't claim otherwise.

Two source documents ground everything below:

- `eBMR-Claude/Final/13-UI-UX-Specification-by-Persona-and-Device.md` — the
  42-screen catalogue, personas, and the "My Work" routing model.
- `eBMR-Claude/Final/11-State-Machines-and-Transition-Authority-Rules.md` —
  the record lifecycle each screen sits on.
- `eBMR-Claude/Final/24-Customer-Onboarding-Configuration-Validation-and-Quality-Agreement-Pack.md` —
  the tenant onboarding process used in Part A.

Where a step below maps a business-process stage onto a specific screen and
the source document doesn't literally say so, it's marked **(mapped, not
doc-cited)** — worth knowing before you present it as a documented fact to
a client.

---

## How to navigate the preview

The catalogue defines **42 logical screen types**. The preview builds those
out as **82 physical screens**, because each of the three profiles gets its
own copy with its own products, people, equipment and exceptions — nothing
is shared or re-skinned at runtime.

```
screens/
├── 001-sign-in.html          ← start here
├── md/    menu.html + my-work · masters(6) · production(14) · quality(3) · records(3) · admin(4)
├── ph/    menu.html + my-work · masters(6) · production(15) · quality(3) · records(3) · admin(4)
└── ddcp/  menu.html + my-work · combination(8) · records(3) · admin(4)
```

Three clicks to any screen:

1. **Sign in** → pick a section (Medical Device / Pharmaceutical / Combination Product).
2. **Work-area menu** (`<profile>/menu.html`) → pick a work area.
3. **The screen** — its sidebar lists only that work area's screens, plus
   "‹ All work areas" back to step 2.

This is deliberate: a Production sidebar shows Production screens and
nothing else. Earlier revisions showed every work area in one sidebar,
which made it hard to tell which part of the system you were in.

Two consequences worth knowing when reading the walkthrough below:

- **Common work areas are duplicated, not shared.** Masters, Records and
  Administration exist inside all three profiles. Links below usually point
  at the MD copy for brevity; the PH and DDCP equivalents are the same path
  with `md/` swapped for `ph/` or `ddcp/`, and they show that profile's own
  records.
- **Profile vocabulary never crosses over.** MD screens say Nonconformance
  and Rework; PH screens say Deviation/OOS and state explicitly that
  reprocessing doesn't exist in v1; DDCP keeps drug, device, integrated and
  final release as four separate badges. That separation is a product rule,
  not a styling choice.

[dev-catalogue.html](dev-catalogue.html) is a flat index of all 82 for
development use — it's not how an operator would navigate.

---

## Part A — New tenant, step by step

Doc 24 describes the tenant lifecycle as a single macro sequence:

```
Qualified → Admitted → Contracted → Provisioned → Configured →
QualifiedSystem (IQ/OQ accepted) → PQComplete → Live →
[Suspended ↔ Live] → Offboarding → Archived/Destroyed
```

Most of this is a **back-office process** with no on-screen equivalent —
eligibility screening, contracting, and validation sign-off happen outside
the product. The steps below call out exactly which stages have a real
click path in this prototype and which don't.

### A1. Qualified — prospect screening (no screen)
Doc 24 §5.1 lists the mandatory qualification questions (manufacturing
profile — MD/PH/DDCP, product classification, expected record volume,
existing eQMS). §5.2 covers rejection/escalation conditions. This happens
before any account exists — nothing to click yet.

### A2. Admitted — profile & capability facts *(in-product)*
This is where the prototype picks up. → **[SCR-003 — Admission & capability
boundary](screens/md/masters/admission.html)**

What doc 24 §6 calls "profile-specific admission facts" (organization
identity, site list, product classification, which operations the site is
approved for) is recorded here. The screen shows facts arriving from
source systems (site registration, product classification, capability
declarations) and keeps every downstream approval control **unavailable**
until each fact resolves — the screen's own subtitle says this directly.
Click **Approve admission** once every source-backed fact shows "Accepted"
— this opens a signature-style confirmation (who is approving, what
they're attesting to) before closing.

The DDCP-specific version of the same step is
**[SCR-035 — DDCP admission & Part 4 route](screens/ddcp/combination/admission.html)**,
which additionally records the 21 CFR Part 4 combination-product route.

### A3. Contracted — quality agreement (no screen)
MSA/SLA/DPA and the Quality Agreement (responsibility schedule — who signs
what, per doc 24's referenced `T-QA-01` template) are agreed off-platform.
Doc 24 §12.2 is worth quoting to a client here: certain configuration is
**prohibited** for any tenant regardless of contract terms — audit trail,
e-signatures, segregation of duties, and immutable snapshots can never be
disabled. That's a sales-conversation point, not a screen.

### A4. Provisioned — tenant & site setup (no screen, but visible downstream)
Doc 24 §11 and §2 principle 3: each customer gets **one dedicated Frappe
site and logical database** — tenants are never comingled. This is
infrastructure provisioning; there's no UI for it in this prototype (it
would be a super-admin/ops action, out of scope for the 42 in-product
screens).

### A5. Configured — users, roles, training, interfaces *(in-product)*
Three screens cover the parts of configuration that do have a UI:

- **[SCR-031 — Authority, training & delegation](screens/md/admin/authority.html)**
  (PER-15, Config/Access admin) — provision users, assign roles per
  profile/site, record training completions, set up delegation. This is
  where "who can sign what" gets configured — doc 24 §12.1 lists
  role/permission configuration as one of the configuration families.
- **[SCR-032 — Interfaces, migration & recovery](screens/md/admin/interfaces.html)**
  (PER-15/16) — configure system interfaces and, if the tenant is migrating
  from a paper or legacy system, walk through data migration. Doc 24 §15.1
  gives the actual 10-step migration workflow: inventory sources → classify
  facts → approve mapping → preserve source digest → mock conversion →
  reconcile counts/digests → representative workflow tests → customer
  acceptance → freeze/cutover → final reconciliation. **(mapped, not
  doc-cited — doc 24 doesn't name this screen, but the workflow it
  describes is what this screen's "Accept migration" action represents.)**
- **[SCR-033 — Privileged support access](screens/md/admin/support.html)**
  (PER-15/16) — vendor/support access is provisioned and time-boxed here,
  with an explicit "Terminate access now" control — relevant during initial
  setup when a vendor engineer may need temporary elevated access.

### A6. QualifiedSystem — IQ/OQ (no screen)
Installation/Operational Qualification is a validation activity (doc 24
§19-referenced computerized-system risk assessment, IQ/OQ evidence) — no
in-product screen; evidence is collected and reviewed off-platform.

### A7. PQComplete — customer Performance Qualification (uses production screens)
This is where the customer runs real-shaped test batches through the
**actual production workflow** described in Part B below — the PQ
"evidence" is simply the customer executing SCR-005 through SCR-027 (or
the DDCP equivalent) on representative products, per doc 24 §8's discovery
packs (each tenant profile gets 3–4 end-to-end packs, classified
normal / exception-heavy / materially-different).

### A8. Live → go-live (no screen, but a defined gate)
Doc 24 §20 is a go-live readiness checklist; §21 is the literal
authorization sign-off template (`T-GL-01`). Once signed, the tenant's
Quality function authorizes production use and the tenant moves to `Live`.

**Summary for a client-facing walkthrough:** the *clickable* part of new
tenant onboarding is admission (SCR-003 / SCR-035) → user & role setup
(SCR-031) → interfaces/migration if applicable (SCR-032) → support access
if needed (SCR-033) → then straight into the same production screens every
other user uses. Everything else (contracting, infrastructure
provisioning, IQ/OQ, go-live sign-off) is a business process the UI doesn't
represent, and shouldn't be presented as if it does.

---

## Part B — Day-to-day walkthrough (Medical Device profile)

This follows the actual record lifecycle from doc 11 §7.1/§9. Each step
names the screen, its SCR ID, and who (persona) is expected to be there.

| # | Screen | Persona | What happens |
|---|--------|---------|--------------|
| 1 | [002 — My Work](screens/md/my-work/inbox.html) | All | Universal landing after sign-in. Task cards in Ready/Waiting/Blocked/Returned/Completed tabs — opening a card routes to the relevant screen below. |
| 2 | [005 — Structured master editor](screens/md/masters/editor.html) | PER-01 Master Author | Draft a manufacturing master (`DRAFT` state). `Save draft` keeps working; `Submit for review` moves it to `IN_REVIEW`. |
| 3 | [006 — Master validation & semantic comparison](screens/md/masters/validation.html) | PER-02 Technical Reviewer | Independent check against the prior version. `Return with findings` sends it back to draft; `Check complete` advances to approval. |
| 4 | [007 — Approval, effectivity & impact](screens/md/masters/approval.html) | PER-03 Quality Master Approver | `Approve & schedule effectivity` moves the master to `APPROVED` → `EFFECTIVE`; `Reject` sends it back. |
| 5 | [008 — Execution request & issuance](screens/md/masters/issuance.html) | PER-04 Planner/Batch Issuer | Issues a governing snapshot of the effective master for a specific execution — `ISSUED`. |
| 6 | [009 — Production control board](screens/md/production/control-board.html) | PER-05 Production Supervisor | Board view of all in-flight executions; opening one routes into guided execution. |
| 7 | [010 — Readiness checklist](screens/md/production/readiness.html) | PER-05–08 | Pre-execution readiness gate (`READY`) — equipment, materials, personnel. |
| 8 | [011 — Guided step execution (MD)](screens/md/production/execution.html) | PER-06 Operator | `IN_EXECUTION`. Step-by-step device history record. A failed step (as shown) opens a nonconformance automatically and blocks forward progress until Device Quality dispositions it — this is deliberately shown as *blocked*, not a bug. |
| 9 | [012 — Material scan](screens/md/production/material-scan.html) | PER-07 Material Operator | Issue / consume / return / scrap / reversal of materials against the execution. |
| 10 | [014 — Equipment/line clearance](screens/md/production/equipment.html) | PER-05–08/10 | Records clearance/readiness evidence for equipment in use — not a full CMMS, evidence only. |
| 11 | [015 — Independent verification](screens/md/production/verification.html) | PER-08 Verifier | Pass/Fail witnessing of a critical step, by someone other than the performer. |
| 12 | [016 — Inspection/sampling result](screens/md/production/inspection.html) | PER-08/11 | In-process inspection/sampling results. |
| 13 | [017 — Timer/yield/reconciliation](screens/md/production/timer-yield.html) | PER-05–08/10 | Server-calculated timers, yields, reconciliation — displayed only, never computed client-side. |
| 14 | [018 — Pause/recovery](screens/md/production/pause.html) or [019 — Hold/issue](screens/md/production/hold.html) | PER-05/06, all trained users | Branch: a routine pause (`ON_HOLD` → resumes back into execution) vs. a hold/containment issue (its own sub-lifecycle: Open → Contained → Under assessment → Disposition approved → Action in progress → Verification pending → Closed). |
| 15 | [020 — Device nonconformance](screens/md/quality/nonconformance.html) | PER-09 Device Quality | Where a failed step's NC is dispositioned — "Record disposition & open rework" is a regulated Device Quality decision. |
| 16 | [024 — Correction/late-entry](screens/md/production/correction.html) | Authorized / Quality | Any correction to an already-recorded fact goes through this screen, never a silent edit. |
| 17 | [025 — Completion & production review](screens/md/production/completion.html) | PER-05 Production Supervisor | Compiles the finished package (`AWAITING_QUALITY_REVIEW`) — "Attest manufacturing package complete" is a signed attestation, then hands off to Quality. |
| 18 | [026 — Quality review workspace (MD)](screens/md/quality/review.html) | PER-09 Device Quality | Full package review. `Return with findings` sends it back into production; `Complete review` (a signed action) hands off to the release ceremony — **note this is a separate action from release itself**. |
| 19 | [027 — Release/rejection ceremony (MD)](screens/md/quality/release.html) | PER-09 Device Quality | The actual `RELEASED`/`REJECTED` decision — its own signature, deliberately separate from "Complete review" above (21 CFR 820.198). This is a terminal state; it never reopens. |
| 20 | [034 — Post-release amendment](screens/md/admin/amendment.html) | PER-09/13/14 | The only path to touch a record after release — a new, separately authorized amendment, never an edit to the released record. |

## Part B (continued) — Pharmaceutical profile

Same lifecycle shape, different screens for the profile-specific steps:
[013 — Dispense/charge, independent check](screens/ph/production/dispensing.html) (PER-07/08)
replaces material scan for dispensing booths — note the independence rule
shown on that screen: the system denies the independent check outright if
the same identity performed the dispense. Exceptions route through
[021 — Drug deviation/investigation](screens/ph/quality/deviation.html)
(PER-12/13, "Propose conclusion for QU approval") instead of device
nonconformance. Review and release use the PH variants:
[026 — Quality review (PH)](screens/ph/quality/review.html) and
[027 — Release/rejection ceremony (PH)](screens/ph/quality/release.html)
(PER-13, Pharmaceutical QU Reviewer).

---

## Part C — Drug-Device Combination Product (DDCP) flow

DDCP has its own sequencing (doc 11 §9.4) because a combination product
carries three parallel record threads — drug constituent, device
constituent, and the integrated record — that are **never merged into one
combined status badge** (a hard rule, `UI-CLAUDE.md`).

| # | Screen | Persona | What happens |
|---|--------|---------|--------------|
| 1 | [035 — DDCP admission & Part 4 route](screens/ddcp/combination/admission.html) | PER-17/22 | Combination-product-specific admission, records the 21 CFR Part 4 route. |
| 2 | [036 — Constituent compatibility & handoff](screens/ddcp/combination/compatibility.html) | PER-18/22 | Confirms drug/device constituent compatibility before they're paired — "Approve pairing" is a regulated decision. |
| 3 | [037 — Integrated DDCP master editor](screens/ddcp/combination/integrated-master.html) | PER-18 | The combined master for the integrated product. |
| 4 | [038 — Filling/loading & assembly](screens/ddcp/combination/filling.html) | PER-19 | `IN_PROGRESS` — physical assembly execution. |
| 5 | [039 — Integrated performance/dose-delivery testing](screens/ddcp/combination/testing.html) | PER-20 | Integrated testing of the assembled product. |
| 6 | [041 — Cross-constituent issue & impact](screens/ddcp/combination/cross-constituent.html) | PER-21/22 | Branch: an issue that spans both constituents (e.g. a device-side defect that might affect drug delivery) gets its own investigation and disposition here — this is the `PAUSED`/`HELD` branch of DDCP execution. |
| 7 | [040 — Labeling, dating & genealogy](screens/ddcp/combination/labeling.html) | PER-19/22 | `EXECUTION_COMPLETE` — final labeling and full genealogy record. |
| 8 | [042 — Complete review & final release](screens/ddcp/combination/release.html) | PER-22 DDCP Complete Record Reviewer | Two separate signed ceremonies on one screen: "Complete integrated review" (acknowledges the package) and "Release final combination product" / "Reject" (the actual release decision) — kept as two distinct actions on purpose, same 820.198-style separation as the MD/PH release ceremonies. As shown, release is correctly **blocked** while any cross-constituent exception (like the ones from step 6) is still open — that's the gate working as intended, not a defect. |

---

## Part D — Cross-cutting screens (not part of one linear flow)

These exist **in all three profiles** — each showing that profile's own
records. MD paths are given; swap `md/` for `ph/` or `ddcp/` for the others.

- **002 — My Work** ([MD](screens/md/my-work/inbox.html) ·
  [PH](screens/ph/my-work/inbox.html) · [DDCP](screens/ddcp/my-work/inbox.html)) —
  the inbox each persona lands on from the work-area menu; the routing
  mechanism between everything above.
- **028 — Record explorer & genealogy** ([MD](screens/md/records/explorer.html) ·
  [PH](screens/ph/records/explorer.html) · [DDCP](screens/ddcp/records/explorer.html)) —
  browse/search records and their genealogy within that profile.
- **029 — Audit/signature/transition timeline** ([MD](screens/md/records/timeline.html) ·
  [PH](screens/ph/records/timeline.html) · [DDCP](screens/ddcp/records/timeline.html)) —
  the immutable audit trail view for any record (21 CFR Part 11).
- **030 — Inspection export** ([MD](screens/md/records/export.html) ·
  [PH](screens/ph/records/export.html) · [DDCP](screens/ddcp/records/export.html)) —
  generates a regulator-ready export package.
- **023 — Laboratory dependency panel** ([MD](screens/md/production/lab.html) ·
  [PH](screens/ph/production/lab.html)) — shows QC/lab results a production
  record is waiting on. PH's version carries the interesting case: a stale
  result and an OOS result that together block Complete review.
- **[031 / 032 / 033 — Administration]** — covered in Part A5 above; these
  are also used continuously after go-live, not just at onboarding (adding
  a new user, rotating support access, etc.).

---

## Appendix A — Personas (PER-01 to PER-22)

| Code | Role |
|------|------|
| PER-01 | Master Author / Preparer |
| PER-02 | Technical Reviewer / Independent Checker |
| PER-03 | Quality Master Approver / Effectivity Authority |
| PER-04 | Planner / Batch Issuer |
| PER-05 | Production Supervisor |
| PER-06 | Operator / Manufacturing Performer |
| PER-07 | Material / Dispensing Operator |
| PER-08 | Independent Verifier / Inspector / Sampler |
| PER-09 | Device Quality / Release |
| PER-10 | Packaging / Label Operator |
| PER-11 | QC Analyst / Lab Reviewer |
| PER-12 | Drug Investigation Owner |
| PER-13 | Pharmaceutical QU Reviewer / Release |
| PER-14 | Records / Audit / Retention |
| PER-15 | Configuration / Access / Training / Validation Admin |
| PER-16 | Vendor Support / Ops |
| PER-17 | DDCP Regulatory / Admission Owner |
| PER-18 | Constituent Compatibility / Integrated Master Team |
| PER-19 | DDCP Filling/Assembly Operator + Verifier |
| PER-20 | Integrated Test Performer / Reviewer |
| PER-21 | Cross-constituent Investigation / Disposition |
| PER-22 | DDCP Complete Record Reviewer / Final Release Authority |

## Appendix B — Full screen catalogue (SCR-001–042)

See [dev-catalogue.html](dev-catalogue.html) for the live, clickable version
— a flat index of all 82 physical screens, grouped by profile and work area.

The table below lists the **42 logical screen types**. Each row exists once
per applicable profile in the built preview — so "SCR-005 Structured master
editor" is three physical files (`md/`, `ph/`, `ddcp/` where applicable),
each with that profile's own master, versions and validation findings.

| Area | Screens |
|------|---------|
| My Work | SCR-001 Sign-in · SCR-002 My Work/task inbox |
| Masters | SCR-003 Admission & capability boundary · SCR-004 Master catalogue & lineage · SCR-005 Structured master editor · SCR-006 Master validation · SCR-007 Approval & effectivity · SCR-008 Execution request & issuance |
| Production | SCR-009 Production control board · SCR-010 Readiness checklist · SCR-011 Guided execution (MD/PH) · SCR-012 Material scan · SCR-013 Pharmaceutical dispense/charge · SCR-014 Equipment/line clearance · SCR-015 Independent verification · SCR-016 Inspection/sampling · SCR-017 Timer/yield/reconciliation · SCR-018 Pause/recovery · SCR-019 Hold/issue · SCR-022 Packaging/label control · SCR-023 Lab dependency panel · SCR-024 Correction/late-entry · SCR-025 Completion & production review |
| Device Quality (MD) | SCR-020 Device nonconformance · SCR-026 Quality review (MD) · SCR-027 Release/rejection ceremony (MD) |
| Pharmaceutical Quality (PH) | SCR-021 Drug deviation/investigation · SCR-026 Quality review (PH) · SCR-027 Release/rejection ceremony (PH) |
| Combination Product (DDCP) | SCR-035 Admission & Part 4 route · SCR-036 Constituent compatibility · SCR-037 Integrated master editor · SCR-038 Filling/assembly · SCR-039 Integrated testing · SCR-040 Labeling, dating & genealogy · SCR-041 Cross-constituent issue · SCR-042 Complete review & final release |
| Records | SCR-028 Record explorer & genealogy · SCR-029 Audit/signature/transition timeline · SCR-030 Inspection export |
| Administration | SCR-031 Authority, training & delegation · SCR-032 Interfaces, migration & recovery · SCR-033 Privileged support access · SCR-034 Post-release amendment |

**Not in scope for this build** (per `07-Capability-Map-MVP-and-Release-Baseline.md`
§25.1, deferred beyond v1): full eQMS/CAPA, complaint/recall management,
LIMS, full CMMS, MES/SCADA, ERP integration, label-artwork/print systems,
and the full design-controls/DDF suite. None of these have a screen in
this catalogue, and that's intentional, not a gap.
