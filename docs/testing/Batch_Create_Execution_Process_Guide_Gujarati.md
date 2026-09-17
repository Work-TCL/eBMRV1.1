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
11. [Step Dependencies — વિગતવાર](#11-step-dependencies--વિગતવાર)
12. [Deviation — Batch માં કંઈક ખોટું થાય તો](#12-deviation--batch-માં-કંઈક-ખોટું-થાય-તો)
13. [CAPA — Deviation પછીનું પગલું](#13-capa--deviation-પછીનું-પગલું)
14. [QC Testing — Batch ના sample/result કેવી રીતે જોડાય](#14-qc-testing--batch-ના-sampleresult-કેવી-રીતે-જોડાય)
15. [Cleaning Execution + Line Clearance — Batch શરૂ કરતાં પહેલાં](#15-cleaning-execution--line-clearance--batch-શરૂ-કરતાં-પહેલાં)
16. [નવો Multi-step Recipe — `RCP-MJ-PFS-V1` v4 (manual browser data)](#16-નવો-multi-step-recipe--rcp-mj-pfs-v1-v4-2026-09-17-released)
17. [જાણીતી મર્યાદાઓ (honest gaps)](#17-જાણીતી-મર્યાદાઓ-honest-gaps)

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

**⚠️ "recipe એ declare કરેલો role" નો સાચો અર્થ:** ફક્ત Admin/Supervisor/Operator જ ખરેખર `batch_
execution.execute` ધરાવે છે — recipe નો `required_role_code` બીજા કોઈ role (QC Reviewer/QA Reviewer/
Sanitation Operator વગેરે) ને point કરે તો એ step **કોઈનાથી પણ ક્યારેય execute ના જ થઈ શકે** (Supervisor/
Admin override સિવાય). પૂરી વિગત + real finding → §16.1.

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

## 11. Step Dependencies — વિગતવાર

**Dependency શું છે:** Recipe author (`recipe.author` — Process Engineer) દરેક step માટે "આ step પહેલાં કયો
step complete હોવો જોઈએ" જાહેર કરી શકે (`gxp_recipe_dependency` — predecessor step → successor step,
recipe-master ના "Dependencies" editor, §9.4). Batch execution વખતે (`gxp_batch_step`) એ જ ગ્રાફ frozen
snapshot તરીકે વપરાય છે.

**Runtime state machine (code: `services/gxp-api/app/modules/batch_execution/commands.py`):**

```
pending  ──(બધા declared predecessor complete થાય)──▶  ready  ──Start──▶  in_progress  ──Complete──▶  complete
```

- Step ને **0 predecessor** હોય (દા.ત. પહેલો step) → batch Start થતાં જ સીધો `ready`.
- Step ને **1+ predecessor** હોય → જ્યાં સુધી **બધા** predecessor `complete` ના થાય ત્યાં સુધી `pending`
  જ રહે — Start બટન દેખાય જ નહીં.
- એક step **બહુવિધ successor**ને unblock કરી શકે (દા.ત. નીચેના §16 ના recipe માં `ASSY-VER-01` complete
  થાય એટલે `TEST-CCI-01` **અને** `TEST-VIS-01` બંને એકસાથે `ready` થાય — parallel testing).
- એક step **બહુવિધ predecessor**ની રાહ પણ જોઈ શકે (દા.ત. `HOLD-QA-01` ને `TEST-CCI-01` **અને**
  `TEST-VIS-01` — બંને complete થાય પછી જ `ready` થાય).
- **Condition rule (optional):** Dependency પર `condition_rule_id`/`condition_rule_version` પણ set કરી
  શકાય (§9.4, `GET /rules/v1` dropdown) — એ predecessor complete ઉપરાંત rule evaluation ને પણ predecessor
  ready થવાની શરત બનાવે. **નવા recipe (§16) માં કોઈ condition rule વાપર્યો નથી** — બધા dependency ફક્ત
  plain predecessor-complete શરત પર છે, guess ના કરવો પડે એટલા માટે.

**⚠️ Circular dependency:** Backend `POST /recipes/v2/drafts/{id}/validate` વખતે dependency ગ્રાફ cycle
ચેક કરે છે — cycle હોય તો validate જ fail થાય, batch બનવા સુધી પહોંચે જ નહીં.

**ક્યાં જોવું:** `/batch-execution` ના step Detail modal માં "Predecessors"/"Unblocks next" — batch ના
context માં આ જ dependency ગ્રાફ, real step code સાથે.

---

## 12. Deviation — Batch માં કંઈક ખોટું થાય તો

**શું:** Batch execution દરમિયાન કોઈ પણ unexpected ઘટના (parameter tolerance બહાર, equipment breakdown,
material discrepancy, વગેરે) — Document 26 ના deviation module માં record કરવાની.

**ક્યાં:** `/deviations` (અલગ પેજ — batch-execution પર deviation create કરવાનું બટન નથી, manually
`/deviations` પર જવું પડે). **કોણ:** Operator/Supervisor (`qms_deviation.create`).

| Field | મતલબ | Batch સાથે જોડાણ |
|---|---|---|
| `source_type` | ક્યાંથી ઉદ્ભવ્યું | `"batch"` પસંદ કરો |
| `source_id` | કયો ચોક્કસ record | **Batch picker (dropdown)** — આ batch નું UUID auto-select થાય |
| `deviation_number` | Unique ઓળખ | free text (દા.ત. `DEV-2026-0201`) |
| `deviation_type` / `severity` | પ્રકાર/ગંભીરતા | dropdown |
| `owner_subject_id` | કોણ investigate કરશે | user dropdown |

**State machine (code-verified, `app/modules/qms/models.py::DEVIATION_STATES`):**

```
OPEN → TRIAGE → CONTAINMENT → INVESTIGATION → IMPACT_ASSESSMENT → DISPOSITION → CLOSED
```

દરેક transition નું પોતાનું permission છે (§13 ના જ pattern — `qms_deviation.triage`/`.contain`/
`.investigate`/`.impact`/`.disposition`/`.close`, મોટા ભાગે Supervisor શરૂ કરે, QA Reviewer/Releaser
disposition+close કરે). **Disposition** signed action છે.

**⚠️ અગત્યનું — batch execution ને deviation બિલકુલ block નથી કરતું:** Deviation open હોય તો પણ batch ના
step Start/Complete થઈ શકે છે — **link ફક્ત informational/traceability માટે છે**, deviation ને step-level
hold સાથે automatic જોડાણ નથી (એ manual practice છે — deviation મળે તો operator જાતે step-level Hold
કરે, §6.4). Release check (§8) પણ deviation ની state નથી જોતું — ફક્ત QA review completeness જુએ છે.

---

## 13. CAPA — Deviation પછીનું પગલું

**શું:** Deviation ના root cause પરથી corrective/preventive action plan — Document 27.

**ક્યાં:** `/capa`. **કોણ:** QA Reviewer (`capa.create`).

| Field | મતલબ |
|---|---|
| `source_type` | `"deviation"` પસંદ કરો (batch સીધું નહીં — chain છે: **Batch → Deviation → CAPA**) |
| `source_id` | કઈ deviation પરથી — dropdown (deviation number/id) |
| `problem_statement` | શું ખોટું થયું, free text |
| `root_cause_ref` | `investigation_ref` અથવા `proactive_rationale` — ઓછામાં ઓછું 1 ફરજિયાત |
| `risk_class` | dropdown |
| `owner_subject_id` / `target_date` | કોણ/ક્યાં સુધીમાં |

**જોડાણ chain:** `gxp_batch` (deviation નું `source_id`) ← `deviation_record` (CAPA નું `source_id`) ←
`capa_record`. **CAPA સીધું batch ને point નથી કરતું** — હંમેશા deviation દ્વારા જ. Actions
(`capa.action.add`/`.complete`), Effectiveness check (`capa.effectiveness`), Close (`capa.close`) — બધા
QA Reviewer/Releaser level ના permission છે.

---

## 14. QC Testing — Batch ના sample/result કેવી રીતે જોડાય

**શું:** Batch માંથી લીધેલા sample નું lab testing — Document 23/24 (`/qc` module).

**જોડાણ chain (code: `app/modules/qc/commands.py`):** `QcSample.source_type = "batch"` +
`QcSample.source_id = <batch_id>` → `QcTestOrder` (sample_id દ્વારા) → result → disposition
(release/reject/OOS investigation).

| પગલું | કોણ | ક્યાં |
|---|---|---|
| Sample collect | Operator/QC | `/qc` — "Collect sample", source = batch |
| Test order create/start | QC Reviewer | sample પરથી dropdown |
| Result record | QC Reviewer | test order પર |
| OOS (out of specification) | QC Reviewer → QA Reviewer extended investigation | `oos_record.extended_investigation` |

**⚠️ Batch execution ના generic step parameter (§6, દા.ત. `FILL_WEIGHT_MG`) અને `/qc` નું lab-tested
sample — 2 જુદી વસ્તુ છે:** પહેલું ઈન-લાઇન/ઈન-પ્રોસેસ measurement (operator પોતે માપે, step Complete
માટે વપરાય), બીજું lab sample (અલગ physical sample, QC lab process, અલગ chain-of-custody). §16 ના
`FILL-IPC-01` step ઈન-પ્રોસેસ છે — lab QC sample નહીં, એ `/qc` પર અલગથી log કરવાનું રહે (જો જરૂરી હોય).

---

## 15. Cleaning Execution + Line Clearance — Batch શરૂ કરતાં પહેલાં

**2 જુદા record, ગૂંચવાવ નહીં (code: `app/modules/equipment/cleaning_models.py`):**

| Record | શું track કરે | Batch સાથે FK |
|---|---|---|
| **Cleaning execution** | Equipment/area ને ખરેખર સાફ કરવાની ક્રિયા (start → complete, dirty-hold સમય) | નથી — equipment/area level |
| **Line clearance** | "આ area/line અગાઉના batch ના material/label/document થી ખાલી છે" ની attestation — pass/fail | ✅ **`previous_batch_id`/`next_batch_id`** સીધા `ebmr.gxp_batch.id` ને point કરે |

**ક્યાં:** `/line-clearance`. **કોણ:** Sanitation Operator (`line_clearance.create`/`.complete`).

| Field | મતલબ | Type |
|---|---|---|
| Area | કયું equipment area | area dropdown |
| Previous batch | જે batch માંથી area ખાલી કરવાનું | **Batch picker** (`type: "batchSelect"`) |
| Next batch | જે batch માટે area તૈયાર કરવાનું | **Batch picker** |

**Result:** Pass → area ની clearance state `CLEARED` થાય (downstream readiness check — DDCP batch
readiness, Packaging — આ જ state શોધે છે). Fail → `NOT_STARTED` પર reset.

**§16 ના નવા recipe સાથે જોડાણ:** `LC-01` step (પહેલો step, section "Line Clearance") એ generic recipe
step છે — batch execution નો ભાગ, **પણ એ પોતે `/line-clearance` ના real attestation record ને automatically
create/check નથી કરતું** (§6.4 ના જ material/equipment requirement ની જેમ — declarative/display, actual
cross-module link હજુ નથી, §17 જુઓ). Realistic sequence: `/line-clearance` પર real clearance pass કરો
(અલગ પેજ), **પછી** `/batch-execution` પર `LC-01` step ને પણ Complete કરો (record purpose માટે, batch ના
પોતાના step chain ને આગળ વધારવા).

---

## 16. નવો Multi-step Recipe — `RCP-MJ-PFS-V1` v4 (2026-09-17, RELEASED)

`MERIDIJECT-PFS` product ની `RCP-MJ-PFS-V1` recipe family નું **v1** ફક્ત 1 step (`FILL-01`) નું હતું —
batch execution ના multi-step/dependency/parallel-testing flow ને પૂરેપૂરું demo/test કરવા માટે અપૂરતું.
**v4 — RELEASED** (`process.engineer` → author → validate → submit; `qa.releaser` → signed release,
author≠releaser SoD) — 6 section, 9 step, 9 dependency, 5 parameter, 3 material requirement, 6 equipment
requirement, 4 evidence requirement સાથે.

**v2/v3 એ જ recipe ના પહેલા 2 attempt હતા** — બંનેમાં role-assignment ભૂલ મળી (§16.1 જુઓ, code-testing
દરમિયાન API દ્વારા ચકાસતાં પકડાયેલી), v4 એ fix કરેલો છે. **v4 ની correctness (parameter range, dependency
ગ્રાફ, roles) code-testing pass દરમિયાન batch create → 9 step Complete → Production Complete → QA
Review → Release ચલાવીને ચકાસી છે** (batch number `MJ-PFS-B-2803`, હવે RELEASED, ફરી ના વાપરવો) — પણ
**તમારો પોતાનો batch browser માંથી manually ચલાવવાનો છે**, નીચે §16.5 માં ટાઈપ કરવાની બધી real/tested
value આપી છે.

### 16.1 ⚠️ મહત્વનું finding — `required_role_code` ફક્ત એ role માટે જ કામ કરે જે પહેલેથી `batch_execution.execute` ધરાવે

Recipe step પર `required_role_code` set કરવાથી **કોઈ પણ role ને batch step execute કરવાની સત્તા મળતી
નથી** — એ ફક્ત **narrowing** છે. Actual gate 2-સ્તરનું છે (code: `batch_execution/commands.py::_enforce_
step_role()`):

1. પહેલા actor પાસે **`batch_execution.execute`** permission હોવું જ જોઈએ (base gate, બધા step માટે સમાન).
2. પછી જ (જો હોય તો) step ના `required_role_code` સાથે actor નો role match ચેક થાય.

**Live-verified (code: `scripts/seed.py::ROLE_PERMISSIONS`) — `batch_execution.execute` ફક્ત આ 3 role
ધરાવે છે:** Admin, Supervisor, **Operator**. **QC Reviewer, QA Reviewer, Sanitation Operator — આમાંથી
કોઈ પણ role `batch_execution.execute` ધરાવતો નથી** (ફક્ત `batch_execution.view`) — એટલે આ role નો કોઈ
પણ user, `required_role_code` ભલે એ role ને point કરે, **Start/Record/Link/Complete કોઈ પણ generic
batch step action call જ ના કરી શકે** — `403 ROLE_MISSING` (base gate પર જ block, step-level role ચેક
સુધી પહોંચે એ પહેલાં).

**Practical અસર:** `v2`/`v3` માં `LC-01`→Sanitation Operator, `TEST-CCI-01`/`TEST-VIS-01`→QC Reviewer,
`HOLD-QA-01`→QA Reviewer રાખેલા — **બધા 4 step કાયમ માટે "stuck" રહી ગયા**, કોઈ પણ real user થી ક્યારેય
Start ના જ થઈ શકે (Supervisor/Admin `override_reason` થી override કરે તો જ, જે routine flow નથી).
**v4 માં બધા 9 step નો required role `Operator` છે** — QC/QA-conceptual step (`TEST-CCI-01` વગેરે) નું
role-label ભલે "QC ચેક" સૂચવે, ખરેખર **Operator** user જ કરી શકે (procedural expectation — QC-trained
operator હોવો જોઈએ — role enforcement નહીં). **આ platform-level gap છે** — QC Reviewer/QA Reviewer role
ને `batch_execution.execute` આપવું (અથવા step-level role ને base-gate થી independent બનાવવું) એ regulated
RBAC ની નવી decision છે, guess નથી કરવો — §17 માં નવો honest gap તરીકે નોંધ્યું છે.

### 16.2 Dependency ગ્રાફ (1 નજરમાં)

```
LC-01 → DISP-01 → FILL-01 → FILL-IPC-01 → ASSY-01 → ASSY-VER-01 ─┬→ TEST-CCI-01 ─┐
                                                                   └→ TEST-VIS-01 ─┴→ HOLD-QA-01
```

`TEST-CCI-01`/`TEST-VIS-01` — બંને `ASSY-VER-01` complete થાય એટલે **સાથે** `ready` થાય (parallel).
`HOLD-QA-01` — બંનેમાંથી **બંને** complete થાય પછી જ `ready` (2 predecessor).

### 16.3 Step-by-step field detail (v4 — actually executable)

| Step code | Section | Step type | Role | Qualification | Critical | Parameter | Material req. | Equipment req. | Evidence |
|---|---|---|---|---|---|---|---|---|---|
| `LC-01` | Line Clearance | `equipment_check` | **Operator** | — | ✅ | — | — | `FILLING_LINE` (cleaning+qualification current) | photo ×1 |
| `DISP-01` | Dispensing | `weigh` | Operator | ASEPTIC_GOWN_CERT_DEMO | ✅ | `DISP_WEIGHT_KG` decimal kg, target 12.500 (12.375–12.625) | Drug spec (`MATSPEC-MERIDIZ-BULK-DS-001`), 12.500 kg, partial_container | `DISPENSING_BALANCE` (calibration current) | — |
| `FILL-01` | Aseptic Fill | `weigh` | Operator | ASEPTIC_GOWN_CERT_DEMO | ✅ | `FILL_WEIGHT_MG` decimal mg, target 1000 (950–1050), **rule: `FILL-VOLUME-TOLERANCE`** | Drug spec, 1.05 mL, full_container | `FILLING_LINE` | photo ×1 |
| `FILL-IPC-01` | Aseptic Fill | `ipc_qc` | Operator | ASEPTIC_GOWN_CERT_DEMO | ✅ | `IPC_FILL_WEIGHT_MG` decimal mg, target 1000 (950–1050), **rule: `FILL-VOLUME-TOLERANCE`** | — | — | photo ×1 |
| `ASSY-01` | Device Assembly | `assembly` | Operator | ASEPTIC_GOWN_CERT_DEMO | ✅ | — | Device spec (`MATSPEC-SYR-1ML-BARREL-001`), 1 EA, full_container | `ASSEMBLY_STATION` (qualification current) | photo ×1 |
| `ASSY-VER-01` | Device Assembly | `verification` | Operator | ASEPTIC_GOWN_CERT_DEMO | ✅ | — | — | — | — |
| `TEST-CCI-01` | In-Process Testing | `test` | **Operator** *(QC ચેક, §16.1 જુઓ)* | — | ✅ | `CCI_LEAK_TEST_PASS` boolean | — | `CCI_TESTER` (calibration current) | — |
| `TEST-VIS-01` | In-Process Testing | `test` | **Operator** *(QC ચેક)* | — | ✅ | `VISUAL_INSPECTION_PASS` boolean | — | `VISUAL_INSPECTION_STATION` | — |
| `HOLD-QA-01` | QA Hold | `hold_point` | **Operator** *(QA checkpoint)* | — | ✅ | — | — | — | — |

*(rule code real, live DB માં ચેક કરેલું — `FILL-VOLUME-TOLERANCE` rule, tolerance type, v1.0.1,
RELEASED — અગાઉના doc નો honest gap "real rule બનાવવો પડશે" હવે બંધ.)*

### 16.4 ⚠️ Honest નોંધ — acceptance rule automatic evaluate નથી થતો

`FILL-01`/`FILL-IPC-01` નો acceptance rule (`FILL-VOLUME-TOLERANCE`) parameter સાથે જોડાયેલો છે, પણ rule
evaluation ખરેખર `rules.evaluate` action દ્વારા **અલગથી invoke કરવો પડે** — `Record results`/`Complete`
બટન rule ને automatically evaluate નથી કરતું (rule_id ફક્ત metadata તરીકે parameter સાથે સંગ્રહાય છે,
batch_execution module rule engine ને call નથી કરતું — §17 માં આ ને honest gap તરીકે નોંધ્યું છે).

---

### 16.5 📋 Manual walkthrough — browser માં જાતે ભરવાની data (કંઈ પણ auto-run નથી કરેલું)

**નોંધ:** આ section ફક્ત **data reference** છે — recipe (v4) real, RELEASED, DB માં already છે (§16 ની
ઉપરની નોંધ), પણ batch/execution/review/release **તમે પોતે browser માંથી manually કરવાના છે**. નીચેની
value real/tested છે (તમે same recipe ના parameter range સામે already ચકાસેલી — in range), પણ **batch
number તમારો પોતાનો નવો રાખો** (દા.ત. `MJ-PFS-B-2900` — `MJ-PFS-B-2803` નામ પહેલેથી બીજા code-testing
pass માં વપરાઈ ચૂક્યું છે, ફરી ના વાપરવું, unique constraint error આવશે).

**કોણ શું કરે — 1 નજરમાં (login username, demo password બધા માટે `ChangeMe123!`):**

| # | પગલું | Login કરવો | Role | Page |
|---|---|---|---|---|
| 1 | Create batch | `supervisor1` | Supervisor | `/batch-execution` |
| 2 | Issue batch | `supervisor1` (એ જ session) | Supervisor | `/batch-execution` |
| 3 | Start batch | `operator1` (અથવા `supervisor1` — બંને `batch_execution.execute` ધરાવે) | Operator | `/batch-execution` |
| 4 | બધા 9 step — Start/Record results/Link evidence/Complete | `operator1` | Operator *(§16.1 ના finding પ્રમાણે — QC/QA role થી ના જ થાય)* | `/batch-execution` |
| 5 | Evidence stage/finalize (Platform ops) | `qa.reviewer` (**`operator1` થી નથી થતું — Operator role `evidence.upload` ધરાવતો નથી, ફક્ત Admin/QA Reviewer ધરાવે છે**) | QA Reviewer | Platform ops → Evidence operations |
| 6 | Production Complete | `operator1` | Operator | `/batch-execution` |
| 7 | QA Review (create package + Complete review) | `qa.reviewer` | QA Reviewer | `/qa-review` |
| 8 | Release (Evaluate + Release) | `qa.releaser` (**qa.reviewer થી અલગ user ફરજિયાત — SoD**) | QA Releaser | `/release` |

#### 16.5.1 `/batch-execution` → "New batch" — શું ભરવું

**કોણ:** `supervisor1` login કરો (Admin થી પણ ચાલે, પણ realistic role demo માટે `supervisor1` વાપરો).

| Field | શું પસંદ/ટાઈપ કરવું |
|---|---|
| Product | `MERIDIJECT-PFS` → `MJ-PFS-40MG` v1 (RELEASED) |
| Recipe | `RCP-MJ-PFS-V1` → **v4** (dropdown માં "released first" — v4 જ પસંદ કરવો, v1/v2/v3 નહીં) |
| Batch number | તમારો પોતાનો નવો, દા.ત. `MJ-PFS-B-2900` |
| Target quantity | `4000` |
| Target UOM | `EA` |
| Production order ref (optional) | `PO-2026-9010` (અથવા તમારો પોતાનો) |

→ **Create** → batch detail ખૂલશે → **Issue** બટન (એ જ `supervisor1` session) → **Start** બટન (`operator1`
થી — logout/login કરીને, અથવા `supervisor1` થી પણ ચાલે, §3-§5 ના જ pattern).

#### 16.5.2 Step-by-step — Record results માં શું ટાઈપ કરવું

**કોણ:** `operator1` login કરો — બધા 9 step આ 1 જ user થી થાય (§16.5 ની ઉપરની "કોણ શું કરે" table
પ્રમાણે, §16.1 ના finding ને લીધે QC Reviewer/QA Reviewer થી step execute ના જ થાય).

Start થયા પછી `LC-01` `ready` થશે (§16.2 ના dependency ગ્રાફ પ્રમાણે). દરેક step: **Start** → (નીચે
મુજબ Record results/Link evidence) → **Complete** — §6.3/§6.4 ના જ button pattern, password ceremony
દરેક signed action પર (`operator1` નો પોતાનો password `ChangeMe123!`).

| Step | Record results — parameter | ટાઈપ કરવાની value | Evidence જોઈએ? |
|---|---|---|---|
| `LC-01` | — | — | ✅ photo ×1 (નીચે §16.5.3) |
| `DISP-01` | `DISP_WEIGHT_KG` | `12.510` *(target 12.500, range 12.375–12.625 — in range)* | — |
| `FILL-01` | `FILL_WEIGHT_MG` | `1002` *(target 1000, range 950–1050 — in range)* | ✅ photo ×1 |
| `FILL-IPC-01` | `IPC_FILL_WEIGHT_MG` | `998` *(in range)* | ✅ photo ×1 |
| `ASSY-01` | — | — | ✅ photo ×1 |
| `ASSY-VER-01` | — | — | — |
| `TEST-CCI-01` | `CCI_LEAK_TEST_PASS` | `true` (checkbox/Yes) | — |
| `TEST-VIS-01` | `VISUAL_INSPECTION_PASS` | `true` (checkbox/Yes) | — |
| `HOLD-QA-01` | — | — | — |

`TEST-CCI-01`/`TEST-VIS-01` બંને `ASSY-VER-01` Complete થતાં જ સાથે `ready` થશે — કોઈ પણ ક્રમમાં Start/
Complete કરી શકાય. `HOLD-QA-01` બંને complete થાય પછી જ `ready` થશે.

#### 16.5.3 Evidence — `LC-01`/`FILL-01`/`FILL-IPC-01`/`ASSY-01` માટે

**કોણ — 2 અલગ user જોઈએ:** Stage/Finalize (પગલું 1) → `qa.reviewer` (**`operator1` થી નથી થતું** —
Operator role `evidence.upload` ધરાવતો નથી, ફક્ત Admin/QA Reviewer ધરાવે છે). Link evidence (પગલું 2,
step પર) → `operator1` (એ જ step-execute session, `batch_execution.execute`).

Evidence ફાઈલ સીધી step પરથી upload નથી થતી (§6.4). પહેલા:

1. Sidebar → **Platform ops → Evidence operations** → "Stage an evidence upload":

   | Field | Value |
   |---|---|
   | Owner type | `batch_step` |
   | Owner | Batch → Step 2-level dropdown — તમારો batch પસંદ કરો, પછી step (`LC-01`/`FILL-01`/વગેરે) |
   | Filename | કોઈ પણ, દા.ત. `LC-01-photo.jpg` |
   | Mime type | `image/jpeg` |
   | File | કોઈ પણ real photo/image select કરો |
   | Reason | `Line clearance photo evidence` (કે step પ્રમાણે) |

   → Stage → Finalize (એ જ પેજ પર).

2. પાછા `/batch-execution` → એ step ની row → **Link evidence** બટન → dropdown માંથી હમણાં staged કરેલી
   evidence પસંદ કરો (SHA-256/media type auto-fill થશે) → Requirement code = `photo` → Submit.

#### 16.5.4 Production Complete

બધા 9 step Complete થાય પછી batch action row માં **"Production complete"** બટન દેખાશે (§7) —
click → password → Confirm.

#### 16.5.5 QA Review — `/qa-review`

1. `qa.reviewer` login → `/qa-review` → **"New review package"** બટન.
2. Modal માં **Batch** dropdown — તમારો batch (batch number/product name સાથે) પસંદ કરો → **Create
   package**.
3. Package ખૂલશે (અથવા list માંથી ફરી ખોલો) → **"Complete review"** બટન → password → Confirm
   (signature meaning `Reviewed`).

#### 16.5.6 Release — `/release`

1. `qa.releaser` login (**qa.reviewer થી અલગ user હોવો ફરજિયાત — SoD**) → `/release`.
2. **Scope type** = `batch`, **Batch** dropdown — તમારો batch પસંદ કરો → **"Evaluate eligibility"**
   બટન.
3. Eligibility "Eligible for release" (લીલું banner, 0 blocker) બતાવે તો → **"Release"** બટન → Reason
   (optional field, દા.ત. `All steps complete, QA review complete, no open deviations`) → password →
   Confirm (signature meaning `Released`).

**⚠️ Honest નોંધ (matches §8):** Release eligibility એ ફક્ત QA review completeness + Vault snapshot
integrity ચેક કરે છે — batch ની `production_complete` state કે DDCP execution/readiness (§10) એ સીધું
નથી જોતું, ભલે realistic sequence (Production Complete → QA Review → Release) follow કરવો સાચી practice
છે.

**Reference data (2026-09-17, code-testing pass દરમિયાન same recipe/value વાપરીને ચકાસેલું — batch
number `MJ-PFS-B-2803`, હવે પહેલેથી RELEASED, ફરી ના વાપરવો):** ઉપરની બધી parameter value (12.510/
1002/998/true/true) આ જ recipe ના declared min/max range સામે **in range** confirm થયેલી છે — તમે
manually ટાઈપ કરો ત્યારે same range apply થશે.

---

## 17. જાણીતી મર્યાદાઓ (honest gaps)

| વસ્તુ | સ્થિતિ |
|---|---|
| Record results ની out-of-range value | **✅ FIXED 2026-09-17** — step Detail modal ના "Recorded value" column માં હવે "⚠ out of range" દેખાય છે (data capture/Complete ને હજુ પણ block નથી કરતું — informational જ છે, જેમ Document 106 ધારે છે) |
| Material/Equipment requirement | **✅ FIXED 2026-09-17** — step Detail modal માં હવે "Material requirements"/"Equipment requirements" ટેબલ દેખાય છે (material name, target/range, consume mode, equipment class, calibration/qualification/cleaning flags). Actual lot/asset **link કરવાની** UI/API હજુ નથી — એ ભાગ SG-045/SG-048 પર જ ખુલ્લો છે, ફક્ત **જોવાનું** હવે શક્ય છે |
| Link evidence — Evidence object ID | **✅ FIXED 2026-09-17** — હવે raw UUID paste કરવાને બદલે dropdown માંથી પસંદ કરી શકાય (એ જ step માટે પહેલેથી staged evidence ની list, `GET /evidence/v1/objects`) — SHA-256/media type પણ auto-fill થાય |
| Evidence staging ("Platform ops") ના Owner ID | **✅ FIXED 2026-09-17** — Owner type `batch_step` હોય ત્યારે હવે Batch → Step 2-level dropdown વાપરી શકાય, raw UUID manual paste ફરજિયાત નથી (બીજા owner type માટે હજુ manual entry) |
| Step correction/rework | હજુ open — Complete થયેલો step પછી ભૂલ સુધારવાનો controlled flow નથી (regulated correction/audit semantics ની decision જરૂરી, SG-048 #023/#024) |
| Timer/duration enforcement | હજુ open — Hold-time limit આપોઆપ ચેક નથી થતું (Temporal integration જરૂરી, આ platform માં હજુ નથી) |
| `/batch-execution` ↔ `/ddcp` auto-sync | હજુ open (ઉપર §10 જુઓ) — ફક્ત read-only "sync status" view. Auto-complete કરવું એ regulated signature/authority ની નવી decision માંગે છે (SG-180), guess નથી કરવો |
| Parameter `rule_id` નું automatic evaluation | **નવું finding, 2026-09-17 (code-verified, `batch_execution/commands.py` — grep 0 match `rules_service.evaluate_rule`)** — Recipe parameter (§16.3 ના `FILL_WEIGHT_MG`/`IPC_FILL_WEIGHT_MG`) પર `rule_id` set કરી શકાય છે, પણ Record results/Complete એ rule ને actually evaluate **નથી** કરતું — ફક્ત parameter ના પોતાના `min_value`/`max_value` સામે check થાય છે (§6.5). Rule evaluation ફક્ત `/rules` પેજ પર manually (`rules.evaluate`) અથવા DDCP module ના પોતાના rule-evaluated ops (`DDCP_Client_Demo_Guide_Gujarati.md` §21.3.3) દ્વારા થાય છે. Batch execution ને rule engine સાથે જોડવું એ regulated acceptance-logic ની નવી decision છે — guess નથી કરવો, નવો SPEC_GAP તરીકે યોગ્ય |
| `LC-01` (recipe step) ↔ `/line-clearance` (real attestation) | Batch execution નો `LC-01` step અને `/line-clearance` નું real pass/fail attestation record — **2 અલગ, જોડાયેલા નથી** records (§15 જુઓ). `LC-01` Complete કરવાથી `/line-clearance` નો કોઈ record આપોઆપ નથી બનતો, અને ઊલટું — બંને manually જ ચલાવવા પડે, ફક્ત `batch_id` common context છે (SG-180 ના જ class નું finding, DDCP execution vs batch execution ની જેમ) |
| `required_role_code` ને non-execute role point કરવો | **નવું, મહત્વનું finding, 2026-09-17 (code-verified — §16.1 માં પૂરી વિગત)** — QC Reviewer/QA Reviewer/Sanitation Operator (અને `batch_execution.execute` ના ધરાવતો કોઈ પણ role) ને recipe step નો `required_role_code` બનાવવાથી એ step **કાયમ માટે execute ના જ થઈ શકે** તેવો — base permission gate (`batch_execution.execute`) role-check પહેલાં જ 403 આપે. Recipe author ને UI માં કોઈ warning નથી મળતું (કોઈ પણ role name ટાઈપ/પસંદ કરી શકાય, ભલે એ role batch execute ના કરી શકે). `RCP-MJ-PFS-V1` ના v2/v3 attempt આ જ ભૂલ સાથે release થયા હતા (§16 ની શરૂઆતની નોંધ) — v4 એ fix કર્યું. **Fix વિકલ્પો (project-owner decision જરૂરી, guess નથી કરવો):** (a) QC Reviewer/QA Reviewer ને `batch_execution.execute` આપવું (broader scope change), (b) Recipe Master ના "Required role" picker ને ફક્ત `batch_execution.execute`-ધારક roles સુધી મર્યાદિત કરવું (UI-level guard), (c) જેમ છે એમ રાખવું, દસ્તાવેજીકરણ સાથે |

**વધુ detail/history માટે:** `docs/generated/18_SPEC_GAPS.md` (SG-045, SG-047, SG-048, SG-056,
SG-180) અને `DDCP_Client_Demo_Guide_Gujarati.md` §11-12.
