# eBMR / eDHR — સંપૂર્ણ ફંક્શનલ ટેસ્ટિંગ ગાઇડ (ગુજરાતીમાં)

આ દસ્તાવેજ આખા પ્લેટફોર્મ (દરેક મોડ્યુલ)ને ફ્રન્ટએન્ડ (બ્રાઉઝર UI) અને બેકએન્ડ (API/ડેટાબેઝ) બંને બાજુથી, પગલાં-દર-પગલાં, વાસ્તવિક-જગત (real-world) ડેટા સાથે કેવી રીતે ટેસ્ટ કરવું તે સમજાવે છે. દરેક મોડ્યુલ માટે ચાર ભાગ છે:

1. **હેતુ** — આ ફંક્શન વાસ્તવિક ફેક્ટરી/કંપનીમાં શા માટે અને ક્યારે વપરાય છે.
2. **ઉદાહરણ ડેટા** — ટેસ્ટ કરવા માટે નમૂનારૂપ (sample) વાસ્તવિક-જેવો ડેટા.
3. **ફ્રન્ટએન્ડ પગલાં** — બ્રાઉઝરમાં બરાબર ક્યાં ક્લિક કરવું, શું ભરવું.
4. **બેકએન્ડ ચકાસણી** — સર્વર/ડેટાબેઝ શું ચેક કરે છે, ક્યાં નિષ્ફળ (fail) થઈ શકે, અને શા માટે.

> **નોંધ:** આ સિસ્ટમ એક રેગ્યુલેટેડ (regulated) ફાર્મા મેન્યુફેક્ચરિંગ પ્લેટફોર્મ છે (US FDA 21 CFR Part 11 ધોરણો પ્રમાણે). એટલે ઘણી જગ્યાએ "સહી" (electronic signature) જરૂરી છે — યુઝરનેમ/પાસવર્ડથી લોગિન કરવું એ સહી નથી; સહી માટે અલગથી પાસવર્ડ ફરીથી નાખવો પડે છે (re-authentication), જેને આ ગાઇડમાં "સહી સેરેમની" (signature ceremony) કહી છે.

## શરૂઆત કરતાં પહેલાં

- **URL:** ફ્રન્ટએન્ડ `http://<server>:4101`, બેકએન્ડ API `http://<server>:8010`.
- **લોગિન ટેસ્ટ યુઝર્સ (ડેમો ડેટા, `scripts/seed.py`માંથી):**
  - `admin` / `ChangeMe123!` — બધા રોલ (Admin) ધરાવે છે, દરેક પેજ ટેસ્ટ કરવા માટે વાપરો.
  - `operator1` — શોપ-ફ્લોર ઓપરેટર (બેચ execution, ડિસ્પેન્સિંગ).
  - `qa.reviewer` — QA Reviewer (પ્રથમ સહી/રિવ્યૂ).
  - `qa.releaser` — QA Releaser (અંતિમ રિલીઝ સહી, reviewer કરતાં અલગ વ્યક્તિ હોવી જ જોઈએ — SoD/Segregation of Duties).
- **સાઇટ (Site):** સિસ્ટમ સિંગલ-સાઇટ છે (Phase 1) — લોગિન પછી આપોઆપ એ જ સાઇટ વપરાય છે.
- **દરેક ટેસ્ટ પછી શું જોવું:** (1) UI માં યોગ્ય success/error સંદેશ આવ્યો? (2) `/audit` પેજ પર એ જ રેકોર્ડ માટે નવી ઓડિટ એન્ટ્રી બની? (3) જો સહી જરૂરી હતી તો Audit Ledgerમાં "Signed" કૉલમમાં ✓ ચિહ્ન છે?

---

## ભાગ ૧ — વહીવટ અને પ્લેટફોર્મ પાયો (WP-01: GxP Core)

### ૧.૧ Admin → Users (વપરાશકર્તા વ્યવસ્થાપન)

**હેતુ:** ફેક્ટરીમાં દરેક કર્મચારીનું પોતાનું અલગ લોગિન હોવું જોઈએ (shared login પ્રતિબંધિત છે — Part 11 ની જરૂરિયાત). અહીંથી નવો યુઝર બનાવવો, તેને રોલ (ભૂમિકા) અને સાઇટ સોંપવી, અને જરૂર પડે ડિએક્ટિવેટ કરવો.

**ઉદાહરણ ડેટા:**
| ફિલ્ડ | કિંમત |
|---|---|
| Username | `ravi.patel` |
| Full name | `Ravi Patel` |
| Email | `ravi.patel@meridian-pharma.example` |
| Role | `Operator` |
| Site | `Site 1` (ડિફોલ્ટ સાઇટ) |

**ફ્રન્ટએન્ડ પગલાં:**
1. `admin` તરીકે લોગિન કરો → ડાબી સાઇડબારમાં **Admin → Users** ખોલો.
2. **Create user** બટન દબાવો.
3. ઉપરનું ડેટા ભરો, પ્રારંભિક પાસવર્ડ સેટ કરો, સેવ કરો.
4. લિસ્ટમાં `ravi.patel` દેખાય છે કે નહીં ચકાસો; તેની હરોળ (row) પર ક્લિક કરીને role/site અસાઈન કરો.
5. ડિએક્ટિવેટ ટેસ્ટ: તે યુઝર પર "Deactivate" ક્રિયા ચલાવો → status "deactivated" દેખાવો જોઈએ.

**બેકએન્ડ ચકાસણી:**
- `POST /users` — username યુનિક હોવું જ જોઈએ (ડુપ્લિકેટ આપતાં 409 ભૂલ આવવી જોઈએ — આ પણ એક ટેસ્ટ કેસ છે: `ravi.patel` ફરીથી બનાવવાનો પ્રયત્ન કરો, ભૂલ મળવી જોઈએ).
- પાસવર્ડ ડેટાબેઝમાં ક્યારેય સાદા લખાણ (plaintext) માં સંગ્રહાતો નથી — હેશ (hash) જ સંગ્રહાય છે.
- દરેક ક્રિયા (create/deactivate) `audit` કોષ્ટકમાં નોંધાય છે, actor = લોગ-ઇન થયેલ Admin.

