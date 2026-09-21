# DDCP Client Demo Guide — શરૂઆતથી Release સુધી (Gujarati)

**હેતુ:** આ document `docs/testing/DDCP_Comprehensive_Test_Manual_Gujarati.md` (exhaustive role-wise test
manual) જેવું ટેસ્ટ-કેસ ડોક્યુમેન્ટ **નથી**. આ એક **client demo script** છે — એક કાલ્પનિક (fictional) US
pharma કંપની ભાગ ભજવીને (role-play), શરૂઆતથી છેક release સુધીની આખી પ્રોસેસ, real-world data સાથે, RBAC
(કોણ શું કરી શકે) બતાવવા માટે. બધું code (`services/gxp-api/app/modules/*`, `frontend/src/app/*`,
`scripts/seed.py`) માંથી ચકાસેલું — કંઈ પણ ના-જોયેલું field/endpoint નામ inventing નથી કર્યું.

**⚠️ પ્રામાણિકતા નોંધ (CLAUDE.md §5):** આ document માં "ડેમો ડેટા" fictional છે અને **હજુ system માં
દાખલ કરેલો નથી** — તમારે (કે તમારી ટીમે) browser માં ખરેખર દરેક સ્ટેપ કરવો પડશે. કંઈ પણ "already tested,
PASS" તરીકે claim નથી કરેલું.

**તારીખ:** 2026-09-03 (§1-§20 મૂળ; §21 2026-09-16 નવેસરથી ઉમેર્યું) | **Frontend:**
`http://88.99.15.183:4101` | **Backend:** `http://88.99.15.183:8010` | **Site:** `SITE1` | **Password
(બધા demo user માટે):** `ChangeMe123!`

**Session expiry:** આજથી login token / idle timeout / absolute session timeout ત્રણેય **1 દિવસ (1440
મિનિટ)** કરી દીધા છે (`services/gxp-api/app/core/config.py`, `pm2 restart ebmr-new-api` કરેલું) — demo
દરમિયાન વારંવાર logout નહીં થાય. *(આ engineering default છે, કોઈ approved regulated value નથી — SG-163,
production પહેલા review કરવું.)*

