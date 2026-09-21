# ૬. Product Master — Gujarati Demo Guide

> ⭐ **આ ડોક્યુમેન્ટ ડેમોનો core ભાગ છે.** Source: `services/gxp-api/app/modules/product_master/
> {models,commands,router,service}.py`, `frontend/src/app/product-master/page.tsx`,
> `services/gxp-api/scripts/seed.py`, `services/gxp-api/tests/test_product_master.py`,
> અગાઉ live-tested `docs/testing/DDCP_Client_Demo_Guide_Gujarati.md`.

---

## ૬.૧ અગત્યનું — REAL Regulated Page ઓળખવી

| | `/product-master` | `/products` |
|---|---|---|
| સ્ટેટસ | **✅ REAL** — Document 09 Product/Constituent/Regulatory-Profile Master | **❌ Dead redirect** — 2026-09-08 થી `/product-master` પર redirect જ કરે છે (જૂનું ટેબલ કાયમ ખાલી) |
| API | `POST/PUT /products/v1/...` | (backend હજુ live છે પણ frontend વાપરતું જ નથી — કોઈ RBAC ગેટ પણ નથી) |

**ડેમોમાં હંમેશા `/product-master` વાપરવું.**

---

## ૬.૨ Lifecycle (State Machine)

```
draft → under_review → released → suspended
                              ↑________|  (reinstate)
                              ↓
                         obsolete / superseded  (terminal, ✅ 2026-09-18 Fixed)
```

> ✅ **2026-09-18 Fixed:** `obsolete`/`superseded` હવે reachable છે — `POST /products/v1/{id}/obsolete`
> અને `.../supersede`, બંને `product.suspend` permission (Admin + QA Releaser) + e-signature ("Approved",
> **independent of the author**) સાથે. `supersede` ને `superseding_version_id` જોઈએ — બીજા,
> **released** version ની ID, જે `superseded_by_version_id` field માં record થાય છે. બંને states
> **terminal** — obsolete/superseded થયા પછી કોઈ transition શક્ય નથી. (Signature shape નું reasoning:
> SG-208, `docs/generated/18_SPEC_GAPS.md`.)

---

## ૬.૩ મુખ્ય Fields

| Field | ઉદાહરણ (MeridiJect PFS) |
|---|---|
| `product_business_id` | `MERIDIJECT-PFS` |
| `product_code` | `MJ-PFS-40MG` |
| `name` | `MeridiJect™ Prefilled Syringe 40mg` |
| `version_no` | `1` |
| `manufacturing_profile_code` | `injectable_ddcp` |
| `strength_value` / `strength_uom` | `40` / `mg` |
| `sterile_profile_id` | Released sterile process profile (injectable_ddcp માટે **ફરજિયાત**) |
| `product_family_id` | ✅ **2026-09-18 Fixed** — હવે real dropdown (`ProductFamily` picker) + inline "+ New family" create. પહેલાં UI માં ક્યાંય render જ નહોતું થતું (orphaned FK). |
| `combination_product_type` | ✅ **2026-09-18 Fixed** — હવે controlled dropdown: `prefilled_syringe` / `autoinjector` / `inhalation_device` / `drug_eluting_device` / `other` (free text fallback). **Provisional taxonomy** — SG-209 માં logged, final list હજુ confirm કરવાનું બાકી. |
| `udi_applicable` | `true` |
| `pmoa_reference`, `part4_profile_code` | Regulatory metadata |

**Manufacturing Profiles supported:** `injectable_ddcp`, `inhalation_ddcp`, `drug_eluting_device`,
`device`, `pharma`. (`injectable_ddcp`/`inhalation_ddcp` ને released sterile profile ફરજિયાત.)

**Product Constituents:** "meal-kit" style drug+device combination — `ProductConstituent`
(constituent_type/role_code) બીજા Product Master version ને point કરે, + `ConstituentCompatibilityVersion`
(drug↔device interface compatibility) parent release સાથે જ release થાય.

---

## ૬.૪ Permission મેટ્રિક્સ

| Action | Permission Code | કોણ ધરાવે છે | E-signature? | Meaning |
|---|---|---|---|---|
| Draft Create/Edit/Submit/Validate | `product.author` | Admin, **Process Engineer** | ના | — |
| **Release** | `product.release` | Admin, **QA Releaser** | **હા** | "Released" |
| **Suspend** | `product.suspend` | Admin, **QA Releaser** ✅ | **હા** | "Performed", reason ફરજિયાત |
| **Reinstate** | `product.suspend` | Admin, **QA Releaser** ✅ | **હા** | "Approved", reason ફરજિયાત, independent (of whoever suspended) |
| **Obsolete** ✅ નવું | `product.suspend` | Admin, **QA Releaser** | **હા** | "Approved", **independent of the author**, reason ફરજિયાત |
| **Supersede** ✅ નવું | `product.suspend` | Admin, **QA Releaser** | **હા** | "Approved", **independent of the author**, `superseding_version_id` ફરજિયાત |
| View | `product.view` | બધા operational roles | ના | — |

> ✅ **2026-09-18 Fixed:** `product.suspend` હવે **QA Releaser ને પણ** મળેલ છે (પહેલાં ફક્ત Admin).
> **Obsolete/Supersede independence નોંધ:** Suspend/Reinstate ની independence "whoever suspended it" સામે
> ચેક થાય છે, પણ Obsolete/Supersede ની independence **draft ના author** સામે ચેક થાય છે (Document 106 §8
> "cancel/abort/void" family — SG-208 જુઓ). એટલે: જે વ્યક્તિએ draft બનાવ્યો (`process.engineer`), એ
> વ્યક્તિ (ભલે QA Releaser role પણ ધરાવતી હોય) પોતે એ જ version ને obsolete/supersede ના કરી શકે —
> અલગ QA Releaser જોઈએ.