### ૧.૨ Admin → Roles / Sites / Company

**હેતુ:** કંપનીનું નામ, સાઇટ (પ્લાન્ટ લોકેશન), અને દરેક રોલ ને કયા પરમિશન કોડ મળે તે અહીંથી ગોઠવાય છે — દા.ત. "QA Releaser" રોલ પાસે `batch.release` પરમિશન હોવી જ જોઈએ, નહીં તો કોઈ બેચ રિલીઝ જ નહીં કરી શકે.

**ફ્રન્ટએન્ડ પગલાં:** Admin → Roles ખોલો → "QA Releaser" રોલ પસંદ કરો → તેમાં `batch.release`, `qa_review.decide` જેવી પરમિશન છે કે નહીં જુઓ.

**બેકએન્ડ ચકાસણી:** કોઈ પણ મ્યુટેશન (write) API કૉલ પહેલાં Mutation Gateway પોલિસી ચેક કરે છે — યુઝર પાસે જરૂરી પરમિશન ન હોય તો `403 Forbidden` મળવો જોઈએ. **ટેસ્ટ:** `operator1` થી બેચ રિલીઝ કરવાનો પ્રયત્ન કરો → નકારાવું જ જોઈએ.

### ૧.૩ Admin → Access review

**હેતુ:** કોણ, કઈ સાઇટ પર, કઈ ભૂમિકા ધરાવે છે તેની સંપૂર્ણ યાદી — સામયિક (periodic) access review માટે, જેથી કોઈ છોડી ગયેલ કર્મચારીની ઍક્સેસ રહી ન જાય.

**ફ્રન્ટએન્ડ પગલાં:** યાદીમાં શોધો, "Authorization decision check" ફોર્મમાં action = `batch.release` નાખી "Check" દબાવો — તમારી પોતાની ઍક્સેસ ALLOW/DENY બતાવશે.

**બેકએન્ડ ચકાસણી:** `POST /policy/v1/decisions` એ જ પોલિસી એન્જિન વાપરે છે જે અસલ મ્યુટેશન વખતે વપરાય છે — એટલે અહીં જે જવાબ મળે એ જ ખરેખર થશે (read-only ડ્રાય-રન).

### ૧.૪ Audit Ledger (ઓડિટ ટ્રેલ)

**હેતુ:** સિસ્ટમમાં થયેલ **દરેક** ફેરફારનો કાયમી, ભૂંસી ન શકાય તેવો (immutable) રેકોર્ડ — કોણે, ક્યારે, શું બદલ્યું, અને શું સહી કરેલી હતી. FDA ઇન્સ્પેક્ટર માટે સૌથી મહત્વનું પેજ.

**ફ્રન્ટએન્ડ પગલાં:**
1. કોઈ પણ બેચ/મટીરિયલ લોટનું ID કૉપિ કરો (દા.ત. batch execution પેજ પરથી).
2. `/audit` પેજ પર જાઓ → "Record ID" ફિલ્ડમાં પેસ્ટ કરો, "Record type" માં `gxp_batch` નાખો.
3. "Verify hash chain" ચેકબોક્સ ચાલુ કરો → પરિણામમાં "Chain" કૉલમમાં ✓ (લીલું) આવવું જોઈએ — મતલબ કોઈએ ડેટા સાથે છેડછાડ (tamper) નથી કરી.

**બેકએન્ડ ચકાસણી:** દરેક ઓડિટ event માં પાછલા event નો hash (`prev_event_hash`) સંગ્રહાય છે — સાંકળ (chain) બને છે. જો કોઈ જૂનું રેકોર્ડ ડેટાબેઝમાં સીધું બદલી નાખે (જે ક્યારેય ન થવું જોઈએ), તો hash મેળ નહીં ખાય અને "Chain" કૉલમ ❌ (તૂટેલી) બતાવશે.

### ૧.૫ Vault (પુરાવા/માસ્ટર રેકોર્ડ તિજોરી)

**હેતુ:** કોઈ પણ રેકોર્ડ પ્રકાર (દા.ત. જેના માટે અલગ ખાસ રિલીઝ ફ્લો બન્યો નથી) ને સત્તાવાર રીતે "રિલીઝ" (કાયમી, ફેરફાર ન કરી શકાય તેવું વર્ઝન) બનાવવાનો સામાન્ય માર્ગ.

**ઉદાહરણ ડેટા:** Object type = `sop_document`, Business ID = `SOP-CLEAN-014`, Canonical payload (key/value): `title` → `Line clearance SOP`, `revision` → `3`.

**ફ્રન્ટએન્ડ પગલાં:** Vault પેજ → "Release a master record" ફોર્મ → ઉપરનું ડેટા ભરો (key/value પેરમાં — હવે raw JSON ટેક્સ્ટ નથી ભરવાનું) → સહી સેરેમનીમાં પાસવર્ડ ફરીથી નાખો → Submit.

**બેકએન્ડ ચકાસણી:** આ generic release path ફક્ત એ રેકોર્ડ types માટે વપરાય જેની પોતાની ખાસ રિલીઝ પ્રક્રિયા ન હોય (બેચ રિલીઝ, મટીરિયલ લોટ ડિસ્પોઝિશન જેવા મોડ્યુલ પોતાનો અલગ ફ્લો વાપરે છે). એક વાર released થયા પછી canonical_payload ક્યારેય UPDATE/DELETE થતું નથી — નવો ફેરફાર જોઈએ તો નવું વર્ઝન (supersede) બને છે.

### ૧.૬ Platform → Evidence / Workflow ops

**હેતુ:** કોઈ પુરાવા (ફોટો, PDF, ચાર્ટ) ને સિસ્ટમમાં અપલોડ કરેલ પછી ડાઉનલોડ કરવો, legal hold લગાવવો (તપાસ ચાલુ હોય ત્યારે ડિલીટ ન થાય તે માટે), અને Temporal વર્કફ્લો ઓર્કેસ્ટ્રેશન ઓપરેશન્સ.

