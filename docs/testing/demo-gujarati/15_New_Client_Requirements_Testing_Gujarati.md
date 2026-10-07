## ૧૫. નવા Client Requirements — Manual Browser Testing Guide (Gujarati)

> **હેતુ:** આ ડોક્યુમેન્ટ ફક્ત આ છેલ્લા session માં ઉમેરાયેલા/બદલાયેલા **૧૧ features** ને browser માંથી
> manually test કરવા માટે છે (client એ આપેલ ૧૨-point gap list માંથી — #૫ પહેલેથી જ system માં યોગ્ય
> રીતે કામ કરતું હોવાથી કંઈ બદલાયું નથી, એ પણ નીચે અલગથી સમજાવેલ છે).
>
> **જરૂરી:** Browser માં app ખોલો, પછી નીચે આપેલ સંબંધિત username થી login કરો.
> **Password બધા user માટે સરખો:** `ChangeMe123!`
>
> દરેક section માં: શું બદલાયું → કયા page પર → કયા login થી → step-by-step શું કરવું →
> શું result આવવો જોઈએ (expected result).

---

### Login Reference (આ ડોક્યુમેન્ટ માટે જરૂરી Users)

| Username | Role | આ guide માં ક્યાં વપરાય છે |
|---|---|---|
| `admin` | Admin | Product/Recipe code, "+ Add new UOM", Batch record |
| `process.engineer` | Process Engineer | Material/Supplier code, Material storage fields |
| `equipment.admin` | Equipment Administrator | Equipment asset/area code |
| `calibration.tech` | Calibration Technician | Internal/External calibration, Recalibration due date |
| `maintenance.tech` | Maintenance Technician | Breakdown maintenance, Actual downtime |
| `operator1` | Operator | Equipment Documents upload, Material lot storage fields |
| `qa.releaser` | QA Releaser | QC Testing Incomplete blocker (Release) |
| `qa.reviewer` | QA Reviewer | QC Testing Incomplete blocker (QA Review) |

---

## ૧૫.૧ — Unique Code: Auto Generate vs Manual Entry (Requirement #૧)

**શું બદલાયું:** Material, Equipment (asset + area), Product, Recipe, Supplier — આ પાંચેય જગ્યાએ Code
field હવે **Auto / Manual** — બે button સાથે આવે છે. **Auto** પસંદ કરો તો field disabled થઈ જાય છે
અને "Will be assigned on save" લખેલું દેખાય છે — save કર્યા પછી system જાતે
`MAT-000123` / `EQP-000045` / `PRD-000012` / `RCP-000007` / `SUP-000003` જેવો code બનાવે છે.
**Manual** પસંદ કરો તો પહેલાની જેમ જાતે code type કરી શકાય છે (અને duplicate code હોય તો error આવે છે).

**Test ૧ — Material (`/materials`, login: `process.engineer`)**

1. **Materials** page ખોલો → **New material** button click કરો.
2. Modal માં "Code" field પાસે **Auto** / **Manual** — બે button દેખાશે (default: Auto).
3. **Auto** પસંદેલું રાખો, "Will be assigned on save" hint દેખાય છે એ ચેક કરો.
4. Name: `Test Material Auto 1`, UOM: `kg` ભરો → **Create material** click કરો.
5. ✅ **Expected:** નવું material list માં `MAT-` થી શરૂ થતાં code સાથે દેખાવું જોઈએ (દા.ત. `MAT-000015`).
6. ફરીથી **New material** ખોલો → આ વખતે **Manual** click કરો → Code માં જાતે `TEST-MANUAL-01` ટાઈપ કરો
   → Name/UOM ભરીને save કરો.
7. ✅ **Expected:** Material `TEST-MANUAL-01` code સાથે જ બને છે.
8. એ જ code (`TEST-MANUAL-01`) થી ફરી એક material બનાવવાનો પ્રયત્ન કરો.
9. ✅ **Expected:** Error આવવો જોઈએ — "Material code already exists for this site".

**Test ૨ — Equipment Asset / Area (`/equipment`, login: `equipment.admin`)**

1. **Equipment** page → **New equipment asset** → Code પાસે Auto/Manual જુઓ → Auto રાખી Manufacturer/
   Model ભરી Create કરો.
