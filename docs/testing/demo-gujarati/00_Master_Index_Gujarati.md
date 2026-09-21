# ૦. eBMR/eDHR Platform — Client Demo Master Index (Gujarati)

> **ડેમો સ્ટોરી:** આ આખો ડોક્યુમેન્ટ સેટ એક કાલ્પનિક કંપની **"Meridian Therapeutics Inc."** ("MeridiJect™"
> નામની Pre-Filled Syringe (PFS) combination-product બનાવતી) ના role-play પર આધારિત છે — real seeded
> system (Organization "Demo Manufacturing Co.", Site `SITE1`) પર જ. બધા routes, permission codes,
> roles અને gaps **current code વાંચીને (2026-09-18) ચકાસેલ છે** — કંઈ પણ ધારેલું (guessed) નથી.
>
> દરેક ડોક્યુમેન્ટમાં: શું છે → routes/APIs → **role/permission મેટ્રિક્સ** → filled example ડેટા સાથે
> વોકથ્રુ → honestly-flagged known gaps/bugs (જેથી ડેમો live fail ના થાય).

---

## ૧. ડોક્યુમેન્ટ યાદી (ભલામણ કરેલ ડેમો ક્રમમાં)

| # | ડોક્યુમેન્ટ | મુખ્ય Module(s) |
|---|---|---|
| ૦૧ | [Company અને Sites](01_Company_Sites_Gujarati.md) | Organization, Sites |
| ૦૨ | [Users, Roles, Access Review](02_Users_Roles_Access_Gujarati.md) | IAM, RBAC, 36 roles |
| ૦૩ | [Materials, Inventory, Dispensing](03_Materials_Inventory_Gujarati.md) | Suppliers, Materials, Specs, Lots, Inventory, Dispensing |
| ૦૪ | [Equipment અને Devices](04_Equipment_Devices_Gujarati.md) | Equipment master, Calibration, Maintenance, Devices |
| ૦૫ | [Line Clearance](05_Line_Clearance_Gujarati.md) | Area clearance |
| ૦૬ | [Product Master](06_Product_Master_Gujarati.md) ⭐ | Product/Constituent/Regulatory Profile |
| ૦૭ | [Recipe Master](07_Recipe_Master_Gujarati.md) ⭐ | Master Recipe / MMR / Rules |
| ૦૮ | [Batch અને Batch Execution](08_Batch_Batch_Execution_Gujarati.md) ⭐ | eBMR execution, Genealogy, Yield, Packaging, Field Actions |
| ૦૯ | [DDCP](09_DDCP_Gujarati.md) | Device/Drug Combination Product execution |
| ૧૦ | [CAPA](10_CAPA_Gujarati.md) | Corrective/Preventive Action |
| ૧૧ | [Deviation](11_Deviation_Gujarati.md) | Deviation management |
| ૧૨ | [Batch Review અને Release](12_Batch_Review_Release_Gujarati.md) | QA Review, Release |
| ૧૩ | [Sterilization, Aseptic, EM, Cleaning](13_Sterilization_Aseptic_Gujarati.md) | Sterile processing |
| ૧૪ | [Platform, Audit, Evidence, Vault](14_Platform_Audit_Evidence_Vault_Gujarati.md) | Dashboard, Audit trail, Evidence, Documents, Training |

⭐ = user ની મુખ્ય required functionality (Product Master, Recipe Master, Batch Manufacture)

---

## ૨. Demo Login Credentials (બધા Seeded Users)

**Password બધા માટે સરખો: `ChangeMe123!`**

