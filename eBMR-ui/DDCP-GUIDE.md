# DDCP (Drug-Device Combination Product) — Full Guide

Use cases and test cases for the Combination Product module: screens
`admission.html` → `compatibility.html` →
`integrated-master.html` → `filling.html` →
`testing.html` → `labeling.html` →
`cross-constituent.html` → `screens/ddcp/combination/release.html` (SCR-042).

**Read this before the rest of the doc.** This is a static HTML design
preview — no backend, no database. Every screen you'll walk through below
is **frozen at one deliberately-blocked snapshot in time**: admission has 1
of 6 facts missing, compatibility has a stale drawing check, the
cross-constituent issue is still under assessment, and final release has 2
open exceptions. Every primary "commit" button in the DDCP chain
(`Approve admission`, `Approve pairing`, `Close XC-0091`,
`Release final combination product` / `Reject`) is currently `disabled` in
the HTML, on purpose — this is the product correctly refusing to let you
skip a gate, not a bug. Section 6 below splits test cases into what you can
actually click through **today** vs. what a QA engineer would test **once
this is wired to a real backend** — don't confuse the two.

---

## 1. Overview

DDCP covers combination products regulated under 21 CFR Part 4 (device +
drug regulated together, e.g. a prefilled auto-injector). The demo product
running through every screen is **EpiRelease Auto-Injector 0.3mg**
(Epinephrine 0.3mg Solution drug constituent + Auto-Injector AI-40 Rev B
device constituent), final assembly **FA-33210**, 4,000 units.

The one hard rule that shapes every DDCP screen (`DB131-AC-003`, called out
in an HTML comment in `screens/ddcp/combination/release.html`): **drug status, device status,
and integrated-record status are always shown as three separate badges,
never merged into one combined status.** You will see this literally on
SCR-042 — "Handoff accepted" (drug) / "Handoff accepted" (device) / "2
exceptions open" (integrated) are three different pills, not one.

## 2. Personas

| Code | Role | Appears on |
|------|------|------------|
| PER-17 | DDCP Regulatory/Admission Owner | SCR-035 (signed in as **T. Alvarez**) |
| PER-18 | Constituent Compatibility / Integrated Master Team | SCR-036, SCR-037 (**S. Bloom**) |
| PER-19 | DDCP Filling/Assembly Operator + Verifier | SCR-038, SCR-040 (**M. Ortiz**) |
| PER-20 | Integrated Test Performer/Reviewer | SCR-039 (**H. Novak**) |
| PER-21 | Cross-constituent Investigation/Disposition | SCR-041 (**J. Kwan**) |
| PER-22 | DDCP Complete Record Reviewer/Final Release Authority | SCR-042 (**P. Nair**) |

Note the demo intentionally uses a **different named person on almost every
screen** — this is realistic: DDCP requires segregation of duties across
constituents, so admission, compatibility, filling, testing, investigation,
and release are genuinely different people in practice, not one operator
wearing every hat.

## 3. Lifecycle (source: `11-State-Machines-and-Transition-Authority-Rules.md` §9.4)

```
PLANNED → ISSUED → READY → IN_PROGRESS ──┬──► EXECUTION_COMPLETE
                                          │        (SCR-040 labeling/genealogy)
                                          ▼
                                    PAUSED / HELD
                                (SCR-041 cross-constituent issue)
                                          │
                                          ▼
                          AWAITING_QUALITY_REVIEW → REVIEW_COMPLETE
                                          │
                                          ▼
                          RELEASED / REJECTED / CANCELLED   (SCR-042, terminal)
```

`SCR-038` (filling/assembly) and `SCR-039` (integrated testing) both sit
inside `IN_PROGRESS`. `SCR-042` performs **two separate signed actions**
("Complete integrated review" then, separately, "Release/Reject") — this
mirrors the same 820.198-style separation used in the MD and PH release
ceremonies elsewhere in the product.

## 4. Screen map

