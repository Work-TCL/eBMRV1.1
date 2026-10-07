# ૧૩. Sterilization, Aseptic, Environmental Monitoring, Cleaning — Gujarati Demo Guide

> Source: `services/gxp-api/app/modules/equipment/{sterilization,aseptic,em,cleaning}_{models,
> commands,router}.py`, `frontend/src/app/{sterilization,aseptic,em,cleaning}/`,
> `services/gxp-api/scripts/seed.py`, `services/gxp-api/tests/conftest.py`.

---

## ૧૩.૧ Sterilization

**Covers:** Steam autoclave, dry heat, depyrogenation, gas, radiation, SIP, CIP, sterile filtration.

**State Machine:** `DRAFT → CYCLE_STARTED → CYCLE_RUNNING → CYCLE_COMPLETE/REVIEW_PENDING →
ACCEPTED/FAILED` (+ `HOLD`)

**અગત્યનો design principle:** ઓપરેટર ક્યારેય "Pass/Fail" જાતે નથી નક્કી કરતો — ફક્ત raw telemetry
data (parameter_summary) + controller ના `critical_alarm` ફ્લેગ (જે immediate HOLD force કરે) capture
થાય છે. **Accept/Reject decision ફક્ત review step પર, અલગ (independent) વ્યક્તિ દ્વારા જ થાય છે** —
અને `critical_alarm` ક્યારેય પણ raised થયું હોય તેવો cycle accept ના જ થઈ શકે, ભલે પછીથી telemetry
ઠીક લાગે.

**Reprocessing control:** જો નવો cycle ના load items, પહેલાના `FAILED` cycle સાથે item_reference
share કરે, તો explicit `reprocessing_authorization_ref` વગર reject થાય.

**Sterile Filtration:** અલગ sub-flow — Install Filter → Integrity Test (pre/post) → Complete. Reuse
count auto-calculate થાય (પાછલા ACCEPTED uses પરથી) — **પણ કોઈ enforced reuse limit નથી** (gap).

| Action | Permission | કોણ | Signed? |
|---|---|---|---|
| Sterilization Profile Create | `process_cycle_profile_version.create` | Admin, QA Reviewer (**Sterilization Operator ને ઇરાદાપૂર્વક નથી**) | — |
| Cycle Create | `process_cycle.create` | Admin, QA Reviewer, **Sterilization Operator** | ના |
| Cycle Start | `process_cycle.start` | Admin, QA Reviewer, Sterilization Operator | **હા** — "Performed" |
| **Review/Accept/Reject Cycle** | `process_cycle.review` | Admin, QA Reviewer, **QC Reviewer** (Sterilization Operator **નહીં — SoD**) | **હા** — "Reviewed", independent |
| Filter Install/Complete | `sterile_filter_use.*` | Admin, Sterilization Operator | Complete: **હા** — "Performed" |

**Demo Login:** `sterilization.operator` (cycle create/start) → `qc.reviewer` (review/accept)

**Example:** Profile `STR-PROC-001` v1, `process_type="steam_autoclave"`.

---

## ૧૩.૨ Aseptic

**Real terminology:** "**Aseptic Operation**" — media fill એ dedicated workflow નથી, ફક્ત reference
field (`media_fill_reference`) તરીકે capture થાય.

**State Machine:** `PREPARATION → EXECUTION → ASEPTIC_COMPLETE` (+ `HOLD`)

**Readiness Composition (અગત્યનું cross-module feature):** Start કરતા પહેલા ૪ વસ્તુ automatic ચેક
થાય છે:
1. EM Area Readiness (નીચે ૧૩.૩)
2. Line Clearance Status (ડોક્યુમેન્ટ ૦૫)
3. Equipment Eligibility (દરેક listed equipment_id માટે)
4. Sterile-Input Eligibility (દરેક listed sterile input માટે — ૧૩.૧ સાથે જોડાણ)

**બધા ૪ pass ના થાય ત્યાં સુધી Start ના જ થાય.**

**Interventions:** `inherent`/`routine`/`corrective`/`non_routine` — **`planned=false` હોય તો આપોઆપ
`requires_deviation=true` થાય અને HOLD force થાય** ("no hidden intervention").

**Events:** `severity: info/warning/critical` — critical event પણ HOLD force કરે (EM/HVAC excursion,
gown breach).

| Action | Permission | કોણ | Signed? |
|---|---|---|---|
| Aseptic Profile Create | `aseptic_profile_version.create` | Admin, **Aseptic Supervisor** | — |
| Operation Create | `aseptic_operation.create` | Admin, Aseptic Operator | ના |
| **Start Operation** | `aseptic_operation.start` | Admin, **Aseptic Supervisor** (Aseptic Operator **નહીં — ઇરાદાપૂર્વક split**) | **હા** — "Performed" |
| Intervention/Event Record | `aseptic_operation.intervention`/`.event` | Admin, Aseptic Operator | ના |
| **Complete Operation** | `aseptic_operation.complete` | Admin, Aseptic Operator | **હા** — "Performed", critical હોય તો reason ફરજિયાત |

**Demo Login:** `aseptic.supervisor` (profile/start) → `aseptic.operator` (execute)

**Example:** Profile `ASP-PROC-001`, `required_area_classification="ISO_7"`.

---

## ૧૩.૩ Environmental Monitoring (EM)

**Tracks:** viable_air, surface_contact, settle_plate, personnel, nonviable_particle, temperature,
humidity, differential_pressure.

**Flow:** Task Create → Collect (instrument calibration eligibility ચેક) → Record Result → Review
(independent).