2. ✅ **Expected:** નવો asset `EQP-0000xx` code સાથે બને છે.
3. એ જ રીતે **New equipment area** માં પણ Auto/Manual ચેક કરો (`ARE-000xx` code બનશે).

**Test ૩ — Product / Recipe / Supplier**

- `/product-master` (login: `admin` અથવા `process.engineer`) → **New product draft** → "Product code"
  field Auto રાખો → **ફક્ત Version 1 draft માટે જ auto-generate થાય છે** (later version એ જ product ના
  પહેલા version નો code reuse કરે છે, hint માં લખેલું છે).
- `/recipe-master/new` (login: `admin`) → "Recipe code" Auto રાખો → **ફક્ત નવી recipe family માટે જ**
  auto-generate થાય છે.
- `/suppliers` (login: `process.engineer`) → **Register a supplier** → "Supplier code" Auto/Manual ચેક
  કરો.

---

## ૧૫.૨ — Centralized UOM Dropdown + "Add New UOM" (Requirement #૨/#૩)

**શું બદલાયું:** Material, Material Lot, Material Receipt, Dispensing, Batch Execution, QC, Yield,
Product Master, Inventory, Recipe Master — બધે UOM field હવે **free text નથી**, real dropdown છે જે
released UOM list (`rules.gxp_uom`) માંથી જ પસંદ કરવા દે છે. Dropdown ની નીચે authorized user માટે
**"+ Add new UOM…"** option પણ છે.

**Test ૧ — Dropdown enforced છે (`/materials`, કોઈપણ login)**

1. **New material** modal ખોલો → "Unit of measure" field પર click કરો.
2. ✅ **Expected:** Free-text box નથી — એક dropdown list ખૂલે છે જેમાં `kg (MASS)`, `g (MASS)`,
   `mg (MASS)`, `L (VOLUME)`, `mL (VOLUME)`, `mm (LENGTH)`, `each (COUNT)`, `EA (COUNT)`, `unit (COUNT)`
   જેવા options દેખાય છે.
3. `kg` પસંદ કરો → material create કરો → list માં UOM column માં `kg` દેખાવું જોઈએ.

**Test ૨ — Inline "Add new UOM" (login: `admin` — કારણ કે Admin પાસે જ UOM author + release બંને
permission છે)**

1. કોઈપણ UOM dropdown ખોલો (દા.ત. `/materials` → New material → Unit of measure) → સૌથી નીચે
   **"+ Add new UOM…"** option click કરો.
2. Modal ખૂલશે — ભરો: Code: `oz`, Dimension: `MASS`, Base unit: `kg`, Factor: `0.0283495`,
   Offset: `0`, Precision (dp): `4` → **Create** click કરો.
3. ✅ **Expected:** કારણ કે `admin` પાસે release permission પણ છે, સીધું **Release** signature screen
   ખૂલશે — Password (`ChangeMe123!`) નાખી **Sign & submit** કરો.
4. ✅ **Expected:** UOM dropdown માં હવે `oz` પસંદ થયેલો દેખાય છે, અને ફરી dropdown ખોલો તો `oz` list
   માં ઉમેરાયેલો દેખાય છે.
5. **જો `process.engineer` જેવા user થી login કરો** (જેની પાસે release permission નથી) → એ જ પ્રમાણે
   નવો UOM બનાવો → ✅ **Expected:** "This creates a draft. It becomes selectable everywhere once an
   authorized reviewer releases it." — એવો message દેખાય, અને એ code હજુ dropdown list માં ના દેખાય
   (draft state માં, released state માં નહીં) જ્યાં સુધી `admin`/`rules.release` વાળો user `/rules`
   page પરથી release ના કરે.

**Test ૩ — ખોટો/જૂનો UOM code reject થાય છે (backend check, Postman/curl વગર પણ browser Network
tab થી ચકાસી શકાય)**

- Browser DevTools ખોલી કોઈ material create ની API call ના body માં `"uom": "not-a-real-unit"` મોકલવાનો
  પ્રયત્ન કરો (અથવા frontend dropdown સિવાય કોઈ રીતે અજાણ્યો code ના જ મોકલી શકાય — એ જ મુખ્ય મુદ્દો
  છે: **UI હવે ખોટો UOM મોકલી જ ના શકે**).