**⚠️⚠️ 2026-09-16 — સૌથી અગત્યની નોંધ, પહેલાં આ વાંચો:** §5-§16 માં નીચે જે `MJ-PFS-B-2601` batch ડેટા
દેખાય છે એ હવે ડેમો સૂચન **નથી** — એ ખરેખર live DB માં **સંપૂર્ણપણે execute થઈને Released સુધી પહોંચી
ગયેલો છે** (બધા 8 recipe step complete, DDCP evidence 2 વાર freeze, 2 deviation closed, QA review
complete, batch release = `released`). એ જ batch number, receipt number, lot number, deviation number
ફરી વાપરવાની કોશિશ કરશો તો unique-constraint error અથવા "wrong state" error આવશે. **હાથોહાથ
browser-testing માટે નવો, અડ્યા વગરનો ડેટા જોઈએ છે** — એ **[§21 — નવું Test Cycle, 2026-09-16](#21-નવું-test-cycle-round-2-2026-09-16-real-live-data)**
માં છે, code-verified સામે current live DB (batch/lot/receipt/deviation numbers, RBAC roles, field
list — બધું ફરી ચકાસેલું). §5-§20 હજુ પણ સાચા છે concept/field/RBAC સમજવા માટે — ફક્ત એમાં લખેલા
literal batch/lot/receipt/deviation **numbers** હવે consumed છે, નવા demo run માટે §21 ના numbers
વાપરવા.

---

## અનુક્રમણિકા

1. [આ ડેમો કેમ powerful છે — client ને શું બતાવવું](#1-આ-ડેમો-કેમ-powerful-છે--client-ને-શું-બતાવવું)
2. [ડેમો સ્ટોરી — કંપની અને પ્રોડક્ટ](#2-ડેમો-સ્ટોરી--કંપની-અને-પ્રોડક્ટ)
3. [Setup — Demo Users (કોણ-કોણ જોઈએ)](#3-setup--demo-users-કોણ-કોણ-જોઈએ)
4. [RBAC નકશો — સંપૂર્ણ Role Table](#4-rbac-નકશો--સંપૂર્ણ-role-table)
5. [Phase 1 — Suppliers (પુરવઠાદાર)](#5-phase-1--suppliers-પુરવઠાદાર)
6. [Phase 2 — Materials + Receiving + Inventory (કાચો માલ)](#6-phase-2--materials--receiving--inventory-કાચો-માલ)
7. [Phase 3 — Equipment + Device Lot (મશીન + ડિવાઇસ)](#7-phase-3--equipment--device-lot-મશીન--ડિવાઇસ)
8. [Phase 4 — Product Master (પ્રોડક્ટ ટેમ્પલેટ)](#8-phase-4--product-master-પ્રોડક્ટ-ટેમ્પલેટ)
9. [Phase 5 — Recipe Master (પ્રોસેસ ટેમ્પલેટ)](#9-phase-5--recipe-master-પ્રોસેસ-ટેમ્પલેટ)
10. [Phase 6 — DDCP Profile (Drug+Device સ્પેક)](#10-phase-6--ddcp-profile-drugdevice-સ્પેક)
11. [Phase 7 — Batch Create + Issue + Start](#11-phase-7--batch-create--issue--start)
12. [Phase 8 — DDCP Batch Execution](#12-phase-8--ddcp-batch-execution)
13. [Phase 9 — Deviation (સમસ્યા આવે ત્યારે)](#13-phase-9--deviation-સમસ્યા-આવે-ત્યારે)
14. [Phase 10 — Line Clearance](#14-phase-10--line-clearance)
15. [Phase 11 — Batch Readiness + DDCP Evidence Freeze](#15-phase-11--batch-readiness--ddcp-evidence-freeze)
16. [Phase 12 — QA Review + Final Release](#16-phase-12--qa-review--final-release)
17. [ટેક્નિકલ મેપિંગ સારાંશ (Frontend ↔ Backend)](#17-ટેક્નિકલ-મેપિંગ-સારાંશ-frontend--backend)
18. [Client demo — શું emphasize કરવું](#18-client-demo--શું-emphasize-કરવું)
19. [જાણીતી મર્યાદાઓ (પ્રામાણિકતા)](#19-જાણીતી-મર્યાદાઓ-પ્રામાણિકતા)
20. [સંદર્ભ](#20-સંદર્ભ)
21. [નવું Test Cycle (Round 2, 2026-09-16) — Real Live Data](#21-નવું-test-cycle-round-2-2026-09-16-real-live-data)
22. [2026-09-17 Update — Release હવે Production Complete માંગે છે + CAPA data](#22-2026-09-17-update--release-હવે-production-complete-માંગે-છે--capa-data)

---

## 1. આ ડેમો કેમ powerful છે — client ને શું બતાવવું

Client ને 3 વસ્તુ સાબિત કરવાની છે:

1. **RBAC ખરેખર કામ કરે છે** — દરેક પગલું ચોક્કસ role જ કરી શકે, બીજું કોઈ નહીં (backend `403 Forbidden`
   આપે, UI એ button પણ hide/disable કરે).
2. **Segregation of Duties (SoD)** — જે "શું બનાવવું" નક્કી કરે (DDCP Engineer, profile) એ "શું બન્યું"
   record નથી કરતું (DDCP Operator, execution); જે operator કામ કરે એ પોતે verify નથી કરી શકતો (IND-001,
   independent verification).
3. **Electronic signature ≠ Login** (AG-07) — અમુક ચોક્કસ pivotal ક્ષણો પર (batch release, material lot
   release, deviation disposition/close, supplier qualification approve) system password **ફરી માંગે
   છે** — એ ખરેખર 21 CFR Part 11 e-signature ceremony છે, ફક્ત "logged in" હોવું પૂરતું નથી.

આ ડેમો story-driven છે: **Meridian Therapeutics Inc.** નામની કંપની પોતાનું પહેલું combination product
(prefilled syringe) manufacture કરે છે — supplier onboard કરવાથી માંડીને final release સુધી, 6-7 જુદા
જુદા લોકો (roles) ના હાથમાંથી પસાર થાય છે.

---

## 2. ડેમો સ્ટોરી — કંપની અને પ્રોડક્ટ

> **આ કંપની અને પ્રોડક્ટ સંપૂર્ણપણે કાલ્પનિક (fictional) છે** — કોઈ સાચી કંપની/બ્રાન્ડ સાથે કોઈ સંબંધ
> નથી. ફક્ત demo માટે.

| | |
|---|---|
| **કંપની** | **Meridian Therapeutics, Inc.** — Durham, North Carolina, USA (FDA-registered biologics facility) |
| **પ્રોડક્ટ** | **MeridiJect™** — Meridizumab 40 mg/0.4 mL Prefilled Syringe (subcutaneous biologic, autoimmune indication) |
| **Combination product family** | **Prefilled Syringe (PFS)** — Document 54 / SPEC-DDCP-001 |
| **Constituent 1 (Drug)** | Meridizumab bulk drug substance — supplier: **BioSource Biologics LLC** (Cary, NC) |
| **Constituent 2 (Device)** | 1 mL glass prefilled-syringe barrel + staked needle + safety shield — supplier: **ClearGlass Device Components Inc.** (San Jose, CA) |
| **Batch size** | 4,000 units, target |
| **Manufacturing site** | `SITE1` (Demo Site 1) |

**કેમ PFS family?** PFS ને સૌથી વધુ actions (8) છે — supplier→material→device→fill→assembly→testing→
release ની આખી chain PFS માં best demonstrate થાય છે.

---

## 3. Setup — Demo Users (કોણ-કોણ જોઈએ)

**Seeded (already exist, `scripts/seed.py`):** `admin`, `operator1`, `qa.reviewer`, `qa.releaser`,
`qc.reviewer`, `equipment.admin`, `engineering.manager`, `calibration.tech`, `maintenance.tech`,
`sanitation.operator` — password બધા માટે `ChangeMe123!`.

**Demo માટે નવા બનાવવા પડશે** (`admin` → **Admin → Users**, `/admin/users` → "New user" → "Assign role",
Section 2.5 ના DDCP manual ના pattern પ્રમાણે):

| Username | Full name | Role | આ ડેમોમાં કરે છે |
|---|---|---|---|
| `ddcp.engineer` | Dev DdcpEngineer | DDCP Engineer | DDCP Profile (Stage 1) |
| `ddcp.operator` | Opal DdcpOperator | DDCP Operator | DDCP execution (Stages 2-4) |
| `ddcp.operator2` | *(બીજું DDCP Operator, IND-001 independent verify માટે — 2 જુદા users જોઈએ)* | DDCP Operator | Independent assembly verify |

*(`supervisor1` અને `process.engineer` (Phases 4-5 — Product + Recipe Master authoring) બંને હવે live DB માં
પહેલેથી છે — બનાવવાની જરૂર નથી. `process.engineer` 2026-09-08 નો નવો role, §9.12 જુઓ.)*

**Role assignment લાગુ થાય તરત** (`/auth/me` live query — logout/login ની જરૂર નથી).

---

## 4. RBAC નકશો — સંપૂર્ણ Role Table

આ આખા ડેમોમાં **12 જુદા roles** વપરાય છે. દરેકનું કામ, permission code, અને Document reference (code
`scripts/seed.py` માંથી verified):

| Role | આ ડેમોમાં કરે છે | મુખ્ય Permission codes | Doc # |
|---|---|---|---|
| **Admin** | Master data, users, all templates (break-glass; holds every role) | `platform.administer`, `product.author`, `product.release`, `recipe.author`, `recipe.release` | — |
| **Process Engineer** | Product Master + Recipe Master **authoring** — draft/edit/validate/simulate/submit; **release નહીં** (Phases 4-5) | `product.author`, `recipe.author`, `*.view` | 9, 10 |
| **Supervisor** | Batch create/issue, step role-override, material receipt, line clearance | `batch_execution.create/.issue`, `batch_step.role_override`, `material_receipt.create` | 11, 19, 39 |
| **Operator** | Batch execution, material handling, deviation raise | `batch_execution.execute`, `qms_deviation.create` | 11, 19-22, 26 |
| **DDCP Engineer** | PFS Profile author + release | `ddcp_profile.author`, `.release` | 54 |
| **DDCP Operator** | Handoff, fill, assembly, tests, readiness, evidence | `ddcp_constituent.*`, `ddcp_fill.*`, `ddcp_device.*`, `ddcp_release.*` | 54 |
| **QA Reviewer** | Batch review, deviation investigate/impact, QA review package | `batch.review` (સહી), `qms_deviation.investigate/.impact` | 14, 26 |
| **QA Releaser** | Product release, Recipe release, Batch release, material lot release, deviation disposition/close, supplier qual approve | `product.release` (સહી, author થી independent — §8.5), `recipe.release` (સહી, author થી independent — §9.10), `batch.release` (સહી), `material_lot.release` (સહી), `qms_deviation.disposition/.close` (સહી), `supplier_qualification.approve` (સહી) | 9, 10, 15, 18, 19, 26 |
| **QC Reviewer** | Material lot disposition | `material_lot.disposition` (સહી) | 19, 23 |
| **Equipment Administrator** | Equipment asset create + qualify | `equipment_asset.create`, `.qualify` | 38 |
| **Calibration Technician** | Filler/line equipment calibration | `equipment_asset.calibrate` | 38 |
| **Sanitation Operator** | Line clearance execute | `line_clearance.create/.complete` (સહી) | 39 |

**(સહી)** = એ action વખતે system **password ફરી માંગે છે** (real e-signature ceremony, AG-07) —
`scripts/seed.py`ના `SIGNATURE_POLICY_FLOOR` માંથી verified.

**અગત્યની honest નોંધ:** Supplier record બનાવવું (`POST /suppliers/v1`) અને Material master બનાવવું
(`POST /materials`) — આ બંને actionsને code માં **કોઈ RBAC gate નથી** (`create_supplier`/
`create_material` કોઈ `evaluate_policy()` call જ નથી કરતા — ચેક કરેલું). એટલે કોઈ પણ logged-in user એ
બનાવી શકે. Demo માં અમે વાસ્તવિકતા માટે `supervisor1` થી બનાવીશું, પણ technically `qa.reviewer` કે
`operator1` થી પણ ચાલી જાય — client ને આ ખુલ્લેઆમ કહેવું (roadmap item તરીકે, bug તરીકે નહીં).

---

## 5. Phase 1 — Suppliers (પુરવઠાદાર)

**કોણ:** `supervisor1` (create) → `qa.releaser` (approve, સહી). **ક્યાં:** `/suppliers`.
**Backend:** `POST /suppliers/v1` (create), `POST /suppliers/{id}/qualifications` (qualification request),
`POST /supplier-qualifications/{id}/approve` (approve — સહી). **Doc:** 18 (SPEC-QMS-005).

### 5.0 કેમ "Supplier" અને "Qualification" બે અલગ રેકોર્ડ છે? (સાદી ભાષામાં)

**Supplier record** = કંપની ની master ઓળખ ("આ કોણ છે" — code, legal name, country, site). કોઈ પણ
logged-in user બનાવી શકે (RBAC gate નથી), કારણ કે ફક્ત register કરવું એ કોઈ regulated નિર્ણય નથી.

**Supplier Qualification** = "શું આ supplier પાસેથી ખરેખર material લેવાની **મંજૂરી** છે?" — સાવ અલગ,
અલગથી approve થતો રેકોર્ડ. રિયલ વર્લ્ડ: તમે કોઈ નવો વેપારી શોધો (register) ત્યારે જ એની પાસેથી માલ ના
લેવાનું શરૂ ના કરો — પહેલાં એનું ઓડિટ/verification કરો, પછી જ "approved vendor list" માં નાખો. એ જ ફરક
અહીં છે — supplier બનાવવો easy, qualification approve થવી કડક (સહી-required, QA Releaser only).

| Field | મતલબ | ઉદાહરણ |
|---|---|---|
| Role type | supplier ની ભૂમિકા — `supplier` (વેચનાર), `manufacturer` (બનાવનાર), `both` | આ ડેમોમાં બંને supplier `manufacturer` — કારણ કે તેઓ પોતે જ material બનાવે છે, વચ્ચે કોઈ distributor નથી |
| Scope (qualification) | કઈ ચોક્કસ વસ્તુ/process માટે આ supplier ને qualified ગણ્યો | `{"materials": ["bulk_drug"], "process": "fill-finish"}` — ફક્ત bulk drug માટે qualified, બીજા material માટે નહીં |
| Risk class | High/Medium/Low — આ supplier કેટલો critical છે | Biologic drug substance = `High` (દર્દીની સેફ્ટી સીધી અસર); Device component = `Medium` |
| Effective from / Expires | Qualification ક્યાં સુધી valid | +2 વર્ષ — પછી ફરી evaluate કરવો પડે, supplier કાયમ માટે qualified નથી રહેતો |

**શા માટે approve ને સહી જોઈએ:** qualification approve એટલે "અમે ખાતરી કરી કે આ supplier વિશ્વાસપાત્ર
છે" — આ decision ભવિષ્યની **દરેક** receipt/lot ને અસર કરે છે (Phase 2 નું `source_not_approved` ચેક આ જ
approval status વાપરે છે), એટલે ફક્ત click નહીં, real password re-entry (e-signature) જોઈએ.

### 5.1 Supplier 1 — Drug Substance

| Field | Data |
|---|---|
| Supplier code | `SUP-BIO-001` |
| Legal name | `BioSource Biologics LLC` |
| Role type | `manufacturer` |
| Country | `US` |
| Site | Cary, NC — `SITE-BIO-CARY` |

### 5.2 Supplier 2 — Device Component

| Field | Data |
|---|---|
| Supplier code | `SUP-DEV-001` |
| Legal name | `ClearGlass Device Components Inc.` |
| Role type | `manufacturer` |
| Country | `US` |
| Site | San Jose, CA — `SITE-DEV-SJ` |

### 5.3 Qualification — બંને supplier માટે

| Field | Data |
|---|---|
| Scope | `{"materials": ["bulk_drug"], "process": "fill-finish"}` (free JSON) |
| Risk class | `High` (biologic drug substance) / `Medium` (device component) |
| Effective from / Expires | આજ / +2 વર્ષ |

`qa.releaser` login → qualification approve → **password ફરી માંગશે** — client ને બતાવો: "ફક્ત login
પૂરતું નથી, approval ક્ષણે ફરી identity confirm કરવી પડે."

---

## 6. Phase 2 — Materials + Receiving + Inventory (કાચો માલ)

**કોણ:** `supervisor1`/`admin` (material master create) → `operator1` (receipt create/examine) →
`qc.reviewer` (lot disposition — સહી) → `operator1`/`supervisor1` (inventory reserve/transfer/count).
**ક્યાં:** `/materials`, `/material-receipts`, `/material-lots`, `/inventory`.
**Backend:** `POST /materials` (master), `POST /materials/v1/receipts` + `.../examine` (receiving),
`POST /materials/{id}/lots` (quick lot shortcut), `/inventory/v1/*`. **Doc:** 19 (receiving), 20
(inventory). *(Field lists below verified against `frontend/src/app/{materials,material-receipts,
material-lots,inventory}/page.tsx` અને `services/gxp-api/app/modules/material/{commands,router}.py`,
2026-09-03.)*

### 6.0 કેમ આ ત્રણ અલગ વસ્તુ છે? — Materials vs Material Receipts vs Material Lots (સાદી ભાષામાં)

આ ત્રણેય "કાચો માલ" સાથે સંબંધિત છે, પણ ત્રણ સાવ જુદા સવાલોના જવાબ આપે છે: **શું છે** (Material) →
**શું આવ્યું** (Receipt) → **વાપરવા લાયક છે કે નહીં** (Lot). કોઈ પણ એક ખૂટે તો સિસ્ટમ અધૂરી પડે.

**Material — Master data ("આ વસ્તુ શું છે")**
રિયલ વર્લ્ડ ઉદાહરણ: તમારી ફેક્ટરીના ગોડાઉનના રજિસ્ટરમાં "Item Code / Item Name / Unit" ની એક કાયમી
યાદી હોય છે — "Sugar — KG", "Bottle cap — EA" — ભલે ગમે તેટલી વાર delivery આવે, entry એક જ વાર બને છે.
`/materials` પર બનતું `MAT-DRUG-MERIDIZ` (code) / `Meridizumab Bulk Drug Substance` (name) / `ML` (unit)
એ જ છે. **શા માટે જરૂરી:** આ master ના હોય તો દરેક delivery વખતે ફરી-ફરી "આ કયો material છે, કયા unit
માં ગણવો" નક્કી કરવું પડે — કોઈ consistency ના રહે, અને "કુલ કેટલો sugar સ્ટોકમાં છે" એ સવાલનો જવાબ જ ના
મળે (અલગ-અલગ નામે એ જ વસ્તુ 10 જગ્યાએ વેરાયેલી હોય).

**Material Receipt — "શું આવ્યું, ક્યાંથી, ક્યારે" (ચેક કરતાં પહેલાંનો રેકોર્ડ)**
રિયલ વર્લ્ડ ઉદાહરણ: ફેક્ટરીના gate પર ટ્રક આવે ત્યારે store/security વ્યક્તિ સૌથી પહેલાં લખે — "આજે આટલી
ક્વોન્ટિટી, આ સપ્લાયર તરફથી, આ documents સાથે આવ્યું" (`/material-receipts` નું "Log a material
receipt"). પછી કોઈ (`operator1`) box ખોલી ને ચેક કરે — packaging તૂટેલું નથી ને, label સાચું છે ને, ખરેખર
એ જ સપ્લાયર છે ને જેની પાસેથી order કર્યો હતો ("Examine receipt"). **શા માટે જરૂરી:** રેગ્યુલેટેડ
ફેક્ટરીમાં "ટ્રકમાંથી ઊતર્યું" અને "વાપરવા માટે વિશ્વાસપાત્ર છે" — આ બે અલગ ક્ષણો છે, અને વચ્ચે એક ઔપચારિક
ચેક-પોઇન્ટ હોવો જ જોઈએ. Examine પાસ ના થાય (damage/seal-broken/ખોટો supplier) તો receipt
discrepancy-hold માં અટકી જાય છે — lot **બનતો જ નથી**, code-level guarantee.

**Material Lot — QC પાસ થયેલો, વાપરી શકાય એવો સ્ટોક**
રિયલ વર્લ્ડ ઉદાહરણ: Receipt નું examine સાફ (clean) આવે એટલે material lot બને — પણ સીધો વપરાય નહીં,
પહેલાં **Quarantine** (અલગ કબાટમાં, "હજુ વાપરવું નહીં" ટેગ સાથે) જાય. QC/`qc.reviewer` લેબમાં ટેસ્ટ કરે,
પછી જ **Release** (વાપરવા માટે લીલી ઝંડી) અથવા **Reject** કરે. `/material-lots` પર આ જ સ્ટેટસ ટ્રેકિંગ
દેખાય છે. **શા માટે જરૂરી:** આ QC gate ના હોય તો ચેક ના થયેલો, ખરાબ કે ખોટો કાચો માલ સીધો batch માં જતો
રહે — દવા/પ્રોડક્ટની સેફ્ટી સાથે સીધો સંબંધ, એટલે આ સૌથી કડક નિયંત્રિત પગલું છે (Document 106 ની સહી-યાદીમાં
`material_lot.disposition` છે એ આ જ કારણે).

**સાર (ટૂંકમાં):** Material = કાયમી "શું" ની યાદી (એક વાર બને) · Receipt = "આજે આ ચોક્કસ ડિલિવરી આવી" નો
રેકોર્ડ (દરેક ટ્રક વખતે નવો) · Lot = "QC એ ચેક કરીને પાસ/ફેલ કરેલો, batch માં વાપરી શકાય એવો સ્ટોક-યુનિટ"
(receipt માંથી બને, પોતાનું quarantine→released જીવનચક્ર હોય).

**Supplier vs Manufacturer — શું ફરક છે?**

| | Supplier (પુરવઠાદાર) | Manufacturer (ઉત્પાદક) |
|---|---|---|
| મતલબ | જેની પાસેથી તમે ખરીદો/order કરો (વેપારી, distributor, અથવા સીધો ઉત્પાદક પણ હોઈ શકે) | જેણે ખરેખર material **બનાવ્યું** |
| ઉદાહરણ | Amazon પરથી ફોન ખરીદો — Amazon એ supplier | ફોન Samsung એ બનાવ્યો — Samsung એ manufacturer |
| આ ડેમોમાં | `BioSource Biologics LLC` ને supplier તરીકે પસંદ કર્યું | ખાલી છોડ્યું — કારણ કે supplier પોતે જ material બનાવે છે (role type `manufacturer` તરીકે Phase 1 માં જ નોંધાયેલ) |
| ક્યારે બંને જુદા ભરવા | જયારે તમે એક distributor પાસેથી ખરીદો પણ material કોઈ ત્રીજી ફેક્ટરીમાં બન્યું હોય | — |

બંને ફિલ્ડ `/material-receipts` ના "Supplier"/"Manufacturer" dropdown માંથી પસંદ થાય છે (તમારા
registered Suppliers લિસ્ટમાંથી જ) — free text નથી, જેથી ખોટવાળી entry ના થાય. ફક્ત **Supplier** ની
approval-status ચેક થાય છે (RCV-FR-005) — Manufacturer field શુદ્ધ traceability માટે છે.

**Received quantity vs Accepted quantity — ફરક શું?**

- **Received quantity (gross)** — ટ્રકમાંથી/બોક્સમાંથી કુલ કેટલું ઊતર્યું, જેમનું-તેમ (દા.ત. `12.500 L`).
  આ હંમેશા ભરવું ફરજિયાત છે.
- **Accepted quantity** — ચેક કર્યા પછી ખરેખર કેટલું વાપરવા યોગ્ય માન્યું. ખાલી છોડો તો gross બરાબર જ
  ગણાય (code: `accepted_quantity or received_gross_quantity`) — પણ જો, દા.ત., 1 container લીક થયેલું
  મળે તો gross `12.5 L` છતાં accepted `12.0 L` ભરી શકાય. **જે quantity lot માં જાય છે, વાસ્તવમાં એ
  accepted quantity જ છે** — gross ફક્ત "શું આવ્યું" નો ઐતિહાસિક રેકોર્ડ છે.
- **Received quantity (net)** — ઓપ્શનલ, gross કરતાં જુદું હોય તો (દા.ત. કન્ટેનરનું વજન બાદ કરીને).

**Manufacture date / Expiry date / Retest date — ફરક શું?**

| Field | મતલબ |
|---|---|
| **Manufacture date** | Material ખરેખર ક્યારે બન્યું (ઉત્પાદકની ફેક્ટરીમાં). |
| **Expiry date** | આ તારીખ પછી material **બિલકુલ વાપરી ના શકાય** — ફેંકી દેવું પડે. મોટા ભાગની finished વસ્તુઓ માટે. |
| **Retest date** | Material "બગડતું" નથી (દા.ત. અમુક કેમિકલ/API) પણ ચોક્કસ સમય પછી ફરી લેબ-ટેસ્ટ કરવો ફરજિયાત — પાસ થાય તો વધુ સમય વાપરી શકાય, નહીં તો રિજેક્ટ. Expiry = "ચોક્કસ મરી ગયું"; Retest = "ફરી ચેક કરાવો, કદાચ હજુ સારું છે". |

ત્રણેય ઓપ્શનલ છે (material પ્રમાણે લાગુ પડે એ ભરવાનું).

**CoA document hash શું છે?**

**CoA = Certificate of Analysis** — સપ્લાયર/ઉત્પાદકે આપેલું સર્ટિફિકેટ જેમાં લખ્યું હોય "અમે આ ચોક્કસ
lot નું લેબ-ટેસ્ટ કર્યું, આ પરિણામ આવ્યા, સ્પષ્ટ સ્પેસિફિકેશન પ્રમાણે છે." આ ડોક્યુમેન્ટ evidence તરીકે
vault માં save થાય છે (AG-12, tamper-proof). **Hash (SHA-256)** એ document ના content નું ડિજિટલ
ફિંગરપ્રિન્ટ છે — document માં એક અક્ષર પણ પછીથી બદલાય તો hash સાવ જુદો આવે. આ સાબિત કરવા માટે વપરાય કે
"જે CoA અમે approve કર્યું હતું, એ જ છે, પછીથી કોઈએ બદલ્યું નથી" — કાગળ પર સહી જેવું, પણ ડિજિટલ અને
tamper-evident. Optional field છે (evidence upload ઉપલબ્ધ હોય તો જ ભરાય).

---

**⚠️ અગત્યનું — receiving ના 2 જુદા રસ્તા છે, ડેમોમાં આ frame સ્પષ્ટ કરવો:**

| | `/material-receipts` (proper path) | `/material-lots` → "Receive lot" (quick shortcut) |
|---|---|---|
| શું કરે | Receipt log → Examine (visual/identity/supplier check) → clean result **આપોઆપ** lot બનાવે | એક જ સ્ટેપમાં સીધો lot બનાવે, કોઈ examine step નથી |
| Supplier check | **હા** — examine વખતે `Supplier.status == "approved"` ચેક થાય છે (RCV-FR-005); ના-approved supplier હોય તો lot **નથી** બનતો, receipt discrepancy-hold થાય | Supplier dropdown છે પણ **traceability માટે જ** — કોઈ approval ચેક નથી (UI hint માં જ લખેલું છે) |
| ક્યારે વાપરવું | **આ ડેમો માટે ભલામણ** — Document 19 નો real receiving control બતાવવો હોય તો | ઝડપી/manual entry (દા.ત. legacy data migrate) — production માં આ shortcut રાખવો કે નહીં એ client નક્કી કરે |

### 6.1 Material Masters

`admin`/`supervisor1` → `/materials` → "New material":

| Field | Drug | Device |
|---|---|---|
| Code | `MAT-DRUG-MERIDIZ` | `MAT-DEV-SYR-1ML` |
| Name | `Meridizumab Bulk Drug Substance` | `1 mL Prefilled Syringe Barrel + Needle` |
| Unit of measure | `ML` | `EA` |

### 6.2 Material Receipt — Log + Examine (`/material-receipts`, proper path)

પેજ પોતે એક **list** છે (Receipt/Material/Quantity/Received/Status/Note columns — discrepancy હોય તો
reason સીધો Note column માં જ દેખાય, અલગ ખોલવું ના પડે). `operator1` → **"Log a receipt"** button →
modal ખૂલે (site આપોઆપ active site પરથી ભરાય છે):

| Field | Drug receipt | Device receipt |
|---|---|---|
| Receipt number | `RCPT-DRUG-2601` | `RCPT-DEV-2601` |
| Material | `MAT-DRUG-MERIDIZ` (dropdown) | `MAT-DEV-SYR-1ML` (dropdown) |
| PO reference | `PO-MAT-2026-1187` | `PO-MAT-2026-1188` |
| Supplier | `BioSource Biologics LLC (SUP-BIO-001)` (dropdown — Suppliers list પરથી) | `ClearGlass Device Components Inc (SUP-DEV-001)` (dropdown) |
| Manufacturer | ખાલી (supplier જ manufacturer છે) | ખાલી |
| Supplier's lot number | `SUP-LOT-2601-D` (supplier ના label/CoA પરથી, free text) | `SUP-LOT-2601-V` |
| Manufacturer's lot number | ખાલી | ખાલી |
| Carrier / shipment reference | `FEDEX-8847231` | `FEDEX-8847232` |
| Received quantity (gross) | `12.500` | `4200` |
| Unit of measure | `L` | `EA` |
| Manufacture / Expiry / Retest date | Optional | Optional |
| Shipment condition | `ambient` | `ambient` |

Submit → modal બંધ, receipt list માં state = **received** સાથે દેખાય. એ જ row પર હવે **"Examine"** button
દેખાય (ફક્ત `received` state ના row પર, ને ફક્ત `operator1`/`supervisor1`/`admin` ને) — click કરો → modal
ખૂલે (visual examination, 5 ફરજિયાત Yes/No પ્રશ્નો, બધા જવાબ આપ્યા વગર submit નહીં થાય):

| Field | Value (clean result) |
|---|---|
| Identity confirmed | `Yes` |
| Labeling correct | `Yes` |
| Damage observed | `No` |
| Seal broken | `No` |
| Contamination observed | `No` |
| Internal lot number | `LOT-DRUG-2601` (device: `LOT-DEV-2601`) |
| Container count | `1` |
| Examination notes | Optional |

Submit → receipt state = **examined**, અને **`MaterialLot` આપોઆપ Quarantine માં બની જાય** (container(s)
સાથે) — આ જ `LOT-DRUG-2601`/`LOT-DEV-2601` lot Phase 8 ના "constituent handoff" માં DRUG/DEVICE source
તરીકે reference થાય છે.

**કોઈ પણ receipt ની પૂરી વિગત જોવી હોય તો** list માં એના row પર click કરો — PO reference, Carrier
reference, Supplier's/Manufacturer's lot number, Manufacture/Expiry/Retest date, Shipment condition,
CoA hash, Record version બધું એક જ modal માં દેખાય, અને Supplier/Manufacturer **નામ સાથે** દેખાય (દા.ત.
"BioSource Biologics (SUP-BIO-002)"), raw ID નહીં — code-verified: `get_receipt()` હવે Suppliers table
સાથે join કરીને નામ resolve કરે છે.

**Client demo moment (client ને live બતાવવાનું):** Supplier જેની qualification હજુ **approved** નથી
(Phase 1 ના approve પહેલાં, અથવા કોઈ નવો draft-status supplier) — એના પર receipt examine (સાફ result,
કોઈ damage/seal/contamination નહીં) submit કરો → **છતાં lot ના જ બને** — receipt
`discrepancy_hold` / `source_not_approved` state માં જાય (red banner), code-verified check
(`examine_receipt()`, RCV-FR-005).

**⚠️ અગત્યની ચોખવટ — આ જ receipt પર ફરી "Examine" કરવાનો પ્રયત્ન ના કરવો:** એક વાર receipt
`discrepancy_hold` માં જાય પછી **એ કાયમ માટે ત્યાં જ રહે છે** — `examine_receipt()` ફક્ત `received`
state ના receipt પર જ ચાલે છે (code: `commands.py` લાઇન ~888, `Only a receipt in 'received' state can
be examined`), અને discrepancy_hold receipt ને ફરી `received` બનાવવાનો કોઈ endpoint જ નથી. Supplier ને
પછીથી approve કરો તો પણ **જૂનો receipt એમ જ discrepancy_hold રહેશે** — આ bug નથી, ડિલિબરેટ છે (એક વાર
લીધેલો નિર્ણય ફરી ના લખાય, audit trail નો ભાગ છે).

**સાચી રીત:** Phase 1 માં supplier ને approve કરો, પછી **નવો receipt log કરો** (નવો receipt number, એ જ
material/supplier) અને **એ નવા receipt** ને examine કરો → આ વખતે lot સીધો Quarantine માં બની જાય.
**"એક પણ button click આ ચેક bypass ના કરી શકે"** — IND-001 (Phase 8) જેવો જ negative-control moment,
ફક્ત supplier approval માટે.

### 6.3 Material Lots — list, quick shortcut, QC disposition

`/material-lots` list હવે **Received** અને **Released** બંને timestamp column બતાવે છે (ઉપરાંત Lot,
Material, Available, Expiry, Status). "Receive lot" button (quick shortcut, §6 ઉપરની ટેબલ પ્રમાણે) આ જ
પેજ પર છે — fields: Material, Internal lot number, **Supplier lot** (free text — dropdown નથી, ઉપર
જુઓ), Received quantity, Unit of measure, Expiry date.

**QC disposition:** `qc.reviewer` → lot ના row પર "Disposition" button → Decision (`Released`/`Rejected`)
+ Reason + password re-confirm (**સહી**, `material_lot.disposition`). Released lot નું **Released**
column હવે timestamp બતાવે.

### 6.4 Inventory — reserve / transfer / cycle count / adjustment

`/inventory` — 3 tabs (**Availability**, **Lot ledger**, **Adjustments**). *(બધું code-verified against
`frontend/src/app/inventory/page.tsx` અને `services/gxp-api/app/modules/material/commands.py`
(`create_inventory_reservation`/`create_inventory_transfer`/`create_cycle_count`/
`create_inventory_adjustment_request`), 2026-09-07.)*

#### 6.4.0 કેમ QC "Released" કરવા છતાં material Availability tab માં તરત ના દેખાય? (સાદી ભાષામાં)

**QC disposition (§6.3)** અને **Inventory નું physical location** — આ **બે સાવ અલગ રેકોર્ડ** છે, code
verified: `disposition_material_lot()` (§6.3, `qc.reviewer` ની સહી) ફક્ત `MaterialLot.status` બદલે છે —
lot ક્યાં **ઊભો** છે (કયા વેરહાઉસ location માં) એને **બિલકુલ અડતું નથી**. રિયલ વર્લ્ડ: QC લેબમાં કાગળ પર
"Released" સહી કરે એટલે માલ પોતાની મેળે ગોડાઉનમાં Quarantine કબાટમાંથી Released કબાટમાં ચાલ્યો નથી જતો —
કોઈ (વેરહાઉસ ઓપરેટર) ને ખરેખર **ટ્રોલી લઈને ખસેડવો પડે છે**. Inventory ના "Transfer" action એ જ ભૌતિક
ખસેડવાનું ડિજિટલ રેકોર્ડ છે. એટલે: QC releases the *decision*; a person still has to move the *material* —
અને Availability tab (જે `/inventory/v1/availability` વાપરે છે) ફક્ત ત્યાં જ lot બતાવે જ્યાં lot **released
status + non-expired + non-retest-due + `released`-zone location માં ballance હોય** (code:
`_is_eligible()`, `material/commands.py:1678`).

**બીજી ચોખવટ — `/material-lots` page નું "Available" column vs Inventory નું "Available":** આ **બે અલગ
counter** છે (code verified) — `/material-lots` નું Available column `MaterialLot.available_quantity` છે
(receipt વખતે set થાય, ફક્ત material-issue/destruction actions એને ઘટાડે), જ્યારે Inventory tab નું
Available `InventoryBalanceProjection.available` (location-wise ledger, reserve/transfer/count/adjust
એને બદલે) છે. **બંને એકબીજા સાથે sync નથી** — client ને demo માં clear કરવું: "lot-level count" અને
"location-level ledger" બે અલગ સવાલોના જવાબ છે, એક view નથી.

#### 6.4.1 Material lot / Container / Location — હવે real dropdown (fixed 2026-09-07)

**અગાઉ** (2026-09-07 પહેલાં) Transfer/Cycle count/Adjustment ના form માં આ ત્રણેય raw **UUID** free-text
તરીકે type કરવા પડતા હતા, અને કોઈ પેજ પર એ UUID ક્યાંય text તરીકે દેખાડેલા જ નહોતા — operator ને
DevTools/database સુધી જવું પડતું. **હવે fix થયેલું છે** (code-verified,
`frontend/src/app/inventory/page.tsx` + 2 નવા read-only backend endpoints):

| Field | Dropdown data ક્યાંથી આવે |
|---|---|
| Material lot | `GET /material-lots` (પહેલેથી અસ્તિત્વમાં હતું) — `internal_lot — material_code (status)` બતાવે |
| Container | **નવું:** `GET /material-lots/{lot_id}/containers` — lot select કરો એટલે dropdown auto-populate થાય, `container_code — quantity uom` બતાવે |
| Location (From/To) | **નવું:** `GET /inventory/v1/warehouse-locations?site_id=...` — `location_code (zone_type)` બતાવે |

Container dropdown ખાલી હોય (lot select કર્યા પછી "No containers exist for this lot..." hint દેખાય) તો
એ §6.4.2 નું જ symptom છે — હવે UI માં જ inline દેખાય છે, DB query જરૂરી નથી.

**"Lot ledger" tab પણ:** ત્યાંનું "Material lot ID" free-text field પણ એ જ `GET /material-lots` dropdown
બન્યું છે (lot ને code/status સાથે select કરો, raw UUID નહીં) — Availability tab ના "Ledger" quick-jump
button (row પર click) સાથે પણ સુસંગત, કારણ બંને એક જ `materialLots` list share કરે છે (parent
`InventoryPage` માં એક જ વાર fetch થાય, ActionModal ને prop તરીકે પણ પસાર થાય — duplicate fetch નહીં).

**⚠️ Honest નોંધ — આ 2 નવા endpoint શા માટે નવા છે:** Document 20 ના પોતાના declared 8-op API list માં ન
`warehouse_location` ન `material_container` ની કોઈ list operation હતી (SG-081 — locations માટે
explicit-recorded decision "ક્યારેય guessed endpoint ના ઉમેરવો", કારણ future API-completion addendum
સાથે conflict થવાનું જોખમ). **SG-081 હવે read-side માટે PARTIALLY RESOLVED છે** (2026-09-07) — logic:
plain **read-only GET listing** કોઈ future write/CRUD contract સાથે conflict નથી કરતું (કંઈ overwrite
નથી કરવાનું, ફક્ત વાંચવાનું), જ્યારે manual UUID entry (production database સીધું જોવું પડે) એ
usability/safety risk આ કરતાં મોટું હતું. *(§6.4.6 જુઓ — write-side પણ હવે resolve થયેલ છે, create
endpoint બન્યો છે.)* Full detail: `18_SPEC_GAPS.md` SG-081.

#### 6.4.2 ⚠️ Honest નોંધ — "Receive lot" quick shortcut (§6, ઉપરની ટેબલ) નો lot કદી Transfer/Reserve ના થઈ શકે

Code-verified (`receive_material_lot()`, `material/commands.py:202-238`): `/material-lots` ના "Receive
lot" quick-shortcut path **કોઈ `MaterialContainer` બનાવતું જ નથી** — ફક્ત `MaterialLot` row બને છે, કોઈ
container નહીં. પરિણામ:

- **Transfer** કદી ના થઈ શકે — `CreateInventoryTransferCommand.container_id` ફરજિયાત field છે, અને કોઈ
  container છે જ નહીં.
- **Reserve** કદી eligible ના બને — FEFO candidate query `MaterialContainer` સાથે join કરે છે
  (`container_status == "active"`); container ના હોય તો કોઈ candidate ના મળે, `create_inventory_reservation`
  "No eligible released, non-expired, non-retest-due lot/container..." error આપશે.
- **Cycle count**/**Adjustment** હજુ ચાલે — બંનેમાં Container ID **optional** છે (`_lock_or_create_balance`
  `container_id=None` ને balance key તરીકે સ્વીકારે છે), એટલે quick-shortcut lot ને directly કોઈ location
  પર count/adjust કરી initial balance બનાવી શકાય — પણ Transfer/Reserve હજુ પણ નહીં ચાલે (container ના હોવાથી).

**Client ને કહેવું:** "Full inventory movement" ડેમો કરવો હોય તો lot **proper `/material-receipts` →
Examine** path થી જ બનવો જોઈએ (§6.2) — quick shortcut lot ફક્ત lot-level master data માટે છે, warehouse
movement માટે નહીં (roadmap item, code-level limitation, bug નહીં). **UI હવે આ ને proactively બતાવે
છે** (§6.4.1) — Transfer modal માં આવો lot select કરો એટલે Container dropdown ખાલી રહે અને hint text
સીધો સમજાવે "No containers exist for this lot — it was created via the 'Receive lot' quick shortcut…",
DB query જોવાની જરૂર નથી.

#### 6.4.3 Concrete ડેમો ડેટા — `LOT-DRUG-2601` (§6.2 માંથી, 1 container, code `LOT-DRUG-2601-C001`)

**Warehouse locations (`SITE1`/`WH1`, seed-only master data — Document 20 ના 8-op API list માં કોઈ CRUD
નથી, SG-081 — આ 3 જ કાયમ માટે exist કરશે, code verified `scripts/seed.py`
`WAREHOUSE_LOCATION_FLOOR`):**

| Location code | Zone type | Location ID (UUID) |
|---|---|---|
| `QUARANTINE-01` | `quarantine` | `c1565059-7bde-4f9e-85dd-22411f6d6db9` |
| `RELEASED-01` | `released` | `f5dd1413-6ab4-44f9-9c03-63cde8f1a048` |
| `REJECTED-01` | `rejected` | `73c00c9e-f841-447f-af34-e11b4caaadeb` |

*(આ IDs આ demo environment ના — `SITE1` ફરીથી seed થાય તો બદલાઈ જાય; production માં client ના પોતાના
warehouse layout પ્રમાણે અલગ locations seed થશે.)*

**Step 1 — Put-away transfer (Quarantine માં મૂકવું, examine પછી તરત):** `operator1`/`supervisor1` →
Inventory → **Transfer**:

| Field | Value | નોંધ |
|---|---|---|
| Material lot | dropdown → `LOT-DRUG-2601 — MAT-DRUG-MERIDIZ (quarantine)` પસંદ કરો | |
| Container | dropdown auto-populate થાય → `LOT-DRUG-2601-C001 — 12.500 L` પસંદ કરો | lot select કર્યા પછી જ dropdown ભરાય (§6.4.1) |
| From location | ખાલી છોડો (`(none — put-away)`) | code: `from_location_id=None` = "આ container નું પહેલું ledger entry" (put-away), `transaction_type=RECEIPT` |
| To location | dropdown → `QUARANTINE-01 (quarantine)` પસંદ કરો | lot status `quarantine` છે, zone-compatibility rule (`_ZONE_STATUS_COMPAT`) એને `quarantine` zone માં જ સ્વીકારે |
| Quantity | `12.500` (container ની પૂરી `current_quantity`, gross = accepted since accepted left blank) | પહેલા put-away માટે quantity **બરાબર** container ની પૂરી quantity જ હોવી જોઈએ (code check) |

**Step 2 — QC disposition (§6.3 જુઓ)** — `qc.reviewer` lot ને `Released` કરે. **⚠️ આ ક્ષણે material
હજુ Quarantine zone માં જ ઊભો છે** (§6.4.0) — Availability tab માં હજુ નહીં દેખાય.

**Step 3 — Release-zone transfer (physical move QC decision પ્રમાણે):**

| Field | Value |
|---|---|
| Material lot | dropdown → એ જ `LOT-DRUG-2601` |
| Container | dropdown → એ જ `LOT-DRUG-2601-C001` |
| From location | dropdown → `QUARANTINE-01` |
| To location | dropdown → `RELEASED-01` — lot status હવે `released`, zone-rule `released` zone જ સ્વીકારે |
| Quantity | `12.500` |

Submit → **હવે** Availability tab પર Material = `MAT-DRUG-MERIDIZ` શોધો → row દેખાશે, Location =
`RELEASED-01`, Available = `12.500 L`.

**Step 4 — Reserve** (`inventory_reservation.create`, Operator/Supervisor) — **⚠️ sequencing નોંધ:**
`CreateInventoryReservationCommand` ને એક **પહેલેથી અસ્તિત્વમાં હોય એવો Batch** જોઈએ (`session.get(Batch,
cmd.batch_id)` — ના મળે તો `NotFoundError`). Batch Phase 7 (§11) માં જ બને છે — એટલે **આ ડેમોમાં Reserve
ને ખરેખર live demonstrate કરવો હોય તો Phase 7 પછી જ કરવો** (batch number `MJ-PFS-B-2601`), Phase 2 માં
ફક્ત fields સમજાવવા:

| Field | Value |
|---|---|
| Batch | dropdown → `MJ-PFS-B-2601 — MeridiJect PFS (...)` (Phase 7 create પછી જ list માં દેખાય) |
| Material | dropdown → `MAT-DRUG-MERIDIZ` |
| Quantity | `2.000` |
| UOM | `L` |

Submit → server FEFO પ્રમાણે (expiry ascending, પછી received_at ascending) જાતે eligible lot/container
પસંદ કરે — તમે lot pick નથી કરતા (INV-FR-010/012). Availability tab ફરી ખોલો → Available હવે `10.500 L`
(2.000 `reserved` માં ગયું).

**Step 5 — Cycle count** (routine, unsigned) — physically ફરી ગણ્યું `12.300 L` (`0.200 L` variance,
ઓછું મળ્યું — spillage):

| Field | Value |
|---|---|
| Material lot | dropdown → `LOT-DRUG-2601` |
| Container | dropdown → `LOT-DRUG-2601-C001` |
| Location | dropdown → `RELEASED-01` |
| Counted quantity | `12.300` |
| Reason/notes | `Routine monthly cycle count — minor spillage observed` |

Submit → system delta ગણે (`counted − on_hand`), `ADJUST_NEGATIVE` ledger entry બને, `on_hand` = `12.300`.
**Available** પર negative check છે — counted quantity, already-reserved quantity કરતાં ઓછું ના જઈ શકે
(code: `new_available < 0` guard).

**Step 6 — Request adjustment** (exceptional, reason ફરજિયાત) — ધારો કે physical audit માં ફરક મળ્યો:

| Field | Value |
|---|---|
| Material lot | dropdown → `LOT-DRUG-2601` |
| Container | dropdown → `LOT-DRUG-2601-C001` |
| Location | dropdown → `RELEASED-01` |
| Expected quantity | `12.300` |
| Observed quantity | `12.100` |
| Reason (ફરજિયાત) | `Physical count discrepancy found during quarterly warehouse audit — 0.200 L unaccounted, investigating` |

#### 6.4.4 સારાંશ — બધા 4 actions

| Action | Permission code | કોણ | Fields |
|---|---|---|---|
| Reserve material | `inventory_reservation.create` | Operator/Supervisor | Batch (dropdown), Material (dropdown), Quantity, UOM *(lot server-side FEFO પસંદ થાય — તમે lot નથી પસંદ કરતા; existing Batch જોઈએ)* |
| Transfer | `inventory_transaction.transfer` | Operator/Supervisor | Material lot (dropdown), Container (dropdown, lot select કર્યા પછી ભરાય, ફરજિયાત), From/To location (dropdown), Quantity |
| Cycle count | `inventory_cycle_count.execute` | Operator/Supervisor | Material lot (dropdown), Container (dropdown, optional), Location (dropdown), Counted quantity, Reason/notes |
| Request adjustment | `inventory_adjustment_request.create` | Operator/Supervisor | Material lot (dropdown), Container (dropdown, optional), Location (dropdown), Expected quantity, Observed quantity, Reason (ફરજિયાત) |

**Fixed 2026-09-07:** Batch/Material lot/Container/Location — **બધા 4 reference field હવે real dropdown
છે** (§6.4.1), કોઈ raw UUID હવે hand-type નથી કરવો પડતો. Batch dropdown 2026-09-08 થી `GET /batches/v1`
(the now-sole authoritative `gxp_batch` listing, §11/§19 #27) વાપરે છે — legacy `/batches` retired;
Container/Location dropdown 2 નવા read-only endpoints વાપરે છે (§6.4.1).

#### 6.4.5 Adjustment approve — હવે UI માં જ (built 2026-09-07)

**અગાઉ:** Adjustment request submit થઈ શકતું (`inventory_adjustment_request.create`), પણ **QA Releaser
approve** કરે એવી policy backend માં ready હોવા છતાં (`inventory_adjustment_request.approve` permission
code, સહી + requester-independence check — બધું code-verified) **frontend માં approve button જ નહોતું**
— request-only UI. **હવે built છે** (code-verified, `frontend/src/app/inventory/page.tsx` + 1 નવો
read-only backend endpoint `GET /inventory/v1/adjustments`):

**Adjustments tab હવે 2 ભાગમાં છે:**

1. **ઉપર** — "Request adjustment" button (પહેલાં જેવું જ જ, હવે dropdown fields સાથે — §6.4.1).
2. **નીચે** — **"Adjustment requests" ટેબલ** (નવું) — બધા adjustment request (કોઈ પણ status) દેખાય: Lot,
   Location, Expected, Observed, Variance (નકારાત્મક હોય તો red), Reason, Requested by, Requested (date),
   Status (Requested/Approved pill), અને છેલ્લી column માં **"Approve" button** — ફક્ત:
   - `canApprove` (Admin/QA Releaser role) હોય, **અને**
   - request status `requested` હોય (already-approved row પર button જ નથી), **અને**
   - **તમે પોતે એ request ના requester ના હો** (CON-FR-014 — self-approval button UI માં જ disabled,
     hover પર કારણ દેખાય: "You requested this — an independent QA Releaser must approve it") — server-side
     પણ આ જ ચેક `approve_inventory_adjustment_request()` માં પાછું થાય છે (defense-in-depth, ફક્ત UI hide
     નથી).

**Approve click → SignatureCeremony modal ખૂલે** (codebase નું shared signed-action component,
`components/shared/SignatureCeremony.tsx` — batch/deviation/OOS ના signed actions જેવો જ pattern):
variance/expected/observed/reason ની summary બતાવે → **Reason ફરજિયાત** (નવું reason, approval માટેનું —
request ના મૂળ reason કરતાં અલગ) → **password ફરી માંગે** (real e-signature, Document 106 row 55) →
submit → `POST /inventory/v1/adjustments/{id}/approve` → સફળ થાય તો balance update થાય
(`InventoryTransaction` ADJUST_POSITIVE/NEGATIVE row બને, request status = `approved`).

**Client demo moment:** `operator1`/`supervisor1` થી adjustment request કરો → `qa.releaser` login કરો →
Adjustments tab → Approve → **password ફરી માંગશે**. પછી **એ જ request ને ફરી** approve કરવાનો પ્રયત્ન
કરો (already `approved` status) — button જ નથી (row પર hવે Approve column ખાલી, status pill
"Approved"). અને `admin`/`supervisor1` (પોતે જ request કરનાર) થી login કરીને Approve button hover કરો —
**disabled**, SoD literally UI માં block થાય છે, ફક્ત policy document માં નહીં (IND-001/CON-FR-014 જેવો જ
negative-control moment, Phase 8 ના assembly-verify pattern ને મળતો).

#### 6.4.6 નવું warehouse location બનાવવું — હવે UI માં (built 2026-09-07, SG-081 write-side)

**અગાઉ:** `warehouse_location` seed-only master data હતું — `scripts/seed.py` સિવાય કોઈ પણ નવું location
ઉમેરવાનો રસ્તો જ નહોતો (§6.4.1 ના honest note પ્રમાણે). **હવે create endpoint + UI બંને built છે**
(code-verified, `services/gxp-api/app/modules/material/{commands,router}.py`
(`create_warehouse_location`/`post_create_warehouse_location`) + `frontend/src/app/inventory/page.tsx`
(`NewLocationModal`)):

- Inventory page ના header પર **"New location"** button (canManageLocations હોય તો જ દેખાય).
- Fields: **Warehouse code** (દા.ત. `WH1`), **Location code** (unique, દા.ત. `QUARANTINE-02`), **Zone
  type** (dropdown — `quarantine`/`released`/`rejected`/વગેરે, released/quarantine/rejected zone-compatibility
  rule ને directly drive કરે છે).
- Submit → `POST /inventory/v1/warehouse-locations` → નવું location તરત જ Transfer/Cycle count/Adjustment
  ના Location dropdown માં દેખાય (parent page ના `locations` list ને reload કરે).
- **Duplicate check code-verified:** એ જ site પર એ જ warehouse+location code બીજી વાર બનાવવાનો પ્રયત્ન
  કરો → clean `VALIDATION_FAILED` error (raw DB constraint error નહીં).

**⚠️ Honest નોંધ — access control:** આ action માટે **નવો permission code `warehouse_location.create`**
બનાવ્યો (project-owner ની specific સૂચના પ્રમાણે — ન Material/Supplier જેવો "કોઈ RBAC gate નહીં", ન
"Admin-only" — dedicated code) — **Admin/Supervisor** ને જ ગ્રાન્ટ કરેલો છે, `Operator` ને નહીં (batch/device
create ની જેમ જ "layout define કરવો" vs "એની સામે execute કરવું" split). Code-verified: `operator1` થી
call કરવાનો પ્રયત્ન → `403 ROLE_MISSING`.

**⚠️ Honest નોંધ — SG-081 હજુ પૂરેપૂરું resolved નથી:** ફક્ત **Create** built છે. Update/Rename/Delete
માટે હજુ કોઈ endpoint/UI નથી — location એક વાર બને પછી કાયમ માટે ત્યાં જ રહે છે (permanent, ભૂલથી ખોટો
zone type પસંદ કરો તો પણ સુધારી ના શકાય, નવો બનાવવો પડે). Client ને કહેવું: roadmap item, code-level
limitation. Full detail: `18_SPEC_GAPS.md` SG-081.

---

## 7. Phase 3 — Equipment Area + Equipment Asset + Device Lot + Sterilization (જગ્યા + મશીન + ડિવાઇસ + Sterilization)

**કોણ:** `equipment.admin` (area + asset create + qualify) → `calibration.tech` (calibrate) →
`supervisor1` (device lot create) → `qa.reviewer` (cycle **profile** author, SG-203) →
`sterilization.operator` (cycle create/start/data) → `qa.reviewer` (cycle review, **સહી**). **ક્યાં:**
`/equipment`, `/devices`, `/sterilization`. **Backend:** `POST /equipment/v1/areas`, `/assets`,
`.../qualifications`, `.../calibrations`; `POST /devices/v1/lots`, `/devices/v1/units/bulk-create`;
`POST /sterilization/v1/profiles`, `/cycles`, `.../start`, `.../data`, `.../review`. **Doc:** 38
(equipment), 12 (device), 42 (sterilization).

**⚠️ 2026-09-16 fix — આ Phase પહેલાં Equipment **Area** ક્યાંય બનતું જ નહોતું:** આ section પહેલાં ફક્ત
Equipment **Asset** (§7.2, `LINE-PFS-01`) ની detail આપતું હતું, "Equipment area/line" field (§12.1 Op3,
§15.1) અને Line Clearance (§14) બંને એ જ `LINE-PFS-01` code વાપરતા હતા — પણ **Equipment Area એ
`equipment.equipment_areas` નામનું સાવ અલગ table/FK છે, Equipment Asset (`equipment.equipment_assets`)
નહીં** — `LINE-PFS-01` એ asset code છે, કોઈ area એ નામનું exist જ નથી કરતું (live DB માં ચકાસેલું). હવે
§7.1 એ ખૂટતું Equipment Area પગલું ઉમેરે છે; §7.2/§14/§15.1/§12.1 Op3 બધા ઠીક કર્યા.

### 7.0 Equipment Area, Equipment Asset અને Device Lot કેમ જરૂરી? (સાદી ભાષામાં)

**Equipment Area** = ભૌતિક **જગ્યા/ઓરડો** (cleanroom, fill suite, warehouse) — રિયલ વર્લ્ડ ઉદાહરણ:
ફેક્ટરીના નકશા પર દોરેલો "Room 204 — Grade A Fill Suite" એ ઝોન. Line Clearance (§14) અને DDCP readiness
નું "Equipment area/line" ચેક (§15.1) **આ જ table** સામે થાય છે — machine સામે નહીં.

**Equipment Asset** = ચોક્કસ **મશીન/લાઇન** નું master data — રિયલ વર્લ્ડમાં ફેક્ટરીના દરેક મશીનનું પોતાનું
"ID કાર્ડ" હોય (કયું મશીન, કયો manufacturer/model, ક્યાં install થયું). **Area ≠ Asset** — એક area (room)
માં ઘણા asset (machines) હોઈ શકે, પણ code માં આ 2 જુદા table છે, કોઈ automatic link નથી (asset ને
`location_id` field છે, પણ demo data માં set નથી કરવું જરૂરી).

| Field | મતલબ | ઉદાહરણ |
|---|---|---|
| Area code | જગ્યાનું unique ID | `AREA-GRADE-A` |
| Area type | કયા પ્રકારની જગ્યા (free text) | `cleanroom` |
| Classification | Cleanroom grade | `ISO_5` |
| Equipment code | મશીનનું unique ID | `LINE-PFS-01` |
| Manufacturer/Model | મશીન કોણે બનાવ્યું, કયું મોડેલ | `Groninger` / `KFL-100` |
| Dedicated | આ મશીન **ફક્ત એક જ પ્રોડક્ટ** માટે વપરાય છે, કે multiple products માટે shared છે | `No` — shared line, એટલે દરેક પ્રોડક્ટ બદલાય ત્યારે cleaning validation જરૂરી (Dedicated = `Yes` હોય તો cross-contamination risk ઓછું, કારણ કે બીજું કોઈ પ્રોડક્ટ ક્યારેય એ મશીનમાં ગયું જ નથી) |

**Qualify (IQ/OQ/PQ)** — 3-સ્ટેપ ચેક કે મશીન વાપરવા લાયક છે: **IQ** (Installation Qualification — સાચું
install થયું છે?) → **OQ** (Operational Qualification — સાચું ચાલે છે?) → **PQ** (Performance
Qualification — actual production conditions માં consistently કામ કરે છે?). ત્રણેય પાસ ના થાય ત્યાં
સુધી મશીન production-eligible નથી ગણાતું.

**Calibrate** — measuring instruments (temperature, weight, pressure...) ને નિયમિત ધોરણે ચેક કરવું કે
એ સાચું માપે છે. Calibration expire થઈ ગયું હોય તો એ મશીનના measurements પર વિશ્વાસ ના કરાય — એટલે DDCP
readiness check (Phase 11) આને blocker તરીકે વાપરે છે.

**Device Lot** — ready-to-use device components (સિરીંજ બેરલ, needle) નું lot. **ફક્ત RELEASED Product
Version સામે જ બની શકે** (code-verified `_assert_product_version_released` check) — કારણ કે device
lot નો UDI-DI ચોક્કસ product version સાથે કાયમ માટે જોડાયેલો રહે છે, draft/unreleased version પર
bind ના કરાય.

| Field | મતલબ |
|---|---|
| Product version | કયા RELEASED product version માટે આ device lot છે (Phase 4 release પછી જ ઉપલબ્ધ) |
| UDI-DI | **Unique Device Identifier** — US FDA નો ફરજિયાત device-identification કોડ, દરેક product version માટે unique (બારકોડ જેવું, પણ regulatory requirement) |

### 7.1 Equipment Area — Grade A Fill Suite (`equipment.admin`, `/equipment` → "New area")

**⚠️ આ પગલું પહેલાં ક્યાંય નહોતું — ખૂટતું હતું (2026-09-16 fix).** Line Clearance (§14) અને DDCP
readiness ના "Equipment area/line" ચેક (§15.1, §12.1 Op3) ને આ area ફરજિયાત જોઈએ.

| Field | Data | ફરજિયાત? |
|---|---|---|
| Area code | `AREA-GRADE-A` | ✅ — site-wide unique |
| Area type | `fill_suite` | — free text |
| Classification | `ISO_5` | — cleanroom grade |
| Criticality | `high` | — free text |
| Cleanliness status | ખાલી (§14 નું line clearance પછીથી update કરશે) | — |

### 7.2 Equipment Asset — Fill/Assembly Line (`equipment.admin` → `/equipment` → "New asset")

| Field | Data |
|---|---|
| Equipment code | `LINE-PFS-01` |
| Manufacturer/Model | `Groninger` / `KFL-100` |
| Dedicated | `No` |

**Record qualification** (`equipment.admin` → equipment detail → "Record qualification" — **⚠️
`Equipment Administrator` role જ આ બટન જુએ છે**, code-verified `canCreateEquipment`):

| Field | Data |
|---|---|
| Qualification status | `qualified` |
| Qualified | ✅ Yes |
| Effective date | આજ |
| Expiry date | +2 વર્ષ |

**Record calibration** (**⚠️ અલગ role — `calibration.tech` (Calibration Technician) જ આ બટન જુએ છે,
`equipment.admin` ને નહીં — code-verified `canCalibrateEquipment`, frontend+backend બંનેમાં same split,
§ ની નીચે honest નોંધ જુઓ**): `calibration.tech` login → એ જ equipment detail → "Record calibration":

| Field | Data |
|---|---|
| Performed date | આજ |
| Next due date | +1 વર્ષ |
| Result | `pass` |
| Standard reference | `NIST-TRACE-2026` |

બંને પૂરા થાય પછી → **eligible for use** (DDCP readiness check §15.1 નું `LINE_NOT_READY`/"Filler
equipment not eligible" blocker આ જ 2 status (qualification+calibration) વાપરે છે — code:
`equipment_commands._ineligibility_reasons()`).

**⚠️ પ્રામાણિકતા નોંધ — "Calibrate"/"Maintenance" બટન equipment.admin ને કેમ નથી દેખાતું (bug નથી, SoD
by design):** `Equipment Administrator` role ને ફક્ત `equipment_asset.create`/`.qualify` permission છે
(`scripts/seed.py` `ROLE_PERMISSIONS`) — `.calibrate` ફક્ત `Calibration Technician` ને, `.maintain` ફક્ત
`Maintenance Technician` ને, અલગ-અલગ demo user (`calibration.tech`/`maintenance.tech`,
`ChangeMe123!`). Frontend બટન (`canCalibrateEquipment`/`canMaintainEquipment`) role ના હોય તો **દેખાય જ
નહીં** (disabled નહીં, hide) — DDCP Engineer/Operator, Aseptic Operator/Supervisor જેવો જ SoD pattern:
"કોણ install કરે" ≠ "કોણ calibrate/maintain કરે". `admin` (બધા role ધરાવે) થી 1 જ session માં demo
ચલાવવું હોય તો ચાલે, પણ real SoD demo બતાવવો હોય તો role બદલવો.

**⚠️ Area (§7.1) અને Asset (§7.2) — 2 જુદા master data, 2 જુદો purpose:** §15.1 નું "Equipment area/line"
field `AREA-GRADE-A` (§7.1) લે છે, "Filler equipment" field `LINE-PFS-01` (§7.2) લે છે — બંને field ને
**એક જ code આપવો ખોટો છે** (પહેલાં આ doc ની ભૂલ હતી — હવે ઠીક).

### 7.4 Sterilization Cycle — Needle Component ને "Ready to Use" કરવું

**કોણ:** `qa.reviewer` (cycle profile author — SG-203) → `sterilization.operator` (cycle create/start/data)
→ `qa.reviewer` (review). **⚠️ same-actor rule ફક્ત cycle start ≠ cycle review વચ્ચે છે** (profile author
અને cycle reviewer બંને `qa.reviewer` હોય તો પણ કોઈ conflict નથી — SIG-FR-018 ફક્ત
`cycle.started_by_user_id` ને ચેક કરે છે, profile author ને નહીં). **ક્યાં:** `/sterilization`. **Doc:**
42 (SPEC-EQP-005). **Full field/RBAC/state-machine reference:**
`Sterilization_Aseptic_Comprehensive_Test_Manual_Gujarati.md`.

**કેમ જરૂરી? (સાદી ભાષામાં):** §10.1 નું DDCP profile needle constituent ને `required_state = Ready to
use` માંગે છે — આ સ્થિતિ ખાલી declare કરવાથી નથી મળતી, ખરેખર **sterilization cycle run કરીને, independent
QA reviewer એ accept કરે** ત્યારે જ મળે છે (§12.1 Op 2 નો "Sterilization/depyrogenation reference" field
આ જ cycle ના load item ID માંગે છે).

**✅ 2026-09-16 RESOLVED — Sterilization cycle profile ને હવે real create UI છે (SG-203).** પહેલાં ફક્ત
direct SQL insert workaround હતો (backend command જ નહોતું) — **project-owner-directed, પૂછીને 2 નિર્ણય
લીધા:** (1) profile ને **QA Reviewer** authorize કરે (Sterilization Operator નહીં — જે role પછીથી cycle
data ને independent review કરે એ જ role spec પણ define કરે, "કોણ define કરે ≠ કોણ execute કરે" split
યથાવત્ રાખવા), (2) **direct-to-RELEASED** (aseptic profile ના §8.1 જેવો જ, draft/review stage નહીં).

`qa.reviewer` login → `/sterilization` → "New sterilization cycle profile" button:

| Field | Data | ફરજિયાત? |
|---|---|---|
| Profile number | `STR-PROC-001` | ✅ |
| Version no. | `1` | ✅ |
| Process type | `steam_autoclave` (dropdown) | ✅ |
| Validation reference | `PQ-STR-2026-004` | — |
| Sterile status validity (hours) | `720` (= 30 દિવસ — cycle ACCEPTED થયા પછી load item કેટલો સમય "eligible" રહે) | — |
| Critical parameters (kv, flat) | `temperature_c_min` → `121`; `hold_minutes_min` → `15` | — |
| Indicator requirements (kv) | `biological_indicator` → `required` | — |

Submit → સીધું state **RELEASED** — "Cycle profile version" dropdown માં `STR-PROC-001 v1 -
steam_autoclave` તરત દેખાશે. **⚠️ Sterilization Operator (`sterilization.operator`) થી આ બટન કરવાનો
પ્રયત્ન** → button જ ના દેખાય (frontend `canCreateCycleProfile`), raw API call કરો તો `403 ROLE_MISSING`
— code-verified negative test.

**Create process cycle** (`sterilization.operator` → `/sterilization` → "Create process cycle"):

| Field | Data |
|---|---|
| Process type | `steam_autoclave` |
| Equipment | `LINE-PFS-01` (§7.2 — qualified + calibrated હોવું જ જોઈએ, નહીં તો `422 STERILIZER_INELIGIBLE`) |
| Cycle profile version | `STR-PROC-001 v1` |
| Batch | ખાલી |
| Load items — Row 1 | Item type `component`; Item reference `LOT-DEV-2601` (**Phase 2 નો real released device material lot** — manual entry, dropdown નથી); Position `Tray 1` |

Submit → state **DRAFT**.

**Start cycle (સહી)** — "Start cycle (sign)" → password → state **CYCLE_STARTED**.

**Record cycle data (2 વાર):**

*પહેલી વાર (running):*

| Field | Data |
|---|---|
| Controller cycle ID | `CTRL-STR-2601-01` |
| Parameter data | `temperature_c` → `121.4`; `pressure_bar` → `2.05` |
| Critical alarm | `No` |
| Final batch of data | `No` |

Submit → state **CYCLE_RUNNING**.

*બીજી વાર (final):*

| Field | Data |
|---|---|
| Controller cycle ID | `CTRL-STR-2601-01` |
| Parameter data | `hold_minutes` → `16` |
| Indicator results | `BI_1` → `negative` |
| Critical alarm | `No` |
| Final batch of data | **Yes** |

Submit → state **REVIEW_PENDING**.

**Review (સહી, independent — `qa.reviewer` login, `sterilization.operator` થી અલગ user):**

| Field | Data |
|---|---|
| Decision | `Accept` |

Submit → password → state **ACCEPTED**, `LOT-DEV-2601` ના load item નો `sterile_status = eligible` (+
expiry, profile ના `sterile_status_validity_hours=720` = 30 દિવસ). **Cycle detail ના "Load items" ટેબલ
માંથી આ item ની ID copy કરો** — §12.1 Op 2 ના DEVICE handoff Accept ના "Sterilization/depyrogenation
reference" field માં આ જ ID પેસ્ટ કરવાની છે.

**Client demo moment:** `sterilization.operator` (જેણે start કર્યું) થી review કરવાનો પ્રયત્ન — **fail
થશે** (SIG-FR-018, same-actor block, code-verified `cycle.started_by_user_id == actor_user_id`).
`qa.reviewer` (અલગ user) → succeed.

### 7.3 Device Lot + Device Units (`supervisor1`/`admin` → `/devices` → "Device lot & unit assembly")

Device lot **released Product Version** સામે જ બની શકે (`_assert_product_version_released` — code
verified) — એટલે આ step Phase 4 (Product Master release, §8) **પછી જ** થાય. **2 અલગ સ્ટેપ** (backend 2
અલગ endpoint છે — `POST /devices/v1/lots` પછી `POST /devices/v1/units/bulk-create`):

**સ્ટેપ 1 — Lot બનાવવો:**

| Field | Data | ફરજિયાત? |
|---|---|---|
| Product version | MeridiJect PFS v1 (dropdown, Phase 4 release પછી જ RELEASED list માં દેખાય) | ✅ |
| Batch | ખાલી (optional — dropdown, producing batch જોડવું હોય તો, Phase 7 create પછી જ ઉપલબ્ધ) | — |
| UDI-DI | `(01)00812345678901` | — Unique Device Identifier, US FDA ફરજિયાત device-identification કોડ |

Submit → "Device lot created" banner, Lot ID દેખાય.

**સ્ટેપ 2 — Serial units ઉમેરવા (એ જ lot ID પર, તરત નીચે ફોર્મ ખૂલે છે):**

| Field | Data |
|---|---|
| Serials (એક લાઇન દીઠ 1, અથવા comma-separated) | `MJ-DEV-0001`<br>`MJ-DEV-0002`<br>`MJ-DEV-0003` |

Submit → `POST /devices/v1/units/bulk-create` → એ lot સાથે જોડાયેલા real device unit (per-serial) records
બને છે — "3 units created" જેવો count દેખાય.

---

## 8. Phase 4 — Product Master (પ્રોડક્ટ ટેમ્પલેટ)

**કોણ:** `process.engineer`/`admin` (`product.author` — draft/edit/submit) → `qa.releaser`/`admin`
(`product.release` — **સહી**, author થી અલગ વ્યક્તિ). **2026-09-08 થી Product Master ને Recipe Master
જેવો જ author≠releaser split મળ્યો** (§8.5). **ક્યાં:** `/product-master` (⚠️ `/products` નહીં — એ
જૂનું/generic CRUD page છે, regulated draft→submit→release workflow `/product-master` માં જ છે —
`canAuthorProduct` check verified).
**Backend:** `/products/v1/drafts` (create — `POST`), `/products/v1/drafts/{id}` (edit — **`PUT`, not
`PATCH`**; now wired to a real "Edit" button, §8.4), `/drafts/{id}/submit`, `/drafts/{id}/release`,
`/{id}/validate-completeness` (advisory check), `/{id}/suspend`, `/{id}/reinstate`. **Doc:** 09
(SPEC-EBMR-001). *(Fields re-verified 2026-09-07 field-by-field against
`frontend/src/app/product-master/page.tsx` (`DraftModal`/`EditDraftModal`/`ConstituentEditor`) and
`services/gxp-api/app/modules/product_master/{commands,service,models}.py`.)*

**Fixed 2026-09-07:** `/products` sidebar navigation માંથી hide કરી દીધું (`Sidebar.tsx`) — demo દરમિયાન
હવે client ને confusing legacy link ક્યાંય નહીં દેખાય. **⚠️ Honest નોંધ:** આ ફક્ત nav-level hide છે —
`/products` route અને એના backend endpoints (`POST`/`PATCH`/`DELETE /products`) હજુ સીધા URL/API થી
reachable છે, code-verified **કોઈ RBAC gate નથી** create/update પર (ફક્ત delete ને `platform.administer`
જોઈએ). આ Product/Recipe/Batch master ના **બે સ્વતંત્ર authoritative store** હોવાના મોટા architecture
issue નો જ ભાગ છે — પહેલેથી જ **SG-173** તરીકે logged (AG-05 violation, migration/cutover plan
project-owner માટે reserved) — આ pass માં ફક્ત UI hide કર્યું, backend endpoint close/gate કરવાનો નિર્ણય
SG-173 ના scope નો છે, અલગથી પૂછવો પડશે.

**કેમ જરૂરી? (સાદી ભાષામાં):** Product Master = "શું બનાવવું છે" નું master ટેમ્પલેટ — batch execution
પહેલાં આ template **RELEASED** હોવું જ જોઈએ. રિયલ વર્લ્ડ ઉદાહરણ: recipe book છપાવતાં પહેલાં એને ઘણી
વાર draft માં edit કરો, ફાઇનલ approve થાય પછી જ પ્રિન્ટ (release) — પ્રિન્ટ થયા પછી એ જ કોપી ફરી ના
બદલાય, નવી edition (નવું version) છાપવી પડે. *(2026-09-07 સવારે આ analogy નો "draft stage માં ભૂલ
સુધારી શકાય" ભાગ code-verified ખોટો હતો — કોઈ Edit UI જ નહોતું. **એ જ દિવસે પછી fix થયું** — જુઓ §8.4,
હવે analogy ફરી સાચી છે.)*

### 8.1 "New product draft" modal — real fields (code-verified, updated 2026-09-07)

`admin` → "New draft" button → modal ખૂલે. **Core fields** (પહેલેથી હતા):

| Field | મતલબ | ઉદાહરણ | ફરજિયાત? |
|---|---|---|---|
| Business ID | Internal ઓળખ code (`product_business_id`) | `MERIDIJECT-PFS` | હા |
| Product code | Batch/label પર વપરાતો code — ખાલી છોડો તો Business ID જ કોપી થાય (UI hint) | `MJ-PFS-40MG` | ના (defaults) |
| Version no. | આ ચોક્કસ version નંબર — auto-increment નથી, તમે જાતે ટાઈપ કરો છો; એ જ Business ID + Version no ફરી વાપરો તો `ValidationFailedError` (code: `create_draft()` duplicate check) | `1` | હા |
| Name | Product નું નામ | `MeridiJect™ Prefilled Syringe 40mg` | હા |
| Site | dropdown — registered sites માંથી | `Demo Site 1` | હા |
| Manufacturing profile | dropdown — **ફક્ત આ 5 જ hardcoded option છે** (§8.2 જુઓ): `pharma`/`device`/`injectable_ddcp`/`inhalation_ddcp`/`drug_eluting_device` | `injectable_ddcp` (PFS = injectable) | હા |
| Sterile process profile | **✅ FIXED 2026-09-07 — હવે real dropdown** (§8.3 જુઓ), site ના RELEASED sterile process profile માંથી પસંદ કરો | `ASP-PROC-001 v1 — ISO_5` | Conditionally — profile `injectable_ddcp`/`inhalation_ddcp` હોય તો **Release વખતે** જોઈએ (§8.3) |
| Device model code | free text | `MJ-DEV-01` | Conditionally — "UDI applicable" check હોય તો **Release વખતે** જોઈએ |
| UDI applicable | checkbox | ✅ (PFS device component હોવાથી) | ના |

**✅ FIXED 2026-09-07 — Combination product fields + Constituents, હવે modal માં જ છે** (code-verified,
`DraftModal`/`ConstituentEditor` — no backend change needed, `CreateProductDraftCommand` already accepted
all of this, only the UI never exposed it):

| Field | મતલબ | ઉદાહરણ |
|---|---|---|
| Combination product type | Free text | `drug-device-combination` |
| Strength value / UOM | બે અલગ field — quantity + unit | `40` / `mg` |
| PMOA reference | Free text, optional | — |
| Part 4 profile code | Free text, optional | — |
| Finished tracking strategy | Free text, optional | `lot` |
| **Constituents** (repeatable) | દરેક row = Type (dropdown `DRUG`/`BIOLOGIC`/`DEVICE`/`PACKAGING`/`LABEL` — DDCP module ના જ vocabulary માંથી, UI consistency માટે), Role code (free text), **Constituent's own Business ID** (lookup — નીચે જુઓ), Source site (optional), Tracking strategy (optional), Sequence no (optional) | Row 1: `DRUG`/`primary_drug`/lookup `MERIDIZUMAB-BULK`; Row 2: `DEVICE`/`device_component`/lookup `SYR-1ML-BARREL` |

**Constituent lookup કેવી રીતે કામ કરે:** "meal kit" analogy સાચી છે — drug/device પોતે અલગ Product
Master records હોવા જોઈએ (પોતાનું Business ID + Version). Modal માં constituent add કરવા "Constituent's
Business ID" ટાઈપ કરો → "Find versions" → એ Business ID ના existing versions (name/version/lifecycle
state સાથે) button તરીકે દેખાય → click કરીને પસંદ કરો → "Add constituent". **આ જ lookup**, page ના
top-level "Look up versions" search જેવો જ endpoint વાપરે છે (`GET /products/v1/{business_id}/versions`)
— કોઈ નવો backend endpoint જોઈતો નહોતો.

**⚠️ Honest નોંધ:** Constituent add કરવા પહેલાં એ constituent (દા.ત. `MERIDIZUMAB-BULK`) નું પોતાનું
Product Master draft **પહેલેથી બનેલું હોવું જોઈએ** — parent (combination) product બનાવતાં પહેલાં drug
અને device ના પોતાના Product Master version પહેલાં બનાવવા પડશે (demo order: પહેલાં
`MERIDIZUMAB-BULK`/`SYR-1ML-BARREL` ના draft, પછી `MERIDIJECT-PFS` નો draft, એના constituents માં એ બે
reference કરો).

### 8.2 Manufacturing profile — 5 option, ફક્ત આ 5 જ "supported" ગણાય

Code-verified (`service.py` `SUPPORTED_MANUFACTURING_PROFILES`): dropdown ના બધા 5 option
(`pharma`/`device`/`injectable_ddcp`/`inhalation_ddcp`/`drug_eluting_device`) ખરેખર "supported" ગણાય છે
(PRD-FR-009) — કોઈ dropdown option "unsupported" નથી (સારી consistency, ખરાબ UX gap નથી). MeridiJect PFS
(prefilled syringe, injectable biologic) માટે **`injectable_ddcp`** સાચો પસંદ છે.

### 8.3 "Sterile process profile" — Release ને block કરી શકે, હવે real registry સામે validate થાય છે

Code-verified (`service.py` `STERILE_REQUIRED_PROFILES = {"injectable_ddcp", "inhalation_ddcp"}` +
`validate_completeness()`): **profile `injectable_ddcp` પસંદ કરો અને Sterile process profile ખાલી
છોડો** → draft create/submit તો સફળ થશે (**required-ness ફક્ત Release વખતે જ ચેક થાય છે, by design**)
→ **Release કરવાનો પ્રયત્ન કરો ત્યારે** `ValidationFailedError` ("sterile_profile_id is required for
this manufacturing profile (PRD-FR-010)") — code-verified `release_product_version()` માં. એ જ રીતે
"UDI applicable" check કર્યું હોય પણ Device model code ખાલી હોય તો પણ Release એ જ રીતે block થાય
(PRD-FR-012).

**✅ FIXED 2026-09-07 — હવે real sterile-profile registry સામે validate થાય છે.** પહેલાં આ field ફક્ત
raw UUID text લેતું અને કોઈ existing sterile-profile entity સામે ચેક નહોતું કરતું (કોઈ પણ random UUID
ચાલી જતું). Fix (code-verified):

- **Real registry મળ્યો:** Document 40 (`equipment.aseptic_profile_versions`, seed data `ASP-PROC-001`
  v1, ISO_5, state `RELEASED`) — WP-06 ના aseptic/sterile operations module એ જ registry પહેલેથી real
  functionality (readiness composition) માટે વાપરે છે; Product Master એ પોતાનું `sterile_profile_id`
  ક્યારેય એની સામે cross-check નહોતું કરતું, ફક્ત "field is null?" ચેક કરતું.
- **નવો backend check** (`product_master/commands.py::_validate_sterile_profile`, `create_draft` અને
  `update_draft` બંનેમાં): sterile_profile_id આપ્યું હોય તો હવે (1) એ id ખરેખર
  `aseptic_profile_versions` માં exist કરે છે, (2) એ profile state `RELEASED` છે, અને (3) એ profile એ જ
  site નું છે — ત્રણમાંથી કોઈ પણ ચેક નિષ્ફળ જાય તો **create/update વખતે જ** `ValidationFailedError`
  ("PRD-FR-010"), random UUID હવે **create પર જ** block થાય, Release સુધી રાહ જોવી નથી પડતી.
- **નવો real dropdown** (`GET /products/v1/sterile-profiles?site_id=...`, નવો endpoint): "New product
  draft" અને "Edit draft" બંને modal માં field હવે free-text Input ના બદલે Select છે — site ના
  RELEASED sterile process profile ની list બતાવે (દા.ત. `ASP-PROC-001 v1 — ISO_5`), UUID જાતે ટાઈપ
  કરવાની જરૂર જ નથી. VersionDetailModal (read-only view) પણ હવે raw UUID ના બદલે resolved label બતાવે
  છે.
- **✅ પણ FIXED 2026-09-07 (same day, follow-up) — હવે નવો sterile process profile બનાવી પણ શકાય.**
  પહેલાં ફક્ત એક જ seeded profile (`ASP-PROC-001`) existed, કોઈ create UI/API જ નહોતું (Document 40 ના
  own 7-op API list માં profile create/release operation જ નથી — `18_SPEC_GAPS.md` SG-176). હવે
  **`/aseptic` page** પર "New sterile process profile" button છે (Admin + Aseptic Supervisor role જોઈએ) —
  Profile number, Version no., Required area classification (ISO_5/6/7/8/Unclassified), Validation
  reference ભરીને directly `RELEASED` state માં profile બને છે. એ જ profile તરત Product Master ના
  dropdown માં પણ દેખાય (બંને એક જ `GET .../sterile-profiles` cross-module query function વાપરે છે).
  Backend: `POST /aseptic/v1/profiles`.
- **✅ પણ FIXED 2026-09-07 (same day, બીજો follow-up) — હવે list દેખાય છે + Supersede (= update/delete)
  UI પણ છે.** `/aseptic` page પર "New sterile process profile" button નીચે હવે **"Sterile process
  profiles"** નામનું table છે — બધા profiles (RELEASED + SUPERSEDED બંને state) list થાય, Profile
  number/Version/State/Area classification/Validation reference સાથે. **RELEASED master data content
  ક્યારેય edit/delete નથી થતું** (આ app ના બીજા બધા versioned master data — Product Master, Recipe
  Master — ની જેમ જ) — એના બદલે **"Supersede" button** (ફક્ત RELEASED row પર) નવો version (v+1) બનાવે
  છે, જૂનો version `SUPERSEDED` mark થાય (list માં history તરીકે કાયમ રહે, પણ Product Master ના
  dropdown માંથી તરત જતો રહે). Backend: `POST /aseptic/v1/profiles/{id}/supersede` + migration `0085`
  (`supersedes_profile_version_id`). True hard delete જાણી જોઈને નથી બનાવ્યું — client ને પૂછ્યા પછી
  જ (SG-176 માં નોંધેલું).

**Client demo moment (updated):** `injectable_ddcp` profile પસંદ કરો → "Sterile process profile"
dropdown માંથી real profile (`ASP-PROC-001 v1 — ISO_5`) પસંદ કરો → draft બનાવો → succeed. Honest gap
બતાવવા random UUID હવે try જ ના કરી શકાય (dropdown માં typing નથી) — backend API સીધું call કરીને
બતાવી શકાય કે ખોટો UUID હવે **create વખતે જ** `VALIDATION_FAILED` આપે છે, Release સુધી રાહ નથી જોવી
પડતી. Field ખાલી છોડીને flow હજુ પણ demo કરી શકાય: draft બનાવો → Submit → **Release try કરો → block
થાય, ValidationFailedError** → "Check completeness" button (VersionDetailModal) એ જ finding advisory
તરીકે પહેલેથી બતાવે છે ("Issue eligibility" panel).

### 8.4 ✅ FIXED 2026-09-07 — draft બન્યા પછી હવે Edit UI છે

**અગાઉ:** `services/gxp-api/app/modules/product_master/commands.py` નું `update_draft()` (backend
`PUT /products/v1/drafts/{id}`, draft state માં name/profile/sterile-profile/UDI/device-code/
combination-fields/**constituents** બધું બદલી શકે) **frontend માંથી ક્યાંય call જ નહોતું થતું**. **હવે
થાય છે** (code-verified, `frontend/src/app/product-master/page.tsx` — `EditDraftModal` + `api.put()`,
જે `lib/api.ts` ના `api` helper માં પણ નવું ઉમેરવું પડ્યું, કારણ codebase માં આ **પહેલો જ PUT call**
હતો):

- `VersionDetailModal` માં હવે **"Edit"** button છે (ફક્ત `lifecycle_state === "draft"` હોય ત્યારે, જેમ
  Check completeness/Submit — server-side પણ `update_draft()` draft state સિવાય reject કરે છે,
  `ValidationFailedError: "Only a draft can be edited"`).
- Edit modal માં એ જ fields (§8.1) — Business ID/Product code/Version no/Site **fixed** રહે છે
  (`UpdateProductDraftCommand` માં એ fields જ નથી — identity immutable), બાકી બધું (Name, Manufacturing
  profile, Sterile process profile, Device model code, UDI applicable, Combination product fields,
  **Constituents**) edit કરી શકાય.
- **Constituents** = full replace (create ની જેમ જ) — Edit modal ખૂલે ત્યારે existing constituents
  pre-filled દેખાય, "Remove" કરી શકાય, નવા add કરી શકાય.
- Optimistic concurrency: `expected_version` mismatch થાય (કોઈ બીજું edit વચ્ચે થયું હોય) તો
  `StaleVersionError` — બીજા બધા edit actions ની જેમ જ.

**Client demo moment:** draft બનાવો, `injectable_ddcp` profile પસંદ કરો, Sterile process profile
**ખાલી છોડો** → "Check completeness" → finding દેખાય ("sterile_profile_id is required...") → **Edit**
→ Sterile process profile dropdown માંથી `ASP-PROC-001 v1` પસંદ કરો → Save → "Check completeness"
ફરી → finding જતું રહે. પહેલાં આ sequence માટે નવો આખો draft (નવો Version no) બનાવવો પડતો, હવે એ જ
draft માં સુધારો.

Create Draft → (Edit, જરૂર પડે તેટલી વાર) → Submit → **Release** (`admin` — regulated recipe/product
control; Submit unconditional state-move છે, **Release જ** completeness gate ચલાવે છે — §8.3).

### 8.5 Role-wise actions — Product Master (code-verified `scripts/seed.py` + `product_master/{commands,router}.py`)

**2026-09-08 થી author ≠ releaser** — Recipe Master જેવો જ split (Decision 2):

| Action | Permission code | Endpoint | Role(s) allowed | સહી? |
|---|---|---|---|---|
| Create draft | `product.author` | `POST /products/v1/drafts` | **Process Engineer**, Admin | ના |
| Edit draft | `product.author` | `PUT /products/v1/drafts/{id}` | **Process Engineer**, Admin | ના |
| Check completeness (advisory) | `product.author` | `POST /{id}/validate-completeness` | **Process Engineer**, Admin | ના |
| Submit draft | `product.author` | `POST /drafts/{id}/submit` | **Process Engineer**, Admin | ના |
| Get release challenge | `product.release` | `POST /products/v1/{id}/signature-challenges` | **QA Releaser**, Admin | — |
| Release | `product.release` + signature policy | `POST /drafts/{id}/release` | **QA Releaser** (author થી અલગ વ્યક્તિ), Admin | **✅ હા — password** |
| Suspend / Reinstate | `product.suspend` | `POST /{id}/suspend`, `/reinstate` | **Admin only** (હજુ SG-035 નો બાકીનો scope — `SIGNATURE_POLICY_UNRESOLVED` આપે) | ના |
| View (list/detail/constituents) | `product.view` | `GET ...` | Admin, Process Engineer, Supervisor, Operator, QA Reviewer, QA Releaser, QC Reviewer | ના |

**Release signature — QA Releaser, author થી independent (2026-09-08):** `product_version` / `release`
signature policy હવે `signature_required=true`, `required_role = QA Releaser`, `requires_independent_signer =
true` — `release_product_version()` product version ના પોતાના `Created` audit event સામે ચેક કરે
(recipe_version/release / IND-011 / નવો **IND-021** જેવો જ bespoke pattern). Author = releaser હોય તો
`SOD_CONFLICT` (409). Live DB પર `scripts/sync_signature_policies.py` થી applied.

**Client demo moments (real enforced negative-controls):**
1. `admin` (કે `process.engineer`) draft → Submit. પોતે release કરવાનો પ્રયત્ન કરે (`admin` QA Releaser
   role પણ ધરાવે છે) → **`SOD_CONFLICT` (409)** — "author cannot also release".
2. `qa.releaser` password વગર release → **428** (`MISSING_SIGNATURE`).
3. `qa.releaser` (author નથી) → **Release** button → SignatureCeremony → password → **200**, released,
   real `signature_id` + Vault snapshot.
- `process.engineer` → **Release** button **દેખાતું નથી** (`product.release` નથી); force કરો → **403**.

**Standing-role-pair SoD (Decision 1 — Document 107, customer Quality org owns):** platform floor માં
હવે `SOD-021 (Process Engineer, QA Releaser)` છે — **`severity = REPORT_ONLY`** (blocking નથી; person-level
independence IND-011/IND-021 થી પહેલેથી enforced છે). Customer પોતાની SoD matrix માં એને PROHIBITED કરી
શકે — નવો `scripts/sync_sod_rules.py` (`sync_permissions.py` જેવો re-runnable) live DB પર apply કરવા.
REPORT_ONLY રાખવાથી all-roles `admin` break-glass કામ કરતો રહે છે.

**Suspend/Reinstate હજુ unresolved** (SG-035 નો બાકીનો scope) — deliberately extend નથી કર્યું. Full
detail: `18_SPEC_GAPS.md` SG-035.

---

## 9. Phase 5 — Recipe Master (પ્રોસેસ ટેમ્પલેટ / MMR)

**કોણ:** `process.engineer` (`recipe.author` — draft/edit/validate/simulate/submit) → `qa.releaser`
(`recipe.release` — **સહી**, author થી અલગ વ્યક્તિ). **ક્યાં:** `/recipe-master`.
**Backend:** `POST /recipes/v2/drafts` (create), `PUT /recipes/v2/drafts/{id}` (edit), `.../validate`,
`.../simulate`, `.../submit`, `.../signature-challenges` + `.../release`. **List:** `GET
/recipes/v2/families` → `GET /recipes/v2/{recipe_family_id}/versions`. **Doc:** 10 (SPEC-EBMR-002).
*(બધા fields code-verified 2026-09-08 against `frontend/src/app/recipe-master/page.tsx` (`DraftModal`)
અને `services/gxp-api/app/modules/recipe_master/{commands,router,models}.py`; **2026-09-16 update** —
create હવે popup modal નથી, પોતાનું **full page** છે, નીચે §9.1 જુઓ.)*

**કેમ જરૂરી? (સાદી ભાષામાં):** Product Master "શું બનાવવું" કહે છે, Recipe Master **"કેવી રીતે
બનાવવું"** કહે છે — batch execution વખતે operator ને step-by-step બતાવવાનું master ટેમ્પલેટ (જેમ
રસોઈની recipe: ingredients નહીં, પણ "કયા section માં, કયા ક્રમમાં, **કોણે**, શું કરવું"). Recipe **family**
= કાયમી ઓળખ (recipe_code); તેની નીચે એક કરતાં વધુ **version** (v1, v2…) — દરેક version પોતાનું
draft→under_review→released જીવનચક્ર ધરાવે.

### 9.1 "New recipe draft" — top-level fields (frontend ↔ backend, code-verified)

`process.engineer` → `/recipe-master` → **"New draft"** button → **`/recipe-master/new` પર જાય, popup
નહીં** (2026-09-16, project-owner-directed: Sections/Steps/Dependencies graph editor + એના 4 per-step
sub-editor, §9.3.1-9.3.4, modal માં ફિટ થવા માટે બહુ મોટા હતા — `DraftModal` retired, form/logic
`recipe-master/shared.tsx` માં move કર્યું જેથી list page (`page.tsx`) અને નવું create page બંને same
`RecipeGraphEditor` વાપરે, code duplicate ના થાય). Page ના top-level field
(**6 dropdown/required field — 2026-09-08 થી કોઈ free-text/raw-UUID નથી — + 2 optional free-text field,
2026-09-16 code-verified against current `/recipe-master/new`**) બરાબર એ જ રહ્યા છે, ફક્ત container બદલાયું:

| Frontend field | Backend field (`CreateRecipeDraftCommand`) | Type / UI control | Reference / dropdown data | ફરજિયાત? | ઉદાહરણ |
|---|---|---|---|---|---|
| **Product** | `product_business_id` | **`<select>` dropdown** | **`GET /products/v1/business-ids`** — બધા Product Master products (business ID + name), એક જ list જે `/product-master` વાપરે | હા | `MERIDIJECT-PFS — MeridiJect™ Prefilled Syringe` |
| Recipe code | `recipe_code` | free-text `Input` | — (globally unique; એ જ code ફરી વાપરો તો family re-use થાય, નવો નહીં) | હા | `RCP-MJ-PFS-V1` |
| Version no. | `version_no` | number `Input` (min 1) | auto-increment **નથી** — તમે જાતે ટાઈપ કરો; એ જ family+version ફરી → `VALIDATION_FAILED` | હા | `1` |
| **Product version** | `product_version_id` | **dependent `<select>` dropdown** (Product પસંદ કરો પછી enable) | **`GET /products/v1/{business_id}/versions`** — એ product ના બધા versions, `v{n} — {name} ({lifecycle_state})`; **released first**. Non-released પસંદ કરો તો warning hint (batch creation ને released જોઈએ). Backend હવે unknown UUID ને `NOT_FOUND` (404) આપે, પહેલાં opaque 500 હતું | હા | `v1 — MeridiJect PFS (released)` |
| Site | `site_id` | **`<select>` dropdown** | **`GET /sites`** — registered sites. Product version પસંદ કરો એટલે એની `site_id` auto-fill થાય (editable) | હા | `Demo Site 1` (`SITE1`) |
| Manufacturing profile | `manufacturing_profile_code` | **`<select>` dropdown** | Product Master ના જ 5 values (`pharma` / `device` / `injectable_ddcp` / `inhalation_ddcp` / `drug_eluting_device`). Product version પસંદ કરો એટલે એનો profile auto-fill થાય (editable). MeridiJect PFS = `injectable_ddcp` | હા | `injectable_ddcp` |
| Batch size | `batch_size_value` | free-text `Input` | — **✅ 2026-09-16 code-verified: હવે form માં real field છે** (પહેલાં §9.5 "backend-only" કહેતું હતું — તે હવે stale/ખોટું છે). Numeric string, દા.ત. `4000` | ના | `4000` |
| Batch size UOM | `batch_size_uom` | free-text `Input` | — free text, **dropdown/picker નથી** (UOM picker `rules.gxp_uom` સામે ક્યાંય resolve નથી થતું frontend માં) | ના | `EA` |

**Edit** (`EditGraphModal`, `PUT /recipes/v2/drafts/{id}`) ના પણ એ જ 2 batch-size field છે, existing version ના
`batch_size_value`/`batch_size_uom` થી pre-filled.

નીચે 3 repeatable editors: **Sections**, **Steps**, **Dependencies** (§9.2–9.4).

*(Product + Product version પસંદ કરો એટલે Site અને Manufacturing profile એ product version પરથી
auto-fill થાય — બંને પછી પણ editable છે, પણ default consistent રહે.)*

### 9.2 Sections (repeatable — `sections[]` → `SectionInput`)

દરેક section = manufacturing process નો મુખ્ય તબક્કો. ઓછામાં ઓછું 1 section ફરજિયાત.

| Sub-field | Backend | Type | Reference / dropdown | ફરજિયાત? | ઉદાહરણ |
|---|---|---|---|---|---|
| Section code | `stable_section_code` | text | — (version અંદર unique; steps આ code થી section ને link કરે) | હા | `SEC-FILL` |
| Name | `name` | text | — | હા | `Aseptic Fill` |
| Sequence | `sequence` | number | — (sections ને ક્રમમાં બતાવવા) | ના (પણ ભરવો) | `1` |

*(Backend `SectionInput` વધુ optional fields સ્વીકારે — `area_requirement_id`, `parallel_group`,
`expected_duration_minutes` — પણ frontend form માં આ 3 જ છે.)*

### 9.3 Steps (repeatable — `steps[]` → `StepInput`)

દરેક step = section ની અંદરની ચોક્કસ action. ઓછામાં ઓછો 1 step ફરજિયાત.

| Sub-field | Backend | Type / UI control | Reference / dropdown data | ફરજિયાત? | ઉદાહરણ |
|---|---|---|---|---|---|
| Step code | `stable_step_code` | text | — (version અંદર unique; dependencies આ code વાપરે) | હા | `FILL-01` |
| Section code | `section_code` | text | **ઉપરના કોઈ section નો `stable_section_code`** સાથે બરાબર match થવો જોઈએ (ના થાય તો create rejects) | હા | `SEC-FILL` |
| Step type | `step_type` | **`<select>` dropdown** | **16 controlled values** (code `STEP_TYPES`): `instruction`, `data_entry`, `scan`, `weigh`, `equipment_check`, `calculation`, `ipc_qc`, `signature`, `verification`, `timer`, `hold_point`, `material_consume`, `assembly`, `test`, `packaging`, `custom_approved_type` | હા | `weigh` |
| Instruction text | `instruction_text` | **free-text `<textarea>`** (2 rows) | — **✅ 2026-09-16 code-verified: real field, §9.5 નું "backend-only" claim હવે stale છે.** Operator batch execution વખતે આ જ text step Detail modal માં વાંચે (§11.3) — rich-text/markdown નથી, plain text જ | ના | `Balance ને tare કરો, drug substance ne filler hopper માં ધીમે-ધીમે dispense કરો, target weight cross ના થાય એની કાળજી રાખો.` |
| Sequence hint | `sequence_hint` | number | — (readiness/ordering hint) | ના (પણ ભરવો) | `1` |
| Critical step | `is_critical` | **`<select>` Yes/No** | — (critical step ભૂલ = deviation-tracking કડક) | ના (default No) | `Yes` |
| Required role | `required_role_code` | **`<select>` dropdown** | **`GET /roles`** — બધા seeded roles. Demo-relevant: `Operator`, `DDCP Operator`, `QC Reviewer`, `Sanitation Operator`, `Aseptic Operator`. **ખાલી = કોઈ પણ `batch_execution.execute` holder** | ના | `Operator` |
| Required qualification code | `required_qualification_code` | free-text `Input` **+ `<datalist>` suggestions** (2026-09-16 ઉમેર્યું) | **`GET /training/v1/qualification-codes`** — `qms.qualification_record` (Document 31) માંથી distinct granted code, suggestion list તરીકે. **⚠️ formal FK નથી** — કોઈ qualification-code catalog table જ નથી (SG-086). Typing કોઈ પણ નવો code હજુ સ્વીકારાય | ના | `ASEPTIC_GOWN_CERT_DEMO` |

**🛑 CRITICAL — 2026-09-16 code-verified, પહેલાં આ doc એ "enforce નથી" ખોટું કહ્યું હોત, ખરેખર ઊંધું છે (fields ગોઠવતા ગોઠવતા આ મળ્યું):**
`batch_execution/commands.py::_enforce_step_qualification()` આ field ને batch step **start** વખતે **hard
enforce** કરે છે (`QUALIFICATION_MISSING`/`QUALIFICATION_EXPIRED`, `required_role_code`/SG-178 થી પણ
કડક — **કોઈ override path જ નથી**, Supervisor/Admin પણ bypass ના કરી શકે) — પણ **iam.qualifications**
table સામે ચેક કરે છે, **qms.qualification_record નહીં** (જ્યાં ઉપરનો dropdown સૂચન લાવે છે એ table). Code
grep-verified: **`iam.qualifications` માં ક્યાંય, કોઈ પણ endpoint/script/seed થી, row insert થવાનો રસ્તો જ
નથી** (`session.add(Qualification` — 0 match આખા codebase માં) — matches the same table `material/
commands.py`'s dispensing-qualification ચેક પણ વાપરે છે, જે એ જ કારણથી કાયમ fail થાય. **પરિણામ: કોઈ પણ
recipe step પર `required_qualification_code` set કરો તો — Admin સહિત **કોઈ પણ** user એ step ક્યારેય start
નહીં કરી શકે** (`QUALIFICATION_MISSING`, કાયમ, કોઈ escape hatch નહીં). Demo/testing માટે: **આ field હાલ
ખાલી જ રાખો** જ્યાં સુધી `iam.qualifications` ને populate કરવાનો કોઈ રસ્તો (નવો IAM endpoint, અથવા
SG-086 ના resolution પ્રમાણે `qms.qualification_record` → `iam.qualifications` write-through) ના બને —
§9.7 નું MeridiJect worked example ઈરાદાપૂર્વક કોઈ step પર આ field set નથી કરતું, બરાબર આ કારણથી.

**`required_role_code` નું enforcement (SG-178, §9.6 જુઓ):** ખાલી ના હોય તો — batch issue વખતે એ role
step પર **freeze** થાય, અને batch execution વખતે એ role વગરનો user step start કરે તો
**`STEP_ROLE_MISMATCH` (403)**.

દરેક step ની નીચે 4 વધુ repeatable sub-editor છે — **બધા 2026-09-16 code-verified real UI editor છે**
(§9.3.1–9.3.4). §9.5 માં હજુ genuinely backend-only રહેલા 4 field ની honest list છે.

### 9.3.1 Parameters (`step.parameters[]` → `ParameterInput`) — step પર શું measure/record થાય

| Sub-field | Backend | Type / UI control | Reference / dropdown | ફરજિયાત? | ઉદાહરણ |
|---|---|---|---|---|---|
| Parameter code | `parameter_code` | free-text `Input` | — (batch execution "Record results" આ code થી જ ઓળખે, §11.3) | હા | `FILL_WEIGHT_MG` |
| Data type | `data_type` | free-text `Input` (placeholder સૂચવે: `decimal`/`integer`/`text`/`boolean`) | — **dropdown નથી**, તમારે placeholder ના suggested string માંથી જ ટાઈપ કરવાનું (typo ચેક નથી) | હા | `decimal` |
| Source | `source_type` | free-text `Input` (placeholder સૂચવે: `manual_entry`/`equipment_reading`/`calculated`/`scan`) | — **dropdown નથી**, same pattern | હા | `manual_entry` |
| UOM | `uom` | free-text `Input` | — **dropdown/UOM picker નથી** (backend server-side `rules_service.resolve_uom` થી resolve કરે, પણ frontend raw string જ મોકલે) | ના | `mg` |
| Target | `target_value` | free-text `Input` | — | ના | `1000` |
| Min | `min_value` | free-text `Input` | — | ના | `950` |
| Max | `max_value` | free-text `Input` | — | ના | `1050` |
| Precision (decimal digits) | `precision_digits` | `Input type="number" min={0}` | — | ના | `1` |
| Validation rule | `rule_id` | **`<select>` dropdown** | **`GET /rules/v1`** — currently-effective released rules (DDCP ના IPC field જેવો જ linked acceptance-rule picker), `rule_id - rule_type v{semantic_version}`. **⚠️ 2026-09-16 live DB status: DB reset (§ Phase 0) પછી 0 released rule છે** — dropdown ખાલી દેખાશે જ્યાં સુધી `/rules` (Document 22, `rules.author`/`.release`) પર જઈને પહેલા rule author+release ના કરો — tolerance value ખરેખર QA/client નિર્ણય છે (§19 ના જ pattern), guess ના કરાય | ના | *(ખાલી — rule ના હોય ત્યાં સુધી)* |
| Rule version pin (rule_id સેટ હોય તો જ દેખાય) | `rule_version` | free-text `Input` | ખાલી = issue વખતની effective released version | ના | `1.0.0` |
| Manual fallback policy (rule_id સેટ હોય તો જ દેખાય) | `manual_fallback_policy` | free-text `Input` | — | ના | `Rule engine ડાઉન હોય તો QC Reviewer manual pass/fail આપે` |
| Required | `required` | checkbox (default checked) | — Complete step માટે server ચેક કરે કે required parameter નો result record થયેલો છે (§11.3 `PARAMETER_REQUIRED`) | — | ✅ checked |

### 9.3.2 Material requirements (`step.material_requirements[]` → `MaterialRequirementInput`) — step પર શું material consume થાય

| Sub-field | Backend | Type / UI control | Reference / dropdown | ફરજિયાત? | ઉદાહરણ |
|---|---|---|---|---|---|
| Material | `material_spec_version_id` | **બે linked `<select>` dropdown** (Business ID → Version) — **Material Specification** picker, **raw `/materials` list નહીં** | **`GET /material-specifications/v1/business-ids`** (Business ID પસંદ કરો) → **`GET /material-specifications/v1/{business_id}/versions`** (એ business ID ના versions, released first). **⚠️ 2026-09-16 live DB status: DB reset પછી 0 material spec version છે** — બંને dropdown ખાલી દેખાશે જ્યાં સુધી `/material-specifications` પર જઈને પહેલા spec author+release ના કરો | હા | `MJ-DRUGSUB-01 v1 (released)` |
| Target qty | `target_value` | free-text `Input` | — | ના | `1.05` |
| Min qty | `min_value` | free-text `Input` | — | ના | `1.00` |
| Max qty | `max_value` | free-text `Input` | — | ના | `1.10` |
| UOM | `uom` | free-text `Input` | — dropdown નથી (parameter UOM જેવો જ pattern) | ના | `mL` |
| Substitution allowed | `substitution_allowed` | checkbox (default unchecked) | checked કરો તો નીચે "Alternative material" dropdown pair દેખાય | — | ☐ unchecked |
| Alternative material (substitution_allowed checked હોય તો જ) | `alternative_material_spec_version_id` | બીજી Material Spec Business ID → Version dropdown pair | same 2 endpoints ઉપર | ના | — |
| Consume mode | `consume_mode` | free-text `Input` | — dropdown નથી | ના | `full_container` |
| Genealogy required | `genealogy_required` | checkbox (default **checked**) | — batch genealogy/traceability (Document 03 MAT-021) આ material lot ને track કરશે કે નહીં | — | ✅ checked |

### 9.3.3 Equipment requirements (`step.equipment_requirements[]` → `EquipmentRequirementInput`) — step પર શું equipment class જોઈએ

**નોંધ:** આ ફક્ત equipment **class** (string) declare કરે છે — ચોક્કસ equipment asset/serial picker નથી
(equipment master પર કોઈ link જ નથી, code-verified).

| Sub-field | Backend | Type / UI control | Reference / dropdown | ફરજિયાત? | ઉદાહરણ |
|---|---|---|---|---|---|
| Equipment class | `equipment_class` | free-text `Input` | — dropdown/equipment-asset picker નથી; તમે class-name string ટાઈપ કરો | હા | `FILLING_LINE` |
| Any unit of this class is fine | `exact_equipment_optional` | checkbox (default **checked**) | — | — | ✅ checked |
| Requires current calibration | `require_current_calibration` | checkbox (default unchecked) | — | — | ☐ unchecked |
| Requires current qualification | `require_current_qualification` | checkbox (default unchecked) | — | — | ☐ unchecked |
| Requires current cleaning | `require_current_cleaning` | checkbox (default unchecked) | — | — | ☐ unchecked |

### 9.3.4 Evidence requirements (`step.evidence_requirements[]` → `EvidenceRequirementInput`) — step પર શું evidence ફરજિયાત

| Sub-field | Backend | Type / UI control | Reference / dropdown | ફરજિયાત? | ઉદાહરણ |
|---|---|---|---|---|---|
| Evidence type | `evidence_type` | free-text `Input` (placeholder સૂચવે: photo/scan/printout) | — dropdown નથી | હા | `photo` |
| Required count | `required_count` | `Input type="number" min={1}` (default `1`) | — | ના (default 1) | `1` |
| Allowed MIME types | `allowed_mime_types` | free-text `Input` | — dropdown નથી | ના | `image/jpeg,image/png` |
| Retention class | `retention_class` | free-text `Input` | — dropdown નથી | ના | `GXP_PERMANENT` |

**Batch execution (§11.3) આ requirement list step Detail modal માં બતાવે છે (read-only)** — actual
photo/file **upload કરવાની UI/API હજુ નથી** (SG-047, §11.3 ના known-gaps table જુઓ). એટલે આ editor થી
declare કરેલી requirement, batch execution વખતે ફક્ત "શું ફરજિયાત છે" તરીકે વંચાય, enforce નથી થતી.

### 9.4 Dependencies (repeatable — `dependencies[]` → `DependencyInput`)

"કયો step પૂરો થાય પછી જ કયો શરૂ થઈ શકે" — directed acyclic graph (cycle હોય તો release blocks).

| Sub-field | Backend | Type / UI control | Reference / dropdown | ફરજિયાત? | ઉદાહરણ |
|---|---|---|---|---|---|
| Predecessor step code | `predecessor_step_code` | text | ઉપરના steps માંનો કોઈ `stable_step_code` | હા | `FILL-01` |
| Successor step code | `successor_step_code` | text | ઉપરના steps માંનો કોઈ `stable_step_code` | હા | `FILL-IPC-01` |
| Condition rule (optional) | `condition_rule_id` | **`<select>` dropdown** (2026-09-08 થી form માં) | **`GET /rules/v1`** — currently-effective released rules (Document 08); `rule_id — rule_type v{semantic_version}`. Set કરો તો successor ત્યારે જ ready થાય જ્યારે એ rule true evaluate થાય. `validate_completeness` release વખતે ચેક કરે કે rule ને effective released version છે | ના | `yield_percent — CALCULATION v1.0.0` |
| Rule version pin (optional) | `condition_rule_version` | text | ખાલી = issue વખતની effective released version | ના | `1.0.0` |

*(Detail modal પણ હવે **Dependencies** table બતાવે — predecessor → successor + condition rule.)*

### 9.5 Backend-only fields (form માં નથી — honest, 2026-09-16 re-verified)

**મહત્વનું update (2026-09-16):** આ list પહેલાં `batch_size_value`/`batch_size_uom`, per-step `parameters[]`
અને per-step `evidence_requirements[]` ને પણ "backend-only" ગણાવતી હતી — એ **stale/ખોટું** હતું.
`frontend/src/app/recipe-master/page.tsx` ના direct code-read (2026-09-16) એ પુષ્ટિ કરી કે batch size
(§9.1), parameters (§9.3.1), material requirements (§9.3.2), equipment requirements (§9.3.3), evidence
requirements (§9.3.4), અને instruction text (§9.3) — **બધા real, code-verified UI editor** ધરાવે છે. નીચેની
list હવે ફક્ત genuinely બાકી રહેલા fields ની છે:

| Field | ક્યાં accept થાય | નોંધ |
|---|---|---|
| `qualification_policy_id` (per step) | `StepInput` | step-level qualification-policy FK override — form માં કોઈ field/dropdown નથી (grep: 0 match), `required_qualification_code` (§9.3, plain string) થી અલગ | API થી જ |
| `signature_policy_id` (per step) | `StepInput` | step-level signature-policy FK override — form માં કોઈ field નથી | API થી જ |
| `exception_policy_id` (per step) | `StepInput` | step-level exception-policy FK override — form માં કોઈ field નથી | API થી જ |
| `area_requirement_id` (per section) | `SectionInput` | section ને ચોક્કસ area FK સાથે bind કરવાનો field — form માં `parallel_group`/`expected_duration_minutes` (§9.2) છે પણ આ નથી | API થી જ |

આ 4 field ને UI editor આપવો પોતે એક design decision છે (policy-picker source, area-picker source —
guess ના કરાય); હાલ પૂરતું open item, નવો SPEC_GAP જરૂર જણાય તો raise કરવો.

### 9.6 Reference-table dropdowns — સારાંશ

**10 reference field real dropdown છે** (2026-09-08 થી top-level 8; 2026-09-16 code-verified 2 વધુ
per-step sub-editor picker મળ્યા — parameter acceptance rule, material spec version):

| Field | Dropdown endpoint / source |
|---|---|
| Product | `GET /products/v1/business-ids` |
| Product version | `GET /products/v1/{business_id}/versions` (Product પસંદ કરો પછી; released first) |
| Site | `GET /sites` (product version પરથી auto-fill) |
| Manufacturing profile | hardcoded 5 values (product version પરથી auto-fill) |
| Step type | hardcoded 16-value list (code `STEP_TYPES`) |
| Required role | `GET /roles` |
| Critical step | Yes/No |
| Dependency condition rule | `GET /rules/v1` — effective released rules (નવો endpoint, `rules.evaluate`-gated) |
| Parameter validation/acceptance rule (§9.3.1) | `GET /rules/v1` — **dependency-condition rule dropdown જ list reuse કરે છે** (same `ruleOptions`, same endpoint, બે જુદા fields માટે) |
| Material requirement → Material (§9.3.2) | `GET /material-specifications/v1/business-ids` → `GET /material-specifications/v1/{business_id}/versions` — 2-step cascading picker, **raw `/materials` list નહીં, Material Specification master** |

**UOM ક્યાંય dropdown નથી** (parameter, material, batch-size — ત્રણેય જગ્યાએ free-text `Input`) — આ 1
consistent gap, `rules.gxp_uom` picker ક્યાંય frontend માં wire નથી થયેલો.

### 9.7 પૂરું worked example — MeridiJect PFS recipe (`RCP-MJ-PFS-V1`)

**Top-level:**

| Field | Value (dropdown માંથી પસંદ) |
|---|---|
| Product | `MERIDIJECT-PFS — MeridiJect™ Prefilled Syringe` |
| Recipe code | `RCP-MJ-PFS-V1` (type કરો) |
| Version no. | `1` |
| Product version | `v1 — MeridiJect PFS (released)` |
| Site | `Demo Site 1` (`SITE1`) — auto-filled |
| Manufacturing profile | `injectable_ddcp` — auto-filled from the product version |

**Sections (4):**

| Section code | Name | Sequence |
|---|---|---|
| `SEC-DISP` | Dispensing & Line Setup | `1` |
| `SEC-FILL` | Aseptic Fill | `2` |
| `SEC-ASSY` | Device Assembly | `3` |
| `SEC-TEST` | In-Process & Functional Testing | `4` |

**Steps (9) — `Required role` column જ SG-178 enforcement drive કરે છે:**

| Step code | Section code | Step type | Seq | Critical | Required role | મતલબ (demo) |
|---|---|---|---|---|---|---|
| `LC-01` | `SEC-DISP` | `equipment_check` | `1` | `Yes` | `Sanitation Operator` | Line clearance confirm |
| `DISP-01` | `SEC-DISP` | `weigh` | `2` | `Yes` | `Operator` | Bulk drug dispense to filler |
| `FILL-01` | `SEC-FILL` | `custom_approved_type` | `3` | `Yes` | `Operator` | Aseptic fill run (1.0 mL/unit) |
| `FILL-IPC-01` | `SEC-FILL` | `ipc_qc` | `4` | `Yes` | `QC Reviewer` | In-process fill-weight check |
| `ASSY-01` | `SEC-ASSY` | `assembly` | `5` | `Yes` | `DDCP Operator` | Needle + safety-shield staking |
| `ASSY-VER-01` | `SEC-ASSY` | `verification` | `6` | `Yes` | `DDCP Operator` | Independent assembly verify (IND-001 — Phase 8) |
| `TEST-CCI-01` | `SEC-TEST` | `test` | `7` | `Yes` | `QC Reviewer` | Container-closure integrity test |
| `TEST-VIS-01` | `SEC-TEST` | `test` | `8` | `No` | `Operator` | Visual inspection |
| `HOLD-QA-01` | `SEC-TEST` | `hold_point` | `9` | `Yes` | *(ખાલી)* | QA review hold before release (any) |

**Dependencies (8) — linear chain:**

| Predecessor | Successor |
|---|---|
| `LC-01` | `DISP-01` |
| `DISP-01` | `FILL-01` |
| `FILL-01` | `FILL-IPC-01` |
| `FILL-IPC-01` | `ASSY-01` |
| `ASSY-01` | `ASSY-VER-01` |
| `ASSY-VER-01` | `TEST-CCI-01` |
| `TEST-CCI-01` | `TEST-VIS-01` |
| `TEST-VIS-01` | `HOLD-QA-01` |

**Parameters / Material / Equipment / Evidence — 3 key step માટે (§9.3.1–9.3.4, 2026-09-16 ઉમેર્યું):**

**⚠️ પ્રામાણિકતા:** `rule_id` (§9.3.1) અને Material Specification (§9.3.2) ના dropdown 2026-09-16 એ live DB
માં **ખાલી** છે (DB reset પછી કોઈ released rule/material spec version નથી, §19/§21 જુઓ). નીચેની table
માં એ 2 field ને લગતાં columns **ખાલી** રાખ્યા છે — `/rules` અને `/material-specifications` પર પહેલા
master data author+release કરવું એ પોતે એક જુદો client/QA નિર્ણય છે (tolerance value, spec limit —
guess ના કરાય). બાકીના (target/min/max/uom/equipment class/evidence type) manual-entry fields છે,
directly ભરી શકાય.

*`DISP-01` (weigh — bulk drug substance dispense):*

| Sub-editor | Field → Value |
|---|---|
| Parameter | `DISP_WEIGHT_KG` · data type `decimal` · source `manual_entry` · UOM `kg` · target `12.500` · min `12.375` · max `12.625` · precision `3` · rule *(ખાલી)* · required ✅ |
| Material requirement | Material *(ખાલી — spec author કરવો પડશે)* · target `12.5` · UOM `kg` · substitution ☐ · consume mode `full_container` · genealogy ✅ |
| Equipment requirement | class `DISPENSING_BOOTH` · any-unit ✅ · calibration ✅ required · qualification ☐ · cleaning ✅ required |

*`FILL-01` (custom_approved_type — aseptic fill run):*

| Sub-editor | Field → Value |
|---|---|
| Parameter | `FILL_WEIGHT_MG` · data type `decimal` · source `equipment_reading` · UOM `mg` · target `1000` · min `950` · max `1050` · precision `1` · rule *(ખાલી)* · required ✅ |
| Material requirement | Material *(ખાલી)* — primary container (syringe barrel + stopper) · target `1` · UOM `EA` · substitution ☐ · genealogy ✅ |
| Equipment requirement | class `FILLING_LINE` · any-unit ✅ · calibration ✅ required · qualification ✅ required · cleaning ✅ required |

*`FILL-IPC-01` (ipc_qc — in-process fill-weight check):*

| Sub-editor | Field → Value |
|---|---|
| Parameter | `IPC_FILL_WEIGHT_MG` · data type `decimal` · source `manual_entry` · UOM `mg` · target `1000` · min `950` · max `1050` · precision `1` · rule *(ખાલી)* · required ✅ |
| Evidence requirement | type `photo` · required count `1` · MIME `image/jpeg,image/png` · retention `GXP_PERMANENT` (IPC reading નું balance-display photo) |

**API એ જે body receive કરે (create draft):**

```jsonc
POST /recipes/v2/drafts
{
  "idempotency_key": "<uuid>",
  "product_business_id": "MERIDIJECT-PFS",
  "recipe_code": "RCP-MJ-PFS-V1",
  "version_no": 1,
  "product_version_id": "<released MeridiJect PFS v1 UUID>",
  "site_id": "d8a7b934-a315-462d-94ba-449b44dfce41",   // SITE1
  "manufacturing_profile_code": "injectable_ddcp",
  "sections": [
    {"stable_section_code": "SEC-DISP", "name": "Dispensing & Line Setup", "sequence": 1},
    {"stable_section_code": "SEC-FILL", "name": "Aseptic Fill", "sequence": 2},
    {"stable_section_code": "SEC-ASSY", "name": "Device Assembly", "sequence": 3},
    {"stable_section_code": "SEC-TEST", "name": "In-Process & Functional Testing", "sequence": 4}
  ],
  "steps": [
    {"stable_step_code": "LC-01",       "section_code": "SEC-DISP", "step_type": "equipment_check",      "sequence_hint": 1, "is_critical": true,  "required_role_code": "Sanitation Operator"},
    {"stable_step_code": "DISP-01",     "section_code": "SEC-DISP", "step_type": "weigh",                "sequence_hint": 2, "is_critical": true,  "required_role_code": "Operator",
      "instruction_text": "Balance ne tare karo, drug substance ne filler hopper ma dhime-dhime dispense karo.",
      "parameters": [{"parameter_code": "DISP_WEIGHT_KG", "data_type": "decimal", "source_type": "manual_entry", "uom": "kg", "target_value": "12.500", "min_value": "12.375", "max_value": "12.625", "precision_digits": 3, "required": true}],
      "equipment_requirements": [{"equipment_class": "DISPENSING_BOOTH", "exact_equipment_optional": true, "require_current_calibration": true, "require_current_qualification": false, "require_current_cleaning": true}]},
    {"stable_step_code": "FILL-01",     "section_code": "SEC-FILL", "step_type": "custom_approved_type", "sequence_hint": 3, "is_critical": true,  "required_role_code": "Operator",
      "parameters": [{"parameter_code": "FILL_WEIGHT_MG", "data_type": "decimal", "source_type": "equipment_reading", "uom": "mg", "target_value": "1000", "min_value": "950", "max_value": "1050", "precision_digits": 1, "required": true}],
      "equipment_requirements": [{"equipment_class": "FILLING_LINE", "exact_equipment_optional": true, "require_current_calibration": true, "require_current_qualification": true, "require_current_cleaning": true}]},
    {"stable_step_code": "FILL-IPC-01", "section_code": "SEC-FILL", "step_type": "ipc_qc",              "sequence_hint": 4, "is_critical": true,  "required_role_code": "QC Reviewer",
      "parameters": [{"parameter_code": "IPC_FILL_WEIGHT_MG", "data_type": "decimal", "source_type": "manual_entry", "uom": "mg", "target_value": "1000", "min_value": "950", "max_value": "1050", "precision_digits": 1, "required": true}],
      "evidence_requirements": [{"evidence_type": "photo", "required_count": 1, "allowed_mime_types": "image/jpeg,image/png", "retention_class": "GXP_PERMANENT"}]},
    {"stable_step_code": "ASSY-01",     "section_code": "SEC-ASSY", "step_type": "assembly",            "sequence_hint": 5, "is_critical": true,  "required_role_code": "DDCP Operator"},
    {"stable_step_code": "ASSY-VER-01", "section_code": "SEC-ASSY", "step_type": "verification",        "sequence_hint": 6, "is_critical": true,  "required_role_code": "DDCP Operator"},
    {"stable_step_code": "TEST-CCI-01", "section_code": "SEC-TEST", "step_type": "test",                "sequence_hint": 7, "is_critical": true,  "required_role_code": "QC Reviewer"},
    {"stable_step_code": "TEST-VIS-01", "section_code": "SEC-TEST", "step_type": "test",                "sequence_hint": 8, "is_critical": false, "required_role_code": "Operator"},
    {"stable_step_code": "HOLD-QA-01",  "section_code": "SEC-TEST", "step_type": "hold_point",          "sequence_hint": 9, "is_critical": true}
  ],
  "dependencies": [
    {"predecessor_step_code": "LC-01",       "successor_step_code": "DISP-01"},
    {"predecessor_step_code": "DISP-01",     "successor_step_code": "FILL-01"},
    {"predecessor_step_code": "FILL-01",     "successor_step_code": "FILL-IPC-01"},
    {"predecessor_step_code": "FILL-IPC-01", "successor_step_code": "ASSY-01"},
    {"predecessor_step_code": "ASSY-01",     "successor_step_code": "ASSY-VER-01"},
    {"predecessor_step_code": "ASSY-VER-01", "successor_step_code": "TEST-CCI-01"},
    {"predecessor_step_code": "TEST-CCI-01", "successor_step_code": "TEST-VIS-01"},
    {"predecessor_step_code": "TEST-VIS-01", "successor_step_code": "HOLD-QA-01"}
  ]
}
```

### 9.8 Lifecycle & actions

`draft` → (Edit જરૂર પડે તેટલી વાર) → **Submit** (`under_review`) → **Release** (`released`, **સહી**).
Released પછી: `suspended` / `obsolete` / `superseded` (content ફરી edit ના થાય — નવો version).

| Action | મતલબ |
|---|---|
| **Validate** | schema/logic ચેક — બધા step type valid, section codes match, graph માં cycle નથી, referenced rules released છે |
| **Simulate** | dry-run — batch execute કર્યા વગર ચેક કે recipe logically ચાલશે; findings list આપે (`complete: true/false`) |
| **Compare** | બે version વચ્ચેનો semantic diff (added/removed/changed sections & steps) |
| **Issue eligibility** | આ version થી batch issue થઈ શકે કે નહીં (`lifecycle_state == released` + કોઈ completeness finding નહીં) |
| **Submit for review** | `draft → under_review` (unconditional state move) |
| **Release** | completeness gate + **Part 11 signature ceremony** (§9.10) → `under_review → released`; Vault snapshot + `version_hash` બને |

### 9.9 Role-wise actions (code-verified `recipe_master/router.py` + `scripts/seed.py`)

| Action | Endpoint | Permission code | Role(s) allowed | સહી? |
|---|---|---|---|---|
| Create draft | `POST /recipes/v2/drafts` | `recipe.author` | **Process Engineer**, Admin | ના |
| Edit draft | `PUT /recipes/v2/drafts/{id}` | `recipe.author` | **Process Engineer**, Admin | ના |
| Validate | `POST .../validate` | `recipe.author` | **Process Engineer**, Admin | ના |
| Simulate | `POST .../simulate` | `recipe.author` | **Process Engineer**, Admin | ના |
| Submit | `POST .../submit` | `recipe.author` | **Process Engineer**, Admin | ના |
| Get release challenge | `POST .../signature-challenges` | `recipe.release` | **QA Releaser**, Admin | — |
| Release | `POST .../release` | `recipe.release` + signature policy | **QA Releaser** (author થી અલગ વ્યક્તિ), Admin | **✅ હા — password** |
| View (list / versions / detail / compare / issue-eligibility) | `GET ...` | `recipe.view` | Admin, Process Engineer, Supervisor, Operator, QA Reviewer, QA Releaser, QC Reviewer | ના |
| **Start a batch step whose recipe declared `required_role_code`** | `POST /batches/v1/{id}/steps/{sid}/start` | `batch_execution.execute` + step's `required_role_code` | એ specific role ધરાવનાર; Supervisor/Admin `override_reason` + `batch_step.role_override` થી | ના (override_reason audit પર) |

### 9.10 Release signature — QA Releaser, author થી independent (2026-09-08)

`recipe_version` / `release` માટે હવે signature policy છે (`scripts/seed.py` `SIGNATURE_POLICY_FLOOR`,
live DB પર `scripts/sync_signature_policies.py` થી applied):

- `signature_required = true`, `meaning = "Released"`
- `required_role = QA Releaser` — signer પાસે **QA Releaser role હોવો જ જોઈએ** (`recipe.release` permission
  કરતાં કડક; Admin live DB પર બધા roles ધરાવે એટલે Admin પણ કરી શકે)
- `requires_independent_signer = true` — signer એ **recipe version નો author ના હોઈ શકે**
  (`release_recipe_version()` recipe ના પોતાના `Created` audit event સામે ચેક કરે — IND-001 / CON-FR-014
  જેવો જ bespoke pattern). Error: `SOD_CONFLICT` (409).

**Flow:** `qa.releaser` → version detail → **Release** button → **SignatureCeremony modal ખૂલે** → what
you're signing summary → **password ફરી type કરો** → `POST .../signature-challenges` (challenge બને) →
`POST .../release` (challenge_id + reauth_password) → succeed, real `signature_id` સાથે, Vault snapshot
freeze.

**Client demo moments:**
1. `process.engineer` (author) જો QA Releaser role પણ ધરાવતો હોય તોય પોતાની recipe release કરવાનો પ્રયત્ન
   કરે → **`SOD_CONFLICT` (409)** — "author ≠ releaser".
2. `qa.releaser` password વગર release → **428** (`MISSING_SIGNATURE`).
3. `qa.releaser` challenge + password સાથે → **200**, `lifecycle_state = released`.

### 9.11 Data-entry walkthrough — કોણ શું કરે (step by step)

| # | User (login) | ક્યાં | Action |
|---|---|---|---|
| 1 | `process.engineer` | `/recipe-master` → "New draft" | §9.7 નું બધું data ભરો → **Create draft** → `draft` |
| 2 | `process.engineer` | version detail → **Validate** | schema/graph clean confirm |
| 3 | `process.engineer` | version detail → **Simulate** | `complete: true` confirm (findings ના હોય) |
| 4 | `process.engineer` | version detail → **Submit for review** | `draft → under_review` |
| 5 | `qa.releaser` (login બદલો) | version detail → **Release** → SignatureCeremony | password ફરી → `under_review → released`, `version_hash` બને |
| 6 | કોઈ પણ (view) | `/recipe-master` list | family row → "Versions" → released v1 દેખાય, Batch (Phase 7) હવે આ recipe વાપરી શકે |

**Negative controls (client ને બતાવો):**
- `operator1` → "New draft" button જ **દેખાતું નથી** (`recipe.author` નથી); force કરો તો `POST /drafts` → **403 `ROLE_MISSING`**.
- `process.engineer` → **Release** button **દેખાતું નથી** (`recipe.release` નથી); force કરો → **403**.
- §9.10 ના SOD_CONFLICT / 428 signature demos.

### 9.12 User creation — `process.engineer`

**✅ 2026-09-08: `process.engineer` / `ChangeMe123!` live DB (`ebmr_new_gxp`) માં બની ગયો છે**
(username `process.engineer`, role `Process Engineer` @ `SITE1`) — હવે સીધો login કરી શકાય, કંઈ કરવાનું
નથી. `scripts/seed.py` ના `DEMO_USERS` માં પણ ઉમેરાયો છે એટલે fresh reseed પણ એને બનાવશે.

બીજા demo users પણ live DB માં પહેલેથી છે: `admin`, `operator1`, `supervisor1`, `qa.reviewer`,
`qa.releaser`, `qc.reviewer`, `ddcp.engineer`, `ddcp.operator`, `ddcp.operator2`, `sanitation.operator`,
equipment/aseptic/EM roles.

નીચે ની 3 રીત ફક્ત **બીજા deployment** પર (કે user delete થઈ ગયો હોય તો) ફરી બનાવવા માટે reference છે:

**રીત A — UI (ભલામણ):** `admin` login → **Admin → Users** (`/admin/users`) → **"New user"**:

| Field | Value |
|---|---|
| Username | `process.engineer` |
| Full name | `Pat ProcessEngineer` |
| Email | `process.engineer@example.com` |
| Password | `ChangeMe123!` |

→ save → **"Assign role"** row: Site = `Demo Site 1`, Role = **`Process Engineer`** → assign. Role તરત
લાગુ (`/auth/me` live) — logout જરૂરી નથી.

**રીત B — SQL fallback** (UI ના ચાલે તો, migrator role થી; password hash એ `ChangeMe123!` નો bcrypt —
નીચેનો hash `scripts/seed.py` નો `DEMO_PASSWORD` hash છે, દરેક seeded demo user એ જ વાપરે):

```sql
-- IDs: SITE1 = d8a7b934-a315-462d-94ba-449b44dfce41
--      Process Engineer role = ea770342-2419-4e76-a615-00455416640d
INSERT INTO iam.users (id, username, email, full_name, password_hash, status)
VALUES (gen_random_uuid(), 'process.engineer', 'process.engineer@example.com',
        'Pat ProcessEngineer',
        (SELECT password_hash FROM iam.users WHERE username = 'operator1'),  -- same ChangeMe123! hash
        'active')
ON CONFLICT (username) DO NOTHING;

INSERT INTO iam.user_site_roles (id, user_id, site_id, role_id, status, effective_from)
SELECT gen_random_uuid(),
       (SELECT id FROM iam.users WHERE username = 'process.engineer'),
       'd8a7b934-a315-462d-94ba-449b44dfce41',
       'ea770342-2419-4e76-a615-00455416640d',
       'active', now()
ON CONFLICT DO NOTHING;
```

*(role_id/site_id આ demo environment ના — બીજા deployment માં `SELECT id FROM iam.roles WHERE name =
'Process Engineer'` અને `iam.sites WHERE code = 'SITE1'` થી resolve કરો.)*

**રીત C — curl** (admin token સાથે, `POST /auth/users` + `POST /users/{id}/roles`): DDCP manual
§2.5 નો જ pattern.

**Verify:** `process.engineer` / `ChangeMe123!` login → `/recipe-master` પર "New draft" button દેખાય;
`/batch-execution` પર batch actions **ના** દેખાય (recipe author ને batch permission નથી).

---

## 10. Phase 6 — DDCP Profile (Drug+Device સ્પેક)

**કોણ:** `ddcp.engineer`. **ક્યાં:** `/ddcp` → "Profile designer" tab. **Backend:**
`/ddcp/v1/prefilled-syringe/profiles` (create + release). **Doc:** 54 (SPEC-DDCP-001).

*(Full verified field-by-field detail: `docs/testing/DDCP_Comprehensive_Test_Manual_Gujarati.md` §4.1 —
અહીં demo-specific data reuse કરેલી છે.)*

### 10.0 `/ddcp` પાનું — 1 જ પાનું, 3 tabs (Phase 6/8/11 ત્રણેય અહીં જ થાય છે)

**અગત્યનું, પહેલાં clear કરવું:** Phase 6 (આ section), Phase 8 (§12) અને Phase 11 (§15) — story માટે
અલગ "phase" તરીકે નંબર આપ્યા છે, પણ **UI માં એ 3 અલગ પાનાં નથી** — બધા **એક જ `/ddcp` પાનાના 3 tabs**
છે (code: `frontend/src/app/ddcp/page.tsx`):

| Tab | કોણ જુએ | આ document માં ક્યાં | Backend |
|---|---|---|---|
| **Profile designer** | `ddcp.engineer`/Admin જ (`ddcp_profile.author`) — બીજા role ને "Profile designer hidden" banner | §10 (અહીં) | `POST .../profiles`, `.../release` |
| **Batch readiness & release** | બધા DDCP role read-only જુએ; Assess/Freeze બટન ફક્ત `ddcp.operator`/Admin ને | §15 (Phase 11) | `GET .../readiness`, `POST .../release-readiness`, `.../evidence-package` |
| **Execution & result records** | ફક્ત `ddcp.operator`/Admin (`ddcp_constituent.*`/`ddcp_fill.*`/`ddcp_device.*`) — બીજા role ને tab જ ના દેખાય | §12 (Phase 8) | Family પ્રમાણે 8-11 જુદા op endpoint (§12.1) |

Tab બદલો તો form data જળવાય રહે (CSS hide/show, remount નહીં) — પણ **ટોચે "Product family" dropdown
બદલો** (નીચે જુઓ) તો ત્રણેય tab નું content remount થાય, જેથી એક family નું data બીજી family માં ક્યારેય
"લીક" ના થાય.

**Client demo tip:** `ddcp.engineer` login → ફક્ત "Profile designer" tab દેખાય ("Execution hidden"
banner). પછી `ddcp.operator` login → "Profile designer" tab જ ના દેખાય ("Profile designer hidden"
banner), "Batch readiness & release" + "Execution & result records" બંને દેખાય. `admin` login → ત્રણેય
tab દેખાય. આ જ RBAC-per-tab literally UI માં demonstrate કરો.

### 10.0.1 ટોચનું "Product family" dropdown — Product Master થી **સાવ અલગ** વસ્તુ

`/ddcp` પાનાની ટોચે એક જ dropdown છે — **"Product family"** — ચાર option: *Prefilled syringe /
injectable* (Doc 54, આ ડેમો), *Autoinjector* (Doc 55), *Inhalation MDI/DPI* (Doc 56), *Coated /
combination device* (Doc 57). **આ Phase 4 નું Product Master (§8) નથી** — બંને એકબીજા સાથે code-level
જોડાયેલા જ નથી:

| | **Product family** (`/ddcp` ટોચનું dropdown) | **Product Master** (`/product-master`, §8) |
|---|---|---|
| શું છે | ડિવાઇસ-કેટેગરી પસંદગી — DDCP module એ 4 જુદા schema (Doc 54-57) માંથી ક્યું વાપરવું, ફક્ત UI selector | ખરેખર commercial પ્રોડક્ટ નો master રેકોર્ડ (MeridiJect™ — name, constituents, regulatory profile, versioned) |
| Database માં | કોઈ પણ table/row નથી — ફક્ત frontend `DDCP_FAMILIES` catalog ના 4 entry માંથી 1 (`catalog.ts`), પસંદગી session-local state | `ProductVersion` row, Business ID + Version, draft→submit→release lifecycle |
| કોણ બનાવે/બદલે | કોઈ નહીં — hardcoded 4 option, કોઈ create/edit UI જ નથી | `process.engineer`/Admin (author), `qa.releaser`/Admin (release — સહી) |
| DDCP Profile સાથે સંબંધ | Profile ક્યાં API prefix (`/ddcp/v1/prefilled-syringe/...` વગેરે) પર જશે એ નક્કી કરે | — |
| Product Master સાથે FK સંબંધ | **✅ FIXED 2026-09-08 (SG-175, migration 0089)** — Profile designer ના create form માં હવે **"Product (Product Master)"** ફરજિયાત field છે (નીચે §10.1) — RELEASED Product Master version પસંદ કરવો જ પડે | — |

**Coincidence — બંને જગ્યાએ સરખા દેખાતા શબ્દો છે, પણ જુદી વસ્તુ:** Product Master ના "Manufacturing
profile" dropdown (§8.1/8.2) માં `injectable_ddcp`/`inhalation_ddcp`/`drug_eluting_device` option છે —
આ નામ DDCP ના 4 family જોડે **મેળ ખાય છે** (ડિઝાઇન intent એ જ છે: MeridiJect ના Product Master draft પર
`injectable_ddcp` પસંદ કરેલું, અને `/ddcp` પર "Prefilled syringe / injectable" family પસંદ કરેલી —
conceptually એ જ વસ્તુ). **2026-09-08 પહેલાં code આ બે ને ક્યાંય જોડતું નહોતું** — હવે **જોડે છે**:
`ddcp.ddcp_profile_version` પર નવો `product_version_id` FK (migration `0089`) — Profile designer ના
create form પર પસંદ કરેલો Product Master version હવે backend માં ચેક થાય છે: (1) એ version ખરેખર
exist કરે છે, (2) એ **RELEASED** છે, (3) એ જ site નું છે, અને — **PFS/Inhalation family માટે જ** (એ 2
family ને જ Product Master ના manufacturing-profile code સાથે unambiguous 1:1 મેળ છે) — (4) એ Product
ના manufacturing profile ખરેખર એ જ family સાથે મેળ ખાય છે (`injectable_ddcp`/`inhalation_ddcp`). ખોટો
Product version પસંદ કરો (અથવા DRAFT version) તો create જ `PROFILE_SCHEMA_INVALID`/`VALIDATION_FAILED`
થી block થાય — **હવે trace ના રાખવું, code enforce કરે છે.**

**⚠️ Autoinjector/Coated device — હજુ family-match check નથી (residual gap, SG-175 નો બાકીનો ભાગ):**
Product Master ના 5 manufacturing-profile code માંથી કોઈ પણ "autoinjector" કે "coated device" ને
ચોક્કસ નામ નથી આપતું (`drug_eluting_device` ફક્ત coated device નું 1 example subtype છે, exhaustive
નથી) — એટલે આ 2 family માટે ફક્ત existence/RELEASED/site ચેક થાય છે, family-match નહીં. Guess કરીને આ
mapping ઉમેરવું CLAUDE.md §4 ના નિયમ વિરુદ્ધ જાય — project-owner માટે reserved (§19 #25 જુઓ).

### 10.1 Profile designer — Create fields (8, PFS family)

**કેમ જરૂરી? (સાદી ભાષામાં):** Recipe Master "કેવી રીતે બનાવવું" કહે છે ( સામાન્ય manufacturing steps),
પણ combination product (drug + device) માટે એક **વધારાનું, ટેકનિકલ સ્પેક-લેયર** જોઈએ — DDCP Profile એ
જ છે: "આ ચોક્કસ ડિવાઇસ family (Prefilled Syringe) માટે drug/device constituents ની બરાબર શું સ્થિતિ
હોવી જોઈએ, batch શરૂ કરતાં પહેલાં." Recipe Master Admin બનાવે, DDCP Profile `ddcp.engineer` બનાવે —
અલગ role, અલગ expertise (recipe = general process knowledge; DDCP profile = device/combination-product
regulatory expertise).

| Field | મતલબ | ફરજિયાત? | ડેમો ડેટા |
|---|---|---|---|
| Profile code | Unique code — profile ને ઓળખવાનું | ✅ | `PFS-MERIDIJECT-001` |
| **Product (Product Master)** | **✅ નવું (2026-09-08, SG-175)** — RELEASED Product Master version, 2-step dropdown (Product → એ product ના RELEASED versions) | ✅ | `MERIDIJECT-PFS` → `v1 — MeridiJect™ Prefilled Syringe 40mg` |
| Subtype | Combination product ના ડિવાઇસ નો પ્રકાર (closed dropdown) | — | `Prefilled syringe` (Cartridge/Vial-device co-pack/Other injectable પણ option) |
| Dosage form | દવા કયા ભૌતિક સ્વરૂપમાં છે (free text) | — | `Liquid injectable` |
| Presentation | ગ્રાહકને/nurse ને કેવી રીતે મળે છે (free text) | — | `1 mL prefilled syringe, single-dose` |
| **Product architecture settings** | Sterile-process/fill-control સંબંધિત settings — key/value, **સાવ free-form** (backend JSONB, કોઈ pre-defined key-list validate નથી થતું) | — | `sterileProcess` → `true`, `fillControlRuleId` → `FILL-RULE-PFS-01` |
| **Required controls** | Batch release પહેલાં જોઈતા controls — key/value, **સાવ free-form**, 1 જ recognized key (નીચે નોંધ) | — | `visualInspectionProfile` → `VI-MERIDIJECT-001` |
| Constituent requirements | Batch શરૂ કરતાં પહેલાં દરેક constituent ની expected સ્થિતિ — "શું જોઈએ" ની ચેકલિસ્ટ (repeatable) | ✅ (≥1 row) | Row 1: `Drug`/`bulk_drug`/`Released` (drug lot QC-released જ હોવો જોઈએ); Row 2: `Device`/`needle`/`Ready to use` |

**"Required controls" ની 1 recognized key — honest નોંધ:** `serialization` → `true` row એ UDI/unit
serialization ને applicable તરીકે flag કરે (PFS-FR-019, reporting-only, **ક્યારેય release block નથી
કરતું**). ⚠️ Backend ખરેખર **nested** shape વાંચે છે (`{"serialization": {"required": true}}`) — આ flat
key/value editor એ nested shape produce **કરી શકતું નથી**; top-level `serialization`→`true` store
થાય છે (કારણ backend field genuinely free-form JSONB છે) પણ reporting check એને recognize નહીં કરે.
Non-blocking gap છે — ordinary demo/testing ને અસર નથી કરતું, પણ client ને honestly કહેવું (§19).

**Change reference** (`CHG-MERIDIJECT-2026-001`) = change-control ટ્રેસેબિલિટી — "કયા મંજૂર થયેલા change
request હેઠળ આ profile release કર્યો" (કોઈ પણ regulated spec ફેરફાર change control વગર ના થાય).

Create → **Release** (Expected version=`1`, Change reference=`CHG-MERIDIJECT-2026-001`) → **RELEASED**.
**⚠️ Batch RELEASED profile વગર start ના જ થઈ શકે** — regulated recipe control, client ને emphasize
કરવું.

*(બીજી 3 family — Autoinjector/Inhalation/Coated device — નું field list આ જ shape નું છે, ફક્ત 1-2
typed field બદલાય છે (injector type / fill route+environment profile / coating+sterilization route) —
પૂરું field-by-field: `DDCP_Comprehensive_Test_Manual_Gujarati.md` §4.2-4.4. આ ડેમો PFS ("Prefilled
syringe / injectable" family) પૂરતો સીમિત છે — PFS ને સૌથી વધુ actions છે, §2 માં જ કારણ આપેલું છે.)*

---

## 11. Phase 7 — Batch Create + Issue + Start

**⚠️⚠️ 2026-09-08, SECOND correction, same day — the version just above (still in this section a few
hours ago) is now ALSO wrong, and superseded.** History, for honesty: the *original* text told you to
use `/batch-execution`. That was backwards — DDCP read a different table. This guide was then corrected
to say "use legacy `/batches` instead" — that was *accurate at the time*, but described a real,
project-owner-confirmed architecture defect (SG-149/SG-173), not a design to keep. **The project owner
then directed the actual fix: retarget every dependent module onto `ebmr.gxp_batch`, delete the legacy
demo data, retire the legacy pages.** That migration is done (migration `0090`, code-verified,
live-tested end to end below) — **`/batch-execution` is now correct again, and this time it's because
the backend actually agrees, not because of a doc typo.**

**એટલે: batch ના 2 table હવે નથી — `/batch-execution` → `ebmr.gxp_batch` જ એકમાત્ર authoritative Batch
store છે**, DDCP (11 columns), material (9), equipment (7) અને machine_integration (5) — બધા 32 FK
column હવે `ebmr.gxp_batch`/`ebmr.gxp_batch_step` તરફ point કરે છે (migration `e5f7a9c1b3d6_0090`).
Legacy `/batches`, `/batches/new`, `/batches/[id]`, `/products`, `/recipes`, `/recipes/new` બધા હવે
`/batch-execution`/`/product-master`/`/recipe-master` તરફ **redirect** કરે છે (sidebar nav માંથી પણ કાઢી
દીધા) — legacy `ebmr.batches`/`batch_steps`/`products`/`recipes` tables હવે કાયમ માટે ખાલી (data delete
થયું, demo/test data જ હતું — 2 batch, 6 step, 3 DDCP handoff, 2 product, 2 recipe).

**Live-tested end to end (2026-09-08, real data, not fabricated):** `MJ-PFS-B-2601` batch created via
`POST /batches/v1` against MeridiJect PFS's real RELEASED Product Master version + Recipe Master version
(§8/§9) → issued → started → a real DDCP constituent handoff (`POST
/ddcp/v1/prefilled-syringe/constituent-handoffs`) recorded against it, **no 404** → confirmed in the DB
(`ddcp.constituent_handoff.batch_id` = the `gxp_batch` id) → a real material inventory reservation
(`POST /inventory/v1/reservations`) against the same batch, **also succeeded**. This batch is left in
the live DB — it is the first real row in the now-unified store, not throwaway test data, and matches
this guide's own example batch number.

**કોણ:** `supervisor1` (`batch_execution.create`/`.issue`) → `operator1`/`ddcp.operator` (start/execute,
per recipe step `required_role_code` — SG-178 hard-enforced here). **ક્યાં:** `/batch-execution` — the
one page, for DDCP and for QC/Packaging/Yield/QA-Review/Release v1 alike. **Backend:**
`POST /batches/v1` (create), `/{id}/issue`, `/{id}/start`, `/{id}/steps/{step_id}/start`. **Doc:** 11
(SPEC-EBMR-002/003).

**કેમ જરૂરી? (સાદી ભાષામાં):** અત્યાર સુધીના Phase 1-6 બધા **master data/template** હતા (કાયમી, reusable
— "શું", "કેવી રીતે"). **Batch** = ખરેખર ઉત્પાદન કરવાનું ચોક્કસ "run" — રિયલ વર્લ્ડમાં જેમ recipe book
એક જ હોય પણ દર વખતે રસોઈ કરો એ એક નવો "batch".

### 11.1 "New batch" modal — real fields, real dropdowns (code-verified `frontend/src/app/batch-execution/page.tsx`)

2026-09-08 fix: this modal used to take Product version ID/Recipe version ID as raw UUID text (no
dropdown at all). Now real cascading dropdowns, matching `create_batch()`'s own validation exactly:

| Field | મતલબ | ડ્રોપડાઉન data ક્યાંથી | ઉદાહરણ |
|---|---|---|---|
| Product | dropdown | `GET /products/v1/business-ids` | `MERIDIJECT-PFS — MeridiJect™ Prefilled Syringe 40mg` |
| Product version | dependent dropdown, RELEASED only | `GET /products/v1/{business_id}/versions` | `v1` |
| Recipe | dependent dropdown, families matching the picked product | `GET /recipes/v2/families` | `RCP-MJ-PFS-V1` |
| Recipe version | dependent dropdown, RELEASED + matching the picked product version | `GET /recipes/v2/{family_id}/versions` | `v1` |
| Batch number | આ ચોક્કસ run ની unique ઓળખ | free text | `MJ-PFS-B-2601` |
| Target qty / UOM | આ batch માંથી કેટલા યુનિટ બનાવવાનો ધ્યેય | free text | `4000` / `EA` |
| Production order ref | Internal/ERP order number — traceability | free text, optional | `PO-2026-4471` |

**Create → Issue → Start** ત્રણ અલગ પગલાં કેમ: **Create** = ફક્ત record બને. **Issue** = recipe ના
steps ને actual "to-do list" (execution snapshot + step instances) માં ફેરવે — recipe **frozen copy**
batch સાથે જોડાઈ જાય. **Start** = ખરેખર કામ શરૂ. આ જ `batch_id` હવે DDCP execution (Phase 8) અંદર
foreign-key તરીકે વપરાય છે — **DDCP batch ડેટા generic batch ના એ જ record પર layer થાય છે, હવે ખરેખર
અલગ સિસ્ટમ નથી** (code-verified, not just design intent).

### 11.2 Role-wise actions — Batch Create/Issue/Start + step execution (single path, code-verified)

| Action | Permission code | Role(s) allowed | સહી? |
|---|---|---|---|
| Create batch | `batch_execution.create` | Admin, Supervisor | ના |
| Issue batch | `batch_execution.issue` | Admin, Supervisor | ના |
| Start / Hold / Resume / Abort batch | `batch_execution.execute` | Admin, Supervisor, Operator | ના |
| Start/claim a step | `batch_execution.execute` + recipe નું `required_role_code` (set હોય તો) | એ specific role ધરાવનાર જ; Supervisor/Admin `override_reason` + `batch_step.role_override` થી proceed કરી શકે — **2026-09-08 થી hard-enforced, §9.9/SG-178 જુઓ** | ના (override_reason audit પર) |
| View batch/steps | `batch_execution.view` | Admin, Supervisor, Operator, QA Reviewer, QA Releaser, QC Reviewer | ના |

**ઉદાહરણ (concrete, multi-role chain — end-to-end, live-tested above):**
1. `supervisor1` → `/batch-execution` → `MJ-PFS-B-2601` **Create** કરે (§11 fields — RELEASED Product +
   Recipe version પસંદ કરીને; draft version પર batch ના જ બની શકે).
2. `supervisor1` (અથવા `admin`) → **Issue** કરે — recipe ના steps ની frozen snapshot/to-do list બને
   (real example: `LC-01`/Sanitation Operator → `DISP-01`/Operator → `FILL-01`/Operator → ... — §9.7).
3. **Start** → batch `in_execution`. ready step claim/start કરવા માટે recipe એ declare કરેલો role જ
   જોઈએ — SG-178 hard-enforce કરે: role ના હોય તો `STEP_ROLE_MISMATCH` (403); Supervisor/Admin
   `override_reason` આપીને proceed કરી શકે.
4. હવે DDCP execution (Phase 8) એ જ `batch_id` વાપરીને constituent handoff/fill/assembly/... records
   કરે — **સીધું, કોઈ table mismatch વગર.**
5. Batch production complete થાય પછી **Phase 12 (QA Review + Release, §16)** — `qa.reviewer` review કરે
   (**સહી**) → **જુદો** `qa.releaser` release કરે (**સહી**), independence code-enforced.

**સાર — ક્યાં SoD ખરેખર code-enforced છે, ક્યાં ફક્ત design intent છે (client ને સ્પષ્ટ બતાવો):**

| Phase | બહુવિધ role involved? | Independent review/release enforced? |
|---|---|---|
| Product Master (§8.5) | ✅ **Process Engineer** authors, **QA Releaser/Admin** releases | ✅ **enforce છે** (2026-09-08) — `product.release` PE ને નથી; release signature `requires_independent_signer` (author ≠ releaser → `SOD_CONFLICT`), §8.5 |
| Recipe Master authoring (§9.9) | ✅ **Process Engineer** authors, **QA Releaser/Admin** releases | ✅ **enforce છે** — `recipe.release` PE ને નથી; release signature `requires_independent_signer` (author ≠ releaser, `SOD_CONFLICT`), §9.10. Standing-pair SoD rule (Document 107) બાકી |
| Recipe Master step-level role (`required_role_code`, §9.9) | ✅ per-step declared + **hard-enforced** at step start | ✅ **SG-178 RESOLVED 2026-09-08** (documented override for Supervisor/Admin) |
| Batch Create/Issue (§11.2) | Admin/Supervisor only | ✅ enforce છે — Operator ને create/issue permission જ નથી |
| Batch step execute (§11.2) | recipe નો declared role | ✅ **enforce છે** — `STEP_ROLE_MISMATCH` fail-closed (SG-178) |
| Batch QA Review/Release (Phase 12) | QA Reviewer vs QA Releaser | ✅ enforce છે (2 જુદા role, 2 જુદી સહી, independence ચેક) |
| Deviation (Phase 9) | Operator→Supervisor→QA Reviewer→QA Releaser (4 role) | ✅ enforce છે (state machine દરેક પગલે role ચેક કરે) |
| DDCP Assembly Verify (Phase 8, IND-001) | Same-user block | ✅ enforce છે (independent verification) |
| Inventory Adjustment Approve (§6.4.5, CON-FR-014) | Same-user block | ✅ enforce છે |

આ ટેબલ client demo માટે સૌથી અગત્યનું છે — "SoD ક્યાં ખરેખર code-enforced છે, ક્યાં ફક્ત declared/UI-only
છે" એ તફાવત સ્પષ્ટ પાડે છે. Batch Review/Release, Deviation, DDCP Assembly Verify — બધા code-enforced;
Product/Recipe Master authoring, step-level role હજુ single-role/unenforced છે (ઉપરની ટેબલ મુજબ).

### 11.3 Record Results / Complete Step — સહી સાથે, next step unblock કરે (✅ 2026-09-09 નવું)

**અગત્યનું પહેલાં સમજવું:** આ section §11.2 ના પગલા 3 (ready step claim/start) પછીનું છે — **generic
recipe-step ચેઇન** (`LC-01` → `DISP-01` → ... → `HOLD-QA-01`, §9.7) ને ખરેખર **પૂરી** કરવા વિશે. આ
Phase 8 ની DDCP-specific execution (constituent handoff/fill/assembly, §12) થી **અલગ** સિસ્ટમ છે —
બંને વચ્ચેનો ફરક §12.0 માં વિગતવાર સમજાવ્યો છે, જરૂર વાંચો.

**2026-09-09 પહેલાં આ capability જ નહોતી** — ફક્ત "Start" step બટન હતું, "Complete" કંઈ જ નહોતું. એટલે
batch open કરો એટલે "Execution blockers" banner માં DISP-01/FILL-01/... બધા steps "predecessor not yet
completed" કહીને block દેખાય — આ design પ્રમાણે સાચું જ છે (પહેલા step સિવાય બધા predecessor પર
depend કરે), પણ પહેલો step (દા.ત. `LC-01`) start કર્યા પછી પણ **પૂરો કરવાનો કોઈ રસ્તો જ નહોતો** —
એટલે chain ક્યારેય આગળ ના વધે. હવે real capability બની ગઈ છે.

**કોણ:** `batch_execution.execute` (Admin, Supervisor, Operator) + recipe એ step માટે declare કરેલો
`required_role_code` (set હોય તો — §11.2 ના step-start rule જ, complete માટે પણ એ જ SG-178 ચેક લાગુ
પડે છે). **ક્યાં:** `/batch-execution` → batch ખોલો → step ના row માં "Record results" / "Complete"
બટન. **Backend:** `POST /batches/v1/{batch_id}/steps/{step_id}/signature-challenges`,
`.../results`, `.../complete`. **Doc:** 11 (BAT-FR-006/007/009/010/015/016), signature Document 106
rows 19/21.

**Flow — step "in_progress" થયા પછી (Start ના પછી):**

| # | પગલું | ક્યાં | વિગત |
|---|---|---|---|
| 1 | **Record results** (જો step ને parameter હોય) | "Record results" બટન → parameter ના field (recipe એ §9.3 માં declare કરેલા — data type/UOM/target/min-max hint તરીકે દેખાય) ભરો | દરેક submit = 1 signed action (Document 106 row 21, meaning `Performed`) — password ફરી નાખવો પડે (fresh step-up, 21 CFR Part 11) |
| 2 | **Complete** | "Complete" બટન → password નાખો → sign & complete | Document 106 row 19 (meaning `Performed`) — server ચેક કરે કે step ના બધા **required** parameter માટે result record થયેલો છે કે નહીં |
| 3 | **Auto-unblock** | Complete થયા પછી આપોઆપ | Recipe dependency graph ફરી ગણાય (BAT-FR-006 runtime) — જે next step નો predecessor હવે complete છે, એ step "pending" માંથી "ready" થાય, "Start" બટન દેખાય |

**જો required parameter નું result ના ભર્યું હોય અને Complete દબાવો:**

| Error code | મતલબ | ઠીક કરવાની રીત |
|---|---|---|
| `PARAMETER_REQUIRED` (422) | Recipe એ આ step માટે required parameter declare કર્યો છે (દા.ત. `WEIGHT`) પણ કોઈ result record નથી | પહેલા "Record results" થી એ parameter ભરો, પછી Complete |
| `MISSING_SIGNATURE` (428) | Password વગર/challenge વગર submit કરવાની કોશિશ | Password ફરી નાખો — session/login એ સહી નથી (AG-07) |
| `STEP_ROLE_MISMATCH` (403) | Recipe એ declare કરેલો role actor પાસે નથી | §11.2 જ pattern — Supervisor/Admin override_reason આપીને proceed કરી શકે |

**રિયલ વર્લ્ડ ઉદાહરણ:** `DISP-01` (weigh) step — operator balance પર actual weight વાંચે (દા.ત. `12.5
kg`), "Record results" માં `WEIGHT` field ભરે → sign (password) → પછી "Complete" → sign ફરી → હવે
`FILL-01` step "ready" થાય. આ બે અલગ signed action છે (reading capture ≠ step completion) — બંને
Document 106 પ્રમાણે.

**પૂરેપૂરો data-entry chain — MeridiJect PFS batch (§9.7 ના recipe parameters વાપરીને, 2026-09-16 ઉમેર્યું):**

`MJ-PFS-B-2601` batch માટે, જ્યારે §9.7 ના `DISP-01`/`FILL-01`/`FILL-IPC-01` steps sequentially ready
થાય, દરેક પર "Record results" માં આ ચોક્કસ ડેટા ભરો (parameter code recipe એ જ declare કરેલો, §9.3.1
પ્રમાણે — random field name નહીં):

| Step | Parameter code (recipe-declared) | Record results માં ભરવાનું value | Target/Min/Max (Detail modal માં દેખાય, hint તરીકે) | Result |
|---|---|---|---|---|
| `DISP-01` | `DISP_WEIGHT_KG` | `12.510` | `12.500` / `12.375` / `12.625` | ✅ within range → Complete OK |
| `FILL-01` | `FILL_WEIGHT_MG` | `1002` | `1000` / `950` / `1050` | ✅ within range → Complete OK |
| `FILL-IPC-01` | `IPC_FILL_WEIGHT_MG` | `998` | `1000` / `950` / `1050` | ✅ within range → Complete OK |

**નોંધ — min/max ની બહાર value ભરો તો શું (code-verified `commands.py::_step_result_quality_status`):**
Backend **`in_range`/`out_of_range`/`not_evaluated`** compute કરીને `StepResult.quality_status` column માં
store કરે છે, અને `GET .../results` response એ field **પાછું આપે છે** (`router.py` line 157) — પણ
**save/commit ને block નથી કરતું** (docstring: "informational only, never blocks the command"), અને
frontend `StepResultRow` type એ field **read જ નથી કરતું/UI માં ક્યાંય show નથી થતું** (grep-verified 0
match). એટલે: `FILL-01` પર ઈરાદાપૂર્વક `1200` (max 1050 થી ઉપર) ભરો → save થઈ જશે, `Complete` પણ થઈ જશે,
UI માં કોઈ visible warning નહીં — પણ API response/DB row માં `quality_status = "out_of_range"` ખરેખર
હાજર છે, ફક્ત screen પર દેખાતું નથી. Client demo માટે સારો honest point: "ડેટા capture થાય છે અને flag
થાય છે, પણ UI હજુ એ flag બતાવતું નથી" — deviation trigger manual/§13 થી જ કરવો પડે, automatic નથી.

**દરેક step નું "Detail" બટન ખોલીને ચકાસો** (§11.3 ઉપર) — `instruction_text` (§9.3 એ authored કરેલી),
parameter list target/min/max સાથે, અને `FILL-IPC-01` ના `evidence_requirements` (photo, required count
1) list — બધું recipe એ §9.7 માં declare કરેલા પ્રમાણે જ exactly દેખાવું જોઈએ (round-trip verify).

**✅ 2026-09-09 — "Detail" બટન (દરેક step row પર):** step ની પૂરી વિગત — instruction text, section,
critical flag, predecessor/successor steps, દરેક parameter નો target/range + અત્યાર સુધીનો recorded
result, અને declared evidence requirement (upload હજુ નથી, ફક્ત list) — બધું 1 જ modal માં. Recipe એ
declare કરેલી instruction હવે ક્યાંય UI માં દેખાતી નહોતી — હવે અહીં દેખાય. **Backend:**
`GET /batches/v1/{id}/execution-view` નું `step_detail_by_step_id` field.

**ડેમો માટે શું ખૂટે છે (ગાબડાં — SG-047, SG-048):**

| ખૂટતી વસ્તુ | સ્થિતિ |
|---|---|
| Step-level hold (signed reason સાથે) | **✅ FIXED 2026-09-09** — §11.4 જુઓ |
| Production Complete state | **✅ FIXED 2026-09-09** — §11.5 જુઓ |
| Evidence (photo/file) attach કરવું | **✅ 2026-09-17 CORRECTED — ઉપરનું વાક્ય stale/ખોટું હતું.** UI/API બંને code-verified હાજર છે — `gxp_step_evidence_link` ("Link evidence" બટન, §11.3.1 જુઓ). File પોતે અહીંથી upload નથી થતું (Platform ops → Evidence operations પર પહેલા stage કરવું પડે), પણ link કરવાની capability existing SG-047 scope ની અંદર જ પહેલેથી બની ગયેલી — આ guide માં ફક્ત mention નહોતું. |
| Step correction/rework | હજુ open — Complete થયેલો step પછી ભૂલ સુધારવાનો controlled correction flow નથી (SG-048 #023/#024) |
| Timer/duration enforcement | હજુ open — Hold-time/duration limit આપોઆપ ચેક નથી થતું (SG-048 #018, Temporal જરૂરી — આ platform માં ક્યાંય integrate નથી) |
| Material/Equipment link at execution time | **✅ 2026-09-16 CORRECTED — ઉપરનું વાક્ય stale/ખોટું હતું.** Recipe step **હવે** material/equipment requirement declare કરી શકે છે — real UI editor છે (§9.3.2/§9.3.3, code-verified 2026-09-16). **ખરો ખૂટતો ભાગ**: batch execution ની side — `/batch-execution` ના step Detail modal (§11.3) `material_requirements`/`equipment_requirements` બતાવતું જ નથી (ફક્ત `instruction_text`/`parameters`/`evidence_requirements` — `execution-view` ના `StepDetail` type માં એ 2 field code-verified ગેરહાજર), અને batch execution પાસે material-lot consumption/reservation અથવા specific-equipment-asset link કરવાની કોઈ UI/API step level પર નથી. SG-048 #012/#013 |

### 11.3.1 Link Evidence / Hand Over — બે વધારાનાં step-level બટન (✅ 2026-09-17 ડોક્યુમેન્ટ થયું)

**અગત્યનું:** આ 2 બટન UI માં પહેલેથી હતાં (SG-047 scope, code-verified) — ફક્ત આ guide માં ક્યાંય લખ્યાં
નહોતાં, એટલે testers ને "આ શું છે?" confusion થતું હતું. §11.3 ના Record results/Complete ની જેમ જ,
આ પણ step "in_progress" હોય ત્યારે row માં દેખાય છે — પણ બંને **optional** છે, દરેક step પર જરૂરી નથી.

**Link evidence** — **કોણ:** `batch_execution.execute` (Operator, Supervisor, Admin — Start/Record
results/Complete જેવો જ permission). **ક્યાં:** step row → "Link evidence" બટન. **Backend:**
`POST /batches/v1/{batch_id}/steps/{step_id}/evidence-links`. **સહી?** ના — unsigned (Document 106 માં
evidence-link માટે કોઈ policy row નથી, એટલે intentionally unsigned રાખ્યું છે, guess નથી કર્યો).

**પહેલા શું કરવું પડે:** આ બટન ફાઈલ upload નથી કરતું — ફક્ત પહેલેથી staged evidence ને step સાથે "link"
કરે છે. ફાઈલ પહેલા **Platform ops → Evidence operations** (sidebar → "Platform ops") પર "Stage an
evidence upload" થી ચડાવવી પડે — ત્યાંથી મળતો Evidence object ID અને SHA-256 hash અહીં પેસ્ટ કરવાના.

| Field (modal માં ક્રમમાં) | મતલબ | જરૂરી? |
|---|---|---|
| Evidence object ID | Platform ops પરથી મળેલો ID | ✅ ફરજિયાત |
| Evidence SHA-256 | એ જ પેજ પરથી મળેલો content hash | ✅ ફરજિયાત |
| Media type | દા.ત. `image/jpeg` | optional |
| Requirement code | Recipe એ §9.3 માં declare કરેલા evidence requirement સાથે match કરવા (દા.ત. `FILL-IPC-01` નો "photo, required count 1") | optional, પણ Complete વખતે count આ code પરથી જ ગણાય |

**ચેતવણી:** Link Evidence modal માં "1 of 2 required" જેવું કોઈ live progress નથી. Recipe એ કેટલા/કયા
type evidence માંગ્યા છે એ જોવા step ના "Detail" બટન (§11.3) ખોલવું પડે — ત્યાં "Evidence requirements"
ટેબલ (type + required count) અલગથી દેખાય. Complete દબાવતા પહેલા ત્યાં ચકાસી લેવું.

**જો required evidence link કર્યા વગર Complete દબાવો:** `VALIDATION_FAILED` (422) — "Required evidence
has not been linked" + missing type ની list. (`PARAMETER_REQUIRED` જેવો ડેડિકેટેડ error code evidence
માટે નથી — generic `ValidationFailedError` વાપર્યો છે.)

**Hand over** — **કોણ:** `batch_execution.execute` (same roles). **ક્યાં:** step row → "Hand over"
બટન. **Backend:** `POST /batches/v1/{batch_id}/steps/{step_id}/handover`. **સહી?** ના — unsigned
(આ action માટે પણ Document 106 માં કોઈ policy row નથી).

**શું કરે:** ફક્ત step નું "assigned to" operator બદલે છે, બીજું કંઈ નહીં — step ની state `in_progress`
જ રહે છે, original start time/audit event યથાવત રહે છે.

| Field | મતલબ | જરૂરી? |
|---|---|---|
| Hand over to | User picker (dropdown) | ✅ ફરજિયાત |
| Reason | Free text, audit trail માં જાય | optional |

**રિયલ વર્લ્ડ ઉદાહરણ:** `operator1` નો shift પૂરો થાય, `FILL-01` step હજુ `in_progress` છે —
supervisor "Hand over" દબાવે, નવો operator પસંદ કરે, reason લખે ("shift change") → save (password નથી
જોઈતો) → step હવે નવા operator ના નામે, કામ ત્યાં જ ચાલુ રહે.

**બંને માટે common rule:** step `in_progress` સિવાય બીજી કોઈ state (pending/complete/on_hold) માં call
કરો તો `INVALID_TRANSITION` (409, `current_state` detail સાથે) આવે.

### 11.4 Step-level Hold / Resume — signed, ફક્ત એ 1 step અટકે (✅ 2026-09-09 નવું)

**અગત્યનું:** આ §11.2 ના આખા batch ના Hold/Resume થી **અલગ** છે — batch hold આખું production અટકાવે,
step hold **ફક્ત એ 1 step** ને અટકાવે, બાકીના parallel steps (જો હોય તો) ચાલુ રહે.

**કોણ:** `batch_execution.execute` + recipe નો declared role. **ક્યાં:** step "in_progress" હોય ત્યારે
"Hold" બટન દેખાય; "on_hold" હોય ત્યારે "Resume" બટન. **Backend:**
`POST /batches/v1/{batch_id}/steps/{step_id}/hold`, `.../resume`. **Doc:** 11 (BAT-FR-020), signature
Document 106 row 14 (hold) / row 17 (resume) ના shape પરથી (step-level માટે કોઈ literal row Document
106 માં નથી — nearest analogous action reuse કર્યો, નવો invent નથી કર્યો).

| પગલું | વિગત |
|---|---|
| **Hold** | Reason **ફરજિયાત** (દા.ત. "balance calibration pending") → sign (password) → step state `on_hold` થાય, reason step row પર જ દેખાય |
| **બ્લોક શું થાય** | `on_hold` step પર Record results / Complete બંને block — બંનેને `in_progress` જ જોઈએ |
| **Resume** | Optional note → sign (`Approved` meaning — QA-authority ભાવ, hold ના `Performed` કરતાં જુદો) → step પાછો `in_progress`, ફરી results/complete થઈ શકે |

**રિયલ વર્લ્ડ ઉદાહરણ:** `FILL-01` ચાલુ છે, filler balance drift થયું લાગે — operator "Hold" દબાવે,
reason લખે, sign કરે. Batch ના બીજા કોઈ step ને અસર નથી. Balance recalibrate થયા પછી Supervisor/QA
"Resume" દબાવે, sign કરે — `FILL-01` ફરી ચાલુ.

### 11.5 Production Complete — બધા step પૂરા થાય પછી batch ને "done" mark કરવું (✅ 2026-09-09 નવું)

**2026-09-09 પહેલાં:** બધા recipe step Complete થાય તો પણ batch કાયમ "in_execution" જ રહેતું — કોઈ
"production complete" state જ નહોતું (BAT-FR-026 gap). હવે real state છે.

**કોણ:** `batch_execution.execute`. **ક્યાં:** batch ના બધા step "Complete" થાય પછી જ "Production
complete" બટન દેખાય (batch action row માં, Hold/Resume/Abort ની બાજુમાં). **Backend:**
`POST /batches/v1/{batch_id}/production-complete` + `.../signature-challenges`. **Doc:** 11
(BAT-FR-026), signature Document 106 row 16 (`Performed`, "Qualified performer for the task").

- **ચેક:** server ફરી verify કરે કે ખરેખર **દરેક** `gxp_batch_step` "complete" છે — ના હોય તો
  `PRODUCTION_NOT_COMPLETE` (422) + કયા step બાકી છે એની list.
- **સ્કોપ (પ્રામાણિકતા):** આ ફક્ત "બધા step complete છે?" ચેક કરે છે — BAT-FR-026 ના yield/
  reconciliation અને બીજા "production blocker" ચેક (Document 17 જોડાણ જરૂરી) હજુ નથી બન્યા. Batch
  `production_complete` થયા પછી પણ ("moment of truth" સુધી) જો કોઈ deviation મળે તો batch ને ફરી
  **Hold** કરી શકાય (§11.2 ના જ Hold બટનથી) — "production_complete" કાયમી-lock નથી.
- **પછી શું:** batch હવે Phase 12 (QA Review + Release, §16) માટે તૈયાર — QA review/release ને
  `production_complete` state ચેક કરવાની જરૂર **નથી** (SG-056 already-open gap — release એ ફક્ત QA
  review completeness + Vault integrity ચેક કરે, batch.state નહીં), પણ client demo માટે "production
  complete → QA review → release" sequence follow કરવો realistic GMP practice બતાવે છે.

---

## 12. Phase 8 — DDCP Batch Execution

### 12.0 મહત્વનું — "Batch Execution" vs "DDCP Execution" vs "DDCP Release-Readiness" vs "Batch Release": 4 જુદી-જુદી વસ્તુઓ (ગૂંચવાવ નહીં) (✅ 2026-09-09)

Client demo માં આ 4 શબ્દ ("batch execution", "DDCP execution", "DDCP release/readiness", "batch
release") વારંવાર ભેગા થઈ જાય છે — પણ કોડમાં એ **4 સાવ અલગ વસ્તુ** છે, અલગ table, અલગ endpoint, અલગ
પાનું:

| # | નામ | ક્યાં (પાનું) | શું track કરે | Endpoint (ઉદાહરણ) | Phase |
|---|---|---|---|---|---|
| 1 | **Batch Execution** (generic recipe steps) | `/batch-execution` | Recipe એ declare કરેલા steps (`LC-01`…`HOLD-QA-01`) ની `gxp_batch_step` state — Start/Record results/Complete | `POST .../steps/{id}/start`, `.../results`, `.../complete` | §11.2, §11.3 |
| 2 | **DDCP Execution** | `/ddcp` → "Execution & result records" tab | Combination-product-ચોક્કસ 11 ops (constituent handoff, fill, assembly-verify, CCI/visual test, …) — 9 જુદા DDCP table | `POST /ddcp/v1/prefilled-syringe/...` | §12 (Phase 8) |
| 3 | **DDCP Release-Readiness** | `/ddcp` → "Batch readiness & release" tab | DDCP-ચોક્કસ 3 checkpoint (drug/device/combined) + evidence freeze — readiness/blocker ચેક + immutable manifest | `GET .../readiness`, `POST .../release-readiness`, `.../evidence-package` | §15 (Phase 11) |
| 4 | **Batch (QA) Release** | `/release` | આખા batch ની અંતિમ regulatory disposition (Release/Hold/Reject) — ખરેખર decide કરે batch use થઈ શકે કે નહીં | `POST /release/v1/scopes/.../evaluate`, `.../release` | §16 (Phase 12) |

**⚠️ સૌથી અગત્યની ચેતવણી — આ 4 એકબીજા સાથે જોડાયેલા નથી (code-verified, SG-180 open, 2026-09-09):**

- **#1 અને #2 એકબીજાને touch જ નથી કરતા.** `/ddcp` પર constituent handoff Accept કરો, fill run
  Complete કરો — એનાથી `/batch-execution` નો matching recipe step (`DISP-01`/`FILL-01`/`ASSY-01`)
  આપોઆપ complete **નથી** થતો. ઊલટું પણ સાચું — `/batch-execution` પર બધા recipe step Complete કરો તો
  પણ `/ddcp` ના DDCP-specific execution records એની અસર **નથી** લેતા. **બંને track સાવ સ્વતંત્ર છે** —
  same `batch_id` પર, પણ બે અલગ progress ગણતરી.
- **#3 (DDCP readiness) પણ #1 ને નથી જોતું** — `/ddcp` નું "Check readiness" ફક્ત DDCP ના પોતાના
  constituent-handoff/QC/line-clearance/equipment status ચેક કરે છે (§15.1 ના 4 blocker), generic
  recipe-step ચેઇન `/batch-execution` નું બિલકુલ નહીં.
- **#4 (ખરેખર Release) સૌથી અગત્યનું — તે #2 અને #3 બેમાંથી એકેય નથી વાંચતું** (code-verified,
  `release/service.py::evaluate_eligibility()`): Release eligibility ફક્ત 2 વસ્તુ ચેક કરે — (a) QA
  review package `REVIEW_COMPLETE` છે કે નહીં (§16), (b) Vault execution-snapshot ની integrity. **DDCP
  evidence freeze (#3, "Freeze evidence package") થયું હોય કે ના હોય, DDCP execution (#2) પૂરું થયું
  હોય કે ના હોય — Release બટન એને ચેક જ નથી કરતું** (SG-056, પહેલેથી open gap). એટલે theoretically
  batch ને Release કરી શકાય જ્યારે DDCP execution અધૂરું હોય — client ને demo માં આ સ્પષ્ટ કહેવું,
  છુપાવવું નહીં.

**Client demo માટે practical સલાહ:** Story-level demo માટે sequence આ જ રાખો (§9.7/§11.2/§12/§15/§16
પ્રમાણે) — Batch Execution ના generic step complete કરો (§11.3) **અને** DDCP execution ops પણ કરો
(§12.1) **અને** DDCP readiness/freeze કરો (§15) **પછી જ** Release (§16) — ભલે backend એ ક્રમ enforce
ના કરે, "real GMP process" તરીકે demo આ sequence બતાવે. Client ને directly કહો: "આ 3 checklists
independent છે, ભવિષ્યમાં એક unified completeness gate બનાવવાનો scope decision બાકી છે (SG-180)."



**કોણ:** `ddcp.operator` (+ `ddcp.operator2` independent verify માટે). **ક્યાં:** `/ddcp` → "Execution &
result records" tab (§10.0 નું tab #3 — Profile designer/Batch readiness ના જ `/ddcp` પાનાં પર). **Doc:**
54. *(Full field tables + બધા negative test case: `DDCP_Comprehensive_Test_Manual_Gujarati.md` §5.1 —
data reuse.)*

**✅ 2026-09-08 — batch picker અહીં Phase 7 ના `/batch-execution` batch જ છે**, and it's the only one:
`ddcp/commands.py` હવે દરેક op માં `session.get(Batch, cmd.batch_id)` `app.modules.batch_execution.
models.Batch` (`ebmr.gxp_batch`) સામે કરે છે (migration `0090`, SG-149/SG-173 RESOLVED — §11 જુઓ, live
end-to-end tested).

**Tab કેવી રીતે કામ કરે:** ટોચે "What are you recording?" dropdown છે — PFS family ના **11 ops**
માંથી 1 પસંદ કરો, નીચે એ op ના fields દેખાય, submit → એ ચોક્કસ endpoint call થાય. નીચેનું 6-પગલાંનું
ટેબલ story-level સારાંશ છે (ordered); 12.1 દરેક op ના real fields + ડેમો data સાથે.

**કેમ 6 અલગ પગલાં? (સાદી ભાષામાં)** — batch "Start" (Phase 7) એટલે ફક્ત run ખૂલી ગયો; ખરેખર combination
product બનવાના 6 ચોક્કસ, ક્રમબદ્ધ પગલાં અહીં થાય છે:

| # | પગલું | મતલબ | ઉદાહરણ |
|---|---|---|---|
| 1 | **Constituent Handoff** | Drug lot અને device lot ને batch માટે ઔપચારિક રીતે "સ્વીકારવું" — ફક્ત QC-released lot જ Accept થઈ શકે (Phase 2 ના QC disposition સાથે સીધો સંબંધ) | DRUG lot `LOT-DRUG-2601` → `Accept`; DEVICE lot `LOT-DEV-2601` → `Accept` |
| 2 | **Fill Operations** | Drug ને syringe માં ભરવાની actual process. **IPC** = In-Process Check — વચ્ચે-વચ્ચે sample લઈ ચેક કરવું કે fill weight/volume બરાબર છે, આખું batch પૂરું થાય ત્યાં સુધી રાહ ના જોવાય | Start → IPC → Complete, Target fill `1.000000 mL` |
| 3 | **Production Counts** | Target સામે ખરેખર કેટલા યુનિટ filled/produced થયા | FILLED `4000 EA` |
| 4 | **Device Assembly** | Syringe પર needle/safety shield લગાડવું — **IND-001**: assemble કરનાર વ્યક્તિ પોતે verify ના કરી શકે, બીજી વ્યક્તિ જ ચેક કરે | `ddcp.operator` records → `ddcp.operator2` independently verifies |
| 5 | **Functional Tests** | **CCI** (Container Closure Integrity) જેવા ટેસ્ટ — syringe leak-proof/sterile-seal બરાબર છે કે નહીં, QC result સાથે લિંક | CCI test link to QC result |
| 6 | **Stability/Retain Samples** | ભવિષ્યમાં ટેસ્ટ કરવા/investigation માટે નમૂના અલગ રાખવા (long-term stability data અથવા future તપાસ માટે) | — |

**Client demo moment:** Assembly step ને `ddcp.operator` (એ જ user) verify કરવાનો પ્રયત્ન કરો — **fail
થશે** (IND-001). પછી `ddcp.operator2` થી verify — succeed. "એક જ વ્યક્તિ પોતાનું કામ ચેક ના કરી શકે"
literally block થાય છે, ફક્ત policy document માં નહીં.

### 12.1 11 ops — real fields + MeridiJect ડેમો data (code-verified `catalog.ts`)

**Op 1 — "Record a constituent handoff" (5 fields):**

| Field | ડેમો data |
|---|---|
| Batch | `MJ-PFS-B-2601` (picker) |
| Constituent type | `Drug` |
| Component role | `bulk_drug` (profile ના constituent requirement સાથે match — §10.1) |
| Source → key/ID | `Material lot ID` → `LOT-DRUG-2601` |
| Additional attributes (kv, free-form) | `coa_reference` → `COA-2026-001` (optional) |

DEVICE constituent માટે એ જ op ફરી: Constituent type `Device`, Component role `needle`, Source lot
`LOT-DEV-2601`.

**Op 2 — "Accept or reject a constituent handoff" (6 fields):**

| Field | ડેમો data |
|---|---|
| Handoff ID | dropdown — Op 1 થી session માં બનેલો handoff, refresh પછી ખાલી થાય તો "Look up existing records for a batch" (§12, ✅ 2026-09-08 fixed — હવે real banner) વાપરીને batch ના real history માંથી ફરી ભરો |
| Expected version | `1` (auto-fill, concurrency ચેક) |
| Decision | `Accept` |
| Rejection reason | ખાલી (Reject વખતે જ ફરજિયાત) |
| Profile (optional check) | **✅ FIXED 2026-09-08 — હવે real dropdown** (Op 3 ના "Released profile" જેવો જ `profileSelect`, પહેલાં free text UUID હતું), RELEASED PFS profile માંથી પસંદ કરો — આપો તો preparation-status/attributes એની requirement સામે પણ ચેક થાય |
| Sterilization/depyrogenation reference | **DRUG handoff માટે ખાલી** (required_state=`Released`, trigger set માં નથી); **DEVICE handoff માટે ફરજિયાત** (નીચે જુઓ) |

**⚠️ 2026-09-16 clarification (code-verified, `ddcp/commands.py` L520-527) — "ક્યારે ફરજિયાત" ને ચોક્કસ
કરેલું, પહેલાં ફક્ત "profile ને જોઈએ ત્યારે" જ લખેલું હતું:** Trigger `required_state ∈ {STERILIZED,
DEPYROGENATED, READY_TO_USE}` — **§10.1 ના Row 2 (Device/needle) નું required_state `Ready to use` જ
છે**, એટલે **આ ચોક્કસ ડેમોમાં DEVICE handoff Accept ને આ field ફરજિયાત છે** (ખાલી છોડો તો
`SterileComponentIneligibleError`, 422). DRUG (Row 1, required_state=`Released`) trigger set માં નથી,
ખાલી છોડવું સાચું જ છે.

**આ reference ક્યાંથી મળે?** આ field માં **sterilization load item ID** જોઈએ — **§7.4 (Phase 3, ✅
2026-09-16 થી આ જ document માં ઉમેર્યું)** પૂરું sequence આપે છે: Equipment qualify+calibrate (§7.2) →
Sterilization cycle profile (workaround) → cycle create→start→data→**review/Accept** (§7.4) → `LOT-DEV-
2601` નો load item **ACCEPTED**, `sterile_status = eligible` થાય. Cycle detail ના "Load items" ટેબલ
માંથી એ item ID copy કરીને **અહીં** પેસ્ટ કરો — DEVICE handoff Accept ત્યારે જ pass થશે. *(વધુ ઊંડું
field/RBAC/state-machine સંદર્ભ, અથવા 4th product family (Autoinjector/Inhalation/Coated) માટે —
`Sterilization_Aseptic_Comprehensive_Test_Manual_Gujarati.md`.)*

**Sequence અગત્યની:** આ Phase 8 ના DEVICE handoff Accept **પહેલાં** sterilization cycle પૂરું (ACCEPTED)
થયેલું હોવું જ જોઈએ — નહીં તો કોઈ valid load item ID જ નહીં હોય. Story-level ક્રમ: Sterilization Phase 1-4
→ પાછા આ DDCP guide ના Phase 8, Op 1 (handoff record) → Op 2 (Accept, sterilization reference સાથે).

DRUG અને DEVICE — બંને handoff ને અલગ-અલગ Accept કરવા (2 વાર આ op).

**✅ SG-179 RESOLVED 2026-09-08 (project-owner-directed, hit live while demoing) — DRUG/BIOLOGIC Accept
પહેલાં **હંમેશા** `BULK_NOT_RELEASED` આપતું, LOT-DRUG-2601 real released હોવા છતાં.** Root cause:
`decide_constituent_handoff()` DRUG/BIOLOGIC માટે ફક્ત એક released **Batch** reference જ ચેક કરતું
(PFS-FR-003 ના literal wording મુજબ) — પણ આ platform માં bulk drug ને internally batch તરીકે
બનાવવાની/release કરવાની કોઈ feature જ નથી (bulk drug અહીં હંમેશા Supplier → Receipt → **Material Lot**
તરીકે જ આવે છે, device component ની જેમ જ). Op 1 નું ડેમો data (Source → Material lot ID) સાચું જ હતું —
backend એ lot_id ને DRUG/BIOLOGIC માટે ક્યારેય ચેક જ નહોતું કરતું. હવે fix: `source_batch_reference` માં
જે key હોય (`batch_id` કે `lot_id`) એ પ્રમાણે ચેક થાય — DRUG/BIOLOGIC માટે lot_id હવે device component
જેવો જ real released-lot ચેક પાસ કરે છે. Full detail: `18_SPEC_GAPS.md` SG-179.

**Op 3 — "Start a fill operation" (10 fields):**

| Field | ડેમો data |
|---|---|
| Batch | `MJ-PFS-B-2601` |
| Released profile | `PFS-MERIDIJECT-001 v1` (§10.1) |
| Equipment area/line | `AREA-GRADE-A` (Phase 3, §7.1 — equipment **area**, asset નહીં) |
| Filler equipment | `LINE-PFS-01` (Phase 3, §7.2 — equipment **asset**) |
| Fill program ID / version | `PROG-FILL-001` / `1` |
| Product contact path (kv, free-form) | `path` → `standard` |
| Target fill quantity / uom | `1.000000` / `mL` |
| Cycle group | `CYCLE-A` |

**Op 4 — "Record a fill in-process check (IPC)" (8 fields):**

| Field | ડેમો data |
|---|---|
| Fill operation ID | dropdown — Op 3 નું result |
| Expected version | `1` |
| Sample ID | `IPC-001` |
| Measured value / uom | `1.020000` / `mL` |
| Method | `Gravimetric` |
| Source | `MANUAL` |
| Acceptance rule | `FILL-WEIGHT-RULE-01` |

Out-of-spec measured value → fill run **hold** થાય (§13, Phase 9 deviation scenario આ જ IPC નો ઉપયોગ
કરે છે).

**Op 5 — "Record an aseptic intervention" (6 fields, optional op — ડેમો story માં skip કરી શકાય):**

| Field | ડેમો data |
|---|---|
| Fill operation ID | dropdown — Op 3 નું result |
| Expected version | current version |
| Intervention type | `Stopper adjustment` |
| Started at / Ended at | timestamp |
| Impacted unit scope (kv, free-form) | `unitRange` → `1001-1050` |
| Aseptic intervention reference | Aseptic module (`/aseptic`) નો intervention ID, જો પહેલેથી નોંધેલો હોય |

**Op 6 — "Complete a fill operation" (5 fields):**

| Field | ડેમો data |
|---|---|
| Fill operation ID | dropdown — Op 3 નું result |
| Expected version | current version |
| Machine count (end) | `4000` |
| Sterile filter use reference | optional |
| Reason / note | optional |

≥1 `FILLED` production count (Op 7) પહેલેથી નોંધાયેલો હોવો જોઈએ, નહીં તો Complete fail થાય.

**Op 7 — "Record a production count" (9 fields):**

| Field | ડેમો data |
|---|---|
| Batch | `MJ-PFS-B-2601` |
| Count type | `FILLED` |
| Source | `MANUAL` |
| Quantity | `4000` |
| Unit of measure | `EA` |
| Device reference | optional |
| Reason code | `ROUTINE` |
| Occurred at | timestamp |
| Source event ID | `EVT-COUNT-2601-01` (machine/edge system retry-safe — એ જ ID ફરી submit થાય તો double-count નહીં) |

**Op 8 — "Record a device assembly step" (8 fields):**

| Field | ડેમો data |
|---|---|
| Batch | `MJ-PFS-B-2601` |
| Assembly step | `Needle install` |
| Component lot (ref) | `LOT-DEV-2601` |
| Unit identifier | `MJ-UNIT-0001` |
| Equipment | `LINE-PFS-01` |
| Process parameters (kv, free-form) | `torque` → `2.5` |
| Result | `Pass` (Fail/Rework પણ option — Rework વખતે નીચેનું field ફરજિયાત) |
| Rework procedure reference | ખાલી (Result=Rework હોય તો ફરજિયાત — PFS-FR-027 rework by default disallowed) |

**Op 9 — "Independently verify an assembly step" (2 fields):**

| Field | ડેમો data |
|---|---|
| Assembly record ID | dropdown — Op 8 નું result (**IND-001: Op 8 કરનાર user થી અલગ user જ verify કરી શકે**) |
| Expected version | current version |

**Op 10 — "Link a device functional test" (7 fields):**

| Field | ડેમો data |
|---|---|
| Batch | `MJ-PFS-B-2601` |
| Test type | `CCI` (Container Closure Integrity) |
| QC result (ref) | QC module નો result ID (`/qc`) |
| Result | `Pass` |
| Sample plan reference | optional |
| Method reference | optional |
| Linked at | timestamp |

**Op 11 — "Record a stability / retain sample reference" (4 fields):**

| Field | ડેમો data |
|---|---|
| Batch | `MJ-PFS-B-2601` |
| Stability/retain plan | `STAB-PLAN-MERIDIJECT-01` |
| Quantity | `12` |
| Occurred at | timestamp |

---

## 13. Phase 9 — Deviation (સમસ્યા આવે ત્યારે)

**Scenario:** Fill operation ના IPC (in-process check) દરમિયાન એક sample નું fill-weight out-of-spec
મળે છે. **ક્યાં:** `/deviations`. **Backend:** `/qms/v1/deviations/*`. **Doc:** 26 (SPEC-QMS-001, DEV-FR
series).

**કેમ જરૂરી? (સાદી ભાષામાં):** Deviation = "કંઈક expected પ્રમાણે ના થયું" નો ઔપચારિક રેકોર્ડ — રિયલ
વર્લ્ડમાં જેમ કોઈ પોલીસ FIR: સમસ્યા થાય એટલે તરત dismiss/ignore ના કરાય, systematic રીતે નોંધવું,
તપાસવું, નિર્ણય લેવો, અને બંધ કરવું પડે — દરેક પગલું કોણે, ક્યારે, શું કર્યું એ કાયમ માટે traceable.

**Lifecycle (state machine, code verified — `OPEN → TRIAGE → CONTAINMENT → INVESTIGATION →
IMPACT_ASSESSMENT → DISPOSITION → CLOSED`):**

**✅ 2026-09-09 — re-verified field-by-field against `frontend/src/app/deviations/{page,[id]/page}.tsx`
and `services/gxp-api/app/modules/qms/commands.py`; every field below is one the UI actually renders and
the backend actually accepts/requires.** Also this same day: "Raise deviation"'s Source type dropdown now
drives a real Source record dropdown instead of a free-text ID box (see note under row 1).

| # | પગલું | મતલબ | કોણ | સહી? | Data |
|---|---|---|---|---|---|
| 1 | **Create** (OPEN) | સમસ્યા નોંધવી — શું થયું, ક્યાં, કેટલી ગંભીર | `operator1` | ના | `deviation_number`=`DEV-2026-0141`; `source_type`=`batch`; `source_id`=batch `MJ-PFS-B-2601` (Source type બદલો એટલે Source record dropdown એ જ type ના real record બતાવે — `batch`→batch list, `qc`→QC sample list, `material`→released material lot list, `equipment`→equipment asset list, `supplier`→supplier list; `environment`/`document`/`system` માટે હજુ કોઈ browsable list નથી, ID જાતે લખવું પડે); `severity`=`Major`; `deviation_type`=`Fill weight out of spec` |
| 2 | **Triage** | કેટલી ઝડપથી તપાસ કરવી નક્કી કરવું | `supervisor1` | ના | `severity`=`Major` (ફરી confirm/બદલી શકાય); `investigation_priority`=`High`; `product_impact`=`"Filled units from this run only, pending investigation"` (ઓપ્શનલ) |
| 3 | **Contain** | તપાસ પૂરી થાય એ પહેલાં **તાત્કાલિક** નુકસાન અટકાવવા શું પગલું લીધું | `supervisor1` | ના | `immediate_correction`=`"Line held, affected units segregated"`; `containment`=`"Filler pump isolated pending investigation"` (બેમાંથી ઓછામાં ઓછું 1 ફરજિયાત — `ContainmentRequiredError`, બંને UI માં ભરી શકાય) |
| 4 | **Investigation** | ખરેખર **મૂળ કારણ** શું હતું. **5-why** = "કેમ?" 5 વાર પૂછીને સપાટી પરના લક્ષણથી અસલી કારણ સુધી પહોંચવાની ટેકનિક | `qa.reviewer` | ના | `investigator_subject_id`=qa.reviewer (dropdown); `due_date`=+10 days (ફરજિયાત, investigation ખોલવા માટે); `root_cause`=`{"method":"5-why","conclusion":"filler pump calibration drift"}` (conclusion ભરો ત્યાં સુધી impact assessment blocked રહે) |
| 5 | **Impact** | આ સમસ્યાએ 6 જુદા area ને કેટલી અસર કરી | `qa.reviewer` | ના | 6 category, **બધા ફરજિયાત ટેક્સ્ટ** (missing હોય તો `ValidationFailedError`): `quality_impact`=`"No other batches affected"`; `patient_user_impact`=`"None — caught before release"`; `released_distributed_product_impact`=`"None — batch not yet released"`; `validation_impact`=`"None"`; `data_integrity_impact`=`"None"`; `regulatory_impact`=`"None — no reportable event"` |
| 6 | **Disposition** | Final નિર્ણય — material/batch નું શું કરવું, અને ભવિષ્યમાં આ ફરી ના થાય એ માટે **CAPA**/change control/training જોઈએ કે નહીં | `qa.releaser` | **✅ હા — password** | `disposition_code`=`REWORK`; `disposition_rationale`=`"Rework after filler pump recalibration"`; `capa_required`=`Yes`; `capa_rationale`=`"Root cause is a recurring wear pattern — CAPA needed"` (ફરજિયાત ટેક્સ્ટ, backend એ `capa_rationale` વગર `ValidationFailedError` આપે — CAPA ના જોઈએ તોય કારણ લખવું પડે); `change_control_required`=`No`; `training_required`=`Yes` → `training_rationale`=`"Filler operators need pump-calibration refresher"` (2026-09-09 UI ઉમેર્યું — checkbox ✅ કરો ત્યારે જ rationale field ખૂલે) |
| 7 | **Close** | લેખિત final conclusion — રેકોર્ડ કાયમ માટે બંધ | `qa.releaser` | **✅ હા — password** | `conclusion`=final written conclusion (ફરજિયાત ટેક્સ્ટ) |

**Client demo moment:** Disposition અને Close — બંને વખતે **password ફરી માંગશે** (`_resolve_signature`
call, code verified) — 2 જુદી જુદી e-signature ceremonies, ભલે actor same person (`qa.releaser`) હોય.
અને Investigation/Impact/Disposition/Close — દરેક પાછલા step પૂરા થયા વગર blocked રહે
(`InvestigationIncompleteError`, `ImpactRequiredError`, `DispositionRequiredError` — code verified).

**✅ 2026-09-09 fixed — UI gap closed:** Disposition modal હવે `change_control_required`/
`change_control_rationale` અને `training_required`/`training_rationale` (Document 26 DEV-FR-014/015) બંને
લે છે — CAPA required ની જેમ જ checkbox + (checked હોય ત્યારે) rationale textarea, અને record ના Facts
panel માં already-existing "Change control"/"Training" pill પર સાચું data દેખાય. Backend command પોતે આ 2
field ને flag+rationale તરીકે જ store કરે છે (SG-060 હજુ ખુલ્લું — link કરવા માટે કોઈ real change-control/
training entity નથી), એ SG-060 નો scope છે, UI gap નહીં.

---

## 14. Phase 10 — Line Clearance

**કોણ:** `sanitation.operator`. **ક્યાં:** `/line-clearance`. **Doc:** 39 (SPEC-EQP-002). Full detail:
`DDCP_Comprehensive_Test_Manual_Gujarati.md` §6.

**કેમ જરૂરી? (સાદી ભાષામાં):** નવું batch શરૂ કરતાં પહેલાં line/room ને ચેક કરવું કે પાછલા batch ની
કોઈ સામગ્રી, label, document કે leftover material રહી નથી ગયું — રિયલ વર્લ્ડ ઉદાહરણ: રસોડામાં નવી વાનગી
બનાવતાં પહેલાં ઓટલો સાફ કરવો, જેથી પાછલી વાનગીનો કોઈ ટુકડો ભળી ના જાય (mix-up/cross-contamination
અટકાવવા). "Start" (unsigned — ચેક શરૂ કરવું) → "Complete" (**સહી-required**, password re-entry —
"line ખરેખર clear છે" એ next batch શરૂ કરવાની પૂર્વશરત છે, એટલે real e-signature). DDCP batch readiness
(Phase 11, §15.1) ને `AREA-GRADE-A` **equipment area** (§7.1 — asset `LINE-PFS-01` નહીં) માટે clear line
જોઈએ.

| Field | Data | ફરજિયાત? |
|---|---|---|
| Equipment area/line | `AREA-GRADE-A` (dropdown, §7.1) | ✅ |
| Previous batch | ખાલી (optional — પાછલો batch, જો હોય તો) | — |
| Next batch | `MJ-PFS-B-2601` (optional — Phase 7 create પછી જ dropdown માં) | — |
| Checklist items | ખાલી (optional — Equipment-type item આપો તો એ asset ની qualification/calibration પણ cross-check થાય) | — |

"Start" → "Complete (sign)" → **Result** `Pass — area is clear` → password → area `AREA-GRADE-A` state
`CLEARED` થાય (§15.1 નો `LINE_NOT_READY` blocker હવે clear).

---

## 15. Phase 11 — Batch Readiness + DDCP Evidence Freeze

**કોણ:** `ddcp.operator`. **ક્યાં:** `/ddcp` → "Batch readiness & release" tab (§10.0 નું tab #2 — read
ફક્ત બધા DDCP role ને, Assess/Freeze બટન `ddcp.operator`/Admin ને જ). **Doc:** 54.

**કેમ જરૂરી? (સાદી ભાષામાં):** Phase 8 માં ખરેખર manufacturing થઈ ગયું, પણ release કરતાં પહેલાં "શું
બધું ખરેખર બરાબર થયું?" એ ઔપચારિક રીતે ફરી-ચેક કરવું પડે — રિયલ વર્લ્ડ ઉદાહરણ: ઘર બંધાઈ ગયા પછી, રહેવા
જતાં પહેલાં inspector આખા ઘરનું final inspection કરે (electricity, water, structure — બધું અલગ-અલગ
ચેક).

### 15.1 "Check readiness" (4 fields)

| Field | ડેમો data |
|---|---|
| Batch | `MJ-PFS-B-2601` |
| Released profile version | `PFS-MERIDIJECT-001 v1` (§10.1) |
| Equipment area/line (optional) | `AREA-GRADE-A` (§7.1, **equipment area** — `LINE-PFS-01` નહીં) — આપો તો line clearance/EM status પણ ચેક થાય |
| Filler equipment (optional) | `LINE-PFS-01` (§7.2, **equipment asset**) — આપો તો એ equipment ની eligibility પણ ચેક થાય |

**4 શક્ય blocker:**

| Blocker | મતલબ | ઠીક કરવાની રીત |
|---|---|---|
| `BULK_NOT_RELEASED` | Drug/biologic constituent handoff હજુ Accept નથી થયો | §12.1 Op 1+2 — DRUG handoff record + Accept |
| `PRIMARY_COMPONENT_NOT_RELEASED` | Device/packaging/label constituent handoff હજુ Accept નથી થયો | §12.1 Op 1+2 — DEVICE handoff record + Accept |
| `LINE_NOT_READY` ("Line clearance NOT_STARTED") | `AREA-GRADE-A` (equipment area) પર line clearance Complete (signed) નથી થયું | §14 (Phase 10) — Start → Complete (સહી) |
| `LINE_NOT_READY` ("Filler equipment not eligible") | `LINE-PFS-01` (equipment asset) qualify/calibrate નથી થયું | §7.2 — Qualify → Calibrate |

Phase 5-10 (§9-14) બધું પૂરું થયું હોય તો બધા 4 blocker clear દેખાય.

### 15.2 "Assess release readiness" — 3 અલગ checkpoints

| Checkpoint | શું ચેક કરે |
|---|---|
| **DRUG_CONSTITUENT** | Drug lot ની constituent-handoff/QC સ્થિતિ |
| **DEVICE_CONSTITUENT** | Device lot ની constituent-handoff/QC સ્થિતિ |
| **COMBINED_PRODUCT** | બંને constituent ભેગા થઈને combination product તરીકે release-eligible છે કે નહીં |

API: `POST .../release-readiness` — click કરો એટલે **3 એ 3 checkpoint નો ઔપચારિક રેકોર્ડ write થાય**
(read-only preview નથી, real assessment event). §18 માં emphasize કરેલું: ક્યાંય એક જ "OK" badge નથી —
drug status ≠ device status ≠ combined status, ત્રણેય અલગ-અલગ દેખાય, જેથી client ને ખબર પડે કે drug
ready પણ device pending હોય તો પણ combined "NOT_READY" જ રહેશે.

### 15.3 "Freeze evidence package" — SHA-256 immutable manifest

API: `POST .../evidence-package` — બધા પુરાવા (constituent handoff/fill/assembly/functional-test/
stability records, signatures) ને એક SHA-256-digested પેકેજમાં lock કરવો — **FROZEN**, immutable
manifest. રિયલ વર્લ્ડ ઉદાહરણ: court case ના બધા પુરાવા sealed envelope માં મૂકવા — sealed થયા પછી કોઈ
કંઈ ઉમેરી/બદલી ના શકે (AG-08/AG-12, tamper-proof). Release પછી ("Phase 12") આ frozen evidence જ કાયમી
પુરાવો ગણાય.

**Client demo moment:** "Freeze evidence package" ફરી click કરો (એ જ batch પર) → block નથી થતું —
**નવો** `manifest_version` બને (v2), જૂનો v1 history માં કાયમ રહે (evidence ક્યારેય overwrite નથી થતું,
ફક્ત superseded — AG-08 જ pattern).

---

## 16. Phase 12 — QA Review + Final Release

**✅ 2026-09-08 — restored to its original, now-correct text.** This section briefly said (earlier the
same day) that DDCP-linked batches must review/release through the legacy `/batches/[id]` page instead
of here — that was true only while `ebmr.batches` and `ebmr.gxp_batch` were still two separate tables
(SG-149/SG-173). That split is resolved (migration `0090`, §11) — every batch, DDCP included, is a
`gxp_batch` now, so `/qa-review` + `/release/v1` is correct for all of them, no exception.

**કોણ:** `qa.reviewer` (review — **સહી**) → `qa.releaser` (release — **સહી**). **ક્યાં:** `/qa-review`,
`/release`. **Backend:** QA review package `/qa-review` endpoints (`qa_review.create`/`.execute`/`.view`
— Doc 14); final decision `/release/v1/scopes/batch/{batch_id}/evaluate` → `/eligibility` →
**`/release`** (`release.evaluate`/`.release`/`.hold`/`.reject`/`.view` — Doc 15).

**કેમ 2 અલગ પગલાં? (સાદી ભાષામાં)** — રિયલ વર્લ્ડ ઉદાહરણ: exam paper ને પહેલાં એક teacher ચેક કરે
(marking/review), પછી બીજી, વધુ સિનિયર વ્યક્તિ final result approve કરે — એક જ વ્યક્તિ પોતાનું checking
પોતે જ મંજૂર ના કરી શકે.

1. **QA Review** — `qa.reviewer` → આખા batch record ને ઝીણવટથી ચેક કરે (બધા steps, deviations, readiness
   evidence બરાબર છે કે નહીં) → QA review package create → complete review — **password ફરી માંગશે**
   (`qa_review.execute` — સહી, QA Reviewer only).
2. **Release** — `qa.releaser` → Release scope evaluate (eligibility check — DDCP evidence FROZEN
   છે + કોઈ deviation open નથી, બધા CLOSED હોવા જોઈએ) → **Release** — final નિર્ણય, batch ને
   distribute/ship કરવાની ઔપચારિક મંજૂરી — **password ફરી માંગશે** (`release.release` — સહી, QA Releaser
   only).

**⚠️ DDCP Profile Section 8 ના "Complete review" vs "Release" ની જેમ જ — 2 અલગ actions, 2 અલગ role, 2
અલગ સહી.** Client ને આ pattern એક જ concept તરીકે 3 જગ્યાએ (DDCP release, batch review/release, deviation
disposition/close) બતાવો — "ચેક કરવું" અને "મંજૂરી આપવી" સિસ્ટમમાં ક્યારેય એક step નથી.

*(This section's real fields were not re-verified field-by-field against `frontend/src/app/{qa-review,
release}/page.tsx` in this pass — only the routing/permission-code correction above is newly
code-verified. A future pass should re-confirm the exact form fields the way §6-§10/§8.5/§9.9 were.)*

---

## 17. ટેક્નિકલ મેપિંગ સારાંશ (Frontend ↔ Backend)

| Phase | Frontend route | Backend prefix | Module (`app/modules/…`) | Doc # |
|---|---|---|---|---|
| 1 Suppliers | `/suppliers` | `/suppliers/v1`, `/supplier-qualifications` | `supplier_quality` | 18 |
| 2 Materials | `/materials`, `/material-receipts`, `/material-lots`, `/inventory` | `/materials`, `/materials/v1` (incl. `/receipts`), `/material-lots`, `/inventory/v1` | `material` | 19, 20 |
| 3 Equipment/Device | `/equipment`, `/devices` | `/equipment/v1`, `/devices/v1` | `equipment`, `device` | 38, 12 |
| 4 Product template | `/product-master` | `/products/v1` | `product_master` | 09 |
| 5 Recipe template | `/recipe-master` | `/recipes/v2` | `recipe_master` | 10 |
| 6 DDCP Profile | `/ddcp` (Profile designer) | `/ddcp/v1/prefilled-syringe/profiles` | `ddcp` | 54 |
| 7 Batch | `/batch-execution` | `/batches/v1` | `batch_execution` (table `ebmr.gxp_batch` — the single authoritative Batch store, 2026-09-08) | 11 |
| 8 DDCP execution | `/ddcp` (Execution) | `/ddcp/v1/prefilled-syringe/*` | `ddcp` (FKs `batch_id` into row 7's table) | 54 |
| 9 Deviation | `/deviations` | `/qms/v1/deviations` | `qms` | 26 |
| 10 Line clearance | `/line-clearance` | (`equipment.cleaning_*`) | `equipment` (cleaning) | 39 |
| 11 Readiness/Evidence | `/ddcp` (Batch readiness) | `/ddcp/v1/.../release-readiness`, `.../evidence-package` | `ddcp` | 54 |
| 12 QA Review/Release | `/qa-review`, `/release` | (QA review endpoints), `/release/v1` | `qa_review`, `release` | 14, 15 |

**✅ 2026-09-08 — SG-149/SG-173 RESOLVED (project-owner-directed, migration `0090`).** Every row above is
now a single, unambiguous track — `product`/`recipe`/`batch` (the legacy, non-`gxp_`-prefixed modules)
are retired: their pages redirect to `/product-master`/`/recipe-master`/`/batch-execution`, their tables
are empty, and DDCP/material/equipment/machine_integration's 32 FK columns all point at the `gxp_*`
tables now. `18_SPEC_GAPS.md` SG-149/SG-173 carry the full before/after detail.

**Users/Roles:** `/admin/users` ↔ `/auth/users`, `/auth/roles` (module `iam`). **Login/session:**
`/login` ↔ `POST /auth/token`, `GET /auth/me` (module `iam` + `security`, JWT + `application_session`
row — Section "Session expiry" ઉપર).

---

## 18. Client demo — શું emphasize કરવું

1. **બ્લોક થયેલા બટન = ફીચર, bug નથી.** Profile release, batch release, deviation close — બધા ત્યાં
   સુધી disabled/error આપે જ્યાં સુધી પાછલા step પૂરા ના થાય. "કાગળ પર ભૂલથી પણ સહી થઈ શકે, સિસ્ટમમાં
   ના થાય."
2. **e-signature = password re-entry, ચોક્કસ ક્ષણે જ.** Supplier qual approve, material lot release,
   deviation disposition/close, batch review/release, line clearance complete — બધે demo દરમિયાન client
   ને literally password ફરી type કરાવો.
3. **SoD role split.** DDCP Engineer profile બનાવે, DDCP Operator execute કરે — **એક જ user બંને
   permission સાથે ના હોવો જોઈએ** (production માં). `ddcp.engineer` થી execution tab hidden બતાવો
   (negative control).
4. **IND-001 independent verification** — Phase 8 ના assembly-verify moment — same-user verify attempt
   fail થાય એ live બતાવો.
5. **Audit trail** — `/audit` પર જઈ ને batch/deviation ના બધા actions (કોણે, ક્યારે, શું) timeline
   બતાવો — કંઈ delete/edit ના થાય (AG-08, append-only).
6. **Drug status ≠ Device status ≠ Combined status** — DDCP માં ક્યાંય એક જ "OK" badge નથી (readiness ના
   3 અલગ checkpoints — Phase 11).

---

## 19. જાણીતી મર્યાદાઓ (પ્રામાણિકતા)

| # | મર્યાદા |
|---|---|
| 1 | Supplier/Material master creation — **કોઈ RBAC gate નથી** (કોઈ પણ logged-in user બનાવી શકે); ફક્ત qualification approve/lot release/disposition gated છે. Client ને roadmap item તરીકે કહેવું. |
| 2 | ~~Product/Recipe Master માં author ≠ releaser split ન હતું~~ — **FIXED 2026-09-08**: `Process Engineer` role હવે `product.author` + `recipe.author` ધરાવે (release **નહીં**); `product.release` + `recipe.release` `QA Releaser` ને; બંને release signature policy `requires_independent_signer` (author ≠ releaser → `SOD_CONFLICT`, `IND-011`/`IND-021`). Standing-role-pair `SOD-021 (Process Engineer, QA Releaser)` platform floor માં ઉમેરાયો **REPORT_ONLY** તરીકે (Decision 1 — customer Quality org PROHIBITED કરી શકે, નવો `scripts/sync_sod_rules.py`). વિગત: §8.5, §9.9. |
| 3 | Release module (`/release/v1`) હાલમાં **ફક્ત `scope_type="batch"` support કરે છે** — device-lot/serial-level અલગ release scope હજુ built નથી (code comment: SG-056). |
| 4 | `ddcp.engineer`/`ddcp.operator` demo users seed થયેલ નથી — Section 3 મુજબ manually બનાવવા પડશે. |
| 5 | Autoinjector/Inhalation/Coated-device families ની depth PFS કરતાં ઓછી documented છે આ guide માં — જરૂર પડે `DDCP_Comprehensive_Test_Manual_Gujarati.md` §5.2-5.4 જુઓ. |
| 6 | Material lot બનાવવાના **2 જુદા રસ્તા** (§6) સાથે-સાથે અસ્તિત્વમાં છે — `/material-receipts` (supplier-approval ચેક કરે) અને `/material-lots` નું "Receive lot" quick shortcut (ચેક નથી કરતું). બંને valid lot બનાવે, ફક્ત એક જ regulated control run કરે. Client ને સ્પષ્ટ કહેવું — bug નથી, deliberate coexistence છે; production માં shortcut રાખવો કે નહીં એ client નક્કી કરે. |
| 7 | ~~Inventory adjustment approve કરવાનું UI હજુ બન્યું નહોતું~~ — **FIXED 2026-09-07**: Adjustments tab હવે pending-requests ટેબલ + Approve (SignatureCeremony, CON-FR-014 self-approval block) બતાવે છે, નવો `GET /inventory/v1/adjustments` read-only endpoint સાથે (§6.4.5). Reject હજુ કોઈ path નથી (backend command જ નથી — ફક્ત approve). |
| 8 | ~~Inventory ના Transfer/Cycle count/Adjustment forms raw UUID માંગતા હતા~~ — **FIXED 2026-09-07**: Batch/Material lot/Container/Location બધા હવે real dropdown છે, 2 નવા read-only backend endpoints (`GET /material-lots/{id}/containers`, `GET /inventory/v1/warehouse-locations`) ઉમેર્યા (§6.4.1). |
| 9 | `/material-lots` નું "Receive lot" quick shortcut (#6 ઉપર) **કોઈ `MaterialContainer` બનાવતું નથી** — એ path થી બનેલો lot કદી Transfer કે Reserve ના થઈ શકે (§6.4.2); Cycle count/Adjustment (container optional હોવાથી) ચાલે. |
| 10 | `/material-lots` ના "Available" column (`MaterialLot.available_quantity`) અને Inventory ના Availability tab (`InventoryBalanceProjection.available`) **બે અલગ, sync-ના-થયેલા counter** છે (§6.4.0). |
| 11 | ~~Warehouse location seed-only હતું, UI થી નવું બનાવવાનો રસ્તો નહોતો~~ — **FIXED 2026-09-07**: "New location" button/modal built (§6.4.6), નવો `warehouse_location.create` permission code (Admin/Supervisor only). **Update/Rename/Delete હજુ કોઈ endpoint નથી** — location એક વાર બને પછી કાયમ માટે immutable રહે છે. |
| 12 | Dev/demo DB માં `WH1`/`TEST-CREATE-01` નામનું 1 test location code-testing વખતે (2026-09-07) બનેલું છે — delete UI ના હોવાથી કાયમ રહેશે; demo વખતે client ને real location codes જ પસંદ કરવા (`QUARANTINE-01`/`RELEASED-01`/`REJECTED-01`), આ test row ignore કરવો. |
| 13 | ~~Product Master "New draft" modal માં Combination product type / Strength / Constituents ના fields જ નહોતા~~ — **FIXED 2026-09-07**: બધા fields + repeatable Constituents editor (Business-ID lookup સાથે) create modal માં ઉમેર્યા, backend command પહેલેથી support કરતું હતું (§8.1). |
| 14 | ~~Product Master draft ને create પછી edit કરવાનું કોઈ UI નહોતું~~ — **FIXED 2026-09-07**: `VersionDetailModal` માં "Edit" button (draft state માં જ), `PUT /products/v1/drafts/{id}` ને wire કર્યું (§8.4) — આ codebase નો પહેલો frontend PUT call હતો, `lib/api.ts` ના `api` helper માં `put()` ઉમેરવું પડ્યું. |
| 15 | Product Master release **completeness gate ફક્ત Release action પર જ ચાલે છે** (§8.3) — Create/Submit પર કોઈ ચેક નથી, એટલે `injectable_ddcp`/`inhalation_ddcp` profile + ખાલી Sterile process profile ID (કે UDI applicable + ખાલી Device model code) સાથે draft submit સુધી પહોંચી શકે, Release એ જ ક્ષણે block કરે — **હવે Edit UI (§8.4) થી draft ને submit પહેલાં જ સુધારી શકાય, નવો draft ફરજિયાત નથી**. |
| 16 | Dev/demo DB માં `TEST-CONST-DRUG`/`TEST-CONST-DEVICE`/`TEST-CONST-COMBO` નામના 3 test product draft (2026-09-07, Edit/Constituents feature ના code-testing વખતે) બનેલા છે — delete UI ના હોવાથી કાયમ રહેશે; demo વખતે client ને real business ID જ વાપરવા (`MERIDIJECT-PFS`/વગેરે), આ test rows ignore કરવા. |
| 17 | આ guide માં આપેલ બધો ડેમો ડેટા **fictional અને હજુ system માં દાખલ કરેલો નથી** — ખરેખર run કરીને જ verify થશે. |
| 18 | **SG-178 — RESOLVED 2026-09-08** (project-owner-directed: Option A + documented override). Recipe step `required_role_code` હવે regulated `/batch-execution` path માં hard-enforced: migration `0086` `ebmr.gxp_batch_step.required_role_code` ઉમેરે, `issue_batch` snapshot માં freeze કરે, `start_step` role ના હોય તો `STEP_ROLE_MISMATCH` (403) આપે; `override_reason` + નવી `batch_step.role_override` permission (Admin/Supervisor) થી documented override. Legacy `app/modules/batch` store જાણી જોઈને unenforced (SG-173). Frontend: recipe form માં "Required role" picker, `/batch-execution` માં override-reason box. વિગત §9.1/§11.1, `18_SPEC_GAPS.md` SG-178. |
| 19 | Product Master (§8.5), Recipe Master (§9.1), અને Batch Create/Issue/Start (§11.1) માટે detailed role-wise action ટેબલ + concrete multi-role ઉદાહરણ **2026-09-07 ઉમેર્યા** — code re-verify કરીને, જેમાં ક્યાં SoD ખરેખર enforced છે (Batch Review/Release, Deviation, IND-001, CON-FR-014) અને ક્યાં ફક્ત design intent છે (Product/Recipe Master authoring, step-level role) એનો સ્પષ્ટ સારાંશ (§11.1 નું છેલ્લું ટેબલ) સામેલ છે. |
| 20 | ~~Recipe Master "New draft" form માં Product business ID / Product version ID / Manufacturing profile free-text (raw UUID) હતા~~ — **FIXED 2026-09-08**: ત્રણેય હવે real dropdown (§9.1/§9.6) — Product `GET /products/v1/business-ids`, Product version dependent `GET /products/v1/{bizid}/versions` (released first), Manufacturing profile 5-value list; Site + profile product version પરથી auto-fill. Backend હવે unknown `product_version_id` ને `NOT_FOUND` (404) આપે (પહેલાં opaque 500). કોઈ backend endpoint નવો નહોતો — product_master ના existing `product.view`-gated read endpoints જ Process Engineer પણ વાપરે. |
| 21 | ~~`process.engineer` demo user live DB માં ન હતો~~ — **FIXED 2026-09-08**: `process.engineer` / `ChangeMe123!` @ `SITE1` બની ગયો + `scripts/seed.py` `DEMO_USERS` માં પણ ઉમેરાયો (§9.12). |
| 22 | ~~Verification runs એ live `ebmr_new_gxp` DB માં throwaway recipe families (`RCP-SMOKE*`/`RCP-PICKER*`) છોડ્યા હતા~~ — **FIXED 2026-09-08**: controlled repair migration `0087_repair_verification_recipe_families` (MIG-FR-005) એ exact `recipe_code` થી delete કરી (0 batch/genealogy references confirmed); `audit.audit_events`/`vault.*` અડ્યા નથી (append-only). *(આ turn ના product-master verification નો `PRD-SMOKE*` migration `0088` માં clean થાય.)* Note: `TEST-CONST-*` / `TEST-CREATE-01` / `TEST-SIGREL-*` / `DEMO-STERILE-REAL-*` હજુ છે (પહેલાંની sessions ના, demo વખતે ignore). |
| 23 | **Decision 1 (Document 107 SoD) — long-term:** SoD matrix (`iam.sod_rules`) પહેલેથી data-driven છે; ખૂટતું હતું re-runnable live sync. **નવો `scripts/sync_sod_rules.py`** (`sync_permissions.py`/`sync_signature_policies.py` જેવો — upsert by `code`, ક્યારેય delete નહીં) ઉમેર્યો; `SOD-021 (Process Engineer, QA Releaser, REPORT_ONLY)` + `IND-021 (ProductVersion/release/AUTHOR, PROHIBITED)` platform floor માં. Customer Quality org PQ વખતે `SOD-021` ને PROHIBITED કરી શકે. |
| 24 | ~~Recipe Master dependency `condition_rule_id`/`condition_rule_version` backend-only હતા (form માં નથી)~~ — **FIXED 2026-09-08**: Dependencies editor માં ઉમેર્યા (§9.4) — `condition_rule_id` real dropdown (નવો `GET /rules/v1`, effective released rules, `rules.evaluate`-gated — SG-081 read-side precedent), `condition_rule_version` optional text pin. Detail modal પણ હવે Dependencies table બતાવે. |
| 25 | ~~`/ddcp` નું "Product family" dropdown અને Product Master (§8) વચ્ચે કોઈ FK/link જ નહોતું~~ — **FIXED 2026-09-08 (SG-175, migration `0089`), project-owner-directed** (asked directly, chose Option B — `ddcp.ddcp_profile_version.product_version_id` FK — over SG-175's originally-recommended Option A, જે ઊંધી દિશામાં FK સૂચવતું હતું): DDCP profile create (બધી 4 family) ને હવે RELEASED Product Master version ફરજિયાત reference કરવો પડે (§10.1) — existence/RELEASED/site ચેક + PFS/Inhalation માટે manufacturing-profile code match પણ. **⚠️ Residual (હજુ ખુલ્લું):** Autoinjector/Coated device માટે family-match check નથી (Product Master ના 5 code માંથી કોઈ પણ એ 2 family ને ચોક્કસ નામ નથી આપતું — guess નથી કરવાનું); અને Option A ની દિશા (Product Master પોતે DDCP profile ને point કરે) બિલ્ડ નથી થઈ — ફક્ત reverse lookup (DDCP → Product) જ છે. Full detail: `18_SPEC_GAPS.md` SG-175. |
| 26 | ~~2026-09-08, this guide's own previous error...~~ — **SUPERSEDED same day by #27 below.** This entry described an intermediate, correct-at-the-time state (2 disjoint batch tables, DDCP demo forced onto the legacy `/batches` path) that the project owner then had fixed for real, not documented around. Left here rather than deleted (this guide got it wrong twice in one day before landing on the actual fix — see #27 — and that history is worth keeping honest). |
| 27 | **2026-09-08, later the same day, project-owner-directed ("prefer [Document 11's batch_execution] for batch... database is not on demo and test mode... delete data for existing batch... accurate functionality... proper frontend user experience with foreign key dropdown value") — SG-149/SG-173 fully RESOLVED for Batch, not just documented.** Migration `e5f7a9c1b3d6_0090`: (1) deleted the 2 demo/test batches, 6 batch steps, 3 DDCP constituent handoffs, and the 2 legacy Product + 2 legacy Recipe rows that existed only to support them (all confirmed demo/code-testing data, zero real customer records); (2) retargeted all 32 FK columns across `ddcp` (11), `material` (9), `equipment` (7) and `machine_integration` (5) from the legacy `ebmr.batches`/`batch_steps` onto the authoritative `ebmr.gxp_batch`/`gxp_batch_step`, plus the matching Python import swaps and one `.status`→`.state` rename (`ddcp/commands.py::get_readiness()`). **Also fixed along the way:** `iam/commands.py::delete_site()`'s blocking-reference guard checked only the legacy `Product`/`Batch` tables — a site with real Product Master/Recipe Master/`batch_execution` data could be deleted with no warning; now checks `ProductVersion`/`RecipeVersion`/`gxp_batch` too. **Frontend:** legacy `/batches`, `/batches/new`, `/batches/[id]`, `/products`, `/recipes`, `/recipes/new`, `/recipes/[id]/edit` all now redirect to `/batch-execution`/`/product-master`/`/recipe-master`; removed from sidebar nav; root/login redirect and `useRequireAdmin`'s default both moved off `/batches`. The 4 pickers that listed batches via the legacy `GET /batches` (`dispensing`, `packaging`, `inventory`, `useEntityOptions`) now use a new `listBatchesForSite()` helper against `GET /batches/v1`, reshaped into the same `BatchSummary` type so no JSX changed; `/batches/v1`'s list/detail endpoints were also enriched with resolved `product_name`/`product_code` (a join to `ProductVersion`) so those pickers show a real label, not a bare UUID. **Live-tested end to end, not just unit-level** (`ebmr_new_gxp_test`'s own pytest DB has a pre-existing, unrelated credential failure blocking all suites — confirmed via an untouched module — so verification here is real API calls against the live DB instead): created `MJ-PFS-B-2601` via `/batches/v1` against MeridiJect PFS's actual RELEASED Product Master + Recipe Master versions → issued → started → recorded a real DDCP constituent handoff against it (no 404) → confirmed the row landed with the `gxp_batch` id → a real material inventory reservation against the same batch also succeeded. This batch is left in the live DB as real data, not cleaned up. **Not done this pass** (separate, smaller scope, left for a future pass if wanted): actually dropping the legacy `app/modules/batch`/`product`/`recipe` code/tables (Document 100 "contract" step — kept for now per the same expand→migrate→contract discipline, since the frontend cutover above was only just verified); re-verifying `/qa-review`/`/release` field-by-field (§16 routing/permissions were corrected, its detailed fields were not re-checked this pass). Full detail: `18_SPEC_GAPS.md` SG-149, SG-173. |
| 28 | **2026-09-08, later still, project-owner-directed (hit live while the client tested Phase 8 Op 2) — SG-179 RESOLVED.** Accepting a real DRUG constituent handoff (a released `LOT-DRUG-2601` material lot, correctly recorded per §12.1 Op 1's own "Material lot ID" guidance) always failed `BULK_NOT_RELEASED`. Root cause: `decide_constituent_handoff()` only ever checked a released **Batch** reference for `DRUG`/`BIOLOGIC` constituents (PFS-FR-003's literal wording) and never checked a Material Lot for them at all — but this platform has no feature anywhere to create/release a batch record for externally-supplied bulk drug substance; every real onboarding path (Supplier → Receipt → Lot) produces a lot, identically to the device component (PFS-FR-004). A second latent bug in the same branch: it compared `gxp_batch.state` to the literal string `"released"`, a value that state machine never produces. Asked directly which fix to take (accept a lot too / build real batch tracking for bulk drug / leave blocked) — chose accept-a-lot-too, matching how the rest of the platform already works. Fixed: `decide_constituent_handoff()` now resolves whichever key `source_batch_reference` actually carries — `batch_id` only for DRUG/BIOLOGIC (kept for the literal spec wording + the state-value bug fixed alongside it, though nothing can produce one yet), `lot_id` for any constituent type (real released-lot check, same as the device branch). Also fixed §12.1 Op 2's "Profile (optional check)" field — was plain free text, now the same real `profileSelect` dropdown Op 3 already used. Verified live against the client's own real pending handoffs (both DRUG and DEVICE) via a rolled-back transaction — confirmed both now pass, their actual PENDING handoffs left untouched for them to accept themselves through the UI. No migration (`source_batch_reference` is JSONB). Full detail: `18_SPEC_GAPS.md` SG-179. |
| 29 | **✅ 2026-09-09, project-owner-directed (client batch got permanently stuck — every generic recipe step past the first showed "predecessor not yet completed" forever) — SG-047 PARTIALLY RESOLVED.** `/batch-execution` had `Start` for a step but **no way to ever finish one** — `gxp_step_result`/completion were prose-only, undeferred field lists (SG-047). Also found and fixed alongside: the frontend compared batch state to `"in_progress"` everywhere, but the backend only ever emits `"in_execution"` — so once a batch started, the "In progress" KPI stayed 0 and, critically, **the per-step Start button silently never rendered at all**. Built: `gxp_step_result` table (migration `db47f27cf18b_0092`, typed by reusing `gxp_recipe_parameter`'s own already-declared data_type/UOM/precision, not a new guess); signed `POST .../steps/{id}/results` and `.../complete` (Document 106 rows 21/19, `Performed` meaning, no independence — independent verification is modelled as its own dedicated recipe step, e.g. `ASSY-VER-01`, not a second signer on the same action); a runtime half for BAT-FR-006 readiness (a `pending` successor becomes `ready` once every declared predecessor is `complete`). Frontend: "Record results"/"Complete" buttons on an in-progress step, each a real signed ceremony (password re-auth), pre-filled with the recipe's declared parameters (target/min/max/UOM shown as hints). Full detail + what's still open (evidence attach, step-level hold, correction/rework, timers, material/equipment linkage, Production-Complete batch state): §11.3 above, `18_SPEC_GAPS.md` SG-047/SG-048. |
| 30 | **✅ 2026-09-09, found answering a client question (not yet resolved — SG-180 open, project-owner decision needed).** "Batch Execution" (generic recipe-step chain, `/batch-execution`) and "DDCP Execution" (`/ddcp`'s constituent-handoff/fill/assembly records) both point at the same `ebmr.gxp_batch` row (since migration `0090`'s cutover, #27 above) but **neither reads nor writes the other** — confirmed by exhaustive grep, zero call sites. Completing DDCP's execution tabs does not complete/unblock the matching generic recipe step (`DISP-01`/`FILL-01`/`ASSY-01`/…) and vice versa. Separately (already SG-056, not new): the actual `/release` eligibility check reads **neither** DDCP execution nor DDCP's own "release-readiness"/evidence-freeze (§15) — only QA-review-package completeness and Vault snapshot integrity — so a batch can in principle be Released while DDCP execution/readiness is incomplete. See §12.0 above for the full 4-way comparison table and the recommended demo sequence. Three fix options recorded in `18_SPEC_GAPS.md` SG-180, none chosen yet — this is a scope decision for the project owner, not something guessed here. |
| 31 | **✅ 2026-09-09, client-requested ("show detail of step") — built same day as #29.** Step rows on `/batch-execution` only ever showed code/role/state/assigned/started — the recipe's own instruction text, section, dependency graph and declared evidence requirements were nowhere in the UI. New "Detail" button on every step row (any state, not just running) opens a read-only view: step type, section, instruction text, critical flag, predecessors/successors, every parameter with its target/range and currently recorded value, and declared evidence requirements (upload still not built, SG-047 — shown for visibility only). Backend: `GET /batches/v1/{id}/execution-view`'s new `step_detail_by_step_id`, read from the live recipe graph (display-only, not a regulated decision — the frozen execution snapshot in Vault remains the authoritative instruction record). §11.3 above. |
| 32 | **✅ 2026-09-09, project-owner-directed (client asked to fix the §11.3 "what's missing" gap table; asked which of six items to prioritize — chose step-level hold + Production Complete, explicitly declined material/equipment linkage once it turned out blocked on SG-045) — SG-047/SG-048 further partial resolution.** Two new capabilities: (a) step-scoped hold/resume (`StepHold`, migration `a6d525b2d585_0093`) — signed `POST .../steps/{id}/hold`/`.../resume` (Document 106 row 14/17's shapes reused, no step-scoped row exists in Document 106 itself), holds exactly one step without stopping the batch or any other step; (b) `production_complete` batch state (BAT-FR-026, steps-completeness sub-clause only) — signed `POST /batches/v1/{id}/production-complete` (Document 106 row 16), refuses with `PRODUCTION_NOT_COMPLETE` + the list of unfinished step codes until every `gxp_batch_step` is `complete`; a `production_complete` batch can still be pulled into Hold if a problem is found late. §11.4/§11.5 above. **Material/Equipment linkage (BAT-FR-012/013) was NOT built** — considered directly, but `RecipeStep` has no field anywhere declaring which material lot or equipment class a step needs, and defining that field is itself SG-045's own still-open, unresolved schema question ("tolerance rule"/"consume mode"/"calibration policy" are policy concepts, not typed columns) — building it now would mean guessing exactly the schema SG-045 already declined to guess. Verified: `test_batch_execution.py` 27/27 (4 new tests: hold+resume happy path, hold-requires-reason, hold-requires-signature, production-complete happy path + blocked-until-complete + wrong-state) plus `test_batch_flow.py`/`test_release.py`/`test_qa_review.py` as an untouched-module control, 34/34. Full detail: `18_SPEC_GAPS.md` SG-047, SG-048, SG-045 (the last updated with a "not a resolution" note only). |
| 33 | **✅ 2026-09-16, નવું finding (code-verified, `frontend/src/app/{ddcp,batch-execution}/page.tsx`) — `/batch-execution` અને `/ddcp` વચ્ચે કોઈ navigation link, query param કે UUID copy-button નથી.** Sidebar માં બંને અલગ-અલગ, batch-context-free static entry. `/batch-execution` ના batch detail view માં Batch ID plain, selectable UUID text તરીકે દેખાય છે (`IdFact` component, `frontend/src/components/ui/FactGrid.tsx`) — copy-button નથી, href નથી. `/ddcp` ના batch પસંદગી field (`batchSelect`) ક્યારેય URL query param (દા.ત. `?batch_id=`) થી auto-fill નથી થતા — tester એ manually UUID select/copy કરીને, sidebar થી `/ddcp` પર જઈને, સાચી "Product family" પસંદ કરીને (batch ના product પરથી ખબર પડવી જોઈએ — family auto-detect નથી થતી), પછી paste કરવું પડે. §12.0 એ already સમજાવેલું છે કે batch execution અને DDCP execution 2 સ્વતંત્ર progress-track છે (SG-180) — આ finding એ જ વાતનો UI-mechanics-level પુરાવો છે: કોડ પણ બંને પાનાં વચ્ચે કોઈ programmatic bridge બનાવતો નથી, ફક્ત common `batch_id` FK data-level જોડે છે. §21.3 નીચે આ manual-copy પગલું જ demo-step તરીકે લખ્યું છે. Roadmap item, bug નથી. |
| 34 | **✅ 2026-09-16, નવું finding (code-verified, `services/gxp-api/app/modules/ddcp/{router,commands}.py`, uncommitted diff).** 2 નાના backend-only addition, હજુ frontend માં વપરાયા નથી: (a) `GET /ddcp/v1/prefilled-syringe/constituent-handoffs/{id}` અને `GET .../batches/{batch_id}/constituent-handoffs` — handoff ને સીધું ID/batch થી read કરવાના નવા endpoint (અત્યાર સુધી ફક્ત genealogy view થી જ handoff data મળતું, હવે એક વધારાનો direct રસ્તો પણ છે); (b) profile GET/list response હવે વધુ fields પરત કરે છે — `site_id`, `dosage_form`, `presentation`, `constituent_architecture`, `required_controls`, `release_checkpoint_set`, `vault_object_id`, `released_by`, `release_signature_id`, `effective_from`, `created_at` (પહેલાં ફક્ત id/profile_code/subtype/version/state/product_version_id જ આવતા — બીજા 49 modules માં પકડાયેલા "GET serializer drops field" bug pattern નું જ DDCP-side fix, code-testing repo-wide sweep). PFS ના "Look up a profile version" panel (§10.1, ફક્ત PFS family ને છે) હવે વધુ ડેટા બતાવશે — UI code બદલાયો નથી, JSON panel raw response જ બતાવે છે એટલે આપોઆપ વધુ fields દેખાશે. |
| 35 | **✅ 2026-09-16, Recipe Master "New draft" popup → full page** (project-owner-directed, asked directly — "1 small change... make new screen for it... so there will be things easy for user"). `DraftModal` retired; `process.engineer` → `/recipe-master` → "New draft" now navigates to `/recipe-master/new`, a dedicated page with the same fields/validation/submit call, just more room for the Sections/Steps/Dependencies graph editor and its 4 per-step sub-editors (§9.3.1-9.3.4) than a `Modal` had. Shared code (~800 lines: all draft-editing types, `emptySection`/`buildGraphPayload`/`sectionsFromVersion`, `useRoleAndRuleOptions`, `MaterialSpecVersionPicker`, `RecipeGraphEditor`/`StepBlock`) moved to a new `frontend/src/app/recipe-master/shared.tsx` so the list page's `EditGraphModal` (unchanged, still a modal — only *create* moved) and the new create page both use the one graph editor, no duplication. On successful create, the new page redirects to `/recipe-master?openFamily=<id>`, which the list page reads (via `window.location.search`, not `next/navigation`'s `useSearchParams()` — avoids a Suspense-boundary requirement this page had no other reason for) to auto-jump straight to the new family's versions, same behavior the old modal's `onDone` callback gave. `tsc --noEmit` and `eslint` both clean; both routes live-verified 200 via pm2/curl. |

---

## 20. સંદર્ભ

- **Exhaustive role-wise test cases (dev/QA માટે):** `docs/testing/DDCP_Comprehensive_Test_Manual_Gujarati.md`
- **Sterilization/Aseptic — DDCP ના DEVICE constituent handoff ને જોઈતો "Sterilization reference" ક્યાંથી
  મળે (§12.1 Op 2):** `docs/testing/Sterilization_Aseptic_Client_Demo_Guide_Gujarati.md` (real data-entry)
  + `docs/testing/Sterilization_Aseptic_Comprehensive_Test_Manual_Gujarati.md` (field/RBAC/state-machine
  reference)
- **સાદી ભાષામાં DDCP concept (non-technical):** `eBMR-ui/DDCP-GUIDE-GUJARATI.md` *(⚠️ એ design-preview
  reference માટે છે, વાસ્તવિક backend/frontend સાથે નથી — ફક્ત concept સમજવા)*
- **Permission / signature-policy / SoD-matrix live sync:** `scripts/sync_permissions.py`,
  `scripts/sync_signature_policies.py`, `scripts/sync_sod_rules.py` (all re-runnable, no reseed).
- **Permission catalogue (source of truth):** `services/gxp-api/scripts/sync_permissions.py`,
  `services/gxp-api/scripts/seed.py` (`PERMISSIONS`, `ROLE_PERMISSIONS`, `SIGNATURE_POLICY_FLOOR`)
- **Session/auth config:** `services/gxp-api/app/core/config.py`

---

*આ document code થી verified (2026-09-03; 2026-09-07 ના રોજ ફરી verify/update — Phase 2 ની list + modal
UI, Supplier/Manufacturer name resolution, discrepancy_hold ની one-way-lock ચોખવટ, અને **દરેક Phase (1,
3-12) માં field-by-field "કેમ જરૂરી" સાદી-ભાષા explainer** ઉમેર્યું; 2026-09-07 later same day — Product
Master Constituent Business ID field હવે real dropdown (`GET /products/v1/business-ids`, નવો endpoint) +
Field/Button alignment fix (§8.1), અને **§8.5/§9.1/§11.1 — Product Master, Recipe Master, Batch
Create/Issue/Start માટે detailed role-wise/approver-reviewer action ટેબલ + concrete multi-role
ઉદાહરણ** ઉમેર્યા, જેમાં `required_role_code` step-level enforcement ના honest gap ને re-verify કરીને
correct કર્યું (નવો SG-178) સામેલ છે; **2026-09-08 — SG-178 RESOLVED + §9 full rewrite**: dedicated
`Process Engineer` role (author ≠ releaser; `recipe_version/release` signature = independent QA Releaser,
§9.10), step `required_role_code` regulated `/batch-execution` path માં hard-enforced (migration 0086,
નવી `batch_step.role_override` permission + documented override), recipe form ના બધા top-level fields
હવે real dropdown (Product/Product-version/profile — §9.1/§9.6), unknown product_version → 404,
`process.engineer` demo user live બન્યો, §9 field-by-field spec + MeridiJect PFS worked example + §19
#20/#21 ઉમેર્યા; **2026-09-08 later — Decisions 1/2 + cleanup**: Product Master ને પણ author≠releaser
split (`Process Engineer` = `product.author`; `QA Releaser` = `product.release`; `product_version/release`
signature independent, `IND-021`), Document 107 SoD matrix ને re-runnable `scripts/sync_sod_rules.py` +
`SOD-021` REPORT_ONLY floor row, અને controlled repair migration `0087`/`0088` થી verification-only test
recipe/product families removed — §4/§8.5/§19 #22/#23 update; **2026-09-08 later still — dependency
condition rule**: Recipe Master Dependencies editor ને `condition_rule_id`/`condition_rule_version`
fields મળ્યા (§9.4) — નવો read-only `GET /rules/v1` (effective released rules, SG-081 precedent) real
dropdown feed કરે છે, detail modal માં Dependencies table ઉમેરાયું — §19 #24; **2026-09-08 later still,
project-owner-directed — SG-149/SG-173 RESOLVED for Batch (migration `0090`)**: `/batch-execution`'s "New
batch" modal got real cascading dropdowns; this guide was then twice corrected and re-corrected in the
same day (§19 #26/#27) as the underlying two-table split was found, documented, scoped, and finally
fixed for real — 32 FK columns across `ddcp`/`material`/`equipment`/`machine_integration` retargeted
onto `ebmr.gxp_batch`, demo/test data (2 batches, legacy Product/Recipe rows) deleted, legacy
`/batches`/`/products`/`/recipes` pages retired to redirects, 4 batch pickers repointed, `iam`'s
`delete_site()` guard gap fixed — live-tested end to end against real MeridiJect data, §11/§12/§16/§17
rewritten accordingly):
`app/modules/{supplier_quality,material,product_master,
recipe_master,ddcp,batch_execution,device,equipment,qms,release,rules,iam,machine_integration}/{commands,router,service,models}.py`,
`scripts/seed.py`, `frontend/src/app/{suppliers,materials,material-receipts,material-lots,inventory,
product-master,recipe-master,ddcp,batch-execution,batches,products,recipes,dispensing,packaging,
deviations,release,equipment,devices,line-clearance}/*`, `frontend/src/{lib/api.ts,lib/hooks.ts,
components/layout/Sidebar.tsx}`; **2026-09-09, project-owner-directed — SG-047 partial resolution
(§11.3, §19 #29) + a new §12.0 clarification block (§19 #30) added after answering a client question
about the difference between "batch execution" and "DDCP batch release"**: `gxp_step_result` +
signed step results/completion built (migration `db47f27cf18b_0092`,
`app/modules/batch_execution/{models,service,commands,router}.py`, `app/mutation/errors.py`,
`scripts/{seed.py,sync_signature_policies.py}`, `frontend/src/app/batch-execution/page.tsx` —
Record results/Complete buttons + the `in_progress`→`in_execution` state-string bug fix), verified with
`tests/test_batch_execution.py` (21/21) plus `test_batch_flow.py`/`test_release.py`/`test_qa_review.py`
as an untouched-module control (34/34); a new architectural finding (SG-180, open) — Batch Execution's
generic recipe-step chain and DDCP's own execution records track progress independently on the same
batch, and neither feeds the actual `/release` eligibility check (SG-056) — is recorded in §12.0/§19 #30
and `18_SPEC_GAPS.md`, not silently resolved; **2026-09-09, later the same day, client-requested ("show
detail of step" + "fix the gaps") — a step-detail view (§11.3, §19 #31:
`frontend/src/app/batch-execution/page.tsx`'s new `StepDetailModal`, backend
`step_detail_by_step_id` in `batch_execution/{service,router}.py`) plus step-scoped hold/resume and a
`production_complete` batch state (§11.4/§11.5, §19 #32: new `StepHold` model, migration
`a6d525b2d585_0093`, `hold_step`/`resume_step`/`production_complete_batch` commands, 3 new signed
endpoints, error `PRODUCTION_NOT_COMPLETE`) — SG-047/SG-048 further partial resolution,
project-owner-directed (asked to prioritize among six gaps; material/equipment linkage was considered and
explicitly declined once found blocked on SG-045's own open schema question, not silently skipped),
verified with `test_batch_execution.py` 27/27 (4 new tests) plus the same 34/34 control. Demo data
fictional; roles/endpoints/signature-requirements real.*

---

## 21. નવું Test Cycle (Round 2, 2026-09-16) — Real Live Data

### 21.0 આ section કેમ ઉમેર્યું — live DB સામે ચકાસેલી હકીકત

Live `ebmr_new_gxp` DB સીધું query કરીને ચકાસ્યું (2026-09-16):

| શું | DB સ્થિતિ |
|---|---|
| Batch `MJ-PFS-B-2601` | state = `production_complete`; **બધા 8 recipe step** (`LC-01`/`DISP-01`/`FILL-01`/`FILL-IPC-01`/`ASSY-01`/`ASSY-VER-01`/`TEST-CCI-01`/`TEST-VIS-01`/`HOLD-QA-01`) `complete`; `qa_review_package.state = REVIEW_COMPLETE`; `release_scope.state = released` — **batch આખેઆખો released છે, ફરી create/issue/start ના જ થઈ શકે** |
| Batch `RCP-MJ-PFS-DEMO` | એ જ સ્થિતિ — `production_complete`, review complete, **released** |
| DDCP evidence (`MJ-PFS-B-2601` પર) | `batch_evidence_manifest` ના 2 row — v1 અને v2, બંને `FROZEN` |
| Deviation | `DEV-2026-0141` અને `DEV-2026-0143` — બંને `MJ-PFS-B-2601` પર, બંને `CLOSED` — **આ 2 number ફરી વાપરવાનો પ્રયત્ન કરશો તો `deviation_number` unique constraint error** |
| Material lot `LOT-DRUG-2601` | status `released`, `available_quantity = 12.500 ML` — **હજુ consumed નથી** (DDCP handoff lot ની quantity ઘટાડતું નથી, §12.1 Op1 ની ડેમો data હજુ technically ફરી વાપરી શકાય, પણ receipt/lot number પોતે unique છે) |
| Material lot `LOT-DEV-2601` | status `released`, `available_quantity = 4200.000000 EA` — એ જ વાત |
| Line clearance (`equipment.cleaning_executions`) | **0 row** — Phase 10 ક્યારેય ખરેખર execute નથી થયું આ DB માં (§19 ના honest history માં ક્યાંય line-clearance-execute confirm નથી કરેલું) — સારો fresh-test candidate |
| `LINE-PFS-01` equipment | `qualification_status = QUALIFIED`, `calibration_status = NULL` (= eligible, code: `equipment/commands.py::_ineligibility_reasons()` — `state` column literally `VERIFICATION` છે પણ એ field eligibility check માં વપરાતું જ નથી) — **readiness માટે equipment પહેલેથી eligible છે, કંઈ પ્રિપેર કરવાની જરૂર નથી** |
| Rules module (`rules.gxp_rule_definition`) | ફક્ત 3 rule — `SMOKE-ASSAY` (eligibility, validated), `yield_percent` (CALCULATION, released), 1 draft. **`FILL-WEIGHT-RULE-01` નામનો rule ક્યારેય exist જ નથી કર્યો** — §12.1 Op4/Op10 ના જૂના ડેમો data માં આ ID એક placeholder હતો, ખરેખર rules engine સામે ક્યારેય evaluate નથી થયો (`rules.gxp_rule_evaluation` માં કુલ 1 જ historical evaluation છે, `yield_percent` સામે, outcome = `ERROR`) |

**નિષ્કર્ષ:** Master data (suppliers, materials, `MJ-PFS-40MG` Product, `RCP-MJ-PFS-V1` Recipe, `PFS-MERIDIJECT-001` DDCP profile) **બધું RELEASED અને reusable છે** — ફરી બનાવવાની જરૂર નથી, real GxP practice માં પણ master data batch-દીઠ ફરી નથી બનતું. ફક્ત **batch-specific અને lot-specific numbers** નવા જોઈએ. નીચેનું cycle એ જ આપે છે.

### 21.1 શું reuse કરવું, શું નવું જોઈએ

| Master/Record | Code | Reuse કરવું કે નવું? |
|---|---|---|
| Supplier (drug) | `SUP-BIO-001` | **Reuse** — released, qualified |
| Supplier (device) | `SUP-DEV-001` | **Reuse** |
| Material master (drug) | `MAT-DRUG-MERIDIZ` | **Reuse** |
| Material master (device) | `MAT-DEV-SYR-1ML` | **Reuse** |
| Product Master | `MERIDIJECT-PFS` → `MJ-PFS-40MG` v1 | **Reuse** — RELEASED |
| Recipe Master | `RCP-MJ-PFS-V1` v1 | **Reuse** — RELEASED |
| DDCP Profile | `PFS-MERIDIJECT-001` v1 | **Reuse** — RELEASED |
| Equipment (line/asset) | `LINE-PFS-01` | **Reuse** — already QUALIFIED, eligible |
| Equipment area | `AREA-GRADE-A` | **નવેસરથી વાપરવું** — §21.2 ની નોંધ જુઓ, જૂનો doc `LINE-PFS-01` ને area તરીકે વાપરતો હતો, જે ખોટું હતું (asset code, area code નહીં) |
| Material receipt | `RCPT-DRUG-2601`/`RCPT-DEV-2601` | **નવો number જોઈએ** (unique constraint) |
| Material lot (internal) | `LOT-DRUG-2601`/`LOT-DEV-2601` | **નવો number જોઈએ** (`internal_lot` globally unique) — *(જૂના lot ટેકનિકલ રીતે reuse-eligible છે, released + available quantity બાકી છે, પણ fresh receiving path વધુ realistic demo છે — §21.3.1)* |
| Batch | `MJ-PFS-B-2601` | **નવો number જોઈએ** — જૂનો batch released થઈ ચૂક્યો |
| Deviation | `DEV-2026-0141`/`0143` | **નવો number જોઈએ** |
| Acceptance rule (IPC/dose/closure/loading) | `FILL-WEIGHT-RULE-01` | **⚠️ Real rule બનાવવો પડશે પહેલા** — §21.3.3 ની honest નોંધ જુઓ |

### 21.2 નવો data map — 1 નજરમાં (batch cycle "2701")

| Field | નવો Value |
|---|---|
| Batch number | **`MJ-PFS-B-2701`** |
| Production order ref | `PO-2026-4472` |
| Receipt — drug | `RCPT-DRUG-2701` |
| Receipt — device | `RCPT-DEV-2701` |
| PO reference — drug/device | `PO-MAT-2026-1287` / `PO-MAT-2026-1288` |
| Supplier's lot — drug/device | `SUP-LOT-2701-D` / `SUP-LOT-2701-V` |
| Carrier ref — drug/device | `FEDEX-8851190` / `FEDEX-8851191` |
| Internal lot (examine પછી) — drug/device | **`LOT-DRUG-2701`** / **`LOT-DEV-2701`** |
| Deviation number | **`DEV-2026-0201`** |
| Source event ID (production count) | `EVT-COUNT-2701-01` |
| Fill cycle group | `CYCLE-B` |
| Assembly unit identifier | `MJ-UNIT-2701-0001` |
| Stability plan | `STAB-PLAN-MERIDIJECT-01` (reuse — master reference, no uniqueness constraint) |

*(બધા code-verified against live DB — 2026-09-16 ના રોજ કોઈ પણ collision નથી, `SELECT ... WHERE ... LIKE '%2701%'` run કરીને ચકાસેલું.)*

### 21.3 Step-by-step — શું નવેસરથી કરવું

Field-level meaning/UI location માટે દરેક પગલે મૂળ Phase section refer કરેલો છે — અહીં ફક્ત **નવો data** અને **જે બદલાયું** આપ્યું છે, ડુપ્લિકેટ નથી કર્યું.

#### 21.3.1 Phase 2 ફરી — નવો receipt/lot (§6.2 ના fields, નવો data)

`operator1` → `/material-receipts` → "Log a receipt" → §21.2 ના drug/device receipt data ભરો (received qty gross `12.500`/`L` drug, `4200`/`EA` device — §6.2 જેવું જ) → Submit → **"Examine"** → §6.2 ના જ 5 Yes/No ચેક (Identity/Labeling/Damage/Seal/Contamination) → Internal lot ફિલ્ડમાં `LOT-DRUG-2701`/`LOT-DEV-2701` → Submit → lot **Quarantine** માં બને.

`qc.reviewer` → `/material-lots` → બંને lot ને **Disposition → Released** (સહી — §6.3).

*(Optional, skip કરી શકાય: §6.4 નો પૂરો inventory put-away/reserve/cycle-count/adjustment walkthrough — એ mechanics પહેલેથી `LOT-DRUG-2601` પર 2026-09-07 ના રોજ demo/verify થયેલ છે, ફરી જરૂરી નથી. DDCP constituent handoff — §21.3.2 — lot ને directly reference કરે છે, inventory transfer/reserve independent છે.)*

#### 21.3.2 Phase 7+8 ફરી — નવો batch, DDCP execution (§11/§12 ના fields, નવો data)

1. `supervisor1` → `/batch-execution` → "New batch" → Product `MJ-PFS-40MG` v1 (dropdown, RELEASED) → Recipe `RCP-MJ-PFS-V1` v1 (dropdown, RELEASED) → Batch number `MJ-PFS-B-2701` → Target qty `4000` / `EA` → Production order ref `PO-2026-4472` → **Create**.
2. **Issue** → **Start** (§11.1-11.2, roles unchanged).
3. `ddcp.operator` → sidebar → `/ddcp` → ટોચે "Product family" = **Prefilled syringe / injectable** (default) → "Execution & result records" tab:
   - Op 1 (×2): Constituent handoff — Batch `MJ-PFS-B-2701` (manual paste, §21.4 જુઓ), Drug/`bulk_drug`/lot `LOT-DRUG-2701`; Device/`needle`/lot `LOT-DEV-2701`.
   - Op 2 (×2): Accept બંને (Profile dropdown = `PFS-MERIDIJECT-001 v1`).
   - Op 3: Fill start — Batch `MJ-PFS-B-2701`, Profile `PFS-MERIDIJECT-001 v1`, Line/area **`AREA-GRADE-A`** *(§21.1 ની correction — જૂનો doc ભૂલથી `LINE-PFS-01` ને area field માં પણ વાપરતો હતો; `LINE-PFS-01` equipment asset છે, area નથી — `equipment.equipment_areas` માં એ code exist જ નથી કરતો)*, Filler equipment `LINE-PFS-01`, Fill program `PROG-FILL-001`/`1`, Target fill `1.000000`/`mL`, Cycle group `CYCLE-B`.
   - Op 7: Production count — Batch `MJ-PFS-B-2701`, `FILLED`/`MANUAL`/`4000`/`EA`, Source event ID `EVT-COUNT-2701-01`.
   - Op 6: Complete fill — Machine count end `4000`.
   - Op 8: Device assembly — Batch `MJ-PFS-B-2701`, `Needle install`, Component lot `LOT-DEV-2701`, Unit identifier `MJ-UNIT-2701-0001`, Equipment `LINE-PFS-01`, Result `Pass`.
   - Op 9: `ddcp.operator2` login → Independently verify Op 8's record (IND-001 — same-user attempt fails first, live demo moment, §12 ના જ pattern).
   - Op 10: Functional test — Batch `MJ-PFS-B-2701`, `CCI`, QC result ref (`/qc` નો કોઈ result — ના હોય તો ખાલી છોડી શકાય, field required નથી ref હોવા છતાં backend JSONB free-form ચેક કરે છે), Result `Pass`.

#### 21.3.3 ⚠️ Honest નોંધ — Op 4 (Fill IPC) અત્યારે real acceptance rule વગર **fail થશે**

`FILL-WEIGHT-RULE-01` (જૂના doc નો ડેમો ડેટા) **ક્યારેય DB માં બન્યો જ નથી** — `acceptance_rule_id` field ખરેખર `ruleSelect` dropdown છે (`GET /rules/v1` માંથી), free text નથી. Live DB માં ફક્ત 2 non-draft rule છે: `SMOKE-ASSAY` (eligibility) અને `yield_percent` (CALCULATION, ને 1 જ historical evaluation `ERROR` outcome સાથે). કોઈ પણ ફિલ-વેઇટ/ડોઝ/ક્લોઝર/કોટિંગ-ટોલરન્સ rule હજુ author+release નથી થયો.

**અસર:** Op 4 (fill IPC), autoinjector ના dose-delivery, inhalation ના crimp/closure, coated-device ના drug-loading — આ **બધા rule-evaluated ops** dropdown માં ખાલી અથવા mismatched rule જ બતાવશે; `yield_percent` પસંદ કરીને submit કરશો તો ઈનપુટ-કોન્ટ્રાક્ટ mismatch ને લીધે evaluation error આવવાની શક્યતા છે (code-verified: આ rule CALCULATION type છે, fill-weight acceptance-check નથી).

**સાચી રીત (roadmap, guessed નથી):** `/rules` (Document 22, `rules.author`/`rules.release` permission) પર જઈને એક ખરેખરો fill-weight tolerance rule (દા.ત. `rule_id = FILL-WEIGHT-RULE-01`, `rule_type = eligibility` અથવા યોગ્ય પ્રકાર, target `1.000 mL ± 5%` જેવો tolerance) draft → validate → release કરવો પડશે, પછી જ Op 4 ને real acceptance rule મળશે. આ પોતે client/QA ની ટેકનિકલ નિર્ણય (tolerance value) છે — CLAUDE.md §4 પ્રમાણે guess નથી કરવાનું, `docs/generated/18_SPEC_GAPS.md` માં નવો SPEC_GAP તરીકે record કરવા યોગ્ય. **Op 4-9 વગર પણ Op 1/2/3/6/7/8/9/10/11 (rule-evaluated ના હોય એવા) સંપૂર્ણ ચાલશે** — batch readiness ના blocker rule-evaluated ops પર depend નથી કરતા (§15.1 ના 4 blocker rule-independent છે).

#### 21.3.4 Phase 9 ફરી — નવો deviation (§13 ના fields, નવો data)

`operator1` → `/deviations` → Create → `deviation_number = DEV-2026-0201`, `source_type = batch`, Source record dropdown → `MJ-PFS-B-2701`, severity/type — બાકી §13 ના જ ટેબલ પ્રમાણે (Triage → Contain → Investigation → Impact → Disposition (સહી) → Close (સહી)).

#### 21.3.5 Phase 10 — Line Clearance (પહેલી વાર ખરેખર execute — live DB માં 0 row હતા)

`sanitation.operator` → `/line-clearance` → area = **`AREA-GRADE-A`** (or `AREA-FILL-SUITE-2`, બંને ISO-classified cleanroom/fill-suite છે — client ના real layout પ્રમાણે client નક્કી કરે) → Start → Complete (સહી). આ platform પર પહેલી real line-clearance execution હશે (`equipment.cleaning_executions` હાલ 0 row) — §15.1 ના `LINE_NOT_READY` blocker ને hands-on ચકાસવાની સાચી તક.

#### 21.3.6 Phase 11 + 12 — Readiness, Freeze, QA Review, Release (§15/§16, નવો batch)

બધું §15/§16 પ્રમાણે જ, batch = `MJ-PFS-B-2701`, profile = `PFS-MERIDIJECT-001 v1`. Op4 ના rule gap (§21.3.3) ને લીધે fill operation `HOLD` state માં અટકે તો પણ **§15.1 ના blocker ચેક એને directly નથી જોતા** — production count (Op 7) + constituent handoff (Op 1/2) જ ચેક થાય છે, એટલે readiness છતાં pass થવી જોઈએ; ફક્ત fill operation પોતે `COMPLETE` ના થઈ શકે જ્યાં સુધી rule gap ઠીક ના થાય (§21.3.3 ના Op 6 ને પણ અસર કરે — `complete_filling_stage()` ને ≥1 `FILLED` count જોઈએ, rule hold નહીં, એટલે **Op 7 પહેલાં કર્યું હોય તો Op 6 ચાલશે**, ક્રમ ઊલટાવવો પડે — ઉપર 21.3.2 માં Op 7 ને Op 6 પહેલાં જ મૂક્યું છે, ધ્યાન રાખવું).

### 21.4 DDCP ↔ Batch — કેવી રીતે "compatible" છે (સીધો જવાબ)

**Database level — હા, સીધું જોડાયેલા છે:** DDCP ના દરેક execution table (`constituent_handoff`, `fill_operation`, `device_assembly_record`, વગેરે — §12.0 ની table) `batch_id` column થી `ebmr.gxp_batch` (એ જ table જે `/batch-execution` વાપરે છે) ને directly point કરે છે — migration `0090` પછી (§19 #27) આ **એક જ, unified** batch store છે, 2 જુદા table નથી.

**UI/Navigation level — ના, કોઈ automatic link નથી (નવું finding, §19 #33):**

| | |
|---|---|
| `/batch-execution` થી `/ddcp` પર જવું | કોઈ button/link નથી. Batch ID plain, selectable UUID text તરીકે batch detail પર દેખાય (copy-button નથી) — manually select/copy કરવું પડે |
| `/ddcp` પર એ batch ID વાપરવું | Sidebar → `/ddcp` → સાચી "Product family" જાતે પસંદ કરવી (batch ના product પરથી auto-detect નથી થતું) → "Batch readiness" કે "Execution" tab ના Batch field માં UUID paste કરવું |
| URL query param | કોઈ `?batch_id=` સપોર્ટ નથી — બંને દિશામાં |
| Progress sync | §12.0 એ પહેલેથી કહ્યું છે — Batch Execution ના generic step complete/DDCP execution ops **એકબીજાને touch જ નથી કરતા** (SG-180 open) |

**વ્યવહારુ (practical) સલાહ:** Batch create/issue/start (§11) પછી, batch ID copy કરીને note કરી રાખવો (દા.ત. `MJ-PFS-B-2701` ની સાથે UUID) — DDCP execution tab (§12/§21.3.2) અને readiness tab (§15) બંનેમાં એ જ UUID manually paste કરવાનો રહેશે, દરેક વખતે.

---

## 22. 2026-09-17 Update — Release હવે Production Complete માંગે છે + CAPA data

**⚠️ પ્રામાણિકતા નોંધ:** આ section fresh code-verified છે (2026-09-17) — batch/deviation/lot/receipt number
(`MJ-PFS-B-2701`, `DEV-2026-0201`, `LOT-DRUG-2701`, `LOT-DEV-2701`, `RCPT-DRUG-2701`, `RCPT-DEV-2701`)
હજુ **DB માં વપરાયેલા નથી** (2026-09-17 ના રોજ ફરી ચકાસેલું — §21 ના Round 2 cycle લખાયો ત્યારે 2026-09-16
ના રોજ ફ્રેશ હતા, હજુ પણ છે) — master data (`MERIDIJECT-PFS` v1, `RCP-MJ-PFS-V1` v1, `PFS-MERIDIJECT-001`
v1, `AREA-GRADE-A`) બધું RELEASED/active confirm કર્યું. **આ section ફક્ત data reference છે — batch/
DDCP/deviation/CAPA તમે પોતે browser માંથી manually ચલાવવાના છે, કંઈ પણ auto-run/pre-create નથી કરેલું.**

### 22.1 SG-180 reopened — Release હવે "manufacturing completeness" ચેક કરે છે

**શું બદલાયું:** આ જ session માં, live testing દરમિયાન એક batch (`MJ-PFS-B-0000`, અલગ recipe) 3/9 step
પૂરા હોવા છતાં review+release થઈ ગયો — આ §21.4 (SG-180) નું જ, પહેલેથી-documented, 2026-09-11 ના રોજ
project-owner દ્વારા **જાણી-જોઈને decline કરેલું** behavior હતું (write-side auto-sync signature-policy
conflict ને લીધે ના બનાવ્યું). આજે ફરી પુછતાં project owner એ **હવે hard gate ઉમેરવાનું** પસંદ કર્યું:
`evaluate_eligibility()` (`app/modules/release/service.py`) હવે `batch.state != "production_complete"`
હોય તો `PRODUCTION_NOT_COMPLETE` (CRITICAL) blocker ઉમેરે છે — "Evaluate eligibility" અને final "Release"
બંને પર (એ જ function ફરી call થાય છે).

**⚠️ આ §21 ના scenario માટે ખાસ અગત્યનું:** આ નવો gate **ફક્ત generic `gxp_batch_step` ચેઇન** વાંચે છે
(`/batch-execution`ના પોતાના "Production Complete" બટન જે already ચેક કરે છે, એ જ) — DDCP ના પોતાના
execution table (`constituent_handoff`/`fill_operation`/વગેરે) **નથી** વાંચતો (SG-180 નો બીજો, હજુ ખુલ્લો
અડધો ભાગ — §21.4 માં જ "Progress sync" row). એટલે **ફક્ત §21.3.2 ના DDCP ops પૂરા કરવાથી Release eligible
નહીં થાય** — batch નું પોતાનું generic step પણ `/batch-execution` પર Complete + Production Complete
કરવું જ પડશે.

**સારા સમાચાર:** `RCP-MJ-PFS-V1` **v1** (§21.3.2 જે વાપરે છે) માં **ફક્ત 1 જ** generic step છે —
`FILL-01` — 9-step recipe (બીજા doc, `Batch_Create_Execution_Process_Guide_Gujarati.md` §16 ની v4) નહીં.
Real, code-verified field data (2026-09-17):

| Field | Value |
|---|---|
| Step code | `FILL-01` (`weigh` type, required role `Operator`, critical) |
| Record results — parameter | `FILL_WEIGHT_MG` — decimal, `mg`, target `1000`, range `950`–`1050` (required) |
| Link evidence — requirement | `photo` ×1 (allowed types `image/jpeg`, `image/png`) |
| Material requirement (display-only, §17 ના જ honest gap) | Drug spec, target `1.05 mL`, range `1.00`–`1.10`, `full_container` |
| Equipment requirement (display-only) | `FILLING_LINE` (કોઈ calibration/qualification/cleaning ફરજિયાત નથી) |

**Steps (`/batch-execution`, `operator1`/`ChangeMe123!`, §11.3/§11.3.1 ના જ button pattern) — §21.3.2 ના
step 1-2 (Create → Issue → Start) પછી:**

1. `FILL-01` row → **Start**.
2. **Record results** → `FILL_WEIGHT_MG` = `1002` (in range) → submit (signed).
3. **Link evidence** — 2026-09-17 થી (SG-204) `operator1` હવે આ પોતે, એ જ session થી કરી શકે (પહેલા
   Operator role `evidence.upload`/`.download` ધરાવતો નહોતો, ફક્ત Admin/QA Reviewer): sidebar →
   **Platform ops → Evidence operations** → "Stage an evidence upload" (Owner type `batch_step`, Owner
   = આ batch → `FILL-01` step — 2-level dropdown, raw UUID paste નહીં — Filename કોઈ પણ, Mime type
   `image/jpeg`, File કોઈ પણ real image, Reason free text) → Finalize (એ જ પેજ પર). પછી પાછા
   `/batch-execution` → `FILL-01` row → **Link evidence** → dropdown માંથી હમણાં staged evidence પસંદ
   કરો (SHA-256/media type auto-fill) → Requirement code = `photo` → Submit.
4. `FILL-01` row → **Complete** (signed).
5. Batch action row → **Production Complete** (signed) — હવે જ `batch.state = production_complete` થાય.

આ 5 પગલાં પછી જ `/release` પર "Evaluate eligibility" 0 blocker બતાવશે (ધારીને કે QA review પણ complete
છે અને Vault snapshot integrity બરાબર છે, §16 પ્રમાણે જ).

### 22.2 CAPA — §21.3.4 ના deviation પરથી (આ guide માં પહેલા ક્યારેય નહોતું)

§21.3.4 batch `MJ-PFS-B-2701` પર deviation `DEV-2026-0201` બનાવે છે, Disposition+Close સુધી ચલાવે છે.
CAPA એ deviation પરથી જ બને — batch ને સીધું નહીં (chain: Batch → Deviation → CAPA,
`Batch_Create_Execution_Process_Guide_Gujarati.md` §13 જુઓ, code-verified
`app/modules/qms/capa_commands.py` સામે). Field reference (`/capa`, `qa.reviewer` login,
`capa.create`):

| Field | આ scenario માટે Value |
|---|---|
| `source_type` | `deviation` |
| `source_id` | §21.3.4 ની deviation — dropdown, `DEV-2026-0201` |
| `problem_statement` | `Fill weight recorded near the low tolerance boundary on batch MJ-PFS-B-2701 — recurring pattern under investigation` |
| `root_cause_ref` અથવા `proactive_rationale` | ઓછામાં ઓછું 1 ફરજિયાત — દા.ત. `root_cause_ref = "Filler pump wear identified during DEV-2026-0201 investigation"` |
| `risk_class` | dropdown — તમારા site ના risk matrix પ્રમાણે (દા.ત. `MEDIUM`) |
| `owner_subject_id` | કોઈ user — દા.ત. `qa.reviewer` પોતે અથવા `supervisor1` |
| `target_date` | ભવિષ્યની કોઈ પણ date, દા.ત. `2026-10-15` |

**Create** પછી: **Action** (`capa.action.add`/`.complete`) — દા.ત. 1 action "Replace filler pump wear
component", owner `supervisor1`, પછી Complete mark કરો. **Effectiveness check** (`capa.effectiveness`)
અને **Close** (`capa.close`) — બંને QA Reviewer/Releaser level permission, §13 ના જ ટેબલ પ્રમાણે.

**⚠️ CAPA Release ને block નથી કરતું** — Deviation ની જેમ જ (§13 નો જ honest note) — chain traceability
માટે છે, automatic blocker નથી. Release eligibility ફક્ત §22.1 નો production-complete gate + QA review
+ Vault integrity ચેક કરે છે (§8/§16 પ્રમાણે જ).

---
