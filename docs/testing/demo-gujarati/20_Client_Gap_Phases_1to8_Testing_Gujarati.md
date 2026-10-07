## ૨૦. Client Meeting Gap-Analysis — Phase ૧ થી ૮ — Manual Browser Testing Guide (Gujarati)

> **હેતુ:** ૨૦૨૬-૧૦-૦૩/૦૪ ના client meeting (૧૧ transcripts) માંથી નીકળેલા ૮-Phase plan ના બધા ફેરફાર
> (Phase ૧ થી ૮, બધા **live system પર પહેલેથી જ deploy થયેલા છે**) અહીં manually test કરવા માટે આ
> document છે. દરેક section માં: શું બદલાયું → કયા page પર → કયા login થી → step-by-step real data
> સાથે શું કરવું → expected result.
>
> **આ document doc #૧૫-#૧૯ (સપ્ટેમ્બર ૨૧ ના અલગ ૧૨-point client gap list) થી અલગ છે** — આ ઓક્ટોબર
> ૦૩-૦૬ ની meeting માંથી આવેલા ૮ phases cover કરે છે.
>
> **Password બધા user માટે સરખો:** `ChangeMe123!`
> **Site code:** `T1` (live system માં seeded એક જ site)

---

### Login Reference (આ ડોક્યુમેન્ટ માટે જરૂરી Users)

| Username | Role | આ guide માં ક્યાં વપરાય છે |
|---|---|---|
| `admin` | Admin | Users bulk import, Role Activity checklist |
| `process.engineer` | Process Engineer | Supplier/Material Spec/Product/Equipment authoring |
| `qa.releaser` | QA Releaser | Material Spec/Product release, Calibration approval, Supplier qualification approval |
| `equipment.admin` | Equipment Administrator | Equipment asset create, bulk import |
| `calibration.tech` | Calibration Technician | Calibration recording |
| `maintenance.tech` | Maintenance Technician | Maintenance recording (breakdown/planned) |
| `engineering.manager` | Engineering Manager | Equipment return-to-service |
| `operator1` | Operator | Material Receipt + Examine |

---

### પહેલેથી Seeded Real Data (આ guide માં વાપરવા માટે)

| પ્રકાર | Code | નામ |
|---|---|---|
| Material | `MAT-API-001` | Active Pharmaceutical Ingredient - Metformin (kg) |
| Material | `MAT-EXC-001` | Microcrystalline Cellulose - Excipient (kg) |
| Equipment class | `BALANCE` | Balance |
| Equipment class | `AUTOCLAVE` | Steam Autoclave |

---

## ૨૦.૧ — Bulk User Import: Upload CSV + Column Mapping (Phase ૧ follow-up)

**શું બદલાયું:** પહેલાં "Bulk import" modal માં CSV text જાતે paste કરવું પડતું હતું (ચોક્કસ column
order માં). હવે **file upload** કરો, system તમારી file ના header વાંચીને બતાવે છે, અને તમે દરેક
required field (Full name, Email, Role name, Site code) ને તમારી file ના કયા column સાથે match
કરવું એ **જાતે પસંદ** કરો છો — ગમે તે column order/નામ હોય તો પણ ચાલે. આ જ નવું upload+mapping UI
Equipment (૨૦.૭) અને Product Master (૨૦.૮) ના bulk import માં પણ વપરાયેલું છે.

**Test (`/admin/users`, login: `admin`)**

1. નીચેની content ને `users-sample.csv` નામની file તરીકે તમારા computer પર save કરો:

   ```csv
   full_name,email,role_name,site_code
   Rahul Patel,rahul.patel@example.com,Operator,T1
   Priya Shah,priya.shah@example.com,Supervisor,T1
   ```