---

## ૧૫.૩ — Material Storage Location અને In-House Flag (Requirement #૪)

**શું બદલાયું:** Material Master માં **"In-house"** flag અને **"Default storage condition"**
ઉમેરાયા; Material Lot (Receive તથા Receipt Examine — બંને જગ્યાએ) માં **Storage condition** અને
**Storage location** ઉમેરાયા.

**Test ૧ — Material Master (`/materials`, login: `process.engineer`)**

1. **New material** ખોલો → Name/UOM ભર્યા પછી નીચે **"Default storage condition"** dropdown
   (`ambient`, `cold_storage`, `freezer`, `refrigerator`, `controlled_temperature`, `warehouse`) અને
   **"Manufactured/maintained in-house"** checkbox દેખાય છે.
2. Storage condition: `cold_storage` પસંદ કરો, in-house checkbox **✔** કરો → Create કરો.
3. List માં નવી "Storage" column માં `In-house · cold_storage` દેખાવું જોઈએ.
4. Edit કરીને storage condition `freezer` માં બદલો → save કરો → column update થવો જોઈએ.

**Test ૨ — Material Lot Receive (`/material-lots`, login: `operator1`)**

1. **Receive lot** button click કરો → Material પસંદ કરો (જેમાં Default storage condition set કરેલો
   છે) → ✅ **Expected:** "Storage condition" field આપોઆપ material ના default થી ભરાય છે (દા.ત.
   `freezer`).
2. "Storage location" dropdown ખોલો → seeded locations (`QUARANTINE-01`, `RELEASED-01`,
   `REJECTED-01`) દેખાવા જોઈએ → એક પસંદ કરો.
3. Internal lot number, Quantity ભરી lot receive કરો.
4. List/table માં નવી "Storage" column માં પસંદ કરેલો storage condition દેખાવો જોઈએ.

**Test ૩ — Material Receipt → Examine (`/material-receipts`, login: `operator1`)**

1. નવો receipt create કરો → **Examine receipt** ખોલો.
2. Visual checks (Identity confirmed = Yes, બાકી બધા No) ભરો, Internal lot number આપો.
3. નીચે "Storage condition" અને "Storage location" dropdown દેખાય છે — ભરો → **Examine receipt**
   submit કરો.
4. ✅ **Expected:** Clean examination પર lot બને છે (quarantine માં) અને એમાં આપેલો storage
   condition/location save થયેલો `/material-lots` પર જઈને ચકાસી શકાય.

---

## ૧૫.૪ — Equipment Documentation (Requirement #૬)

**શું બદલાયું:** દરેક Equipment Asset ના detail page પર નવો **"Documents"** tab ઉમેરાયો — spec sheet,
manual, SOP/WI, IQ/OQ, calibration certificate, vendor document, drawing વગેરે upload/download કરી
શકાય છે.

**Steps (login: `operator1`, page: `/equipment` → કોઈપણ asset ખોલો → `/equipment/[id]`)**

1. Asset detail page ખોલો → Tabs માં **Calibrations, Maintenance, Use log, Eligibility** પછી નવો
   **Documents** tab દેખાવો જોઈએ → click કરો.
2. **Upload document** button click કરો.
3. "Document type" dropdown ખોલો → options ચેક કરો: Spec sheet, Operating/maintenance manual,
   SOP / WI, IQ/OQ, Calibration certificate, Vendor document, Drawing, Other.
4. `Calibration certificate` પસંદ કરો → કોઈ પણ PDF/image file પસંદ કરો → Reason (optional) → **Upload**.
5. ✅ **Expected:** Upload પછી table માં નવો row દેખાય: Type = "Calibration certificate", Filename,
   State = `FINALIZED`, Uploaded date.
6. એ row ની **Download** button click કરો → ✅ **Expected:** File સાચી રીતે browser માં download થાય.

---

## ૧૫.૫ — Internal vs External Calibration (Requirement #૭)

**શું બદલાયું:** Calibration record માં હવે **Calibration type: Internal/External** પસંદ કરવાનું
છે. External પસંદ કરો તો **Provider name** (required) અને **Certificate reference** field ખૂલે છે.

**Steps (login: `calibration.tech`, page: `/equipment/[id]` — qualified equipment asset)**

