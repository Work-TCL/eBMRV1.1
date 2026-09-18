# ૯. DDCP — Device/Drug Combination Product Execution — Gujarati Demo Guide

> Source: `services/gxp-api/app/modules/ddcp/{models,commands,router}.py`,
> `frontend/src/app/ddcp/page.tsx`, `frontend/src/components/ddcp/catalog.ts`,
> `services/gxp-api/scripts/seed.py`.

---

## ૯.૧ DDCP એટલે શું?

**DDCP = Drug/Device Combination Product execution.** જ્યારે product એક combination device હોય
(દા.ત. Pre-Filled Syringe – PFS, Autoinjector, Inhalation device, Coated device), ત્યારે drug fill
અને device assembly બંનેને covers કરતા specialized execution steps જોઈએ — એ જ DDCP module કરે છે.

**૪ Product Families:** PFS (Injectable), Autoinjector, Inhalation, Coated Device — બધા સરખા UI અને
સરખા permission codes વાપરે છે.

**DDCP profile ⟷ Batch જોડાણ:** DDCP નું કોઈ column `gxp_batch` ને point નથી કરતું — દરેક DDCP record
(handoff, fill operation, assembly record) પોતે `batch_id` (એ જ `gxp_batch` ટેબલ, જે batch-execution
વાપરે છે) directly ધરાવે છે, અને `profile_version_id` દરેક command માં caller એ જાતે આપવો પડે છે.
મતલબ — **DDCP એ generic batch record પર જ "layer" કરે છે**, અલગ batch concept નથી — પણ operator ને
દરેક વખતે સાચો profile જાતે પસંદ કરવો પડે.

---

## ૯.૨ પ્રોફાઇલ ⟷ Product Master જોડાણ

DDCP Profile version હવે `product_version_id` ધરાવે છે — એટલે profile એક **released Product Master
version** સાથે જોડાયેલ છે. PFS અને Inhalation family માટે manufacturing-profile-code પણ cross-check
થાય છે; Autoinjector/Coated Device માટે આ ચેક હજુ open item છે.

---

## ૯.૩ Execution Steps — સંપૂર્ણ ક્રમ (PFS ઉદાહરણ)

| # | સ્ટેપ | કોણ | Command |
|---|---|---|---|
| ૧ | Profile author + release | **DDCP Engineer** | `create_injectable_profile_version` → `release_injectable_profile_version` |
| ૨ | Constituent handoff record | DDCP Operator | `record_constituent_handoff` (PENDING) |
| ૩ | **Handoff Decide** (Accept/Reject) | DDCP Operator | `decide_constituent_handoff` — source batch/lot ખરેખર `released` છે કે નહીં ચેક કરે |
| ૪ | Batch Readiness Check | DDCP Operator | `evaluate_injectable_batch_readiness` — line/EM/equipment eligibility + બધા mandatory handoffs ACCEPTED |
| ૫ | Filling Stage Start | DDCP Operator | `start_filling_stage` |
| ૬ | **Fill Sub-actions**: IPC result, aseptic intervention, count | DDCP Operator | `record_fill_ipc_result`, `record_aseptic_intervention_for_fill`, `record_syringe_unit_or_count` |
| ૭ | Filling Complete | DDCP Operator | `complete_filling_stage` (hold ખુલ્લો હોય તો complete ના થાય) |
| ૮ | Device Assembly Step | DDCP Operator | `record_device_assembly_step` (PASS/FAIL/REWORK) |
| ૯ | **Independent Verify (IND-001)** | **બીજો** DDCP Operator | `verify_device_assembly_step` |
| ૧૦ | Functional Test Link | DDCP Operator | `record_pfs_functional_test` (QC result ને link કરે, duplicate નથી કરતું) |
| ૧૧ | Release Readiness Evaluate | DDCP Operator | `evaluate_pfs_release_readiness` |
| ૧૨ | Evidence Package બનાવવું | DDCP Operator | `create_pfs_batch_evidence_package` |

---

## ૯.૪ IND-001 — Independent Verification શા માટે?

Device assembly step **જે વ્યક્તિએ performed કરી, એ જ વ્યક્તિ verify ના કરી શકે** — database-level
`CHECK` constraint (`verified_by ≠ performed_by`) છે, ઉપરાંત application code માં પણ ચેક છે (friendly
error: "The performer of an assembly step cannot also verify it").

**એટલે જ `ddcp.operator2` નામનો બીજો demo login seed કરેલ છે** — બંને `ddcp.operator`/`ddcp.operator2`
**એક જ role (DDCP Operator)** ધરાવે છે (RBAC થી અલગ ના પાડી શકાય), પણ **user identity** થી અલગ પડે
છે — ડેમોમાં assembly step `ddcp.operator` થી કરવી, verify `ddcp.operator2` થી કરવું.

---

## ૯.૫ Permission મેટ્રિક્સ

