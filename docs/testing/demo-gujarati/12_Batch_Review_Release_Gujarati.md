# ૧૨. Batch Review અને Release — Gujarati Demo Guide

> Source: `services/gxp-api/app/modules/{qa_review,release}/{models,commands,service,router}.py`,
> `frontend/src/app/{qa-review,release}/`, `services/gxp-api/scripts/seed.py`.

---

## ૧૨.૧ QA Review શું ચેક કરે છે?

**Real completeness check હવે ૯ signal પર આધારિત છે (✅ 2026-09-19 QC/materials/environment/equipment/
yield-reconciliation ઉમેર્યા):**

1. Batch `state == production_complete` છે કે નહીં (નહીં તો blocker)
2. Batch `on_hold` છે કે નહીં (blocker)
3. Vault execution-snapshot integrity (digest/link valid) — blocker if failed
4. **QC** — batch પર (`QcSample.source_type="batch"`) કોઈ release-blocking ટેસ્ટ ઓર્ડરનું latest result
   `oos`/`invalid` છે, અથવા batch પર કોઈ OOS record ખુલ્લું (`state != closed`) છે → blocker
5. **Materials** — batch માં issue થયેલ (`MaterialIssue.batch_id`) કોઈ material lot હજુ `released`/
   `consumed` સિવાયના status માં (quarantine/rejected/expired/વગેરે) છે → blocker
6. **Environment (EM)** — batch સાથે linked (`EmSampleOrReading.batch_id`) કોઈ reading
   `alert_action_status = action_excursion` છે → blocker
7. **Equipment** — batch ના કોઈ step એ actually વાપરેલ (`EquipmentUseLog.batch_id`, ✅ 2026-09-19 નવું
   persisted — પહેલાં step-start પર check થઈને discard થઈ જતું હતું) asset હાલમાં (`get_eligibility()`
   ફરી ચલાવીને) ineligible છે (hold/calibration/qualification/cleaning) → blocker — batch execution પછી
   equipment hold પર ગયું હોય તો પણ પકડાય
8. **Yield/Reconciliation** (✅ 2026-09-19, નવું — જુઓ નીચે "ખોટી claim" નોંધ) — batch પર કોઈ
   `ManufacturingCalculation`/`ReconciliationRecord` `FAILED`/`OUT_OF_LIMIT`/`OUT_OF_TOLERANCE` છે → blocker
9. Batch પર કોઈ "Corrected" audit event છે કે નહીં → `has_exceptions`

**Non-blocking warnings (visible, review complete ને રોકતા નથી):** QC `oot` (out-of-trend) results,
EM `alert`-level readings, calculated-પણ-QA-verify-ના-થયેલ yield/reconciliation record, અધૂરું/unbalanced
Packaging run (`PackagingRun.state != complete` અથવા `reconciliation_state = discrepancy`) —
`GET /qa-review/v1/packages/{id}/exceptions` ના `warnings` array માં દેખાય છે.

> ⚠️ **Genealogy હજુ completeness ચેક તરીકે wired નથી** — nodes/edges હવે ✅ 2026-09-19 real production
> events (material issue → batch, production-complete) પર auto-populate થાય છે (નીચે ૧૨.૬ જુઓ), પણ "batch
> ની genealogy કેટલી complete ગણાય" — એ regulated completeness rule Document 13 ક્યાંય define નથી કરતું
> (guess કરવાને બદલે honestly ખુલ્લું રાખ્યું — SG-054). ડેટા હવે populate થાય છે, પણ blocker/warning
> તરીકે વપરાતી નથી.
>
> ⚠️ **ખોટી claim સુધારી (2026-09-19):** આ doc ની જૂની આવૃત્તિ કહેતી હતી કે "Document 17 (yield/
> reconciliation) ક્યારેય built જ નથી" — એ ખોટું હતું. `yield_reconciliation` module (Calculate/Verify
> API, ડોક્યુમેન્ટ ૮.૭ માં પહેલેથી listed) પહેલેથી જ built હતું, `get_batch_summary()` પોતે
> `release_blocked` flag પણ compute કરતું હતું — ફક્ત review/release ના completeness ચેક એ ક્યારેય call
> નહોતું કરતું. Packaging read-API ની જેમ, જૂની "never built" નોંધ સમય જતાં stale થઈ ગઈ હતી.

**States:** `READY_FOR_REVIEW → REVIEW_COMPLETE`, `REOPENED`. Completeness status: `complete`,
`has_exceptions`, `blocked` — **`complete` સિવાય બીજી કોઈ status પર review complete ના કરી શકાય**
(itemized exception-acceptance path હજુ built નથી).