1. Asset detail → **Record calibration** action ખોલો.
2. Performed date, Next due date, Result ભરો.
3. નીચે **"Calibration type"** dropdown દેખાય: `internal` / `external`.
4. `internal` રાખીને submit કરો → ✅ **Expected:** સફળતાપૂર્વક save થાય, Provider fields ના પૂછાય.
5. ફરીથી calibration record કરો → આ વખતે **`external`** પસંદ કરો.
6. ✅ **Expected:** "Provider name" (required) અને "Certificate reference" field તરત દેખાય.
7. Provider name ખાલી રાખીને submit કરવાનો પ્રયત્ન કરો → ✅ **Expected:** Error — "provider_name is
   required for an external calibration".
8. Provider name: `Acme Calibration Services`, Certificate reference: `CERT-2026-001` ભરીને submit
   કરો → ✅ **Expected:** Save થાય છે.
9. Calibration history માં નવો row External + Provider name/Certificate સાથે દેખાવો જોઈએ.

---

## ૧૫.૬ — Recalibration: Next Due Date Auto-Calculate (Requirement #૮)

**શું બદલાયું:** Calibration form માં "Frequency (days)" ભરો તો system **Performed date +
Frequency days** પરથી next due date જાતે calculate કરીને બતાવે છે, અને એ જ asset ના
"next calibration due date" તરીકે save કરે છે (caller એ manually type કરેલી "Next due date" ને
override કરીને).

**Steps (login: `calibration.tech`)**

1. **Record calibration** ખોલો → Performed date: આજની તારીખ → Result: `pass`.
2. "Frequency (days)" field માં `90` ટાઈપ કરો.
3. ✅ **Expected:** તરત જ field ની નીચે hint માં "Next due (calculated): <date>" દેખાય — એ date
   Performed date + 90 days બરાબર હોવી જોઈએ.
4. Submit કરો → Asset detail ના top FactGrid માં "Calibration due" તારીખ એ જ calculated date
   દેખાવી જોઈએ (manually type કરેલી "Next due date" field ની કિંમત નહીં).
5. History (calibration list) એ જ પુરાણા calibration records સાચવે છે — નવો record ઉમેરાય છે, જૂનો
   ડિલિટ/overwrite નથી થતો.

---

## ૧૫.૭ — Breakdown Maintenance Type (Requirement #૯)

**શું બદલાયું:** Maintenance Type dropdown માં **"breakdown"** નવો option ઉમેરાયો (Planned,
Corrective ની સાથે) — breakdown પસંદ કરો તો equipment તરત જ **Hold** માં જાય છે (Out of service).
Maintenance complete કરતી વખતે **"Actual downtime (hours)"** field પણ ઉમેરાયું છે.

**Steps (login: `maintenance.tech`)**

1. Equipment asset detail → **Record maintenance** ખોલો.
2. "Type" dropdown ખોલો → ✅ **Expected:** `planned`, `corrective`, `breakdown` — ત્રણેય options
   દેખાય.
3. `breakdown` પસંદ કરો, Fault description: `Sudden pump failure` ભરીને submit કરો.
4. ✅ **Expected:** Asset ની state તરત **OUT_OF_SERVICE** થાય છે અને top પર Hold banner દેખાય છે
   (બરાબર `corrective` જેવું જ behavior).
5. Maintenance tab માં નવો work order "breakdown" type સાથે દેખાય છે → **Complete maintenance**
   button click કરો.
6. Modal માં "Work performed" ની નીચે નવું **"Actual downtime (hours)"** field દેખાય છે
   (hint માં Expected downtime પણ દેખાય જો entry સમયે ભરેલું હોય).
7. Actual downtime: `6.5` ભરો, "Post-maintenance verification complete" ✔ કરો → submit કરો.
8. ✅ **Expected:** Work order "verified" થાય, asset state VERIFICATION માં જાય, અને work order ની
   વિગતોમાં Actual downtime = `6.5 h` દેખાય.

---

## ૧૫.૮ — QC Testing Incomplete: Release/Review Block (Requirement #૧૦)