| Screen | File | Sidebar label |
|---|---|---|
| SCR-035 | `screens/ddcp/combination/admission.html` | Admission & Part 4 |
| SCR-036 | `screens/ddcp/combination/compatibility.html` | Compatibility & handoff |
| SCR-037 | `screens/ddcp/combination/integrated-master.html` | Integrated master |
| SCR-038 | `screens/ddcp/combination/filling.html` | Filling & assembly |
| SCR-039 | `screens/ddcp/combination/testing.html` | Integrated testing |
| SCR-040 | `screens/ddcp/combination/labeling.html` | Labeling & genealogy |
| SCR-041 | `screens/ddcp/combination/cross-constituent.html` | Cross-constituent issue |
| SCR-042 | `screens/ddcp/combination/release.html` | Complete review & release |

All eight sit in the **Combination Product** work area and share one sidebar
scoped to that area — Records and Administration are separate work areas,
reached via "‹ All work areas" (`screens/ddcp/menu.html`), not from this
sidebar.

**Getting here:** `screens/001-sign-in.html` → *Drug-Device Combination* →
work-area menu → *Combination Product*. The DDCP profile has 17 physical
screens in total: these 8, plus a task inbox, 3 Records screens, 4
Administration screens and the menu itself — each with DDCP's own data
(EpiRelease Auto-Injector 0.3mg, final assembly FA-33210, XC-0091), not
shared with the MD or PH copies of the same screen types.

---

## 5. Use cases

### UC-DDCP-00 — End-to-end: admit, build, execute, and release a combination product
**Actor:** all six PER-17–22 personas in sequence · **Goal:** take EpiRelease
Auto-Injector 0.3mg from admission through final release.
**Preconditions:** drug master (Epinephrine 0.3mg Solution) and device
master (Auto-Injector AI-40 Rev B) already exist independently.
**Main flow:**
1. PER-17 admits the combination product and its Part 4 route (SCR-035).
2. PER-18 confirms exact drug/device version compatibility (SCR-036), then
   builds the integrated master (SCR-037).
3. Production issues and readies an execution (shared Masters/Production
   screens, SCR-008/010 — not DDCP-specific).
4. PER-19 performs filling/assembly with independent verification
   (SCR-038).
5. PER-20 records integrated dose-delivery testing (SCR-039).
6. PER-19 reconciles packaging and compiles genealogy (SCR-040).
7. **If** an issue spans both constituents, PER-21 investigates and
   dispositions it (SCR-041) — see UC-DDCP-07 for the branch.
8. PER-22 completes the integrated review, then separately releases or
   rejects the final product (SCR-042).
**Postcondition:** product is `RELEASED` (terminal) or `REJECTED`
(terminal); once terminal, only a post-release amendment (SCR-034) can
touch the record — never a silent edit.

---

### UC-DDCP-01 — Admit a combination product & Part 4 route
**Screen:** SCR-035 · **Actor:** PER-17 (T. Alvarez)
**Preconditions:** drug and device master identities exist; Part 4 route
determined externally.
**Main flow:**
1. Actor opens SCR-035 from the Combination Product sidebar or My Work.
2. Reviews the admission checklist (6 facts): combination type, PMOA/Part 3
   determination, drug constituent identity, device constituent identity,
   Part 4 route version, applicable exclusions.
3. Each fact shows its source document (e.g. "Regulatory dossier RD-088")
   and state (`Accepted` / `Missing`).
4. Actor clicks **Approve admission**.
**Exception flow (current snapshot):** "Applicable exclusions" is
`Missing` (source: Regulatory reviewer input) → **Approve admission stays
disabled**, with the reason text explaining a Regulatory reviewer
specialist trigger is required — the preparer cannot self-clear this fact.
**Postcondition (once unblocked):** admission moves to `Admitted`; SCR-036
and SCR-037 become reachable.

---

