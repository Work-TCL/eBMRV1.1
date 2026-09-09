# DDCP — સંપૂર્ણ Functional Test Manual (Master Document, Gujarati) — v2 (Role-Wise)

**દસ્તાવેજ સંદર્ભ:** Documents 54–57 (SPEC-DDCP-001/002/003/004) + Document 39 (Line Clearance, SPEC-EQP-002)
**મોડ્યુલ:** `services/gxp-api/app/modules/ddcp/*`, `services/gxp-api/app/modules/equipment/cleaning_*`
(backend); `frontend/src/app/ddcp/*`, `frontend/src/app/line-clearance/*`, `frontend/src/components/ddcp/*` (UI)
**તારીખ:** 2026-09-03 (v2 — role-wise structure; dynamic id-pickers, settings-field honesty)

## v1 → v2: શું બદલાયું

1. **Part B હવે role-wise છે, functionality-wise નહીં.** v1 માં દરેક family ની અંદર બધા functional
   blocks ભેગા હતા (profile design થી release evidence સુધી), "કોણ કરે" ફક્ત 1 line માં mention થતું.
   **v2 માં Part B ના 2 મુખ્ય section — "DDCP Engineer શું કરે" અને "DDCP Operator શું કરે" — છે, અને
   દરેક section ની અંદર એ role ની બધી actions, બધી 4 families માટે, ક્રમમાં** — જેથી `ddcp.engineer`
   role થી ટેસ્ટ કરતી વખતે તમે ફક્ત section 4 વાંચો, `ddcp.operator` થી ટેસ્ટ કરતી વખતે ફક્ત section 5.
2. **Settings/Key-Value fields ની સમજ ઉમેરી** (Section 3.4) — "Setting name" field માં શું ટાઈપ કરવું
   ખબર ના પડે એ સમસ્યા માટે: મોટા ભાગના kv field genuinely free-form છે (backend કંઈ validate નથી
   કરતું) — હવે UI માં આ explicit રીતે લખેલું છે. જ્યાં backend ખરેખર ચોક્કસ key વાંચે છે (દા.ત.
   `environment_status.ready`), ત્યાં field ને હવે **dynamic Yes/No control** માં બદલી નાખ્યું છે —
   Setting name ટાઈપ કરવાની જરૂર જ નથી.
3. **ID-reference fields હવે dynamic dropdown છે** (Section 3.5) — "Handoff ID"/"Fill operation ID"/
   "Assembly record ID" જેવા field, જે પહેલાના op ના result માંથી copy-paste કરવા પડતા, હવે session
   માં બનેલા records માંથી dropdown તરીકે પસંદ કરી શકાય છે.

3 જૂના doc (`DDCP_Manual_Test_Guide_Gujarati.md`, `DDCP_Field_Data_Cheatsheet_Gujarati.md`,
`DDCP_Role_Based_Test_Cases_Gujarati.md`) હજુ folder માં છે — quick reference તરીકે. **નવું testing આ
doc થી શરૂ કરો.**

---

## અનુક્રમણિકા

