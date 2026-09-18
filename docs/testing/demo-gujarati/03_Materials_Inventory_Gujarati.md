# ૩. Suppliers, Materials, Material Specifications, Inventory, Dispensing — Gujarati Demo Guide

> Source: `services/gxp-api/app/modules/{supplier_quality,material}/**`,
> `frontend/src/app/{suppliers,supplier-cases,materials,material-specifications,material-lots,
> material-receipts,inventory,dispensing}/**`, `services/gxp-api/scripts/seed.py`.

---

## ૩.૧ Supplier Management

**શું છે:** Supplier/manufacturer register કરવા, formal qualification (risk class, scope, evidence,
quality agreement) run કરવી, અને supplier quality case/SCAR manage કરવા.

| Route | કરે છે |
|---|---|
| `/suppliers` | List, register (code/legal name/role type/country), detail → qualification request/approve |
| `/supplier-cases`, `/supplier-cases/[id]` | Case ખોલવો, SCAR issue, supplier response, review, effectiveness, close |

| Action | Permission | કોણ | Signed? |
|---|---|---|---|
| Supplier Create | `supplier.create` ✅ | Admin, **Process Engineer** | ના |
| Qualification Request | `supplier_qualification.create` ✅ | Admin, **Process Engineer** | ના |
| Qualification View | `supplier.view` | View-capable roles | — |
| **Qualification Approve** | `supplier_qualification.approve` | Admin, **QA Releaser** | **હા** — "Approved", independent (requester ≠ approver) |

**Example:** Supplier Code `SUP-MERIDIAN-EXC` — "Excipients Corp Ltd." — role_type `Manufacturer` —
country `USA`.

**Login:** `process.engineer` (create + qualification request) → `qa.releaser` (approve, અલગ વ્યક્તિ).

> ✅ **2026-09-18 Fixed:** અગાઉ Supplier create/qualification-request પર કોઈ RBAC ચેક જ નહોતી — હવે
> Process Engineer + Admin જ કરી શકે (project-owner decision, material.create જેવો જ pattern).

---

## ૩.૨ Material Master

| Route | કરે છે |
|---|---|
| `/materials` | List, create (code/name/uom), edit (name/status — code immutable), delete (lot reference હોય તો block) |

| Action | Permission | કોણ | Signed? |
|---|---|---|---|
| Create / Update | `material.create` / `material.update` ✅ | Admin, **Process Engineer** | ના |
| Delete | `platform.administer` | ફક્ત Admin | ના |

**Example:** Code `MAT-EXCIPIENT-01` — Name "Sodium Chloride USP" — UOM `kg`.

**Login:** `process.engineer`.

> ✅ **2026-09-18 Fixed:** અગાઉ Material create/update પર કોઈ RBAC ચેક જ નહોતી.

---

## ૩.૩ Material Specifications

**શું છે:** Material master થી અલગ, versioned, controlled acceptance-criteria spec.

| Route | કરે છે |
|---|---|
| `/material-specifications` | Draft create (business ID + version + material + name), version lookup, release |

| Action | Permission | કોણ | Signed? |
|---|---|---|---|
| Draft Author | `material_spec.author` | Admin, **Process Engineer** | ના |
| View | `material_spec.view` | Admin, Process Engineer | — |
| **Release** | `material_spec.release` | Admin, **QA Releaser** | **હા** ✅ — "Released", independent of drafting author (SG-185, fixed 2026-09-18) |

**Example:** Business ID `MATSPEC-PFS-BODY-001`, Version `1`, Material `MAT-SYRINGE-BODY`.

**SoD:** Product/Recipe Master ની જેમ જ — draft author (`process.engineer`) અને release કરનાર
(`qa.releaser`) **અલગ વ્યક્તિ** હોવી જોઈએ, નહીંતર SoD conflict error આવશે.

---

## ૩.૪ Material Lots, Receipts, Inventory

**બે અલગ intake path અસ્તિત્વમાં છે:**

### (a) Legacy Quick-Receive (`/material-lots`)
`POST /materials/{id}/lots` — **કોઈ RBAC gate નથી, કોઈ signature નથી** — કોઈ પણ logged-in user lot
ને સીધો quarantine માં નાખી શકે.

### (b) Formal Receiving Flow — Document 19 (`/material-receipts`)
| Step | Permission | કોણ | Signed? |
|---|---|---|---|
| Receipt Log | `material_receipt.create` | Admin, Operator, Supervisor | ના |
| Examine (clean → lot auto-બને; discrepancy → hold) | `material_receipt.examine` | Admin, Operator, Supervisor | ના |

**Disposition (Quarantine → Release/Reject) — બે parallel mechanism, બંને હવે UI માં:**

| Path | UI Available? | Permission | કોણ | Signed? |
|---|---|---|---|---|
| Legacy Disposition (`/material-lots`, "Disposition" button) | ✅ | `material_lot.disposition` | Admin, **QC Reviewer** | **હા** — "Approved", independent |
| Document-19 v2 Release/Reject (`/material-lots`, "Release (QA)"/"Reject (QA)" buttons) | ✅ **2026-09-18 ઉમેર્યું** | `material_lot.release`/`.reject` | Admin, **QA Releaser** | **હા** — "Released"/"Rejected", SoD: receiver/sampler signer ના બની શકે |