### UC-DDCP-02 — Confirm constituent compatibility & handoff
**Screen:** SCR-036 · **Actor:** PER-18 (S. Bloom)
**Preconditions:** admission complete (UC-DDCP-01); exact drug/device
master versions identified (not free-text names).
**Main flow:**
1. Actor reviews the exact versions compared: "Epinephrine 0.3mg Solution ·
   Master v2.1" vs. "Auto-Injector AI-40 · Master Rev B".
2. Reviews 3 interface/contact restrictions: cartridge fill volume ≤0.35mL
   (Compatible), contact material Type I borosilicate (Compatible), needle
   gauge 25G ± tolerance (**Stale** — drawing under revision).
3. Actor clicks **Approve pairing**.
**Exception flow (current snapshot):** needle gauge check is `stale`
pending a revised device drawing → **Approve pairing stays disabled**.
**Postcondition (once unblocked):** pairing is compatible; SCR-037's
device-constituent section may proceed to effectivity.

---

### UC-DDCP-03 — Build the integrated master
**Screen:** SCR-037 · **Actor:** PER-18 (S. Bloom)
**Main flow:**
1. Actor works through 5 master sections in the stepper: Admission & scope
   (done), Drug constituent process (done), Device constituent process
   (current — 1 warning), Filling & assembly steps, Integrated performance
   criteria.
2. On the Device constituent process section, actor sees the torque
   specification field flagged `is-error` — value "2.4–2.8" with **no unit
   set**.
3. Comparison-vs-governing table shows this as a tracked change: torque
   spec changed from "2.2–2.6 N·m" (v1.4, governing) to "2.4–2.8 N·m"
   (this draft) — a `Changed` badge, not silently overwritten.
4. Actor must resolve the missing unit before the master can go to
   effectivity (shared Masters flow, SCR-006/007) — this screen is
   display/edit only, it has no submit button of its own in this
   prototype.
**Note:** this is a non-blocking warning ("resolve before effectivity"),
distinct from the hard blocks on SCR-035/036/041/042.

---

### UC-DDCP-04 — Fill/load and assemble with independent verification
**Screen:** SCR-038 · **Actor:** PER-19 (M. Ortiz)
**Preconditions:** integrated master effective; execution issued and ready.
**Main flow:**
1. Actor scans the destination device before any drug quantity entry:
   "DEV-77102 / AI-40 Rev B", source batch "SRC-B-2026-0142" — device
   identity is confirmed first, by design.
2. Actor records fill volume: 0.30 mL against applicable limit 0.29–0.31
   mL (within range).
3. Screen requires **independent verification by a second identity** — the
   sig-block explicitly shows `data-sig="blocked"` / "Awaiting a second
   identity" and states this "cannot be satisfied by a checkbox."
**Exception flow:** actor hits a problem mid-fill → clicks **Stop / Raise
Issue** in the header → routes to SCR-019 (Hold/issue), the same
destination used for every "Stop / Raise Issue" button across the whole
product, not a DDCP-specific dead end.
**Postcondition:** fill/assembly event recorded, pending the second
verifier's independent confirmation on their own session.

---

### UC-DDCP-05 — Record integrated performance / dose-delivery testing
**Screen:** SCR-039 · **Actor:** PER-20 (H. Novak)
**Main flow:**
1. Actor reviews dose-delivery accuracy results (method DDT-01 v3) against
   limit 95–105% label claim: S01 98.4% (Accepted), S02 96.1% (Accepted).
2. S03 shows `Pending`/`Not received` — native data `Missing` — and its
   State column reads **"Blocking — not Pass"**, in a highlighted row.
3. S04 shows 97.8%, native data `Amended once`, state `Under re-review`.
4. Screen states plainly: "4 of 20 required samples shown. Overall
   integrated performance evidence cannot be marked complete while S03 is
   missing."
**Key business rule demonstrated:** missing/stale/amended/failed evidence
is a **blocking state**, never summarized as an overall "Pass" — this is
literally the page subtitle.

---