2. **Users** page → **Bulk import** button click કરો.
3. "Download a sample CSV" link પણ ચકાસી શકાય (click કરતા browser file download કરે છે).
4. **CSV file** પાસે "Choose File" click કરી ઉપર બનાવેલી `users-sample.csv` પસંદ કરો.
5. ✅ **Expected:** તરત જ "Match each field" screen ખૂલે — "Full name", "Email", "Role name",
   "Site code" — ચાર dropdown દેખાય, અને **Email**/**Role name**/**Site code** આપમેળે (auto-match)
   સાચા column સાથે પસંદ થયેલા દેખાય (કારણ કે તમારી file ના column નામ અને field નામ સરખા છે).
6. **Continue** click કરો → **Preview** click કરો.
7. ✅ **Expected:** બે rows ની table — બંને સામે લીલા રંગમાં **OK** લખેલું.
8. **Import 2 row(s)** click કરો.
9. ✅ **Expected:** "Created 2 user(s)..." message દેખાય, પાછળ list માં નવા ૨ users ઉમેરાયેલા દેખાય
   (`pending_activation` status માં — SMTP ના configured હોવાથી email નહીં જાય, એ expected છે).

**Test ૨ — Column નામ અલગ હોય તો પણ mapping કરી શકાય**

1. આ content વાળી બીજી file બનાવો (column નામ ઈરાદાપૂર્વક અલગ રાખ્યા છે):

   ```csv
   name,email,role,site
   Test MappingUser,test.mapping@example.com,Operator,T1
   ```

2. ફરી **Bulk import** → આ નવી file upload કરો.
3. ✅ **Expected:** "Full name" અને "Role name" dropdown **"— Not in this file —"** દેખાય (auto-match
   ના થયું, કારણ કે "name"/"role" field નામ સાથે બરાબર match નથી થતા) — જ્યારે "Email" auto-match
   થયેલું દેખાય.
4. "Full name" dropdown ખોલી `name` પસંદ કરો, "Role name" dropdown ખોલી `role` પસંદ કરો.
5. **Continue** → **Preview** → ✅ **Expected:** row **OK** દેખાય.
6. **Import** ન કરો તો પણ ચાલે (ફક્ત mapping કામ કરે છે એ ચકાસવા માટે હતું) — **Close** કરી શકાય.

---

## ૨૦.૨ — Role Permission: Activity Checklist (Phase ૨)

**શું બદલાયું:** Role બનાવતી વખતે ૧૨૮ technical permission groups જાતે ટિક કરવાને બદલે, હવે
**૧૫ business-નામ વાળી Activity** (દા.ત. "Material Management", "Equipment & Facilities") નું
checklist છે — એક Activity ટિક કરો એટલે એની નીચેની બધી permissions આપમેળે select થઈ જાય.

**Test (`/admin/roles`, login: `admin`)**

1. કોઈ role ખોલો (અથવા નવો બનાવો) → **Edit permissions** પર જાઓ.
2. ઉપર "Activity checklist" panel દેખાશે — **"Equipment & Facilities"** ટિક કરો.
3. ✅ **Expected:** નીચે technical matrix માં equipment-સંબંધિત બધા module groups આપમેળે expand
   અને select થઈ જાય છે.
4. **"QC Testing & Lab"** પણ ટિક કરો.
5. ✅ **Expected:** પહેલાંનું selection (Equipment) રહે છે, QC permissions પણ ઉમેરાય છે (merge થાય,
   replace નહીં).
6. "Equipment & Facilities" નું ટિક કાઢી નાખો.
7. ✅ **Expected:** ફક્ત Equipment ની permissions જ કાઢી જાય, QC Testing ની રહે.
8. **Save** કરો → page reload કરો → ✅ **Expected:** selection બરાબર એમ ને એમ રહે.

---

## ૨૦.૩ — Supplier: Structured Material Scope + Document Upload (Phase ૩)

**શું બદલાયું:** Supplier Qualification માં material scope હવે free-text નથી — **"Add Material"**
picker થી ચોક્કસ material પસંદ કરી ઉમેરી શકાય. Qualification evidence document પણ હવે real
upload/download (પહેલાં raw vault-id જાતે ટાઈપ કરવો પડતો).

**Test (`/suppliers`, login: `process.engineer`)**

