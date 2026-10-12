# ૨૨. Operations Modules — શું, શા માટે, કેવી રીતે જોડાયેલ (Gujarati Explainer)

> Source: `services/gxp-api/app/modules/equipment/{cleaning,sterilization,em}_*.py`,
> `app/modules/aseptic/`, `app/modules/packaging/`, `app/modules/qa_review/`, `app/modules/release/`,
> `app/modules/yield_reconciliation/`, `app/modules/genealogy*`, `frontend/src/app/{cleaning,sterilization,
> aseptic,em,line-clearance,qa-review,release,yield,equipment}/`.
>
> **આ doc નો હેતુ:** doc #૦૪/૦૫/૦૮/૧૩ already routes/permissions/demo-walkthrough આપે છે. આ doc એ
> **concept-level explainer** છે — "આ module શું કામ કરે, શા માટે manufacturing માં જરૂરી છે, બીજા
> modules સાથે code-level કેમ જોડાયેલ છે" — simple ઉદાહરણ અને test-case tables સાથે. બધી વિગત actual
> code વાંચીને (2026-10-08) ચકાસેલ છે, કંઈ પણ ધારેલું નથી.
>
> **ઉદાહરણ dataset (બધે consistent):** Organization "Demo Manufacturing Co." (role-play "Meridian
> Therapeutics Inc."), Site `SITE1`, Product `MJ-PFS-40MG` ("MeridiJect™ Prefilled Syringe 40mg"),
> Recipe `RCP-MJ-PFS-V1`, Batch `MJ-PFS-B-2601`.

---

## ૨૨.૦ આ બધા modules નો કુદરતી ક્રમ (Process Flow)

Batch બનાવતી વખતે operations modules આ ક્રમમાં ભેગા થાય છે — એટલે આ doc પણ એ જ ક્રમમાં લખેલ છે, client ની
list ના ક્રમમાં નહીં:

```
Equipment/Area તૈયાર → Cleaning → Line Clearance → Sterilization → Environmental Monitoring (EM)
      → Aseptic Operation (ઉપરના બધા ના readiness check કરીને જ start થાય)
      → Packaging
      → QA Review (exception-review ગેટ)
      → Release (final disposition ગેટ — ઉપરના બધા signals ફરી ચેક કરે)
      → Yield & Reconciliation (mass-balance પ્રૂફ)
      → Genealogy (traceability graph — write નહીં, માત્ર lookup)
```

**સૌથી મહત્વનો concept:** Aseptic Operation પોતે કંઈ "ચેક" નથી કરતું — એ Cleaning, EM, Equipment,
Sterilization — ચારેયના live status ને **ભેગું કરીને** (compose કરીને) readiness નક્કી કરે છે. Release
પણ એવું જ કરે છે — QA Review, QC, Material, DDCP, EM, Equipment, CAPA, Yield — બધાના signal ભેગા કરીને
final decision લે છે. આ platform ની design philosophy છે: **દરેક module પોતાનો data રાખે, પણ decision
લેતી વખતે બીજા module ના live data ને query કરે — data copy નથી કરતું.**

---

## ૨૨.૧ Cleaning

**શું છે અને શા માટે જરૂરી:** Equipment/area પર એક batch/product વાપર્યા પછી, બીજો batch/product એ જ
equipment/area પર વાપરવા પહેલાં "ચોખ્ખું" (clean) સાબિત કરવું પડે — નહીં તો cross-contamination (એક
product નું residue બીજા product માં ભળી જવું) થાય, જે patient safety risk છે. એટલે CGMP કાયદો equipment
cleaning ને documented, verified step માંગે છે.

**કેવી રીતે કામ કરે** (state machine `DIRTY → CLEANING → CLEANING_VERIFICATION → CLEAN → READY_FOR_USE`,
fail થાય તો `HOLD`):

| Step | Permission | કોણ | Signed? |
|---|---|---|---|
| **New procedure version** | `cleaning_procedure_version.create` | Admin, QA Reviewer | ના (direct-to-RELEASED, 2026-10-08 ઉમેરેલ) |
| Create (cleaning શરૂ) | `cleaning_execution.create` | Sanitation Operator, Operator, QA Reviewer | ના (2026-10-09 ફિક્સ: doc માં અગાઉ ખોટી રીતે "Supervisor" લખેલું — Supervisor role પાસે આ permission નથી; QA Reviewer પાસે છે પણ doc માં missing હતું, scripts/seed.py સામે ચકાસેલ) |
| Record step | (same) | same | ના |
| **Complete** | `cleaning_execution.complete` | same | **હા** — "Performed" |
| **Verify** | `cleaning_execution.verify` | QA Reviewer, QC Reviewer | **હા** — "Reviewed", **independent verifier ફરજિયાત** (જે વ્યક્તિએ complete કર્યું એ જ verify ના કરી શકે) |

Verify "fail" → equipment/area `HOLD` માં જાય + `requires_deviation=true` (deviation ખોલવી પડે).

**બીજા modules સાથે જોડાણ:**
- Cleaning complete/verify equipment/area નું `cleanliness_status` field update કરે (`_mirror_cleanliness()`) — આ field Equipment module માં "captured" હતું, Cleaning module જ એને "real" બનાવે છે.
- **Line Clearance** ના equipment-checklist-items આ જ `cleanliness_status` ને સીધું વાંચે છે (equipment CLEAN ના હોય તો line clearance "Pass" complete ના થાય).
- **Aseptic Operation** ની readiness check equipment eligibility દ્વારા આડકતરી રીતે cleaning status વાપરે છે.
- **Sterilization** cycle ને cleaning record સાથે લિંક કરી શકાય (`sterilization_cycle_id` FK) — પુરાવા તરીકે, પણ એ cleaning ની પોતાની signature ને replace નથી કરતું.

**ઉદાહરણ:** Filler-01 equipment પર batch `MJ-PFS-B-2601` પૂરું થયા પછી, `sanitation.operator` cleaning
શરૂ કરે → steps log કરે → complete (sign) → `qa.reviewer` independent verify (sign, Pass) → equipment
`CLEAN` → હવે next batch માટે eligible.

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-08 ઉમેરેલ)

UI માં જે-તે field નું exact label સાથે — live system માં સીધું ભરી શકાય એવું realistic pharma data.
Login seq.: પહેલા `qa.reviewer` (procedure author), પછી `sanitation.operator` (performer), પછી ફરી
`qa.reviewer` (independent verifier).

> ✅ **2026-10-08 live-verified:** આ આખો flow (સ્ટેપ ૧-૫, નીચેની બધી જ exact values સાથે) curl દ્વારા
> live `ebmr-new-api` સામે ચલાવીને ચકાસેલ છે — ધારેલું નથી. પરિણામ: `CLN-PROC-FILLER-002 v1` created,
> execution state `DIRTY→CLEANING→CLEANING_VERIFICATION→CLEAN`, `AREA-GRADE-C.cleanliness_status =
> CLEAN`, `clean_until` = start + 2880 મિનિટ (૪૮ કલાક) બરાબર ગણાયેલ.