### UC-DDCP-06 — Reconcile packaging & compile genealogy
**Screen:** SCR-040 · **Actor:** PER-19 (M. Ortiz)
**Main flow:**
1. Actor reviews packaging reconciliation: Issued 4,000 · Packaged 3,996 ·
   Rejected 4 · Balance **0** (fully accounted for — no unexplained gap).
2. Actor reviews genealogy assembled from both constituents: drug lot
   (Batch B-2026-0142), device lot (Serial lot SL-77102), integrated
   record (FA-33210 · 3,996 finished units).
3. Screen states the rule explicitly: "the integrated genealogy record
   links both, it does not merge them into one identity."
**Postcondition:** execution reaches `EXECUTION_COMPLETE`, ready for
`AWAITING_QUALITY_REVIEW`.

---

### UC-DDCP-07 — Investigate and disposition a cross-constituent issue
**Screen:** SCR-041 · **Actor:** PER-21 (J. Kwan) · **Record:** XC-0091
**Preconditions:** an issue was raised that could affect both constituents
(here: device-side assembly torque out of spec on 40 units during a line
audit).
**Main flow:**
1. Actor reviews the trigger: torque reading below spec on 40 units,
   assessing whether drug delivery accuracy is affected for those units.
2. Actor reviews impact assessment by constituent, tracked **separately**:
   - Drug constituent impact — `In progress` (stale/pending)
   - Device constituent impact — `Assessed`, confirmed 40 units affected
   - Final product impact — `Blocked`, explicitly "cannot close until both
     above resolve"
3. Actor clicks **Close XC-0091**.
**Exception flow (current snapshot):** drug constituent impact is still
`In progress` → **Close XC-0091 stays disabled** — the screen states this
directly: "Device closure alone cannot close this cross-constituent
blocker." One constituent finishing its half of the investigation is
insufficient by design.
**Postcondition (once unblocked):** XC-0091 closes; SCR-042's evidence
group 8 ("Cross-constituent exceptions") drops from 2 open to 1 (XC-0094
would still be open in this scenario).

---

### UC-DDCP-08 — Complete integrated review & release/reject the final product
**Screen:** SCR-042 (`screens/ddcp/combination/release.html`) · **Actor:** PER-22 (P. Nair)
**Preconditions:** all upstream evidence groups compiled.
**Main flow — Ceremony 1 (Complete integrated review):**
1. Actor reviews 10 evidence groups: 1–7 and 9 are `Accepted`/`Not
   applicable`; group 8 (Cross-constituent exceptions) is `Conflict` (2
   open — XC-0091, XC-0094); group 10 (Final release gates) is `Blocked`.
2. In this snapshot, Ceremony 1 is **already completed and signed**: "P.
   Nair — 05 Aug 2026, 14:15 EDT", Event EVT-90310, explicitly
   acknowledging groups 1–7 and 9 while stating groups 8 and 10 "remain
   open and are carried forward, not hidden."
**Main flow — Ceremony 2 (Release/Reject), separate and later:**
3. Actor reviews scope (FA-33210 · 4,000 units), package digest
   (v1.4 · sha256:9c31…e02a), unresolved blockers (2 — XC-0091, XC-0094),
   and the applicable Quality Agreement clause (§4.2).
4. Actor would enter a rationale and click **Release final combination
   product** or **Reject** — both equally available, neither preselected.
**Exception flow (current snapshot):** 2 cross-constituent exceptions
unresolved → **both Release and Reject stay disabled**, with the reason
text stated on-screen. This is the correct behavior — release is
impossible while XC-0091/XC-0094 are open, exactly what UC-DDCP-07 exists
to resolve.
**Postcondition (once unblocked):** product reaches terminal state
`RELEASED` or `REJECTED`. A released product's only further path is
SCR-034 (post-release amendment) — never a reopened release ceremony.

---

## 6. Test cases

### 6.1 Prototype-verifiable today (click through the live HTML, no backend needed)

