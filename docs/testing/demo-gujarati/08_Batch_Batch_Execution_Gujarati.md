# ૮. Batch અને Batch Execution (eBMR) — Gujarati Demo Guide

> Source: `services/gxp-api/app/modules/batch_execution/{models,commands,router}.py`,
> `frontend/src/app/batch-execution/page.tsx`, `services/gxp-api/scripts/seed.py`.

---

## ૮.૧ અગત્યનું — બે "Batch" UI છે, ફક્ત એક જ REAL છે

| | `/batches` | `/batch-execution` |
|---|---|---|
| સ્ટેટસ | **Legacy/Dead** — ડિસેમ્બર 2026-09-08 થી કાયમ redirect જ કરે છે `/batch-execution` પર (જૂનું `ebmr.batches` ટેબલ કાયમ ખાલી છે) | **✅ REAL regુલેટેડ eBMR engine** |
| Backend Table | `ebmr.batches` (ડેડ) | `ebmr.gxp_batch` / `ebmr.gxp_batch_step` |
| API | — | `/batches/v1/*` |

**ડેમોમાં હંમેશા `/batch-execution` વાપરવું.**

---

## ૮.૨ Batch Lifecycle (State Machine)

```
planned → issued → in_execution → on_hold → aborted
                          ↓
                  production_complete → on_hold (post-complete hold)
```

**Batch Step states:** `pending → ready → in_progress → on_hold → complete`

> **⚠️ અગત્યની સ્પષ્ટતા client ને:** `gxp_batch.state` ક્યારેય "Released"/"Closed" સુધી પોતે નથી
> પહોંચતું — batch `production_complete` પર અટકે છે. **QA Review અને Release એ સંપૂર્ણપણે અલગ
> modules (ડોક્યુમેન્ટ ૧૨) દ્વારા, અલગ `release_scope` record પર થાય છે.** એટલે batch-execution
> સ્ક્રીન પર તમને ક્યારેય "Released" સ્ટેટસ નહીં દેખાય — release ની સ્થિતિ જોવા માટે QA
> Review/Release સ્ક્રીન જ જોવી પડે.

---

## ૮.૩ Batch કેવી રીતે બને છે

Batch **released Product Master version** + **released Recipe Master version** પરથી બને છે.

| Field | ઉદાહરણ |
|---|---|
| `site_id` | SITE1 |
| `product_version_id` | Released MeridiJect PFS product version |
| `recipe_version_id` | Released MeridiJect PFS recipe version |
| `batch_number` | `MJ-2026-0142` |
| `target_qty` | `50000` (Decimal — ક્યારેય float નહીં, regulated quantity) |
| `target_uom` | `units` |

**Batch issue થાય ત્યારે:** Recipe version ના steps freeze થઈને `gxp_batch_step` rows બને છે, અને
Vault માં એક frozen "execution snapshot" સેવ થાય છે — execution હંમેશા આ frozen snapshot સામે જ ચાલે
છે, live recipe સામે નહીં (recipe પછીથી edit થાય તો પણ ચાલુ batch પર અસર ના પડે).

### Equipment Requirements — હવે Step-Start પર Enforce થાય છે (✅ 2026-09-18 Fixed)

Recipe ના Equipment Requirement (Document ૦૭ જુઓ — `require_current_calibration`/
`require_current_qualification`/`require_current_cleaning`) પણ issue સમયે freeze થાય છે
(`gxp_batch_step_equipment_requirement`), અને **Step Start સમયે ખરેખર enforce થાય છે** — પહેલાં ફક્ત
captured હતા, કંઈ ચેક નહોતું થતું.

**કેવી રીતે કામ કરે છે:** Step Start ફોર્મ પર, જો recipe step કોઈ equipment requirement declare કરે
છે, તો operator ને `equipment_asset_ids` માં specific equipment asset(s) પસંદ કરવા પડે છે. Backend
પછી equipment module ના own eligibility check (`get_eligibility`) સામે verify કરે છે:

| Situation | Result |
|---|---|
| Requirement declared, કોઈ equipment_asset_ids ના આપ્યા | `422 EQUIPMENT_REQUIREMENT_NOT_MET` |
| આપેલ asset ખોટા class નું | `422 EQUIPMENT_CLASS_MISMATCH` |
| Asset class સાચું પણ qualification/calibration/cleaning expired | `403` (દા.ત. `EQUIPMENT_NOT_QUALIFIED`, `CALIBRATION_EXPIRED`, `CLEANING_REQUIRED`) |
| Asset eligible | Step start succeeds |