**સ્ટેપ ૧ — "New cleaning procedure version" (`/cleaning`, login: `qa.reviewer`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Procedure number | `CLN-PROC-FILLER-002` |
| Version no. | `1` |
| Cleaning type | `Deep Clean` |
| Dirty hold limit (minutes) | `180` |
| Clean hold limit (minutes) | `2880` (૪૮ કલાક) |
| Validation reference | `VAL-CLN-FILLER-002-2026` |
| Disassembly required | `Yes` |
| Agents | `agent_1` → `1% Sodium Hypochlorite (NaOCl) solution`, `agent_2` → `70% Isopropyl Alcohol (IPA)`, `agent_3` → `Water for Injection (WFI) - final rinse` |
| Steps | `1` → `Disconnect and disassemble filler nozzle assembly`, `2` → `Pre-rinse product-contact parts with Purified Water`, `3` → `Apply 1% NaOCl solution, contact time 10 minutes`, `4` → `Scrub with validated nylon brush`, `5` → `Rinse with WFI (minimum 3 cycles)`, `6` → `Wipe down with 70% IPA`, `7` → `Visual inspection under UV light`, `8` → `Reassemble and cap open ports` |

"Create procedure" ક્લિક → list card માં `CLN-PROC-FILLER-002 v1` દેખાશે, state `RELEASED`.

**સ્ટેપ ૨ — "Start cleaning execution" (login: `sanitation.operator`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Cleaning procedure version | `CLN-PROC-FILLER-002 v1 - Deep Clean` (dropdown — સ્ટેપ ૧ માં બનાવેલ) |
| Equipment | ખાલી રાખો |
| Area | `AREA-GRADE-C` (live seeded area, equipment create કરવાની જરૂર નથી) |
| Batch context | `product` → `MJ-PFS-40MG`, `batch_number` → `MJ-PFS-B-2601` |

"Start cleaning execution" ક્લિક → execution state `CLEANING`.

**સ્ટેપ ૩ — "Record step" (same login, execution ખોલીને):**

| Field | Value |
|---|---|
| Step code | `SCRUB` |
| Step result | `done` |
| Agents used | `agent` → `1% Sodium Hypochlorite (NaOCl) solution` |
| Disassembly verified | `Yes` |

**સ્ટેપ ૪ — "Complete (sign)" (same login, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Previous batch identity removed | `Yes` |
| Inspection result | `visual_check` → `clean, no residue` |

→ execution state `CLEANING_VERIFICATION`.

**સ્ટેપ ૫ — "Verify (sign)" (login: `qa.reviewer` — સ્ટેપ ૩/૪ ના user થી અલગ, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Result | `Pass` |

→ execution state `CLEAN`, area `cleanliness_status = CLEAN`.

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| OPS-CLN-00 | ઉપરનું સ્ટેપ ૧ ("New cleaning procedure version") QA Reviewer લોગિન સાથે run કરો | `CLN-PROC-FILLER-002 v1` RELEASED state માં listed | Cleaning |
| OPS-CLN-01 | AREA-GRADE-C પર cleaning create → complete (sign) → QA Reviewer verify Pass (sign) | Area `cleanliness_status = CLEAN`, `clean_until` set | Cleaning, Equipment |
| OPS-CLN-02 | એ જ user જેણે complete કર્યું, verify કરવાનો પ્રયત્ન કરે | System block કરે — independent verifier error | Cleaning |
| OPS-CLN-03 | Verify "Fail" result આપે | Area → `HOLD`, `requires_deviation=true` | Cleaning, Deviation |
| OPS-CLN-04 | Equipment `HOLD`/dirty સ્થિતિમાં Line Clearance "equipment" checklist item run કરે | Item auto-fail — Pass complete ના થાય | Cleaning, Line Clearance |
| OPS-CLN-05 | Cleaning verify ચાલુ હોય ત્યારે same area પર બીજું cleaning create કરવાનો પ્રયત્ન | Block — concurrent cleaning ની મંજૂરી નથી | Cleaning |
| OPS-CLN-06 | Operator role થી "New cleaning procedure version" create કરવાનો પ્રયત્ન | `403 ROLE_MISSING` — Admin/QA Reviewer જ કરી શકે | Cleaning |
| OPS-CLN-07 | સમાન `procedure_number` + `version_no` બીજી વાર create કરવાનો પ્રયત્ન | `422 VALIDATION_FAILED` — duplicate | Cleaning |

**જાણીતી ખામી:** ~~Cleaning procedure version author/release UI નથી~~ — **2026-10-08 ફિક્સ થયેલ**: Admin/QA
Reviewer હવે `/cleaning` પર જ "New cleaning procedure version" button થી live create કરી શકે (ઉપર સ્ટેપ ૧
જુઓ), row click → detail popup પણ ઉમેરેલ. બાકી ખુલ્લું: કોઈ background scheduler નથી — `CLEAN_EXPIRED`
status માત્ર query થાય ત્યારે જ ગણાય છે (live auto-expire નથી).

---

## ૨૨.૨ Line Clearance

**શું છે અને શા માટે જરૂરી:** Area-level ચેક — પાછલા batch નું material/label/identity area માંથી
સંપૂર્ણ દૂર થયું છે એની પુષ્ટિ, આગલો batch શરૂ કરતા પહેલાં. Previous/next batch reference optional
(traceability માટે).

**કેવી રીતે કામ કરે** (state machine `NOT_STARTED → IN_PROGRESS → VERIFICATION_PENDING → CLEARED/
NOT_STARTED(fail) → EXPIRED/USED`):

| Checklist item type | ઓટો-ચેક થાય છે? |
|---|---|
| `material` | ના — manual verify |
| `label` | ના — manual verify |
| `equipment` | **હા** — listed equipment asset qualified + calibrated + clean ના હોય તો Complete "Pass" જ fail થઈ જશે (`WRONG_EQUIPMENT_INSTALLED`) |

| Step | Permission | કોણ | Signed? |
|---|---|---|---|
| Start (Create) | `line_clearance.create` | Admin, Operator, Supervisor, Sanitation Operator | ના |
| **Complete** | `line_clearance.complete` | same | **હા** — "Performed" (critical flag હોય તો fail પર reason ફરજિયાત) |

**Demo Login:** `sanitation.operator` / `ChangeMe123!`

**બીજા modules સાથે જોડાણ (code-confirmed):**
- `cleaning_commands.get_area_line_clearance_status()` — **Aseptic Operation** ની readiness composition
  આ function ને સીધું call કરે છે (પોતાનો copy નથી રાખતું).
- **DDCP** readiness check પણ આ જ function વાપરે છે — line clearance ના થાય ત્યાં સુધી DDCP blocked.
- 🔧 **SG-056 PARTIALLY RESOLVED (PKG-FR-009, 2026-10-09, project-owner-directed — "Yes, wire to the
  real check"):** Packaging હવે **real જોડાયેલ છે** — નવું `get_batch_line_clearance_status()` (આ જ
  module માં, `get_area_line_clearance_status()` ની બાજુમાં, પણ `area_id` ની જગ્યાએ
  `LineClearance.next_batch_id` વડે key થાય છે — `PackagingRun`ને નવું `area_id` column ઉમેરવાની જરૂર
  નથી, batch-level match area-level કરતાં વધુ ચોક્કસ છે). `POST /packaging/v1/runs/{id}/line-clearance`
  હવે આ real check સામે fail-closed છે — `CLEARED` (expired નહીં) clearance ના હોય તો
  `409 LINE_CLEARANCE_REQUIRED` (pre-existing error code, પહેલાં ક્યાંય વપરાતો જ નહોતો). Live-verified:
  fresh batch પર clearance વગર → block; real signed clearance complete કર્યા પછી → success.

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-08 ઉમેરેલ)

UI માં જે-તે field નું exact label સાથે — live system માં સીધું ભરી શકાય એવું realistic pharma data.
Login: `sanitation.operator` (પાસવર્ડ `ChangeMe123!`).

**સ્ટેપ ૧ — "Start line clearance" (`/line-clearance`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Equipment area / line | `AREA-GRADE-C` (dropdown) |
| Previous batch | ખાલી રાખો |
| Next batch | ખાલી રાખો |
| Checklist / procedure version | `CLN-PROC-001 v1 - routine` (dropdown — **2026-10-08 ફિક્સ**: પહેલા free-text UUID-જેવું field હતું, હવે `/cleaning/v1/procedure-versions` માંથી real dropdown; column હજુ પણ plain reference code string જ છે, "Not listed? Enter manually" થી કોઈ પણ બીજો code પણ લખી શકાય) |
| Checklist items — item ૧ | Item type: `Material` (Equipment asset field આ item type પર **દેખાતું જ નથી** — 2026-10-08 ફિક્સ: પહેલાં material/label item પર પણ equipment picker દેખાતું હતું, હવે item type = Equipment હોય ત્યારે જ દેખાય છે) |
| Checklist items — item ૨ | Item type: `Label` |
| Critical clearance | `No` |

"Start line clearance" ક્લિક → clearance state `IN_PROGRESS`.

> ⚠️ **Equipment item type વાપરવું હોય તો:** Item type = `Equipment` પસંદ કરો કે તરત "Equipment asset"
> dropdown દેખાશે (conditional). પણ પસંદ કરેલ equipment asset ખરેખર **qualified + calibrated + clean**
> ના હોય તો Complete "Pass" `WRONG_EQUIPMENT_INSTALLED` error સાથે fail થશે — આ live ચકાસેલ real behavior
> છે (demo equipment assets માંથી મોટાભાગના `qualification_status`/calibration હજુ set નથી, એટલે ડેમો
> માટે material/label items જ વાપરવા સરળ રહેશે, અથવા પહેલાં Equipment page પર કોઈ asset ને qualify+
> calibrate+clean કરો).

**સ્ટેપ ૨ — "Complete (sign)" (same login, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Result | `Pass area is clear` |
| Expiry | ખાલી રાખો |
| Reason | ખાલી રાખો (critical ના હોય તો જરૂરી નથી) |

→ clearance state `CLEARED`. Detail popup હવે (2026-10-08 ફિક્સ) raw UUID ને બદલે real નામ બતાવશે:
Area `AREA-GRADE-C`, Checklist `CLN-PROC-001`, Performer/Verifier બંને `sanitation.operator` (SoD નોંધ:
material/label-only clearance માં performer=verifier allowed છે — independent-verifier ફરજિયાત ફક્ત
**Cleaning execution** ના verify step માં છે, doc #૨૨.૧ જુઓ, Line Clearance ની પોતાની complete action
માં નથી).

> ✅ **2026-10-08 live-verified:** આ આખો flow (material+label items, Complete Pass) curl દ્વારા live
> `ebmr-new-api` સામે ચલાવીને ચકાસેલ — clearance ખરેખર `CLEARED` state સુધી પહોંચ્યું, detail માં
> `area_code`/`checklist_version`/`performer_username`/`verifier_username` બધા સાચા દેખાયા. Equipment-item
> eligibility fail (`WRONG_EQUIPMENT_INSTALLED`, reasons `EQUIPMENT_NOT_QUALIFIED`+`CALIBRATION_EXPIRED`)
> પણ એક અલગ, unqualified demo equipment asset સામે live reproduce કરેલ.

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| OPS-LC-00 | AREA-GRADE-C પર material+label items સાથે clearance start → Complete Pass (sign) | State `CLEARED` | Line Clearance |
| OPS-LC-01 | `AREA-GRADE-C` નું line clearance Pass ના થયું હોય, DDCP batch ready-check run કરે | DDCP readiness `blocked` — line clearance missing reason | Line Clearance, DDCP |
| OPS-LC-02 | એ જ area clearance Pass થયા પછી DDCP ready-check ફરી run કરે | Blocker દૂર — DDCP eligible | Line Clearance, DDCP |
| OPS-LC-03 🔧 | Line Clearance Pass ના થયું હોય, Packaging run `complete_line_clearance` call કરે | `409 LINE_CLEARANCE_REQUIRED` — real check (2026-10-09 RESOLVED). Real clearance Pass કર્યા પછી જ success | Line Clearance, Packaging |
| OPS-LC-04 | Checklist item type = Equipment પસંદ કરો | Equipment asset dropdown દેખાય (conditional show) | Line Clearance |
| OPS-LC-05 | Equipment item ઉમેરીને પછી item type ને Material માં બદલો | Equipment asset field અદૃશ્ય + જૂની value clear થાય (submit માં leak ના થાય) | Line Clearance |
| OPS-LC-06 | Unqualified/uncalibrated equipment asset સાથે Equipment item → Complete Pass | `422 WRONG_EQUIPMENT_INSTALLED` — reasons list માં ચોક્કસ કારણ | Line Clearance, Equipment |
| OPS-LC-07 | Checklist/procedure version field માં dropdown માંથી `CLN-PROC-001` પસંદ કરો | Field માં string code `"CLN-PROC-001"` જાય (UUID નહીં — column હજુ plain string) | Line Clearance, Cleaning |

**જાણીતી ખામી:** ~~Packaging real Line Clearance status query નથી કરતું~~ 🔧 **2026-10-09 RESOLVED**
(ઉપર જુઓ). `checklist_version` column હજુ પણ plain string field છે (schema change નથી કરેલ) —
dropdown ફક્ત typo-safety માટે છે, actual queryable link નથી (જો ભવિષ્યમાં genuine FK/traceability
જોઈએ તો એ અલગ, મોટો schema decision છે).

---

## ૨૨.૩ Sterilization (CIP/SIP/Sterile Filtration)

**શું છે અને શા માટે જરૂરી:** Injectable product (જેમ કે MeridiJect PFS) માટે વાપરેલ equipment/filter
ખરેખર sterile (જીવાણુ-મુક્ત) થયું છે એનું validated પુરાવું જોઈએ — નહીં તો contamination patient સુધી
પહોંચી શકે.

### આ module ના ૩ અલગ-અલગ ભાગ — શા માટે દરેક જરૂરી છે

Sterilization એક જ "entity" નથી — ૩ અલગ વસ્તુ ભેગી મળીને કામ કરે છે, દરેકનો હેતુ અલગ:

**૧) Cycle Profile Version — "શું sterilize કરવું, કેવી રીતે" ની master recipe.** આ એક template છે —
process type (steam autoclave/CIP/SIP/sterile filtration વગેરે), critical parameters (temperature,
pressure range), indicator requirements (biological indicator ફરજિયાત છે કે નહીં), sterile-status
validity (sterile ગણાય એ કેટલા કલાક સુધી માન્ય). **શા માટે જરૂરી:** દરેક વખતે નવેસરથી "કેટલા ડિગ્રી પર
sterilize કરવું" ટાઈપ ના કરવું પડે — એક વાર approved profile બનાવો, દરેક real cycle એને સંદર્ભે છે.
Master data છે, direct-to-RELEASED (કોઈ draft/review stage નથી).

**૨) Process Cycle — ખરેખર ચાલેલું, real sterilization run.** એક ચોક્કસ equipment પર, ચોક્કસ load
items (filter/garment/component) સાથે, ચોક્કસ profile સામે ચલાવેલ **વાસ્તવિક ઘટના**. Controller થી
real parameter data (temperature/pressure readings) અને biological/chemical indicator results આ cycle
સાથે જોડાય. **શા માટે જરૂરી:** "આ ચોક્કસ equipment ખરેખર sterile થયું" નો legal proof — profile માત્ર
ઈરાદો બતાવે, cycle એ સાબિતી છે.

**૩) Sterile Filter Use — filter-specific, cycle થી અલગ entity.** Sterile filtration વખતે વપરાતું
ચોક્કસ filter (serial number, lot, manufacturer) — install, pre-use integrity test (filter વાપરતા
પહેલાં ચકાસવું કે કાણાં/leak નથી), post-use integrity test (વાપર્યા પછી ફરી ચકાસવું), complete. **શા
માટે Cycle થી અલગ entity:** એક filter ઘણી વખત ફરીથી વાપરી શકાય (reuse), અને filter નું પોતાનું
serial/lot traceability (manufacturer defect વખતે recall માટે) cycle ના traceability થી અલગ બાબત છે —
`sterilization_cycle_id` દ્વારા બંને **optionally** જોડાયેલ રહી શકે (કયા cycle એ આ filter sterilize
કર્યું, પુરાવા તરીકે), પણ filter નો પોતાનો lifecycle સ્વતંત્ર છે.

**કેવી રીતે કામ કરે (Process Cycle ની state machine):** `DRAFT → CYCLE_STARTED → CYCLE_RUNNING →
CYCLE_COMPLETE → REVIEW_PENDING → ACCEPTED/FAILED`. **મહત્વનો design point:** cycle માં pass/fail
field જ નથી — operator manually "pass" mark **ના કરી શકે**. ફક્ત independent reviewer જ accept/reject
નક્કી કરે.

| Step | Permission | કોણ | Signed? | Independent? |
|---|---|---|---|---|
| Create profile | `process_cycle_profile_version.create` | Admin, QA Reviewer | ના (direct-to-RELEASED) | — |
| Create + Start cycle | `process_cycle.create`/`.start` | Sterilization Operator | Start: **હા** ("Performed") | ના |
| **Review cycle** | `process_cycle.review` | QA Reviewer, QC Reviewer | **હા** ("Reviewed") | **હા** |
| Install filter | `sterile_filter_use.create` | Sterilization Operator | ના | — |
| **Complete filter use** | `sterile_filter_use.complete` | Sterilization Operator | **હા** | ના |

**બીજા modules સાથે જોડાણ:**
- `sterilization_commands.get_item_status(item_id)` — **Aseptic Operation** readiness composition આ
  function call કરીને "sterile input eligible છે?" ચેક કરે, start કરતા પહેલાં.
- `CleaningExecution.sterilization_cycle_id` — cleaning record ને CIP/SIP cycle evidence સાથે link કરે.
- જો કોઈ load item ની `item_reference` પહેલાંના FAILED cycle સાથે મેળ ખાય, તો નવું cycle
  `reprocessing_authorization_ref` વગર start જ ના થાય (fail-closed).

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-08 ઉમેરેલ)

**સ્ટેપ ૧ — "New sterilization cycle profile" (`/sterilization`, login: `qa.reviewer`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Profile number | `STR-PROC-FILLER-002` |
| Version no. | `1` |
| Process type | `steam_autoclave` |
| Validation reference | `PQ-STR-FILLER-002` |
| Sterile status validity (hours) | `720` (૩૦ દિવસ) |
| Critical parameters | `temperature_c` → `{"min": 121, "target": 121.5}` |
| Indicator requirements | `biological_indicator` → `required` |

**સ્ટેપ ૨ — "Create process cycle" (login: `sterilization.operator`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Process type | `steam_autoclave` |
| Equipment | કોઈ પણ seeded equipment (dropdown — દા.ત. `EQP-000001`) |
| Cycle profile version | `STR-PROC-FILLER-002 v1 - steam_autoclave` (dropdown — સ્ટેપ ૧ માં બનાવેલ) |
| Batch | ખાલી રાખો |
| Load items — item ૧ | Item type: `filter`, Item reference: `FILTER-DEMO-001` (manual entry — materialLotSelect dropdown માં ના હોય તો "enter manually"), Position: `shelf-1` |

"Create process cycle" ક્લિક → cycle state `DRAFT`.

**સ્ટેપ ૩ — "Start cycle (sign)" (same login, password `ChangeMe123!`):** → cycle state `CYCLE_STARTED`.

**સ્ટેપ ૪ — "Record cycle data" (same login):**

| Field | Value |
|---|---|
| Controller cycle ID | `AUTOCLAVE-LOG-20261008-001` |
| Parameter data | `temperature_c` → `121.6`, `pressure_bar` → `1.1`, `hold_time_min` → `20` |
| Alarm data | ખાલી |
| Indicator results | `BI_1` → `negative`, `CI_1` → `pass` |
| Critical alarm | `No` |
| Final batch of data | `Yes` |

→ cycle state `REVIEW_PENDING` (final=true હોવાથી સીધું review માટે તૈયાર).

**સ્ટેપ ૫ — "Review (sign)" (login: `qa.reviewer` — operator થી અલગ user, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Decision | `Accept` |

→ cycle state `ACCEPTED`.

**સ્ટેપ ૬ — "Install / integrity test" → "Install a filter" (login: `sterilization.operator`):**

| Field | Value |
|---|---|
| Filter serial | `FILTER-DEMO-001` |
| Filter lot | `FLOT-2601` |
| Filter type | `0.22 micron PES` |
| Manufacturer | `Millipore` |
| Batch | ખાલી |
| Sterilization cycle | `steam_autoclave cycle - EQP-000001 (ACCEPTED)` (dropdown — **2026-10-08 ફિક્સ**: પહેલા free-text UUID field હતું, હવે real cycle list માંથી dropdown; સ્ટેપ ૨-૫ માં બનાવેલ cycle પસંદ કરો) |
| Housing location | `Filler-01 inlet` |
| Direction | `forward` |

**સ્ટેપ ૭ — "Record an integrity test" (same login) — ૨ વાર run કરો:**

| Run | Filter use | Phase | Result | Test reference |
|---|---|---|---|---|
| ૧ | `FILTER-DEMO-001 (0.22 micron PES) - ...` (dropdown — **2026-10-08 ફિક્સ**: હવે free-text `use_id` ની જગ્યાએ real filter-use list dropdown) | `Pre-use` | `Pass` | `method` → `bubble_point`, `instrument_id` → `BPT-04`, `bubble_point_value` → `3.2 bar` |
| ૨ | same | `Post-use` | `Pass` | `bubble_point_value` → `3.1 bar` |

**સ્ટેપ ૮ — "Complete a filter use" (sign, same login, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Filter use | same dropdown |
| Process parameters | `flow_rate_lpm` → `2.5` |
| Reason | ખાલી |

→ filter use state `ACCEPTED`, `sterilization_cycle_id` સાચું linked (detail માં cycle ID દેખાશે).

> ✅ **2026-10-08 live-verified:** આખો flow (પ્રોફાઇલ → cycle create→start→data→review-accept → filter
> install→pre-test→post-test→complete) curl દ્વારા live `ebmr-new-api` સામે ચલાવીને ચકાસેલ — cycle
> ખરેખર `ACCEPTED` પહોંચ્યું, filter use `ACCEPTED` પહોંચ્યું અને `sterilization_cycle_id` સાચા cycle
> સાથે linked થયું (એ જ cycle જે real dropdown થી પસંદ કરેલ, free-text UUID નહીં).

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| OPS-STR-00 | ઉપરનું સ્ટેપ ૧-૫ પૂરું ચલાવો | Cycle `ACCEPTED` | Sterilization |
| OPS-STR-01 | Cycle start → data record → QA Reviewer review "Accept" | Cycle `ACCEPTED`; item eligible | Sterilization |
| OPS-STR-02 | Cycle review "Reject" કરે | Cycle `FAILED`; item ineligible | Sterilization, Deviation |
| OPS-STR-03 | FAILED cycle ના item_reference સાથે નવું cycle authorization-ref વગર create | Block — reprocessing authorization ફરજિયાત | Sterilization |
| OPS-STR-04 | Aseptic Operation start — sterile filter item FAILED status ધરાવે | Start block — `SterileComponentIneligibleError` | Sterilization, Aseptic |
| OPS-STR-05 | "Install a filter" ફોર્મ માં Sterilization cycle dropdown ખોલો | Real ACCEPTED/running cycles ની list દેખાય, UUID પેસ્ટ કરવાની જરૂર નથી | Sterilization |
| OPS-STR-06 | "Record an integrity test" / "Complete a filter use" ફોર્મ માં Filter use dropdown ખોલો | Real filter-use list (serial + type + state સાથે) દેખાય | Sterilization |

---

## ૨૨.૪ Environmental Monitoring (EM)

**શું છે અને શા માટે જરૂરી:** Cleanroom ની હવા/surface particle count, pressure વગેરે classified limit
ની અંદર જ રહે એનું સતત પુરાવું — sterile operation એ area માં ખરેખર યોગ્ય છે કે નહીં નક્કી કરવા.

### આ module ના ૪ અલગ-અલગ ભાગ — શા માટે દરેક જરૂરી છે

**૧) EM Program Version — "ક્યાં, શું, કેટલી વાર monitor કરવું" ની master plan.** Program number,
monitoring types (viable_air/surface_contact વગેરે), alert limits, action limits — આ બધું એક program
version માં define થાય. **શા માટે જરૂરી:** દરેક area માટે અલગ-અલગ limit કેમ લાગુ પડે એનો single source
— દા.ત. Grade A area નું particle limit Grade C કરતાં ઘણું કડક હોય.

**૨) EM Location — ચોક્કસ physical sampling point.** Area ની અંદર ચોક્કસ જગ્યા (દા.ત. "Filler-01 LAF
grille", "Gowning room door") જ્યાં sample લેવાય — `EquipmentArea` થી અલગ, વધુ ચોક્કસ (એક area માં
ઘણા locations હોય શકે). Seed-only master (કોઈ create API નથી).

**૩) EM Sample/Reading — એક જ row માં "task" અને "result" બંને.** Sampling schedule થાય ત્યારે row
બને (state `SAMPLE_TASK`), sample collect થાય, result record થાય (એ જ row update થાય, નવી row નહીં) —
Document ૪૧ ની "plan+execution combined" ડિઝાઇન. **શા માટે જરૂરી:** "ક્યારે sample લેવાનું નક્કી થયું"
અને "શું result આવ્યું" — બંને એક જ traceable record માં, અલગ-અલગ tables માં sync રાખવાની જરૂર નથી.

**૪) EM Excursion — limit ઓળંગાય ત્યારે જ બનતો, અલગ entity.** Result `action_excursion` આવે ત્યારે
**automatically** (performer ની કોઈ અલગ action વગર) બને છે — sample ની problem ને investigate/disposition
કરવા માટે પોતાનું lifecycle (`impact assessment`) ધરાવે છે, sample ની પોતાની state થી અલગ.

**કેવી રીતે કામ કરે:** Sampling task અને result એક જ row છે — `SAMPLE_TASK → COLLECTED →
RESULT_PENDING → REVIEWED`. Result પર `alert_action_status` (normal/alert/action_excursion)
**performer manually record કરે** — automatic limit-evaluation નથી (open gap). `action_excursion`
આવે તો system automatically `EmExcursion` row બનાવે (`requires_deviation=true` default).

| Step | Permission | કોણ | Signed? |
|---|---|---|---|
| Create program | `em_program.create` | Admin, EM Technician | ના |
| Schedule task | `em_sample.create` | Admin, EM Technician | ના |
| **Record result** | `em_sample.record_result` | EM Technician, Microbiology Analyst | **હા** — "Performed" |
| **Review** | `em_sample.review` | QA Reviewer, QC Reviewer | **હા** — "Reviewed", independent |
| Record excursion impact | `em_excursion.impact` | Admin, QA Reviewer | ના |

**બીજા modules સાથે જોડાણ:**
- `em_commands.get_area_readiness(area_id)` — **Aseptic Operation** readiness composition **સૌથી
  પહેલાં** આ function call કરે (READY/WARNING/HOLD/NOT_READY).
- Excursion થાય → `requires_deviation=true` → Deviation module માં manual follow-up જરૂરી.
- Resample ક્યારેય જૂની row overwrite નથી કરતી — નવી row બને (AG-08 immutable history).

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-08 ઉમેરેલ)

