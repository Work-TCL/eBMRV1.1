# ૨૩. Quality System Modules — શું, શા માટે, કેવી રીતે જોડાયેલ (Gujarati Explainer)

> Source: `services/gxp-api/app/modules/qms/*_models.py`, `*_commands.py`, `*_router.py` (API prefix
> `/qms/v1/...`, Documents ૨૮-૩૭), `frontend/src/app/{nonconformances,changes,complaints,field-actions,
> audits,risks,supplier-cases,documents,training,quality-metrics}/`.
>
> **આ doc નો હેતુ:** doc #૧૦ (CAPA) અને #૧૧ (Deviation) પહેલેથી full detail આપે છે. આ doc બાકીના ૧૦
> Quality System modules ને cover કરે છે — concept-level, simple ઉદાહરણ અને test-case tables સાથે.
>
> **ઉદાહરણ dataset:** Organization "Demo Manufacturing Co.", Site `SITE1`, Product `MJ-PFS-40MG`,
> Batch `MJ-PFS-B-2601`. Demo users (password બધા માટે `ChangeMe123!`): `admin`, `qa.releaser`,
> `qa.reviewer`, `qc.reviewer`, `process.engineer`.
>
> **2026-10-09 revision pass:** દરેક module ની "બીજા modules સાથે જોડાણ" claims code સામે ફરી
> ચકાસેલ — ૫ claims stale નીકળી (risk.review signature inverted in the old table, Training
> qualification gate already wired at 3 call sites, Supplier suspend already gating material receipt
> SG-097, CAPA source_type already 11 not 8, Release already wiring 10 signal sources not 2) અને 3
> ખોટી SG-number citation સુધારી (SG-091→૯૭, SG-073→૭૧, SG-105→૧૦૬). દરેક module માં doc #૨૨ ની જ
> style માં live-verified "વાસ્તવિક ડેટા એન્ટ્રી" section ઉમેરેલ છે, જેમાં ૪ real UI payload bugs
> મળ્યા+ફિક્સ થયા (NCR Evaluate/Verify, SCAR acknowledgment, Internal Audit auditees field) — દરેક
> 🐛/🔧 callout સાથે ચિહ્નિત. એક નાનો, non-regulated dashboard enhancement પણ ઉમેરેલ: Risk Register ના
> `next_review_due_at` ને હવે Topbar ના Reminders bell માં પણ બતાવાય છે (§૨૩.૬ જુઓ).

---

## ૨૩.૦ શા માટે આ "Quality System" category અલગ છે?

Doc #૨૨ ના Operations modules **batch ની અંદર** ચાલે છે (equipment/room/process level). આ doc ના ૧૦
modules **batch ની બહારના quality decisions** maneage કરે છે — defect મળ્યા પછી શું કરવું, supplier ની
ભૂલ, internal audit finding, risk, document control, training — આ બધા company-wide quality management
system (QMS) નો ભાગ છે, ISO 13485 / 21 CFR 820 જેવા regulation ની required part.