**Part A — Foundation**
1. [DDCP એટલે શું અને શા માટે regulated છે](#1-ddcp-એટલે-શું-અને-શા-માટે-regulated-છે)
2. [Access, Login, Roles — Setup](#2-access-login-roles--setup)
3. [UI કેવી રીતે કામ કરે છે (Developer-level Mechanics)](#3-ui-કેવી-રીતે-કામ-કરે-છે-developer-level-mechanics)

**Part B — Role-Wise Action Performance (મુખ્ય ભાગ)**

4. [Role: DDCP Engineer — Stage 1, બધી 4 Families](#4-role-ddcp-engineer--stage-1-બધી-4-families)
5. [Role: DDCP Operator — Stages 2-4, બધી 4 Families](#5-role-ddcp-operator--stages-2-4-બધી-4-families)
6. [Supporting Role: Line Clearance (Operator/Sanitation Operator)](#6-supporting-role-line-clearance-operatorsanitation-operator)

**Part C — Cross-Cutting**

7. [Role: Admin — Cross-Check](#7-role-admin--cross-check)
8. [Negative-Control Roles](#8-negative-control-roles)
9. [સામાન્ય Negative / Error Test Cases](#9-સામાન્ય-negative--error-test-cases)
10. [Error Codes નો શબ્દકોશ](#10-error-codes-નો-શબ્દકોશ)
11. [Fix History / જાણીતી મર્યાદાઓ](#11-fix-history--જાણીતી-મર્યાદાઓ)
12. [Traceability Sheet](#12-traceability-sheet)

---

# Part A — Foundation

## 1. DDCP એટલે શું અને શા માટે regulated છે

**DDCP = Drug-Device Combination Product** — દવા (drug) અને મિકેનિકલ ડિવાઇસ (device) બંને એક જ યુનિટમાં.

| પ્રકાર | ઉદાહરણ | Document | API prefix |
|---|---|---|---|
| **Prefilled Syringe (PFS)** | પહેલેથી ભરેલી સિરીંજ | Document 54 | `/ddcp/v1/prefilled-syringe` |
| **Autoinjector** | Pen-injector (single-use/reusable) | Document 55 | `/ddcp/v1/autoinjector` |
| **Inhalation (MDI/DPI)** | Inhaler — metered-dose/dry-powder | Document 56 | `/ddcp/v1/inhalation` |
| **Coated / Combination Device** | Drug-eluting stent | Document 57 | `/ddcp/v1/coated-device` |

**શા માટે regulated?** FDA ના combination-product નિયમો — drug ની ગુણવત્તા અને device ની ગુણવત્તા બંને
સાબિત કરવા પડે, અને બંને ને જોડતી દરેક ક્રિયા કાયમી, tamper-proof રેકોર્ડ થવી જોઈએ.

**4 functional stages, દરેક family માટે એક જ pattern — અને 2 roles વચ્ચે વહેંચાયેલા:**

```
Stage 1  Profile Design    →  "recipe/spec" define કરવી          →  DDCP Engineer
Stage 2  Batch Execution    →  handoff→fill/assembly→tests→disposition →  DDCP Operator
Stage 3  Batch Readiness    →  batch તૈયાર છે કે નહીં ચકાસવું        →  DDCP Operator (assess) / બધા (read)
Stage 4  Release Evidence   →  freeze કરેલો પુરાવો                  →  DDCP Operator
```

**શા માટે 2 roles?** SoD (Segregation of Duties) — જે "શું જોઈએ" નક્કી કરે (spec), એ "શું થયું" record
ના કરે (execution) — bias ટાળવા. Section 2.3 માં detail.

---

## 2. Access, Login, Roles — Setup

### 2.1 Browser Access

| વસ્તુ | URL |
|---|---|
| Frontend (UI) | `http://88.99.15.183:4101` |
| Backend API | `http://88.99.15.183:8010` |

### 2.2 Login

| Field | શું ભરવું |
|---|---|
| Username | 2.4 ના table માંથી |
| Password | `ChangeMe123!` |
| Site | `SITE1` |

**શા માટે Login જરૂરી?** 21 CFR Part 11 — દરેક action કોણે કર્યું ઓળખાવું જોઈએ. "Login/MFA એ પોતે
electronic signature નથી" (AG-07) — signature-required actions ને password ફરી નાખવો પડે (Section 6
માં Line Clearance નું ઉદાહરણ).

### 2.3 Roles — કોણ શું કરી શકે

| Role | Permission codes | કરે છે | Section |
|---|---|---|---|
| **DDCP Engineer** | `ddcp_profile.author`, `.release` | Stage 1 — profile design | 4 |
| **DDCP Operator** | `ddcp_constituent.handoff`/`.decide`, `ddcp_fill.*`, `ddcp_device.*`, `ddcp_release.evaluate`/`.export` | Stages 2-4 — execution | 5 |
| Operator/Sanitation Operator/Supervisor | `line_clearance.create`/`.complete` | Line clearance (DDCP readiness ને support) | 6 |
| **Admin** | ઉપરની બધી | Cross-check | 7 |

**IND-001:** Device assembly "independently verify" — verify કરનાર **એ જ વ્યક્તિ ના હોવી જોઈએ** જેણે
step record કર્યું — user-id compare, role level પર નહીં. 2 જુદા DDCP Operator users જોઈએ.

### 2.4 Demo Users

| Username | Role |
|---|---|
| `admin` | Admin |
| `ddcp.engineer` *(2.5 મુજબ બનાવો)* | DDCP Engineer |
| `ddcp.operator` *(2.5 મુજબ બનાવો)* | DDCP Operator |
| `operator1` / `qa.reviewer` / `qa.releaser` / `qc.reviewer` | કોઈ પણ `ddcp_*` નથી — negative control |

### 2.5 Test Users બનાવવા (Admin જ કરી શકે)

`admin` → **Admin → Users** (`/admin/users`) → **"New user"**:

| Field | Engineer | Operator |
|---|---|---|
| Username | `ddcp.engineer` | `ddcp.operator` |
| Email | `ddcp.engineer@example.com` | `ddcp.operator@example.com` |
| Full name | `Dev DdcpEngineer` | `Opal DdcpOperator` |
| Password | `ChangeMe123!` | `ChangeMe123!` |

"Create user" → નીચે **"Assign role"**: User + Site=`Demo Site 1 (SITE1)` + Role. Assignment
`/auth/me` પર live query થાય છે — logout/login વગર જ તરત effect.

---

## 3. UI કેવી રીતે કામ કરે છે (Developer-level Mechanics)

### 3.1 3 Tabs

```
canAuthorProfile = holdsAnyRole(me, ["Admin", "DDCP Engineer"])   → "Profile designer" tab
canExecute        = holdsAnyRole(me, ["Admin", "DDCP Operator"])   → "Execution & result records" tab
                                                                     + "Batch readiness & release" ના Assess/Freeze બટન
```

"Batch readiness & release" tab હંમેશા દેખાય (read બધા માટે). Tabs form data જાળવી રાખે છે (CSS
hide/show, remount નહીં). Product family બદલવાથી 3 એ 3 tab નું content remount થાય (data leak ના થાય).

### 3.2 Field Control Types

| Control | કેવો દેખાય | ક્યાં |
|---|---|---|
| Text/Decimal | Text box (decimal string જ રહે, AG-15) | Codes, quantities |
| Select | Closed dropdown, backend enforce કરે | Subtype, decision |
| Suggestions | Text + સૂચનો, ગમે તે ટાઈપ કરી શકાય | test_type, count_type |
| Picker | Real DB dropdown, "Enter ID manually" fallback | batch/equipment/area/profile |
| **Record picker (નવું)** | Session માં બનેલા records નું dropdown | Handoff ID/Fill operation ID/Assembly record ID — 3.5 જુઓ |
| Ref | Key dropdown + ID box | source_batch_reference |
| Repeat | "+ Add row" | constituent_requirements |
| Key-Value | Setting/Value જોડ — **મોટે ભાગે free-form** | 3.4 જુઓ |
| **Yes/No (kv-backed, નવું)** | સાદો Yes/No — key આપોઆપ set થાય | environment_status — 3.4 જુઓ |
| Bool | Yes/No dropdown | unit_serialization |
| Datetime | Browser picker | occurred_at |

### 3.3 "Execution & Result Records" — Dropdown કેવી રીતે કામ કરે

```
catalog.ts → DdcpFamily.ops: DdcpOp[]   // { path, label, fields: DdcpField[], producesRecordKind? }
ExecutionCard:
  1. "What are you recording?" → op = family.ops[selectedIndex]
  2. op.fields → field.type પ્રમાણે control render
  3. Submit → buildPayload() → POST `${prefix}/${filledPath}` (idempotency_key auto)
  4. op.producesRecordKind હોય → સફળ result નો id session-local "recentRecords" cache માં ઉમેરાય
     (Section 3.5)
```

### 3.4 Settings / Key-Value Fields — "Setting name" માં શું ટાઈપ કરવું?

**મોટા ભાગના kv field (Product architecture settings, Required controls, Process parameters, Product
contact path, Impacted unit scope, Drug/device impact assessment, Additional attributes) genuinely
free-form છે** — backend એને exactly એ જ રીતે JSONB તરીકે store કરે છે, **કોઈ પણ key/value ને validate
નથી કરતું**. એટલે "database side validation" ના અર્થ માં **કોઈ hidden setting-name catalogue અસ્તિત્વમાં
નથી** — તમે તમારા process ને describe કરવા કોઈ પણ નામ વાપરી શકો. દરેક field ના hint માં "Free-form —
the backend stores whatever you enter here as-is" લખેલું છે, જેથી ખબર પડે કે guess કરવાની જરૂર નથી.

**અપવાદ — જ્યાં backend ખરેખર 1 ચોક્કસ key વાંચે છે:**

| Field | Family/Op | ચોક્કસ key | શું થાય | UI એ હવે શું કર્યું |
|---|---|---|---|---|
| Environment status snapshot → **"Environment ready"** | Inhalation "Start an inhaler fill run", Coated device "Start a coating run" | `ready` (bool) | `No` → `ENVIRONMENT_NOT_READY`/`COATING_ENVIRONMENT_NOT_READY` block (ફક્ત profile ને environment profile જોઈએ ત્યારે જ ચેક થાય) | **✅ FIXED — હવે "Environment ready" Yes/No control છે, key ટાઈપ કરવાની જરૂર જ નથી** (`type: "boolKv"`, `kvKey: "ready"`) |
| Required controls (PFS profile) | PFS profile design | nested `{"serialization": {"required": true}}` | UDI/serialization compliance reporting-flag (PFS-FR-019) — **reporting-only, ક્યારેય release block નથી કરતું** | ⚠️ **હજુ ખુલ્લું** — આ nested shape flat kv editor produce ના કરી શકે (1 level ના key/value જ સપોર્ટ કરે છે). Field ના hint માં આ સ્પષ્ટ લખેલું છે. જરૂર પડે તો API સીધું call કરો — non-blocking હોવાથી ordinary testing ને અસર નથી કરતું. |
| Autoinjector profile ના `unit_serialization` | Autoinjector profile design | — | — | ✅ **પહેલેથી જ સાચું** — Autoinjector profile ને પોતાનું typed "Unit serialization required" Bool field છે (kv જ નથી વાપરવો પડતો), PFS ને એ dedicated field નથી (ઉપરની row) |

**કેવી રીતે ખબર પડે કોઈ field માં ચોક્કસ key છે કે નહીં?** Field નો hint ચેક કરો — જો "Free-form" લખેલું
હોય તો કંઈ પણ નામ વાપરો; ના હોય તો hint માં ચોક્કસ key/behavior લખેલું છે.

### 3.5 ID-Reference Fields — હવે Dynamic Dropdown (✅ FIXED)

**સમસ્યા હતી:** "Accept or reject a constituent handoff" ના "Handoff ID" field માં — તમારે "Record a
constituent handoff" ના result banner માંથી ID **manually copy-paste** કરવો પડતો. એ જ રીતે "Fill
operation ID" (3 ops માં) અને "Assembly record ID".

**✅ Fix:** આ 4 fields હવે `type: "recordSelect"` — session દરમિયાન બનેલા એ જ પ્રકારના records નું
dropdown બતાવે છે (backend GET list endpoint ના હોવાથી — session-local memory, real DB fetch નહીં):

| Field | ક્યાં | Dropdown માંથી શું મળે |
|---|---|---|
| Handoff ID | "Accept or reject a constituent handoff" | આ session માં "Record a constituent handoff" થી બનેલા બધા handoff |
| Fill operation ID | IPC / Intervention / Complete (3 ops) | આ session માં "Start a fill operation" થી બનેલા બધા fill operation |
| Assembly record ID | "Independently verify an assembly step" | આ session માં "Record a device assembly step" થી બનેલા બધા assembly record |

Dropdown ના entries: `<short-id>… — <op label> (<time>)`. કોઈ record ના બન્યો હોય ત્યાં સુધી "No
{kind}s available yet" — manual ID box દેખાય (પહેલાની જેમ). **નોંધ:** આ memory ફક્ત આ browser tab ના
session પૂરતી છે — page reload/family switch કરો તો ખાલી થાય (નવેસરથી record કરવા પડે, અથવા manual ID
paste કરો).

---

# Part B — Role-Wise Action Performance

## 4. Role: DDCP Engineer — Stage 1, બધી 4 Families

**Permission:** `ddcp_profile.author`, `ddcp_profile.release`. **UI:** ફક્ત "Profile designer" tab.
**કરે છે:** પ્રોડક્ટ ની spec/recipe — batch execution શરૂ થાય એ પહેલા, દરેક 4 family માટે profile
create+release. **શા માટે:** Batch **RELEASED** profile વગર શરૂ ના જ થઈ શકે — regulated recipe control.

`ddcp.engineer` / `ChangeMe123!` થી login → `/ddcp` → "Profile designer" tab (default).

### 4.1 Action: PFS Profile Create + Release

**Fields — Create (7):**

| Field | Type | જરૂરી? | Data | શા માટે |
|---|---|---|---|---|
| Profile code | Text | ✅ | `PFS-DEMO-001` | Unique code |
| Subtype | Select | — | `Prefilled syringe` | Prefilled syringe/Cartridge/Vial-device co-pack/Other injectable |
| Dosage form | Text | — | `Liquid injectable` | Free text |
| Presentation | Text | — | `1 mL prefilled syringe, single-dose` | Free text |
| Product architecture settings (kv, free-form) | — | — | `sterileProcess`→`true`, `fillControlRuleId`→`FILL-RULE-01` | Documentation only, backend stores as-is |
| Required controls (kv, free-form + 1 recognized key) | — | — | `visualInspectionProfile`→`VI-001` | Section 3.4 — `serialization.required` nested key non-blocking gap |
| Constituent requirements | Repeat | ✅ (≥1) | Row 1: `Drug`/`bulk_drug`/`Released`; Row 2: `Device`/`needle`/`Ready to use` | Release પહેલા ફરજિયાત |

**Release (3):** Profile (auto-selected) / Expected version=`1` / Change reference=`CHG-2026-045`.

**"Release" → succeed ત્યારે:** DRAFT state + ≥1 constituent requirement. Signature
`signature_required=False` (SG-148 resolved) — **હવે succeed થાય**.

**Test Cases:**

| # | ક્રિયા | Expected |
|---|---|---|
| TC-ENG-PFS-01 | Create + Release ઉપરના data | DRAFT → RELEASED |
| TC-ENG-PFS-02 | Subtype=`XYZ` | `PROFILE_SCHEMA_INVALID` |
| TC-ENG-PFS-03 | Requirements 0 rows → Release | `PROFILE_RELEASE_BLOCKED` |
| TC-ENG-PFS-04 | RELEASED profile ફરી release | `INVALID_TRANSITION` |
| TC-ENG-PFS-05 | Expected version=`999` | `STALE_VERSION` |
| TC-ENG-PFS-06 | "Look up a profile version" (PFS only) | `state: RELEASED` |

### 4.2 Action: Autoinjector Profile Create + Release

| Field | Type | Data |
|---|---|---|
| Profile code | Text (✅) | `AUTO-DEMO-001` |
| Injector type | Select (✅) | `Pen — single use` |
| Device BOM version | Text | `BOM-INJ-001` |
| **Unit serialization required** | **Bool (dedicated field — PFS ને આ નથી, 3.4 જુઓ)** | `Yes` |
| Product architecture settings (kv, free-form) | — | `springForce`→`moderate` |
| Required controls (kv, free-form) | — | `activationForceProfile`→`AF-001` |
| Constituent requirements | Repeat (✅ ≥1) | `Device`/`needle_system`/`Ready to use` |

Release: `1` / `CHG-AUTO-001`. Signature check નથી (resolve_signature_requirement call જ નથી આ family
માટે).

### 4.3 Action: Inhalation Profile Create + Release

| Field | Type | Data |
|---|---|---|
| Profile code | Text (✅) | `INH-DEMO-001` |
| Subtype | Select (✅ **ફરજિયાત**) | `MDI — metered dose` |
| Fill route | Text | `standard-mdi` — fill run એ જ route declare કરવો પડશે |
| Environment profile | Text | `ENV-PROFILE-01` |
| Product architecture settings (kv, free-form) | — | `valveType`→`metering` |
| Required controls (kv, free-form) | — | `sprayPatternProfile`→`SP-001` |
| Constituent requirements | Repeat (✅ ≥1) | `Drug`/`bulk_solution`/`Released` |

Release: `1` / `CHG-INH-001`.

**Test Case:** TC-ENG-INH-01 — Subtype ખાલી → Create button disable રહે (required field).

### 4.4 Action: Coated Device Profile Create + Release

**⚠️ Subtype field જ નથી** — Document 57 કોઈ subtype vocabulary define નથી કરતું.

| Field | Type | Data |
|---|---|---|
| Profile code | Text (✅) | `COAT-DEMO-001` |
| Coating route | Text | `standard-elution` |
| Sterilization route | Text | `ETO-STD-01` |
| Environment profile | Text | `ENV-PROFILE-COAT-01` |
| Product architecture settings (kv, free-form) | — | `coatingThicknessTargetUm`→`15` |
| Required controls (kv, free-form) | — | `coatingIntegrityProfile`→`CI-001` |
| Constituent requirements | Repeat (✅ ≥1) | `Device`/`stent_substrate`/`Released` |

Release: `1` / `CHG-COAT-001`.

### 4.5 DDCP Engineer — Negative Controls

| # | ક્રિયા | Expected |
|---|---|---|
| TC-ENG-NEG-01 | `/ddcp` ખોલો — "Execution" tab દેખાય છે? | ❌ ના — "Execution hidden" banner (DDCP Operator role જોઈએ) |
| TC-ENG-NEG-02 | Dev tools/curl થી `POST .../constituent-handoffs` સીધું call | `403 Forbidden` — Engineer ને `ddcp_constituent.handoff` નથી (backend-level defence, UI પણ hide કરે છે) |

---

## 5. Role: DDCP Operator — Stages 2-4, બધી 4 Families

**Permission:** `ddcp_constituent.handoff`/`.decide`, `ddcp_fill.*`, `ddcp_device.*`,
`ddcp_release.evaluate`/`.export`. **UI:** "Batch readiness & release" tab (Assess/Freeze સહિત) +
"Execution & result records" tab. **કરે છે:** Engineer એ release કરેલા profile પ્રમાણે, ખરેખર batch
execute કરવો — handoff, fill/assembly/coating, tests, disposition, readiness, evidence.

`ddcp.operator` / `ChangeMe123!` થી login → `/ddcp` → "Execution & result records" tab.

### 5.1 PFS — 8 Actions (ક્રમમાં)

#### 5.1.1 Constituent Handoff — "કયું Drug/Device વપરાયું" Record કરવો

**શા માટે:** દરેક ingredient નું source traceable — regulatory audit માટે. 2-step (PENDING → decide).

**Op — "Record a constituent handoff" (5 fields):**

| Field | Data | શા માટે |
|---|---|---|
| Batch | Picker | કયા batch માટે |
| Constituent type | `Drug` | Drug/Biologic/Device/Packaging/Label |
| Component role | `bulk_drug` | Profile requirement જોડે match |
| Source → key/ID | `Upstream batch ID` / existing batch ID | ક્યાંથી આવ્યું |
| Additional attributes (kv, free-form) | `coa_reference`→`COA-2026-001` | Optional |

**Op — "Accept or reject a constituent handoff" (6 fields):**

| Field | Data | શા માટે |
|---|---|---|
| **Handoff ID** | **Dropdown — session માં બનેલા handoff (3.5)** | કયો decide કરવો |
| Expected version | `1` | Concurrency |
| Decision | `Accept` | Accept/Reject |
| Rejection reason | (Reject વખતે જ) | Audit |
| Profile (optional check) | profile ID | Extra validation |
| Sterilization/depyrogenation reference | (conditionally જરૂરી) | Traceability |

**Test Cases:** TC-OP-PFS-HAND-01 (Create→Accept, DRUG/bulk_drug) → ACCEPTED. TC-OP-PFS-HAND-02
(duplicate) → `VALIDATION_FAILED`. TC-OP-PFS-HAND-03 (expected version=`99`) → `STALE_VERSION`.
TC-OP-PFS-HAND-04 (DEVICE/needle, એ જ flow) → ACCEPTED.

#### 5.1.2 Fill Operations — Start → IPC → Intervention → Complete

**શા માટે:** Aseptic filling ના દરેક step regulated રેકોર્ડ.

| Op | મુખ્ય fields (data) | નોંધ |
|---|---|---|
| **Start a fill operation** | Batch; Released profile; Line/Filler equipment=Picker; Program `PROG-001`/`1`; Product contact path (kv, free-form)=`path`→`standard`; Target fill=`1.000000`, uom=`mL`; Cycle group=`CYCLE-A` | Handoffs accepted હોવા જોઈએ |
| **Record IPC** | **Fill operation ID = dropdown (3.5)**; Expected version; Sample ID=`IPC-001`; Measured value=`1.020000`; uom=`mL`; Method=`Gravimetric`; Source=`MANUAL`; Acceptance rule | Out-of-spec = hold |
| **Record intervention** | **Fill operation ID = dropdown**; Expected version; Intervention type=`Stopper adjustment`; Started/Ended at; Impacted unit scope (kv, free-form)=`unitRange`→`1001-1050`; Aseptic reference | Optional |
| **Complete** | **Fill operation ID = dropdown**; Expected version; Machine count=`1000`; Filter use ref; Reason | ≥1 FILLED count જોઈએ |

**Test Cases:** TC-OP-PFS-FILL-01 (Start→IPC→Count→Complete) → Success chain. TC-OP-PFS-FILL-02
(FILLED count વગર Complete) → Fail. TC-OP-PFS-FILL-03 (ફરી Complete) → `INVALID_TRANSITION`.

#### 5.1.3 Production Counts — Unit Ledger

**"Record a production count" (9 fields):** Batch; Count type=`FILLED`; Source=`MANUAL`;
Quantity=`1000`; uom=`EA`; Device reference; Reason code=`ROUTINE`; Occurred at; **Source event
ID=`EVT-COUNT-001`** (machine retry-safe — એ જ ID ફરી મોકલાય તો double-count નહીં).

**Test Case:** TC-OP-PFS-COUNT-01 — એ જ source_event_id 2 વાર → 1 જ count (idempotent).

#### 5.1.4 Device Assembly — Step + Rework + Independent Verify

**શા માટે:** Assembly traceable; Rework default disallow (PFS-FR-027); IND-001 independent check.

| Op | Fields (data) |
|---|---|
| **Record assembly step** | Batch; Assembly step=`Needle install`; Component lot (ref)=`COMP-LOT-001`; Unit identifier=`UNIT-0001`; Equipment; Process parameters (kv, free-form)=`torque`→`2.5`; Result=`Pass`; Rework procedure ref (Rework વખતે ફરજિયાત); Occurred at |
| **Independently verify** | **Assembly record ID = dropdown (3.5, "pick a step someone else performed")**; Expected version |

**Test Cases:** TC-OP-PFS-ASM-01 (Pass) → Success. TC-OP-PFS-ASM-02 (Rework, ref ખાલી) →
`REWORK_ROUTE_REQUIRED`. TC-OP-PFS-ASM-03 (Rework + ref) → Success. TC-OP-PFS-ASM-04 (verify same
user) → IND-001 fail. TC-OP-PFS-ASM-05 (2 જુદા users — `ddcp.operator` + `admin`) → Success.

#### 5.1.5 Functional Tests — QC Link

**"Link a device functional test" (7 fields):** Batch; Test type=`CCI`; QC result (ref)=`QC-001`;
Result=`Pass`; Sample plan ref; Method ref; Linked at.

**Test Case:** TC-OP-PFS-TEST-01 — duplicate batch/test_type/QC-ID → `VALIDATION_FAILED`.

#### 5.1.6 Stability/Retain Samples

**"Record a stability/retain sample reference" (4 fields):** Batch; Plan reference=`STAB-PLAN-01`;
Quantity=`12`; Occurred at.

#### 5.1.7 Batch Readiness — "Batch Production માટે તૈયાર છે?"

**"Check readiness" (4 fields):** Batch; Profile version (RELEASED); Equipment area/line; Filler
equipment. **→ 4 શક્ય blocker:**

| Blocker | ઠીક કરવાની રીત |
|---|---|
| `BULK_NOT_RELEASED` | 5.1.1 મુજબ DRUG handoff accept |
| `PRIMARY_COMPONENT_NOT_RELEASED` | એ જ, DEVICE/Packaging/Label |
| `LINE_NOT_READY` ("Line clearance NOT_STARTED") | **Section 6 જુઓ** |
| `LINE_NOT_READY` ("Filler equipment not eligible") | `/equipment/{id}` → Qualify/Calibrate/Return to service |

#### 5.1.8 Release Readiness Assessment + Evidence Freeze

| Button | API | શું કરે |
|---|---|---|
| **Assess release readiness** | `POST .../release-readiness` | ખરેખર 3 checkpoints (DRUG_CONSTITUENT/DEVICE_CONSTITUENT/COMBINED_PRODUCT) write — official record |
| **Freeze evidence package** | `POST .../evidence-package` | SHA-256-digested, FROZEN, immutable manifest |

**Test Cases:** TC-OP-PFS-REL-01 (Assess) → checkpoints write. TC-OP-PFS-REL-02 (Freeze) → FROZEN.
TC-OP-PFS-REL-03 (ફરી Freeze) → નવો manifest_version.

### 5.2 Autoinjector — 5 Actions

| Action | Fields (data) | Test Case |
|---|---|---|
| **Start assembly operation** | Batch, Released profile, Line=`LINE-AUTO-01`, Equipment=`EQUIP-AUTO-01`, Program=`PROG-INJ-01`/`1` | — |
| **Bind drug container** | Batch, Drug container (ref: Container ID)=`CONT-001`, Injector unit serial=`INJ-SER-0001` | TC-OP-AI-01: એ જ container ફરી bind → `CONTAINER_ALREADY_USED` |
| **Functional test** | Batch, Test type=`ACTIVATION_FORCE`, QC result=`QC-INJ-001`, Sample plan=`SAMPLE-PLAN-INJ-01`, Method=`METHOD-ACT-01`, Result=`PASS` | — |
| **Dose delivery result** | Batch, Sample ID=`DOSE-001`, Measured value=`0.980000`, uom=`mL`, Acceptance rule=`DOSE-ACC-RULE-01` | — |
| **Unit disposition** | Batch, Unit identifier=`INJ-SER-0001`, Result=`Pass`, Reason (Reject/Rework વખતે જરૂરી), NCR/Rework refs | TC-OP-AI-02: Reject+ Reason ખાલી → `VALIDATION_FAILED` |
| **Reusable device pairing** | Reusable device=`PEN-REUSE-01`, Cartridge lot=`CART-LOT-01`, Compatibility=`Compatible`, Rationale, Batch | — (Reusable pen "consume" નથી થતું) |

### 5.3 Inhalation — 5 Actions

| Action | Fields (data) | Test Case |
|---|---|---|
| **Start fill run** | Batch, Released profile, Fill route=`standard-mdi` (profile match જોઈએ), Line/Equipment, Program, **Environment ready = Yes/No (3.4)**, Hold-time rule | TC-OP-INH-01: Fill route mismatch → `FILL_ROUTE_MISMATCH` (422) |
| **Crimp/closure result** | Batch, Unit/sample=`CLOSURE-001`, Measured value=`12.500000`, uom=`N`, Acceptance rule, Test type=`SEAL` | — |
| **Inhaler dose test** | Batch, Test type=`DELIVERED_DOSE`, QC result, Method, Result=`PENDING` | — |
| **Dose counter test** | Batch, Unit/sample=`COUNTER-001`, Program version=`1`, Result=`PASS` | — |
| **Bind dose unit to device** | Batch, Dose unit (ref: Blister ID)=`BLIST-001`, Device=`DEV-001` | TC-OP-INH-02: ફરી bind → `DOSE_UNIT_BINDING_ALREADY_USED` |

### 5.4 Coated Device — 7 Actions

| Action | Fields (data) | Test Case |
|---|---|---|
| **Start coating run** | Batch, Released profile, Line/Equipment, Program, **Environment ready = Yes/No (3.4)**, Initial drug solution=`50.000000 g` | Mass-balance ISSUED entry |
| **Drug/coating usage** | Batch, Usage type=`APPLIED`, Quantity=`35.000000`, uom=`g`, Reason=`ROUTINE`, Occurred at | Mass-balance ledger |
| **Bind device-coating** | Batch, Device unit (ref: Unit ID)=`STENT-UNIT-001`, Coating solution/lot=`COAT-LOT-001` | — |
| **Drug loading result** | Batch, Unit/sample=`LOAD-001`, Measured value=`4.200000`, uom=`mcg`, Acceptance rule, Test type=`COATING_INTEGRITY` | Fail → **OOS**, નહીં FAIL (COAT-FR-016) |
| **Post-sterilization test** | Batch, Sterilization cycle (ref)=`STERIL-CYCLE-001`, Test type=`RELEASE_ELUTION`, QC result, Result=`PENDING` | — |
| **Functional test** | Batch, Test type=`DIMENSIONAL_FUNCTION`, QC result=`QC-COAT-FUNC-001`, Method, Result=`PENDING` | — |
| **Unit disposition** | Batch, Unit identifier=`STENT-UNIT-001`, Result=`Pass`, Reason, Drug/device impact assessment (kv, free-form)=`contaminationRisk`→`low`, Rework procedure ref | TC-OP-COAT-01: Rework, impact assessment ખાલી → block (COAT-FR-025, **બંને** જોઈએ) |

### 5.5 DDCP Operator — Negative Controls

| # | ક્રિયા | Expected |
|---|---|---|
| TC-OP-NEG-01 | `/ddcp` ખોલો — "Profile designer" tab દેખાય? | ❌ ના — "Profile designer hidden" banner |
| TC-OP-NEG-02 | curl થી `POST .../profiles` સીધું call | `403 Forbidden` — Operator ને `ddcp_profile.author` નથી |

---

## 6. Supporting Role: Line Clearance (Operator/Sanitation Operator)

**⚠️ DDCP module નો ભાગ નથી** (Document 39), પણ DDCP readiness એના પર depend કરે છે.

**શા માટે:** Batch શરૂ કરતાં પહેલા equipment line પાછલા batch ના materials/identity થી સાફ છે એ સાબિત
કરવું — cross-contamination ટાળવા. DDCP readiness આ ને `LINE_NOT_READY` તરીકે ચકાસે છે (5.1.7).

**કોણ કરે:** Admin/Operator/Supervisor/Sanitation Operator — sidebar → **"Line clearance"**
(`/line-clearance`).

**"Start line clearance" (unsigned):**

| Field | Data | શા માટે |
|---|---|---|
| Equipment area/line | DDCP readiness ના form માં પસંદ કરેલો એ જ area | Readiness એ જ area_id જુએ |
| Previous/Next batch | Picker | Traceability |
| Checklist version | `LC-CHK-001` | |
| Checklist items (repeat) | item_type=`Equipment`, equipment_id=<asset ID> (optional) | Equipment items eligibility-checked |
| Critical clearance | `Yes`/`No` | Yes → complete વખતે reason ફરજિયાત |

**"Complete (sign)" — ⚠️ signature-required (Document 106 row 111):**

| Field | Data |
|---|---|
| Result | `Pass — area is clear` |
| Expiry (optional) | ISO datetime |
| Reason | Critical હોય તો ફરજિયાત |
| **Password (re-enter)** | login password — Part 11 step-up |

**Test Case:** TC-LC-01 — Start → Complete (Pass) → DDCP readiness ફરી Check → `LINE_NOT_READY` (line
clearance) blocker જતો રહે.

---

# Part C — Cross-Cutting

## 7. Role: Admin — Cross-Check

Admin ને દરેક action અલગથી ટેસ્ટ કરવાની જરૂર નથી (Section 4/5 માં થઈ ગયું) — Admin નો ઉપયોગ ફક્ત:

| # | ક્રિયા | Expected |
|---|---|---|
| TC-ADMIN-01 | `admin` login, `/ddcp` ખોલો | 3 એ 3 tab દેખાય (Engineer+Operator union) |
| TC-ADMIN-02 | ≥1 profile action + ≥1 execution action | બંને succeed |
| TC-ADMIN-03 | Section 2.5 મુજબ test users બનાવવા | ફક્ત Admin કરી શકે (`useRequireAdmin()`) |

---

## 8. Negative-Control Roles

DDCP ની બહારના roles ને access **ના મળવો જોઈએ**:

| # | Login as | Role | Expected UI | Expected backend |
|---|---|---|---|---|
| 1 | `operator1` | Operator | Read-only, tabs hidden | `403 Forbidden` |
| 2 | `qa.reviewer` | QA Reviewer | Read-only, tabs hidden | `403 Forbidden` |
| 3 | `qa.releaser` | QA Releaser | Read-only, tabs hidden | `403 Forbidden` |
| 4 | `qc.reviewer` | QC Reviewer | Read-only, tabs hidden | `403 Forbidden` |

**TC-NEG-01:** કોઈ પણ 1 role login → `/ddcp` → "Read-only" banner, tabs hidden.

---

## 9. સામાન્ય Negative / Error Test Cases

| Test Case | ક્રિયા | Expected |
|---|---|---|
| ખાલી required field | Profile code ખાલી → Create | Button disabled |
| Repeat વગર Release | 0 rows → Release | `PROFILE_RELEASE_BLOCKED` |
| અસ્તિત્વ ના ધરાવતો Batch | Manual-ID random UUID | `NOT_FOUND` |
| Duplicate submit | 2 વાર ઝડપી ક્લિક | 1 જ record (idempotency) |
| Stale version | Expected version=`999` | `STALE_VERSION` |
| Cross-role submit | Section 8 નો negative role | `403 Forbidden` |

---

## 10. Error Codes નો શબ્દકોશ

| Code | અર્થ |
|---|---|
| `NOT_FOUND` | ID અસ્તિત્વમાં નથી |
| `VALIDATION_FAILED` | Duplicate/ખોટી enum value |
| `STALE_VERSION` | Version બદલાયું — ફરી load |
| `INVALID_TRANSITION` | Current state માં action પરવાનગી નથી |
| `PROFILE_SCHEMA_INVALID` | Subtype/constituent_type અજાણી |
| `PROFILE_RELEASE_BLOCKED` | Constituent requirement વગર release |
| `SIGNATURE_POLICY_UNRESOLVED` | Signature policy set નથી (DDCP core actions માટે હવે resolved) |
| `REWORK_ROUTE_REQUIRED` | Rework માટે procedure reference ફરજિયાત |
| `CONTAINER_ALREADY_USED` | Container પહેલેથી bound |
| `DOSE_UNIT_BINDING_ALREADY_USED` | Dose unit પહેલેથી bound |
| `LINE_NOT_READY` | Line/equipment ready નથી (5.1.7/6) |
| `BULK_NOT_RELEASED` | Drug/biologic handoff accepted નથી |
| `PRIMARY_COMPONENT_NOT_RELEASED` | Device/packaging/label handoff accepted નથી |
| `PFS_PROFILE_NOT_EFFECTIVE` | Profile RELEASED નથી |
| `FILL_ROUTE_MISMATCH` | fill_route profile જોડે match નથી |
| `ENVIRONMENT_NOT_READY` / `COATING_ENVIRONMENT_NOT_READY` | "Environment ready" = No (3.4) |
| `403 Forbidden` | Role પાસે permission નથી |

---

## 11. Fix History / જાણીતી મર્યાદાઓ

| # | સ્થિતિ | વિગત |
|---|---|---|
| 1 | ✅ FIXED | Frontend role-check backend RBAC સાથે મેચ નહોતું — `canAuthorProfile`/`canExecute` |
| 2 | ✅ FIXED | Readiness form માં `profile_version_id` field નહોતું |
| 3 | ✅ FIXED (PFS only) | Handoff decide, fill sub-actions, assembly verify UI |
| 4 | ✅ RESOLVED | Signature policy — profile release/handoff decide/fill start+complete હવે unblocked |
| 5 | ✅ FIXED | Line Clearance UI (`/line-clearance`, Section 6) |
| 6 | ✅ FIXED | Readiness/Genealogy/Review-summary raw JSON → tables/KPI tiles |
| 7 | ✅ FIXED (v2) | Environment status kv → Yes/No control (Section 3.4) |
| 8 | ✅ FIXED (v2) | Handoff/Fill-operation/Assembly-record ID fields → dynamic session dropdown (Section 3.5) |
| 9 | ✅ DOC (v2) | Free-form kv fields ના hint હવે explicit "not validated" કહે છે (Section 3.4) |
| 10 | ⚠️ ખુલ્લું | PFS `required_controls.serialization.required` — nested key, flat kv editor produce ના કરી શકે (reporting-only, non-blocking) |
| 11 | ⚠️ ખુલ્લું | Autoinjector/Inhalation/Coated — "Complete run" op UI માં નથી (backend function છે) |
| 12 | ⚠️ ખુલ્લું | DDCP Engineer/Operator demo user seeded નથી — Section 2.5 મુજબ જાતે બનાવવા |

---

## 12. Traceability Sheet

| Test Case ID | Role | Status | Executed by | Executed at | Actual result / Defect ref |
|---|---|---|---|---|---|
| TC-ENG-PFS-01..06, TC-ENG-NEG-01..02 | DDCP Engineer | | | | |
| TC-ENG-AUTO/INH/COAT (Section 4.2-4.4) | DDCP Engineer | | | | |
| TC-OP-PFS-HAND/FILL/COUNT/ASM/TEST/REL, TC-OP-NEG-01..02 | DDCP Operator | | | | |
| TC-OP-AI-01..02, TC-OP-INH-01..02, TC-OP-COAT-01 | DDCP Operator | | | | |
| TC-LC-01 | Operator/Sanitation Operator | | | | |
| TC-ADMIN-01..03 | Admin | | | | |
| TC-NEG-01 | Negative-control roles | | | | |

---

*આ document 3 જૂના DDCP testing doc નું v2 consolidation છે — role-wise restructure + settings-field
honesty + dynamic id-picker fixes. બધું backend code (`app/modules/ddcp/*.py`,
`app/modules/equipment/cleaning_*.py`, `scripts/seed.py`) અને frontend code (`frontend/src/app/ddcp/*`,
`frontend/src/app/line-clearance/*`, `frontend/src/components/ddcp/*`) માંથી verified — કંઈ પણ
guess/fabricate નથી કરેલું.*