**ફ્રન્ટએન્ડ પગલાં:** Platform પેજ → "Download evidence" કાર્ડમાં evidence ID નાખો → ડાઉનલોડ બટન દબાવો → ફાઇલ બ્રાઉઝરમાં ડાઉનલોડ થવી જોઈએ (ફક્ત FINALIZED/ARCHIVED સ્ટેટસના evidence માટે જ કામ કરે).

**બેકએન્ડ ચકાસણી:** evidence object હજુ DRAFT સ્ટેટસમાં હોય તો ડાઉનલોડ નકારાવો જોઈએ (ડ્રાફ્ટ પુરાવો હજુ ફાઇનલ નથી).

---

## ભાગ ૨ — પ્રોડક્ટ, રેસિપી અને બેચ એક્ઝિક્યુશન (WP-02)

### ૨.૧ Product Master (પ્રોડક્ટ માસ્ટર)

**હેતુ:** કંપની જે દવા/પ્રોડક્ટ બનાવે છે તેની સત્તાવાર "સ્પેસિફિકેશન શીટ" — નામ, કોડ, UDI (Unique Device Identifier જો ડિવાઇસ સંલગ્ન હોય), constituent (ઘટકો, જેમ કે combination product માટે drug + device).

**ઉદાહરણ ડેટા:**
| ફિલ્ડ | કિંમત |
|---|---|
| Product code | `MERIDIJECT-PFS-01` |
| Name | `MeridiJect Pre-Filled Syringe 1mL` |
| Manufacturing profile | `injectable_ddcp` |
| Device model code | `AUTOINJ-STD-01` (UDI applicable હોય તો) |

**ફ્રન્ટએન્ડ પગલાં:**
1. `/product-master` → **Create** → ડ્રાફ્ટ પ્રોડક્ટ વર્ઝન બનાવો, ઉપરનું ડેટા ભરો.
2. Constituent ઉમેરો (દા.ત. `DRUG` type, role = `bulk_drug`) — ઓછામાં ઓછો એક જરૂરી (combination product હોય તો).
3. "Release" ક્રિયા ચલાવો → સહી સેરેમની → સહી પછી સ્ટેટસ "RELEASED" થવો જોઈએ.
4. Release પહેલાં ટ્રાય કરો: જો કોઈ constituent ન હોય તો Release બ્લોક થવો જોઈએ ("A combination product needs at least one constituent").

**બેકએન્ડ ચકાસણી:** Release ફક્ત DRAFT સ્ટેટસમાંથી જ થાય; એક વાર RELEASED થયા પછી એ જ વર્ઝનમાં ફેરફાર અશક્ય — નવો ફેરફાર જોઈએ તો નવું વર્ઝન બનાવવું પડે (draft → review → release ચક્ર ફરી).

### ૨.૨ Recipe Master (રેસિપી/BMR માસ્ટર)

**હેતુ:** પ્રોડક્ટ કેવી રીતે બનાવવો તેની વિગતવાર સૂચનાઓ — દરેક સ્ટેપ, પેરામીટર (તાપમાન, વજન, સમય), તેની મર્યાદા (min/max), અને કયો પુરાવો જરૂરી છે.

**ઉદાહરણ ડેટા:** Recipe code `REC-PFS-01`, Step `MIX-01` — "Bulk drug mixing", parameter `mixing_temp_c`, target 22, min 18, max 26.

**ફ્રન્ટએન્ડ પગલાં:** `/recipe-master` → નવી recipe family બનાવો → RELEASED પ્રોડક્ટ વર્ઝન સાથે લિંક કરો → સ્ટેપ્સ અને પેરામીટર ઉમેરો → Release કરો.

**બેકએન્ડ ચકાસણી:** રેસિપી version પણ RELEASED પ્રોડક્ટ સાથે જ જોડાયેલ હોવું જોઈએ — draft પ્રોડક્ટ સામે batch ક્યારેય ન બની શકે (batch-execution પેજ પર ચકાસાય છે).

### ૨.૩ Batch Execution (બેચ ઉત્પાદન — સૌથી મુખ્ય મોડ્યુલ)

**હેતુ:** ખરેખર ફેક્ટરી ફ્લોર પર બેચ (ઉત્પાદનનો એક જથ્થો, દા.ત. ૧૦,૦૦૦ સિરીંજ) બનાવવાની શરૂઆતથી અંત સુધીની આખી પ્રક્રિયા — Recipeમાં લખેલ દરેક સ્ટેપ ક્રમમાં પૂરો કરવો, દરેક પેરામીટર રેકોર્ડ કરવો.

**ઉદાહરણ ડેટા:** Batch number `BATCH-2026-0142`, target qty `10000`, uom `EA`, Product = MeridiJect PFS RELEASED વર્ઝન, Recipe = REC-PFS-01 RELEASED વર્ઝન.

**ફ્રન્ટએન્ડ પગલાં:**
1. `/batch-execution` → **Create batch** → RELEASED પ્રોડક્ટ અને RELEASED રેસિપી પસંદ કરો (ડ્રોપડાઉનમાં ડ્રાફ્ટ વર્ઝન દેખાશે નહીં).
2. "Issue batch" ક્રિયા ચલાવો (પ્લાન્ડ → ઇસ્યુડ).
3. "Start batch" ચલાવો (ઇસ્યુડ → ઇન-એક્ઝિક્યુશન).
4. પહેલા સ્ટેપ પર ક્લિક કરો → "Record results" — mixing_temp_c માટે `22` ભરો (min 18 – max 26 ની અંદર) → સહી → સ્ટેપ પૂરો કરો.
5. **નકારાત્મક ટેસ્ટ:** `30` (મર્યાદા બહાર) નાખવાનો પ્રયત્ન કરો — સિસ્ટમે ચેતવણી/ભૂલ આપવી જોઈએ.
6. જરૂર પડે "Hold step" ચલાવો (કારણ સાથે) → ફક્ત તે જ સ્ટેપ અટકે, બાકીની બેચ ચાલુ રહે.
7. બધા સ્ટેપ પૂરા થાય પછી "Mark production complete" ચલાવો.