| Username | Role | મુખ્ય ઉપયોગ |
|---|---|---|
| `admin` | Admin | Company/Sites/Users/Roles, Suspend/Reinstate, break-glass |
| `operator1` | Operator | Batch execution, dispensing, cleaning, evidence upload |
| `supervisor1` | Supervisor | Batch issue, deviation triage — ✅ **2026-09-18: હવે seed થયેલ છે**, manual create ની જરૂર નથી |
| `qa.reviewer` | QA Reviewer | Batch/deviation/CAPA/EM/cleaning review |
| `qa.releaser` | QA Releaser | Product/Recipe/Batch/CAPA/Deviation release-class decisions |
| `qc.reviewer` | QC Reviewer | Material lot disposition, sterilization/cleaning verify, OOS/OOT |
| `equipment.admin` | Equipment Administrator | Equipment/area create, qualify |
| `engineering.manager` | Engineering Manager | Equipment return-to-service |
| `calibration.tech` | Calibration Technician | Equipment calibration |
| `maintenance.tech` | Maintenance Technician | Equipment maintenance |
| `sanitation.operator` | Sanitation Operator | Cleaning, line clearance |
| `em.technician` | EM Technician | EM program/task/sample |
| `microbiology.analyst` | Microbiology Analyst | EM result recording |
| `sterilization.operator` | Sterilization Operator | Sterilization/CIP-SIP cycles |
| `aseptic.operator` | Aseptic Operator | Aseptic execution |
| `aseptic.supervisor` | Aseptic Supervisor | Aseptic profile, operation start |
| `process.engineer` | Process Engineer | Product/Recipe/Material-Spec/**Supplier/Material** **authoring** |
| `integration.admin` | Integration Administrator | ERP/Edge integration |
| `ddcp.engineer` | DDCP Engineer | DDCP profile author/release |
| `ddcp.operator` | DDCP Operator | DDCP execution (performer) |
| `ddcp.operator2` | DDCP Operator | DDCP **independent verify** (IND-001) |
| `security.architect` | Security Architect | Threat-model authoring, control mapping (ડોક્યુમેન્ટ ૦૨) |
| `security.risk.approver` | Security Risk Approver | Accept residual risk, approve exceptions |
| `security.admin` | Security Admin | IdP/session/secrets/certificates/incidents |
| `platform.admin` | Platform Admin | Privileged access, break-glass |
| `vendor.support` | Vendor Support Engineer | Read-only privileged support sessions |

**2026-09-18 ઉમેરો:** ઉપરના છેલ્લા ૫ security roles માટે demo users હવે seed થયેલ છે (અગાઉ
role/permission તરીકે અસ્તિત્વમાં હતા, પણ કોઈ login નહોતું — ડોક્યુમેન્ટ ૦૨.૬ જુઓ). `supervisor1`
પણ હવે seed થયેલ છે (અગાઉ manual create કરવો પડતો).

---

## ૩. Example Product Dataset (Live-Tested, Reused Throughout)

| Entity | Value |
|---|---|
| Organization | Demo Manufacturing Co. (role-play: "Meridian Therapeutics Inc.") |
| Site | `SITE1` — Demo Site 1 |
| Product | `MERIDIJECT-PFS` — Code `MJ-PFS-40MG` — "MeridiJect™ Prefilled Syringe 40mg" |
| Recipe | `RCP-MJ-PFS-V1` |
| Batch | `MJ-PFS-B-2601` |
| Manufacturing Profile | `injectable_ddcp` (PFS family) |

---

## ૪. Recommended End-to-End Demo Flow

```
૦૧ Company/Site setup (admin)
       ↓
૦૨ Users/Roles verify + supervisor1 create (admin)
       ↓
૦૩ Supplier → Material → Material Spec → Receive Lot → Disposition (multiple roles)
       ↓
૦૪ Equipment create/qualify/calibrate (equipment.admin, calibration.tech)
       ↓
૦૬ Product Master: Draft → Submit → Release (process.engineer → qa.releaser)
       ↓
૦૭ Recipe Master: Draft → Steps/BOM → Submit → Release (process.engineer → qa.releaser)
       ↓
૦૮ Batch Create/Issue → Execute Steps (admin → operator1)
       ↓
૦૫ Line Clearance (sanitation.operator)
       ↓
૧૩ Sterilization → EM → Cleaning → Aseptic readiness+execute (multiple roles)
       ↓
૦૯ DDCP: Handoff → Fill → Assembly → Independent Verify (ddcp.operator → ddcp.operator2)
       ↓
   (જો કંઈ ખોટું થાય:) ૧૧ Deviation → ૧૦ CAPA
       ↓
૦૮ Production Complete (operator1)
       ↓
૧૨ QA Review → Release (qa.reviewer → qa.releaser)
       ↓
૧૪ Audit Trail / Evidence / Vault — trust-building closing demo (admin/qa.reviewer)
```

---

## ૫. Bugs — Status (2026-09-18 pass)

**નીચેના ૬ items અગાઉ "Critical Known Bugs" તરીકે અહીં listed હતા — બધા હવે તપાસીને ફિક્સ થયેલ છે
(code + tests + live demo DB પર લાગુ, 126/126 tests pass):**

1. ✅ **CAPA Close/Cancel** (ડોક્યુમેન્ટ ૧૦) — હવે real signature ceremony સાથે કામ કરે છે.
2. ✅ **Platform "Apply Legal Hold" (evidence)** (ડોક્યુમેન્ટ ૧૪) — signature ceremony wired; નવો
   backend challenge endpoint પણ ઉમેરાયો.
3. ✅ **Documents "Release"** (ડોક્યુમેન્ટ ૧૪) — signature ceremony wired.
4. ✅ **Material Specification "Release"** (ડોક્યુમેન્ટ ૦૩, SG-185) — project-owner decision પ્રમાણે
   (Product/Recipe release જેવો જ pattern) signature policy seed કરી, independence enforcement
   ઉમેર્યું.
5. ✅ **QC Method "Release"** (SG-186) — project-owner decision પ્રમાણે (qc_test_specification/release
   જેવો pattern) signature policy seed કરી.
6. ✅ **Deviation TRIAGE state mismatch** (ડોક્યુમેન્ટ ૧૧) — UI હવે backend ના real state machine સાથે
   match કરે છે (REOPENED ના બધા options પણ હવે સાચા બતાવાય છે).

**આ એક item bug નહોતું — by design, still true:**

7. **Product/Recipe/Material-Spec Master Release — SoD (author ≠ releaser)** — જો draft author અને
   release કરનાર **એક જ વ્યક્તિ** હોય, release call **ઇરાદાપૂર્વક** fail થશે (`SOD_CONFLICT`).
   **હંમેશા બે અલગ login વાપરવા** (ડોક્યુમેન્ટ ૦૬/૦૭/૦૩) — આ regulated SoD control છે, bug નથી.

---

## ૬. Honest Gaps Summary (Client ને Roadmap તરીકે રજૂ કરવા)

**✅ 2026-09-18 pass માં Fixed (હવે gap નથી):**

| Area | શું થયું | ડોક્યુમેન્ટ |
|---|---|---|
| ~~Supplier/Material create — RBAC ગેટ નથી~~ | project-owner decision: Process Engineer + Admin (material.create/update, supplier.create, supplier_qualification.create — 4 નવા permission codes) | ૦૩ |
| ~~QC core pipeline (sample/result/test-order) પર RBAC ગેટ જ નથી~~ | project-owner decision: Execution (sample/test-order/result) → Operator+Supervisor+Admin; Investigation (lab-cause/retest/resample/impact) → QC Reviewer+QA Reviewer+Admin (11 નવા permission codes) | ૧૩ |
| ~~`/security` console નું frontend gate mismatch~~ | SG-204-class fix: gate હવે actual 5 security roles ચેક કરે છે (Admin-only નહીં); ૫ demo users પણ ઉમેર્યા | ૦૨ |
| ~~Document-19 v2 material lot release/reject — UI જ નથી~~ | backend પહેલેથી તૈયાર જ હતું — `/material-lots` પેજ પર "Release (QA)"/"Reject (QA)" buttons ઉમેર્યા (QA Releaser-only, independence server-enforced) | ૦૩ |

**✅ 2026-09-18 બીજો pass (Product/Recipe Master lifecycle + Equipment enforcement + Auto-Deviation):**

| Area | શું થયું | ડોક્યુમેન્ટ |
|---|---|---|
| ~~Product Master: `obsolete`/`superseded` unreachable~~ | બંને commands ઉમેર્યા, e-signature (independent of author, Document 106 §8 "cancel/abort/void" family — SG-208) | ૦૬ |
| ~~Product Master: `ProductFamily` authoring API નથી~~ | create+list API + frontend picker/inline-create | ૦૬ |
| ~~Product Master: `combination_product_type` free text~~ | controlled dropdown (provisional taxonomy — SG-209) | ૦૬ |
| ~~Legacy `/products` endpoints RBAC gate વગર~~ | `product.view` gate ઉમેર્યું | ૦૬ |
| ~~`product.suspend` ફક્ત Admin ને જ~~ | QA Releaser ને પણ ઉમેર્યું | ૦૬ |
| ~~Recipe Master: suspend/reinstate/obsolete/supersede — કંઈ જ built નથી~~ | ચારેય built, Product Master જેવો જ pattern (SG-208) | ૦૭ |
| ~~Recipe Master: `equipment_class` free string~~ | `EquipmentClass` master entity + dropdown | ૦૭ |
| ~~Equipment calibration/qualification/cleaning flags enforce નથી થતા~~ | Batch-step-start પર હવે real enforcement (equipment module ના existing eligibility check reuse કરીને) | ૦૭/૦૮ |
| ~~Supervisor role માટે demo user નથી~~ | `supervisor1` seed થયેલ | ૦૮ |
| ~~In-process out-of-range result auto-deviation trigger નથી કરતું~~ | હવે આપોઆપ OPEN/unassigned deviation ખૂલે છે (severity=minor, deviation_type=process) | ૦૮/૧૧ |
| ~~QA Review completeness / Release eligibility માત્ર ૩-૪ signal પર (SG-054/056)~~ | QC/materials/environment/equipment/CAPA/yield-reconciliation હવે real hard blocker તરીકે wired (QC oos/invalid + open OOS, material lot not released, EM action_excursion, equipment currently ineligible, batch-attributed deviation/OOS પરથી ખોલાયેલ open CAPA, yield/reconciliation FAILED/OUT_OF_LIMIT/OUT_OF_TOLERANCE — Document 17 "never built" claim ખોટી હતી, module પહેલેથી જ built હતું); QC oot/EM alert/yield-not-verified/packaging incomplete non-blocking warning તરીકે; genealogy nodes/edges હવે real events (material issue, production-complete) પર auto-populate થાય છે પણ completeness rule તરીકે વપરાતા નથી (Document 13 કોઈ rule define નથી કરતું) — genealogy completeness rule એકમાત્ર બાકી ગેપ | ૧૨ |

**હજુ ખુલ્લા ગેપ (આ પાસમાં ટચ નથી કર્યા — મોટા feature builds, પોતાની regulated decisions સાથે):**

| Area | Gap | ડોક્યુમેન્ટ |
|---|---|---|
| `gxp_batch.state` ક્યારેય "Released" નથી બતાવતું — release અલગ module માં (by design, bug નથી) | ૦૮/૧૨ |
| ~~Deviation/CAPA batch release ને block નથી કરતા~~ — **✅ Deviation half Fixed (SG-059 RESOLVED, બીજા session દ્વારા, ડોક્યુમેન્ટ ૧૧ જુઓ)**: open (non-CLOSED) deviation હવે batch release ને `OPEN_DEVIATION` blocker સાથે block કરે છે — auto-created deviations (ઉપર જુઓ) પણ આમાં ગણાય છે. **CAPA half હજુ ખુલ્લો.** | ૧૦/૧૧/૧૨ |
| Release ફક્ત `scope_type="batch"` support કરે છે (SG-056) | ૧૨ |
| Packaging hold state પહોંચી ના શકાય તેવું (read API `GET /packaging/v1/runs` ✅ already exists — 08 doc ની જૂની "no GET API" નોંધ ખોટી હતી, ચકાસાયેલ 2026-09-19) | ૦૮ |
| **Material consumption inventory ને link નથી કરતું** (નવું મળેલ, 2026-09-18) — batch ના `material_consume` step ના recipe-level auto inventory deduct નથી કરતું; `MaterialLot.available_quantity` અને `InventoryBalanceProjection` **બે અલગ, unsynchronized tracks** છે | ૦૩/૦૮ |
| DDCP ના કોઈ પણ action પર e-signature નથી, RBAC-only (SG-148, ~૧૪ actions) | ૦૯ |
| Recipe Master ના ૪ raw-UUID policy fields (`qualification_policy_id` વગેરે) — કોઈ backing entity નથી, deliberately unbuilt | ૦૭ |

---

## ૭. કેવી રીતે વાપરવું

આ index થી શરૂ કરો → user ના role પ્રમાણે login કરો → સંબંધિત document ખોલો → "ડેમો વોકથ્રુ" સેક્શન
follow કરો (દરેક field ready-filled example સાથે છે) → "ધ્યાન રાખવા જેવી બાબતો" સેક્શન પહેલાં એકવાર
વાંચી લો જેથી live demo દરમિયાન કોઈ button click surprise fail ના આપે.