---

## ૬.૫ Segregation of Duties — Author ≠ Releaser (Code-Level Enforced!)

**આ ફક્ત role separation નથી — person-level enforcement છે.** `release_product_version()` ચકાસે છે
કે version ના `Created` audit event નો actor, release કરનાર actor થી **અલગ વ્યક્તિ** હોવી જોઈએ —
ભલે એ વ્યક્તિ પાસે બંને (`product.author` + `product.release`) permission હોય (દા.ત. Admin). Same person
પોતે draft કરેલ product ને પોતે જ release ના કરી શકે.

> **ડેમો માટે અગત્યનું:** જો `admin` login થી જ author + release બંને કરવાનો પ્રયાસ કરશો, તો release
> call **SoD conflict error સાથે fail થશે**. હંમેશા **બે અલગ login** વાપરવા — `process.engineer`
> (author) → `qa.releaser` (release).

---

## ૬.૬ E-signature Ceremony — શું થાય છે?

1. `POST .../signature-challenges` — record ના current version + hash સાથે bound એક time-limited
   challenge બને છે.
2. Actual Release/Suspend/Reinstate call માં `challenge_id` + `reauth_password` (તમારો પોતાનો login
   password ફરીથી) મોકલવો પડે છે.

આ AG-07 rule (login/MFA એ signature નથી) ને satisfy કરે છે — signing ના સમયે fresh password જોઈએ,
session login થી અલગ.

---

## ૬.૭ ડેમો વોકથ્રુ — Example Filled Data (Live-Tested Dataset)

> આ ડેટાસેટ પહેલાથી real UI સામે end-to-end ટેસ્ટ થયેલ છે (2026-09-08) — fabricated નથી.

**Login: `process.engineer` / `ChangeMe123!`**

### Step 1 — Draft Create (`/product-master`)

| Field | Value |
|---|---|
| Business ID | `MERIDIJECT-PFS` |
| Product Code | `MJ-PFS-40MG` |
| Name | `MeridiJect™ Prefilled Syringe 40mg` |
| Manufacturing Profile | `injectable_ddcp` |
| Strength | `40 mg` |
| Sterile Profile | (પહેલેથી released sterile profile પસંદ કરવો — જુઓ ડોક્યુમેન્ટ ૧૩) |

### Step 2 — Submit for Review (`process.engineer`)
Draft → `under_review`.

### Step 3 — Validate Completeness (`process.engineer`)
PRD-FR-032 ચેક — manufacturing profile પ્રમાણે ફરજિયાત fields (sterile profile વગેરે) બધા ભરેલા છે
કે નહીં.

### Step 4 — Release (`qa.releaser`, **e-signature ફરજિયાત**)
Challenge → password re-entry → Signature meaning "Released" → Product `released` state માં.

### Step 5 — Suspend/Reinstate Demo (વૈકલ્પિક, `qa.releaser` login — Admin પણ ચાલે)

| Field | Value |
|---|---|
| Reason (Suspend) | "Sterile profile revalidation pending — temporary hold" |
| Reason (Reinstate) | "Revalidation completed, QA approved" — **અલગ QA Releaser** login જોઈએ (suspend કરનારથી independent) |

### Step 6 — Obsolete/Supersede Demo ✅ નવું (`qa.releaser`, **draft author થી અલગ**)

**Obsolete (કાયમી retire, replacement વગર):**

| Field | Value |
|---|---|
| Version state | `released` |
| Reason | "Product discontinued — replaced by next-gen device" |
| Signature | Challenge → password re-entry → meaning "Approved" |
| Result | `obsolete` state — **terminal**, હવે કોઈ transition શક્ય નથી |

**Supersede (નવા released version દ્વારા replace):**

| Field | Value |
|---|---|
| Prerequisite | બીજો **released** version (same `product_business_id`) already existing હોવો જોઈએ |
| `superseding_version_id` | એ બીજા version ની ID |
| Reason | "Replaced by v2 — updated device configuration" |
| Result | `superseded` state, `superseded_by_version_id` field માં successor ID record થાય છે |

> **અગત્યનું:** બંને actions draft ના author થી **independent** QA Releaser જ કરી શકે — same actor જે
> draft બનાવ્યો હોય (ભલે QA Releaser role પણ ધરાવતો હોય) એ પોતે obsolete/supersede ના કરી શકે
> (`SOD_INDEPENDENCE_REQUIRED`).

---

## ૬.૮ ધ્યાન રાખવા જેવી બાબતો (Known Limitations)

1. ~~`obsolete`/`superseded` states પહોંચી ના શકાય તેવા છે~~ **✅ Fixed (2026-09-18)** — §૬.૨/૬.૭
   જુઓ. Signature shape (independent of author, matching Document 106 §8 "cancel/abort/void" family)
   SG-208 માં logged, project-owner confirmation બાકી.
2. ~~`ProductFamily` માટે કોઈ authoring API જ નથી~~ **✅ Fixed (2026-09-18)** — હવે create+list API
   (`/products/v1/families`) + frontend picker/inline-create.
3. ~~`combination_product_type` free text છે, controlled dropdown નથી~~ **✅ Fixed (2026-09-18)** —
   dropdown, પણ taxonomy **provisional** (SG-209).
4. **Legacy `/products` backend endpoints હજુ live છે** — ✅ **RBAC gate હવે ઉમેર્યું (2026-09-18)**
   (`product.view` gate) — frontend હજુ પણ આ routes વાપરતું નથી.
5. ~~`product.suspend` ફક્ત Admin ને જ~~ **✅ Fixed (2026-09-18)** — QA Releaser ને પણ મળેલ છે.
