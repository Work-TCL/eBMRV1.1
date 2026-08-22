# NZ-eBMR — Real-World Demo (ગુજરાતીમાં): રેસીપીથી રિલીઝ સુધી, સાચા આંકડા સાથે

**આ ડોક્યુમેન્ટ કેમ:** તમે કહ્યું — "તમે ચા બનાવો છો એમ વિચારો: પહેલા રેસીપી, પછી
સ્ટેપ બાય સ્ટેપ પ્રોસેસ." આ ડોક્યુમેન્ટ બરાબર એ જ રીતે લખેલું છે — એક જ પ્રોડક્ટ,
શરૂઆતથી અંત સુધી, **દરેક જગ્યાએ સાચા આંકડા** (કાલ્પનિક નહીં — જે UI માં ખરેખર ટાઈપ
થયેલા છે એ જ). `DDCP-ROLE-FLOW-GUJARATI.md` role-login ને સમજાવે છે; આ ડોક્યુમેન્ટ
**એક પ્રોડક્ટની આખી જિંદગી** સમજાવે છે — રેસીપી કોણે લખી, કેટલું મટીરીયલ જોઈએ, batch
કેવી રીતે બન્યો, અને છેલ્લે release કેવી રીતે થયો.

**પ્રોડક્ટ જેની વાત કરીશું:** EpiRelease Auto-Injector 0.3mg (કોડ: **EPIREL-03**) —
એક drug-device combination product. Epinephrine (દવા) + Auto-Injector (ડિવાઇસ)
= એક ready-to-use ઈન્જેક્શન પેન.

---

## તા-નો દાખલો, પ્રોડક્ટ પર લાગુ કરીને

| ચા બનાવવામાં | EpiRelease બનાવવામાં |
|---|---|
| રેસીપી: 1 કપ પાણી + 1 ચમચી ચા-પત્તી + 1 ચમચી ખાંડ | રેસીપી (Integrated Master v1.5): 0.30 mL Epinephrine + 1 Auto-Injector શેલ + 1 લેબલ + 1 કાર્ટન + 1 leaflet — **દરેક એક યુનિટ માટે** |
| 10 કપ ચા બનાવવી છે? → 10 કપ પાણી, 10 ચમચી પત્તી, 10 ચમચી ખાંડ | 4,000 યુનિટનો ઓર્ડર? → 1,200.000 mL Epinephrine, 4,000 ડિવાઇસ, 4,000 લેબલ, 4,000 કાર્ટન, 4,000 leaflet |
| રેસીપી કોઈ પણ લખી શકે, પણ ઘરમાં "આજે આ જ રેસીપી વાપરવી" કોણ નક્કી કરે? | રેસીપી S. Bloom લખે, પણ "આ effective છે, વાપરી શકાય" — એ P. Nair (Quality) નક્કી કરે, જુદી સહી સાથે |
| ચા ખરાબ બને તો ફેંકી દો | Auto-Injector માં ખામી નીકળે તો "Cross-constituent issue" ખૂલે, batch અટકે, તપાસ થાય |

આ સામ્યતા યાદ રાખો — આખા ડોક્યુમેન્ટમાં આ જ ચાર વસ્તુ વારંવાર આવશે: **રેસીપી → સ્કેલ
(scale) → બેચ → એક્ઝિક્યુશન**.

---

## પાત્રો (Real people, real roles)

| નામ | ભૂમિકા | શું કરે |
|---|---|---|
| **L. Park** | Configuration Administrator | Organisation સેટ કરે — sites, users, roles, products, materials, equipment |
| **S. Bloom** | Integrated Master Team | રેસીપી લખે — compatibility pairing, per-unit BOM, process steps |
| **T. Alvarez** | Regulatory/Admission Owner | Admission &amp; Part 4 route લખે — regulatory classification |
| **M. Chen** | Planner/Batch Issuer | Approved રેસીપી સામે final assembly order (batch) બનાવે અને issue કરે |
| **A. Desai** | Production Supervisor | Line clearance જેવી readiness બાબતો સંભાળે |
| **M. Ortiz** | Filling/Assembly Operator | ફિલિંગ, એસેમ્બલી, લેબલિંગ — shop floor નું ખરું કામ |
| **H. Novak** | Integrated Test Performer | Dose-delivery testing કરે — Operator અને Quality વચ્ચેની ભૂમિકા |
| **J. Kwan** | Cross-constituent Investigation | જ્યારે drug+device બંનેને અસર કરતી સમસ્યા થાય ત્યારે તપાસ કરે |
| **P. Nair** | Quality Master Approver **અને** Final Release Authority | રેસીપી approve કરે (પહેલા) **અને** final batch release કરે (છેલ્લે) — બે અલગ સહી, બે અલગ સમયે |