**બેકએન્ડ ચકાસણી:**
- દરેક સ્ટેપ Recipe માં નક્કી કરેલ ક્રમ (predecessor/successor) પ્રમાણે જ ખૂલે છે — આગળનો સ્ટેપ પૂરો કર્યા વગર પાછળનો સ્ટેપ શરૂ ન થાય.
- દરેક પેરામીટર result, hold, complete — બધું જ "signed act" છે (Document 106 ની સહી પોલિસી પ્રમાણે) — ઓડિટ ટ્રેલમાં signature_id સાથે નોંધાય છે.
- જૂનું legacy `/batches` મોડ્યુલ retire થઈ ગયું છે — હવે ફક્ત `gxp_batch` (batch-execution) જ સાચો રેકોર્ડ છે; DDCP, QC, Packaging, Yield, QA Review, Release — બધા હવે આ જ રેકોર્ડ વાંચે છે.

### ૨.૪ Dispensing (વિતરણ/વેઈંગ)

**હેતુ:** બેચ માટે જરૂરી કાચો માલ (raw material) ગોડાઉનમાંથી બહાર કાઢી, વજન કરી, બેચમાં ઉમેરવાની પ્રક્રિયા — ખોટો જથ્થો કે ખોટો મટીરિયલ લોટ ન વપરાય તેની ખાતરી.

**ઉદાહરણ ડેટા:** Material lot `LOT-DRUG-2026-088`, required qty `5.2 kg`, actual weighed `5.198 kg`.

**ફ્રન્ટએન્ડ પગલાં:** `/dispensing` → બેચ પસંદ કરો → material lot પસંદ કરો (ડ્રોપડાઉનમાં ફક્ત RELEASED લોટ દેખાય) → વજન રીડિંગ નાખો → device ID (વજન કાંટાનું ID) → સહી → સબમિટ.

**બેકએન્ડ ચકાસણી:** REJECTED/QUARANTINE સ્ટેટસવાળા લોટ ડ્રોપડાઉનમાં ન દેખાય તેની ચકાસણી કરો (ફક્ત RELEASED જ). Loss/spill/sample ટ્રાન્ઝેક્શન એક જ કમાન્ડથી નોંધાય છે.

### ૨.૫ Genealogy (વંશાવળી ટ્રેસિંગ)

**હેતુ:** કોઈ ફરિયાદ/રિકોલ આવે તો — "આ ચોક્કસ સિરિયલ નંબરની સિરીંજમાં કયો કાચો માલ (કયો સપ્લાયર, કયો લોટ) વપરાયો હતો?" — તે તરત શોધવા માટે.

**ફ્રન્ટએન્ડ પગલાં:** `/genealogy` → serial number અથવા material lot ID નાખી શોધો → આખું ટ્રી (ઉપર તરફ મટીરિયલ, નીચે તરફ ફિનિશ્ડ પ્રોડક્ટ) દેખાવું જોઈએ.

---

## ભાગ ૩ — QA રિવ્યૂ, રિલીઝ, પેકેજિંગ, યિલ્ડ (WP-03)

### ૩.૧ Line Clearance (લાઇન ક્લિયરન્સ)

**હેતુ:** નવી બેચ શરૂ કરતાં પહેલાં ખાતરી કરવી કે એ જ સાધન/વિસ્તાર પર પાછલી બેચનો કોઈ મટીરિયલ/ઓળખ ચિહ્ન રહી ગયો નથી (ક્રોસ-કન્ટામિનેશન અટકાવવા).

**ફ્રન્ટએન્ડ પગલાં:** `/line-clearance` → વિસ્તાર (area) પસંદ કરો → "Result: Pass/Fail" ચેકલિસ્ટ ભરો (equipment આઇટમ પસંદ કરેલ હોય તો સિસ્ટમ આપોઆપ ચેક કરે કે એ સાધન qualified/calibrated/clean છે કે નહીં) → સહી → Submit.

**બેકએન્ડ ચકાસણી:** Pass કરવાથી area નું ક્લિયરન્સ સ્ટેટસ CLEARED થાય — DDCP અને Packaging બંને આ સ્ટેટસ ચેક કરે છે બેચ શરૂ કરતાં પહેલાં.

### ૩.૨ QA Review

**હેતુ:** બેચ પૂરી થયા પછી, રિલીઝ કરતાં પહેલાં, QA ટીમ આખા બેચ રેકોર્ડ (દરેક સ્ટેપ, દરેક deviation, દરેક પેરામીટર)ની સમીક્ષા કરે — "review by exception" પદ્ધતિથી (ફક્ત જ્યાં સમસ્યા હોય ત્યાં ધ્યાન આપવું).

**ફ્રન્ટએન્ડ પગલાં:** `/qa-review` → બેચ પસંદ કરો → exception summary જુઓ (લાલ = ધ્યાન આપવાની જરૂર) → integrity check જુઓ → Approve/Reject.

**બેકએન્ડ ચકાસણી:** correction (સુધારો) જરૂરી હોય તો મૂળ ડેટા ક્યારેય overwrite થતું નથી — નવો correction રેકોર્ડ બને છે, જૂનું history માં રહે છે.

### ૩.૩ Release (અંતિમ રિલીઝ)

**હેતુ:** બેચને બજારમાં મોકલવાની અંતિમ, કાયદેસર મંજૂરી — સૌથી ઊંચી જવાબદારીવાળી સહી (QA Releaser, QA Reviewer કરતાં અલગ વ્યક્તિ હોવી જ જોઈએ — SoD).

**ફ્રન્ટએન્ડ પગલાં:** `/release` → બેચ સ્કોપ પસંદ કરો → "Eligible for release" (લીલું) દેખાય તો જ Release બટન સક્રિય → `qa.releaser` થી લોગિન કરી સહી કરો.

**બેકએન્ડ ચકાસણી:** `qa.reviewer` એ જ યુઝર release ન કરી શકે (self-approval બ્લોક) — **નકારાત્મક ટેસ્ટ:** `qa.reviewer` થી release કરવાનો પ્રયત્ન કરો → નકારાવો જોઈએ. એક વાર REJECTED/HOLD થયેલ સ્કોપ ફરીથી release/reject ન થઈ શકે (ટર્મિનલ સ્ટેટ).

