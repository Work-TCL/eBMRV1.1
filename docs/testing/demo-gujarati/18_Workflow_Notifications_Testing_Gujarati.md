# ૧૮. Workflow Handoff Notifications — Testing Guide (Gujarati)

> **આ ડોક્યુમેન્ટ શેના માટે:** આ session માં નવું બનેલ **"Workflow Handoff Notification"** ફીચર —
> એટલે કે "કોઈ એક user એ draft/record બનાવ્યો, હવે **બીજા** user એ તેના પર decision લેવાનો છે" ત્યારે
> સિસ્ટમ automatically સાચા user ને notify કરે — તેને **browser માંથી, real seeded data સાથે** કેવી
> રીતે ટેસ્ટ કરવું તેની સંપૂર્ણ, module-by-module ગાઇડ છે.
>
> બધા routes, field labels, role/permission names **current code વાંચીને ચકાસેલ છે (2026-09-24)** —
> કંઈ પણ ધારેલું (guessed) નથી. Field labels એ જ છે જે browser ના form માં ખરેખર દેખાય છે.
>
> **Login:** બધા users માટે password સરખો છે: `ChangeMe123!`

---

## ૧. આ ફીચર શું છે (સાદી ભાષામાં)

અત્યાર સુધી, જ્યારે કોઈ Operator/Admin એક record (દા.ત. deviation, batch, NCR) ને એવી state માં
લાવે જ્યાં **બીજા કોઈ role** (સામાન્ય રીતે QA Releaser અથવા QA Reviewer) એ next decision (approve/
disposition/close/release) લેવાનો હોય — તો એ બીજા user ને ખબર જ ના પડે, જ્યાં સુધી એ પોતે એ page
manually ના ખોલે.

હવે **Topbar ના જમણી બાજુ, "🔔 Reminders" bell ની બાજુમાં એક નવું 📥 (inbox) icon** દેખાશે —
**"Workflow Actions" bell**. આ icon:

- ફક્ત ત્યારે જ દેખાય જ્યારે logged-in user માટે ઓછામાં ઓછું ૧ item pending હોય.
- ઉપર **niલા રંગનું badge** (number) બતાવે — કેટલા items **unread** (નથી જોયા) છે.
- Click કરો → એક dropdown list ખૂલે — દરેક item માં: **entity નું નામ** (દા.ત. "Deviation DEV-001"),
  **શું pending છે** (દા.ત. "Disposition needed"), અને click કરવાથી **સીધું એ record ના page પર**
  લઈ જાય.
- જે user એ પોતે એ record ને એ state માં લાવ્યો (trigger કર્યો), **તેને પોતાને આ notification ક્યારેય
  ના દેખાય** — આ ઇરાદાપૂર્વક છે (Segregation of Duties / SoD nudge — જે વ્યક્તિ કામ કરે એ જ પોતે
  approve ના કરી શકે).
- Record પર action લેવાઈ જાય (અથવા record બીજી state માં ચાલ્યું જાય) એટલે notification **આપોઆપ
  અદૃશ્ય** થઈ જાય — refresh કરવાની જરૂર નથી.

---

## ૨. Browser માં General Testing Pattern (દરેક Module માટે સરખો)

દરેક module ટેસ્ટ કરવા માટે નીચેનો pattern વાપરો — ફક્ત fields/roles module પ્રમાણે બદલાય છે (§૪ માં
દરેક module નું અલગ table છે):

