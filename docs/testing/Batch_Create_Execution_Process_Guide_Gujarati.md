# Batch Create + Execution Process — સાદી Guide (Gujarati)

**હેતુ:** આ document `DDCP_Client_Demo_Guide_Gujarati.md` જેવો scripted demo script **નથી** — એ ફક્ત
**process reference** છે: batch કેવી રીતે બને છે, કોણ શું કરી શકે, દરેક પગલે કઈ data ભરવાની હોય છે, અને
DDCP profile સાથે batch કેવી રીતે જોડાય છે. જ્યારે પણ confuse થાવ, આ doc માં પાછું આવીને ચેક કરો.

**⚠️ પ્રામાણિકતા નોંધ (CLAUDE.md §5):** આ document code-verified (2026-09-17) છે — કોઈ પણ field/button/
permission લખતા પહેલા actual backend code અને frontend UI ચેક કરેલા છે, guess નથી કર્યો.

---

## અનુક્રમણિકા

1. [Batch શું છે — 1 લીટીમાં](#1-batch-શું-છે--1-લીટીમાં)
2. [આખી Process — એક નજરમાં](#2-આખી-process--એક-નજરમાં)
3. [પગલું 1 — Create Batch](#3-પગલું-1--create-batch)
4. [પગલું 2 — Issue Batch](#4-પગલું-2--issue-batch)
5. [પગલું 3 — Start Batch](#5-પગલું-3--start-batch)
6. [પગલું 4 — Step Execution (દરેક step ને પૂરો કરવો)](#6-પગલું-4--step-execution-દરેક-step-ને-પૂરો-કરવો)
7. [પગલું 5 — Production Complete](#7-પગલું-5--production-complete)
8. [પગલું 6 — QA Review + Release](#8-પગલું-6--qa-review--release)
9. [Role-wise Master Table (બધું 1 જ ટેબલમાં)](#9-role-wise-master-table-બધું-1-જ-ટેબલમાં)
10. [DDCP Profile સાથે Batch કેવી રીતે જોડાય છે](#10-ddcp-profile-સાથે-batch-કેવી-રીતે-જોડાય-છે)
11. [જાણીતી મર્યાદાઓ (honest gaps)](#11-જાણીતી-મર્યાદાઓ-honest-gaps)

---

## 1. Batch શું છે — 1 લીટીમાં

**Batch = ખરેખર ઉત્પાદન કરવાનું 1 ચોક્કસ "run".** Product Master (**શું** બનાવવું) અને Recipe Master
(**કેવી રીતે** બનાવવું) કાયમી, reusable master data છે — batch દર વખતે એ બંનેના **RELEASED version**
પરથી નવો બને છે, જેમ recipe book 1 જ હોય પણ દર વખતે રસોઈ કરો એ નવો "batch".

---

## 2. આખી Process — એક નજરમાં

```
Create batch → Issue batch → Start batch → Steps execute (1-by-1) → Production Complete
                                                                              ↓
                                                              QA Review → QA Release
```

| # | પગલું | ટૂંકમાં શું થાય |
|---|---|---|
| 1 | **Create** | ફક્ત batch નો record બને (Product+Recipe version પસંદ કરીને) |
| 2 | **Issue** | Recipe ના steps ની frozen "to-do list" બને (execution snapshot) |
| 3 | **Start** | ખરેખર કામ શરૂ — પહેલો step "ready" થાય |
| 4 | **Step execution** | દરેક step: Start → data entry (જરૂર હોય તો) → Complete → આગળનો step "ready" |
| 5 | **Production Complete** | બધા step પૂરા થાય પછી batch ને "done" mark કરવું |
| 6 | **QA Review + Release** | 2 જુદા role — review કરે, પછી release કરે (independent) |

**ક્યાં:** આખી process 1 જ પેજ પર — `/batch-execution`. QA Review/Release અલગ પેજ પર — `/release`.

---

## 3. પગલું 1 — Create Batch

**કોણ:** Admin, Supervisor (`batch_execution.create`). **સહી જોઈએ?** ના.

| Field | મતલબ | ડ્રોપડાઉન data ક્યાંથી |
|---|---|---|
| Product | કયું product બનાવવું | Product Master ના business ID |
| Product version | RELEASED version જ પસંદ કરી શકાય | Product Master |
| Recipe | Product સાથે match થતી recipe family | Recipe Master |
| Recipe version | RELEASED + Product version સાથે match | Recipe Master |
| Batch number | આ run ની unique ઓળખ (દા.ત. `MJ-PFS-B-2601`) | free text |
| Target quantity / UOM | કેટલા unit બનાવવાનો ધ્યેય | free text |
| Production order ref | Internal/ERP order number (optional) | free text |

**નોંધ:** draft/unreleased Product કે Recipe version પર batch **ના જ બની શકે** — RELEASED હોવું ફરજિયાત.

---

## 4. પગલું 2 — Issue Batch

**કોણ:** Admin, Supervisor (`batch_execution.issue`). **સહી જોઈએ?** ના.

**શું થાય:** Recipe ના steps ની **frozen copy** batch સાથે જોડાઈ જાય — recipe પછીથી બદલાય તો પણ આ
batch ની snapshot અસર નથી લેતી (regulatory traceability માટે જરૂરી). આ frozen snapshot માંથી જ દરેક
step નો record (`gxp_batch_step`) બને છે — હજુ કોઈ step start નથી થયો, ફક્ત to-do list તૈયાર થઈ.

---

## 5. પગલું 3 — Start Batch

**કોણ:** Admin, Supervisor, Operator (`batch_execution.execute`). **સહી જોઈએ?** ના.

**શું થાય:** Batch ની state `in_execution` થાય. જે step ને કોઈ predecessor નથી (દા.ત. પહેલો step),
એ આપોઆપ **"ready"** થાય — હવે એનું "Start" બટન દેખાય. બાકીના બધા step "pending" (predecessor ની રાહ
જોતા) દેખાય, એ design પ્રમાણે સાચું જ છે.

આ જ પેજ પર batch-level **Hold / Resume / Abort** બટન પણ છે (આખા batch ને અટકાવવા/બંધ કરવા માટે —
નીચેના step-level Hold થી અલગ, §6.4 જુઓ).

---

## 6. પગલું 4 — Step Execution (દરેક step ને પૂરો કરવો)

### 6.1 Step ની states

```
pending  →  ready  →  in_progress  →  complete
              ↑            ↓
              └──── on_hold (step-level, temporary) ────┘
```

### 6.2 Step Start

**કોણ:** `batch_execution.execute` + recipe એ declare કરેલો `required_role_code` (set હોય તો — એ
ચોક્કસ role ધરાવનાર જ start કરી શકે; Supervisor/Admin `override_reason` આપીને પણ proceed કરી શકે).
**સહી જોઈએ?** ના. **શું થાય:** step state `in_progress` થાય, operator/start time record થાય.

### 6.3 `in_progress` step પર દેખાતાં બટન — શું ફરજિયાત, શું optional

| બટન | ક્યારે ફરજિયાત | સહી (password)? | શું કરે છે |
|---|---|---|---|
| **Record results** | Recipe એ આ step માટે parameter declare કર્યો હોય તો (દા.ત. weight) | ✅ હા (દરેક submit = 1 સહી) | Parameter ની actual measured value ભરવી |
| **Link evidence** | Recipe એ evidence requirement declare કર્યો હોય તો (દા.ત. "1 photo") | ❌ ના | પહેલેથી upload થયેલી evidence ને step સાથે જોડવી (file અહીંથી upload નથી થતી) |
| **Hand over** | ક્યારેય ફરજિયાત નથી — situational (shift change) | ❌ ના | Step નું "assigned to" operator બદલવું, state એ જ રહે |
| **Hold** | ક્યારેય ફરજિયાત નથી — situational (કંઈક interrupt થાય તો) | ✅ હા, reason ફરજિયાત | **ફક્ત આ 1 step** ને અટકાવવો (batch ના બીજા step ચાલુ રહે) |
| **Resume** | Hold પછી જ દેખાય | ✅ હા | Step પાછો `in_progress` |
| **Complete** | **હંમેશા જરૂરી** (step પૂરો કરવા) | ✅ હા | Step પૂરો — server બધું ચેક કરે (નીચે §6.5) |

**સામાન્ય ક્રમ:** Start → (જરૂર હોય તો Record results) → (જરૂર હોય તો Link evidence) → Complete.
Hand over/Hold એ routine flow નો ભાગ નથી, ફક્ત exception situation માટે.

### 6.4 દરેક બટનની વિગત

**Record results** — Recipe એ declare કરેલા parameter (data type, UOM, target/min/max) ના field
દેખાય, actual value ભરો. દરેક submit અલગ સહી-action છે (fresh password) — Part 11 ના નિયમ પ્રમાણે.
Multiple વાર submit કરી શકાય, છેલ્લી value જ final ગણાય.

**Link evidence** — ફાઈલ પોતે અહીંથી upload નથી થતી. પહેલા **Platform ops → Evidence operations**
પર "Stage an evidence upload" કરીને Evidence object ID + SHA-256 hash મેળવો, પછી અહીં paste કરો:

| Field | જરૂરી? |
|---|---|
| Evidence object ID | ✅ |
| Evidence SHA-256 | ✅ |
| Media type (દા.ત. `image/jpeg`) | optional |
| Requirement code (recipe ના evidence requirement સાથે match) | optional, પણ Complete વખતે આ code પરથી જ count ગણાય |

⚠️ કેટલી/કઈ evidence જોઈએ એ live "1 of 2" જેવું ક્યાંય નથી દેખાતું — step ના **"Detail"** બટન ખોલીને
"Evidence requirements" ટેબલ ચેક કરવી પડે.

**Hand over** — "Hand over to" (user dropdown, ફરજિયાત) + "Reason" (free text, optional). Password
નથી જોઈતો. Start time/original audit એ જ રહે છે, ફક્ત current owner બદલાય.

**Hold / Resume** — Hold માટે reason ફરજિયાત. Hold દરમિયાન Record results/Complete બંને block. Resume
પર step પાછો કામ કરી શકાય એ સ્થિતિમાં આવે.

### 6.5 Complete — server શું ચેક કરે (ક્રમમાં)

1. Batch હજુ `in_execution` હોવું જોઈએ.
2. Step `in_progress` હોવો જોઈએ (નહીં તો `INVALID_TRANSITION`, 409).
3. Actor પાસે required role હોવો જોઈએ (અથવા Supervisor/Admin override).
4. દરેક **required** parameter નું result record થયેલું હોવું જોઈએ (નહીં તો `PARAMETER_REQUIRED`, 422).
5. દરેક declared evidence requirement પૂરી થયેલી હોવી જોઈએ (નહીં તો `VALIDATION_FAILED`, 422).
6. બધું pass થાય તો → step `complete`, અને **downstream steps આપોઆપ re-check** થાય — જે step નો આ
   એકમાત્ર/છેલ્લો બાકી predecessor હતો, એ `pending` માંથી `ready` થાય (Start બટન દેખાય).

---

## 7. પગલું 5 — Production Complete

**કોણ:** `batch_execution.execute`. **સહી જોઈએ?** ✅ હા. **ક્યાં દેખાય:** ફક્ત ત્યારે જ જ્યારે batch ના
**બધા** step `complete` હોય (batch action row માં, Hold/Resume/Abort ની બાજુમાં).

**શું ચેક કરે:** સર્વર ફરી ખાતરી કરે કે ખરેખર દરેક step complete છે — ના હોય તો
`PRODUCTION_NOT_COMPLETE` (422) + બાકી step ની list. **પછી શું:** Batch `production_complete` state
માં જાય — QA Review/Release માટે તૈયાર. (Production complete કાયમી-lock નથી — પછી પણ Hold કરી શકાય.)

---

## 8. પગલું 6 — QA Review + Release

| Phase | કોણ | સહી | Independent? |
|---|---|---|---|
| QA Review | QA Reviewer | ✅ (`Reviewed`) | — |
| QA Release | QA Releaser | ✅ (`Released`) | ✅ Reviewer ≠ Releaser ફરજિયાત (SoD enforced) |

**ક્યાં:** `/release`. **નોંધ:** Release check batch ની `production_complete` state નથી જોતું — ફક્ત
QA review પૂરો છે કે નહીં + Vault snapshot integrity જુએ છે. Production Complete step realistic GMP
sequence બતાવવા માટે છે, backend technically ફરજિયાત નથી કરતું.

---

## 9. Role-wise Master Table (બધું 1 જ ટેબલમાં)

| Action | Permission code | Role(s) | સહી? |
|---|---|---|---|
| Create batch | `batch_execution.create` | Admin, Supervisor | ના |
| Issue batch | `batch_execution.issue` | Admin, Supervisor | ના |
| Start / Hold / Resume / Abort **batch** | `batch_execution.execute` | Admin, Supervisor, Operator | ના |
| Start / Hand over / Link evidence a **step** | `batch_execution.execute` + recipe નો declared role | recipe એ declare કરેલો role (અથવા Supervisor/Admin override) | ના |
| Record results | `batch_execution.execute` + declared role | ઉપર મુજબ | ✅ |
| Hold / Resume a **step** | `batch_execution.execute` + declared role | ઉપર મુજબ | ✅ |
| Complete a **step** | `batch_execution.execute` + declared role | ઉપર મુજબ | ✅ |
| Production Complete | `batch_execution.execute` | Admin, Supervisor, Operator | ✅ |
| View batch/steps | `batch_execution.view` | Admin, Supervisor, Operator, QA Reviewer, QA Releaser, QC Reviewer | ના |
| QA Review | (training/qms review permission) | QA Reviewer | ✅ |
| QA Release | (release permission) | QA Releaser (≠ Reviewer) | ✅ |

---

## 10. DDCP Profile સાથે Batch કેવી રીતે જોડાય છે

**DDCP profile શું છે:** Combination product (દા.ત. prefilled syringe, auto-injector) નું "spec sheet"
— recipe જેવું જ, પણ ખાસ combination-product side માટે. એ declare કરે છે:
- કયા **constituent** જોઈએ (drug, device/needle, packaging, label) અને દરેક કઈ **state** માં હોવો
  જોઈએ (દા.ત. device `STERILIZED`, drug `READY_TO_USE`) —
- Assembly ના પગલાં અને required **tests** (CCI/leak/visual/dose-delivery) —
- Release પહેલા જરૂરી **checkpoints** (drug checkpoint, device checkpoint, combined checkpoint).

**Batch ↔ Profile જોડાણ કેવી રીતે થાય છે (અગત્યનું — સીધું FK નથી):**

```
Batch (gxp_batch)  →  Product Version (product_version_id)  ←  DDCP Profile Version
                                                                 (product_version_id FK)
```

Batch પર સીધો "DDCP profile" field **નથી**. જોડાણ **Product Version દ્વારા** થાય છે — DDCP profile,
બનતી વખતે, કયા Product Version માટે છે એ પસંદ કરે છે (RELEASED Product Version ફરજિયાત). તો batch જે
Product Version પરથી બન્યો છે, એ જ Product Version પર જે DDCP profile point કરે છે — એ જ profile આ
batch ને લાગુ પડે છે.

**એકવાર batch DDCP-profile-linked product વાપરે, પછી શું:** `/ddcp` પેજ પર જઈને, **એ જ `batch_id`**
વાપરીને DDCP-specific execution records ભરવાના — ટૂંકમાં:

| DDCP record | શું track કરે |
|---|---|
| Constituent handoff | Drug/device lot ને batch માં accept/reject કરવું |
| Fill operation | Fill run (setup/execution/hold/complete) |
| Production count ledger | Filled/rejected/sampled unit counts |
| Device assembly record | Assembly ના પગલાં (needle install, shield, વગેરે) — independent verify સાથે |
| Device functional test link | CCI/leak/dose-delivery test ને QC result સાથે જોડવું |
| DDCP release checkpoint | Drug/device/combined checkpoint pass/fail |
| Batch evidence manifest | Release પહેલા evidence નું frozen package |

**⚠️ સૌથી અગત્યની ચેતવણી — `/batch-execution` ના generic step (§6) અને `/ddcp` ના records એકબીજા
સાથે sync નથી થતા:**
- `/batch-execution` પર બધા recipe step Complete કરો તો પણ `/ddcp` ના records એની અસર **નથી** લેતા.
- `/ddcp` પર constituent handoff Accept / fill Complete કરો તો પણ `/batch-execution` નો matching
  recipe step (દા.ત. `DISP-01`/`FILL-01`) આપોઆપ Complete **નથી** થતો.
- બંને track ને **અલગ-અલગ, પોતપોતાની રીતે** પૂરા drive કરવા પડે છે — ફક્ત `batch_id` common છે.
- `/ddcp` પર જ એક "sync status" view છે (કયો DDCP action કયા recipe step ને અનુલક્ષે છે એ **બતાવે**
  છે) — પણ એ ફક્ત informational છે, આપોઆપ complete નથી કરતું.
- **Release check** (`/release`) batch execution state કે DDCP state — બેમાંથી કોઈ નથી જોતું, ફક્ત
  QA review completeness + Vault snapshot integrity જુએ છે.

**Practical order:** `/batch-execution` પર generic manufacturing step (line clearance, dispensing,
fill, વગેરે) ચલાવો, **અને** `/ddcp` પર combination-product-specific step (handoff/fill/assembly/tests/
readiness) ચલાવો — બંને, પછી `/release` પર જાવ. Backend order enforce નથી કરતું, પણ demo/process
consistency માટે આ sequence follow કરવી.

---

## 11. જાણીતી મર્યાદાઓ (honest gaps)

| વસ્તુ | સ્થિતિ |
|---|---|
| Record results ની out-of-range value | **✅ FIXED 2026-09-17** — step Detail modal ના "Recorded value" column માં હવે "⚠ out of range" દેખાય છે (data capture/Complete ને હજુ પણ block નથી કરતું — informational જ છે, જેમ Document 106 ધારે છે) |
| Material/Equipment requirement | **✅ FIXED 2026-09-17** — step Detail modal માં હવે "Material requirements"/"Equipment requirements" ટેબલ દેખાય છે (material name, target/range, consume mode, equipment class, calibration/qualification/cleaning flags). Actual lot/asset **link કરવાની** UI/API હજુ નથી — એ ભાગ SG-045/SG-048 પર જ ખુલ્લો છે, ફક્ત **જોવાનું** હવે શક્ય છે |
| Link evidence — Evidence object ID | **✅ FIXED 2026-09-17** — હવે raw UUID paste કરવાને બદલે dropdown માંથી પસંદ કરી શકાય (એ જ step માટે પહેલેથી staged evidence ની list, `GET /evidence/v1/objects`) — SHA-256/media type પણ auto-fill થાય |
| Evidence staging ("Platform ops") ના Owner ID | **✅ FIXED 2026-09-17** — Owner type `batch_step` હોય ત્યારે હવે Batch → Step 2-level dropdown વાપરી શકાય, raw UUID manual paste ફરજિયાત નથી (બીજા owner type માટે હજુ manual entry) |
| Step correction/rework | હજુ open — Complete થયેલો step પછી ભૂલ સુધારવાનો controlled flow નથી (regulated correction/audit semantics ની decision જરૂરી, SG-048 #023/#024) |
| Timer/duration enforcement | હજુ open — Hold-time limit આપોઆપ ચેક નથી થતું (Temporal integration જરૂરી, આ platform માં હજુ નથી) |
| `/batch-execution` ↔ `/ddcp` auto-sync | હજુ open (ઉપર §10 જુઓ) — ફક્ત read-only "sync status" view. Auto-complete કરવું એ regulated signature/authority ની નવી decision માંગે છે (SG-180), guess નથી કરવો |

**વધુ detail/history માટે:** `docs/generated/18_SPEC_GAPS.md` (SG-045, SG-047, SG-048, SG-056,
SG-180) અને `DDCP_Client_Demo_Guide_Gujarati.md` §11-12.
