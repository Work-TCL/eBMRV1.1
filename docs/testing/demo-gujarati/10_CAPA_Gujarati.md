# ૧૦. CAPA (Corrective &amp; Preventive Action) — Gujarati Demo Guide

> Source: `services/gxp-api/app/modules/qms/{capa_models,capa_commands,capa_router}.py`,
> `frontend/src/app/capa/`, `services/gxp-api/scripts/seed.py`,
> `services/gxp-api/tests/test_qms_capa.py`.

> ✅ **2026-09-18 fix:** CAPA Close/Cancel હવે frontend માં real e-signature ceremony (password
> re-entry) સાથે કામ કરે છે — અગાઉ broken હતું (નીચે ૧૦.૬ મુદ્દા ૧ જુઓ, હવે fixed). Effectiveness
> Check પણ હવે **Define** અને **Record Result** — બે અલગ, સાચા fields સાથેના steps માં split છે (પહેલા
> એક જ form માં conflated હતું, required fields missing હતા).
>
> ✅ **2026-09-18 fix:** CAPA `source_id` હવે FK-validated છે (નીચે ૧૦.૬ મુદ્દા ૩ જુઓ) — `deviation`/
> `oos`/`oot`/`ncr`/`complaint`/`audit`/`supplier`/`risk` માંથી કોઈ પણ `source_type` માટે, `source_id`
> ખરેખર અસ્તિત્વમાં ન હોય તો CAPA create `VALIDATION_FAILED` સાથે reject થાય છે.
>
> ✅ **2026-09-18 fix (project-owner-directed):** **Record Effectiveness Result** હવે e-signature
> ફરજિયાત કરે છે — "Approved", QA Releaser, owner થી independent, Close જેવી જ ceremony (નીચે ૧૦.૬
> મુદ્દા ૨ જુઓ). **Define** effectiveness check હજુ unsigned (plan-time criteria, quality conclusion
> નથી).
>
> ✅ **2026-09-18 fix (project-owner-directed):** Open deviation હવે batch release ને **block કરે છે**
> (SG-059 RESOLVED — નીચે ૧૦.૬ મુદ્દા ૪ જુઓ).
>
> ✅ **2026-09-19 fix:** CAPA હવે પણ batch release block કરે છે — batch ને directly નહીં (Document 27
> નું `source_type` "batch" support જ નથી કરતું, spec ની બહાર જઈને invent નથી કર્યું), પણ batch પર
> attributed deviation/OOS માંથી ખોલાયેલ કોઈ CAPA હજુ ખુલ્લું હોય તો (`OPEN_CAPA` blocker,
> `release/service.py::_capa_signals`) — નીચે ૧૦.૬ મુદ્દા ૪ જુઓ.

---

## ૧૦.૧ CAPA એટલે શું?

CAPA = **Corrective and Preventive Action** — કોઈ deviation/OOS/OOT/NCR/complaint/audit/supplier
issue/risk/trend માંથી ઓળખાયેલ systemic સમસ્યા ને **મૂળ કારણ (root cause) સુધી પહોંચી, કાયમી ધોરણે
ઉકેલવા** માટેની ઔપચારિક પ્રક્રિયા.

## ૧૦.૨ Lifecycle

```
OPEN → PLAN → IMPLEMENTATION → IMPLEMENTATION_VERIFIED → EFFECTIVENESS_MONITORING
     → EFFECTIVENESS_REVIEW → CLOSED
                    ↓ (fail)                                  ↓
            EFFECTIVENESS_FAILED → REOPENED/IMPLEMENTATION   REOPENED
```
`CANCELLED` પણ terminal state છે (Close endpoint જ, `cancellation_reason` સાથે — અલગ Cancel button
UI માં દેખાય છે પણ backend endpoint `/close` જ છે).

**Effectiveness step બે ભાગમાં:**
1. **Define effectiveness check** — `criterion`, `data_source`, `observation_start/end`, `due_date`
   (બધા ફરજિયાત) → state `EFFECTIVENESS_MONITORING`.