1. **Register a supplier** → Legal name: `Testwell Pharma Chemicals`, Role type: `supplier`,
   Country: `IN` → Create.
2. નવા supplier ને ખોલો → **Start qualification** (અથવા qualification tab) → Risk class: `critical`.
3. Qualification ખુલ્યા પછી **"Add Material"** button દેખાય — click કરી `MAT-API-001` પસંદ કરો.
4. ✅ **Expected:** Material list માં `MAT-API-001 - Active Pharmaceutical Ingredient - Metformin`
   ઉમેરાયેલું દેખાય (free-text ની જગ્યાએ real picker).
5. **Upload document** (જો button દેખાય) → કોઈ પણ નાની file (દા.ત. PDF/image) upload કરો.
6. ✅ **Expected:** Document list માં file નામ સાથે દેખાય, **Download** click કરતા file પાછી મળે.
7. Qualification decision screen પર "Explanation" label દેખાય (પહેલાં "Justification" હતું)
   decision `approved` પસંદ કરો ત્યારે.

---

## ૨૦.૪ — Equipment Calibration Approval Gate (Phase ૪)

**શું બદલાયું:** Calibration "Pass" થવા છતાં, હવે એક **અલગ વ્યક્તિ** (performer સિવાય) એને
**Approve** કરે ત્યાં સુધી equipment "eligible for use" નથી થતું.

**Test (`/equipment`, login steps નીચે)**

1. `equipment.admin` login → **New asset** → Equipment class: `BALANCE`, Computer-operated: `Manual`
   → Create.
2. Asset ને **Qualify** કરો (qualified = Yes).
3. `calibration.tech` login → એ જ asset પર **Calibrate** → Performed date: આજની તારીખ, Result: `Pass`,
   Next due date: ૧ વર્ષ પછીની તારીખ → Submit.
4. ✅ **Expected:** Asset ની "Eligible for use" banner **લાલ/warning** રંગમાં "Not eligible" બતાવે —
   reason: "Most recent calibration has not yet been approved".
5. `calibration.tech` (એ જ performer) થી approve કરવાનો પ્રયત્ન કરો.
6. ✅ **Expected:** Error — approver performer કરતાં અલગ વ્યક્તિ હોવો જોઈએ (SoD).
7. `qa.releaser` login → Calibration tab માં pending calibration **Approve** કરો.
8. ✅ **Expected:** હવે banner **લીલા** રંગમાં "Eligible for use" બતાવે.

---

## ૨૦.૫ — Material Specification: Structured Criteria + Business ID Removal (Phase ૫ Part A)

**શું બદલાયું:** Material Specification draft બનાવતી વખતે **Business ID field હવે નથી** (auto
generate થાય છે, material code પરથી). Test criteria હવે free-text blob ની જગ્યાએ **repeatable rows**
(Test Name / Specification / Acceptance Criteria / Fulfillment Path).

**Test (`/material-specifications`, login: `process.engineer`)**

1. **New draft** → Material: `MAT-API-001` પસંદ કરો.
2. ✅ **Expected:** "Business ID" field ક્યાંય દેખાતું નથી (ફક્ત Material/Name/Site fields).
3. Criteria section માં **Add row**: Test Name: `Assay`, Specification: `98.0 to 102.0%`,
   Acceptance Criteria: `98.0 to 102.0%`, Fulfillment Path: `In-house`.
4. બીજી row ઉમેરો: Test Name: `Appearance`, Fulfillment Path: `Supplier COA`.
5. Save/Create કરો.
6. ✅ **Expected:** detail page પર business id આપોઆપ `MAT-API-001-SPEC` જેવું દેખાય, બંને criteria
   rows table માં દેખાય.
7. `qa.releaser` login → draft **Release** કરો (signature સાથે).
8. ✅ **Expected:** released snapshot માં criteria rows frozen/visible દેખાય.

---

## ૨૦.૬ — Material Receipt/Examine Merge + Service Provider + QC Bridge (Phase ૬)

