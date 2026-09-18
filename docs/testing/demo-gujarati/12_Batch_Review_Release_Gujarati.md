# ૧૨. Batch Review અને Release — Gujarati Demo Guide

> Source: `services/gxp-api/app/modules/{qa_review,release}/{models,commands,service,router}.py`,
> `frontend/src/app/{qa-review,release}/`, `services/gxp-api/scripts/seed.py`.

---

## ૧૨.૧ QA Review શું ચેક કરે છે?

**Real completeness check ફક્ત ૩ signal પર આધારિત છે (honestly નોંધવું — full-scope નથી):**

1. Batch `state == production_complete` છે કે નહીં (નહીં તો blocker)
2. Batch `on_hold` છે કે નહીં (blocker)
3. Vault execution-snapshot integrity (digest/link valid) — blocker if failed
4. Batch પર કોઈ "Corrected" audit event છે કે નહીં → `has_exceptions`

> ⚠️ **QC results, materials, equipment, environment, genealogy, packaging, signatures — આમાંથી
> કંઈ પણ completeness ચેક માં આ પાસ માં wired નથી.** Client ને honestly કહેવું — "review by exception"
> નો concept છે, પણ full-scope engine હજુ build નથી થયું.

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

**Real eligibility ફક્ત ૪ વસ્તુ ચેક કરે છે:**

1. `batch.state == production_complete`
2. QA Review package `REVIEW_COMPLETE` છે અને current version સાથે match કરે છે
3. Batch `on_hold` નથી
4. Vault snapshot integrity

> ⚠️ **QC, QMS(deviation/CAPA), materials, equipment, environment, packaging, genealogy,
> yield/reconciliation — ૯ માંથી ૬ eligibility category હજુ કોઈ real data source નથી ધરાવતી**, ચૂપચાપ
> કંઈ contribute નથી કરતી. Honestly flag — batch release "clean" દેખાય તો પણ open deviation/CAPA
> block નથી કરતું (ડોક્યુમેન્ટ ૧૦/૧૧ સાથે cross-reference).

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

## ૧૨.૫ ધ્યાન રાખવા જેવી બાબતો (Known Limitations)

1. **QA Review completeness માત્ર ૩ signal પર છે** — QC/materials/equipment/environment/genealogy/
   packaging/deviation/CAPA — હજુ wired નથી.
2. **Release eligibility ના ૯ માંથી ૬ category dormant છે** — ખાસ કરીને, **open deviation/CAPA batch
   release ને block નથી કરતા** (ડોક્યુમેન્ટ ૧૦/૧૧ સાથે consistent).
3. **Release ફક્ત `scope_type="batch"` support કરે છે** — device/serial-level નહીં.
4. **Rework/Reprocess/Destroy path built નથી.**
5. `gxp_batch.state` પોતે "Released" ક્યારેય નથી બતાવતું — release decision અલગ `release_scope`
   record પર (ડોક્યુમેન્ટ ૦૮.૨ સાથે cross-reference).