**Equipment Class Master (નવું):** `equipment_class` હવે free text ઉપરાંત એક controlled
`EquipmentClass` entity (`/recipes/v2/equipment-classes`) સાથે link થઈ શકે છે — Recipe Master ના
equipment requirement editor માં dropdown તરીકે.

---

## ૮.૪ Permission મેટ્રિક્સ

| Action | Permission Code | કોણ ધરાવે છે | E-signature? | Meaning |
|---|---|---|---|---|
| Batch Create / Issue | `batch_execution.create` | Admin, **Supervisor** | ના | — |
| Start batch / Hold / Resume / Abort | `batch_execution.execute` | Admin, Operator, Supervisor | Step-level actions signed (નીચે જુઓ) | — |
| Step Start | `batch_execution.execute` | Admin, Operator, Supervisor | ના | — |
| Record In-process Result | `batch_execution.execute` | Admin, Operator, Supervisor | **હા** | "Performed" |
| Complete Step | `batch_execution.execute` | Admin, Operator, Supervisor | **હા** | "Performed" |
| Hold Step | `batch_execution.execute` | Admin, Operator, Supervisor | **હા** | "Performed" |
| Resume Step | `batch_execution.execute` | Admin, Operator, Supervisor | **હા** | "Approved" (QA authority holds lિફ્ટ કરે) |
| Result Correction (request+approve, 2-signature) | `batch_step.correct` | — | **હા (2 વ્યક્તિ)** | "Approved" — requester ≠ approver |
| Production Complete | `batch_execution.execute` | Admin, Operator, Supervisor | **હા** | "Performed" |
| View | `batch_execution.view` | Admin, Operator, Supervisor, QA Reviewer, QA Releaser, QC Reviewer, DDCP Operator | ના | — |

**ડેમોમાં ફક્ત `admin` login જ batch Create/Issue કરી શકે** (Supervisor role માટે કોઈ demo user
seed નથી — ડોક્યુમેન્ટ ૦૨ પ્રમાણે `supervisor1` બનાવવો).

**Signature ceremony:** password re-entry + record-hash bound challenge — MFA/login session
પોતે signature નથી (AG-07).

---

## ૮.૫ In-process Checks — હવે Auto-Deviation Trigger કરે છે (✅ 2026-09-18 Fixed)

Step Result (પેરામીટર value, UOM, quality_status) `min_value`/`max_value` સામે ચેક થાય છે — આ ચેક
command ને હજુ **block નથી કરતું** (result record તો થઈ જ જાય છે), પણ **out-of-range result હવે
આપોઆપ એક Deviation Record ખોલે છે** — same transaction માં, StepResult ના audit trail સાથે bound.

**Project-owner-directed shape (2026-09-18):**

| Field | Auto-set Value |
|---|---|
| `state` | `OPEN` |
| `severity` | `minor` (હંમેશા — human triage વખતે major/critical માં reclassify કરે) |
| `deviation_type` | `process` |
| `source_type` / `source_id` | `batch` / batch ID |
| `owner_subject_id` | **null (unassigned)** — Supervisor/QA Reviewer એ triage કરીને પોતે claim કરવો પડે |
| `deviation_number` | `DEV-AUTO-<batch_number>-<step_code>-<result-id-prefix>` |
| Audit reason | "Auto-opened: in-process result for parameter '...' on step '...' was out of range." |

**Scope (project owner એ explicit રીતે પસંદ કરેલ):** ફક્ત out-of-range in-process result trigger
કરે છે. Step manually hold કરવો, અથવા equipment ineligibility block — આ બે trigger આ pass માં
**deliberately સામેલ નથી** (future scope).

Step ને manually `on_hold` કરવો હજુ પણ અલગ, independent action છે (signed, "authorized holder") —
auto-deviation એ hold ની જગ્યા નથી લેતું, બંને સ્વતંત્ર છે.

**ડેમો:** `operator1` login → out-of-range result record કરો (દા.ત. WEIGHT parameter min 1.0/max 2.0
પર 2.5 value) → `/deviations` પેજ પર `admin`/`qa.reviewer` login થી જુઓ — `DEV-AUTO-...` number સાથે
નવો OPEN deviation દેખાશે, owner ખાલી.

---

## ૮.૬ ડેમો વોકથ્રુ — Example Filled Data