| Step | શું કરવું |
|---|---|
| ૧ | **Trigger user** તરીકે login કરો (મોટાભાગે `admin` — બધા module માં કામ કરવા માટે પૂરતા permissions ધરાવે છે) |
| ૨ | Concerned module ના page પર જાવ, નવો record બનાવો, અને §૪ ના table પ્રમાણે તેને "pending" state સુધી આગળ વધારો |
| ૩ | **એ જ user (`admin`) તરીકે logged-in રહીને** Topbar જુઓ — 📥 icon **ના દેખાવો જોઈએ** (અથવા દેખાય તો પણ આ ચોક્કસ record તેમાં ના હોવો જોઈએ) — કારણ કે Admin એ પોતે જ trigger કર્યું છે (SoD exclusion) |
| ૪ | Logout કરો, **Notified user** તરીકે login કરો (§૪ ના table માં આપેલ, દા.ત. `qa.releaser`) |
| ૫ | Topbar માં 📥 icon જુઓ — badge count વધેલો દેખાવો જોઈએ |
| ૬ | 📥 icon click કરો — dropdown માં entity નું નામ + "શું જોઈએ છે" ટેક્સ્ટ દેખાવો જોઈએ |
| ૭ | Entry પર click કરો — સાચા record ના page પર જવું જોઈએ, અને entry "read" (નિલા dot વગર) થઈ જવો જોઈએ |
| ૮ | એ જ page પર §૪ પ્રમાણે next action (disposition/approve/close વગેરે) perform કરો |
| ૯ | Action સફળ થયા પછી, ફરીથી 📥 icon જુઓ — એ item હવે **dropdown માંથી ગાયબ** થઈ ગયો હોવો જોઈએ (અથવા જો module માં ૨ stage હોય, તો બીજું નવું item આવેલું દેખાવું જોઈએ — §૪ માં નોંધેલ છે) |

> **નોંધ:** Bell દર ૩૦ સેકન્ડે આપોઆપ refresh થાય છે. જો તરત ના દેખાય, થોડી seconds રાહ જુઓ અથવા page
> reload કરો.

---

## ૩. કયા Real Users વાપરવા

| Username | Role | આ ડોક્યુમેન્ટમાં ઉપયોગ |
|---|---|---|
| `admin` | Admin | લગભગ બધા module માં **Trigger** (record બનાવવો/આગળ વધારવો) તરીકે — બધા modules પર broad permission ધરાવે છે |
| `qa.releaser` | QA Releaser | મોટાભાગના modules માં **Notified user** (release/disposition/close/approve decision લેનાર) |
| `qa.reviewer` | QA Reviewer | CAPA Plan, NCR Verification, SCAR Review માટે **Notified user** |
| `qc.reviewer` | QC Reviewer | NCR Verification માટે (qa.reviewer સાથે) |
| `process.engineer` | Process Engineer | Supplier/Material master બનાવવા માટે (Material Lot, Supplier Qualification ટેસ્ટ કરવા) |
| `operator1` | Operator | Material receiving, QC sample/result entry માટે |

---

## ૪. Module-by-Module: Trigger State, Data, Notified User

> **Permission code** column એ backend માં code check કરે છે તે — QA દર્શાવવા માટે, taste ના ભાગ નથી,
> ફક્ત reference માટે છે.