**નોંધ:** role-select સ્ક્રીન પર ૫ card છે (Admin, Recipe Author, Planner, Operator,
Quality) — પણ ઉપરના ટેબલમાં ૯ વ્યક્તિ છે. "Recipe Author" card એક સાથે S. Bloom
અને T. Alvarez બંનેને represent કરે છે (team). "Quality" card P. Nair ને represent
કરે છે, પણ testing.html પર ખરેખર કામ કરનાર વ્યક્તિ H. Novak દેખાય છે — sidebar lock
role-picker પ્રમાણે થાય છે, પણ **દરેક સ્ક્રીન પર context bar માં એ કામ ખરેખર કોણે
કર્યું એ સાચું, ચોક્કસ નામ જ દેખાય છે.** આ demo ની એક પ્રામાણિક મર્યાદા છે — client ને
કહેવા જેવી વાત.

---

# ભાગ ૧ — રેસીપી (Integrated Master) કેવી રીતે બને છે

### 1.1 — Admission & Part 4 (પહેલું પગલું)

**સ્ક્રીન:** `combination/admission.html` | **વ્યક્તિ:** T. Alvarez

**શું થાય:** ૬ facts ચેક થાય છે — ૫ પહેલેથી Accepted:
1. Combination type — prefilled drug delivery device (dossier RD-088) ✓
2. PMOA / application context (21 CFR Part 3) ✓
3. Drug constituent identity — Epinephrine 0.3mg Solution, master v2.1 ✓
4. Device constituent identity — Auto-Injector AI-40 Rev B, master Rev B ✓
5. Part 4 route version — 21 CFR Part 4, v2.0 ✓
6. **Applicable exclusions — Missing** ✗ (આ એક જ વસ્તુ બાકી છે)

"Approve admission" બટન **લૉક** છે. કારણ: ટેક્સ્ટમાં જ લખેલું — "Unresolved Critical
questions route to the Regulatory reviewer, not the preparer." એટલે કે તૈયાર
કરનાર વ્યક્તિ પોતે "ચાલશે" કહી ન શકે.

**ટેસ્ટ કેસ:**
| પગલું | અપેક્ષિત |
|---|---|
| પેજ ખોલો | "5 of 6 complete", Approve બટન disabled |
| "Record exclusions — none apply to this route" બટન દબાવો | Row 6 નું state "Missing" → "Accepted" થાય |
| પછી "Approve admission" | હવે enabled — ક્લિક કરી શકાય |

**કેમ આ પહેલું પગલું છે:** જ્યાં સુધી regulatory route નક્કી ન થાય ત્યાં સુધી —
compatibility, રેસીપી, બેચ — કંઈ જ શરૂ ન થઈ શકે. eBMR માં આ "sequence lock" છે,
UI ની સજાવટ નથી.

### 1.2 — Compatibility & Handoff (બીજું પગલું)

**સ્ક્રીન:** `combination/compatibility.html` | **વ્યક્તિ:** S. Bloom

**શું થાય:** બે constituent ની ચોક્કસ ઓળખ સરખાવાય — free-text નામ નહીં, પણ master
version સામે:
- Drug: Epinephrine 0.3mg Solution · Master v2.1 — Approved
- Device: Auto-Injector AI-40, Rev B · Master Rev B — Approved

પછી ૩ interface restriction ચેક થાય:
1. Cartridge fill volume ≤ 0.35 mL (spec DEV-CH-04) — Compatible ✓
2. Contact material — Type I borosilicate only (study EL-2024-09) — Compatible ✓
3. **Needle gauge 25G ± tolerance (drawing DWG-AI40-07 rev C) — Drawing under revision** ✗