> ✅ **2026-09-18 Fixed:** Backend endpoints (`POST /materials/v1/lots/{id}/release`/`reject`) અને
> signature policy પહેલેથી જ તૈયાર હતા — ફક્ત frontend UI missing હતી. હવે quarantine lot પર
> `qa.releaser` login થી "Release (QA)"/"Reject (QA)" buttons દેખાય છે (QA Releaser + Admin ને જ,
> independence server-side enforced — receiver/sampler પોતે sign ના કરી શકે).

**Retest, Sampling:** `material_lot.retest`, `.sampling_order`, `.collect_sample` — બધા RBAC-gated,
unsigned.

**Inventory (`/inventory`):** Availability, Reservation (release = signed, "Released"), Transfer,
Split/Merge container, Cycle Count (unsigned, "routine" correction), Warehouse Location (Admin/
Supervisor), **Exceptional Adjustment** (create → Operator/Supervisor; **approve/reject → Admin/QA
Releaser, signed, reason required, independence enforced** — requester પોતાના જ adjustment approve ના
કરી શકે).

**Example:** Warehouse `WH1`, Location `QUARANTINE-02`, Lot `LOT-MJ-2026-014`.

---

## ૩.૫ Dispensing (`/dispensing`)

**શું છે:** Batch માટે material lot નું controlled weighing — SoD સાથે independent verify.

| Step | Permission | કોણ | Signed? | Meaning |
|---|---|---|---|---|
| Order Create | `dispensing_order.create` | broad | ના | — |
| Select Source / Start / Readings / Manual Reading / Complete | `dispensing_order.*` | **Operator** | **હા** | "Performed" |
| **Verify** | `dispensing_order.verify` | **QC Reviewer** | **હા** | "Verified" — **independent (weigher ≠ verifier)** |
| Cancel | `dispensing_order.cancel` | QA Releaser | **હા** | "Approved", reason required, independent |

**Example:**

| Field | ઉદાહરણ |
|---|---|
| Batch | `MJ-2026-0142` |
| Material | `MAT-EXCIPIENT-01` |
| Target Qty | `2.5 kg`, tolerance `±0.1 kg` |

**Weigh (`operator1`)** → target ની અંદર reading લખવી → **Verify (`qc.reviewer`, અલગ વ્યક્તિ)**.

---

## ૩.૬ ધ્યાન રાખવા જેવી બાબતો (Known Limitations)

1. ~~Supplier/Material create/update — કોઈ RBAC gate નથી~~ **✅ Fixed (2026-09-18)** — Process
   Engineer + Admin જ.
2. **Legacy material lot receipt (`/materials/{id}/lots`) — RBAC gate/signature બંને નથી** (હજુ ખુલ્લું
   — આ પાસમાં ટચ નથી કર્યું, Document-19 formal receiving flow (§૩.૪-b) વાપરવાની ભલામણ).
3. ~~Material Specification Release non-functional~~ **✅ Fixed (2026-09-18)** — signature policy
   seed થયેલ, release હવે કામ કરે છે.
4. ~~Document-19 v2 lot release/reject માટે કોઈ UI નથી~~ **✅ Fixed (2026-09-18)** — હવે
   `/material-lots` પર "Release (QA)"/"Reject (QA)" buttons.
5. **🔴 Batch material consumption inventory ને automatic link નથી કરતું** (code-level ચકાસેલ,
   2026-09-18) — Client demo માટે **અગત્યનું clarification**:
   - **બે અલગ, unsynchronized quantity track છે:**
     - **Track A:** `MaterialLot.available_quantity` — ફક્ત `issue_material_to_batch()`
       (`POST /batches/{id}/material-issues`, જૂનો/સાદો path) અને destruction દ્વારા move થાય છે.
       Genealogy trace (`MaterialIssue` rows) પણ આ path જ બનાવે છે.
     - **Track B:** `InventoryBalanceProjection` (on_hand/reserved/available) — Reservation →
       Dispensing (§૩.૫) → `record_consumption()` flow દ્વારા move થાય છે. `MaterialLot` ને touch
       જ નથી કરતું.
   - **Batch execution નો `material_consume` recipe step type** (ડોક્યુમેન્ટ ૦૭ §૭.૪) હાલમાં **ફક્ત
     એક label છે** — `batch_execution/commands.py` માં material module નો import જ નથી, કોઈ
     step_type dispatch જ નથી. એટલે batch માં `material_consume` step run કરવાથી **inventory માંથી
     કંઈ deduct નથી થતું** — automatic રીતે.
   - **ડેમોમાં inventory movement બતાવવા માટે:** Dispensing flow (§૩.૫) અલગથી run કરવો પડે — batch
     execution step ના result સાથે એ linked નથી.
   - Real fix (batch step → inventory deduction auto-wire) એક નવો, પોતાનો scoping decision-set
     માંગે છે (કયો track વાપરવો — A કે B? બંને reconcile કરવા?) — client સાથે discuss કરીને પછી
     build કરવું.