2. **Record effectiveness result** — પહેલાં defined check પસંદ કરવો (`check_id`) + `result`
   (pass/fail/inconclusive) + `evidence` → state `EFFECTIVENESS_REVIEW` (pass/inconclusive) અથવા
   `EFFECTIVENESS_FAILED` (fail).

## ૧૦.૩ મુખ્ય Fields

| Field | Example |
|---|---|
| `capa_number` | `CAPA-2026-007` (free text) |
| `source_type` | `deviation` (પણ oos/oot/ncr/complaint/audit/supplier/risk/trend/security/validation હોઈ શકે) |
| `source_id` | Deviation ID (દા.ત. `DEV-2026-014`) — **FK-validated** (નીચે જુઓ) |
| `problem_statement` | "Line 2 fill-head recurring calibration drift — 3rd occurrence this quarter" |
| `scope_type` / `scope_refs` | `site` / `product` / `process` / `enterprise` |
| `risk_class` | `high` |
| `root_cause_ref` | `{"investigation_ref": "<deviation-investigation-id>"}` |
| `corrective_action` / `preventive_action` / `effectiveness_plan` | JSON — plan-time |
| Child: **CAPA Action** | `{"description":"qualify new seal supplier","action_type":"corrective","owner","due_date"}` |
| Child: **Effectiveness Check** | `{"criterion":"seal failure rate < 0.1% over 90 days","data_source":"QC incoming inspection log","due_date":"...","result":"pass","evidence":{"description":"..."}}` |

**✅ 2026-09-18 fix:** `source_id` હવે 8 જાણીતા `source_type` (deviation/oos/oot/ncr/complaint/audit/
supplier/risk) માટે FK-validated છે — ખોટો/અસ્તિત્વમાં ન હોય એવો ID આપવાથી create `VALIDATION_FAILED`
સાથે reject થાય છે. બાકીના ૩ types (`trend`/`security`/`validation`) માટે કોઈ single unambiguous table
codebase માં નથી (SG-063, open gap) — એ ત્રણ માટે check હજુ થતી નથી.

---

## ૧૦.૪ Permission મેટ્રિક્સ

| Action | Permission Code | કોણ ધરાવે છે | E-signature? |
|---|---|---|---|
| Create | `capa.create` | Admin, QA Reviewer | ના |
| Plan | `capa.plan` | Admin, QA Reviewer | ના |
| Add Action | `capa.action.add` | Admin, QA Reviewer | ના |
| Complete Action | `capa.action.complete` | Admin, QA Reviewer, QC Reviewer | ના |
| Define Effectiveness | `capa.effectiveness` | Admin, **QA Releaser** | ના |
| **Record Effectiveness Result** | `capa.effectiveness` | Admin, **QA Releaser** | **હા** — "Approved", independent |
| Extend | `capa.extend` | Admin, QA Reviewer | ના |
| **Close** | `capa.close` | Admin, **QA Releaser** | **હા** — "Approved", independent |
| **Cancel** | `capa.close` (same endpoint, `cancellation_reason` સાથે) | Admin, QA Releaser | **હા** |
| Reopen | `capa.reopen` | Admin, QA Releaser | ના |
| View | `capa.view` | Admin + QMS-view roles | ના |

**✅ 2026-09-18 fix:** `process.engineer` ને હવે `capa.view` (read-only) મળે છે — પહેલા બિલકુલ view
permission ન હતું.

---

## ૧૦.૫ ડેમો વોકથ્રુ — Example Filled Data

**Login:** `qa.reviewer` / `ChangeMe123!` (create/plan/actions) → `qa.releaser` (effectiveness/close)

### Step 1 — CAPA Create (`qa.reviewer`)

| Field | Example |
|---|---|
| CAPA Number | `CAPA-2026-007` |
| Source Type | `deviation` |
| Source ID | `DEV-2026-014` (ડોક્યુમેન્ટ ૧૧ નું deviation) |
| Problem Statement | "Line 2 seal-head recurring drift — 3જી ઘટના આ quarter માં" |
| Risk Class | `high` |
| Root Cause Ref | `{"investigation_ref": "<deviation-investigation-id>"}` |