| Permission Code | Action | કોણ ધરાવે છે |
|---|---|---|
| `ddcp_profile.author` | Profile draft author | Admin, **DDCP Engineer** |
| `ddcp_profile.release` | Profile version release | Admin, **DDCP Engineer** |
| `ddcp_constituent.handoff` | Constituent handoff record | Admin, **DDCP Operator** |
| `ddcp_constituent.decide` | Handoff Accept/Reject | Admin, DDCP Operator |
| `ddcp_fill.start` | Fill stage start | Admin, DDCP Operator |
| `ddcp_fill.record_ipc` | Fill IPC result | Admin, DDCP Operator |
| `ddcp_fill.record_count` | Production count | Admin, DDCP Operator |
| `ddcp_fill.record_intervention` | Aseptic intervention link | Admin, DDCP Operator |
| `ddcp_fill.complete` | Fill stage complete | Admin, DDCP Operator |
| `ddcp_device.assemble` | Assembly step record | Admin, DDCP Operator |
| `ddcp_device.verify` | Independent verify | Admin, DDCP Operator (**અલગ વ્યક્તિ**) |
| `ddcp_device.record_test` | Functional test link | Admin, DDCP Operator |
| `ddcp_release.evaluate` | Release readiness | Admin, DDCP Operator |
| `ddcp_release.export` | Evidence package | Admin, DDCP Operator |

**DDCP Engineer role ને ફક્ત authoring/release permission છે — execution નથી** (ઇરાદાપૂર્વક SoD).

**Seeded logins:** `ddcp.engineer`, `ddcp.operator`, `ddcp.operator2` — બધા `ChangeMe123!`.

---

## ૯.૬ ⚠️ E-signature — DDCP માં હાલ કોઈ પણ action signed નથી

**અગત્યનો gap:** DDCP ના દરેક action માટે signature machinery code માં wired છે, પણ **`signature_
required=False`** resolve થાય છે — કારણ કે WP-08 ના કોઈ પણ action માટે હજુ real Document 106 policy
row seed નથી થયેલ (SG-148, code comment માં જ સ્પષ્ટ). એટલે device-assembly PASS/FAIL, independent
verify, handoff accept/reject — બધું **RBAC-only** છે, password re-entry નથી. Client ને honestly
કહેવું: "signature ceremony machinery ready છે, policy row બાકી છે."

---

## ૯.૭ ડેમો વોકથ્રુ — Example Filled Data (PFS — MeridiJect)

**Logins:** `ddcp.engineer` → `ddcp.operator` → `ddcp.operator2`

### Step 1 — Profile Author + Release (`ddcp.engineer`)

| Field | ઉદાહરણ |
|---|---|
| Profile Code | `injectable_ddcp` |
| Product Version | MeridiJect PFS released version |
| Constituent Requirements | Drug (bulk solution), Device (syringe barrel + plunger), Label |

### Step 2-3 — Constituent Handoff + Decide (`ddcp.operator`)

| Field | ઉદાહરણ |
|---|---|
| Constituent Type | `DRUG` |
| Source | Released bulk batch `MJ-2026-0142` |
| Decision | `ACCEPT` |

### Step 4 — Readiness Check (`ddcp.operator`)
Line + EM + equipment eligibility + બધા mandatory handoffs ACCEPTED → `READY`.

### Step 5-7 — Filling (`ddcp.operator`)

| Field | ઉદાહરણ |
|---|---|
| Fill Weight IPC | `2.05 mg` (within limits) |
| Aseptic Intervention | "Line clearance re-verify — minor stop" |
| Count | `4,980 units filled` |

### Step 8 — Device Assembly (`ddcp.operator`)

| Field | ઉદાહરણ |
|---|---|
| Step Type | `NEEDLE_INSTALL` |
| Result | `PASS` |

### Step 9 — Independent Verify (**`ddcp.operator2` — અલગ login!**)
Assembly step verify → PASS confirm.

### Step 10-12 — Functional Test → Release Readiness → Evidence Package (`ddcp.operator`)

---

## ૯.૮ ધ્યાન રાખવા જેવી બાબતો (Known Limitations)

1. **DDCP profile ⟷ batch structural FK નથી** — operator એ દરેક વખતે સાચો profile જાતે પસંદ કરવો
   પડે, સિસ્ટમ auto-detect નથી કરતું (સિવાય કે product-family based auto-detect UI level પર છે).
2. **DDCP માં કોઈ પણ action e-signed નથી** (ઉપર ૯.૬ જુઓ) — RBAC-only.
3. **Autoinjector/Coated Device family માટે Product Master cross-check હજુ enforce નથી** — ફક્ત
   PFS/Inhalation માટે.
4. **Genealogy write API DDCP events થી હજુ auto-populate નથી થતું** — ડેમોમાં genealogy trace ઓછો
   ડેટા બતાવી શકે.
