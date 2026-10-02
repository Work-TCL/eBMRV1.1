## ૧૭. સંપૂર્ણ Platform Field-by-Field Data Guide + Fixed Bugs Test Cases (Gujarati)

> **હેતુ:** આ **એક જ, સ્વયં-સંપૂર્ણ (self-contained)** ડોક્યુમેન્ટ છે — તમારે બીજા doc ખોલવાની જરૂર
> ના પડે એ રીતે બનાવેલું છે. એમાં ત્રણ વસ્તુ છે:
>
> 1. **Material Consumption ↔ Inventory System કેવી રીતે કામ કરે છે** — આખા flow ની સમજૂતી.
> 2. **Field-by-field Data Guide** — Materials/Suppliers, Recipe Master, Product Master, Batch
>    Execution, Inventory, CAPA, Deviation, Equipment, QC Testing, Batch Release, Batch Review —
>    દરેક form નું દરેક field, backend નું ચોક્કસ field name સાથે, જેથી browser માં ટેસ્ટ કરતી
>    વખતે તમે બરાબર શું ભરવું એ જાણો.
> 3. **બધા Fixed Bugs ના Test Cases** (2026-09-22 gap-audit session, doc #૧૬ ના ૧૬.૧-૧૬.૭ નો
>    સંક્ષિપ્ત સાર + ૧૬.૮/૧૬.૯ નું પૂરું વિગતવાર પગલું-દર-પગલું, field references સાથે).
>
> **જરૂરી:** Browser માં app ખોલો. **Password બધા demo user માટે સરખો:** `ChangeMe123!`
> Backend field names હંમેશા `આ રીતે` (code font, English) લખેલા છે — એ frontend form ના પાછળ
> ખરેખર API ને મોકલાતું નામ છે, ફક્ત reference માટે, તમારે ટાઈપ કરવાની જરૂર નથી.

---

## ભાગ ૦ — Material Consumption ↔ Inventory System કેવી રીતે કામ કરે છે

આખી chain આ ક્રમમાં ચાલે છે (દરેક તીર `→` નો અર્થ "પછીનું પગલું"):

```
Material Master (ઓળખ)
   → Material Specification Version (સ્વીકાર્ય શું ગણાય — વૈકલ્પિક, recipe step ને ચોક્કસ
     material જોઈએ ત્યારે વપરાય)
   → Supplier (ક્યાંથી આવ્યું)
   → Material Receipt (માલ આવ્યો)
   → Examine (Material Lot બને છે — શરૂઆતમાં status "quarantine")
   → QC Sampling / Release (lot નું status "released" થાય)
   → Put-away (lot કોઈ Warehouse Location માં જાય — હવે Availability list માં દેખાય)
   → Reservation (batch એ lot માંથી ચોક્કસ quantity "બુક" કરે — અહીં FEFO/expiry/
     supplier-status ના check ચાલે છે)
   → Dispensing (Order → Source lot પસંદ → Weigh/Start → Readings → Verify → Complete —
     Dispensed Container બને છે)
   → Consumption (record_consumption — Dispensed Container + Lot ને batch/step સાથે જોડે છે —
     **આજના નવા material-required gate (§૧૬.૮/§ભાગ-૧૨.૧) અહીં જ ચકાસે છે**)
   → Genealogy (supplier lot → internal lot → batch — સંપૂર્ણ traceability)
```

**બે આજના fix આ chain ના જુદા-જુદા બિંદુ પર કામ કરે છે:**
- **Recipe-declared material requirement gate (§૧૨.૧):** batch step complete કરતાં પહેલાં
  Consumption ખરેખર થયું છે કે નહીં એ ચકાસે છે (chain નો છેલ્લો ભાગ).
- **Supplier-suspend gate (§૧૨.૨):** Reservation/Dispensing/Availability બિંદુ પર — Consumption
  પહેલાં જ — supplier હજુ `approved` છે કે નહીં એ ચકાસે છે.

---

## ભાગ ૧ — Login Reference (બધા Module માટે એકસાથે)