### Step 2 — Plan (`qa.reviewer`)
- Corrective action: "Seal supplier replace + incoming inspection ઉમેરવી"
- Preventive action: "Calibration frequency મહિનેથી પખવાડિયે વધારવી"

### Step 3 — CAPA Action ઉમેરવી (`qa.reviewer`)

| Field | Example |
|---|---|
| Description | "નવો seal supplier qualify કરવો" |
| Action Type | `corrective` |
| Owner | `process.engineer` |
| Due Date | (30 દિવસ પછી) |

### Step 4 — Action Complete (`qa.reviewer`)
- Implementation Evidence: `{"description":"નવો supplier qualified, PO placed","evidence_refs":["DOC-1"]}`
(બધા actions complete થાય એટલે state → `IMPLEMENTATION_VERIFIED`.)

### Step 5 — Define Effectiveness Check (`qa.releaser`)

| Field | Example |
|---|---|
| Criterion | "Seal failure rate < 0.1% over 90 days" |
| Data Source | "QC incoming inspection log" |
| Observation Start / End | (આજ / 90 દિવસ પછી) |
| Due Date | (90 દિવસ પછી) |

### Step 6 — Record Effectiveness Result (`qa.releaser`, **e-signature ફરજિયાત**)

| Field | Example |
|---|---|
| Effectiveness Check | Step 5 નો check પસંદ કરવો |
| Result | `pass` |
| Evidence | "Observed rate 0.02% — target ની અંદર" |

Sign → password re-entry → (state → `EFFECTIVENESS_REVIEW`)

### Step 7 — Close (`qa.releaser`, **e-signature ફરજિયાત**)

| Field | Example |
|---|---|
| Conclusion | "Effectiveness demonstrated — seal failure rate 0.02%, target < 0.1%. CAPA closed." |

Sign → password re-entry → CAPA `CLOSED`.

---

## ૧૦.૬ ધ્યાન રાખવા જેવી બાબતો (Known Limitations)

1. ~~CAPA Close/Cancel frontend માં broken~~ **✅ Fixed (2026-09-18)** — હવે real signature ceremony
   (password re-entry) સાથે કામ કરે છે.
2. ~~Effectiveness Define/Record-ને e-signature નથી~~ **✅ Fixed (2026-09-18, project-owner-directed)**
   — **Record Result** હવે signed છે (Document 106 row 80/close જેવી જ "Approved"/QA Releaser/
   independent-of-owner ceremony, `capa_record`/`effectiveness` નવી SignaturePolicy row). **Define**
   ઇરાદાપૂર્વક unsigned જ રાખ્યું (plan-time criteria entry, quality conclusion નહીં — Document 106
   એના માટે કોઈ signature point વ્યાખ્યાયિત નથી કરતું).
3. ~~CAPA↔Deviation (અને oos/oot/ncr/complaint/audit/supplier/risk) link ચેક નથી થતી~~
   **✅ Fixed (2026-09-18)** — `source_id` હવે એ 8 `source_type` માટે FK-validated છે; `trend`/
   `security`/`validation` માટે કોઈ backing table ન હોવાથી unvalidated રહે છે (SG-063, open gap).
4. ~~Deviation/CAPA batch release ને block નથી કરતા~~ **✅ Fixed for deviations (2026-09-18) અને CAPA
   (2026-09-19)** — batch પર attributed કોઈ પણ open deviation (state ≠ `CLOSED`) `OPEN_DEVIATION`
   blocker સાથે release block કરે છે. **CAPA — batch ને directly નહીં** (Document 27 નું `source_type`
   "batch" support કરતું જ નથી, DEV-FR-022 જેવી કોઈ direct requirement પણ નથી — spec ની બહાર જઈને નવો
   source_type invent નથી કર્યો) **પણ real ૨-hop સંબંધ દ્વારા**: batch પર attributed deviation/OOS ને
   source બનાવીને ખોલાયેલ કોઈ CAPA હજુ ખુલ્લું (state CLOSED/CANCELLED સિવાય) હોય તો `OPEN_CAPA`
   blocker (`release/service.py::_capa_signals`).
