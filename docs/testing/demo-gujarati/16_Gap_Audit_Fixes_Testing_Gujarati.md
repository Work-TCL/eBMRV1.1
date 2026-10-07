   ## ૧૬. Gap-Audit Fixes — Manual Browser Testing Guide (Gujarati)

   > **હેતુ:** આ ડોક્યુમેન્ટ 2026-09-22 ના gap-audit session માં ઉમેરાયેલા/બદલાયેલા features manually
   > test કરવા માટે છે: (૧) security fix — પહેલાં login વગર data ખુલ્લું દેખાતું હતું, (૨) sidebar
   > menu ના હોય તો પણ URL સીધું type કરીને page ખૂલી જતું હતું, (૩) ત્રણ નવા signature requirement
   > (CAPA Plan/Extend, Batch Record PDF), (૪) જૂનું Material Lot Disposition બટન કાયમ માટે કાઢી
   > નાખ્યું, (૫) SCAR supplier suspension હવે material receipt ને ખરેખર block કરે છે, (૬) Warehouse
   > Location ને rename/retire કરવાની નવી સુવિધા, (૭) Recipe માં જાહેર કરેલું જરૂરી material વાપર્યા
   > વગર batch step complete નહીં થાય, (૮) Supplier suspend થાય તો પહેલેથી received/released material
   > પણ હવે reserve/use નહીં થઈ શકે (ફક્ત નવો receipt જ નહીં).
   >
   > **જરૂરી:** Browser માં app ખોલો, નીચે આપેલ username થી login કરો. **Password બધા માટે સરખો:**
   > `ChangeMe123!`

   ---

   ### Login Reference (આ ડોક્યુમેન્ટ માટે જરૂરી Users)

   | Username | Role | આ guide માં ક્યાં વપરાય છે |
   |---|---|---|
   | `calibration.tech` | Calibration Technician | Security/RBAC test — બહુ સાંકડું role, બીજું કંઈ permission નથી |
   | `operator1` | Operator | Direct-URL બ્લોક ચકાસવા, material receipt, reservation |
   | `admin` | Admin | CAPA બનાવવી, batch record PDF blocker જોવો, SCAR/batch બનાવવા |
   | `supervisor1` | Supervisor | CAPA Plan/Extend — RBAC પાસ પણ signature-role ના કારણે FAIL (negative test) |
   | `qa.releaser` | QA Releaser | CAPA Plan/Extend/Close સાચી રીતે sign કરવા, Batch Record PDF sign કરવા, SCAR close, Material Spec/Material Lot release |
   | `qc.reviewer` | QC Reviewer | Material Lot — હવે ફક્ત Release/Reject જ કરી શકે (જૂનું Disposition નથી) |
   | `process.engineer` | Process Engineer | Material Specification draft, Recipe draft બનાવવા (author role) |

   ---

   ## ૧૬.૧ — Security Fix: Login વગર Data ના ખૂલવું જોઈએ

   **શું બદલાયું:** પહેલાં Materials, Material Lots, Material Receipts, Inventory, QC, Equipment,
   Cleaning, EM, Aseptic, Sterilization, DDCP, ERP/LIMS Integration — આ બધા modules ના કેટલાક data
   API સીધા (કોઈ પણ login વગર) ખૂલી જતા હતા. હવે **login જરૂરી છે** — login વગર `401 Unauthorized`
   error આવે છે.

   **Test (Browser, કોઈ technical tool વગર):**

   1. એક **નવી Incognito / Private વિન્ડો** ખોલો (જેથી તમે કોઈ પણ user તરીકે login ના હો).
   2. App ના address bar માં સીધું આ પ્રકારનું data URL paste કરો (backend port — સામાન્ય રીતે
      `:8010`): દા.ત. `http://localhost:8010/materials` અથવા `http://localhost:8010/equipment/v1/assets`.
   3. ✅ **Expected:** પહેલાં અહીં raw material/equipment list (JSON data) દેખાતું હતું. **હવે**
      `{"code":"..."}` સાથે Unauthorized/401 error આવવો જોઈએ — કોઈ real data ના દેખાવું જોઈએ.
   4. હવે એ જ Incognito વિન્ડોમાં પહેલા સામાન્ય રીતે login કરો (કોઈ પણ user) → app વાપરો → બધું પહેલાં
      ની જેમ જ કામ કરે — ✅ **Expected:** Login કરેલ user માટે કંઈ પણ તૂટેલું ના લાગવું જોઈએ, ફક્ત
      login-વગરની access જ બંધ થઈ છે.

   ---

   ## ૧૬.૨ — Sidebar માં Menu ના હોય તો URL સીધું Type કરીને પણ Page ના ખૂલવું જોઈએ

   **શું બદલાયું:** પહેલાં sidebar માં કોઈ menu item ના દેખાય (કારણ કે એ role પાસે permission નથી)
   તો પણ, જો user એ page ની URL સીધી address bar માં type કરે તો page ખૂલી જતું અને ક્યારેક ડેટા પણ
   દેખાતું. હવે આ pages પર સીધું URL type કરવાથી **આપોઆપ `/batch-execution` પર પાછું મોકલી દેવાય છે**.

   **Test (login: `calibration.tech` — આ role પાસે લગભગ કંઈ view permission નથી, ફક્ત equipment
   calibrate કરી શકે):**

   1. `calibration.tech` થી login કરો.
   2. Sidebar જુઓ — ✅ **Expected:** Product master, Recipe master, Vault, Audit ledger, CAPA,
      Deviations જેવા menu items **sidebar માં દેખાતા જ નથી** (કારણ કે permission નથી).
   3. હવે address bar માં સીધું `/product-master` type કરીને Enter દબાવો.
   4. ✅ **Expected:** Page ના ખૂલે — તરત `/batch-execution` પર redirect થઈ જાય છે.
   5. એ જ રીતે `/vault`, `/audit`, `/capa`, `/deviations`, `/rules` — આ બધા URL સીધા try કરો.
   6. ✅ **Expected:** દરેક વખતે `/batch-execution` પર જ પાછા આવો છો, કોઈ પણ data ની ઝલક પણ નથી
      દેખાતી.

   ---

   ## ૧૬.૩ — CAPA: Plan Approval અને Extend હવે Signed Actions છે

   **શું બદલાયું:** પહેલાં CAPA નું **"Plan approval"** (corrective/preventive action ભરવું) અને
   **"Extend target date"** કોઈ પણ signature વગર સીધા submit થઈ જતા. હવે — Document 27 ની requirement
   પ્રમાણે — આ બંને actions **Close/Record-effectiveness-result ની જેમ જ signed** છે: independent
   **QA Releaser** signature જરૂરી.

   **Test ૧ — સાચી રીતે Sign કરવું (login: પહેલા `admin` → પછી `qa.releaser`)**

   1. `admin` થી login કરી નવી CAPA બનાવો (`/capa` → Raise CAPA) — **Owner** field માં પોતાના સિવાય
      કોઈ બીજા user ને પસંદ કરો (દા.ત. `supervisor1`) — independence check માટે જરૂરી.
   2. CAPA detail page ખોલો → **"Plan approval"** button click કરો.
   3. ✅ **Expected:** હવે એક નવો signature-ceremony screen ખૂલે છે (પહેલાંની જેમ સીધું plain form
      નહીં) — Corrective action / Preventive action / Effectiveness plan fields સાથે, નીચે password
      field અને **"Sign & approve plan"** button.
   4. Corrective action ભરો → password (`ChangeMe123!`) નાખો → **Sign & approve plan** click કરો.
   5. Logout કરી `qa.releaser` થી ફરી login કરો, એ જ CAPA ખોલો → **"Plan approval"** ફરી click કરો.
   6. ✅ **Expected:** આ વખતે signature ceremony ખૂલે, `qa.releaser` password નાખી sign કરે — CAPA
      state `PLAN` માં જાય છે.
   7. હવે **"Extend target date"** button click કરો (હજુ `qa.releaser` login જ) → New target date,
      Reason, Risk review ભરો → password → **Sign & extend**.
   8. ✅ **Expected:** સફળતાપૂર્વક sign થાય, નવી target date લાગુ થાય.

   **Test ૨ — ખોટા Role થી Sign કરવાનો પ્રયત્ન (Negative test, login: `supervisor1`)**

   1. `supervisor1` થી login કરો → એ જ (અથવા નવી) CAPA ખોલો → **"Plan approval"** click કરો.
   2. ✅ **Expected:** Signature ceremony ખૂલે (challenge request સફળ થાય છે — RBAC પરવાનગી છે).
   3. Fields ભરીને password નાખી submit કરો.
   4. ✅ **Expected:** Error આવવો જોઈએ — `ROLE_MISSING` ("...requires the signing role named by the
      signature policy") — કારણ કે `supervisor1` પાસે `QA Releaser` role નથી, ફક્ત QA Releaser જ આ
      sign કરી શકે.

   ---

   ## ૧૬.૪ — Batch Record PDF હવે QA Releaser Sign કરે છે (પહેલાં Unsigned હતું)

   > ⚠️ **સુધારો (correction) અગાઉના doc #૧૫, section ૧૫.૧૦ માં:** ત્યાં લખેલું છે કે "Generate PDF"
   > click કરતાં જ સીધું PDF બની જાય છે. **હવે એવું નથી** — હવે એ પણ signed action છે.

   **શું બદલાયું:** Batch Record PDF export (client requirement #૧૧) હવે final batch record ની
   regulatory evidence ગણાય છે એટલે **QA Releaser signature જરૂરી** છે.

   **Test (login: `admin` → પછી `qa.releaser`)**

   1. `admin` થી login કરી `/batch-execution` → કોઈ પણ batch ખોલો → **"Batch record"** button click
      કરો → modal ના તળિયે **"Generate PDF"** click કરો.
   2. ✅ **Expected:** હવે સીધું PDF નથી બનતું — એક signature-ceremony screen ખૂલે છે: "Generate batch
      record PDF" title, નીચે **Reason** field (લખવું ફરજિયાત) અને password field.
   3. Reason ભરો (દા.ત. `Batch record export for QA file`) → password નાખો → submit કરવાનો પ્રયત્ન
      કરો.
   4. ✅ **Expected:** Error — `admin` પાસે `QA Releaser` role ના હોવાથી **ROLE_MISSING** error આવે
      છે (Admin permission થી action reach તો કરી શકે, પણ sign ના કરી શકે).
   5. Logout કરી `qa.releaser` થી login કરો → એ જ batch → Batch record → Generate PDF → Reason ભરી,
      password નાખી → **"Sign & generate"** click કરો.
   6. ✅ **Expected:** આ વખતે સફળતાપૂર્વક PDF બને છે — "Batch record PDF generated" banner અને
      **Download PDF** button દેખાય છે.

   ---

   ## ૧૬.૫ — Material Lot: જૂનું "Disposition" બટન કાયમ માટે કાઢી નાખ્યું

   **શું બદલાયું:** `/material-lots` page પર પહેલાં **બે** disposition રસ્તા હતા — જૂનું
   **"Disposition"** બટન (QC Reviewer sign કરતો) અને નવું **"Release (QA)" / "Reject (QA)"** (QA
   Releaser sign કરે છે, Document 106 પ્રમાણે સાચું). બંને એક જ lot ના status ને અલગ-અલગ
   authorization થી બદલી શકતા હતા — એ **ભૂલ (SG-075)** હતી. હવે **ફક્ત Release/Reject જ છે**,
   Disposition બટન કાયમ માટે કાઢી નાખ્યું.

   **Test (login: `operator1` → lot બનાવવા, પછી `qa.releaser` → release કરવા)**

   1. `operator1` થી કોઈ material lot receive કરો (quarantine માં આવે છે).
   2. `/material-lots` page પર જુઓ → એ lot ની row ના Actions column માં:
   3. ✅ **Expected:** **"Disposition"** નામનું બટન હવે **ક્યાંય નથી**. ફક્ત **"Release (QA)"** અને
      **"Reject (QA)"** બટન જ દેખાય છે (અને એ પણ ફક્ત `material_lot.release`/`.reject` permission
      વાળા user ને — QC Reviewer ને હવે આ બટન દેખાતા જ નથી, કારણ કે QC Reviewer પાસે release/reject
      permission ક્યારેય નહોતું).
   4. `qa.releaser` થી login કરો → એ lot માટે **"Release (QA)"** click કરો → password નાખી sign
      કરો.
   5. ✅ **Expected:** Lot status `Released` થાય છે — પહેલાંની જેમ જ કામ કરે છે, ફક્ત UI માંથી જૂનો
      રસ્તો ગાયબ છે.

   ---

   ## ૧૬.૬ — SCAR: Supplier Suspend/Reinstate હવે ખરેખર Material Receipt ને Block કરે છે

   **શું બદલાયું:** પહેલાં SCAR (Supplier Corrective Action Request) close કરતી વખતે "Source status
   decision" માં **"suspend"** પસંદ કરો તો પણ Supplier ના master record નું status ખરેખર બદલાતું
   નહોતું — એટલે એ supplier પાસેથી નવો material receipt લેવો શક્ય જ રહેતો (block નહોતું થતું). હવે
   **suspend** પસંદ કરવાથી supplier નું status ખરેખર **"suspended"** થાય છે, અને એ પછી એ supplier નો
   કોઈ પણ નવો receipt **discrepancy hold** માં જાય છે.

   **Test (login: `admin` → SCAR બનાવવા/close કરવા; `operator1` → receipt કરવા)**

   1. `/suppliers` page → કોઈ supplier ની વિગત નોંધી લો (દા.ત. `Acme Chemicals`, status હાલમાં
      `approved` હોવો જોઈએ).
   2. `/supplier-cases` → એ supplier સામે નવો SCAR case ખોલો → જરૂરી steps (Issue → Response →
      Review → Effectiveness) પૂરા કરો (જુઓ file #૧૦ CAPA/SCAR guide ની પેટર્ન, અથવા existing
      supplier-cases doc).
   3. Close SCAR કરતી વખતે **"Source status decision"** માં **`suspend`** પસંદ કરો → Conclusion ભરી
      → sign કરી close કરો.
   4. `/suppliers` page પર પાછા જાવ → એ જ supplier ખોલો.
   5. ✅ **Expected:** Supplier નું status હવે **"suspended"** દેખાય છે (પહેલાં "approved" જ રહેતું
      હતું).
   6. `operator1` થી login કરી, એ જ supplier પસંદ કરીને એક નવો **Material Receipt** બનાવો → Examine
      કરો (બધા visual check "Yes"/clean રાખો).
   7. ✅ **Expected:** Receipt clean examine હોવા છતાં **discrepancy hold** માં જાય છે — discrepancy
      type: `source_not_approved` (કારણ કે supplier હવે approved નથી).
   8. (વૈકલ્પિક) ફરી એક નવો SCAR ખોલી, આ વખતે close કરતી વખતે **`reinstate`** પસંદ કરો → Supplier
      status પાછું `approved` થવું જોઈએ, અને પછીનો receipt ફરી ક્લીન પાસ થવો જોઈએ.

   ---

   ## ૧૬.૭ — Warehouse Location: હવે Rename અને Retire કરી શકાય છે

   **શું બદલાયું:** પહેલાં Warehouse Location (`/inventory` ના Availability tab પર "New location")
   ફક્ત **બનાવી** શકાતું હતું — rename કે retire કરવાનો કોઈ રસ્તો નહોતો. હવે બંને ઉમેરાયા છે.

   **Test (login: `supervisor1` અથવા `admin`, page: `/inventory`)**

   1. `/inventory` → Availability tab → **"New location"** થી નવું location બનાવો (Warehouse code:
      `WH-TEST`, Location code: `LOC-TEST-01`, Zone type: `quarantine`).
   2. Location list માં એ નવું location શોધો → **Edit/Rename** action (pencil icon અથવા "Rename"
      button) click કરો.
   3. Location code બદલીને `LOC-TEST-01-RENAMED` કરો, Zone type `released` કરો → Save.
   4. ✅ **Expected:** List માં નવું નામ/zone દેખાય છે.
   5. એ જ location ને **Retire** કરો (reason ફરજિયાત: દા.ત. `Zone decommissioned`).
   6. ✅ **Expected:** Location હવે active list માંથી ગાયબ થઈ જાય છે (retire = soft-delete, data
      delete નથી થતું).
   7. (વૈકલ્પિક negative test) કોઈ location માં material lot store થયેલું હોય (storage location
      તરીકે) તો એને retire કરવાનો પ્રયત્ન કરો → ✅ **Expected:** Error — "Cannot retire a warehouse
      location that still has material stored in it".

   ---

   ## ૧૬.૮ — Batch Step: જરૂરી Material વાપર્યા વગર Step Complete નહીં થાય

   **શું બદલાયું:** Recipe ના કોઈ step માં ચોક્કસ material જરૂરી (required) છે એવું જાહેર કરેલું હોય
   (Recipe Master માં "Material requirement" ઉમેરીને), તો હવે batch execution વખતે એ material ખરેખર
   consume (વાપર્યું) ના હોય ત્યાં સુધી **એ step complete નહીં થઈ શકે**. પહેલાં આ material requirement
   ફક્ત recipe ની detail પર "reference માટે" દેખાડાતું હતું — completion વખતે કોઈ check જ નહોતો.

   > **સ્પષ્ટતા (scope):** આ check એટલું જ ચકાસે છે કે batch માટે એ જ material (દા.ત. "Test Raw
   > Material") **ક્યાંય પણ** consume થયું છે કે નહીં — કયા ચોક્કસ step માટે વપરાયું એ નહીં, અને
   > quantity/tolerance પણ નહીં ચકાસે (ફક્ત હાજરી/ઓળખ, પ્રમાણ નહીં).

   **Test Setup (login: `process.engineer` → spec/recipe draft બનાવવા; `qa.releaser` → release કરવા)**

   1. `/materials` → નવું material બનાવો (દા.ત. code `RM-TESTMAT`, name `Test Raw Material`, UOM `kg`).
   2. `/material-specifications` → **New draft** → ઉપરનું material પસંદ કરી spec version બનાવો →
      Submit → `qa.releaser` થી login કરી **Release** કરો (password: `ChangeMe123!`).
   3. `process.engineer` થી login કરો → `/recipe-master` → નવું recipe draft બનાવો (અથવા existing
      draft edit કરો, released product version સાથે) → કોઈ એક step ખોલો → **"Add material
      requirement"** click કરો → ઉપર release કરેલ material spec પસંદ કરો → Save → Submit કરો.
   4. `qa.releaser` થી login કરી એ recipe version **Release** કરો.
   5. `/batch-execution` → નવો batch બનાવો (એ જ product + recipe version પસંદ કરીને) → **Issue** →
      **Start**.

   **Test (Block ચકાસવો)**

   6. જે step માં material requirement ઉમેર્યું હતું એ step ખોલો → **Start step** કરો.
   7. **"Complete step"** click કરો → signature ceremony ખૂલશે → password નાખી **Sign & complete**
      click કરો.
   8. ✅ **Expected:** Error આવવો જોઈએ — `VALIDATION_FAILED: Required material has not been consumed
      for this batch` — step complete **ના** થાય, ceremony window ખુલ્લી જ રહે.

   > ⚠️ **જાણીતી મર્યાદા (known limitation, ડોક્યુમેન્ટ કરેલી):** હાલમાં material consumption record
   > કરવા માટે backend endpoint (`POST /materials/v1/consumptions`) છે, પણ **frontend માં હજુ કોઈ
   > button/page નથી** જે એને call કરે — એટલે "consumption record કર્યા પછી step સફળતાપૂર્વક complete
   > થાય છે" એ ભાગ અત્યારે શુદ્ધ browser-click થી ચકાસી શકાતો નથી. Block ખરેખર કામ કરે છે એ ચકાસવા
   > માટે ઉપરના પગલાં ૬-૮ પૂરતા છે.

   ---

   ## ૧૬.૯ — Supplier Suspend થાય તો પહેલેથી Received Material પણ Reserve/Use નહીં થઈ શકે

   **શું બદલાયું:** Section ૧૬.૬ માં supplier suspend થાય તો **નવો** receipt block થતો બતાવ્યું હતું.
   હવે એક પગલું આગળ વધારાયું — supplier suspend **થયા પહેલાં** જે material lot receive/release/
   put-away થઈ ચૂક્યો હોય, એ lot પણ હવે supplier suspend થતાં જ **Availability list માંથી ગાયબ** થઈ
   જાય છે અને એને **Reserve પણ ના કરી શકાય**.

   **Test (login: `admin` → SCAR/supplier માટે; `operator1` → receipt/reserve માટે; `qa.releaser` →
   lot release માટે)**

   1. Section ૧૬.૬ ની જેમ, એક supplier ને `approved` રાખો → `operator1` થી એની પાસેથી material
      receive → examine (clean) → `qa.releaser` થી **Release** → **Put-away** (કોઈ location માં,
      દા.ત. `RELEASED-01`).
   2. `/inventory` → Availability tab → એ material પસંદ કરો.
   3. ✅ **Expected:** Lot list માં દેખાય છે, available quantity સાથે.
   4. હવે એ જ supplier સામે નવો SCAR ખોલી, close કરતી વખતે **"Source status decision" = suspend**
      પસંદ કરી sign કરો (Section ૧૬.૬ ના પગલાં પ્રમાણે — `admin` login).
   5. `/inventory` → Availability tab → એ જ material ફરી જુઓ (page refresh કરો જો જરૂર પડે).
   6. ✅ **Expected:** હવે એ lot list માં **દેખાતો નથી** (ખાલી list) — supplier suspended હોવાથી.
   7. `operator1` થી login કરી **"Reserve"** button click કરો → એ જ material પસંદ કરી, કોઈ પણ batch
      ID અને quantity નાખી submit કરો.
   8. ✅ **Expected:** Error આવવો જોઈએ — `VALIDATION_FAILED: No eligible released, non-expired,
      non-retest-due lot/container has sufficient available quantity for this reservation` —
      reservation **નથી** બનતું.
   9. (વૈકલ્પિક) `admin` થી નવો SCAR ખોલી, close કરતી વખતે **`reinstate`** પસંદ કરો → `/inventory` →
      Availability list માં એ lot **પાછો દેખાવો** જોઈએ, અને Reserve ફરી **સફળ** થવું જોઈએ.

   ---

   ## Summary Checklist (Quick Reference)

   | # | શું | મુખ્ય Page | મુખ્ય Login |
   |---|---|---|---|
   | ૧૬.૧ | Login વગર data બંધ | (કોઈપણ data API, Incognito) | (કોઈ login નહીં) |
   | ૧૬.૨ | Sidebar ના હોય તો URL પણ બ્લોક | `/product-master`, `/vault`, `/capa` વગેરે | calibration.tech |
   | ૧૬.૩ | CAPA Plan/Extend signed | `/capa/{id}` | admin (create), qa.releaser (sign), supervisor1 (negative) |
   | ૧૬.૪ | Batch Record PDF signed | `/batch-execution` → Batch record | qa.releaser |
   | ૧૬.૫ | જૂનું Disposition બટન ગાયબ | `/material-lots` | operator1, qa.releaser |
   | ૧૬.૬ | SCAR suspend → receipt block | `/supplier-cases`, `/suppliers`, `/material-receipts` | admin, operator1 |
   | ૧૬.૭ | Warehouse Location rename/retire | `/inventory` | supervisor1, admin |
   | ૧૬.૮ | જરૂરી material વગર step complete ના થાય | `/recipe-master`, `/batch-execution` | process.engineer, qa.releaser, admin |
   | ૧૬.૯ | Supplier suspend → જૂનું material પણ block | `/inventory`, `/supplier-cases` | admin, operator1, qa.releaser |