**ટેસ્ટ કેસ:**
| પગલું | અપેક્ષિત |
|---|---|
| "Approve pairing" દબાવો (ડ્રોઈંગ ઠીક કર્યા વગર) | Locked — reason: "needle gauge compatibility is stale" |
| "Confirm revised drawing DWG-AI40-07 rev D received" દબાવો | State "Drawing under revision" → "Compatible" |
| પછી "Approve pairing" | Enabled |

**કેમ ૦.૩૫ mL ની limit અગત્યની:** device chamber ફક્ત ૦.૩૫ mL સુધી લઈ શકે. આપણી
રેસીપીમાં ૦.૩૦ mL વાપરવાનું છે — સીમાની અંદર, પણ સીમા ક્યાં છે એ પહેલા નક્કી કરવું
પડે, પછી જ રેસીપીમાં એ આંકડો લખાય.

### 1.3 — Integrated Master Editor (રેસીપી ખરેખર લખાય છે અહીં)

**સ્ક્રીન:** `combination/integrated-master.html` | **વ્યક્તિ:** S. Bloom

**આ સૌથી અગત્યનું પેજ છે — અહીં ખરી "રેસીપી" લખાય છે.**

**Per-unit Bill of Materials — એક EpiRelease માટે બરાબર આટલું જોઈએ:**

| Material | એક યુનિટ માટે | સ્ત્રોત |
|---|---|---|
| Epinephrine 0.3mg Solution | **0.30 mL** | Drug constituent · Master v2.1 |
| Auto-Injector AI-40, Rev B | **1 unit** | Device constituent · Master Rev B |
| Final presentation label (LBL-EPI) | **1 pc** | — |
| Final carton (CTN-EPI) | **1 pc** | — |
| Patient information leaflet (PIL-EPI) | **1 pc** | — |

**Live calculator — સ્ક્રીન પર ખરેખર કામ કરે છે:** પેજ પર "Preview at order size"
નામનું ફિલ્ડ છે, default ૪,૦૦૦. તેમાં કોઈ પણ સંખ્યા નાખો, "Required" કોલમ તરત જ બદલાય:

| Order size | Epinephrine જોઈએ | Auto-Injector જોઈએ | Label/Carton/Leaflet જોઈએ |
|---|---|---|---|
| 4,000 (default) | 1,200.000 mL | 4,000 units | 4,000 pcs દરેક |
| 10,000 (ટેસ્ટ કરેલું) | 3,000.000 mL | 10,000 units | 10,000 pcs દરેક |
| 1 (એક જ યુનિટ) | 0.300 mL | 1 unit | 1 pc દરેક |

ગણતરી: **0.30 mL × ઓર્ડર સાઈઝ = કુલ mL જોઈએ.** આ જ ગણતરી "Create a final assembly"
wizard નું Step 3 automatically કરે છે — ફર્ક એટલો કે ત્યાં operator ને ફક્ત જવાબ
દેખાય છે, અહીં author ને ફોર્મ્યુલા દેખાય છે.

**પ્રોસેસ સ્ટેપ — રેસીપી માત્ર મટીરીયલ નથી, પ્રોસેસ પણ છે:**
1. OP-010 — Constituent handoff (drug + device બંને accept થાય)
2. OP-020 — Filling / loading (0.30 mL ભરાય)
3. OP-030 — Assembly (device + drug જોડાય)
4. OP-040 — Integrated testing
5. OP-050 — Labeling & reconciliation

**Critical specifications:**
- Fill volume: 0.30 mL, limit 0.29–0.31 mL — **પૂરું, approval માટે તૈયાર**
- Torque spec: 2.4–2.8 — **"unit not set" ચેતવણી** (N·m લખવાનું ભૂલાયું છે)

**ટેસ્ટ કેસ:**
| પગલું | અપેક્ષિત |
|---|---|
| "Preview at order size" માં 10000 લખો | બધા rows ની "Required" column બદલાય — Epinephrine 3,000.000 mL, બાકી બધું 10,000 |
| ફિલ્ડ ખાલી કરો | બધું 0 બતાવે (કંઈ crash ન થાય) |
| "Save draft" દબાવો | Toast: "Draft saved — demo only, nothing stored." |
| "Continue to recipe approval" | `recipe-approval.html` પર જાય |

**યાદ રાખો:** torque spec ની "unit not set" ચેતવણી અહીં **non-blocking** (ચેતવણી
માત્ર) છે — પણ Recipe Approval સ્ક્રીન પર એ જ ખામી **blocking** (અટકાવનારી) બની જાય
છે. એક જ હકીકત, બે જગ્યાએ, બે અલગ ગંભીરતા — આ deliberate design છે.

