# ૧૯. Complete eBMR Journey — Supplier થી Market Release સુધી (Gujarati)

> **આ ડોક્યુમેન્ટ શેના માટે:** ધારો કે એક **નવી pharma/device company** eBMR/eDHR સિસ્ટમ પર શરૂઆત
> કરે છે — તેને **પહેલો batch market માં release કરવા** માટે, ક્રમમાં, કયા-કયા module માંથી પસાર
> થવું પડે, દરેક step પર કોણ શું કરે, **અને દરેક form ના દરેક field માં શું ભરવું** — તે **બધું એક જ
> જગ્યાએ, ક્રમબદ્ધ, સંપૂર્ણ field-by-field data સાથે** આપેલ છે.
>
> આ doc #૦૧-#૧૮ ના **જ same verified dataset** (કાલ્પનિક કંપની **"Meridian Therapeutics Inc."**,
> product **"MeridiJect™ Prefilled Syringe 40mg"**) વાપરે છે, અને doc #૧૭/#૧૮ ના જ verified field
> tables ને એક સળંગ story માં ગોઠવેલ છે — બધા field names/labels **current code વાંચીને ચકાસેલ છે**.
>
> **Login:** બધા users માટે password: `ChangeMe123!`
> **Table Legend:** UI Label = browser form માં દેખાતું નામ | Backend field = API ને જતું ચોક્કસ
> નામ (reference માત્ર, ટાઈપ કરવાની જરૂર નથી) | જરૂરી? = ફરજિયાત ("હા") કે વૈકલ્પિક ("ના")

---

## ૦. Master Dataset (આખા Document માં આ જ Data વપરાશે)

| Entity | Value |
|---|---|
| Organization | Demo Manufacturing Co. (role-play: "Meridian Therapeutics Inc.") |
| Site | `SITE1` |
| Supplier | `SUP-MERIDIAN-EXC` — Excipients Corp Ltd. |
| Material | `MAT-EXCIPIENT-01` — Sodium Chloride USP, UOM `kg` |
| Material Lot | `LOT-2601-01` |
| Equipment | `FILLER-01` (Area `AREA-GRADE-C`) |
| Product | `MJ-PFS-40MG` — MeridiJect™ Prefilled Syringe 40mg (business id `MERIDIJECT-PFS`) |
| Recipe | `RCP-MJ-PFS-V1` |
| Batch | `MJ-PFS-B-2601` |
| Manufacturing Profile | `injectable_ddcp` |
| Deviation | `DEV-2601-01` |
| CAPA | `CAPA-2601-01` |
| OOS | `OOS-2601-01` |
| Complaint | `CMP-2601-01` |

---

## ૧. સંપૂર્ણ Journey — એક નજરમાં

```
PHASE 0   Company/Site/Users Setup                              (admin)
   │
PHASE 1   Supplier Onboarding + Qualification                    (process.engineer → qa.releaser)
   │
PHASE 2   Material Master + Receiving + QC Release                (process.engineer, operator1 → qa.releaser)
   │
PHASE 3   Equipment Setup (Create/Qualify/Calibrate)               (equipment.admin, calibration.tech)
   │
PHASE 4   Product Master (Draft → Release)                        (process.engineer → qa.releaser)
   │
PHASE 5   Recipe Master (Draft → BOM/Steps → Release)              (process.engineer → qa.releaser)
   │
PHASE 6   Batch Create → Issue → Execute                          (admin/supervisor1 → operator1)
   │
PHASE 7   In-Process QC Testing                                  (operator1/qc analyst)
   │        ├──(fail)──► PHASE 8  OOS/OOT Investigation           (qa.reviewer → qa.releaser)
   │        └──(problem during execution)──► PHASE 9  Deviation   (admin/supervisor1 → qa.releaser)
   │                                              │
   │                                       PHASE 10  CAPA (જો જરૂરી) (qa.reviewer/qa.releaser)
   │
PHASE 11  Production Complete → QA Review → RELEASE DECISION       (operator1 → qa.reviewer → qa.releaser)
   │
   ▼  ═══════════ BATCH હવે MARKET માં RELEASED છે ═══════════
   │
PHASE 12  Post-Market: Complaint (જો આવે તો)                       (admin → qa.releaser → Field Action)
```

**Workflow Notification bell (📥)** દરેક "→" પર જ્યાં **user બદલાય છે** ત્યાં automatically fire
થાય છે — doc #૧૮ માં દરેકનું વધારાનું detail છે. આ doc માં દરેક Phase માં "📥 Notification" line
સાથે ટૂંકમાં નોંધેલ છે.

---

## PHASE 0 — Company, Site, Users Setup

**કોણ:** `admin`

1. Login: `admin` / `ChangeMe123!`.
2. Organization અને Site (`SITE1`) પહેલેથી seed થયેલ છે — ચકાસી લો.
3. જરૂરી users seed થયેલ છે કે નહીં ચકાસો (નીચે ભાગ ૧.૧).

### ૦.૧ આ Journey માં વપરાતા Users

| Username | Role | Journey માં ઉપયોગ |
|---|---|---|
| `admin` | Admin | Setup, Deviation/Complaint trigger, fallback |
| `process.engineer` | Process Engineer | Supplier/Material/Product/Recipe **draft author** |
| `operator1` | Operator | Receiving, Dispensing, Batch execution, QC sample/result entry |
| `supervisor1` | Supervisor | Batch create/issue, Deviation Triage/Contain |
| `qa.reviewer` | QA Reviewer | Deviation Investigation/Impact, QC review, QA Review package, CAPA Plan (RBAC), NCR/SCAR review |
| `qa.releaser` | QA Releaser | **બધા release-class signed decisions** — Material/Product/Recipe/Batch Release, Deviation/CAPA/OOS Disposition+Close, Complaint Close |
| `equipment.admin` | Equipment Administrator | Equipment create/qualify |
| `calibration.tech` | Calibration Technician | Equipment calibration |

**વધુ વિગત માટે:** doc #૦૧ (Company/Sites), doc #૦૨ (Users/Roles).

---

## PHASE 1 — Supplier Onboarding + Qualification

