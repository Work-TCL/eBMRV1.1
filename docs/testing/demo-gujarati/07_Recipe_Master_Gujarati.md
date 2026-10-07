# ૭. Recipe Master — Gujarati Demo Guide

> ⭐ **આ ડોક્યુમેન્ટ ડેમોનો core ભાગ છે.** Source: `services/gxp-api/app/modules/recipe_master/
> {models,commands,router,service}.py`, `services/gxp-api/app/modules/rules/{models,precision}.py`,
> `frontend/src/app/recipe-master/{page,new/page,shared}.tsx`, `services/gxp-api/scripts/seed.py`.

---

## ૭.૧ અગત્યનું — REAL Regulated Page ઓળખવી

| | `/recipe-master` | `/recipes` |
|---|---|---|
| સ્ટેટસ | **✅ REAL** — Document 10 Master Recipe / MMR | **❌ Dead redirect** — 2026-09-08 થી `/recipe-master` પર |
| API | `POST/PUT /recipes/v2/...` | — |

**ડેમોમાં હંમેશા `/recipe-master` વાપરવું.**

---

## ૭.૨ Structure — Recipe એટલે શું?

```
RecipeFamily (કાયમી code, દા.ત. RCP-MJ-PFS-V1)
   └── RecipeVersion (version 1, 2, 3... — એક Product Master version સાથે linked)
          └── RecipeSection (દા.ત. "Dispensing", sequence, expected duration)
                 └── RecipeStep (16 types માંથી એક — instruction/weigh/scan/ipc_qc/assembly/વગેરે)
                        ├── RecipeParameter (target/min/max value, UOM, precision)
                        ├── RecipeEvidenceRequirement (કયા પ્રકારનું evidence જોઈએ)
                        ├── RecipeMaterialRequirement (BOM line — material spec version FK)
                        ├── RecipeEquipmentRequirement (equipment class)
                        └── RecipeStepDependency (predecessor/successor, conditional rule)
```

**એક Product → ઘણી Recipe Versions:** `RecipeVersion.product_version_id` એક specific Product Master
version ને FK કરે છે.

---

## ૭.૩ Lifecycle (State Machine)

```
draft → under_review → released → suspended
                              ↑________|  (reinstate)
                              ↓
                         obsolete / superseded  (terminal)
```

> ✅ **2026-09-18 Fixed:** Recipe Master માટે હવે Product Master જેવો જ **પૂરો lifecycle** છે —
> suspend/reinstate/obsolete/supersede — ચારેય built (પહેલાં **કંઈ જ** નહોતું, released recipe
> કાયમ released રહેતી). Permission `recipe.suspend` (નવો, Admin + QA Releaser) — §૭.૬ જુઓ.

---

## ૭.૪ Step Types (16)

`instruction`, `data_entry`, `scan`, `weigh`, `equipment_check`, `calculation`, `ipc_qc`, `signature`,
`verification`, `timer`, `hold_point`, `material_consume`, `assembly`, `test`, `packaging`,
`custom_approved_type`

**દરેક Step પર:** `instruction_text` (4000 char સુધી), `required_role_code`,
`required_qualification_code` (real qualification-gating field — batch execution engine આ ચેક
enforce કરે છે), `is_critical`.

---

## ૭.૫ મુખ્ય Fields

| Field | ઉદાહરણ (RCP-MJ-PFS-V1) |
|---|---|
| `recipe_code` | `RCP-MJ-PFS-V1` |
| `product_version_id` | Released `MERIDIJECT-PFS` version |
| `batch_size_value` / `batch_size_uom` | `5000` / `units` |
| Section: `stable_section_code` | `SEC-1` — "Dispensing" |
| Step: `stable_step_code` | `STEP-A` — `step_type="weigh"` |
| Parameter: `target_value`/`min_value`/`max_value` | `40.0` / `39.5` / `40.5` mg — **Decimal(24,8), ક્યારેય float નહીં** |
| Parameter: `precision_digits` | `2` |
| Material Requirement: `material_spec_version_id` | ડોક્યુમેન્ટ ૦૩ ની material spec version FK (existence-checked) |
| Equipment Requirement: `equipment_class` / `equipment_class_id` | `equipment_class` free label (દા.ત. `BALANCE`) + ✅ **નવું** controlled `equipment_class_id` dropdown (`EquipmentClass` master, `/recipes/v2/equipment-classes`) |
| Equipment Requirement: `require_current_calibration`/`_qualification`/`_cleaning` | ✅ **હવે batch-step-start પર ખરેખર enforce થાય છે** (ડોક્યુમેન્ટ ૦૮ §૮.૩ જુઓ) — પહેલાં ફક્ત captured હતા |

**Rules attachment:** Step dependency (conditional branching) અને Parameter (calculation/limit) —
બંને એક **released** Rules-module rule ને point કરે છે (existence-check completeness-time પર). Rules
Engine `Decimal` arithmetic વાપરે છે (CC-1 થી CC-10 calculation classes, દરેકનો પોતાનો rounding mode)
— ક્યારેય binary float નહીં.

---

## ૭.૬ Permission મેટ્રિક્સ

