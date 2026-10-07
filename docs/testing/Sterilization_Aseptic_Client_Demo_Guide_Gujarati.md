# Sterilization &amp; Aseptic Operations — Client Demo Guide, શરૂઆતથી છેક Aseptic Assembly સુધી (Gujarati)

**હેતુ:** `Sterilization_Aseptic_Comprehensive_Test_Manual_Gujarati.md` (role-wise, field-by-field exhaustive
manual) જેવું **નથી** — આ story-driven **client demo script** છે, **Meridian Therapeutics Inc.** ની
**MeridiJect™** prefilled-syringe story નું ચાલુ (`DDCP_Client_Demo_Guide_Gujarati.md` જુઓ), આ વખતે drug/
device constituent ને **sterilize** કરવાથી માંડીને **aseptic assembly** સુધીના પગલાં પર focus.

**⚠️ પ્રામાણિકતા નોંધ (CLAUDE.md §5):** આ document માં ડેમો ડેટા fictional છે, હજુ system માં દાખલ કરેલો
નથી — browser માં ખરેખર દરેક સ્ટેપ કરવો પડશે.

**તારીખ:** 2026-09-16 | **Frontend:** `http://88.99.15.183:4101` | **Backend:** `http://88.99.15.183:8010`
| **Site:** `SITE1` | **Password (બધા demo user માટે):** `ChangeMe123!`

**⚠️ Live DB સ્થિતિ (2026-09-16):** આજે જ full database reset થયો (roles/users/site/company/signature-
policy સિવાય બધું ખાલી). **તમે (client/user) પોતે પહેલેથી** `MAT-DRUG-MERIDIZ`/`MAT-DEV-SYR-1ML` materials
અને `LINE-PFS-01` equipment asset ફરી બનાવવાનું શરૂ કરી દીધું છે (live DB માં confirmed) — આ guide એ
existing data ને **touch નથી કરતો**, ફક્ત નવા, અલગ નામના sterilization/aseptic-ચોક્કસ master data
(`AREA-GRADE-A`, `STR-AUTOCLAVE-01`, `ASY-LINE-01`, `STR-PROC-001`, `ASP-PROC-001`) બનાવે છે — તમારા ચાલુ
કામ સાથે collision નહીં થાય. જો `AREA-GRADE-A` પહેલેથી બની ગયું હોય (unique code), એ જ વાપરો, ફરી બનાવવાની
જરૂર નથી.

---

## અનુક્રમણિકા