**કોણ Trigger કરે:** `process.engineer` | **કોણ Approve કરે:** `qa.releaser`

### ૧.૧ New Supplier (`/suppliers` → "New supplier")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| Supplier code | `supplier_code` | ના (auto) | `SUP-MERIDIAN-EXC` |
| Role type | `role_type` | હા | `supplier` |
| Country | `country` | ના | `US` |
| Legal name | `legal_name` | હા | `Excipients Corp Ltd.` |
| Site name | `sites[0].site_name` | ના | `Excipients Corp — Plant 1` |
| City | `sites[0].city` | ના | `Newark` |
| Manufacturer flag | `sites[0].manufacturer_flag` | ના | No |

### ૧.૨ Supplier Qualification Request (supplier detail → Qualification tab → "New request")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| Supplier site | `supplier_site_id` | હા (picker) | ઉપર બનાવેલ site |
| Risk class | `risk_class` | ના | `critical` |
| Quality agreement vault id | `quality_agreement_vault_id` | ના | (ખાલી) |
| Effective from | `effective_from` | ના | (ખાલી) |
| Expires at | `expires_at` | ના | (ખાલી) |

→ Qualification state `requested`.

### ૧.૩ 📥 Notification + Approve

`qa.releaser` bell માં "Supplier qualification -- Excipients Corp Ltd." — "Approval needed"
(doc #૧૮ §૫.૧૫). Click → `/suppliers?supplier_id=...`:

| UI Label | Backend field | ઉદાહરણ |
|---|---|---|
| Decision | `decision` | `approved` |
| Justification | `justification` | `"Audit completed, quality agreement signed, risk acceptable"` |

Supplier status `draft`/`under_qualification` → **`approved`**.

**વધુ વિગત માટે:** doc #૦૩ §૩.૧ (Suppliers), doc #૧૮ §૫.૧૫.

---

## PHASE 2 — Material Master + Receiving + QC Release

**કોણ:** `process.engineer` (master/spec) → `operator1` (receive) → `qa.releaser` (release)

### ૨.૧ Material Master (`/materials` → "New material")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| Code | `code` | હા | `MAT-EXCIPIENT-01` |
| Name | `name` | હા | `Sodium Chloride USP` |
| UOM | `uom` | હા | `kg` |
| Default storage condition | `default_storage_condition` | ના | `Room temperature` |
| Manufactured in-house | `is_in_house` | ના | No |

### ૨.૨ Material Specification (`/material-specifications` → "New draft")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| Business ID | `material_spec_business_id` | હા | `SPEC-EXCIPIENT-01` |
| Version number | `version_no` | હા | `1` |
| Material | `material_id` | હા (picker) | `MAT-EXCIPIENT-01` |
| Name | `name` | હા | `Sodium Chloride USP Spec v1` |

Draft submit કરતાં જ spec સીધી `draft` state માં બને (અહીં કોઈ separate "Submit" step નથી) — **📥
`qa.releaser` bell** માં તરત જ "Material Spec [business_id] v[version]" — "Ready for release" દેખાય.
Click → `/material-specifications?material_spec_version_id=...` → **Release** (signed, independent
of author).

### ૨.૩ Material Receipt (`/material-receipts` → "New receipt")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| Receipt number | `receipt_number` | હા | `RCPT-2601-01` |
| Material | `material_id` | હા (picker) | `MAT-EXCIPIENT-01` |
| PO reference | `po_reference` | ના | `PO-2601-001` |
| Carrier/shipment reference | `carrier_reference` | ના | `FEDEX-778812` |
| Supplier | `supplier_id` | ના (picker) | `SUP-MERIDIAN-EXC` |
| Manufacturer | `manufacturer_id` | ના | (ખાલી — supplier જ manufacturer) |
| Supplier's lot number | `supplier_lot` | ના | `EXC-LOT-990` |
| Manufacturer's lot number | `manufacturer_lot` | ના | (ખાલી) |
| Received quantity (gross) | `received_gross_quantity` | હા | `100.000000` |
| Received quantity (net) | `received_net_quantity` | ના | `98.500000` |
| Accepted quantity | `accepted_quantity` | ના | `98.500000` |
| Manufacture date | `manufacture_date` | ના | `2026-08-01` |
| Expiry date | `expiry_date` | ના | `2028-08-01` |
| Retest date | `retest_date` | ના | `2027-08-01` |
| Shipment condition | `shipment_condition_status` | ના | `intact` |
| CoA document hash | `coa_document_hash` | ના | (ખાલી) |

### ૨.૪ Examine Receipt (receipt detail → "Examine")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| Identity confirmed | `identity_confirmed` | હા | Yes |
| Labeling correct | `labeling_ok` | હા | Yes |
| Damage observed | `damage_observed` | હા | No |
| Seal broken | `seal_broken` | હા | No |
| Contamination observed | `contamination_observed` | હા | No |
| Container count | `container_count` | ના | `4` |
| Internal lot number | `internal_lot` | હા | `LOT-2601-01` |

→ Clean examine + supplier `approved` → Material Lot `LOT-2601-01` બને, status `quarantine`.

### ૨.૫ Warehouse Location + Put-away (`/inventory` → UI button is named **"Transfer"**, doc's "Put-away" = the first Transfer for a container)

Lot `LOT-2601-01` is still `quarantine` at this point (release decision comes only in §૨.૬) — the
destination location's zone must be `quarantine`, નહીં તો backend zone-compatibility check
(`InvalidTransitionError`) fail થાય. `released` zone-type location એ પછીથી, QA release (§૨.૬) પછી
material ને move કરવા માટે વપરાય.

| Warehouse Location | Backend field | ઉદાહરણ |
|---|---|---|
| Warehouse code | `warehouse_code` | `WH-01` |
| Location code | `location_code` | `LOC-QRN-01` |
| Zone type | `zone_type` | `quarantine` |

Examine (§૨.૪) માં `container_count = 4` આપ્યું હતું, એટલે lot ને 4 `MaterialContainer` rows મળે
(`LOT-2601-01-C001`…`C004`, દરેક `98.500000 ÷ 4 = 24.625000`). Transfer form પર **Container** picker
mandatory છે (dropdown, lot ના containers માંથી — અહીં 4 options દેખાશે) અને પહેલી location-assignment
ની quantity એ **પસંદ કરેલા container ની આખી quantity** બરાબર જ હોવી જોઈએ (backend enforce કરે છે) — એટલે
`98.500000` ને એક જ Transfer માં move ના કરાય; **4 અલગ Transfer** કરવા પડે, દરેક container માટે એક:

| Put-away (Transfer) | Backend field | ઉદાહરણ (container ૧) |
|---|---|---|
| Material lot | `material_lot_id` | `LOT-2601-01` |
| Container | `container_id` | `LOT-2601-01-C001` |
| From location | `from_location_id` | (ખાલી — પહેલું put-away) |
| To location | `to_location_id` | `LOC-QRN-01` |
| Quantity | `quantity` | `24.625000` |

→ Container ૨, ૩, ૪ માટે એ જ રીતે repeat કરો (દરેક વખતે `24.625000`, `to_location_id` એ જ).

### ૨.૬ 📥 Notification + QC Sample/Test (lot → `qc_disposition_pending`)

**Note:** Receipt બનાવવાથી, Examine કરવાથી કે Put-away/Transfer કરવાથી `qa.releaser` bell માં કંઈ નથી
આવતું — એ notification ફક્ત lot state `qc_disposition_pending` થાય ત્યારે જ ટ્રિગર થાય છે (backend rule:
`services/gxp-api/app/modules/notifications/registry.py`, lot spec's `qc_disposition_pending` key), જે
નીચે PHASE ૭ ના QC sample+test પૂરા થયા પછી જ આવે. અહીં સુધી lot `quarantine`/`sampling`/`testing` state
માં હોય ત્યાં સુધી કોઈ bell notification expected નથી — એ bug નથી.

QC sampling + testing (PHASE ૭ ના §૭.૧/૭.૨ પ્રમાણે, spec `MAT-EXCIPIENT-01` સામે) પૂર્ણ થતાં lot
state `qc_disposition_pending` થાય → `qa.releaser` bell માં "Lot LOT-2601-01" — "Ready for release
decision" (doc #૧૮ §૫.૧૪). Click → `/material-lots?q=LOT-2601-01`:

**Release (QA):** role `QA Releaser`, signed, meaning `Released` — કોઈ વધારાનું field નથી, ફક્ત
signature (Password) confirm.

### ૨.૭ Reservation + Dispensing (batch માટે — PHASE ૬ પહેલાં)

| Reservation | Backend field | ઉદાહરણ |
|---|---|---|
| Batch | `batch_id` | `MJ-PFS-B-2601` |
| Material | `material_id` | `MAT-EXCIPIENT-01` |
| Quantity | `quantity` | `40.000000` |
| UOM | `uom` | `kg` |

| Dispensing Order | Backend field | ઉદાહરણ |
|---|---|---|
| Batch | `batch_id` | `MJ-PFS-B-2601` |
| Material | `material_id` | `MAT-EXCIPIENT-01` |
| Target quantity | `target_qty` | `40.000000` |
| UOM | `target_uom` | `kg` |
| Tolerance low/high | `tolerance_low`/`tolerance_high` | `39.500000` / `40.500000` |

Source select → Reservation ઉપર | Start → Manual reading: Actual weight `40.050000` → Verify
(independent user) → Complete (Dispensed Container બને).

> ⚠️ **આટલેથી અટકશો નહીં — "Record a consumption" પણ જરૂરી:** ઉપરનું Dispensing Complete ફક્ત
> Dispensed Container બનાવે છે; batch execution નું material gate (§૬.૨ ની નોંધ જુઓ) એક અલગ, separate
> action ચેક કરે છે — `/dispensing` → "Material transaction operations" console → **"Record a
> consumption"**:
>
> | Field | ઉદાહરણ |
> |---|---|
> | Batch | `MJ-PFS-B-2601` (એ જ batch, જેના માટે ઉપર dispense કર્યું) |
> | Step ID | ખાલી રાખો (optional — આ ચેક ચોક્કસ step સાથે નહીં, આખા batch સાથે જોડાયેલ છે) |
> | Dispensed container ID | ઉપરના Complete એ બનાવેલ container |
> | Quantity | `40.050000` |
> | Unit of measure | `kg` |
> | Source type | `manual` |
>
> **દરેક નવા batch માટે આ આખું Phase ૨.૭ (Reservation → Dispensing → Record a consumption) ફરીથી
> કરવું પડે** — material consumption ચોક્કસ `batch_id` સાથે જોડાયેલ છે, એક batch નું dispensing/
> consumption બીજા batch માટે ના ચાલે (દા.ત. testing માટે નવો batch `MJ-PFS-B-2603` બનાવ્યો હોય તો
> એના માટે અલગથી Reservation/Dispensing/Consumption કરવું પડે, ભલે material/quantity બિલકુલ સરખા હોય).

**વધુ વિગત માટે:** doc #૦૩ (Materials/Inventory/Dispensing), doc #૧૭ ભાગ ૨, doc #૧૮ §૫.૧૪.

---

## PHASE 3 — Equipment Setup

**કોણ:** `equipment.admin` (create/qualify) → `calibration.tech` (calibrate)

### ૩.૧ New Equipment Asset (`/equipment` → "New asset")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| Equipment code | `equipment_code` | હા | `FILLER-01` |
| Manufacturer | `manufacturer` | ના | `PharmaFill Inc.` |
| Model | `model` | ના | `PF-3000` |
| Serial no. | `serial_no` | ના | `SN-FILLER-0087` |
| Firmware version | `firmware_version` | ના | `2.4.1` |
| Dedicated to single product | `dedicated` | ના | No |
| Area | `area_id` | ના (picker) | `AREA-GRADE-C` |

### ૩.૨ Qualification

| UI Label | ઉદાહરણ |
|---|---|
| Qualification status | `PQ_COMPLETE` |
| Qualified | Yes |
| Effective date | `2026-08-15` |
| Expiry date | `2028-08-15` |
| Reason | `"Initial PQ per protocol PQ-FILLER-01"` |

### ૩.૩ Calibration

| UI Label | ઉદાહરણ |
|---|---|
| Performed date | `2026-08-10` |
| Next due date | `2027-02-10` |
| Result | `pass` |
| Standard reference | `NIST-STD-4471` |
| Calibration type | `internal` |
| Provider | (ખાલી — internal) |

**નોંધ:** Equipment module માટે હાલ Workflow Notification નથી — readiness `/equipment` page પર
manually ચકાસવી.

**વધુ વિગત માટે:** doc #૦૪ (Equipment/Devices), doc #૧૭ ભાગ ૮.

---

## PHASE 4 — Product Master

**કોણ Trigger કરે (Draft):** `process.engineer` | **કોણ Release કરે:** `qa.releaser`

### ૪.૧ New Draft (`/product-master` → "New draft")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| Business ID | `product_business_id` | હા | `MERIDIJECT-PFS` |
| Product code | `product_code` | ના (auto) | `MJ-PFS-40MG` |
| Version no. | `version_no` | હા | `1` |
| Name | `name` | હા | `MeridiJect™ Prefilled Syringe 40mg` |
| Site | `site_id` | હા | `SITE1` |
| Manufacturing profile | `manufacturing_profile_code` | હા | `injectable_ddcp` |
| Sterile process profile | `sterile_profile_id` | Release વખતે DDCP માટે ફરજિયાત | Released aseptic profile |
| Device model code | `device_model_code` | UDI applicable હોય તો ફરજિયાત | `DEV-MODEL-PFS-01` |
| UDI applicable | `udi_applicable` | ના | Yes |
| Product family | `product_family_id` | ના | `PFS-FAMILY` (નવો બનાવી શકાય) |
| Combination product type | `combination_product_type` | ના | `prefilled_syringe` |
| Strength value / UOM | `strength_value`/`strength_uom` | ના | `40` / `mg` |
| Constituents | `constituents[]` | Combination type set હોય તો Release વખતે ફરજિયાત | Drug + Device constituent link |

### ૪.૨ Submit → Release

Draft → Submit (unsigned) → state `under_review` → **📥 `qa.releaser` bell** માં "Product
[business_id] v[version]" — "Ready for release". Click → `/product-master?product_version_id=...`
→ (**author થી અલગ user**) → **Release**, signature (Password), meaning `Released`.

> ⚠️ **SoD:** `process.engineer` પોતે release ના કરી શકે — `SOD_CONFLICT`.

**વધુ વિગત માટે:** doc #૦૬ (Product Master), doc #૧૭ ભાગ ૪.

---

## PHASE 5 — Recipe Master

**કોણ Trigger કરે (Draft):** `process.engineer` | **કોણ Release કરે:** `qa.releaser`

### ૫.૧ New Draft (`/recipe-master`)

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| Recipe code | `recipe_code` | હા | `RCP-MJ-PFS-V1` |
| Product version | `product_version_id` | હા | Released `MJ-PFS-40MG` v1 |
| Batch size value/UOM | `batch_size_value`/`batch_size_uom` | હા | `5000` / `units` |

### ૫.૨ Section + Step + Sub-forms

| Sub-section | UI Label / Backend field | ઉદાહરણ |
|---|---|---|
| **Section** | Section code (`stable_section_code`) | `SEC-1` |
| | Section name (`name`) | `Dispensing` |
| **Step** | Step code (`stable_step_code`) | `STEP-A` |
| | Step type | `weigh` |
| | Instruction text (`instruction_text`) | `"Weigh Sodium Chloride USP per BOM target"` |
| | Required role code | `OPERATOR` |
| | Required qualification code | `DISPENSING_OPERATOR` |
| | Is critical | Yes |
| **Parameter** | Parameter code | `TARGET_WEIGHT` |
| | Data type | `decimal` |
| | Source | `manual_entry` |
| | Target / Min / Max | `40.0` / `39.5` / `40.5` mg |
| | Precision digits | `2` |
| **Material requirement** | Material (spec version) | `MAT-EXCIPIENT-01` (Phase ૨.૨ ની released spec) |
| | Target/Min/Max qty | `40.0` / `39.5` / `40.5` |
| | UOM | `kg` |
| | Substitution allowed | No |
| **Equipment requirement** | Equipment class label | `BALANCE` |
| | Equipment class (picker) | `BALANCE` (controlled master) |
| | Require calibration/qualification/cleaning | Yes/Yes/Yes |
| **Evidence requirement** | Evidence type | `photo` |
| | Required count | `1` |
| **QC requirement** | QC test specification | `QC-SPEC-ASSAY-01` (Phase ૭.૧ ની released spec — dropdown released/**in_process** specs બતાવે, draft નહીં) |

> ⚠️ **અગત્યનું:** આ QC requirement વાળું step ક્યારેય "Step: Complete" (§૬.૨) નહીં થાય જ્યાં સુધી એ ચોક્કસ
> step માટે Phase ૭.૨ નું Sample → Order → Result (`source_type = batch_step`, પાસ result) પૂરું ના થાય —
> batch step નું પોતાનું "Record results"/evidence link (§૬.૨) આ QC gate ને સંતોષતું નથી, એ બે તદ્દન અલગ
> systems છે (batch_execution vs qc module).

### ૫.૩ Submit → Release

Validate/Simulate → Submit → state `under_review` → **📥 `qa.releaser` bell** માં "Recipe
[recipe_code] v[version]" — "Ready for release". Click → `/recipe-master?recipe_version_id=...` →
(અલગ user) → **Release**, signature, meaning `Released`.

**વધુ વિગત માટે:** doc #૦૭ (Recipe Master), doc #૧૭ ભાગ ૩.

---

## PHASE 6 — Batch Create → Issue → Execute

**કોણ:** `admin`/`supervisor1` (create/issue) → `operator1` (execute)

### ૬.૧ Create Batch (`/batch-execution` → "New batch")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| Batch number | `batch_number` | હા | `MJ-PFS-B-2601` |
| Product | (picker) | હા | `MERIDIJECT-PFS` |
| Product version | `product_version_id` | હા (Released) | v1 |
| Recipe | (picker) | હા | `RCP-MJ-PFS-V1` |
| Recipe version | `recipe_version_id` | હા (Released) | v1 |
| Target quantity | `target_qty` | હા | `50000` |
| UOM | `target_uom` | હા | `units` |
| Production order ref | `production_order_ref` | ના | `PO-PROD-2601` |

### ૬.૨ Lifecycle Actions

| Action | Endpoint | Signed? | ઉદાહરણ Fields |
|---|---|---|---|
| Issue | `/{id}/issue` | ના | — |
| Start | `/{id}/start` | ના | — |
| Step: Start | `/steps/{id}/start` | ના | — (role/qualification/equipment gate ચકાસાય) |
| Step: Record results | `/steps/{id}/results` | ના | Actual weight `40.05` mg |
| Step: Complete | `/steps/{id}/complete` | **હા** (`Performed`) | — (નીચેની નોંધ જુઓ) |
| Hold/Resume batch | `/{id}/hold`,`/resume` | ના | Reason: `"Line stopped for inspection"` |
| Production complete | `/{id}/production-complete` | ના | — (બધા steps complete હોય તો જ) |

> ⚠️ **Step: Complete આ error આપે તો:** `VALIDATION_FAILED: Required in-process QC test(s) have not
> reached a passing result` — એનો અર્થ એ step ને §૫.૨ માં QC requirement attach છે, અને એ ચોક્કસ step માટે
> PHASE ૭ (§૭.૨) નું Sample → Order → Result (`source_type=batch_step`) નો `outcome: pass` result હજુ
> નથી. Batch step નું પોતાનું Record results/Link evidence (ઉપર) આ ચેક જુદો છે — સંતોષતું નથી. **નોંધ:**
> આ ચેક ફક્ત result ના `outcome` ને જુએ છે — test order નું **Second-person review** (§૭.૨ નું છેલ્લું
> પગલું) *જરૂરી નથી* Step: Complete માટે, એ ફક્ત batch ના final release (Phase ૧૧) માટે જરૂરી છે (review
> ના થાય ત્યાં સુધી `/qa-review` કે `/release` "1 blocking test order(s) not yet reviewed" બતાવશે — એ
> Step: Complete ને block નથી કરતું). **ક્રમ:** Step: Start → (જરૂર હોય તો) Phase ૭.૨ ચલાવો → Step:
> Record results / Link evidence → Step: Complete.
>
> ⚠️ **Step: Complete આ error આપે તો:** `VALIDATION_FAILED: Required material has not been consumed
> for this batch` — એનો અર્થ §૫.૨ ના Material requirement માટે આ **આખા batch** પર (ચોક્કસ step પર નહીં)
> કોઈ material consumption રેકોર્ડ નથી. Phase ૨.૭ (Reservation → Dispensing → **Record a consumption**,
> ત્રણેય જરૂરી) આ batch માટે પૂરું કરો — યાદ રાખો, દરેક નવા batch માટે આ ફરીથી કરવું પડે, ભલે material
> પહેલાં કોઈ બીજા batch માટે dispense કર્યું હોય.

**Line Clearance** (doc #૦૫), **DDCP Handoff/Fill/Assembly/Verify** (doc #૦૯), **Sterilization/EM/
Aseptic** (doc #૧૩) — `injectable_ddcp` profile માટે જરૂરી પડે તો આ steps પણ આવે.

**વધુ વિગત માટે:** doc #૦૮ (Batch/Batch Execution), doc #૧૭ ભાગ ૫.

---

## PHASE 7 — In-Process QC Testing

**કોણ:** `operator1`/QC analyst (sample/result) → `qa.reviewer` (second-person review)

### ૭.૦ Acceptance Rule (`/rules` → New rule draft → Release, **Test Specification પહેલાં જરૂરી**)

એક QC test નું result ક્યારેય `pass` outcome સુધી પહોંચતું જ નથી (કાયમ `pending` રહે છે) જ્યાં સુધી એની
test definition સાથે એક **released** Acceptance rule link ના હોય — Review કે Correction એ પછીથી ઠીક નથી
કરી શકતા (result append-only છે, AG-08). એટલે spec બનાવતાં પહેલાં rule બનાવવો પડે:

| UI Label | ઉદાહરણ |
|---|---|
| Rule ID | `ASSAY-ACCEPT-01` |
| Rule type | `CC-3 - Tolerance evaluation` |
| Semantic version | `1.0.0` |
| Expression | AND group: (`value` ≥ `39.5`) અને (`value` ≤ `40.5`) |
| Input variables | `value` — decimal |
| Output | `eligible` — boolean |
| Calculation class | `CC-3 - Tolerance evaluation` |

Release: `qa.releaser`, independent signer.

### ૭.૧ Test Specification (`/qc` → Draft → Release, **Phase ૫ પહેલાં** કરવું જરૂરી)

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| Spec code | `spec_code` | હા | `QC-SPEC-ASSAY-01` |
| Scope type | `scope_type` | હા | `in_process` |
| Scope version ID | `scope_version_id` | હા (picker) | `RCP-MJ-PFS-V1` (STEP-A) |
| Test code | (per test definition) | હા | `ASSAY` |
| Test name | | હા | `Sodium Chloride Assay` |
| Result data type | | હા | `numeric` |
| UOM | | ના | `mg` |
| **Acceptance rule** | `acceptance_rule_business_id` | **હા, practically** (§૭.૦ જુઓ — વગર result કાયમ `pending` રહેશે) | `ASSAY-ACCEPT-01` |
| Trend rule | `trend_rule_business_id` | ના | (ખાલી) |
| Required | | | Yes |
| Release blocking | | | Yes |

Release: `qa.releaser`, independent.

> ⚠️ **Spec code re-use = નવું version:** `spec_code` એ જ રાખીને ફરી "New test specification" કરો તો
> `version_no` auto-increment થાય (દા.ત. v1 → v2) — અલગ "new version" button નથી. પણ v1 already released
> હોય તો એના test definitions (અને એ v1 ને refer કરતું recipe step નું QC requirement) કાયમ માટે frozen
> રહે છે — v2 બનાવવાથી જૂનું batch/recipe એની તરફ આપોઆપ shift નથી થતું; નવો recipe version release
> કરીને નવો batch issue કરવો પડે (§૫.૨/§૬.૧).

### ૭.૨ Sample → Order → Result

| પગલું | UI Field | ઉદાહરણ |
|---|---|---|
| Create sample | Sample number | `SMP-2601-01` |
| | Sample type | `in_process` |
| | Source type | `batch_step` (**`batch` નહીં** — batch step ના completion gate ને આ ચોક્કસ step સાથે જોડાયેલ sample જ સંતોષે છે) |
| | Source record | Batch `MJ-PFS-B-2601` → Step `STEP-A` (બે dependent dropdowns) |
| | Quantity/UOM | `5` / `g` |
| Add test order | Test definition | `ASSAY` (released spec માંથી — સાચું spec version પસંદ કરો, દા.ત. v2) |
| | Assigned analyst | `operator1` |
| Record raw data | Method version | `HPLC-v2` |
| | Instrument ref | `HPLC-04` |
| | Sample amount | `1.0 g` |
| Record result | Result type | `numeric` |
| | Value | `40.05` (§૭.૦ ના rule range 39.5-40.5 ની અંદર) |
| | UOM | `mg` |
| **Second-person review** | (કોઈ field નહીં) | `qa.reviewer` — signed, independent of analyst (`operator1` પોતે review ના કરી શકે) |

**નોંધ — review vs. step completion:** `outcome: pass` result બન્યા પછી તરત જ batch step "Complete"
(§૬.૨) થઈ શકે છે — Second-person review એ Step: Complete માટે જરૂરી **નથી**. Review ફક્ત batch ના final
release (Phase ૧૧) માટે જરૂરી છે; review ના થાય ત્યાં સુધી `qa-review`/`release` readiness view "1
blocking test order(s) not yet reviewed" બતાવશે — batch આગળ execute કરવાનું ચાલુ રાખી શકાય, review
ગમે ત્યારે (Production Complete પહેલાં) કરી શકાય.

**જો result spec ની અંદર (pass):** → batch step "Complete" (§૬.૨) હવે થઈ શકે, પછી PHASE ૧૧ તરફ આગળ. **જો બહાર (fail/OOS) અથવા trend ટ્રિગર
(OOT):** → PHASE ૮.

**વધુ વિગત માટે:** doc #૧૭ ભાગ ૯, doc #૧૮ §૫.૧૨/§૫.૧૩.

---

## PHASE 8 — OOS/OOT Investigation (જો Test Fail થાય)

**કોણ:** `operator1`/`qa.reviewer` (investigate) → **બીજો independent** qualified user (extended
investigation sign) → `qa.releaser` (disposition + close)

### ૮.૧ Open OOS (`/quality/oos` → "Open from result")

| UI Label | Backend field | ઉદાહરણ |
|---|---|---|
| Source QC result | `source_result_id` | Phase ૭.૨ નો result (spec બહારની value, દા.ત. `99.000000`) |
| OOS number | `oos_number` | `OOS-2601-01` |

> ⚠️ **"Source QC result" dropdown બતાવે "No QC result for this batch"?** આ dropdown batch-level
> (`source_type='batch'`) અને step-level in-process (`source_type='batch_step'`) બંને sample પરથી
> આવેલ result શોધે છે (`GET /qc/v1/results?batch_id=...`, `qc/router.py::list_results_for_batch`) —
> એટલે Phase ૭ નું કોઈપણ QC testing (batch-level હોય કે step-level) આ list માં દેખાવું જોઈએ. જો ખાલી
> દેખાય તો ખરેખર batch માટે **કોઈ QC result recorded જ નથી** (batch/batch_step બંને source પરથી) —
> પહેલા Phase ૭ પૂરું કરો, dropdown ની સમસ્યા નથી.

### ૮.૨ Investigation Pipeline

| પગલું | UI Field | ઉદાહરણ |
|---|---|---|
| Lab investigation | Activity type | `checklist_review` |
| | Response | `"No obvious analyst/instrument error found"` |
| Classify lab cause | Assignable cause found? | No |
| Extended investigation (**independent signer**) | (signature ceremony જ) | — |
| Retest plan | Justification | `"Confirm assay via retest"` |
| | Number of retests | `2` |
| | Method reference | `HPLC-1` |
| Resample plan | Scientific rationale | `"Rule out sampling error"` |
| Impact assessment | Impact text | `"No confirmed impact to other batches; hold pending disposition"` |
| | Hold status | `hold` |

→ state `final_disposition`.

### ૮.૩ 📥 Notification + Disposition + Close

`qa.releaser` bell — "Disposition needed" (doc #૧૮ §૫.૧૨):

| UI Label | ઉદાહરણ |
|---|---|
| Final classification | `laboratory_error` |

→ state `qa_approval` → **બીજા** `qa.releaser` ના bell માં "Ready for closure" (SoD — dispositioning
user પોતે close ના કરી શકે) → Close (signature).

**Retest pass થાય તો** batch આગળ વધે (Phase ૭ પર પાછું); fail રહે તો Phase ૯/૧૦ તરફ.

**વધુ વિગત માટે:** doc #૧૭ ભાગ ૯.૩, doc #૧૮ §૫.૧૨/§૫.૧૩.

---

## PHASE 9 — Deviation (જો Batch દરમિયાન કંઈ Unexpected થાય)

**કોણ Trigger કરે:** `admin`/`supervisor1` | **કોણ Disposition/Close કરે:** `qa.releaser`

### ૯.૧ Raise Deviation (`/deviations` → "New")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| Deviation number | `deviation_number` | હા | `DEV-2601-01` |
| Type | `deviation_type` | હા | `process` |
| Severity | `severity` | હા | `major` |
| Source type | `source_type` | હા | `batch` |
| Source record | `source_id` | હા | `MJ-PFS-B-2601` |
| Planned deviation | `planned` | ના | No |

### ૯.૨ Pipeline

| પગલું | UI Field | ઉદાહરણ | Role |
|---|---|---|---|
| Triage | Severity | `major` | `supervisor1` |
| | Investigation priority | `high` | |
| | Product impact | `"Under investigation"` | |
| Contain | Immediate correction | `"Line stopped"` | `supervisor1` |
| | Containment | `"Batch quarantined pending review"` | |
| | Reason | `"Precautionary hold"` | |
| Investigation | Investigator | `qa.reviewer` | `qa.reviewer` |
| | Due date | `+5 days` | |
| | Root cause method | `5-why` | |
| | Conclusion | `"Operator technique variance on STEP-A"` | |
| Impact | Quality/Patient/Product/Validation/Data-integrity/Regulatory impact | બધા `none` | `qa.reviewer` |
| **Disposition** | Disposition code | `CONTINUE` | **`qa.releaser`** — signed |
| | Rationale | `"No quality impact found upon investigation"` | |
| | CAPA required | Yes | |
| | CAPA rationale | `"Recurring pattern across 3 batches — systemic fix needed"` | |
| **Close** | Conclusion | `"Investigated; disposition CONTINUE; CAPA-2601-01 opened"` | **`qa.releaser`** — signed |

### ૯.૩ 📥 Notification

IMPACT_ASSESSMENT state પર `qa.releaser` bell — "Disposition needed"; DISPOSITION state પર ફરી
"Ready for QA closure" (doc #૧૮ §૫.૨).

**વધુ વિગત માટે:** doc #૧૧ (Deviation), doc #૧૭ ભાગ ૭, doc #૧૮ §૫.૨.

---

## PHASE 10 — CAPA (Root-Cause Correction)

**કોણ Trigger કરે:** `admin` | **કોણ Plan કરે:** `qa.reviewer`/`qa.releaser` | **કોણ Close કરે:**
`qa.releaser`

> ⚠️ CAPA **auto-create નથી** થતું — Phase ૯ એ "CAPA required = Yes" mark કર્યું તો પણ, `/capa` પર
> જઈને **manually**, `DEV-2601-01` ને source તરીકે select કરીને CAPA બનાવવો પડે.

### ૧૦.૧ Raise CAPA (`/capa` → "New")

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| CAPA number | `capa_number` | હા | `CAPA-2601-01` |
| Risk class | `risk_class` | હા | `medium` |
| Target date | `target_date` | હા | `+60 days` |
| Problem statement | `problem_statement` | હા | `"Recurring weigh variance on STEP-A across 3 batches"` |
| Source type | `source_type` | હા | `deviation` |
| Source record | `source_id` | હા | `DEV-2601-01` |
| Investigation reference | `root_cause_ref.investigation_ref` | હા | Deviation ના investigation ref |

→ state `OPEN`.

### ૧૦.૨ 📥 Notification + Signed Actions

`qa.reviewer`/`qa.releaser` bell — "CAPA plan needed" (doc #૧૮ §૫.૩):

| Action | UI Field | ઉદાહરણ |
|---|---|---|
| **Plan** | Corrective action | `"Retrain operators on balance technique"` |
| | Preventive action | `"Add balance calibration check to shift-start checklist"` |
| | Effectiveness plan | `"Monitor next 5 batches for weigh variance"` |
| **Extend** (જો જરૂરી) | New target date / Reason / Risk review | — |
| **Record effectiveness** | Effectiveness check / Result / Evidence | `"Weigh variance <0.5% over 5 batches"` / `pass` / `"Batches MJ-PFS-B-2602..2606 weigh logs reviewed"` |
| **Close** | Conclusion | `"Effectiveness confirmed; CAPA closed"` |

→ state `EFFECTIVENESS_REVIEW` → `qa.releaser` bell "Ready for QA closure" → Close.

> ⚠️ `qa.reviewer` પાસે Plan/Extend ની RBAC permission છે પણ **signature role check `QA Releaser`
> માંગે છે** — ફક્ત `qa.releaser` જ પૂરું sign કરી શકે.

**વધુ વિગત માટે:** doc #૧૦ (CAPA), doc #૧૭ ભાગ ૬, doc #૧૮ §૫.૩.

---

## PHASE 11 — Production Complete → QA Review → RELEASE DECISION

આ **સૌથી અગત્યનો Phase — "Batch ને market માં release કરવા શું જોઈએ"** તેનો સીધો જવાબ.

**કોણ:** `operator1` (production complete) → `qa.reviewer` (QA review) → `qa.releaser` (release)

### ૧૧.૧ Production Complete

બધા batch steps complete (Phase ૬), કોઈ open Deviation/OOS/OOT ના હોય (Phase ૮/૯ બંધ) →
`operator1`: **Production Complete** (signature, કોઈ extra field નહીં).

### ૧૧.૨ QA Review Package (`/qa-review`)

| UI Label | Backend field | ઉદાહરણ |
|---|---|---|
| Batch | (picker) | `MJ-PFS-B-2601` |

Create → Reindex (જરૂર પડે) → **Complete review** — signature ceremony (કોઈ extra field નહીં),
role `qa.reviewer`.

### ૧૧.૩ Release Evaluate + Decision (`/release`)

| Action | UI Field | ઉદાહરણ | Role | Signed? |
|---|---|---|---|---|
| Evaluate | Scope type | `batch` | `qa.reviewer`/`qa.releaser` | ના |
| | Batch | `MJ-PFS-B-2601` | | |
| **Release** | Reason | `"All QA checks passed"` (વૈકલ્પિક) | **`qa.releaser`** (Evaluate કરનાર થી independent) | **હા** |
| Hold | Reason (ફરજિયાત) | | `qa.releaser` | હા |
| Reject | Reason (ફરજિયાત) | | `qa.releaser` | હા |

Evaluate ચકાસે: Manufacturing completeness, QA Review, QC, Materials, Equipment, Environment,
CAPA, Yield/Reconciliation (blocking), Packaging (warning only) — **બધું ✅ હોય તો જ scope
`eligible`**.

### ૧૧.૪ 📥 Notification

`qa.releaser` bell — "Batch MJ-PFS-B-2601" — "Ready for release decision" (doc #૧૮ §૫.૧). Click →
`/release?scope_id=...` → Release button → Password confirm.

**➡️ આ પછી batch officially "Released" — market માં જવા માટે તૈયાર.**

**વધુ વિગત માટે:** doc #૧૨ (Batch Review/Release), doc #૧૭ ભાગ ૧૦/૧૧, doc #૧૮ §૫.૧.

---

## PHASE 12 — Post-Market: Complaint Handling

**કોણ Trigger કરે:** `admin` | **કોણ Investigate/Close કરે:** `qa.releaser`

### ૧૨.૧ New Complaint (`/complaints`)

| UI Label | Backend field | જરૂરી? | ઉદાહરણ |
|---|---|---|---|
| Complaint number | `complaint_number` | હા | `CMP-2601-01` |
| Received at | `received_at` | હા | `2026-10-05` |
| Source channel | `source_channel` | હા | `written` |
| Nature code | `nature_code` | હા | `DEVICE_MALFUNCTION` |
| Description | `description` | હા | `"Patient reported syringe plunger stuck during injection"` |
| Lot/batch/serial reference | `lot_batch_serial_refs` | ના | `MJ-PFS-B-2601` |
| Complainant contact | `complainant_info` | ના | `"Jane Doe, Pharmacy X, jane@pharmacy-x.example"` |
| Constituent classification | `constituent_classification` | ના | `combination` |

### ૧૨.૨ Pipeline

| પગલું | UI Field | ઉદાહરણ |
|---|---|---|
| Triage | Severity | `serious` |
| Investigation decision | Investigation required? | Yes |
| Investigate | Findings | `"Device inspected, plunger friction slightly high; batch review shows no process deviation"` |
| | Conclusion | `"Isolated device tolerance issue, not batch-wide"` |
| **Reportability** | Applicable regimes | `FDA_MDR` |
| | Rationale | `"Device malfunction meets MDR reportability criteria"` |
| Response | Direction | `outbound` |
| | Type | `response` |
| | Recipient | `"Jane Doe"` |
| | Message | `"Thank you for reporting; investigation complete, corrective action in progress"` |
| **Close** | Conclusion | `"Investigation complete; response sent; no batch-wide impact confirmed"` |

### ૧૨.૩ 📥 Notification

state `REPORTABILITY_ASSESSMENT` પર `qa.releaser` bell — "Reportability assessment needed";
`RESPONSE` state પર ફરી "Ready for QA closure" (doc #૧૮ §૫.૬). જો ગંભીર હોય → **Field Action**
(recall/correction, doc #૧૮ §૫.૯) પણ ખોલી શકાય.

**વધુ વિગત માટે:** doc #૧૪ (Platform), doc #૧૮ §૫.૬/§૫.૯.

---

## ૨. Master Checklist — "Batch ને Market માં Release કરવા શું જોઈએ"

| # | Requirement | ક્યાં ચકાસાય |
|---|---|---|
| ૧ | Supplier qualified/approved | Phase ૧ |
| ૨ | Material lot received, tested, QC-released | Phase ૨, ૭ |
| ૩ | Equipment qualified + calibration valid | Phase ૩ |
| ૪ | Product Master version **released** (author ≠ releaser) | Phase ૪ |
| ૫ | Recipe Master version **released** (author ≠ releaser) | Phase ૫ |
| ૬ | Batch issued, બધા steps complete, production complete | Phase ૬ |
| ૭ | બધા in-process QC results pass (OOS/OOT બંધ) | Phase ૭, ૮ |
| ૮ | કોઈ open Deviation નથી (બધા disposition + closed) | Phase ૯ |
| ૯ | જરૂરી CAPA closed (જો કોઈ deviation/OOS એ requested કર્યું હોય) | Phase ૧૦ |
| ૧૦ | QA Review package complete | Phase ૧૧ |
| ૧૧ | Release Scope evaluate = `eligible` (બધા blockers clear) | Phase ૧૧ |
| ૧૨ | Release decision — signed, **independent** QA Releaser | Phase ૧૧ |

**કોઈ પણ એક item ❌ હોય તો `/release` નું Evaluate step `blocked` બતાવશે — release button નહીં
મળે.**

---

## ૩. બધા Reference Docs (આ Journey ના દરેક Phase માટે વિગતવાર)

| Phase | Detailed Doc |
|---|---|
| ૦ | [Company/Sites](01_Company_Sites_Gujarati.md), [Users/Roles](02_Users_Roles_Access_Gujarati.md) |
| ૧, ૨ | [Materials/Suppliers/Inventory](03_Materials_Inventory_Gujarati.md) |
| ૩ | [Equipment/Devices](04_Equipment_Devices_Gujarati.md) |
| ૪ | [Product Master](06_Product_Master_Gujarati.md) |
| ૫ | [Recipe Master](07_Recipe_Master_Gujarati.md) |
| ૬ | [Batch/Batch Execution](08_Batch_Batch_Execution_Gujarati.md), [DDCP](09_DDCP_Gujarati.md), [Sterilization/Aseptic](13_Sterilization_Aseptic_Gujarati.md), [Line Clearance](05_Line_Clearance_Gujarati.md) |
| ૮ | [Workflow Notifications §૫.૧૨/૫.૧૩](18_Workflow_Notifications_Testing_Gujarati.md) |
| ૯ | [Deviation](11_Deviation_Gujarati.md) |
| ૧૦ | [CAPA](10_CAPA_Gujarati.md) |
| ૧૧ | [Batch Review/Release](12_Batch_Review_Release_Gujarati.md) |
| ૧૨ | [Platform/Audit/Evidence/Vault](14_Platform_Audit_Evidence_Vault_Gujarati.md) |
| બધા 📥 Notification points | [Workflow Notifications Testing](18_Workflow_Notifications_Testing_Gujarati.md) |
| Field-by-field data (source, cross-check) | [Full Platform Field Guide](17_Full_Platform_Field_Guide_Gujarati.md) |