**સૌથી મહત્વનો concept — CAPA નું "hub" ભૂમિકા:** CAPA (doc #૧૦) ૧૩ પ્રકારના source ને સ્વીકારે છે:
`deviation, oos, oot, ncr, complaint, audit, supplier, risk, trend, security, validation, change_control,
field_action`. એટલે આ doc ના Nonconformance, Complaint, Internal Audit, Supplier Case, Field Action — બધા
CAPA ના "source" બની શકે.

🔧 **2026-10-09 RESOLVED (project-owner-directed, client gap-closure item #1):** NCR/Complaint/Internal
Audit/SCAR/Field Action — આ પાંચ module માં `capa_required=true` mark કરવાથી હવે **real draft CAPA
auto-create થાય છે** (પહેલાં ફક્ત flag/data હતું, manual `/capa` create જરૂરી હતું). એક જ transaction માં
(signed disposition/response/close/reportability action સાથે) એક `OPEN` state નો `CapaRecord` insert
થાય છે — `capa_number` auto-generated (`CAPA-AUTO-...`), `root_cause_ref.proactive_rationale` = તમે
લખેલ `capa_rationale`, `owner_subject_id` = જે actor એ flag set કર્યું (placeholder, પછી reassign કરવું
પડે), `risk_class` = `"pending_assessment"` (placeholder — Document 27 માં આ field પછી edit કરવાનો કોઈ
endpoint નથી, એ CAPA module ની પહેલેથી existing limitation છે), `target_date` = +30 દિવસ default.
Live-verified: NCR disposition → `capa_required:true` → `/qms/v1/capas` પર એ CAPA તરત દેખાય.

---

## ૨૩.૧ Nonconformance (NCR)

**શું છે અને શા માટે જરૂરી:** QC/inspection માં fail થયેલ material/component/device/packaging/finished
product ને "segregate" કરીને defective product silently ship ના થાય એની ખાતરી.

**કેવી રીતે કામ કરે:** `OPEN → SEGREGATED → EVALUATION → {REWORK|REPAIR|RETURN|SCRAP|USE_AS_IS} →
VERIFICATION → CLOSED (→ REOPENED → ...)`. ~~CLOSED પછી કોઈ reopen operation જ નથી (SG-069)~~ **🔧
2026-10-09 ફિક્સ (SG-069 RESOLVED):** Document 26/27 ના પોતાના already-approved reopen contract ને
verbatim મિરર કરીને reopen ઉમેર્યું — `reason` + `new_evidence` ફરજિયાત, **unsigned** (RBAC-ગેટેડ ફક્ત,
નવું `ncr.reopen` permission, `ncr.disposition`/`.close` ની જ QA Releaser role), ફક્ત `CLOSED` માંથી જ,
prior closure (`closed_at`/`closure_history`) ક્યારેય cleared/overwritten નથી થતું. `REOPENED` માંથી
Document 26 ની જ breadth — `EVALUATION`/કોઈ પણ disposition/`VERIFICATION`/સીધું `CLOSED` ફરી — resume
કરી શકાય.

| Step | Permission | કોણ | Signed? |
|---|---|---|---|
| Disposition | `ncr.disposition` | QA Releaser | હા |
| Verify | `ncr.verify` | QA Reviewer, QC Reviewer | હા |
| Close | `ncr.close` | QA Releaser | હા |
| **Reopen** (નવું) | `ncr.reopen` | QA Releaser | **ના** — unsigned, same as Deviation/CAPA reopen |

**બીજા modules સાથે જોડાણ:** CAPA નો એક valid source type. `release_blocker_active` field local-only
છે — **Release module ને wire નથી કરેલ** (deviation/CAPA ના blocker ની જેમ નહીં — genuine gap).

**ઉદાહરણ:** Incoming raw material inspection માં defect મળે → `admin` NCR create+segregate+evaluate →
`qa.releaser` disposition "SCRAP" (sign) → `qc.reviewer` verify (sign) → `qa.releaser` close (sign).

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-09 ઉમેરેલ)

UI માં જે-તે field નું exact label સાથે — live system માં સીધું ભરી શકાય એવું realistic pharma data.
Login seq.: પહેલા `admin` (raise + segregate + evaluate), પછી `qa.releaser` (disposition sign), પછી
`qc.reviewer` (independent verify sign), પછી ફરી `qa.releaser` (close sign).

> ✅ **2026-10-09 live-verified:** આ આખો flow (સ્ટેપ ૧-૬, નીચેની બધી જ exact values સાથે, **બંને bug-fix
> પછી**) curl દ્વારા live `ebmr-new-api` સામે ચલાવીને ચકાસેલ છે — ધારેલું નથી. પરિણામ: NCR created, state
> `OPEN→SEGREGATED→EVALUATION→RETURN→VERIFICATION→CLOSED`, disposition signature meaning `Released`,
> verify signature meaning `Verified`, close signature meaning `Approved`, final `version=6`.

**સ્ટેપ ૧ — "Raise a nonconformance" (`/nonconformances`, login: `admin`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| NCR number | `NCR-2601-001` |
| Defect code | `ASSAY-OOS-LOW` |
| Severity | `Major` |
| Scope type | `Material` |
| Affected record (picker) | `MAT-API-001 — Active Pharmaceutical Ingredient - Metformin` |
| Specification reference | `SPEC-MAT-API-001 Rev C, Section 4.2 (Assay 98.0-102.0% w/w)` |

"Raise nonconformance" ક્લિક → list card માં `NCR-2601-001` દેખાશે, state `OPEN`, owner = raising user
(`admin`) આપોઆપ.

**સ્ટેપ ૨ — "Record segregation" (same login, NCR ખોલીને):**

| Field | Value |
|---|---|
| Segregation location | `Quarantine Cage QC-03, Warehouse Zone B` |
| Reason | `Incoming inspection assay result 94.8% w/w, below SPEC-MAT-API-001 lower limit 98.0%` |

→ state `SEGREGATED`.

**સ્ટેપ ૩ — "Evaluate" (same login):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Evaluation conclusion | `Lot confirmed out-of-spec on assay (94.8% w/w vs 98.0-102.0% spec); recommend disposition.` |
| Usability | `Not usable for intended purpose; candidate for return or scrap.` |
| Quality impact | `Moderate` |
| Safety impact | `None` |
| Performance impact | `None` |
| Investigation needed | અનચેક |

> 🐛 **2026-10-09 real bug fixed:** આ form પહેલા ફક્ત `{conclusion}` મોકલતું હતું —
> `evaluate_ncr()` ને ૫ વધારાની key ફરજિયાત છે (`usability`, `quality_impact`, `safety_impact`,
> `performance_impact`, `investigation_needed`), "Evaluate" button **દરેક વખતે** `422
> VALIDATION_FAILED` આપતું હતું. Fix: ઉપરના ૫ fields ફોર્મમાં ઉમેર્યા (CAPA #૨૨ ના EM "Record result"
> bug ની જ ક્લાસ — backend contract already correct હતો, frontend payload અધૂરો હતો).

→ state `EVALUATION`.

**સ્ટેપ ૪ — "Disposition (sign)" (login: `qa.releaser`, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Disposition type | `Return` |
| Quantity | `25` (kg) |
| Justification | `Assay result 94.8% w/w confirmed on retest; below SPEC-MAT-API-001 lower acceptance limit of 98.0% w/w. Return to supplier per QA disposition.` |
| CAPA required | અનચેક |

→ signature meaning `Released`, state `RETURN`.

**સ્ટેપ ૫ — "Verify (sign)" (login: `qc.reviewer` — disposition-signer થી અલગ, password `ChangeMe123!`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Confirmation | `Confirmed returned to supplier per RMA-2601-003.` |

> 🐛 **2026-10-09 real bug fixed (second one):** `SCRAP`/`RETURN`/`USE_AS_IS` disposition માટે
> `verify_ncr()` ને `confirmation` object જોઈએ (`reinspection_evidence` ફક્ત `REWORK`/`REPAIR` માટે) —
> પણ આ form કોઈ પણ disposition type માટે હંમેશા `reinspection_evidence` જ મોકલતું, એટલે NCR ની ૫ માંથી ૩
> disposition type પર "Verify" button દરેક વખતે `422` (`confirmation is required...`) આપતું. Fix: form
> હવે `ncr.state`/latest disposition type જોઈને જરૂરી field (REWORK/REPAIR → "Reinspection result" →
> `reinspection_evidence`; બાકીના ત્રણ → "Confirmation" → `confirmation`) condition પ્રમાણે મોકલે છે.

→ signature meaning `Verified`, state `VERIFICATION`.

**સ્ટેપ ૬ — "Close (sign)" (login: `qa.releaser`, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Conclusion | `Lot MAT-API-001 (25 kg) returned to supplier per QA disposition; return verified RMA-2601-003. No further action required.` |

→ signature meaning `Approved`, state `CLOSED`.

**સ્ટેપ ૭ — "Reopen" (login: `qa.releaser`, **unsigned** — RBAC-gated only):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Reason | `Supplier disputes the RETURN disposition with new COA evidence.` |
| New evidence | `Supplier-submitted retest COA shows the lot result was actually within spec; original assay was a lab error.` |

→ **કોઈ password prompt નથી** (reopen signed નથી, Deviation/CAPA reopen ની જ pattern) → state
`REOPENED`, `closed_at`/`closure_history` preserved (cleared નથી થતાં), `reopen_history` માં નવી entry.

**સ્ટેપ ૮ — "Close (sign)" ફરી (same login, REOPENED માંથી સીધું, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Conclusion | `Re-reviewed with supplier COA; original RETURN disposition stands. Reopen round-trip verified.` |

→ state `CLOSED` ફરી, version આગળ વધ્યું. (વૈકલ્પિક: `REOPENED` માંથી "Evaluate" પણ ફરી call કરી શકાય —
Document 26 ની જ breadth, re-dispositioning માટે.)

> ✅ **2026-10-09 live-verified:** સ્ટેપ ૭-૮ curl દ્વારા live `ebmr-new-api` સામે ચલાવીને ચકાસેલ —
> `NCR-2601-001` `CLOSED`(v6) `→REOPENED`(v7, unsigned, `closed_at` preserved) `→CLOSED`(v8, signed
> ફરી). SG-069 હવે RESOLVED.

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| QMS-NCR-00 | ઉપરનું સ્ટેપ ૧-૮ (admin → qa.releaser → qc.reviewer → qa.releaser) exact values સાથે run કરો | `NCR-2601-001` `CLOSED→REOPENED→CLOSED`, version 8; બધા fixed/new payload સફળ થાય | NCR |
| QMS-NCR-01 | NCR create → segregate → evaluate → disposition SCRAP (sign) → verify (sign) → close (sign) | State `CLOSED` | NCR |
| QMS-NCR-02 | NCR CLOSED પછી reopen કરવાનો પ્રયત્ન (reason + new_evidence સાથે) | **સફળ** — state `REOPENED`, unsigned, prior closure preserved (SG-069 RESOLVED 2026-10-09) | NCR |
| QMS-NCR-02b | reason/new_evidence ખાલી રાખીને reopen try કરો | `422 VALIDATION_FAILED` | NCR |
| QMS-NCR-02c | NCR CLOSED ના હોય (દા.ત. EVALUATION) ત્યારે reopen try કરો | `409 INVALID_TRANSITION` | NCR |
| QMS-NCR-03 | NCR `release_blocker_active=true` હોય, batch release evaluate કરે | Release blocked નથી (documented gap) | NCR, Release |
| QMS-NCR-04 | NCR close પછી CAPA create — source_type="ncr" select | CAPA source FK validate pass | NCR, CAPA |

---

## ૨૩.૨ Change Control

**શું છે અને શા માટે જરૂરી:** Product/process/recipe/spec/material/equipment/document/software/supplier
માં કોઈ પણ ફેરફાર પહેલાં impact assess કરવું અને approve કરવું ફરજિયાત — અચાનક/અનિયંત્રિત ફેરફાર quality
risk છે.

**કેવી રીતે કામ કરે:** `DRAFT → IMPACT_ASSESSMENT → APPROVAL → IMPLEMENTATION → VERIFICATION →
EFFECTIVE → CLOSED` (+ `CANCELLED`, + `ROLLED_BACK` — 🔧 2026-10-09 ઉમેરેલ, નીચે જુઓ). Emergency path
pre-approval bypass કરીને સીધું implement કરી શકે.

| Step | Permission | Signed? |
|---|---|---|
| Approve | `change.approve` | હા |
| Verify | `change.verify` | હા |
| Close | `change.close` | હા |

**બીજા modules સાથે જોડાણ (real FK):**
- `risk_ref` → **Risk Register** (`qms.risk_record`) — impact assessment risk cite કરી શકે.
- `qms.controlled_document_version.change_control_id` → **Documents** module — document release ને
  driving change cite કરવા real FK.
- 🔧 **SG-071 RESOLVED (2026-10-09, project-owner-directed):** Rollback operation (CHG-FR-019) હવે
  build થયેલ છે — નવું terminal state `ROLLED_BACK`, માત્ર `IMPLEMENTATION`/`VERIFICATION` state માંથી જ
  પહોંચી શકાય (પહેલાંથી — DRAFT/IMPACT_ASSESSMENT/APPROVAL માંથી rollback `INVALID_TRANSITION` આપે છે).
  કોઈ નવો endpoint નથી — existing `/close` endpoint જ `rollback_reason` field લઈને (હાલના
  `cancellation_reason` ની જેમ) એ જ signed `"close"` ceremony (QA Releaser, owner-independent) reuse કરે
  છે. `CANCELLED` (implement પહેલાં છોડેલ) થી અલગ — `ROLLED_BACK` નો અર્થ "implementation શરૂ/verify
  થયા પછી undo કરવું પડ્યું". Response `rollback_reason`/`rolled_back_at` fields પણ detail view માં
  દેખાય છે. Live-verified: qa.releaser → qa.reviewer flow દ્વારા VERIFICATION state માંથી signed
  rollback, પરિણામ `state: ROLLED_BACK` + real `signature_id`.
- ⚠️ CAPA/Deviation ના `change_control_required` flag Change Control auto-create નથી કરતા (SG-072,
  documented).

**ઉદાહરણ:** Recipe `RCP-MJ-PFS-V1` ના fill-volume parameter બદલવો હોય → `process.engineer` change
control draft → impact assessment (risk_ref link) → `qa.releaser` approve (sign) → implement → verify
(sign) → close (sign) → Document release આ change_control_id ને cite કરી શકે.

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-09 ઉમેરેલ)

UI માં જે-તે field નું exact label સાથે — live system માં સીધું ભરી શકાય એવું realistic pharma data.
Login seq.: `qa.reviewer` (author: draft + impact + implement + task), `qa.releaser` (approve/
make-effective/close sign), `admin` (verify sign — independent-signer rule, જુઓ નીચે નોંધ).

> ✅ **2026-10-09 live-verified:** આ આખો flow (સ્ટેપ ૧-૮) curl દ્વારા live `ebmr-new-api` સામે ચલાવીને
> ચકાસેલ — `CHG-2601-001` state
> `DRAFT→IMPACT_ASSESSMENT→APPROVAL→IMPLEMENTATION→VERIFICATION→EFFECTIVE→CLOSED`, `risk_ref` real-FK
> linked to live Risk Register record `RSK-DEMO-001`, approve signature meaning `Approved`, verify
> meaning `Verified`, close meaning `Approved`, final `version=8`.

**સ્ટેપ ૧ — "Raise a change control" (`/changes`, login: `qa.reviewer`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Change number | `CHG-2601-001` |
| Type | `Recipe` |
| Classification | `Permanent` |
| Current state | `Recipe RCP-MJ-PFS-V1 step 4 (Fill) fill_volume parameter = 0.50 mL target, 0.48-0.52 mL range.` |
| Proposed state | `Recipe RCP-MJ-PFS-V1 step 4 (Fill) fill_volume parameter = 0.55 mL target, 0.53-0.57 mL range, to match updated label claim.` |
| Reason for change | `Label claim update requires a 10% fill-volume increase for MJ-PFS-40MG; process engineering confirmed filler Filler-01 can hold the new range within validated tolerance.` |
| Emergency change | અનચેક |

"Raise change" ક્લિક → `CHG-2601-001` listed, state `DRAFT`.

**સ્ટેપ ૨ — "Assess impact" (same login):**

| Field | Value |
|---|---|
| Regulatory impact | `Minor fill-volume adjustment within same device/container-closure; no new submission required.` |
| Requires regulatory review | અનચેક |
| Validation impact | `Filler-01 fill-volume accuracy requires re-qualification (OQ) at the new 0.55 mL target.` |
| Revalidation required | **ચેક** (સ્ટેપ ૬ નું verification evidence ફરજિયાત બનાવે) |
| Training impact | `Filling operators must be briefed on the new target/range.` |
| Training required | **ચેક** (સ્ટેપ ૭ નું training confirmation ફરજિયાત બનાવે) |

🔧 **UI gap FIXED (2026-10-10):** `risk_ref` (Risk Register FK) `change_router.py`/`change_commands.py`
માં real field હતું, પણ impact form માં એના માટે કોઈ UI field નહોતું. Fix: "Assess impact" modal માં
"Risk record" `EntityPickerField` ઉમેર્યું (`entities.risks`, same picker data `/risks` page પોતે
વાપરે છે) — હવે UI ક્લિક કરીને જ risk link થઈ શકે, curl જરૂરી નથી.

→ state `IMPACT_ASSESSMENT`.

**સ્ટેપ ૩ — "Approve (sign)" (login: `qa.releaser`, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Approval notes | `Impact assessment reviewed -- regulatory/validation/training all addressed. Approved for implementation.` |

→ signature meaning `Approved`, state `APPROVAL`.

**સ્ટેપ ૪ — "Mark implemented" (login: `qa.reviewer`):** → state `IMPLEMENTATION`.

**સ્ટેપ ૫ — "Add task" (same login):**

| Field | Value |
|---|---|
| Description | `Re-qualify Filler-01 fill-volume accuracy at new 0.55 mL target (OQ) and update WI-FILL-014.` |
| Owner (picker) | `qa.reviewer — QA Reviewer` |
| Due date | આજ + ૫ દિવસ |

**સ્ટેપ ૬ — "Verify (sign)" (login: `admin`, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Verification evidence | `Filler-01 OQ re-qualification PASS at 0.55 mL target (report OQ-FILLER-01-2026-014).` |

⚠️ **શા માટે `admin`, `qa.reviewer` નહીં:** record નો owner/author `qa.reviewer` જ છે (સ્ટેપ ૧), અને
independence rule verify signerને owner થી અલગ માંગે છે — `qa.reviewer` પોતે try કરે તો `409
SOD_INDEPENDENCE_REQUIRED`. Live demo માં `change.verify` permission ફક્ત `Admin`/`QA Reviewer` role
પાસે છે (QA Releaser/Supervisor/Process Engineer પાસે નથી) — એટલે `admin` જ એકમાત્ર ઉપલબ્ધ independent
બીજો signer છે.

→ signature meaning `Verified`, state `VERIFICATION`.

**સ્ટેપ ૭ — "Make effective" (login: `qa.releaser`):**

| Field | Value |
|---|---|
| Effective at | આવતી કાલ |
| Required training has been completed | ચેક |

→ state `EFFECTIVE`.

**સ્ટેપ ૮ — "Close (sign)" (same login, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Post-implementation review conclusion | `New fill-volume target (0.55 mL) implemented and verified with no adverse effect on 3 subsequent batches.` |

→ signature meaning `Approved`, state `CLOSED`.

---

#### 🔧 Rollback ઉદાહરણ (2026-10-09 ઉમેરેલ) — બીજો change, VERIFICATION માંથી rolled back

CHG-2601-001 તો CLOSED (terminal) પહોંચી ગયો — rollback demonstrate કરવા નવો, અલગ change જોઈએ, જે
VERIFICATION સુધી જાય અને ત્યાં જ undo કરવો પડે. Login seq. એ જ: `qa.reviewer` → `qa.releaser` →
`qa.reviewer` → `admin` (verify) → `qa.releaser` (rollback sign).

> ✅ **2026-10-09 live-verified:** આ flow curl દ્વારા live `ebmr-new-api` સામે ચલાવીને ચકાસેલ (demo DB
> પર અલગ owner/releaser pair — `operator1` owner, `qa.releaser` approve/rollback sign, `qa.reviewer`
> verify sign — જેથી SoD independence confirm થાય) — final state `ROLLED_BACK`, real `signature_id`
> પાછો આવ્યો.

**સ્ટેપ ૧ — "Raise a change control" (`/changes`, login: `qa.reviewer`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Change number | `CHG-2601-002` |
| Type | `Equipment` |
| Classification | `Temporary` |
| Current state | `Filler-02 pressure sensor calibration interval = 90 days (per PM-FILLER-02 schedule).` |
| Proposed state | `Filler-02 pressure sensor calibration interval shortened to 30 days, trial basis, to evaluate drift pattern before the next scheduled PM.` |
| Reason for change | `Trending shows sensor drift approaching alert limit near the end of the 90-day interval on the last 2 cycles; shortening to 30 days as a temporary trial while root cause investigation (DEV-2026-0087) is open.` |
| Emergency change | અનચેક |

"Raise change" ક્લિક → `CHG-2601-002` listed, state `DRAFT`.

**સ્ટેપ ૨ — "Assess impact" (same login):**

| Field | Value |
|---|---|
| Regulatory impact | `No submission impact -- internal PM schedule change only.` |
| Requires regulatory review | અનચેક |
| Validation impact | `Calibration interval change requires re-verification that 30-day cycle captures drift before alert limit.` |
| Revalidation required | **ચેક** |
| Training impact | `None -- interval is system-scheduled, no operator procedure change.` |
| Training required | અનચેક |

→ state `IMPACT_ASSESSMENT`.

**સ્ટેપ ૩ — "Approve (sign)" (login: `qa.releaser`, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Approval notes | `Trial interval approved pending verification of drift-capture adequacy.` |

→ signature meaning `Approved`, state `APPROVAL`.

**સ્ટેપ ૪ — "Mark implemented" (login: `qa.reviewer`):** → state `IMPLEMENTATION`.

**સ્ટેપ ૫ — "Add task" (same login):**

| Field | Value |
|---|---|
| Description | `Update PM-FILLER-02 schedule to 30-day calibration interval; monitor next 2 cycles for drift trend.` |
| Owner (picker) | `qa.reviewer — QA Reviewer` |
| Due date | આજ + ૩૦ દિવસ |

**સ્ટેપ ૬ — "Verify (sign)" (login: `admin`, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Verification evidence | `30-day interval trend reviewed after first cycle -- drift pattern still approaches alert limit mid-cycle, 30 days does NOT meaningfully improve capture vs. 90 days. Recommend reverting while a sensor-replacement CAPA is evaluated instead.` |

→ signature meaning `Verified`, state `VERIFICATION`.

**સ્ટેપ ૭ — 🔧 "Rollback (sign)" (`/changes/{id}`, login: `qa.releaser`, password `ChangeMe123!`) —
2026-10-10 UI FIXED, હવે real button છે:**

| Field (UI label) | ભરવાની Value |
|---|---|
| Rollback reason | `Verification (step 6) shows the 30-day trial interval does not meaningfully improve drift capture over the original 90-day schedule; reverting Filler-02 PM-FILLER-02 to its original 90-day interval while sensor replacement is evaluated under a separate CAPA.` |

→ signature meaning `Approved`, state `ROLLED_BACK`, `rollback_reason`/`rolled_back_at` "Closure" tab
પર દેખાય. "Rollback"/"Close" બંને button હવે અદૃશ્ય (terminal state, `ALLOWED_FROM` ખાલી).

> ✅ **2026-10-10 live-verified (UI, Playwright):** "Rollback" button (danger-styled, "Close" ની બાજુમાં,
> ફક્ત IMPLEMENTATION/VERIFICATION state માં દેખાય) → signed modal → submit → "Closure" tab પર real
> `ROLLBACK REASON`/`ROLLED BACK AT` text confirm થયા (`CHG-LIVE-1791611845` સામે, same backend data
> આ doc ના earlier 2026-10-09 curl-verification એ create કરેલ હતું).

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| QMS-CHG-00 | ઉપરનું સ્ટેપ ૧-૮ (qa.reviewer → qa.releaser → qa.reviewer → admin → qa.releaser) exact values સાથે run કરો | `CHG-2601-001` `CLOSED` state, version 8, `risk_ref` = `RSK-DEMO-001` | Change Control, Risk Register |
| QMS-CHG-01 | Change draft → impact → approve (sign) → implement → verify (sign) → close (sign) | State `CLOSED` | Change Control |
| QMS-CHG-02 | Impact assessment માં risk_ref cite કરે | Risk Register FK link સાચો | Change Control, Risk Register |
| QMS-CHG-03 | Document release change_control_id cite કરે | Document version → Change Control real FK | Change Control, Documents |
| QMS-CHG-04 | Emergency change — pre-approval bypass કરીને implement | State directly IMPLEMENTATION, emergency_reason ફરજિયાત | Change Control |
| QMS-CHG-05 🔧 | DRAFT state માંથી `rollback_reason` સાથે `/close` call કરો (implement પહેલાં) | `409 INVALID_TRANSITION` — rollback ફક્ત IMPLEMENTATION/VERIFICATION માંથી જ માન્ય | Change Control |
| QMS-CHG-06 🔧 | VERIFICATION state સુધી pipeline run કરીને પછી signed `rollback_reason` સાથે `/close` call કરો (qa.releaser sign) | State `ROLLED_BACK`, `rollback_reason`/`rolled_back_at` set, real `signature_id` પાછો આવે | Change Control |

---

## ૨૩.૩ Complaints

**શું છે અને શા માટે જરૂરી:** Market માંથી આવતી product complaint નો intake, investigation, અને
regulatory reportability decision (શું FDA ને જણાવવું પડે?).

**કેવી રીતે કામ કરે:** `RECEIVED → TRIAGE → {NO_INVESTIGATION_JUSTIFIED|INVESTIGATION} →
REPORTABILITY_ASSESSMENT → RESPONSE → CLOSED`.

| Step | Permission | Signed? |
|---|---|---|
| Reportability assessment | `complaint.reportability` | હા |
| Close | `complaint.close` | હા |

**બીજા modules સાથે જોડાણ:** 🔧 `capa_required=true` હવે real draft CAPA auto-create કરે છે (SG-103
CAPA-half RESOLVED 2026-10-09 — `field_action_required` હજુ flag-only, auto-create નથી). Genealogy
lookup (lot/serial થી batch trace) હજુ deferred — no cross-module call. External MDR/FAERS submission
data-capture only.

**ઉદાહરણ:** Customer MJ-PFS syringe ના plunger issue ની complaint report કરે → `admin` create → triage
→ investigation → reportability assessment (sign, applicable_regime="FDA_MDR") → response → close (sign).

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-09 ઉમેરેલ)

UI માં જે-તે field નું exact label સાથે — live system માં સીધું ભરી શકાય એવું realistic pharma data.
Login: આખો flow `admin` (આ live demo માં `admin` ને `scripts/enable_all_roles_for_admin.py` ચલાવીને
બધા role assign કરેલ છે — `complaint_record` પાસે પોતાનું owner/investigator identity column જ ના
હોવાથી independent-signer rule ફક્ત role-level enforce થાય છે, person-level નહીં).

> ✅ **2026-10-09 live-verified:** આ આખો flow (સ્ટેપ ૧-૭) curl દ્વારા live `ebmr-new-api` સામે ચલાવીને
> ચકાસેલ — `CMP-MJPFS-001` complaint `RECEIVED→TRIAGE→INVESTIGATION→REPORTABILITY_ASSESSMENT→RESPONSE→
> CLOSED` (version ૧→૭). Reportability sign પહેલા `admin` પાસે "Postmarket Regulatory Affairs" role ના
> હોવાથી `403 ROLE_MISSING` મળ્યું હતું — role assign કર્યા પછી જ સફળ થયું (real role-gate, bypass નથી).
> `capa_required=true`/`field_action_required=true` સાચે DB માં persist થયા.

**સ્ટેપ ૧ — "Log complaint" (`/complaints`, login: `admin`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Complaint number | `CMP-MJPFS-001` |
| Received at | આજની તારીખ |
| Source channel | `Written` |
| Nature code | `DEVICE_MALFUNCTION` |
| Description | `Customer reports the plunger sticks and fails to fully deliver the dose on an MJ-PFS prefilled syringe.` |
| Product version ID (picker) | `MJ-PFS-40MG v1` |
| Lot / batch / serial reference | `MJ-PFS-B-2601` |
| Complainant contact | `Dr. A. Shah, prescribing physician office` |

"Log complaint" ક્લિક → list માં `CMP-MJPFS-001` state `RECEIVED`. (`constituent_classification` આ
create modal માં નથી — ફક્ત Triage step માં settable.)

**સ્ટેપ ૨ — "Triage":**

| Field (UI label) | ભરવાની Value |
|---|---|
| Severity | `Major` |
| Injury, death or malfunction reported | ચેક |
| Constituent classification | `Device` |

→ state `TRIAGE`.

**સ્ટેપ ૩ — "Investigation decision":**

| Field | Value |
|---|---|
| Investigation required | ચેક |

→ state `INVESTIGATION`.

**સ્ટેપ ૪ — "Record investigation":**

| Field | Value |
|---|---|
| Findings | `Confirmed plunger-rod friction out of spec on lot MJ-PFS-B-2601, affecting dose delivery.` |
| Conclusion | `Confirmed device defect: plunger-rod tolerance drift on lot MJ-PFS-B-2601.` |

→ state `REPORTABILITY_ASSESSMENT`.

**સ્ટેપ ૫ — "Reportability assessment" (sign — role "Postmarket Regulatory Affairs" ફરજિયાત, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Applicable regimes | `FDA_MDR` ચેક |
| Rationale | `Confirmed device malfunction with potential for patient harm meets FDA MDR reportability criteria.` |
| Submission due | `2026-10-29` |
| CAPA required | ચેક |
| Field action required | ચેક |

→ state `RESPONSE`. નોંધ: આ ceremony modal `capa_rationale`/`field_action_rationale` text field નથી
આપતું — ફક્ત બે checkbox; API પોતે rationale string સ્વીકારે છે (curl verified, DB persist), પણ UI થી
લખી શકાતું નથી.

**સ્ટેપ ૬ — "Record communication" (Communications tab, type "Response"):**

| Field | Value |
|---|---|
| Direction | `Outbound` |
| Recipient | `Dr. A. Shah` |
| Message | `We have confirmed the defect on lot MJ-PFS-B-2601 and initiated corrective action; a replacement unit has been issued.` |

**સ્ટેપ ૭ — "Close" (sign — role "QA Releaser" ફરજિયાત, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Conclusion | `Investigation complete; FDA MDR reportability assessed; response sent; CAPA/field-action rationale captured for manual follow-up.` |

→ state `CLOSED`, version `7`.

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| QMS-CMP-00 | ઉપરનું સ્ટેપ ૧-૭ exact values સાથે run કરો (admin, બધા role assign કરેલ) | `CMP-MJPFS-001` `CLOSED`, version 7 | Complaints |
| QMS-CMP-01 | Complaint create → triage → investigation → reportability (sign) → response → close (sign) | State `CLOSED` | Complaints |
| QMS-CMP-02 | Reportability assessment "FDA_MDR applicable" mark કરે | `applicable_regimes` record થાય, પણ real submission integration નથી | Complaints |
| QMS-CMP-03 🔧 | Complaint CAPA-worthy mark કરે (`capa_required=true`) | Flag set **+ real draft CAPA auto-created** (`source_type="complaint"`, state `OPEN`) | Complaints, CAPA |
| QMS-CMP-04 | Complaint lot/serial ref આપે, genealogy trace expect કરે | Automatic lookup **નથી** — deferred gap | Complaints, Genealogy |

---

## ૨૩.૪ Field Actions (Recalls/Corrections)

**શું છે અને શા માટે જરૂરી:** Complaint/deviation/CAPA/trend/regulatory-request થી triggered correction/
removal/recall — affected lot/scope define, regulatory decision, execute+notify, reconcile, effectiveness
check.

**કેવી રીતે કામ કરે:** `ASSESSMENT → SCOPE_DEFINITION → REGULATORY_DECISION → APPROVAL →
EXECUTION_NOTIFICATION → RECONCILIATION → EFFECTIVENESS → CLOSED`. `scope()` CLOSED action ને ફરી
reopen કરી શકે (revision++).

| Step | Permission | Signed? |
|---|---|---|
| Reportability, Approve, Close | `field_action.reportability`/`.approve`/`.close` | હા |

**બીજા modules સાથે જોડાણ:**
- `risk_assessment_ref` → **Risk Register** — real FK (field action પોતાનું risk cite કરે).
- ⚠️ **Genealogy જોડાયેલ નથી** — `lot_batch_serial_refs`/`distribution_ref` caller-supplied JSON, Genealogy
  module ને query નથી કરતું. User એ manually affected lots લખવા પડે.
- 🔧 `capa_required=true` હવે real draft CAPA auto-create કરે છે (SG-106 RESOLVED 2026-10-09 — doc માં
  અગાઉ ખોટી રીતે "SG-105" cite થયેલું, SG-105 ખરેખર FAR-FR-008 ERP/WMS consignee-scope requirement વિશે
  છે, અલગ gap; FAR-FR-020 export હજુ open).

**ઉદાહરણ:** MJ-PFS batch `MJ-PFS-B-2601` ના કોઈ lot માં defect confirmed → `admin` field action create
(trigger_ref = complaint) → scope define (affected lots manually list) → regulatory decision → approve
(sign) → execution/notification → reconciliation (affected/returned count) → effectiveness → close (sign).

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-09 ઉમેરેલ)

Login: આખો flow `admin`. Trigger તરીકે ઉપર §૨૩.૩ માં બનાવેલ complaint `CMP-MJPFS-001` વાપરેલ (real FK).

> ✅ **2026-10-09 live-verified:** આ આખો flow (સ્ટેપ ૧-૮) curl દ્વારા live ચલાવીને ચકાસેલ — `FA-MJPFS-001`
> field action
> `ASSESSMENT→SCOPE_DEFINITION→REGULATORY_DECISION→APPROVAL→EXECUTION_NOTIFICATION→RECONCILIATION→
> EFFECTIVENESS→CLOSED` (version ૧→૮). Close command એ `reconciliation.outstanding_count=0` અને
> `effectiveness_check` બંનેની હાજરી code-level ચકાસ્યા પછી જ `CLOSED` આપ્યું — `outstanding_count>0`
> સાથે મોકલ્યું હોત તો `RECONCILIATION_INCOMPLETE` સાથે block થાત.

**સ્ટેપ ૧ — "Raise a field action" (`/field-actions`, login: `admin`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Action number | `FA-MJPFS-001` |
| Action type | `Correction` |
| Trigger type | `Complaint` |
| Trigger record (picker) | `CMP-MJPFS-001` |

→ state `ASSESSMENT`.

**સ્ટેપ ૨ — "Define scope":**

| Field (UI label) | ભરવાની Value |
|---|---|
| Lot / batch / serial reference | `MJ-PFS-B-2601` |
| Action required | `Return` |
| Place a distribution hold on this scope | ચેક |

→ state `SCOPE_DEFINITION`. નોંધ: આ modal એક સમયે ફક્ત **એક જ** scope item submit કરે છે, અને
`product_ref`/`distribution_ref` માટે કોઈ field નથી — backend એ બંને સ્વીકારે છે (curl verified), UI થી
enter કરી શકાતું નથી.

**સ્ટેપ ૩ — "Reportability" (sign — role "Postmarket Regulatory Affairs" ફરજિયાત, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Applicable regimes | `FDA_RECALL` ચેક |
| Decision | `Reportable` |
| Submission due | `2026-10-24` |
| Rationale | `Confirmed lot-specific device defect affecting dose delivery meets FDA field-correction reportability criteria.` |

→ state `REGULATORY_DECISION`. નોંધ: Complaint ના reportability ceremony થી અલગ — અહીં **CAPA required
checkbox જ UI માં નથી** — ફક્ત direct API call થી `capa_required=true` set થઈ શકે (🔧 જે હવે set કરવાથી
backend માં real draft CAPA auto-create થાય છે, જુઓ §૨૩.૪ ઉપર — UI checkbox ઉમેરવાનું હજુ બાકી).

**સ્ટેપ ૪ — "Approve" (sign — role "QA Releaser" ફરજિયાત, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Conclusion | `Correction approved for lot MJ-PFS-B-2601 distribution hold and customer notification.` |

→ state `APPROVAL`.

**સ્ટેપ ૫ — "Record notification" (Notifications tab):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Recipient | `MedSupply Distributors Inc.` |
| Channel | `Letter` |
| Message | `Field correction notice: please quarantine remaining MJ-PFS-B-2601 units and follow enclosed correction instructions.` |

→ state `EXECUTION_NOTIFICATION`.

**સ્ટેપ ૬ — "Reconcile":**

| Field | Value |
|---|---|
| Affected | `120` |
| Contacted | `120` |
| Returned | `110` |
| Corrected | `110` |
| Destroyed | `0` |
| Unavailable | `10` |
| Outstanding | `0` |

→ state `RECONCILIATION` (`outstanding_count=0` close માટે ફરજિયાત શરત).

**સ્ટેપ ૭ — "Effectiveness":**

| Field | Value |
|---|---|
| Result | `Pass` |
| Evidence | `No recurrence of plunger-stick complaints in the 90-day follow-up window.` |

→ state `EFFECTIVENESS`.

**સ્ટેપ ૮ — "Close" (sign — role "QA Releaser" ફરજિયાત, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Conclusion | `Field correction complete: reconciliation shows zero outstanding units, 90-day effectiveness check passed.` |

→ state `CLOSED`, version `8`.

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| QMS-FA-00 | ઉપરનું સ્ટેપ ૧-૮ exact values સાથે run કરો | `FA-MJPFS-001` `CLOSED`, version 8 | Field Actions |
| QMS-FA-01 | Field action create → scope → regulatory decision → approve (sign) → notify → reconcile → effectiveness → close (sign) | State `CLOSED` | Field Actions |
| QMS-FA-02 | Scope define માં risk_assessment_ref cite કરે | Real FK link to Risk Register | Field Actions, Risk Register |
| QMS-FA-03 | Affected lots manually enter કરવા (genealogy auto-trace expect) | Automatic trace **નથી** — manual entry જોઈએ | Field Actions, Genealogy |
| QMS-FA-04 | CLOSED action ફરી scope() call કરે | Reopen → `SCOPE_DEFINITION`, revision++ | Field Actions |

---

## ૨૩.૫ Internal Audits

**શું છે અને શા માટે જરૂરી:** GxP program/criteria સામે internal audit — finding record, CAPA-worthy
response, verify, close — company પોતે પોતાની ભૂલ શોધે (external inspector પહેલાં).

**કેવી રીતે કામ કરે:** `SCHEDULED → IN_PROGRESS → FINDINGS_OPEN → CLOSED`. Finding: `OPEN →
RESPONSE_SUBMITTED → VERIFIED`.

| Step | Permission | Signed? |
|---|---|---|
| Start, Finding Verify, Close | `internal_audit.start`/`.finding.verify`/`.close` | હા |

**બીજા modules સાથે જોડાણ:** **Real SoD check** — `lead_auditor_id`/team member `auditees` માં ના હોવો
જોઈએ (`AUDITOR_SOD_CONFLICT`). 🔧 `capa_required=true` હવે real draft CAPA auto-create કરે છે (SG-101
AUDIT-FR-008 RESOLVED 2026-10-09, `source_type="audit"` પેરન્ટ audit ને point કરે છે — reschedule/
metrics/export હજુ open). External audit
tracking entity જ નથી (nothing to build).

**ઉદાહરણ:** Sterile manufacturing area નો internal audit → `admin` audit create (lead_auditor =
auditor, auditees = aseptic team — SoD check pass) → start (sign) → finding add (observation on
cleaning log gap) → `qa.reviewer` response submit → verify (sign) → close (sign).

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-09 ઉમેરેલ)

Login seq.: `admin` (schedule + start + finding add) → `qa.reviewer` (response submit) → `qa.releaser`
(independent verify + close, બંને signed).

> ✅ **2026-10-09 live-verified:** આખો flow (સ્ટેપ ૧-૬) curl દ્વારા live ચલાવીને ચકાસેલ — `IA-2026-
> ASEPTIC-01` state `SCHEDULED→IN_PROGRESS→FINDINGS_OPEN→CLOSED` (version ૧→૪), finding `FIND-ASEPTIC-01`
> state `OPEN→RESPONSE_SUBMITTED→VERIFIED` (version ૧→૩), start/verify/close ત્રણેય signed.

**સ્ટેપ ૧ — "Schedule an internal audit" (`/audits`, login: `admin`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Audit number | `IA-2026-ASEPTIC-01` |
| Programme reference | `2026 Annual GxP Audit Program` |
| Scheduled date | આજ + ૩ દિવસ |
| Audit criteria | `21 CFR 820, ISO 13485` |
| Process scope | `Sterile Manufacturing - Grade C/D cleaning program` |
| Lead auditor (user ID) | `qa.reviewer` |
| Auditees | `process.engineer` (+ "Add auditee" repeatable row) |

> 🔧 **2026-10-09 ઉમેરેલ field:** "Schedule an internal audit" form માં પહેલા **`auditees` field જ
> નહોતું** — ફક્ત "Lead auditor" settable હતું; `auditees` ફક્ત audit detail page પર read-only
> `JsonPanel` તરીકે દેખાતું, set કરવાનો કોઈ UI રસ્તો નહોતો (SoD demo UI થી impossible હતી). Fix: "Add
> auditee" repeatable row field ઉમેર્યું (એ જ `RepeatableRows`/userSelect pattern aseptic ના Equipment
> field જેવું) — હવે create form થી જ auditees set કરી શકાય, `AUDITOR_SOD_CONFLICT` genuinely demo
> કરી શકાય.

"Schedule audit" ક્લિક → list માં `IA-2026-ASEPTIC-01` state `SCHEDULED`.

**સ્ટેપ ૨ — "Start audit" (sign) (login: `admin`, password `ChangeMe123!`):** → state `IN_PROGRESS`.

**સ્ટેપ ૩ — "Add finding" (login: `admin`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Finding number | `FIND-ASEPTIC-01` |
| Severity | `Major` |
| Requirement reference | `21 CFR 211.68(b) - Equipment cleaning and maintenance records` |
| Observation | `Grade C corridor cleaning log for Filler-01 area shows a gap of 3 consecutive shifts with no entry and no documented justification.` |
| Owner | `process.engineer` |

→ finding state `OPEN`, audit આપોઆપ `FINDINGS_OPEN`.

**સ્ટેપ ૪ — "Respond to finding" (login: `qa.reviewer`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Correction | `Cleaning log gap reviewed with sanitation team; missing entries backfilled from equipment usage log cross-check, area re-verified clean before next use.` |
| Root cause | `Shift-handover SOP did not require the outgoing sanitation operator to confirm log completion before sign-off.` |
| Corrective action | `Revise cleaning SOP shift-handover checklist to require log-completeness confirmation at every shift change.` |
| A formal CAPA is required | ચેક |
| CAPA rationale | `Systemic shift-handover gap could recur across other cleaning logs; CAPA warranted.` |

→ finding state `RESPONSE_SUBMITTED`.

**સ્ટેપ ૫ — "Verify finding" (sign) (login: `qa.releaser` — qa.reviewer થી અલગ, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Verification notes | `Revised shift-handover checklist confirmed in effect; walkthrough of 3 subsequent shifts shows complete, gap-free cleaning logs.` |
| Effective | `Yes - finding can close` |

→ finding state `VERIFIED`.

**સ્ટેપ ૬ — "Close audit" (sign) (login: `qa.releaser`):**

| Field | Value |
|---|---|
| Conclusion | `All findings verified effective. Aseptic area internal audit closed; shift-handover cleaning-log CAPA tracked separately.` |

→ audit state `CLOSED`.

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| QMS-AUD-00 | ઉપરનું સ્ટેપ ૧-૬ exact values સાથે run કરો | Audit `CLOSED`, finding `VERIFIED` | Internal Audits |
| QMS-AUD-01 | Audit create → start (sign) → finding add → response → verify (sign) → close (sign) | State `CLOSED` | Internal Audits |
| QMS-AUD-02 | lead_auditor_id પોતે auditees માં listed હોય | Block — `AUDITOR_SOD_CONFLICT` | Internal Audits |
| QMS-AUD-03 🔧 | Finding `capa_required=true` mark કરે | Flag set **+ real draft CAPA auto-created** (`source_type="audit"`) | Internal Audits, CAPA |
| QMS-AUD-04 | Finding verify ના થયું હોય, audit close કરવાનો પ્રયત્ન | Block — open finding | Internal Audits |

---

## ૨૩.૬ Risk Register

**શું છે અને શા માટે જરૂરી:** Product/process/system/supplier/equipment risk નું formal assessment —
initial score → controls → residual score → acceptance → periodic review, જેથી decision reproducible
રહે methodology બદલાય તો પણ.

**કેવી રીતે કામ કરે:** `DRAFT → INITIAL_ASSESSMENT → CONTROLS_MITIGATION → RESIDUAL_ASSESSMENT →
ACCEPTED → (review) → NEW_VERSION`. Methodology `rules.gxp_rule_definition` (Rules engine) માંથી reuse
થાય, નવો master નહીં.

| Step | Permission | Signed? |
|---|---|---|
| Accept | `risk.accept` | ⚠️ **ના** — ~~this doc previously said "હા" here, that was backwards~~ (2026-10-09 ફિક્સ: code-ચકાસેલ) `accept_risk()` ક્યારેય `_resolve_signature()` call જ નથી કરતું — ફક્ત `accepted_role` (free text, દા.ત. "Head of Quality") + `rationale` ફરજિયાત, કોઈ password re-auth ceremony નથી |
| Review (periodic) | `risk.review` | **હા** — ~~this doc previously said "ના, documented gap" here, that was backwards~~ (2026-10-09 ફિક્સ) "Reviewed", record owner (`owner_subject_id`)થી independent QA Reviewer (SG-138 resolved 2026-09-10, Document 106 §9 row 97) — frontend `/risks/{id}` પર review જ એકમાત્ર transition છે જે `<SignatureCeremony>` (password re-auth) વાપરે છે, accept/assessment/controls ત્રણેય plain form છે |

**બીજા modules સાથે જોડાણ:** `field_action.risk_assessment_ref` → real FK (doc #૨૩.૪). `change_control.
risk_ref` → real FK (doc #૨૩.૨). Deviation/OOS/Complaint/Audit **auto-trigger risk review નથી કરતા** —
manual, optional `trigger_source_ref` સાથે.

**ઉદાહરણ:** Sterile filling process risk assessment → `process.engineer` draft → initial assessment →
controls/mitigation add → residual assessment → `qa.releaser` accept (rationale + role, unsigned) → ૧
વર્ષ પછી `qa.reviewer` periodic review (**sign**, independent of owner).

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-09 ઉમેરેલ)

UI માં જે-તે field નું exact label સાથે — live system માં સીધું ભરી શકાય એવું realistic pharma data.
Login: `admin` (આ live demo માં `admin` user ને `enable_all_roles_for_admin.py` script દ્વારા **બધા જ**
role permissions આપેલ છે, એટલે Risk Register ના બધા સ્ટેપ એક જ login થી ચાલે છે — review સિવાય કોઈ પણ
સ્ટેપ independent signer ફરજિયાત નથી કરતું).

> ✅ **2026-10-09 live-verified:** આખો flow (methodology release → risk create → initial assessment →
> controls → residual assessment → accept with a near-term review date) curl દ્વારા live `ebmr-new-api`
> સામે ચલાવીને ચકાસેલ — risk ખરેખર `ACCEPTED` પહોંચ્યું, અને accept પછી `GET /dashboard/v1/reminders`
> (Topbar ની bell icon, દરેક page પર) માં નવી `risk_review_due` category સાચા `due_date`/`days_remaining`
> સાથે દેખાઈ — doc #૨૩.૬ ની નીચેની "no scheduler" નોંધ સાથે જોડાયેલ નવું pull-side reminder fix (જુઓ નીચે).

**પૂર્વ-જરૂરિયાત — risk methodology:** "Raise a risk" ફોર્મ નું "Risk methodology" field એક **released**
`risk_methodology` rule માંગે છે (Rules page પર author થાય, doc #૨૩ ના scope બહાર) — આ demo માટે
`risk-methodology-fmea-demo v1.0.0` નામની methodology પહેલેથી release કરેલ છે (QA Releaser સહી સાથે),
dropdown માં એ પસંદ કરો.

**સ્ટેપ ૧ — "Raise a risk" (`/risks`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Risk number | `RSK-DEMO-001` |
| Risk type | `Process` |
| Hazard or problem | `Sterile filling line contamination risk during intervention.` |
| Potential effect | `Non-sterile product reaching patient, serious adverse event.` |
| Risk methodology | `risk-methodology-fmea-demo v1.0.0` (dropdown) |
| Context | ખાલી રાખો |

"Raise risk" ક્લિક → risk state `DRAFT`.

**સ્ટેપ ૨ — "Add assessment" (risk ખોલીને, પહેલી વાર — initial assessment):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Risk methodology | `risk-methodology-fmea-demo v1.0.0` (પહેલેથી ભરેલ હશે) |
| Severity | `4` |
| Occurrence | `3` |
| Detectability | `2` |

→ RPN auto-calculate (`24`) દેખાશે, state `INITIAL_ASSESSMENT`.

**સ્ટેપ ૩ — "Add controls":**

| Field (UI label) | ભરવાની Value |
|---|---|
| Control type | `Engineering` |
| Control description | `Add redundant isolator pressure interlock.` |
| Mitigation action | `ECO-9981 — interlock installation tracked as a change-controlled action.` |

→ state `CONTROLS_MITIGATION`.

**સ્ટેપ ૪ — "Add assessment" (ફરી — residual assessment, same form):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Severity | `4` |
| Occurrence | `1` |
| Detectability | `2` |

→ RPN `8`, state `RESIDUAL_ASSESSMENT`.

**સ્ટેપ ૫ — "Accept" (unsigned — role + rationale only):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Accepting role | `QA Manager` |
| Acceptance rationale | `Residual risk acceptable after adding redundant isolator pressure interlock.` |
| Next review due | આજની તારીખ + ૧૦ દિવસ (દા.ત. `2026-10-19`) |

"Accept" ક્લિક → **કોઈ password prompt નથી** (ઉપરનું ફિક્સ જુઓ — Accept signed નથી) → state `ACCEPTED`.

→ હવે કોઈ પણ logged-in user ને, કોઈ પણ page પર, Topbar ની bell icon માં "Risk periodic review due —
RSK-DEMO-001" ૧૦ દિવસમાં due તરીકે દેખાશે (`GET /dashboard/v1/reminders?within_days=30`).

> 🔧 **2026-10-09 ઉમેરેલ feature (gap નહીં, enhancement):** અગાઉ `next_review_due_at` ફક્ત `/risks` page
> પર જ (એ risk ને ખોલો તો) દેખાતું — platform-wide કોઈ પણ reminder નહોતું. હવે
> `app/modules/dashboard/service.py::list_upcoming_reminders()` એ ACCEPTED state ના દરેક risk ને પણ
> scan કરે છે (material-lot expiry/equipment-calibration ની જ pattern) અને Topbar bell + `/home` page
> બંને પર surface કરે છે. આ હજુ પણ **pull-only** છે — કોઈ push notification/background scheduler નથી
> (એ અડધો ભાગ ઈરાદાપૂર્વક ખુલ્લો જ છે, `risk_models.py`ની comment જુઓ) — પણ હવે ઓછામાં ઓછું "કોઈ પણ
> સાઇન-ઈન user એ જુએ છે" એ ખાતરી છે, પહેલા કંઈ જ નહોતું.

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| QMS-RSK-01 | Risk draft → initial → controls → residual → accept (role + rationale, **unsigned**) | State `ACCEPTED` | Risk Register |
| QMS-RSK-02 | Periodic review run કરે (QA Reviewer, independent of owner) | Review **sign** થાય — "Reviewed" (SG-138 resolved) | Risk Register |
| QMS-RSK-03 | Change Control impact assessment risk_ref cite કરે | Real FK link | Risk Register, Change Control |
| QMS-RSK-04 | `is_overdue` review date પસાર થાય | Dashboard-page flag set, પણ કોઈ push/scheduler notification નથી (હજુ ખુલ્લો ભાગ) | Risk Register |
| QMS-RSK-05 | Risk ACCEPTED + `next_review_due_at` ૩૦ દિવસની અંદર હોય, `GET /dashboard/v1/reminders` call કરો | `risk_review_due` category સાચા `entity_id`/`label`/`days_remaining` સાથે list માં દેખાય (2026-10-09 ઉમેરેલ) | Risk Register, Dashboard |

---

## ૨૩.૭ Supplier Cases (SCAR)

**શું છે અને શા માટે જરૂરી:** Supplier-caused quality issue (reject/deviation/complaint/audit) ની formal
investigation — containment → supplier ને SCAR → supplier response → internal review → source-status
decision (requalify/suspend/reinstate).

**કેવી રીતે કામ કરે:** Case: `OPEN → CONTAINMENT → SCAR_ISSUED → CLOSED`. SCAR: `SCAR_ISSUED →
SUPPLIER_RESPONSE → IMPLEMENTATION → EFFECTIVENESS → CLOSED`.

| Step | Permission | Signed? |
|---|---|---|
| Review, Close | `scar.review`/`.close` | હા |

**બીજા modules સાથે જોડાણ (real FK):** `supplier_id`→`ebmr.supplier`, `supplier_site_id`→
`ebmr.supplier_site`, `material_id`→`materials.materials` — identity references only (AG-05 one-owner
rule, આ module આ tables નો owner નથી). **SG-097 (2026-09-22) RESOLVED** — doc માં અગાઉ ખોટી રીતે
"SG-091" cite થયેલું હતું (SG-091 ખરેખર અલગ, unrelated gap છે — `signature_policies.reason_required`).
`close_scar()` હવે `source_status_decision="suspend"`/`"reinstate"` પર `supplier_quality` module ના
પોતાના owning command `suspend_supplier()`/`reinstate_supplier()` ને call કરે છે (AG-06 cross-module
owning-command call) — એટલે `ebmr.supplier.status` **ખરેખર write થાય છે**, placeholder નથી. Material
module નો `_is_eligible()`/receipt-examination check (`Supplier.status != "approved"` → receipt
`discrepancy_hold`/`discrepancy_type="source_not_approved"`) એ જ write ને વાંચીને material receipt/
lot-use ને **genuinely gate કરે છે** (2026-10-09 curl દ્વારા live ચકાસેલ, નીચે જુઓ).

**ઉદાહરણ:** Raw material supplier એ out-of-spec lot મોકલ્યું → `admin` case create (supplier_id,
material_id link) → containment → SCAR issue → supplier response → `qa.reviewer` review (sign) →
`qa.releaser` close (sign, source_status_decision="requalify").

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-09 ઉમેરેલ)

Login seq.: `admin` (supplier/material master data + case/response + receipt) → `qa.releaser`
(qualification approve-sign + SCAR close-sign) → `qa.reviewer` (SCAR review-sign).

> ✅ **2026-10-09 live-verified — SG-097 end-to-end proof:** supplier `SUP-NAOCL-01` ("Apex Chemical
> Supply Co.") qualification approved (`status="approved"`) → SCAR `SCAR-2026-NAOCL-01` ને
> `source_status_decision="suspend"` સાથે close કર્યું → `GET /suppliers/v1/{id}` confirm `status=
> "suspended"` → એ જ supplier પરથી નવો material receipt create+examine કર્યો (બધા answer "clean") →
> receipt `discrepancy_hold`, `discrepancy_type="source_not_approved"`. **Gate genuinely enforced —
> SG-097 RESOLVED, placeholder નથી.**

**સ્ટેપ ૦a — Supplier master data (`/suppliers`, login: `admin`), પૂર્વ-જરૂરી:**

| Field (UI label) | ભરવાની Value |
|---|---|
| Supplier code | `SUP-NAOCL-01` |
| Legal name | `Apex Chemical Supply Co.` |
| Role type | `Supplier` |
| Country | `US` |

**સ્ટેપ ૦b — "Request supplier qualification" → "Approve" (sign, login: `qa.releaser`):**

| Field | Value |
|---|---|
| Supplier site | `Apex Main Plant` |
| Risk class | `Medium` |
| Decision | `approved` |

→ `Supplier.status`: `draft → under_qualification → approved`.

**સ્ટેપ ૦c — "New material" (`/materials`, login: `process.engineer`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Code | `RM-NAOCL-01` |
| Name | `Sodium Hypochlorite (NaOCl) 1% Solution, USP grade` |
| UOM | `L` |

**સ્ટેપ ૧ — "Open a supplier quality case" (`/supplier-cases`, login: `admin`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Case number | `SQC-2026-NAOCL-01` |
| Defect code | `OOS-ASSAY-LOW` |
| Severity | `Major` |
| Supplier ID | `Apex Chemical Supply Co.` (picker) |
| Material ID | `RM-NAOCL-01` (picker) |
| Affected lot | `APEX-NAOCL-LOT-2241` |
| Containment | `Lot APEX-NAOCL-LOT-2241 placed on hold pending SCAR investigation.` |

**સ્ટેપ ૨ — "Issue SCAR" (login: `admin`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| SCAR number | `SCAR-2026-NAOCL-01` |
| Problem statement | `Incoming NaOCl lot APEX-NAOCL-LOT-2241 failed assay (measured 0.82% w/v against 1.0% ±0.05% spec) on incoming QC testing.` |

**સ્ટેપ ૩ — "Record supplier response" (login: `admin`, supplier liaison વતી):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Supplier acknowledgment | `Supplier acknowledges receipt of SCAR-2026-NAOCL-01 and confirms investigation underway.` |
| Supplier root cause | `Dilution skid flow-meter drift caused under-concentration on this batch; confirmed via calibration records.` |
| Supplier corrective actions | `Recalibrate dilution skid flow-meter and add in-process assay check every 2 hours.` |

> 🐛 **2026-10-09 real bug fixed:** "Supplier acknowledgment" field આ form માં પહેલા **હતું જ નહીં** —
> `review_scar()` ને `scar.acknowledgment` truthy ફરજિયાત છે (નહીં તો `SUPPLIER_RESPONSE_INCOMPLETE`),
> પણ form ફક્ત `supplier_root_cause`/`supplier_actions` જ મોકલતું — **pure UI-click flow થી submit
> કરેલ કોઈ પણ SCAR response ક્યારેય review pass જ નહોતું કરી શકતું.** Fix: "Supplier acknowledgment"
> textarea field ઉમેર્યું, `acknowledgment: {statement: ...}` મોકલે છે.

**સ્ટેપ ૪ — "Review SCAR response" (sign) (login: `qa.reviewer`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Decision | `accepted` |
| Rationale | `Root cause (flow-meter drift) is well-supported by calibration records; corrective action (recalibration + in-process assay) is adequate and verifiable.` |

**સ્ટેપ ૫ — "Record effectiveness" (login: `admin`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Result | `pass` |
| Evidence | `4 incoming lots checked; all assay results within 0.95-1.05% spec post-recalibration.` |

**સ્ટેપ ૬ — "Close SCAR" (sign) (login: `qa.releaser`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Source status decision | `Suspend` |
| Conclusion | `Recurring OOS-assay pattern on this source combined with a second confirmed incoming failure this quarter; source suspended pending full on-site requalification audit.` |
| Requalification required | ચેક |

→ SCAR `CLOSED`. **તરત `GET /suppliers/v1/{supplier_id}` → `status: "suspended"`.**

**સ્ટેપ ૭ — સાબિતી: હવે આ supplier પરથી નવો receipt create કરો (`/material-receipts`, login: `admin`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Receipt number | `RCPT-NAOCL-SUSPENDED-01` |
| Material | `RM-NAOCL-01` |
| Supplier | `Apex Chemical Supply Co.` (હવે suspended) |
| Received quantity (gross) | `200.000000` |
| Accepted quantity | `200.000000` |

**સ્ટેપ ૮ — "Examine receipt" (બધા જવાબ "clean"):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Material matched with PO/Material number | `Yes` |
| Labeling correct | `Yes` |
| Seal intact? | `Yes` |
| Container count | `4` |
| Internal lot number | `LOT-NAOCL-SUSPENDED-01` |

→ બધા જ જવાબ "clean" હોવા છતાં receipt state `discrepancy_hold` માં જાય છે, banner "On hold
source_not_approved" — આ check UI form પર કોઈ field તરીકે દેખાતું જ નથી, ફક્ત supplier ના current
`status` પરથી server-side silently લાગુ થાય છે.

**સ્ટેપ ૯ — "Disposition" (sign, login: `qa.releaser`) — project-owner-directed 2026-10-12:**
`discrepancy_type="source_not_approved"` પર held receipt ની disposition **ફરજિયાત** `severity=
"significant"` + લિંક કરેલ Deviation માંગે છે — `severity="minor"` પસંદ કરવાનો વિકલ્પ જ UI માં disable
છે (server-side પણ `VALIDATION_FAILED` સાથે block થાય છે). કારણ: suspended supplier પરથી material
accept કરવું એ shipment-level issue નથી, એ organization ની પોતાની supplier-suspension decision નું
override છે — એક લીટીના reason સાથે "minor" તરીકે pass ન થવું જોઈએ. (`identity_mismatch`/`damaged`/
`seal_broken` માટે severity હજુ પણ free choice જ રહે છે.)

| Field (UI label) | ભરવાની Value |
|---|---|
| Decision | `Accepted` |
| Severity | `Significant` (locked, editable નથી) |
| Justification | `Supplier requalification audit complete per SCAR-2026-NAOCL-01; accepting this lot under deviation pending full requalification.` |
| Deviation | કોઈ પણ existing deviation record (picker) |
| Internal lot number | `LOT-NAOCL-SUSPENDED-01-ACC` |

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| QMS-SCR-00 | ઉપરનું સ્ટેપ ૦a-૮ exact values સાથે run કરો | SCAR `CLOSED`, supplier `suspended`, receipt `discrepancy_hold` | Supplier Cases, Suppliers, Materials |
| QMS-SCR-01 | Case create → containment → SCAR issue → supplier response (acknowledgment સહિત) → review (sign) → close (sign) | State `CLOSED` | Supplier Cases |
| QMS-SCR-02 | SCAR close `source_status_decision="suspend"` પછી એ જ supplier પરથી નવો material receipt create+examine કરવાનો પ્રયત્ન | `ebmr.supplier.status` ખરેખર `suspended` થાય (owning-command cross-module call); receipt `discrepancy_hold`/`discrepancy_type="source_not_approved"` પર જાય — **block real છે, SG-097 RESOLVED 2026-09-22** (2026-10-09 live curl-verified) | Supplier Cases, Suppliers, Materials |
| QMS-SCR-02b | સ્ટેપ ૯ ને `severity="minor"` સાથે submit કરવાનો પ્રયત્ન | Block — `VALIDATION_FAILED`, UI માં Severity select જ disabled (2026-10-12 project-owner-directed) | Materials |
| QMS-SCR-03 | SCAR close પછી supplier સાથે નવી case create કરવાનો પ્રયત્ન ("suspend" active હોય) | Block — નવી case ना থাय | Supplier Cases |
| QMS-SCR-04 🔧 | `capa_required=true` mark કરે | Flag set **+ real draft CAPA auto-created** (`source_type="supplier"`, પેરન્ટ `SupplierQualityCase` ને point કરે) | Supplier Cases, CAPA |

---

## ૨૩.૮ Documents (Document Control)

**શું છે અને શા માટે જરૂરી:** SOP/policy/spec/work-instruction/form control — master+version split,
controlled-copy tracking, release signature-gated — quality system નો backbone, બીજા module આના
document ને point કરે.

**કેવી રીતે કામ કરે:** `DRAFT → REVIEW → RELEASED → EFFECTIVE → SUPERSEDED → OBSOLETE`. `release()`
approve+release બંને એક signed step માં (Vault `release_master()` વાપરે — Product/Recipe Master જેવું જ
pattern).

| Step | Permission | Signed? |
|---|---|---|
| Release | `document.release` | **હા — only signed step** |

**બીજા modules સાથે જોડાણ:** `change_control_id` real FK → **Change Control** (doc #૨૩.૨). **Training**
નો `training_requirement.content_document_version_id` આ table ને real FK કરે (જ્યારે training content
= released document).

🔧 **SG-079 RESOLVED (DOC-FR-014 half, 2026-10-09, project-owner-directed — "Simple unsigned log"):**
Per-user acknowledgment capture હવે real operation છે — `POST /documents/v1/versions/{id}/acknowledgments`
+ `GET .../acknowledgments`. **આ Part 11 signature નથી** (AG-07 — login/MFA signature ન ગણાય, અને
DOC-FR-014 પોતે "approval signature થી distinct" કહે છે) — કોઈ challenge/reauth નહીં, receipt પર
`signature_id` હંમેશા `null`. ફક્ત `EFFECTIVE` version પર જ ચાલે (`DOCUMENT_VERSION_OBSOLETE` અન્યથા).
એક user એક version ને ફરી acknowledge કરે તો idempotent (duplicate row નથી, error નથી). DOC-FR-013
(training auto-assignment on release) હજુ open.

**ઉદાહરણ:** Aseptic gowning SOP નવું version → `process.engineer` draft → submit → `qa.releaser` release
(sign) → Training module આ document version ને content તરીકે cite કરીને requirement બનાવે.

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-09 ઉમેરેલ)

Login seq.: પહેલા `qa.reviewer` (document author/owner), પછી `qa.releaser` (independent releaser).

> ✅ **2026-10-09 live-verified:** આ આખો flow (સ્ટેપ ૧-૩) curl દ્વારા live `ebmr-new-api` સામે ચલાવીને
> ચકાસેલ — `SOP-ASEPTIC-GOWN-004 v2.0` state `DRAFT→REVIEW→RELEASED` (record version 3), signed release,
> Vault snapshot written, `training_impact={"required":true}`, `acknowledgment_required=true`.

**સ્ટેપ ૧ — "New draft" (`/documents`, login: `qa.reviewer`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Document code | `SOP-ASEPTIC-GOWN-004` |
| Type | `Sop` |
| Version label | `2.0` |
| Content hash | `c19aef05166f2c3803fab4f9124fc19bc6c5d6af63ee169992c50a0bfb422d45` |
| Externally authored document | અનચેક |

"Create draft" ક્લિક → version `DRAFT`.

**સ્ટેપ ૨ — "Submit for review" (same login):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Reviewer (user ID) | `process.engineer`નો user id (raw UUID paste — **no picker/name-search exists for this field**, known limitation) |

→ state `REVIEW`.

**સ્ટેપ ૩ — "Release (sign)" (login: `qa.releaser` — document owner (`qa.reviewer`) થી independent, password `ChangeMe123!`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Effective from | આજની તારીખ |
| Periodic review due | +૧ વર્ષ |
| Training required before this version can be made effective | ચેક |
| Read-and-understood acknowledgment required | ચેક |

→ version state `RELEASED`, record version `3`, Vault snapshot written, signature captured. Training
module હવે આ document version ને `content_document_version_id` તરીકે cite કરી શકે (નીચે §૨૩.૯ જુઓ).

**સ્ટેપ ૪ — "Make effective" (`/documents`, login: `qa.releaser`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Training confirmed (step 3 માં "Training required" check કરેલ હતું, એટલે ફરજિયાત) | ચેક |

→ version state `EFFECTIVE`, record version `4`. હવે acknowledge કરી શકાય (acknowledgment ફક્ત
`EFFECTIVE` version પર જ માન્ય છે, `RELEASED` પર નહીં).

**સ્ટેપ ૫ — 🔧 "Acknowledge" (`/documents`, EFFECTIVE version ની Card પર button, login: કોઈ પણ
`document.acknowledge` permission ધરાવતો user, દા.ત. `operator1`) — 2026-10-10 UI FIXED:**

| Field (UI label) | ભરવાની Value |
|---|---|
| Statement | `I have read and understood SOP-ASEPTIC-GOWN-004 v2.0 (gowning procedure) and will follow it exactly as written.` (optional) |

→ `200 OK`, `signature_id: null` (**આ Part 11 signature નથી** — unsigned read-and-understood log, AG-07
પ્રમાણે login/MFA signature ન ગણાય). Card ના "Acknowledgments" section માં new row તરત દેખાય (`user_id`,
`statement`, `acknowledged_at`).

> ✅ **2026-10-10 live-verified (UI, Playwright):** "Acknowledge" button → modal → submit → panel
> `ACKNOWLEDGMENTS (1)` સુધી update થયું, real row (`admin`, statement, timestamp) દેખાયો. એ જ user ફરી
> acknowledge કરે (same version) → **idempotent**, panel હજુ `(1)` જ બતાવે, બીજી row નથી બનતી, પહેલાની
> `acknowledged_at` જ રહે છે.

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| QMS-DOC-00 | ઉપરનું સ્ટેપ ૧-૫ exact values સાથે run કરો | `SOP-ASEPTIC-GOWN-004 v2.0` `EFFECTIVE`, version 4, ૧ acknowledgment row | Documents, Vault |
| QMS-DOC-01 | Document draft → submit → release (sign) | State `RELEASED`, Vault snapshot | Documents, Vault |
| QMS-DOC-02 | Change control change_control_id cite કરીને document release | Real FK link — traceable | Documents, Change Control |
| QMS-DOC-03 | Training requirement content_document_version_id cite કરે | Real FK, training content linked | Documents, Training |
| QMS-DOC-04 🔧 | EFFECTIVE version પર `POST .../acknowledgments` call કરો | Real unsigned log entry, `signature_id: null`, `GET .../acknowledgments` પર દેખાય | Documents |
| QMS-DOC-05 🔧 | REVIEW/non-EFFECTIVE version પર acknowledge કરવાનો પ્રયત્ન | `409 DOCUMENT_VERSION_OBSOLETE` | Documents |
| QMS-DOC-06 🔧 | એક user એ જ version ને બે વાર acknowledge કરે | Idempotent — ૨ row નહીં, error નહીં, પહેલું timestamp preserve | Documents |

---

## ૨૩.૯ Training

**શું છે અને શા માટે જરૂરી:** Role/document/qualification/change/CAPA સાથે જોડાયેલ training assignment
track — untrained વ્યક્તિ regulated કામ ના કરે એની ખાતરી.

**કેવી રીતે કામ કરે:** `ASSIGNED → ASSESSMENT_PENDING → {COMPLETED|FAILED}` (FAILED terminal — retrain
નવું linked assignment બનાવે, જૂનું reopen નથી થતું).

| Step | Permission | Signed? |
|---|---|---|
| Assignment **Create** | `training.assignment.create` | **હા — unique!** (`create_qms_signature_challenge_for_new_record()` — code-level special case કારણ કે row sign વખતે હજુ existe નથી) |
| Complete, Assess | `.assignment.complete`/`.assess` | હા |

**બીજા modules સાથે જોડાણ:** `content_document_version_id` → real FK **Documents**. ⚠️ **સુધારેલ
finding (2026-10-09, live-verified — અગાઉનું "zero call sites" claim ખોટું હતું):** `iam.qualifications`
(Document ૦૭/IAM) નો **અલગ** qualification store exists, `QUALIFICATION_MISSING`/`QUALIFICATION_EXPIRED`
gate સાથે — અને આ gate ખરેખર **3 જગ્યાએ enforced છે**: `batch_execution/commands.py::
_enforce_step_qualification()` (batch step start/complete, recipe step નું `required_qualification_code`
set હોય ત્યારે), `qc/commands.py`, `material/commands.py` (dispensing). ત્રણેય જગ્યાએ unqualified actor
ને `403` સાથે block કરે છે, qualified થયા પછી આગળ વધવા દે છે. આ Training module **પોતાનું અલગ**
`qms.qualification_record` બનાવે છે, અને `create_qualification()` command એ row ને `iam.qualifications`
માં **write-through mirror** પણ કરે છે — એટલે Training ની "Grant a qualification" UI વાપરીને જ gate ને
satisfy કરી શકાય. **dual-authority પ્રશ્ન હજુ ખુલ્લો છે (SG-086, resolved નથી):** બે અલગ tables
(version/state/scope `qms.qualification_record` માં છે, `iam.qualifications` માં નથી) એક-તરફી mirror
થી જોડાયેલ છે, single source of truth નથી. Recipe Master નું `required_qualification_code` આ module ની
qualification-codes list ને **non-authoritative suggestion** તરીકે જ વાંચે છે.

**ઉદાહરણ:** Aseptic gowning SOP release થયા પછી → Training requirement create (content_document_
version_id link) → `aseptic.operator` assignment create (sign, special "new-record" signature) →
complete+assess (sign) → qualification record.

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-09 ઉમેરેલ)

Login seq.: `supervisor1` (requirement + assignment-create), `operator1` (complete), `qa.releaser`
(assess — trainee થી independent).

> ✅ **2026-10-09 live-verified:** આખો flow (સ્ટેપ ૧-૪) curl દ્વારા live ચલાવીને ચકાસેલ. પરિણામ:
> requirement (`content_document_version_id` = ઉપર §૨૩.૮ માં released `SOP-ASEPTIC-GOWN-004 v2.0`),
> assignment state `ASSIGNED→ASSESSMENT_PENDING→COMPLETED`, score `92`, trainer/assessor signatures
> captured.

**સ્ટેપ ૧ — "New training requirement" (`/training`, login: `supervisor1`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Title | `Aseptic Gowning SOP v2.0 - Read and Understand` |
| Training type | `Read and understand` |
| Source type | `Document` |
| Document code | `SOP-ASEPTIC-GOWN-004` (dropdown — 🔧 2026-10-10 ઉમેરેલ, `Source type = Document` પસંદ કરો ત્યારે જ દેખાય) |
| Document version | `2.0 (EFFECTIVE)` (dropdown — document code પસંદ કર્યા પછી જ populate થાય) |
| Requires assessment | ચેક |
| Pass score | `80` |

> ✅ **2026-10-10 live-verified (UI, Playwright):** Document code select કરતાં Document version
> dropdown real versions (`2.0 (EFFECTIVE)`) સાથે populate થયું, submit કર્યા પછી DB માં real
> `content_document_version_id` FK set થયેલ confirm કર્યું (2-step picker — Document 30's own 7-op API
> list માં "all versions" list endpoint નથી, ફક્ત per-code, એટલે code પહેલાં, versions પછી).

"Create requirement" ક્લિક → matrix માં requirement listed.

**સ્ટેપ ૨ — "Assign training" (same login, signed "create" — special new-record flow, password `ChangeMe123!`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Requirement | `Aseptic Gowning SOP v2.0 - Read and Understand` (dropdown) |
| Person | `aseptic.operator` |
| Due date | +૧૪ દિવસ |

→ assignment state `ASSIGNED`.

**સ્ટેપ ૩ — "Complete training" (login: `operator1`, password `ChangeMe123!`):** → assignment state
`ASSESSMENT_PENDING`.

**સ્ટેપ ૪ — "Assess training" (login: `qa.releaser` — trainee `aseptic.operator` થી independent, password `ChangeMe123!`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Outcome | `Passed` |
| Score | `92` |

→ assignment state `COMPLETED`, `score=92.0`.

---

### વધારાનું live-fire ચકાસણી — Qualification gate (batch execution) ખરેખર enforce થાય છે કે નહીં

> ✅ **2026-10-09 live-verified:** નવું product `QUALGATE-DEMO v1` + recipe `RCP-QUALGATE-DEMO v1`
> (step `STEP-A`, `required_qualification_code="ASEPTIC_GOWNING_CERT"`) બંને release કર્યા, batch
> `BAT-QUALGATE-DEMO-1` issue+start કર્યો. `admin` (જેની પાસે આ qualification code ની કોઈ
> `iam.qualifications` row નહોતી) એ `STEP-A` start કરવાનો પ્રયત્ન કર્યો → **`403
> QUALIFICATION_MISSING`**. પછી Training ની "Grant a qualification" UI વડે `admin` ને
> `ASEPTIC_GOWNING_CERT` ગ્રાન્ટ કર્યું (command પોતે `iam.qualifications` માં write-through પણ કરે
> છે). એ જ step ફરી start કર્યો → **`200 OK`**, step started. આ confirm કરે છે: gate code માં real,
> enforced છે — માત્ર documented/skipped નથી.

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| QMS-TRN-00 | ઉપરનું સ્ટેપ ૧-૪ exact values સાથે run કરો | Assignment `COMPLETED`, score 92 | Training, Documents |
| QMS-TRN-01 | Requirement create (document link) → assignment create (sign) → complete (sign) | State `COMPLETED` | Training, Documents |
| QMS-TRN-02 | Assessment fail | State `FAILED` — terminal, retrain = નવું assignment | Training |
| QMS-TRN-03 | Untrained user ને recipe step `required_qualification_code` ધરાવતું batch step start/complete કરવા દેવું | Gate **enforced છે** — `403 QUALIFICATION_MISSING`/`QUALIFICATION_EXPIRED` (3 call sites: batch execution, QC, material dispensing) — 2026-10-09 live-verified; Training ની "Grant a qualification" UI વડે qualification ગ્રાન્ટ કર્યા પછી એ જ step start સફળ થાય (dual-store SG-086 હજુ ખુલ્લું) | Training, IAM, Batch Execution, Recipe Master, QC, Materials |
| QMS-TRN-04 | Assignment create signature — record હજુ DB માં ના હોય એ સમયે | Special "new-record" challenge flow કામ કરે | Training |

---

### "Grant waiver" અને "Grant qualification" — શું છે અને કેવી રીતે વાપરવું (2026-10-12 ઉમેરેલ)

**"Grant qualification" (qualification_record) શું છે:** કોઈ વ્યક્તિ ખરેખર કોઈ ચોક્કસ કામ (દા.ત.
aseptic gowning, dispensing) કરવા માટે qualified/certified છે — એ record. Batch execution/QC/Material
dispensing ના ત્રણેય જગ્યાએ `required_qualification_code` check real-enforced છે (ઉપર QMS-TRN-03 જુઓ)
— qualification ના હોય તો `403 QUALIFICATION_MISSING`/`QUALIFICATION_EXPIRED` સાથે block થાય છે.
`create_qualification()` command બે જગ્યાએ એક સાથે write કરે છે: પોતાનું `qms.qualification_record`
(history/scope/evaluator માટે) + `iam.qualifications` (જે gate ખરેખર વાંચે છે) — એટલે "Grant
qualification" UI એ **આ gate ને satisfy કરવાનો એકમાત્ર રસ્તો છે**.

| Field (UI label) | ભરવાની Value |
|---|---|
| Person qualified | `aseptic.operator` (picker) |
| Qualification code | `ASEPTIC_GOWNING_CERT` (free-type, પહેલેથી વપરાયેલ codes suggest થાય) |
| Evaluator | `qa.releaser` (optional, picker) |
| Effective from | આજની તારીખ |
| Effective to | ખાલી રાખો (= expiry નથી) |

→ `qms.qualification_record` + `iam.qualifications` બંનેમાં row બને, state `QUALIFIED`.
**Renewal:** ફરી "Grant qualification" run કરવાથી જૂનો record edit નથી થતો — નવો record બને,
`renewed_from_qualification_id` વડે જૂના ને point કરે (document version ના supersede pattern જેવું જ).

**"Grant waiver" (training_waiver) શું છે:** કોઈ specific વ્યક્તિ ને કોઈ specific training
requirement માંથી **documented રીતે મુક્તિ** આપવી — દા.ત. પહેલેથી equivalent training બીજે ક્યાંક
લઈ લીધેલ હોય. ⚠️ આ waiver કોઈ signature column નથી ધરાવતું — approver ફક્ત plain data તરીકે record
થાય છે, Part 11 electronic signature નહીં (જે acknowledgment pattern જેવું જ, §૨૩.૮ માં જોયું એવું).

| Field (UI label) | ભરવાની Value |
|---|---|
| Requirement | `Aseptic Gowning SOP v2.0 - Read and Understand` (dropdown — §૨૩.૯ સ્ટેપ ૧ માં બનાવેલ) |
| Person waived | `operator2` (picker) |
| Approved by | `supervisor1` (picker) |
| Reason | `Equivalent gowning training completed at previous employer (certificate on file, HR ref #૪૪૨).` |
| Expires at | ખાલી અથવા ભવિષ્યની તારીખ |
| Scope | ખાલી (optional — key-value વડે narrow કરી શકાય) |

→ `training_waiver` row બને. **મહત્વનું:** waiver એ `required_qualification_code` ના batch/QC/
dispensing gate ને touch નથી કરતું — એ ફક્ત Training matrix પર "આ વ્યક્તિ માટે આ requirement
waived છે" તરીકે દેખાય, assignment ક્યારેય `ASSIGNED` state માં create જ ન થવું જોઈએ એ વાત UI level
પર જ છે (backend ત્રણ qualification-gate call site ને waiver ની કોઈ ખબર નથી).

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| QMS-TRN-05 | "Grant qualification" ઉપરની values સાથે run કરો | `qms.qualification_record` + `iam.qualifications` બંનેમાં row, state `QUALIFIED` | Training, IAM |
| QMS-TRN-06 | QMS-TRN-05 પછી ફરી "Grant qualification" run કરો (renewal) | નવો record, `renewed_from_qualification_id` જૂનાને point કરે, જૂનો edit નથી થયો | Training |
| QMS-TRN-07 | "Grant waiver" ઉપરની values સાથે run કરો | `training_waiver` row બને, signature column `null` (unsigned, plain-data approver) | Training |

---

## ૨૩.૧૦ Quality Metrics

**શું છે અને શા માટે જરૂરી:** Versioned metric definition + periodic snapshot + CAPA/SCAR/Field-Action
effectiveness-check framework — "action ખરેખર કામ કર્યું" સાબિત કરવા.

**કેવી રીતે કામ કરે:** Metric: `DRAFT → RELEASED → SUPERSEDED`. Snapshot: `COMPLETE → FROZEN` (દરેક
`calculate()` call નવી row — reproducibility ગેરંટી). Effectiveness: `OBSERVATION → {PASS|FAIL|
INCONCLUSIVE}`.

| Step | Permission | Signed? |
|---|---|---|
| Metric Release | `quality_metric.definition.release` | હા |
| Management Review freeze | `quality_metric.management_review` | હા — package-wide signature |

**બીજા modules સાથે જોડાણ:** `effectiveness_check.source_module` generic hook CAPA/SCAR/Field-Action
effectiveness check માટે **બનાવેલ** છે — પણ ⚠️ **કોઈ પણ module પોતે `create_effectiveness_check()` call
નથી કરતું** — standalone API છે, caller એ manually invoke કરવું પડે.

🔧 **SG-107 PARTIALLY RESOLVED (2026-10-09, project-owner-directed — "Just 2-3 straightforward ones"):**
9 metric family માંથી **3** (deviation/NCR/OOS) હવે real internal `COUNT(*)` aggregation ધરાવે છે —
`calculate()` ને `result` field **આપવી જરૂરી નથી** જો `source_model_id` = `deviation_record`/
`nonconformance_record`/`oos_record` હોય, તો period ની અંદર real row count query થાય
(`{"opened_count": N, "auto_computed": true}`). **આ true "rate" નથી** — ફક્ત count, કોઈ denominator
query નથી (batch count સામે "rate" કરવાનો cross-module contract હજુ નક્કી નથી, guess કરવાનું risk
ટાળ્યું — SG-107 ની પોતાની `risk_if_guessed` નોંધ પ્રમાણે). બાકીની ૬ family (CAPA/complaint/supplier/
audit/training/batch-quality) + rate/denominator half + drilldown (MET-FR-015) + threshold rule-engine
(MET-FR-017) હજુ open. `result` manually supply કરવું હજુ પણ કામ કરે (backward compatible).

**ઉદાહરણ:** Deviation rate metric definition release → quarterly snapshot calculate (result caller
supply કરે) → management review package freeze (sign). CAPA #૨૨ ની effectiveness check manually
create (source_module="CAPA").

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-09 ઉમેરેલ)

Login: `admin` (આખો flow — create, release-sign, calculate, management-review-sign, effectiveness-check
બધું આ જ login થી; independence rule ફક્ત actor ≠ definition ના `owner_subject_id` ચેક કરે છે).

> ✅ **2026-10-09 live-verified:** આખો flow (સ્ટેપ ૧-૫) curl દ્વારા live ચલાવીને ચકાસેલ. પરિણામ: metric
> `QM-DEV-RATE` `DRAFT`(v1) `→RELEASED`(v2, signed) → snapshot Q3-2026 period `COMPLETE` (result
> `{numerator:5, denominator:60, value:0.0833}`, `threshold_exceeded=true`) `→FROZEN` (review package
> signed) → effectiveness check (`source_module="capa"`, existing `CAPA-2026-0001`) state `OBSERVATION`.

**સ્ટેપ ૧ — "Define metric" (`/quality-metrics`, button "Define metric"):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Metric code | `QM-DEV-RATE` |
| Source model | `deviation_record` |
| Frequency | `Quarterly` |
| Numerator definition | `Deviations closed in the period (deviation_record.state=CLOSED)` |
| Denominator definition | `Batches reaching production_complete in the period` |

> 🔧 **2026-10-09 ફિક્સ:** આ modal પહેલા `owner_subject_id` માટે કોઈ field નહોતું બતાવતું — logged-in
> user જ હંમેશા owner બનતો, અને independent-signer rule બરાબર એ જ owner ને release સહી કરતા રોકતી (UI
> થી independent release impossible). હવે "Owner" picker field ઉમેર્યું — creator બીજા કોઈ real
> user ને owner set કરી શકે. Live-verified: `admin` create કરે (owner=`qa.reviewer`), `admin` જ પછી
> release-sign કરે — સફળ, SoD intact.

**સ્ટેપ ૨ — "Release metric" (`/quality-metrics`, button "Release metric", sign):**

> 🔧 **2026-10-09 ફિક્સ:** પહેલા Release માટે કોઈ UI button જ નહોતું — ફક્ત curl/API થી શક્ય હતું (નીચે
> છોડેલ raw calls, હજુ પણ equivalent). Fix: `GET /quality-metrics/v1/definitions` નવું list endpoint
> (DRAFT સહિત બધા metric બતાવે, `/dashboard` થી અલગ — એ ફક્ત RELEASED બતાવે છે, by design) + "Release
> metric" button + signed modal ઉમેર્યું.

| Field (UI label) | ભરવાની Value |
|---|---|
| Metric | `QM-DEV-RATE` (dropdown — DRAFT metric) |
| Effective from | આજની તારીખ |

Raw API equivalent (હજુ પણ કામ કરે છે): `POST /quality-metrics/v1/definitions/{id}/signature-challenges
{"action":"release"}` → challenge_id → `POST /quality-metrics/v1/definitions/{id}/release`
(challenge_id + password) → `version 1→2`, state `DRAFT→RELEASED`.

**સ્ટેપ ૩ — "Calculate snapshot" (same page):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Metric | `QM-DEV-RATE` (dropdown — **સ્ટેપ ૨ પૂરું ના થાય ત્યાં સુધી ખાલી રહેશે**, dropdown ફક્ત `RELEASED` metric બતાવે છે) |
| Period start / end | `2026-07-01` / `2026-09-30` |
| Numerator / Denominator | `5` / `60` |
| Threshold exceeded for this period | ✅ ચેક |

→ "Recorded value: 0.0833" auto-compute → snapshot `COMPLETE`.

**સ્ટેપ ૪ — "Freeze & sign package" (Management review package card):**

Snapshot checkbox ચેક → "Freeze & sign package (1)" → password → snapshot `COMPLETE→FROZEN`.

**સ્ટેપ ૫ — "Create effectiveness check" (`/quality-metrics`, "Effectiveness checks" card):**

> 🔧 **2026-10-09 ફિક્સ:** પહેલા Effectiveness check create/list/evaluate માટે કોઈ UI ક્યાંય નહોતું —
> સંપૂર્ણ API-only. Fix: `GET /effectiveness/v1/checks` નવું list endpoint + "Effectiveness checks" card
> (list + "Create effectiveness check" modal + per-row "Evaluate" modal) ઉમેર્યું.

| Field (UI label) | ભરવાની Value |
|---|---|
| Source module | `CAPA` |
| Source record ID | live `CAPA-2026-0001`નો id |
| Criterion | `Blend-time deviation recurrence drops to zero for two consecutive quarters after CAPA-2026-0001's corrective action is implemented.` |
| Observation period start / end | `2026-10-09` / `2027-04-09` |
| Related metric | `QM-DEV-RATE` (optional) |

→ state `OBSERVATION`. પછી "Evaluate" button (card ની row પર) → Result `Pass`, Evidence ભરીને → state
`PASS` (result uppercased), signature નથી (આ action unsigned જ છે, design).

---

#### 🔧 Auto-compute ઉદાહરણ (2026-10-09 ઉમેરેલ) — `result` વગર જ real count

🔧 **UI gap FIXED (2026-10-10):** "Calculate snapshot" modal માં Numerator field પહેલાં **ફરજિયાત**
(`required`) હતું — હવે auto-compute-eligible metric (source model = deviation/NCR/OOS) select કરતાં
Numerator optional બને છે, hint text દેખાય છે, અને ખાલી રાખવાથી UI થી જ auto-compute trigger થાય છે
(curl જરૂરી નથી). Login: `admin`.

**સ્ટેપ ૧ — નવું metric define કરો (`/quality-metrics`, button "Define metric"):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Metric code | `QM-NCR-COUNT` |
| Source model | `nonconformance_record` |
| Frequency | `Monthly` |
| Numerator definition | `Count of NCRs opened in the period (auto-computed internally -- see note below)` |
| Denominator definition | ખાલી રાખો (blank = plain count, rate નહીં) |
| Owner | `qa.reviewer` (પોતાના સિવાય, independent release માટે) |

**સ્ટેપ ૨ — "Release metric" button → sign (password `ChangeMe123!`).** → state `RELEASED`.

**સ્ટેપ ૩ — 🔧 "Calculate snapshot" (`/quality-metrics`, same button, UI દ્વારા જ — 2026-10-10 UI FIXED):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Metric | `QM-NCR-COUNT` (dropdown) |
| Period start / end | `2020-01-01` / `2030-12-31` |
| Numerator | **ખાલી રાખો** — select કરતાં જ hint દેખાય: "Leave blank to auto-compute a real count for this source (deviation/NCR/OOS)." |
| Denominator | ખાલી જ રહે (Numerator ખાલી હોય ત્યારે field disabled થાય) |

Numerator ખાલી રાખવાથી modal માં જ confirm-text દેખાય: "Numerator left blank — this metric's source
(`nonconformance_record`) will be auto-counted internally for the period instead." → submit કરતાં
`GET /quality-metrics/v1/dashboard?site_id=<site_id>` પર: `"latest_result": {"opened_count": N,
"source_model_id": "nonconformance_record", "auto_computed": true, ...}`

> ✅ **2026-10-10 live-verified (UI, Playwright):** "Calculate snapshot" button → modal → NCR-source
> metric select → Numerator ખાલી રાખ્યું (hint/auto-compute text confirm થયું) → submit → dashboard પર
> real નવો snapshot (`opened_count: 6`, `auto_computed: true`) દેખાયો — real live NCR count, guessed
> નંબર નથી. બીજા source_model_id (દા.ત. `QM-COMPLAINT-RATE`) select કરતાં Numerator હજુ **ફરજિયાત**
> જ રહે છે — ફક્ત deviation/NCR/OOS માટે જ optional બને છે.

**જાણીતી ખામી (2026-10-09 ફિક્સ થયેલ — બધા ત્રણેય):**
1. ~~Release માટે કોઈ UI control નથી.~~ **ફિક્સ:** `GET /quality-metrics/v1/definitions` નવું list
   endpoint ઉમેર્યું (`/dashboard` ફક્ત `RELEASED` બતાવે, by design MET-FR-016 — DRAFT ક્યારેય ત્યાં ના
   હોય) + `/quality-metrics` page પર "Release metric" button + `ReleaseMetricModal`
   (SignatureCeremony). **સાથે એક real GET-shape-mismatch bug પણ મળ્યો+ફિક્સ થયો:** `/dashboard`
   endpoint ક્યારેય `definition_id`/`state`/`frequency` પાછું નહોતું આપતું, ન nested `latest_snapshot`
   — frontend એ fields વર્ષોથી વાંચવાની કોશિશ કરતું હતું, એટલે "Calculate snapshot" dropdown ક્યારેય
   real `definition_id` જ નહોતું મેળવતું (existing `latest_result`/`threshold_exceeded` ફ્લેટ fields
   additive રીતે રાખેલ, existing test ન તોડે).
2. ~~Owner હંમેશા creator.~~ **ફિક્સ:** "Define metric" modal માં "Owner" picker field ઉમેર્યું — હવે
   creator પોતાના સિવાય કોઈ બીજા user ને owner બનાવી શકે, જેથી independent-release UI થી જ શક્ય બને
   (live-verified: admin creates, owner=qa.reviewer, admin release-signs — સફળ).
3. ~~Effectiveness check માટે કોઈ UI નથી.~~ **ફિક્સ:** `GET /effectiveness/v1/checks` નવું list endpoint
   + `/quality-metrics` page પર "Effectiveness checks" card (list + "Create effectiveness check" modal
   + per-row "Evaluate" modal) ઉમેર્યું — CAPA/SCAR/Field Action ના પોતાના effectiveness UI થી આ અલગ,
   generic hook માટેનું UI છે (હજુ પણ manual-invoke — કોઈ module auto-call નથી કરતું, એ ભાગ documented
   gap તરીકે ખુલ્લો જ છે).

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| QMS-MET-00 | ઉપરનું સ્ટેપ ૧-૫ exact values સાથે run કરો | Metric `RELEASED`, snapshot `FROZEN`, effectiveness check `OBSERVATION` | Quality Metrics, CAPA |
| QMS-MET-01 | Metric definition release (sign) → snapshot calculate | Snapshot `COMPLETE` | Quality Metrics |
| QMS-MET-02 | Management review package freeze (sign) | Snapshots `FROZEN`, review package immutable | Quality Metrics |
| QMS-MET-03 | CAPA close પછી automatic effectiveness check expect કરવું | Auto-create **નથી** — manual API call જોઈએ (SG-107) | Quality Metrics, CAPA |
| QMS-MET-04 🔧 | `source_model_id="deviation_record"`/`"nonconformance_record"`/`"oos_record"` metric પર `result` વગર `calculate()` call કરો | Real internal `COUNT(*)` query ચાલે, `{"opened_count": N, "auto_computed": true}` (SG-107 count-half RESOLVED 2026-10-09) — બાકી ૬ family + rate/denominator હજુ caller-supplied (SG-107 રહે) | Quality Metrics |
| QMS-MET-05 | "Define metric" modal માં Owner picker થી creator સિવાય બીજો user set કરો, પછી creator પોતે જ release-sign કરે | Success — SoD intact, independent-release હવે UI થી શક્ય (2026-10-09 ફિક્સ) | Quality Metrics |
| QMS-MET-06 | "Release metric" button → DRAFT metric પસંદ કરો → sign | State `DRAFT→RELEASED`, signed (2026-10-09 UI ઉમેરેલ) | Quality Metrics |
| QMS-MET-07 | "Effectiveness checks" card → "Create effectiveness check" → પછી row પર "Evaluate" | Check `OBSERVATION→PASS/FAIL/INCONCLUSIVE` (2026-10-09 UI ઉમેરેલ) | Quality Metrics, CAPA |

---

## ૨૩.૧૧ Deviation/CAPA — Cross-Connection Summary (doc #૧૦/#૧૧ નો સંદર્ભ)

- **CAPA `source_type`** ખરેખર ૧૧ પ્રકાર validate કરે: `deviation, oos, oot, ncr, complaint, audit,
  supplier, risk, trend, security, validation` (`capa_models.py::CAPA_SOURCE_TYPES`, 2026-10-09
  code-ચકાસેલ — doc માં અગાઉ "ફક્ત ૮" ખોટું લખેલું) — આમાંથી ૮ પાસે `source_id` existence-check કરતું FK
  model છે (`deviation, oos, oot, ncr, complaint, audit, supplier, risk`); બાકીના ૩ (`trend, security,
  validation`) માટે કોઈ single owning table ના હોવાથી `source_id` unvalidated રહે છે
  (`capa_commands.py::_CAPA_SOURCE_MODELS`) — એ એક અલગ, સાંકડો મુદ્દો છે, "validate થાય છે કે નહીં"
  થી જુદો. **Change Control અને Field Action** આ ૧૧ માંથી એકેયમાં નથી — આ બે જ ખરેખર CAPA source
  બની ના શકે (SG-063 હજુ ખુલ્લો).
- **Release blocking:** `release/service.py::evaluate_eligibility()` ખરેખર **૧૦ signal source** wire
  કરે છે (2026-10-09 code-ચકાસેલ — doc માં અગાઉ "ફક્ત Deviation/CAPA" ખોટું લખેલું): production-complete
  (batch state), QA review, Vault execution-snapshot integrity, Deviation (`OPEN_DEVIATION`,
  `source_type="batch"`), QC, Materials, EM, Equipment, Yield/Reconciliation, અને CAPA (`OPEN_CAPA`, એ
  જ `source_type="batch"` attribution, ૨-hop: batch→deviation/OOS→CAPA). છતાં **NCR, Complaint, Change
  Control, Field Action, SCAR, Internal Audit, Risk Register — આ ૭ માંથી કોઈને પણ release-blocking
  wiring નથી** — doc #૨૨.૮ માં પણ આ repeat કરેલ છે, મહત્વનો cross-reference.
- **Notification chain** (doc #૧૮ §૬ diagram): Batch → QC OOS/OOT | Reject→NCR | Deviation→CAPA →
  Release. Complaint→Investigation→Reportability→(Response|Field Action). Supplier NCR/OOS→Supplier
  Case→SCAR.

---

## ૨૩.૧૨ સારાંશ — Cross-Module Connection Map

```
NCR ──(source_type)────────────→ CAPA (manual create)
Change Control ──(risk_ref)────→ Risk Register
Change Control ──(change_control_id)→ Documents
Documents ──(content_document_version_id)→ Training
Field Action ──(risk_assessment_ref)→ Risk Register
Field Action ──(trigger_ref)────→ Complaint/Deviation/CAPA (caller-supplied, not auto-linked)
Supplier Case ──(supplier_id/material_id)→ Suppliers, Materials (read-only)
Internal Audit ──(SoD check)────→ (self — auditor ≠ auditee)
Quality Metrics ──(effectiveness_check.source_module)→ CAPA/SCAR/Field Action (manual invoke only)
```

**સૌથી મહત્વના documented gaps (બધા module માં repeat થતો pattern — યાદ રાખવા જેવો):**
1. 🔧 **CAPA auto-creation RESOLVED (2026-10-09)** — NCR/Complaint/Internal Audit/SCAR/Field Action,
   બધા પાંચ module માં `capa_required=true` mark કરવાથી હવે real draft CAPA auto-create થાય છે (જુઓ
   §૨૩.૦ ઉપર). FAR-FR-020/CMP-FR-011,013-016,024/AUDIT-FR-012,015-017 (export/trend/metrics/genealogy)
   હજુ open.
2. **Release હવે ૧૦ signal source block કરે** (production-complete, QA review, Vault integrity,
   Deviation, QC, Materials, EM, Equipment, Yield/Reconciliation, CAPA) — છતાં NCR, Complaint, Change
   Control, Field Action, SCAR, Internal Audit, Risk Register — આ ૭ Quality System module માંથી કોઈ
   release blocker નથી.
3. **Dual qualification store** (Training vs IAM) — SG-086, resolved નથી.