### ૩.૪ Packaging

**હેતુ:** ફિનિશ્ડ પ્રોડક્ટને ડબ્બા/બોક્સમાં પેક કરી, લેબલ લગાવવાની પ્રક્રિયા, લેબલ કાઉન્ટ રેકોર્ડ કરવો (પછી યિલ્ડ મોડ્યુલ આ કાઉન્ટનો ઉપયોગ મટીરિયલ બેલેન્સ ગણવા કરે છે).

**ફ્રન્ટએન્ડ પગલાં:** `/packaging` → બેચ પસંદ કરો → packaging run શરૂ કરો → label count (દા.ત. `9950` used, `50` rejected) નાખો → સહી → Complete.

### ૩.૫ Yield (યિલ્ડ/મટીરિયલ બેલેન્સ)

**હેતુ:** કેટલો કાચો માલ વપરાયો અને કેટલો ફિનિશ્ડ પ્રોડક્ટ બન્યો — તેનું ગણિત (mass balance) મેળવવું, જેથી કોઈ જથ્થો "ગુમ" ન થાય તેની ખાતરી થાય.

**ફ્રન્ટએન્ડ પગલાં:** `/yield` → બેચ પસંદ કરો → "Evaluate label reconciliation" ચલાવો (Packaging ના લેબલ કાઉન્ટ પરથી આપોઆપ ગણતરી થાય) → જો approved_loss (મંજૂર નુકસાન) 0 નથી, તો કારણ (category + description) ફરજિયાત ભરવું.

**બેકએન્ડ ચકાસણી:** આ ગણતરી ગ્રાહકે વ્યાખ્યાયિત કરેલ tolerance rule વાપરે છે — કોઈ ડિફોલ્ટ pharma tolerance સિસ્ટમમાં built-in નથી (દરેક કંપની અલગ tolerance વાપરે).

---

## ભાગ ૪ — સપ્લાયર, મટીરિયલ અને QC (WP-04)

### ૪.૧ Suppliers (સપ્લાયર માસ્ટર)

**હેતુ:** કંપની જેની પાસેથી કાચો માલ ખરીદે છે તે સપ્લાયરની માહિતી અને મંજૂરી (approval) સ્ટેટસ.

**ઉદાહરણ ડેટા:** Legal name `ChemSource Industries Pvt Ltd`, Supplier code `SUP-CHM-014`, status `approved`.

**ફ્રન્ટએન્ડ પગલાં:** `/suppliers` → **Create** → ડેટા ભરો → સ્ટેટસ approve કરો.

**બેકએન્ડ ચકાસણી:** unapproved સપ્લાયર પાસેથી મટીરિયલ receipt નોંધવો શક્ય છે (block નથી) — પણ સિસ્ટમ `source_not_approved` ડિસ્ક્રેપન્સી (discrepancy) hold આપોઆપ ઉભી કરે છે, જેથી QA ધ્યાન આપે.

### ૪.૨ Materials / Material Receipts (મટીરિયલ પ્રાપ્તિ)

**હેતુ:** ગોડાઉનમાં કાચો માલ આવે ત્યારે — શું આવ્યું, કોના તરફથી, કેટલો જથ્થો, અને પ્રારંભિક તપાસ (visual inspection, CoA દસ્તાવેજ) — તેની નોંધ.

**ઉદાહરણ ડેટા:** PO reference `PO-2026-3311`, gross qty `25 kg`, net qty `24.8 kg`, supplier lot `SCI-88291`, expiry `2027-06-30`.

**ફ્રન્ટએન્ડ પગલાં:** `/material-receipts` → **Create** → ડેટા ભરો → "Examine" ક્રિયા ચલાવો (પરીક્ષણ પરિણામ પ્રમાણે material lot બને છે).

**બેકએન્ડ ચકાસણી:** ડિસ્ક્રેપન્સી (દા.ત. gross ≠ expected, shipment damaged) મળે તો receipt "On hold" સ્ટેટસમાં જાય — QA એ ઉકેલ્યા વગર material lot આગળ વધી ન શકે.

### ૪.૩ Material Lots / Material Specifications

**હેતુ:** દરેક લોટને RELEASED/REJECTED/QUARANTINE સ્ટેટસ — ફક્ત RELEASED લોટ જ ડિસ્પેન્સિંગ/બેચમાં વાપરી શકાય. Material Specification એ સ્વીકૃતિ માપદંડ (acceptance criteria) ની માસ્ટર શીટ છે.

**ફ્રન્ટએન્ડ પગલાં:** `/material-lots` → લોટ પસંદ કરો → disposition (release/reject) ક્રિયા ચલાવો → સહી.

**બેકએન્ડ ચકાસણી:** REJECTED લોટ કોઈ પણ ડાઉનસ્ટ્રીમ મોડ્યુલ (dispensing, inventory reservation) માં પસંદ કરી ન શકાય તેની ખાતરી કરો.

### ૪.૪ Inventory (સ્ટોક વ્યવસ્થાપન)

**હેતુ:** ગોડાઉનમાં કયો મટીરિયલ, કયા લોકેશન પર, કેટલો જથ્થો ઉપલબ્ધ છે — રિઝર્વેશન, ટ્રાન્સફર, સાયકલ કાઉન્ટ, અને વિસંગતતા (discrepancy) સુધારો.

**ફ્રન્ટએન્ડ પગલાં:**
1. Reservation: material પસંદ કરો → qty નાખો → સિસ્ટમ આપોઆપ FEFO (First-Expiry-First-Out) પ્રમાણે લોટ પસંદ કરે (તમે લોટ પસંદ કરતા નથી, ફક્ત મટીરિયલ અને જથ્થો).
2. Adjustment request: વિસંગતતા મળે (ગણતરી vs. actual) તો adjustment request બનાવો.
3. Approve adjustment: **બીજા** યુઝરથી (એ જ યુઝર પોતાની વિનંતી approve ન કરી શકે — SoD) approve કરો.
4. Split/Merge container: એક કન્ટેનરને બે ભાગમાં વહેંચો અથવા બે કન્ટેનર ભેગા કરો.