**શું બદલાયું:** (અ) Receipt બનાવ્યા પછી Examine step **તરત જ** ખૂલે છે (પહેલાં અલગ click કરવો
પડતો). (બ) Damage ચેક હવે "Shipping/package damage" અને "Material container damage" — બે અલગ
પ્રશ્નો. (ક) "Seal Broken" હવે "Seal intact?" — ના પાડો તો reason લખવો ફરજિયાત. (ડ) Supplier ને
હવે "Service Provider" role પણ મળી શકે. (ઇ) Material Specification ના criteria release થાય ત્યારે
પાછળથી QC Testing module માં આપોઆપ draft test બને છે (QA ને manually ફરી type નથી કરવું પડતું).

**Test ૧ — Receipt + Examine merge, નવા fields (`/material-receipts`, login: `operator1`)**

1. **Log a receipt** → Material: `MAT-API-001`, Site: `T1`, Quantity: `100`, UOM: `kg` → Log receipt.
2. ✅ **Expected:** Receipt બન્યા પછી **તરત જ** "Examine receipt" modal ખૂલે છે (list page પર પાછા
   જવું નથી પડતું).
3. "Material matched with PO/Material number": `Yes`, Labeling correct: `Yes`,
   "Shipping/package damage": `No`, "Material container damage": `No`, "Seal intact?": `No`.
4. ✅ **Expected:** "Seal intact?" ને `No` કરતાં જ નીચે **"Seal not intact — explain"** text box
   દેખાય છે, ભર્યા વગર submit button disabled રહે છે.
5. Reason લખો: `Seal appeared loose on arrival`, Internal lot: `LOT-TEST-001` → Submit.
6. ✅ **Expected:** receipt discrepancy_hold state માં જાય (seal_broken ના કારણે).
7. ફરી નવું receipt બનાવી આ વખતે બધા જવાબ `No`/સાચા રાખો (damage/seal બધું clean) → ✅ **Expected:**
   Material Lot બને (quarantine state માં), discrepancy hold ના થાય.

**Test ૨ — Service Provider Supplier (`/suppliers`, login: `process.engineer`)**

1. **Register a supplier** → Legal name: `Precision Calibration Services LLC`,
   **Role type: `service_provider`** (નવો option) → Create.
2. ✅ **Expected:** supplier list માં role "service provider" દેખાય.

**Test ૩ — Equipment Calibration Provider Picker (`/equipment`, login: `calibration.tech`)**

1. કોઈ asset ખોલો → **Calibrate** → Calibration type: `External`.
2. ✅ **Expected:** "Provider" dropdown માં ઉપર બનાવેલ `Precision Calibration Services LLC`
   પસંદ કરી શકાય (હવે free-text ની જગ્યાએ picker, ન મળે તો "type a name" option પણ છે).

---

## ૨૦.૭ — Equipment Enhancements (Phase ૭)

**શું બદલાયું:** (અ) નવું asset બનાવતી વખતે **"Computer-operated or manual?"** પ્રશ્ન ફરજિયાત.
(બ) Breakdown maintenance પછી equipment ને ફરી use કરવા માટે **નવી calibration (recorded + approved)**
જોઈએ — સિવાય કે "Non-critical" ટિક કરેલું હોય. (ક) Planned maintenance ના completion માં
Activity/Result checklist. (ડ) Bulk import હવે file-upload+mapping રીતે (જુઓ ૨૦.૧).

**Test ૧ — Computer-operated પ્રશ્ન (login: `equipment.admin`)**

1. **New asset** → બધા fields ભરો, Equipment class: `BALANCE`.
2. ✅ **Expected:** "Computer-operated or manual?" dropdown ફરજિયાત છે — ખાલી રાખીને submit
   button disabled રહે છે. `Manual` પસંદ કરી Create કરો.

**Test ૨ — Breakdown → Recalibration Required Gate**