1. [ડેમો સ્ટોરી — આ phase માં શું થાય છે](#1-ડેમો-સ્ટોરી--આ-phase-માં-શું-થાય-છે)
2. [Setup — Demo Users](#2-setup--demo-users)
3. [Phase 1 — Equipment: Area + Sterilizer + Fill Line (Equipment Administrator)](#3-phase-1--equipment-area--sterilizer--fill-line-equipment-administrator)
4. [Phase 2 — Sterilization Cycle Profile (qa.reviewer authors)](#4-phase-2--sterilization-cycle-profile-qareviewer-authors)
5. [Phase 3 — Sterilization Cycle: Create → Start → Data → Review](#5-phase-3--sterilization-cycle-create--start--data--review)
6. [Phase 4 — Sterile Filtration: Install → Integrity → Complete](#6-phase-4--sterile-filtration-install--integrity--complete)
7. [Phase 5 — Line Clearance (Aseptic ની પૂર્વશરત)](#7-phase-5--line-clearance-aseptic-ની-પૂર્વશરત)
8. [Phase 6 — Sterile Process Profile (Aseptic Supervisor)](#8-phase-6--sterile-process-profile-aseptic-supervisor)
9. [Phase 7 — Aseptic Operation: Create → Start → Intervention → Event → Complete](#9-phase-7--aseptic-operation-create--start--intervention--event--complete)
10. [Phase 8 — DDCP સાથે જોડાણ (આગળનું પગલું)](#10-phase-8--ddcp-સાથે-જોડાણ-આગળનું-પગલું)
11. [Client Demo Moments — શું emphasize કરવું](#11-client-demo-moments--શું-emphasize-કરવું)
12. [જાણીતી મર્યાદાઓ](#12-જાણીતી-મર્યાદાઓ)

---

## 1. ડેમો સ્ટોરી — આ phase માં શું થાય છે

MeridiJect™ prefilled syringe ના 2 constituent — **needle** (device) અને **drug** (biologic) — DDCP profile
પ્રમાણે batch માં જોડાતા પહેલાં ચોક્કસ સ્થિતિમાં હોવા જોઈએ (`required_state = STERILIZED`/
`READY_TO_USE`). આ phase બતાવે છે **કેવી રીતે** એ સ્થિતિ ખરેખર achieve થાય છે:

```
Needle component → Steam autoclave sterilization cycle → independent QA review → "eligible" sterile status
                                                                                          ↓
                                          Sterile input તરીકે → Aseptic assembly operation (Grade A area)
                                                                                          ↓
                                          DDCP constituent handoff → "Sterilization reference" = આ જ load item ID
```

---

## 2. Setup — Demo Users

બધા seeded, DB reset પછી પણ યથાવત્ (roles/users reset માંથી excluded હતા) — password `ChangeMe123!`:

| Username | Role | આ ડેમોમાં કરે છે |
|---|---|---|
| `equipment.admin` | Equipment Administrator | Area/Asset બનાવે, qualify/calibrate કરે |
| `sterilization.operator` | Sterilization Operator | Cycle create/start/data, filter install/integrity/complete |
| `qa.reviewer` | QA Reviewer | Cycle review (accept — **સહી**, independent) |
| `sanitation.operator` | Sanitation Operator | Line clearance (aseptic ની પૂર્વશરત) |
| `aseptic.supervisor` | Aseptic Supervisor | Sterile process profile, Operation start (**સહી**) |
| `aseptic.operator` | Aseptic Operator | Operation create, intervention, event, complete (**સહી**) |

---

## 3. Phase 1 — Equipment: Area + Sterilizer + Fill Line (Equipment Administrator)

`equipment.admin` → `/equipment`.

### 3.1 New area

| Field | Data |
|---|---|
| Area code | `AREA-GRADE-A` |
| Area type | `cleanroom` |
| Classification | `ISO_5` |
| Criticality | `critical` |
| Cleanliness status | ખાલી (પછીથી cleaning execution/line clearance update કરશે) |

### 3.2 New asset — Sterilizer

| Field | Data |
|---|---|
| Equipment code | `STR-AUTOCLAVE-01` |
| Manufacturer | `Getinge` |
| Model | `GEA-6612ER` |
| Serial no. | `GEA-2026-00147` |

### 3.3 New asset — Aseptic Fill/Assembly Line

| Field | Data |
|---|---|
| Equipment code | `ASY-LINE-01` |
| Manufacturer | `Bausch+Ströbel` |
| Model | `VarioSys VFS`| 
| Serial no. | `BS-2026-00812` |

### 3.4 બંને asset ને Qualify (equipment detail page → "Qualify")

| Field | Data |
|---|---|
| Qualification status | `qualified` |
| Qualified | Yes |
| Effective date | આજ |
| Expiry date | +2 વર્ષ |

### 3.5 બંને asset ને Calibrate

| Field | Data |
|---|---|
| Performed date | આજ |
| Next due date | +1 વર્ષ |
| Result | `pass` |
| Standard reference | `NIST-TRACE-2026` |

**⚠️ આ 2 પગલાં વગર (Qualify+Calibrate) સ્ટેપ 5 નું cycle create `422 STERILIZER_INELIGIBLE` આપશે** — code
verified check, skip ના કરવું.

---

## 4. Phase 2 — Sterilization Cycle Profile (`qa.reviewer` authors)

**✅ 2026-09-16 RESOLVED (SG-203) — હવે real create UI/API છે.** પહેલાં Sterilization Cycle Profile ને
Aseptic ના "Sterile process profile" (§8) જેવો create endpoint જ નહોતો — ફક્ત `GET
/sterilization/v1/profiles` (picker), migrator role થી direct SQL insert જ એકમાત્ર રસ્તો હતો.
**Project-owner-directed, પૂછીને:** (1) profile ને **QA Reviewer** (Sterilization Operator નહીં) author
કરે — જે role પછીથી cycle data independently review કરે એ જ role spec પણ define કરે, "કોણ define કરે ≠
કોણ execute કરે" split જાળવવા; (2) **direct-to-RELEASED** (aseptic ના §8.1 જેવું જ).

`qa.reviewer` login → `/sterilization` → **"New sterilization cycle profile"** button:

| Field | Data | ફરજિયાત? |
|---|---|---|
| Profile number | `STR-PROC-001` | ✅ |
| Version no. | `1` | ✅ |
| Process type | `steam_autoclave` (dropdown) | ✅ |
| Validation reference | `PQ-STR-2026-004` | — |
| Sterile status validity (hours) | `720` (= 30 દિવસ) | — |
| Critical parameters (kv, flat) | `temperature_c_min` → `121`; `hold_minutes_min` → `15` | — |
| Indicator requirements (kv) | `biological_indicator` → `required` | — |

Submit → સીધું state **RELEASED** — "Cycle profile version" dropdown માં `STR-PROC-001 v1 -
steam_autoclave` તરત દેખાશે. **⚠️ `sterilization.operator` થી આ બટન કરવાનો પ્રયત્ન** → button જ ના
દેખાય (`canCreateCycleProfile`), raw API call → `403 ROLE_MISSING` (code-verified negative test,
`test_create_process_cycle_profile_version_requires_role`).

---

## 5. Phase 3 — Sterilization Cycle: Create → Start → Data → Review

**કોણ:** `sterilization.operator` (create/start/data) → `qa.reviewer` (review, **અલગ user**). **ક્યાં:**
`/sterilization`.

### 5.1 Create process cycle

| Field | Data |
|---|---|
| Process type | `steam_autoclave` |
| Equipment | `STR-AUTOCLAVE-01` |
| Cycle profile version | `STR-PROC-001 v1` |
| Batch | ખાલી (optional — batch હજુ નથી બન્યો આ ડેમોમાં) |
| Load items — Row 1 | Item type `component`; Item reference (manual — હજુ કોઈ material lot dropdown માં નથી) `MJ-NEEDLE-LOT-2701`; Position `Tray 1` |

Submit → state **DRAFT**.

### 5.2 Start cycle (સહી)

Button "Start cycle (sign)" → password ફરી → state **CYCLE_STARTED**.

### 5.3 Record cycle data (2 વાર — running, પછી final)

**પહેલી વાર (running data):**

| Field | Data |
|---|---|
| Controller cycle ID | `CTRL-STR-2701-01` |
| Parameter data | `temperature_c` → `121.4`; `pressure_bar` → `2.05` |
| Alarm data | ખાલી |
| Indicator results | ખાલી |
| Critical alarm | No |
| Final batch of data | No |

Submit → state **CYCLE_RUNNING**.

**બીજી વાર (final data):**

| Field | Data |
|---|---|
| Controller cycle ID | `CTRL-STR-2701-01` |
| Parameter data | `hold_minutes` → `16` |
| Indicator results | `BI_1` → `negative` |
| Critical alarm | No |
| Final batch of data | **Yes** |

Submit → state **REVIEW_PENDING**.

### 5.4 Review (સહી, independent — qa.reviewer)

`qa.reviewer` login → cycle ખોલો → "Review (sign)" → Decision `Accept` → password → state **ACCEPTED**,
load item `MJ-NEEDLE-LOT-2701` નો `sterile_status = eligible` (+ expiry, profile ના
`sterile_status_validity_hours=720` = 30 દિવસ પરથી).

**Client demo moment:** `sterilization.operator` (જેણે start કર્યું) થી review કરવાનો પ્રયત્ન કરો —
**fail થશે** (SIG-FR-018, same-actor block). `qa.reviewer` (અલગ user) → succeed.

---

## 6. Phase 4 — Sterile Filtration: Install → Integrity → Complete

**કોણ:** `sterilization.operator`. **ક્યાં:** `/sterilization` → "Sterile filtration" section.

### 6.1 Install a filter

| Field | Data |
|---|---|
| Site ID | (hint માં દેખાતું resolved ID copy કરો) |
| Filter serial | `FLT-MJ-2701-01` |
| Filter lot | `FLT-LOT-2601` |
| Filter type | `0.22 micron PVDF` |
| Manufacturer | `Millipore` |
| Batch | ખાલી |
| Sterilization cycle ID | ખાલી (optional) |
| Housing location | `Fill suite A, Housing 2` |
| Direction | `forward` |

Submit → state **INSTALLED**.

### 6.2 Integrity test — Pre-use

| Field | Data |
|---|---|
| Filter use ID | (§6.1 થી copy) |
| Expected version | `1` |
| Phase | `Pre-use` |
| Result | `Pass` |
| Test reference | `method` → `bubble_point`; `bar` → `3.2` |

Submit → state **IN_USE**.

### 6.3 Integrity test — Post-use

| Field | Data |
|---|---|
| Filter use ID | એ જ |
| Expected version | `2` |
| Phase | `Post-use` |
| Result | `Pass` |
| Test reference | `bar` → `3.15` |

Submit → state **POST_USE_TEST**.

### 6.4 Complete filter use (સહી)

| Field | Data |
|---|---|
| Filter use ID | એ જ |
| Expected version | `3` |
| Process parameters | `filtered_volume_l` → `12.5` |
| Reason | `Routine bulk drug filtration, MeridiJect batch prep` |

Submit → password → state **ACCEPTED**.

---

## 7. Phase 5 — Line Clearance (Aseptic ની પૂર્વશરત)

**કોણ:** `sanitation.operator`. **ક્યાં:** `/line-clearance`. Aseptic operation start (§9.2) ને
`AREA-GRADE-A` નું line clearance **CLEARED** જોઈએ, નહીં તો `409 ASEPTIC_AREA_NOT_READY`.

| Field | Data |
|---|---|
| Equipment area/line | `AREA-GRADE-A` |
| Previous batch | ખાલી |
| Next batch | ખાલી |
| Checklist items | ખાલી/optional |

"Start" → "Complete (sign)" → `Passed = Yes` → password → area cleared.

---

## 8. Phase 6 — Sterile Process Profile (Aseptic Supervisor)

**કોણ:** `aseptic.supervisor`. **ક્યાં:** `/aseptic` → "New sterile process profile".

| Field | Data |
|---|---|
| Profile number | `ASP-PROC-001` |
| Version no. | `1` |
| Required area classification | `ISO_5` (AREA-GRADE-A સાથે match) |
| Validation reference | `MF-MERIDIJECT-2026-01` |

Submit → સીધું state **RELEASED** (no draft/review stage — spec પ્રમાણે જ).

---

## 9. Phase 7 — Aseptic Operation: Create → Start → Intervention → Event → Complete

**કોણ:** `aseptic.operator` (create/intervention/event/complete) → `aseptic.supervisor` (start, **અલગ
role**). **ક્યાં:** `/aseptic`.

### 9.1 Create aseptic operation

| Field | Data |
|---|---|
| Area | `AREA-GRADE-A` |
| Aseptic profile version | `ASP-PROC-001 v1` |
| Batch | ખાલી |
| Batch step ID | ખાલી |
| Sterile input references — Row 1 | Sterile item ID — **✅ 2026-09-16 હવે real dropdown** (`GET /sterilization/v1/items/eligible`), §5.4 નો ACCEPTED load item (દા.ત. `LOT-DEV-2601 (component) — steam_autoclave cycle, eligible until ...`) directly list માં દેખાશે |
| Media fill reference | ખાલી (media fill run નથી, routine batch) |

Submit → state **PREPARATION**.

### 9.2 Start operation (સહી, ફક્ત Aseptic Supervisor)

`aseptic.supervisor` login → operation ખોલો → readiness ચેક પાસ થવી જોઈએ (§7 નું line clearance,
§3.4 નું equipment qualification, §5.4 નું sterile input eligibility) → "Start operation (sign)" →
password → state **EXECUTION**.

**Client demo moment:** `aseptic.operator` (પોતે) થી start કરવાનો પ્રયત્ન → **fail** (`403 ROLE_MISSING`
— Operator ને `start` permission જ નથી, ફક્ત Supervisor ને). SoD literally UI/backend બંનેમાં block થાય.

### 9.3 Record intervention (planned, routine)

| Field | Data |
|---|---|
| Intervention type | `routine` |
| Planned | `Yes` |
| Location | `Fill line A, Station 2` |
| Reason | ખાલી (planned=Yes એટલે ફરજિયાત નથી) |
| Impacted unit scope | `unitRange` → `1-50` |

### 9.4 Record event (info)

| Field | Data |
|---|---|
| Event type | `gowning_check` |
| Source | `line_supervisor` |
| Severity | `Info` |
| Additional details | `result` → `pass` |

### 9.5 Complete operation (સહી)

| Field | Data |
|---|---|
| Critical | `false` |
| QC test order ID | ખાલી |
| QC result ID | ખાલી |
| Reason | ખાલી |

Submit → password → state **ASEPTIC_COMPLETE**.

---

## 10. Phase 8 — DDCP સાથે જોડાણ (આગળનું પગલું)

હવે `MJ-NEEDLE-LOT-2701` (§5 થી ACCEPTED, sterile eligible) DDCP profile ના constituent requirement ને
satisfy કરે છે. `DDCP_Client_Demo_Guide_Gujarati.md` ના Phase 8 (constituent handoff Accept) પર જાઓ,
"Sterilization/depyrogenation reference" field માં **આ load item ID** પેસ્ટ કરો — Comprehensive Test
Manual §9 નું cross-check literally live થશે: `sterile_status="eligible"` હોવાથી handoff pass થશે.

---

## 11. Client Demo Moments — શું emphasize કરવું

1. **Independent review** — §5.4, same-actor cycle review block.
2. **SoD: Operator ≠ Supervisor** — §9.2, aseptic start ફક્ત Supervisor ને.
3. **Readiness composition** — §9.2 પહેલાં line clearance/qualification ના હોય તો start ના જ થાય —
   4 જુદા module (EM, Line Clearance, Equipment, Sterilization) ની live composition, ફક્ત 1 flag નહીં.
4. **Reprocessing control** — (optional demo) એ જ item_reference (`MJ-NEEDLE-LOT-2701`) સાથે નવું cycle
   બનાવો, પણ §5 ના cycle ને reject કરો (review માં Decision=Reject) પહેલા — બીજી વાર create કરવાનો
   પ્રયત્ન → `409 REPROCESSING_AUTHORIZATION_REQUIRED`, `reprocessing_authorization_ref` આપ્યા વગર.
5. **HOLD = કાયમી block** — Intervention ને Planned=**No** કરીને ફરી try કરો (નવી operation પર) →
   operation HOLD માં જાય → Complete કરવાનો પ્રયત્ન → કાયમ માટે `422` (Comprehensive Manual §14 #5) —
   client ને પ્રામાણિકપણે કહેવું, આ roadmap item છે.

---

## 12. જાણીતી મર્યાદાઓ

Comprehensive Test Manual §14 ની જ યાદી — સૌથી અગત્યની આ demo માટે:
- ~~Sterilization cycle profile ને UI/API create endpoint નથી~~ — **✅ RESOLVED 2026-09-16 (SG-203)** —
  `qa.reviewer` હવે `/sterilization` → "New sterilization cycle profile" થી real profile બનાવી શકે (§4).
- ~~Sterile input reference (§9.1) dropdown નથી~~ — **✅ RESOLVED 2026-09-16** — હવે real dropdown (§9.1).
  §5.1 નું filter/load-item reference (cycle create form ની અંદર) હજુ manual ID જ છે (item_reference free
  text captured, backend enforce નથી કરતું — genuinely free-form, picker ની જરૂર જ નથી).
- Aseptic HOLD state કાયમી block (§11 #5).
- Personnel qualification ક્યારેય check નથી થતું.

*આ document code થી verified (2026-09-16) — સંપૂર્ણ field/RBAC/state-machine વિગત:
`Sterilization_Aseptic_Comprehensive_Test_Manual_Gujarati.md`. Demo data fictional; roles/endpoints/
signature-requirements real.*