**બેકએન્ડ ચકાસણી:** self-approval બ્લોક ટેસ્ટ કરો — જે યુઝરે adjustment request કરી હોય એ જ યુઝરથી approve કરવાનો પ્રયત્ન કરો → નકારાવો જોઈએ.

### ૪.૫ QC (ગુણવત્તા નિયંત્રણ પ્રયોગશાળા)

**હેતુ:** સેમ્પલ ટેસ્ટ કરવો (દા.ત. પોટેન્સી, શુદ્ધતા), પરિણામ નોંધવું, અને Pass/Fail/OOS (Out Of Specification) નક્કી કરવું.

**ઉદાહરણ ડેટા:** QC sample `QC-2026-0521`, method `HPLC-ASSAY-001`, result value `99.2%` (spec: 95–105%).

**ફ્રન્ટએન્ડ પગલાં:** `/qc` → test order બનાવો → test run શરૂ કરો → result નાખો → બીજા યુઝરથી review કરો (પોતે result નોંધનાર વ્યક્તિ review ન કરી શકે) → OOS મળે તો investigation ટ્રિગર થાય.

**બેકએન્ડ ચકાસણી:** result correction માટે — મૂળ result બદલાતું નથી, નવો "correction request" બને છે જે અલગ વ્યક્તિએ approve કરવો પડે.

### ૪.૬ Rules / UOM (એકમ રૂપાંતરણ અને ગણતરી નિયમો)

**હેતુ:** `kg` થી `mg`, `L` થી `mL` જેવા એકમ રૂપાંતરણ, અને પોટેન્સી/યિલ્ડ જેવા ગ્રાહક-વ્યાખ્યાયિત ગણતરી નિયમો.

**ફ્રન્ટએન્ડ પગલાં:** `/rules` → નવો UOM અથવા UOM conversion draft બનાવો → "Simulate" (ટેસ્ટ ઇનપુટ સાથે ચલાવીને જુઓ, કંઈ regulated ડેટા લખાતું નથી) → Release.

---

## ભાગ ૫ — ગુણવત્તા વ્યવસ્થાપન સિસ્ટમ (QMS, WP-05)

આ બધા મોડ્યુલ (`Deviations`, `CAPA`, `Changes`, `Nonconformances`, `Complaints`, `Risks`, `Internal Audits`, `Field Actions`, `Supplier Cases`) એક સરખા ઢાંચે (Raise → Investigate → Disposition → Close) કામ કરે છે.

### ૫.૧ Deviations (વિચલન)

**હેતુ:** કંઈક પ્રક્રિયા પ્રમાણે ન થયું હોય (દા.ત. તાપમાન મર્યાદા બહાર ગયું) ત્યારે ઔપચારિક રીતે નોંધવું, તપાસવું, અને અસર (impact) નક્કી કરવી.

**ઉદાહરણ ડેટા:** Deviation number `DEV-2026-0033`, type `process`, source = બેચ `BATCH-2026-0142`, severity `major`.

**ફ્રન્ટએન્ડ પગલાં:** `/deviations` → **Raise deviation** → source type પસંદ કરો (batch/qc/material/equipment) → source record પસંદ કરો (ડ્રોપડાઉનમાંથી, અથવા manual ID જો એ પ્રકાર માટે લિસ્ટ ન હોય) → severity/type ભરો → Submit → Triage → Investigation → Root cause → Disposition → Close.

**બેકએન્ડ ચકાસણી:** `capa_required = true` હોય તો CAPA મોડ્યુલમાં લિંક દેખાવો જોઈએ; Closed થયા પછી ફરી ખોલવા માટે "Reopen" ક્રિયા (નવું કારણ સાથે) જ વાપરી શકાય.

### ૫.૨ CAPA (સુધારાત્મક/નિવારક ક્રિયા)

**હેતુ:** Deviation/Complaint નું મૂળ કારણ (root cause) શોધ્યા પછી, ફરી ન થાય તે માટે કાયમી સુધારો કરવો.

**ફ્રન્ટએન્ડ પગલાં:** `/capa` → deviation માંથી લિંક થયેલ CAPA ખોલો → root cause, corrective action, preventive action, effectiveness plan ભરો → Approve → પછી ચોક્કસ સમય પછી effectiveness check કરો.

### ૫.૩ Changes (ચેન્જ કંટ્રોલ)

**હેતુ:** પ્રક્રિયા/સાધન/દસ્તાવેજમાં કોઈ ફેરફાર કરતાં પહેલાં — તેની અસર (impact) આકારણી (regulatory, validation, training) અને મંજૂરી.

**ફ્રન્ટએન્ડ પગલાં:** `/changes` → current state vs proposed state ભરો → impact assessment (regulatory/validation/training) → Approve → Implement → Retrospective review.

### ૫.૪ Nonconformances

**હેતુ:** કોઈ પ્રોડક્ટ/મટીરિયલ સ્પષ્ટીકરણ (specification) પ્રમાણે ન મળે ત્યારે — rework/reject/use-as-is નિર્ણય.

**ફ્રન્ટએન્ડ પગલાં:** `/nonconformances` → affected scope + serials નાખો → evaluation → disposition (rework route ફરજિયાત જો rework પસંદ કરો તો).

### ૫.૫ Complaints (ફરિયાદ)

**હેતુ:** ગ્રાહક/ડોક્ટર તરફથી આવેલ ફરિયાદ — triage, investigation, અને જરૂર પડે postmarket safety case સાથે લિંક.

**ફ્રન્ટએન્ડ પગલાં:** `/complaints` → complainant info, lot/batch/serial ref નાખો → triage → investigation findings → conclusion.

### ૫.૬ Risks (જોખમ વ્યવસ્થાપન)

**હેતુ:** સંભવિત જોખમનું સ્કોરિંગ (probability × severity), નિયંત્રણ (controls) લગાવવા, અને accept/mitigate નિર્ણય.