1. એ જ asset ને Qualify + Calibrate (Pass) + Approve કરો (૨૦.૪ પ્રમાણે) → Return to service.
2. `maintenance.tech` login → **Record maintenance** → Type: `breakdown`,
   Fault description: `Sudden power failure` → **"Non-critical" ટિક ના કરો** → Submit.
3. ✅ **Expected:** Asset "Recalibration required" fact `Yes` દેખાય.
4. Maintenance **Complete/Verify** કરો.
5. `engineering.manager` login → **Return to service** try કરો.
6. ✅ **Expected:** Block થાય — "RECALIBRATION_REQUIRED" error, "A breakdown requires recalibration
   before this equipment is eligible for use".
7. `calibration.tech` → નવી Calibration record કરો (Pass) → `qa.releaser` → Approve.
8. ✅ **Expected:** હવે "Recalibration required" fact `No` થઈ જાય, Return to service સફળ થાય.

**Test ૩ — Non-critical breakdown gate skip કરે છે**

1. બીજું asset બનાવી ઉપર પ્રમાણે qualify/calibrate/approve/return-to-service કરો.
2. Breakdown maintenance record કરો — આ વખતે **"Non-critical" ટિક કરો**.
3. ✅ **Expected:** "Recalibration required" `No` જ રહે છે, maintenance complete કર્યા પછી સીધું
   Return to service થઈ શકે (નવી calibration વગર).

**Test ૪ — Planned Maintenance Activity Checklist**

1. Record maintenance → Type: `planned` → Submit (work order ખૂલે).
2. એ જ work order ને **Complete/Verify** કરવા ખોલો.
3. ✅ **Expected:** "Activity checklist" section દેખાય — **Add row** કરી Activity:
   `Check belt tension`, Result: `OK` ભરો, બીજી row: Activity: `Lubricate bearings`, Result: `Done`.
4. Verify submit કરો → ✅ **Expected:** work order detail/history માં બંને activity rows સચવાયેલી
   દેખાય.

**Test ૫ — Bulk Equipment Import (upload + mapping)**

1. આ content `equipment-sample.csv` તરીકે save કરો:

   ```csv
   equipment_code,equipment_class_code,manufacturer,model,serial_no,firmware_version,dedicated,is_computer_operated
   ,BALANCE,Mettler Toledo,XPE205,SN-20261006-1,,false,false
   ,AUTOCLAVE,Getinge,GEV-67,SN-20261006-2,v2.1,true,true
   ```

2. **Equipment** page → **Bulk import** → file upload કરો.
3. ✅ **Expected:** "Equipment class code" અને "Computer-operated" auto-match થયેલા દેખાય (exact
   column નામ match થાય છે); બાકીના fields પણ auto-match થશે કારણ કે sample ના column નામ બરાબર
   fields ના key સાથે મળે છે.
4. **Continue** → **Preview** → બંને rows **OK** → **Import 2 row(s)**.
5. ✅ **Expected:** "Created 2 equipment asset(s)." દેખાય, list માં નવા ૨ assets ઉમેરાયા.

---

## ૨૦.૮ — Product Master Cleanup (Phase ૮)

**શું બદલાયું:** (અ) "Business ID" field હવે form માં **નથી** — auto generate થાય છે. (બ) Existing
product ની નવી version બનાવવા માટે **"New version"** button (Versions card પર) — Business ID
જાતે ફરી ટાઈપ નથી કરવું પડતું. (ક) "Manufacturing Profile" field હવે **Advanced** section માં
(ફરજિયાત જ છે, ફક્ત ઓછું મુખ્ય દેખાય એ રીતે ખસેડ્યું). (ડ) Field order: Product Family → Code →
Name → Strength. (ઇ) Bulk import (upload+mapping, જુઓ ૨૦.૧).

**Test ૧ — Business ID Auto-Generate + New Version Button (`/product-master`, login: `admin`)**

1. **New draft** → ✅ **Expected:** "Business ID" નામનું કોઈ field દેખાતું નથી. Field order ટોપ થી:
   Product Family, Product code, Version no., Name, Strength value/UOM, પછી Site.