| ID | Title | Steps | Expected result |
|---|---|---|---|
| TC-035-01 | Admission checklist renders all 6 facts with correct source/state | Open `screens/ddcp/combination/admission.html` | Table shows 6 rows; 5 `Accepted` (green check), 1 `Missing` ("Applicable exclusions" / "Regulatory reviewer input") |
| TC-035-02 | Approve admission is correctly disabled | On SCR-035, inspect **Approve admission** | Button is disabled; adjacent text explains why (exclusions missing, requires Regulatory reviewer, not preparer) |
| TC-036-01 | Compatibility restrictions show mixed states | Open `screens/ddcp/combination/compatibility.html` | 2 of 3 restrictions `Compatible`; needle gauge row shows `Stale — recheck required` |
| TC-036-02 | Approve pairing is correctly disabled | Inspect **Approve pairing** | Disabled; reason cites the stale needle-gauge check specifically |
| TC-037-01 | Torque spec unit-missing warning displays | Open `screens/ddcp/combination/integrated-master.html` | Torque field shows `is-error` styling + "unit not set" + non-blocking warning text |
| TC-037-02 | Version comparison shows the torque change, not a silent overwrite | Same screen, comparison table | Row shows `Changed` badge, Old "2.2–2.6 N·m", New "2.4–2.8 N·m" |
| TC-038-01 | Stop / Raise Issue navigates correctly | On `screens/ddcp/combination/filling.html`, click **Stop / Raise Issue** | Navigates to `hold.html` |
| TC-038-02 | Independent verification shows blocked, not a checkbox | Inspect the verification sig-block | Shows "Awaiting a second identity" with a lock icon, no checkbox present |
| TC-039-01 | Blocking sample is visually distinguished | Open `screens/ddcp/combination/testing.html` | Row FA-33210-S03 is highlighted (critical background), State = "Blocking — not Pass" |
| TC-039-02 | No overall Pass/Fail summary is computed client-side | Same screen | Page states evidence "cannot be marked complete" — no aggregate pass/fail badge exists anywhere on the page |
| TC-040-01 | Packaging balance reconciles to zero | Open `screens/ddcp/combination/labeling.html` | Issued 4,000 − Packaged 3,996 − Rejected 4 = Balance 0, shown in green |
| TC-040-02 | Genealogy shows 3 distinct linked identities, not 1 merged | Inspect genealogy card | 3 separate constituent badges (drug lot / device lot / integrated record) |
| TC-041-01 | Close XC-0091 is correctly disabled | Open `screens/ddcp/combination/cross-constituent.html` | Disabled; reason cites drug constituent assessment still in progress |
| TC-041-02 | Constituent impacts tracked separately | Inspect impact assessment card | 3 separate badges (drug/device/final), each with its own state — device `Assessed`, drug `In progress`, final `Blocked` |
| TC-042-01 | Constituent badges never combine | Open `screens/ddcp/combination/release.html` | 4 separate badges shown (drug/device/integrated/final release), never one combined pill |
| TC-042-02 | Ceremony 1 and Ceremony 2 are visibly separate actions | Inspect both ceremony cards | "Ceremony 1 of 2" is shown already-signed (P. Nair, EVT-90310); "Ceremony 2 of 2" is a distinct card below with its own rationale field and buttons |
| TC-042-03 | Release/Reject both correctly disabled together | Inspect Ceremony 2 buttons | Both disabled simultaneously (neither is enabled while the other is blocked) — reason cites the 2 open XC records by number |
| TC-042-04 | Sidebar full navigation reachable from every DDCP screen | From any of 035/036/038/041/042, open sidebar | All 8 DDCP screens + Task inbox + Records + Administration links present and resolve (HTTP 200) |

### 6.2 Functional / business test cases (for when this is wired to a real backend)

These describe what a QA engineer should verify **once DDCP screens are
backed by real commands and data** — written against the business rules
each screen currently documents, not against today's static HTML.