**ફ્રન્ટએન્ડ પગલાં:** `/risks` → context ભરો → initial score → controls ઉમેરો → residual score → acceptance.

### ૫.૭ Training (તાલીમ)

**હેતુ:** દરેક કર્મચારીએ પોતાનું કામ કરવા માટે જરૂરી SOP/પ્રક્રિયાની તાલીમ લીધી છે કે નહીં તેનો રેકોર્ડ.

**ફ્રન્ટએન્ડ પગલાં:** `/training` → subject ID નાખી (અથવા "મારું પોતાનું" બટનથી) status જુઓ → જો pending હોય તો waiver (મુક્તિ) નોંધી શકાય (કારણ સાથે).

### ૫.૮ Documents (દસ્તાવેજ નિયંત્રણ)

**હેતુ:** SOP/દસ્તાવેજના વર્ઝન — ફેરફાર થાય તો training impact આકારણી કરવી પડે.

**ફ્રન્ટએન્ડ પગલાં:** `/documents` → document code નાખી versions જુઓ.

### ૫.૯ Field Actions / Supplier Cases / Quality Metrics / OOS

- **Field Actions:** પ્રોડક્ટ રિકોલ/ફિલ્ડ કરેક્શન — trigger, reportability assessment, effectiveness check.
- **Supplier Cases:** સપ્લાયર તરફથી આવેલ ખરાબ મટીરિયલનો કેસ — containment, supplier root cause, approved-supplier-list impact.
- **Quality Metrics:** KPI ડેશબોર્ડ (deviation rate, CAPA on-time %, વગેરે).
- **OOS (Out Of Specification):** QC પરિણામ સ્પષ્ટીકરણ બહાર આવે ત્યારે ઔપચારિક તપાસ — હાલમાં કોઈ યાદી (list) endpoint નથી, એટલે OOS ID થી સીધું શોધવું પડે.

---

## ભાગ ૬ — સાધનસામગ્રી, સ્ટરાઇલ અને એજ (WP-06)

### ૬.૧ Equipment (સાધનસામગ્રી)

**હેતુ:** દરેક મશીન/સાધનનું calibration, qualification, અને maintenance સ્ટેટસ — Line Clearance અને DDCP બંને આ ચેક કરે છે.

**ફ્રન્ટએન્ડ પગલાં:** `/equipment` → સાધન પસંદ કરો → calibration due date, qualification status જુઓ → maintenance work order નોંધો (parts used સાથે).

### ૬.૨ Sterilization / Aseptic (સ્ટરાઇલાઇઝેશન)

**હેતુ:** ઇન્જેક્ટેબલ પ્રોડક્ટ માટે સાધન/કન્ટેનર જંતુરહિત (sterile) કરવાની પ્રક્રિયા (CIP/SIP સાયકલ) અને ફિલ્ટર ઇન્ટિગ્રિટી ટેસ્ટ.

**ફ્રન્ટએન્ડ પગલાં:** `/sterilization` → cycle શરૂ કરો → parameter data (temp/pressure/time) નોંધો → indicator result → Complete (ફક્ત post-use ટેસ્ટ રેકોર્ડ થયેલ હોય તો જ complete થઈ શકે).

### ૬.૩ EM (Environmental Monitoring)

**હેતુ:** ક્લીનરૂમમાં હવા/સપાટીમાં માઇક્રોબાયલ કાઉન્ટ મોનિટર કરવું.

**ફ્રન્ટએન્ડ પગલાં:** `/em` → location + sample પસંદ કરી પરિણામ જુઓ → trends (સમય જતાં ટ્રેન્ડ) જુઓ.

### ૬.૪ Cleaning / Line Clearance

જુઓ ભાગ ૩.૧ (Line Clearance). Cleaning મોડ્યુલ સાધનની cleaning validation/log રાખે છે.

### ૬.૫ Edge / Devices / Machine Integration

**હેતુ:** ફેક્ટરી ફ્લોર પરના મશીન (PLC/SCADA) સીધા સિસ્ટમ સાથે જોડાયેલ હોય ત્યારે — સિગ્નલ મેપિંગ, ડિવાઇસ સિરિયલ લુકઅપ, ગેટવે એનરોલમેન્ટ.

**ફ્રન્ટએન્ડ પગલાં:** `/devices` → સિરિયલ નંબરથી ડિવાઇસ શોધો → release readiness જુઓ. `/edge` → gateway enroll કરો → certificate rotate કરો.

**નોંધ:** આ modules નું અમુક ભાગ (machine-to-machine credential) ફક્ત મશીન માટે છે, માણસ માટે UI નથી — એ જાણી જોઈને એ રીતે બનાવેલ છે.

---

## ભાગ ૭ — ERP/LIMS ઇન્ટિગ્રેશન (WP-07)

**હેતુ:** કંપનીના હાલના ERP (SAP વગેરે) અને LIMS (લેબ સિસ્ટમ) સાથે ડેટા સિંક — પણ eBMR પોતે જ સત્તાવાર (authoritative) રહે છે, ERP/LIMS ફક્ત integrate થાય છે.

**ફ્રન્ટએન્ડ પગલાં:** `/integrations/erp` → sync command મોકલો → જો કોઈ ડિસ્પેચ crash પછી અટકી ગયો હોય (`DISPATCHED` સ્ટેટસ) તો reconcile ચલાવો.

**બેકએન્ડ ચકાસણી:** reversal (પાછું ફેરવવું) ક્યારેય જૂનો રેકોર્ડ ભૂંસતું નથી — નવો command બને છે જે મૂળ GxP નિર્ણય સાથે જોડાયેલ રહે છે.

---

## ભાગ ૮ — DDCP (Device/Drug Combination Product, WP-08)

**હેતુ:** સંયોજન પ્રોડક્ટ (દવા + ડિવાઇસ, જેમ કે pre-filled syringe, autoinjector, inhaler, coated device) માટે ખાસ execution — handoff (ઘટકોનું હસ્તાંતરણ), filling, assembly, testing, counts.