| # | Module | Trigger પછી State | Notification | Permission Code | Notified User(s) |
|---|---|---|---|---|---|
| ૧ | Batch Release | Evaluate → `eligible` | "Ready for release decision" | `release.release` | `qa.releaser` |
| ૨ | Deviation | Impact Assess → `IMPACT_ASSESSMENT` | "Disposition needed" | `qms_deviation.disposition` | `qa.releaser` |
| ૨ | Deviation | Disposition → `DISPOSITION` | "Ready for QA closure" | `qms_deviation.close` | `qa.releaser` |
| ૩ | CAPA | Create → `OPEN` | "CAPA plan needed" | `capa.plan` | `qa.reviewer`, `qa.releaser` |
| ૩ | CAPA | Effectiveness Pass → `EFFECTIVENESS_REVIEW` | "Ready for QA closure" | `capa.close` | `qa.releaser` |
| ૪ | Document | Submit → `REVIEW` | "Ready for release" | `document.release` | `qa.releaser` |
| ૫ | Nonconformance (NCR) | Evaluate → `EVALUATION` | "Disposition needed" | `ncr.disposition` | `qa.releaser` |
| ૫ | NCR | Disposition (REWORK/REPAIR/RETURN/SCRAP/USE_AS_IS) | "Verification needed" | `ncr.verify` | `qa.reviewer`, `qc.reviewer` |
| ૫ | NCR | Verify → `VERIFICATION` | "Ready for QA closure" | `ncr.close` | `qa.releaser` |
| ૬ | Complaint | Investigate → `REPORTABILITY_ASSESSMENT` | "Reportability assessment needed" | `complaint.reportability` | `qa.releaser` |
| ૬ | Complaint | Reportability → `RESPONSE` | "Ready for QA closure" | `complaint.close` | `qa.releaser` |
| ૭ | Change Control | Impact → `IMPACT_ASSESSMENT` | "Approval needed" | `change.approve` | `qa.releaser` |
| ૭ | Change Control | Verify+Effective → `EFFECTIVE` | "Ready for closure" | `change.close` | `qa.releaser` |
| ૮ | SCAR (Supplier Case) | Supplier Response → `SUPPLIER_RESPONSE` | "Internal review needed" | `scar.review` | `qa.reviewer` |
| ૮ | SCAR | Review Accept+Effectiveness → `EFFECTIVENESS` | "Ready for closure" | `scar.close` | `qa.releaser` |
| ૯ | Field Action | Reportability → `REGULATORY_DECISION` | "Approval needed" | `field_action.approve` | `qa.releaser` |
| ૯ | Field Action | Effectiveness → `EFFECTIVENESS` | "Ready for closure" | `field_action.close` | `qa.releaser` |
| ૧૦ | Internal Audit | Add Finding → `FINDINGS_OPEN` | "Ready for closure" | `internal_audit.close` | `qa.releaser` |
| ૧૧ | Risk | Residual Assessment → `RESIDUAL_ASSESSMENT` | "Acceptance needed" | `risk.accept` | `qa.releaser` |
| ૧૨ | OOS (Out-of-Spec) | Impact → `final_disposition` | "Disposition needed" | `oos_record.disposition` | `qa.releaser` |
| ૧૨ | OOS | Disposition → `qa_approval` | "Ready for closure" | `oos_record.close` | `qa.releaser` |
| ૧૩ | OOT (Out-of-Trend) | Evaluate → `open` | "Ready for closure" | `oot_record.close` | `qa.releaser` |
| ૧૪ | Material Lot | Sample+Test → `qc_disposition_pending` | "Ready for release decision" | `material_lot.release` | `qa.releaser` |
| ૧૫ | Supplier Qualification | Create → `requested` | "Approval needed" | `supplier_qualification.approve` | `qa.releaser` |
| ૧૬ | Material Specification 🆕 | Create draft → `draft` | "Ready for release" | `material_spec.release` | `qa.releaser` |
| ૧૭ | Product Master 🆕 | Submit → `under_review` | "Ready for release" | `product.release` | `qa.releaser` |
| ૧૮ | Recipe Master 🆕 | Submit → `under_review` | "Ready for release" | `recipe.release` | `qa.releaser` |

---

## ૫. Detailed Step-by-Step — Module પ્રમાણે (Real Data સાથે)

નીચેના દરેક module માં **frontend form માં ખરેખર દેખાતા field labels** અને realistic example
values આપેલ છે — સીધા copy કરીને browser માં ભરી શકાય.

### ૫.૧ Batch Release (`/release`)

આ module ને doc #૧૨ (Batch Review/Release) માં પહેલેથી વિગતવાર કવર કરેલ છે — ફક્ત notification ના
ભાગ પર ધ્યાન:

1. `admin` તરીકે login કરી batch ને production-complete સુધી લઈ જાવ (doc #૮/#૧૨ પ્રમાણે) અને QA
   Review package complete કરો.
2. `/release` page ખોલો → "Batch" dropdown માંથી batch પસંદ કરો → **Evaluate** click કરો.
3. Scope `eligible` થઈ જાય એટલે — logout, `qa.releaser` તરીકે login કરો.
4. 📥 bell માં "Batch [batch_number]" — "Ready for release decision" દેખાવો જોઈએ.
5. Click કરો → `/release?scope_id=...` પર જાય, batch આપોઆપ ખુલેલો દેખાય.
6. **Release** button click → SignatureCeremony ખૂલે → **Password** field માં `ChangeMe123!` ભરો
   → Confirm.
7. Bell માંથી item ગાયબ થઈ જવો જોઈએ.

---

### ૫.૨ Deviation (`/deviations`)

doc #૧૧ માં પહેલેથી કવર છે. Notification-focused steps:

1. `admin`: **Deviation Number** = `DEV-TEST-01`, **Deviation Type** = `process`, **Severity** =
   `major` ભરી create કરો.
2. Triage → Contain (Containment description ભરો) → Investigation (Investigator + Root Cause
   method) → Impact Assessment (બધા impact fields ને `none`/`low` ભરો, save કરો).
3. હવે state `IMPACT_ASSESSMENT` — `qa.releaser` તરીકે login કરી bell માં "Deviation DEV-TEST-01" —
   "Disposition needed" જુઓ.
4. Click → `/deviations/{id}` ખૂલે. **Disposition code** = `CONTINUE`, **Disposition rationale** =
   `"No quality impact found"`, CAPA required = No → submit.
5. Bell માં હવે એ જ deviation "Ready for QA closure" તરીકે ફરી દેખાવો જોઈએ (નવો notification —
   કારણ કે state `DISPOSITION` થયું).
6. **Conclusion** ભરીને Close કરો → bell માંથી ગાયબ.

---

### ૫.૩ CAPA (`/capa`)

1. `admin`: CAPA create કરો — **Problem statement**, **Root cause ref**, source = existing
   deviation/NCR. Create થતાં જ state `OPEN`.
2. `qa.reviewer` (અથવા `qa.releaser`) login કરો — bell માં "CAPA [number]" — "CAPA plan needed".
3. Click → `/capa/{id}`. **Corrective action**, **Preventive action** ભરી Plan submit કરો.
4. Actions ઉમેરી complete કરો, **Effectiveness check**: Criterion/Data source/Observation
   dates ભરી, **Result** = `pass` નોંધો.
5. State `EFFECTIVENESS_REVIEW` થતાં — `qa.releaser` ના bell માં "Ready for QA closure" દેખાય.
6. Click → **Conclusion** ભરી Close (signature જરૂરી હોય તો Password ભરો) → bell ખાલી.

---

### ૫.૪ Controlled Document (`/documents`)

1. `admin`: **Document code**, **Type** = `sop`, **Version label** = `1.0` ભરી draft બનાવો.
2. **Submit** (reviewers ઉમેરો) → state `REVIEW`.
3. `qa.releaser` login → bell માં "[document_code] v1.0" — "Ready for release".
4. Click → `/documents?document_code=...` — document code auto-filled search સાથે ખૂલે.
5. **Review completed** ✓ કરી **Release** → Password confirm → bell માંથી ગાયબ.

---

### ૫.૫ Nonconformance / NCR (`/nonconformances`) 🆕

1. `admin`: `/nonconformances` → New NCR:
   - **NCR number**: `NCR-TEST-01`
   - **Defect code**: `DIM-001`
   - **Severity**: `major`
   - **Scope type**: `material`
   - **Affected record ID**: (કોઈ પણ existing material lot ID)
   - **Specification reference**: `SPEC-001`
2. Segregate (**Segregation location** = `Quarantine Cage 3`) → Evaluate (**Evaluation
   conclusion** = `"Not usable as-is"`) → state `EVALUATION`.
3. `qa.releaser` login → bell માં "NCR NCR-TEST-01" — "Disposition needed".
4. Click → `/nonconformances/{id}`. **Disposition type** = `USE_AS_IS`, **Justification** =
   `"Cosmetic defect only, no functional impact"` ભરી submit.
5. State REWORK/REPAIR/RETURN/SCRAP/USE_AS_IS માંથી કોઈ પણ થાય — bell માં **નવો** item "Verification
   needed" દેખાય, પણ આ વખતે `qa.reviewer` **અથવા** `qc.reviewer` ના bell માં (qa.releaser ના નહીં).
6. `qa.reviewer` login → click → **Reinspection result** ભરી Verify → state `VERIFICATION`.
7. `qa.releaser` ના bell માં ફરી "Ready for QA closure" દેખાય → **Conclusion** ભરી Close.

---

### ૫.૬ Complaint (`/complaints`) 🆕

1. `admin`: **Complaint number**, **Received at**, **Source channel** = `written`, **Nature code**
   = `DEVICE_MALFUNCTION`, **Description** = `"Autoinjector failed to deliver full dose"`,
   **Lot/batch/serial reference** ભરો.
2. Triage (**Severity** = `serious`) → Investigation decision (Investigation required = Yes) →
   Investigate (**Findings**, **Conclusion** ભરો) → state `REPORTABILITY_ASSESSMENT`.
3. `qa.releaser` login → bell "Reportability assessment needed".
4. Click → **Applicable regimes** = `FDA_MDR`, **Rationale** ભરી submit → state `RESPONSE`.
5. Response record કરો (**Direction**/**Type**/**Message**) → bell માં "Ready for QA closure".
6. **Conclusion** ભરી Close → bell ખાલી.

---

### ૫.૭ Change Control (`/changes`) 🆕

1. `admin`: **Change number**, **Type** = `recipe`, **Classification** = `permanent`,
   **Current state**/**Proposed state** (JSON અથવા text), **Reason for change** ભરો.
2. **Regulatory impact**/**Validation impact**/**Training impact** ભરી Impact submit → state
   `IMPACT_ASSESSMENT`.
3. `qa.releaser` login → bell "Approval needed".
4. Click → **Approval notes** ભરી Approve → state `IMPLEMENTATION`.
5. Implement (**Description**, **Due date**) → Verify (**Verification evidence**) → Make Effective
   (**Effective at**) → state `EFFECTIVE`.
6. Bell માં ફરી "Ready for closure" દેખાય → **Post-implementation review conclusion** ભરી Close.

---

### ૫.૮ SCAR / Supplier Case (`/supplier-cases`) 🆕

1. `admin`: Supplier case create — **Case number**, **Defect code**, **Severity**, **Affected
   lot**, **Containment**.
2. Case detail પર SCAR issue કરો — **SCAR number**, **Response due**, **Problem statement**.
3. Supplier Response ભરો — **Supplier root cause**, **Supplier corrective actions** → state
   `SUPPLIER_RESPONSE`.
4. `qa.reviewer` login → bell "Internal review needed".
5. Click → `/supplier-cases/{case_id}` (SCAR case ના page પર જ ખૂલે). **Decision** = `accepted`,
   **Rationale** ભરી Review submit → state `IMPLEMENTATION`.
6. Effectiveness ભરો (**Result** = `pass`, **Evidence**) → state `EFFECTIVENESS`.
7. `qa.releaser` ના bell માં "Ready for closure" → **Source status decision** = `no_change`,
   **Conclusion** ભરી Close.

---

### ૫.૯ Field Action (`/field-actions`) 🆕

1. `admin`: **Action number**, **Action type** = `recall`, **Trigger type**, **Trigger record ID**
   ભરી create.
2. Scope define કરો (**Lot/batch/serial reference**, **Action required**).
3. Reportability ભરો — **Applicable regimes**, **Decision** = `reportable`, **Rationale** → state
   `REGULATORY_DECISION`.
4. `qa.releaser` login → bell "Approval needed" → **Conclusion** ભરી Approve → state `APPROVAL`.
5. Communications/Reconciliation પૂરા કરો → Effectiveness ભરો (**Result**, **Evidence**) → state
   `EFFECTIVENESS`.
6. Bell માં "Ready for closure" → **Conclusion** ભરી Close.

---

### ૫.૧૦ Internal Audit (`/audits`) 🆕

1. `admin`: **Audit number**, **Programme reference**, **Scheduled date**, **Audit criteria** ભરી
   create → Start audit.
2. **Finding number**, **Severity**, **Response due**, **Requirement reference**, **Observation**
   ભરી finding ઉમેરો → audit state `FINDINGS_OPEN`.
3. `qa.releaser` login → bell "Ready for closure".
4. Click → `/audits/{id}`. (ધ્યાન: closure પહેલા finding ને Response + Verify કરવો જરૂરી — **Correction**/
   **Root cause**/**Corrective action** ભરી Respond, પછી `qa.releaser`/qualified verifier **Verification
   notes** ભરી Verify.) પછી **Conclusion** ભરી audit Close કરો.

---

### ૫.૧૧ Risk (`/risks`) 🆕

1. `admin`: **Risk number**, **Risk type**, **Hazard or problem**, **Potential effect**, **Context**
   ભરી create → state `DRAFT`.
2. Initial Assessment (**Severity**/**Occurrence**/**Detectability**) → Controls (**Control type**/
   **Control description**/**Mitigation action**) → Residual Assessment (ફરી Severity/Occurrence/
   Detectability, ઓછા numbers સાથે) → state `RESIDUAL_ASSESSMENT`.
3. `qa.releaser` login → bell "Acceptance needed".
4. Click → `/risks/{id}`. **Accepting role**, **Acceptance rationale** ભરી Accept → state
   `ACCEPTED` → bell માંથી ગાયબ (Risk Review માટે કોઈ notification નથી — §૬ જુઓ).

---

### ૫.૧૨ OOS / Out-of-Specification (`/quality/oos`) 🆕

1. `operator1`: QC Sample → Test Order → Result record કરો (spec ની acceptance range બહારની
   value — દા.ત. spec `<=10.0` હોય તો `99.000000`) → QC Result "oos" mark થાય.
2. `/quality/oos` page → **Source QC result ID** ભરી "Open OOS" (**OOS number** આપો).
3. `qa.reviewer`: **Activity type**/**Response** ભરી Lab Investigation → **Assignable cause
   found?** = No → Classify.
4. **બીજા** qualified user (independent — dispositioning user પોતે ના હોવો જોઈએ) દ્વારા: Extended
   Investigation sign કરો → Retest plan (**Justification**, **Number of retests**) → Resample plan
   (**Scientific rationale**) → **Impact assessment**, **Hold status** ભરી Impact submit → state
   `final_disposition`.
5. `qa.releaser` login → bell "Disposition needed" (OOS number સાથે).
6. Click → **Final classification** ભરી, signature (Password) સાથે Disposition submit → state
   `qa_approval`.
   > **ધ્યાન:** disposition કરનાર user ને પોતાને close notification **નહીં** દેખાય (SoD) — **બીજા**
   > `qa.releaser` (અથવા Admin) ના bell માં "Ready for closure" દેખાશે.
7. એ user login કરી Close submit કરે → bell ખાલી.

---

### ૫.૧૩ OOT / Out-of-Trend (`/quality/oos`, "Out-of-trend" card) 🆕

1. `qa.releaser`: QC spec માં trend rule attach કરેલ test ના result ને evaluate કરો — trend
   rule ની range બહારની value આપો → `/quality/oot/v1/evaluate` (OOT card માં **Source QC result**
   પસંદ કરો) → state `open`.
2. **નોંધ:** આ module માટે કોઈ dedicated detail page નથી (existing product limitation) — bell entry
   click કરવાથી `/quality/oos` page જ ખૂલશે (OOT card સાથે).
3. `qa.releaser` (કોઈ પણ, evaluate કરનાર સિવાય) ના bell માં "Ready for closure" દેખાય.
4. **OOT record ID** + **Expected version** ભરી Close submit → bell ખાલી.

---

### ૫.૧૪ Material Lot (`/material-lots`) 🆕

1. `operator1`: Material lot receive કરો — **Material**, **Internal lot number** = `LOT-TEST-01`,
   **Received quantity**, **Expiry date** ભરો → state `quarantine`.
2. Sampling + Testing પૂરું થઈ lot `qc_disposition_pending` state માં આવે (QC module દ્વારા —
   doc #૦૩ જુઓ).
3. `qa.releaser` login → bell "Lot LOT-TEST-01" — "Ready for release decision".
4. Click → `/material-lots?q=LOT-TEST-01` — search box માં lot number auto-filled, list માં એ
   lot સીધો દેખાય.
5. Lot row પર Release action, signature (Password) confirm → bell ખાલી.

---

### ૫.૧૫ Supplier Qualification (`/suppliers`) 🆕

1. `process.engineer`: Supplier create — **Legal name**, **Role type**, **Country**, **Site name**
   ભરો.
2. એ supplier ના site માટે Qualification request — **Supplier site**, **Risk class** = `critical`.
   → state `requested`.
3. `qa.releaser` login → bell "Supplier qualification -- [legal_name]" — "Approval needed".
   > **ખાસ નોંધ:** આ notification **site-independent** છે — `qa.releaser` ભલે ગમે તે site પર
   > assign હોય, તોય આ item તેને દેખાશે (કારણ કે supplier qualification approval કોઈ ચોક્કસ site
   > સાથે બંધાયેલ નથી).
4. Click → `/suppliers?supplier_id=...` — સીધો એ supplier નો detail modal ખૂલે.
5. **Decision** = `approved`, **Justification** ભરી submit → bell ખાલી.

---

### ૫.૧૬ Material Specification (`/material-specifications`) 🆕

> **આ module એક real user report થી ઉમેરાયું** — spec draft બનાવ્યા પછી `qa.releaser` ને bell માં
> કંઈ દેખાતું નહોતું (registry.py માં material specification ક્યારેય ઉમેરાયેલ જ નહોતું). હવે fixed.

1. `process.engineer`: **New specification draft** — **Business ID**, **Version number**,
   **Material** (picker), **Name** ભરો → submit. Spec સીધું `draft` state માં બને (અહીં કોઈ separate
   "Submit" step નથી — Recipe/Product થી અલગ).
2. `qa.releaser` login → bell "Material Spec [business_id] v[version]" — "Ready for release".
3. Click → `/material-specifications?material_spec_version_id=...` — સીધો release signature ceremony
   ખૂલે.
4. Password (signature) confirm → Release → bell ખાલી.

---

### ૫.૧૭ Product Master (`/product-master`) 🆕

1. `process.engineer`: **New draft** — **Business ID**, **Product code**, **Name**,
   **Manufacturing profile** ભરો → **Submit** → state `under_review`.
2. `qa.releaser` login → bell "Product [business_id] v[version]" — "Ready for release".
3. Click → `/product-master?product_version_id=...` — સીધો version detail ખૂલે (Release button ત્યાં
   જ છે).
4. **Release** → signature → bell ખાલી.

---

### ૫.૧૮ Recipe Master (`/recipe-master`) 🆕

1. `process.engineer`: **New draft** — **Recipe code**, **Product version**, **Batch size** ભરી,
   Section/Step ઉમેરી → **Submit** → state `under_review`.
2. `qa.releaser` login → bell "Recipe [recipe_code] v[version]" — "Ready for release".
3. Click → `/recipe-master?recipe_version_id=...` — સીધો version detail ખૂલે (Release button ત્યાં જ
   છે).
4. **Release** → signature → bell ખાલી.

---

## ૬. Module-to-Module જોડાણ (કેવી રીતે એક Module બીજા સાથે જોડાયેલ છે)

Notification ફીચર દરેક module ને **સ્વતંત્ર રીતે** track કરે છે — પણ real business process માં આ
modules એકબીજા સાથે **જોડાયેલા** છે. Testing કરતી વખતે આ chain સમજવી ઉપયોગી છે:

```
Batch Execution (production)
   │
   ├─► QC Result OOS/OOT થાય ──► OOS/OOT investigation ──► Disposition/Close
   │                                                            │
   ├─► Step/Material Reject થાય ──► Nonconformance (NCR) ──► Disposition ──► Verification ──► Close
   │
   ├─► Unexpected event ──► Deviation ──► Disposition (capa_required?) ──┐
   │                                                                      ▼
   │                                                                    CAPA ──► Plan ──► Effectiveness ──► Close
   │
   └─► Production Complete + QA Review ──► Release Scope (eligible) ──► Release Decision

Field/Market
   │
   └─► Customer Complaint ──► Investigation ──► Reportability ──┬──► Response ──► Close
                                                                  └──► (ગંભીર હોય તો) Field Action ──► Approve ──► Close

Supplier Side
   │
   ├─► Supplier Qualification (new supplier) ──► Approve
   └─► Supplier-caused NCR/OOS ──► Supplier Case ──► SCAR issue ──► Response ──► Review ──► Effectiveness ──► Close

Document/Process Change
   │
   └─► Change Control (recipe/spec/SOP બદલવો) ──► Impact ──► Approve ──► Implement ──► Verify ──► Effective ──► Close
         │
         └─► ઘણી વાર Document release સાથે જોડાયેલ ──► Document Submit ──► Release

Quality System (ongoing)
   │
   ├─► Internal Audit ──► Findings ──► Response ──► Verify ──► Close
   └─► Risk Assessment ──► Initial ──► Controls ──► Residual ──► Accept ──► (periodic) Review
```

**Testing tip:** આખી chain એક સાથે demo કરવા માટે — પહેલા એક Deviation બનાવો જેમાં
**CAPA required = Yes** રાખો; disposition કરતી વખતે સિસ્ટમ આપોઆપ `DeviationCAPARequired` event
publish કરે છે (પણ CAPA record પોતે manually `/capa` પર જઈને, એ deviation ને **source** તરીકે
select કરીને, **તમારે** બનાવવો પડે — auto-create નથી થતું, એ SPEC_GAP તરીકે નોંધાયેલ છે).

---

## ૭. અગત્યની ખામીઓ (Known Limitations) — Testing વખતે ધ્યાનમાં રાખો

| # | શું | વિગત |
|---|---|---|
| ૧ | OOT માટે કોઈ detail page નથી | Bell click કરવાથી `/quality/oos` page જ ખૂલશે — ચોક્કસ OOT record સીધો નહીં ખૂલે (existing platform limitation, notification bug નથી) |
| ૨ | Material Lot deep-link ફક્ત search box ભરે | `/material-lots?q=LOT-XXX` — સીધો lot open નથી થતો, list માં filter થઈને દેખાય છે |
| ૩ | Risk "Review" (periodic) માટે notification નથી | ફક્ત પહેલી acceptance માટે notification મળે છે — પછીના periodic/triggered reviews માટે નહીં (§Topic 1, Client Decision doc જુઓ) |
| ૪ | Bell auto-refresh ૩૦ સેકન્ડે | તરત ના દેખાય તો થોડી રાહ જુઓ |
| ૫ | Email/SMS notification નથી | ફક્ત browser માં logged-in હોય ત્યારે જ દેખાય (Client Decision doc, Topic 4 જુઓ) |

---

## ૮. Admin-Only: Rebuild Check (Troubleshooting)

જો કોઈ notification ના દેખાય (અથવા ખોટી રીતે રહી ગયેલ લાગે), `admin` તરીકે login કરી નીચેનો
API call કરી શકાય (કોઈ UI button નથી, ફક્ત technical troubleshooting માટે):

```
POST /dashboard/v1/workflow-actions:rebuild
```

આ સિસ્ટમ ના બધા ૧૮ modules ને ફરીથી scan કરી notification list ને current data સાથે sync કરે છે —
કોઈ data delete/change નથી કરતું, ફક્ત notification list ને refresh કરે છે.