**⚠️ Alert/Action ચેક performer-attested છે, automatic numeric-limit comparison નથી** (gap —
monitoring-type units અલગ-અલગ હોવાથી). `action_excursion` result → આપોઆપ `EmExcursion` બને +
`requires_deviation=true`.

**Area Readiness:** open excursion → `HOLD`; last 5 samples માંથી કોઈ `alert` → `WARNING`; નહીં તો
`READY` (**ક્યારેય manual toggle નથી**, હંમેશા derived).

| Action | Permission | કોણ | Signed? |
|---|---|---|---|
| EM Program/Task Create | `em_program.create`/`em_sample.create` | Admin, **EM Technician** | ના |
| Record Result | `em_sample.record_result` | Admin, EM Technician, **Microbiology Analyst** | **હા** — "Performed" |
| **Review Result** | `em_sample.review` | Admin, QA Reviewer, QC Reviewer (EM Technician/Microbiology Analyst **નહીં — SoD**) | **હા** — "Reviewed", independent |

**Demo Login:** `em.technician` → `microbiology.analyst` (result) → `qa.reviewer` (review)

**Example:** Location `EM-LOC-GRADE-A-01` (Area `AREA-GRADE-A`, ISO_5, critical), `monitoring_type=
"viable_air"`, result `{"cfu": 2}` (normal) અથવા `{"cfu": 999}` (action_excursion).

---

## ૧૩.૪ Cleaning (Equipment/Area Cleaning Verification)

**નોંધ:** આ "Cleaning Validation study" module નથી — execution/verification of an existing cleaning
procedure છે. `CleaningProcedureVersion` (SOP master) seed-only છે, કોઈ create endpoint નથી.

**State Machine:** `CLEANING → CLEANING_VERIFICATION → CLEAN/HOLD`

`dirty_hold_exceeded`/`clean_until` procedure ના `dirty_hold_limit_minutes`/`clean_hold_limit_minutes`
પરથી computed. Verification fail → equipment/area hold (history ક્યારેય overwrite નથી થતી).

| Action | Permission | કોણ | Signed? |
|---|---|---|---|
| Cleaning Execution Create/Complete | `cleaning_execution.create`/`.complete` | Admin, Operator, Supervisor, QA Reviewer, **Sanitation Operator** | Complete: **હા** — "Performed" |
| **Verify Cleaning** | `cleaning_execution.verify` | Admin, QA Reviewer, QC Reviewer (Sanitation Operator **નહીં — code-level SoD**) | **હા** — "Verified", independent |

**Demo Login:** `sanitation.operator` (clean) → `qc.reviewer` (verify)

**Example:** Procedure `CLN-PROC-001`, `dirty_hold_limit_minutes=240`, `clean_hold_limit_minutes=4320`.

---

## ૧૩.૫ QC અને Validation — સંક્ષિપ્ત સંદર્ભ (Context Only)

આ ડોક્યુમેન્ટમાં deep-dive નથી (user ના મુખ્ય list માં નથી), પણ સંદર્ભ માટે:

- **QC (`/qc`)** — Test spec/method authoring, sample lifecycle, test order/run/result, OOS/OOT.
  ✅ **2026-09-18 Fixed:** create_sample/receive/test-order/record-result/complete જેવા execution
  actions પર હવે RBAC છે (Operator/Supervisor/Admin); lab-investigation/classify-lab-cause/retest-plan/
  resample-plan/impact-assessment જેવા investigation actions પર QC Reviewer/QA Reviewer/Admin. અગાઉ
  આમાંથી કોઈના પર પણ RBAC ગેટ નહોતી.
- **Validation (`/validation`)** — આ **platform ની પોતાની qualification evidence trail** છે
  (IQ/OQ/PQ, Documents 79-96) — batch manufacturing નો ભાગ નથી, પ્લેટફોર્મ qualify કરવા માટે છે.
  Demo માં ભેગું ના કરવું.

---

## ૧૩.૬ ડેમો વોકથ્રુ — સંપૂર્ણ ક્રમ (Sterilize → Aseptic → EM → Cleaning)

1. **Sterilization cycle** (`sterilization.operator` → `qc.reviewer` accept) — sterile input ready.
2. **EM sample** (`em.technician`/`microbiology.analyst` → `qa.reviewer` review) — area READY.
3. **Line Clearance** (`sanitation.operator`, ડોક્યુમેન્ટ ૦૫) — area cleared.
4. **Cleaning verification** (`sanitation.operator` → `qc.reviewer` verify) — equipment CLEAN.
5. **Aseptic Operation Start** (`aseptic.supervisor`) — **બધા ૪ readiness ચેક pass થાય તો જ start
   થશે**.
6. **Aseptic Execute** (`aseptic.operator`) — intervention/event record → Complete.

---

## ૧૩.૭ ધ્યાન રાખવા જેવી બાબતો (Known Limitations)

1. **EM Alert/Action limits performer-attested છે**, automatic numeric ચેક નથી.
2. **Sterile filter reuse count track થાય છે પણ enforce નથી થતો.**
3. ~~QC core execution pipeline પર કોઈ RBAC ગેટ જ નથી~~ **✅ Fixed (2026-09-18)** — ઉપર ૧૩.૫ જુઓ.
4. **Aseptic Supervisor/Operator split RBAC-only છે** — sterilization/EM/cleaning ની જેમ code-level
   identity-check નથી.
5. **Frontend Sidebar આ આખા cluster ને ફક્ત "signed-in" gate આપે છે** — role-specific button hide/show
   individual page પર જ થાય, backend જ real enforcement છે.