| Action | Permission Code | કોણ ધરાવે છે | E-signature? |
|---|---|---|---|
| Draft Create/Edit/Validate/Simulate/Submit | `recipe.author` | Admin, **Process Engineer** | ના |
| **Release** | `recipe.release` | Admin, **QA Releaser** | **હા** — "Released" |
| **Suspend** ✅ નવું | `recipe.suspend` | Admin, **QA Releaser** | **હા** — "Performed", reason ફરજિયાત |
| **Reinstate** ✅ નવું | `recipe.suspend` | Admin, **QA Releaser** | **હા** — "Approved", independent of whoever suspended |
| **Obsolete** ✅ નવું | `recipe.suspend` | Admin, **QA Releaser** | **હા** — "Approved", **independent of the author** |
| **Supersede** ✅ નવું | `recipe.suspend` | Admin, **QA Releaser** | **હા** — "Approved", **independent of the author**, `superseding_version_id` ફરજિયાત |
| View | `recipe.view` | બધા operational roles | ના |

**Process Engineer role હવે real, dedicated authoring role છે** — Admin-only નથી (અગાઉનો gap હવે
resolved — code comment: "Closes the DDCP_Client_Demo_Guide §9.1 'author == releaser' gap").

---

## ૭.૭ Segregation of Duties — Author ≠ Releaser (Code-Level)

Product Master ની જેમ જ — `release_recipe_version()` ચકાસે છે કે release કરનાર, draft ના author થી
અલગ વ્યક્તિ છે. **બે અલગ login જરૂરી:** `process.engineer` (author) → `qa.releaser` (release).

---

## ૭.૮ ડેમો વોકથ્રુ — Example Filled Data (Live-Tested Dataset)

**Login: `process.engineer` / `ChangeMe123!`**

### Step 1 — Recipe Draft Create (`/recipe-master`)

| Field | Value |
|---|---|
| Recipe Code | `RCP-MJ-PFS-V1` |
| Linked Product Version | `MERIDIJECT-PFS` v1 (released — ડોક્યુમેન્ટ ૦૬) |
| Batch Size | `5000 units` |

### Step 2 — Section + Steps ઉમેરવા

| Section | Step | Type | Instruction |
|---|---|---|---|
| Dispensing | `STEP-A` | `weigh` | "Sodium Chloride 40mg ±0.5mg weigh કરવું" |
| Filling | `STEP-B` | `material_consume` | "Bulk solution consume — DDCP handoff સાથે link" |
| Assembly | `STEP-C` | `assembly` | "Needle-shield assembly — device DDCP ref" |
| QC | `STEP-D` | `ipc_qc` | "Fill-weight IPC check" |

### Step 3 — Material Requirement ઉમેરવી (BOM)
Material Spec Version FK પસંદ કરવી (ડોક્યુમેન્ટ ૦૩ માં released spec).

### Step 4 — Validate + Submit (`process.engineer`)

### Step 5 — Release (`qa.releaser`, **e-signature ફરજિયાત**)
Recipe → `released` state → હવે batch (ડોક્યુમેન્ટ ૦૮) આ recipe version પરથી બની શકે.

### Step 6 — Suspend/Reinstate/Obsolete/Supersede ✅ નવું (`qa.releaser`, **draft author થી અલગ**)

Product Master (ડોક્યુમેન્ટ ૦૬ §૬.૭ Step 6) જેવો જ pattern — same independence rule:
- **Suspend/Reinstate:** independent of whoever suspended.
- **Obsolete/Supersede:** independent of **draft ના author** (`process.engineer`).

| Action | Reason ઉદાહરણ |
|---|---|
| Suspend | "Material spec under review — temporary hold" |
| Reinstate | "Review complete, spec confirmed" |
| Obsolete | "Recipe replaced by next-gen process" |
| Supersede | `superseding_version_id` = બીજો released recipe version (same recipe_code family), reason "Replaced by v2" |

---

## ૭.૯ ધ્યાન રાખવા જેવી બાબતો (Known Limitations)

1. ~~🔴 Recipe Master માં suspend/reinstate/obsolete/supersede — કંઈ જ built નથી.~~ **✅ Fixed
   (2026-09-18)** — §૭.૩/૭.૬/૭.૮ જુઓ. Signature shape SG-208 માં logged, project-owner confirmation
   બાકી.
2. **`RecipeStep.qualification_policy_id`, `signature_policy_id`, `exception_policy_id`,
   `RecipeSection.area_requirement_id`** — raw UUID fields, **કોઈ backing entity નથી, UI માં પણ
   નથી** — deliberately unbuilt (prior session decision: no confirmed referent) — demo માં આ ના
   બતાવવા.
3. ~~`RecipeEquipmentRequirement` ના calibration/qualification/cleaning flags capture થાય છે પણ
   batch-step-start સમયે enforce નથી થતા~~ **✅ Fixed (2026-09-18)** — ડોક્યુમેન્ટ ૦૮ §૮.૩ જુઓ.
   `require_current_cleaning` ની verification `equipment.cleanliness_status` field સામે થાય છે —
   actual cleaning-execution record સામે live-tested નથી (SG-207).
4. ~~`equipment_class` free string છે~~ **✅ Fixed (2026-09-18)** — હવે `EquipmentClass` master entity
   (`equipment_class_id`) સાથે link — free-string field legacy compatibility માટે kept.