**શું બદલાયું:** પહેલા release/QA review ફક્ત **fail થયેલા** QC result પર જ block થતું હતું. હવે જો
કોઈ release-blocking QC test order **હજુ પૂરો જ ના થયો હોય** (result જ ના આવ્યો હોય, review ના
થયું હોય) તો પણ નવો blocker **`QC_TESTING_INCOMPLETE`** આવે છે.

**આ ચકાસવા માટે (સહેલો રસ્તો — existing running batch પર):**

1. `/qc` page ખોલો (login: `qc.reviewer` અથવા `admin`) → કોઈ પણ batch માટે એક નવો QC Test Order
   બનાવો (Sample → Test order) પણ **result record ના કરો / review ના કરો** (order ને `created` /
   `in_progress` state માં જ રહેવા દો).
2. `/release` page ખોલો (login: `qa.releaser`) → એ જ batch માટે release evaluate કરો.
3. ✅ **Expected:** Blockers list માં નવો code **`QC_TESTING_INCOMPLETE`** દેખાય (અગાઉ ફક્ત
   `QC_RESULT_FAILED`/`OPEN_OOS` જ દેખાતા).
4. `/qa-review` page (login: `qa.reviewer`) → એ જ batch ની QA Review package ની Exceptions list માં
   પણ "QC test order ... has not reached a reviewed/terminal state" — એવો message દેખાય.
5. હવે QC page પર જઈને એ test order ને result record કરી **Review** કરી દો (state `reviewed` થાય).
6. Release/QA Review ફરી evaluate કરો → ✅ **Expected:** `QC_TESTING_INCOMPLETE` blocker હવે નથી
   દેખાતો.

---

## ૧૫.૯ — Required In-Process QC Test per Recipe Step (Requirement #૧૨)

**શું બદલાયું:** હવે Recipe ના કોઈ step માટે specific **in-process QC test** ને "required" તરીકે
declare કરી શકાય છે. Batch execution વખતે એ step **complete ના થઈ શકે** જ્યાં સુધી એ QC test નું
result **pass** ના આવે.

**Test ૧ — Recipe માં QC requirement ઉમેરવું (`/recipe-master/new`, login: `admin`)**

1. નવો recipe draft બનાવવાનું શરૂ કરો (Product પસંદ કરો, Recipe code Auto રાખો).
2. કોઈ step ના editor માં scroll કરો → નવો section દેખાશે:
   **"Required in-process QC test(s) before this step can be completed"**.
3. **"+ Add QC requirement"** click કરો → dropdown માંથી કોઈ released, in-process QC specification
   પસંદ કરો (dropdown ખાલી હોય તો પહેલા `/qc` page પર જઈને એક in-process QC specification
   create + release કરવી પડશે) → "Required" checkbox ✔ રહેવા દો.
4. Recipe draft save કરો, submit → release કરો.

**Test ૨ — Batch Execution માં Gate ચકાસવું (`/batch-execution`, login: `operator1`)**

1. એ recipe થી નવો batch create/issue/start કરો → જે step પર QC requirement ઉમેર્યું હતું એને
   Start કરો.
2. Result વગેરે record કરીને **Complete** button click કરો (QC test result record કર્યા વગર).
3. ✅ **Expected:** Error — "Required in-process QC test(s) have not reached a passing result" —
   step complete ના થાય.
4. હવે `/qc` page પર જઈને એ જ step માટે (source type: batch step) sample/test order/result બનાવો,
   result outcome = `pass` record કરો.
5. Batch execution પર પાછા આવીને ફરી **Complete** click કરો.
6. ✅ **Expected:** આ વખતે step સફળતાપૂર્વક complete થાય છે.

---

## ૧૫.૧૦ — Batch Record View + PDF (Requirement #૧૧)