### 1.4 — Recipe Catalogue

**સ્ક્રીન:** `combination/recipe-catalogue.html` | **વ્યક્તિ:** S. Bloom / P. Nair

આ organisation એ ક્યારેય લખેલા **બધા** Integrated Master version ની યાદી:

| Product | Version | Effective from | Status |
|---|---|---|---|
| EpiRelease Auto-Injector 0.3mg | v1.4 | 22 Jul 2026 | **Effective** |
| EpiRelease Auto-Injector 0.3mg | v1.5 | — | Under review (draft — આપણે અહીં જ છીએ) |
| EpiRelease Auto-Injector 0.5mg | v1.0 | — | Draft |
| EpiRelease Auto-Injector 0.3mg | v1.3 | Superseded | Obsolete |

**અગત્યનો નિયમ:** એક જ સમયે **એક જ** version Effective હોઈ શકે. Planner (M. Chen)
જ્યારે batch બનાવે ત્યારે ફક્ત v1.4 પસંદ કરી શકે — v1.5 ગમે તેટલું આગળ વધ્યું હોય,
પસંદ કરવા માટે ઉપલબ્ધ જ નથી (radio button disabled). "Create new version" બટન પણ
locked છે — કારણ v1.5 draft પહેલેથી ચાલુ છે.

### 1.5 — Recipe Approval (રેસીપીની સહી — batch ની સહીથી અલગ)

**સ્ક્રીન:** `combination/recipe-approval.html` | **વ્યક્તિ:** P. Nair

**Checklist — ૬ માંથી ૫ પૂરું:**
1. Admission & Part 4 route approved — T. Alvarez, 04 Aug 2026 ✓
2. Constituent compatibility approved — S. Bloom, 04 Aug 2026 ✓
3. Per-unit bill of materials complete — 5 material lines ✓
4. Process steps defined — 5 steps ✓
5. Fill volume specification — 0.29–0.31 mL ✓
6. **Torque specification — unit not recorded ✗** (ઉપર editor માં જોયેલી એ જ ચેતવણી, હવે blocking)

**ટેસ્ટ કેસ:**
| પગલું | અપેક્ષિત |
|---|---|
| PIN ભરીને sign કરવાનો પ્રયત્ન કરો (torque ઠીક કર્યા વગર) | Button disabled — click જ ન થાય |
| "Correct torque spec unit to N·m in the editor" દબાવો | Torque row "Incomplete" → "Complete" |
| PIN ખાલી રાખીને "Sign & make effective" દબાવો | Blocked — PIN ફરજિયાત |
| PIN ભરો (દા.ત. 552341), ફરી દબાવો | v1.5 "Version history" ટેબલમાં ઉમેરાય, status "Effective" |

**સૌથી અગત્યનું વાક્ય, જે client ને કહેવા જેવું:**
> "P. Nair અહીં રેસીપી approve કરે છે — હજુ સુધી કોઈ batch બન્યો જ નથી. પછી, જ્યારે
> ખરો batch બનશે અને પૂરો થશે, ત્યારે P. Nair જ ફરીથી સહી કરશે — પણ **અલગ સ્ક્રીન
> પર, અલગ સમયે, અલગ પુરાવા સામે.** આ બે અલગ સહી છે, ભલે વ્યક્તિ એક જ હોય."

---

# ભાગ ૨ — રેસીપી પરથી બેચ (Final Assembly Order) બને છે

**સ્ક્રીન:** `combination/new-batch.html` | **વ્યક્તિ:** M. Chen (Planner)

હવે v1.5 નહીં — v1.4 (Effective) સામે ઓર્ડર બનાવીશું, કારણ v1.5 હજુ પણ demo માં
draft જ છે સિવાય કે તમે ઉપરનું approval step ચલાવો.

### Step 1 — શું બનાવવું
v1.4 (Effective) પસંદ કરી શકાય; v1.5 (draft) "Cannot be used" દેખાય.

### Step 2 — ઓર્ડરની વિગત
- Order number: **FA-33211** (system આપોઆપ આપે, બદલી ન શકાય)
- Quantity: **4,000 units**
- Site/Line: Site 3 — Line C