| Action | Permission | કોણ | Signed? |
|---|---|---|---|
| Create Review Package | `qa_review.create` | Admin, **QA Reviewer** | ના |
| Reindex/Complete Review | `qa_review.execute` | Admin, QA Reviewer | **હા** — "Reviewed" (Complete only) |
| View | `qa_review.view` | બ્રોડ roles | — |

---

## ૧૨.૨ Release — Eligibility ચેક શું ચેક કરે છે?

**Real eligibility હવે ૧૧ વસ્તુ ચેક કરે છે (✅ 2026-09-18 deviation, ✅ 2026-09-19 QC/materials/
environment/equipment/CAPA/yield-reconciliation):**

1. `batch.state == production_complete`
2. QA Review package `REVIEW_COMPLETE` છે અને current version સાથે match કરે છે
3. Batch `on_hold` નથી
4. Vault snapshot integrity
5. **QMS/deviation** — batch પર (`source_type="batch"`) કોઈ deviation ખુલ્લું (`state != CLOSED`) → blocker
   (✅ 2026-09-18 fixed, SG-059)
6. **QC** — release-blocking ટેસ્ટનું latest result `oos`/`invalid`, અથવા batch પર OOS record ખુલ્લું → blocker
7. **Materials** — batch માં issue થયેલ કોઈ lot `released`/`consumed` સિવાયના status માં → blocker
8. **Environment (EM)** — batch સાથે linked કોઈ reading `action_excursion` → blocker
9. **Equipment** — batch એ actually વાપરેલ કોઈ asset હાલમાં ineligible → blocker (૧૨.૧ #૭ જુઓ, same logic)
10. **CAPA** (✅ 2026-09-19, નવું) — batch પર attributed deviation/OOS માંથી ખોલાયેલ કોઈ CAPA હજુ ખુલ્લું
    (`state` CLOSED/CANCELLED સિવાય) → blocker — જુઓ નીચે "CAPA કેવી રીતે"
11. **Yield/Reconciliation** (✅ 2026-09-19, નવું — ખોટી "never built" claim સુધારી, ૧૨.૧ ની નોંધ જુઓ) —
    `FAILED`/`OUT_OF_LIMIT`/`OUT_OF_TOLERANCE` state → blocker

**Non-blocking warnings** (evaluation ના `warnings` array માં, `eligible` ને અસર નથી કરતા): QC `oot`,
EM `alert`, calculated-પણ-verify-ના-થયેલ yield/reconciliation record, અધૂરું/unbalanced Packaging run.

> ⚠️ **Genealogy — data હવે populate થાય છે (૧૨.૬ જુઓ), પણ completeness rule તરીકે હજુ wired નથી**
> (regulated rule Document 13 define નથી કરતું — SG-054). આ એકમાત્ર "કારણ data નથી" ગેપ બાકી છે — QC/
> materials/equipment/environment/CAPA/yield બધા હવે real data + real rule બંને ધરાવે છે.

### CAPA કેવી રીતે wired છે (✅ 2026-09-19) — batch ને directly નહીં, deviation/OOS દ્વારા

Document 27 (CAPA) નું `source_type` field માત્ર ૧૧ મૂલ્યો accept કરે છે (deviation/oos/oot/ncr/complaint/
audit/supplier/risk/trend/security/validation) — **"batch" એમાં નથી**, અને એ deliberately (Document 27 ના
own spec પ્રમાણે) — `"batch"` ને નવું source_type તરીકે ઉમેરવું એ spec ની બહાર જઈને regulated vocabulary
invent કરવા બરાબર થાય, જે અગાઉ પ્રોજેક્ટ-ઓનર દ્વારા ના પાડેલ નિર્ણય હતો.

એટલે બદલે: batch પર attributed (`source_type="batch"`) કોઈ પણ deviation/OOS ને source બનાવીને ખોલાયેલ
CAPA (`CapaRecord.source_type in (deviation, oos)`, `source_id` = એ deviation/OOS ની id) — આ real,
spec-compliant ૨-hop સંબંધ છે, કોઈ નવું field invent નથી કર્યું. એવું કોઈ CAPA હજુ ખુલ્લું હોય તો release
block કરે.

### Release State Machine
```
draft_evaluation → eligible/blocked → released/rejected/hold
                                              ↓
                                          hold (post-release controlled hold — recall જેવું, ORIGINAL decision rewrite નથી થતું)
```

### ⚠️ Scope Limitation (હજુ true)
**ફક્ત `scope_type = "batch"` જ support છે** — device-lot/serial-level release હજુ built નથી.

---

## ૧૨.૩ Permission મેટ્રિક્સ — Release

| Action | Permission | કોણ | Signed? | Meaning |
|---|---|---|---|---|
| Evaluate Eligibility | `release.evaluate` | Admin, QA Reviewer, QA Releaser | ના | — |
| View | `release.view` | બ્રોડ roles | — | — |
| **Release (final disposition)** | `release.release` | Admin, **QA Releaser** (QA Reviewer **નહીં**) | **હા** | "Released" |
| **Hold** | `release.hold` | Admin, QA Reviewer, QA Releaser | **હા** | "Released" (literal — code comment: verbatim per no-guessing rule) |
| **Reject** | `release.reject` | Admin, **QA Releaser** (QA Reviewer **નહીં**) | **હા** | "Released" |

**SoD (code-level):** Release/Hold/Reject signer, batch ના QA review package complete કરનાર વ્યક્તિ
થી **અલગ** હોવો જોઈએ (independent signer check, review ના audit trail સામે verify થાય છે).

**Rework/Reprocess/Destroy — કોઈ approved route built નથી** — release decision codes ફક્ત
RELEASED/REJECTED/HOLD.

---

## ૧૨.૪ ડેમો વોકથ્રુ — Example Filled Data

**Login:** `qa.reviewer` (QA Review) → `qa.releaser` (Release, **અલગ વ્યક્તિ**)

### Step 1 — QA Review Package Create (`qa.reviewer`)
Batch `MJ-PFS-B-2601` (production_complete state) → Review package auto-completeness ચેક.

### Step 2 — Review Complete (`qa.reviewer`, e-signature)
Completeness `complete` હોય તો જ → Signature "Reviewed".

### Step 3 — Release Eligibility Evaluate (`qa.releaser`)
`release.evaluate` → batch eligible/blocked બતાવે.

### Step 4 — Release (`qa.releaser`, **e-signature ફરજિયાત**, independent of reviewer)

| Field | ઉદાહરણ |
|---|---|
| Decision Code | `RELEASED` |
| Reason | — (release ને reason ફરજિયાત નથી) |

---

## ૧૨.૫ Genealogy — હવે auto-populate થાય છે (✅ 2026-09-19, completeness ચેક તરીકે નહીં)

Document 13 §8 પ્રમાણે genealogy nodes/edges domain events (MaterialConsumed, DrugBatchProduced, ...) એ
generate કરવાના હતા, પણ કોઈ module એ events ક્યારેય emit નહોતું કરતું (schema-only, ડેટા ખાલી). હવે ૨
real write path wired છે:

| Event (Document 13 §8) | ક્યાં wired | શું બને |
|---|---|---|
| `MaterialConsumed` | `material/commands.py::issue_material_to_batch` | `material_lot` node + `drug_batch` node (get-or-create) + `CONSUMED_IN` edge |
| `DrugBatchProduced` | `batch_execution/commands.py::production_complete_batch` | `drug_batch` node (get-or-create, જો material issue પહેલેથી ના બનાવેલ હોય તો) |

**ડેમો:** Material issue કરો (`/material-lots` → batch માં issue) → `/genealogy` પેજ પર batch node ના
ancestors જુઓ — issue થયેલ material lot node CONSUMED_IN edge સાથે દેખાશે.

> ⚠️ **Review/Release ના completeness ચેક માં genealogy હજુ blocker/warning તરીકે વપરાતું નથી** — "batch
> ની genealogy ક્યારે complete ગણાય" (દા.ત. શું દરેક recipe material issue થવું ફરજિયાત છે?) એ regulated
> completeness rule Document 13 ક્યાંય define નથી કરતું — data હવે real છે, પણ એ rule guess કરવાને બદલે
> honestly ખુલ્લું રાખ્યું (SG-054).

---

## ૧૨.૬ ધ્યાન રાખવા જેવી બાબતો (Known Limitations)

1. **QA Review completeness હવે QC/materials/environment/equipment/yield-reconciliation પણ wired છે**
   (✅ 2026-09-19) — genealogy data populate થાય છે પણ completeness rule તરીકે નહીં (ઉપર ૧૨.૫ જુઓ) —
   **આ એકમાત્ર બાકી "કારણ real data નથી" ગેપ છે.**
2. **Release eligibility હવે deviation (✅ 2026-09-18) + QC/materials/environment/equipment/CAPA/
   yield-reconciliation (✅ 2026-09-19) block કરે છે.** Genealogy completeness rule હજુ dormant (data
   છે, rule નથી). **Packaging deliberately non-blocking છે** (warning-only, project-owner-directed).
3. **Release ફક્ત `scope_type="batch"` support કરે છે** — device/serial-level નહીં.
4. **Rework/Reprocess/Destroy path built નથી.**
5. `gxp_batch.state` પોતે "Released" ક્યારેય નથી બતાવતું — release decision અલગ `release_scope`
   record પર (ડોક્યુમેન્ટ ૦૮.૨ સાથે cross-reference).