| Username | Role | ક્યાં વપરાય છે |
|---|---|---|
| `process.engineer` | Process Engineer | Material/Recipe/Product draft બનાવવા (author) |
| `qa.releaser` | QA Releaser | Material Spec/Recipe/Product/Material Lot **release**, CAPA Plan/Extend/Close, Batch Release/Hold/Reject, Deviation Disposition/Close, OOS Disposition/Close |
| `operator1` | Operator | Material receipt, Reservation, Dispensing, QC sample/order/result entry, Deviation/CAPA raise |
| `supervisor1` | Supervisor | Batch create/issue, Equipment hold, Deviation Triage/Contain |
| `qa.reviewer` | QA Reviewer | Deviation Investigation/Impact, QC test-order review, CAPA plan/action (RBAC પાસ, sign માટે qa.releaser જોઈએ), QA Review package complete, Release Evaluate/Hold |
| `qc.reviewer` | QC Reviewer | Material Lot Release/Reject, QC method author, QC result correction approve, CAPA action complete |
| `equipment.admin` | Equipment Administrator | Equipment asset/area બનાવવા, Qualification record |
| `calibration.tech` | Calibration Technician | Equipment Calibration record |
| `maintenance.tech` | Maintenance Technician | Equipment Maintenance record |
| `engineering.manager` | Engineering Manager | Equipment Return-to-service |
| `admin` | Admin | SCAR/Supplier case, બધે fallback access |

---

## ભાગ ૨ — Materials & Suppliers

### ૨.૧ Material Master (`/materials` → "New material")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ | નોંધ |
|---|---|---|---|---|
| Code | `code` | હા | `RM-TESTMAT` | બન્યા પછી બદલી ના શકાય |
| Name | `name` | હા | `Test Raw Material` | |
| UOM | `uom` | હા | `kg` | Released UOM list માંથી પસંદ કરવાનું |
| Default storage condition | `default_storage_condition` | ના | `Room temperature` | Dropdown |
| Manufactured/maintained in-house | `is_in_house` (checkbox) | ના | — | |

### ૨.૨ Supplier Master (`/suppliers` → "New supplier")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ | નોંધ |
|---|---|---|---|---|
| Supplier code | `supplier_code` | ના (auto) | `SUP-001` | |
| Role type | `role_type` | હા | `supplier` | Dropdown: `supplier`/`manufacturer`/`both` |
| Country | `country` | ના | `US` | |
| Legal name | `legal_name` | હા | `Acme Chemicals Inc.` | |
| Site name | `sites[0].site_name` | ના | `Main Site` | |
| City | `sites[0].city` | ના | — | |

Supplier નો status શરૂઆતમાં `draft`/`under_qualification` હોય છે — receipt માટે વાપરવા `approved`
હોવો જોઈએ (Supplier Qualification approve કરવી પડે, `qc.reviewer`/`qa.releaser` — જુઓ `/suppliers`
detail page નું Qualification tab).

### ૨.૩ Material Specification (`/material-specifications` → "New draft")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ | નોંધ |
|---|---|---|---|---|
| Business ID | `material_spec_business_id` | હા | `SPEC-TESTMAT` | |
| Version number | `version_no` | હા | `1` | |
| Material ID | `material_id` | હા (picker) | — | ઉપર બનાવેલ Material પસંદ કરો |
| Name | `name` | હા | `Test Material Spec v1` | |

**Signed action — Release:** role `QA Releaser` (independent of author), meaning `Released`.
Author: `process.engineer` (`material_spec.author`). Releaser: `qa.releaser`
(`material_spec.release`).