> ⚠️ **Update (2026-09-22):** નીચે ના steps ૪-૭ હવે જૂના છે — "Generate PDF" હવે સીધું PDF નથી
> બનાવતું, હવે **QA Releaser signature જરૂરી** છે (SG-137). સાચા updated steps માટે જુઓ
> [doc #૧૬, section ૧૬.૪](16_Gap_Audit_Fixes_Testing_Gujarati.md#૧૬૪--batch-record-pdf-હવે-qa-releaser-sign-કરે-છે-પહેલાં-unsigned-હતું).

**શું બદલાયું:** દરેક batch ના execution modal માં નવું **"Batch record"** button ઉમેરાયું છે — જે
Steps/Results, Material consumption, Equipment used, Deviations, QC results અને Signature/Status
history — બધું એક જ જગ્યાએ બતાવે છે, અને **"Generate PDF"** થી controlled PDF બનાવીને evidence તરીકે
save કરે છે.

**Steps (login: `operator1` અથવા `admin`, page: `/batch-execution`)**

1. કોઈ પણ batch ખોલો (batch list માંથી row click કરીને execution modal ખોલો).
2. Modal ના તળિયે (Close button ની બાજુમાં) નવું **"Batch record"** button દેખાય છે → click કરો.
3. ✅ **Expected:** નવો modal ખૂલે — Steps table (state + results), Materials consumed, Equipment
   used, Deviations, QC results, Status history — બધા sections દેખાય (data ના હોય તો "No ... "
   એવો hint દેખાય, error નહીં).
4. તળિયે **"Generate PDF"** button click કરો.
5. ✅ **Expected:** થોડી second માં "Batch record PDF generated" banner દેખાય, સાથે **Download PDF**
   button.
6. **Download PDF** click કરો → ✅ **Expected:** એક વ્યવસ્થિત formatted PDF download થાય, જેમાં
   Title = "Batch Record — <batch number>", અને ઉપર બતાવેલા બધા sections tables તરીકે હોય.
7. ફરી એ જ batch record modal ખોલો → PDF ફરી generate કરો → **Expected:** આ વખતે પણ નવો evidence
   record બને (દરેક "Generate PDF" click નવો PDF બનાવે, જૂનો delete નથી થતો — evidence trail તરીકે).

---

## ૧૫.૧૧ — Requirement #૫ (Material Receipt → Auto Quarantine): કંઈ બદલાયું નથી

Client એ પૂછેલું કે material receipt accept થાય ત્યારે lot આપોઆપ correct status માં જવો જોઈએ (અને
QA disposition ના થાય ત્યાં સુધી quarantine માંથી release ના થવો જોઈએ). **તપાસ કરતાં ખબર પડી કે આ
પહેલેથી જ સાચી રીતે કામ કરે છે** — તેથી કંઈ code બદલવામાં નથી આવ્યું. Confirm કરવા માટે:

1. `/material-receipts` → નવો receipt બનાવીને **Examine** કરો (બધા visual check "Yes"/clean).
2. ✅ **Expected:** Lot આપોઆપ `/material-lots` માં **status = Quarantine** સાથે બને છે — કોઈ manual
   "transfer to quarantine" step કરવો પડતો નથી.
3. એ lot ને directly "Released" કરવાનો પ્રયત્ન કરો (કોઈ signed disposition વગર) — ✅ **Expected:**
   શક્ય નથી — `qc.reviewer`/`qa.releaser` એ signed **Release/Disposition** action જ કરવો પડે છે.

---

## Summary Checklist (Quick Reference)

| # | Requirement | મુખ્ય Page | મુખ્ય Login |
|---|---|---|---|
| ૧ | Auto/Manual Code | Materials, Equipment, Product Master, Recipe Master, Suppliers | process.engineer, equipment.admin, admin |
| ૨/૩ | UOM Dropdown + Add New | Materials (અને બધે UOM field હોય ત્યાં) | કોઈપણ (Add new UOM માટે admin) |
| ૪ | Material Storage/In-house | Materials, Material Lots, Material Receipts | process.engineer, operator1 |
| ૬ | Equipment Documents | Equipment → asset → Documents tab | operator1 |
| ૭ | Internal/External Calibration | Equipment → asset → Record calibration | calibration.tech |
| ૮ | Recalibration Due Date | Equipment → asset → Record calibration | calibration.tech |
| ૯ | Breakdown Maintenance | Equipment → asset → Record/Complete maintenance | maintenance.tech |
| ૧૦ | QC Testing Incomplete | QC, Release, QA Review | qc.reviewer, qa.releaser, qa.reviewer |
| ૧૧ | Batch Record + PDF | Batch Execution → batch → Batch record | operator1, admin |
| ૧૨ | Step-level QC Gate | Recipe Master (author) + Batch Execution (execute) | admin, operator1 |
| ૫ | (No change — already correct) | Material Receipts → Examine | operator1 |
