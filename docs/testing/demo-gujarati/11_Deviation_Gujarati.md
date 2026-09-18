# ૧૧. Deviation Management — Gujarati Demo Guide

> Source: `services/gxp-api/app/modules/qms/{models,commands,router,signature_support}.py`,
> `frontend/src/app/deviations/`, `services/gxp-api/scripts/seed.py`,
> `services/gxp-api/tests/test_qms_deviation.py`.

> ✅ **2026-09-18 fix:** `process.engineer` ને હવે `qms_deviation.view` (read-only) મળે છે — પહેલા
> બિલકુલ view permission ન હતું (નીચે ૧૧.૬ મુદ્દા ૪ જુઓ).
>
> ✅ **2026-09-18 fix (project-owner-directed, SG-059 RESOLVED):** Batch પર attributed કોઈ પણ open
> (non-`CLOSED`) deviation હવે batch release ને block કરે છે (નીચે ૧૧.૬ મુદ્દા ૩ જુઓ).

---

## ૧૧.૧ Deviation એટલે શું?

Manufacturing process માં જ્યારે કંઈક **planned/approved process થી અલગ** થાય (દા.ત. temperature
excursion, equipment malfunction, પ્રોસેસ સ્ટેપ ચૂકી જવાય) — ત્યારે તેને formal રીતે record, investigate,
અને disposition (નિર્ણય) કરવા માટે **Deviation Record** બનાવવામાં આવે છે. આ eBMR/eDHR compliance નો
core building block છે.

> ✅ **2026-09-18 ઉમેર્યું — Auto-Deviation on Out-of-Range Result:** Manual creation ઉપરાંત, હવે
> batch execution ના in-process result (ડોક્યુમેન્ટ ૦૮ §૮.૫) જ્યારે declared min/max ની બહાર જાય, ત્યારે
> **સિસ્ટમ આપોઆપ** એક deviation ખોલે છે — `OPEN` state, **owner unassigned** (`owner_subject_id = null`
> — Supervisor/QA Reviewer એ manually claim કરવો પડે), `severity = minor` (human triage વખતે upgrade
> કરી શકે), `deviation_type = process`, `deviation_number = DEV-AUTO-<batch>-<step>-<...>`. **Scope
> (project-owner-directed):** ફક્ત out-of-range result trigger — step-hold/equipment-block triggers
> આ pass માં deliberately સામેલ નથી. વિગત ડોક્યુમેન્ટ ૦૮ §૮.૫ માં.

## ૧૧.૨ Lifecycle (State Machine)

```
OPEN → TRIAGE → CONTAINMENT → INVESTIGATION → IMPACT_ASSESSMENT → DISPOSITION → CLOSED
                                                                                    ↓
                                                                                REOPENED
```

REOPENED માંથી સીધું CONTAINMENT, INVESTIGATION, IMPACT_ASSESSMENT, DISPOSITION અથવા CLOSED — કોઈ પણ
state પર જઈ શકાય (backend supports it — UI હાલ મર્યાદિત options બતાવે છે, નીચે ૧૧.૬ જુઓ).

## ૧૧.૩ મુખ્ય Fields

| Field | Example |
|---|---|
| `deviation_number` | `DEV-0002` (free text — તમે કોઈ પણ ફોર્મેટ આપી શકો) |
| `deviation_type` | `process` |
| `source_type` | `batch` / `qc` / `material` / `equipment` / `environment` / `supplier` / `document` / `system` |
| `severity` | `critical` / `major` / `minor` |
| `owner_subject_id`, `investigator_subject_id` | જવાબદાર વ્યક્તિઓ — ✅ **2026-09-18:** `owner_subject_id` હવે **nullable** (auto-created deviation માટે null, human triage વખતે assign) |
| `containment` | `{"actions":[{"target_type":"batch","target_id":"...","description":"batch quarantined"}]}` |
| `root_cause` | `{"method":"5-why","no_assignable_cause":false}` |
| `impact_assessment` | ૬ ફરજિયાત categories: `quality`, `patient_user`, `released_distributed_product`, `validation`, `data_integrity`, `regulatory` |
| `disposition_code` | `CONTINUE` / `HOLD` / `REJECT` / `REWORK` / `REPROCESS` / `ADDITIONAL_TEST` / `DESTROY` / `FIELD_ACTION_ASSESSMENT` |
| `disposition_rationale`, `capa_required`, `capa_rationale` | disposition-time decision |

---

## ૧૧.૪ Permission મેટ્રિક્સ

| Action | Permission Code | કોણ ધરાવે છે (seeded roles) | E-signature? |
|---|---|---|---|
| Create | `qms_deviation.create` | Admin, Operator, **Supervisor**, QA Reviewer, QC Reviewer | ના |
| Triage | `qms_deviation.triage` | Admin, Supervisor, QA Reviewer | ના |
| Contain | `qms_deviation.contain` | Admin, Supervisor, QA Reviewer | ના |
| Investigate | `qms_deviation.investigate` | Admin, QA Reviewer | ના |
| Impact Assessment | `qms_deviation.impact` | Admin, QA Reviewer | ના |
| **Disposition** | `qms_deviation.disposition` | Admin, **QA Releaser** | **હા** |
| Extend | `qms_deviation.extend` | Admin, QA Reviewer | ના |
| **Close** | `qms_deviation.close` | Admin, **QA Releaser** | **હા** |
| Reopen | `qms_deviation.reopen` | Admin, QA Releaser | ના |
| View | `qms_deviation.view` | Admin + Operator/Supervisor/QA Reviewer/QA Releaser/QC Reviewer | ના |