### ૨.૪ Material Receipt (`/material-receipts` → "New receipt")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ | નોંધ |
|---|---|---|---|---|
| Receipt number | `receipt_number` | હા | `RCPT-001` | |
| Material | `material_id` | હા (picker) | — | |
| PO reference | `po_reference` | ના | — | |
| Carrier / shipment reference | `carrier_reference` | ના | — | |
| Supplier | `supplier_id` | ના (picker) | — | RCV-FR-005 gate આ field પર આધારિત |
| Manufacturer | `manufacturer_id` | ના | — | ફક્ત supplier થી અલગ હોય તો |
| Supplier's lot number | `supplier_lot` | ના | — | |
| Manufacturer's lot number | `manufacturer_lot` | ના | — | |
| Received quantity (gross) | `received_gross_quantity` | હા | `100.000000` | |
| Received quantity (net) | `received_net_quantity` | ના | — | |
| Accepted quantity | `accepted_quantity` | ના | (gross જ default) | |
| Manufacture date | `manufacture_date` | ના | — | |
| Expiry date | `expiry_date` | ના | — | |
| Retest date | `retest_date` | ના | — | |
| Shipment condition | `shipment_condition_status` | ના | — | |
| CoA document hash | `coa_document_hash` | ના | — | |

### ૨.૫ Examine Receipt (receipt detail → "Examine")

| UI Label | Backend field | જરૂરી? | નોંધ |
|---|---|---|---|
| Identity confirmed | `identity_confirmed` (Yes/No) | હા | "No" → discrepancy hold |
| Labeling correct | `labeling_ok` | હા | |
| Damage observed | `damage_observed` | હા | "Yes" → discrepancy hold |
| Seal broken | `seal_broken` | હા | |
| Contamination observed | `contamination_observed` | હા | |
| Container count | `container_count` | ના (default ૧) | |
| Internal lot number | `internal_lot` | હા | Material Lot આ number થી બને છે |

Clean examine (બધા Yes/No યોગ્ય) + supplier `approved` → lot `quarantine` માં બને છે. Supplier
`approved` ના હોય → discrepancy hold, `source_not_approved` (જુઓ ભાગ ૧૨.૨).

### ૨.૬ Material Lot Release/Reject (`/material-lots` → lot ની row → "Release (QA)"/"Reject (QA)")

Role: `QA Releaser` (`material_lot.release`/`.reject`), signed, meaning `Released`. (જૂનું
"Disposition" બટન QC Reviewer sign કરતું — હવે કાયમ માટે કાઢી નાખેલું છે, જુઓ ભાગ ૧૨.૫.)

### ૨.૭ Warehouse Location (`/inventory` → Availability tab → "New location")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ | નોંધ |
|---|---|---|---|---|
| Warehouse code | `warehouse_code` | હા | `WH-01` | એક building/site ને ગ્રુપ કરે છે |
| Location code | `location_code` | હા | `LOC-TEST-01` | Warehouse code અંદર unique |
| Zone type | `zone_type` | હા | `quarantine`/`released`/`rejected` | Dropdown |

**Rename/Retire:** Location row → pencil icon (rename: Location code, Zone type બદલી શકાય) અથવા
Retire (Reason ફરજિયાત — material store થયેલું હોય તો error આવે).

### ૨.૮ Put-away / Transfer (`/inventory` → Transfer tab)

| UI Label | Backend field | જરૂરી? |
|---|---|---|
| Material lot | `material_lot_id` | હા |
| Container | `container_id` | ના |
| From location | `from_location_id` | ના (blank = પહેલું put-away) |
| To location | `to_location_id` | હા |
| Quantity | `quantity` | હા |

### ૨.૯ Inventory Reservation (`/inventory` → "Reserve")

| UI Label | Backend field | જરૂરી? |
|---|---|---|
| Batch | `batch_id` | હા |
| Material | `material_id` | હા |
| Quantity | `quantity` | હા |
| UOM | `uom` | હા |

**Eligibility ચકાસાય છે (`_is_eligible`):** lot status `released`, expiry/retest date ના વીતેલી
હોય, **supplier `approved`** (આજનું નવું check, § ભાગ ૧૨.૨). કોઈ પણ શરત ના મળે → error: `No
eligible released, non-expired, non-retest-due lot/container has sufficient available quantity
for this reservation`.