| ID | Title | Preconditions | Steps | Expected result |
|---|---|---|---|---|
| TC-F-035-01 | Admission approval succeeds once all 6 facts resolve | All facts `Accepted` incl. exclusions | Record the exclusions fact → click Approve admission → confirm e-signature | Admission moves to `Admitted`; SCR-036/037 become reachable for this product |
| TC-F-035-02 | Admission approval is blocked for the preparer even with facts complete, if Critical questions are open | An "Unresolved Critical question" is raised (e.g. sterile-barrier applicability) | Attempt approval as the preparer (not Regulatory reviewer) | Server denies the action; only a Regulatory reviewer identity may clear it |
| TC-F-036-01 | Pairing approval succeeds once the device drawing revision lands | Needle gauge restriction re-checked and marked `Compatible` | Click Approve pairing → confirm | Pairing state moves to compatible/approved; unlocks integrated master effectivity |
| TC-F-036-02 | A free-text product name cannot substitute for exact governed versions | Attempt to pair using a description instead of Master v2.1 / Rev B identifiers | System rejects the pairing input | Error requiring exact master version references |
| TC-F-038-01 | Fill/assembly event cannot commit without a second verifier identity | Same operator (M. Ortiz) attempts to also perform independent verification | Attempt verification under M. Ortiz's session | Server denies — independent verification requires a different identity, matching the same rule used on SCR-015/016 |
| TC-F-039-01 | Integrated performance evidence cannot be marked complete while any sample is missing/stale/failed | 20 required samples, ≥1 in Missing/Stale/Failed state | Attempt to advance execution past testing | Blocked; all 20 must resolve to Accepted before EXECUTION_COMPLETE |
| TC-F-041-01 | XC record closes only when both constituent impacts resolve | Drug impact still `In progress` | Attempt Close XC-0091 | Denied — matches TC-041-01's on-screen reason; closing requires both assessments `Assessed`/resolved |
| TC-F-041-02 | Closing one of two open XC records partially unblocks release | XC-0091 closed, XC-0094 still open | Reload SCR-042 evidence group 8 | Shows "1 open" (not 2); Final release gates remain `Blocked` until XC-0094 also closes |
| TC-F-042-01 | Release requires zero open cross-constituent exceptions | Both XC-0091 and XC-0094 closed | Click Release final combination product → enter rationale → confirm | Product reaches `RELEASED` (terminal); event recorded with signer identity + timestamp |
| TC-F-042-02 | Completing review does not itself release the product | Ceremony 1 signed, Ceremony 2 not yet actioned | Query product state after Ceremony 1 only | State is still pre-release; Ceremony 2 is a mandatory separate signed action |
| TC-F-042-03 | Released record cannot be re-released or silently edited | Product already `RELEASED` | Attempt a second release action, or attempt to edit a released fact directly | Both denied; only route is a new SCR-034 post-release amendment, itself separately authorized |
| TC-F-042-04 | Rejected record is terminal, not a return-to-draft | Product `REJECTED` | Attempt to resume execution or re-submit for release | Denied — `REJECTED` is terminal per DB11-DEC-005/006, same rule as MD/PH release ceremonies |

---

## 7. Cross-references

- Business rules cited above come from `eBMR-Claude/Final/07-Capability-Map-MVP-and-Release-Baseline.md`,
  `11-State-Machines-and-Transition-Authority-Rules.md` §9.4, and
  `13-UI-UX-Specification-by-Persona-and-Device.md` §9A/§6A.5.
- Day-to-day walkthrough context: [SYSTEM-WALKTHROUGH.md](SYSTEM-WALKTHROUGH.md) Part C.
- The `data-state="..."` values used throughout (`accepted`, `blocked`,
  `conflict`, `stale`, `missing`, `na`) are the fixed 8-state vocabulary
  defined in the UI governance rules — no other state values are used
  anywhere in the DDCP screens, by design.