### Step 3 — Materials & lots — અહીં રેસીપીનું ગણિત ખરેખર વપરાય છે

ભાગ ૧.૩ ની per-unit રેસીપી × 4,000 = બરાબર આ ટેબલનો "Required" કોલમ (real data,
પહેલેથી UI માં છે). આ સ્ક્રીન પર ફક્ત **required** (કેટલું જોઈએ) દેખાય છે — lot
પસંદ કરવાનું અહીં થાય, "ખરેખર કેટલું વપરાયું" એ પછીથી, labeling સ્ક્રીન પર reconcile
થાય છે (નીચે ભાગ 3.3):

| Material | Lot | Required |
|---|---|---|
| Epinephrine 0.3mg solution (DRG-0142) | B-2026-0142 | **4,000 fills** |
| Auto-Injector AI-40 Rev B (DEV-77102) | SL-77102 | **4,000 units** |
| Final presentation label (LBL-EPI) | LOT-E221 | **4,000** |
| Final carton (CTN-EPI) | LOT-C880 | **4,000** |

જુઓ — **1,200.000 mL** (રેસીપી ગણતરી, ભાગ ૧.૩) = **4,000 fills** (અહીં required)
ની બરાબર વાત, ફક્ત જુદા એકમમાં લખેલી (mL ને બદલે "fills" ગણેલા, કારણ ઓપરેટર માટે
"કેટલી વાર ભરવું" વધુ સીધું છે). "ખરેખર કેટલું વપરાયું અને કેટલું નકામું ગયું"
(3,996 વપરાયું, 4 reject) — એ સંખ્યા આ સ્ક્રીન પર નથી, **labeling.html** પર છે,
કારણ ઓર્ડર વખતે તમે ફક્ત "કેટલું જોઈએ" નક્કી કરો છો; "કેટલું ખરેખર વપરાયું" તો કામ
પૂરું થાય પછી જ ખબર પડે.

### Step 4 — Readiness (અહીં સિસ્ટમ ના પાડે છે)

**Blocker:** "B-2026-0142: Constituent batch not yet released by the Quality Unit."
દવાનો batch (Epinephrine) પોતે જ હજુ Quality Unit દ્વારા release નથી થયો — તો એના
પર combination product કેવી રીતે બને?

**ટેસ્ટ કેસ:** "Recheck readiness" દબાવો → "The Quality Unit released B-2026-0142
at 08:47" → blocker clear → આગળ વધાય.

### Step 5 — Review & Issue

PIN વગર સહી ન થાય. PIN ભરીને સહી કરો → **FA-33211** "Issued final assembly orders"
યાદીમાં ઉમેરાય. હવે આ **જીવંત regulated record** છે.

---

# ભાગ ૩ — Execution: ખરેખર બનાવવાનું (real numbers, step by step)

### 3.1 — Filling & Assembly

**સ્ક્રીન:** `combination/filling.html` | **વ્યક્તિ:** M. Ortiz

- Destination device સ્કેન: `DEV-77102 / AI-40 Rev B`
- Source batch સ્કેન: `SRC-0142`
- **Fill volume ટાઈપ કરવાનું: 0.30 mL** (limit 0.29–0.31 mL — within range)
- Equipment: **Fill station FS-8** (એ જ FS-8 જેનો asset record આપણે setup માં જોયો)

**Independent verification:** "Awaiting a second identity" — M. Ortiz પોતે verify
ન કરી શકે. બીજી વ્યક્તિએ, બીજા session થી, sign in કરીને confirm કરવું પડે.

**ટેસ્ટ કેસ:** 0.30 ને બદલે 0.32 mL ટાઈપ કરો → limit બહાર → સિસ્ટમ accept ન કરે.
(આ જ logic, જુદા numbers સાથે, `setup/bom.html` ના tolerance column માં પણ છે.)

### 3.2 — Integrated Testing

**સ્ક્રીન:** `combination/testing.html` | **વ્યક્તિ:** H. Novak

Method: Dose-delivery accuracy DDT-01 v3, sample FA-33210-S01…S20 (20 sample માંથી
અહીં ૪ દેખાય):

| Sample | Limit | Result | State |
|---|---|---|---|
| S01 | 95–105% label claim | 98.4% | Accepted |
| S02 | 95–105% label claim | 96.1% | Accepted |
| S03 | 95–105% label claim | **Pending** | **Blocking — "Pass" તરીકે ગણાય નહીં** |
| S04 | 95–105% label claim | 97.8% | Amended once |