**ઉદાહરણ ડેટા:** Family = Pre-filled syringe, Batch = `BATCH-2026-0142`, handoff — constituent `bulk_drug`, source lot = `LOT-DRUG-2026-088`.

**ફ્રન્ટએન્ડ પગલાં:**
1. `/ddcp` → Product family પસંદ કરો → profile (RELEASED Product Master વર્ઝન સાથે) પસંદ કરો.
2. "Readiness" તપાસો (EM/Line clearance/Equipment eligibility — ત્રણેય લીલા હોવા જોઈએ).
3. Handoff રેકોર્ડ કરો → Accept/Decide.
4. Fill operation શરૂ કરો → counts (FILLED/REJECTED_VISUAL વગેરે) નોંધો → Finish fill.
5. Assembly step રેકોર્ડ કરો → બીજા યુઝરથી verify કરો (IND-001: જેણે કર્યું એ પોતે verify ન કરી શકે).
6. Genealogy અને Review summary જુઓ.

**બેકએન્ડ ચકાસણી:** manufacturing profile match ચકાસો — દા.ત. injectable profile ફક્ત `injectable_ddcp` profile ધરાવતા પ્રોડક્ટ સાથે જ કામ કરે.

---

## ભાગ ૯ — Postmarket Surveillance (WP-09)

**હેતુ:** પ્રોડક્ટ બજારમાં ગયા પછી સેફ્ટી કેસ, સિગ્નલ ડિટેક્શન, અને નિયમનકારી રિપોર્ટિંગ (MDR 30/5 day, Part 4).

**ફ્રન્ટએન્ડ પગલાં:** `/postmarket` → safety case વર્ગીકૃત કરો (classification) → follow-up ઉમેરો → reportability decision (બે અલગ-અલગ સહી જરૂરી — independent second signature) → જો reportable હોય તો regulatory report ફાઇલ કરો, deadline ક્લોક જુઓ.

**બેકએન્ડ ચકાસણી:** correction/removal ની independent approval માટે — assessment કરનાર અને approve કરનાર બે અલગ વ્યક્તિ હોવી જ જોઈએ.

---

## ભાગ ૧૦ — સિક્યુરિટી (WP-10)

**હેતુ:** થ્રેટ મોડલ, જોખમ ઓપરેશન્સ, ઓળખ/સેશન વ્યવસ્થાપન, સિક્યુરિટી ઘટના (incident), vulnerability, અને privileged access વિનંતી.

**ફ્રન્ટએન્ડ પગલાં:** `/security` → incident રિપોર્ટ કરો → vulnerability રજિસ્ટર કરો → privileged access વિનંતી કરો (સહી સાથે, ટાઇમ-બાઉન્ડ).

---

## ભાગ ૧૧ — વેલિડેશન (WP-12)

**હેતુ:** સિસ્ટમ પોતે (સોફ્ટવેર) યોગ્ય રીતે કામ કરે છે તેનું ઔપચારિક પ્રમાણ — migration વેલિડેશન, go-live checklist.

**ફ્રન્ટએન્ડ પગલાં:** `/validation` → test execution રેકોર્ડ કરો. `/validation/go-live` → દરેક migrated data class માટે tolerance rule ફરજિયાત → VSR (Validation Summary Report) row — FAIL outcome હોય તો rollback reference ફરજિયાત.

---

## ભાગ ૧૨ — AI Advisory (WP-13)

**હેતુ:** AI ફક્ત **સલાહકાર** (advisory) છે — તે ક્યારેય સહી કરી શકતું નથી, રિલીઝ/ડિસ્પોઝિશન નિર્ણય લઈ શકતું નથી, ઓડિટ બદલી શકતું નથી. AI ની ગેરહાજરી ક્યારેય કોઈ regulated પ્રક્રિયાને અટકાવતી નથી.

**ફ્રન્ટએન્ડ પગલાં:** `/ai` → use case ID થી લુકઅપ કરો → advisory પરિણામ જુઓ (તે ફક્ત સૂચન છે, અંતિમ નિર્ણય માણસ જ લે છે).

---

## પરિશિષ્ટ — સામાન્ય નકારાત્મક (negative) ટેસ્ટ, જે દરેક મોડ્યુલમાં અજમાવવા

1. **ખોટી પરમિશન:** ઓછા અધિકારવાળા યુઝરથી લખવાની ક્રિયા (write action) ટ્રાય કરો → `403` મળવો જોઈએ.
2. **Self-approval:** જે યુઝરે વિનંતી કરી હોય એ જ યુઝરથી મંજૂરી ટ્રાય કરો → નકારાવું જોઈએ (SoD).
3. **ખોટું Expected version:** કોઈ રેકોર્ડ પર જૂનું version નંબર આપી ફેરફાર ટ્રાય કરો → `409 Conflict` (optimistic concurrency) મળવો જોઈએ.
4. **સહી વગર:** સહી જરૂરી હોય એવી ક્રિયા API થી સીધી (UI બાયપાસ કરીને) ટ્રાય કરો → નકારાવી જોઈએ.
5. **સહી પોલિસી ન હોય:** અમુક નવી ક્રિયા માટે હજુ સહી પોલિસી ડેટાબેઝમાં ઉમેરાઈ ન હોય તો — `SIGNATURE_POLICY_UNRESOLVED` ભૂલ સાથે યોગ્ય રીતે અટકવું જોઈએ (silently પાસ ન થવું જોઈએ). UI માં આ કિસ્સો પીળા Banner તરીકે અગાઉથી જ બતાવેલ હોય છે.
6. **ડુપ્લિકેટ સબમિટ:** એક જ idempotency key થી બે વાર સબમિટ કરો → બીજી વાર નવો રેકોર્ડ ન બનવો જોઈએ (એ જ પરિણામ પાછું મળવું જોઈએ).
7. **ઓડિટ ચકાસણી:** ઉપરની દરેક ક્રિયા પછી `/audit` પર જઈ ખાતરી કરો કે નવી એન્ટ્રી બની, actor સાચો છે, અને hash chain તૂટી નથી.