### ૨.૧૦ Dispensing (`/dispensing` — Order → Source → Start → Readings → Verify → Complete)

| પગલું | Endpoint | મુખ્ય fields |
|---|---|---|
| Create order | `/dispensing/v1/orders` | Batch, Material, Target qty/UOM, Tolerance low/high |
| Select source | `/orders/{id}/select-source` | Reservation અથવા Material lot + Container |
| Start | `/orders/{id}/start` | (qualification gate) |
| Manual reading | `/orders/{id}/manual-reading` | Actual weight |
| Verify | `/orders/{id}/verify` | (independence-from-performer) |
| Complete | `/orders/{id}/complete` | inventory consumption + Dispensed Container બને |

**Select-source પર પણ supplier-eligibility ફરી ચકાસાય છે** (§ ભાગ ૧૨.૨) — DSP-FR-025.

### ૨.૧૧ Material Consumption (backend-only, હાલમાં કોઈ UI button નથી)

`POST /materials/v1/consumptions` — fields: `batch_id`, `step_id` (વૈકલ્પિક), `dispensed_container_id`,
`material_lot_id`, `quantity`, `uom`. **⚠️ જાણીતી મર્યાદા:** frontend માં આ call કરતું કોઈ button
અત્યારે નથી — batch step ના material-gate ને "consumption પછી step complete થાય છે" સુધી પૂરું
browser-click થી ચકાસી શકાતું નથી (જુઓ ભાગ ૧૨.૧).

---

## ભાગ ૩ — Recipe Master (`/recipe-master`)

Draft બનાવવા/edit કરવા: recipe draft ખોલો → Section ઉમેરો → એની અંદર Step ઉમેરો → step ની અંદર
નીચેના sub-forms:

| Sub-section | Fields (backend name) |
|---|---|
| **Section** | Section code (`stable_section_code`), Section name (`name`), Parallel group (optional), Expected duration minutes (optional) |
| **Step** | Step code (`stable_step_code`), Step type, Instruction text (`instruction_text`), Required role code (optional), Required qualification code (optional), Expected hold duration minutes (optional), Dependencies (predecessor steps) |
| **Parameter** (`parameters[]`) | Parameter code, Data type (`decimal`/`integer`/`text`/`boolean`), Source (`manual_entry`/`equipment_reading`/`calculated`/`scan`), Target, Min, Max, Precision, Rule version pin (optional) |
| **Material requirement** (`material_requirements[]`) | Material (spec version picker, `material_spec_version_id`), Target qty, Min qty, Max qty, UOM, Alternative material (`alternative_material_spec_version_id`), Substitution allowed, Consume mode (optional) |
| **Equipment requirement** (`equipment_requirements[]`) | Equipment class label (`equipment_class`), Equipment class (controlled picker, `equipment_class_id`), Exact equipment optional, Require current calibration/qualification/cleaning |
| **Evidence requirement** (`evidence_requirements[]`) | Evidence type (e.g. `photo`/`scan`/`printout`), Required count, Allowed MIME types (optional), Retention class (optional) |
| **QC requirement** (`qc_requirements[]`) | QC test specification (released spec picker) |

**Submit → Release:** role `QA Releaser` (independent of author `recipe.author` = Process
Engineer), meaning `Released`.

---

## ભાગ ૪ — Product Master (`/product-master` → "New draft")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ | નોંધ |
|---|---|---|---|---|
| Business ID | `product_business_id` | હા | `PROD-COMBO-001` | |
| Product code | `product_code` | ના (auto) | `PRD-000123` | |
| Version no. | `version_no` | હા | `1` | |
| Name | `name` | હા | `Combo Pen v1` | |
| Site | `site_id` | હા | — | |
| Manufacturing profile | `manufacturing_profile_code` | હા | `pharma` | Options: `pharma`/`device`/`injectable_ddcp`/`inhalation_ddcp`/`drug_eluting_device` |
| Sterile process profile | `sterile_profile_id` | Release વખતે DDCP profile માટે જરૂરી | — | Released aseptic profile જોઈએ |
| Device model code | `device_model_code` | UDI applicable હોય તો Release વખતે જરૂરી | — | |
| UDI applicable | `udi_applicable` (checkbox) | ના | — | |
| Product family | `product_family_id` | ના | — | "+ New family" થી પણ બની શકે |
| Combination product type | `combination_product_type` | ના | `prefilled_syringe` | |
| Strength value / UOM | `strength_value`/`strength_uom` | ના | `10`/`mg` | |
| Constituents | `constituents[]` | Combination type set હોય તો Release વખતે જરૂરી | — | બીજા Product Master version ને link કરે |