**કેમ ૪ જ સેમ્પલ ૨૦ માંથી:** "Integrated performance evidence cannot be marked
complete while a sample is missing" — S03 pending છે, એટલે batch complete
ગણાય જ નહીં, ભલે બાકીના ૧૯ pass હોય.

### 3.3 — Labeling & Genealogy

**સ્ક્રીન:** `combination/labeling.html` | **વ્યક્તિ:** M. Ortiz

| Item | Issued | Packaged | Rejected |
|---|---|---|---|
| Final presentation label (LBL-EPI) | 4,000 | 3,996 | 4 |
| Final carton (CTN-EPI) | 4,000 | 3,996 | 4 |
| Patient information leaflet (PIL-EPI) | 4,000 | 3,996 | 4 |

**Genealogy:** દરેક finished unit ને drug lot (B-2026-0142) અને device serial lot
(SL-77102) બંને સાથે traced — link રાખેલી, merge નહીં કરેલી.

**Yield:** 4,000 planned → 4,000 issued → **3,996 good units** → 4 rejected →
**99.9% yield**. આ ૪ યુનિટ testing ના S03/S04 જેવી સેમ્પલ-લેવલ સમસ્યાને કારણે નહીં,
process-level નુકસાનને કારણે ગણાય છે — બંને જુદી વસ્તુ છે.

---

# ભાગ ૪ — જ્યારે વસ્તુ ખરેખર ખોટી થાય

### 4.1 — Cross-constituent Issue

**સ્ક્રીન:** `combination/cross-constituent.html` | **વ્યક્તિ:** J. Kwan

**XC-0091:** "Device-side assembly torque below spec on **40 units**" — line audit
દરમિયાન મળ્યું.

Impact assessment, constituent પ્રમાણે અલગ:
- Drug constituent impact — **Under assessment** (હજુ ચાલુ)
- Device constituent impact — Confirmed, 40 units affected
- Final product impact — **Blocked** — "Device closure alone cannot close a
  cross-constituent blocker" — drug ની બાજુ પણ પૂરી થવી જોઈએ.

**કેમ આ torque number સાથે જોડાયેલું:** યાદ છે ભાગ ૧.૩ માં torque spec ની "unit
missing" ચેતવણી? એ જ spec ના device ના ૪૦ યુનિટ પર torque limit બહાર નીકળ્યા —
રેસીપીની અધૂરી વિગત, છેક ઉત્પાદનમાં સમસ્યા બનીને પાછી આવે છે. આ real-world connection
client ને બતાવવા જેવો છે.

### 4.2 — Complete Review & Release

**સ્ક્રીન:** `combination/release.html` | **વ્યક્તિ:** P. Nair

૧૦ evidence group, ૮ accepted, ૨ સમસ્યાવાળા:
- Group 5 — Integrated performance testing — **4/5 — 1 sample pending** (S03, ઉપર જોયેલો)
- Group 8 — Cross-constituent exceptions — **1 open** (XC-0091, ઉપર જોયેલો)

Release/Reject બંને બટન **locked**: "Unavailable — XC-0091 is unresolved."

**ટેસ્ટ કેસ:** XC-0091 બંધ ન થાય ત્યાં સુધી, અને S03 નું પરિણામ ન આવે ત્યાં સુધી,
P. Nair પાસે release કરવાનો કોઈ રસ્તો નથી — override બટન ક્યાંય નથી.

---

# ભાગ ૫ — Asset: FS-8 નું આખું જીવન

**સ્ક્રીન:** `setup/equipment.html` → `setup/asset-detail.html`

Filling માં વપરાયેલું **Fill station FS-8** — આ ફક્ત "નામ + due date" નથી, પૂરો
asset record છે:

- **ઓળખ:** FS-8, Bosch Packaging FST-2200, commissioned 14 Mar 2024, GxP-critical
- **Calibration:** ત્રિમાસિક (quarterly) — 22 Jan, 22 Apr, 22 Jul 2026 pass, next 22 Oct 2026
- **Maintenance:** 10 Feb (seal replacement), 15 May (nozzle inspection), next 15 Aug 2026
- **Qualification:** IQ/OQ/PQ ત્રણેય Passed, Mar 2024 માં
- **Genealogy — આ મશીને શું બનાવ્યું:** FA-33210 (Active), FA-33188 (Released),
  FA-33140 (Released), FA-33002 (**Rejected**)