**Login:** `admin` (create/issue) → `operator1` (execute steps)

### Step 1 — Batch Create/Issue (`admin`)
ઉપર ૮.૩ પ્રમાણે ફોર્મ ભરો → Submit → Batch `planned`/`issued` state માં બને.

### Step 2 — Batch Start (`operator1`)
`POST /{id}/start` → batch `in_execution` state માં.

### Step 3 — પ્રથમ Step Start + Complete (`operator1`, e-signature)

| Field | ઉદાહરણ |
|---|---|
| Step | "Dispensing verification" |
| Result | Weight = `2.05 mg`, quality_status = `within_limits` |
| Signature meaning | "Performed" |

### Step 4 — Production Complete (`operator1`, e-signature)
બધા steps complete થયા બાદ → `POST /{id}/production-complete`.

### Step 5 — QA Review/Release
→ જુઓ ડોક્યુમેન્ટ ૧૨ (Batch Review અને Release) — batch record પોતે "Released" નહીં બતાવે, release
status અલગ સ્ક્રીન પર જોવું.

---

## ૮.૭ સંલગ્ન Modules (Supporting — batch manufacture flow નો ભાગ)

| Module | શું કરે છે | નોંધ |
|---|---|---|
| **Genealogy** (`/genealogy`) | Lot/batch/device parent-child ટ્રેસિબિલિટી ગ્રાફ | Read-only UI; write API હજુ internal-event-driven, બહારથી કોઈ create endpoint નથી — ડેમોમાં ડેટા ઓછો દેખાઈ શકે |
| **Yield Reconciliation** (`/yield`) | Yield/potency calculation + material/packaging/label mass-balance | Calculate = Operator/Supervisor; **Verify = QA Reviewer only** (real SoD split); e-signature required verify પર |
| **Packaging** (`/packaging`) | Post-batch packaging/labeling/reconciliation run | Permission: `packaging.execute` (Operator/Supervisor/Admin); **કોઈ e-signature નથી**; **કોઈ GET/read API નથી** (known baseline gap) |
| **Field Actions** (`/field-actions`) | Released product પર recall/correction/removal | QA Reviewer = investigate/scope; **QA Releaser = regulatory decision/approve/close** (SoD) |

---

## ૮.૮ ધ્યાન રાખવા જેવી બાબતો (Known Limitations)

1. **`gxp_batch.state` ક્યારેય "Released" સુધી નથી પહોંચતું** — release status અલગ module માં (ઉપર
   ૮.૨ જુઓ). **By design, bug નથી** — Client ને શરૂઆતમાં જ સ્પષ્ટ કરવું, નહીંતર confusion થાય.
2. ~~In-process out-of-range result આપોઆપ exception/deviation trigger નથી કરતું~~ **✅ Fixed
   (2026-09-18)** — હવે આપોઆપ OPEN, unassigned-owner deviation ખૂલે છે (§૮.૫ જુઓ). Scope: ફક્ત
   out-of-range trigger, step-hold/equipment-block triggers હજુ future scope.
3. ~~Supervisor role માટે demo user નથી~~ **✅ Fixed (2026-09-18)** — `supervisor1` હવે seed થયેલ છે
   (password `ChangeMe123!`), manual create કરવાની જરૂર નથી.
4. **Packaging module માં read API જ નથી, hold state પણ પહોંચી ના શકાય તેવું છે** — હજુ ખુલ્લું
   (આ પાસમાં ટચ નથી કર્યું) — baseline spec ગેપ તરીકે honestly નોંધવું.
5. ~~`packaging`, `genealogy`, `yield`, `field-actions` પેજ પર frontend role-based button hide/disable
   નથી~~ **✅ ચકાસાયેલ (2026-09-18)** — `packaging`/`yield`/`field-actions` પહેલેથી જ role-gated હતા;
   `genealogy` પેજ સંપૂર્ણપણે read-only છે (કોઈ write action જ નથી) એટલે gating ની જરૂર જ નહોતી.
6. **Equipment Requirements enforcement નવું છે (2026-09-18)** — `require_current_cleaning` ની
   real-world verification `equipment.cleanliness_status` field સામે થાય છે (Document 39 ના
   cleaning-execution flow દ્વારા set થયેલ) — actual `CleaningExecution`/`LineClearance` record સામે
   live-tested નથી આ pass માં (SG-207, SPEC_GAPS.md જુઓ), ફક્ત qualification/calibration path live
   verify થયેલ.