**Signed actions:** Submit (unsigned) → **Release** (QA Releaser, independent, meaning
`Released`) → Suspend/Reinstate/Obsolete/Supersede (બધા QA Releaser, reason ફરજિયાત).
Author: `process.engineer` (`product.author`).

---

## ભાગ ૫ — Batch / Batch Execution (`/batch-execution`)

### ૫.૧ Create Batch

| UI Label | Backend field | જરૂરી? |
|---|---|---|
| Batch number | `batch_number` | હા |
| Product | (picker) | હા |
| Product version | `product_version_id` | હા (Released only) |
| Recipe | (picker) | હા |
| Recipe version | `recipe_version_id` | હા (Released only, product version સાથે match) |
| Target quantity | `target_qty` | હા |
| UOM | `target_uom` | હા |
| Production order ref | `production_order_ref` | ના |

### ૫.૨ Lifecycle actions

| Action | Endpoint | Signed? | નોંધ |
|---|---|---|---|
| Issue | `/{id}/issue` | ના | Execution snapshot freeze થાય |
| Start | `/{id}/start` | ના | |
| Step: Start | `/steps/{id}/start` | ના | Role/qualification/equipment gate |
| Step: Record results | `/steps/{id}/results` | ના | Parameter values |
| Step: Complete | `/steps/{id}/complete` | **હા** (`Performed`) | Parameter/Evidence/QC/**Material** gates (§ભાગ ૧૨.૧) |
| Hold/Resume batch | `/{id}/hold`, `/{id}/resume` | ના (reason capture) | |
| Step hold/resume | `/steps/{id}/hold`, `/resume` | **હા** | |
| Production complete | `/{id}/production-complete` | ના | બધા step complete હોય તો જ |
| Batch record PDF | Batch record modal → "Generate PDF" | **હા** (QA Releaser, reason ફરજિયાત) | § ડોક #૧૬ ૧૬.૪ |

---

## ભાગ ૬ — CAPA (`/capa`)

### ૬.૧ Raise CAPA

| UI Label | Backend field | જરૂરી? | નોંધ |
|---|---|---|---|
| CAPA number | `capa_number` | હા | |
| Risk class | `risk_class` | હા | `high`/`medium`/`low` |
| Target date | `target_date` | હા | |
| Problem statement | `problem_statement` | હા | |
| Source type | `source_type` | હા | `deviation`/`oos`/`oot`/`ncr`/`complaint`/`audit`/`supplier`/`risk`/`trend`/`security`/`validation` |
| Source record | `source_id` | હા | Picker (deviation/ncr/complaint/audit/supplier) અથવા free text |
| Investigation reference | `root_cause_ref.investigation_ref` | હા (proactive ના હોય તો) | |

### ૬.૨ Signed actions (role `QA Releaser`, independent of owner)

| Action | Fields |
|---|---|
| **Plan approval** | Corrective action, Preventive action, Effectiveness plan |
| **Extend target date** | New target date, Reason, Risk review |
| **Close** | Conclusion |
| **Record effectiveness result** | Effectiveness check, Result (`pass`/`fail`/`inconclusive`), Evidence |

⚠️ `qa.reviewer` પાસે Plan/Extend ની **RBAC permission** છે (button દેખાય/click થાય) પણ signature
role check `QA Releaser` માંગે છે — એટલે `qa.reviewer` sign **નહીં** કરી શકે (ROLE_MISSING). ફક્ત
`qa.releaser` જ પૂરું sign કરી શકે. જુઓ ડોક #૧૬ ૧૬.૩.

---

## ભાગ ૭ — Deviation (`/deviations`)

### ૭.૧ Raise Deviation

| UI Label | Backend field | જરૂરી? | નોંધ |
|---|---|---|---|
| Deviation number | `deviation_number` | હા | |
| Type | `deviation_type` | હા | Free text, દા.ત. `process` |
| Severity | `severity` | હા | `critical`/`major`/`minor` |
| Source type | `source_type` | હા | `batch`/`qc`/`material`/`equipment`/`environment`/`supplier`/`document`/`system` |
| Source record | `source_id` | હા | Picker અથવા free text |
| Planned deviation | `planned` (checkbox) | ના | Yes → Scope/Start/End date પણ ફરજિયાત |

### ૭.૨ Pipeline (Triage → Contain → Investigation → Impact → Disposition → Close)

| પગલું | Fields | Role | Signed? |
|---|---|---|---|
| Triage | Severity, Investigation priority, Product impact | Supervisor/QA Reviewer | ના |
| Contain | Immediate correction, Containment, Reason | Supervisor/QA Reviewer | ના |
| Investigation | Investigator, Due date, Root cause method, Conclusion | QA Reviewer | ના |
| Impact | Quality/Patient/Product/Validation/Data-integrity/Regulatory impact (૬ fields, બધા ફરજિયાત) | QA Reviewer | ના |
| **Disposition** | Disposition code (`CONTINUE`/`HOLD`/`REJECT`/`REWORK`/`REPROCESS`/`ADDITIONAL_TEST`/`DESTROY`/`FIELD_ACTION_ASSESSMENT`), Rationale, CAPA/Change/Training required+rationale | **QA Releaser** (investigator/owner થી independent) | **હા** |
| **Close** | Conclusion | **QA Releaser** | **હા** |

---

## ભાગ ૮ — Equipment (`/equipment`)

### ૮.૧ New Asset

| UI Label | Backend field | જરૂરી? |
|---|---|---|
| Equipment code | `equipment_code` | હા |
| Manufacturer | `manufacturer` | ના |
| Model | `model` | ના |
| Serial no. | `serial_no` | ના |
| Firmware version | `firmware_version` | ના |
| Dedicated to single product/process | `dedicated` (checkbox) | ના |

### ૮.૨ Action forms (બધા unsigned, ફક્ત Hold signed)

| Action | Fields | Role |
|---|---|---|
| Record qualification | Qualification status, Qualified Yes/No, Effective/Expiry date, Reason | Equipment Administrator |
| Record calibration | Performed date, Next due date, Result (`pass`/`fail`/`oot`), Standard ref, Calibration type, Provider (external હોય તો) | Calibration Technician |
| Record maintenance | Type (`planned`/`corrective`/`breakdown`), Next due date, Fault description, Work performed, Post-maintenance verification | Maintenance Technician |
| **Place on hold** | Hold reason (ફરજિયાત) | Operator/Supervisor/QA Reviewer/QA Releaser — **signed** |
| Return to service | Reason | Engineering Manager |

---

## ભાગ ૯ — QC Testing (`/qc`, `/quality/oos`)

### ૯.૧ Test Specification (Draft → Release)

| UI Label | Backend field | જરૂરી? |
|---|---|---|
| Spec code | `spec_code` | હા |
| Scope type | `scope_type` | હા — `product`/`in_process`/`device` |
| Scope version ID | `scope_version_id` | હા (picker) |
| Test definitions (દરેક) | Test code, Test name, Result data type (`numeric`/`text`/`pass_fail`/`json`), UOM, Required, Release blocking | ઓછામાં ઓછું ૧ |

**Release:** QA Releaser, independent.

### ૯.૨ Sample → Order → Result

| પગલું | Fields |
|---|---|
| Create sample | Sample number, Sample type (`release`/`stability`/`in_process`/`environmental`/`raw_material`/`retain`), Source type (`batch`/`material_lot`/`environment`/`stability_study`/`equipment`), Source record, Quantity/UOM |
| Add test order | Test definition (released spec માંથી), Assigned analyst |
| Record raw data | Method version, Instrument ref, Sample amount |
| Record result | Result type, Value, UOM |
| **Second-person review** | (કોઈ field નહીં) — QA Reviewer, independent of analyst — **signed** |

### ૯.૩ OOS (`/quality/oos`)

Open OOS from result → Lab investigation → Lab cause classify → Retest/Resample plan →
Impact assessment → **Disposition (signed, QA Releaser)** → **Close (signed)**.

---

## ભાગ ૧૦ — Batch Release (`/release`)

| Action | Fields | Role | Signed? |
|---|---|---|---|
| Evaluate eligibility | Scope type (`batch` only), Batch | QA Reviewer/QA Releaser | ના |
| **Release** | Reason (વૈકલ્પિક) | **QA Releaser** (independent of QA Reviewer) | **હા** |
| **Hold** | Reason (ફરજિયાત) | **QA Releaser** | **હા** |
| **Reject** | Reason (ફરજિયાત) | **QA Releaser** | **હા** |

Eligibility check ૯ categories જુએ છે: Manufacturing completeness, QA review, QC, Materials,
Equipment, Environment, CAPA, Yield/Reconciliation (blocking), Packaging (warning only).

---

## ભાગ ૧૧ — Batch Review / QA Review (`/qa-review`)

| Action | Fields | Role | Signed? |
|---|---|---|---|
| Create review package | Batch (picker) | QA Reviewer | ના |
| Reindex | — | QA Reviewer | ના |
| **Complete review** | — (standard password ceremony જ) | **QA Reviewer** | **હા** |

Blockers: batch on hold, integrity-check નિષ્ફળ, QC/Materials/Environment/Equipment/CAPA/Yield
hard-blockers. Warnings (block નથી કરતા): Packaging.

---

## ભાગ ૧૨ — બધા Fixed Bugs ના Test Cases

### ૧૨.૧ — Batch Step: જરૂરી Material વાપર્યા વગર Complete નહીં થાય (નવું, 2026-09-22)

**શું બદલાયું:** Recipe step માં "Material requirement" (ભાગ ૩ જુઓ) જાહેર કરેલું હોય, તો batch
execution વખતે એ material ખરેખર consume ના થયું હોય ત્યાં સુધી step complete **નહીં** થાય.

**Full Test (ભાગ ૨/૩/૪/૫ ના fields વાપરીને):**

1. `process.engineer` → `/materials` → Material બનાવો (ભાગ ૨.૧).
2. `process.engineer` → `/material-specifications` → Draft બનાવો (ભાગ ૨.૩) → Submit.
3. `qa.releaser` → એ spec **Release** કરો.
4. `process.engineer` → `/product-master` → Product draft બનાવો (ભાગ ૪) → Submit → `qa.releaser`
   → **Release**.
5. `process.engineer` → `/recipe-master` → Recipe draft → એ product version પસંદ → Step ખોલો →
   **"Add material requirement"** → ઉપરનો released spec પસંદ કરો (ભાગ ૩) → Submit → `qa.releaser`
   → **Release**.
6. `supervisor1`/`admin` → `/batch-execution` → **New batch** (ભાગ ૫.૧, ઉપરના product+recipe
   version) → **Issue** → **Start**.
7. એ material-requirement વાળું step ખોલો → **Start step**.
8. **Complete step** → sign કરો.
9. ✅ **Expected:** `VALIDATION_FAILED: Required material has not been consumed for this batch` —
   step complete **ના** થાય.

> ⚠️ Consumption record કરવાનું UI હજુ નથી (ભાગ ૨.૧૧) — "consumption પછી unblock થાય છે" એ ભાગ
> pure browser-click થી ચકાસી શકાતો નથી; ઉપરના પગલાં ૭-૯ block ચકાસવા માટે પૂરતા છે.

### ૧૨.૨ — Supplier Suspend → પહેલેથી Received Material પણ Block (નવું, 2026-09-22)

**Full Test:**

1. `admin` → Supplier ને `approved` રાખો → `operator1` → Material receive (ભાગ ૨.૪) → Examine
   (ભાગ ૨.૫, clean) → `qa.releaser` → **Release** (ભાગ ૨.૬) → `operator1` → **Put-away** (ભાગ
   ૨.૮).
2. `/inventory` → Availability → ✅ lot દેખાય છે.
3. `admin` → નવો SCAR → Close → **Source status decision = suspend** (sign).
4. `/inventory` → Availability → ✅ **lot ગાયબ** થઈ ગયો.
5. `operator1` → **Reserve** (ભાગ ૨.૯, એ જ material) → ✅ Error: `VALIDATION_FAILED: No eligible
   released, non-expired, non-retest-due lot/container has sufficient available quantity for this
   reservation`.
6. (વૈકલ્પિક) SCAR `reinstate` → lot પાછો દેખાય, Reserve ફરી સફળ.

### ૧૨.૩ થી ૧૨.૯ — અગાઉના Fixes (ડોક #૧૬ માંથી સંક્ષિપ્ત, પૂરું વિગતવાર doc #૧૬ માં)

| # | શું | સંક્ષિપ્ત Test | પૂરું વિગતવાર |
|---|---|---|---|
| ૧૨.૩ | Login વગર data બંધ | Incognito → data URL → 401 જોઈએ | ડોક #૧૬ § ૧૬.૧ |
| ૧૨.૪ | Sidebar ના હોય તો URL બ્લોક | `calibration.tech` → `/product-master` type → redirect જોઈએ | ડોક #૧૬ § ૧૬.૨ |
| ૧૨.૫ | CAPA Plan/Extend signed | ભાગ ૬.૨ ના fields → `qa.releaser` sign, `qa.reviewer`/negative | ડોક #૧૬ § ૧૬.૩ |
| ૧૨.૬ | Batch Record PDF signed | ભાગ ૫.૨ છેલ્લી row → `qa.releaser` sign | ડોક #૧૬ § ૧૬.૪ |
| ૧૨.૭ | જૂનું Disposition બટન ગાયબ | `/material-lots` → ફક્ત Release/Reject જ | ડોક #૧૬ § ૧૬.૫ |
| ૧૨.૮ | SCAR suspend → **નવો** receipt block | ભાગ ૨.૪/૨.૫ → discrepancy hold `source_not_approved` | ડોક #૧૬ § ૧૬.૬ |
| ૧૨.૯ | Warehouse Location rename/retire | ભાગ ૨.૭ | ડોક #૧૬ § ૧૬.૭ |

---

## Quick Reference — બધા Test Cases એક નજરમાં

| # | Module | મુખ્ય Page | Login | Signed? |
|---|---|---|---|---|
| ૧૨.૧ | Batch Execution | `/recipe-master`, `/batch-execution` | process.engineer, qa.releaser, supervisor1 | હા |
| ૧૨.૨ | Inventory | `/inventory`, `/supplier-cases` | admin, operator1, qa.releaser | ના (reservation) |
| ૧૨.૩ | Security | (કોઈપણ data API) | (login નહીં) | — |
| ૧૨.૪ | RBAC | `/product-master` વગેરે | calibration.tech | — |
| ૧૨.૫ | CAPA | `/capa/{id}` | admin, qa.releaser, supervisor1 | હા |
| ૧૨.૬ | Batch Record | `/batch-execution` | qa.releaser | હા |
| ૧૨.૭ | Material Lot | `/material-lots` | operator1, qa.releaser | હા |
| ૧૨.૮ | SCAR/Receipt | `/supplier-cases`, `/material-receipts` | admin, operator1 | હા |
| ૧૨.૯ | Warehouse | `/inventory` | supervisor1, admin | ના |