**client ને કહેવા જેવી લાઈન:**
> "જો FS-8 ની calibration કાલે fail થાય, તો આ એક પેજ તમને સેકંડોમાં કહી દેશે —
> કયા-કયા batch અસર પામી શકે. કાગળ પર આ શોધવામાં દિવસો લાગત."

---

# ટેસ્ટ કેસ — સંપૂર્ણ યાદી (client ને "proof" તરીકે બતાવવા)

| # | સ્ક્રીન | Action | Real data | અપેક્ષિત પરિણામ |
|---|---|---|---|---|
| 1 | admission.html | Exclusions ઠીક કરો | RD-088 dossier | Approve unlock |
| 2 | compatibility.html | ડ્રોઈંગ rev D confirm કરો | DWG-AI40-07 | Approve unlock |
| 3 | integrated-master.html | Order size 4000→10000 બદલો | 0.30 mL/unit | બધા totals recalculate |
| 4 | recipe-approval.html | Torque unit ઠીક કરો, PIN વગર sign | 2.4–2.8 N·m | પહેલા blocked, PIN વગર still blocked |
| 5 | recipe-approval.html | PIN ભરીને sign | — | v1.5 → Effective, ટેબલમાં ઉમેરાય |
| 6 | new-batch.html step1 | v1.5 પસંદ કરવાનો પ્રયત્ન | — | પસંદ ન થાય (disabled radio) |
| 7 | new-batch.html step4 | Recheck readiness | B-2026-0142 | Cleared થાય |
| 8 | filling.html | Fill volume 0.30 mL | Limit 0.29–0.31 | Within range |
| 9 | filling.html | Verification | — | "Awaiting a second identity" — locked |
| 10 | testing.html | S03 sample | Pending | Blocking, "Pass" ન ગણાય |
| 11 | cross-constituent.html | Close XC-0091 | Drug impact pending | Locked |
| 12 | release.html | Release/Reject | XC-0091 open | બંને locked |
| 13 | asset-detail.html | FS-8 genealogy | FA-33002 | Rejected છતાં યાદીમાં દેખાય (છુપાવાયું નહીં) |
| 14 | role-select.html | Author role select કરો | — | Admission/Compatibility/Integrated master unlock, બાકી બધું lock |
| 15 | role-select.html | Quality role select કરો | — | Recipe approval + Release unlock, રેસીપી-લખવાનું lock |

---

# Client ને બતાવવાનો ટૂંકો ક્રમ (૧૫ મિનિટ)

1. **role-select.html** ખોલો — S. Bloom (Author) બનો.
2. `integrated-master.html` ખોલો — per-unit BOM બતાવો, "Preview at order size" માં
   4000 ને બદલે 8000 લખો — ટોટલ બદલાય એ બતાવો. કહો: *"આ જ ગણિત, batch બને ત્યારે,
   ઓપરેટર માટે આપોઆપ થાય છે."*
3. `recipe-approval.html` ખોલો — torque spec ની ખામીને કારણે approve locked છે એ
   બતાવો, ઠીક કરો, sign કરો.
4. Role switch કરો → **Quality** બનો → સેમ પેજ પર "Integrated master" હવે locked
   છે એ બતાવો.
5. `new-batch.html` ખોલો (role switch → Planner) — Step 3 માં ઉપરની જ recipe ના
   numbers ×4,000 થયેલા બતાવો.
6. Step 4 પર blocker બતાવો, resolve કરો, batch issue કરો.
7. `setup/asset-detail.html` પર FS-8 નું genealogy બતાવીને પૂરું કરો — *"એક
   મશીનની history, બધા batch સાથે જોડાયેલી."*

**એક વાક્ય જે આખા demo નો સાર છે:**
> "0.30 mL ની રેસીપીથી શરૂ કરીને, 4,000 યુનિટના batch સુધી, ને છેલ્લે release સુધી —
> દરેક નંબર એકબીજા સાથે જોડાયેલો છે. કોઈ પણ જગ્યાએ કોઈ છૂટક, ન સમજાય એવો આંકડો નથી."
