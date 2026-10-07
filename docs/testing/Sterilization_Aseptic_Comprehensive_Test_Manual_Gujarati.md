# Sterilization &amp; Aseptic Operations — સંપૂર્ણ Functional Test Manual (Master Document, Gujarati)

**દસ્તાવેજ સંદર્ભ:** Document 42 (SPEC-EQP-005, Sterilization/CIP-SIP/Sterile Filtration) + Document 40
(SPEC-EQP-004, Sterile/Aseptic Manufacturing Operations) — બંને Document 38 (Equipment/Calibration) અને
Document 41 (EM) અને Document 39 (Line Clearance) સાથે cross-referenced.
**મોડ્યુલ:** `services/gxp-api/app/modules/equipment/{sterilization,aseptic}_{router,commands,models}.py`
(backend); `frontend/src/app/{sterilization,aseptic}/page.tsx` (UI)
**તારીખ:** 2026-09-16 | **Format:** `docs/testing/DDCP_Comprehensive_Test_Manual_Gujarati.md` જેવો જ — code
થી verified, કંઈ પણ invent નથી કરેલું (CLAUDE.md §5).

**⚠️ Live DB નોંધ (2026-09-16):** આજે જ database નો full reset થયો છે (roles/users/site/company અને
signature-policy/SoD floor સિવાય **બધું** ખાલી) — એટલે `equipment.equipment_areas`,
`equipment.equipment_assets` (ફક્ત 1 leftover row, `LINE-PFS-01`, `INSTALLED` state — qualified નથી,
ignore કરવો), `process_cycle_profile_versions`, `aseptic_profile_versions` બધા **0 row** થી શરૂ થાય છે.
આ manual master data-independent રીતે લખાયેલો છે (field-by-field, real data literal રીતે hardcode નથી
કરેલું) — concrete data-entry sequence માટે `Sterilization_Aseptic_Client_Demo_Guide_Gujarati.md` જુઓ.

---

## અનુક્રમણિકા

