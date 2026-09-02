# DDCP (Drug-Device Combination Product) — વિગતવાર Manual Test Guide (ગુજરાતીમાં)

**દસ્તાવેજ સંદર્ભ:** Documents 54–57 (SPEC-DDCP-001/002/003/004)
**મોડ્યુલ:** `services/gxp-api/app/modules/ddcp/` (backend), `frontend/src/app/ddcp/page.tsx` (UI)
**તારીખ:** 2026-09-02

---

## અનુક્રમણિકા (Index)

1. [DDCP એટલે શું અને શા માટે છે](#1-ddcp-એટલે-શું-અને-શા-માટે-છે)
2. [Browser માં Frontend કેવી રીતે Access કરવું](#2-browser-માં-frontend-કેવી-રીતે-access-કરવું)
3. [Login કેવી રીતે કરવું](#3-login-કેવી-રીતે-કરવું)
4. [DDCP પેજનું માળખું (Page Structure)](#4-ddcp-પેજનું-માળખું-page-structure)
5. [Product Family Selector — 4 પ્રકારના પ્રોડક્ટ](#5-product-family-selector--4-પ્રકારના-પ્રોડક્ટ)
6. [Card 1 — Profile Designer (વિગતવાર)](#6-card-1--profile-designer-વિગતવાર)
7. [Card 2 — Batch Readiness & Release (વિગતવાર)](#7-card-2--batch-readiness--release-વિગતવાર)
8. [Card 3 — Execution & Result Records (વિગતવાર)](#8-card-3--execution--result-records-વિગતવાર)
9. [Prefilled Syringe (PFS) — Step-by-Step Test Cases](#9-prefilled-syringe-pfs--step-by-step-test-cases)
10. [Autoinjector (Document 55) — Fields ની સમજ](#10-autoinjector-document-55--fields-ની-સમજ)
11. [Inhalation MDI/DPI (Document 56) — Fields ની સમજ](#11-inhalation-mdidpi-document-56--fields-ની-સમજ)
12. [Coated / Combination Device (Document 57) — Fields ની સમજ](#12-coated--combination-device-document-57--fields-ની-સમજ)
13. [Negative / Error Test Cases (બધા પ્રકાર માટે સામાન્ય)](#13-negative--error-test-cases-બધા-પ્રકાર-માટે-સામાન્ય)
14. [Error Codes નો શબ્દકોશ](#14-error-codes-નો-શબ્દકોશ)
15. [જાણીતી મર્યાદાઓ (Known Limitations)](#15-જાણીતી-મર્યાદાઓ-known-limitations)

---

## 1. DDCP એટલે શું અને શા માટે છે

**DDCP = Drug-Device Combination Product** (દવા + ડિવાઇસ નું સંયુક્ત ઉત્પાદન). આ એવા પ્રોડક્ટ છે જેમાં
દવા (drug) અને એક મિકેનિકલ ડિવાઇસ (device) બંને એકસાથે એક જ યુનિટમાં હોય છે — દા.ત.:

| પ્રકાર (Type) | ઉદાહરણ | Document |
|---|---|---|
| **Prefilled Syringe (PFS)** | પહેલેથી ભરેલી સિરીંજ (injectable) | Document 54 |
| **Autoinjector** | Pen-injector, single-use અથવા reusable injector | Document 55 |
| **Inhalation (MDI/DPI)** | Inhaler (અસ્થમા/શ્વાસ માટે), metered-dose કે dry-powder | Document 56 |
| **Coated / Combination Device** | Drug-eluting stent જેવું ડિવાઇસ જેના પર દવાનું coating હોય | Document 57 |

**શા માટે આ regulated (નિયંત્રિત) છે?** આ પ્રોડક્ટ FDA ના combination-product નિયમો હેઠળ આવે છે —
એટલે drug ની ગુણવત્તા અને device ની ગુણવત્તા, બંને એકસાથે સાબિત કરવા પડે, અને બંને ને જોડતી (link કરતી)
દરેક ક્રિયા — કયું drug lot કયા device unit સાથે ગયું, કયું ટેસ્ટ pass/fail થયું, કોણે assemble કર્યું, કોણે
verify કર્યું — બધું જ કાયમી રીતે (permanently), છેડછાડ-ના-થાય-તેવી (tamper-proof) રીતે રેકોર્ડ થવું જોઈએ.

**Application માં DDCP નો hetu (purpose):**
1. **Profile** બનાવવો — એટલે કે આ પ્રોડક્ટ ના "recipe"/"spec" ને define કરવો (કયા constituents જોઈએ,
   કયા controls જોઈએ).
2. **Batch execution** દરમિયાન દરેક પગલું (fill, assembly, coating વગેરે) રેકોર્ડ કરવો.
3. **Release readiness** ચકાસવી — batch release કરવા લાયક છે કે નહીં, 3 checkpoints પર.
4. **Evidence package** freeze કરવો — QA/regulatory review માટે કાયમી પુરાવો.

---

## 2. Browser માં Frontend કેવી રીતે Access કરવું

Application નું frontend (UI) અને backend (API) બંને હવે internet પર reachable છે (temporary, testing
માટે ખોલેલા છે):

| વસ્તુ | URL |
|---|---|
| **Frontend (UI) — આ URL browser માં ખોલો** | `http://88.99.15.183:4101` |
| Backend API (UI પોતે આનો ઉપયોગ કરે છે, સીધું ખોલવાની જરૂર નથી) | `http://88.99.15.183:8010` |

**નોંધ:** આ IP address અને port temporary testing માટે ખુલ્લા રાખેલા છે (firewall માં rule ઉમેરેલો છે).
Testing પૂરું થાય પછી બંધ કરી શકાય છે.

Browser માં ઉપરનું frontend URL ખોલો → સીધું **Login** પેજ ખૂલશે.

---

## 3. Login કેવી રીતે કરવું

| Field | શું ભરવું | શા માટે |
|---|---|---|
| **Username** | `admin` | આ demo/test user છે, જેને બધા 26 roles આપેલા છે — એટલે DDCP ના બધા features access કરી શકશો. |
| **Password** | `ChangeMe123!` | બધા demo user માટે એક જ password (default). |

Login પછી **Site** પસંદ કરવાનું આવી શકે — `SITE1` પસંદ કરો (આ demo organization નું એકમાત્ર site છે).

**શા માટે Login જરૂરી છે?** આ regulated system છે (21 CFR Part 11 મુજબ) — દરેક action કોણે કર્યું તે
identify (ઓળખ) થવું જ જોઈએ. "Login/MFA એ પોતે electronic signature નથી" (AG-07) — signature ની જરૂર
હોય તેવી ક્રિયાઓ માટે અલગથી password ફરીથી નાખવો પડે છે (નીચે જુઓ).

Login પછી ડાબી બાજુ (Sidebar) માં **"DDCP"** લિંક પર ક્લિક કરો, અથવા સીધું browser માં આ URL ખોલો:
`http://88.99.15.183:4101/ddcp`

---

## 4. DDCP પેજનું માળખું (Page Structure)

પેજ ખૂલતાં જ ઉપરથી નીચે આ ક્રમમાં દેખાશે:

1. **Page Title**: "DDCP product profiles" — સાથે subtitle જે Documents 54–57 નો ઉલ્લેખ કરે છે.
2. **Product family selector** (Dropdown) — 4 માંથી 1 પ્રોડક્ટ-પ્રકાર પસંદ કરવાનું.
3. **(જો role match ના થાય તો) "Read-only" Banner** — જુઓ નીચે.
4. **Card 1: Profile Designer** — નવો profile version બનાવવો, release કરવો, lookup કરવો.
5. **Card 2: Batch Readiness & Release** — batch ની readiness check કરવી, evidence freeze કરવી.
6. **Card 3: Execution & Result Records** — actual production/testing ડેટા submit કરવો.

**Role check શા માટે?** Card 1 અને Card 3 ફક્ત ત્યારે જ દેખાય છે જ્યારે logged-in user પાસે **Admin**,
**QA Reviewer**, અથવા **Supervisor** — આમાંથી કોઈ 1 role હોય (`admin` user પાસે બધા roles છે, એટલે બધું
દેખાશે). આ segregation-of-duties (SoD) નું UI-level reflection છે — regulated data ફક્ત authorized
લોકો જ author/release કરી શકે, બાકીના ફક્ત વાંચી (read) શકે.

---

## 5. Product Family Selector — 4 પ્રકારના પ્રોડક્ટ

પેજ ની ટોચ પર **"Product family"** નામનું dropdown છે:

| Dropdown Value | અંદર શું બદલાય છે |
|---|---|
| Prefilled syringe / injectable (Doc 54) | API prefix `/ddcp/v1/prefilled-syringe` — સૌથી વધારે features (genealogy, review-summary બધું છે) |
| Autoinjector (Doc 55) | API prefix `/ddcp/v1/autoinjector` |
| Inhalation — MDI / DPI (Doc 56) | API prefix `/ddcp/v1/inhalation` |
| Coated / combination device (Doc 57) | API prefix `/ddcp/v1/coated-device` |

**આ dropdown શા માટે છે?** ચારેય પ્રોડક્ટ-પ્રકાર ને પોતાનું અલગ backend module છે (અલગ tables, અલગ
commands), પણ UI pattern (profile → batch readiness → execution) બધા માટે same છે. એટલે 1 જ પેજ,
dropdown બદલવાથી નીચેના બધા cards એ પ્રોડક્ટ-પ્રકારના સાચા API endpoints પર call કરવા લાગે છે.

**Test Case 5.1 — Dropdown બદલવાની ચકાસણી**
1. Dropdown ને "Prefilled syringe" પર રાખો.
2. Card 3 (Execution) માં "Operation" dropdown ખોલો — `constituent-handoffs`, `fill-operations` વગેરે 6
   options દેખાવા જોઈએ.
3. હવે ટોચ ના dropdown ને "Autoinjector" પર બદલો.
4. Card 3 નું "Operation" dropdown ફરીથી ખોલો — હવે `assembly-operations`, `drug-container-bindings`
   વગેરે 6 જુદા options દેખાવા જોઈએ (કારણકે code માં "family change પર stale selection ના રહે" એવું
   ખાસ logic છે).
5. **અપેક્ષિત પરિણામ (Expected):** Operation list તરત બદલાય, અને પહેલા selected value જો નવી list માં
   ના હોય તો પહેલો option auto-select થાય.

---

## 6. Card 1 — Profile Designer (વિગતવાર)

**આ card શું છે?** પ્રોડક્ટ ની "profile" (spec/recipe) બનાવવા અને release કરવા માટે.
**Profile એટલે શું?** — batch શરૂ કરતાં પહેલા define કરવું પડે કે આ પ્રોડક્ટ માં કયા constituents
(drug/device/packaging/label) જોઈએ, કયા controls જોઈએ. જ્યાં સુધી profile **RELEASED** ના થાય ત્યાં
સુધી કોઈ batch એ profile વાપરીને શરૂ ના થઈ શકે.

### 6.1 "Create profile version" Form

| Field | શું છે | શા માટે |
|---|---|---|
| **Profile code** *(required)* | પ્રોડક્ટ નો unique code, દા.ત. `PFS-DEMO-001` | આ profile ને ઓળખવા માટે નું નામ. Site + profile_code + version — 3 ભેગા મળીને unique key બને છે (database માં `UniqueConstraint`). |
| **Subtype** | દા.ત. PFS માટે `PREFILLED_SYRINGE`, `CARTRIDGE`, `VIAL_DEVICE_COPACK`, `OTHER_INJECTABLE` | પ્રોડક્ટ નો ચોક્કસ પેટા-પ્રકાર. ખોટો subtype આપશો તો `ProfileSchemaInvalidError` (400) આવશે. |
| **Constituent architecture (JSON)** | દા.ત. `{"sterileProcess": true}` | Document 54 §6 ના TS schema પ્રમાણે — sterile flags, fill control rule ids વગેરે structured માહિતી. Database માં JSONB તરીકે store થાય છે (દરેક field માટે અલગ column નથી બનાવ્યું — flexible schema). |
| **Required controls (JSON)** | દા.ત. `{"visualInspectionProfile": "VI-001"}` | કયા controls (CCI profile, visual inspection profile વગેરે) આ પ્રોડક્ટ માટે ફરજિયાત છે. |
| **Constituent requirements (JSON array)** *(ઓછામાં ઓછું 1 જોઈએ, release પહેલા)* | `[{"constituent_type": "DRUG", "component_role": "bulk_drug", "required_state": "RELEASED"}]` | આ profile માટે કયા-કયા constituent (DRUG/BIOLOGIC/DEVICE/PACKAGING/LABEL) જોઈએ, અને દરેક કઈ state માં (RELEASED/READY_TO_USE/STERILIZED/DEPYROGENATED) હોવો જોઈએ. **આ ખાલી હોય તો profile ક્યારેય release નહીં થાય** — backend માં check છે: "A profile version needs at least one constituent requirement before release". |

**"Create profile version" Button:**
- **ક્યારે disabled રહે:** જ્યાં સુધી "Profile code" ખાલી હોય અથવા submit ચાલુ હોય ત્યાં સુધી.
- **ક્લિક કરવાથી શું થાય:** `POST /ddcp/v1/{prefix}/profiles` call જાય છે. નવો profile **DRAFT** state
  માં બને છે, version = 1 (અથવા એ જ profile_code નું છેલ્લું version + 1).
- **શા માટે "DRAFT" state થી શરૂ થાય:** કારણકે profile હજુ review/release નથી થયો — DRAFT state માં
  ફેરફાર કરી શકાય, પણ કોઈ batch એને વાપરી ના શકે.
- **Idempotency:** દરેક submit સાથે એક unique `idempotency_key` auto-generate થઈને જાય છે — જો network
  glitch થી બે વાર click થઈ જાય, તો બીજી વાર database માં duplicate profile **નહીં** બને (same receipt
  પાછું મળશે).

**Test Case 6.1.1 — સફળ Profile Creation**
1. Profile code: `PFS-TEST-001`
2. Subtype: `PREFILLED_SYRINGE`
3. Constituent architecture: `{"sterileProcess": true}`
4. Required controls: `{}`
5. Constituent requirements:
   ```json
   [{"constituent_type": "DRUG", "component_role": "bulk_drug", "required_state": "RELEASED"}]
   ```
6. "Create profile version" પર ક્લિક કરો.
7. **Expected:** લીલા (ok) રંગનું banner — "Profile version created (draft)" — સાથે નવો Profile ID
   દેખાય. આ ID copy કરી લો (નીચેના steps માટે જોઈશે).

**Test Case 6.1.2 — Invalid Subtype**
1. Subtype ફિલ્ડમાં `XYZ` (ખોટી value) નાખો.
2. Create પર ક્લિક કરો.
3. **Expected:** Error — `PROFILE_SCHEMA_INVALID` — "Unrecognized subtype".

**Test Case 6.1.3 — Invalid JSON**
1. "Constituent architecture" ફિલ્ડમાં `{invalid json` (અધૂરું JSON) લખો.
2. Create પર ક્લિક કરો.
3. **Expected:** Error — "Invalid JSON: ..." (frontend પોતે JSON.parse કરે છે, submit પહેલા જ પકડાય છે).

### 6.2 "Release a profile version" Form

| Field | શું છે | શા માટે |
|---|---|---|
| **Profile ID** | ઉપર બનાવેલા profile નું ID (auto-filled થઈ જાય છે create પછી) | કયો profile release કરવો છે તે ઓળખવા. |
| **Expected version** | Number, default `1` | **Optimistic concurrency control** — જો કોઈ બીજા user એ આ profile ને વચ્ચે બદલી નાખ્યો હોય (version વધી ગયું હોય), તો release **નિષ્ફળ** જશે (`StaleVersionError`) — એટલે તમે જૂની માહિતી પર blind release ના કરી શકો. |
| **Change ref** | Optional free text | Change control સાથે link કરવા માટે (દા.ત. "CHG-2026-045") — audit trail માં reason તરીકે સચવાય છે. |

**"Release" Button:**
- **ક્લિક કરવાથી શું થાય:** `POST /ddcp/v1/{prefix}/profiles/{id}/release`.
- **શા માટે આ ક્રિયા મહત્વની છે:** Release પછી જ profile **immutable** (અફર) બની જાય છે — DRAFT માંથી
  **RELEASED** state માં જાય. જૂનું RELEASED version (જો કોઈ હોય) આપોઆપ **SUPERSEDED** થઈ જાય છે —
  એટલે એક સમયે profile_code દીઠ ફક્ત 1 જ version "current released" હોય.
  **Release ત્યારે જ થઈ શકે જ્યારે:**
  1. Profile હાલમાં DRAFT state માં હોય (પહેલેથી RELEASED હોય તો `InvalidTransitionError`).
  2. ઓછામાં ઓછો 1 constituent requirement હોય (નહીં તો `ProfileReleaseBlockedError`).
- **Signature ceremony:** આ action code માં signature-required તરીકે wired છે
  (`resolve_signature_requirement(record_type="ddcp_profile_version", action="release")`) — પણ
  Document 106 (signature policy baseline) માં DDCP માટે હજુ કોઈ row નથી, એટલે backend
  **fail-closed** રહેશે — `SIGNATURE_POLICY_UNRESOLVED` (409) error આવશે. **આ bug નથી** — આ ઈરાદાપૂર્વક
  ડિઝાઇન છે: જ્યાં સુધી Quality/Regulatory team સત્તાવાર રીતે "release" ક્રિયા માટે signature ની
  meaning/role નક્કી ના કરે, ત્યાં સુધી system કોઈને પણ "guess" કરીને sign કરવા નહીં દે.

**Test Case 6.2.1 — Release (હાલમાં blocked રહેશે)**
1. Profile ID: (6.1.1 માંથી મળેલું ID)
2. Expected version: `1`
3. Change ref: `CHG-TEST-001`
4. "Release" પર ક્લિક કરો.
5. **Expected (અત્યારના તબક્કે):** `SIGNATURE_POLICY_UNRESOLVED` error. આ સાબિત કરે છે કે system correctly
   fail-closed છે — release signature policy set ના થાય ત્યાં સુધી કોઈ profile release ના થઈ શકે.

**Test Case 6.2.2 — Stale Version**
1. Expected version માં `999` (ખોટો number) નાખો.
2. Release ક્લિક કરો.
3. **Expected:** `STALE_VERSION` error — "Profile version was modified since it was read".

**Test Case 6.2.3 — Constituent Requirement વગર Release**
1. નવો profile બનાવો પણ "Constituent requirements" ખાલી (`[]`) રાખો.
2. Release કરવાનો પ્રયત્ન કરો.
3. **Expected:** `PROFILE_RELEASE_BLOCKED` — "A profile version needs at least one constituent
   requirement before release" (signature check પહેલા જ આ check થાય છે).

### 6.3 "Look up a profile version" Form (ફક્ત PFS માટે)

| Field | શું છે |
|---|---|
| **Profile ID** | કોઈ પણ profile નું ID |

**"Look up" Button** (🔍 icon સાથે):
- **ક્યારે દેખાય:** ફક્ત Prefilled Syringe માટે (`hasProfileGet: true`) — બીજા 3 પ્રોડક્ટ-પ્રકાર માટે
  backend માં GET-by-id endpoint હજુ બન્યું નથી, એટલે UI એ button જ નથી બતાવતું (honest UI — ના હોય
  તેવી વસ્તુ બતાવવી નહીં).
- **ક્લિક કરવાથી શું થાય:** `GET /ddcp/v1/prefilled-syringe/profiles/{id}` — profile ID, code, subtype,
  version, state — JSON panel માં દેખાય.

**Test Case 6.3.1**
1. 6.1.1 નું Profile ID lookup box માં નાખો → Look up ક્લિક કરો.
2. **Expected:** JSON panel માં `state: "DRAFT"` દેખાય (કારણકે release blocked છે, હજુ DRAFT જ છે).

---

## 7. Card 2 — Batch Readiness & Release (વિગતવાર)

**આ card શું છે?** કોઈ ચોક્કસ **batch** (ઉત્પાદન batch, જે પહેલેથી `/batches` module માં બનેલો હોવો
જોઈએ) DDCP પ્રોડક્શન શરૂ કરવા માટે તૈયાર (ready) છે કે નહીં — તે ચકાસવા માટે, અને છેલ્લે release
readiness + evidence freeze કરવા માટે.

| Field | શું છે | શા માટે |
|---|---|---|
| **Batch ID** | એક `ebmr.batches` batch નું UUID | આ કયા batch માટે ડેટા જોવો/ક્રિયા કરવી છે તે ઓળખવા. |

**"Load" Button** (🔍 icon):
- **ક્લિક કરવાથી શું થાય:** 3 GET calls (parallel નહીં, sequential):
  1. `GET /batches/{id}/readiness` — **હંમેશા** call થાય છે.
  2. `GET /batches/{id}/genealogy` — ફક્ત `hasGenealogy: true` હોય તો (PFS અને Inhalation માટે).
  3. `GET /batches/{id}/review-summary` — ફક્ત PFS માટે (`hasReviewSummary: true`).
- **શા માટે readiness ને `profile_version_id` જોઈએ (પણ UI માં આ field નથી!):** *(જાણીતી મર્યાદા —
  જુઓ Section 15)* backend નું `readiness` endpoint ને query parameter તરીકે `profile_version_id`
  જોઈએ, પણ current UI form માં એ ફિલ્ડ **નથી** — એટલે "Load" ક્લિક કરવાથી `422 Unprocessable Entity`
  (missing required query param) આવી શકે છે. આ backend થી direct API call કરીને test કરવું પડશે
  (નીચે જુઓ).

**Readiness ના 3 Checkpoint Codes (backend logic):**

| Checkpoint | ક્યારે SATISFIED | ક્યારે BLOCKED |
|---|---|---|
| **DRUG_CONSTITUENT** | Drug/biologic નો handoff **ACCEPTED** state માં હોય | કોઈ accepted drug/biologic handoff ના મળે (`BULK_NOT_RELEASED`) |
| **DEVICE_CONSTITUENT** | બધા device handoffs accepted હોય, અને કોઈ functional test fail ના હોય | Pending device handoff (`PRIMARY_COMPONENT_NOT_RELEASED`) અથવા failed test (`DEVICE_TEST_FAILED`) |
| **COMBINED_PRODUCT** | ઉપરના બંને + કોઈ fill operation hold માં ના હોય + ઓછામાં ઓછો 1 FILLED count હોય | ઉપરના blockers, અથવા open hold (`PFS_RECONCILIATION_FAILED`) |

**Buttons (readiness data load થયા પછી જ દેખાય છે):**

| Button | ક્યારે દેખાય | ક્લિક કરવાથી શું થાય | શા માટે |
|---|---|---|---|
| **Assess release readiness** | ફક્ત authorized role (Admin/QA Reviewer/Supervisor) માટે | `POST /batches/{id}/release-readiness` — ઉપરના 3 checkpoints ને ફરીથી calculate કરીને database માં `DdcpReleaseCheckpoint` rows update/insert કરે છે. | આ **write** action છે (પહેલાનું "Load" ફક્ત read હતું) — checkpoint state ને database માં "official" તરીકે lock કરવા. |
| **Freeze evidence package** | એ જ role check | `POST /batches/{id}/evidence-package` — batch ના બધા regulated records (handoffs, fill ops, assembly records, test links, checkpoints) ના id+version ને ભેગા કરીને, એક SHA-256 digest બનાવીને, **FROZEN** (અફર) evidence manifest બનાવે છે. | આ QA/regulatory review માટે "આ ક્ષણે batch ની સંપૂર્ણ સ્થિતિ શું હતી" તેનો કાયમી, ચેડાં-ના-થાય-તેવો પુરાવો છે. Manifest ને ફરી edit ના કરી શકાય — નવી evidence package જોઈએ તો નવું `manifest_version` બને છે. |

**Test Case 7.1 — Batch Readiness Load (UI મર્યાદા સાથે)**
1. કોઈ પણ existing batch નું ID નાખો.
2. "Load" ક્લિક કરો.
3. **Expected (UI limitation):** `profile_version_id` query param ના મોકલવાથી error આવી શકે. આ
   backend/frontend વચ્ચેનું known gap છે (જુઓ Section 15) — backend ને સીધું curl/Postman થી ટેસ્ટ
   કરવા માટે:
   ```
   GET http://88.99.15.183:8010/ddcp/v1/prefilled-syringe/batches/{batch_id}/readiness?profile_version_id={profile_id}
   ```

---

## 8. Card 3 — Execution & Result Records (વિગતવાર)

**આ card શું છે?** Batch execution દરમિયાન થતી actual production/testing ક્રિયાઓ રેકોર્ડ કરવા માટે —
દા.ત. fill operation શરૂ કરવી, device assembly step રેકોર્ડ કરવો, functional test link કરવો.

**શા માટે JSON textarea, typed form નહીં?** આ page ની નોંધ મુજબ: "The execution, IPC and
functional-test records for this family carry structured payloads — submit them here as JSON." —
દરેક operation નું payload (data structure) deeply nested છે (દા.ત. `product_contact_path`,
`process_parameters` — બધા JSON objects), એટલે એક generic JSON form વાપરવો વધુ પ્રામાણિક (honest) છે
typed fields ની ખોટી ધારણા (guess) કરવા કરતાં.

| Field | શું છે | શા માટે |
|---|---|---|
| **Operation** (dropdown) | કયું action કરવું — પસંદ કરેલા પ્રોડક્ટ-પ્રકાર પ્રમાણે 5-7 options | નીચે dropdown ના options ની list આપેલી છે, પ્રોડક્ટ-પ્રકાર પ્રમાણે. |
| **Payload (JSON)** | Selected operation નું data — textarea માં JSON | Command ના fields — table નીચે આપેલા છે. |

**"Submit" Button:**
- **ક્લિક કરવાથી શું થાય:** `POST {prefix}/{operation}` — JSON body ને parse કરીને, `idempotency_key`
  automatically ઉમેરીને મોકલે છે.
- **Result:** સફળ થાય તો "OK — command {id}" દેખાય; નિષ્ફળ થાય તો error code + message.

### 8.1 Prefilled Syringe (PFS) ના 6 Operations

| Operation (dropdown) | Backend Function | જરૂરી Fields (JSON keys) | શું કરે છે |
|---|---|---|---|
| `constituent-handoffs` | `record_constituent_handoff` | `batch_id`, `from_constituent` (DRUG/BIOLOGIC/DEVICE/PACKAGING/LABEL), `to_constituent`, `source_batch_reference` (`{"batch_id":...}` અથવા `{"lot_id":...}`), `attributes` | કોઈ constituent (દા.ત. bulk drug) ને batch માટે "handoff" તરીકે નોંધવો — PENDING state માં શરૂ થાય, પછી accept/reject કરવો પડે (હાલ UI માં decide કરવાનું form નથી — SectionN 15 જુઓ). |
| `fill-operations` | `start_filling_stage` | `batch_id`, `profile_version_id`, `line_id`, `filler_equipment_id`, `fill_program_id`, `fill_program_version`, `product_contact_path`, `target_fill` (decimal string), `target_fill_uom`, `cycle_group` | Filling stage શરૂ કરવો. **પહેલા batch readiness ready હોવી જ જોઈએ** (નહીં તો `LineNotReadyError`/`BulkNotReleasedError` વગેરે). |
| `production-counts` | `record_syringe_unit_or_count` | `batch_id`, `count_type` (FILLED/REJECTED_VISUAL/REJECTED_IPC/SAMPLED/LINE_LOSS/PACKED), `source` (MACHINE/MANUAL/RECONCILIATION), `quantity`, `uom`, `device_reference`, `reason_code`, `occurred_at`, `source_event_id` | Unit counts (કેટલા ભરાયા, કેટલા reject થયા વગેરે) નોંધવા — append-only ledger. `source_event_id` આપો તો, એ જ event ફરીથી મોકલાય તો પણ **double-count નહીં થાય** (machine retry protection). |
| `device-assembly` | `record_device_assembly_step` | `batch_id`, `assembly_step` (દા.ત. NEEDLE_INSTALL, SHIELD, TIP_CAP...), `component_lot_reference`, `unit_identifier`, `equipment_id`, `process_parameters`, `result` (PASS/FAIL/REWORK), `rework_procedure_reference` | Device assembly નું 1 પગલું (step) નોંધવો. **REWORK result આપવા માટે `rework_procedure_reference` ફરજિયાત છે** — નહીં તો `ReworkRouteRequiredError` (default rework disallowed). |
| `functional-tests` | `record_pfs_functional_test` | `batch_id`, `test_type` (CCI/LEAK/SEAL/GLIDE_FORCE/DOSE_DELIVERY વગેરે), `qc_record_reference`, `result_state` (PENDING/PASS/FAIL/OOS), `sample_plan_reference`, `method_reference` | QC test result ને batch સાથે link કરવો. **QC ની actual value અહીં store નથી થતી** — ફક્ત QC module ના result ની reference (id) store થાય છે (data duplication ટાળવા). |
| `stability-retain-samples` | `record_stability_retain_reference` | `batch_id`, `plan_reference`, `quantity`, `occurred_at` | Stability/retain sample plan ની reference નોંધવી. |

### 8.2 Payload ઉદાહરણો (Copy-Paste કરી શકાય)

**Constituent handoff:**
```json
{
  "batch_id": "<તમારો batch id>",
  "from_constituent": "DRUG",
  "to_constituent": "bulk_drug",
  "source_batch_reference": {"batch_id": "<upstream bulk batch id>"},
  "attributes": {}
}
```

**Fill operation start:**
```json
{
  "batch_id": "<batch id>",
  "profile_version_id": "<released profile id>",
  "line_id": "<equipment area id>",
  "filler_equipment_id": "<equipment asset id>",
  "fill_program_id": "PROG-001",
  "fill_program_version": "1",
  "product_contact_path": {"path": "standard"},
  "target_fill": "1.000000",
  "target_fill_uom": "mL"
}
```

**Device assembly step:**
```json
{
  "batch_id": "<batch id>",
  "assembly_step": "NEEDLE_INSTALL",
  "component_lot_reference": {"lot_id": "COMP-LOT-001"},
  "result": "PASS"
}
```

**Functional test:**
```json
{
  "batch_id": "<batch id>",
  "test_type": "CCI",
  "qc_record_reference": {"record_id": "<qc result id>"},
  "result_state": "PASS"
}
```

---

## 9. Prefilled Syringe (PFS) — Step-by-Step Test Cases

આ section માં એક **સંપૂર્ણ end-to-end test scenario** આપેલો છે, જે actual regulated workflow ને
mimic (અનુસરે) કરે છે.

### TC-DDCP-PFS-01 — Profile બનાવવો અને release કરવાનો પ્રયત્ન
| Step | ક્રિયા | Expected Result |
|---|---|---|
| 1 | Product family = "Prefilled syringe" પસંદ કરો | Cards બદલાય |
| 2 | Profile Designer માં profile code `PFS-E2E-01`, subtype `PREFILLED_SYRINGE`, 1 constituent requirement (DRUG/bulk_drug/RELEASED) સાથે profile બનાવો | DRAFT profile બને, ID મળે |
| 3 | એ જ ID થી Release કરવાનો પ્રયત્ન કરો | `SIGNATURE_POLICY_UNRESOLVED` (409) — expected, spec-gap SG-167/172 ના class નું જ છે |
| 4 | Lookup form માં એ જ ID નાખો | Profile state = `DRAFT` દેખાય |

### TC-DDCP-PFS-02 — Constituent Handoff Flow
| Step | ક્રિયા | Expected Result |
|---|---|---|
| 1 | Execution card માં Operation = `constituent-handoffs` પસંદ કરો | |
| 2 | Payload માં valid `batch_id` (existing batch), `from_constituent: "DRUG"`, `to_constituent: "bulk_drug"`, `source_batch_reference: {"batch_id": "<કોઈ existing batch>"}` નાખો | |
| 3 | Submit કરો | "OK — command ..." દેખાય, નવો handoff **PENDING** state માં બને |
| 4 | એ જ batch_id/from/to/source સાથે ફરીથી submit કરો | `VALIDATION_FAILED` — "A handoff for this batch/constituent/source already exists" (duplicate detection) |

### TC-DDCP-PFS-03 — Device Assembly + Rework Rule
| Step | ક્રિયા | Expected Result |
|---|---|---|
| 1 | Operation = `device-assembly`, `result: "PASS"` સાથે submit કરો | સફળ |
| 2 | ફરીથી, `result: "REWORK"` પણ `rework_procedure_reference` વગર submit કરો | `REWORK_ROUTE_REQUIRED` error — "Filled primary container rework/reprocessing is disallowed by default (PFS-FR-027)" |
| 3 | `result: "REWORK"` + `rework_procedure_reference: {"procedure_id": "REWORK-SOP-01"}` સાથે submit કરો | સફળ |

### TC-DDCP-PFS-04 — Functional Test Duplicate Check
| Step | ક્રિયા | Expected Result |
|---|---|---|
| 1 | `test_type: "CCI"`, `qc_record_reference: {"record_id": "QC-001"}` સાથે submit કરો | સફળ |
| 2 | એ જ batch, એ જ test_type, એ જ `record_id` સાથે ફરીથી submit કરો | `VALIDATION_FAILED` — "This qc_record_reference is already linked for this batch/test_type" |

---

## 10. Autoinjector (Document 55) — Fields ની સમજ

Product family dropdown માં "Autoinjector" પસંદ કરો. Profile Designer card એ જ રીતે કામ કરે છે (subtype
હવે `AUTOINJECTOR`, `PEN_SINGLE_USE`, `PEN_REUSABLE`, `CARTRIDGE_SYSTEM` માંથી પસંદ કરવો). Batch card
માં Genealogy/Review-summary **નથી દેખાતા** (`hasGenealogy: false`, `hasReviewSummary: false`) — ફક્ત
Readiness.

| Operation | Backend Function | મુખ્ય Fields | શું કરે છે |
|---|---|---|---|
| `assembly-operations` | `start_injector_assembly_operation` | `batch_id`, `profile_version_id`, `line_id`, `equipment_id`, `program_id`, `program_version` | Injector assembly run શરૂ કરવો |
| `drug-container-bindings` | `bind_drug_container_to_injector_unit` | `batch_id`, `drug_container_reference` (`{"container_id":...}` અથવા `{"lot_id":...}`), `injector_unit_serial` | એક drug container ને એક injector unit સાથે (serial number દ્વારા) જોડવો — **1 container ફક્ત 1 જ unit સાથે** જોડાય શકે (`CONTAINER_ALREADY_USED` error નહીં તો) |
| `functional-tests` | `execute_injector_functional_test` | `batch_id`, `test_type`, `qc_record_reference`, `result_state` | Injector નું functional test (activation force, dose accuracy વગેરે) |
| `dose-delivery-results` | `evaluate_dose_delivery_result` | `batch_id`, `sample_id`, `actual_value`, `uom`, `acceptance_rule_id` | Dose ની ચોકસાઈ (accuracy) rules engine દ્વારા ચકાસવી — `acceptance_rule_id` એ પહેલેથી released rule ID હોવો જોઈએ |
| `unit-dispositions` | `record_unit_disposition` | `batch_id`, `unit_identifier`, `result` (PASS/REJECT/REWORK), `reason`, `ncr_reference`, `rework_procedure_reference` | એક unit ને final disposition આપવો — REJECT/REWORK માટે `reason` ફરજિયાત |
| `reusable-device-pairings` | `record_reusable_device_pairing` | `reusable_device_reference`, `cartridge_lot_reference`, `compatibility_status` (COMPATIBLE/INCOMPATIBLE/PENDING_REVIEW), `rationale`, `batch_id` | Reusable pen + cartridge ની compatibility નોંધવી (reusable pen "consume" નથી થતું, એટલે આ અલગ table માં જાય છે) — **`batch_id` હાલમાં ફરજિયાત છે** (batch વગર pairing authoring હજુ implement નથી થયું) |

---

## 11. Inhalation MDI/DPI (Document 56) — Fields ની સમજ

Genealogy **છે** (`hasGenealogy: true`) પણ Review-summary **નથી**.

| Operation | Backend Function | મુખ્ય Fields | શું કરે છે |
|---|---|---|---|
| `fill-runs` | `start_inhaler_fill_run` | `batch_id`, `profile_version_id`, `fill_route`, `line_id`, `equipment_id`, `environment_status`, `blend_hold_limit_rule_id` | Inhaler fill run શરૂ કરવો. **`fill_route` profile ના declared route સાથે match થવો જોઈએ** (`FillRouteMismatchError` નહીં તો) |
| `closure-results` | `record_crimp_or_closure_result` | `batch_id`, `unit_or_sample_id`, `measured_value`, `uom`, `acceptance_rule_id`, `test_type` (default `SEAL`) | Crimp/seal ટેસ્ટ result — rules engine દ્વારા evaluate |
| `dose-tests` | `record_inhaler_dose_test` | `batch_id`, `test_type` (DELIVERED_DOSE/AERODYNAMIC_PARTICLE_SIZE/SPRAY_PATTERN/PRIMING...), `qc_record_reference`, `result_state` | Dose-related QC test link |
| `dose-counter-tests` | `record_dose_counter_test` | `batch_id`, `unit_or_sample_id`, `program_version`, `result_state` | Dose counter (કેટલા doses બાકી છે તે બતાવતું mechanism) નું test |
| `dose-unit-bindings` | `bind_dose_unit_to_device` | `batch_id`, `dose_unit_reference` (`{"blister_id":...}`/`{"capsule_id":...}`/`{"reservoir_lot_id":...}`), `device_reference` | Dose unit (blister/capsule/reservoir) ને device સાથે જોડવો — duplicate binding ના થાય તે માટે check છે |

---

## 12. Coated / Combination Device (Document 57) — Fields ની સમજ

Genealogy અને Review-summary **બંને નથી** (સૌથી ઓછા features — Profile GET પણ નથી).

| Operation | Backend Function | મુખ્ય Fields | શું કરે છે |
|---|---|---|---|
| `coating-runs` | `start_coating_run` | `batch_id`, `profile_version_id`, `line_id`, `equipment_id`, `environment_status`, `initial_drug_solution_quantity`, `initial_drug_solution_uom` | Coating run શરૂ કરવો — શરૂઆતમાં જ drug-solution ISSUED તરીકે mass-balance ledger માં નોંધાય જાય છે |
| `drug-coating-usage` | `record_drug_coating_usage` | `batch_id`, `usage_type` (ISSUED/APPLIED/RESIDUAL/SAMPLED/REJECTED/RECOVERED/DISPOSED), `quantity` (decimal string), `uom`, `reason_code` | Drug/coating material નું mass-balance — કેટલું issue થયું, કેટલું apply થયું, કેટલું waste ગયું |
| `device-coating-bindings` | `bind_device_to_coating_constituent` | `batch_id`, `device_unit_reference`, `coating_solution_reference` | Device unit ને coating solution/lot સાથે જોડવો |
| `drug-loading-results` | `record_drug_loading_result` | `batch_id`, `unit_or_sample_id`, `measured_value`, `uom`, `acceptance_rule_id`, `test_type` (default `COATING_INTEGRITY`) | Device પર drug ની loading/quantity ચકાસવી — rules engine દ્વારા; fail થાય તો result `OOS` (drug quantity માટે FAIL ના બદલે OOS વપરાય છે) |
| `post-sterilization-tests` | `record_post_sterilization_test` | `batch_id`, `sterilization_reference`, `test_type`, `qc_record_reference`, `result_state` | Sterilization પછીનું ટેસ્ટ — sterilization cycle ની reference (Document 42 module માંથી, duplicate નહીં) |
| `functional-tests` | `record_device_functional_test` | `batch_id`, `test_type`, `qc_record_reference`, `method_reference`, `result_state` | સામાન્ય device functional test (rule-evaluation વગર — સીધું result_state આપો) |
| `unit-dispositions` | `record_coated_device_disposition` | `batch_id`, `unit_identifier`, `result` (PASS/REJECT/REWORK), `reason`, `drug_device_impact_assessment`, `rework_procedure_reference` | Final disposition. **REWORK માટે procedure reference + drug/device impact assessment બંને ફરજિયાત** (COAT-FR-025) — coated device નું rework ખાસ કરીને risky હોવાથી double check છે |

---

## 13. Negative / Error Test Cases (બધા પ્રકાર માટે સામાન્ય)

| Test Case | ક્રિયા | Expected Error |
|---|---|---|
| **ખાલી required field** | Profile code ખાલી રાખીને Create ક્લિક કરો | Button જ disabled રહેશે (`disabled={busy \|\| !profileCode.trim()}`) |
| **અસ્તિત્વ ના ધરાવતો Batch ID** | Execution માં ખોટો/random UUID `batch_id` નાખો | `NOT_FOUND` — "Batch not found" |
| **અસ્તિત્વ ના ધરાવતો Profile ID lookup** | Lookup form માં random UUID નાખો | JSON panel માં `{"error": "NOT_FOUND: ..."}` |
| **Malformed JSON payload** | Execution card ના Payload માં `{बराबर नहीं}` જેવું અધૂરું JSON | "Invalid JSON: ..." — submit પહેલા જ frontend પકડે છે |
| **Duplicate submit (Idempotency ચકાસવા)** | એક જ form ને 2 વાર ઝડપથી ક્લિક કરો (double-click) | Database માં **1 જ** record બને — બંને click નું result same aggregate_id આપશે |
| **Signature-required action** (Release) | કોઈ પણ profile release કરો | `SIGNATURE_POLICY_UNRESOLVED` (409) — spec-gap SG-167/SG-172 ના class નું, blocking, Document 106 policy ની રાહ જોવાય છે |

---

## 14. Error Codes નો શબ્દકોશ

| Error Code | અર્થ (ગુજરાતીમાં) |
|---|---|
| `NOT_FOUND` | ID થી શોધેલો record (batch/profile/handoff) અસ્તિત્વમાં નથી |
| `VALIDATION_FAILED` | Input data માં કંઈક ખોટું છે (દા.ત. duplicate, ખોટી enum value) |
| `STALE_VERSION` | તમે જે version પર કામ કરી રહ્યા હતા, ત્યાં સુધીમાં કોઈ બીજાએ (અથવા તમે પોતે બીજી ટેબમાં) એ record બદલી નાખ્યો છે — તાજું data ફરી load કરો |
| `INVALID_TRANSITION` | Record ની current state માં આ action પરવાનગી નથી (દા.ત. પહેલેથી RELEASED profile ને ફરી release કરવો) |
| `PROFILE_SCHEMA_INVALID` | Subtype અથવા constituent_type ખોટી/અજાણી value છે |
| `PROFILE_RELEASE_BLOCKED` | Profile ને constituent requirement વગર release ના કરી શકાય |
| `SIGNATURE_POLICY_UNRESOLVED` | આ action ને electronic signature જોઈએ છે, પણ Document 106 policy હજુ set નથી થઈ — **fail-closed**, bug નથી |
| `REWORK_ROUTE_REQUIRED` | REWORK result માટે released procedure reference ફરજિયાત છે (default rework disallowed) |
| `CONTAINER_ALREADY_USED` | આ drug container પહેલેથી બીજા injector unit સાથે bound છે |
| `DOSE_UNIT_BINDING_ALREADY_USED` | આ dose unit પહેલેથી બીજા device સાથે bound છે |
| `LINE_NOT_READY` | Equipment area/line ready નથી (EM status, line clearance, અથવા equipment eligibility fail) |
| `BULK_NOT_RELEASED` | Drug/biologic bulk batch હજુ released state માં નથી |
| `PRIMARY_COMPONENT_NOT_RELEASED` | Device/packaging/label component lot હજુ released નથી |
| `PFS_PROFILE_NOT_EFFECTIVE` | Profile RELEASED state માં નથી (DRAFT અથવા SUPERSEDED છે) |

---

## 15. જાણીતી મર્યાદાઓ (Known Limitations)

આ UI ની honest (પ્રામાણિક) મર્યાદાઓ — testing વખતે આ યાદ રાખવું:

1. **Batch Readiness "Load" button ને `profile_version_id` નથી પૂછતું** — backend endpoint ને આ
   query parameter ફરજિયાત જોઈએ છે, પણ UI form માં field નથી. આ કારણે "Load" click કરવાથી error
   આવી શકે. Backend ને સીધું API call (curl/Postman) થી ટેસ્ટ કરવું.
2. **Constituent Handoff "Decide" (Accept/Reject) માટે કોઈ UI નથી** — Handoff બનાવ્યા પછી તેને
   accept/reject કરવાનું form પેજ પર નથી (ફક્ત `record_constituent_handoff` reachable છે, `decide_
   constituent_handoff` નહીં). આ backend API level પર જ ટેસ્ટ કરી શકાય.
3. **Fill Operation ના sub-actions (IPC result, intervention, complete) માટે UI નથી** — ફક્ત
   "start" (fill-operations) Execution card થી પહોંચી શકાય છે. `ipc-results`, `interventions`,
   `complete` — આ બધા endpoints ને path parameter (`fill_operation_id`) જોઈએ છે, જે generic
   Execution form support નથી કરતું.
4. **Device Assembly "Verify" (independent verification) માટે UI નથી** — Assembly step record
   કરી શકાય છે, પણ તેને verify કરવાનું (IND-001 independence check સાથે) form નથી.
5. **Signature-required actions (Release, Fill Start) અત્યારે હંમેશા fail-closed રહેશે** —
   Document 106 માં DDCP માટે કોઈ signature policy row નથી (spec-gap, blocking). આ **UI bug નથી**,
   ઈરાદાપૂર્વક regulated fail-closed behavior છે.
6. **Product/Recipe/Batch dual-store issue (SG-173)** — આ platform-wide architecture finding છે
   (DDCP ને directly અસર નથી કરતું, પણ `batch_id` જે batch module વાપરે છે તેમાં આ related છે) —
   details માટે અલગથી પૂછો.

---

*આ document `docs/testing/DDCP_Manual_Test_Guide_Gujarati.md` પર save થયેલો છે. બધી field/button ની
સમજ backend code (`app/modules/ddcp/*.py`) અને frontend code (`frontend/src/app/ddcp/page.tsx`) માંથી
સીધી લેવામાં આવેલી છે — કંઈ પણ guess/fabricate નથી કરેલું.*