2. Name: `Metformin Tablet 500mg`, Site: `T1` → "Advanced" (collapsed section) ખોલો →
   Manufacturing profile: `pharma` → Create.
3. ✅ **Expected:** draft બની જાય, detail page પર Business ID આપોઆપ `PRDB-000xxx` જેવું દેખાય.
4. Product list માં એ product ની **Versions** card ખોલો (ⓘ history icon/button).
5. ✅ **Expected:** ત્યાં નવું **"New version"** button દેખાય.
6. **New version** click કરો.
7. ✅ **Expected:** modal title માં "New version - PRDB-000xxx" દેખાય, Version no. આપોઆપ `2` ભરેલું,
   Business ID field (hidden) પાછળથી એ જ existing product સાથે જોડાય છે — Name બદલીને
   (`Metformin Tablet 500mg (v2)`) Create કરો.
8. ✅ **Expected:** Versions list માં હવે v1 અને v2 બંને, બંને નો Business ID સરખો.

**Test ૨ — Manufacturing Profile Advanced Section**

1. **New draft** ફરી ખોલો → ✅ **Expected:** main form માં "Manufacturing profile" સીધું દેખાતું
   નથી — **"Advanced"** લખેલ collapsible section click કરવું પડે.
2. Advanced ખોલતા ✅ **Expected:** "Manufacturing profile" dropdown ત્યાં ફરજિયાત field તરીકે
   દેખાય (ખાલી રાખીને submit ના થઈ શકે — ખોલીને ભરવું જ પડે).

**Test ૩ — Bulk Product Import (upload + mapping)**

1. આ content `products-sample.csv` તરીકે save કરો:

   ```csv
   product_code,name,manufacturing_profile_code,product_family_code,combination_product_type,strength_value,strength_uom
   ,Metformin Tablet 500mg,pharma,,,500,mg
   ,Insulin Prefilled Syringe,injectable_ddcp,,prefilled_syringe,100,mL
   ```

2. **Product Master** page → **Bulk import** → ✅ **Expected:** સૌથી પહેલા **"Site"** dropdown
   દેખાય (ફરજિયાત, file upload step પહેલા) — `T1` પસંદ કરો.
3. File upload કરો → mapping step auto-match બતાવશે (sample ના column નામ field key સાથે બરાબર
   મળે છે) → **Continue** → **Preview** → બંને **OK** → **Import 2 row(s)**.
4. ✅ **Expected:** "Created 2 product draft(s)." — બંને ની Business ID આપોઆપ generate થયેલી,
   version 1.

---

## ૨૦.૯ — શું Deliberately Built નથી (client એ પોતે postpone કરેલું, bug નથી)

| Item | કારણ |
|---|---|
| AI દ્વારા Material Spec PDF માંથી auto-extraction (Phase ૫ Part B) | Client એ "hold" કહ્યું — cost/data-privacy decision બાકી |
| New/Old Equipment toggle (જૂનું equipment onboard કરવાનો ટૂંકો રસ્તો) | Client એ વિગતવાર rules પછી મોકલવાનું કહ્યું |
| Computer System Validation (21 CFR Part 11) questionnaire | Client એ detail design postpone કરી |
| Maintenance Specification + Acceptance Criteria | Client: "હમણાં hold કરો, પછી design મોકલીશ" |
| Breakdown Critical/Non-critical ની વિગતવાર rules | ફક્ત binary flag જ બનાવ્યું (૨૦.૭ Test ૩) |
| Product category-specific fields (device vs pharma) | કશું existing નથી — client એ ભવિષ્યમાં ચર્ચા કરવાનું કહ્યું |
| Purchase Order module | Scope બહાર રાખ્યું |

---

**Document સંબંધિત નોંધ:** આ guide live system પર ૨૦૨૬-૧૦-૦૬ ના રોજ ચકાસેલ છે (migration મારફતે
backend code restart કરેલું, બધા નવા routes/fields confirm કરેલા). કોઈ પણ test માં expected
result ના મળે તો development team ને જણાવો.