**Part A — Foundation**
1. [Sterilization અને Aseptic Operations એટલે શું, અને શા માટે regulated છે](#1-sterilization-અને-aseptic-operations-એટલે-શું-અને-શા-માટે-regulated-છે)
2. [Access, Login, Roles — Setup](#2-access-login-roles--setup)
3. [UI કેવી રીતે કામ કરે છે (Developer-level Mechanics)](#3-ui-કેવી-રીતે-કામ-કરે-છે-developer-level-mechanics)

**Part B — Role-Wise Action Performance (મુખ્ય ભાગ)**
4. [પૂર્વશરત — Equipment Administrator: Asset/Area બનાવવા + Qualify/Calibrate](#4-પૂર્વશરત--equipment-administrator-assetarea-બનાવવા--qualifycalibrate)
5. [Role: Sterilization Operator — Process Cycle + Sterile Filtration](#5-role-sterilization-operator--process-cycle--sterile-filtration)
6. [Role: QA Reviewer / QC Reviewer — Process Cycle Review (Independent)](#6-role-qa-reviewer--qc-reviewer--process-cycle-review-independent)
7. [Role: Aseptic Supervisor — Sterile Process Profile + Operation Start](#7-role-aseptic-supervisor--sterile-process-profile--operation-start)
8. [Role: Aseptic Operator — Operation Create, Intervention, Event, Complete](#8-role-aseptic-operator--operation-create-intervention-event-complete)
9. [Cross-Module: DDCP ના Constituent Handoff સાથે સંબંધ (PFS-FR-005)](#9-cross-module-ddcp-ના-constituent-handoff-સાથે-સંબંધ-pfs-fr-005)

**Part C — Reference**
10. [State Machine સંદર્ભ (બધા 4 entity)](#10-state-machine-સંદર્ભ-બધા-4-entity)
11. [RBAC / Signature નકશો — સંપૂર્ણ ટેબલ](#11-rbac--signature-નકશો--સંપૂર્ણ-ટેબલ)
12. [Negative / Error Test Cases](#12-negative--error-test-cases)
13. [Error Code શબ્દકોશ](#13-error-code-શબ્દકોશ)
14. [જાણીતી મર્યાદાઓ (પ્રામાણિકતા)](#14-જાણીતી-મર્યાદાઓ-પ્રામાણિકતા)
15. [Traceability Sheet](#15-traceability-sheet)

---

## 1. Sterilization અને Aseptic Operations એટલે શું, અને શા માટે regulated છે

**Sterilization (Document 42)** = કોઈ પણ વસ્તુ (component, garment, filter, bulk drug solution) ને
**સંપૂર્ણપણે જીવાણુ-મુક્ત** કરવાની validated process — autoclave (વરાળ/steam), dry heat, gas, radiation,
CIP (Clean-in-Place), SIP (Sterilize-in-Place), અથવા sterile filtration (0.22 micron ફિલ્ટર થી ગાળીને).
**Sterile Filtration** ને અલગ tracking છે કારણ filter પોતે "sterilize" નથી થતું — filter **integrity test**
(પહેલા અને પછી) સાબિત કરે કે filter એ ખરેખર બધા જીવાણુ રોકી લીધા.

**Aseptic Operations (Document 40)** = **પહેલેથી sterile** components/materials ને **sterile environment**
(Grade A cleanroom) માં ભેગા કરવાની/ભરવાની process — દા.ત. sterile syringe barrel + sterile needle +
sterile drug solution ને ભેગા કરવા, વચ્ચે કંઈ પણ contaminate ના થવું જોઈએ. Sterilization "વસ્તુ sterile
બનાવે છે"; Aseptic Operations "sterile વસ્તુઓ ને sterile રાખીને ભેગી કરે છે" — બંને **અલગ, ક્રમબદ્ધ**
પગલાં છે (પહેલા sterilize, પછી aseptic assembly).

**શા માટે regulated:** Injectable/sterile પ્રોડક્ટમાં કોઈ પણ જીવાણુ દર્દીના લોહીમાં સીધું જાય — non-sterile
oral tablet કરતાં risk ઘણો વધારે. એટલે:
- દરેક sterilization cycle નું data (temperature/pressure/time, biological/chemical indicator result)
  **independent reviewer** એ ચેક કરવું પડે (operator પોતે accept ના કરી શકે — SIG-FR-018).
- Aseptic operation શરૂ કરતાં પહેલાં **readiness composition** ચેક થાય — area (EM સ્ટેટસ), line clearance,
  equipment eligibility, sterile input status — **બધું** તૈયાર હોય તો જ start થાય.
- Filter ને 2 વાર integrity test કરવો પડે (pre-use અને post-use) — filter પોતે fail થયું હોય તો ખબર પડે.

---

## 2. Access, Login, Roles — Setup

### 2.1 Browser Access, Login

`http://88.99.15.183:4101` (frontend), `http://88.99.15.183:8010` (backend) — Site `SITE1`, password બધા
demo user માટે `ChangeMe123!` (પહેલેથી seeded, DB reset પછી પણ **યથાવત્** — roles/users reset માંથી
excluded હતા).

### 2.2 Roles — કોણ શું કરી શકે (code-verified `scripts/seed.py`)

| Role | આ 2 module માં કરે છે | Permission codes |
|---|---|---|
| **Sterilization Operator** | Process cycle create/start/data-record; filter install/integrity-test/complete | `process_cycle.create`, `.start`, `sterile_filter_use.create`, `.complete` |
| **QA Reviewer** | Process cycle review (accept/reject — **સહી**); create/start પણ કરી શકે (overlap) | `process_cycle.review`, `.create`, `.start` |
| **QC Reviewer** | Process cycle review (accept/reject — **સહી**) | `process_cycle.review` |
| **Aseptic Operator** | Operation create, intervention record, event record, complete (**સહી**) | `aseptic_operation.create`, `.intervention`, `.event`, `.complete` |
| **Aseptic Supervisor** | Operation start (**સહી**); sterile process profile create/supersede | `aseptic_operation.start`, `aseptic_profile_version.create` |
| **Equipment Administrator** | Equipment asset/area create, qualify, calibrate, maintain, hold | Document 38 codes (`equipment_asset.create/.qualify/.calibrate/...`) |
| **Sanitation Operator** | Line clearance (aseptic readiness ની પૂર્વશરત) | `line_clearance.create/.complete` |
| **Admin** | બધું | બધા ઉપરના codes |

**Demo users (પહેલેથી seed, live DB માં confirmed 2026-09-16):** `sterilization.operator`,
`aseptic.operator`, `aseptic.supervisor`, `equipment.admin`, `qa.reviewer`, `qc.reviewer`,
`sanitation.operator` — બધા `ChangeMe123!`, `SITE1`. **⚠️ અગત્યનું ડિઝાઇન નોંધ:** `Aseptic Operator` ને
`start` permission **નથી** (ફક્ત `Aseptic Supervisor` ને) — "કોણ setup કરે" (Operator) અને "કોણ start
કરવાની મંજૂરી આપે" (Supervisor) નો SoD split, DDCP ના Engineer/Operator split જેવો જ.

### 2.3 Master data prerequisites (code-verified, ડિફોલ્ટ 0)

આ 2 module શરૂ કરતાં પહેલાં આ master data જોઈએ (§4 જુઓ, પૂરું data-entry sequence):
1. **Equipment Area** (`/equipment` → "New area") — sterilization equipment ને area જોડાણ optional છે,
   પણ aseptic operation ને **ફરજિયાત** area જોઈએ (`AsepticOperation.area_id` NOT NULL).
2. **Equipment Asset** (`/equipment` → "New asset") — sterilizer/autoclave equipment; qualify + calibrate
   કરવું પડે, નહીં તો cycle create `STERILIZER_INELIGIBLE` (422) આપશે.
3. **Sterilization Cycle Profile** (`/sterilization/v1/profiles` — **⚠️ UI માં create form નથી**, ફક્ત
   `GET` list picker; profile seed-only master data છે, §14 #1 જુઓ).
4. **Sterile Process Profile** (aseptic — `/aseptic` → "New sterile process profile", UI માં real create
   form **છે**, `Aseptic Supervisor`/Admin).

---

## 3. UI કેવી રીતે કામ કરે છે (Developer-level Mechanics)

### 3.1 2 પાનાં, 2 સાવ અલગ shape

`/sterilization` અને `/aseptic` — બંને `OpsRecordPage` shared shell વાપરે છે (list + create + signed
transitions) પણ 2 મહત્વના ફરક:

| | `/sterilization` | `/aseptic` |
|---|---|---|
| Record list | `CycleListCard` — real `DataTable`, paginated, search | કોઈ list table નથી — ફક્ત inline "ID થી lookup" box |
| Detail view | Modal (`detailInModal`) | Inline (page પર જ ખૂલે) |
| Master data create | નથી (profile seed-only) | "New sterile process profile" button (`headerAction`, ફક્ત Aseptic Supervisor/Admin ને) |
| Extra section | `FiltrationSection` — સાવ અલગ `FormConsole`/`SignedJsonForm` pair (filter install/integrity/complete, અલગ API root `/filtration/v1`) | નથી |

**કેમ filtration અલગ છે:** Sterile filter use ના mutation 2 જુદા API prefix (`/filtration/v1/filters/...`
અને `/filtration/v1/uses/...`) પર છે, ભલે એ જ DB row (`SterileFilterUse`) અપડેટ કરે — `OpsRecordPage` ને
1 જ `apiRoot` ધારેલો છે, એટલે filtration એ shared shell ના બદલે પોતાનો `FormConsole` + `SignedJsonForm`
pair વાપરે છે (code comment, ડિલિબરેટ, bug નથી).

### 3.2 Field control types — શું dropdown છે, શું raw text

| Field | ક્યાં | Control | નોંધ |
|---|---|---|---|
| Equipment | Sterilization create | dropdown (`equipmentSelect`) | ✅ real |
| Cycle profile version | Sterilization create | dropdown (`sterilizationProfileSelect`) | ✅ real, RELEASED-only |
| Batch | બંને create form | dropdown (`batchSelect`) | ✅ real, optional |
| Load item reference | Sterilization create (repeat row) | dropdown (`materialLotSelect`, `materialLotCodes`) | ✅ real, manual fallback |
| Load item type/position | Sterilization create (repeat row) | raw text | free-form, backend enforce નથી કરતું |
| Area | Aseptic create | dropdown (`areaSelect`) | ✅ real |
| Aseptic profile version | Aseptic create | dropdown (`asepticProfileSelect`) | ✅ real, RELEASED-only |
| **Sterile item ID** | Aseptic create (repeat row, `sterile_input_refs[].item_id`) | **raw text, કોઈ dropdown નથી** | ⚠️ sterilization ના load-item picker જેવો picker **નથી** — §14 #2 |
| Batch step ID | Aseptic create | raw text | કોઈ dropdown નથી |
| Critical (Complete operation) | Aseptic complete transition | **raw text `"true"/"false"`** | ⚠️ bool Select નથી, sterilization ના `critical_alarm`/`final` થી અલગ UX — §14 #3 |
| Filter serial/lot/type/manufacturer/housing/direction | Filtration install | raw text | કોઈ master list નથી (physical filter identity, free text વાજબી) |
| Site ID (Filtration install) | Filtration install | raw text, hint માં resolved site ID દેખાય | manually type કરવું, પણ ક્યાં જોવું ખબર પડે |

### 3.3 Signed actions — password ફરી ક્યારે માંગે

| Page | Action | Signed? |
|---|---|---|
| Sterilization | Start cycle | ✅ સહી |
| Sterilization | Record cycle data | ❌ unsigned |
| Sterilization | Review (accept/reject) | ✅ સહી, **independent** |
| Filtration | Install filter | ❌ unsigned |
| Filtration | Integrity test | ❌ unsigned |
| Filtration | Complete filter use | ✅ સહી |
| Aseptic | Create profile / Supersede profile | ❌ unsigned (spec માં કોઈ draft/review stage જ નથી) |
| Aseptic | Create operation | ❌ unsigned |
| Aseptic | Start operation | ✅ સહી |
| Aseptic | Record intervention | ❌ unsigned |
| Aseptic | Record event | ❌ unsigned |
| Aseptic | Complete operation | ✅ સહી |

---

## 4. પૂર્વશરત — Equipment Administrator: Asset/Area બનાવવા + Qualify/Calibrate

**કોણ:** `equipment.admin` (Equipment Administrator role). **ક્યાં:** `/equipment`, `/equipment/[id]`.

### 4.1 New area (`/equipment` → "New area")

| Field | ફરજિયાત? | નોંધ |
|---|---|---|
| Area code | ✅ | Site-wide unique |
| Area type | — | free text, દા.ત. `fill_suite`, `gowning_room`, `warehouse` |
| Classification | — | Cleanroom grade — દા.ત. `ISO_5`, `ISO_7` (aseptic profile ના `required_area_classification` સાથે match કરવું) |
| Criticality | — | free text, `high`/`medium`/`low` |
| Cleanliness status | — | free text — cleaning execution/DDCP પછીથી update કરી શકે |

### 4.2 New asset (`/equipment` → "New asset")

| Field | ફરજિયાત? |
|---|---|
| Equipment code | ✅ |
| Manufacturer / Model / Serial no. | — |
| Firmware version | — |

### 4.3 Qualify (equipment detail page)

| Field | ફરજિયાત? |
|---|---|
| Qualification status | ✅ |
| Qualified (checkbox) | — |
| Effective date / Expiry date | — |

**⚠️ Sterilization cycle create ને equipment `qualification_status == "qualified"` જ જોઈએ** (code:
`equipment_commands._ineligibility_reasons()`, most-specific-first check) — qualify ના કર્યું હોય તો
`STERILIZER_INELIGIBLE` (422).

### 4.4 Calibrate

| Field | ફરજિયાત? |
|---|---|
| Performed date | ✅ |
| Next due date | ✅ |
| Result | ✅ |
| Standard reference | — |
| Frequency (days) | — |
| Reviewer | — |

**Eligibility check ના જ ભાગ:** `calibration_status == "oot"` → `CALIBRATION_OOT_IMPACT_REQUIRED`;
overdue/expired calibration → `CALIBRATION_EXPIRED`. Sterilization અને aseptic બંને (`_compute_readiness`
દ્વારા equipment_ids પર) આ જ check reuse કરે છે.

---

## 5. Role: Sterilization Operator — Process Cycle + Sterile Filtration

**Doc:** 42 (SPEC-EQP-005). **ક્યાં:** `/sterilization`.

### 5.0 પૂર્વશરત — Cycle Profile Author: QA Reviewer (✅ 2026-09-16, SG-203)

**Backend:** `POST /sterilization/v1/profiles` (`process_cycle_profile_version.create`, unsigned,
direct-to-RELEASED). **કોણ:** `qa.reviewer`/Admin **જ** — `Sterilization Operator` ને આ permission નથી
(deliberate split: જે role પછીથી cycle data independently review કરે એ જ role spec define કરે,
Sterilization Operator નહીં — SG-203 ના resolution નોંધ જુઓ).

**⚠️ 2026-09-16, live confusion જોવા મળી — "Sterile process profile" (Product Master) ≠ "Sterilization
cycle profile" (અહીં):** આ 2 નામ લગભગ સરખા લાગે છે પણ **સાવ 2 જુદા table/record છે** —

| | Sterilization Cycle Profile (અહીં, §5.0) | Sterile Process Profile (Product Master ને જોઈએ) |
|---|---|---|
| Document | 42 | 40 |
| DB table | `equipment.process_cycle_profile_versions` | `equipment.aseptic_profile_versions` |
| ક્યાં create થાય | `/sterilization` → "New sterilization cycle profile" | `/aseptic` → "New sterile process profile" (§8.1) |
| વપરાય ક્યાં | §5.1 ના "Cycle profile version" dropdown માં | Product Master ના "Sterile process profile" dropdown માં (`GET /products/v1/sterile-profiles`) |

**અહીં profile બનાવવાથી Product Master નું dropdown ખાલી જ રહેશે** — code-verified: Product Master ના
`_validate_sterile_profile()` ફક્ત `aseptic_service.get_released_profile_version()` call કરે છે,
`process_cycle_profile_versions` ને ક્યારેય જોતું જ નથી. Product Master ના DDCP profile માટે §8.1 (Aseptic
page) પર જ profile બનાવવો.

| Field | ફરજિયાત? | નોંધ |
|---|---|---|
| Profile number | ✅ | Unique (profile_number + version_no) |
| Version no. | ✅ | Default `1` |
| Process type | ✅ | Dropdown, §5.1 ના જ 9 વિકલ્પ |
| Validation reference | — | free text |
| Sterile status validity (hours) | — | Cycle ACCEPTED થયા પછી load item કેટલો સમય "eligible" રહે (§6 જુઓ) |
| Critical parameters (kv, flat) | — | free-form key/value; nested `{min,target}` shape flat editor થી નથી બની શકતું |
| Indicator requirements (kv) | — | free-form |

Submit → સીધું state **RELEASED**, §5.1 ના "Cycle profile version" dropdown માં તરત દેખાય. **Negative
control:** `sterilization.operator` થી આ endpoint call → `403 ROLE_MISSING` (code-verified,
`test_create_process_cycle_profile_version_requires_role`).

### 5.1 Create process cycle

**Backend:** `POST /sterilization/v1/cycles` (`process_cycle.create`). **CIP/SIP નોંધ:** `POST
/cip-sip/v1/cycles` એ જ command/handler વાપરે છે, ફક્ત `process_type=CIP`/`SIP` થી — 2 જુદા endpoint નથી,
1 જ table.

| Field | ફરજિયાત? | ડેમો ડેટા ઉદાહરણ |
|---|---|---|
| Process type | ✅ | `steam_autoclave` (dropdown: `steam_autoclave`/`dry_heat`/`depyrogenation`/`gas`/`radiation`/`external_reference`/`SIP`/`CIP`/`sterile_filtration`) |
| Equipment | ✅ | qualified/calibrated asset (dropdown) |
| Cycle profile version | ✅ | RELEASED profile (dropdown) |
| Batch | — | optional (dropdown) |
| Load items (≥1 row) | ✅ | Item type `component`, Item reference (material lot dropdown), Position optional |

**Create ચેક (code-verified):** (1) equipment eligibility (§4.3); (2) load_items ≥1; (3) **reprocessing
check** — જો કોઈ `item_reference` પહેલાંના **FAILED** cycle ના load item સાથે match થાય, અને
`reprocessing_authorization_ref` ના આપ્યું હોય → `409 REPROCESSING_AUTHORIZATION_REQUIRED`. Fix: એ જ
request માં `reprocessing_authorization_ref: {"deviation_ref": "DEV-..."}` આપવું.

### 5.2 Start cycle (સહી)

`POST /sterilization/v1/cycles/{id}/start` — ફક્ત **DRAFT** state માંથી → **CYCLE_STARTED**. Fields:
`cycle_id`, `expected_version`. Document 106 meaning "Performed", role કોઈ ચોક્કસ નથી (permission-code જ
ગેટ), independent નથી.

### 5.3 Record cycle data (unsigned, ઘણી વાર call કરી શકાય)

ફક્ત **CYCLE_STARTED**/**CYCLE_RUNNING** માંથી. Fields: Controller cycle ID, Parameter data (kv, દા.ત.
`temperature_c`→`121.3`), Alarm data (kv), Indicator results (kv, દા.ત. `BI_1`→`negative`), Critical alarm
(Yes/No), Final batch of data (Yes/No).

| `final` | `critical_alarm` | પરિણામ state |
|---|---|---|
| No | No | `CYCLE_RUNNING` (ફરી data record કરી શકાય) |
| No | **Yes** | **HOLD** + `requires_deviation=true` (તરત, `final` ના value ને ધ્યાનમાં લીધા વગર) |
| **Yes** | No | **REVIEW_PENDING** (`completed_at` set) |

**⚠️ Operator પોતે pass/fail નક્કી નથી કરતો (STR-FR-009 by design)** — `record_cycle_data` કોઈ
accept/reject field જ સ્વીકારતું નથી, ફક્ત raw data. નિર્ણય §6 ના independent reviewer નો છે.

### 5.4 Sterile Filtration — Install (unsigned)

`POST /filtration/v1/filters/install` (`sterile_filter_use.create`) → state **INSTALLED**.

| Field | ફરજિયાત? |
|---|---|
| Site ID | ✅ (hint માં resolved ID દેખાય) |
| Filter serial | ✅ |
| Filter lot / type / manufacturer | — |
| Batch | — (dropdown) |
| Sterilization cycle ID | — (આ filter ને sterilize કરનાર cycle, જો હોય તો) |
| Housing location / Direction | — |

**Reuse count:** `install_filter()` આપોઆપ ગણે છે — same `filter_serial`+site પર પહેલાંના **ACCEPTED** uses
ની count (settable નથી, computed).

### 5.5 Filtration — Integrity Test (unsigned, 2 વાર: pre + post)

`POST /filtration/v1/filters/{use_id}/integrity-tests`. Fields: Filter use ID, Expected version, Phase
(Pre-use/Post-use), Result (Pass/Fail), Test reference (kv).

| Phase | Result | પરિણામ state |
|---|---|---|
| Pre-use | Pass | **IN_USE** |
| Pre-use | Fail | **FAILED** + `requires_deviation=true` |
| Post-use | Pass **અથવા** Fail | **POST_USE_TEST** (Fail → `requires_deviation=true` set, પણ state હજુ POST_USE_TEST જ — final classification `complete` વખતે) |

### 5.6 Filtration — Complete (સહી)

`POST /filtration/v1/uses/{use_id}/complete` — ફક્ત **POST_USE_TEST** માંથી. `post_use_integrity_result
== "pass"` → **ACCEPTED**, નહીં તો → **FAILED**. Fields: Process parameters (kv), Reason.

### 5.7 Sterilization Operator — Negative Controls

| પ્રયત્ન | અપેક્ષિત પરિણામ |
|---|---|
| Unqualified equipment પર cycle create | `422 STERILIZER_INELIGIBLE` |
| FAILED cycle ના item_reference ફરી, authorization વગર | `409 REPROCESSING_AUTHORIZATION_REQUIRED` |
| `load_items: []` (ખાલી) સાથે create | `422 VALIDATION_FAILED` |
| CYCLE_STARTED સિવાયના state માંથી `data` call | `409 INVALID_TRANSITION` |
| `start` ને expected_version ખોટો આપવો | `409 STALE_VERSION` |
| Sterilization Operator પોતે `review` call કરે | `403 ROLE_MISSING` (permission નથી) |
| POST_USE_TEST સિવાય state માંથી filter `complete` | `409 INVALID_TRANSITION` |

---

## 6. Role: QA Reviewer / QC Reviewer — Process Cycle Review (Independent)

**Backend:** `POST /sterilization/v1/cycles/{id}/review` (`process_cycle.review`, **સહી**, meaning
"Reviewed", **independent=True**). ફક્ત **REVIEW_PENDING**/**HOLD** state માંથી.

| Field | ફરજિયાત? |
|---|---|
| Decision | ✅ — Accept/Reject |
| Reason | Reject વખતે required |

**Independence — SIG-FR-018 (code-enforced, `cycle.started_by_user_id == actor_user_id` ચેક):** જેણે
`start` કર્યું એ જ reviewer બની ના શકે — `ValidationFailedError`. **Client demo moment:** `sterilization.
operator` (જેણે start કર્યું) થી review કરવાનો પ્રયત્ન → block. `qa.reviewer` (અલગ user) → succeed.

**Decision effects:**
| Decision | પૂર્વશરત | પરિણામ |
|---|---|---|
| Accept | `critical_alarm=false` હોવું જ જોઈએ (નહીં તો block) | state **ACCEPTED**; **બધા load items** ને `sterile_status="eligible"` + expiry (profile ના `sterile_status_validity_hours` પરથી) મળે |
| Reject | Reason ફરજિયાત | state **FAILED** + `requires_deviation=true` |

**§9 ના DDCP cross-check માટે** — આ `sterile_status="eligible"` જ field છે જે DDCP ના constituent-handoff
sterilization check વાંચે છે.

---

## 7. Role: Aseptic Supervisor — Sterile Process Profile + Operation Start

**Doc:** 40 (SPEC-EQP-004). **ક્યાં:** `/aseptic`.

### 7.1 New sterile process profile (unsigned — spec માં draft/review stage જ નથી)

`POST /aseptic/v1/profiles` (`aseptic_profile_version.create`) → સીધું state **RELEASED**.

| Field | ફરજિયાત? |
|---|---|
| Profile number | ✅ — unique (profile_number + version_no) |
| Version no. | ✅ — default 1 |
| Required area classification | — (dropdown: `ISO_5`/`ISO_6`/`ISO_7`/`ISO_8`/`Unclassified`) |
| Validation reference | — free text, દા.ત. media-fill/qualification protocol ID |

**Backend-only fields** (UI form માં નથી, પણ command સ્વીકારે છે — `POST` raw JSON થી ભરી શકાય):
`product_id`, `personnel_qualifications`, `sterile_input_requirements`, `intervention_catalogue`,
`hold_time_rules`, `em_dependencies`, `filter_sterilization_requirements`, `release_blockers`.

### 7.2 Supersede profile (unsigned)

`POST /aseptic/v1/profiles/{id}/supersede` — ફક્ત **RELEASED** profile માંથી. નવો row `version_no+1`,
**RELEASED**; જૂનો → **SUPERSEDED**. Content ક્યારેય in-place edit નથી થતું (AG-08 pattern).

### 7.3 Start operation (સહી, ફક્ત Aseptic Supervisor — Operator ને permission નથી)

`POST /aseptic/v1/operations/{id}/start` — ફક્ત **PREPARATION** state માંથી, અને **Readiness composition**
પાસ થવી જોઈએ (`GET /aseptic/v1/operations/{id}/readiness` થી પહેલાં ચેક કરી શકાય):

| Readiness component | ચેક કરે છે | Backend function |
|---|---|---|
| EM area readiness | Area માં open excursion (disposition ના મળેલ) નથી, recent sample alert નથી | `em_commands.get_area_readiness()` (Doc 41) |
| Line clearance | Area નું latest line clearance `CLEARED`, expired નથી | `cleaning_commands.get_area_line_clearance_status()` (Doc 39) |
| Equipment eligibility | દરેક `equipment_ids` qualified/calibrated (§4.3 જ ચેક) | `equipment_commands.get_eligibility()` |
| Sterile input status | દરેક `sterile_input_refs` નો sterile status eligible | `sterilization_commands.get_item_status()` (§9) |

Blocker હોય તો: `409 ASEPTIC_AREA_NOT_READY` (સામાન્ય) અથવા `422 STERILE_COMPONENT_INELIGIBLE` (sterile
input specifically). **⚠️ Personnel qualification ક્યારેય check નથી થતું** (§14 #4).

---

## 8. Role: Aseptic Operator — Operation Create, Intervention, Event, Complete

### 8.1 Create aseptic operation (unsigned)

`POST /aseptic/v1/operations` (`aseptic_operation.create`) → state **PREPARATION**.

| Field | ફરજિયાત? | નોંધ |
|---|---|---|
| Area | ✅ | dropdown, real |
| Aseptic profile version | ✅ | dropdown, RELEASED-only, real |
| Batch | — | dropdown, optional |
| Batch step ID | — | raw text, **no picker** — Document 40 ના literal "recipe stage" ના બદલે `ebmr.gxp_batch_step` (batch_execution ના જ table) — deliberate substitution, model docstring માં નોંધેલું |
| Sterile input references (repeat, `item_id`) | — | **raw text, no picker** (§14 #2) — value = sterilization load item ID અથવા filter use ID |
| Media fill reference (kv) | — | media fill run હોય ત્યારે જ, દા.ત. `media_fill_id`→`MF-2026-03` |

**Backend-only:** `equipment_ids` (list — readiness ના equipment eligibility ચેક માટે, UI form માં field
નથી, JSON raw body થી જ સેટ કરી શકાય).

### 8.2 Record intervention (unsigned, EXECUTION/HOLD state માંથી)

| Field | ફરજિયાત? |
|---|---|
| Intervention type | ✅ — `inherent`/`routine`/`corrective`/`non_routine` |
| Planned | — (Yes/No, default Yes) |
| Location | — |
| Reason | **Planned=No હોય તો ફરજિયાત** |
| Impacted unit scope (kv) | — |

**⚠️ `planned=No` → operation state → HOLD + `requires_deviation=true`** (તરત, automatic).

### 8.3 Record event (unsigned, EXECUTION/HOLD state માંથી)

| Field | ફરજિયાત? |
|---|---|
| Event type | ✅ — free text (દા.ત. `particle_excursion`, `gown_breach`) |
| Source | — |
| Severity | — Info/Warning/**Critical** (default Info) |
| Additional details (kv) | — |

**⚠️ `severity=Critical` → operation state → HOLD + `requires_deviation=true`.**

### 8.4 Complete operation (સહી)

`POST /aseptic/v1/operations/{id}/complete` — ફક્ત **EXECUTION** state માંથી (HOLD માંથી સીધું complete
**નથી** થઈ શકતું — §14 #5).

| Field | ફરજિયાત? |
|---|---|
| Critical | — raw text `"true"`/`"false"` (§14 #3) |
| QC test order ID | — existence-checked જ, content નહીં (§14 #6) |
| QC result ID | — existence-checked જ |
| Reason | **Critical=true હોય તો ફરજિયાત** |

**Block:** `requires_deviation=true` હોય તો `422 VALIDATION_FAILED` (ASP-FR-026) — §14 #5 ની અસર અહીં જ
દેખાય.

### 8.5 Aseptic Operator — Negative Controls

| પ્રયત્ન | અપેક્ષિત પરિણામ |
|---|---|
| Aseptic Operator પોતે `start` call કરે | `403 ROLE_MISSING` (Aseptic Supervisor જ) |
| Unready area (EM excursion open) પર `start` | `409 ASEPTIC_AREA_NOT_READY` |
| Unqualified equipment `equipment_ids` માં | `409 ASEPTIC_AREA_NOT_READY` |
| Non-eligible sterile input `sterile_input_refs` માં | `422 STERILE_COMPONENT_INELIGIBLE` |
| Unplanned intervention પછી directly `complete` (deviation clear કર્યા વગર) | `422 VALIDATION_FAILED` — કાયમ માટે block (§14 #5) |
| `critical=true` complete, `reason` વગર | `422 VALIDATION_FAILED` |

---

## 9. Cross-Module: DDCP ના Constituent Handoff સાથે સંબંધ (PFS-FR-005)

DDCP profile ના constituent requirement (દા.ત. needle → `required_state = STERILIZED`) સાચવવા માટે, DDCP
ના `decide_constituent_handoff()` (Accept/Reject handoff) command **આ જ module** ને પૂછે છે:

```
DDCP constituent handoff Accept → profile_version_id આપ્યું હોય →
  required_state ∈ {STERILIZED, DEPYROGENATED, READY_TO_USE} →
    sterilization_use_id ફરજિયાત →
      sterilization_commands.get_item_status(sterilization_use_id) call →
        sterile_status ∈ (None, "eligible") → PASS
        નહીં તો → SterileComponentIneligibleError
```

`sterilization_use_id` = §5.1 ના load item ID, **અથવા** §5.4-5.6 ના filter use ID (polymorphic — બંને
ચેક થાય). **⚠️ Filter use ID માટે એક quirk (code-verified, §14 #7):** આ check `state ∈ (None, "completed")`
પણ જુએ છે, પણ `SterileFilterUse.state` enum માં literal `"completed"` **ક્યારેય assign જ નથી થતું**
(ફક્ત `ACCEPTED`/`FAILED`) — practically load-item ના `sterile_status="eligible"` half જ pass કરાવે છે.
**Client demo માટે:** DDCP handoff ના "Sterilization/depyrogenation reference" field માં load item ID
(§5.1-5.3 થી ACCEPTED cycle નો) વાપરવો, filter use ID નહીં.

---

## 10. State Machine સંદર્ભ (બધા 4 entity)

**Process Cycle:** `DRAFT --start(સહી)--> CYCLE_STARTED --data--> CYCLE_RUNNING --data(final)--> REVIEW_PENDING --review(સહી,accept)--> ACCEPTED` | `--data(critical_alarm)--> HOLD --review(reject)--> FAILED` | `REVIEW_PENDING --review(reject)--> FAILED`

**Sterile Filter Use:** `(install) --> INSTALLED --integrity(pre,pass)--> IN_USE --integrity(post)--> POST_USE_TEST --complete(સહી,pass)--> ACCEPTED` | `INSTALLED --integrity(pre,fail)--> FAILED` | `POST_USE_TEST --complete(સહી,fail)--> FAILED`

**Aseptic Profile Version:** `(create) --> RELEASED --supersede--> SUPERSEDED` (નવો row RELEASED)

**Aseptic Operation:** `(create) --> PREPARATION --start(સહી)--> EXECUTION --complete(સહી)--> ASEPTIC_COMPLETE` | `EXECUTION --intervention(unplanned)/event(critical)--> HOLD --(કોઈ resolve endpoint નથી, §14 #5)--`

---

## 11. RBAC / Signature નકશો — સંપૂર્ણ ટેબલ

| record_type | action | Permission code | Role(s) | સહી? | Independent? |
|---|---|---|---|---|---|
| process_cycle_profile_version | create | `process_cycle_profile_version.create` | Admin, **QA Reviewer** (Sterilization Operator ને નથી — SG-203) | ના | — |
| process_cycle | create | `process_cycle.create` | Admin, QA Reviewer, Sterilization Operator | ના | — |
| process_cycle | start | `process_cycle.start` | Admin, QA Reviewer, Sterilization Operator | ✅ | ના |
| process_cycle | data | `process_cycle.start` (reused) | એ જ | ના | — |
| process_cycle | review | `process_cycle.review` | Admin, QA Reviewer, QC Reviewer | ✅ | **✅ હા** (starter ≠ reviewer) |
| sterile_filter_use | create | `sterile_filter_use.create` | Admin, Sterilization Operator | ના | — |
| sterile_filter_use | integrity-test | `sterile_filter_use.create` (reused) | એ જ | ના | — |
| sterile_filter_use | complete | `sterile_filter_use.complete` | Admin, Sterilization Operator | ✅ | ના |
| aseptic_profile_version | create/supersede | `aseptic_profile_version.create` | Admin, Aseptic Supervisor | ના | — |
| aseptic_operation | create | `aseptic_operation.create` | Admin, Aseptic Operator | ના | — |
| aseptic_operation | start | `aseptic_operation.start` | Admin, **Aseptic Supervisor** (Operator ને નથી) | ✅ | ના |
| aseptic_operation | intervention | `aseptic_operation.intervention` | Admin, Aseptic Operator | ના | — |
| aseptic_operation | event | `aseptic_operation.event` | Admin, Aseptic Operator | ના | — |
| aseptic_operation | complete | `aseptic_operation.complete` | Admin, Aseptic Operator | ✅ | ના |

**Fail-closed ચેક:** ઉપરના 5 signed action (start/review/complete×3) — બધા ને matching
`SIGNATURE_POLICY_FLOOR` row છે (gap નથી). બાકીના (create/data/intervention/event) `_resolve_signature`
call જ નથી કરતા — deliberately unsigned, gap નથી.

---

## 12. Negative / Error Test Cases

| # | Test | Module | અપેક્ષિત |
|---|---|---|---|
| N1 | Unqualified equipment પર cycle create | Sterilization | `422 STERILIZER_INELIGIBLE` |
| N2 | Reprocessing without authorization | Sterilization | `409 REPROCESSING_AUTHORIZATION_REQUIRED` |
| N3 | Same-actor start+review | Sterilization | `422 VALIDATION_FAILED` (SIG-FR-018) |
| N4 | Critical alarm cycle → accept પ્રયત્ન | Sterilization | block (accept ફક્ત critical_alarm=false પર) |
| N5 | Non-INSTALLED state પર integrity-test | Filtration | `409 INVALID_TRANSITION` |
| N6 | Non-POST_USE_TEST state પર complete | Filtration | `409 INVALID_TRANSITION` |
| N7 | Unready area પર aseptic start | Aseptic | `409 ASEPTIC_AREA_NOT_READY` |
| N8 | Non-eligible sterile input પર start | Aseptic | `422 STERILE_COMPONENT_INELIGIBLE` |
| N9 | Aseptic Operator પોતે start | Aseptic | `403 ROLE_MISSING` |
| N10 | HOLD state માંથી directly complete | Aseptic | `422 VALIDATION_FAILED` (કાયમ, §14 #5) |
| N11 | Stale expected_version કોઈ પણ transition પર | બંને | `409 STALE_VERSION` |
| N12 | Password વગર/challenge વગર signed action | બંને | `428 MISSING_SIGNATURE` |

---

## 13. Error Code શબ્દકોશ

| Code | HTTP | ક્યાં | મતલબ |
|---|---|---|---|
| `STERILIZER_INELIGIBLE` | 422 | cycle create | Equipment qualified/calibrated નથી |
| `REPROCESSING_AUTHORIZATION_REQUIRED` | 409 | cycle create | FAILED cycle નો item ફરી, authorization વગર |
| `ASEPTIC_AREA_NOT_READY` | 409 | operation start | EM/line-clearance/equipment readiness block |
| `STERILE_COMPONENT_INELIGIBLE` | 422 | operation start, DDCP handoff | Sterile input eligible નથી |
| `VALIDATION_FAILED` | 422 | સામાન્ય | Field-level rule ભંગ (reason ફરજિયાત, requires_deviation block, વગેરે) |
| `STALE_VERSION` | 409 | સામાન્ય | `expected_version` mismatch (optimistic concurrency) |
| `INVALID_TRANSITION` | 409 | સામાન્ય | Command આ state માંથી allowed નથી |
| `MISSING_SIGNATURE` | 428 | signed action | Password/challenge વગર |
| `ROLE_MISSING` | 403 | RBAC | Permission નથી |

**⚠️ Document 42/40 §16 એ declare કરેલા પણ code માં ક્યારેય raise ના થતા codes** (test manual એ expect ના
કરવા): `CYCLE_PROFILE_NOT_EFFECTIVE`, `LOAD_PATTERN_INVALID`, `CYCLE_PARAMETER_FAILED`,
`CYCLE_REVIEW_REQUIRED`, `FILTER_INTEGRITY_FAILED`, `STERILE_STATUS_EXPIRED`,
`STERILIZATION_STATUS_INVALID` (ફક્ત readiness ના blocker-dict code તરીકે વપરાય, raised exception તરીકે
નહીં), `ASEPTIC_HOLD_TIME_EXCEEDED`, `UNPLANNED_INTERVENTION_REVIEW_REQUIRED`,
`ASEPTIC_ENVIRONMENT_EXCURSION`, `ASEPTIC_OPERATOR_NOT_QUALIFIED` (§14 #4 જ, code declare કરે છે પણ raise
ક્યાંય નથી કરતું — "no personnel-qualification entity exists to check against").

---

## 14. જાણીતી મર્યાદાઓ (પ્રામાણિકતા)

| # | મર્યાદા |
|---|---|
| 1 | ~~Sterilization cycle profile નું UI માં કોઈ create form નથી~~ — **✅ RESOLVED 2026-09-16 (SG-203)**: `POST /sterilization/v1/profiles` + `/sterilization` ના "New sterilization cycle profile" બટન (§5.0), `QA Reviewer`/Admin gated, direct-to-RELEASED. No supersede endpoint built (schema માં `supersedes_profile_version_id` self-FK નથી, aseptic profile થી અલગ — future migration જોઈએ તો). |
| 2 | ~~Aseptic ના "Sterile input references" repeat row નું `item_id` field raw text છે, dropdown નથી~~ — **✅ RESOLVED 2026-09-16**: હવે real dropdown, `GET /sterilization/v1/items/eligible?site_id=` વાપરીને (eligible sterilization load items — filter uses ની "completed" state ક્યારેય reach નથી થતી, item 7 જુઓ, એટલે practically ફક્ત load items જ list માં દેખાય). `frontend/src/components/shared/RepeatableFields.tsx`ને નવો `customSelect` `RepeatSubField` type મળ્યો — કોઈ પણ page પોતાનો already-fetched options/status field પર જ carry કરી શકે, `RepeatableRows`માં નવો named prop pair ઉમેર્યા વગર (SG-201 resolution ની શરૂઆત). |
| 3 | Aseptic ના "Complete operation" transition નું **"Critical" field raw text `"true"/"false"`** છે, sterilization ના `critical_alarm`/`final` (Yes/No Select) જેવો bool dropdown **નથી** — સમાન semantics, જુદો UX. |
| 4 | **Personnel qualification ક્યારેય ચેક નથી થતું** — `ASEPTIC_OPERATOR_NOT_QUALIFIED` error code declare થયેલો છે પણ raise ક્યાંય નથી થતો; આ platform માં કોઈ "વ્યક્તિ aseptic ceremony માટે qualified છે કે નહીં" tracking entity જ નથી. `aseptic_profile_version.personnel_qualifications` field (kv) capture થાય છે પણ enforced ક્યાંય નથી. |
| 5 | **`requires_deviation=true` થયા પછી aseptic operation કાયમ માટે block રહે છે** — unplanned intervention કે critical event પછી state HOLD થાય, પણ આ module માં ક્યાંય `requires_deviation` ને `false` પાછું set કરવાનો કોઈ code path જ નથી (કોઈ "resolve deviation"/HOLD→EXECUTION endpoint નથી) — `complete` કાયમ 422 આપશે. Real-world માં કદાચ external QMS deviation resolve થાય તો પણ, આ module એ જાણતું નથી. |
| 6 | Aseptic complete ના QC test order/result reference **existence-checked જ છે, content-validated નથી** — QC result ખરેખર pass/fail છે કે નહીં, એ complete ને block/allow નથી કરતું (ફક્ત id ખરેખર DB માં છે કે નહીં). |
| 7 | DDCP cross-check (§9) નો `state ∈ (None, "completed")` — `SterileFilterUse.state` enum ક્યારેય literal `"completed"` produce નથી કરતું (latent inconsistency, code બંને જગ્યાએ verified) — practically filter-use route થી DDCP check pass કરવો લગભગ અશક્ય, load-item route જ વાપરવો. |
| 8 | Sterile filter `reuse_count` — install સમયે આપોઆપ ગણાય છે (પહેલાંના ACCEPTED uses ની count, same filter_serial+site) — `test_sterilization_flow.py` એ confirm કરે છે (0→1 બે install→complete cycle પછી), model docstring જૂનું (SG-116 પહેલાનું) છે એ મુજબ "ક્યારેય increment નથી થતું" કહે છે — **code doc lag**, functional bug નથી. |
| 9 | Filtration section (§3.1) નું **RBAC ફ્રન્ટએન્ડમાં ગેટેડ નથી** — Install/Integrity-test/Complete બટન બધા user ને દેખાય, server-side જ block કરે (403). Sterilization/Aseptic ના main config ની જેમ frontend `can` check નથી. |
| 10 | `/sterilization` અને `/aseptic` વચ્ચે, અથવા `/equipment`/`/batch-execution` થી — **કોઈ navigation link/query param નથી** (DDCP audit જેવો જ ગેપ, code-verified: `Link href`/`router.push`/`useSearchParams` બંને file માં 0 match). Batch/equipment/area ID manually copy-paste કરવું પડે. |
| 11 | ~~"Aseptic profile version" (§8.1 Create aseptic operation) dropdown ના બદલે raw text field તરીકે દેખાતું~~ — **✅ RESOLVED 2026-09-16, real bug (RBAC misconfiguration, empty list નહીં):** `entities.asepticProfiles` (frontend shared hook) `GET /products/v1/sterile-profiles` વાપરતું હતું — `product.view` gated, જે `Aseptic Operator`/`Aseptic Supervisor` **બેમાંથી કોઈ role ને નથી** (`scripts/seed.py` ચકાસેલું) — એટલે dropdown `403` → `EntityPickerField` એને "empty list" ની જેમ જ silently manual-text-fallback માં દેખાડતું, ભૂલ ક્યાંય UI માં દેખાય નહીં. Fix: `entities.asepticProfiles` હવે `GET /aseptic/v1/profiles` વાપરે છે (આ module ના પોતાના read endpoint, **કોઈ RBAC ગેટ જ નથી**) — client-side RELEASED filter. Live-verified: `aseptic.operator` થી `/aseptic/v1/profiles` હવે 200 (પહેલાં `/products/v1/sterile-profiles` 403 આપતું હતું). Product Master નું પોતાનું sterile-profile field અસર નથી પામ્યું (એ પોતાનો સીધો fetch વાપરે છે, `entities.asepticProfiles` નહીં). |

---

## 15. Traceability Sheet

| Capability | Document | Backend function | Frontend field/section | Permission | Signature |
|---|---|---|---|---|---|
| Cycle profile create (SG-203) | 42 | `create_process_cycle_profile_version` | §5.0 | `process_cycle_profile_version.create` | ના |
| Cycle create | 42 | `create_process_cycle` | §5.1 | `process_cycle.create` | ના |
| Cycle start | 42 | `start_cycle` | §5.2 | `process_cycle.start` | ✅ |
| Cycle data | 42 | `record_cycle_data` | §5.3 | `process_cycle.start` | ના |
| Cycle review | 42 | `review_cycle` | §6 | `process_cycle.review` | ✅ independent |
| Filter install | 42 | `install_filter` | §5.4 | `sterile_filter_use.create` | ના |
| Filter integrity | 42 | `record_filter_integrity_test` | §5.5 | `sterile_filter_use.create` | ના |
| Filter complete | 42 | `complete_filter_use` | §5.6 | `sterile_filter_use.complete` | ✅ |
| Aseptic profile create/supersede | 40 | `create_aseptic_profile_version`/`supersede_...` | §7.1-7.2 | `aseptic_profile_version.create` | ના |
| Aseptic operation create | 40 | `create_aseptic_operation` | §8.1 | `aseptic_operation.create` | ના |
| Aseptic start (readiness) | 40, 41, 39, 38 | `start_operation`/`_compute_readiness` | §7.3 | `aseptic_operation.start` | ✅ |
| Aseptic intervention | 40 | `record_intervention` | §8.2 | `aseptic_operation.intervention` | ના |
| Aseptic event | 40 | `record_event` | §8.3 | `aseptic_operation.event` | ના |
| Aseptic complete | 40 | `complete_operation` | §8.4 | `aseptic_operation.complete` | ✅ |
| DDCP cross-check | 54 (PFS-FR-005), 42/40 | `get_item_status` (shared) | §9 | — | — |

*આ document code થી verified (2026-09-16) — `services/gxp-api/app/modules/equipment/{sterilization,
aseptic}_{router,commands,models}.py`, `tests/{test_sterilization_flow,test_aseptic_flow}.py`,
`frontend/src/app/{sterilization,aseptic}/page.tsx`, `scripts/seed.py`. Real data-entry sequence:
`Sterilization_Aseptic_Client_Demo_Guide_Gujarati.md`.*