**Seeded demo logins ઉપલબ્ધ:** `admin`, `operator1`, `supervisor1`, `qa.reviewer`, `qa.releaser`,
`qc.reviewer` (બધા password `ChangeMe123!`). ✅ `supervisor1` હવે seed થયેલ છે (2026-09-18) —
triage/contain demo directly `supervisor1` login થી બતાવી શકાય.

**E-signature ceremony (Disposition અને Close):** password re-entry (`reauth_password`) + challenge —
challenge `meaning` field signature policy માંથી આવે છે (દા.ત. "Released"/"Approved"). **Independence
rule:** dispositioning/closing કરનાર વ્યક્તિ deviation ના `investigator_subject_id`/`owner_subject_id`
થી અલગ હોવી જોઈએ — same person પોતાનું જ investigation close ના કરી શકે.

---

## ૧૧.૫ ડેમો વોકથ્રુ — Example Filled Data

**Login:** `operator1` / `ChangeMe123!` (create) → `qa.reviewer` (triage/contain/investigate/impact) →
`qa.releaser` (disposition/close)

### Step 1 — Deviation Create (`operator1`)

| Field | Example |
|---|---|
| Deviation Number | `DEV-2026-014` |
| Type | `process` |
| Source Type | `batch` |
| Source (Batch) | MeridiJect PFS batch (ડોક્યુમેન્ટ ૦૮ માં બનાવેલ batch) |
| Severity | `major` |
| Description | "Line 2 પર fill-weight check દરમિયાન 3 consecutive units target ની બહાર મળ્યા" |

### Step 2 — Triage + Containment (`qa.reviewer`)
- Containment action: `{"actions":[{"target_type":"batch","target_id":"<batch-id>","description":"Batch quarantined pending investigation"}]}`

### Step 3 — Investigation + Root Cause (`qa.reviewer`)
- Method: `5-why`
- Conclusion: "Fill-head #2 calibration drift ઓળખાયું"

### Step 4 — Impact Assessment (`qa.reviewer`)
છ categories (quality, patient_user, released_distributed_product, validation, data_integrity,
regulatory) — દરેક માટે impact `none`/`minor`/વગેરે નક્કી કરવું.

### Step 5 — Disposition (`qa.releaser`, **e-signature જરૂરી**)

| Field | Example |
|---|---|
| Disposition Code | `CONTINUE` |
| Rationale | "Fill-head recalibrate કર્યા બાદ re-verify — quality impact નથી" |
| CAPA Required? | `Yes` — "recurring pattern seen — systemic action જરૂરી" |

### Step 6 — Close (`qa.releaser`, **e-signature જરૂરી**)
- Closure conclusion: "Investigated; no quality impact; disposition CONTINUE."

### વૈકલ્પિક વોકથ્રુ — Auto-Deviation Demo ✅ નવું

Manual create ને બદલે, **live auto-trigger બતાવવા**:
1. ડોક્યુમેન્ટ ૦૮ પ્રમાણે batch step start કરો (`operator1`).
2. Result record કરો — parameter ની declared `max_value` થી વધારે value આપો (દા.ત. WEIGHT max 2.0kg
   પર 2.5kg).
3. `admin`/`qa.reviewer` login થી `/deviations` પેજ ખોલો — નવો `DEV-AUTO-...` deviation **પહેલેથી
   OPEN** state માં દેખાશે, **owner ખાલી**.
4. `qa.reviewer` triage કરીને પોતે claim કરે — પછી Step 2 થી આગળ normal flow ચાલુ.

---

## ૧૧.૬ ધ્યાન રાખવા જેવી બાબતો (Known Limitations — honestly flag in demo)

1. ~~UI/backend state mismatch on TRIAGE~~ **✅ Fixed (2026-09-18)** — Deviation detail પેજ હવે
   TRIAGE state માંથી ફક્ત "Contain" જ બતાવે છે (backend ફક્ત `TRIAGE → CONTAINMENT` transition allow
   કરે છે) — sequence: Triage → Contain → Investigate.
2. ~~REOPENED પછી મર્યાદિત options~~ **✅ Fixed (2026-09-18)** — REOPENED state હવે Contain/
   Investigation/Impact/Disposition/Close/Extend — backend જે ખરેખર allow કરે છે એ બધું જ UI માં
   બતાવે છે.
3. ~~Deviation/CAPA હાલ batch release ને block નથી કરતા~~ **✅ Fixed for deviations (2026-09-18,
   project-owner-directed, SG-059 RESOLVED)** — batch પર attributed (`source_type="batch"`,
   `source_id=<batch>`) કોઈ પણ deviation જે `CLOSED` state માં ન હોય, એ હવે release ને `OPEN_DEVIATION`
   blocker સાથે block કરે છે (`release/service.py::evaluate_eligibility()`; `POST /release/v1/
   scopes/.../evaluate` અને final `.../release` બંને પર enforced). Rule પસંદ કરેલો: severity threshold
   નહીં, ANY open deviation. **CAPA જાણી જોઈને block નથી કરતું** — Document 27 માં DEV-FR-022 જેવી કોઈ
   requirement જ નથી, ડોક્યુમેન્ટ ૧૦.૬ મુદ્દા ૪ જુઓ.
4. ~~`process.engineer` role deviation જોઈ પણ ના શકે~~ **✅ Fixed (2026-09-18)** — `process.engineer`
   ને હવે `qms_deviation.view` (read-only) મળે છે; triage/contain/investigate/disposition/close માટે
   હજુ `qa.reviewer`/`qa.releaser` જ વાપરવા (એ actions Process Engineer ને assign નથી).