**સ્ટેપ ૧ — "Schedule EM sampling task" (`/em`, login: `em.technician`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Program version | `EM-PROG-001` (dropdown — **2026-10-08 ફિક્સ**: પહેલા free-text UUID field હતું, હવે "EM programs" list card માંથી real dropdown) |
| Location | `EM-LOC-GRADE-A-01 - critical` (dropdown, પહેલેથી જ real picker હતું) |
| Monitoring type | `viable_air` (free text — કોઈ controlled vocabulary નથી, by design) |

"Schedule task" ક્લિક → sample state `SAMPLE_TASK`.

**સ્ટેપ ૨ — "Record EM result (sign)" (same login, password `ChangeMe123!`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Sample / reading | સ્ટેપ ૧ માં બનાવેલ sample (dropdown — **2026-10-08 ફિક્સ**: પહેલા free-text, header button થી ખોલો તો ખાલી field મળતું) |
| Expected version | `1` |
| Result | `count` → `5`, `unit` → `cfu` |
| Alert / action status | `normal` |

> 🐛 **2026-10-08 real bug fixed:** "Record EM result" button **હંમેશા fail થતું હતું** —
> `em_sample_or_reading`/`record_result` ને Document 106 signature policy જરૂરી છે ("Performed"), પણ
> frontend form એ `challenge_id`/`reauth_password` ક્યારેય collect જ નથી કરતું — બેર POST મોકલતું, જે
> live ચકાસતા `MISSING_SIGNATURE` error સાથે fail થયું (CAPA close/cancel ના જૂના bug ની જ ક્લાસ). Fix:
> આ page ની પોતાની "Review (sign)" button જે `SignatureCeremony` pattern વાપરે છે, એ જ pattern "Record
> result" માં પણ wire કર્યું — હવે "Record result (sign)" ક્લિક → password પૂછે → ખરેખર save થાય.

→ sample state `RESULT_PENDING`.

**સ્ટેપ ૩ — "Review result (sign)" (sample ખોલીને, login: `qa.reviewer` — operator થી અલગ, password `ChangeMe123!`):** → sample state `REVIEWED`.

**સ્ટેપ ૪ (excursion path) — Result માં Alert/action status `action_excursion` પસંદ કરો તેને બદલે:**

→ `EmExcursion` automatically બને છે. "Record excursion impact" (login: `qa.reviewer`):

| Field | Value |
|---|---|
| Excursion | સ્ટેપ ૪ માં auto-created excursion (dropdown — **2026-10-08 ફિક્સ**) |
| Affected batches | `MJ-PFS-B-2601` → `true` |
| Disposition | `Area re-sampled, result within limit - no batch impact confirmed` |

> 🐛 **2026-10-08 real bug fixed (backend):** ઉપરનું ઉદાહરણ disposition text (૬૬ characters) સાથે
> live test કરતા **સર્વર `500 SYSTEM_FAULT` crash** થયું — `em_excursions.disposition` column
> `VARCHAR(40)` જ હતું, કોઈ પણ વાસ્તવિક વાક્ય એના કરતાં લાંબું હોય. Migration 0140 દ્વારા column ને
> `TEXT` (unlimited) સુધી widen કરેલ — equipment module ના પોતાના `fault_description`/`diagnosis`
> fields ના જ પેટર્ન પ્રમાણે. હવે કોઈ પણ લંબાઈનું disposition લખી શકાય.

> ✅ **2026-10-08 live-verified:** આખો flow (program/location dropdown fix → signed result-record fix
> → normal path review → separate action_excursion path → disposition-widen fix) curl દ્વારા live
> `ebmr-new-api` સામે ચલાવીને ચકાસેલ — sample `REVIEWED` પહોંચ્યું, excursion ની impact assessment
> લાંબા disposition સાથે સફળતાપૂર્વક save થઈ.

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| OPS-EM-00 | ઉપરનું સ્ટેપ ૧-૩ (normal path) પૂરું ચલાવો | Sample `REVIEWED` | EM |
| OPS-EM-01 | Sample record "normal" → QA review | Area readiness = READY | EM |
| OPS-EM-02 | Sample result "action_excursion" record | `EmExcursion` auto-create, `requires_deviation=true` | EM, Deviation |
| OPS-EM-03 | Excursion ખુલ્લું હોય એવા area માં Aseptic Operation start કરવાનો પ્રયત્ન | Start block — area not ready | EM, Aseptic |
| OPS-EM-04 | Same user sample record + review બંને કરવાનો પ્રયત્ન | Block — independent reviewer ફરજિયાત | EM |
| OPS-EM-05 | "Record EM result" ને signature ceremony (password) વગર call કરવાનો જૂનો પ્રયત્ન | પહેલાં: હંમેશા `MISSING_SIGNATURE` — હવે ફિક્સ થયેલ | EM |
| OPS-EM-06 | Excursion impact assessment ૪૦ character થી લાંબું disposition લખો | પહેલાં: `500 SYSTEM_FAULT` — હવે ફિક્સ થયેલ (migration 0140) | EM |

---

## ૨૨.૫ Aseptic Operation

**શું છે અને શા માટે જરૂરી:** Sterile fill operation (દા.ત. MeridiJect PFS ભરવું) શરૂ કરવા પહેલાં room,
equipment, sterile input — **બધું જ** simultaneously ready હોવું જોઈએ, અને operation દરમ્યાન દરેક human
intervention/event logged હોવું જોઈએ — contamination-control નો સૌથી સખત પુરાવો.

**કેવી રીતે કામ કરે:** `PREPARATION → EXECUTION → ASEPTIC_COMPLETE` (fail/intervention → `HOLD`).

**આ module ની ખાસિયત — Readiness Composition:** `get_readiness()` પોતે કશું ના ચેક કરે, બીજા ૪ module
ને call કરે:

```
_compute_readiness() →
    em_commands.get_area_readiness(area_id)                     [EM]
  + cleaning_commands.get_area_line_clearance_status(area_id)    [Line Clearance]
  + equipment_commands.get_eligibility(asset_id)  (પ્રત્યેક equipment) [Equipment]
  + sterilization_commands.get_item_status(item_id) (પ્રત્યેક sterile input) [Sterilization]
  → blockers[] પાછું આપે
```

| Step | Permission | કોણ | Signed? | વિશેષ |
|---|---|---|---|---|
| Create operation | `aseptic_operation.create` | Admin, Aseptic Operator | ના | — |
| **Start** | `aseptic_operation.start` | Admin, **Aseptic Supervisor** | **હા** | Readiness clean ના હોય તો block (`AsepticAreaNotReadyError`); operator ને start permission નથી — SoD |
| Record intervention/event | `aseptic_operation.intervention`/`.event` | Admin, Aseptic Operator | ના | Unplanned/critical → `HOLD` + `requires_deviation=true` (2026-10-09 ફિક્સ: doc માં અગાઉ ખોટી રીતે બંને માટે `aseptic_operation.create` લખેલું — real codes `aseptic_router.py` માં અલગ છે, roles ની claim સાચી જ હતી) |
| **Complete** | `aseptic_operation.complete` | Admin, **Aseptic Operator** | **હા** | live-verified: Supervisor ને complete permission નથી (`ROLE_MISSING`) — Operator જ કરે; `requires_deviation` ખુલ્લું હોય ત્યાં સુધી complete ના થાય (2026-10-09 ફિક્સ: permission code પણ ખોટો લખેલો હતો, ઉપર જુઓ) |

**બીજા modules સાથે જોડાણ:** EM + Line Clearance + Equipment + Sterilization — ચારેયના live function
call દ્વારા (ઉપર જુઓ). `qc_test_order_id`/`qc_result_id` QC સાથે capture થાય છે પણ content-validate
નથી થતું (SG-117 ખુલ્લો gap).

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-08 ઉમેરેલ)

**સ્ટેપ ૧ — "Create aseptic operation" (`/aseptic`, login: `aseptic.operator`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Area | `AREA-GRADE-C` (dropdown — Line Clearance + EM બંને સ્ટેપ ૧/doc #૨૨.૧-૨.૪ માં પહેલેથી clean કરેલ) |
| Aseptic profile version | `ASEP-PROF-001 v1` (dropdown) |
| Batch | ખાલી રાખો (અથવા `MJ-PFS-B-2601` જો seeded હોય) |
| Batch step | ખાલી રાખો |
| Equipment | ખાલી રાખો (demo equipment assets qualified/calibrated નથી — ભરશો તો Start block થશે, નીચે ખામી જુઓ) |
| Sterile input references | ખાલી રાખો |
| Media fill reference | ખાલી |

> 🐛 **2026-10-08 real bug fixed:** "Equipment" field **આ form માં ક્યારેય existed જ નહોતું** —
> backend નું `CreateOperationCommand.equipment_ids` real, accepted field છે (readiness composition ની
> "Equipment eligibility" check આ જ field વાંચે છે), પણ frontend form એ ક્યારેય મોકલતું જ નહીં (હંમેશા
> ખાલી list) — એટલે "Equipment eligibility" check practically **ક્યારેય real equipment સામે run જ
> નહોતી થતી**, ભલે backend logic સાચું હતું. Fix: નવું "Equipment" repeatable field ઉમેર્યું (equipment
> picker dropdown સાથે).

"Create aseptic operation" ક્લિક → operation state `PREPARATION`.

**સ્ટેપ ૨ — "Start operation (sign)" (login: `aseptic.supervisor`, password `ChangeMe123!`):**

→ readiness composition run થાય (EM+Line Clearance+Equipment+Sterile input, બધું ખાલી list હોવાથી
ઓટોમેટિક pass) → operation state `EXECUTION`.

**સ્ટેપ ૩ — "Record intervention" (login: `aseptic.operator`):**

| Field | Value |
|---|---|
| Intervention type | `Routine` |
| Planned | `Yes` |
| Location | `Filling needle adjustment` |
| Reason | `Routine needle height check per batch record` |

**સ્ટેપ ૪ — "Record event" (same login):**

| Field | Value |
|---|---|
| Event type | `gown_check` |
| Source | `Gowning room exit monitor` |
| Severity | `Info` |

**સ્ટેપ ૫ — "Complete (sign)" (login: `aseptic.operator` — **Supervisor નહીં**, password `ChangeMe123!`):**

| Field | Value |
|---|---|
| Critical | `false` |
| QC test order ID | ખાલી |
| QC result ID | ખાલી |

→ operation state `ASEPTIC_COMPLETE`.

> ✅ **2026-10-08 live-verified:** આખો flow (Create → readiness all-clean → Start sign → intervention →
> event → Complete sign) curl દ્વારા live `ebmr-new-api` સામે ચલાવીને ચકાસેલ — operation ખરેખર
> `ASEPTIC_COMPLETE` પહોંચ્યું. Readiness JSON માં `em_readiness`/`line_clearance`/`equipment_checks`/
> `sterile_input_checks` ચારેય ભાગ real data સાથે દેખાયા (doc ના ઉપરના "4-module composition" claim ની
> ખરી સાબિતી, ધારેલું નહીં).

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| OPS-ASC-00 | ઉપરનું સ્ટેપ ૧-૫ પૂરું ચલાવો | Operation `ASEPTIC_COMPLETE` | Aseptic |
| OPS-ASC-01 | બધા readiness signal clean — start કરવાનો પ્રયત્ન | Start success, `PREPARATION→EXECUTION` | Aseptic, EM, Line Clearance, Equipment, Sterilization |
| OPS-ASC-02 | EM area "NOT_READY" હોય ત્યારે start | Block — `AsepticAreaNotReadyError` | Aseptic, EM |
| OPS-ASC-03 | Unplanned intervention log કરે | Operation → `HOLD`, `requires_deviation=true` | Aseptic, Deviation |
| OPS-ASC-04 | `requires_deviation=true` ખુલ્લું હોય, complete કરવાનો પ્રયત્ન | Block | Aseptic |
| OPS-ASC-05 | Create form માં Equipment field થી એક real (પણ unqualified) equipment ઉમેરો, Start કરો | Block — equipment eligibility check હવે ખરેખર run થાય | Aseptic, Equipment |
| OPS-ASC-06 | Aseptic Supervisor login થી Complete કરવાનો પ્રયત્ન | Block — `ROLE_MISSING` (Operator જ complete કરી શકે) | Aseptic |

---

## ૨૨.૬ Packaging

**શું છે અને શા માટે જરૂરી:** Secondary packaging દરમ્યાન label/component ની ગણતરી સંતુલિત (balanced)
રહે એની ખાતરી — કોઈ extra label/serial બહાર ના જાય (anti-diversion/serialization control).

**કેવી રીતે કામ કરે:** `not_ready → ready → in_progress → reconciliation_pending → complete` (`hold`
કોઈપણ તબક્કે).

| Step | Permission | Signed? |
|---|---|---|
| Create run, issue label, reconcile, complete | `packaging.execute` (બધા) | **ના — કોઈ પણ Document 16 operation signed નથી**, માત્ર RBAC gate |

Complete ત્યારે જ થાય જ્યારે: `line_clearance_completed=true` **AND** `reconciliation_state="balanced"`
**AND** label reconciliation `balanced`.

**બીજા modules સાથે જોડાણ:**
- 🔧 **SG-056 RESOLVED (PKG-FR-009, 2026-10-09):** ~~`line_clearance_completed` self-attested flag~~ —
  હવે real `equipment.line_clearances` ને query કરે છે (`get_batch_line_clearance_status()`,
  `next_batch_id` વડે key). `CLEARED` clearance ના હોય તો `409 LINE_CLEARANCE_REQUIRED`. `PackagingRun.
  line_ref` હજુ free-text field છે (schema change નથી કરેલ), પણ real gate હવે batch-level match વડે
  કામ કરે છે.
- **Release** ની `_packaging_signals()` packaging data વાંચે છે પણ **warning-only** — ક્યારેય release
  block નથી કરતું.
- 🔧 **SG-056 RESOLVED (PKG-FR-003/006, 2026-10-09):** `label_master`/`print_job` master entity હવે
  **real છે** — `POST /packaging/v1/label-versions` (minimal create) + `POST /packaging/v1/print-jobs`
  (Document 16 ના પોતાના API list માં નામ છે). Label issuance હવે unknown `label_version_id`/
  `print_job_id` ને `404 NOT_FOUND` સાથે reject કરે — પહેલાં કોઈ પણ raw UUID silently accept થતું.

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-08 ઉમેરેલ)

> આ module માટે demo dataset માં "MJ-PFS" batch seeded નથી — live system માં ખરેખર seeded real batch
> `B-2026-0001` ("Metformin 500mg Tablet", code `PRD-000001`) વાપરેલ છે, જેથી ઉદાહરણ ધારેલું નહીં, ખરેખર
> ચકાસેલું હોય.

**સ્ટેપ ૧ — "New run" (`/packaging`, login: `admin` અથવા `packaging.execute` permission ધરાવતો user):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Batch | `B-2026-0001 - Metformin 500mg Tablet (PRD-000001)` (dropdown — પહેલેથી real picker હતું) |
| Line reference | `PKG-LINE-01` (free text — real Equipment FK નથી, doc #૨૨.૨ ની known gap) |

→ run state `not_ready`.

**સ્ટેપ ૨અ — 🔧 પહેલાં real Line Clearance (`/line-clearance`, login: `sanitation.operator`,
password `ChangeMe123!`) — "Start line clearance":**

| Field (UI label) | ભરવાની Value |
|---|---|
| Equipment area / line | `AREA-GRADE-C` (dropdown) |
| Previous batch | ખાલી રાખો |
| **Next batch** | `B-2026-0001` (dropdown — **આ field ફરજિયાત ભરવું** — packaging ની real-check હવે `next_batch_id` વડે જ match કરે છે, doc #૨૨.૨ સ્ટેપ ૧ ના demo માં આ field સામાન્ય રીતે ખાલી રખાય છે, પણ packaging gate સંતોષવા ખાસ અહીં ભરવું) |
| Checklist items — item ૧ | Item type: `Material` |
| Critical clearance | `No` |

"Start line clearance" ક્લિક → `IN_PROGRESS`. પછી "Complete (sign)" — Result `Pass area is clear`,
Expiry ખાલી → state `CLEARED`.

**સ્ટેપ ૨બ — 🔧 હવે packaging ની own "Line clearance" button (same batch run):**

| Field | Value |
|---|---|
| Reason / notes | `Line visually inspected, previous batch identity removed; equipment line clearance CLEARED against B-2026-0001 (step 2અ).` |

→ run state `ready`.

> ⚠️ **ખુલ્લો gap, ફિક્સ નથી:** Packaging ના "Line clearance" button પર UI કોઈ hint/link બતાવતું નથી
> કે real equipment Line Clearance (સ્ટેપ ૨અ) પહેલાં જરૂરી છે — operator UI માં ફક્ત generic
> `409 LINE_CLEARANCE_REQUIRED` error જોશે, "પહેલાં `/line-clearance` પર જાઓ" જેવું guidance text UI
> માં નથી. Backend contract real/enforced છે (2026-10-09 live-verified), frontend-guidance ઉમેરવાનું
> હજુ બાકી.

**સ્ટેપ ૨ક — 🔧 Label version + print job create કરો — ⚠️ UI નથી, API/curl દ્વારા જ (login: `admin`):**

```
POST /packaging/v1/label-versions
  {
    "idempotency_key": "<uuid>", "site_id": "<site_id>", "label_code": "LBL-PRD-000001",
    "version_label": "1.0", "content_hash": "b1946ac92492d2347c6235b4d2611184"
  }
→ label_version_id

POST /packaging/v1/print-jobs
  {
    "idempotency_key": "<uuid>", "run_id": "<run_id>", "label_version_id": "<label_version_id>",
    "quantity": 1000, "variable_data": {"lot": "B-2026-0001"}, "printer_ref": "ZEBRA-LINE-01-PRINTER"
  }
→ print_job_id
```

> ✅ **2026-10-09 live-verified:** આ exact flow live demo DB સામે ચલાવેલ — `label_master`/`print_job`
> row બન્યા (SG-056 RESOLVED, item #૧૦). Random/અસ્તિત્વ-ન-ધરાવતો `label_version_id` મોકલવાથી
> `404 NOT_FOUND` આવ્યું — પહેલાં કોઈ પણ raw UUID silently accept થતું હતું.
>
> ⚠️ **ખુલ્લો gap, ફિક્સ નથી:** `/packaging` page પર label-version/print-job create માટે UI ક્યાંય
> નથી — "Issue labels" form (સ્ટેપ ૩) માં `label_version_id`/`print_job_id` field પણ UI માં નથી, ફક્ત
> backend command/router level પર જ real FK બન્યા છે. Frontend wiring આ pass માં ઉમેરેલ નથી.

**સ્ટેપ ૩ — "Issue labels":**

| Field (UI label) | ભરવાની Value |
|---|---|
| Quantity issued | `1000` |
| Serial range - start | `SN-26010001` |
| Serial range - end | `SN-26011000` |

> 🐛 **2026-10-08 real bug fixed:** "Issue labels" form માં **Serial range માટે કોઈ field જ નહોતું** —
> backend નું `IssueLabelCommand.serial_range` real, accepted field છે (module ના પોતાના core હેતુ
> "anti-diversion/serial control" માટે જ છે), પણ UI ફક્ત Quantity જ પૂછતું — ક્યારેય કોઈ real serial
> capture જ નહોતું થતું. Fix: Serial range start/end fields ઉમેર્યા.
>
> ⚠️ **ઊંડો real finding, live-test કરતા મળ્યો:** Backend ની duplicate-serial check
> (`packaging_service.assert_no_duplicate_serials`) ફક્ત `serial_range={"serials": [...]}` શેપ (દરેક
> serial ને explicit list માં) જ ચેક કરે છે — `{"start", "end"}` range શેપ ને **સાઈલન્ટલી ignore કરે છે**
> (ફંક્શનના પોતાના docstring માં: "numeric range-based allocation dedup is not built this pass,
> SG-056"). ફક્ત start/end fields ઉમેરવાથી data capture તો થાત, પણ duplicate-detection ક્યારેય real રીતે
> કામ જ ના કરત. એટલે frontend માં પણ `expandSerialRange()` ઉમેર્યું — start/end ને (સમાન prefix +
> સરખી digit-width હોય તો) પૂરી serials list માં expand કરે, પછી જ submit કરે.

→ run state `in_progress`.

**સ્ટેપ ૪ — "Reconcile labels":**

| Field | Value |
|---|---|
| Applied | `995` |
| Returned | `0` |
| Destroyed | `3` |
| Rejected | `2` |
| Samples | `0` |

**સ્ટેપ ૫ — "Reconcile packaging":**

| Field | Value |
|---|---|
| Components issued | `1000` |
| Finished packs | `995` |
| Rejects | `2` |
| Samples | `0` |
| Destroyed | `3` |

→ run state `reconciliation_pending`, reconciliation result `balanced` (issued=applied+destroyed+rejected).

**સ્ટેપ ૬ — "Complete run":** → run state `complete`.

> ✅ **2026-10-08 live-verified:** આખો flow (real batch → line clearance → labels issue with full
> serials list → reconcile labels+packaging balanced → complete) curl દ્વારા live `ebmr-new-api` સામે
> ચલાવીને ચકાસેલ — run ખરેખર `complete` પહોંચ્યું. **Duplicate-serial detection પણ ખાસ ચકાસેલ**: એક જ
> serials list બે અલગ runs પર issue કરવાનો પ્રયત્ન કરતા બીજી વખત ખરેખર
> `VALIDATION_FAILED: Duplicate serial(s) already issued` આવ્યું — fix પહેલાં આ ક્યારેય trigger જ નહોતું
> થતું (UI કોઈ serials મોકલતું જ નહોતું).

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| OPS-PKG-00 | ઉપરનું સ્ટેપ ૧-૬ પૂરું ચલાવો | Run state `complete`, reconciliation `balanced` | Packaging |
| OPS-PKG-01 | Run create → labels issue → reconcile balanced → complete | Run state = `complete` | Packaging |
| OPS-PKG-02 | Reconciliation discrepancy (issued ≠ applied+rejected+returned) | `result=discrepancy` — complete block | Packaging |
| OPS-PKG-03 🔧 | Real line clearance ના થયું હોય (કે fail), છતાં packaging line-clearance complete કરવાનો પ્રયત્ન | `409 LINE_CLEARANCE_REQUIRED` — real check (2026-10-09 RESOLVED, પહેલાં self-attest bug હતો) | Packaging, Line Clearance |
| OPS-PKG-04 | Packaging reconciliation discrepancy હોવા છતાં Release evaluate કરે | Release blocked નથી — માત્ર warning (packaging non-blocking) | Packaging, Release |
| OPS-PKG-05 | સમાન serial range (start/end) બે અલગ runs પર issue કરવાનો પ્રયત્ન | Block — duplicate-serial detection (fix પછી જ ખરેખર કામ કરે) | Packaging |
| OPS-PKG-06 | Start/end prefix અલગ હોય (દા.ત. `SN-A-001` થી `SN-B-050`) | `expandSerialRange()` null પાછું આપે — serials list વગર જ `{start,end}` સેવ થાય, dedup check ના થાય | Packaging |
| OPS-PKG-07 🔧 | `POST /packaging/v1/label-versions` → નવું label version create કરો, પછી `POST /packaging/v1/print-jobs` એ જ id સાથે call કરો | Success — real `label_master`/`print_job` row બને (SG-056 RESOLVED 2026-10-09) | Packaging |
| OPS-PKG-08 🔧 | `print-jobs` call માં random/અસ્તિત્વ-ન-ધરાવતો `label_version_id` મોકલો | `404 NOT_FOUND` — પહેલાં કોઈ પણ raw UUID silently accept થતું | Packaging |

---

## ૨૨.૭ QA Review

**શું છે અને શા માટે જરૂરી:** Release પહેલાં નું "review by exception" ગેટ — batch ના exceptions/holds/
corrections નો QA review ફરજિયાત, પછી જ release માટે eligible ગણાય.

**કેવી રીતે કામ કરે:** એક batch = એક review package. `completeness_status` system **automatic ગણે** —
**૩ possible value** (doc માં પહેલા ફક્ત ૨ લખેલ હતા, ખોટું હતું, code વાંચીને સુધારેલ):

| Value | ક્યારે | Complete button |
|---|---|---|
| `blocked` | Hard blocker — batch `on_hold`, Vault integrity fail, batch હજુ `production_complete` નથી, અથવા QC/material/environment/equipment/yield signal માંથી કોઈ real block | **Disabled** |
| `has_exceptions` | કોઈ hard blocker નથી, પણ batch ના audit trail માં corrections નોંધાયેલા છે | **Disabled** |
| `complete` | કોઈ blocker, કોઈ correction નહીં | **Enabled** |

`READY_FOR_REVIEW → REVIEW_COMPLETE` (batch પછી બદલાય તો → `REOPENED`).

| Step | Permission | કોણ | Signed? |
|---|---|---|---|
| Create/reindex package | `qa_review.create`/`qa_review.execute` | QA Reviewer | ના |
| **Complete review** | `qa_review.execute` | QA Reviewer | **હા** — "Reviewed" (role "QA Reviewer" નામથી ચેક, independence data તરીકે record થાય પણ enforced નથી — SG-181, 2026-10-09 ફિક્સ: doc માં અગાઉ ખોટી રીતે "SG-138" cite થયેલું હતું — SG-138 RESOLVED છે અને અલગ work package વિશે છે; SG-181 જ "every PERFORMER on the batch" independence half ને ખુલ્લો documented કરે છે) |

**Complete ત્યારે જ શક્ય જ્યારે** `completeness_status == "complete"` — `blocked`/`has_exceptions` બંનેમાં
complete block.

**બીજા modules સાથે જોડાણ:** **Release** ની `evaluate_eligibility()` આ package ને સીધું lookup કરે —
package ના હોય, અથવા `state ≠ REVIEW_COMPLETE`, અથવા `package.batch_version != batch.version` (stale)
તો `QA_REVIEW_MISSING`/`REVIEW_NOT_CURRENT` blocker. Release ની signature independence (QA Reviewer ≠
QA Releaser) પણ આ package ના audit trail માંથી actor lookup કરીને enforce થાય છે.

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-08 ઉમેરેલ)

**સ્ટેપ ૧ — "New review package" (`/qa-review`, login: `qa.reviewer`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Batch | `B-2026-0001 - Metformin 500mg Tablet (PRD-000001) · production_complete` (dropdown — પહેલેથી real picker) |

"Create package" ક્લિક → package state `READY_FOR_REVIEW`.

**ઉદાહરણ — real live data (ધારેલું નહીં):** આ જ batch પર પહેલેથી બનાવેલ package ખોલતા:

```
completeness_status: "blocked"
blockers: ["QC test order 4ffac062-... has not reached a reviewed/terminal state"]
warnings: [
  "Packaging run 2cb181b8-... is 'not_ready' (reconciliation: not_started)",
  "Packaging run 359d8b92-... is 'in_progress' (reconciliation: not_started)",
  ... (વધુ ૩ packaging run warnings)
]
```

આ real example બતાવે છે: QC test order unresolved હોય ત્યાં સુધી "Complete review" button disabled રહે
(hard blocker), જ્યારે Packaging runs ની warnings **ફક્ત દેખાય છે, block નથી કરતી** (doc #૨૨.૮ Release
ના "packaging non-blocking" design ની જ સુસંગત repeat — QA Review પણ એ જ philosophy વાપરે છે).

**Complete કરવા માટે:** QC test order ને review/terminal state સુધી લઈ જવું પડે (QC module ની જવાબદારી,
આ module ની નહીં) — પછી જ "Reindex" → `completeness_status: "complete"` → "Complete review (sign)"
enabled થાય.

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| OPS-QAR-01 | Batch ખુલ્લા hold વગર, બધા QC/material/environment/equipment/yield signal clean — review package create, complete (sign) | `REVIEW_COMPLETE` | QA Review |
| OPS-QAR-02 | Batch પર ખુલ્લો hold હોય — completeness ચેક | `completeness_status = blocked` — complete block | QA Review |
| OPS-QAR-03 | Review `REVIEW_COMPLETE` પછી batch data બદલાય (reindex) | Status → `REOPENED` | QA Review |
| OPS-QAR-03b | `REOPENED` package પર "Complete review" button | **2026-10-09 real bug fixed:** button પહેલા `p.state !== "REVIEW_COMPLETE"` પર ગેટેડ હતું — એટલે `REOPENED` state પર પણ દેખાતું, click કરતા હંમેશા `409 INVALID_TRANSITION` (`models.py` ALLOWED_TRANSITIONS: `REOPENED→READY_FOR_REVIEW` જ છે, સીધું `REVIEW_COMPLETE` નથી) — NCR ના verify/close button ની જ "frontend allowed-transition vs backend accepted-state" bug ક્લાસ. Fix: button હવે ફક્ત `state === "READY_FOR_REVIEW"` પર દેખાય; `REOPENED` પર ફક્ત "Reindex" button જ દેખાય (જે પહેલા `READY_FOR_REVIEW` માં લાવે, પછી જ Complete શક્ય) | QA Review |
| OPS-QAR-04 | QA Review package જ ના બનાવ્યું હોય, Release evaluate કરે | `QA_REVIEW_MISSING` blocker | QA Review, Release |
| OPS-QAR-05 | Batch પર audit-trail correction હોય, પણ કોઈ hard blocker ના હોય | `completeness_status = has_exceptions` — complete block (blocked થી અલગ reason) | QA Review |
| OPS-QAR-06 | QC test order unresolved હોય ત્યારે package ખોલો | Blocker list માં ચોક્કસ QC test order ID સાથે message દેખાય | QA Review, QC |

> ✅ **2026-10-08 live-verified:** Batch/Product નામ resolution ઉમેર્યું (`_resolve_package_refs()`,
> packaging ના જ pattern) — curl દ્વારા live ચકાસેલ, raw UUID ની જગ્યાએ `B-2026-0001 - Metformin 500mg
> Tablet (PRD-000001)` સાચું દેખાયું. ઉપરનું blocked-package ઉદાહરણ પણ ખરેખર live `GET /qa-review/v1/
> packages/{id}/exceptions` call થી મેળવેલ — ધારેલું નહીં.

---

## ૨૨.૮ Release

**શું છે અને શા માટે જરૂરી:** Market માં જતા પહેલાં નો **final disposition gate** — platform ના બધા જ
quality signal ને ફરીથી, તાજેતરમાં (immediately before commit) ચેક કરીને release/hold/reject નક્કી કરે.

**કેવી રીતે કામ કરે:** `draft_evaluation → eligible/blocked → released/rejected/hold`.
`evaluate_release_scope()` નીચેના બધા signal ભેગા કરે:

| Signal source | Blocker code |
|---|---|
| Batch production complete? | `PRODUCTION_NOT_COMPLETE` |
| QA Review (doc #૨૨.૭) | `QA_REVIEW_MISSING` / `REVIEW_NOT_CURRENT` |
| Batch on hold? | `BATCH_ON_HOLD` |
| Vault integrity (digest/link check) | `INTEGRITY_CHECK_FAILED` |
| Open Deviation attributed to batch | `OPEN_DEVIATION` |
| QC, Material, DDCP, EM, Equipment, CAPA signals | real blockers |
| Yield & Reconciliation (doc #૨૨.૯) | real blocker |
| Packaging (doc #૨૨.૬) | **warning only, non-blocking** |

| Step | Permission | કોણ | Signed? |
|---|---|---|---|
| Evaluate | `release.evaluate` | QA Releaser, QA Reviewer | ના |
| **Release/Hold/Reject decision** | `release.release`/`.hold`/`.reject` | **QA Releaser**, QA Reviewer ની સ્વતંત્ર | **હા** — reason ફરજિયાત, re-evaluate immediately before commit (stale green ના ચાલે) |

**બીજા modules સાથે જોડાણ:** QA Review, Vault, Deviation, QC, Material, EM, Equipment, CAPA, Yield —
બધા સાથે live read. ⚠️ **Genealogy કોઈ પણ release blocker નથી** — "completeness ની કોઈ rule જ invent
નથી કરેલ" (SG-055, honest gap — 2026-10-09 ફિક્સ: doc માં અગાઉ ખોટી રીતે "SG-054" cite થયેલું હતું,
SG-054 ખરેખર Document 14/QA Review ની પોતાની "genealogy completeness" gap છે, Release ની પોતાની નહીં;
SG-055 ૨૦૨૬-૦૯-૨૨ ના update માં ખાસ "Genealogy is the only named category with no signal at all" કહે
છે — બરાબર આ જ claim માટેનું correct id).

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-08 ઉમેરેલ)

**સ્ટેપ ૧ — "Evaluate" (`/release`, login: `qa.releaser`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Batch | `B-2026-0001 - Metformin 500mg Tablet (PRD-000001)` (dropdown) |

"Evaluate" ક્લિક → `POST /release/v1/scopes/batch/{batch_id}/evaluate` → scope state તરત refresh થાય.

**ઉદાહરણ — real live data (ધારેલું નહીં, આ જ batch `B-2026-0001` પર ખરેખર `curl` થી મેળવેલ):**

```
scope: { batch_number: "B-2026-0001", product_code: "PRD-000001",
         product_name: "Metformin 500mg Tablet", state: "blocked", version: 4 }

evaluation.eligible: false
evaluation.blockers (૪ — બધા CRITICAL):
  REVIEW_NOT_CURRENT     source=qa_review_package  → resolution: COMPLETE_QA_REVIEW
  OPEN_DEVIATION         source=deviation_record    → resolution: RESOLVE_DEVIATION
  QC_TESTING_INCOMPLETE  source=qc_test_order       → resolution: COMPLETE_QC_TESTING
  OPEN_CAPA              source=capa_record         → resolution: RESOLVE_CAPA

evaluation.warnings (૬ — બધા WARNING, non-blocking):
  PACKAGING_INCOMPLETE × ૬  source=packaging_run (doc #૨૨.૬ માં બનાવેલ ૬ runs)
  → resolution: REVIEW_PACKAGING_RUN
```

આ real example બતાવે છે: દરેક blocker/warning object માં `code`, `severity`, `source_type`,
`source_id` (જે-તે ચોક્કસ record ની UUID), `message_key`, અને `resolution_action` હોય છે — UI આ
`resolution_action` નો ઉપયોગ કરીને સીધું related module તરફ link બતાવી શકે (દા.ત.
`COMPLETE_QC_TESTING` → QC module ખોલો). ૪ CRITICAL blocker પૈકી કોઈ પણ એક clear ન થાય ત્યાં સુધી
`eligible: false` રહે — "Release" button disabled. ૬ Packaging warning ફક્ત display માટે — તે ક્યારેય
`eligible` ને false નથી કરતા (packaging non-blocking design, doc #૨૨.૬ માં જ explain કરેલ).

**Release decision (sign) ત્યારે જ શક્ય જ્યારે** `eligible: true` — ઉપરના ૪ blocker પૈકી દરેક clear
થવું જોઈએ: QA Review package complete કરવું (doc #૨૨.૭), deviation close કરવું, QC test order
terminal state માં લઈ જવું, CAPA resolve કરવું. પછી ફરી "Evaluate" → `eligible: true` → "Release"
(sign, reason ફરજિયાત) → Vault માં release package snapshot લખાય.

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| OPS-REL-01 | બધા signal ચોખ્ખા — evaluate → release decision (sign) | `released`, Vault snapshot created | Release, Vault, QA Review |
| OPS-REL-02 | Open deviation attributed to batch — evaluate | `OPEN_DEVIATION` blocker, `source_id` = deviation ની ચોક્કસ UUID | Release, Deviation |
| OPS-REL-03 | Packaging reconciliation ના-verified runs હોય — evaluate | `PACKAGING_INCOMPLETE` warning (list માં દેખાય), `eligible` છતાં true રહી શકે | Release, Packaging |
| OPS-REL-04 | QA Reviewer જ release decision sign કરવાનો પ્રયત્ન કરે (independence violation) | Block — QA Releaser ફરજિયાત, QA Reviewer થી અલગ | Release, QA Review |
| OPS-REL-05 | Genealogy trace અધૂરું હોય — evaluate | Release છતાં eligible (genealogy non-blocking, documented gap) | Release, Genealogy |
| OPS-REL-06 | QA review package stale (batch પછી બદલાયો) — evaluate | `REVIEW_NOT_CURRENT` blocker, `source_id` = package ની UUID | Release, QA Review |
| OPS-REL-07 | QC test order હજુ reviewed/terminal state માં નથી — evaluate | `QC_TESTING_INCOMPLETE` blocker, `source_id` = test order ની UUID | Release, QC |
| OPS-REL-08 | Open CAPA batch પર attribute થયેલ — evaluate | `OPEN_CAPA` blocker, `source_id` = CAPA ની UUID | Release, CAPA |

> ✅ **2026-10-08 live-verified:** Scope/Product નામ resolution ઉમેર્યું (`_resolve_scope_refs()`,
> packaging/QA Review ના જ pattern) — raw UUID ની જગ્યાએ `batch_number`/`product_code`/`product_name`
> હવે `scope_id`, `batch_id`, `product_version_id`, `released_vault_object_id` ની સાથે resolve થઈને
> આવે છે. ઉપરનું `blocked`-state evaluation ઉદાહરણ ખરેખર live `POST .../evaluate` + `GET .../
> eligibility` call થી મેળવેલ — ધારેલું નહીં; આ જ batch પર doc #૨૨.૬ Packaging ના testing દરમિયાન
> બનાવેલ ૬ packaging run ની warning તરીકે જ અહીં live દેખાય છે (cross-module traceability નું real
> ઉદાહરણ).

---

## ૨૨.૯ Yield & Reconciliation

**શું છે અને શા માટે જરૂરી:** કેટલું material/label/component ગયું અને કેટલું બહાર આવ્યું — mass-balance
પ્રૂફ. ના મળે એવો loss "lost" ના ગણાય, investigation trigger થવી જોઈએ.

**આ module ની ૨ અલગ entity, અને દરેક શા માટે જોઈએ:**

| Entity | શું રેકોર્ડ કરે | કેમ અલગ table |
|---|---|---|
| **Manufacturing Calculation** (`yield`/`potency`) | Theoretical vs actual quantity, rules-engine formula નું result, tolerance limit | Document ૦૮ ના generic Rules engine ને delegate — આ module પોતે formula embed નથી કરતું (`rule_object_id`/`rule_evaluation_id` link) |
| **Reconciliation Record** (`material`/`packaging`/`label`/`component`) | Issued/consumed/returned/samples/rejected/destroyed/approved_loss ની mass-balance (component માટે `assembled`/`scrapped` પણ) | Yield = "કેટલું percentage બન્યું" (ratio); Reconciliation = "ક્યાં-ક્યાં ગયું" (ભાગ-ભાગ account) — બે અલગ regulatory પ્રશ્નના જવાબ, એક entity માં ભેગા કરવા યોગ્ય નહીં |

### Reconciliation ના ૪ પ્રકાર — Packaging/Label/Component ખાસ કરીને કેવી રીતે કામ કરે

**બધા ૪ પ્રકાર (`material`/`packaging`/`label`/`component`) એક જ engine વાપરે** — same
`_persist_reconciliation()` function, same mass-balance formula (`issued - (consumed+returned+samples+
rejected+destroyed+...)` = `variance`), same tolerance-rule check, same `ACCEPTABLE`/`OUT_OF_TOLERANCE`
outcome, same independent-verify જરૂરિયાત. ફક્ત data ક્યાંથી આવે અને કેટલા category — એ અલગ પડે:

| પ્રકાર | Data ક્યાંથી આવે | ખાસ વાત |
|---|---|---|
| **Material** | User સીધું `item_ref`/`quantities` ભરે | Packaging સાથે literally **એક જ function** (`_evaluate_reconciliation`) — ફક્ત `reconciliation_type` string અલગ |
| **Packaging** | User સીધું `item_ref`/`quantities` ભરે (bulk packaging material — carton, foil વગેરે, batch ના packaging run માં વપરાયેલ) | Material જ પેટર્ન, અલગ item (bulk material, label નહીં) |
| **Label** | **User કશું ભરતો જ નથી** — ફક્ત `packaging_run_id` આપે, quantities Packaging module (Document ૧૬) ના પોતાના label counts માંથી **auto-derive** થાય (`applied`→`consumed` મેપ થાય) | Packaging module નો પોતાનો `reconciliation_state` (`balanced`/`discrepancy`) check આનાથી **સંપૂર્ણપણે અલગ અને independent** છે — Packaging run complete કરવા માટે પોતાનો check pass કરવો પડે (doc #૨૨.૬), પણ Yield ની આ Label reconciliation **optional** છે, કોઈ force નથી કરતું ચલાવવા — Packaging નો result ફક્ત audit માટે સાથે રેકોર્ડ થાય, blindly trust નથી કરાતો |
| **Component** | User `item_ref`/`quantities` ભરે, વધારાના ૨ category (`assembled`/`scrapped`) સાથે; optional `device_unit_id` (specific serialized unit, દા.ત. DDCP combination-product) | `device_unit_id` આપો તો એ જ batch નું હોવું જોઈએ (ચેક થાય) — `get_batch_summary` નું `by_device_unit` field દરેક serial unit નો અલગ totals/exception બતાવે, જેથી batch-level average માં એક ખરાબ unit "છુપાઈ" ના જાય |

**Release સાથે જોડાણ — બધા ૪ પ્રકાર સરખા ગણાય:** `_yield_signals()` (doc #૨૨.૮ Release) batch ની
**દરેક** `ReconciliationRecord` વાંચે — type (material/packaging/label/component) કોઈ ફેર નથી પાડતું:
- `OUT_OF_TOLERANCE`/`FAILED` state → **CRITICAL blocker**
- Resolved પણ હજુ independently verify નથી થયું → non-blocking warning

**⚠️ અગત્યની વાત — ૨ અલગ "packaging" signal, ગૂંચવવું નહીં:** Release ની પોતાની `_packaging_signals()`
(doc #૨૨.૮) સીધી `PackagingRun.state`/`.reconciliation_state` વાંચે — **always non-blocking** (project-
owner decision: "packaging/labeling independently track થાય, release ના timeline થી અલગ"). આ Yield ના
**Label** reconciliation type થી **સંપૂર્ણપણે અલગ mechanism** છે. એટલે batch નું packaging
`_packaging_signals()` પ્રમાણે "balanced" હોઈ શકે, છતાં Yield માં Label reconciliation ક્યારેય evaluate
જ ના થયું હોય (કોઈ force નથી કરતું) — બંને independent, એક બીજા ને substitute નથી કરતા.

**કેવી રીતે કામ કરે (calculation):** `PENDING_INPUT → READY → CALCULATED → VERIFIED/FAILED/OUT_OF_LIMIT`
(`SUPERSEDED` correction માટે — edit નહીં, નવી row).
**Reconciliation નો પોતાનો initial state અલગ છે:** evaluate કરતાં જ સીધું `ACCEPTABLE` (within tolerance)
અથવા `OUT_OF_TOLERANCE` (બહાર) — `CALCULATED` reconciliation માટે ક્યારેય વપરાતું નથી, ફક્ત calculation
માટે.

| Step | Permission | Signed? |
|---|---|---|
| Evaluate (yield/potency/material/packaging/label/component reconciliation) | `yield_calculation.evaluate`/`reconciliation.evaluate` | ના |
| **Verify** | `reconciliation.verify` | **હા** — independent verifier ફરજિયાત (performer ≠ verifier, SIG-FR-018) |
| View batch summary | `reconciliation.view` (નવું, નીચે જુઓ) | ના |

**બીજા modules સાથે જોડાણ:** **Release** ની `_yield_signals()` આ module ની batch summary ને સીધી call
કરે — real blocker/warning contribute કરે (doc #૨૨.૮ માં જ real live example). ERP external comparison
data **informational only** — GxP-computed variance ને override નથી કરતું.

---

### 🐛 2026-10-08 live-testing દરમિયાન મળેલ ૩ real bug, fix કરેલ

**Bug ૧ — Batch summary GET endpoint પર કોઈ authentication જ નહોતું:** `GET /reconciliation/v1/
batches/{id}/summary` ને `actor` dependency જ નહોતી — કોઈ પણ, token વગર પણ, આખા batch ની yield/
reconciliation data (quantities, tolerance, variance, loss reasons) વાંચી શકતું. દરેક બીજા module ના
read endpoint (qa_review.view/release.view) સાથે સરખાવતાં આ ચોક્કસ gap હતું. **Fix:** નવી permission
`reconciliation.view` ઉમેરી (Admin/Operator/Supervisor/QA Reviewer/QA Releaser/QC Reviewer ને — બરાબર
એ જ roles જેમને `qa_review.view`/`release.view` પહેલેથી છે), endpoint ને `evaluate_policy()` call
ઉમેર્યો.

**Bug ૨ — Signature-challenge endpoint પર પણ કોઈ role check નહોતો:** `POST .../signature-challenges`
કોઈ પણ logged-in user ને (role ને ધ્યાનમાં લીધા વગર) "Verified" ની challenge આપી દેતું — actual
`/verify` POST પોતે `reconciliation.verify` check કરતું હતું એટલે આખરે block તો થતું, પણ record_hash/
version leak થતું અને ના-વપરાતા challenge row ભેગા થતા. **Fix:** challenge endpoint માં પણ એ જ
`reconciliation.verify` check ઉમેર્યો (QA Review/Release ના પોતાના signature-challenges routes જે
pattern already વાપરે છે, એ જ).

**Bug ૩ (સૌથી મોટું) — within-tolerance reconciliation ક્યારેય verify જ ના થઈ શકે:**
`_persist_reconciliation()` within-tolerance case ને **`ACCEPTABLE`** state આપે છે, પણ `verify_record()`
ની gate list માત્ર `CALCULATED`/`OUT_OF_LIMIT`/`OUT_OF_TOLERANCE` સ્વીકારતી — `ACCEPTABLE` ભૂલથી છૂટી
ગયેલ. પરિણામ: Release ની `_yield_signals()` પોતે `RECONCILIATION_NOT_VERIFIED` warning (resolution
action `VERIFY_RECONCILIATION`) બતાવે, પણ એ જ action try કરતાં **દરેક વખતે** `VALIDATION_FAILED` મળે —
સૌથી common case (within-tolerance reconciliation, batch ને exception ન હોય ત્યારે) ક્યારેય verify જ
ના થઈ શકે. Live reproduced: material reconciliation evaluate (within tolerance) → `ACCEPTABLE` →
verify attempt → `VALIDATION_FAILED: current_state=ACCEPTABLE`. **Fix:** gate list માં `ACCEPTABLE`
ઉમેર્યું.

---

### Frontend dropdown audit

`/yield` page પહેલેથી જ સારી રીતે બનેલ — Batch, Rule ID, Packaging run ID, Linked deviation ID બધા
`EntityPickerField` વાપરે છે (raw UUID free-text ક્યાંય નહીં). ~~એક અપવાદ: Device unit ID free text જ
રાખ્યું — કોઈ list endpoint અસ્તિત્વ જ નથી ધરાવતું~~ **🔧 2026-10-09 ફિક્સ:** એ justification હવે
stale હતી — `§૨૨.૧૧ Equipment/Devices`ના એ જ session માં ઉમેરેલ `GET /devices/v1/units` (`batch_id`
filter સાથે) હવે real existe છે. "Device unit ID" field હવે `EntityPickerField` છે, selected Batch ને
`batch_id` તરીકે પસાર કરીને scoped (component reconciliation નો hint — "must belong to this batch" —
હવે dropdown પોતે જ enforce કરે છે, manual match-checking જરૂરી નથી). Live-verified:
`GET /devices/v1/units?site_id=...&batch_id=...` એ જ ૩ device unit પાછા આપે જે ખરેખર એ batch ના છે.

**બેકએન્ડ ફિલ્ડ UI માં ક્યારેય દેખાતા જ નહોતા** (backend response માં હતા, frontend interface/render માં
ડ્રોપ): `evaluated_by_user_id`/`verified_by_user_id` (હવે username તરીકે resolve — નવું
`_resolve_summary_refs()`), `device_unit_id` (હવે serial number તરીકે, DeviceUnit lookup), `input_refs`,
`supersedes_id`, `loss_reasons`, `tolerance_rule`, `external_reference`, `external_comparison` — બધા
હવે detail popup માં દેખાય છે.

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-08 ઉમેરેલ, real batch
`B-2026-0001` પર ખરેખર curl થી ચલાવેલ)

**સ્ટેપ ૧ — "Evaluate yield" (`/yield`, login: `operator1`):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Batch | `B-2026-0001 - Metformin 500mg Tablet (PRD-000001)` (dropdown) |
| Phase code | ખાલી (whole-batch) |
| UOM | `kg` |
| Theoretical quantity | `1000` |
| Actual quantity | `995` |
| Min percent | `95` |
| Max percent | `105` |

→ `state: CALCULATED`, `result: {raw_percent: "99.500", yield_percent: "99.50"}`.

**સ્ટેપ ૨ — "Material" reconciliation (same page, same login):**

| Field (UI label) | ભરવાની Value |
|---|---|
| Batch | `B-2026-0001` |
| UOM | `kg` |
| Item reference | `material_code` → `METFORMIN-API` |
| Quantities — Issued | `1000` |
| Quantities — Consumed | `995` |
| Quantities — Samples | `3` |
| Quantities — Approved loss | `2` |
| Tolerance type/value | `percentage` / `2` |
| Loss reasons | category `process_loss`, description "Residual powder in blender bowl, within expected process loss", quantity `2` |

→ `state: ACCEPTABLE`, `variance: "0.000000"` (1000 issued = 995+3+2 accounted, બરાબર mass balance).

**સ્ટેપ ૩ — Verify બંને (login: `qa.reviewer`, independent of `operator1` જેણે evaluate કર્યું):**

Calculation ની "Verify" ક્લિક → sign → `state: VERIFIED`. Reconciliation ની "Verify" ક્લિક → sign →
`state: VERIFIED` (Bug ૩ ના fix પછી જ આ કામ કરે છે — fix પહેલાં અહીં જ અટકી જતું).

**Final batch summary** (ખરેખર `GET /reconciliation/v1/batches/{id}/summary` call થી — ધારેલું નહીં):

```
release_blocked: false
calculations: [{ calculation_type: YIELD, theoretical: 1000, actual: 995, result.yield_percent: "99.50",
                 state: VERIFIED, evaluated_by_username: "operator1", verified_by_username: "qa.reviewer" }]
reconciliations: [{ reconciliation_type: MATERIAL, quantities: {issued:1000, consumed:995, samples:3,
                 approved_loss:2, accounted:1000}, variance: "0.000000", state: VERIFIED,
                 loss_reasons: [{category: process_loss, quantity: 2, description: "..."}] }]
```

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| OPS-YLD-01 | Yield evaluate — within limit, independent verify | `CALCULATED` → `VERIFIED` | Yield & Reconciliation |
| OPS-YLD-02 | Calculated yield limit ની બહાર | `OUT_OF_LIMIT` — Release blocker (CRITICAL) | Yield & Reconciliation, Release |
| OPS-YLD-03 | Material reconciliation evaluate — within tolerance, independent verify | `ACCEPTABLE` → `VERIFIED` (Bug ૩ નો regression test) | Yield & Reconciliation |
| OPS-YLD-04 | VERIFIED record માં correction જરૂરી | જૂની row edit નહીં — નવી row `supersedes_id` સાથે | Yield & Reconciliation |
| OPS-YLD-05 | ERP external comparison data mismatch, GxP calculation OK | GxP variance જ final ગણાય (ERP informational) | Yield & Reconciliation |
| OPS-YLD-06 | Token વગર batch summary GET | `401` (Bug ૧ નો regression test) | Yield & Reconciliation |
| OPS-YLD-07 | `reconciliation.view` ના ધરાવતો role batch summary GET કરે | `403 ROLE_MISSING` | Yield & Reconciliation |
| OPS-YLD-08 | `reconciliation.verify` ના ધરાવતો role signature-challenge request કરે | `403 ROLE_MISSING` (Bug ૨ નો regression test) | Yield & Reconciliation |

> ✅ **2026-10-08 live-verified:** ઉપરનો આખો flow (evaluate yield → evaluate material reconciliation →
> બંને independent verify → final summary) ખરેખર live API સામે `curl` થી ચલાવેલ, real batch
> `B-2026-0001` પર — invented data નહીં. `reconciliation.view` permission + `_resolve_summary_refs()`
> પણ live restart પછી ચકાસેલ (no-auth → `401`, wrong-role → `403 ROLE_MISSING`, `qa.releaser` →
> `200` resolved data).

---

## ૨૨.૧૦ Genealogy

**શું છે અને શા માટે જરૂરી:** Supplier lot → material → batch → device/package → distribution —
recall/investigation વખતે "આ ખરાબ material ક્યાં-ક્યાં ગયું" જાણવા માટે **forward/backward trace graph**.

**આ module ની ૨ entity, અને દરેક શા માટે જોઈએ:**

| Entity | શું છે | Edit થાય? |
|---|---|---|
| **Node** (`genealogy_node`) | graph નો એક point — supplier lot, material lot, container, batch, device, package, carton, pallet, distribution reference વગેરે (૧૭ પ્રકાર કુલ) | **ક્યારેય નહીં** — pure insert-only fact (version/state column જ નથી) |
| **Edge** (`genealogy_edge`) | ૨ node વચ્ચેનું સંબંધ — `CONSUMED_IN`/`DERIVED_FROM`/`PRODUCED_AS`/`PACKAGED_AS` વગેરે ૧૪ પ્રકાર, quantity/uom સાથે | Edit નહીં — correction `SUPERSEDED` ફ્લેગ + નવી edge તરીકે (AG-08) |

Node ક્યારેય edit નથી થતું કારણ કે node પોતે "આ entity exist કરે છે" એ fact જ છે — ભૂલ node માં નહીં,
ક્યાં node ક્યાં જોડાયેલ છે (edge) એમાં હોય, એટલે correction mechanism edge level પર જ છે.

**કેવી રીતે કામ કરે:** **Public write API જ નથી** (`genealogy.view` — read-only permission, ૫ GET
endpoint: lookup, ancestors, descendants, full-trace-by-serial, affected-products-by-lot). Node/edge
બીજા modules પોતે internally લખે — `batch_execution`/`material` dispensing ના call sites real છે, અને
🔧 **2026-10-09 (project-owner-directed, client gap-closure item #11) થી packaging/sterilization/DDCP
પણ wire થયા** (SG-052 PARTIALLY RESOLVED — નીચે જુઓ). `complaint`-triggered review (GEN-FR-019, WP-09
dependency) હજુ ખુલ્લું.

**બીજા modules સાથે જોડાણ:** ⚠️ **Release કોઈ પણ genealogy completeness blocker નથી વાપરતું** (SG-055 —
doc #૨૨.૮ માં જ cross-reference; 2026-10-09 ફિક્સ, અગાઉ ખોટી રીતે "SG-054" cite થયેલું).

---

### 🐛 live-testing દરમિયાન મળેલ ૩ real bug, fix કરેલ (frontend-only, backend સાચું હતું)

**Bug ૧ — Node-type filter dropdown ખોટી values ધરાવતું:** `/genealogy` ના "Node type" dropdown માં
`"batch"`/`"shipment"` options હતા — પણ backend ના real `NODE_TYPES` enum માં આ નામ જ નથી (real નામ
`"drug_batch"` છે, `"shipment"` જેવું કંઈ નથી). **Live reproduced:** `node_type=batch` સાથે lookup
કરતાં `[]` (ખાલી) મળ્યું, જ્યારે real data (`B-2026-0001`) `node_type=drug_batch` પર જ મળે છે — UI થી
"batch" પસંદ કરનાર user ને હંમેશા ખોટું "કંઈ ના મળ્યું" દેખાય, ભલે data હોય. **Fix:** dropdown ને
`genealogy/models.py::NODE_TYPES` સાથે બરાબર મેચ કર્યું (૧૭ options, બધા real).

**Bug ૨ — Edge ડેટા backend માં હતો, UI માં ક્યારેય દેખાતો જ નહોતો:** Ancestor/descendant trace ના
response માં backend પહેલેથી જ `edges` array મોકલતું (edge_type, quantity, uom, state સાથે) — પણ
frontend ના `Trace` interface માં આ field જ નહોતું, ફક્ત `edge_ids.length` ("N edge(s)") count જ
દેખાતું. એટલે genealogy ની સૌથી અગત્યની વાત — "શું કેટલું, ક્યાંથી ક્યાં ગયું" — UI માં ક્યારેય
દેખાતી જ નહોતી. **Fix:** `Edge` interface ઉમેર્યું, "Edges (the connections)" નામનું નવું table
ઉમેર્યું (Edge type | From | To | Quantity | State), node id ને business_ref તરીકે resolve કરીને.

**Bug ૩ (2026-10-09, real user question) — "Full trace by serial"/"Affected products by lot" ના ફિલ્ડ
free text હતા, પણ એ ખરેખર reference value છે:** `genealogy_service.full_trace()`/
`affected_products()` બંને `GenealogyNode.business_ref` ને જ lookup કરે છે (એ જ column જે "Find nodes"
mode પહેલેથી browse કરે છે) — codebase વાંચીને confirm કર્યું, guess નહીં. એટલે "Serial"/"Material lot"
ફિલ્ડ પણ ખરેખર dropdown-able છે, free text ની જરૂર નથી. **Fix:** નવું `useGenealogyNodeRefs()` hook
ઉમેર્યું (`GET /genealogy/v1/nodes/lookup?site_id=` નો જ unfiltered data, "Find nodes" ની જ source) —
બંને ફિલ્ડ હવે `EntityPickerField` (value = node નો business_ref string, id નહીં — "Full trace"/
"Affected products" endpoint URL માં business_ref જ લે છે), manual-entry fallback સાથે. Type-wise
filter (serial vs lot) ઇરાદાપૂર્વક નથી ઉમેર્યું — backend પોતે પણ lookup વખતે કોઈ type-based ભેદ નથી
પાડતું (કોઈ પણ node type નો business_ref બંને endpoint પર કામ કરે), એટલે dropdown ની label માં
node_type પણ દેખાય છે જેથી user સાચું pick કરી શકે.

---

### ⚠️ જાણીતી મર્યાદા (bug નહીં, honest gap — fix નથી કરેલ)

`GET /material-lot/{lot}/affected-products` (recall query) ફક્ત `FINAL_PRODUCT_NODE_TYPES` માં listed
node types જ પાછા આપે: `device_unit`/`combination_product_*`/`package`/`carton`/`pallet`/
`distribution_reference` — **`drug_batch` આ list માં નથી**. Live-verified: material lot
`LOT-API-2603` નું `affected-products` lookup `affected_products: []` (ખાલી) આપે છે, છતાં એ જ lot
ખરેખર batch `B-2026-0001` માં consumed છે (descendants trace માં real `CONSUMED_IN` edge દેખાય છે). આ
module ના non-device, non-packaged oral-solid-style product (જેમ કે Metformin tablet) માટે recall
query "affected products" ક્યારેય drug batch પોતે બતાવશે નહીં — ફક્ત device/package/carton/pallet/
distribution સુધી પહોંચેલ હોય તો જ. "શું drug_batch ને પોતે final product ગણવું" એ regulated recall-query
scope નો નિર્ણય છે (CLAUDE.md ની SPEC_GAP rule પ્રમાણે guess નથી કરેલ) — code બદલ્યો નથી, ફક્ત honestly
documented.

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-08 ઉમેરેલ, real live data —
ધારેલું નહીં)

આ module માં કોઈ create form નથી (read-only) — નીચેનો chain material dispensing/batch consumption
દ્વારા already live-generated છે (user એ `/materials`/`/batch-execution` વાપરીને બનાવેલ, genealogy
module એ auto-record કર્યું):

**લુકઅપ (`/genealogy`, login: `operator1`, Query = "Find nodes", Node type = `drug_batch`):**

→ real result: `B-2026-0001` (node_type `drug_batch`, authoritative_record_type `batch`).

**એ node પર "Trace" ક્લિક → Ancestors tab:**

```
nodes: [{ business_ref: "LOT-API-2603", node_type: "material_lot" }]
edges: [{ edge_type: "CONSUMED_IN", from: LOT-API-2603, to: B-2026-0001,
          quantity: "50.00000000", uom: "kg", state: "ACTIVE" }]
```

**એ જ material lot node ખોલતાં Descendants tab:**

```
nodes: [
  { business_ref: "B-2026-0001", node_type: "drug_batch" },
  { business_ref: "DISP-B2026-0001-01", node_type: "material_container" }
]
edges: [
  { edge_type: "CONSUMED_IN", from: LOT-API-2603, to: B-2026-0001, quantity: "50.00000000", uom: "kg" },
  { edge_type: "DERIVED_FROM", from: LOT-API-2603, to: DISP-B2026-0001-01, quantity: "30.00000000", uom: "kg" }
]
```

આ real example બતાવે છે: એક જ material lot (LOT-API-2603) બે અલગ-અલગ edge type થી જોડાયેલ — `CONSUMED_IN`
(સીધું batch માં વપરાયું, 50kg) અને `DERIVED_FROM` (dispensed container DISP-B2026-0001-01 બન્યું, 30kg)
— mass-balance ના બે અલગ pathway, બંને traceable.

---

#### 🔧 PACKAGED_AS ઉદાહરણ (2026-10-09 ઉમેરેલ) — same batch `B-2026-0001`

doc #૨૨.૬ (Packaging) નું સ્ટેપ ૧-૬ ઉપરના જ batch `B-2026-0001` સામે ચલાવ્યા પછી (run `complete`
સુધી પહોંચે), એ જ `B-2026-0001` `drug_batch` node (ઉપરનું lookup) નું **Descendants tab** ખોલતાં:

```
nodes: [{ node_type: "package", business_ref: null, authoritative_record_type: "package_node" }]
edges: [{ edge_type: "PACKAGED_AS", from: B-2026-0001, to: <package node>, state: "ACTIVE" }]
```

> ✅ **2026-10-09 live-verified:** `GET /genealogy/v1/nodes/{drug_batch_node_id}/descendants` curl
> દ્વારા live demo DB સામે ચકાસેલ — packaging run complete કર્યા પછી real `PACKAGED_AS` edge એક real
> `package` node તરફ confirm થયો (edge id `fe66a318-...`, state `ACTIVE`). Sterilization cycle
> `accept` (doc #૨૨.૩) → `STERILIZED_IN` edge તરફ `evidence_record` node, અને DDCP assembly step
> `PASS` → `ASSEMBLED_INTO` edge તરફ `device_unit` node — એ જ pattern, batch node ના descendants માં.
>
> ⚠️ **જાણીતી simplification:** DDCP wiring માટે કોઈ `device_unit` master table નથી (dedupe કરવા
> માટે), એટલે દરેક સફળ (`PASS`) assembly-step record પોતાનો અલગ genealogy node બનાવે છે — same physical
> unit ની multiple steps માટે એક જ node નથી. Edges/data real અને traceable છે, પણ "એક unit = એક node"
> ગેરંટી નથી.

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| OPS-GEN-01 | Material dispense + batch consumption થાય | Node + `CONSUMED_IN`/`DERIVED_FROM` edge auto-create | Genealogy, Material, Batch Execution |
| OPS-GEN-02 | Lookup — Node type `drug_batch`, real batch ID | Real node મળે (Bug ૧ નો regression test — પહેલાં `"batch"` dropdown value ખોટી હોવાથી ખાલી પરિણામ મળતું) | Genealogy |
| OPS-GEN-03 | Node ખોલીને ancestors/descendants trace | Edges table માં edge_type/quantity/uom દેખાય (Bug ૨ નો regression test) | Genealogy |
| OPS-GEN-04 | Genealogy write API સીધી call કરવાનો પ્રયત્ન (non-existent) | API જ નથી — ૪૦૪/method not allowed | Genealogy |
| OPS-GEN-05 | Genealogy trace અધૂરું, batch release evaluate | Release blocked નથી (documented gap, SG-055) | Genealogy, Release |
| OPS-GEN-06 | Non-device material lot નું affected-products lookup | `affected_products: []` — drug_batch final-product list માં નથી (documented honest gap, fix નથી) | Genealogy |
| OPS-GEN-07 | "Full trace by serial" ફિલ્ડ dropdown ખોલો | Real node list દેખાય (`B-2026-0001 (drug_batch)`, `LOT-API-2603 (material_lot)`, ...) — pick કરતાં real trace મળે (Bug ૩ નો regression test) | Genealogy |
| OPS-GEN-08 | "Affected products by lot" ફિલ્ડ dropdown ખોલો | એ જ node list dropdown માં દેખાય, manual-entry fallback પણ ઉપલબ્ધ | Genealogy |
| OPS-GEN-09 🔧 | Packaging run `complete` સુધી ચલાવો, પછી batch node ના descendants જુઓ | Real `package` node + `PACKAGED_AS` edge (SG-052 PARTIALLY RESOLVED 2026-10-09) | Genealogy, Packaging |
| OPS-GEN-10 🔧 | Sterilization cycle `batch_id` સેટ હોય, "Review" → `accept` sign કરો, descendants જુઓ | Real `evidence_record` node + `STERILIZED_IN` edge — ફક્ત `accept` પર, `reject` પર નહીં | Genealogy, Sterilization |
| OPS-GEN-11 🔧 | DDCP device assembly step `result="PASS"` record કરો, descendants જુઓ | Real `device_unit` node + `ASSEMBLED_INTO` edge — ફક્ત `PASS` પર, `FAIL`/`REWORK` પર edge નથી | Genealogy, DDCP |

> ✅ **2026-10-09 live-verified:** `useGenealogyNodeRefs()` fix real site ના live node list સામે curl
> થી ચકાસેલ (૩ real node — `B-2026-0001`/`LOT-API-2603`/`DISP-B2026-0001-01`) — બંને endpoint
> (`/serial/B-2026-0001/full-trace`, `/material-lot/LOT-API-2603/affected-products`) એ જ business_ref
> values થી સાચું જવાબ આપે છે. 2026-10-08 ના બંને fix (node-type list, edges table) પણ ફરી real batch
> `B-2026-0001`/real material lot `LOT-API-2603` ના live data સામે curl + frontend બંનેથી ચકાસેલ —
> `node_type=batch` હવે `[]` નથી આપતું કારણ dropdown પોતે જ `drug_batch` મોકલે છે; edges table માં real
> `CONSUMED_IN 50kg`/`DERIVED_FROM 30kg` બંને દેખાય છે.

---

## ૨૨.૧૧ Equipment / Devices

> **વધુ વિગત માટે:** [04_Equipment_Devices_Gujarati.md](04_Equipment_Devices_Gujarati.md) — master data
> ફોર્મ fields, permission list ત્યાં પણ છે; નીચે આ module ની own explanation + live-verified data છે.

**શું છે અને શા માટે જરૂરી:** દરેક equipment asset ની "use કરવા માટે લાયક છે કે નહીં" — qualified,
calibrated, maintenance-clear, hold પર નથી — એ એક જ જગ્યાએ ચેક કરવાની જરૂર પડે (Cleaning, Line
Clearance, EM, Aseptic બધા આ જ ચેક reuse કરે).

**આ module ની ૪ entity, અને દરેક શા માટે જોઈએ:**

| Entity | શું રેકોર્ડ કરે | કેમ અલગ |
|---|---|---|
| **Equipment Asset** | Equipment code, class, state (INSTALLED/VERIFICATION/OUT_OF_SERVICE/RETIRED), hold status | Asset પોતે — identity + lifecycle state |
| **Equipment Calibration** | ક્યારે calibrate થયું, કોના standard સામે, next due date | Calibration નો પોતાનો due-date cycle છે — asset ની lifecycle થી અલગ ટ્રૅક કરવું પડે |
| **Maintenance Work Order** | Scheduled/breakdown maintenance, parts/work performed, change-control link (critical modification માટે) | Maintenance history ઓડિટ ટ્રેલ પોતાનો — qualification ને અસર કરે પણ અલગ entity |
| **Equipment Use Log** | કયા batch/step માં, ક્યારે વપરાયું (reserve/release સાથે) | Traceability: "આ batch ક્યા equipment પર ચાલ્યું" — asset ની પોતાની state થી અલગ, historical record |

`Equipment Area` (cleanroom/warehouse/QC lab ગ્રેડ) એ **cleaning module માં defined** shared master છે
(`cleaning_models.py`) — Equipment, EM, Aseptic, Line Clearance, DDCP બધા આ જ વાપરે (doc #૨૨.૧ cross-
reference).

**બીજા modules સાથે જોડાણ:**
- `get_eligibility(asset_id)` — qualified + calibrated + maintenance-clear + not-on-hold ચેક કરે.
  **Line Clearance** અને **Aseptic Operation** બંને આ function call કરે.
- `cleanliness_status` field — Cleaning module જ (doc #૨૨.૧) એને update કરે.
- `EquipmentArea` — **EM** (`EmLocation.area_id`), **Aseptic** (`AsepticOperation.area_id`), **Line
  Clearance** — બધા આ જ shared master વાપરે.

---

### 🐛 2026-10-08 live-testing દરમિયાન મળેલ real bug, fix કરેલ

**Equipment ના ૩ read endpoint પર કોઈ role/site check જ નહોતો** — `GET .../eligibility`,
`GET .../history`, `GET /dashboard` ત્રણેય `actor` dependency ધરાવતા (authenticated જોઈએ) પણ
`evaluate_policy()`/site-scope check ક્યારેય call નહોતા કરતા. **2026-10-02 ના "Client Topic 15" fix** એ
બરાબર આ જ ગેપ `/assets`/`/areas` પર fix કર્યો હતો ("કોઈ પણ authenticated actor, કોઈ પણ role, કોઈ પણ
site નું equipment જોઈ શકતું") — પણ એ જ router ના આ ૩ sibling endpoint missed રહી ગયા. **Live
reproduced:** `operator1` (ફક્ત site `T1` પર role ધરાવતો) `/dashboard?site_id=SITE-0001` (જ્યાં role જ
નથી) call કરતાં પહેલાં ડેટા મળી જતું — હવે `403 ROLE_MISSING` મળે છે. **Fix:** ત્રણેય endpoint માં
`evaluate_policy()`/`resolve_site_scope()` ઉમેર્યું (એ જ `equipment_asset.view` permission, Client
Topic 15 ના roles ને already granted — કોઈ નવી permission grant ની જરૂર ના પડી).

**બીજું findings (backend-ready-but-missing-UI, bug નહીં):** `/devices` ના Unit detail માં
`batch_id`/`product_version_id` raw UUID તરીકે દેખાતા — `_resolve_unit_refs()` ઉમેરીને હવે
`batch_number`/`product_code`+`product_name` resolve કરીને દેખાય છે (packaging/release ના જ pattern).

---

### 🐛 2026-10-09 live-testing દરમિયાન મળેલ (real user request) — Devices ને browsable list + real dropdown

**"`/devices` પર browsable list નથી" એ deliberate decision ખોટું saved હતું:** doc #૪.૨/૪.૪ (જુઓ
[04_Equipment_Devices_Gujarati.md](04_Equipment_Devices_Gujarati.md)) એ "Document 12 ના own API list
ની બહાર endpoint invent ના કરવું" reasoning આપીને list endpoint ઉમેરવાનું ખોટું ગણાવ્યું હતું — પણ
**એ જ session માં બાકીના બધા module** (`process_cycle`/`aseptic_operation`/`sterile_filter_use`/
`cleaning_execution`/`line_clearance`) પર બરાબર આ જ "SG-081 read-side precedent" થી list endpoint
ઉમેરાયેલ — Devices ને અપવાદ રાખવાનું કોઈ વાસ્તવિક કારણ નહોતું. **Fix:** નવું `GET /devices/v1/units`
list endpoint ઉમેર્યું (paginated, `site_id`/`batch_id`/`device_lot_id`/`lots_only` filter, search by
serial, `device.view` permission — કોઈ નવી permission ની જરૂર ના પડી) — `/devices` હવે real
browsable DataTable બતાવે છે (by-serial manual lookup form ની જગ્યાએ).

**"Device lot" ફિલ્ડ પણ ખરેખર reference value છે, free text નહીં:** "Lot release readiness" card નું
"Device lot ID" ફિલ્ડ plain text હતું — પણ `device_lot_id` ખરેખર એક real `DeviceUnit` row ની id જ છે
(lot પોતે "serial_number IS NULL" ધરાવતો `device_unit` row છે, DHR-FR-001/002 નું પોતાનું "lot-scope"
ડિઝાઇન — codebase વાંચીને confirm કર્યું). **Fix:** નવા `GET /devices/v1/units?lots_only=true` endpoint
થી backed dropdown (`EntityPickerField`, manual fallback સાથે), label માં `udi_di`/`batch_number`/
`product_code` બતાવીને.

**"Open" button row detail inline card માં ખુલતું, modal માં નહીં (follow-up fix):** DataTable ના
"Open" ક્લિક કર્યા પછી detail table ની નીચે inline Card માં દેખાતું — બીજા બધા list+detail page (Aseptic/
Sterilization/Packaging) માં `Modal` વપરાય છે, Devices એ જ pattern missed હતું. **Fix:** inline `Card`
ને `Modal` (`open`/`onClose`, `large`) થી replace કર્યું — title માં serial/lot + state pill, "Hold unit"
button modal ની અંદર જ.

**"Lot release readiness" raw JSON dump બતાવતું (real design issue):** `<JsonPanel>` સીધો backend ના
`{lot_id, unit_count, blocked_unit_ids, eligible, note}` object ને dump કરતું — કોઈ designed UI નહીં.
**Fix:** `Banner` (eligible/not-eligible ટોન), `FactGrid` (lot/unit count/eligible pill), અને blocked
units નું real `Table` (serial number + HELD pill) — raw `blocked_unit_ids` (UUID list) ની જગ્યાએ.
Backend માં પણ નવું `blocked_units: [{unit_id, serial_number}]` field ઉમેર્યું (`blocked_unit_ids`
backward-compat માટે રાખ્યું, existing test નો ઉપયોગ કરે છે) જેથી UI raw UUID ની જગ્યાએ real serial
number બતાવી શકે.

---

### વાસ્તવિક ડેટા એન્ટ્રી — Testing માટે Copy-Paste કરવા જેવા ઉદાહરણ (2026-10-08 ઉમેરેલ, real live data)

**Equipment eligibility check (`/equipment/EQP-000001`, login: `operator1`):**

```
asset_id: 2b923ca1-2917-4e15-b75e-228f89dd90a8
state: VERIFICATION
eligible: true
reasons: []
```

**Equipment dashboard (site T1):**

```
due_calibration_count: 1
due_maintenance_count: 0
out_of_service: []
```

**Cross-site rejection (bug ના fix ની live proof):** `operator1` (role ફક્ત site `T1` પર) → site
`SITE-0001` નું dashboard માંગે → `403 ROLE_MISSING: "Actor holds no role at this scope"`.

**Device unit lookup (`/devices`, login: `operator1`):** live seeded ૨ device "lot" (બંનેનો
`serial_number` ખાલી — seed data ની મર્યાદા) હતા. Live demo માટે real serialized unit lot
`773b2e12-...` નીચે bulk-create કર્યું (`supervisor1`, જે `device.create` ધરાવે):

```
serial_number: "SN-LIVE-VERIFY-001"
device_lot_id: "773b2e12-..."
device_lot_label: "PRD-000001"  (lot ના પોતાના udi_di ના હોવાથી product_code fallback)
batch_number: "B-2026-0001"
product_name: "Metformin 500mg Tablet" (product_code: "PRD-000001")
state: "created"
```

`GET /devices/v1/units?site_id=...&device_lot_id=773b2e12-...` થી આ જ unit scoped મળે છે;
`?q=LIVE-VERIFY` સર્ચ થી પણ એ જ મળે છે (DataTable નું search box આ જ param વાપરે છે).

**Test Cases:**

| Test ID | Steps | Expected Result | Modules Touched |
|---|---|---|---|
| OPS-EQP-01 | Equipment calibration expired — Aseptic readiness check | Equipment signal ineligible — start block | Equipment, Aseptic |
| OPS-EQP-02 | Role ફક્ત site A પર — site B નું eligibility/history/dashboard માંગે | `403 ROLE_MISSING` (bug નો regression test) | Equipment |
| OPS-EQP-03 | Device unit history lookup — batch/product resolved નામ સાથે | raw UUID ની જગ્યાએ `batch_number`/`product_name`/`product_code` દેખાય | Equipment, Device |
| OPS-EQP-04 | `/devices` DataTable ખોલો, serial થી search કરો | Real unit list દેખાય, row click → detail (Bug-૪ regression test — before તો list જ નહોતું) | Device |
| OPS-EQP-05 | "Device lot" dropdown ખોલો (Lot release readiness card) | Real lot list દેખાય (`lots_only=true`), pick → readiness check | Device |
| OPS-EQP-06 | `lots_only=true` વગર list | Lot + serialized unit બંને દેખાય, `device_lot_id` filter સાચું scope કરે | Device |
| OPS-EQP-07 | DataTable row નો "Open" બટન ક્લિક કરો | Modal ખુલે (inline card નહીં), "Hold unit" button modal ની અંદર | Device |
| OPS-EQP-08 | HELD unit ધરાવતા lot નો readiness check | Banner "Not eligible", blocked units table માં real serial number (raw UUID નહીં) દેખાય | Device |

> ✅ **2026-10-09 live-verified (2 rounds):** `GET /devices/v1/units` (unfiltered, `lots_only=true`,
> `device_lot_id=`, `q=`) બધા real seeded + નવા bulk-created unit (`SN-LIVE-VERIFY-001`) સામે curl થી
> ચકાસેલ — `device_lot_label`/`batch_number`/`product_code` બધા સાચા resolve થયા. Modal + designed
> readiness UI પણ real data સામે ચકાસેલ: `SN-LIVE-VERIFY-001` ને `supervisor1` થી hold કર્યું, પછી
> `release-readiness` call કરતાં `blocked_units: [{unit_id, serial_number: "SN-LIVE-VERIFY-001"}]`
> સાચું resolve થયેલ (પહેલાં ફક્ત raw `blocked_unit_ids` UUID list હતી). `pytest tests/test_device.py`
> 11/11.
>
> ✅ **2026-10-08 live-verified:** cross-site rejection અને device unit name-resolution બંને real
> seeded data (site `T1`/`SITE-0001`, batch `B-2026-0001`, device unit `773b2e12-...`) સામે curl થી
> ચકાસેલ — `pytest tests/test_equipment_flow.py` 49/49 (48 existing + 1 નવું cross-site regression
> test) અને `tests/test_device.py` 10/10 unchanged.

---

## ૨૨.૧૨ સારાંશ — Cross-Module Connection Map

```
Equipment/Area ──(cleanliness_status, eligibility)──→ Cleaning, Line Clearance, Aseptic
EM ──(get_area_readiness)──────────────────────────→ Aseptic
Line Clearance ──(get_area_line_clearance_status)──→ Aseptic, DDCP   [Packaging માં NOT wired — gap]
Sterilization ──(get_item_status)──────────────────→ Aseptic
Aseptic ──(readiness_snapshot, requires_deviation)─→ Deviation (manual)
Packaging ──(packaging signals, warning-only)──────→ Release
QA Review ──(completeness, REVIEW_COMPLETE)────────→ Release
Yield & Reconciliation ──(batch summary)───────────→ Release
Material/Batch Execution ──(node/edge create)──────→ Genealogy (write-only producer)
Genealogy ──(view only)─────────────────────────────→ (કોઈ release blocker નહીં — gap SG-055)
Release ──(release_master snapshot)────────────────→ Vault
```

**સૌથી મહત્વના ૨ documented gaps (honest, repeat ના કરવા):**
1. Packaging real Line Clearance status query નથી કરતું — self-attested flag (SG-050/055).
2. Genealogy completeness Release માટે કોઈ blocker નથી (SG-055, 2026-10-09 ફિક્સ — અગાઉ ખોટી રીતે
   "SG-054" cite થયેલું) — invent નથી કરવાનું, confirmed as-is.
